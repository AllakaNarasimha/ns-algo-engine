from datetime import timedelta
import re
import pandas as pd
from typing import Optional, Dict, Any


class CandleAggregator:
    """
    Handles candle construction logic based on tick data.
    Aggregates price ticks into OHLC candles based on specified granularity.
    """
    def __init__(self, granularity: str = '1m') -> None:
        self.granularity = granularity
        match = re.match(r'^(\d+)(MS|S|m|h|d|w|M)$', self.granularity)
        if not match:
            raise ValueError("granularity must be in the format <number><unit> where unit is one of MS, S, m, h, d, w, M")
        self.num = int(match.group(1))
        self.unit = match.group(2)
        self.current_bucket: Optional[pd.Timestamp] = None
        self.ohlc: Optional[Dict[str, Any]] = None  # {'time', 'open', 'high', 'low', 'close'}

    def get_bucket_start(self, dt: pd.Timestamp) -> pd.Timestamp:
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

    def update(self, candle: Dict[str, Any], dt: pd.Timestamp) -> Optional[Dict[str, Any]]:
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
            ltp = candle.get('ltp') or candle.get('close')
            self.ohlc = {
                'timestamp': bucket_ts,
                'open': candle.get('open', ltp),
                'high': candle.get('high', ltp),
                'low': candle.get('low', ltp),
                'close': candle.get('close', ltp)
            }
            self.current_bucket = bucket_ts
            return finalized
        else:
            # Update current candle
            ltp = candle.get('ltp') or candle.get('close')
            if self.ohlc:
                self.ohlc['high'] = max(self.ohlc['high'], candle.get('high', ltp))
                self.ohlc['low'] = min(self.ohlc['low'], candle.get('low', ltp))
                self.ohlc['close'] = candle.get('close', ltp)
            return None

    def finalize_current(self) -> Optional[Dict[str, Any]]:
        """Manually finalize and return the current candle."""
        if self.ohlc:
            finalized = self.ohlc.copy()
            self.ohlc = None
            self.current_bucket = None
            return finalized
        return None

    def reset(self) -> None:
        """Reset the aggregator state."""
        self.current_bucket = None
        self.ohlc = None


class CandleManager:
    """
    Manages the candles DataFrame and indicator injection.
    """
    def __init__(self) -> None:
        self.candles_df = pd.DataFrame(columns=['timestamp'])
        self.candles_df.set_index('timestamp', inplace=True)

    def add_candle(self, candle: Dict[str, Any]) -> None:
        """Add a finalized candle to the DataFrame."""
        new_candle_df = pd.DataFrame([candle]).set_index('timestamp')
        self.candles_df = pd.concat([self.candles_df, new_candle_df])

    def inject_indicators(self, candle_dt: pd.Timestamp, indicators: Dict[str, Any], 
                         data_state_manager: Any) -> None:
        """Inject indicators into the candles DataFrame."""
        try:
            if candle_dt in self.candles_df.iloc[:data_state_manager.current_index].index:
                indicator_columns = ['orb_time', 'pivot_time', 'pivot_high', 'pivot_low', 
                                   'pivot_direction', 'range_high', 'range_low']
                for k in indicator_columns:
                    if k in indicators:
                        self.candles_df.at[candle_dt, k] = indicators[k]
                
                # Forward fill certain indicators
                ffill_columns = ['orb_time', 'pivot_high', 'pivot_low', 'range_high', 'range_low']
                for k in ffill_columns:
                    try:
                        self.candles_df[k] = self.candles_df[k].ffill()
                    except Exception:
                        pass
        except Exception:
            pass

    def reset(self) -> None:
        """Reset the candles DataFrame."""
        self.candles_df = pd.DataFrame(columns=['timestamp'])
        self.candles_df.set_index('timestamp', inplace=True)
