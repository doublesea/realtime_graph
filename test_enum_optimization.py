"""
测试枚举值Y轴优化
只显示实际出现的枚举值
"""
import pandas as pd
from datetime import datetime, timedelta
from nicegui import ui
from realtime_plot import RealtimePlot
from chart_widget import RealtimeChartWidget


# 定义一个有很多枚举值的信号类型
signal_types = {
    'device_status': {
        'type': 'enum',
        'enum_labels': {
            0: 'INIT',
            1: 'IDLE',
            2: 'STARTING',
            3: 'RUNNING',
            4: 'PAUSED',
            5: 'STOPPING',
            6: 'STOPPED',
            7: 'ERROR',
            8: 'WARNING',
            9: 'MAINTENANCE',
            10: 'CALIBRATION',
            11: 'TESTING',
            12: 'SHUTDOWN',
            13: 'EMERGENCY',
            14: 'RECOVERY',
            15: 'DIAGNOSTIC',
            16: 'STANDBY',
            17: 'SLEEP',
            18: 'HIBERNATE',
            19: 'REBOOT'
        }
    }
}


def create_test_data():
    """创建测试数据，只使用部分枚举值"""
    timestamps = []
    values = []
    
    start_time = datetime.now()
    
    # 只使用3, 4, 7三个枚举值（RUNNING, PAUSED, ERROR）
    for i in range(100):
        timestamps.append(start_time + timedelta(seconds=i * 0.1))
        
        # 循环使用这三个值
        if i % 30 < 10:
            values.append(3)  # RUNNING
        elif i % 30 < 20:
            values.append(4)  # PAUSED
        else:
            values.append(7)  # ERROR
    
    df = pd.DataFrame({
        'timestamp': timestamps,
        'device_status': values
    })
    
    return df


@ui.page('/')
def main_page():
    """主页面"""
    ui.label('枚举值Y轴优化测试').classes('text-2xl font-bold mb-4')
    ui.label('定义了20个枚举值（0-19），但只显示实际出现的3个值（3, 4, 7）').classes('text-gray-600 mb-4')
    
    # 创建实时绘图对象
    plot = RealtimePlot(signal_types=signal_types, window_seconds=30)
    
    # 创建测试数据
    test_df = create_test_data()
    
    # 更新数据
    plot.update_data(test_df)
    
    # 显示图表
    with ui.card().classes('w-full'):
        ui.label('设备状态图表').classes('text-xl font-bold')
        chart = RealtimeChartWidget(initial_option=plot.option)
        chart.update_enum_labels(signal_types)
    
    # 添加数据信息
    with ui.card().classes('w-full mt-4'):
        ui.label('数据信息').classes('text-lg font-bold mb-2')
        ui.label(f'数据点数: {len(test_df)}')
        ui.label(f'定义的枚举值: 0-19 (共20个)')
        ui.label(f'实际出现的值: 3 (RUNNING), 4 (PAUSED), 7 (ERROR)')
        ui.label('Y轴应该只显示这3个枚举值，而不是全部20个')
    
    # 添加刷新按钮
    def refresh_data():
        """刷新数据 - 使用不同的枚举值"""
        new_timestamps = []
        new_values = []
        
        start_time = datetime.now()
        
        # 这次使用1, 2, 9三个值（IDLE, STARTING, MAINTENANCE）
        for i in range(100):
            new_timestamps.append(start_time + timedelta(seconds=i * 0.1))
            
            if i % 30 < 10:
                new_values.append(1)  # IDLE
            elif i % 30 < 20:
                new_values.append(2)  # STARTING
            else:
                new_values.append(9)  # MAINTENANCE
        
        new_df = pd.DataFrame({
            'timestamp': new_timestamps,
            'device_status': new_values
        })
        
        plot.update_data(new_df)
        chart.update_chart_option(plot.option)
        ui.notify('数据已刷新，现在应显示: IDLE, STARTING, MAINTENANCE')
    
    ui.button('刷新数据（切换到其他枚举值）', on_click=refresh_data).classes('mt-4')


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(port=8084, title='枚举值Y轴优化测试')

