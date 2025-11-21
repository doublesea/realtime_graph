# 枚举信号Y轴优化 (Enum Signal Y-Axis Optimization)

## 问题描述 (Problem Description)

当枚举信号定义了很多枚举值（例如20个状态），但实际数据中只出现了少数几个值时，Y轴会显示所有定义的枚举值，导致：
- Y轴刻度非常拥挤
- 大量空白区域（未使用的枚举值）
- 图表难以阅读

When an enum signal defines many enum values (e.g., 20 states) but only a few values actually appear in the data, the Y-axis displays all defined enum values, resulting in:
- Very crowded Y-axis labels
- Large empty areas (unused enum values)
- Difficult to read chart

## 解决方案 (Solution)

动态调整Y轴类别，只显示数据中实际出现的枚举值。

Dynamically adjust Y-axis categories to display only enum values that actually appear in the data.

### 实现步骤 (Implementation Steps)

#### 1. 数据分析和映射 (Data Analysis and Mapping)

在 `realtime_plot.py` 的 `_update_chart_data` 方法中：

In the `_update_chart_data` method of `realtime_plot.py`:

```python
if signal_config['type'] == 'enum' and len(data) > 0:
    enum_labels = signal_config.get('enum_labels', {})
    
    # 收集实际出现的枚举值
    # Collect actually appearing enum values
    actual_values = set()
    for _, val in data:
        val_int = int(round(val))
        if val_int in enum_labels:
            actual_values.add(val_int)
    
    # 按值排序
    # Sort by value
    sorted_values = sorted(actual_values)
    
    # 构建实际显示的类别列表
    # Build category list for display
    if sorted_values:
        categories = [enum_labels[v] for v in sorted_values]
        
        # 创建值到索引的映射
        # Create value-to-index mapping
        value_to_index = {v: idx for idx, v in enumerate(sorted_values)}
        
        # 重新映射数据：将原始枚举值转换为新的类别索引
        # Remap data: convert original enum values to new category indices
        remapped_data = []
        for ts, val in data:
            val_int = int(round(val))
            if val_int in value_to_index:
                remapped_data.append([ts, value_to_index[val_int]])
        
        # 更新series数据
        # Update series data
        self.option['series'][i]['data'] = remapped_data
        
        # 更新Y轴配置
        # Update Y-axis configuration
        self.option['yAxis'][i]['data'] = categories
        self.option['yAxis'][i]['_actual_values'] = sorted_values
        self.option['yAxis'][i]['min'] = 0
        self.option['yAxis'][i]['max'] = len(categories) - 1 if len(categories) > 1 else 0
```

**关键点 (Key Points):**
- 扫描数据中实际出现的枚举值
- Scan for enum values that actually appear in the data
- 创建原始值到新索引的映射
- Create mapping from original values to new indices
- 重新映射所有数据点
- Remap all data points
- 更新Y轴类别和范围
- Update Y-axis categories and range

#### 2. Tooltip显示优化 (Tooltip Display Optimization)

在 `chart_widget.py` 的tooltip formatter中：

In the tooltip formatter of `chart_widget.py`:

```javascript
if (enumLabels) {
    // 对于枚举类型，v现在是类别索引，需要从Y轴categories中获取标签
    // For enum type, v is now category index, need to get label from Y-axis categories
    const yAxisIndex = p.seriesIndex;
    
    let categoryLabel = null;
    try {
        const option = window.chartInstances[INSTANCE_ID]._currentOption;
        if (option && option.yAxis && option.yAxis[yAxisIndex]) {
            const categories = option.yAxis[yAxisIndex].data;
            const idx = Math.round(v);
            if (categories && idx >= 0 && idx < categories.length) {
                categoryLabel = categories[idx];
            }
        }
    } catch (e) {
        // Fallback to original method
    }
    
    if (categoryLabel) {
        displayValue = categoryLabel;
    } else {
        const enumVal = Math.round(v);
        displayValue = enumLabels[enumVal.toString()] || enumVal.toString();
    }
}
```

**关键点 (Key Points):**
- 数据值现在是重新映射后的索引（0, 1, 2...）
- Data values are now remapped indices (0, 1, 2...)
- 从Y轴categories中获取对应的标签文本
- Get corresponding label text from Y-axis categories
- 保证tooltip显示正确的枚举标签
- Ensure tooltip displays correct enum labels

#### 3. 保存option引用 (Save Option Reference)

为了让tooltip能访问当前的Y轴配置，需要保存option：

To allow tooltip access to current Y-axis configuration, save the option:

```javascript
// 在初始化时
// During initialization
window.chartInstances[INSTANCE_ID] = {
    enumLabelsMap: {},
    _currentOption: null,  // 存储当前option
    // ...
};

// 在finished事件中更新
// Update in finished event
el.chart.on('finished', function() {
    const opt = el.chart.getOption();
    window.chartInstances[INSTANCE_ID]._currentOption = opt;
    // ...
});

// 在update_chart_option中更新
// Update in update_chart_option
const option = el.chart.getOption();
window.chartInstances[{self.instance_id}]._currentOption = option;
```

## 效果 (Effect)

### 优化前 (Before Optimization)

- 定义了20个枚举值（0-19）
- Defined 20 enum values (0-19)
- Y轴显示全部20个标签
- Y-axis displays all 20 labels
- 实际只使用了3个值，但占用了很大的纵向空间
- Actually only 3 values used, but occupies large vertical space

### 优化后 (After Optimization)

- 定义了20个枚举值（0-19）
- Defined 20 enum values (0-19)
- Y轴只显示实际出现的3个标签
- Y-axis displays only 3 labels that actually appear
- 图表紧凑，更容易阅读
- Chart is compact and easier to read
- 自动适应数据变化
- Automatically adapts to data changes

## 使用示例 (Usage Example)

```python
from realtime_plot import RealtimePlot
from chart_widget import RealtimeChartWidget

# 定义信号类型
signal_types = {
    'device_status': {
        'type': 'enum',
        'enum_labels': {
            0: 'INIT',
            1: 'IDLE',
            2: 'STARTING',
            # ... more labels ...
        }
    }
}

# 创建绘图对象
plot = RealtimePlot(signal_types=signal_types, window_seconds=30)

# 更新数据
plot.update_data(df)

# 创建图表组件
chart = RealtimeChartWidget(initial_option=plot.option)
chart.update_enum_labels(signal_types)
```

**注意 (Note)**:
- `RealtimeChartWidget` 构造函数参数名是 `initial_option`（不是 `option`）
- Constructor parameter name is `initial_option` (not `option`)
- 信号类型通过 `update_enum_labels()` 方法传递（不是构造函数参数）
- Signal types are passed via `update_enum_labels()` method (not constructor parameter)

## 测试 (Testing)

运行测试程序：
Run test program:

```bash
python test_enum_optimization.py
```

访问: http://localhost:8084

测试场景 (Test Scenarios):
1. 初始数据使用枚举值 3, 4, 7 (RUNNING, PAUSED, ERROR)
2. Initial data uses enum values 3, 4, 7 (RUNNING, PAUSED, ERROR)
3. 点击刷新按钮，切换到枚举值 1, 2, 9 (IDLE, STARTING, MAINTENANCE)
4. Click refresh button to switch to enum values 1, 2, 9 (IDLE, STARTING, MAINTENANCE)
5. 观察Y轴自动调整
6. Observe Y-axis automatic adjustment

## 技术细节 (Technical Details)

### 数据流程 (Data Flow)

1. **原始数据**: 枚举值 [3, 4, 7, 3, 4, 7, ...]
2. **Original data**: Enum values [3, 4, 7, 3, 4, 7, ...]

3. **分析阶段**: 发现实际出现的值 = {3, 4, 7}
4. **Analysis phase**: Find actually appearing values = {3, 4, 7}

5. **映射阶段**: 
6. **Mapping phase**:
   - 3 → 0 (第一个类别)
   - 3 → 0 (first category)
   - 4 → 1 (第二个类别)
   - 4 → 1 (second category)
   - 7 → 2 (第三个类别)
   - 7 → 2 (third category)

7. **Y轴配置**: categories = ['RUNNING', 'PAUSED', 'ERROR']
8. **Y-axis configuration**: categories = ['RUNNING', 'PAUSED', 'ERROR']

9. **Series数据**: [[timestamp, 0], [timestamp, 1], [timestamp, 2], ...]
10. **Series data**: [[timestamp, 0], [timestamp, 1], [timestamp, 2], ...]

11. **显示结果**: Y轴只显示3个标签，数据正确映射
12. **Display result**: Y-axis displays only 3 labels, data correctly mapped

### 动态更新 (Dynamic Update)

当数据更新时，如果出现新的枚举值或某些值不再出现：
- Y轴类别会自动重新计算
- 映射关系会重新建立
- 图表会平滑更新

When data updates, if new enum values appear or some values no longer appear:
- Y-axis categories are automatically recalculated
- Mapping relationships are re-established
- Chart updates smoothly

## 注意事项 (Notes)

1. **数据一致性**: 确保数据值是有效的枚举值
2. **Data consistency**: Ensure data values are valid enum values

3. **tooltip兼容性**: tooltip必须从Y轴categories获取标签，而不是从原始enumLabels映射
4. **Tooltip compatibility**: Tooltip must get labels from Y-axis categories, not from original enumLabels mapping

5. **性能**: 对于大数据集，枚举值扫描是O(n)操作，但通常可以接受
6. **Performance**: For large datasets, enum value scanning is O(n) operation, but usually acceptable

7. **边界情况**: 
8. **Edge cases**:
   - 如果没有数据，使用原始配置
   - If no data, use original configuration
   - 如果只有一个枚举值，Y轴范围设置为[0, 0]
   - If only one enum value, Y-axis range set to [0, 0]

## 相关文件 (Related Files)

- `realtime_plot.py`: 数据分析和映射逻辑
- `realtime_plot.py`: Data analysis and mapping logic
- `chart_widget.py`: Tooltip显示优化
- `chart_widget.py`: Tooltip display optimization
- `test_enum_optimization.py`: 功能测试程序
- `test_enum_optimization.py`: Feature test program

