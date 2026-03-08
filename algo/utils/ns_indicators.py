import pandas as pd
import os
from typing import List, Dict, Any, Optional
from .app_config import AppConfig

try:
    import talib
    _HAS_TALIB = True
except Exception:
    talib = None
    _HAS_TALIB = False

class NSIndicators:
    def __init__(self, df):
        self.df = df
        # Load AppConfig once and store it (default file config.xml)
        self.config = AppConfig.from_xml()

    def update_emas(self, df, emas = []):
        for ema in emas:
            ema_col = f'ema{ema}'
            if ema_col not in df.columns or df[ema_col].isna().all():
                if _HAS_TALIB:
                    df[ema_col] = talib.EMA(df['close'].astype(float), timeperiod=ema)
                else:
                    df[ema_col] = df['close'].rolling(ema, min_periods=1).mean()  
        return df        
    
    def generate_indicator_series(self, df, ema_col, candles_json):
        return [
            {'time': candles_json[i]['time'], 'value': float(row[ema_col])}
            for i, (_, row) in enumerate(df.iterrows()) if not pd.isna(row[ema_col])
        ]
    
    def get_indicator_series(self, indicators: List[Dict[str, Any]] = []) -> List[Dict[str, Any]]:
        indicator_series = []
        ema_values = [ind['properties']['value'] for ind in indicators if ind.get('indicator') == 'ema']

        self.df = self.update_emas(self.df, ema_values)
        # Create candles_json with 'time' key for series generation
        candles_json = [{'time': int(ts.timestamp())} for ts in self.df.index]
        
        for ind in indicators:
            if ind['indicator'] == 'ema':
                ema = ind['properties']['value']
                color = ind['properties'].get('color', '#FF0000')  # Default color if not provided
                ema_col = f'ema{ema}'
                series = self.generate_indicator_series(self.df, ema_col, candles_json)
                indicator_series.append({
                    'type': 'line',
                    'id': ema_col,
                    'name': ema_col,
                    'color': color,
                    'lineWidth': 1,
                    'series': series
                })
        return indicator_series
    
    def get_indicators_from_config(self) -> List[Dict[str, Any]]:
        """Load and return indicators from config.xml"""
        chart_indicators = self.config.load_chart_indicators()
        
        # Convert config format to indicator format for get_indicator_series
        indicators = []
        for ind in chart_indicators:
            if ind['name'] == 'ema' and ind['visible']:
                indicators.append({
                    'indicator': 'ema',
                    'properties': {
                        'value': ind['value'],
                        'color': ind['color'],
                        'run_on_candle': ind['run_on_candle']
                    }
                })
        
        return self.get_indicator_series(indicators)
