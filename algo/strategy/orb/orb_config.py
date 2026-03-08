from __future__ import annotations
import datetime
import re
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


def _validate_granularity(val: str) -> str:
    if not re.match(r'^\d+(MS|S|m|h|d|w|M)$', val):
        raise ValueError("candle_granularity must be in the format <number><unit> where unit is one of MS, S, m, h, d, w, M")
    return val


@dataclass
class OrbConfig:
    range_minutes: int = 15
    max_trades_per_day: int = 3
    candle_granularity: str = field(default='1m', metadata={'validate': _validate_granularity})
    stop_loss_pct: Optional[float] = None
    trailing_stop_pct: Optional[float] = None
    target_pct: Optional[float] = None
    require_boundary_touch: bool = True
    orb_start_time: datetime.time = field(init=False)
    orb_end_time: datetime.time = field(init=False)

    def __post_init__(self):
        # validate granularity
        self.candle_granularity = _validate_granularity(self.candle_granularity)
        self.update_orb_times()

    def update_orb_times(self):
        """Update orb_start_time and orb_end_time based on current range_minutes."""
        self.orb_start_time = datetime.time(9, 15)
        start_datetime = datetime.datetime.combine(datetime.date.today(), self.orb_start_time)
        self.orb_end_time = (start_datetime + datetime.timedelta(minutes=self.range_minutes)).time()

    @classmethod
    def from_app_config(cls, app_config: Any) -> "OrbConfig":
        """Create OrbConfig from AppConfig's strategy_params."""
        params: Dict[str, Any] = {k: v for k, v in app_config.strategy_params.items() if k != 'additional_indicators'}
        return cls(**params)