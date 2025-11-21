# 时间戳无时区偏移修复

## 问题描述

原始代码中，时间戳在Python和JavaScript之间传递时会进行时区转换，导致显示的时间与数据中的原始时间不一致。

## 原始逻辑的问题

### 之前的流程

```
Python端:
  datetime.now()           → 2025-11-21 19:57:41 (本地时间)
  ↓
  .timestamp()             → 转为UTC时间戳 (考虑时区)
  ↓
  * 1000                   → 毫秒时间戳

JavaScript端:
  new Date(timestamp)      → 将UTC时间戳转为Date对象
  ↓
  getFullYear()等         → 转回本地时间显示
  ↓
  显示: 2025-11-21 19:57:41 (本地时间)
```

**问题**：
- 如果Python和浏览器在不同时区，显示的时间会不同
- 即使在同一时区，`.timestamp()` 方法会考虑系统时区，可能导致意外的偏移

## 修复方案

### 新的流程

```
Python端:
  datetime.now()                    → 2025-11-21 19:57:41
  ↓
  (x - epoch).total_seconds()       → 直接计算秒数，不考虑时区
  ↓
  * 1000                            → 毫秒数 (视为naive UTC)

JavaScript端:
  new Date(timestamp)               → Date对象
  ↓
  getUTCFullYear()等               → 使用UTC方法，不做时区转换
  ↓
  显示: 2025-11-21 19:57:41         → 与原始数据完全一致
```

**优点**：
- ✅ 数据是什么时间就显示什么时间
- ✅ 不受Python或浏览器时区影响
- ✅ 完全可预测的行为

## 代码修改

### 修改1：Python端 (realtime_plot.py)

**修改前**：
```python
# 将时间戳转换为 ECharts 时间格式（毫秒时间戳）
timestamps = df['timestamp'].apply(
    lambda x: int(x.timestamp() * 1000) if isinstance(x, datetime) else x  # ❌ 使用时区
).tolist()
```

**修改后**：
```python
# 将时间戳转换为 ECharts 时间格式（毫秒时间戳）
# 不使用时区转换，直接将datetime视为UTC时间
def datetime_to_ms(x):
    if isinstance(x, datetime):
        # 将datetime视为naive UTC时间，不考虑本地时区
        epoch = datetime(1970, 1, 1)
        return int((x - epoch).total_seconds() * 1000)
    else:
        return x

timestamps = df['timestamp'].apply(datetime_to_ms).tolist()
```

**关键点**：
- 使用 `(x - epoch).total_seconds()` 直接计算时间差
- 不调用 `.timestamp()` 方法，避免时区转换
- 将 datetime 视为 naive UTC 时间

### 修改2：JavaScript端 - Tooltip时间 (chart_widget.py)

**修改前**：
```javascript
// 格式化时间（日期+时间+毫秒）
const date = new Date(timestamp);
const year = date.getFullYear();        // ❌ 本地时区方法
const month = String(date.getMonth() + 1).padStart(2, '0');
const day = String(date.getDate()).padStart(2, '0');
const h = String(date.getHours()).padStart(2, '0');
const m = String(date.getMinutes()).padStart(2, '0');
const s = String(date.getSeconds()).padStart(2, '0');
const ms = String(date.getMilliseconds()).padStart(3, '0');
```

**修改后**：
```javascript
// 格式化时间（日期+时间+毫秒）
// 使用UTC方法，直接显示数据中的时间值，不做时区转换
const date = new Date(timestamp);
const year = date.getUTCFullYear();     // ✅ UTC方法
const month = String(date.getUTCMonth() + 1).padStart(2, '0');
const day = String(date.getUTCDate()).padStart(2, '0');
const h = String(date.getUTCHours()).padStart(2, '0');
const m = String(date.getUTCMinutes()).padStart(2, '0');
const s = String(date.getUTCSeconds()).padStart(2, '0');
const ms = String(date.getUTCMilliseconds()).padStart(3, '0');
```

**关键点**：
- 使用 `getUTC*()` 系列方法
- 不做任何时区转换
- 直接显示 UTC 时间（实际上是原始数据的时间值）

### 修改3：JavaScript端 - X轴时间标签 (chart_widget.py)

**问题**：X轴（横轴）使用ECharts内置的时间格式化模板 `{HH}:{mm}:{ss}.{SSS}`，会自动做时区转换。

**解决方案**：在JavaScript中统一设置X轴的自定义formatter。

在三个关键位置添加X轴formatter设置：

**位置1：初始化时**
```javascript
// 设置x轴formatter，避免时区转换
const option = el.chart.getOption();
const xAxisConfig = [];
if (option.xAxis) {
    for (let i = 0; i < option.xAxis.length; i++) {
        xAxisConfig.push({
            axisLabel: {
                formatter: function(value) {
                    const date = new Date(value);
                    const h = String(date.getUTCHours()).padStart(2, '0');
                    const m = String(date.getUTCMinutes()).padStart(2, '0');
                    const s = String(date.getUTCSeconds()).padStart(2, '0');
                    const ms = String(date.getUTCMilliseconds()).padStart(3, '0');
                    return h + ':' + m + ':' + s + '.' + ms;
                }
            }
        });
    }
}

el.chart.setOption({
    xAxis: xAxisConfig,
    // ... 其他配置
}, false);
```

**位置2：图表配置更新时（update_chart_option方法）**

在恢复tooltip配置的同时，恢复X轴formatter。

**位置3：finished事件中**

每次图表更新完成后，重新设置X轴formatter，防止被覆盖。

**关键点**：
- X轴formatter必须在多个位置设置，确保不被覆盖
- 使用 `getUTC*()` 方法保持一致性
- 为所有X轴设置相同的formatter

## 技术说明

### datetime.timestamp() vs 直接计算

| 方法 | 行为 | 时区影响 |
|------|------|---------|
| `x.timestamp()` | 返回UTC时间戳 | ✅ 考虑时区 |
| `(x - epoch).total_seconds()` | 直接计算时间差 | ❌ 不考虑时区 |

**示例**（假设在东八区）：
```python
from datetime import datetime

x = datetime(2025, 11, 21, 19, 57, 41)  # 本地时间

# 方法1：使用 timestamp()
ts1 = x.timestamp()  # 1732186661.0 (UTC时间戳)
# 实际表示: 2025-11-21 11:57:41 UTC (比本地少8小时)

# 方法2：直接计算
epoch = datetime(1970, 1, 1)
ts2 = (x - epoch).total_seconds()  # 1732215461.0
# 实际表示: 2025-11-21 19:57:41 (视为UTC，但值是本地时间)
```

### JavaScript Date 方法对比

| 方法 | 行为 | 时区影响 |
|------|------|---------|
| `getFullYear()` | 返回本地年份 | ✅ 转换为本地时区 |
| `getUTCFullYear()` | 返回UTC年份 | ❌ 不做时区转换 |

**示例**：
```javascript
const date = new Date(1732215461000);

// 本地方法（假设浏览器在东八区）
date.getHours()     // 3  (UTC时间 + 8小时)

// UTC方法
date.getUTCHours()  // 19 (UTC时间，不转换)
```

## 使用场景

### 适用场景

✅ **适合使用无时区转换的场景**：
- 数据采集时间与显示时间需要完全一致
- 多个不同时区的用户需要看到相同的时间
- 时间只是标记，不需要真实的时区概念
- 历史数据回放，需要显示记录时的原始时间

### 不适用场景

❌ **不适合使用无时区转换的场景**：
- 需要跨时区协作（每个用户看到本地时间）
- 需要真实的UTC时间戳（用于同步、排序等）
- 需要与其他系统交换时间数据（需要标准UTC格式）

## 测试验证

### 测试步骤

1. 运行程序：`python test_dynamic_chart.py`
2. 选择信号并开始
3. 鼠标悬停查看tooltip
4. 对比页面右上角的"当前时间"

### 预期结果

**页面右上角显示**：
```
当前时间: 2025-11-21 19:57:41
```

**Tooltip显示**：
```
2025-11-21 19:57:41.205
```

**X轴（横轴）显示**：
```
19:57:41.205
```

三者完全一致，都显示数据的原始时间值 ✅

## 注意事项

### 1. datetime对象必须是naive

```python
# ✅ 正确：naive datetime
dt = datetime.now()                    # 无时区信息
dt = datetime(2025, 11, 21, 19, 57, 41)

# ❌ 错误：aware datetime（带时区）
import pytz
dt = datetime.now(pytz.timezone('Asia/Shanghai'))  # 有时区信息
# 会导致计算错误
```

### 2. 跨时区数据交换

如果需要与其他系统交换数据：

```python
# 方案1：使用标准UTC时间戳
timestamp = dt.timestamp()  # 标准UTC时间戳

# 方案2：使用ISO格式字符串
iso_string = dt.isoformat()  # '2025-11-21T19:57:41'
```

### 3. 数据库存储

**推荐做法**：
- 数据库使用标准UTC时间戳存储
- 读取后转换为naive datetime（如果需要）
- 显示时使用本文档的方法

## 回滚方案

如果需要恢复原来的时区转换行为：

**Python端恢复**：
```python
timestamps = df['timestamp'].apply(
    lambda x: int(x.timestamp() * 1000) if isinstance(x, datetime) else x
).tolist()
```

**JavaScript端恢复**：
```javascript
const year = date.getFullYear();
const month = String(date.getMonth() + 1).padStart(2, '0');
// ... 其他本地方法
```

## 总结

| 方面 | 修改前 | 修改后 |
|------|--------|--------|
| Python转换 | `x.timestamp()` | `(x - epoch).total_seconds()` |
| Tooltip显示 | `get*()` 本地方法 | `getUTC*()` UTC方法 |
| X轴标签 | `{HH}:{mm}:{ss}` 模板 | 自定义UTC formatter |
| 时区影响 | ✅ 受时区影响 | ❌ 不受时区影响 |
| 显示结果 | 本地时间 | 原始数据时间 |
| 适用场景 | 需要时区转换 | 不需要时区转换 |

**修复的位置**：
1. ✅ Python时间戳转换（realtime_plot.py）
2. ✅ Tooltip时间显示（chart_widget.py）
3. ✅ X轴时间标签（chart_widget.py，3个位置）

---

**修复版本**: 6.0  
**修复日期**: 2025-11-21  
**状态**: ✅ 已完成

