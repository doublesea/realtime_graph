"""
测试数据生成器
生成 DataFrame 格式的多信号时间序列数据
支持随机生成一批数据，不同信号的数据周期不一致
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional


class DataGenerator:
    """模拟实时设备数据生成器（支持不同信号周期）"""
    
    def __init__(self, num_signals: int = 50, base_sample_rate: float = 5.0):
        """
        初始化数据生成器
        
        Args:
            num_signals: 信号通道数量（最多20个）
            base_sample_rate: 基础采样频率（Hz，每秒采样次数）
        """
        self.num_signals = min(num_signals, 20)
        self.base_sample_rate = base_sample_rate
        self.base_interval = 1.0 / base_sample_rate  # 基础采样间隔（秒）
        
        # 初始化数据存储：使用字典存储每个信号的时间序列
        self.data: Dict[str, List] = {
            'timestamp': [],
            **{f'signal_{i+1}': [] for i in range(self.num_signals)}
        }
        
        # 为每个信号生成不同的参数（频率、相位、幅度、周期）
        self.signal_params = []
        np.random.seed(42)  # 固定随机种子以保证可重复性
        for i in range(self.num_signals):
            # 每个信号有不同的采样周期（相对于基础周期的倍数）
            period_multiplier = np.random.choice([1, 2, 3, 5])  # 1x, 2x, 3x, 5x 基础周期
            
            self.signal_params.append({
                'frequency': 0.1 + np.random.uniform(0, 0.5),  # 随机频率 0.1-0.6 Hz
                'phase': np.random.uniform(0, 2 * np.pi),  # 随机相位
                'amplitude': 1.0 + np.random.uniform(0, 2.0),  # 随机幅度 1.0-3.0
                'offset': i * 0.3,  # 不同偏移以便区分
                'noise': np.random.uniform(0.05, 0.2),  # 随机噪声水平
                'period_multiplier': period_multiplier,  # 采样周期倍数
                'last_update_counter': 0  # 上次更新的计数器值
            })
        
        self.start_time = datetime.now()
        self.counter = 0
    
    def generate_next_data(self) -> pd.DataFrame:
        """
        生成下一批数据点（增量生成）
        每个信号根据其周期倍数决定是否更新
        
        Returns:
            DataFrame: 包含 timestamp 和本次更新的信号列的数据
                     没有更新的信号将使用 NaN 或上一个值
        """
        current_time = self.start_time + timedelta(seconds=self.counter * self.base_interval)
        
        # 准备本次数据行
        row_data = {'timestamp': current_time}
        
        # 为每个信号判断是否需要更新
        t = self.counter * self.base_interval
        for i in range(self.num_signals):
            params = self.signal_params[i]
            signal_name = f'signal_{i+1}'
            
            # 检查是否到了这个信号的更新周期
            if self.counter % params['period_multiplier'] == 0:
                # 生成正弦波 + 噪声
                value = (
                    params['amplitude'] * np.sin(2 * np.pi * params['frequency'] * t + params['phase']) +
                    params['offset'] +
                    np.random.normal(0, params['noise'])
                )
                row_data[signal_name] = value
                params['last_update_counter'] = self.counter
            else:
                # 使用上一个值（线性插值或保持不变）
                if len(self.data[signal_name]) > 0:
                    row_data[signal_name] = self.data[signal_name][-1]
                else:
                    row_data[signal_name] = params['offset']
        
        # 添加到内部存储
        self.data['timestamp'].append(current_time)
        for i in range(self.num_signals):
            signal_name = f'signal_{i+1}'
            self.data[signal_name].append(row_data[signal_name])
        
        self.counter += 1
        
        # 返回 DataFrame
        return pd.DataFrame([row_data])
    
    def generate_batch_data(self, num_points: int) -> pd.DataFrame:
        """
        一次性生成一批数据点
        
        Args:
            num_points: 生成的数据点数量
            
        Returns:
            DataFrame: 包含 timestamp 和所有信号列的数据
        """
        batch_data = []
        for _ in range(num_points):
            data_point = self.generate_next_data()
            batch_data.append(data_point)
        
        if batch_data:
            return pd.concat(batch_data, ignore_index=True)
        return pd.DataFrame()
    
    def get_all_data(self) -> pd.DataFrame:
        """
        获取所有累积的数据
        
        Returns:
            DataFrame: 包含所有时间戳和信号的数据
        """
        return pd.DataFrame(self.data)
    
    def get_recent_data(self, window_seconds: float = 60.0) -> pd.DataFrame:
        """
        获取最近指定时间窗口内的数据
        
        Args:
            window_seconds: 时间窗口大小（秒）
            
        Returns:
            DataFrame: 最近时间窗口内的数据
        """
        if not self.data['timestamp']:
            return pd.DataFrame()
        
        current_time = self.data['timestamp'][-1]
        cutoff_time = current_time - timedelta(seconds=window_seconds)
        
        # 找到第一个在时间窗口内的索引
        valid_indices = [
            i for i, ts in enumerate(self.data['timestamp'])
            if ts >= cutoff_time
        ]
        
        if not valid_indices:
            return pd.DataFrame()
        
        # 提取有效数据
        result = {
            'timestamp': [self.data['timestamp'][idx] for idx in valid_indices],
            **{f'signal_{sig_idx+1}': [self.data[f'signal_{sig_idx+1}'][idx] for idx in valid_indices]
               for sig_idx in range(self.num_signals)}
        }
        
        return pd.DataFrame(result)
    
    def get_signal_info(self) -> pd.DataFrame:
        """
        获取所有信号的参数信息
        
        Returns:
            DataFrame: 包含每个信号的参数信息
        """
        info_list = []
        for i, params in enumerate(self.signal_params):
            info_list.append({
                'signal': f'signal_{i+1}',
                'frequency': params['frequency'],
                'amplitude': params['amplitude'],
                'offset': params['offset'],
                'period_multiplier': params['period_multiplier'],
                'effective_sample_rate': self.base_sample_rate / params['period_multiplier']
            })
        return pd.DataFrame(info_list)
    
    def reset(self):
        """重置数据生成器（保留信号参数配置）"""
        self.data = {
            'timestamp': [],
            **{f'signal_{i+1}': [] for i in range(self.num_signals)}
        }
        self.start_time = datetime.now()
        self.counter = 0
        
        # 重置各信号的上次更新计数器
        for params in self.signal_params:
            params['last_update_counter'] = 0

