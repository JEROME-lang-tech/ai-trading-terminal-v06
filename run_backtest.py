#!/usr/bin/env python3
"""
Full research run: backtest + walk-forward validation + Monte Carlo.

  python run_backtest.py
  python run_backtest.py --symbol ETH-USD --profile validated
"""
import argparse, json, os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aitrader.config import PROFILES
from aitrader import data, indicators as ind, backtest as bt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="BTC-USD")
    ap.add_argument("--profile", default="validated", choices=list(PROFILES))
    ap.add_argument("--timeframe", default=None)
    ap.add_argument("--days", type=int, default=730)
    ap.add_argument("--save", default="reports")
    args = ap.parse_args()

    cfg = PROFILES[args.profile]()
    tf = args.timeframe or cfg.execution.timeframe

    print(f"\nLoading {args.symbol} {tf} ({args.days}d)...")
    df = data.load(args.symbol, tf, days=args.days, verbose=True)
    print(f"Building indicators...")
    df = ind.add_all(df)

    print(f"\nRunning backtest...")
    r = bt.run_backtest(df, cfg, symbol=args.symbol, verbose=True)
    r.monte_carlo = bt.monte_carlo(r.trades, cfg, sims=2000)
    print(r.report())

    print("\nWalk-forward (out-of-sample folds):")
    folds = bt.walk_forward(df, cfg, symbol=args.symbol, n_folds=4)
    pos = sum(1 for f in folds if f["expectancy_r"] > 0)
    print(f"  {pos}/{len(folds)} folds profitable")

    os.makedirs(args.save, exist_ok=True)
    stem = f"{args.symbol}_{tf}_{args.profile}"
    r.equity.to_csv(f"{args.save}/{stem}_equity.csv")
    if len(r.trades):
        r.trades.to_csv(f"{args.save}/{stem}_trades.csv", index=False)
    summary = {"symbol": args.symbol, "timeframe": tf, "profile": args.profile,
               "metrics": r.metrics, "monte_carlo": r.monte_carlo, "folds": folds}
    with open(f"{args.save}/{stem}_summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)
    with open(f"{args.save}/{stem}_report.txt", "w") as f:
        f.write(r.report())
    print(f"\nSaved to {args.save}/{stem}_*")


if __name__ == "__main__":
    main()
