import os
import json
import pandas as pd


class MultiSymbolChart:
    """
    Consolidates multiple symbol charts into a single interactive viewer.
    Allows switching between symbols via dropdown.
    """
    
    def __init__(self, cfg):
        self.cfg = cfg
        self.symbols_data = {}
        
    def add_symbol_data(self, symbol, candles_df, completed_trades, indicators_data):
        """
        Add data for a single symbol to be included in the multi-symbol chart
        
        Args:
            symbol: Symbol name
            candles_df: DataFrame with OHLCV data
            completed_trades: List of completed trade dictionaries
            indicators_data: List of indicator dictionaries with name, color, data
        """
        try:
            df = candles_df.copy()
            
            # Ensure index is timezone-aware datetime
            if not isinstance(df.index, pd.DatetimeIndex):
                df.index = pd.to_datetime(df.index)
            if df.index.tz is None:
                df.index = df.index.tz_localize('UTC')
            else:
                df.index = df.index.tz_convert('UTC')
            
            # Prepare candles JSON
            candles_json = []
            for ts, row in df.iterrows():
                try:
                    candles_json.append({
                        'time': int(ts.timestamp()),
                        'open': float(row['open']),
                        'high': float(row['high']),
                        'low': float(row['low']),
                        'close': float(row['close']),
                        'volume': int(row.get('volume', 0))
                    })
                except Exception:
                    continue
            
            candles_json.sort(key=lambda x: x['time'])
            
            # Prepare indicators
            indicators = []
            for ind in indicators_data:
                indicators.append({
                    'name': ind['name'],
                    'color': ind['color'],
                    'lineWidth': ind.get('lineWidth', 1),
                    'data': ind['data']
                })
            
            # Prepare trades
            trades_list = []
            if completed_trades:
                for trade in completed_trades:
                    trade_copy = trade.copy()
                    # Convert timestamps
                    if trade_copy.get('entry_datetime'):
                        if not isinstance(trade_copy['entry_datetime'], str):
                            trade_copy['entry_datetime'] = str(pd.to_datetime(trade_copy['entry_datetime'], utc=True))
                    if trade_copy.get('exit_datetime'):
                        if not isinstance(trade_copy['exit_datetime'], str):
                            trade_copy['exit_datetime'] = str(pd.to_datetime(trade_copy['exit_datetime'], utc=True))
                    trades_list.append(trade_copy)
            
            self.symbols_data[symbol] = {
                'candles': candles_json,
                'indicators': indicators,
                'trades': trades_list,
                'df': df  # Keep for marker/pl calculation
            }
            
            return True
            
        except Exception as e:
            print(f"Error adding symbol {symbol} to multi-symbol chart: {e}")
            return False
    
    def _load_template(self):
        """Load the multi-symbol chart template"""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        template_path = os.path.join(base_dir, 'templates', 'multi_symbol_chart_template.html')
        
        if os.path.exists(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            # Return embedded template if file doesn't exist
            return self._get_embedded_template()
    
    def export_chart(self, output_filename='multi_symbol_chart.html'):
        """
        Generate the consolidated multi-symbol HTML chart
        
        Args:
            output_filename: Name of the output HTML file
            
        Returns:
            Path to the generated HTML file
        """
        if not self.symbols_data:
            print("No symbols data to export")
            return None
        
        try:
            output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'output')
            os.makedirs(output_dir, exist_ok=True)
            
            # Prepare the data structure for all symbols
            all_symbols_data = {}
            for symbol, data in self.symbols_data.items():
                all_symbols_data[symbol] = {
                    'candles': data['candles'],
                    'indicators': data['indicators'],
                    'trades': data['trades']
                }
            
            # Load template
            html_template = self._load_template()
            
            # Replace placeholders
            html_content = html_template.replace(
                '__ALL_SYMBOLS_DATA__',
                json.dumps(all_symbols_data, indent=2)
            )
            
            # Write file
            output_path = os.path.join(output_dir, output_filename)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(f"Multi-symbol chart exported to: {output_path}")
            
            # Auto-open if configured
            if getattr(self.cfg, 'tv_auto_open', False):
                import webbrowser
                try:
                    webbrowser.open('file://' + os.path.abspath(output_path))
                except Exception as e:
                    print(f"Could not auto-open browser: {e}")
            
            return output_path
            
        except Exception as e:
            print(f"Error exporting multi-symbol chart: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _get_embedded_template(self):
        """Returns embedded HTML template if file doesn't exist"""
        return '''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8" />
    <title>Multi-Symbol Chart Viewer</title>
    <script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script>
    <style>
        body, html {
            margin: 0;
            padding: 0;
            background: #0d1117;
            color: #ddd;
            font-family: Inter, Arial;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        #wrap {
            flex: 1;
            display: flex;
            flex-direction: column;
        }
        #chart {
            flex: 1;
            position: relative;
        }
        #top-bar {
            position: absolute;
            top: 8px;
            left: 8px;
            z-index: 10;
            display: flex;
            gap: 10px;
        }
        #symbol-selector {
            background: rgba(0, 0, 0, 0.8);
            color: white;
            border: 1px solid #444;
            padding: 6px 10px;
            font-size: 14px;
            border-radius: 4px;
            cursor: pointer;
        }
        .legend {
            position: absolute;
            top: 45px;
            left: 8px;
            background: rgba(0, 0, 0, 0.7);
            padding: 6px 10px;
            font-size: 12px;
            border-radius: 4px;
            font-family: monospace;
        }
        .watermark {
            position: absolute;
            bottom: 8px;
            right: 12px;
            font-size: 11px;
            color: #444;
            font-weight: 600;
        }
        #stats {
            position: absolute;
            top: 8px;
            right: 8px;
            background: rgba(0, 0, 0, 0.8);
            padding: 8px;
            border-radius: 4px;
            font-size: 12px;
            max-width: 300px;
        }
        .stat-row {
            display: flex;
            justify-content: space-between;
            padding: 2px 0;
        }
        .stat-label {
            color: #888;
        }
        .stat-value {
            color: #fff;
            font-weight: bold;
        }
        .positive {
            color: #26a69a;
        }
        .negative {
            color: #ef5350;
        }
    </style>
</head>
<body>
    <div id="wrap">
        <div id="chart">
            <div id="top-bar">
                <select id="symbol-selector">
                    <option value="">Select Symbol...</option>
                </select>
            </div>
            <div class="legend" id="legend">Select a symbol to view chart</div>
            <div id="stats"></div>
        </div>
    </div>
    <div class="watermark">Multi-Symbol Chart Viewer</div>
    
    <script>
        const allSymbolsData = __ALL_SYMBOLS_DATA__;
        
        let chart = null;
        let candleSeries = null;
        let volumeSeries = null;
        let indicatorSeries = [];
        let currentSymbol = null;
        
        // Initialize chart
        function initChart() {
            const chartDiv = document.getElementById('chart');
            chart = LightweightCharts.createChart(chartDiv, {
                layout: { 
                    background: { type: 'Solid', color: '#0d1117' }, 
                    textColor: '#DDD' 
                },
                rightPriceScale: { borderColor: '#30363d' },
                timeScale: { 
                    borderColor: '#30363d', 
                    timeVisible: true, 
                    secondsVisible: false 
                },
                grid: { 
                    vertLines: { color: '#1e242b' }, 
                    horzLines: { color: '#1e242b' } 
                },
                crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
                localization: { timeZone: 'Asia/Kolkata' }
            });
            
            candleSeries = chart.addCandlestickSeries({
                upColor: '#26a69a',
                downColor: '#ef5350',
                borderVisible: false,
                wickUpColor: '#26a69a',
                wickDownColor: '#ef5350'
            });
            
            volumeSeries = chart.addHistogramSeries({
                priceFormat: { type: 'volume' },
                priceScaleId: 'vol'
            });
            
            candleSeries.priceScale().applyOptions({ 
                scaleMargins: { top: 0.05, bottom: 0.27 } 
            });
            volumeSeries.priceScale().applyOptions({ 
                scaleMargins: { top: 0.75, bottom: 0.02 } 
            });
            
            window.addEventListener('resize', () => {
                chart.applyOptions({ width: chartDiv.clientWidth });
            });
        }
        
        // Load symbol data
        function loadSymbol(symbol) {
            if (!symbol || !allSymbolsData[symbol]) return;
            
            currentSymbol = symbol;
            const data = allSymbolsData[symbol];
            
            // Clear existing indicator series
            indicatorSeries.forEach(s => chart.removeSeries(s));
            indicatorSeries = [];
            
            // Load candles
            candleSeries.setData(data.candles);
            
            // Load volume
            const volumeData = data.candles.map(c => ({
                time: c.time,
                value: c.volume || 0,
                color: c.close >= c.open ? 'rgba(38,166,154,0.5)' : 'rgba(239,83,80,0.5)'
            }));
            volumeSeries.setData(volumeData);
            
            // Load indicators
            data.indicators.forEach(ind => {
                const series = chart.addLineSeries({
                    color: ind.color,
                    lineWidth: ind.lineWidth || 1,
                    priceLineVisible: false
                });
                series.setData(ind.data);
                indicatorSeries.push(series);
            });
            
            // Prepare markers from trades
            const markers = prepareMarkers(data.trades, data.candles);
            candleSeries.setMarkers(markers);
            
            // Update stats
            updateStats(symbol, data.trades);
            
            // Fit content
            chart.timeScale().fitContent();
        }
        
        // Prepare markers from trades
        function prepareMarkers(trades, candles) {
            const markers = [];
            const timeMap = {};
            candles.forEach(c => { timeMap[c.time] = true; });
            
            function findNearestTime(targetTime) {
                let nearest = null;
                let minDiff = Infinity;
                candles.forEach(c => {
                    const diff = Math.abs(c.time - targetTime);
                    if (diff < minDiff) {
                        minDiff = diff;
                        nearest = c.time;
                    }
                });
                return nearest;
            }
            
            trades.forEach(trade => {
                const posType = (trade.position_type || '').toLowerCase();
                
                // Entry marker
                if (trade.entry_datetime) {
                    const entryTime = Math.floor(new Date(trade.entry_datetime).getTime() / 1000);
                    const nearestEntry = findNearestTime(entryTime);
                    if (nearestEntry) {
                        const isLong = posType.includes('long');
                        markers.push({
                            time: nearestEntry,
                            position: isLong ? 'belowBar' : 'aboveBar',
                            color: isLong ? 'rgba(38,166,154,0.6)' : 'rgba(239,83,80,0.6)',
                            shape: isLong ? 'arrowUp' : 'arrowDown',
                            text: 'E'
                        });
                    }
                }
                
                // Exit marker
                if (trade.exit_datetime) {
                    const exitTime = Math.floor(new Date(trade.exit_datetime).getTime() / 1000);
                    const nearestExit = findNearestTime(exitTime);
                    if (nearestExit) {
                        const pl = parseFloat(trade.pl || 0);
                        const isLong = posType.includes('long');
                        markers.push({
                            time: nearestExit,
                            position: isLong ? 'aboveBar' : 'belowBar',
                            color: pl >= 0 ? 'rgba(38,166,154,0.8)' : 'rgba(239,83,80,0.8)',
                            shape: isLong ? 'arrowDown' : 'arrowUp',
                            text: `${pl >= 0 ? '+' : ''}${pl.toFixed(1)}`
                        });
                    }
                }
            });
            
            return markers;
        }
        
        // Update statistics
        function updateStats(symbol, trades) {
            const statsDiv = document.getElementById('stats');
            
            if (!trades || trades.length === 0) {
                statsDiv.innerHTML = `<div><strong>${symbol}</strong></div><div>No trades</div>`;
                return;
            }
            
            let totalPL = 0;
            let wins = 0;
            let losses = 0;
            
            trades.forEach(trade => {
                const pl = parseFloat(trade.pl || 0);
                totalPL += pl;
                if (pl > 0) wins++;
                else if (pl < 0) losses++;
            });
            
            const winRate = trades.length > 0 ? (wins / trades.length * 100).toFixed(1) : 0;
            const plClass = totalPL >= 0 ? 'positive' : 'negative';
            
            statsDiv.innerHTML = `
                <div style="margin-bottom: 8px;"><strong>${symbol}</strong></div>
                <div class="stat-row">
                    <span class="stat-label">Total Trades:</span>
                    <span class="stat-value">${trades.length}</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Wins / Losses:</span>
                    <span class="stat-value">${wins} / ${losses}</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Win Rate:</span>
                    <span class="stat-value">${winRate}%</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Total P&L:</span>
                    <span class="stat-value ${plClass}">${totalPL >= 0 ? '+' : ''}${totalPL.toFixed(2)}</span>
                </div>
            `;
        }
        
        // Initialize
        initChart();
        
        // Populate symbol selector
        const selector = document.getElementById('symbol-selector');
        Object.keys(allSymbolsData).sort().forEach(symbol => {
            const option = document.createElement('option');
            option.value = symbol;
            option.textContent = symbol;
            selector.appendChild(option);
        });
        
        // Auto-select first symbol
        if (Object.keys(allSymbolsData).length > 0) {
            const firstSymbol = Object.keys(allSymbolsData).sort()[0];
            selector.value = firstSymbol;
            loadSymbol(firstSymbol);
        }
        
        // Handle symbol change
        selector.addEventListener('change', (e) => {
            loadSymbol(e.target.value);
        });
        
        // Update legend on crosshair move
        const legendEl = document.getElementById('legend');
        chart.subscribeCrosshairMove(param => {
            if (!param.time || !currentSymbol) {
                legendEl.textContent = currentSymbol || 'Select a symbol';
                return;
            }
            
            const data = param.seriesData.get(candleSeries);
            if (data) {
                legendEl.textContent = `${currentSymbol} | O:${data.open.toFixed(2)} H:${data.high.toFixed(2)} L:${data.low.toFixed(2)} C:${data.close.toFixed(2)}`;
            }
        });
    </script>
</body>
</html>'''
