"""
模拟数据生成器
生成 DataFrame 格式的多信号时间序列数据
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict


class DataGenerator:
    """模拟实时设备数据生成器"""
    
    def __init__(self, num_signals: int = 20, sample_rate: float = 5.0):
        """
        初始化数据生成器
        
        Args:
            num_signals: 信号通道数量（最多20个）
            sample_rate: 采样频率（Hz，每秒采样次数）
        """
        self.num_signals = min(num_signals, 20)
        self.sample_rate = sample_rate
        self.interval = 1.0 / sample_rate  # 采样间隔（秒）
        
        # 初始化数据存储：使用字典存储每个信号的时间序列
        self.data: Dict[str, List] = {
            'timestamp': [],
            **{f'signal_{i+1}': [] for i in range(self.num_signals)}
        }
        
        # 为每个信号生成不同的参数（频率、相位、幅度）
        self.signal_params = []
        for i in range(self.num_signals):
            self.signal_params.append({
                'frequency': 0.1 + i * 0.05,  # 不同频率
                'phase': i * 0.3,  # 不同相位
                'amplitude': 1.0 + i * 0.1,  # 不同幅度
                'offset': i * 0.5,  # 不同偏移
                'noise': 0.1  # 噪声水平
            })
        
        self.start_time = datetime.now()
        self.counter = 0
    
    def generate_next_data(self) -> pd.DataFrame:
        """
        生成下一批数据点
        
        Returns:
            DataFrame: 包含 timestamp 和所有信号列的数据
        """
        current_time = self.start_time + timedelta(seconds=self.counter * self.interval)
        
        # 生成时间戳
        self.data['timestamp'].append(current_time)
        
        # 为每个信号生成数据点
        t = self.counter * self.interval
        for i in range(self.num_signals):
            params = self.signal_params[i]
            # 生成正弦波 + 噪声
            value = (
                params['amplitude'] * np.sin(2 * np.pi * params['frequency'] * t + params['phase']) +
                params['offset'] +
                np.random.normal(0, params['noise'])
            )
            self.data[f'signal_{i+1}'].append(value)
        
        self.counter += 1
        
        # 返回 DataFrame
        return pd.DataFrame({
            'timestamp': [self.data['timestamp'][-1]],
            **{f'signal_{i+1}': [self.data[f'signal_{i+1}'][-1]] 
               for i in range(self.num_signals)}
        })
    
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
    
    def reset(self):
        """重置数据生成器"""
        self.data = {
            'timestamp': [],
            **{f'signal_{i+1}': [] for i in range(self.num_signals)}
        }
        self.start_time = datetime.now()
        self.counter = 0

