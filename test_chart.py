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
                <li>时间跨度：60秒，共600个数据点</li>
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
    
    # 初始化 RealtimePlot
    realtime_plot = RealtimePlot(num_signals=4, window_seconds=60.0, signal_types=signal_types)
    
    # 将数据加载到绘图控件
    realtime_plot.update_data(df)
    
    # 获取配置
    option = realtime_plot.get_option()
    
    # 显示数据统计
    with ui.card().classes('w-full p-4'):
        ui.label('📈 数据统计').classes('text-h6 mb-2')
        with ui.row().classes('gap-4'):
            ui.label(f'数据点数：{len(df)}')
            ui.label(f'信号数量：{len(signal_types)}')
            ui.label(f'时间跨度：{(df["timestamp"].max() - df["timestamp"].min()).total_seconds():.1f} 秒')
    
    # 创建图表
    with ui.card().classes('w-full').style('overflow-y: scroll; max-height: 85vh; padding: 10px;'):
        chart_widget = RealtimeChartWidget(option)
        # 更新枚举标签映射
        chart_widget.update_enum_labels(signal_types)
    
    # 使用提示
    with ui.card().classes('w-full p-2').style('background-color: #fff3e0;'):
        ui.html('''
        <div style="font-size: 12px; color: #e65100;">
            <b>💡 交互提示：</b>
            <span style="margin-left:10px;">• 拖动底部滑块缩放时间轴</span>
            <span style="margin-left:10px;">• 使用 Ctrl+滚轮 缩放</span>
            <span style="margin-left:10px;">• 鼠标悬停查看数据点详情</span>
        </div>
        ''', sanitize=False)


# 启动应用
if __name__ in {'__main__', '__mp_main__'}:
    ui.run(port=8081, title='Chart Widget Test')

