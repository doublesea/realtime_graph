# Tooltip 宽度优化

## 问题描述

**现象**：tooltip 显示多个信号时，宽度不够，导致信号名称和数值重叠

**截图分析**：
- 显示了6个信号（temperature、pressure、voltage、current、status、speed）
- 信号名称较长（如 `temperature_[0]`、`pressure_[1]`）
- 原来的宽度设置（80px）不够，导致文字和数值重叠

## 优化方案

### 1. 增加单列布局的宽度

**文件**：`chart_widget.py`

**修改前**：
```javascript
// 单列布局
html += '<div style="margin:3px 0">';
html += '<span style="display:inline-block;width:10px;height:10px;..."></span>';
html += '<span style="display:inline-block;width:80px">' + sig.name + '</span>';  // ❌ 只有80px
html += '<span style="font-weight:bold">' + sig.displayValue + '</span>';
html += '</div>';
```

**修改后**：
```javascript
// 单列布局：增加宽度，使用flex布局避免重叠
html += '<div style="margin:4px 0;display:flex;align-items:center;min-width:250px;">';  // ✅ 最小宽度250px
html += '<span style="width:10px;height:10px;...;flex-shrink:0;"></span>';
html += '<span style="min-width:140px;font-size:12px;flex-shrink:0;">' + sig.name + '</span>';  // ✅ 140px宽度
html += '<span style="font-weight:bold;font-size:12px;margin-left:10px;text-align:right;flex-grow:1;">' + sig.displayValue + '</span>';
html += '</div>';
```

**改进点**：
- ✅ 使用 `display:flex` 布局，更灵活
- ✅ 信号名称宽度从 `80px` 增加到 `min-width:140px`
- ✅ 整行最小宽度设置为 `250px`
- ✅ 数值右对齐，使用 `flex-grow:1` 自动填充
- ✅ 增加间距，字体从11px增加到12px

### 2. 优化多列布局

**修改前**：
```javascript
// 多列布局
html += '<div style="display:flex;gap:15px;">';
html += '<div style="flex:0 0 auto;">';  // ❌ 宽度不固定
html += '<span style="width:65px;...">' + sig.name + '</span>';  // ❌ 65px不够
```

**修改后**：
```javascript
// 多列布局：增加每列的宽度
html += '<div style="display:flex;gap:20px;">';
html += '<div style="flex:0 0 auto;min-width:240px;">';  // ✅ 每列最小240px
html += '<span style="min-width:120px;...">' + sig.name + '</span>';  // ✅ 120px宽度
html += '<span style="text-align:right;flex-grow:1;">' + sig.displayValue + '</span>';  // ✅ 右对齐
```

**改进点**：
- ✅ 每列最小宽度 `240px`
- ✅ 信号名称宽度从 `65px` 增加到 `min-width:120px`
- ✅ 列间距从 `15px` 增加到 `20px`
- ✅ 数值右对齐

### 3. 设置 Tooltip 整体宽度

**文件**：`realtime_plot.py`

**修改前**：
```python
'extraCssText': 'box-shadow: 0 2px 8px rgba(0, 0, 0, 0.5); max-height: 90vh; max-width: 800px; overflow-y: auto;',
```

**修改后**：
```python
'extraCssText': 'box-shadow: 0 2px 8px rgba(0, 0, 0, 0.5); max-height: 90vh; max-width: 600px; min-width: 280px; overflow-y: auto;',
```

**改进点**：
- ✅ 添加 `min-width: 280px` - 确保最小宽度
- ✅ `max-width` 从 `800px` 调整到 `600px` - 更合理的最大宽度
- ✅ Tooltip 会根据内容自动在 280px-600px 之间调整

### 4. JavaScript 中恢复 Tooltip 配置

**文件**：`chart_widget.py`

在两个地方添加 `extraCssText`：

**位置1**：初始化时
```javascript
tooltip: {
    show: true,
    trigger: 'axis',
    formatter: ...,
    confine: false,
    appendToBody: true,
    extraCssText: 'min-width: 280px; max-width: 600px;'  // ✅ 新增
}
```

**位置2**：更新配置时
```javascript
// 恢复tooltip配置
tooltip: {
    show: true,
    trigger: 'axis',
    formatter: window.chartInstances[1].tooltipFormatter,
    confine: false,
    appendToBody: true,
    extraCssText: 'min-width: 280px; max-width: 600px;'  // ✅ 新增
}
```

## 对比效果

### 修改前 ❌
```
┌─────────────────────────┐
│ 2025-11-21 19:57:41.205 │
├─────────────────────────┤
│ ● temperatur26.049      │  ← 重叠！
│ ● pressure_[11101.775   │  ← 重叠！
│ ● voltage_[25.093       │  ← 重叠！
│ ● current_[30.132       │  ← 重叠！
│ ● status_[4关闭(OFF)    │  ← 重叠！
│ ● speed_[5]984.234      │  ← 重叠！
└─────────────────────────┘
宽度：约200px（不够）
```

### 修改后 ✅
```
┌───────────────────────────────────┐
│ 2025-11-21 19:57:41.205          │
├───────────────────────────────────┤
│ ● temperature_[0]      26.049    │  ← 清晰！
│ ● pressure_[1]      11101.775    │  ← 清晰！
│ ● voltage_[2]           5.093    │  ← 清晰！
│ ● current_[3]           0.132    │  ← 清晰！
│ ● status_[4]        关闭(OFF)    │  ← 清晰！
│ ● speed_[5]           984.234    │  ← 清晰！
└───────────────────────────────────┘
宽度：280-600px（自适应）
```

## 布局说明

### 单列布局（≤12个信号）

```
┌─────────────────────────────────┐
│ [●] signal_name_[0]    123.456  │
│  ↑       ↑                ↑     │
│ 10px   140px           右对齐    │
│                                  │
│ 总宽度：min-width: 250px        │
└─────────────────────────────────┘
```

**元素分配**：
- 圆点：10px (固定)
- 间距：10px
- 信号名：140px (最小宽度)
- 间距：10px
- 数值：自动填充，右对齐

### 多列布局（>12个信号）

```
┌─────────────┬─────────────┐
│ [●] sig_1   │ [●] sig_13  │
│ [●] sig_2   │ [●] sig_14  │
│ ...         │ ...         │
│ [●] sig_12  │ [●] sig_24  │
└─────────────┴─────────────┘
   ↑ 240px        ↑ 240px
      ↑── gap: 20px ──↑
```

**每列**：
- 最小宽度：240px
- 列间距：20px
- 最多12个信号/列

## 测试步骤

1. **刷新浏览器**：`http://localhost:8082` (Ctrl+F5)

2. **选择6个信号**（全选）

3. **点击"开始"**

4. **鼠标悬停到图表上**

5. **验证 Tooltip**：
   - ✅ 信号名称完整显示，不被截断
   - ✅ 数值右对齐，不与信号名重叠
   - ✅ 整体布局清晰，易读
   - ✅ 宽度适中（约280-350px）

## 响应式设计

Tooltip 宽度会根据内容自动调整：

| 信号数量 | 布局方式 | 宽度范围 |
|---------|---------|---------|
| 1-3个 | 单列 | 280-320px |
| 4-6个 | 单列 | 300-350px |
| 7-12个 | 单列 | 350-400px |
| 13-24个 | 双列 | 480-560px |
| >24个 | 多列 | 自动增长，最大600px |

## 技术细节

### Flexbox 布局优势

```css
display: flex;
align-items: center;
```

**优点**：
- 自动垂直居中对齐
- `flex-shrink: 0` 防止压缩
- `flex-grow: 1` 自动填充剩余空间
- `min-width` 确保最小宽度
- `text-align: right` 数值右对齐

### 为什么使用 min-width 而不是 width

```css
/* 不好 */
width: 140px;  /* 固定宽度，可能不够或浪费空间 */

/* 更好 */
min-width: 140px;  /* 最小宽度，内容多时自动扩展 */
```

## 兼容性

- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Edge 90+
- ✅ Safari 14+
- ⚠️ IE 不支持（Flexbox 支持有限）

## 后续优化建议

1. **自动调整字体大小**：
   - 信号数量多时，可以自动减小字体

2. **信号名称缩略**：
   - 超长信号名自动截断，鼠标悬停显示完整名称

3. **数值格式化**：
   - 大数值使用千分位分隔符
   - 科学计数法显示超大/超小数值

4. **主题支持**：
   - 支持深色/浅色主题切换
   - 自定义颜色方案

---

**优化版本**: 5.0  
**优化日期**: 2025-11-21  
**状态**: ✅ 已完成

