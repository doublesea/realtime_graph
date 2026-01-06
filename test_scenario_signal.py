
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from nicegui import ui
from echart_widget import EChartWidget

def create_test_data():
    """
    根据场景生成测试数据：
    1. 信号1在29s有一个点
    2. 信号2在30s到35s有一段信号
    3. 信号1在36s有一个点
    """
    # 以当前时间作为参考
    now = datetime.now().replace(microsecond=0)
    # 为了方便观察，我们将起始点设为 0s
    start_time = now
    
    data = []
    
    # 1. 信号1在29s有一个点
    data.append({
        'timestamp': start_time + timedelta(seconds=29),
        'signal_1': 10.5,
        'signal_2': np.nan
    })
    
    # 2. 信号2在30s到35s有一段信号 (每隔0.5s一个点)
    for i in range(0, 11):  # 0s to 5s, total 11 points for 5.5s span
        t = 30 + i * 0.5
        data.append({
            'timestamp': start_time + timedelta(seconds=t),
            'signal_1': np.nan,
            'signal_2': 20 + np.sin(i * 0.5) * 5
        })
        
    # 3. 信号1在36s有一个点
    data.append({
        'timestamp': start_time + timedelta(seconds=36),
        'signal_1': 15.2,
        'signal_2': np.nan
    })
    
    df = pd.DataFrame(data)
    # 按时间戳排序
    df = df.sort_values('timestamp').reset_index(drop=True)
    return df

@ui.page('/')
def main():
    ui.label('信号测试场景').classes('text-h4 mb-4')
    ui.markdown('''
    ### 测试场景描述：
    1. **信号1**：在 29s 有一个孤立点，在 36s 有另一个孤立点。
    2. **信号2**：在 30s 到 35s 之间有一段连续的信号。
    
    *注意：由于 ECharts 配置了 `connectNulls: False` 且 `max_time_gap_seconds: 1.0`，信号1的两个点之间不应该连线。*
    ''')
    
    # 定义信号类型
    signal_types = {
        'signal_1': {'type': 'numeric', 'label': '信号 1'},
        'signal_2': {'type': 'numeric', 'label': '信号 2'}
    }
    
    # 创建图表控件，设置窗口大小为 60s 以便看全所有点
    chart = EChartWidget(signal_types=signal_types, window_seconds=60.0)
    
    # 生成并加载测试数据
    df = create_test_data()
    chart.update_data(df)
    
    with ui.row().classes('mt-4'):
        ui.button('重新加载数据', on_click=lambda: chart.update_data(create_test_data()))
        ui.button('清空数据', on_click=chart.clear_data)

if __name__ in {'__main__', '__mp_main__'}:
    ui.run(port=8083, title='信号测试场景')

