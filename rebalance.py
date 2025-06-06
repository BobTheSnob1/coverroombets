#!/usr/bin/env python3
"""
Rebalance a mock-stock portfolio so that each ticker in the market has the same total value.
Reads two text files:
  1. A “portfolio” file containing your current cash and owned-shares listing.
  2. A “market” file containing the latest closing prices for all tickers.

Usage:
    python rebalance_all.py --portfolio portfolio.txt --market market.txt

Outputs a series of commands of the form:
    !buy TICKER QTY
    !sell TICKER QTY
which will rebalance your holdings so that every ticker listed in the market file
ends up with (as close as possible) the same total value.  Any leftover cash that
cannot be spent on a whole share is minimized.
"""

import argparse
import re
import math

def parse_portfolio(path):
    """
    Parse the portfolio file.
    Expected format (blank lines may be ignored):
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

    # Remove any empty lines
    lines = [line for line in raw_lines if line]

    cash = 0.0
    stocks = {}

    # Find the line with “💰 Cash” and grab the next nonempty line as the cash amount
    for i, line in enumerate(lines):
        if line.startswith("💰 Cash"):
            if i + 1 < len(lines):
                cash_str = lines[i + 1].lstrip("€").replace(",", "")
                cash = float(cash_str)
            break

    # Find “📈 Stocks Owned” and parse subsequent lines as “Name (TICKER): qty shares”
    for i, line in enumerate(lines):
        if line.startswith("📈 Stocks Owned"):
            # Everything after this line should be “Name (TICKER): <qty> shares”
            for j in range(i + 1, len(lines)):
                m = re.match(r".*\((?P<ticker>[^)]+)\):\s*(?P<qty>\d+)\s*shares", lines[j])
                if m:
                    ticker = m.group("ticker").strip()
                    qty = int(m.group("qty"))
                    stocks[ticker] = qty
            break

    return cash, stocks


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

    # Remove empty lines
    lines = [line for line in raw_lines if line]

    prices = {}
    i = 0
    while i < len(lines):
        # Look for lines that contain “(<TICKER>)”
        m = re.match(r".*\((?P<ticker>[^)]+)\)", lines[i])
        if m and (i + 1) < len(lines):
            ticker = m.group("ticker").strip()
            price_line = lines[i + 1]
            pm = re.match(r"€(?P<price>[\d\.]+)", price_line)
            if pm:
                price = float(pm.group("price"))
                prices[ticker] = price
                i += 2
                continue
        i += 1

    return prices


def rebalance(cash, stocks, prices):
    """
    Given:
        cash   = available cash in €
        stocks = { ticker: current_quantity }
        prices = { ticker: current_price_in_€ }

    Calculate trades to rebalance so each ticker in the market ends up
    with (as close as possible) the same total value. Return a list
    of strings like “!buy TICKER QTY” or “!sell TICKER QTY”.
    """

    # 1) Use all tickers listed in 'prices', even those with zero current quantity
    all_tickers = sorted(prices.keys())
    N = len(all_tickers)

    # 2) Compute current value in each position (zero if not currently owned)
    current_value = {}
    for t in all_tickers:
        old_qty = stocks.get(t, 0)
        current_value[t] = old_qty * prices[t]

    total_stock_value = sum(current_value.values())
    total_portfolio_value = total_stock_value + cash

    # 3) The “ideal” per-ticker value if we split total_portfolio_value evenly
    #    among all N tickers in the market.
    target_value = total_portfolio_value / N

    # 4) Compute the “ideal” (floating) number of shares for each ticker, and floor it
    ideal_shares = {}
    new_shares = {}
    for t in all_tickers:
        p = prices[t]
        f = target_value / p
        ideal_shares[t] = f
        new_shares[t] = int(math.floor(f))

    # 5) See how much cash is needed to buy all those floored share counts
    cost_floor = sum(new_shares[t] * prices[t] for t in all_tickers)
    remaining_cash = total_portfolio_value - cost_floor

    # 6) Distribute any leftover cash by giving +1 share to whichever ticker
    #    has the largest fractional remainder (if we can afford it).
    remainders = []
    for t in all_tickers:
        remainder = ideal_shares[t] - new_shares[t]
        remainders.append((t, remainder))
    # Sort tickers by descending fractional remainder
    remainders.sort(key=lambda x: x[1], reverse=True)

    for t, rem in remainders:
        price_t = prices[t]
        if price_t <= remaining_cash:
            new_shares[t] += 1
            remaining_cash -= price_t

    # 7) Build trade commands based on the difference between new_shares and old quantity
    commands = []
    for t in all_tickers:
        old_qty = stocks.get(t, 0)
        diff = new_shares[t] - old_qty
        if diff > 0:
            commands.append(f"!buy {t} {diff}")
        elif diff < 0:
            commands.append(f"!sell {t} {-diff}")

    return commands


def main():
    parser = argparse.ArgumentParser(
        description="Rebalance a mock-stock portfolio so that each ticker in the market has equal value."
    )
    parser.add_argument(
        "--portfolio",
        "-p",
        required=True,
        help="Path to the portfolio text file (cash + stocks owned)",
    )
    parser.add_argument(
        "--market",
        "-m",
        required=True,
        help="Path to the market summary text file (ticker prices)",
    )
    args = parser.parse_args()

    cash, stocks = parse_portfolio(args.portfolio)
    prices = parse_market(args.market)

    trades = rebalance(cash, stocks, prices)
    if not trades:
        print("# Portfolio is already balanced (or no trades needed).")
    else:
        for cmd in trades:
            print(cmd)


if __name__ == "__main__":
    main()
