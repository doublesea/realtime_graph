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


class EChartWidget:
    def __init__(self, signal_types: dict, window_seconds: float = 60.0, df: pd.DataFrame = None, defer_init: bool = False):
        """
        初始化 EChartWidget
        
        Args:
            signal_types: 信号类型配置字典
            window_seconds: 时间窗口大小（秒）
            df: 可选的初始数据 DataFrame，如果提供则立即更新数据
            defer_init: 是否延迟初始化JavaScript（用于tab等延迟渲染场景）
        """
        self.signal_types = signal_types
        self.signal_names = list(signal_types.keys())
        self.num_signals = len(signal_types)
        self.window_seconds = window_seconds
        
        # 创建 RealtimePlot
        self.realtime_plot = RealtimePlot(
            num_signals=self.num_signals, 
            window_seconds=self.window_seconds, 
            signal_types=signal_types)
        
        # 如果有初始数据，则更新
        if df is not None and not df.empty:
            self.realtime_plot.update_data(df)
            self.last_timestamp = df['timestamp'].max()
        else:
            self.last_timestamp = datetime.now()
        
        self.option = self.realtime_plot.get_option()
        self.chart_widget = RealtimeChartWidget(self.option, defer_init=defer_init, realtime_plot=self.realtime_plot)
        
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
    
    def update_signal_types(self, signal_types: dict):
        """
        更新信号类型配置并重新初始化图表
        
        Args:
            signal_types: 新的信号类型配置
        """
        self.signal_types = signal_types
        self.signal_names = list(signal_types.keys())
        self.num_signals = len(signal_types)
        
        # 重新创建 RealtimePlot
        self.realtime_plot = RealtimePlot(
            num_signals=self.num_signals,
            window_seconds=self.window_seconds,
            signal_types=signal_types
        )
        
        # 获取新的配置
        new_option = self.realtime_plot.get_option()
        
        # 更新现有图表（不销毁，避免JavaScript丢失）
        self.chart_widget.update_chart_option(new_option, exclude_tooltip=True)
        self.chart_widget.update_enum_labels(signal_types)
        self.chart_widget.set_realtime_plot(self.realtime_plot)
        
        # 确保显示空数据
        empty_series_data = [
            {
                'data': [],
                'showSymbol': False,
                'symbolSize': 6
            }
            for _ in range(len(signal_types))
        ]
        self.chart_widget.update_series_data(empty_series_data)
    
    def ensure_initialized(self):
        """确保JavaScript已初始化（用于tab切换等延迟渲染场景）"""
        if hasattr(self.chart_widget, 'ensure_initialized'):
            self.chart_widget.ensure_initialized()
    
    def get_element(self):
        """获取图表元素（用于在UI布局中使用）"""
        return self.chart_widget.get_element()
    
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

