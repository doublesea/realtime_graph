"""
ECharts图表组件封装
将ui.echart绘图部分单独封装为一个类，提供简洁的接口供主程序调用
"""
import json
from nicegui import ui
from typing import Dict, Any, Optional


class RealtimeChartWidget:
    """实时图表组件，封装ui.echart和相关JavaScript交互"""
    
    _global_init_done = False  # 类变量，确保全局脚本只初始化一次
    _instance_count = 0  # 实例计数器
    _move_requests = {}  # 全局字典，存储待处理的移动请求 {instance_id: (signal_idx, direction)}
    
    def __init__(self, initial_option: Dict[str, Any], defer_init: bool = False, realtime_plot=None):
        """
        初始化图表组件
        
        Args:
            initial_option: 初始的ECharts配置选项
            defer_init: 是否延迟初始化JavaScript（用于tab等延迟渲染场景）
            realtime_plot: RealtimePlot 实例，用于子图顺序调节功能
        """
        RealtimeChartWidget._instance_count += 1
        self.instance_id = RealtimeChartWidget._instance_count
        self.chart_element: Optional[Any] = None
        self._initial_option = initial_option
        self._js_initialized = False  # 标记JavaScript是否已初始化
        self._defer_init = defer_init
        self.realtime_plot = realtime_plot  # 保存 realtime_plot 引用
        self._internal_subplot_order = None  # 内部维护的子图顺序（当没有 realtime_plot 时使用）
        self._setup_chart()
        self._setup_sidebar()  # 设置侧边栏
    
    def _setup_chart(self):
        """创建图表元素并设置所有必要的CSS和JavaScript"""
        # 获取图表高度
        chart_height = self._initial_option.get('height', 1000)
        
        # 只添加一次全局CSS（使用类变量标记）
        if not RealtimeChartWidget._global_init_done:
            ui.add_head_html('''
            <style>
            .echarts {
                position: relative !important;
            }
            </style>
            ''')
            RealtimeChartWidget._global_init_done = True
        
        # 创建图表元素
        self.chart_element = ui.echart(self._initial_option).style(
            f'height: {chart_height}px; width: 100%; min-height: {chart_height}px;'
        )
        # 添加唯一的类名以便在 JS 中精确定位
        self.chart_element.classes(f'chart-instance-{self.instance_id}')
        
        # 根据 defer_init 决定是否立即初始化 JavaScript
        if not self._defer_init:
            self._setup_javascript_optimized()
        else:
            # 延迟初始化：注册命名空间，但不执行 setupTooltip
            self._setup_namespace_only()
    
    def _setup_namespace_only(self):
        """只设置命名空间和函数，不初始化tooltip（用于延迟初始化场景）"""
        chart_id = self.chart_element.id
        instance_id = self.instance_id
        
        # 在 defer_init 模式下，只创建命名空间，setupTooltip 通过 _do_initialize 动态注入
        # 使用 add_body_html 在页面加载时注入（初始化时可用）
        tooltip_code = self._get_tooltip_formatter_code()
        try:
            # 在初始化时，add_body_html 应该可用
            ui.add_body_html(f'''
            <script>
            (function() {{
                console.log('=== Chart Widget Namespace Setup (Deferred) ===');
                console.log('Instance ID:', {instance_id});
                console.log('Chart ID:', {chart_id});
                
                const INSTANCE_ID = {instance_id};
                const CHART_ID = {chart_id};
                
                // 创建命名空间
                if (!window.chartInstances) {{
                    window.chartInstances = {{}};
                }}
                
                window.chartInstances[INSTANCE_ID] = {{
                    chartId: CHART_ID,
                    enumLabelsMap: {{}},
                    _currentOption: null,
                    _initialized: false,
                    
                    tooltipFormatter: function(params) {{
                        {tooltip_code}
                    }},
                    
                    updateEnumLabels: function(newLabels) {{
                        window.chartInstances[INSTANCE_ID].enumLabelsMap = newLabels;
                    }}
                }};
                
                console.log('Namespace created for instance', INSTANCE_ID, '(waiting for initialization)');
            }})();
            </script>
            ''')
        except Exception:
            # 如果 add_body_html 失败，使用 timer 延迟执行 run_javascript
            ui.timer(0.1, lambda: ui.run_javascript(f'''
            (function() {{
                console.log('=== Chart Widget Namespace Setup (Deferred) ===');
                const INSTANCE_ID = {instance_id};
                const CHART_ID = {chart_id};
                if (!window.chartInstances) {{
                    window.chartInstances = {{}};
                }}
                window.chartInstances[INSTANCE_ID] = {{
                    chartId: CHART_ID,
                    enumLabelsMap: {{}},
                    _currentOption: null,
                    _initialized: false,
                    tooltipFormatter: function(params) {{
                        {tooltip_code}
                    }},
                    updateEnumLabels: function(newLabels) {{
                        window.chartInstances[INSTANCE_ID].enumLabelsMap = newLabels;
                    }}
                }};
            }})();
            '''), once=True)
    
    def ensure_initialized(self):
        """
        确保JavaScript已初始化（用于tab切换等延迟渲染场景）
        可以安全地多次调用，只会初始化一次
        """
        if not self._js_initialized:
            print(f"[Chart {self.instance_id}] Triggering deferred initialization...")
            # 使用 timer 延迟执行，确保 DOM 已完全渲染
            ui.timer(0.2, self._do_initialize, once=True)  # 减少延迟到0.2秒
    
    def _do_initialize(self):
        """执行实际的JavaScript初始化"""
        if self._js_initialized:
            print(f"[Chart {self.instance_id}] Already initialized, skipping...")
            return
        
        print(f"[Chart {self.instance_id}] Executing JavaScript initialization...")
        self._js_initialized = True
        
        # 直接注入并执行 setupTooltip 代码
        chart_id = self.chart_element.id
        instance_id = self.instance_id
        
        ui.run_javascript(f'''
            (function() {{
                const INSTANCE_ID = {instance_id};
                const CHART_ID = {chart_id};
                
                console.log('=== Manual Initialization Triggered for Instance', INSTANCE_ID, '===');
                
                // 确保命名空间存在，如果不存在则创建
                if (!window.chartInstances) {{
                    window.chartInstances = {{}};
                    console.log('Created window.chartInstances');
                }}
                
                if (!window.chartInstances[INSTANCE_ID]) {{
                    console.warn('Namespace not found for instance', INSTANCE_ID, ', creating it now...');
                    window.chartInstances[INSTANCE_ID] = {{
                        chartId: CHART_ID,
                        enumLabelsMap: {{}},
                        _currentOption: null,
                        _initialized: false,
                        
                        tooltipFormatter: function(params) {{
                            {self._get_tooltip_formatter_code()}
                        }},
                        
                        updateEnumLabels: function(newLabels) {{
                            window.chartInstances[INSTANCE_ID].enumLabelsMap = newLabels;
                        }}
                    }};
                    console.log('Namespace created on-the-fly for instance', INSTANCE_ID);
                }}
                
                if (window.chartInstances[INSTANCE_ID]._initialized) {{
                    console.log('Instance', INSTANCE_ID, 'already initialized');
                    return;
                }}
                
                // 触发右键菜单的重新初始化（如果图表现在已渲染）
                if (window.setupContextMenuForInstance && window.setupContextMenuForInstance[INSTANCE_ID]) {{
                    console.log('Triggering context menu re-initialization for instance', INSTANCE_ID);
                    // 延迟一点确保图表完全渲染
                    setTimeout(function() {{
                        if (window.setupContextMenuForInstance[INSTANCE_ID]) {{
                            window.setupContextMenuForInstance[INSTANCE_ID]();
                        }}
                    }}, 200);
                }}
                
                // 定义并立即执行 setupTooltip
                function setupTooltip() {{
                    console.log('setupTooltip() called for instance', INSTANCE_ID);
                    let attempts = 0;
                    const maxAttempts = 20;
                    let customLine = null;
                    
                    const interval = setInterval(function() {{
                        let el = null;
                        try {{
                            el = typeof getElement === 'function' ? getElement(CHART_ID) : null;
                            if (!el) {{
                                const elements = document.querySelectorAll('.echarts');
                                for (let elem of elements) {{
                                    if (elem.__nicegui_chart) {{
                                        el = {{ chart: elem.__nicegui_chart }};
                                        break;
                                    }}
                                }}
                            }}
                        }} catch (e) {{}}
                        
                        if (el && el.chart) {{
                            const option = el.chart.getOption();
                            
                            // 计算全局时间范围，确保所有 xAxis 对齐
                            let globalMin = null, globalMax = null;
                            if (option.series) {{
                                option.series.forEach(s => {{
                                    if (s.data && s.data.length > 0) {{
                                        s.data.forEach(point => {{
                                            if (point && point[0] != null) {{
                                                if (globalMin === null || point[0] < globalMin) globalMin = point[0];
                                                if (globalMax === null || point[0] > globalMax) globalMax = point[0];
                                            }}
                                        }});
                                    }}
                                }});
                            }}
                            
                            // 更新时间轴格式化
                            const xAxisConfig = [];
                            if (option.xAxis) {{
                                for (let i = 0; i < option.xAxis.length; i++) {{
                                    const xAxisUpdate = {{
                                        axisLabel: {{
                                            formatter: function(value) {{
                                                const date = new Date(value);
                                                const h = String(date.getUTCHours()).padStart(2, '0');
                                                const m = String(date.getUTCMinutes()).padStart(2, '0');
                                                const s = String(date.getUTCSeconds()).padStart(2, '0');
                                                const ms = String(date.getUTCMilliseconds()).padStart(3, '0');
                                                return h + ':' + m + ':' + s + '.' + ms;
                                            }}
                                        }}
                                    }};
                                    // 如果计算出了全局时间范围，为所有 xAxis 设置相同的 min/max
                                    if (globalMin !== null && globalMax !== null) {{
                                        xAxisUpdate.min = globalMin;
                                        xAxisUpdate.max = globalMax;
                                    }}
                                    xAxisConfig.push(xAxisUpdate);
                                }}
                            }}
                            
                            el.chart.setOption({{
                                xAxis: xAxisConfig,
                                axisPointer: {{
                                    link: [{{xAxisIndex: 'all'}}],
                                    label: {{ show: false }},
                                    lineStyle: {{ opacity: 0 }}
                                }},
                                tooltip: {{
                                    show: true,
                                    trigger: 'axis',
                                    formatter: window.chartInstances[INSTANCE_ID].tooltipFormatter,
                                    axisPointer: {{
                                        type: 'line',
                                        label: {{ show: false }},
                                        lineStyle: {{ opacity: 0 }}
                                    }},
                                    appendToBody: true
                                }}
                            }}, false);
                            
                            // 创建垂直指示线
                            if (!customLine) {{
                                const chartDom = el.chart.getDom();
                                chartDom.style.position = 'relative';
                                
                                customLine = document.createElement('div');
                                customLine.id = 'custom-indicator-line-' + INSTANCE_ID;
                                customLine.style.cssText = 'position:absolute;width:1px;background-color:rgba(102,102,102,0.8);pointer-events:none;display:none;z-index:10;transition:none;';
                                
                                const updateLine = function() {{
                                    try {{
                                        const opt = el.chart.getOption();
                                        if (opt && opt.grid) {{
                                            const grids = opt.grid;
                                            let minTop = Infinity, maxBottom = -Infinity;
                                            // 使用 ECharts 官方方法获取高度
                                            const chartHeight = el.chart.getHeight();
                                            const chartWidth = el.chart.getWidth();
                                            
                                            grids.forEach(g => {{
                                                const top = typeof g.top === 'string' && g.top.includes('%') ? (parseFloat(g.top)/100)*chartHeight : parseFloat(g.top);
                                                const h = typeof g.height === 'string' && g.height.includes('%') ? (parseFloat(g.height)/100)*chartHeight : parseFloat(g.height);
                                                if (top < minTop) minTop = top;
                                                if (top + h > maxBottom) maxBottom = top + h;
                                            }});
                                            
                                            // 检查有效性
                                            if (minTop === Infinity) minTop = 0;
                                            if (maxBottom === -Infinity) maxBottom = chartHeight;
                                            
                                            customLine.style.top = minTop + 'px';
                                            customLine.style.height = (maxBottom - minTop) + 'px';
                                            
                                            // 记录 grid 左右边界用于限位
                                            const firstGrid = grids[0];
                                            if (firstGrid) {{
                                                window.chartInstances[INSTANCE_ID]._gridLeft = typeof firstGrid.left === 'string' && firstGrid.left.includes('%') ? (parseFloat(firstGrid.left)/100)*chartWidth : parseFloat(firstGrid.left);
                                                window.chartInstances[INSTANCE_ID]._gridRight = typeof firstGrid.right === 'string' && firstGrid.right.includes('%') ? chartWidth - (parseFloat(firstGrid.right)/100)*chartWidth : chartWidth - parseFloat(firstGrid.right);
                                            }}
                                        }}
                                    }} catch (e) {{
                                        console.error('Error updating indicator line:', e);
                                    }}
                                }};
                                
                                chartDom.appendChild(customLine);
                                el.chart.on('finished', updateLine);
                                window.addEventListener('resize', updateLine);
                                setTimeout(updateLine, 100);
                                
                                chartDom.addEventListener('mousemove', function(e) {{
                                    const rect = chartDom.getBoundingClientRect();
                                    const x = e.clientX - rect.left;
                                    const left = window.chartInstances[INSTANCE_ID]._gridLeft || 0;
                                    const right = window.chartInstances[INSTANCE_ID]._gridRight || rect.width;
                                    if (x >= left && x <= right) {{
                                        customLine.style.left = x + 'px';
                                        customLine.style.display = 'block';
                                    }} else {{
                                        customLine.style.display = 'none';
                                    }}
                                }});
                                chartDom.addEventListener('mouseleave', function() {{ customLine.style.display = 'none'; }});
                            }}
                            
                            window.chartInstances[INSTANCE_ID]._initialized = true;
                            clearInterval(interval);
                        }} else if (attempts++ >= maxAttempts) {{
                            clearInterval(interval);
                        }}
                    }}, 100);
                }}
                
                // 立即执行初始化
                setupTooltip();
            }})();
        ''')
    
    def _get_tooltip_formatter_code(self):
        """获取tooltip formatter的JavaScript code（作为字符串返回）"""
        return '''
                    if (!params || params.length === 0) return '';
                    if (!Array.isArray(params)) params = [params];
                    
                    // 获取时间戳
                    let timestamp = null;
                    for (let i = 0; i < params.length; i++) {
                        if (params[i].value && params[i].value[0]) {
                            timestamp = params[i].value[0];
                            break;
                        }
                    }
                    
                    if (!timestamp) return '';
                    
                    // 格式化时间（日期+时间+毫秒）
                    const date = new Date(timestamp);
                    const year = date.getUTCFullYear();
                    const month = String(date.getUTCMonth() + 1).padStart(2, '0');
                    const day = String(date.getUTCDate()).padStart(2, '0');
                    const h = String(date.getUTCHours()).padStart(2, '0');
                    const m = String(date.getUTCMinutes()).padStart(2, '0');
                    const s = String(date.getUTCSeconds()).padStart(2, '0');
                    const ms = String(date.getUTCMilliseconds()).padStart(3, '0');
                    const time = year + '-' + month + '-' + day + ' ' + h + ':' + m + ':' + s + '.' + ms;
                    
                    let html = '<div style="font-weight:bold;margin-bottom:8px;border-bottom:1px solid #666;padding-bottom:5px;">' + time + '</div>';
                    
                    // 收集信号数据（去重）
                    const signalsMap = new Map();
                    const enumMap = window.chartInstances[INSTANCE_ID].enumLabelsMap;
                    
                    for (let i = 0; i < params.length; i++) {
                        const p = params[i];
                        const v = p.value ? p.value[1] : null;
                        if (v != null) {
                            const signalIndex = p.seriesIndex + 1;
                            
                            if (signalsMap.has(signalIndex)) continue;
                            
                            // 枚举类型显示文本标签，数值类型显示数字
                            let displayValue;
                            const enumLabels = enumMap[signalIndex.toString()];
                            if (enumLabels) {
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
                                } catch (e) {}
                                
                                if (categoryLabel) {
                                    displayValue = categoryLabel;
                                } else {
                                    const enumVal = Math.round(v);
                                    displayValue = enumLabels[enumVal.toString()] || enumVal.toString();
                                }
                            } else {
                                displayValue = v.toFixed(3);
                            }
                            
                            signalsMap.set(signalIndex, {
                                name: p.seriesName,
                                value: v,
                                displayValue: displayValue,
                                color: p.color,
                                index: signalIndex
                            });
                        }
                    }
                    
                    // 按信号编号排序
                    let signals = Array.from(signalsMap.values());
                    signals.sort((a, b) => a.index - b.index);
                    
                    // 分栏显示
                    const maxPerColumn = 12;
                    const numColumns = Math.ceil(signals.length / maxPerColumn);
                    
                    if (numColumns > 1) {
                        html += '<div style="display:flex;gap:20px;">';
                        for (let col = 0; col < numColumns; col++) {
                            html += '<div style="flex:0 0 auto;min-width:240px;">';
                            const start = col * maxPerColumn;
                            const end = Math.min(start + maxPerColumn, signals.length);
                            for (let i = start; i < end; i++) {
                                const sig = signals[i];
                                html += '<div style="margin:3px 0;display:flex;align-items:center;">';
                                html += '<span style="width:8px;height:8px;background-color:' + sig.color + ';border-radius:50%;margin-right:8px;flex-shrink:0;"></span>';
                                html += '<span style="min-width:120px;font-size:11px;flex-shrink:0;">' + sig.name + '</span>';
                                html += '<span style="font-weight:bold;font-size:11px;margin-left:8px;text-align:right;flex-grow:1;">' + sig.displayValue + '</span>';
                                html += '</div>';
                            }
                            html += '</div>';
                        }
                        html += '</div>';
                    } else {
                        for (let i = 0; i < signals.length; i++) {
                            const sig = signals[i];
                            html += '<div style="margin:4px 0;display:flex;align-items:center;min-width:250px;">';
                            html += '<span style="width:10px;height:10px;background-color:' + sig.color + ';border-radius:50%;margin-right:10px;flex-shrink:0;"></span>';
                            html += '<span style="min-width:140px;font-size:12px;flex-shrink:0;">' + sig.name + '</span>';
                            html += '<span style="font-weight:bold;font-size:12px;margin-left:10px;text-align:right;flex-grow:1;">' + sig.displayValue + '</span>';
                            html += '</div>';
                        }
                    }
                    
                    return html;
        '''
    
    def _setup_javascript_optimized(self):
        """优化的JavaScript设置 - 使用实例隔离的命名空间"""
        chart_id = self.chart_element.id
        instance_id = self.instance_id
        
        # 使用实例ID创建唯一的命名空间，避免多实例冲突
        ui.add_body_html(f'''
        <script>
        (function() {{
            console.log('=== Chart Widget Script Starting ===');
            console.log('Instance ID:', {instance_id});
            console.log('Chart ID:', {chart_id});
            
            const INSTANCE_ID = {instance_id};
            const CHART_ID = {chart_id};
            
            // 为每个实例创建独立的命名空间
            if (!window.chartInstances) {{
                window.chartInstances = {{}};
            }}
            
            window.chartInstances[INSTANCE_ID] = {{
                chartId: CHART_ID,
                enumLabelsMap: {{}},
                _currentOption: null,
                _initialized: false,
                
                tooltipFormatter: function(params) {{
                    {self._get_tooltip_formatter_code()}
                }},
                
                updateEnumLabels: function(newLabels) {{
                    window.chartInstances[INSTANCE_ID].enumLabelsMap = newLabels;
                }}
            }};
        
        function setupTooltip() {{
            if (window.chartInstances[INSTANCE_ID]._initialized) return;
            
            console.log('setupTooltip() called for instance', INSTANCE_ID);
            let attempts = 0;
            const maxAttempts = 20;
            let customLine = null;
            
            const interval = setInterval(function() {{
                let el = null;
                try {{
                    el = typeof getElement === 'function' ? getElement(CHART_ID) : null;
                    if (!el) {{
                        const elements = document.querySelectorAll('.echarts');
                        for (let elem of elements) {{
                            if (elem.__nicegui_chart) {{
                                el = {{ chart: elem.__nicegui_chart }};
                                break;
                            }}
                        }}
                    }}
                }} catch (e) {{}}
                
                if (el && el.chart) {{
                    const option = el.chart.getOption();
                    
                    // 计算全局时间范围，确保所有 xAxis 对齐
                    let globalMin = null, globalMax = null;
                    if (option.series) {{
                        option.series.forEach(s => {{
                            if (s.data && s.data.length > 0) {{
                                s.data.forEach(point => {{
                                    if (point && point[0] != null) {{
                                        if (globalMin === null || point[0] < globalMin) globalMin = point[0];
                                        if (globalMax === null || point[0] > globalMax) globalMax = point[0];
                                    }}
                                }});
                            }}
                        }});
                    }}
                    
                    const xAxisConfig = [];
                    if (option.xAxis) {{
                        for (let i = 0; i < option.xAxis.length; i++) {{
                            const xAxisUpdate = {{
                                axisLabel: {{
                                    formatter: function(value) {{
                                        const date = new Date(value);
                                        const h = String(date.getUTCHours()).padStart(2, '0');
                                        const m = String(date.getUTCMinutes()).padStart(2, '0');
                                        const s = String(date.getUTCSeconds()).padStart(2, '0');
                                        const ms = String(date.getUTCMilliseconds()).padStart(3, '0');
                                        return h + ':' + m + ':' + s + '.' + ms;
                                    }}
                                }}
                            }};
                            // 如果计算出了全局时间范围，为所有 xAxis 设置相同的 min/max
                            if (globalMin !== null && globalMax !== null) {{
                                xAxisUpdate.min = globalMin;
                                xAxisUpdate.max = globalMax;
                            }}
                            xAxisConfig.push(xAxisUpdate);
                        }}
                    }}
                    
                    el.chart.setOption({{
                        xAxis: xAxisConfig,
                        axisPointer: {{
                            link: [{{xAxisIndex: 'all'}}],
                            label: {{ show: false }},
                            lineStyle: {{ opacity: 0 }}
                        }},
                        tooltip: {{
                            show: true,
                            trigger: 'axis',
                            formatter: window.chartInstances[INSTANCE_ID].tooltipFormatter,
                            axisPointer: {{
                                type: 'line',
                                label: {{ show: false }},
                                lineStyle: {{ opacity: 0 }}
                            }},
                            appendToBody: true
                        }}
                    }}, false);
                    
                    if (!customLine) {{
                        const chartDom = el.chart.getDom();
                        chartDom.style.position = 'relative';
                        
                        customLine = document.createElement('div');
                        customLine.id = 'custom-indicator-line-' + INSTANCE_ID;
                        customLine.style.cssText = 'position:absolute;width:1px;background-color:rgba(102,102,102,0.8);pointer-events:none;display:none;z-index:10;transition:none;';
                        
                        const updateLine = function() {{
                            try {{
                                const opt = el.chart.getOption();
                                if (opt && opt.grid) {{
                                    const grids = opt.grid;
                                    let minTop = Infinity, maxBottom = -Infinity;
                                    const chartHeight = chartDom.offsetHeight;
                                    grids.forEach(g => {{
                                        const top = typeof g.top === 'string' && g.top.includes('%') ? (parseFloat(g.top)/100)*chartHeight : parseFloat(g.top);
                                        const h = typeof g.height === 'string' && g.height.includes('%') ? (parseFloat(g.height)/100)*chartHeight : parseFloat(g.height);
                                        if (top < minTop) minTop = top;
                                        if (top + h > maxBottom) maxBottom = top + h;
                                    }});
                                    customLine.style.top = minTop + 'px';
                                    customLine.style.height = (maxBottom - minTop) + 'px';
                                    
                                    const firstGrid = grids[0];
                                    const chartWidth = chartDom.offsetWidth;
                                    window.chartInstances[INSTANCE_ID]._gridLeft = typeof firstGrid.left === 'string' && firstGrid.left.includes('%') ? (parseFloat(firstGrid.left)/100)*chartWidth : parseFloat(firstGrid.left);
                                    window.chartInstances[INSTANCE_ID]._gridRight = typeof firstGrid.right === 'string' && firstGrid.right.includes('%') ? chartWidth - (parseFloat(firstGrid.right)/100)*chartWidth : chartWidth - parseFloat(firstGrid.right);
                                }}
                            }} catch (e) {{}}
                        }};
                        
                        chartDom.appendChild(customLine);
                        el.chart.on('finished', updateLine);
                        window.addEventListener('resize', updateLine);
                        setTimeout(updateLine, 100);
                        
                        chartDom.addEventListener('mousemove', function(e) {{
                            const rect = chartDom.getBoundingClientRect();
                            const x = e.clientX - rect.left;
                            const left = window.chartInstances[INSTANCE_ID]._gridLeft || 0;
                            const right = window.chartInstances[INSTANCE_ID]._gridRight || rect.width;
                            if (x >= left && x <= right) {{
                                customLine.style.left = x + 'px';
                                customLine.style.display = 'block';
                            }} else {{
                                customLine.style.display = 'none';
                            }}
                        }});
                        chartDom.addEventListener('mouseleave', function() {{ customLine.style.display = 'none'; }});
                    }}
                    
                    el.chart.on('finished', function() {{
                        const opt = el.chart.getOption();
                        window.chartInstances[INSTANCE_ID]._currentOption = opt;
                        const xAxisCfg = [];
                        if (opt.xAxis) {{
                            for (let i = 0; i < opt.xAxis.length; i++) {{
                                xAxisCfg.push({{
                                    axisLabel: {{
                                        formatter: function(value) {{
                                            const date = new Date(value);
                                            const h = String(date.getUTCHours()).padStart(2, '0');
                                            const m = String(date.getUTCMinutes()).padStart(2, '0');
                                            const s = String(date.getUTCSeconds()).padStart(2, '0');
                                            const ms = String(date.getUTCMilliseconds()).padStart(3, '0');
                                            return h + ':' + m + ':' + s + '.' + ms;
                                        }}
                                    }}
                                }});
                            }}
                        }}
                        el.chart.setOption({{
                            xAxis: xAxisCfg,
                            axisPointer: {{ link: [{{xAxisIndex: 'all'}}] }},
                            tooltip: {{ formatter: window.chartInstances[INSTANCE_ID].tooltipFormatter }}
                        }}, false);
                    }});
                    
                    window.chartInstances[INSTANCE_ID]._initialized = true;
                    clearInterval(interval);
                }} else if (attempts++ >= maxAttempts) {{
                    clearInterval(interval);
                }}
            }}, 100);
        }}
        
        window['setupTooltip_{instance_id}'] = setupTooltip;
        
        function initWhenVisible() {{
            let initialized = false;
            const tryInit = () => {{
                if (initialized) return true;
                try {{
                    const el = typeof getElement === 'function' ? getElement(CHART_ID) : null;
                    if (el && el.chart) {{
                        initialized = true;
                        setupTooltip();
                        return true;
                    }}
                }} catch (e) {{}}
                return false;
            }};
            if (tryInit()) return;
            setTimeout(() => {{
                if (tryInit()) return;
                let retries = 0;
                const interval = setInterval(() => {{
                    if (tryInit() || retries++ >= 10) clearInterval(interval);
                }}, 100);
            }}, 50);
        }}
        
        if (document.readyState === 'loading') {{
            document.addEventListener('DOMContentLoaded', initWhenVisible);
        }} else {{
            initWhenVisible();
        }}
        }})();
        </script>
        ''')
    
    def update_enum_labels(self, signal_types: Dict[str, Dict[str, Any]], realtime_plot=None):
        """
        更新枚举标签映射
        
        Args:
            signal_types: 信号类型配置，格式如 {'signal_name': {'type': 'enum', 'enum_labels': {...}}}
            realtime_plot: 可选的 RealtimePlot 实例，如果提供则自动更新引用
        """
        if realtime_plot is not None:
            self.set_realtime_plot(realtime_plot)
        enum_labels_json = {}
        for signal_index, (signal_name, config) in enumerate(signal_types.items(), start=1):
            if config['type'] == 'enum':
                enum_labels_json[str(signal_index)] = {str(k): v for k, v in config['enum_labels'].items()}
        
        enum_labels_js = json.dumps(enum_labels_json)
        
        update_script = f'''
            if (window.chartInstances && window.chartInstances[{self.instance_id}]) {{
                window.chartInstances[{self.instance_id}].updateEnumLabels({enum_labels_js});
            }}
        '''
        
        def execute_update():
            try:
                ui.run_javascript(update_script)
            except (AssertionError, RuntimeError):
                ui.timer(0.1, lambda: ui.run_javascript(update_script), once=True)
        
        try:
            execute_update()
        except (AssertionError, RuntimeError):
            ui.timer(0.1, execute_update, once=True)
        
        signal_names_list = list(signal_types.keys())
        self._signal_names_list = signal_names_list
        if self.realtime_plot and hasattr(self, 'subplot_order_container'):
            self.update_subplot_order_ui()
        elif hasattr(self, 'subplot_order_container'):
            self.update_subplot_order_ui()
    
    def update_chart_option(self, new_option: Dict[str, Any], exclude_tooltip: bool = True, realtime_plot=None):
        """更新图表配置"""
        if realtime_plot is not None:
            self.set_realtime_plot(realtime_plot)
        new_height = new_option.get('height', 1000)
        
        update_config = {}
        for key, value in new_option.items():
            if exclude_tooltip and key in ['tooltip', 'axisPointer']:
                continue
            update_config[key] = value
        
        config_json = json.dumps(update_config)
        
        def execute_update():
            try:
                ui.run_javascript(f'''
                const el = getElement({self.chart_element.id});
                if (el && el.chart) {{
                    const newConfig = {config_json};
                    el.chart.setOption(newConfig, true, false);
                    const option = el.chart.getOption();
                    window.chartInstances[{self.instance_id}]._currentOption = option;
                    
                    // 计算全局时间范围，确保所有 xAxis 对齐
                    let globalMin = null, globalMax = null;
                    if (option.series) {{
                        option.series.forEach(s => {{
                            if (s.data && s.data.length > 0) {{
                                s.data.forEach(point => {{
                                    if (point && point[0] != null) {{
                                        if (globalMin === null || point[0] < globalMin) globalMin = point[0];
                                        if (globalMax === null || point[0] > globalMax) globalMax = point[0];
                                    }}
                                }});
                            }}
                        }});
                    }}
                    
                    const xAxisConfig = [];
                    if (option.xAxis) {{
                        for (let i = 0; i < option.xAxis.length; i++) {{
                            const xAxisUpdate = {{
                                axisLabel: {{
                                    formatter: function(value) {{
                                        const date = new Date(value);
                                        const h = String(date.getUTCHours()).padStart(2, '0');
                                        const m = String(date.getUTCMinutes()).padStart(2, '0');
                                        const s = String(date.getUTCSeconds()).padStart(2, '0');
                                        const ms = String(date.getUTCMilliseconds()).padStart(3, '0');
                                        return h + ':' + m + ':' + s + '.' + ms;
                                    }}
                                }}
                            }};
                            // 如果计算出了全局时间范围，为所有 xAxis 设置相同的 min/max
                            if (globalMin !== null && globalMax !== null) {{
                                xAxisUpdate.min = globalMin;
                                xAxisUpdate.max = globalMax;
                            }}
                            xAxisConfig.push(xAxisUpdate);
                        }}
                    }}
                    
                    el.chart.setOption({{
                        xAxis: xAxisConfig,
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
                            appendToBody: true
                        }}
                    }}, false, false);
                }}
                ''')
            except (AssertionError, RuntimeError):
                ui.timer(0.1, execute_update, once=True)
        
        try:
            execute_update()
        except (AssertionError, RuntimeError):
            ui.timer(0.1, execute_update, once=True)
        
        self.chart_element._props['style'] = f'height: {new_height}px; width: 100%; min-height: {new_height}px;'
        self.chart_element.update()
    
    def update_series_data(self, series_data: list):
        """更新系列数据"""
        series_json = json.dumps(series_data)
        try:
            ui.run_javascript(f'''
                const el = getElement({self.chart_element.id});
                if (el && el.chart) {{
                    const seriesData = {series_json};
                    const option = el.chart.getOption();
                    if (option.series) {{
                        let dataZoom = null;
                        if (option.dataZoom) {{
                            for (let z of option.dataZoom) {{
                                if (z.type === 'inside') {{ dataZoom = z; break; }}
                            }}
                            if (!dataZoom && option.dataZoom.length > 0) dataZoom = option.dataZoom[0];
                        }}
                        const startPercent = dataZoom && dataZoom.start !== undefined ? dataZoom.start : 0;
                        const endPercent = dataZoom && dataZoom.end !== undefined ? dataZoom.end : 100;

                        for (let i = 0; i < seriesData.length && i < option.series.length; i++) {{
                            option.series[i].data = seriesData[i].data;
                            const totalPoints = seriesData[i].data ? seriesData[i].data.length : 0;
                            const visiblePointCount = totalPoints * (endPercent - startPercent) / 100;
                            
                            if (visiblePointCount > 150) {{
                                option.series[i].showSymbol = false;
                                option.series[i].symbolSize = 4;
                            }} else if (visiblePointCount > 50) {{
                                option.series[i].showSymbol = true;
                                option.series[i].symbolSize = 4;
                            }} else {{
                                option.series[i].showSymbol = true;
                                option.series[i].symbolSize = 6;
                            }}
                        }}
                        el.chart.setOption({{ series: option.series }}, false, false);
                    }}
                }}
            ''')
        except Exception:
            for i, series_config in enumerate(series_data):
                if i < len(self.chart_element.options.get('series', [])):
                    self.chart_element.options['series'][i]['data'] = series_config['data']
                    self.chart_element.options['series'][i]['showSymbol'] = series_config['showSymbol']
                    self.chart_element.options['series'][i]['symbolSize'] = series_config['symbolSize']
            self.chart_element.update()
    
    def get_element(self):
        """获取图表元素（用于在UI布局中使用）"""
        return self.chart_element
    
    def _setup_sidebar(self):
        """设置子图顺序调节侧边栏"""
        with ui.element('div').style(
            'position: fixed; top: 0; left: 0; width: 100%; height: 100%; '
            'background: rgba(0,0,0,0.3); z-index: 9998; display: none;'
        ) as self.sidebar_overlay:
            self.sidebar_overlay.on('click', self.hide_sidebar)
            
        with ui.card().classes('bg-white').style(
            'position: fixed; right: -320px; left: auto; top: 0; width: 300px; height: 100vh; '
            'z-index: 9999; transition: right 0.3s ease; overflow-y: auto; '
            'box-shadow: -1px 0 4px rgba(0,0,0,0.1); border-left: 1px solid #e5e5e5; padding: 0;'
        ) as self.sidebar_card:
            with ui.row().classes('items-center justify-between p-3 border-b border-gray-100 w-full'):
                ui.label('子图顺序').classes('text-body1').style('color: #666; font-weight: 500;')
                ui.button(icon='close', on_click=self.hide_sidebar).props('flat dense round color=grey').classes('text-gray-400')
            with ui.column().classes('w-full p-3') as self.subplot_order_container:
                pass
        self._setup_context_menu()
    
    def _setup_context_menu(self):
        """设置右键菜单"""
        instance_id = self.instance_id
        with ui.row().style('display: none;'):
            trigger_btn = ui.button('Show Sidebar', on_click=self.show_sidebar)
            trigger_btn_id = trigger_btn.id
        
        ui.add_body_html(f'''
        <script>
        (function() {{
            const instanceId = '{instance_id}';
            const targetClass = 'chart-instance-' + instanceId;
            const triggerBtnId = '{trigger_btn_id}'; 
            let menuVisible = false;
            const menu = document.createElement('div');
            menu.id = 'context-menu-' + instanceId;
            menu.style.cssText = 'position: fixed; background: white; border: 1px solid #ccc; border-radius: 4px; box-shadow: 0 2px 8px rgba(0,0,0,0.15); padding: 4px 0; z-index: 10000; display: none; min-width: 150px;';
            menu.innerHTML = `
                <div class="menu-item" data-action="show-sidebar" style="padding: 8px 16px; cursor: pointer; font-size: 14px; display: flex; align-items: center;">
                    <span style="margin-right: 8px;">⚙️</span>
                    <span>子图顺序调节</span>
                </div>
            `;
            document.body.appendChild(menu);
            menu.querySelectorAll('.menu-item').forEach(item => {{
                item.addEventListener('mouseenter', function() {{ this.style.backgroundColor = '#f0f0f0'; }});
                item.addEventListener('mouseleave', function() {{ this.style.backgroundColor = 'transparent'; }});
            }});
            document.addEventListener('contextmenu', function(e) {{
                const chartContainer = e.target.closest('.' + targetClass);
                if (chartContainer) {{
                    e.preventDefault();
                    e.stopPropagation();
                    document.querySelectorAll('[id^="context-menu-"]').forEach(m => {{ if (m.id !== menu.id) m.style.display = 'none'; }});
                    menu.style.display = 'block';
                    menu.style.left = e.clientX + 'px';
                    menu.style.top = e.clientY + 'px';
                    menuVisible = true;
                }} else if (menuVisible) {{
                    menu.style.display = 'none';
                    menuVisible = false;
                }}
            }}, true);
            document.addEventListener('click', function(e) {{
                if (menu.contains(e.target)) return;
                menu.style.display = 'none';
                menuVisible = false;
            }});
            menu.addEventListener('click', function(e) {{
                const action = e.target.closest('.menu-item')?.dataset.action;
                if (action === 'show-sidebar') {{
                    menu.style.display = 'none';
                    menuVisible = false;
                    const btn = document.getElementById('c' + triggerBtnId) || document.getElementById(triggerBtnId);
                    if (btn) btn.click();
                }}
            }});
        }})();
        </script>
        ''')
    
    def show_sidebar(self):
        """显示侧边栏"""
        self.update_subplot_order_ui()
        if hasattr(self, 'sidebar_card') and self.sidebar_card:
            self.sidebar_card.style('right: 0px; left: auto;')
            if hasattr(self, 'sidebar_overlay'):
                self.sidebar_overlay.style('display: block;')
    
    def hide_sidebar(self):
        """隐藏侧边栏"""
        if hasattr(self, 'sidebar_card') and self.sidebar_card:
            self.sidebar_card.style('right: -300px; left: auto;')
            if hasattr(self, 'sidebar_overlay'):
                self.sidebar_overlay.style('display: none;')
    
    def update_subplot_order_ui(self, signal_names_list: list = None, chart_widget_ref=None, is_running_ref=None):
        """更新子图顺序控制UI"""
        if signal_names_list is not None:
            self._signal_names_list = signal_names_list
        if chart_widget_ref is not None:
            self._chart_widget_ref = chart_widget_ref
        if is_running_ref is not None:
            self._is_running_ref = is_running_ref
        if not hasattr(self, '_signal_names_list') or self._signal_names_list is None:
            if self.realtime_plot and hasattr(self.realtime_plot, 'signal_types') and self.realtime_plot.signal_types:
                self._signal_names_list = list(self.realtime_plot.signal_types.keys())
            elif self.realtime_plot:
                num_signals = getattr(self.realtime_plot, 'num_signals', 0)
                self._signal_names_list = [f'Signal {i+1}' for i in range(num_signals)]
            else:
                return
        if not hasattr(self, '_chart_widget_ref') or self._chart_widget_ref is None:
            self._chart_widget_ref = self
        signal_names_list = self._signal_names_list
        chart_widget_ref = self._chart_widget_ref
        is_running_ref = getattr(self, '_is_running_ref', None)
        if not hasattr(self, 'subplot_order_container'):
            self._setup_sidebar()
        if self.realtime_plot:
            current_order = self.realtime_plot.get_subplot_order()
        else:
            if self._internal_subplot_order is None or len(self._internal_subplot_order) != len(signal_names_list):
                self._internal_subplot_order = list(range(len(signal_names_list)))
            current_order = self._internal_subplot_order
        self.subplot_order_container.clear()
        with self.subplot_order_container:
            for display_pos, signal_idx in enumerate(current_order):
                signal_name = signal_names_list[signal_idx] if signal_idx < len(signal_names_list) else f'Signal {signal_idx+1}'
                is_first = (display_pos == 0)
                is_last = (display_pos == len(current_order) - 1)
                with ui.row().classes('w-full items-center py-2 px-1 border-b border-gray-100'):
                    ui.label(str(display_pos + 1)).classes('text-gray-400 text-xs px-2 min-w-[24px] text-center')
                    ui.label(signal_name).classes('flex-1 text-sm text-gray-700 break-all px-2')
                    with ui.row().classes('gap-1'):
                        ui.button(icon='arrow_upward', on_click=lambda idx=signal_idx: self._execute_move(
                            idx, 'up', signal_names_list, chart_widget_ref, is_running_ref
                        )).props('flat dense size=sm').set_enabled(not is_first)
                        ui.button(icon='arrow_downward', on_click=lambda idx=signal_idx: self._execute_move(
                            idx, 'down', signal_names_list, chart_widget_ref, is_running_ref
                        )).props('flat dense size=sm').set_enabled(not is_last)
    
    def _execute_move(self, signal_idx, direction, signal_names_list, chart_widget_ref, is_running_ref):
        """执行移动操作"""
        if self.realtime_plot:
            if direction == 'up': self.realtime_plot.move_subplot_up(signal_idx)
            else: self.realtime_plot.move_subplot_down(signal_idx)
            new_option = self.realtime_plot.get_option()
            if chart_widget_ref: chart_widget_ref.update_chart_option(new_option, exclude_tooltip=True)
            if (is_running_ref and is_running_ref() and self.realtime_plot._data_buffer is not None):
                series_data = [{'data': new_option['series'][i]['data'], 'showSymbol': new_option['series'][i]['showSymbol'], 'symbolSize': new_option['series'][i]['symbolSize']} for i in range(len(new_option['series']))]
                if chart_widget_ref: chart_widget_ref.update_series_data(series_data)
        else:
            if self._internal_subplot_order is None: self._internal_subplot_order = list(range(len(signal_names_list)))
            current_order = self._internal_subplot_order
            try:
                pos = current_order.index(signal_idx)
                if direction == 'up' and pos > 0: current_order[pos], current_order[pos-1] = current_order[pos-1], current_order[pos]
                elif direction == 'down' and pos < len(current_order) - 1: current_order[pos], current_order[pos+1] = current_order[pos+1], current_order[pos]
            except ValueError: return
            order_json = json.dumps(current_order)
            def update_chart_order():
                try:
                    ui.run_javascript(f'''
                    const el = getElement({self.chart_element.id});
                    if (el && el.chart) {{
                        const newOrder = {order_json};
                        const option = el.chart.getOption();
                        const originalGrid = option.grid || [];
                        const originalTitle = option.title || [];
                        const gridTopPositions = [];
                        for (let i = 0; i < originalGrid.length; i++) {{ if (originalGrid[i]) gridTopPositions.push({{index: i, top: originalGrid[i].top || 0}}); }}
                        gridTopPositions.sort((a, b) => a.top - b.top);
                        const currentOrder = gridTopPositions.map(p => p.index);
                        const titleByOriginalIndex = {{}};
                        for (let displayPos = 0; displayPos < currentOrder.length && displayPos < originalTitle.length; displayPos++) {{ titleByOriginalIndex[currentOrder[displayPos]] = originalTitle[displayPos]; }}
                        let chartHeightPerSignal = 150, chartSpacing = 2, baseTopOffset = 30;
                        if (gridTopPositions.length > 0 && originalGrid[gridTopPositions[0].index]?.height) chartHeightPerSignal = originalGrid[gridTopPositions[0].index].height;
                        if (gridTopPositions.length >= 2) {{ chartSpacing = gridTopPositions[1].top - gridTopPositions[0].top - chartHeightPerSignal; if (chartSpacing < 0 || chartSpacing > 50) chartSpacing = 2; }}
                        let baseTop = gridTopPositions.length > 0 ? gridTopPositions[0].top - chartSpacing : baseTopOffset;
                        const reorderedGrid = [], reorderedTitle = [], indexToDisplayPos = {{}};
                        newOrder.forEach((originalIdx, displayPos) => indexToDisplayPos[originalIdx] = displayPos);
                        for (let originalIdx = 0; originalIdx < originalGrid.length; originalIdx++) {{
                            if (originalGrid[originalIdx]) {{
                                const displayPos = indexToDisplayPos[originalIdx] !== undefined ? indexToDisplayPos[originalIdx] : originalIdx;
                                const grid = {{...originalGrid[originalIdx]}};
                                grid.top = chartSpacing + displayPos * (chartHeightPerSignal + chartSpacing) + baseTop;
                                grid.backgroundColor = (displayPos % 2 === 1) ? '#fafafa' : '#f2f2f2';
                                reorderedGrid[originalIdx] = grid;
                            }}
                        }}
                        const actualTitleOffset = chartHeightPerSignal >= 100 ? 22 : 18;
                        newOrder.forEach((originalIdx, displayPos) => {{
                            if (titleByOriginalIndex[originalIdx]) {{
                                const title = {{...titleByOriginalIndex[originalIdx]}};
                                title.top = chartSpacing + displayPos * (chartHeightPerSignal + chartSpacing) + baseTop - actualTitleOffset;
                                reorderedTitle.push(title);
                            }}
                        }});
                        const totalHeight = chartHeightPerSignal * newOrder.length + chartSpacing * (newOrder.length + 1) + 80;
                        el.chart.setOption({{ height: totalHeight, grid: reorderedGrid, title: reorderedTitle }}, false, false);
                        const chartDom = el.chart.getDom();
                        if (chartDom?.parentElement) {{ chartDom.parentElement.style.height = totalHeight + 'px'; chartDom.style.height = totalHeight + 'px'; }}
                    }}
                    ''')
                except Exception: pass
            try: update_chart_order()
            except (AssertionError, RuntimeError): ui.timer(0.1, update_chart_order, once=True)
        self.update_subplot_order_ui(signal_names_list, chart_widget_ref, is_running_ref)
    
    def set_realtime_plot(self, realtime_plot):
        """设置 RealtimePlot 实例"""
        self.realtime_plot = realtime_plot
        if hasattr(self, 'subplot_order_container'):
            if hasattr(self, '_signal_names_list'): delattr(self, '_signal_names_list')
            self.update_subplot_order_ui()
