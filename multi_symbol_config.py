"""
Configuration for running multiple symbols in parallel

Add or remove symbols from the SYMBOLS list below.
Each symbol needs its corresponding database file in the data/ directory.
"""

# List of symbols to backtest in parallel
SYMBOLS = [
    {
        'symbol': 'BAJAJFINSV',
        'instrument_type': 'EQ',
        'db_file': '06jan26_BAJAJFINSV-EQ.db'
    },
    # Uncomment and add more symbols as needed:
    # {
    #     'symbol': 'RELIANCE',
    #     'instrument_type': 'EQ',
    #     'db_file': '06jan26_RELIANCE-EQ.db'
    # },
    # {
    #     'symbol': 'TCS',
    #     'instrument_type': 'EQ',
    #     'db_file': '06jan26_TCS-EQ.db'
    # },
    # {
    #     'symbol': 'INFY',
    #     'instrument_type': 'EQ',
    #     'db_file': '06jan26_INFY-EQ.db'
    # },
    # {
    #     'symbol': 'HDFC',
    #     'instrument_type': 'EQ',
    #     'db_file': '06jan26_HDFC-EQ.db'
    # },
]

# Maximum number of parallel threads
# Adjust based on your system resources (CPU cores, memory)
# Recommended: 2-8 threads for most systems
MAX_WORKERS = 4
