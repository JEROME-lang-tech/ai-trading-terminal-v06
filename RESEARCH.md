# Research log — what actually worked, what didn't

The point of this document is that **most of the ideas in this repo did not
work**, and the ones that shipped survived because they were measured, not
because they sounded good. Every claim below is reproducible with the scripts
in this repo.

Data: 2 years of real 6h/1h candles, BTC-USD / ETH-USD / SOL-USD, Coinbase +
Kraken public APIs (2024-11 → 2026-11). ~2,900 bars per market.

---

## 1. The signal study that killed the first design

The original spec was "AI analyses every strategy and method available".
So I built 14 strategies (trend, mean-reversion, volatility, volume, price
action), a regime classifier, adaptive weighting and a gradient-boosted
meta-model, then tested it on hourly BTC.

**Testing method.** Not hit-rate — that is misleading. I used a *barrier
test*: for every bar where a signal fires, does price reach `+X·ATR` before
it reaches `−Y·ATR` over the next N bars? Competing barriers are the only
honest way to measure a signal, because they force the stop and the target to
race each other.

Result on hourly BTC (17,511 bars), expected value in ATR units:

| selection | tgt 3 / stp 2 | tgt 4 / stp 2 | tgt 6 / stp 3 | tgt 8 / stp 3 |
|---|---|---|---|---|
| all bars | −0.17 | −0.30 | −1.25 | −1.59 |
| \|score\| ≥ 0.20 | −0.10 | −0.18 | −1.09 | −1.44 |
| \|score\| ≥ 0.40 | −0.04 | −0.14 | −0.94 | −1.31 |
| score ≥ .25 + ML band | −0.05 | −0.14 | −1.03 | −1.40 |

**Every cell is negative.** The hourly ensemble had no edge at all.

### The trap I nearly fell into

Before the barrier test I ran a simpler diagnostic that said:

> at \|score\| 0.2–0.3 the hit rate is 57%, and at 0.4–0.6 the mean forward
> move is **+2.15 ATR**

That looks like a strong edge. It is not. It measures "was the direction
right 12 bars later", ignoring that a 2-ATR stop gets hit on the way there.
Once the stop and target compete, the gain disappears. **A directional hit
rate is not an edge.** I would have shipped a losing system on that number.

---

## 2. Ablation: which layer was destroying the edge

A clean trend signal *did* show positive EV on 6h bars (see §3). The full
ensemble did not. So I ablated, mean of BTC/ETH/SOL, 6h, stop 3 ATR / target
6 ATR:

| configuration | return | max DD | trades | win % | PF | expectancy | Sharpe |
|---|---|---|---|---|---|---|---|
| supertrend only, no ML | +1.13% | −4.63% | 44 | 32.1% | 0.92 | −0.138R | −0.27 |
| 7 trend strategies, no ML | +1.25% | −4.15% | 42 | 32.2% | 0.95 | −0.109R | −0.46 |
| all 14 strategies, no ML | +1.38% | −3.65% | 57 | 41.2% | 1.11 | +0.062R | +0.58 |
| all 14 + ML filter | −0.84% | −3.10% | 21 | 39.3% | 0.90 | −0.034R | −0.56 |
| 7 trend + ML filter | −0.91% | −2.85% | 23 | 31.1% | 0.87 | −0.062R | −0.61 |
| **7 trend, threshold 0.40** | **+4.39%** | **−3.64%** | **61** | **46.1%** | **1.33** | **+0.180R** | **+1.60** |

Conclusions:

1. **The ML meta-filter is actively harmful.** Its information coefficient was
   ≈ +0.006, i.e. noise. Worse, it is *anti*-predictive when confident:
   `|ml| > 0.50` → 46.1% hit rate and a **negative** mean move, while
   `|ml|` 0.05–0.50 → 52–55% and positive. An over-confident model on noisy
   bars is a contrarian indicator. It is shipped but **off by default**.
2. **Mean-reversion strategies hurt on crypto.** Per-strategy ICs on this
   data: `macd` +0.037 and `zscore_reversion` +0.016 were the best;
   `adx_trend` −0.035, `atr_breakout` −0.024, `ema_cross` −0.023 were the
   worst. Short-horizon crypto is not mean-reverting at these scales.
3. **Conviction filtering is the single biggest lever.** Weak signals are not
   merely unprofitable, they are *toxic*: `|score| < 0.20` had a 46.6% hit
   rate and a **negative** mean forward move. Requiring ≥ 0.40 more than
   doubled expectancy.

### Two bugs found while doing this

- **A weight-floor bug silently disabled the adaptive layer.** `min_weight`
  was an absolute floor of 0.15, but with 14 strategies uniform weight is
  1/14 = 0.071 — so the floor sat *above* uniform, every strategy got
  clipped to it, and renormalisation returned them all to equal weight.
  The "learning" was a no-op. Fixed by expressing the floor as a multiple of
  equal weight (`min_weight_rel = 0.25`).
- **Monte Carlo reported the tail backwards.** Drawdowns are negative, so the
  adverse tail is the 5th percentile, not the 95th. The original code reported
  the 5% *best* runs as the "95th percentile drawdown" and understated risk.

---

## 3. What survived: trend following on 6h bars

Barrier study, 6h bars, 90-bar horizon, EV in ATR units:

| signal | BTC | ETH | SOL |
|---|---|---|---|
| supertrend (tgt 3 / stp 2) | +0.08 | +0.27 | +0.22 |
| supertrend (tgt 3 / stp 3) | +0.07 | +0.32 | +0.29 |
| ADX>25 DI (tgt 3 / stp 3) | −0.00 | +0.34 | +0.10 |
| buy & hold (tgt 3 / stp 2) | +0.08 | +0.12 | −0.12 |

Positive and **consistent across all three assets and across adjacent
parameter cells** — which is what distinguishes a real effect from a mined
one. Note the win rates are only ~45%: this wins by payoff asymmetry, not by
being right often.

---

## 4. Walk-forward validation (out-of-sample)

4 consecutive time folds per market, identical parameters, no refitting:

| market | fold 1 | fold 2 | fold 3 | fold 4 | profitable |
|---|---|---|---|---|---|
| BTC-USD | +0.201R | +0.288R | +0.095R | +0.618R | **4/4** |
| ETH-USD | +0.433R | −0.018R | +0.083R | +0.154R | **3/4** |
| SOL-USD | +0.403R | +0.073R | +0.894R | −0.138R | **3/4** |

**10 of 12 folds profitable.** Portfolio: +4.90% total, 2.42% CAGR,
−2.54% max drawdown, 184 trades, 46.1% win rate, PF 1.35.

---

## 5. Honest risk picture (Monte Carlo, 2000 reshuffles of the real trades)

| market | median max DD | 95th-pct worst DD | worst of 2000 | P(hit −20% breaker) | P(profit) |
|---|---|---|---|---|---|
| BTC-USD | −3.57% | −7.35% | −13.16% | 0.0% | 83.0% |
| ETH-USD | −3.41% | −6.77% | −12.11% | 0.0% | 78.5% |
| SOL-USD | −3.25% | −6.51% | −10.38% | 0.0% | 86.5% |

5th-percentile final return over the 2-year window: **−2.5% to −3.7%**.
So roughly a 1-in-20 chance of ending the period slightly *down*. That is the
number to internalise: this is a modest, real edge, not a money printer.

---

## 6. Caveats I am not going to hide

- **2 years is a short sample** for a trend-following system. It contains one
  regime, not several.
- **I searched over thresholds.** The chosen 0.35–0.60 region is a plateau
  (all positive: +0.173, +0.180, +0.084, +0.122, +0.077), which is
  reassuring, but the true expectancy is very likely **lower** than measured.
- **Live fills will be worse** than the model. It assumes the stop fills at
  the stop level minus slippage; in a fast market you get gap-through.
- **No funding/borrow costs** are modelled for shorts, and no exchange
  outages, API downtime, or withdrawal limits.
- Crypto trades 24/7; the equity is not marked to a session close, so daily
  drawdown figures are approximations.

**Expect degradation from backtest to live.** Plan for it.
