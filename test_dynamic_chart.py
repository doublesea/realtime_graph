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
from echart_widget import EChartWidget
from signal_manager_widget import SignalGroupManager


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
        self.data_point_count = 0  # 数据点计数器，用于生成时间间隔
        
        # UI组件引用
        self.echart_widget = None  # 使用 EChartWidget
        self.timer = None
        self.is_running = False
        
        # 统计信息标签
        self.data_points_label = None
        self.time_span_label = None
        self.status_label = None
        
        # 控制按钮
        self.start_btn = None
        self.stop_btn = None
        
        # 信号管理组件
        self.signal_manager = None
    
    def generate_data_point(self):
        """生成一个数据点"""
        if not self.selected_signals:
            return None
        
        # 正常时间步进：每次前进100ms
        time_step = timedelta(milliseconds=100)
        
        # 每隔一段时间产生时间间隔，用于测试断开连线功能
        # 在多个位置产生时间间隔，让测试效果更明显
        if self.data_point_count > 0:
            # 每30个点产生一个间隔（约3秒后）
            if self.data_point_count % 30 == 0:
                time_step = timedelta(seconds=1.5)  # 1.5秒，超过默认的1秒阈值
                ui.notify(f'产生时间间隔：跳过 {time_step.total_seconds():.1f} 秒', type='info')
            # 每80个点产生一个更大的间隔（约8秒后）
            elif self.data_point_count % 80 == 0:
                time_step = timedelta(seconds=3.0)  # 3秒，更大的间隔
                ui.notify(f'产生大时间间隔：跳过 {time_step.total_seconds():.1f} 秒', type='warning')
        
        self.current_time += time_step
        self.data_point_count += 1
        
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
        if not self.signal_manager:
            return

        # 更新选中的信号列表
        self.selected_signals = self.signal_manager.get_selected_signals()
        
        if not self.selected_signals:
            # ui.notify('请至少选择一个信号', type='warning')
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
        if self.echart_widget is None:
            # 首次创建
            self.echart_widget = EChartWidget(
                signal_types=signal_types,
                window_seconds=30.0,  # 30秒滚动窗口
                defer_init=True  # 延迟初始化，因为可能在tab中
            )
        else:
            # 更新信号类型
            self.echart_widget.update_signal_types(signal_types)
        
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
        self.data_point_count = 0  # 重置数据点计数器
        
        # 更新UI状态
        self.start_btn.disable()
        self.stop_btn.enable()
        self.status_label.set_text('状态: 正在运行...')
        self.status_label.style('color: #2e7d32; font-weight: bold;')
        
        # 禁用信号选择
        if self.signal_manager:
            self.signal_manager.set_enabled(False)
        
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
        if self.echart_widget:
            self.echart_widget.append_data(new_data)
        
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
        if self.signal_manager:
            self.signal_manager.set_enabled(True)
        
        # 显示所有历史数据
        if self.data_history is not None and not self.data_history.empty:
            self.show_all_history()
        
        ui.notify('已停止，显示全部历史数据', type='info')
    
    def show_all_history(self):
        """显示所有历史数据"""
        if self.data_history is None or self.data_history.empty:
            return
        
        # 更新图表以显示所有数据（不限制30秒窗口）
        if self.echart_widget:
            self.echart_widget.update_data(self.data_history)
        
        # 更新统计信息
        self.update_stats(show_all=True)
    
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
        if self.echart_widget:
            buffered_data = self.echart_widget.get_buffered_data()
        else:
            buffered_data = None
        
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
    
    # 左侧抽屉（信号选择）
    with ui.left_drawer(fixed=False, value=False).classes('bg-slate-50 border-r').style('width: 320px;') as drawer:
        with ui.column().classes('w-full h-full gap-0'):
            with ui.row().classes('w-full p-4 items-center justify-between bg-blue-50'):
                ui.label('📊 信号分组管理').classes('text-lg font-bold').style('color: #1976d2;')
                ui.button(icon='close', on_click=lambda: drawer.toggle()).props('flat dense').classes('md:hidden')
            
            ui.separator()
            
            # 使用新的信号管理组件
            scroll = ui.scroll_area().classes('flex-grow w-full')
            with scroll:
                app.signal_manager = SignalGroupManager(
                    all_signals=app.all_signals,
                    on_selection_change=app.on_signal_selection_changed
                )
                app.signal_manager.render_sidebar()
            
            ui.separator()
            
            # 提示信息
            with ui.card().classes('m-4 bg-blue-50 p-3 shadow-none border'):
                ui.markdown('''
**💡 使用提示：**
1. 在下方创建分组并添加信号
2. 搜索过滤信号
3. 勾选信号后点击"开始"
                ''').classes('text-xs')
    
    # 页眉
    with ui.header(elevated=True).classes('items-center justify-between').style(
        'background: linear-gradient(90deg, #1976d2 0%, #2196f3 100%); padding: 10px 20px;'
    ):
        # 左侧：菜单按钮和标题
        with ui.row().classes('items-center gap-4'):
            ui.button(icon='menu', on_click=lambda: drawer.toggle()).props('flat color=white')
            ui.label('🚀 动态实时图表系统').classes('text-h5').style('color: white; font-weight: bold;')
        
        # 中间：Tab页切换
        with ui.tabs().classes('flex-grow justify-center').style('color: white;') as tabs:
            tab_chart = ui.tab('图表显示', icon='timeline')
            tab_signals = ui.tab('信号列表', icon='list')
            tab_info = ui.tab('系统信息', icon='info')
        
        # 右侧：时间显示
        with ui.row().classes('gap-2'):
            ui.label(f'当前时间: ').style('color: white;')
            time_label = ui.label().style('color: white; font-weight: bold;')
            
            # 实时时钟
            def update_time():
                time_label.set_text(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            ui.timer(1.0, update_time)
            update_time()
    
    # 主体内容
    with ui.column().classes('w-full').style('height: calc(100vh - 120px);'):
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
        
        # Tab页内容
        # 给图表 tab 添加点击事件来触发初始化
        def on_chart_tab_click():
            print(f"[Tab Switch] 图表 tab 被点击")
            # 延迟一点确保 tab 切换完成
            ui.timer(0.2, lambda: (
                print(f"[Tab Switch] 触发图表初始化..."),
                app.echart_widget.ensure_initialized() if hasattr(app, 'echart_widget') and app.echart_widget else None
            ), once=True)  # 减少延迟到0.2秒
        
        tab_chart.on('click', on_chart_tab_click)
        
        with ui.tab_panels(tabs, value=tab_info).classes('w-full flex-grow') as panels:
                
                # Tab: 信号列表 (全量)
                with ui.tab_panel(tab_signals):
                    if app.signal_manager:
                        app.signal_manager.render_main_list()

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
                                <li>点击左上角菜单按钮，在左侧抽屉中选择要监控的信号（至少选一个）</li>
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
                    
                    # 初始化时创建一个空图表，使用延迟初始化（defer_init=True）
                    # 因为图表不在初始 tab 页，所以延迟 JavaScript 初始化
                    # 使用一个信号作为占位符
                    initial_signal_types = {
                        'placeholder_[0]': {'type': 'numeric'}
                    }
                    
                    with app.chart_container:
                        # 使用 EChartWidget，延迟初始化
                        # 图表元素会自动添加到当前的 UI 上下文中
                        app.echart_widget = EChartWidget(
                            signal_types=initial_signal_types,
                            window_seconds=30.0,
                            defer_init=True
                        )
                        print(f"[EChart Widget] 创建完成，延迟初始化模式")
                        
                        # 显示提示信息
                        with ui.card().classes('w-full').style('margin-top: 20px; background-color: #e3f2fd;'):
                            ui.label('👈 请点击左上角菜单按钮选择信号').classes('text-h6').style(
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

