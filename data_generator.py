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
    """模拟实时设备数据生成器（支持不同信号周期和枚举类型）"""
    
    def __init__(self, num_signals: int = 50, base_sample_rate: float = 5.0, enum_signal_indices: Optional[List[int]] = None):
        """
        初始化数据生成器
        
        Args:
            num_signals: 信号通道数量（最多20个）
            base_sample_rate: 基础采样频率（Hz，每秒采样次数）
            enum_signal_indices: 枚举信号的索引列表（从0开始），例如 [2, 3] 表示 signal_3 和 signal_4 是枚举类型
        """
        self.num_signals = min(num_signals, 20)
        self.base_sample_rate = base_sample_rate
        self.base_interval = 1.0 / base_sample_rate  # 基础采样间隔（秒）
        
        # 设置枚举信号索引（默认最后两个信号为枚举类型）
        if enum_signal_indices is None:
            # 默认：如果有4个或以上信号，最后两个为枚举类型
            self.enum_signal_indices = set(range(max(0, self.num_signals - 2), self.num_signals)) if self.num_signals >= 4 else set()
        else:
            self.enum_signal_indices = set(enum_signal_indices)
        
        # 定义枚举值映射（value -> label）
        self.enum_definitions = {
            'default': {
                0: '状态0 (OFF)',
                1: '状态1 (IDLE)',
                2: '状态2 (RUNNING)',
                3: '状态3 (ERROR)'
            },
            'boolean': {
                0: '关闭 (OFF)',
                1: '开启 (ON)'
            },
            'level': {
                0: '低',
                1: '中',
                2: '高'
            }
        }
        
        # 初始化数据存储：使用字典存储每个信号的时间序列
        self.data: Dict[str, List] = {
            'timestamp': [],
            **{f'signal_{i+1}': [] for i in range(self.num_signals)}
        }
        
        # 为每个信号生成不同的参数（频率、相位、幅度、周期）
        self.signal_params = []
        np.random.seed(42)  # 固定随机种子以保证可重复性
        
        # 固定的采样周期设置（针对4个信号）
        # 基础周期设为 10ms (100Hz)，目标周期：20ms, 50ms, 100ms, 200ms
        fixed_period_multipliers = [2, 5, 10, 20]  # 对应 20ms, 50ms, 100ms, 200ms
        
        for i in range(self.num_signals):
            # 使用固定的周期倍数（前4个信号使用固定值，多余的信号循环使用）
            period_multiplier = fixed_period_multipliers[i % len(fixed_period_multipliers)]
            
            # 判断是否为枚举类型
            is_enum = i in self.enum_signal_indices
            
            if is_enum:
                # 枚举信号参数
                # 为不同枚举信号分配不同的枚举定义
                if i % 3 == 0:
                    enum_type = 'default'
                    enum_values = [0, 1, 2, 3]
                elif i % 3 == 1:
                    enum_type = 'boolean'
                    enum_values = [0, 1]
                else:
                    enum_type = 'level'
                    enum_values = [0, 1, 2]
                
                self.signal_params.append({
                    'type': 'enum',
                    'enum_type': enum_type,
                    'enum_values': enum_values,
                    'enum_labels': self.enum_definitions[enum_type],
                    'transition_probability': 0.05,  # 状态转换概率（5%）
                    'current_value': np.random.choice(enum_values),  # 初始状态
                    'period_multiplier': period_multiplier,
                    'last_update_counter': 0
                })
            else:
                # 数值信号参数
                self.signal_params.append({
                    'type': 'numeric',
                    'frequency': 0.1 + np.random.uniform(0, 0.5),  # 随机频率 0.1-0.6 Hz
                    'phase': np.random.uniform(0, 2 * np.pi),  # 随机相位
                    'amplitude': 1.0 + np.random.uniform(0, 2.0),  # 随机幅度 1.0-3.0
                    'offset': i * 0.3,  # 不同偏移以便区分
                    'noise': np.random.uniform(0.05, 0.2),  # 随机噪声水平
                    'period_multiplier': period_multiplier,  # 采样周期倍数（固定）
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
                     没有更新的信号值为 NaN（空值）
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
                if params['type'] == 'enum':
                    # 枚举信号：随机状态转换
                    if np.random.random() < params['transition_probability']:
                        # 状态转换：随机选择一个不同的状态
                        available_values = [v for v in params['enum_values'] if v != params['current_value']]
                        if available_values:
                            params['current_value'] = np.random.choice(available_values)
                    value = float(params['current_value'])  # 枚举值存储为浮点数
                else:
                    # 数值信号：生成正弦波 + 噪声
                    value = (
                        params['amplitude'] * np.sin(2 * np.pi * params['frequency'] * t + params['phase']) +
                        params['offset'] +
                        np.random.normal(0, params['noise'])
                    )
                    params['last_value'] = value  # 保存最后一个有效值
                
                row_data[signal_name] = value
                params['last_update_counter'] = self.counter
            else:
                # 当前时间点没有采样，值为 NaN（空）
                row_data[signal_name] = np.nan
        
        # 添加到内部存储（保持 NaN 值，不填充）
        self.data['timestamp'].append(current_time)
        for i in range(self.num_signals):
            signal_name = f'signal_{i+1}'
            # 内部存储也保持 NaN 值，真实反映采样情况
            self.data[signal_name].append(row_data[signal_name])
        
        self.counter += 1
        
        # 返回 DataFrame（包含 NaN 值）
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
            # 计算实际采样周期（毫秒）
            sample_period_ms = (params['period_multiplier'] * self.base_interval) * 1000
            
            info = {
                'signal': f'signal_{i+1}',
                'type': params['type'],
                'sample_period_ms': sample_period_ms,  # 采样周期（毫秒）
                'effective_sample_rate': self.base_sample_rate / params['period_multiplier']
            }
            
            if params['type'] == 'enum':
                # 枚举信号的特定信息
                enum_labels_str = ', '.join([f"{v}:{params['enum_labels'][v]}" for v in params['enum_values']])
                info['enum_type'] = params['enum_type']
                info['enum_values'] = enum_labels_str
                info['frequency'] = '-'
                info['amplitude'] = '-'
                info['offset'] = '-'
            else:
                # 数值信号的特定信息
                info['enum_type'] = '-'
                info['enum_values'] = '-'
                info['frequency'] = params['frequency']
                info['amplitude'] = params['amplitude']
                info['offset'] = params['offset']
            
            info_list.append(info)
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
            # 如果是枚举信号，重置当前状态为随机值
            if params['type'] == 'enum':
                params['current_value'] = np.random.choice(params['enum_values'])

