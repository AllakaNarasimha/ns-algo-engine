import pandas as pd
import numpy as np
from datetime import datetime, time
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
import asyncio
from collections import deque

@dataclass
class TickData:
    symbol: str
    timestamp: pd.Timestamp
    ltp: float
    volume: float

class ORBCalculator:
    """Calculates Opening Range Breakout levels for each trading day."""
    
    def __init__(self, orb_minutes: int = 15):
        self.orb_minutes = orb_minutes
    
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Returns df with orb_high and orb_low columns."""
        df = df.copy()
        
        def _calc_orb(group):
            if len(group) < self.orb_minutes:
                group['orb_high'] = np.nan
                group['orb_low'] = np.nan
            else:
                group['orb_high'] = group['high'].iloc[:self.orb_minutes].max()
                group['orb_low'] = group['low'].iloc[:self.orb_minutes].min()
            return group
        
        return df.groupby('day').apply(_calc_orb).reset_index(drop=True)

class EMACrossover:
    """Calculates EMA crossover signals (bullish/bearish trend)."""
    
    def __init__(self, fast_period: int = 9, slow_period: int = 21):
        self.fast_period = fast_period
        self.slow_period = slow_period
    
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Returns df with ema_fast, ema_slow, and ema_bull columns."""
        df = df.copy()
        df['ema_fast'] = df['close'].ewm(span=self.fast_period, adjust=False).mean()
        df['ema_slow'] = df['close'].ewm(span=self.slow_period, adjust=False).mean()
        df['ema_bull'] = df['ema_fast'] > df['ema_slow']
        return df

class BreakoutDetector:
    """Detects initial ORB breakouts (without retest confirmation)."""
    
    def detect(self, df: pd.DataFrame) -> pd.DataFrame:
        """Returns df with long_breakout and short_breakout boolean columns."""
        df = df.copy()
        post_orb_mask = df.index >= df.groupby('day').cumcount() >= self.orb_minutes
        df['long_breakout'] = (
            (df['close'] > df['orb_high']) & 
            (df['close'].shift(1) <= df['orb_high']) & 
            post_orb_mask
        )
        df['short_breakout'] = (
            (df['close'] < df['orb_low']) & 
            (df['close'].shift(1) >= df['orb_low']) & 
            post_orb_mask
        )
        return df

class RetestConfirmer:
    """Confirms valid retests after breakouts."""
    
    def __init__(self, lookback_bars: int = 10):
        self.lookback_bars = lookback_bars
    
    def confirm_long(self, group: pd.DataFrame, breakout_idx: int) -> bool:
        """Check if long breakout had valid retest."""
        post_break = group.iloc[breakout_idx:breakout_idx + self.lookback_bars]
        orb_high = group['orb_high'].iloc[breakout_idx]
        orb_low = group['orb_low'].iloc[breakout_idx]
        return (post_break['low'] <= orb_high).any() and not (post_break['low'] < orb_low).any()
    
    def confirm_short(self, group: pd.DataFrame, breakout_idx: int) -> bool:
        """Check if short breakout had valid retest."""
        post_break = group.iloc[breakout_idx:breakout_idx + self.lookback_bars]
        orb_high = group['orb_high'].iloc[breakout_idx]
        orb_low = group['orb_low'].iloc[breakout_idx]
        return (post_break['high'] >= orb_low).any() and not (post_break['high'] > orb_high).any()
    
class StreamingDataManager:
    """Handles incoming websocket ticks, builds 1-min OHLCV incrementally."""
    
    def __init__(self, timeframe='1T'):
        self.bars: pd.DataFrame = pd.DataFrame()
        self.current_bar: Dict = None
        self.timeframe = pd.Timedelta(timeframe)
        self.last_timestamp = None
        
    def update(self, tick: TickData) -> pd.DataFrame:
        """Process single tick, return updated OHLCV DataFrame."""
        if self.last_timestamp != tick.timestamp.floor(self.timeframe):
            # Complete previous bar
            if self.current_bar:
                self._finalize_bar(tick.timestamp)
            
            # Start new bar
            self.current_bar = {
                'open': tick.ltp,
                'high': tick.ltp,
                'low': tick.ltp,
                'close': tick.ltp,
                'volume': tick.volume,
                'timestamp': tick.timestamp.floor(self.timeframe)
            }
            self.last_timestamp = tick.timestamp.floor(self.timeframe)
        else:
            # Update current bar
            self.current_bar['high'] = max(self.current_bar['high'], tick.ltp)
            self.current_bar['low'] = min(self.current_bar['low'], tick.ltp)
            self.current_bar['close'] = tick.ltp
            self.current_bar['volume'] += tick.volume
        
        if self.current_bar:
            bar_df = pd.DataFrame([self.current_bar])
            bar_df.set_index('timestamp', inplace=True)
            self.bars = pd.concat([self.bars, bar_df]).tail(500)  # Keep recent 500 bars
            
        return self.bars.copy()

class StreamingORBStrategy:
    """Real-time ORB + Retest + EMA with incremental state management."""
    
    def __init__(self, orb_minutes: int = 15, ema_fast: int = 9, ema_slow: 21):
        self.orb_calc = ORBCalculator(orb_minutes)
        self.ema = EMACrossover(ema_fast, ema_slow)
        self.data_mgr = StreamingDataManager()
        
        # Streaming state (updated incrementally)
        self.current_day = None
        self.orb_high = np.nan
        self.orb_low = np.nan
        self.orb_complete = False
        self.breakout_detected = {'long': False, 'short': False}
        self.retest_confirmed = {'long': False, 'short': False}
        self.last_signal = 0
        self.ema_cache = deque(maxlen=max(ema_slow * 2, 100))
        
    def update(self, tick: TickData) -> Dict[str, any]:
        """Process new tick, return current state and signal."""
        # 1. Update OHLCV bars
        bars = self.data_mgr.update(tick)
        if len(bars) < 2:
            return {'signal': 0, 'status': 'insufficient_data'}
        
        bars['day'] = bars.index.date
        
        # 2. Incremental ORB calculation
        self._update_orb(bars)
        
        # 3. Incremental EMA
        self._update_ema(bars)
        
        # 4. Check breakouts and retests
        signal = self._check_signals(bars.iloc[-1])
        
        return {
            'signal': signal,
            'price': tick.ltp,
            'orb_high': self.orb_high,
            'orb_low': self.orb_low,
            'ema_bull': self._is_ema_bullish(),
            'timestamp': tick.timestamp
        }
    
    def _update_orb(self, bars: pd.DataFrame):
        """Update ORB levels incrementally."""
        current_day = bars.index[-1].date()
        
        if current_day != self.current_day:
            self.current_day = current_day
            self.orb_high = np.nan
            self.orb_low = np.nan
            self.orb_complete = False
            self.breakout_detected = {'long': False, 'short': False}
            self.retest_confirmed = {'long': False, 'short': False}
        
        # Check if ORB window complete
        market_open = pd.Timestamp.combine(self.current_day, time(9, 15))
        orb_end = market_open + pd.Timedelta(minutes=self.orb_calc.orb_minutes)
        
        if (len(bars) >= self.orb_calc.orb_minutes and 
            bars.index[-1] >= orb_end and not self.orb_complete):
            orb_bars = bars[bars['day'] == self.current_day].head(self.orb_calc.orb_minutes)
            self.orb_high = orb_bars['high'].max()
            self.orb_low = orb_bars['low'].min()
            self.orb_complete = True
    
    def _update_ema(self, bars: pd.DataFrame):
        """Update EMA cache incrementally."""
        close_price = bars['close'].iloc[-1]
        self.ema_cache.append(close_price)
        
        ema_fast_df = pd.Series(list(self.ema_cache)).ewm(span=self.ema.fast_period).mean()
        ema_slow_df = pd.Series(list(self.ema_cache)).ewm(span=self.ema.slow_period).mean()
        self.ema_fast_current = ema_fast_df.iloc[-1]
        self.ema_slow_current = ema_slow_df.iloc[-1]
    
    def _is_ema_bullish(self) -> bool:
        return self.ema_fast_current > self.ema_slow_current
    
    def _check_signals(self, latest_bar: pd.Series) -> int:
        """Check for new signals based on latest bar."""
        if not self.orb_complete or pd.isna(self.orb_high):
            return 0
        
        current_price = latest_bar['close']
        
        # Detect breakout
        if not self.breakout_detected['long'] and current_price > self.orb_high:
            self.breakout_detected['long'] = True
        if not self.breakout_detected['short'] and current_price < self.orb_low:
            self.breakout_detected['short'] = True
        
        # Check retest confirmation (lookback last 5 bars)
        if self.breakout_detected['long'] and not self.retest_confirmed['long']:
            recent_low = min(latest_bar['low'], self.data_mgr.bars['low'].tail(5))
            if (recent_low <= self.orb_high and 
                recent_low > self.orb_low and 
                self._is_ema_bullish()):
                self.retest_confirmed['long'] = True
                return 1  # LONG signal
        
        if self.breakout_detected['short'] and not self.retest_confirmed['short']:
            recent_high = max(latest_bar['high'], self.data_mgr.bars['high'].tail(5))
            if (recent_high >= self.orb_low and 
                recent_high < self.orb_high and 
                not self._is_ema_bullish()):
                self.retest_confirmed['short'] = True
                return -1  # SHORT signal
        
        return 0

# Previous classes remain the same (ORBCalculator, EMACrossover, etc.)

# Websocket Handler Example
class ORBWebsocketHandler:
    """Connects to broker websocket, feeds ticks to strategy."""
    
    def __init__(self, strategy: StreamingORBStrategy, broker_api):
        self.strategy = strategy
        self.broker = broker_api  # Alice Blue/Zerodha/etc
    
    async def start_streaming(self):
        """Start websocket stream for NIFTY/BANKNIFTY."""
        await self.broker.subscribe(['NSE:NIFTY50', 'NSE:BANKNIFTY'])
        
        async for tick_data in self.broker.stream():
            result = self.strategy.update(tick_data)
            
            if result['signal'] != 0 and result['signal'] != self.strategy.last_signal:
                self.strategy.last_signal = result['signal']
                print(f"SIGNAL: {result['signal']} | Price: {result['price']:.2f} | "
                      f"ORB: [{result['orb_low']:.2f}, {result['orb_high']:.2f}]")
                
                # Place order via broker API
                # await self.broker.place_order(symbol='NIFTY', side=result['signal'], qty=50)

# Usage
async def main():
    strategy = StreamingORBStrategy(orb_minutes=15)
    handler = ORBWebsocketHandler(strategy, your_broker_api)
    await handler.start_streaming()

# Test with simulated ticks
def test_streaming():
    strategy = StreamingORBStrategy()
    
    # Simulate NSE market hours ticks
    base_price = 25000
    for i in range(400):  # 400 minutes trading day
        tick_time = pd.Timestamp('2026-02-15 09:15') + pd.Timedelta(minutes=i)
        tick_price = base_price + np.cumsum(np.random.randn(1)[0] * 10)
        
        tick = TickData(tick_time, tick_price, 1000, 'NIFTY')
        result = strategy.update(tick)
        
        if result['signal'] != 0:
            print(f"🚨 SIGNAL {result['signal']} at {tick_time}: {result}")

if __name__ == "__main__":
    test_streaming()
