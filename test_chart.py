"""
简单的图表测试文件
使用静态 DataFrame 数据测试 RealtimeChartWidget
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from nicegui import ui
from realtime_plot import RealtimePlot
from chart_widget import RealtimeChartWidget


def create_test_data():
    """创建测试用的静态 DataFrame 数据"""
    # 生成时间序列（60秒，每100ms一个点，共600个点）
    start_time = datetime.now()
    timestamps = [start_time + timedelta(milliseconds=i*100) for i in range(600)]
    
    # 创建测试数据
    data = {
        'timestamp': timestamps,
        'a_[0]': np.sin(np.linspace(0, 4*np.pi, 600)) * 2 + 1,  # 正弦波
        'b_c_d[1]': np.cos(np.linspace(0, 3*np.pi, 600)) * 1.5 + 2,  # 余弦波
        'sig_x_[2]': np.random.randn(600).cumsum() * 0.1 + 3,  # 随机游走
        'data_y[3]': np.array([0, 1, 2, 3, 0, 1, 2, 3] * 75)  # 枚举信号
    }
    
    return pd.DataFrame(data)

class EChartWidget:
    def __init__(self, df: pd.DataFrame, signal_types: dict, window_seconds: float = 60.0):
        self.signal_types = signal_types
        self.signal_names = list(signal_types.keys())
        self.num_signals = len(signal_types)
        self.window_seconds = window_seconds
        self.last_timestamp = df['timestamp'].max()
        
        self.realtime_plot = RealtimePlot(
            num_signals=self.num_signals, 
            window_seconds=self.window_seconds, 
            signal_types=signal_types)
        self.realtime_plot.update_data(df)
        self.option = self.realtime_plot.get_option()
        self.chart_widget = RealtimeChartWidget(self.option)
        
        self.chart_widget.update_enum_labels(signal_types)
    
    def get_option(self):
        """获取当前图表配置"""
        return self.realtime_plot.get_option()
    
    def append_data(self, df: pd.DataFrame):
        """添加新数据到图表（增量添加）"""
        self.realtime_plot.append_data(df)
        if not df.empty and 'timestamp' in df.columns:
            self.last_timestamp = df['timestamp'].max()
        
        # 更新图表显示
        self._update_chart_display()
    
    def update_data(self, df: pd.DataFrame):
        """
        更新数据（完全替换）
        
        Args:
            df: 新的 DataFrame 数据，必须包含 'timestamp' 列和所有信号列
        """
        self.realtime_plot.update_data(df)
        if not df.empty and 'timestamp' in df.columns:
            self.last_timestamp = df['timestamp'].max()
        
        # 更新图表显示
        self._update_chart_display()
    
    def clear_data(self):
        """清空所有数据"""
        self.realtime_plot.clear_data()
        self.last_timestamp = datetime.now()
        
        # 更新图表显示（清空）
        self._update_chart_display()
    
    def update_config(self, window_seconds: float = None, signal_types: dict = None):
        """
        更新配置并重新初始化图表
        
        Args:
            window_seconds: 新的时间窗口大小（秒），None 表示不更改
            signal_types: 新的信号类型配置，None 表示不更改
        """
        # 保存当前数据
        current_data = self.realtime_plot.get_buffered_data()
        
        # 更新配置
        if window_seconds is not None:
            self.window_seconds = window_seconds
        
        if signal_types is not None:
            self.signal_types = signal_types
            self.signal_names = list(signal_types.keys())
            self.num_signals = len(signal_types)
        
        # 重新初始化 RealtimePlot
        self.realtime_plot = RealtimePlot(
            num_signals=self.num_signals,
            window_seconds=self.window_seconds,
            signal_types=self.signal_types
        )
        
        # 恢复数据
        if current_data is not None and not current_data.empty:
            self.realtime_plot.update_data(current_data)
        
        # 更新图表配置
        new_option = self.realtime_plot.get_option()
        self.chart_widget.update_chart_option(new_option, exclude_tooltip=True)
        self.chart_widget.update_enum_labels(self.signal_types)
        
        # 更新图表显示
        self._update_chart_display()
    
    def get_buffered_data(self):
        """
        获取当前缓存的数据
        
        Returns:
            DataFrame 或 None
        """
        return self.realtime_plot.get_buffered_data()
    
    def _update_chart_display(self):
        """内部方法：更新图表显示"""
        new_option = self.realtime_plot.get_option()
        series_data = [
            {
                'data': new_option['series'][i]['data'],
                'showSymbol': new_option['series'][i]['showSymbol'],
                'symbolSize': new_option['series'][i]['symbolSize']
            }
            for i in range(len(new_option['series']))
        ]
        self.chart_widget.update_series_data(series_data)
    
    def generate_new_batch(self, num_points=10):
        """
        生成一批新数据（用于测试）
        
        Args:
            num_points: 生成的数据点数量
            
        Returns:
            DataFrame: 新生成的数据
        """
        # 从上次的时间戳继续
        timestamps = [self.last_timestamp + timedelta(milliseconds=i*100) for i in range(1, num_points+1)]
        
        # 生成新数据（继续之前的模式）
        t = np.linspace(0, num_points*0.1, num_points)
        data = {
            'timestamp': timestamps,
            self.signal_names[0]: np.sin(t * 4 * np.pi) * 2 + 1 + np.random.randn(num_points) * 0.1,
            self.signal_names[1]: np.cos(t * 3 * np.pi) * 1.5 + 2 + np.random.randn(num_points) * 0.1,
            self.signal_names[2]: np.random.randn(num_points).cumsum() * 0.05 + 3,
            self.signal_names[3]: np.random.choice([0, 1, 2, 3], size=num_points)
        }
        
        return pd.DataFrame(data)

@ui.page('/')
def test_page():
    """测试页面"""
    ui.page_title('Chart Widget Test')
    
    # 标题
    with ui.header(elevated=True).style('background-color: #1976d2;'):
        ui.label('RealtimeChartWidget 测试').style('color: white; font-size: 20px; font-weight: bold;')
    
    # 说明
    with ui.card().classes('w-full p-4').style('background-color: #e3f2fd;'):
        ui.label('📊 测试说明').classes('text-h6 mb-2')
        ui.html('''
        <div style="font-size: 14px;">
            <p>这是一个简单的测试，展示如何使用静态数据绘制图表：</p>
            <ul>
                <li>4个测试信号：a_[0], b_c_d[1], sig_x_[2], data_y[3]</li>
                <li>3个数值信号 + 1个枚举信号</li>
                <li>初始时间跨度：60秒，共600个数据点</li>
                <li>点击"开始添加数据"按钮，每秒添加10个新数据点，共添加10次</li>
            </ul>
        </div>
        ''', sanitize=False)
    
    # 创建测试数据
    df = create_test_data()
    
    # 定义信号类型
    signal_types = {
        'a_[0]': {'type': 'numeric'},
        'b_c_d[1]': {'type': 'numeric'},
        'sig_x_[2]': {'type': 'numeric'},
        'data_y[3]': {
            'type': 'enum',
            'enum_labels': {
                0: 'State 0 (OFF)',
                1: 'State 1 (IDLE)',
                2: 'State 2 (RUNNING)',
                3: 'State 3 (ERROR)'
            }
        }
    }
    
    # 显示数据统计
    with ui.card().classes('w-full p-4'):
        ui.label('📈 数据统计与控制').classes('text-h6 mb-2')
        with ui.row().classes('gap-4 items-center'):
            data_points_label = ui.label(f'数据点数：{len(df)}')
            ui.label(f'信号数量：{len(signal_types)}')
            time_span_label = ui.label(f'时间跨度：{(df["timestamp"].max() - df["timestamp"].min()).total_seconds():.1f} 秒')
        
        with ui.row().classes('gap-2 mt-4 items-center'):
            start_btn = ui.button('开始添加数据', icon='play_arrow').props('color=green')
            stop_btn = ui.button('停止', icon='stop').props('color=red')
            stop_btn.disable()
            status_label = ui.label('状态: 准备就绪')
            counter_label = ui.label('添加次数: 0/10').style('font-weight: bold; color: #1976d2;')
        
        # 新增接口测试按钮
        with ui.row().classes('gap-2 mt-2 items-center'):
            ui.label('接口测试:').style('font-weight: bold;')
            clear_btn = ui.button('清空数据', icon='delete').props('color=orange outline')
            reset_btn = ui.button('重置初始数据', icon='refresh').props('color=blue outline')
            config_btn = ui.button('修改窗口(120秒)', icon='settings').props('color=purple outline')
    
    # 创建图表
    with ui.card().classes('w-full').style('overflow-y: scroll; max-height: 75vh; padding: 10px;'):
        echart_widget = EChartWidget(df, signal_types)
    
    # 定时器和计数器变量
    timer = None
    counter = [0]  # 使用列表以便在闭包中修改
    
    def add_data_once():
        """每次添加一批数据"""
        if counter[0] >= 10:
            # 达到10次，停止
            if timer is not None:
                timer.deactivate()
            start_btn.enable()
            stop_btn.disable()
            status_label.text = '状态: 已完成（添加了10批数据）'
            counter_label.style('color: #2e7d32;')  # 绿色
            return
        
        # 生成并添加新数据
        new_batch = echart_widget.generate_new_batch(num_points=10)
        echart_widget.append_data(new_batch)
        
        # 更新计数器
        counter[0] += 1
        counter_label.text = f'添加次数: {counter[0]}/10'
        status_label.text = f'状态: 正在添加... ({counter[0]}/10)'
        
        # 更新统计信息
        total_points = len(echart_widget.realtime_plot._data_buffer) if echart_widget.realtime_plot._data_buffer is not None else 0
        data_points_label.text = f'数据点数：{total_points}'
        if echart_widget.realtime_plot._data_buffer is not None:
            df_current = echart_widget.realtime_plot._data_buffer
            time_span = (df_current['timestamp'].max() - df_current['timestamp'].min()).total_seconds()
            time_span_label.text = f'时间跨度：{time_span:.1f} 秒'
    
    def start_adding():
        """开始添加数据"""
        nonlocal timer
        counter[0] = 0
        start_btn.disable()
        stop_btn.enable()
        status_label.text = '状态: 正在添加...'
        counter_label.text = '添加次数: 0/10'
        counter_label.style('color: #1976d2;')
        
        # 启动定时器，每秒调用一次
        timer = ui.timer(1.0, add_data_once)
    
    def stop_adding():
        """停止添加数据"""
        nonlocal timer
        if timer is not None:
            timer.deactivate()
        start_btn.enable()
        stop_btn.disable()
        status_label.text = f'状态: 已停止（已添加{counter[0]}批数据）'
    
    def clear_data():
        """清空数据"""
        echart_widget.clear_data()
        data_points_label.text = '数据点数：0'
        time_span_label.text = '时间跨度：0.0 秒'
        status_label.text = '状态: 数据已清空'
        counter[0] = 0
        counter_label.text = '添加次数: 0/10'
        ui.notify('数据已清空', type='info')
    
    def reset_data():
        """重置到初始数据"""
        initial_df = create_test_data()
        echart_widget.update_data(initial_df)
        data_points_label.text = f'数据点数：{len(initial_df)}'
        time_span = (initial_df['timestamp'].max() - initial_df['timestamp'].min()).total_seconds()
        time_span_label.text = f'时间跨度：{time_span:.1f} 秒'
        status_label.text = '状态: 已重置到初始数据'
        counter[0] = 0
        counter_label.text = '添加次数: 0/10'
        ui.notify('已重置到初始数据（600点）', type='positive')
    
    def update_config():
        """修改窗口配置"""
        echart_widget.update_config(window_seconds=120.0)
        status_label.text = '状态: 已修改窗口为120秒'
        ui.notify('时间窗口已修改为 120 秒', type='positive')
        # 更新统计信息
        buffered_data = echart_widget.get_buffered_data()
        if buffered_data is not None and not buffered_data.empty:
            data_points_label.text = f'数据点数：{len(buffered_data)}'
            time_span = (buffered_data['timestamp'].max() - buffered_data['timestamp'].min()).total_seconds()
            time_span_label.text = f'时间跨度：{time_span:.1f} 秒'
    
    # 绑定按钮事件
    start_btn.on_click(start_adding)
    stop_btn.on_click(stop_adding)
    clear_btn.on_click(clear_data)
    reset_btn.on_click(reset_data)
    config_btn.on_click(update_config)
    
    # 使用提示
    with ui.card().classes('w-full p-2').style('background-color: #fff3e0;'):
        ui.html('''
        <div style="font-size: 12px; color: #e65100;">
            <b>💡 功能说明：</b><br>
            <div style="margin-top: 5px;">
                <b>数据操作：</b>
                <span style="margin-left:10px;">• <b>开始添加数据</b>: 每秒自动添加10个数据点，共10次</span><br>
                <span style="margin-left:10px;">• <b>清空数据</b>: 清空图表中的所有数据</span><br>
                <span style="margin-left:10px;">• <b>重置初始数据</b>: 恢复到初始的600个数据点</span><br>
                <span style="margin-left:10px;">• <b>修改窗口</b>: 将时间窗口从60秒修改为120秒</span><br>
            </div>
            <div style="margin-top: 5px;">
                <b>图表交互：</b>
                <span style="margin-left:10px;">• 拖动底部滑块或使用 Ctrl+滚轮 缩放时间轴</span><br>
                <span style="margin-left:10px;">• 鼠标悬停查看数据点详情</span>
            </div>
        </div>
        ''', sanitize=False)


# 启动应用
if __name__ in {'__main__', '__mp_main__'}:
    ui.run(port=8081, title='Chart Widget Test')

