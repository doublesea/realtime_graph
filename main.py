"""
主程序入口
整合 NiceGUI 界面、ECharts 图表和数据生成器
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
    
    # 创建 UI 元素
    header = ui.header(elevated=True).style('background-color: #1976d2').classes('items-center justify-between')
    with header:
        ui.label('实时多信号绘图系统').style('color: white; font-size: 20px; font-weight: bold')
        row = ui.row().classes('items-center gap-4')
        with row:
            status_label = ui.label('状态: 未启动').style('color: white')
            start_btn = ui.button('启动').props('color=green')
            stop_btn = ui.button('停止').props('color=red')
            stop_btn.disable()
            reset_btn = ui.button('重置').props('color=orange')
    
    with ui.card().classes('w-full p-4'):
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
            
            ui.label('采样频率 (Hz):')
            sample_rate_input = ui.number(
                label='', 
                value=5.0, 
                min=0.1, 
                max=100.0,
                precision=1
            ).classes('w-24')
    
    # 创建绘图区域（需要先初始化一个空的 option）
    # 先创建一个临时的 RealtimePlot 对象来获取初始 option
    # 使用默认值 4 个信号来初始化
    temp_plot = RealtimePlot(num_signals=4, window_seconds=60.0)
    option = temp_plot.get_option()
    chart_height = option.get('height', 1000)  # 获取图表总高度
    
    with ui.card().classes('w-full').style('overflow-y: scroll; max-height: 85vh; padding: 10px;'):
        plot_element = ui.echart(option).style(f'height: {chart_height}px; width: 100%; min-height: {chart_height}px;')
        
        # 当客户端连接后，设置自定义 tooltip formatter
        async def setup_tooltip():
            await ui.context.client.connected()
            await ui.run_javascript(f'''
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
                                    html += '<span style="font-weight:bold">' + (v != null ? v.toFixed(3) : 'N/A') + '</span>';
                                    html += '</div>';
                                }}
                                return html;
                            }}
                        }}
                    }});
                }}
            ''')
        
        ui.timer(0.5, setup_tooltip, once=True)
    
    # 初始化数据生成器和绘图对象
    def init_components():
        global data_generator, realtime_plot
        num_signals = int(signal_count_input.value) if signal_count_input.value is not None else 4
        sample_rate = float(sample_rate_input.value) if sample_rate_input.value is not None else 5.0
        
        data_generator = DataGenerator(num_signals=num_signals, sample_rate=sample_rate)
        realtime_plot = RealtimePlot(num_signals=num_signals, window_seconds=60.0)
        
        # 初始化图表显示
        new_option = realtime_plot.get_option()
        new_height = new_option.get('height', 1000)
        
        # 更新图表的所有配置
        for key, value in new_option.items():
            plot_element.options[key] = value
        
        # 更新图表高度 - 确保容器足够大以显示所有子图
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
            """更新绘图数据"""
            if not is_running or data_generator is None or realtime_plot is None:
                return
            
            # 生成新数据
            data_generator.generate_next_data()
            
            # 获取最近1分钟的数据
            recent_df = data_generator.get_recent_data(window_seconds=60.0)
            
            # 更新图表
            if not recent_df.empty:
                realtime_plot.update_data(recent_df)
                # 更新图表显示：只更新 series 数据，性能更好
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
        
        # 重新初始化组件
        init_components()
        status_label.text = '状态: 已重置'
    
    # 现在绑定事件处理器
    start_btn.on_click(start_plotting)
    stop_btn.on_click(stop_plotting)
    reset_btn.on_click(reset_plotting)
    
    # 初始化界面
    init_components()


# 启动应用
if __name__ in {'__main__', '__mp_main__'}:
    create_ui()
    ui.run(port=8080, title='实时多信号绘图系统')

