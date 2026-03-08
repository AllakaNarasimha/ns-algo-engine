import os
import json
try:
    import talib
    _HAS_TALIB = True
except Exception:
    talib = None
    _HAS_TALIB = False
import pandas as pd


class TvChart:
    def __init__(self, symbol, cfg):
        self.symbol = symbol
        self.cfg = cfg
        self._update_counter = 0
        self._last_export_path = None
        self._opened = False
        self._placeholder_written = False
        self._pl_max_abs = 1.0
        self.indicators = []

    def _load_html_template(self, filename):
        # Template files are in the templates/ directory
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(base_dir, 'templates', filename)
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()

    def write_placeholder(self):
        output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'output')
        os.makedirs(output_dir, exist_ok=True)

        html_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), self.cfg.export_csv) 
               
        if self._placeholder_written:
            return html_path
        refresh = ''
        if getattr(self.cfg, 'tv_refresh_seconds', 0) > 0:
            refresh = f"<meta http-equiv='refresh' content='{self.cfg.tv_refresh_seconds}'>"
        placeholder_template = self._load_html_template('tv_placeholder.html')
        placeholder = placeholder_template.replace('%REFRESH%', refresh)
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(placeholder)
        self._placeholder_written = True
        if getattr(self.cfg, 'tv_auto_open', False) and not self._opened:
            import webbrowser
            try:
                webbrowser.open('file://' + os.path.abspath(html_path))
                self._opened = True
            except Exception:
                pass
        return html_path

    def maybe_export(self, df, completed_trades, force=False):
        self._update_counter += 1
        if len(df) <= 2 and not force:
            return self._export(df, completed_trades)
        if not force:
            if not getattr(self.cfg, 'tv_autoupdate', False):
                return None
            every = max(1, int(getattr(self.cfg, 'tv_update_every', 5)))
            if self._update_counter % every != 0:
                return None
        return self._export(df, completed_trades)
    
    def match_time_stamp(self, completed_trades):
        for trade in completed_trades:
            if trade.get('entry_datetime'):
                trade['entry_datetime'] = pd.to_datetime(trade['entry_datetime'].tz_localize(None), utc=True)
            if trade.get('exit_datetime'):
                trade['exit_datetime'] = pd.to_datetime(trade['exit_datetime'].tz_localize(None), utc=True)

    def export_final(self, df, completed_trades):
        return self._export(df, completed_trades, final=True)

    def _export(self, df, completed_trades, final=False):
        try:
            df = df.copy()
            if completed_trades:
                self.match_time_stamp(completed_trades)
            # Save chart data to output folder
            output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'output')
            os.makedirs(output_dir, exist_ok=True)
            chart_data_path = os.path.join(output_dir, 'chart_data.csv')
            df.to_csv(chart_data_path)#
            df.index = pd.to_datetime(df.index.tz_localize(None), utc=True)
            self._prepare_emas(df)
            if 'volume' not in df.columns:
                df['volume'] = 0
            if 'signal' in df.columns:
                df['signal'] = df['signal'].apply(lambda x: x.get('signal') if isinstance(x, dict) else x)
            candles_json = self._prepare_candles(df)
            
            # Add additional indicators
            if self.cfg.additional_indicators:
                for ind in self.cfg.additional_indicators:
                    name = ind['name']
                    params = ind['params']
                    if name == 'EMA':
                        if ind['type'] == 'multi_indicator':
                            for param in params:
                                period = param['period']
                                color = param['color']
                                ema_series = self._prepare_ema_series(df, f'ema{period}', candles_json)
                                self.indicators.append({'name': f'EMA{period}', 'color': color, 'lineWidth': 1, 'priceLineVisible': False, 'data': ema_series})
            else:
                ema5_series = self._prepare_ema_series(df, 'ema5', candles_json)
                ema20_series = self._prepare_ema_series(df, 'ema20', candles_json)
                self.indicators = [
                    { 'name': 'EMA5', 'color': 'yellow', 'lineWidth': 1, 'priceLineVisible': False, 'data': ema5_series},
                    { 'name': 'EMA20', 'color': 'cyan', 'lineWidth': 1, 'priceLineVisible': False, 'data': ema20_series}
                ]

            pivot_lines = self._prepare_pivot_lines(df, candles_json)
            markers = self._prepare_markers(df, completed_trades, candles_json)
            trade_data = self._prepare_trade_data(completed_trades, df, candles_json)
            cum_pl_series = self._prepare_cum_pl(completed_trades, df, candles_json)
            html_template = self._load_html_template('tv_chart_template.html')
            symbol = self.cfg.export_csv.split('_')[0]
            html_template = self._apply_template_replacements(html_template, final, candles_json, self.indicators, markers, cum_pl_series, pivot_lines, trade_data, symbol)
            self._last_export_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), self.cfg.export_csv) 

            with open(self._last_export_path, 'w', encoding='utf-8') as f:
                f.write(html_template)
            if getattr(self.cfg, 'tv_auto_open', False) and not self._opened:
                import webbrowser
                try:
                    webbrowser.open('file://' + os.path.abspath(self._last_export_path))
                    self._opened = True
                except Exception:
                    pass
            return self._last_export_path
        except Exception as e:
            try:
                output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'output')
                os.makedirs(output_dir, exist_ok=True)
                error_log_path = os.path.join(output_dir, 'tv_export_error.log')
                with open(error_log_path, 'a', encoding='utf-8') as f:
                    f.write(f"EXPORT_FAIL: {e}\n")
            except Exception:
                pass
            return None

    def _apply_template_replacements(self, html_template, final, candles_json, indicators, markers, cum_pl_series, pivot_lines, trade_data, symbol):
        separate_pl = getattr(self.cfg, 'tv_pl_separate_panel', False)
        if separate_pl:
            html_template = html_template.replace('%PLDIV%', "<div id='plpanel'></div>") \
                                         .replace('%CHARTFLEX%', '3') \
                                         .replace('%PLFLEX%', '1')
        else:
            html_template = html_template.replace('%PLDIV%', '') \
                                         .replace('%CHARTFLEX%', '1') \
                                         .replace('%PLFLEX%', '0')
        if not final and getattr(self.cfg, 'tv_refresh_seconds', 0) > 0:
            tag = f"<meta http-equiv='refresh' content='{self.cfg.tv_refresh_seconds}'>"
            if '<head>' in html_template:
                html_template = html_template.replace('<head>', '<head>\n' + tag)
        if final:
            no_refresh_script = (
                "<script>\n"
                "(function(){\n"
                "  try{\n"
                "    var metas = document.querySelectorAll('meta[http-equiv=\"refresh\"]');\n"
                "    metas.forEach(function(m){ if(m && m.parentNode) m.parentNode.removeChild(m); });\n"
                "    if(window.__tv_auto_refresh_interval_ids && Array.isArray(window.__tv_auto_refresh_interval_ids)) {\n"
                "      window.__tv_auto_refresh_interval_ids.forEach(function(id){ try{ clearInterval(id); }catch(e){} });\n"
                "    }catch(e){}\n"
                "    try{ window.location.reload = function(){ /* disabled by final export */ }; }catch(e){}\n"
                "  }catch(e){}\n"
                "})();\n"
                "</script>"
            )
            if '</body></html>' in html_template:
                html_template = html_template.replace('</body></html>', no_refresh_script + '\n</body></html>')

        data_obj = {
            'symbol_name': self.symbol,
            'data': {
                'candles': candles_json,
                'indicators': indicators,
                'markers': markers,
                'cum_pl': cum_pl_series,
                'trade_data': trade_data
            }
        }
        html_template = (html_template
                         .replace('__SYMBOL_DATA__', json.dumps(data_obj))
                         .replace('__PL_HOVER__', 'true' if getattr(self.cfg, 'pl_line_hover_only', False) else 'false')
                         .replace('__VOL_RATIO__', str(getattr(self.cfg, 'tv_volume_ratio', 0.25)))                         
                         .replace('%SEPARATE_PL%', 'true' if separate_pl else 'false'))

        pivot_lines_js = json.dumps(pivot_lines)
        pivot_js = (
            f"\n// Multi-pivot overlay injection\nconst pivotLines={pivot_lines_js};\n"
            "if(pivotLines && pivotLines.length){\n"
            "  try {\n"
            "    for(const line of pivotLines){\n"
            "      const s = chart.addLineSeries({color:line.color,lineWidth:1,lineStyle:line.line_style,lastValueVisible:false,priceLineVisible:false,crosshairMarkerVisible:false});\n"
            "      s.setData([{time:line.start,value:line.value},{time:line.end,value:line.value}]);\n"
            "    }\n"
            "  } catch(e){ console.warn('Pivot lines injection failed', e); }\n"
            "}\n"
        )
        # Inject pivot lines before closing script tag
        if '</script>' in html_template:
            html_template = html_template.replace('</script>', pivot_js + '\n      </script>')
        return html_template

    def _prepare_emas(self, df):
        # Compute additional indicators
        if self.cfg.additional_indicators:
            for ind in self.cfg.additional_indicators:
                name = ind['name']
                params = ind['params']
                if name == 'EMA':
                    if ind['type'] == 'multi_indicator':
                        for param in params:
                            period = param['period']
                            if _HAS_TALIB:
                                ema_values = talib.EMA(df['close'].astype(float), timeperiod=period)
                            else:
                                ema_values = df['close'].rolling(period, min_periods=1).mean()
                            df[f'ema{period}'] = ema_values
        else:
            if 'ema5' not in df.columns or df['ema5'].isna().all():
                if _HAS_TALIB:
                    df['ema5'] = talib.EMA(df['close'].astype(float), timeperiod=5)
                else:
                    df['ema5'] = df['close'].rolling(5, min_periods=1).mean()
            if 'ema20' not in df.columns or df['ema20'].isna().all():
                if _HAS_TALIB:
                    df['ema20'] = talib.EMA(df['close'].astype(float), timeperiod=20)
                else:
                    df['ema20'] = df['close'].rolling(20, min_periods=1).mean()


    def _prepare_candles(self, df):
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

    def _prepare_ema_series(self, df, ema_col, candles_json):
        return [
            {'time': candles_json[i]['time'], 'value': float(row[ema_col])}
            for i, (_, row) in enumerate(df.iterrows()) if not pd.isna(row[ema_col])
        ]

    def _prepare_pivot_lines(self, df, candles_json):
        pivot_lines = []
        print(f"Debug: DataFrame columns: {list(df.columns)}")
        
        if 'pivot_time' in df.columns:
            time_column_name = 'pivot_time'
            range_high_column_name = 'pivot_high'
            range_low_column_name = 'pivot_low'            
            print(f"Debug: Found {time_column_name} column")            
            self.create_lines(df, pivot_lines, time_column_name, range_high_column_name, range_low_column_name, "#1900FF", 1)  
        
        if 'orb_time' in df.columns:
            time_column_name = 'orb_time'
            range_high_column_name = 'range_high'
            range_low_column_name = 'range_low'
            print(f"Debug: Found {time_column_name} column")
            self.create_lines(df, pivot_lines, time_column_name, range_high_column_name, range_low_column_name,  "#2BFF0057", 0)       
        
        print(f"Debug: Generated {len(pivot_lines)} pivot lines")
        return pivot_lines

    #0 (LineStyle.Solid): Solid line
    #1 (LineStyle.Dashed): Dashed line
    #2 (LineStyle.Dotted): Dotted line
    #3 (LineStyle.LargeDashed): Large dashed line
    #4 (LineStyle.SparseDotted): Sparse dotted line
    def create_lines(self, df, pivot_lines, time_column_name, range_high_column_name, range_low_column_name, line_color, line_style):
        pivots_full = df[[time_column_name, range_high_column_name, range_low_column_name, 'pivot_direction']].copy()
        pivots_full = pivots_full.dropna(subset=[time_column_name])
        print(f"Debug: Non-null pivot data rows: {len(pivots_full)}")
            
        if not pivots_full.empty:
            pivots_full[time_column_name] = pd.to_datetime(pivots_full[time_column_name], utc=True)
            grouped = []
            for ptime, grp in pivots_full.groupby(time_column_name, sort=False):
                start_idx = grp.index[0]
                high = grp[range_high_column_name].iloc[0] if range_high_column_name in grp else None
                low = grp[range_low_column_name].iloc[0] if range_low_column_name in grp else None
                direction = grp['pivot_direction'].iloc[0] if 'pivot_direction' in grp else None
                grouped.append((ptime, start_idx, high, low, direction))
                print(f"Debug: Pivot group - time: {ptime}, high: {high}, low: {low}, direction: {direction}")
                
            grouped.sort(key=lambda x: x[1])
            for i, (ptime, start_idx, high, low, direction) in enumerate(grouped):
                block_mask = (pivots_full[time_column_name] == ptime)
                segment_indices = pivots_full[block_mask].index
                if len(segment_indices) == 0:
                    continue
                end_idx = segment_indices[-1]
                try:
                    start_unix = int(start_idx.timestamp())
                    end_unix = int(end_idx.timestamp())
                except Exception as e:
                    print(f"Debug: Failed to convert timestamps: {e}")
                    continue
                    
                if high is not None and not pd.isna(high):
                    pivot_lines.append({'start': start_unix, 'end': end_unix, 'value': float(high), 'color': line_color, 'line_style': line_style})
                    print(f"Debug: Added high pivot line at {high}")
                if low is not None and not pd.isna(low):
                    pivot_lines.append({'start': start_unix, 'end': end_unix, 'value': float(low), 'color': line_color,'line_style': line_style})
                    print(f"Debug: Added low pivot line at {low}")

    def _get_unix_time(self, dt_val, df, ts_time_map):
        try:
            ts_key = pd.to_datetime(dt_val, utc=True)
        except Exception:
            return None
        freq = None
        try:
            freq = pd.infer_freq(df.index)
        except Exception:
            freq = None
        if freq is None:
            cand_attrs = ['candle_minutes', 'candle_size', 'candle_mins', 'candle', 'timeframe', 'interval', 'bar_minutes', 'bar_size']
            found = None
            for a in cand_attrs:
                if hasattr(self.cfg, a):
                    found = getattr(self.cfg, a)
                    break
            if found is not None:
                try:
                    n = int(found)
                    freq = f"{n}min"
                except Exception:
                    freq = str(found)
            else:
                freq = '1min'
        try:
            rounded_key = ts_key.round(freq)
        except Exception:
            rounded_key = ts_key.round('1min')
        t_unix_local = ts_time_map.get(rounded_key)
        if t_unix_local is None:
            t_unix_local = ts_time_map.get(ts_key)
        if t_unix_local is None and len(ts_time_map):
            nearest = min(ts_time_map.keys(), key=lambda k: abs(k - ts_key))
            t_unix_local = ts_time_map.get(nearest)
        return t_unix_local

    def _prepare_markers(self, df, completed_trades, candles_json):
        markers = []
        tv_pl_multiline = getattr(self.cfg, 'tv_pl_multiline', False)
        tv_pl_color_scale = getattr(self.cfg, 'tv_pl_color_scale', True)
        padding_lines = int(getattr(self.cfg, 'tv_pl_padding', 0))
        exit_pl_map = {}
        ts_time_map = {pd.to_datetime(ts): c['time'] for ts, c in zip(df.index, candles_json)}
        if completed_trades:
            for tr in completed_trades:                
                exit_dt = tr.get('exit_datetime') or tr.get('entry_datetime')
                if exit_dt is None:
                    continue
                dt_key = pd.to_datetime(exit_dt, utc=True)
                if dt_key not in df.index:
                    continue
                pl_val = float(tr.get('pl', 0))
                pl_text = f"+{pl_val:.1f}" if pl_val >= 0 else f"{pl_val:.1f}"
                direction = tr.get('position_type', '')[:1].upper()
                tup = (direction, pl_val, pl_text)
                exit_pl_map.setdefault(dt_key, []).append(tup)
                if abs(pl_val) > self._pl_max_abs:
                    self._pl_max_abs = abs(pl_val)
        for idx_ts, row in df.iterrows():
            sig = row.get('signal')
            if sig not in ('buy', 'sell'):
                continue
            ts_key = pd.to_datetime(idx_ts)
            t_unix = self._get_unix_time(ts_key, df, ts_time_map)
            if t_unix is None:
                continue
            pl_list = exit_pl_map.get(ts_key)