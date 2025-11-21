# Tooltip 优化说明文档

## 优化内容概述

针对将代码集成到其他工程时 tooltip 无法正确显示的问题，进行了以下优化：

## 主要改进点

### 1. **实例隔离机制**
- **问题**: 原代码使用全局变量（`window.enumLabelsMap`、`window.customTooltipFormatter`），多实例会相互冲突
- **解决方案**: 
  - 为每个图表实例创建唯一的 `instance_id`
  - 使用 `window.chartInstances[instance_id]` 作为命名空间
  - 每个实例的数据完全隔离，互不干扰

### 2. **更健壮的元素获取**
- **问题**: 在某些环境中，`getElement()` 函数可能不可用
- **解决方案**:
  ```javascript
  // 多种方式尝试获取图表元素
  el = typeof getElement === 'function' ? getElement(CHART_ID) : null;
  if (!el) {
      // 备用方案：通过 DOM 查询
      const elements = document.querySelectorAll('.echarts');
      for (let elem of elements) {
          if (elem.__nicegui_chart) {
              el = { chart: elem.__nicegui_chart };
              break;
          }
      }
  }
  ```

### 3. **增强的初始化机制**
- **问题**: DOM 加载时机不确定，导致初始化失败
- **解决方案**:
  - 增加重试次数：从 20 次增加到 50 次
  - 检查 `document.readyState`，确保 DOM 完全加载后再初始化
  - 添加详细的控制台日志，便于调试

### 4. **显式启用 Tooltip**
- **问题**: 在某些容器中，tooltip 可能被禁用或被裁剪
- **解决方案**:
  ```javascript
  tooltip: {
      show: true,              // 显式启用
      trigger: 'axis',         // 确保触发方式正确
      formatter: ...,          // 使用实例特定的 formatter
      confine: false,          // 允许超出图表边界
      appendToBody: true       // 添加到 body，避免被容器裁剪
  }
  ```

### 5. **全局资源优化**
- **问题**: 每个实例都添加相同的全局 CSS，造成资源浪费
- **解决方案**:
  - 使用类变量 `_global_init_done` 标记
  - 全局 CSS 只添加一次

### 6. **容器定位检查**
- **问题**: 自定义指示线依赖父容器的相对定位
- **解决方案**:
  ```javascript
  if (window.getComputedStyle(chartContainer).position === 'static') {
      chartContainer.style.position = 'relative';
  }
  ```

## 技术改进细节

### 类结构变化
```python
class RealtimeChartWidget:
    _global_init_done = False      # 类变量：标记全局初始化状态
    _instance_count = 0            # 类变量：实例计数器
    
    def __init__(self, initial_option):
        RealtimeChartWidget._instance_count += 1
        self.instance_id = RealtimeChartWidget._instance_count  # 实例ID
        ...
```

### JavaScript 命名空间结构
```javascript
window.chartInstances = {
    1: {  // 第一个实例
        enumLabelsMap: {...},
        tooltipFormatter: function() {...},
        updateEnumLabels: function() {...}
    },
    2: {  // 第二个实例
        enumLabelsMap: {...},
        tooltipFormatter: function() {...},
        updateEnumLabels: function() {...}
    }
}
```

## 调试功能

### 控制台日志
- **成功初始化**: `Chart instance X tooltip initialized successfully`
- **初始化失败**: `Failed to initialize chart instance X after 50 attempts`
- **元素获取失败**: `Failed to get chart element: [error details]`

### 检查方法
在浏览器控制台中执行以下命令来检查状态：

```javascript
// 查看所有图表实例
console.log(window.chartInstances);

// 查看特定实例的枚举标签映射
console.log(window.chartInstances[1].enumLabelsMap);

// 手动测试 tooltip formatter
const testParams = [{
    seriesIndex: 0,
    seriesName: 'test_signal',
    value: [Date.now(), 123.456],
    color: '#5470c6'
}];
console.log(window.chartInstances[1].tooltipFormatter(testParams));
```

## 兼容性说明

### 支持的场景
✅ 单页面多图表实例
✅ Tab 页面中的图表
✅ 动态加载的图表
✅ 嵌套容器中的图表
✅ 带有自定义 CSS 的容器

### 已知限制
⚠️ 需要 NiceGUI 支持 `ui.run_javascript()`
⚠️ 浏览器需要支持 ES6（箭头函数、const/let、Map 等）

## 测试建议

### 基本测试
1. 创建单个图表实例，验证 tooltip 正常显示
2. 鼠标悬停查看数据点详情
3. 检查枚举信号是否显示文本标签

### 多实例测试
1. 在同一页面创建多个图表实例
2. 验证每个图表的 tooltip 独立工作
3. 检查枚举标签不会混淆

### Tab 页面测试
1. 在不同 tab 中放置图表
2. 切换 tab 验证 tooltip 正常工作
3. 检查指示线正确显示

### 调试测试
1. 打开浏览器控制台
2. 查找初始化成功/失败的日志
3. 使用上述调试命令检查状态

## 迁移指南

如果您使用的是旧版本的 `chart_widget.py`，无需修改调用代码，新版本完全向后兼容：

```python
# 调用方式不变
widget = RealtimeChartWidget(initial_option)
widget.update_enum_labels(signal_types)
widget.update_series_data(series_data)
```

## 性能优化

优化后的性能改进：
- ✅ 减少了全局 CSS 重复注入
- ✅ 使用 IIFE 避免全局作用域污染
- ✅ 实例隔离提高了多图表场景的稳定性
- ✅ 更快的初始化（增加重试频率）

## 问题排查清单

如果 tooltip 仍然不显示，请按以下步骤排查：

1. **检查控制台日志**
   - 是否有 "tooltip initialized successfully" 消息？
   - 是否有错误信息？

2. **检查实例是否创建**
   ```javascript
   console.log(window.chartInstances);
   ```

3. **检查 tooltip formatter 是否正确**
   ```javascript
   console.log(typeof window.chartInstances[1].tooltipFormatter);
   // 应该输出 "function"
   ```

4. **检查容器定位**
   - 图表父容器是否有 `position: relative`？
   - 是否有 `overflow: hidden` 导致 tooltip 被裁剪？

5. **检查 NiceGUI 版本**
   - 确保使用的是最新版本的 NiceGUI
   - 验证 `ui.run_javascript()` 可用

6. **检查浏览器兼容性**
   - 使用现代浏览器（Chrome, Firefox, Edge）
   - 检查控制台是否有 JavaScript 语法错误

## 联系与反馈

如果遇到问题：
1. 查看控制台日志
2. 使用调试命令检查状态
3. 提供具体的错误信息和场景描述

---

**版本**: 2.0 (优化版)  
**更新日期**: 2025-11-21  
**兼容性**: NiceGUI + ECharts

