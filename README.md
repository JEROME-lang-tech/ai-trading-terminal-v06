# AI Trading Engine

A multi-strategy algorithmic trading engine with adaptive strategy weighting,
regime detection, and hard risk circuit breakers. Runs against a paper
simulator, MetaTrader 5 (demo *or* real), or a crypto exchange.

---

## Read this first: about "0% loss"

**It does not exist.** No system — not this one, not a hedge fund's, not any
AI's — can guarantee zero loss. Markets contain irreducible uncertainty: gaps,
flash crashes, liquidity voids, news. Anyone promising 0% loss is either
lying, running martingale/grid logic that earns small steady returns until a
single catastrophic wipeout, or showing you unrealised paper P&L.

What this engine does instead is make losses **bounded and survivable**:

| Guarantee | Mechanism |
|---|---|
| Every loss is capped | Hard stop-loss on every position, placed at order time |
| A stop can only tighten | Stops never move against you — enforced in `risk.py` |
| Per-trade risk is fixed | 0.5% of equity (configurable) |
| A bad day stops the day | −5% daily → flatten all + halt |
| A bad week stops the week | −10% weekly → flatten all + halt |
| Catastrophe stops everything | −20% drawdown → full shutdown, **manual re-arm required** |
| No account-killers | Martingale, grid and averaging-down are blocked in code |

On the 2-year validation, the worst drawdown was **−2.54%** and Monte Carlo
puts the 95th-percentile worst case at about **−7%**.

---

## What it actually does

```
market data ──> indicators ──> 7 strategies ──> regime detection
                                   │                  │
                                   └──> adaptive <────┘
                                        weights
                                           │
                                    ensemble vote
                                           │
                              conviction >= 0.40 ?
                                           │
                                    risk engine  ──> broker
                                    (veto power)
```

- **7 trend strategies**: supertrend, ADX/DI, Donchian breakout, EMA cross,
  MACD, momentum ROC, Kaufman efficiency ratio
- **Regime detection**: classifies each bar as `TREND_UP / TREND_DOWN / RANGE
  / HIGH_VOL` and re-weights strategy categories accordingly
- **Adaptive weighting**: each strategy's weight tracks its recent
  risk-adjusted realised contribution, so ones that stop working lose
  influence automatically
- **Conviction gate**: trades only fire at `|score| ≥ 0.40`
- **Asymmetric payoff**: stop at 3 ATR, backstop target at 6 ATR, trailing
  stop after 1R so winners can run
- **Risk engine veto**: can overrule anything, including a confident model

The ML meta-filter (gradient-boosted, walk-forward trained) is included but
**disabled by default** — it measurably reduced expectancy. See `RESEARCH.md`.

---

## Quick start

```bash
pip install numpy pandas scikit-learn matplotlib fastapi uvicorn

# run a full research pass: backtest + walk-forward + Monte Carlo
python run_backtest.py --symbol BTC-USD

# run the engine on paper money
python run_live.py

# or open the dashboard
python -m uvicorn aitrader.dashboard.server:api --host 0.0.0.0 --port 8000
```

The dashboard is a full trading terminal:

- **Candlestick chart** — OHLC + volume + EMA20/50, with entry and exit
  markers plotted on the bars, and live stop/target lines for the open
  position. Hover for an OHLC crosshair readout.
- **Market watch** — price, regime and a signed conviction bar per symbol
- **AI signal dial** — the ensemble vote on a gauge with the ±0.40 conviction
  gate marked, plus live per-strategy weight bars (watch these drift over time)
- **Risk monitor** — drawdown and daily-loss usage against their limits, and
  the state of every circuit breaker
- **Trade journal / event log / validation** tabs at the bottom

---

## Testing

```bash
pip install pytest httpx
pytest tests/ -q          # 69 tests
```

The suite covers the things that would quietly cost you money:

- **No look-ahead** — signals computed on truncated history must match the
  full-history computation bar for bar
- **Risk guarantees** — per-trade risk caps, stops that only ever tighten,
  breakers that actually trip, martingale/grid/averaging-down blocked
- **Regressions** — including the two real bugs found during development:
  a weight floor that silently disabled adaptive weighting, and a Monte Carlo
  that reported the drawdown tail backwards
- **API and persistence** — every endpoint, and DB survival across restart

Testing found one genuine safety bug: the daily-loss breaker was evaluated
before the max-drawdown breaker and returned early, so a −25% drawdown was
mislabelled a daily halt — which auto-lifts at midnight. An account down 25%
would have silently resumed trading with no human re-arming it. Breakers are
now evaluated most-severe-first.

---

## Standalone executable

No Python required on the target machine.

```bash
pip install pyinstaller
python build_exe.py        # builds release/ai-trader for the CURRENT OS
./release/ai-trader        # then open http://localhost:8000
```

`build_exe.py` bundles the engine, the dashboard, cached market data and the
reports into one file (~130 MB, mostly numpy/pandas). It opens your browser
automatically; set `NO_BROWSER=1` on servers.

**PyInstaller cannot cross-compile** — run it on Windows to get a `.exe`, on
macOS for a Mac binary. To get all three without installing anything locally:

```bash
git tag v1.0.0 && git push --tags
```

The `.github/workflows/build.yml` workflow builds Windows, macOS and Linux
binaries on their own runners, smoke-tests each one against `/healthz`, and
attaches them to a GitHub release. You can also trigger it manually from the
Actions tab.

---

## Deployment (free)

The app is deployment-ready and verified: `python deploy_check.py` boots it
exactly the way a host does (env-driven port, fresh database, secret set),
exercises every endpoint, kills the process, restarts it, and confirms state
survived. **25/25 checks pass.**

Dockerfile, `render.yaml`, `fly.toml`, `Procfile`, `runtime.txt`,
HuggingFace Space config and a GitHub Actions workflow are all included.

```bash
docker build -t ai-trader . && docker run -p 8000:8000 ai-trader
```

See **`DEPLOY.md`** for the honest comparison of free options, keep-alive
setup, and environment variables. Short version:

| Option | Cost | Always-on | Persistent disk |
|---|---|---|---|
| **Render** free | $0 | sleeps ~15 min idle | no (paid add-on) |
| **HuggingFace Spaces** | $0 | sleeps ~48 h idle | no |
| **Oracle Cloud Always Free** | $0 | **yes** | **yes** |
| Fly / Railway / Koyeb | limited allowances | varies | varies |

Free tiers sleep and have ephemeral disks — fine for paper trading, **not**
for real money. Oracle's Always Free ARM VM is the best zero-cost option if
you eventually want this running unattended for real.

Set `APP_TOKEN` on any public deploy; it guards every route except `/healthz`.

---

## Demo → real: the path

You said you want to test on demo *and* real. That is the right order, and
this is the sequence I'd hold you to:

1. **Paper (this repo, simulator)** — a minimum of **4 weeks**, ideally 8.
   Watch the decision log daily. You are checking that live behaviour matches
   the backtest, not that it's profitable yet.
2. **MT5 demo or Kraken dry-run** — **4+ weeks** on the broker's own
   feed/fills. This catches symbol naming, contract sizes, spread behaviour
   and session quirks that a simulator cannot.
3. **Real, small** — fund with an amount you are fully prepared to lose.
   Keep `risk_per_trade_pct` at 0.5%. Run for **3 months** before sizing up.
4. **Scale** — only after step 3 matches the backtest's *behaviour* (similar
   win rate, similar drawdown shape), not just its P&L.

Red flags that mean go back a step: live win rate more than ~8 points below
backtest, drawdown exceeding the Monte Carlo 95th percentile, or fills
consistently worse than the modelled slippage.

### MetaTrader 5

```bash
pip install MetaTrader5
```

```python
from aitrader.config import PROFILES
cfg = PROFILES["validated"]()
cfg.execution.venue      = "mt5"
cfg.execution.account_type = "demo"      # "real" for live money
cfg.execution.mt5_login    = 12345678
cfg.execution.mt5_password = "..."
cfg.execution.mt5_server   = "YourBroker-Demo"   # "...-Live" for real
cfg.execution.symbols      = ["EURUSD", "XAUUSD"]
cfg.execution.timeframe    = "1h"
```

**Demo and real are the same code path** — only those three credentials
change. That is deliberate: your demo should run byte-for-byte the logic you
later run with real money, otherwise it proves nothing.

> The MT5 Python API requires the Windows/Mac desktop terminal. It will not
> run on Linux. On Linux, use the crypto adapter or a Windows VPS.

### Real-money confirmation

`run_live.py --account real` refuses to start until you type
`I UNDERSTAND THE RISK`. This is intentional friction, not a bug.

---

## Risk configuration

```python
cfg.risk.risk_per_trade_pct   = 0.5    # % equity risked per trade
cfg.risk.atr_stop_multiple    = 3.0    # stop distance
cfg.risk.max_daily_loss_pct   = 5.0    # flatten + halt
cfg.risk.max_weekly_loss_pct  = 10.0   # flatten + halt
cfg.risk.max_drawdown_pct     = 20.0   # SHUTDOWN, manual re-arm
cfg.risk.max_concurrent_positions = 4
cfg.risk.max_gross_exposure_pct  = 40.0
```

Profiles: `validated` (default, walk-forward tested), `conservative`,
`moderate`, `aggressive`. I would not use `aggressive` without re-running the
validation at that sizing and reading the Monte Carlo tail first.

---

## Validated results (2y, 6h bars, BTC + ETH + SOL)

| | |
|---|---|
| Total return | **+4.90%** (2.42% CAGR) |
| Max drawdown | **−2.54%** |
| Trades | 184 |
| Win rate | 46.1% |
| Profit factor | 1.35 |
| Expectancy | +0.180R per trade |
| Out-of-sample folds profitable | **10 / 12** |

Monte Carlo (2000 reshuffles of the real trades): median max DD ≈ −3.4%,
95th-percentile worst ≈ −7%, P(hitting the −20% breaker) = 0.0%, P(profit)
78–86%.

These are modest, real numbers. At 0.5% risk per trade this is a low-return,
low-drawdown system. Raising `risk_per_trade_pct` scales both return and
drawdown roughly proportionally — and the drawdown is what ends accounts.

---

## Repo layout

```
aitrader/
  config.py        risk + strategy + execution config, profiles
  indicators.py    50+ technical indicators (no look-ahead)
  data.py          Coinbase/Kraken fetchers, cache, synthetic fallback
  strategies.py    20-strategy library (7 enabled by default)
  ensemble.py      regime detection, adaptive weighting, ML meta-filter
  risk.py          sizing, stops, circuit breakers  <- the important one
  backtest.py      event-driven backtester, walk-forward, Monte Carlo
  db.py            SQLite persistence (survives restarts)
  engine.py        live/paper trading loop
  brokers/         simulator | mt5 | kraken
  dashboard/       FastAPI backend + trading terminal UI
tests/             69 tests (pytest)
run_backtest.py    research runner
run_live.py        live runner (demo or real)
deploy_check.py    25-point deployment pre-flight
Dockerfile, render.yaml, fly.toml, Procfile   deployment
RESEARCH.md        what worked, what didn't, and why
DEPLOY.md          free-hosting guide
reports/           validation output
```

---

## Disclaimer

This is trading software. It will lose money sometimes. Past and backtested
results do not predict live results, and live results are typically worse
than backtests. Nothing here is financial advice. Do not trade with money you
cannot afford to lose, and understand every component before you enable real
trading.
