# 快速开始指南

## 🚀 立即运行

### 1. 启动 Web 界面（推荐）

```bash
python main.py
```

然后在浏览器中打开：`http://localhost:8080`

### 2. 运行测试示例

```bash
python example_usage.py
```

## 💡 核心概念

### 绘图控件（RealtimePlot）

```python
from realtime_plot import RealtimePlot

# 初始化：4个信号，60秒时间窗口
plot = RealtimePlot(num_signals=4, window_seconds=60.0)

# 方式1：完全更新（替换所有数据）
plot.update_data(dataframe)

# 方式2：增量添加（追加新数据）
plot.append_data(new_dataframe)

# 清空数据
plot.clear_data()

# 获取当前缓存数据
data = plot.get_buffered_data()
```

### 数据生成器（DataGenerator）

```python
from data_generator import DataGenerator

# 初始化：4个信号，基础采样率5Hz
generator = DataGenerator(num_signals=4, base_sample_rate=5.0)

# 查看信号参数（每个信号有不同的采样周期！）
print(generator.get_signal_info())

# 方式1：生成单个数据点
data_point = generator.generate_next_data()

# 方式2：批量生成多个数据点
batch_data = generator.generate_batch_data(num_points=100)

# 重置
generator.reset()
```

## 🎯 关键特性

### ✅ 不同信号不同周期

每个信号有独立的采样周期倍数（1x, 2x, 3x, 5x）：

- **Signal 1**: 周期倍数 3x → 有效采样率 = 5/3 = 1.67 Hz
- **Signal 2**: 周期倍数 2x → 有效采样率 = 5/2 = 2.5 Hz  
- **Signal 3**: 周期倍数 5x → 有效采样率 = 5/5 = 1.0 Hz
- **Signal 4**: 周期倍数 1x → 有效采样率 = 5/1 = 5.0 Hz

### ✅ 数据格式统一

所有数据使用 DataFrame 格式：

```python
import pandas as pd
from datetime import datetime

data = pd.DataFrame({
    'timestamp': [datetime.now(), ...],  # 必须：datetime 类型
    'signal_1': [1.0, 2.0, ...],        # 信号值
    'signal_2': [3.0, 4.0, ...],        # 信号值
    # ... 更多信号
})
```

### ✅ 自动时间窗口管理

绘图控件自动管理时间窗口，超出窗口的数据会被自动裁剪，节省内存。

## 📊 典型使用场景

### 场景1：实时数据流

```python
# 初始化
generator = DataGenerator(num_signals=4, base_sample_rate=5.0)
plot = RealtimePlot(num_signals=4, window_seconds=60.0)

# 实时循环
while True:
    new_data = generator.generate_next_data()
    plot.append_data(new_data)
    # ... 更新显示
```

### 场景2：加载历史数据

```python
# 加载大量历史数据
historical_data = generator.generate_batch_data(num_points=1000)
plot.update_data(historical_data)

# 然后切换到实时模式
while True:
    new_data = generator.generate_next_data()
    plot.append_data(new_data)
```

### 场景3：周期性批量更新

```python
# 每次生成一批数据
while True:
    batch = generator.generate_batch_data(num_points=10)
    plot.append_data(batch)
    time.sleep(1)  # 等待1秒
```

## 🎨 界面功能

- **启动按钮**：开始实时绘图
- **停止按钮**：暂停更新
- **重置按钮**：清空数据并重新初始化
- **信号数量**：可调整（1-20）
- **更新频率**：图表刷新频率（毫秒）
- **基础采样率**：数据生成频率（Hz）

## 📝 注意事项

1. **信号命名**：必须使用 `signal_1`, `signal_2`, ..., `signal_N` 格式
2. **时间戳类型**：必须是 Python `datetime` 对象
3. **信号数量匹配**：DataFrame 的信号数量要与初始化时指定的数量一致
4. **数据排序**：`append_data` 会自动按时间戳排序

## 🔍 调试技巧

### 查看信号参数

```python
info = generator.get_signal_info()
print(info)
```

输出示例：
```
  signal  frequency  amplitude  offset  period_multiplier  effective_sample_rate
signal_1   0.498271   2.559382     0.0                  3               1.666667
signal_2   0.177997   2.732352     0.3                  2               2.500000
```

### 查看缓存数据

```python
buffered = plot.get_buffered_data()
print(f"缓存数据点数: {len(buffered)}")
print(f"时间范围: {buffered['timestamp'].min()} 到 {buffered['timestamp'].max()}")
```

---

更多详细信息请查看 `README_重构说明.md`

