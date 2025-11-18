"""
实时绘图控件
使用 ECharts 创建多子图布局，实现实时数据可视化
封装了数据更新和增量添加接口，数据格式使用 DataFrame
"""
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional


class RealtimePlot:
    """实时多信号绘图控件（ECharts 版本）"""
    
    def __init__(self, num_signals: int = 50, window_seconds: float = 60.0):
        """
        初始化实时绘图控件
        
        Args:
            num_signals: 信号数量（最多20个）
            window_seconds: 数据窗口大小（秒）
        """
        self.num_signals = min(num_signals, 20)
        self.window_seconds = window_seconds
        self.option = self._create_option()
        
        # 内部数据缓存，用于管理时间窗口
        self._data_buffer: Optional[pd.DataFrame] = None
    
    def _create_option(self):
        """创建 ECharts 配置选项"""
        # 计算每个子图的位置和大小
        # 动态计算高度：信号少时充满页面，信号多时使用最小高度
        min_chart_height = 85  # 最小子图高度 85 像素
        chart_spacing = 2  # 子图之间的间距（减小间距让指示线看起来更连续）
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
                'containLabel': True,
                'show': False,  # 不显示边框，让指示线更连续
                'backgroundColor': 'transparent'
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
                    'show': True,  # 所有子图都显示 axisPointer
                    'type': 'line',
                    'snap': False,  # 不吸附到数据点
                    'z': 100,  # 提高层级，确保显示在最上层
                    'lineStyle': {
                        'color': '#666',  # 深灰色
                        'width': 1,
                        'type': 'solid',
                        'opacity': 1
                    },
                    'label': {
                        'show': False  # 不显示标签
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
                'symbol': 'emptyCircle',  # 显示空心圆形数据点
                'symbolSize': 6,  # 数据点大小
                'showSymbol': True,  # 显示数据点标记
                'connectNulls': False,  # 关键：不连接空值，NaN 处断开曲线且不显示点
                'lineStyle': {'width': 2},  # 线条宽度
                'animation': False  # 关闭动画以提高性能
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
                'link': [{'xAxisIndex': 'all'}],  # 链接所有 x 轴，让指示线贯穿所有子图
                'type': 'line',
                'lineStyle': {
                    'color': '#666',
                    'width': 1,
                    'type': 'dashed',
                    'opacity': 0.6
                },
                'triggerOn': 'mousemove'
            },
            'tooltip': {
                'show': True,
                'trigger': 'axis',
                'axisPointer': {
                    'type': 'line',  # 使用线型指示器
                    'axis': 'x',
                    'lineStyle': {
                        'color': '#999',
                        'width': 1,
                        'type': 'solid'
                    },
                    'label': {
                        'show': False  # 不在轴上显示标签
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
    
    
    def _trim_data_by_window(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        根据时间窗口裁剪数据
        
        Args:
            df: 输入的 DataFrame
            
        Returns:
            裁剪后的 DataFrame
        """
        if df.empty or 'timestamp' not in df.columns:
            return df
        
        # 计算时间窗口的起始时间
        latest_time = df['timestamp'].max()
        cutoff_time = latest_time - timedelta(seconds=self.window_seconds)
        
        # 过滤数据
        return df[df['timestamp'] >= cutoff_time].copy()
    
    def _update_chart_data(self, df: pd.DataFrame):
        """
        将 DataFrame 数据更新到图表配置中
        
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
                # 关键改进：只传递有效数据点，跳过 NaN 值
                # 这样 ECharts 只会在有数据的时间点显示点和连线
                data = [[ts, float(val)] 
                        for ts, val in zip(timestamps, df[signal_name])
                        if pd.notna(val)]  # 只保留非 NaN 的数据点
                self.option['series'][i]['data'] = data
        
        # 更新数据缩放范围（显示最近的数据）
        if len(timestamps) > 0:
            min_time = timestamps[0]
            max_time = timestamps[-1]
            
            # 更新 dataZoom
            if 'dataZoom' in self.option and len(self.option['dataZoom']) > 0:
                total_range = max_time - min_time
                if total_range > 0:
                    # 显示最后N秒的数据
                    window_ms = self.window_seconds * 1000
                    if total_range > window_ms:
                        start_percent = ((total_range - window_ms) / total_range) * 100
                        self.option['dataZoom'][0]['start'] = start_percent
                        self.option['dataZoom'][0]['end'] = 100
    
    def update_data(self, df: pd.DataFrame):
        """
        完全更新图表数据（替换所有数据）
        
        Args:
            df: DataFrame，必须包含 'timestamp' 列和 'signal_1', 'signal_2', ... 列
               timestamp 列应为 datetime 类型
        
        Example:
            data = pd.DataFrame({
                'timestamp': [datetime.now(), datetime.now() + timedelta(seconds=1)],
                'signal_1': [1.0, 2.0],
                'signal_2': [3.0, 4.0]
            })
            plot.update_data(data)
        """
        if df.empty:
            return
        
        # 更新内部缓存
        self._data_buffer = df.copy()
        
        # 裁剪到时间窗口
        trimmed_df = self._trim_data_by_window(self._data_buffer)
        
        # 更新图表
        self._update_chart_data(trimmed_df)
    
    def append_data(self, df: pd.DataFrame):
        """
        增量添加新数据到图表（追加数据）
        
        Args:
            df: DataFrame，必须包含 'timestamp' 列和 'signal_1', 'signal_2', ... 列
               timestamp 列应为 datetime 类型
        
        Example:
            new_data = pd.DataFrame({
                'timestamp': [datetime.now()],
                'signal_1': [1.5],
                'signal_2': [3.5]
            })
            plot.append_data(new_data)
        """
        if df.empty:
            return
        
        # 如果缓存为空，直接赋值
        if self._data_buffer is None or self._data_buffer.empty:
            self._data_buffer = df.copy()
        else:
            # 追加新数据
            self._data_buffer = pd.concat([self._data_buffer, df], ignore_index=True)
            
            # 按时间戳排序
            self._data_buffer = self._data_buffer.sort_values('timestamp').reset_index(drop=True)
        
        # 裁剪到时间窗口
        trimmed_df = self._trim_data_by_window(self._data_buffer)
        
        # 更新内部缓存为裁剪后的数据（节省内存）
        self._data_buffer = trimmed_df
        
        # 更新图表
        self._update_chart_data(trimmed_df)
    
    def clear_data(self):
        """清空所有数据"""
        self._data_buffer = None
        for i in range(self.num_signals):
            self.option['series'][i]['data'] = []
    
    def get_option(self) -> dict:
        """
        获取 ECharts 配置选项
        
        Returns:
            dict: ECharts 配置字典
        """
        return self.option
    
    def get_buffered_data(self) -> Optional[pd.DataFrame]:
        """
        获取当前缓存的数据
        
        Returns:
            DataFrame 或 None
        """
        return self._data_buffer.copy() if self._data_buffer is not None else None
