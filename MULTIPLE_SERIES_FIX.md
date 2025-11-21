# 多信号显示问题修复

## 问题描述

**现象**：选择了5个信号，但只画出一条曲线

## 问题分析

### 根本原因

使用**合并更新模式**（`setOption(config, false)`）时，从1个信号变为5个信号，配置无法完全替换：

1. 初始化时创建了1个占位符信号的图表
2. 用户选择5个信号后，调用 `update_chart_option()`
3. 使用 `setOption(config, false)` 合并更新
4. **问题**：grid、xAxis、yAxis、series只更新了第一个，其他4个没有被添加
5. 结果：只显示第一个信号的曲线

### 为什么合并更新不够？

ECharts的 `setOption(option, notMerge)`:
- `notMerge = false` (合并模式)：只更新提供的配置项，不影响其他配置
  - **问题**：数组类型的配置（如series）不会自动扩展
  - 如果原来有1个series，新配置有5个series，只会更新第一个
  
- `notMerge = true` (替换模式)：完全替换所有配置
  - **优点**：可以正确处理数组长度变化
  - **缺点**：会丢失tooltip、axisPointer等自定义配置

## 解决方案

### 方案：完全替换 + 恢复自定义配置

**两步走策略**：
1. 先使用 `setOption(config, true)` 完全替换配置（包括所有series）
2. 再使用 `setOption(config, false)` 恢复tooltip和axisPointer配置

### 修改1：update_chart_option 方法

**文件**：`chart_widget.py`

**修改前**：
```python
def update_chart_option(self, new_option, exclude_tooltip=True):
    # 构建配置
    update_config = {...}
    
    # 合并更新
    ui.run_javascript(f'''
        el.chart.setOption({config_json}, false, false);  # ❌ 只更新第一个series
    ''')
```

**修改后**：
```python
def update_chart_option(self, new_option, exclude_tooltip=True):
    # 构建配置
    update_config = {...}
    
    ui.run_javascript(f'''
        const newConfig = {config_json};
        console.log('New config has', newConfig.series.length, 'series');
        
        // 第一步：完全替换配置（notMerge=true）
        el.chart.setOption(newConfig, true, false);  # ✅ 完全替换，所有series都生效
        console.log('Chart option replaced');
        
        // 验证
        const option = el.chart.getOption();
        console.log('After update, chart has', option.series.length, 'series');
        
        // 第二步：恢复tooltip和axisPointer配置
        el.chart.setOption({{
            axisPointer: {{
                link: [{{xAxisIndex: 'all'}}],
                label: {{ show: false }},
                lineStyle: {{ opacity: 0 }}
            }},
            tooltip: {{
                show: true,
                trigger: 'axis',
                formatter: window.chartInstances[{self.instance_id}].tooltipFormatter,
                axisPointer: {{
                    type: 'line',
                    label: {{ show: false }},
                    lineStyle: {{ opacity: 0 }}
                }},
                confine: false,
                appendToBody: true
            }}
        }}, false, false);  # ✅ 合并更新，恢复自定义配置
        console.log('Tooltip and axisPointer restored');
    ''')
```

**关键点**：
1. ✅ 使用 `notMerge=true` 完全替换，确保5个series都生效
2. ✅ 添加调试日志，显示series数量变化
3. ✅ 第二次调用恢复tooltip和axisPointer
4. ✅ 验证更新后的series数量

### 修改2：清空旧数据

**文件**：`test_dynamic_chart.py`

**方法**：`recreate_chart()`

**添加**：
```python
def recreate_chart(self, signal_types):
    # ... 创建新的RealtimePlot和option ...
    
    # 更新图表配置
    self.chart_widget.update_chart_option(new_option, exclude_tooltip=True)
    self.chart_widget.update_enum_labels(signal_types)
    
    # 新增：确保显示空数据（清空旧的占位符数据）
    empty_series_data = [
        {
            'data': [],
            'showSymbol': False,
            'symbolSize': 6
        }
        for _ in range(len(signal_types))
    ]
    self.chart_widget.update_series_data(empty_series_data)
    
    # 重置数据
    self.data_history = None
    self.update_stats()
```

**作用**：
- 清空所有series的旧数据
- 避免占位符数据残留

### 修改3：改进 update_series_data 方法

**文件**：`chart_widget.py`

**问题**：Python端的 `self.chart_element.options['series']` 可能与实际图表不同步

**修改前**：
```python
def update_series_data(self, series_data: list):
    for i, series_config in enumerate(series_data):
        if i < len(self.chart_element.options['series']):  # ❌ 可能长度不对
            self.chart_element.options['series'][i]['data'] = series_config['data']
    
    self.chart_element.update()
```

**修改后**：
```python
def update_series_data(self, series_data: list):
    import json
    series_json = json.dumps(series_data)
    
    ui.run_javascript(f'''
        const el = getElement({self.chart_element.id});
        if (el && el.chart) {{
            const seriesData = {series_json};
            const option = el.chart.getOption();
            
            console.log('Updating series data:', seriesData.length, 'series');
            console.log('Current option has', option.series.length, 'series');
            
            // 更新每个series的data
            if (option.series) {{
                for (let i = 0; i < seriesData.length && i < option.series.length; i++) {{
                    option.series[i].data = seriesData[i].data;
                    option.series[i].showSymbol = seriesData[i].showSymbol;
                    option.series[i].symbolSize = seriesData[i].symbolSize;
                }}
                
                el.chart.setOption({{
                    series: option.series
                }}, false, false);
                
                console.log('Series data updated successfully');
            }}
        }}
    ''')
```

**关键点**：
- ✅ 使用JavaScript直接操作图表，避免Python端不同步
- ✅ 添加调试日志
- ✅ 先获取当前option，再更新

## 调试日志

### 选择信号时的控制台输出

```javascript
=== Updating Chart Config ===
New config has 5 series
New config has 5 grids
Chart option replaced for instance 1
After update, chart has 5 series  // ✅ 确认5个series都生效
Tooltip and axisPointer restored for instance 1

Updating series data: 5 series
Current option has 5 series  // ✅ 确认长度匹配
Series data updated successfully
```

### 如果只看到1个series

如果控制台显示：
```javascript
After update, chart has 1 series  // ❌ 只有1个
```

说明 `setOption(config, true)` 没有正确执行，可能原因：
1. config_json 序列化有问题
2. JavaScript代码执行失败
3. ECharts版本问题

## 测试步骤

1. **刷新浏览器**：`http://localhost:8082` (Ctrl+F5)

2. **打开控制台**（F12 → Console）

3. **选择5个信号**：
   - 在左侧勾选5个信号（例如全选）
   - 查看控制台

4. **验证日志**：
   ```
   === Updating Chart Config ===
   New config has 5 series        ← 应该是5
   New config has 5 grids         ← 应该是5
   Chart option replaced
   After update, chart has 5 series  ← 应该是5
   Tooltip and axisPointer restored
   ```

5. **查看图表**：
   - 应该看到5个子图（可能是空的）
   - 点击"开始"按钮
   - 应该看到5条曲线开始绘制

## 预期效果

### 选择3个信号
```
┌─────────────────────┐
│ temperature_[0]     │ ← 第1个子图
│  ～～～～～～～～～  │
├─────────────────────┤
│ pressure_[1]        │ ← 第2个子图
│  ～～～～～～～～～  │
├─────────────────────┤
│ voltage_[2]         │ ← 第3个子图
│  ～～～～～～～～～  │
└─────────────────────┘
```

### 选择5个信号
```
┌─────────────────────┐
│ temperature_[0]     │
├─────────────────────┤
│ pressure_[1]        │
├─────────────────────┤
│ voltage_[2]         │
├─────────────────────┤
│ current_[3]         │
├─────────────────────┤
│ status_[4]          │
└─────────────────────┘
```

## 技术总结

### ECharts setOption 的两种模式

| 模式 | notMerge | 适用场景 | 优点 | 缺点 |
|------|----------|---------|------|------|
| 合并更新 | false | 数据更新、样式调整 | 不影响其他配置 | 无法改变数组长度 |
| 完全替换 | true | 结构变化、信号数量变化 | 可以改变数组长度 | 丢失所有未指定的配置 |

### 最佳实践

**信号数量变化时**：
```javascript
// 1. 完全替换（获得正确的series数量）
chart.setOption(newConfig, true);

// 2. 恢复自定义配置（tooltip、axisPointer等）
chart.setOption({
    tooltip: { ... },
    axisPointer: { ... }
}, false);
```

**数据更新时**：
```javascript
// 只合并更新（保持所有配置）
chart.setOption({
    series: updatedSeries
}, false);
```

## 相关问题

### Q: 为什么不在初始化时就创建5个信号？

A: 因为用户可以动态选择任意数量的信号，可能是1个、3个、5个或更多。

### Q: 可以避免完全替换吗？

A: 理论上可以手动添加/删除series，但：
- 代码复杂度高
- 容易出错
- 完全替换更可靠

### Q: 会不会影响性能？

A: 不会，因为：
- 只在用户选择信号时触发（低频操作）
- ECharts的setOption本身就很快
- 完全替换的开销可以忽略

---

**修复版本**: 4.0  
**修复日期**: 2025-11-21  
**状态**: ✅ 待测试

