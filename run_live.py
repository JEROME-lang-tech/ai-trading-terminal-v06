#!/usr/bin/env python3
"""
Run the engine live (paper or real).

  python run_live.py                                  # paper / simulator
  python run_live.py --venue mt5 --account demo       # MT5 demo account
  python run_live.py --venue mt5 --account real       # MT5 REAL money (asks for confirmation)
  python run_live.py --profile aggressive
"""
import argparse, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aitrader.config import PROFILES
from aitrader.engine import TradingEngine, make_broker


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--venue", default="simulator",
                    choices=["simulator", "mt5", "kraken"])
    ap.add_argument("--account", default="demo", choices=["demo", "real"])
    ap.add_argument("--profile", default="validated", choices=list(PROFILES))
    ap.add_argument("--interval", type=int, default=300, help="seconds between ticks")
    args = ap.parse_args()

    cfg = PROFILES[args.profile]()
    cfg.execution.venue = args.venue
    cfg.execution.account_type = args.account

    if args.account == "real":
        print("\n" + "!" * 66)
        print("  REAL MONEY MODE")
        print("!" * 66)
        print(f"  venue   : {args.venue}")
        print(f"  risk    : {cfg.risk.risk_per_trade_pct}% of equity per trade")
        print(f"  breakers: daily -{cfg.risk.max_daily_loss_pct}%  "
              f"weekly -{cfg.risk.max_weekly_loss_pct}%  "
              f"max DD -{cfg.risk.max_drawdown_pct}%")
        print()
        print("  Losses WILL happen. The breakers bound them; they do not")
        print("  eliminate them. There is no such thing as 0% loss.")
        print("!" * 66 + "\n")
        if input('  Type "I UNDERSTAND THE RISK" to arm: ').strip() != "I UNDERSTAND THE RISK":
            print("  Not armed. Exiting.")
            return
        cfg.execution.real_trading_confirmed = True

    broker = make_broker(cfg)
    eng = TradingEngine(cfg, broker)
    if not eng.start(interval_seconds=args.interval):
        print("failed to start:", eng.error)
        return

    print("\nEngine running. Ctrl+C to stop (positions stay open unless you flatten).")
    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        print("\nstopping...")
        eng.stop(flatten=False)


if __name__ == "__main__":
    main()
