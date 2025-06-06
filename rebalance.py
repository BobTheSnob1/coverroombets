#!/usr/bin/env python3
"""
Rebalance a mock-stock portfolio so that each ticker in the market has the same total value.
Supports saving/loading the portfolio to/from a CSV file. 
- If a portfolio text file is provided, updates the saved CSV accordingly.
- If no portfolio text file is provided, uses the saved CSV.
- After generating trades, applies them to the in-memory portfolio and writes out the updated CSV.

Usage:
    python rebalance_all.py --market market.txt [--portfolio portfolio.txt]

Outputs a series of commands of the form:
    !sell TICKER QTY
    !buy TICKER QTY

Sell commands are printed first to free up cash, then buys.  
At the end, the updated portfolio (quantities and cash) is saved to "saved_portfolio.csv".
"""

import argparse
import re
import math
import os
import pandas as pd

SAVED_CSV = "saved_portfolio.csv"

def parse_portfolio_text(path):
    """
    Parse the portfolio text file.
    Expected format:
        💰 Cash
        €<cash_amount>
        📈 Stocks Owned
        <Full Name> (<TICKER>): <quantity> shares
        ...
    Returns:
        cash (float), stocks (dict: ticker -> quantity(int))
    """
    with open(path, "r", encoding="utf-8") as f:
        raw_lines = [line.strip() for line in f.readlines()]
    lines = [line for line in raw_lines if line]

    cash = 0.0
    stocks = {}

    for i, line in enumerate(lines):
        if line.startswith("💰 Cash"):
            if i + 1 < len(lines):
                cash_str = lines[i+1].lstrip("€").replace(",", "")
                cash = float(cash_str)
            break

    for i, line in enumerate(lines):
        if line.startswith("📈 Stocks Owned"):
            for j in range(i+1, len(lines)):
                m = re.match(r".*\((?P<ticker>[^)]+)\):\s*(?P<qty>\d+)\s*shares", lines[j])
                if m:
                    ticker = m.group("ticker").strip()
                    qty = int(m.group("qty"))
                    stocks[ticker] = qty
            break

    return cash, stocks

def load_saved_portfolio():
    """
    Load portfolio from SAVED_CSV. Expects CSV with columns [ticker, quantity].
    Includes a row with ticker="CASH" and quantity=<cash amount>.
    Returns:
        cash (float), stocks (dict: ticker -> quantity(int))
    """
    if not os.path.exists(SAVED_CSV):
        raise FileNotFoundError(f"No saved portfolio CSV found at '{SAVED_CSV}'. Provide a portfolio text file to initialize.")
    df = pd.read_csv(SAVED_CSV)
    if "ticker" not in df.columns or "quantity" not in df.columns:
        raise ValueError(f"Saved CSV '{SAVED_CSV}' must have columns: ticker, quantity")
    cash_row = df[df["ticker"] == "CASH"]
    if cash_row.empty:
        raise ValueError(f"Saved CSV '{SAVED_CSV}' missing CASH row. Provide a portfolio text file to initialize.")
    cash = float(cash_row.iloc[0]["quantity"])
    stocks = {}
    for _, row in df[df["ticker"] != "CASH"].iterrows():
        stocks[row["ticker"]] = int(row["quantity"])
    return cash, stocks

def save_portfolio_csv(cash, stocks):
    """
    Save the portfolio to SAVED_CSV as a CSV with columns:
        ticker, quantity
    Includes a row with ticker="CASH" for the cash amount.
    """
    rows = []
    # Cash row first
    rows.append({"ticker": "CASH", "quantity": cash})
    # Then one row per ticker
    for t, qty in stocks.items():
        rows.append({"ticker": t, "quantity": qty})
    df = pd.DataFrame(rows)
    df.to_csv(SAVED_CSV, index=False)
    print(f"# Saved updated portfolio to '{SAVED_CSV}'")

def parse_market(path):
    """
    Parse the market summary file.
    Expected format (blank lines may be ignored):
        Market Day X Summary
        Closing Prices
        <Full Name> (<TICKER>)
        €<price>
        <Full Name> (<TICKER>)
        €<price>
        ...
    Returns:
        prices (dict: ticker -> price(float))
    """
    with open(path, "r", encoding="utf-8") as f:
        raw_lines = [line.strip() for line in f.readlines()]
    lines = [line for line in raw_lines if line]

    prices = {}
    i = 0
    while i < len(lines):
        m = re.match(r".*\((?P<ticker>[^)]+)\)", lines[i])
        if m and (i+1) < len(lines):
            ticker = m.group("ticker").strip()
            price_line = lines[i+1]
            pm = re.match(r"€(?P<price>[\d\.]+)", price_line)
            if pm:
                prices[ticker] = float(pm.group("price"))
                i += 2
                continue
        i += 1

    return prices

def rebalance(cash, stocks, prices):
    """
    Given:
        cash   = available cash in €
        stocks = { ticker: quantity }
        prices = { ticker: price(float) }
    Compute trades to rebalance across all tickers in prices, 
    returning two lists: sells, buys. 
    After printing them, the calling code should apply the trades to update cash/stocks.
    """
    all_tickers = sorted(prices.keys())
    N = len(all_tickers)

    # Current values
    current_value = {}
    for t in all_tickers:
        old_qty = stocks.get(t, 0)
        current_value[t] = old_qty * prices[t]

    total_stock_value = sum(current_value.values())
    total_portfolio_value = total_stock_value + cash
    target_value = total_portfolio_value / N

    # Compute ideal (floating) shares and floor
    ideal_shares = {}
    new_shares = {}
    for t in all_tickers:
        p = prices[t]
        f = target_value / p
        ideal_shares[t] = f
        new_shares[t] = int(math.floor(f))

    # Compute leftover cash after flooring
    cost_floor = sum(new_shares[t] * prices[t] for t in all_tickers)
    remaining_cash = total_portfolio_value - cost_floor

    # Distribute leftover cash by largest fractional remainders
    remainders = []
    for t in all_tickers:
        remainder = ideal_shares[t] - new_shares[t]
        remainders.append((t, remainder))
    remainders.sort(key=lambda x: x[1], reverse=True)
    for t, rem in remainders:
        price_t = prices[t]
        if price_t <= remaining_cash:
            new_shares[t] += 1
            remaining_cash -= price_t

    # Build sell/buy lists
    sells = []
    buys = []
    for t in all_tickers:
        old_qty = stocks.get(t, 0)
        diff = new_shares[t] - old_qty
        if diff < 0:
            sells.append((t, -diff))
        elif diff > 0:
            buys.append((t, diff))

    # Return in order: sells then buys
    return sells, buys

def apply_trades(cash, stocks, prices, sells, buys):
    """
    Apply sell orders first (takes cash += qty * price, stocks[t] -= qty),
    then apply buys (cash -= qty*price, stocks[t] += qty).
    Returns updated (cash, stocks).
    """
    # Process sells
    for t, qty in sells:
        if qty <= 0:
            continue
        if t not in stocks or stocks[t] < qty:
            raise ValueError(f"Cannot sell {qty} of {t}: only have {stocks.get(t, 0)} shares.")
        cash += qty * prices[t]
        stocks[t] -= qty
        if stocks[t] == 0:
            del stocks[t]

    # Process buys
    for t, qty in buys:
        cost = qty * prices[t]
        if cost > cash + 1e-8:  # small tolerance
            raise ValueError(f"Not enough cash to buy {qty} of {t}: need {cost:.2f}, have {cash:.2f}")
        cash -= cost
        stocks[t] = stocks.get(t, 0) + qty

    return cash, stocks

def main():
    parser = argparse.ArgumentParser(
        description="Rebalance a mock-stock portfolio and persist to CSV."
    )
    parser.add_argument(
        "--portfolio",
        "-p",
        required=False,
        help="Path to the portfolio text file (cash + stocks owned). If omitted, loads from saved CSV."
    )
    parser.add_argument(
        "--market",
        "-m",
        required=True,
        help="Path to the market summary text file (ticker prices)."
    )
    args = parser.parse_args()

    # 1) Load or initialize portfolio
    if args.portfolio:
        # Parse provided portfolio, then overwrite saved CSV
        cash, stocks = parse_portfolio_text(args.portfolio)
        save_portfolio_csv(cash, stocks)
    else:
        # Load from existing CSV
        cash, stocks = load_saved_portfolio()

    # 2) Parse market prices
    prices = parse_market(args.market)

    # 3) Compute trades to rebalance across all market tickers
    sells, buys = rebalance(cash, stocks, prices)

    # 4) Output sell commands first
    if not sells and not buys:
        print("# Portfolio is already balanced (or no trades needed).")
    else:
        for t, qty in sells:
            print(f"!sell {t} {qty}")
        for t, qty in buys:
            print(f"!buy {t} {qty}")

    # 5) Apply trades to update in-memory portfolio
    cash, stocks = apply_trades(cash, stocks, prices, sells, buys)

    # 6) Save updated portfolio to CSV
    save_portfolio_csv(cash, stocks)

if __name__ == "__main__":
    main()
