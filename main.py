"""
主程序入口
整合 NiceGUI 界面、ECharts 图表和数据生成器
重构版本：初始化绘图控件，周期性调用数据生成并更新曲线
"""
import json
import pandas as pd
from nicegui import ui
from typing import Optional
from data_generator import DataGenerator
from realtime_plot import RealtimePlot

# 全局变量
data_generator: Optional[DataGenerator] = None
realtime_plot: Optional[RealtimePlot] = None
plot_element = None
update_timer = None
is_running = False


def create_ui():
    """创建用户界面"""
    global data_generator, realtime_plot, plot_element, update_timer, is_running
    
    # 页面标题
    ui.page_title('实时多信号绘图系统')
    
    # 先定义占位变量
    status_label = None
    start_btn = None
    stop_btn = None
    reset_btn = None
    signal_count_input = None
    sample_rate_input = None
    info_card = None
    
    # 创建 UI 元素
    header = ui.header(elevated=True).style('background-color: #1976d2').classes('items-center justify-between')
    with header:
        ui.label('实时多信号绘图系统 (重构版)').style('color: white; font-size: 20px; font-weight: bold')
        row = ui.row().classes('items-center gap-4')
        with row:
            status_label = ui.label('状态: 未启动').style('color: white')
            start_btn = ui.button('启动', icon='play_arrow').props('color=green')
            stop_btn = ui.button('停止', icon='stop').props('color=red')
            stop_btn.disable()
            reset_btn = ui.button('重置', icon='refresh').props('color=orange')
    
    # 控制面板
    with ui.card().classes('w-full p-4'):
        ui.label('控制面板').classes('text-h6 mb-2')
        with ui.row().classes('items-center gap-4'):
            ui.label('信号数量:')
            signal_count_input = ui.number(
                label='', 
                value=4, 
                min=1, 
                max=20,
                precision=0
            ).classes('w-24')
            
            ui.label('更新频率:')
            ui.label('500 ms (固定)').classes('font-bold text-blue-600')
            
            ui.label('基础采样率 (Hz):')
            sample_rate_input = ui.number(
                label='', 
                value=100.0,  # 默认100Hz (10ms基础周期)
                min=0.1, 
                max=1000.0,
                precision=1
            ).classes('w-24')
    
    # 信号信息面板
    with ui.card().classes('w-full p-4').style('max-height: 200px; overflow-y: auto;'):
        ui.label('信号参数信息').classes('text-h6 mb-2')
        info_card = ui.html('初始化后显示信号参数...', sanitize=False).classes('text-sm')
    
    # 使用提示面板
    with ui.card().classes('w-full p-2').style('background-color: #e3f2fd;'):
        ui.html('''
        <div style="font-size: 12px; color: #1565c0;">
            <b>💡 缩放提示：</b>
            <span style="margin-left:10px;">• 拖动底部滑块或使用 Ctrl+滚轮 缩放时间轴</span>
            <span style="margin-left:10px;">• 放大查看细节时自动显示数据点，缩小查看全局时只显示线条</span>
        </div>
        ''', sanitize=False)
    
    # 创建绘图区域
    temp_plot = RealtimePlot(num_signals=4, window_seconds=60.0)
    option = temp_plot.get_option()
    chart_height = option.get('height', 1000)
    
    # 添加自定义 CSS 样式
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
    
    with ui.card().classes('w-full').style('overflow-y: scroll; max-height: 85vh; padding: 10px;'):
        plot_element = ui.echart(option).style(f'height: {chart_height}px; width: 100%; min-height: {chart_height}px;')
        
        # 初始化枚举标签映射
        ui.add_body_html(f'''
        <script>
        window.enumLabelsMap = {{}};
        
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
                    const signalIndex = parseInt(p.seriesName.replace('Signal ', ''));
                    
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
                        name: p.seriesName,
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
                const el = getElement({plot_element.id});
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
                        const chartContainer = el.chart.getDom().parentElement;
                        
                        customLine = document.createElement('div');
                        customLine.style.cssText = 'position: absolute; top: 0; bottom: 0; width: 2px; background-color: rgba(102, 102, 102, 0.8); pointer-events: none; display: none; z-index: 9999;';
                        customLine.id = 'custom-indicator-line';
                        
                        chartContainer.style.position = 'relative';
                        chartContainer.appendChild(customLine);
                        
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
                        // 使用第一个dataZoom的范围（inside和slider是同步的）
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
                                // 密集：不显示点
                                showSymbol = false;
                                symbolSize = 4;
                            }} else if (visiblePointCount > 100) {{
                                // 中等：显示小点
                                showSymbol = true;
                                symbolSize = 4;
                            }} else if (visiblePointCount > 30) {{
                                // 适中：显示中等点
                                showSymbol = true;
                                symbolSize = 5;
                            }} else {{
                                // 稀疏：显示大点
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
    
    def init_components():
        """初始化绘图控件和数据生成器"""
        global data_generator, realtime_plot
        
        num_signals = int(signal_count_input.value) if signal_count_input.value is not None else 4
        sample_rate = float(sample_rate_input.value) if sample_rate_input.value is not None else 5.0
        
        # 初始化数据生成器
        data_generator = DataGenerator(num_signals=num_signals, base_sample_rate=sample_rate)
        
        # 构建信号类型配置
        signal_types = {}
        for i, params in enumerate(data_generator.signal_params):
            signal_name = f'signal_{i+1}'
            if params['type'] == 'enum':
                signal_types[signal_name] = {
                    'type': 'enum',
                    'enum_labels': params['enum_labels']
                }
            else:
                signal_types[signal_name] = {'type': 'numeric'}
        
        # 初始化绘图控件
        realtime_plot = RealtimePlot(num_signals=num_signals, window_seconds=60.0, signal_types=signal_types)
        
        # 更新信号信息显示
        signal_info = data_generator.get_signal_info()
        info_html = '<table style="width:100%; font-size:10px; border-collapse: collapse;">'
        info_html += '<tr style="background-color:#f0f0f0; font-weight:bold;"><th>信号</th><th>类型</th><th>周期(ms)</th><th>采样率(Hz)</th><th>频率</th><th>幅度</th><th>偏移</th><th>枚举值</th></tr>'
        for _, row in signal_info.iterrows():
            # 根据类型设置背景色
            bg_color = '#fff8e1' if row['type'] == 'enum' else '#ffffff'
            type_label = '<span style="color:#ff6f00;">枚举</span>' if row['type'] == 'enum' else '数值'
            
            # 格式化显示
            freq_str = '-' if row['frequency'] == '-' else f"{row['frequency']:.2f}"
            amp_str = '-' if row['amplitude'] == '-' else f"{row['amplitude']:.2f}"
            offset_str = '-' if row['offset'] == '-' else f"{row['offset']:.2f}"
            enum_str = '-' if row['enum_values'] == '-' else f'<div style="max-width:200px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="{row["enum_values"]}">{row["enum_values"]}</div>'
            
            info_html += f'<tr style="border-bottom:1px solid #ddd; background-color:{bg_color};"><td><b>{row["signal"]}</b></td><td>{type_label}</td><td>{row["sample_period_ms"]:.0f}</td><td>{row["effective_sample_rate"]:.1f}</td><td>{freq_str}</td><td>{amp_str}</td><td>{offset_str}</td><td>{enum_str}</td></tr>'
        info_html += '</table>'
        info_card.content = info_html
        
        # 更新图表配置（排除 tooltip，避免覆盖自定义 formatter）
        new_option = realtime_plot.get_option()
        new_height = new_option.get('height', 1000)
        
        for key, value in new_option.items():
            if key != 'tooltip':  # 保留 JavaScript 中自定义的 tooltip formatter
                plot_element.options[key] = value
        
        plot_element._props['style'] = f'height: {new_height}px; width: 100%; min-height: {new_height}px;'
        plot_element.update()
        
        # 更新 JavaScript 中的枚举标签映射
        enum_labels_json = {}
        for signal_name, config in signal_types.items():
            if config['type'] == 'enum':
                signal_index = int(signal_name.split('_')[1])
                # 将整数键转换为字符串键以便 JSON 序列化
                enum_labels_json[str(signal_index)] = {str(k): v for k, v in config['enum_labels'].items()}
        
        # 更新枚举标签映射到全局变量
        enum_labels_js = json.dumps(enum_labels_json)
        ui.add_body_html(f'''
        <script>
            (function() {{{{
                window.enumLabelsMap = {enum_labels_js};
            }}}})();
        </script>
        ''')
    
    def start_plotting():
        """启动实时绘图"""
        global data_generator, realtime_plot, plot_element, update_timer, is_running
        
        if is_running:
            return
        
        # 初始化组件
        init_components()
        
        is_running = True
        start_btn.disable()
        stop_btn.enable()
        status_label.text = '状态: 运行中'
        
        # 生成初始数据（生成几个数据点以便图表有内容显示）
        sample_rate = float(sample_rate_input.value) if sample_rate_input.value is not None else 100.0
        initial_points = int(sample_rate * 0.5)  # 0.5秒的数据点
        initial_batch = data_generator.generate_batch_data(initial_points)
        realtime_plot.append_data(initial_batch)
        
        # 更新图表显示初始数据
        new_option = realtime_plot.get_option()
        for i in range(len(new_option['series'])):
            plot_element.options['series'][i]['data'] = new_option['series'][i]['data']
            plot_element.options['series'][i]['showSymbol'] = new_option['series'][i]['showSymbol']
            plot_element.options['series'][i]['symbolSize'] = new_option['series'][i]['symbolSize']
        plot_element.update()
        
        # 固定更新频率：每0.5秒更新一次
        update_interval = 0.5  # 秒
        
        def update_plot():
            """
            周期性调用数据生成，并将生成数据传给绘图控件更新曲线
            每次生成0.5秒的数据批次，按照规定的采样率
            """
            if not is_running or data_generator is None or realtime_plot is None:
                return
            
            # 计算0.5秒内应该生成多少个基础时间点
            sample_rate = data_generator.base_sample_rate
            num_points = int(sample_rate * update_interval)
            
            # 批量生成0.5秒的数据
            batch_data = data_generator.generate_batch_data(num_points)
            
            # 将新数据传给绘图控件（内部缓存管理，自动裁剪到时间窗口）
            realtime_plot.append_data(batch_data)
            
            # 更新 series 的关键配置（数据和显示样式）
            new_option = realtime_plot.get_option()
            for i in range(len(new_option['series'])):
                # 更新数据和根据密度自动调整的显示配置
                plot_element.options['series'][i]['data'] = new_option['series'][i]['data']
                plot_element.options['series'][i]['showSymbol'] = new_option['series'][i]['showSymbol']
                plot_element.options['series'][i]['symbolSize'] = new_option['series'][i]['symbolSize']
            
            # 更新状态显示（显示当前数据点数量）
            total_data_points = len(realtime_plot._data_buffer) if realtime_plot._data_buffer is not None else 0
            status_label.text = f'状态: 运行中 (生成 {num_points} 点/批, 缓存 {total_data_points} 点)'
            
            # 使用 update() 更新图表
            plot_element.update()
        
        # 启动定时器
        update_timer = ui.timer(update_interval, update_plot)
    
    def stop_plotting():
        """停止实时绘图"""
        global update_timer, is_running
        
        if not is_running:
            return
        
        is_running = False
        if update_timer:
            update_timer.deactivate()
            update_timer = None
        
        start_btn.enable()
        stop_btn.disable()
        status_label.text = '状态: 已停止'
    
    def reset_plotting():
        """重置绘图"""
        global data_generator, realtime_plot, plot_element
        
        stop_plotting()
        
        if data_generator:
            data_generator.reset()
        
        if realtime_plot:
            realtime_plot.clear_data()
        
        # 重新初始化组件
        init_components()
        status_label.text = '状态: 已重置'
    
    # 绑定事件处理器
    start_btn.on_click(start_plotting)
    stop_btn.on_click(stop_plotting)
    reset_btn.on_click(reset_plotting)
    
    # 初始化界面
    init_components()


# 启动应用
if __name__ in {'__main__', '__mp_main__'}:
    create_ui()
    ui.run(port=8080, title='实时多信号绘图系统')
