"""
ECharts图表组件封装
将ui.echart绘图部分单独封装为一个类，提供简洁的接口供主程序调用
"""
import json
from nicegui import ui
from typing import Dict, Any, Optional


class RealtimeChartWidget:
    """实时图表组件，封装ui.echart和相关JavaScript交互"""
    
    def __init__(self, initial_option: Dict[str, Any]):
        """
        初始化图表组件
        
        Args:
            initial_option: 初始的ECharts配置选项
        """
        self.chart_element: Optional[Any] = None
        self._initial_option = initial_option
        self._setup_chart()
    
    def _setup_chart(self):
        """创建图表元素并设置所有必要的CSS和JavaScript"""
        # 获取图表高度
        chart_height = self._initial_option.get('height', 1000)
        
        # 添加自定义CSS样式
        ui.add_head_html('''
        <style>
        .echarts {
            position: relative !important;
        }
        canvas {
            pointer-events: none;
        }
        </style>
        ''')
        
        # 创建图表元素
        self.chart_element = ui.echart(self._initial_option).style(
            f'height: {chart_height}px; width: 100%; min-height: {chart_height}px;'
        )
        
        # 初始化JavaScript交互功能
        self._setup_javascript()
    
    def _setup_javascript(self):
        """设置JavaScript交互功能（tooltip、指示线、缩放等）"""
        chart_id = self.chart_element.id
        
        # 初始化枚举标签映射和所有交互功能
        ui.add_body_html(f'''
        <script>
        window.enumLabelsMap = {{}};
        
        // 定义全局更新函数
        window.updateEnumLabels = function(newLabels) {{
            window.enumLabelsMap = newLabels;
        }};
        
        // Tooltip formatter 函数
        window.customTooltipFormatter = function(params) {{
            if (!params || params.length === 0) return '';
            if (!Array.isArray(params)) params = [params];
            
            // 获取时间戳
            let timestamp = null;
            for (let i = 0; i < params.length; i++) {{
                if (params[i].value && params[i].value[0]) {{
                    timestamp = params[i].value[0];
                    break;
                }}
            }}
            
            if (!timestamp) return '';
            
            // 格式化时间（日期+时间+毫秒）
            const date = new Date(timestamp);
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            const h = String(date.getHours()).padStart(2, '0');
            const m = String(date.getMinutes()).padStart(2, '0');
            const s = String(date.getSeconds()).padStart(2, '0');
            const ms = String(date.getMilliseconds()).padStart(3, '0');
            const time = year + '-' + month + '-' + day + ' ' + h + ':' + m + ':' + s + '.' + ms;
            
            let html = '<div style="font-weight:bold;margin-bottom:8px;border-bottom:1px solid #666;padding-bottom:5px;">' + time + '</div>';
            
            // 收集信号数据（去重）
            const signalsMap = new Map();
            for (let i = 0; i < params.length; i++) {{
                const p = params[i];
                const v = p.value ? p.value[1] : null;
                if (v != null) {{
                    // 使用 seriesIndex（从0开始），但显示时需要+1来匹配枚举标签映射
                    const signalIndex = p.seriesIndex + 1;
                    
                    if (signalsMap.has(signalIndex)) continue;
                    
                    // 枚举类型显示文本标签，数值类型显示数字
                    let displayValue;
                    const enumMap = window.enumLabelsMap[signalIndex.toString()];
                    if (enumMap) {{
                        const enumVal = Math.round(v);
                        displayValue = enumMap[enumVal.toString()] || enumVal.toString();
                    }} else {{
                        displayValue = v.toFixed(3);
                    }}
                    
                    signalsMap.set(signalIndex, {{
                        name: p.seriesName,  // 现在这将是自定义信号名
                        value: v,
                        displayValue: displayValue,
                        color: p.color,
                        index: signalIndex
                    }});
                }}
            }}
            
            // 按信号编号排序
            let signals = Array.from(signalsMap.values());
            signals.sort((a, b) => a.index - b.index);
            
            // 分栏显示
            const maxPerColumn = 12;
            const numColumns = Math.ceil(signals.length / maxPerColumn);
            
            if (numColumns > 1) {{
                html += '<div style="display:flex;gap:15px;">';
                for (let col = 0; col < numColumns; col++) {{
                    html += '<div style="flex:0 0 auto;">';
                    const start = col * maxPerColumn;
                    const end = Math.min(start + maxPerColumn, signals.length);
                    for (let i = start; i < end; i++) {{
                        const sig = signals[i];
                        html += '<div style="margin:2px 0;white-space:nowrap;display:flex;align-items:center;">';
                        html += '<span style="width:8px;height:8px;background-color:' + sig.color + ';border-radius:50%;margin-right:6px;flex-shrink:0;"></span>';
                        html += '<span style="width:65px;font-size:11px;flex-shrink:0;">' + sig.name + '</span>';
                        html += '<span style="font-weight:bold;font-size:11px;margin-left:4px;">' + sig.displayValue + '</span>';
                        html += '</div>';
                    }}
                    html += '</div>';
                }}
                html += '</div>';
            }} else {{
                for (let i = 0; i < signals.length; i++) {{
                    const sig = signals[i];
                    html += '<div style="margin:3px 0">';
                    html += '<span style="display:inline-block;width:10px;height:10px;background-color:' + sig.color + ';border-radius:50%;margin-right:8px"></span>';
                    html += '<span style="display:inline-block;width:80px">' + sig.name + '</span>';
                    html += '<span style="font-weight:bold">' + sig.displayValue + '</span>';
                    html += '</div>';
                }}
            }}
            
            return html;
        }};
        
        // 初始化 tooltip 和指示线
        (function setupTooltip() {{
            let attempts = 0;
            const maxAttempts = 20;
            let customLine = null;
            
            const interval = setInterval(function() {{
                const el = getElement({chart_id});
                if (el && el.chart) {{
                    el.chart.setOption({{
                        tooltip: {{
                            formatter: window.customTooltipFormatter
                        }}
                    }}, false);
                    
                    // 同步所有 X 轴范围
                    const option = el.chart.getOption();
                    if (option.xAxis && option.xAxis.length > 0) {{
                        const firstXAxis = option.xAxis[0];
                        const xMin = firstXAxis.min;
                        const xMax = firstXAxis.max;
                        
                        if (xMin !== undefined && xMax !== undefined) {{
                            for (let i = 0; i < option.xAxis.length; i++) {{
                                option.xAxis[i].min = xMin;
                                option.xAxis[i].max = xMax;
                            }}
                            
                            el.chart.setOption({{
                                xAxis: option.xAxis
                            }}, false);
                        }}
                    }}
                    
                    // 创建垂直指示线
                    if (!customLine) {{
                        // 获取图表的 DOM 元素和容器
                        const chartDom = el.chart.getDom();
                        const chartContainer = chartDom.parentElement;
                        
                        customLine = document.createElement('div');
                        customLine.style.cssText = 'position: absolute; top: 0; width: 2px; background-color: rgba(102, 102, 102, 0.8); pointer-events: none; display: none; z-index: 9999;';
                        customLine.id = 'custom-indicator-line';
                        
                        // 动态设置竖线高度
                        const updateLineHeight = function() {{
                            const height = chartDom.offsetHeight || chartContainer.offsetHeight;
                            customLine.style.height = height + 'px';
                        }};
                        
                        // 确保容器是相对定位
                        chartContainer.style.position = 'relative';
                        chartContainer.appendChild(customLine);
                        
                        // 初始设置高度
                        updateLineHeight();
                        
                        // 监听窗口大小变化和图表更新
                        window.addEventListener('resize', updateLineHeight);
                        el.chart.on('finished', updateLineHeight);
                        
                        // 鼠标移动事件
                        chartContainer.addEventListener('mousemove', function(e) {{
                            const rect = chartContainer.getBoundingClientRect();
                            const x = e.clientX - rect.left;
                            customLine.style.left = x + 'px';
                            customLine.style.display = 'block';
                        }});
                        
                        chartContainer.addEventListener('mouseleave', function() {{
                            customLine.style.display = 'none';
                        }});
                    }}
                    
                    // 监听图表更新事件，确保 formatter 不被覆盖，并同步 X 轴
                    el.chart.on('finished', function() {{
                        el.chart.setOption({{
                            tooltip: {{
                                formatter: window.customTooltipFormatter
                            }}
                        }}, false);
                        
                        // 每次图表更新后，同步所有 X 轴的范围
                        const currentOption = el.chart.getOption();
                        if (currentOption.xAxis && currentOption.xAxis.length > 1) {{
                            const firstXAxis = currentOption.xAxis[0];
                            const xMin = firstXAxis.min;
                            const xMax = firstXAxis.max;
                            
                            if (xMin !== undefined && xMax !== undefined) {{
                                let needUpdate = false;
                                for (let i = 1; i < currentOption.xAxis.length; i++) {{
                                    if (currentOption.xAxis[i].min !== xMin || currentOption.xAxis[i].max !== xMax) {{
                                        currentOption.xAxis[i].min = xMin;
                                        currentOption.xAxis[i].max = xMax;
                                        needUpdate = true;
                                    }}
                                }}
                                
                                if (needUpdate) {{
                                    el.chart.setOption({{
                                        xAxis: currentOption.xAxis
                                    }}, false);
                                }}
                            }}
                        }}
                    }});
                    
                    // 监听缩放事件，根据可见区域的数据点密度动态调整点的显示
                    el.chart.on('dataZoom', function(params) {{
                        const option = el.chart.getOption();
                        const dataZoom = option.dataZoom && option.dataZoom.length > 0 ? option.dataZoom[0] : null;
                        
                        if (!dataZoom) return;
                        
                        // 遍历所有系列，根据可见范围内的数据点数量决定是否显示点
                        const series = option.series;
                        let needUpdate = false;
                        
                        for (let i = 0; i < series.length; i++) {{
                            if (!series[i].data || series[i].data.length === 0) continue;
                            
                            const totalPoints = series[i].data.length;
                            const startPercent = dataZoom.start !== undefined ? dataZoom.start : 0;
                            const endPercent = dataZoom.end !== undefined ? dataZoom.end : 100;
                            
                            // 计算可见范围内的数据点数量
                            const visibleStartIndex = Math.floor(totalPoints * startPercent / 100);
                            const visibleEndIndex = Math.ceil(totalPoints * endPercent / 100);
                            const visiblePointCount = visibleEndIndex - visibleStartIndex;
                            
                            // 根据可见数据点密度决定是否显示点标记
                            let showSymbol = series[i].showSymbol;
                            let symbolSize = series[i].symbolSize;
                            
                            if (visiblePointCount > 200) {{
                                showSymbol = false;
                                symbolSize = 4;
                            }} else if (visiblePointCount > 100) {{
                                showSymbol = true;
                                symbolSize = 4;
                            }} else if (visiblePointCount > 30) {{
                                showSymbol = true;
                                symbolSize = 5;
                            }} else {{
                                showSymbol = true;
                                symbolSize = 6;
                            }}
                            
                            // 检查是否需要更新
                            if (series[i].showSymbol !== showSymbol || series[i].symbolSize !== symbolSize) {{
                                series[i].showSymbol = showSymbol;
                                series[i].symbolSize = symbolSize;
                                needUpdate = true;
                            }}
                        }}
                        
                        // 如果有变化，更新图表
                        if (needUpdate) {{
                            el.chart.setOption({{
                                series: series
                            }}, false, false);
                        }}
                    }});
                    
                    clearInterval(interval);
                }} else if (attempts++ >= maxAttempts) {{
                    clearInterval(interval);
                }}
            }}, 100);
        }})();
        </script>
        ''')
    
    def update_enum_labels(self, signal_types: Dict[str, Dict[str, Any]]):
        """
        更新枚举标签映射
        
        Args:
            signal_types: 信号类型配置，格式如 {'signal_name': {'type': 'enum', 'enum_labels': {...}}}
        """
        enum_labels_json = {}
        # 使用 enumerate 按顺序为信号分配索引（从1开始），而不是从信号名中解析数字
        for signal_index, (signal_name, config) in enumerate(signal_types.items(), start=1):
            if config['type'] == 'enum':
                # signal_index 是显示编号（从1开始）
                # 使用这个编号作为键，与 tooltip 中的 Signal X 匹配
                # 将整数键转换为字符串键以便 JSON 序列化
                enum_labels_json[str(signal_index)] = {str(k): v for k, v in config['enum_labels'].items()}
        
        # 更新枚举标签映射到全局变量
        enum_labels_js = json.dumps(enum_labels_json)
        
        # 使用 run_javascript 强制立即执行更新（而不是 add_body_html）
        update_script = f'''
            if (typeof window.updateEnumLabels === 'function') {{
                window.updateEnumLabels({enum_labels_js});
            }} else {{
                window.enumLabelsMap = {enum_labels_js};
            }}
        '''
        
        # 通过 run_javascript 立即执行
        try:
            ui.run_javascript(update_script)
        except Exception as e:
            # 如果 run_javascript 失败，使用 add_body_html 作为备选方案
            import time
            timestamp = int(time.time() * 1000)
            ui.add_body_html(f'''
            <script id="enum-labels-{timestamp}">
                (function() {{
                    {update_script}
                }})();
            </script>
            ''')
    
    def update_chart_option(self, new_option: Dict[str, Any], exclude_tooltip: bool = True):
        """
        更新图表配置
        
        Args:
            new_option: 新的ECharts配置选项
            exclude_tooltip: 是否排除tooltip配置（避免覆盖自定义formatter）
        """
        # 更新图表高度
        new_height = new_option.get('height', 1000)
        
        # 更新配置
        for key, value in new_option.items():
            if exclude_tooltip and key == 'tooltip':
                continue  # 保留 JavaScript 中自定义的 tooltip formatter
            self.chart_element.options[key] = value
        
        # 更新样式
        self.chart_element._props['style'] = f'height: {new_height}px; width: 100%; min-height: {new_height}px;'
        self.chart_element.update()
    
    def update_series_data(self, series_data: list):
        """
        更新系列数据
        
        Args:
            series_data: 系列数据列表，每个元素包含 data、showSymbol、symbolSize 等配置
        """
        for i, series_config in enumerate(series_data):
            if i < len(self.chart_element.options['series']):
                # 更新数据和显示样式
                self.chart_element.options['series'][i]['data'] = series_config['data']
                self.chart_element.options['series'][i]['showSymbol'] = series_config['showSymbol']
                self.chart_element.options['series'][i]['symbolSize'] = series_config['symbolSize']
        
        self.chart_element.update()
    
    def get_element(self):
        """获取图表元素（用于在UI布局中使用）"""
        return self.chart_element

