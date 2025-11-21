"""
动态图表测试网页
功能：
1. 页眉、页脚、侧边栏、Tab页
2. 侧边栏选择信号，图表动态更新
3. 开始按钮，添加数据，滚动显示（30秒窗口）
4. 结束时显示所有历史数据
"""
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from nicegui import ui
from realtime_plot import RealtimePlot
from chart_widget import RealtimeChartWidget


class DynamicChartApp:
    """动态图表应用"""
    
    def __init__(self):
        # 信号配置
        self.all_signals = {
            'temperature_[0]': {'type': 'numeric', 'label': '温度传感器', 'unit': '°C'},
            'pressure_[1]': {'type': 'numeric', 'label': '压力传感器', 'unit': 'Pa'},
            'voltage_[2]': {'type': 'numeric', 'label': '电压信号', 'unit': 'V'},
            'current_[3]': {'type': 'numeric', 'label': '电流信号', 'unit': 'A'},
            'status_[4]': {
                'type': 'enum',
                'label': '设备状态',
                'enum_labels': {
                    0: '关闭(OFF)',
                    1: '待机(IDLE)',
                    2: '运行(RUN)',
                    3: '报警(ALARM)'
                }
            },
            'speed_[5]': {'type': 'numeric', 'label': '转速', 'unit': 'RPM'},
        }
        
        # 当前选中的信号
        self.selected_signals = []
        
        # 数据生成器
        self.current_time = datetime.now()
        self.start_time = None
        self.data_history = None  # 存储所有历史数据
        
        # UI组件引用
        self.chart_widget = None
        self.realtime_plot = None
        self.timer = None
        self.is_running = False
        
        # 统计信息标签
        self.data_points_label = None
        self.time_span_label = None
        self.status_label = None
        
        # 控制按钮
        self.start_btn = None
        self.stop_btn = None
        
        # 信号选择checkbox
        self.signal_checkboxes = {}
    
    def generate_data_point(self):
        """生成一个数据点"""
        if not self.selected_signals:
            return None
        
        self.current_time += timedelta(milliseconds=100)  # 每次前进100ms
        
        data = {'timestamp': [self.current_time]}
        
        # 根据运行时间计算相位
        if self.start_time:
            elapsed = (self.current_time - self.start_time).total_seconds()
        else:
            elapsed = 0
        
        for signal_name in self.selected_signals:
            config = self.all_signals[signal_name]
            
            if config['type'] == 'numeric':
                # 生成不同模式的数值数据
                if 'temperature' in signal_name:
                    # 温度：缓慢变化的正弦波 + 噪声
                    value = 25 + 5 * np.sin(elapsed * 0.5) + np.random.randn() * 0.5
                elif 'pressure' in signal_name:
                    # 压力：快速振荡
                    value = 101325 + 1000 * np.sin(elapsed * 2 * np.pi) + np.random.randn() * 50
                elif 'voltage' in signal_name:
                    # 电压：阶跃变化
                    value = 5.0 if (int(elapsed) % 10) < 5 else 3.3
                    value += np.random.randn() * 0.1
                elif 'current' in signal_name:
                    # 电流：指数上升后下降
                    cycle = elapsed % 20
                    if cycle < 10:
                        value = 0.5 * (1 - np.exp(-cycle / 2))
                    else:
                        value = 0.5 * np.exp(-(cycle - 10) / 2)
                    value += np.random.randn() * 0.05
                elif 'speed' in signal_name:
                    # 转速：线性上升
                    value = 1000 + elapsed * 10 + np.random.randn() * 20
                else:
                    value = np.random.randn()
                
                data[signal_name] = [value]
            
            elif config['type'] == 'enum':
                # 状态信号：根据时间周期变化
                cycle = int(elapsed) % 12
                if cycle < 3:
                    state = 0  # OFF
                elif cycle < 5:
                    state = 1  # IDLE
                elif cycle < 10:
                    state = 2  # RUN
                else:
                    state = 3  # ALARM
                data[signal_name] = [state]
        
        return pd.DataFrame(data)
    
    def on_signal_selection_changed(self):
        """信号选择变化时的回调"""
        # 更新选中的信号列表
        self.selected_signals = [
            signal for signal, checkbox in self.signal_checkboxes.items()
            if checkbox.value
        ]
        
        if not self.selected_signals:
            ui.notify('请至少选择一个信号', type='warning')
            return
        
        # 构建信号类型配置
        signal_types = {
            name: {'type': self.all_signals[name]['type']}
            if self.all_signals[name]['type'] == 'numeric'
            else {
                'type': 'enum',
                'enum_labels': self.all_signals[name]['enum_labels']
            }
            for name in self.selected_signals
        }
        
        # 重新创建图表
        self.recreate_chart(signal_types)
        
        ui.notify(f'已选择 {len(self.selected_signals)} 个信号', type='positive')
    
    def recreate_chart(self, signal_types):
        """重新创建图表"""
        # 重新创建RealtimePlot
        self.realtime_plot = RealtimePlot(
            num_signals=len(signal_types),
            window_seconds=30.0,  # 30秒滚动窗口
            signal_types=signal_types
        )
        
        # 获取新的配置（series的data应该都是空的）
        new_option = self.realtime_plot.get_option()
        
        # 更新现有图表（不销毁，避免JavaScript丢失）
        self.chart_widget.update_chart_option(new_option, exclude_tooltip=True)
        self.chart_widget.update_enum_labels(signal_types)
        
        # 确保显示空数据（清空旧的占位符数据）
        empty_series_data = [
            {
                'data': [],
                'showSymbol': False,
                'symbolSize': 6
            }
            for _ in range(len(signal_types))
        ]
        self.chart_widget.update_series_data(empty_series_data)
        
        # 重置数据
        self.data_history = None
        self.update_stats()
    
    def start_data_generation(self):
        """开始数据生成"""
        if not self.selected_signals:
            ui.notify('请先选择信号', type='warning')
            return
        
        self.is_running = True
        self.start_time = datetime.now()
        self.current_time = self.start_time
        self.data_history = None  # 重置历史数据
        
        # 更新UI状态
        self.start_btn.disable()
        self.stop_btn.enable()
        self.status_label.set_text('状态: 正在运行...')
        self.status_label.style('color: #2e7d32; font-weight: bold;')
        
        # 禁用信号选择
        for checkbox in self.signal_checkboxes.values():
            checkbox.disable()
        
        # 启动定时器（每100ms添加一个数据点）
        self.timer = ui.timer(0.1, self.add_data_point)
        
        ui.notify('开始生成数据', type='positive')
    
    def add_data_point(self):
        """添加一个数据点"""
        if not self.is_running:
            return
        
        # 生成新数据点
        new_data = self.generate_data_point()
        
        if new_data is None or new_data.empty:
            return
        
        # 添加到历史数据
        if self.data_history is None or self.data_history.empty:
            self.data_history = new_data.copy()
        else:
            self.data_history = pd.concat([self.data_history, new_data], ignore_index=True)
        
        # 更新实时显示（30秒滚动窗口）
        self.realtime_plot.append_data(new_data)
        self._update_chart_display()
        
        # 更新统计信息
        self.update_stats()
    
    def stop_data_generation(self):
        """停止数据生成"""
        self.is_running = False
        
        # 停止定时器
        if self.timer:
            self.timer.deactivate()
            self.timer = None
        
        # 更新UI状态
        self.start_btn.enable()
        self.stop_btn.disable()
        self.status_label.set_text('状态: 已停止')
        self.status_label.style('color: #d32f2f; font-weight: bold;')
        
        # 启用信号选择
        for checkbox in self.signal_checkboxes.values():
            checkbox.enable()
        
        # 显示所有历史数据
        if self.data_history is not None and not self.data_history.empty:
            self.show_all_history()
        
        ui.notify('已停止，显示全部历史数据', type='info')
    
    def show_all_history(self):
        """显示所有历史数据"""
        if self.data_history is None or self.data_history.empty:
            return
        
        # 更新图表以显示所有数据（不限制30秒窗口）
        self.realtime_plot.update_data(self.data_history)
        self._update_chart_display()
        
        # 更新统计信息
        self.update_stats(show_all=True)
    
    def _update_chart_display(self):
        """更新图表显示"""
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
    
    def update_stats(self, show_all=False):
        """更新统计信息"""
        if self.data_history is None or self.data_history.empty:
            self.data_points_label.set_text('数据点数: 0')
            self.time_span_label.set_text('时间跨度: 0.0 秒')
            return
        
        total_points = len(self.data_history)
        time_span = (self.data_history['timestamp'].max() - 
                     self.data_history['timestamp'].min()).total_seconds()
        
        # 获取当前显示的数据
        buffered_data = self.realtime_plot.get_buffered_data()
        if buffered_data is not None and not buffered_data.empty:
            displayed_points = len(buffered_data)
            displayed_span = (buffered_data['timestamp'].max() - 
                            buffered_data['timestamp'].min()).total_seconds()
        else:
            displayed_points = 0
            displayed_span = 0
        
        if show_all:
            self.data_points_label.set_text(f'数据点数: {total_points} (全部历史)')
            self.time_span_label.set_text(f'时间跨度: {time_span:.1f} 秒 (全部)')
        else:
            self.data_points_label.set_text(
                f'数据点数: {displayed_points} / {total_points} (显示/总计)'
            )
            self.time_span_label.set_text(
                f'时间跨度: {displayed_span:.1f} / {time_span:.1f} 秒 (显示/总计)'
            )


@ui.page('/')
def main_page():
    """主页面"""
    app = DynamicChartApp()

    time.sleep(10)
    
    # 页眉
    with ui.header(elevated=True).classes('items-center justify-between').style(
        'background: linear-gradient(90deg, #1976d2 0%, #2196f3 100%); padding: 10px 20px;'
    ):
        ui.label('🚀 动态实时图表系统').classes('text-h5').style('color: white; font-weight: bold;')
        with ui.row().classes('gap-2'):
            ui.label(f'当前时间: ').style('color: white;')
            time_label = ui.label().style('color: white; font-weight: bold;')
            
            # 实时时钟
            def update_time():
                time_label.set_text(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            ui.timer(1.0, update_time)
            update_time()
    
    # 主体内容（使用左右布局）
    with ui.row().classes('w-full').style('height: calc(100vh - 120px);'):
        # 左侧边栏（信号选择）
        with ui.card().classes('w-64').style(
            'height: 100%; overflow-y: auto; border-right: 2px solid #e0e0e0;'
        ):
            ui.label('📊 信号选择').classes('text-h6 mb-2').style('color: #1976d2;')
            ui.separator()
            
            with ui.column().classes('gap-2 mt-2'):
                # 全选/取消全选按钮
                with ui.row().classes('gap-2'):
                    def select_all():
                        for checkbox in app.signal_checkboxes.values():
                            checkbox.value = True
                        app.on_signal_selection_changed()
                    
                    def deselect_all():
                        for checkbox in app.signal_checkboxes.values():
                            checkbox.value = False
                    
                    ui.button('全选', icon='check_box', on_click=select_all).props('size=sm outline')
                    ui.button('清除', icon='clear', on_click=deselect_all).props('size=sm outline')
                
                ui.separator()
                
                # 信号选择checkbox
                for signal_name, config in app.all_signals.items():
                    label = config['label']
                    if config['type'] == 'numeric':
                        unit = config.get('unit', '')
                        label_text = f"{label} ({unit})" if unit else label
                        icon = 'show_chart'
                    else:
                        label_text = f"{label} (状态)"
                        icon = 'toggle_on'
                    
                    checkbox = ui.checkbox(label_text).props(f'dense')
                    checkbox.on_value_change(lambda: app.on_signal_selection_changed())
                    app.signal_checkboxes[signal_name] = checkbox
                
                ui.separator()
                
                # 提示信息
                with ui.card().style('background-color: #e3f2fd; padding: 10px;'):
                    ui.html('''
                    <div style="font-size: 12px;">
                        <b>💡 使用提示：</b><br>
                        1. 选择要显示的信号<br>
                        2. 点击"开始"按钮<br>
                        3. 实时数据滚动显示(30秒)<br>
                        4. 点击"停止"查看全部历史
                    </div>
                    ''')
        
        # 右侧主体内容
        with ui.column().classes('flex-grow'):
            # 控制面板
            with ui.card().classes('w-full p-4'):
                ui.label('🎮 控制面板').classes('text-h6 mb-2')
                
                # 统计信息
                with ui.row().classes('gap-4 items-center mb-2'):
                    app.data_points_label = ui.label('数据点数: 0')
                    app.time_span_label = ui.label('时间跨度: 0.0 秒')
                    ui.label(f'信号数量: 0').bind_text_from(
                        app, 'selected_signals', 
                        backward=lambda x: f'信号数量: {len(x)}'
                    )
                
                # 控制按钮
                with ui.row().classes('gap-2 items-center'):
                    app.start_btn = ui.button('开始', icon='play_arrow', 
                                              on_click=app.start_data_generation).props('color=green')
                    app.stop_btn = ui.button('停止', icon='stop', 
                                            on_click=app.stop_data_generation).props('color=red')
                    app.stop_btn.disable()
                    app.status_label = ui.label('状态: 准备就绪').style('font-weight: bold;')
            
            # Tab页
            with ui.tabs().classes('w-full') as tabs:
                tab_chart = ui.tab('图表显示', icon='timeline')
                tab_info = ui.tab('系统信息', icon='info')
            
            with ui.tab_panels(tabs, value=tab_info).classes('w-full flex-grow'):
                
                # Tab 2: 系统信息
                with ui.tab_panel(tab_info):
                    with ui.card().classes('w-full p-4'):
                        ui.label('📖 系统功能说明').classes('text-h6 mb-2')
                        ui.html('''
                        <div style="font-size: 14px; line-height: 1.8;">
                            <h3 style="color: #1976d2;">功能特点</h3>
                            <ul>
                                <li><b>多信号支持：</b>支持数值信号和枚举状态信号</li>
                                <li><b>动态选择：</b>可以动态选择要显示的信号组合</li>
                                <li><b>实时更新：</b>每100ms生成一个新数据点</li>
                                <li><b>滚动显示：</b>运行时只显示最近30秒的数据</li>
                                <li><b>历史回放：</b>停止后显示全部历史数据</li>
                            </ul>
                            
                            <h3 style="color: #1976d2; margin-top: 20px;">信号说明</h3>
                            <ul>
                                <li><b>温度传感器：</b>缓慢变化的正弦波（20-30°C）</li>
                                <li><b>压力传感器：</b>快速振荡（标准大气压±1000Pa）</li>
                                <li><b>电压信号：</b>5V和3.3V之间的阶跃变化</li>
                                <li><b>电流信号：</b>指数上升和下降的周期信号</li>
                                <li><b>设备状态：</b>OFF → IDLE → RUN → ALARM 循环</li>
                                <li><b>转速：</b>线性上升的趋势</li>
                            </ul>
                            
                            <h3 style="color: #1976d2; margin-top: 20px;">操作步骤</h3>
                            <ol>
                                <li>在左侧边栏选择要监控的信号（至少选一个）</li>
                                <li>点击"开始"按钮启动数据生成</li>
                                <li>观察实时数据滚动显示（30秒窗口）</li>
                                <li>点击"停止"按钮停止并查看全部历史数据</li>
                                <li>可以重新选择信号组合并再次运行</li>
                            </ol>
                            
                            <h3 style="color: #1976d2; margin-top: 20px;">技术特性</h3>
                            <ul>
                                <li><b>采样频率：</b>10 Hz (每100ms一个点)</li>
                                <li><b>显示窗口：</b>30秒滚动窗口（运行时）</li>
                                <li><b>数据缓存：</b>保存全部历史数据</li>
                                <li><b>实例隔离：</b>支持多图表实例互不干扰</li>
                                <li><b>性能优化：</b>自动调整数据点显示密度</li>
                            </ul>
                        </div>
                        ''')
    
                # Tab 1: 图表显示
                with ui.tab_panel(tab_chart):
                    app.chart_container = ui.column().classes('w-full')
                    
                    # 初始化时创建一个空图表，确保JavaScript正确注入
                    # 使用一个信号作为占位符
                    initial_signal_types = {
                        'placeholder_[0]': {'type': 'numeric'}
                    }
                    app.realtime_plot = RealtimePlot(
                        num_signals=1,
                        window_seconds=30.0,
                        signal_types=initial_signal_types
                    )
                    initial_option = app.realtime_plot.get_option()
                    
                    with app.chart_container:
                        app.chart_widget = RealtimeChartWidget(initial_option)
                        app.chart_widget.update_enum_labels(initial_signal_types)
                        
                        # 显示提示信息
                        with ui.card().classes('w-full').style('margin-top: 20px; background-color: #e3f2fd;'):
                            ui.label('👈 请先在左侧选择信号').classes('text-h6').style(
                                'color: #1976d2; text-align: center; padding: 50px;'
                            )
    # 页脚
    with ui.footer().style(
        'background-color: #263238; color: white; padding: 15px; text-align: center;'
    ):
        ui.html('''
        <div style="font-size: 13px;">
            <b>动态实时图表系统 v1.0</b> | 
            基于 NiceGUI + ECharts | 
            © 2025 | 
            <span style="color: #4fc3f7;">实时数据可视化解决方案</span>
        </div>
        ''')


# 启动应用
if __name__ in {'__main__', '__mp_main__'}:
    ui.run(port=8082, title='动态实时图表系统', dark=False, reload=False)

