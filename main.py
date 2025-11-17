"""
主程序入口
整合 NiceGUI 界面、ECharts 图表和数据生成器
重构版本：初始化绘图控件，周期性调用数据生成并更新曲线
"""
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
    update_rate_input = None
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
            
            ui.label('更新频率 (ms):')
            update_rate_input = ui.number(
                label='', 
                value=200, 
                min=50, 
                max=1000,
                precision=0
            ).classes('w-24')
            
            ui.label('基础采样率 (Hz):')
            sample_rate_input = ui.number(
                label='', 
                value=5.0, 
                min=0.1, 
                max=100.0,
                precision=1
            ).classes('w-24')
    
    # 信号信息面板
    with ui.card().classes('w-full p-4').style('max-height: 200px; overflow-y: auto;'):
        ui.label('信号参数信息').classes('text-h6 mb-2')
        info_card = ui.html('初始化后显示信号参数...', sanitize=False).classes('text-sm')
    
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
        
        # 设置 tooltip formatter 和自定义指示线
        ui.add_body_html(f'''
        <script>
        (function setupTooltip() {{
            let attempts = 0;
            const maxAttempts = 20;
            let customLine = null;
            
            const interval = setInterval(function() {{
                const el = getElement({plot_element.id});
                if (el && el.chart) {{
                    el.chart.setOption({{
                        tooltip: {{
                            formatter: function(params) {{
                                if (!params || params.length === 0) return '';
                                const date = new Date(params[0].value[0]);
                                const h = String(date.getHours()).padStart(2, '0');
                                const m = String(date.getMinutes()).padStart(2, '0');
                                const s = String(date.getSeconds()).padStart(2, '0');
                                const ms = String(date.getMilliseconds()).padStart(3, '0');
                                const time = h + ':' + m + ':' + s + '.' + ms;
                                
                                let html = '<div style="font-weight:bold;margin-bottom:8px;border-bottom:1px solid #666;padding-bottom:5px;">Time: ' + time + '</div>';
                                
                                for (let i = 0; i < params.length; i++) {{
                                    const p = params[i];
                                    const v = p.value[1];
                                    html += '<div style="margin:3px 0">';
                                    html += '<span style="display:inline-block;width:10px;height:10px;background-color:' + p.color + ';border-radius:50%;margin-right:8px"></span>';
                                    html += '<span style="display:inline-block;width:80px">' + p.seriesName + '</span>';
                                    html += '<span style="font-weight:bold">' + (v != null ? Number(v).toFixed(3) : 'N/A') + '</span>';
                                    html += '</div>';
                                }}
                                
                                return html;
                            }}
                        }}
                    }});
                    
                    const chartContainer = el.querySelector('div');
                    if (chartContainer && !customLine) {{
                        customLine = document.createElement('div');
                        customLine.style.cssText = 'position: absolute; top: 0; bottom: 0; width: 1px; background-color: rgba(102, 102, 102, 0.6); pointer-events: none; display: none; z-index: 999;';
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
        
        # 初始化绘图控件
        realtime_plot = RealtimePlot(num_signals=num_signals, window_seconds=60.0)
        
        # 更新信号信息显示
        signal_info = data_generator.get_signal_info()
        info_html = '<table style="width:100%; font-size:12px; border-collapse: collapse;">'
        info_html += '<tr style="background-color:#f0f0f0; font-weight:bold;"><th>信号</th><th>频率(Hz)</th><th>幅度</th><th>偏移</th><th>周期倍数</th><th>有效采样率(Hz)</th></tr>'
        for _, row in signal_info.iterrows():
            info_html += f'<tr style="border-bottom:1px solid #ddd;"><td>{row["signal"]}</td><td>{row["frequency"]:.2f}</td><td>{row["amplitude"]:.2f}</td><td>{row["offset"]:.2f}</td><td>{row["period_multiplier"]}</td><td>{row["effective_sample_rate"]:.2f}</td></tr>'
        info_html += '</table>'
        info_card.content = info_html
        
        # 更新图表配置
        new_option = realtime_plot.get_option()
        new_height = new_option.get('height', 1000)
        
        for key, value in new_option.items():
            plot_element.options[key] = value
        
        plot_element._props['style'] = f'height: {new_height}px; width: 100%; min-height: {new_height}px;'
        plot_element.update()
    
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
        
        # 获取更新频率（毫秒转秒）
        update_interval = float(update_rate_input.value) / 1000.0
        
        def update_plot():
            """
            周期性调用数据生成，并将生成数据传给绘图控件更新曲线
            使用 append_data 接口实现增量更新
            """
            if not is_running or data_generator is None or realtime_plot is None:
                return
            
            # 调用数据生成器生成新数据
            new_data = data_generator.generate_next_data()
            
            # 将新数据传给绘图控件（使用 append_data 接口）
            realtime_plot.append_data(new_data)
            
            # 更新图表显示（只更新 series 数据，性能更好）
            new_option = realtime_plot.get_option()
            for i in range(len(new_option['series'])):
                plot_element.options['series'][i]['data'] = new_option['series'][i]['data']
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
