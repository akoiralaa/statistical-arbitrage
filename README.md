# Statistical Arbitrage — Pairs Trading System

A backtesting framework for pairs trading in cryptocurrency markets, implementing statistical arbitrage via cointegration analysis and mean-reversion signals.

---

## Methodology

### 1. Pair Selection via Cointegration

1. **Hedge ratio estimation** — OLS regression between two asset price series to find the linear combination that minimises spread variance:

   ```
   spread = price_A − β × price_B
   ```

2. **Stationarity testing** — Augmented Dickey-Fuller (ADF) test on the resulting spread. A p-value below the configured threshold (default 0.05) indicates the spread is mean-reverting and the pair is cointegrated.

3. **Batch screening** — `pair_optimizer.py` runs a grid search over a configurable universe of pairs, logging cointegration p-values and selecting candidates above the significance threshold.

### 2. Signal Generation

Rolling Z-score computed over a 252-day lookback window:

```
z = (spread − μ_spread) / σ_spread
```

| Condition | Action |
|-----------|--------|
| z < −2.0 (no open position) | Long spread (buy A, short B) |
| z > +2.0 (no open position) | Short spread (sell A, buy B) |
| \|z\| < 0.5 (open position) | Close position |

### 3. Position Sizing & Risk Controls

- **Risk per trade:** 2% of current capital
- **Max position size:** 10% of capital per leg
- Actual size is the more conservative of the two constraints
- **Stop loss:** 5% from entry price
- **Maximum drawdown:** trading halts if portfolio drawdown exceeds 15%
- **Kelly Criterion** used as a secondary reference (25% fractional Kelly)
- Transaction costs included: 0.1% commission + 0.1% slippage per side

### 4. Performance Metrics

Sharpe Ratio, Calmar Ratio, Profit Factor, Max Drawdown, Annualized Return, Win Rate, and Consecutive Win/Loss streaks computed in `src/analyzer.py`.

---

## Pairs Tested

**Exchange:** Binance via CCXT
**Timeframe:** Daily (1d) candles
**Period:** 2023–2024
**Starting capital:** $10,000

| Pair | Trades | Total Return | Sharpe Ratio | Max Drawdown |
|------|--------|-------------|--------------|--------------|
| BTC/USDT – ETH/USDT | 0 | — | — | — |
| BTC/USDT – SOL/USDT | 1 | −39.7% | −0.67 | 39.7% |
| ETH/USDT – SOL/USDT | 2 | −17.3% | −1.09 | 17.3% |

### Observations

- **BTC/ETH generated zero signals.** During 2023–2024 the pair traded within an unusually tight spread, never breaching the ±2σ entry threshold. This suggests the threshold may be too wide relative to the pair's actual volatility regime, or that the cointegration relationship was structurally weak in this period.

- **Negative returns on BTC/SOL and ETH/SOL.** The 2023–2024 crypto bull market produced strongly trending price action, which systematically breaks the mean-reversion assumption underlying the strategy. Pairs that appeared cointegrated on longer historical windows diverged sharply during this regime.

- **ADF p-value threshold.** The current configuration uses p < 0.15 to maximise the number of viable pairs. This risks including spurious cointegration — tightening to p < 0.05 and adding an Engle-Granger two-step confirmation would improve pair quality.

- **Next steps:** expand the universe to 20+ pairs across multiple exchanges, add a rolling out-of-sample cointegration window to detect regime changes, and test on equity and futures markets where mean-reversion conditions are historically more stable.

---

## Project Structure

```
statistical-arbitrage/
├── main.py                      # Entry point — orchestrates full workflow
├── cointegration.py             # Standalone cointegration screening
├── pair_optimizer.py            # Grid-search over pairs and parameters
├── config.yaml                  # Strategy configuration
├── pair_optimization_results.csv
├── src/
│   ├── data_fetcher.py          # CCXT/Binance market data interface
│   ├── cointegration.py         # CointegrationTester (ADF + OLS)
│   ├── signals.py               # Z-score signal generation
│   ├── backtester.py            # Backtesting engine
│   ├── risk_manager.py          # Position sizing and drawdown controls
│   ├── analyzer.py              # Performance metrics
│   ├── ccxt_connector.py        # Exchange connector
│   └── utils.py                 # Shared helpers
├── scripts/                     # Data preparation utilities (development)
│   ├── fix_cvs.py
│   ├── convert_all_csvs.py
│   └── convert_csv.py
└── data/
    └── historical/              # OHLCV CSVs — gitignored, loaded at runtime
```

---

## Setup

```bash
pip install ccxt pandas numpy statsmodels scipy pyyaml
python main.py
```

Configure exchange, asset universe, entry/exit thresholds, and risk parameters in `config.yaml`.

### Key configuration options

```yaml
assets: [BTC/USDT, ETH/USDT, SOL/USDT]
exchange: binance
timeframe: 1d

signal:
  entry_zscore: 2.0
  exit_zscore: 0.5
  lookback_window: 252

risk:
  max_position_pct: 0.10
  risk_per_trade_pct: 0.02
  stop_loss_pct: 0.05
  max_drawdown_pct: 0.15
```

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `ccxt` | Exchange connectivity (Binance, etc.) |
| `pandas`, `numpy` | Data manipulation |
| `statsmodels` | ADF test, OLS regression |
| `scipy` | Statistical utilities |
| `pyyaml` | Configuration loading |
