from datetime import timedelta
import re

class CandleAggregator:
    """
    Handles candle construction logic based on tick data.
    Aggregates price ticks into OHLC candles based on specified granularity.
    """
    def __init__(self, granularity='1m'):
        self.granularity = granularity
        match = re.match(r'^(\d+)(MS|S|m|h|d|w|M)$', self.granularity)
        if not match:
            raise ValueError("granularity must be in the format <number><unit> where unit is one of MS, S, m, h, d, w, M")
        self.num = int(match.group(1))
        self.unit = match.group(2)
        self.current_bucket = None
        self.ohlc = None  # {'time', 'open', 'high', 'low', 'close'}

    def get_bucket_start(self, dt):
        if self.unit == 'MS':
            # MS is millisecond, 1ms = 1000 microseconds
            ms = self.num * 1000
            floored_us = (dt.microsecond // ms) * ms
            return dt.replace(microsecond=floored_us)
        elif self.unit == 'S':
            floored_second = (dt.second // self.num) * self.num
            return dt.replace(second=floored_second, microsecond=0)
        elif self.unit == 'm':
            floored_minute = (dt.minute // self.num) * self.num
            return dt.replace(minute=floored_minute, second=0, microsecond=0)
        elif self.unit == 'h':
            floored_hour = (dt.hour // self.num) * self.num
            return dt.replace(hour=floored_hour, minute=0, second=0, microsecond=0)
        elif self.unit == 'd':
            floored_day = ((dt.day - 1) // self.num) * self.num + 1
            return dt.replace(day=floored_day, hour=0, minute=0, second=0, microsecond=0)
        elif self.unit == 'w':
            if self.num != 1:
                raise ValueError("Only 1w supported for weeks")
            # Start of week, Monday
            start_of_week = dt - timedelta(days=dt.weekday())
            return start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
        elif self.unit == 'M':
            if self.num != 1:
                raise ValueError("Only 1M supported for months")
            return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            raise ValueError(f"Unsupported unit: {self.unit}")

    def update(self, candle, dt):
        """
        Update with a new price tick at given datetime.
        Returns finalized candle if bucket changes, else None.
        """
        # Determine bucket timestamp
        bucket_ts = self.get_bucket_start(dt)

        if self.current_bucket is None or bucket_ts != self.current_bucket:
            # Finalize previous candle if exists
            finalized = self.ohlc.copy() if self.ohlc else None
            # Start new candle
            self.ohlc = {
                'timestamp': bucket_ts,
                'open': candle['open'] if 'open' in candle and candle['open'] is not None else candle['ltp'],
                'high': candle['high'] if 'high' in candle and candle['high'] is not None else candle['ltp'],
                'low': candle['low'] if 'low' in candle and candle['low'] is not None else candle['ltp'],
                'close': candle['close'] if 'close' in candle and candle['close'] is not None else candle['ltp']
            }
            self.current_bucket = bucket_ts
            return finalized
        else:
            # Update current candle
            self.ohlc['high'] = max(self.ohlc['high'], candle['high'] if 'high' in candle and candle['high'] is not None else candle['ltp'])
            self.ohlc['low'] = min(self.ohlc['low'], candle['low'] if 'low' in candle and candle['low'] is not None else candle['ltp'])
            self.ohlc['close'] = candle['close'] if 'close' in candle and candle['close'] is not None else candle['ltp']
            return None

    def finalize_current(self):
        """Manually finalize and return the current candle."""
        if self.ohlc:
            finalized = self.ohlc.copy()
            self.ohlc = None
            self.current_bucket = None
            return finalized
        return None

    def reset(self):
        """Reset the aggregator state."""
        self.current_bucket = None
        self.ohlc = None