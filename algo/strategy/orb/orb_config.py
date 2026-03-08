import datetime
import re

class OrbConfig:
    def __init__(self, range_minutes=15,
                max_trades_per_day=3,
                candle_granularity: str = '1m',
                stop_loss_pct=None,
                trailing_stop_pct=None,
                target_pct=None,
                require_boundary_touch: bool = True):
        self.candle_granularity = candle_granularity
        if not re.match(r'^\d+(MS|S|m|h|d|w|M)$', self.candle_granularity):
            raise ValueError("candle_granularity must be in the format <number><unit> where unit is one of MS, S, m, h, d, w, M")
        
        self.range_minutes = range_minutes
        self.max_trades_per_day = max_trades_per_day
        self.stop_loss_pct = stop_loss_pct  # stored in true percent units
        self.trailing_stop_pct = trailing_stop_pct
        self.target_pct = target_pct 
        self.require_boundary_touch = require_boundary_touch
        self.update_orb_times()

    def update_orb_times(self):
        """Update orb_start_time and orb_end_time based on current range_minutes."""
        self.orb_start_time = datetime.time(9, 15)
        start_datetime = datetime.datetime.combine(datetime.date.today(), self.orb_start_time)
        self.orb_end_time = (start_datetime + datetime.timedelta(minutes=self.range_minutes)).time()

    @classmethod
    def from_app_config(cls, app_config):
        """Create OrbConfig from AppConfig's strategy_params."""
        params = {k: v for k, v in app_config.strategy_params.items() if k != 'additional_indicators'}
        return cls(**params)