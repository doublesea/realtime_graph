"""
使用示例：演示如何使用重构后的绘图控件和数据生成器

展示了两种使用方式：
1. 使用 update_data 进行全量数据更新
2. 使用 append_data 进行增量数据追加
"""
import pandas as pd
from datetime import datetime, timedelta
from data_generator import DataGenerator
from realtime_plot import RealtimePlot


def example_1_batch_generation():
    """
    示例 1：批量生成数据并使用 update_data 更新图表
    注意：不同信号有不同的采样周期，非采样时间点的值为 NaN（空值）
    """
    print("=" * 60)
    print("示例 1：批量生成数据")
    print("=" * 60)
    
    # 初始化数据生成器：4个信号，基础采样率 5Hz
    generator = DataGenerator(num_signals=4, base_sample_rate=5.0)
    
    # 显示信号参数信息
    signal_info = generator.get_signal_info()
    print("\n信号参数信息：")
    print(signal_info.to_string(index=False))
    print("\n注意：period_multiplier 表示采样周期倍数")
    print("例如：倍数为3表示每3个基础周期采样1次，其余时间点为NaN")
    
    # 批量生成 100 个数据点
    print("\n生成 100 个数据点...")
    batch_data = generator.generate_batch_data(num_points=100)
    print(f"生成的数据形状: {batch_data.shape}")
    print(f"时间范围: {batch_data['timestamp'].min()} 到 {batch_data['timestamp'].max()}")
    
    # 统计每个信号的有效采样点数
    print("\n每个信号的有效采样统计（共100个时间点）:")
    for col in batch_data.columns:
        if col != 'timestamp':
            valid_count = batch_data[col].notna().sum()
            nan_count = batch_data[col].isna().sum()
            print(f"  {col}: 有效={valid_count}, 空值={nan_count}")
    
    print("\n前 5 行数据:")
    print(batch_data.head())
    
    # 初始化绘图控件
    plot = RealtimePlot(num_signals=4, window_seconds=60.0)
    
    # 使用 update_data 更新图表（完全替换）
    plot.update_data(batch_data)
    print("\n图表已更新（使用 update_data）")
    
    # 获取缓存的数据
    buffered = plot.get_buffered_data()
    print(f"图表缓存的数据点数: {len(buffered) if buffered is not None else 0}")


def example_2_incremental_generation():
    """
    示例 2：逐点生成数据并使用 append_data 增量更新图表
    """
    print("\n" + "=" * 60)
    print("示例 2：增量生成数据")
    print("=" * 60)
    
    # 初始化数据生成器：6个信号，基础采样率 10Hz
    generator = DataGenerator(num_signals=6, base_sample_rate=10.0)
    
    # 显示信号参数信息
    signal_info = generator.get_signal_info()
    print("\n信号参数信息：")
    print(signal_info.to_string(index=False))
    
    # 初始化绘图控件
    plot = RealtimePlot(num_signals=6, window_seconds=30.0)
    
    # 模拟实时数据生成：逐点生成并追加
    print("\n逐点生成 50 个数据点...")
    for i in range(50):
        # 生成单个数据点
        new_data = generator.generate_next_data()
        
        # 使用 append_data 增量添加到图表
        plot.append_data(new_data)
        
        if (i + 1) % 10 == 0:
            buffered = plot.get_buffered_data()
            print(f"  已生成 {i + 1} 个点，图表缓存: {len(buffered) if buffered is not None else 0} 个点")
    
    print("\n完成增量数据生成和图表更新")


def example_3_mixed_usage():
    """
    示例 3：混合使用 - 先批量加载历史数据，然后增量添加新数据
    """
    print("\n" + "=" * 60)
    print("示例 3：混合使用（批量 + 增量）")
    print("=" * 60)
    
    # 初始化
    generator = DataGenerator(num_signals=3, base_sample_rate=5.0)
    plot = RealtimePlot(num_signals=3, window_seconds=60.0)
    
    # 第一步：批量生成历史数据
    print("\n第一步：批量生成 200 个历史数据点...")
    historical_data = generator.generate_batch_data(num_points=200)
    plot.update_data(historical_data)
    
    buffered = plot.get_buffered_data()
    print(f"历史数据加载完成，图表缓存: {len(buffered) if buffered is not None else 0} 个点")
    
    # 第二步：模拟实时增量更新
    print("\n第二步：增量添加 30 个新数据点...")
    for i in range(30):
        new_data = generator.generate_next_data()
        plot.append_data(new_data)
        
        if (i + 1) % 10 == 0:
            buffered = plot.get_buffered_data()
            print(f"  已添加 {i + 1} 个新点，图表缓存: {len(buffered) if buffered is not None else 0} 个点")
    
    # 显示最终数据范围
    final_data = plot.get_buffered_data()
    if final_data is not None:
        print(f"\n最终数据统计:")
        print(f"  总数据点数: {len(final_data)}")
        print(f"  时间跨度: {(final_data['timestamp'].max() - final_data['timestamp'].min()).total_seconds():.1f} 秒")
        print(f"  时间范围: {final_data['timestamp'].min()} 到 {final_data['timestamp'].max()}")


def example_4_clear_and_reset():
    """
    示例 4：清空数据和重置
    """
    print("\n" + "=" * 60)
    print("示例 4：清空和重置")
    print("=" * 60)
    
    # 初始化
    generator = DataGenerator(num_signals=2, base_sample_rate=5.0)
    plot = RealtimePlot(num_signals=2, window_seconds=30.0)
    
    # 生成一些数据
    print("\n生成 50 个数据点...")
    batch_data = generator.generate_batch_data(num_points=50)
    plot.update_data(batch_data)
    
    buffered = plot.get_buffered_data()
    print(f"数据点数: {len(buffered) if buffered is not None else 0}")
    
    # 清空图表数据
    print("\n清空图表数据...")
    plot.clear_data()
    
    buffered = plot.get_buffered_data()
    print(f"清空后数据点数: {len(buffered) if buffered is not None else 0}")
    
    # 重置生成器
    print("\n重置数据生成器...")
    generator.reset()
    print("生成器已重置，计数器归零")
    
    # 重新生成数据
    print("\n重新生成 20 个数据点...")
    new_batch = generator.generate_batch_data(num_points=20)
    plot.update_data(new_batch)
    
    buffered = plot.get_buffered_data()
    print(f"重新加载后数据点数: {len(buffered) if buffered is not None else 0}")


if __name__ == '__main__':
    # 运行所有示例
    example_1_batch_generation()
    example_2_incremental_generation()
    example_3_mixed_usage()
    example_4_clear_and_reset()
    
    print("\n" + "=" * 60)
    print("所有示例运行完成！")
    print("=" * 60)

