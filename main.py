"""
主程序入口
整合 NiceGUI 界面、ECharts 图表和数据生成器
重构版本：初始化绘图控件，周期性调用数据生成并更新曲线
"""
import pandas as pd
from nicegui import ui
from typing import Optional
from data_generator import DataGenerator
from realtime_plot import RealtimePlot
from chart_widget import RealtimeChartWidget

# 全局变量
data_generator: Optional[DataGenerator] = None
realtime_plot: Optional[RealtimePlot] = None
chart_widget: Optional[RealtimeChartWidget] = None
update_timer = None
is_running = False


def create_ui():
    """创建用户界面"""
    global data_generator, realtime_plot, chart_widget, update_timer, is_running
    
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
                max=100,
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
        info_card = ui.html('初始化后显示信号参数...').classes('text-sm')
    
    # 使用提示面板
    with ui.card().classes('w-full p-2').style('background-color: #e3f2fd;'):
        ui.html('''
        <div style="font-size: 12px; color: #1565c0;">
            <b>💡 缩放提示：</b>
            <span style="margin-left:10px;">• 拖动底部滑块或使用 Ctrl+滚轮 缩放时间轴</span>
            <span style="margin-left:10px;">• 放大查看细节时自动显示数据点，缩小查看全局时只显示线条</span>
        </div>
        ''')
    
    # 主体内容（图表区域）
    with ui.column().classes('w-full').style('height: calc(100vh - 280px); overflow: hidden;'):
        # 创建绘图区域（初始化临时图表以获取配置）
        temp_plot = RealtimePlot(num_signals=4, window_seconds=60.0)
        option = temp_plot.get_option()
        
        # 使用图表组件封装类创建图表
        with ui.card().classes('w-full h-full').style('overflow-y: auto; padding: 10px;'):
            # 注意：realtime_plot 将在 init_components 中设置
            chart_widget = RealtimeChartWidget(option, realtime_plot=None)
    
    def init_components():
        """初始化绘图控件和数据生成器"""
        global data_generator, realtime_plot, chart_widget
        
        num_signals = int(signal_count_input.value) if signal_count_input.value is not None else 4
        sample_rate = float(sample_rate_input.value) if sample_rate_input.value is not None else 5.0
        
        # 初始化数据生成器
        data_generator = DataGenerator(num_signals=num_signals, base_sample_rate=sample_rate)
        
        # 构建信号类型配置（使用包含 [] 和 _ 的信号名）
        signal_types = {}
        signal_name_patterns = ['a_[{}]', 'b_c_d[{}]', 'sig_x_[{}]', 'data_y[{}]', 'ch_{}[0]', 'sensor_[{}]', 'val_{}[a]', 'input_x[{}]']
        for i, params in enumerate(data_generator.signal_params):
            # 使用不同的信号名模式
            pattern = signal_name_patterns[i % len(signal_name_patterns)]
            signal_name = pattern.format(i)
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
        # 使用自定义信号名替换默认的 signal_X
        signal_names_list = list(signal_types.keys())
        info_html = '<table style="width:100%; font-size:10px; border-collapse: collapse;">'
        info_html += '<tr style="background-color:#f0f0f0; font-weight:bold;"><th>信号</th><th>类型</th><th>周期(ms)</th><th>采样率(Hz)</th><th>频率</th><th>幅度</th><th>偏移</th><th>枚举值</th></tr>'
        for idx, row in signal_info.iterrows():
            # 根据类型设置背景色
            bg_color = '#fff8e1' if row['type'] == 'enum' else '#ffffff'
            type_label = '<span style="color:#ff6f00;">枚举</span>' if row['type'] == 'enum' else '数值'
            
            # 使用自定义信号名
            custom_signal_name = signal_names_list[idx] if idx < len(signal_names_list) else row["signal"]
            
            # 格式化显示
            freq_str = '-' if row['frequency'] == '-' else f"{row['frequency']:.2f}"
            amp_str = '-' if row['amplitude'] == '-' else f"{row['amplitude']:.2f}"
            offset_str = '-' if row['offset'] == '-' else f"{row['offset']:.2f}"
            enum_str = '-' if row['enum_values'] == '-' else f'<div style="max-width:200px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="{row["enum_values"]}">{row["enum_values"]}</div>'
            
            info_html += f'<tr style="border-bottom:1px solid #ddd; background-color:{bg_color};"><td><b>{custom_signal_name}</b></td><td>{type_label}</td><td>{row["sample_period_ms"]:.0f}</td><td>{row["effective_sample_rate"]:.1f}</td><td>{freq_str}</td><td>{amp_str}</td><td>{offset_str}</td><td>{enum_str}</td></tr>'
        info_html += '</table>'
        info_card.content = info_html
        
        # 更新图表配置（排除 tooltip，避免覆盖自定义 formatter）
        new_option = realtime_plot.get_option()
        chart_widget.update_chart_option(new_option, exclude_tooltip=True)
        
        # 更新枚举标签映射
        chart_widget.update_enum_labels(signal_types)
        
        # 设置 realtime_plot 引用到 chart_widget
        chart_widget.set_realtime_plot(realtime_plot)
        
        # 更新子图顺序控制UI（在侧边栏中）
        def get_is_running():
            return is_running
        
        chart_widget.update_subplot_order_ui(signal_names_list, chart_widget, get_is_running)
    
    def start_plotting():
        """启动实时绘图"""
        global data_generator, realtime_plot, chart_widget, update_timer, is_running
        
        if is_running:
            return
        
        # 初始化组件
        init_components()
        
        is_running = True
        start_btn.disable()
        stop_btn.enable()
        status_label.text = '状态: 运行中'
        
        # 创建列名映射（从默认的 signal_{i+1} 到自定义信号名）
        signal_names_list = list(realtime_plot.signal_types.keys())
        column_rename_map = {f'signal_{i+1}': signal_names_list[i] for i in range(len(signal_names_list))}
        
        def rename_columns(df):
            """重命名 DataFrame 的列名"""
            return df.rename(columns=column_rename_map)
        
        # 生成初始数据（生成几个数据点以便图表有内容显示）
        sample_rate = float(sample_rate_input.value) if sample_rate_input.value is not None else 100.0
        initial_points = int(sample_rate * 0.5)  # 0.5秒的数据点
        initial_batch = data_generator.generate_batch_data(initial_points)
        initial_batch = rename_columns(initial_batch)  # 重命名列
        realtime_plot.append_data(initial_batch)
        
        # 更新图表显示初始数据
        new_option = realtime_plot.get_option()
        series_data = [
            {
                'data': new_option['series'][i]['data'],
                'showSymbol': new_option['series'][i]['showSymbol'],
                'symbolSize': new_option['series'][i]['symbolSize']
            }
            for i in range(len(new_option['series']))
        ]
        chart_widget.update_series_data(series_data)
        
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
            batch_data = rename_columns(batch_data)  # 重命名列
            
            # 将新数据传给绘图控件（内部缓存管理，自动裁剪到时间窗口）
            realtime_plot.append_data(batch_data)
            
            # 更新 series 的关键配置（数据和显示样式）
            new_option = realtime_plot.get_option()
            series_data = [
                {
                    'data': new_option['series'][i]['data'],
                    'showSymbol': new_option['series'][i]['showSymbol'],
                    'symbolSize': new_option['series'][i]['symbolSize']
                }
                for i in range(len(new_option['series']))
            ]
            chart_widget.update_series_data(series_data)
            
            # 更新状态显示（显示当前数据点数量）
            total_data_points = len(realtime_plot._data_buffer) if realtime_plot._data_buffer is not None else 0
            status_label.text = f'状态: 运行中 (生成 {num_points} 点/批, 缓存 {total_data_points} 点)'
        
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
        global data_generator, realtime_plot, chart_widget
        
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
