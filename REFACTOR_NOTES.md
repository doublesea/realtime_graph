# 代码重构说明

## 重构日期
2025年11月

## 重构目标
将ui.echart绘图部分从main.py中分离，单独封装为一个类，实现更清晰的代码结构和职责分离。

## 主要改动

### 1. 新增文件：`chart_widget.py`

创建了 `RealtimeChartWidget` 类，封装了所有与ECharts图表相关的功能：

**核心功能：**
- 图表元素创建和初始化
- 自定义CSS样式管理
- JavaScript交互功能（tooltip、指示线、缩放事件等）
- 枚举标签映射管理
- 图表配置更新
- 系列数据更新

**对外接口：**
```python
class RealtimeChartWidget:
    def __init__(self, initial_option: Dict[str, Any])
    def update_enum_labels(self, signal_types: Dict[str, Dict[str, Any]])
    def update_chart_option(self, new_option: Dict[str, Any], exclude_tooltip: bool = True)
    def update_series_data(self, series_data: list)
    def get_element(self)
```

### 2. 重构文件：`main.py`

**代码行数变化：**
- 重构前：560行
- 重构后：266行
- 减少：294行（约52%）

**主要改进：**
1. **删除了大量JavaScript和CSS代码**（约300行）
   - 原本内嵌在main.py中的tooltip formatter
   - 指示线创建和事件监听
   - 缩放事件处理
   - 枚举标签映射更新

2. **简化了图表操作**
   ```python
   # 重构前：
   for key, value in new_option.items():
       if key != 'tooltip':
           plot_element.options[key] = value
   plot_element._props['style'] = f'height: {new_height}px; ...'
   plot_element.update()
   
   # 重构后：
   chart_widget.update_chart_option(new_option, exclude_tooltip=True)
   ```

3. **统一了数据更新接口**
   ```python
   # 重构前：
   for i in range(len(new_option['series'])):
       plot_element.options['series'][i]['data'] = new_option['series'][i]['data']
       plot_element.options['series'][i]['showSymbol'] = new_option['series'][i]['showSymbol']
       plot_element.options['series'][i]['symbolSize'] = new_option['series'][i]['symbolSize']
   plot_element.update()
   
   # 重构后：
   series_data = [
       {'data': ..., 'showSymbol': ..., 'symbolSize': ...}
       for i in range(len(new_option['series']))
   ]
   chart_widget.update_series_data(series_data)
   ```

## 架构改进

### 重构前的架构
```
main.py (560行)
├── UI创建
├── 图表创建和配置（大量JavaScript/CSS）
├── 数据生成逻辑调用
└── 图表更新逻辑
```

### 重构后的架构
```
main.py (266行)                  ← 主控制器
├── UI创建
├── 调用 chart_widget            ← 简洁的接口调用
├── 调用 data_generator          ← 数据生成
└── 调用 realtime_plot           ← 数据管理

chart_widget.py (377行)          ← 图表组件封装
├── RealtimeChartWidget类
├── JavaScript交互管理
├── CSS样式管理
└── 图表更新接口

realtime_plot.py                 ← 数据管理和ECharts配置
data_generator.py                ← 数据生成
```

## 职责分离

| 模块 | 职责 |
|------|------|
| `main.py` | UI框架、流程控制、组件协调 |
| `chart_widget.py` | ECharts图表渲染、交互功能 |
| `realtime_plot.py` | 数据缓存管理、ECharts配置生成 |
| `data_generator.py` | 模拟数据生成 |

## 优势

1. **代码可维护性提升**
   - 图表相关代码集中管理
   - 职责清晰，易于定位问题

2. **代码复用性提升**
   - RealtimeChartWidget可在其他项目中复用
   - 独立的图表组件，便于测试

3. **可读性提升**
   - main.py更加简洁，专注于业务流程
   - 图表细节被封装，降低理解成本

4. **可扩展性提升**
   - 新增图表功能只需修改chart_widget.py
   - 不影响主程序逻辑

## 兼容性

✅ 完全向后兼容，功能无变化
✅ 所有原有功能均正常工作
✅ 无需修改其他文件（data_generator.py, realtime_plot.py等）

## 测试验证

```bash
# 导入测试
python -c "from chart_widget import RealtimeChartWidget; from realtime_plot import RealtimePlot; from data_generator import DataGenerator; print('Import test passed')"

# 运行主程序
python main.py
```

## 后续优化建议

1. 可以进一步将UI创建部分也封装成独立的类
2. 考虑使用配置文件管理图表样式
3. 添加单元测试覆盖RealtimeChartWidget类

