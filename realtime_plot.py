"""
实时绘图核心逻辑
使用 ECharts 创建多子图布局，实现实时数据可视化
"""
import pandas as pd
from datetime import datetime


class RealtimePlot:
    """实时多信号绘图类（ECharts 版本）"""
    
    def __init__(self, num_signals: int = 20, window_seconds: float = 60.0):
        """
        初始化实时绘图
        
        Args:
            num_signals: 信号数量（最多20个）
            window_seconds: 数据窗口大小（秒）
        """
        self.num_signals = min(num_signals, 20)
        self.window_seconds = window_seconds
        self.option = self._create_option()
    
    def _create_option(self):
        """创建 ECharts 配置选项"""
        # 计算每个子图的位置和大小
        # 动态计算高度：信号少时充满页面，信号多时使用最小高度
        min_chart_height = 85  # 最小子图高度 85 像素
        chart_spacing = 8  # 子图之间的间距
        available_height = 800  # 假设可用页面高度约 800px（85vh 的近似值）
        top_bottom_padding = 50  # 顶部和底部的总padding
        
        # 计算理想的子图高度（充满页面）
        ideal_height = (available_height - top_bottom_padding - chart_spacing * (self.num_signals + 1)) / self.num_signals
        
        # 使用理想高度和最小高度中的较大值
        chart_height_per_signal = max(min_chart_height, int(ideal_height))
        
        # 如果子图太多，使用最小高度
        if self.num_signals > 10:
            chart_height_per_signal = min_chart_height
        
        total_height = chart_height_per_signal * self.num_signals + chart_spacing * (self.num_signals + 1) + top_bottom_padding
        
        grids = []
        x_axes = []
        y_axes = []
        series = []
        titles = []  # 添加标题数组
        
        for i in range(self.num_signals):
            # 配置 grid 位置（垂直排列，使用像素定位）
            top = chart_spacing + i * (chart_height_per_signal + chart_spacing) + 30
            
            # 根据子图高度调整标题和grid的显示
            title_offset = 22 if chart_height_per_signal >= 100 else 18
            grid_height = chart_height_per_signal - 25 if chart_height_per_signal >= 100 else chart_height_per_signal - 20
            
            # 配置标题（显示在每个子图的左上角）
            titles.append({
                'text': f'Signal {i+1}',
                'left': 80,  # 与 grid 的 left 对齐
                'top': top - title_offset,  # 在 grid 上方
                'textStyle': {
                    'fontSize': 13,
                    'fontWeight': 'bold',
                    'color': '#333'
                }
            })
            grids.append({
                'left': 70,
                'right': 70,
                'top': top,
                'height': grid_height,  # 根据总高度动态调整
                'containLabel': True
            })
            
            # 配置 x 轴（共享时间轴，只在最后一个显示）
            is_last = (i == self.num_signals - 1)
            x_axes.append({
                'type': 'time',
                'gridIndex': i,
                'show': is_last,  # 只有最后一个显示
                'position': 'bottom',
                'splitLine': {'show': False},
                'axisLine': {'show': is_last, 'lineStyle': {'color': '#999'}},
                'axisTick': {'show': is_last},
                'axisLabel': {
                    'show': is_last,
                    'formatter': '{HH}:{mm}:{ss}.{SSS}',  # 显示时分秒和毫秒
                    'fontSize': 10,
                    'rotate': 0
                },
                'axisPointer': {
                    'show': True,
                    'type': 'line',
                    'lineStyle': {
                        'color': '#999',
                        'width': 2,
                        'type': 'solid'
                    },
                    'label': {
                        'show': False  # 禁用 axis pointer label，避免在每个轴上显示时间
                    }
                }
            })
            
            # 配置 y 轴（不再显示 name，因为已经在左上角有标题了）
            y_axes.append({
                'type': 'value',
                'gridIndex': i,
                'splitLine': {'show': True, 'lineStyle': {'type': 'dashed', 'color': '#e0e0e0'}},
                'scale': True,  # 自动缩放以适应数据
                'axisLabel': {
                    'fontSize': 9
                },
                'splitNumber': 3  # 减少刻度线数量，节省空间
            })
            
            # 配置系列（折线图）
            series.append({
                'type': 'line',
                'xAxisIndex': i,
                'yAxisIndex': i,
                'data': [],
                'name': f'Signal {i+1}',
                'smooth': False,
                'symbol': 'none',
                'lineStyle': {'width': 2},  # 线条稍微粗一点
                'animation': False,  # 关闭动画以提高性能
                'large': True,  # 启用大数据量优化
                'largeThreshold': 500,  # 超过500个点启用优化
                'sampling': 'lttb'  # 使用 LTTB 采样算法，保持曲线形状
            })
        
        return {
            'grid': grids,
            'xAxis': x_axes,
            'yAxis': y_axes,
            'series': series,
            'title': titles,  # 添加标题数组，显示在每个子图左上角
            # 设置图表的总高度
            'height': total_height,
            'axisPointer': {
                'link': [{'xAxisIndex': 'all'}],  # 链接所有 x 轴
                'label': {
                    'backgroundColor': '#777'
                }
            },
            'tooltip': {
                'show': True,
                'trigger': 'axis',
                'axisPointer': {
                    'type': 'cross',
                    'label': {
                        'show': False  # 不在轴上显示 label
                    }
                },
                'backgroundColor': 'rgba(50, 50, 50, 0.9)',
                'borderColor': '#333',
                'borderWidth': 1,
                'textStyle': {
                    'color': '#fff',
                    'fontSize': 12
                },
                'padding': [10, 12],
                'extraCssText': 'box-shadow: 0 2px 8px rgba(0, 0, 0, 0.5); max-height: 400px; overflow-y: auto;',
                'confine': True
            },
            'dataZoom': [
                {
                    'type': 'inside',
                    'xAxisIndex': list(range(self.num_signals)),  # 所有 x 轴同步缩放
                    'start': 0,
                    'end': 100,
                    'filterMode': 'none',  # 不过滤数据，只缩放视图
                    'zoomOnMouseWheel': 'ctrl',  # Ctrl+滚轮缩放
                    'moveOnMouseMove': True  # 鼠标移动平移
                }
            ],
            'animation': False  # 关闭全局动画
        }
    
    
    def update_data(self, df: pd.DataFrame):
        """
        更新图表数据
        
        Args:
            df: DataFrame，包含 timestamp 列和所有 signal_* 列
        """
        if df.empty:
            return
        
        # 将时间戳转换为 ECharts 时间格式（毫秒时间戳）
        timestamps = df['timestamp'].apply(
            lambda x: int(x.timestamp() * 1000) if isinstance(x, datetime) else x
        ).tolist()
        
        # 更新每个信号的数据
        for i in range(self.num_signals):
            signal_name = f'signal_{i+1}'
            if signal_name in df.columns:
                # ECharts 时间序列数据格式：[[timestamp, value], ...]
                data = [[ts, float(val)] for ts, val in zip(timestamps, df[signal_name])]
                self.option['series'][i]['data'] = data
        
        # 更新数据缩放范围（显示最近的数据）
        if len(timestamps) > 0:
            # 计算显示范围（显示最后60秒的数据）
            min_time = timestamps[0]
            max_time = timestamps[-1]
            
            # 更新 dataZoom
            if 'dataZoom' in self.option and len(self.option['dataZoom']) > 0:
                # 计算百分比范围
                total_range = max_time - min_time
                if total_range > 0:
                    # 显示最后60秒（60000毫秒）
                    window_ms = 60000
                    if total_range > window_ms:
                        start_percent = ((total_range - window_ms) / total_range) * 100
                        self.option['dataZoom'][0]['start'] = start_percent
                        self.option['dataZoom'][0]['end'] = 100
    
    def get_option(self) -> dict:
        """
        获取 ECharts 配置选项
        
        Returns:
            dict: ECharts 配置字典
        """
        return self.option
