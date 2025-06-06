# coverroombets

a utility for creating an equal-value index fund from portfolio and stock updates. 

```
usage: rebalance.py [-h] --portfolio PORTFOLIO --market MARKET
rebalance.py: error: the following arguments are required: --portfolio/-p, --market/-m
```

example market.txt:
```
Cover (COVR)
€5.19
Fysich-Mathematische Faculteitsvereniging (FMF)
€31.07
Cleopatra (CLEO)
€91.60
Albertus Magnus (ALMG)
€76.12
Unitas (UNIT)
€98.45
ESN Groningen (ESNG)
€14.15
SIB Groningen (SIBG)
€15.65
AIESEC Groningen (AIEG)
€48.12
Dizkartes Groningen (DIZK)
€72.56
Your Mum Inc. (YMUM)
€239.03
```

example portfolio.txt:
```
💰 Cash
€71.69
📈 Stocks Owned
Cover (COVR): 85 shares
AIESEC Groningen (AIEG): 9 shares
Albertus Magnus (ALMG): 6 shares
Cleopatra (CLEO): 5 shares
Dizkartes Groningen (DIZK): 7 shares
ESN Groningen (ESNG): 35 shares
Fysich-Mathematische Faculteitsvereniging (FMF): 17 shares
SIB Groningen (SIBG): 32 shares
Unitas (UNIT): 5 shares
Your Mum Inc. (YMUM): 2 shares
```