# 动态图表JavaScript注入问题修复

## 问题诊断

### 发现的问题
1. ✅ `test_simple.py` (端口8083) 正常工作 - JavaScript正确执行
2. ❌ `test_dynamic_chart.py` (端口8082) 页面源码中找不到 `Chart Widget Script Starting`
3. ✅ NiceGUI版本 2.20.0 - 版本正常

### 根本原因

**动态创建图表导致JavaScript未注入**

在 `test_dynamic_chart.py` 中：
```python
def recreate_chart(self, signal_types):
    # 清空图表容器
    self.chart_container.clear()  # ❌ 问题：清空后重新创建
    
    with self.chart_container:
        # 创建新的图表
        self.chart_widget = RealtimeChartWidget(option)  # 此时页面已加载
```

**问题分析**：
1. 页面初始加载时，`chart_container` 只包含一个提示文本
2. 用户选择信号后，调用 `recreate_chart()` 清空容器
3. 此时调用 `RealtimeChartWidget()`，其中的 `ui.add_body_html()` 被调用
4. **但页面已经加载完成**，`ui.add_body_html()` 在动态创建时可能不会立即生效
5. 导致JavaScript代码未被注入到页面中

## 解决方案

### 方案：初始化时创建空图表

**核心思路**：在页面初始化时就创建图表实例，确保JavaScript正确注入，之后只更新配置而不销毁重建。

### 修改1：初始化时创建图表

**文件**：`test_dynamic_chart.py`

**位置**：`main_page()` 函数中的 Tab 1 部分

**修改前**：
```python
with ui.tab_panel(tab_chart):
    app.chart_container = ui.column().classes('w-full')
    with app.chart_container:
        ui.label('👈 请先在左侧选择信号').classes('text-h6').style(
            'color: #999; text-align: center; padding: 100px;'
        )
```

**修改后**：
```python
with ui.tab_panel(tab_chart):
    app.chart_container = ui.column().classes('w-full')
    
    # 初始化时创建一个空图表，确保JavaScript正确注入
    # 使用一个信号作为占位符
    initial_signal_types = {
        'placeholder_[0]': {'type': 'numeric'}
    }
    app.realtime_plot = RealtimePlot(
        num_signals=1,
        window_seconds=30.0,
        signal_types=initial_signal_types
    )
    initial_option = app.realtime_plot.get_option()
    
    with app.chart_container:
        app.chart_widget = RealtimeChartWidget(initial_option)
        app.chart_widget.update_enum_labels(initial_signal_types)
        
        # 显示提示信息
        with ui.card().classes('w-full').style('margin-top: 20px; background-color: #e3f2fd;'):
            ui.label('👈 请先在左侧选择信号').classes('text-h6').style(
                'color: #1976d2; text-align: center; padding: 50px;'
            )
```

**关键点**：
- ✅ 页面加载时就创建 `RealtimeChartWidget` 实例
- ✅ JavaScript通过 `ui.add_body_html()` 正确注入
- ✅ 使用占位符信号，用户看到提示选择信号

### 修改2：更新图表而不销毁

**文件**：`test_dynamic_chart.py`

**方法**：`recreate_chart()`

**修改前**：
```python
def recreate_chart(self, signal_types):
    """重新创建图表"""
    # 清空图表容器
    self.chart_container.clear()  # ❌ 销毁图表和JavaScript
    
    with self.chart_container:
        # 创建新的图表
        self.realtime_plot = RealtimePlot(...)
        option = self.realtime_plot.get_option()
        self.chart_widget = RealtimeChartWidget(option)  # ❌ 重新创建
        self.chart_widget.update_enum_labels(signal_types)
```

**修改后**：
```python
def recreate_chart(self, signal_types):
    """重新创建图表"""
    # 重新创建RealtimePlot
    self.realtime_plot = RealtimePlot(
        num_signals=len(signal_types),
        window_seconds=30.0,
        signal_types=signal_types
    )
    
    # 获取新的配置
    new_option = self.realtime_plot.get_option()
    
    # 更新现有图表（不销毁，避免JavaScript丢失）
    self.chart_widget.update_chart_option(new_option, exclude_tooltip=True)
    self.chart_widget.update_enum_labels(signal_types)
    
    # 重置数据
    self.data_history = None
    self.update_stats()
```

**关键点**：
- ✅ 不调用 `clear()`，保持图表实例
- ✅ 只更新图表配置，JavaScript保持有效
- ✅ 使用 `update_chart_option()` 更新所有配置

### 修改3：改进update_chart_option方法

**文件**：`chart_widget.py`

**方法**：`update_chart_option()`

**修改前**：
```python
def update_chart_option(self, new_option: Dict[str, Any], exclude_tooltip: bool = True):
    new_height = new_option.get('height', 1000)
    
    # 更新配置
    for key, value in new_option.items():
        if exclude_tooltip and key in ['tooltip', 'axisPointer']:
            continue
        self.chart_element.options[key] = value  # ❌ 直接赋值可能不完全生效
    
    self.chart_element._props['style'] = f'height: {new_height}px; ...'
    self.chart_element.update()
```

**修改后**：
```python
def update_chart_option(self, new_option: Dict[str, Any], exclude_tooltip: bool = True):
    new_height = new_option.get('height', 1000)
    
    # 使用setOption更新（notMerge=false表示合并更新）
    # 构建更新配置，排除tooltip和axisPointer
    update_config = {}
    for key, value in new_option.items():
        if exclude_tooltip and key in ['tooltip', 'axisPointer']:
            continue
        update_config[key] = value
    
    # 通过JavaScript更新配置，保持tooltip和axisPointer
    import json
    config_json = json.dumps(update_config)
    
    try:
        ui.run_javascript(f'''
            const el = getElement({self.chart_element.id});
            if (el && el.chart) {{
                el.chart.setOption({config_json}, false, false);
                console.log('Chart option updated for instance {self.instance_id}');
            }}
        ''')
    except Exception as e:
        # 备用方案：直接更新options
        for key, value in update_config.items():
            self.chart_element.options[key] = value
    
    # 更新样式
    self.chart_element._props['style'] = f'height: {new_height}px; ...'
    self.chart_element.update()
```

**关键点**：
- ✅ 使用 `ui.run_javascript()` 调用 ECharts 的 `setOption()`
- ✅ 保留 `tooltip` 和 `axisPointer` 配置
- ✅ 添加备用方案以防JavaScript执行失败
- ✅ 添加调试日志

## 技术细节

### ui.add_body_html() vs ui.run_javascript()

| 方法 | 使用场景 | 特点 |
|------|---------|------|
| `ui.add_body_html()` | 页面初始化 | 将HTML/Script添加到body末尾，**仅在页面加载时有效** |
| `ui.run_javascript()` | 动态执行 | 立即执行JavaScript代码，**适用于动态更新** |

**教训**：
- 初始化代码（如定义函数、创建命名空间）应该在页面加载时通过 `ui.add_body_html()` 注入
- 动态更新（如更新图表配置）应该使用 `ui.run_javascript()` 执行

### ECharts setOption 方法

```javascript
chart.setOption(option, notMerge, lazyUpdate)
```

参数：
- `option`: 新的配置对象
- `notMerge`: 
  - `false`（默认）：合并更新，只更新指定的配置项
  - `true`：完全替换，重置所有配置
- `lazyUpdate`: 是否延迟更新

**我们使用**：
```javascript
chart.setOption(config, false, false)  // 合并更新，立即生效
```

## 验证测试

### 测试步骤

1. **打开页面**：`http://localhost:8082`

2. **检查页面源代码**：
   - 右键 → 查看页面源代码
   - 搜索 `Chart Widget Script Starting`
   - ✅ **应该能找到**

3. **检查控制台**（F12）：
   ```
   === Chart Widget Script Starting ===
   Instance ID: 1
   Chart ID: xxx
   Created window.chartInstances
   Creating chart instance namespace for ID: 1
   setupTooltip() called for instance 1
   Attempt 1 to initialize chart 1
   ...
   Chart instance 1 tooltip initialized successfully
   Custom indicator line created for instance 1
   Indicator line height updated: 800
   ```

4. **选择信号**：
   - 在左侧勾选几个信号
   - 查看控制台：`Chart option updated for instance 1`

5. **测试功能**：
   - 点击"开始"按钮
   - 鼠标移动到图表
   - ✅ **应该看到灰色竖线贯穿所有子图**
   - 鼠标悬停
   - ✅ **Tooltip只显示一个时间戳**

### 预期结果

#### Tooltip ✅
```
2025-11-21 19:29:26.123  ← 只有一个时间戳
● temperature_[0]  26.297
● pressure_[1]     101,868.472
● voltage_[2]      5.118
● current_[3]      0.089
```

#### 竖线 ✅
- 灰色垂直线 │ 贯穿所有子图
- 跟随鼠标移动
- 鼠标离开时消失

## 对比总结

### 修复前 ❌
```
页面加载
  └─ 只显示提示文本
  └─ 没有图表，没有JavaScript

用户选择信号
  └─ clear() 清空容器
  └─ 创建新图表
  └─ ui.add_body_html() ❌ 不生效（页面已加载）
  └─ JavaScript未注入
  
结果：tooltip显示多个时间戳，没有竖线
```

### 修复后 ✅
```
页面加载
  └─ 创建占位符图表
  └─ ui.add_body_html() ✅ 注入JavaScript
  └─ JavaScript正确初始化

用户选择信号
  └─ 更新图表配置（不销毁）
  └─ ui.run_javascript() ✅ 更新配置
  └─ JavaScript保持有效
  
结果：tooltip只显示一个时间戳，竖线正常
```

## 适用场景

这个解决方案适用于：
- ✅ 动态创建/更新图表的场景
- ✅ 需要在页面加载后修改图表配置
- ✅ 多实例图表管理
- ✅ 保持JavaScript状态（tooltip formatter等）

## 已知限制

- 初始化时会创建一个占位符图表（几乎不可见）
- 第一次选择信号时，会看到图表从1个信号变为N个信号
- 如果用户频繁切换信号，可能有短暂的渲染延迟

## 扩展建议

如果需要完全动态的图表创建（不需要占位符），可以考虑：

1. **将JavaScript全局化**：
   - 在页面初始化时注入所有JavaScript函数
   - 图表创建时只引用已存在的函数

2. **使用自定义组件**：
   - 创建一个NiceGUI自定义组件
   - 将JavaScript封装在组件中

3. **服务端渲染**：
   - 在服务端完成图表配置
   - 客户端只负责渲染

---

**修复版本**: 3.0  
**修复日期**: 2025-11-21  
**测试状态**: ✅ 待验证

