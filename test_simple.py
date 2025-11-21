"""
简化测试 - 验证tooltip和竖线
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from nicegui import ui
from realtime_plot import RealtimePlot
from chart_widget import RealtimeChartWidget


@ui.page('/')
def test_page():
    ui.page_title('Simple Test')
    
    # 创建测试数据
    timestamps = [datetime.now() + timedelta(seconds=i) for i in range(100)]
    data = pd.DataFrame({
        'timestamp': timestamps,
        'signal_1': np.sin(np.linspace(0, 4*np.pi, 100)) * 2 + 1,
        'signal_2': np.cos(np.linspace(0, 3*np.pi, 100)) * 1.5 + 2,
        'signal_3': np.random.randn(100).cumsum() * 0.1 + 3,
    })
    
    signal_types = {
        'signal_1': {'type': 'numeric'},
        'signal_2': {'type': 'numeric'},
        'signal_3': {'type': 'numeric'},
    }
    
    ui.label('Simple Chart Test - Check Console (F12)').classes('text-h5')
    
    with ui.card().classes('w-full'):
        realtime_plot = RealtimePlot(
            num_signals=3,
            window_seconds=60.0,
            signal_types=signal_types
        )
        realtime_plot.update_data(data)
        
        option = realtime_plot.get_option()
        chart_widget = RealtimeChartWidget(option)
        chart_widget.update_enum_labels(signal_types)
    
    # 添加测试按钮
    def test_console():
        ui.run_javascript('''
            console.log('=== Manual Test ===');
            console.log('window.chartInstances:', window.chartInstances);
            if (window.chartInstances && window.chartInstances[1]) {
                console.log('Instance 1 exists:', window.chartInstances[1]);
                console.log('tooltipFormatter:', typeof window.chartInstances[1].tooltipFormatter);
            } else {
                console.log('ERROR: window.chartInstances[1] not found!');
            }
        ''')
        ui.notify('Check console', type='info')
    
    ui.button('Test Console', on_click=test_console, icon='bug_report').props('color=red')


if __name__ in {'__main__', '__mp_main__'}:
    ui.run(port=8083, title='Simple Test')

