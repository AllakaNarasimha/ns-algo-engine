import datetime
import os
from typing import Optional, Dict, Any

from .orb_config import OrbConfig
from .orb_signal import ORBSignal
from .orb_utils import CandleAggregator, CandleManager
from .orb_trade_manager import ORBTradeManager
from algo.utils.app_config import AppConfig
from algo.engine.data_state_manager import DataStateManager
import logging
import pandas as pd

logging.basicConfig(filename='trading.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ORBStrategy:
    def __init__(self, app_config: AppConfig, data_state_manager: DataStateManager) -> None:
        self.app_config: AppConfig = app_config
        self.config = OrbConfig.from_app_config(app_config)
        self.data_state_manager = data_state_manager
        
        # Logging
        self.logger = logging.getLogger(__name__)
        self._end_time = self._parse_time(app_config.end_time)

        # Components
        self.candle_manager = CandleManager()
        self.candle_aggregator = CandleAggregator(self.config.candle_granularity)
        
        # Initialize signal and trade components later when first candle is available
        self.orb_signal = None
        self.orb_trade_manager = None
        
        # Daily control
        self.current_trade_day: Optional[datetime.date] = None

    def _parse_time(self, time_str: str) -> datetime.time:
        """Parse time string in HH:MM format to datetime.time object."""
        return datetime.datetime.strptime(time_str, '%H:%M').time()
    
    def reset(self) -> None:
        """Reset daily state."""
        self.orb_trade_manager.reset()
        self.candle_aggregator.reset()
        self.candle_manager.reset()
        self.current_trade_day = None

    def update(self, candle: Dict[str, Any], current_datetime: pd.Timestamp) -> Optional[Dict[str, Any]]:
        # Detect day change
        trade_day = current_datetime.date()
        if self.current_trade_day is None:
            self.current_trade_day = trade_day
        elif trade_day != self.current_trade_day:
            self.logger.info(f"New trading day detected: {trade_day}. Resetting ORB state.")
            self.reset()
            self.current_trade_day = trade_day
        
        # Aggregate ticks into candles
        finalized_candle = self.candle_aggregator.update(candle, current_datetime)
        if finalized_candle:
            self.candle_manager.add_candle(finalized_candle)
            
            # Initialize signal and trade components on first candle
            if self.orb_signal is None:
                self.orb_signal = ORBSignal(self.candle_manager.candles_df, self.config)
                self.orb_trade_manager = ORBTradeManager(self.config, self._end_time, self.orb_signal)
            else:
                # Update signal component with latest DataFrame
                self.orb_signal.df = self.candle_manager.candles_df
            
            return self._process_candle(finalized_candle)
        return None    

    def _process_candle(self, candle: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a finalized candle through pivots and trade manager."""   
        signal = self.orb_trade_manager.update_candle(candle)  
        
        self._process_candle_signals(candle)

        return signal

    def _process_candle_signals(self, candle: Dict[str, Any]) -> None:
        """Process trading signals for closed candle."""
        # Inject indicators
        try:
            candle_dt = candle['timestamp']
            indicators = self.get_indicators()
            self.candle_manager.inject_indicators(candle_dt, indicators, self.data_state_manager)
        except Exception:
            pass 
    
    def get_indicators(self) -> Dict[str, Any]:
        # Gather from components
        orb_signal = self.orb_signal
        orb_trade_manager = self.orb_trade_manager
       
        return {
            'orb_time' : orb_signal.orb_end_dt,
            'pivot_time': orb_signal.pivot_candle_time,
            'pivot_high': orb_signal.pivot_high,
            'pivot_low': orb_signal.pivot_low,
            'pivot_direction': orb_signal.pivot_direction if orb_signal.pivot_candle_time else None,
            'range_high': orb_signal.range_high,
            'range_low': orb_signal.range_low,            
            'entry_taken': orb_trade_manager.in_position,  
            'daily_trade_taken': orb_trade_manager.trades_taken_today > 0, 
            'trades_taken_today': orb_trade_manager.trades_taken_today,
            'max_trades_per_day': orb_trade_manager.max_trades_per_day,
            'in_position': orb_trade_manager.in_position,
            'stop_loss': orb_trade_manager.stop_loss,
            'stop_loss_pct': orb_trade_manager.stop_loss_pct,
            'trailing_stop_pct': orb_trade_manager.trailing_stop_pct,
            'entry_price': orb_trade_manager.entry_price,
            'trailing_anchor': orb_trade_manager.trailing_anchor,
            'target_pct': orb_trade_manager.target_pct,
            'target_price': orb_trade_manager.target_price,
            'target_locked': orb_trade_manager.target_locked,
        }

    @property
    def candles_df(self) -> pd.DataFrame:
        """Access to the candles DataFrame."""
        return self.candle_manager.candles_df
