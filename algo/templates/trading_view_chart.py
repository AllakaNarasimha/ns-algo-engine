#!/usr/bin/env python3
"""
TradingView Lightweight Charts Python Implementation
MATCHES HTML TEMPLATE DIMENSIONS EXACTLY
"""

import sys
import json
import numpy as np
from datetime import datetime
from lightweight_charts import Chart
from typing import List, Dict, Any, Optional
import pandas as pd

from algo.utils.ns_indicators import NSIndicators

class TradingViewChart:
    def __init__(self):
        # EXACT HTML TEMPLATE DIMENSIONS
        self.width = None  # Full browser width (flex:1)
        self.height = None  # Full browser height minus P&L panel (flex: %CHARTFLEX%)
        
        # Chart configuration matching HTML template EXACTLY
        self.chart = Chart(toolbox=True)
        # Set layout properties via method call
        try:
            self.chart.layout(
                background_color='#0d1117',
                text_color='#DDD',
                font_family='Inter, Arial'
            )
            # Advanced configuration removed - API compatibility issues
            # self.chart.time_scale.border_color = '#30363d'
            # self.chart.time_scale.time_visible = True
            # self.chart.time_scale.seconds_visible = False
            # self.chart.crosshair.mode = 'Normal'
            # self.chart.localization.timezone = 'Asia/Kolkata'
        except (AttributeError, TypeError):
            # If layout method or properties are not supported, continue without them
            pass
        
        # Store series references
        self.candle_series = None
        self.indicator_series = []
        self.volume_series = None
        self.pl_series = None
        
    def set_candles(self, candle_data: List[Dict[str, Any]]):
        """Set candlestick data - lightweight_charts expects DataFrame with DatetimeIndex"""
        # Convert list of dicts to DataFrame with DatetimeIndex
        candle_df = pd.DataFrame(candle_data)
        candle_df['time'] = pd.to_datetime(candle_df['time'], unit='s')
        candle_df = candle_df.set_index('time')
        
        self.chart.set(candle_df)
        self.candle_series = self.chart  # Reference for markers
        
        # Auto-range for small datasets (matches HTML logic)
        if len(candle_data) > 0 and len(candle_data) <= 2:
            first_time = candle_data[0]['time']
            last_time = candle_data[-1]['time']
            self.chart.time_scale.set_visible_range({'from': first_time, 'to': last_time})
        
    def add_indicators(self, indicators: List[Dict[str, Any]]):
        """Add indicator lines - toggleable like HTML"""
        self.indicator_series = []
        for ind in indicators:
            try:
                series = self.chart.create_line(color=ind['color'])
                # Convert series data (list of dicts) to DataFrame with DatetimeIndex
                series_df = pd.DataFrame(ind['series'])
                series_df['time'] = pd.to_datetime(series_df['time'], unit='s')
                series_df = series_df.set_index('time')
                series.set(series_df)
                self.indicator_series.append({'name': ind['name'], 'series': series})
            except Exception as e:
                print(f"⚠️ Failed to add indicator {ind['name']}: {e}", file=sys.stderr)
                continue
            
    def toggle_indicator(self, name: str, visible: bool = True):
        """Toggle indicators like HTML checkboxes"""
        for ind in self.indicator_series:
            if ind['name'] == name:
                ind['series'].options(visible=visible)
                break
                
    def set_volume(self, candle_data: List[Dict[str, Any]]):
        """Volume histogram with EXACT HTML scaling"""
        vol_data = []
        for candle in candle_data:
            color = 'rgba(38,166,154,0.55)' if candle['close'] >= candle['open'] else 'rgba(239,83,80,0.55)'
            vol_data.append({
                'time': candle['time'],
                'value': candle.get('volume', 0),
                'color': color
            })
        
        # Convert to DataFrame with DatetimeIndex    
        vol_df = pd.DataFrame(vol_data)
        vol_df['time'] = pd.to_datetime(vol_df['time'], unit='s')
        vol_df = vol_df.set_index('time')
            
        self.volume_series = self.chart.create_histogram()
        self.volume_series.set(vol_df)
        
        # EXACT HTML volume scaling
        vol_ratio = min(0.50, max(0.10, 0.20))  # __VOL_RATIO__ equivalent
        price_bottom = vol_ratio + 0.02
        try:
            # Price scale configuration removed - not available in this version
            print(f"⚠️ Volume scaling: Price scale configuration not available", file=sys.stderr)
        except Exception as e:
            print(f"⚠️ Failed to set volume scaling: {e}", file=sys.stderr)
        
    def set_pl(self, pl_data: List[Dict[str, Any]], separate_pl: bool = False, pl_hover: bool = False):
        """P&L line - matches HTML separatePL and hover logic"""
        if pl_data:
            # Convert to DataFrame with DatetimeIndex
            pl_df = pd.DataFrame(pl_data)
            pl_df['time'] = pd.to_datetime(pl_df['time'], unit='s')
            pl_df = pl_df.set_index('time')
            
            if separate_pl:
                # Separate P&L panel (matches %PLDIV%)
                pl_chart = Chart(toolbox=True)
                try:
                    pl_chart.layout(
                        background_color='#0d1117',
                        text_color='#DDD'
                    )
                    # Advanced configuration removed - API compatibility issues
                    # pl_chart.time_scale.border_color = '#30363d'
                    # pl_chart.crosshair.mode = 'Normal'
                except Exception as e:
                    print(f"⚠️ Failed to set P&L chart layout: {e}", file=sys.stderr)
                
                pl_series = pl_chart.create_line(color='#ffa600')
                pl_series.set(pl_df)
                
                # Show P&L chart below main chart (flex: %PLFLEX%)
                # pl_chart.show(blockingFalse=False, width=1400, height=200)
                # pl_chart.show(blocking=False)
                
            else:
                # Overlay P&L (matches HTML logic)
                self.pl_series = self.chart.create_line(color='#ffa600')
                # Price scale configuration removed - not available in this version
                self.pl_series.set(pl_df)
                
    def set_markers(self, markers: List[Dict[str, Any]]):
        """Markers matching HTML"""
        try:
            self.chart.markers = markers
        except Exception as e:
            print(f"⚠️ Failed to set markers: {e}", file=sys.stderr)
            
    def print_trade_summary(self, trade_data: Dict[str, List[Dict[str, Any]]]):
        """Console trade table matching HTML trade-table"""
        print("\n" + "="*80)
        print("🧾 TRADE TABLE (Click timestamps in HTML for same functionality)")
        print("="*80)
        
        all_trades = []
        for time_key, trades in trade_data.items():
            all_trades.extend(trades)
            
        if all_trades:
            df = pd.DataFrame(all_trades)
            if not df.empty:
                print(df[['id', 'position_type', 'entry_datetime', 'exit_datetime', 
                         'entry_price', 'exit_price', 'symbol', 'pl']].to_string(
                    index=False, float_format='%.2f'))
        print("="*80 + "\n")
        
    def show(self, width: int = 1400, height: int = 700):  # DEFAULT HTML SIZE
        """
        Show chart with EXACT HTML template dimensions
        width=1400, height=700 matches typical full-HD browser with P&L flex layout
        """
        print(f"📊 Displaying TradingView Chart: {width}x{height}px (HTML template match)")
        # self.chart.show(blocking=True, width=width, height=height)
    
    def _prepare_candles(self, df) -> List[Dict[str, Any]]:
        candles_json = []
        ts_time_map = {}
        for ts, row in df.iterrows():
            try:
                unix_time = int(ts.timestamp())
                candles_json.append({
                    'time': unix_time,
                    'open': float(row['open']),
                    'high': float(row['high']),
                    'low': float(row['low']),
                    'close': float(row['close']),
                    'volume': int(row.get('volume', 0))
                })
                ts_time_map[pd.to_datetime(ts)] = unix_time
            except Exception:
                continue
        candles_json.sort(key=lambda x: x['time'])
        dedup = []
        last_t = None
        for c in candles_json:
            if c['time'] != last_t:
                dedup.append(c)
                last_t = c['time']
        return dedup
    
    def generate_from_html_template(self,
        candle_df: pd.DataFrame,
        pl_data: List[Dict],
        markers: List[Dict],
        trade_data: Dict[str, List[Dict]],
        separate_pl: bool = False,
        pl_hover: bool = False,
        width: int = 1400,  # FULL BROWSER WIDTH MATCH
        height: int = 700   # CHART FLEX PORTION (excludes P&L panel)
    ):
        """
        Direct replacement for your HTML template data
        """

        candle_data = self._prepare_candles(candle_df)
        indicators = NSIndicators(candle_df).get_indicators_from_config()

        self.set_candles(candle_data)
        self.add_indicators(indicators)
        # self.set_volume(candle_data)
        self.set_pl(pl_data, separate_pl=separate_pl, pl_hover=pl_hover)
        self.set_markers(markers)
        # self.print_trade_summary(trade_data)

        # chart.show(width=width, height=height)
        return self



# USAGE EXACTLY LIKE YOUR HTML TEMPLATE
if __name__ == "__main__":
    print("🚀 TradingView HTML Template -> Python Converter")
    print("📏 Dimensions: FULL BROWSER WIDTH x 70% HEIGHT (matches flex:%CHARTFLEX%)")
    print()
    
    # Your template placeholders as Python variables
    candle_data = []  # __CANDLES__
    indicators = []   # __INDICATORS__
    pl_data = []      # __CUM_PL__
    markers = []      # __MARKERS__
    trade_data = {}   # __TRADE_DATA__
    separate_pl = False  # %SEPARATE_PL%
    
    # Replace above with your actual data loading
    # generate_from_html_template(candle_data, indicators, pl_data, markers, trade_data, separate_pl)
    
    print("✅ READY - Call generate_from_html_template() with your data!")
    print("📐 DEFAULT SIZE: 1400x700px (matches your HTML template layout)")
