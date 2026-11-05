# Start here — 60 seconds to a running app

## 1. Install

You need **Python 3.10+**. Check with `python --version`.

```bash
pip install -r requirements.txt
```

MT5 users on Windows also need: `pip install MetaTrader5` (uncomment it in
`requirements.txt`). It requires the MT5 desktop terminal installed and logged
in. It will **not** work on Linux.

## 2. Run the dashboard

**Linux / macOS:**
```bash
./start.sh
```

**Windows:** double-click `start.bat`

**Or manually:**
```bash
python -m uvicorn aitrader.dashboard.server:api --host 0.0.0.0 --port 8000
```

Then open **http://localhost:8000**

It boots straight into **paper trading** against live market prices. No API
key, no account, no money. You'll see positions open within seconds.

## 3. What you're looking at

- **Top cards** — equity, return, drawdown, win rate, expectancy
- **Equity curve** — updates every 5 seconds
- **Live signals** — per-symbol score, market regime, and how much weight
  each strategy currently carries. Watch these weights shift over time; that's
  the adaptive layer working.
- **Decision log** — every `ENTER` and every `skip`, with the reason. The
  skips matter most: `conviction 0.26 < 0.4` is the system declining to trade.
- **Walk-forward panel** — the out-of-sample validation and Monte Carlo tail
  risk. This is what the strategy is actually expected to do.

**Buttons:** Start / Pause / Resume / Tick now / **Flatten all** / Stop /
Re-arm breakers.

## 4. Command line instead

```bash
python run_backtest.py --symbol BTC-USD    # research: backtest + walk-forward + Monte Carlo
python run_live.py                          # paper trading, no dashboard
python run_live.py --venue mt5 --account demo
python run_live.py --venue mt5 --account real   # asks for typed confirmation
```

## 5. One-file executable (no Python needed)

```bash
pip install pyinstaller && python build_exe.py
./release/ai-trader
```

Builds for the OS you run it on. For a Windows `.exe`, push a tag
(`git tag v1.0.0 && git push --tags`) — the included GitHub Action builds
Windows/macOS/Linux binaries, smoke-tests each, and attaches them to a release.
Or just use `start.bat`, which needs Python but no build step.

## 6. Deploy it for free (optional)

The app is deploy-ready. `Dockerfile`, `render.yaml`, `fly.toml`, `Procfile`
and a HuggingFace config are included — see **DEPLOY.md**.

```bash
python deploy_check.py     # 25-point pre-flight, verifies restart survival
```

Quickest free path: push to GitHub → Render "New Blueprint" → it reads
`render.yaml` → point a free UptimeRobot monitor at `/healthz` to stop it
sleeping. Set `APP_TOKEN` so strangers can't hit your controls.

⚠️ Free tiers sleep and lose their disk. Great for paper trading. Do **not**
run real money on a sleeping free instance — a missed tick is a missed exit.

## 7. Cached data

`data/` ships with ~2 years of real 6h/1h candles for BTC, ETH and SOL, so the
first run works **offline**. Delete those CSVs to re-fetch fresh data from
Coinbase/Kraken (no API key needed — they're public endpoints).

---

## Before real money — the short version

1. **Paper here: 4–8 weeks.** Watch the decision log daily.
2. **Broker demo: 4+ weeks.** MT5 demo or Kraken dry-run.
3. **Real, small, 3 months** at 0.5% risk before sizing up.

`--account real` refuses to start until you type `I UNDERSTAND THE RISK`.

**0% loss is not achievable.** This system is built so losses are bounded and
recoverable: hard stop on every trade, −5% daily halt, −20% drawdown shutdown
requiring manual re-arm. On 2 years of validation the worst drawdown was
−2.54%; Monte Carlo puts the 95th-percentile worst case near −7%. It still
loses on individual trades about 54% of the time.

Read `README.md` for the full setup, `DEPLOY.md` for hosting, and
`RESEARCH.md` for what I tested that didn't work (most of it).

Running the tests: `pip install pytest httpx && pytest tests/ -q` (69 tests).
