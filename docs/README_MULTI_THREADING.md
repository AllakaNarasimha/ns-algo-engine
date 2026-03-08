# Multi-Symbol Backtesting Guide

## Packaging & Environment Setup

This repository is an installable Python package. Follow the steps below to set up your environment:

1. **Create a virtual environment** (optional but recommended):
   ```bash
   python3 -m venv .venv
   . .venv/bin/activate
   ```

2. **Install the package in editable mode** and dependencies:
   ```bash
   pip install --upgrade pip
   pip install -e .
   ```
   Local tarballs in `algo/libs` (e.g. `nslogger`) are installed automatically.

3. **Run the engine** via the console script:
   ```bash
   ns-algo
   ```
   or directly with `python main.py`.

4. **Add dependencies** by editing `requirements.txt` and rerunning the install.

## Overview

The backtesting engine now supports running multiple symbols in parallel using separate threads. This significantly reduces the total time required to backtest multiple symbols.

## Features

- ✅ Run multiple symbols simultaneously in separate threads
- ✅ Thread-safe execution with proper logging
- ✅ Configurable number of parallel workers
- ✅ Individual result tracking per symbol
- ✅ Comprehensive error handling and reporting
- ✅ Backward compatible with single-symbol mode

## Usage

### Multi-Symbol Mode (Default)

1. **Configure symbols** in `multi_symbol_config.py`:

   ```python
   SYMBOLS = [
       {
           'symbol': 'BAJAJFINSV',
           'instrument_type': 'EQ',
           'db_file': '06jan26_BAJAJFINSV-EQ.db'
       },
       {
           'symbol': 'RELIANCE',
           'instrument_type': 'EQ',
           'db_file': '06jan26_RELIANCE-EQ.db'
       },
   ]

   MAX_WORKERS = 4  # Number of parallel threads
   ```

2. **Run the backtest**:
   ```bash
   python main.py
   ```

### Single-Symbol Mode

To run just one symbol (uses config.xml):

```bash
python main.py --single
```

## Configuration Files

### multi_symbol_config.py

- **SYMBOLS**: List of dictionaries, each containing:
  - `symbol`: Stock symbol name
  - `instrument_type`: Usually 'EQ' for equities
  - `db_file`: Database file name in the `data/` directory
- **MAX_WORKERS**: Maximum number of parallel threads
  - Recommended: 2-8 threads depending on your system
  - More threads = more memory usage
  - Too many threads may not improve performance due to GIL

### config.xml

- Base configuration used by all symbols
- Symbol-specific settings (symbol, db_file) are overridden per thread
- Strategy parameters, time ranges, and chart settings are shared

## Output Files

Each symbol generates its own output files in the `algo/output/` directory:

- `{SYMBOL}_orb.csv` - Trading journal
- `{SYMBOL}_orb_prices_5_tv.html` - Interactive chart

## Logging

The application logs all activity with thread information:

```
2026-02-24 10:30:15 - Symbol-0 - INFO - Starting backtest for BAJAJFINSV
2026-02-24 10:30:16 - Symbol-1 - INFO - Starting backtest for RELIANCE
```

At the end, a summary shows the status of all symbols:

```
==================================================
BACKTEST SUMMARY
==================================================
BAJAJFINSV: SUCCESS
RELIANCE: SUCCESS
TCS: FAILED: Database file not found
==================================================
```

## Performance Tips

1. **Optimal Thread Count**:
   - Start with 4 workers
   - If you have 8+ CPU cores, try 6-8 workers
   - Monitor system resources during execution

2. **Memory Considerations**:
   - Each thread loads complete historical data
   - Monitor memory usage, especially with large datasets
   - Reduce MAX_WORKERS if system runs out of memory

3. **Database Files**:
   - Ensure all database files exist in the `data/` directory
   - Database reads are I/O bound, so threading helps significantly

## Troubleshooting

**Problem**: "No symbols configured in multi_symbol_config.py"

- **Solution**: Add at least one symbol to the SYMBOLS list

**Problem**: Thread fails with database error

- **Solution**: Verify the db_file exists in the data/ directory

**Problem**: System becomes unresponsive

- **Solution**: Reduce MAX_WORKERS value

**Problem**: Want to run single symbol

- **Solution**: Use `python main.py --single` or edit SYMBOLS to have only one entry

## Example

Running 5 symbols with 4 parallel workers:

```python
# multi_symbol_config.py
SYMBOLS = [
    {'symbol': 'BAJAJFINSV', 'instrument_type': 'EQ', 'db_file': '06jan26_BAJAJFINSV-EQ.db'},
    {'symbol': 'RELIANCE', 'instrument_type': 'EQ', 'db_file': '06jan26_RELIANCE-EQ.db'},
    {'symbol': 'TCS', 'instrument_type': 'EQ', 'db_file': '06jan26_TCS-EQ.db'},
    {'symbol': 'INFY', 'instrument_type': 'EQ', 'db_file': '06jan26_INFY-EQ.db'},
    {'symbol': 'HDFC', 'instrument_type': 'EQ', 'db_file': '06jan26_HDFC-EQ.db'},
]
MAX_WORKERS = 4
```

This will:

- Run 4 symbols simultaneously
- Process the 5th symbol when one of the first 4 completes
- Generate individual output files for each symbol
- Show completion status for all 5 symbols
