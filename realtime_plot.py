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
    
    def __init__(self, num_signals: int = 50, window_seconds: float = 60.0, signal_types: Optional[dict] = None, max_time_gap_seconds: float = 1.0):
        """
        初始化实时绘图控件
        
        Args:
            num_signals: 信号数量（最多100个）
            window_seconds: 数据窗口大小（秒）
            signal_types: 信号类型配置字典，格式：{'signal_1': {'type': 'numeric'/'enum', 'enum_labels': {0: 'OFF', 1: 'ON'}}}
            max_time_gap_seconds: 最大时间间隔（秒），超过此间隔的数据点之间不连线，默认1.0秒
        """
        self.num_signals = min(num_signals, 100)
        self.window_seconds = window_seconds
        self.signal_types = signal_types or {}
        self.max_time_gap_seconds = max_time_gap_seconds  # 最大时间间隔（秒）
        # 子图顺序：存储子图的索引顺序，默认按 0, 1, 2, ... 排列
        self.subplot_order = list(range(self.num_signals))
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
        top_bottom_padding = 80  # 顶部和底部的总padding（增加以容纳滑块）
        
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
        
        # 计算所需的最大左边距（为枚举标签预留足够空间）
        # 检查是否有枚举信号，并找出最长的标签
        max_label_length = 0
        # 将 signal_types 转换为列表以按索引访问
        signal_types_list = list(self.signal_types.items())
        for i in range(self.num_signals):
            if i < len(signal_types_list):
                signal_name, signal_config = signal_types_list[i]
            else:
                signal_config = {'type': 'numeric'}
            if signal_config['type'] == 'enum':
                enum_labels = signal_config.get('enum_labels', {})
                for label in enum_labels.values():
                    max_label_length = max(max_label_length, len(label))
        
        # 根据最长标签动态计算左边距（每个字符约7像素，最少70像素）
        # 增加最小左边距以适应较长的数值坐标
        grid_left = max(85, min(max_label_length * 7, 200))  # 限制最大200像素
        title_left = 10  # 标题放在最左边
        
        # 在 ECharts 中，grids、x_axes、y_axes 数组的索引必须等于 gridIndex
        # 所以我们需要先创建所有 grids、x_axes、y_axes（按原始索引顺序），
        # 然后根据 subplot_order 调整它们的 top 位置
        # 同时，titles 和 series 也需要按照 subplot_order 顺序创建
        
        # 先创建所有 grids、x_axes、y_axes（按原始索引顺序，gridIndex = 数组索引）
        for i in range(self.num_signals):
            # 根据 subplot_order 找到当前原始索引的显示位置
            display_pos = self.subplot_order.index(i)
            
            # 配置 grid 位置（垂直排列，使用像素定位）
            # 使用 display_pos 来决定显示位置
            top = chart_spacing + display_pos * (chart_height_per_signal + chart_spacing) + 30
            
            # 根据子图高度调整标题和grid的显示
            title_offset = 22 if chart_height_per_signal >= 100 else 18
            grid_height = chart_height_per_signal - 25 if chart_height_per_signal >= 100 else chart_height_per_signal - 20
            
            # Determine background color based on display position (zebra pattern)
            # Alternating between #fafafa and #f2f2f2
            bg_color = '#fafafa' if display_pos % 2 == 1 else '#f2f2f2'

            # 配置 grid（gridIndex = i，即数组索引）
            grids.append({
                'left': grid_left,  # 统一的左边距，确保时间轴对齐
                'right': 70,
                'top': top,  # 根据显示位置设置 top
                'height': grid_height,  # 根据总高度动态调整
                'containLabel': False,  # 禁用自动调整，严格使用left值
                'show': True,  # 显示以展示背景色
                'borderWidth': 0,  # 不显示边框
                'backgroundColor': bg_color
            })
            
            # 配置 x 轴（gridIndex = i，即数组索引）
            is_last = (display_pos == len(self.subplot_order) - 1)
            x_axes.append({
                'type': 'time',
                'gridIndex': i,  # 使用数组索引作为 gridIndex
                'show': is_last,  # 只有最后一个显示
                'position': 'bottom',
                'splitLine': {'show': False},
                'axisLine': {'show': is_last, 'lineStyle': {'color': '#999'}},
                'axisTick': {'show': is_last},
                'axisLabel': {
                    'show': is_last,
                    'formatter': '{HH}:{mm}:{ss}.{SSS}',  # 占位符，将在JavaScript中被替换
                    'fontSize': 10,
                    'rotate': 0
                },
                'axisPointer': {
                    'show': True,  # 需要启用才能触发 tooltip
                    'label': {
                        'show': False  # 禁用axisPointer的标签，避免显示额外的时间戳
                    },
                    'lineStyle': {
                        'opacity': 0  # 设置为完全透明，不显示线
                    }
                }
            })
            
            # 配置 y 轴（gridIndex = i，即数组索引）
            if i < len(signal_types_list):
                signal_name, signal_config = signal_types_list[i]
            else:
                signal_config = {'type': 'numeric'}
            
            if signal_config['type'] == 'enum':
                # 枚举信号的 y 轴：使用类别轴直接显示文本
                enum_labels = signal_config.get('enum_labels', {})
                enum_values = sorted(enum_labels.keys())
                
                # 构建类别数组（按值的顺序）
                categories = [enum_labels[v] for v in enum_values]
                
                y_axes.append({
                    'type': 'category',  # 使用类别轴
                    'gridIndex': i,  # 使用数组索引作为 gridIndex
                    'data': categories,  # 直接设置类别数据
                    'splitLine': {'show': True, 'lineStyle': {'type': 'dashed', 'color': '#e0e0e0'}},
                    'axisLabel': {
                        'fontSize': 8,  # 稍微减小字体
                        'interval': 0,  # 显示所有标签
                        'width': grid_left - 15,  # 设置标签宽度限制
                        'overflow': 'truncate',  # 超出部分截断
                        'ellipsis': '...'  # 截断时显示省略号
                    },
                    '_enum_labels': enum_labels,  # 存储枚举标签，供后续使用
                    '_enum_values': enum_values  # 存储枚举值列表
                })
            else:
                # 数值信号的 y 轴：自动缩放
                y_axes.append({
                    'type': 'value',
                    'gridIndex': i,  # 使用数组索引作为 gridIndex
                    'splitLine': {'show': True, 'lineStyle': {'type': 'dashed', 'color': '#e0e0e0'}},
                    'scale': True,  # 自动缩放以适应数据
                    'axisLabel': {
                        'show': True,  # 显式启用y轴标签显示
                        'fontSize': 9
                    },
                    'splitNumber': 3  # 减少刻度线数量，节省空间
                })
        
        # 按照 subplot_order 顺序创建 titles 和 series
        for display_pos, original_idx in enumerate(self.subplot_order):
            # 根据 subplot_order 找到当前原始索引的显示位置
            top = chart_spacing + display_pos * (chart_height_per_signal + chart_spacing) + 30
            title_offset = 22 if chart_height_per_signal >= 100 else 18
            
            # 获取自定义信号名（如果有的话）
            if original_idx < len(signal_types_list):
                display_name = signal_types_list[original_idx][0]  # 使用自定义信号名
            else:
                display_name = f'Signal {original_idx+1}'  # 默认名称
            
            # 配置标题（显示在每个子图的左上角）
            titles.append({
                'text': display_name,
                'left': title_left,  # 与 grid 的 left 对齐
                'top': top - title_offset,  # 在 grid 上方
                'textStyle': {
                    'fontSize': 13,
                    'fontWeight': 'bold',
                    'color': '#333'
                }
            })
            
            # 获取信号配置
            if original_idx < len(signal_types_list):
                signal_name, signal_config = signal_types_list[original_idx]
            else:
                signal_config = {'type': 'numeric'}
            
            # 获取显示名称
            series_name = display_name if original_idx < len(signal_types_list) else f'Signal {original_idx+1}'
            
            # 配置系列（折线图或阶梯图）
            if signal_config['type'] == 'enum':
                # 枚举信号：使用阶梯图
                series.append({
                    'id': f'series_{original_idx}',  # 添加 ID 以确保 ECharts 在重新排序时正确跟踪
                    'type': 'line',
                    'xAxisIndex': original_idx,  # 使用原始索引
                    'yAxisIndex': original_idx,  # 使用原始索引
                    'data': [],
                    'name': series_name,
                    'step': 'end',  # 阶梯图样式
                    'smooth': False,
                    'symbol': 'circle',  # 实心圆形数据点
                    'symbolSize': 6,
                    'showSymbol': True,
                    'connectNulls': False,
                    'lineStyle': {'width': 2},
                    'animation': False
                })
            else:
                # 数值信号：使用普通折线图
                series.append({
                    'id': f'series_{original_idx}',  # 添加 ID 以确保 ECharts 在重新排序时正确跟踪
                    'type': 'line',
                    'xAxisIndex': original_idx,  # 使用原始索引
                    'yAxisIndex': original_idx,  # 使用原始索引
                    'data': [],
                    'name': series_name,
                    'step': False,  # 显式禁用阶梯图，防止配置合并时的残留
                    'smooth': False,
                    'symbol': 'emptyCircle',  # 显示空心圆形数据点
                    'symbolSize': 6,  # 数据点大小
                    'showSymbol': True,  # 显示数据点标记
                    'connectNulls': False,  # 关键：不连接空值，NaN 处断开曲线且不显示点
                    'lineStyle': {'width': 2},  # 线条宽度
                    'animation': False  # 关闭动画以提高性能
                })
        
        return {
            'grid': grids,  # 按原始索引顺序，但 top 位置根据 subplot_order 设置
            'xAxis': x_axes,  # 按原始索引顺序，gridIndex = 数组索引
            'yAxis': y_axes,  # 按原始索引顺序，gridIndex = 数组索引
            'series': series,  # 按 subplot_order 顺序排列
            'title': titles,  # 按 subplot_order 顺序排列
            # 设置图表的总高度
            'height': total_height,
            'axisPointer': {
                'link': [{'xAxisIndex': 'all'}],  # 链接所有 x 轴
                'label': {
                    'show': False  # 全局禁用axisPointer标签
                },
                'lineStyle': {
                    'opacity': 0  # 设置为完全透明，不显示 ECharts 的线，只用自定义线
                }
            },
            'tooltip': {
                'show': True,
                'trigger': 'axis',
                'axisPointer': {
                    'type': 'line',
                    'label': {
                        'show': False  # 禁用tooltip的axisPointer标签
                    },
                    'lineStyle': {
                        'opacity': 0  # 完全透明，不显示 tooltip 的指示线
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
                'extraCssText': 'box-shadow: 0 2px 8px rgba(0, 0, 0, 0.5); max-height: 90vh; max-width: 600px; min-width: 280px; overflow-y: auto;',
                'confine': False  # 允许tooltip超出图表边界，避免被截断
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
                },
                {
                    'type': 'slider',
                    'show': True,
                    'xAxisIndex': list(range(self.num_signals)),  # 所有 x 轴同步缩放
                    'start': 0,
                    'end': 100,
                    'bottom': 10,
                    'height': 20,
                    'filterMode': 'none',
                    'showDetail': False,  # 不显示详细信息，避免多个时间戳标签
                    'showDataShadow': False,  # 不显示数据阴影
                    'borderColor': '#ccc',
                    'fillerColor': 'rgba(25, 118, 210, 0.2)',
                    'handleStyle': {
                        'color': '#1976d2'
                    },
                    'textStyle': {
                        'color': '#333'
                    }
                }
            ],
            'animation': False,  # 关闭全局动画
            'animationDurationUpdate': 0  # 关闭更新动画，防止子图重排时出现过渡效果
        }
    
    
    def _trim_data_by_window(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        根据时间窗口裁剪数据，并限制最大数据点数量
        
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
        trimmed_df = df[df['timestamp'] >= cutoff_time].copy()
        
        # 额外限制：如果数据点超过2000个，只保留最新的2000个
        # 这样可以避免传输过多数据，同时保持足够的可视化精度
        max_points = 2000
        if len(trimmed_df) > max_points:
            trimmed_df = trimmed_df.tail(max_points).copy()
        
        return trimmed_df
    
    def _update_chart_data(self, df: pd.DataFrame):
        """
        将 DataFrame 数据更新到图表配置中，并根据数据点密度自动调整显示方式
        
        Args:
            df: DataFrame，包含 timestamp 列和所有信号列
        """
        if df.empty:
            return
        
        # 将时间戳转换为 ECharts 时间格式（毫秒时间戳）
        # 不使用时区转换，直接将datetime视为UTC时间
        def datetime_to_ms(x):
            if isinstance(x, datetime):
                # 将datetime视为naive UTC时间，不考虑本地时区
                epoch = datetime(1970, 1, 1)
                return int((x - epoch).total_seconds() * 1000)
            else:
                return x
        
        timestamps = df['timestamp'].apply(datetime_to_ms).tolist()
        
        # 将 signal_types 转换为列表以按索引访问
        signal_types_list = list(self.signal_types.items())
        
        # 更新每个信号的数据
        for series_idx, i in enumerate(self.subplot_order):
            # 使用列表索引获取信号名和配置
            if i < len(signal_types_list):
                signal_name, signal_config = signal_types_list[i]
            else:
                # 如果没有配置，尝试使用默认的 signal_* 列名
                signal_name = f'signal_{i+1}'
                signal_config = {'type': 'numeric'}
            
            if signal_name in df.columns:
                # ECharts 时间序列数据格式：[[timestamp, value], ...]
                # 关键改进：只传递有效数据点，跳过 NaN 值
                # 这样 ECharts 只会在有数据的时间点显示点和连线
                valid_data = [[ts, float(val)] 
                             for ts, val in zip(timestamps, df[signal_name])
                             if pd.notna(val)]  # 只保留非 NaN 的数据点
                
                # 处理数据点间隔：如果相邻数据点时间间隔超过阈值，插入 null 值断开连线
                if len(valid_data) > 1 and self.max_time_gap_seconds > 0:
                    data = []
                    max_gap_ms = self.max_time_gap_seconds * 1000  # 转换为毫秒
                    for j, (ts, val) in enumerate(valid_data):
                        data.append([ts, val])
                        # 检查与下一个数据点的时间间隔
                        if j < len(valid_data) - 1:
                            next_ts = valid_data[j + 1][0]
                            time_gap = next_ts - ts
                            if time_gap > max_gap_ms:
                                # 时间间隔过大，插入 null 值断开连线
                                # 在下一个点之前插入一个 null 点，时间戳设为下一个点的时间戳
                                data.append([next_ts, None])
                else:
                    data = valid_data
                
                self.option['series'][series_idx]['data'] = data
                
                # 如果是枚举类型，动态更新Y轴类别（只显示实际出现的值）
                if signal_config['type'] == 'enum' and len(data) > 0:
                    enum_labels = signal_config.get('enum_labels', {})
                    
                    # 收集实际出现的枚举值（跳过 null 值）
                    actual_values = set()
                    for _, val in data:
                        if val is not None:
                            val_int = int(round(val))
                            if val_int in enum_labels:
                                actual_values.add(val_int)
                    
                    # 按值排序
                    sorted_values = sorted(actual_values)
                    
                    # 构建实际显示的类别列表
                    if sorted_values:
                        categories = [enum_labels[v] for v in sorted_values]
                        
                        # 创建值到索引的映射
                        value_to_index = {v: idx for idx, v in enumerate(sorted_values)}
                        
                        # 重新映射数据：将原始枚举值转换为新的类别索引
                        remapped_data = []
                        for ts, val in data:
                            # 保留 null 值，用于断开连线
                            if val is None:
                                remapped_data.append([ts, None])
                            else:
                                val_int = int(round(val))
                                if val_int in value_to_index:
                                    # 使用新的索引
                                    remapped_data.append([ts, value_to_index[val_int]])
                        
                        # 更新series数据为重新映射后的数据
                        self.option['series'][series_idx]['data'] = remapped_data
                        
                        # 更新Y轴配置
                        self.option['yAxis'][i]['data'] = categories
                        self.option['yAxis'][i]['_actual_values'] = sorted_values  # 记录实际值
                        self.option['yAxis'][i]['min'] = 0  # 设置最小值
                        self.option['yAxis'][i]['max'] = len(categories) - 1 if len(categories) > 1 else 0  # 设置最大值

                # 动态调整显示符号（数据密度检查）
                # 这里的逻辑与前端保持一致，确保在后端更新配置时也应用相同的规则，防止重新排序时出现“闪烁”
                current_data = self.option['series'][series_idx]['data']
                visible_points = len(current_data) if current_data else 0
                
                if visible_points > 150:
                    self.option['series'][series_idx]['showSymbol'] = False
                    self.option['series'][series_idx]['symbolSize'] = 4
                elif visible_points > 50:
                    self.option['series'][series_idx]['showSymbol'] = True
                    self.option['series'][series_idx]['symbolSize'] = 4
                else:
                    self.option['series'][series_idx]['showSymbol'] = True
                    self.option['series'][series_idx]['symbolSize'] = 6
        
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
    
    def set_subplot_order(self, new_order: list):
        """
        设置子图顺序
        
        Args:
            new_order: 新的子图顺序列表，例如 [2, 0, 1, 3] 表示将索引2的子图放在最上面
                      必须包含所有索引 0 到 num_signals-1，且不重复
        """
        # 验证顺序列表
        if len(new_order) != self.num_signals:
            raise ValueError(f"顺序列表长度必须等于信号数量 {self.num_signals}")
        if set(new_order) != set(range(self.num_signals)):
            raise ValueError(f"顺序列表必须包含所有索引 0 到 {self.num_signals-1}")
        
        self.subplot_order = new_order.copy()
        # 重新生成配置
        self.option = self._create_option()
        # 如果已有数据，需要重新更新数据到新配置中
        if self._data_buffer is not None and not self._data_buffer.empty:
            self._update_chart_data(self._trim_data_by_window(self._data_buffer))
    
    def move_subplot_up(self, index: int):
        """
        将指定索引的子图向上移动一个位置
        
        Args:
            index: 要移动的子图索引（原始索引，不是显示位置）
        """
        if index < 0 or index >= self.num_signals:
            raise ValueError(f"索引必须在 0 到 {self.num_signals-1} 之间")
        
        # 找到当前显示位置
        current_pos = self.subplot_order.index(index)
        if current_pos == 0:
            return  # 已经在最上面，无法上移
        
        # 交换位置
        self.subplot_order[current_pos], self.subplot_order[current_pos - 1] = \
            self.subplot_order[current_pos - 1], self.subplot_order[current_pos]
        
        # 重新生成配置
        self.option = self._create_option()
        # 如果已有数据，需要重新更新数据到新配置中
        if self._data_buffer is not None and not self._data_buffer.empty:
            self._update_chart_data(self._trim_data_by_window(self._data_buffer))
    
    def move_subplot_down(self, index: int):
        """
        将指定索引的子图向下移动一个位置
        
        Args:
            index: 要移动的子图索引（原始索引，不是显示位置）
        """
        if index < 0 or index >= self.num_signals:
            raise ValueError(f"索引必须在 0 到 {self.num_signals-1} 之间")
        
        # 找到当前显示位置
        current_pos = self.subplot_order.index(index)
        if current_pos == len(self.subplot_order) - 1:
            return  # 已经在最下面，无法下移
        
        # 交换位置
        self.subplot_order[current_pos], self.subplot_order[current_pos + 1] = \
            self.subplot_order[current_pos + 1], self.subplot_order[current_pos]
        
        # 重新生成配置
        self.option = self._create_option()
        # 如果已有数据，需要重新更新数据到新配置中
        if self._data_buffer is not None and not self._data_buffer.empty:
            self._update_chart_data(self._trim_data_by_window(self._data_buffer))
    
    def get_subplot_order(self) -> list:
        """
        获取当前子图顺序
        
        Returns:
            子图顺序列表
        """
        return self.subplot_order.copy()
