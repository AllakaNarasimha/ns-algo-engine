# Quick Start: Multi-Symbol Multi-Threaded Backtesting

## 🚀 Running Multiple Symbols

### Step 1: Configure Symbols

Edit `multi_symbol_config.py`:

```python
SYMBOLS = [
    {'symbol': 'BAJAJFINSV', 'instrument_type': 'EQ', 'db_file': '06jan26_BAJAJFINSV-EQ.db'},
    {'symbol': 'RELIANCE', 'instrument_type': 'EQ', 'db_file': '06jan26_RELIANCE-EQ.db'},
    {'symbol': 'TCS', 'instrument_type': 'EQ', 'db_file': '06jan26_TCS-EQ.db'},
]

MAX_WORKERS = 4  # Number of parallel threads
```

### Step 2: Run Backtest

```bash
# Multi-threaded mode (default)
python main.py

# Single symbol mode
python main.py --single
```

### Step 3: View Results

#### Individual Charts (updated during analysis)

- `algo/output/BAJAJFINSV_orb_prices_5_tv.html`
- `algo/output/RELIANCE_orb_prices_5_tv.html`
- `algo/output/TCS_orb_prices_5_tv.html`

#### Consolidated Chart (created after all complete)

- `algo/output/multi_symbol_chart.html` ⭐ **Open this!**

## 📊 What You Get

### During Analysis

- ✅ Each symbol runs in separate thread
- ✅ Individual progress logs per symbol
- ✅ Real-time chart updates (if enabled)
- ✅ Symbol-specific CSV trade journals

### After All Complete

- ✅ Summary report of all symbols
- ✅ **Multi-symbol consolidated chart**
- ✅ Statistics dashboard (win rate, P&L)
- ✅ Switch between symbols with dropdown

... (content truncated for brevity)
