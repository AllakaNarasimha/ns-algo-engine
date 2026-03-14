import logging
import datetime
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from algo.utils.app_config import AppConfig


@dataclass
class Position:
    """Represents a trading position."""
    position_type: Optional[str] = None
    entry_price: Optional[float] = None
    entry_datetime: Optional[datetime.datetime] = None
    trade_id: int = 0


class TradeManager:
    def __init__(self, config: AppConfig):
        self.config = config
        self.position = Position()
        self.pl_threshold = config.pl_percent  # Minimum percentage change to consider
        self.logger = logging.getLogger(__name__)
        self._start_time = self._parse_time(config.start_time)
        self._end_time = self._parse_time(config.end_time)

    def _parse_time(self, time_str: str) -> datetime.time:
        """Parse time string in HH:MM format to datetime.time object."""
        return datetime.datetime.strptime(time_str, '%H:%M').time()

    def process_signal(self, current_candle: Dict[str, Any], trade_signal: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        try:
            ct = current_candle['timestamp']
        except Exception:
            ct = None
        
        trade_data = None
        
        # End-of-session handling: close existing position and block further trading
        if ct and self._end_time and ct.time() >= self._end_time:
            if self.position.position_type is not None:
                self.logger.info("End time reached. Auto-closing open position.")
                trade_data = self._close_position(current_candle)
            return trade_data
        
        # Flag controlling whether we are permitted to open NEW positions
        allow_new_entries = True    
        if ct and (ct.hour == 15 and ct.minute == 0):
            allow_new_entries = False
        if ct and self._start_time and (ct.time() < self._start_time or ct.time() >= self._end_time):
            allow_new_entries = False
        
        if trade_signal is None:
            return trade_data
        
        # Check if this is an exit-only signal (stop loss, etc.)
        is_exit_only = trade_signal.get('action') in ['stop_exit', 'exit', 'eod_exit']
        
        # Check if this is an exit-only signal (stop loss, etc.)
        is_exit_only = trade_signal.get('action') in ['stop_exit', 'exit', 'eod_exit']
        
        if trade_signal['signal'] == 'buy':
            # Always allow closing an opposing position
            if self.position.position_type == 'short':
                trade_data = self._close_position(current_candle)
            # Only open a new long if entries are allowed AND not an exit-only signal
            if allow_new_entries and self.position.position_type != 'long' and not is_exit_only:
                self._open_position('long', current_candle)
        elif trade_signal['signal'] == 'sell':
            if self.position.position_type == 'long':
                trade_data = self._close_position(current_candle)
            # Only open a new short if entries are allowed AND not an exit-only signal
            if allow_new_entries and self.position.position_type != 'short' and not is_exit_only:
                self._open_position('short', current_candle)        
        
        return trade_data
    
    def _open_position(self, position_type: str, current_candle: Dict[str, Any]) -> None:
        self.position.position_type = position_type
        self.position.entry_price = current_candle['open']
        self.position.entry_datetime = current_candle['timestamp']
        self.logger.info(f"Opened {position_type.upper()} position at {self.position.entry_price} on {self.position.entry_datetime}")
    
    def _close_position(self, current_candle: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.position.position_type:
            return None
        price = current_candle['close']
        current_datetime = current_candle['timestamp']
        profit_loss = (price - self.position.entry_price) if self.position.position_type == 'long' else (self.position.entry_price - price)
        
        trade_data = {
            'trade_id': self.position.trade_id,
            'entry_datetime': self.position.entry_datetime, 
            'exit_datetime': current_datetime,
            'entry_price': self.position.entry_price,
            'exit_price': price,
            'position_type': self.position.position_type,
            'action': 'closed',
            'position_state': 'closed',
            'profit_loss': profit_loss,
        }
        self.logger.info(f"Closed {self.position.position_type.upper()} position: P&L={profit_loss:.2f}")
        
        self.position.trade_id += 1
        self.position.position_type = None
        self.position.entry_price = None
        self.position.entry_datetime = None
        return trade_data    
        
                