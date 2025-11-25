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
    
    def __init__(self, initial_option: Dict[str, Any], defer_init: bool = False):
        """
        初始化图表组件
        
        Args:
            initial_option: 初始的ECharts配置选项
            defer_init: 是否延迟初始化JavaScript（用于tab等延迟渲染场景）
        """
        RealtimeChartWidget._instance_count += 1
        self.instance_id = RealtimeChartWidget._instance_count
        self.chart_element: Optional[Any] = None
        self._initial_option = initial_option
        self._js_initialized = False  # 标记JavaScript是否已初始化
        self._defer_init = defer_init
        self._setup_chart()
    
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
            canvas {
                pointer-events: none;
            }
            </style>
            ''')
            RealtimeChartWidget._global_init_done = True
        
        # 创建图表元素
        self.chart_element = ui.echart(self._initial_option).style(
            f'height: {chart_height}px; width: 100%; min-height: {chart_height}px;'
        )
        
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
                
                // 定义并立即执行 setupTooltip
                function setupTooltip() {{
                    console.log('setupTooltip() called for instance', INSTANCE_ID);
                    let attempts = 0;
                    const maxAttempts = 20;  // 减少到20次（2秒）
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
                        }} catch (e) {{
                            console.warn('Failed to get chart element:', e);
                        }}
                        
                        if (el && el.chart) {{
                            const option = el.chart.getOption();
                            const xAxisConfig = [];
                            if (option.xAxis) {{
                                for (let i = 0; i < option.xAxis.length; i++) {{
                                    xAxisConfig.push({{
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
                                    confine: false,
                                    appendToBody: true,
                                    extraCssText: 'min-width: 280px; max-width: 600px;'
                                }}
                            }}, false);
                            
                            // 创建垂直指示线
                            if (!customLine) {{
                                const chartDom = el.chart.getDom();
                                const chartContainer = chartDom.parentElement || chartDom;
                                
                                customLine = document.createElement('div');
                                customLine.id = 'custom-indicator-line-' + INSTANCE_ID;
                                customLine.style.cssText = [
                                    'position: absolute', 'top: 0', 'left: 0', 'width: 2px',
                                    'background-color: rgba(102, 102, 102, 0.8)',
                                    'pointer-events: none', 'display: none', 'z-index: 9999'
                                ].join(';');
                                
                                const updateLineHeight = function() {{
                                    const height = chartDom.offsetHeight || chartContainer.offsetHeight || 800;
                                    customLine.style.height = height + 'px';
                                }};
                                
                                const containerPosition = window.getComputedStyle(chartContainer).position;
                                if (containerPosition === 'static') {{
                                    chartContainer.style.position = 'relative';
                                }}
                                
                                chartContainer.appendChild(customLine);
                                setTimeout(updateLineHeight, 100);
                                
                                window.addEventListener('resize', updateLineHeight);
                                el.chart.on('finished', updateLineHeight);
                                
                                const mouseMoveHandler = function(e) {{
                                    const rect = chartContainer.getBoundingClientRect();
                                    const x = e.clientX - rect.left;
                                    if (x >= 0 && x <= rect.width) {{
                                        customLine.style.left = x + 'px';
                                        customLine.style.display = 'block';
                                    }}
                                }};
                                
                                const mouseLeaveHandler = function() {{
                                    customLine.style.display = 'none';
                                }};
                                
                                chartContainer.addEventListener('mousemove', mouseMoveHandler);
                                chartDom.addEventListener('mousemove', mouseMoveHandler);
                                chartContainer.addEventListener('mouseleave', mouseLeaveHandler);
                                chartDom.addEventListener('mouseleave', mouseLeaveHandler);
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
                            console.log('Chart instance', INSTANCE_ID, 'initialized successfully');
                            clearInterval(interval);
                        }} else if (attempts++ >= maxAttempts) {{
                            console.error('Failed to initialize chart', INSTANCE_ID, 'after', maxAttempts, 'attempts');
                            clearInterval(interval);
                        }}
                    }}, 100);
                }}
                
                // 立即执行初始化
                setupTooltip();
            }})();
        ''')
    
    def _get_tooltip_formatter_code(self):
        """获取tooltip formatter的JavaScript代码（作为字符串返回）"""
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
        """优化的JavaScript设置 - 使用实例隔离的命名空间 + IntersectionObserver"""
        chart_id = self.chart_element.id
        instance_id = self.instance_id
        
        # 使用实例ID创建唯一的命名空间，避免多实例冲突
        ui.add_body_html(f'''
        <script>
        (function() {{
            console.log('=== Chart Widget Script Starting ===');
            console.log('Instance ID:', {instance_id});
            console.log('Chart ID:', {chart_id});
            
            // 使用IIFE创建独立作用域，避免全局污染
            const INSTANCE_ID = {instance_id};
            const CHART_ID = {chart_id};
            
            // 为每个实例创建独立的命名空间
            if (!window.chartInstances) {{
                window.chartInstances = {{}};
                console.log('Created window.chartInstances');
            }}
            
            console.log('Creating chart instance namespace for ID:', INSTANCE_ID);
            
            window.chartInstances[INSTANCE_ID] = {{
                chartId: CHART_ID,
                enumLabelsMap: {{}},
                _currentOption: null,  // 存储当前option，供tooltip使用
                _initialized: false,  // 初始化状态标记
                
                // Tooltip formatter 函数
                tooltipFormatter: function(params) {{
                    {self._get_tooltip_formatter_code()}
                }},
                
                updateEnumLabels: function(newLabels) {{
                    window.chartInstances[INSTANCE_ID].enumLabelsMap = newLabels;
                }}
            }};
        
        // 初始化 tooltip 和指示线
        function setupTooltip() {{
            // 检查是否已经初始化
            if (window.chartInstances[INSTANCE_ID]._initialized) {{
                console.log('Chart instance', INSTANCE_ID, 'already initialized, skipping');
                return;
            }}
            
            console.log('setupTooltip() called for instance', INSTANCE_ID);
            let attempts = 0;
            const maxAttempts = 20;  // 减少到20次（2秒）
            let customLine = null;
            
            const interval = setInterval(function() {{
                // 只在前2次和最后尝试时打印日志
                if (attempts < 2 || attempts >= maxAttempts - 1) {{
                    console.log('[Chart', INSTANCE_ID, '] Attempt', attempts + 1, '/', maxAttempts);
                }}
                
                // 获取图表元素
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
                }} catch (e) {{
                    // 静默失败，减少日志
                }}
                
                if (el && el.chart) {{
                    // 设置tooltip formatter和axisPointer（确保所有x轴联动）
                    // 同时设置x轴时间标签的formatter，避免时区转换
                    const option = el.chart.getOption();
                    const xAxisConfig = [];
                    if (option.xAxis) {{
                        for (let i = 0; i < option.xAxis.length; i++) {{
                            xAxisConfig.push({{
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
                        xAxis: xAxisConfig,
                        axisPointer: {{
                            link: [{{xAxisIndex: 'all'}}],  // 关键：链接所有x轴，确保tooltip只触发一次
                            label: {{
                                show: false
                            }},
                            lineStyle: {{
                                opacity: 0  // 隐藏ECharts自带的指示线，使用自定义线
                            }}
                        }},
                        tooltip: {{
                            show: true,  // 显式启用tooltip
                            trigger: 'axis',
                            formatter: window.chartInstances[INSTANCE_ID].tooltipFormatter,
                            axisPointer: {{
                                type: 'line',
                                label: {{
                                    show: false
                                }},
                                lineStyle: {{
                                    opacity: 0
                                }}
                            }},
                            confine: false,  // 允许tooltip超出容器
                            appendToBody: true,  // 添加到body，避免被容器裁剪
                            extraCssText: 'min-width: 280px; max-width: 600px;'  // 设置tooltip宽度
                        }}
                    }}, false);
                    
                    // 创建垂直指示线（如果尚未创建）
                    if (!customLine) {{
                        const chartDom = el.chart.getDom();
                        const chartContainer = chartDom.parentElement || chartDom;
                        
                        // 创建自定义竖线元素
                        customLine = document.createElement('div');
                        customLine.id = 'custom-indicator-line-' + INSTANCE_ID;
                        customLine.style.cssText = [
                            'position: absolute',
                            'top: 0',
                            'left: 0',
                            'width: 2px',
                            'background-color: rgba(102, 102, 102, 0.8)',
                            'pointer-events: none',
                            'display: none',
                            'z-index: 9999',
                            'transition: none'
                        ].join(';') + ';';
                        
                        // 动态设置竖线高度
                        const updateLineHeight = function() {{
                            // 使用图表的实际渲染高度
                            const height = chartDom.offsetHeight || chartContainer.offsetHeight || 800;
                            customLine.style.height = height + 'px';
                            console.log('Indicator line height updated:', height);
                        }};
                        
                        // 确保容器是相对定位
                        const containerPosition = window.getComputedStyle(chartContainer).position;
                        if (containerPosition === 'static') {{
                            chartContainer.style.position = 'relative';
                        }}
                        
                        // 添加竖线到容器
                        chartContainer.appendChild(customLine);
                        console.log('Custom indicator line created for instance', INSTANCE_ID);
                        
                        // 初始设置高度（延迟执行确保DOM完全渲染）
                        setTimeout(updateLineHeight, 100);
                        
                        // 监听窗口大小变化和图表更新
                        window.addEventListener('resize', updateLineHeight);
                        el.chart.on('finished', updateLineHeight);
                        
                        // 鼠标移动事件 - 显示竖线
                        const mouseMoveHandler = function(e) {{
                            const rect = chartContainer.getBoundingClientRect();
                            const x = e.clientX - rect.left;
                            
                            // 确保竖线在容器范围内
                            if (x >= 0 && x <= rect.width) {{
                                customLine.style.left = x + 'px';
                                customLine.style.display = 'block';
                            }}
                        }};
                        
                        // 鼠标离开事件 - 隐藏竖线
                        const mouseLeaveHandler = function() {{
                            customLine.style.display = 'none';
                        }};
                        
                        // 绑定事件（同时绑定到图表和容器）
                        chartContainer.addEventListener('mousemove', mouseMoveHandler);
                        chartDom.addEventListener('mousemove', mouseMoveHandler);
                        chartContainer.addEventListener('mouseleave', mouseLeaveHandler);
                        chartDom.addEventListener('mouseleave', mouseLeaveHandler);
                    }}
                    
                    // 监听图表更新事件，确保formatter、axisPointer和x轴formatter不被覆盖
                    el.chart.on('finished', function() {{
                        const opt = el.chart.getOption();
                        // 保存当前option，供tooltip使用
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
                            axisPointer: {{
                                link: [{{xAxisIndex: 'all'}}]
                            }},
                            tooltip: {{
                                formatter: window.chartInstances[INSTANCE_ID].tooltipFormatter
                            }}
                        }}, false);
                    }});
                    
                    // 标记为已初始化
                    window.chartInstances[INSTANCE_ID]._initialized = true;
                    console.log('Chart instance', INSTANCE_ID, 'tooltip initialized successfully');
                    clearInterval(interval);
                }} else if (attempts++ >= maxAttempts) {{
                    console.error('Failed to initialize chart instance', INSTANCE_ID, 'after', maxAttempts, 'attempts');
                    clearInterval(interval);
                }}
            }}, 100);
        }}
        
        // 将 setupTooltip 函数注册到全局作用域，供外部调用
        window['setupTooltip_{instance_id}'] = setupTooltip;
        
        // 快速初始化：使用更激进的策略
        function initWhenVisible() {{
            let initialized = false;
            
            // 策略1: 立即尝试（适用于图表已经渲染的情况）
            const tryInit = () => {{
                if (initialized) return true;
                try {{
                    const el = typeof getElement === 'function' ? getElement(CHART_ID) : null;
                    if (el && el.chart) {{
                        console.log('Chart element ready for instance', INSTANCE_ID, ', initializing immediately');
                        initialized = true;
                        setupTooltip();
                        return true;
                    }}
                }} catch (e) {{}}
                return false;
            }};
            
            // 立即尝试
            if (tryInit()) return;
            
            // 策略2: 短暂等待后再试（适用于图表正在渲染）
            setTimeout(() => {{
                if (tryInit()) return;
                
                // 策略3: 使用更简单的轮询（不使用 IntersectionObserver）
                let quickRetries = 0;
                const quickInterval = setInterval(() => {{
                    if (tryInit() || quickRetries++ >= 10) {{  // 最多10次，共1秒
                        clearInterval(quickInterval);
                        if (!initialized) {{
                            // 最后的兜底：直接调用setupTooltip让它自己轮询
                            console.log('Quick init failed, falling back to setupTooltip polling');
                            setupTooltip();
                        }}
                    }}
                }}, 100);
            }}, 50);  // 延迟50ms后开始轮询
        }}
        
        // 确保DOM完全加载后再初始化
        if (document.readyState === 'loading') {{
            document.addEventListener('DOMContentLoaded', initWhenVisible);
        }} else {{
            initWhenVisible();
        }}
        }})();
        </script>
        ''')
    
    def update_enum_labels(self, signal_types: Dict[str, Dict[str, Any]]):
        """
        更新枚举标签映射
        
        Args:
            signal_types: 信号类型配置，格式如 {'signal_name': {'type': 'enum', 'enum_labels': {...}}}
        """
        enum_labels_json = {}
        # 使用 enumerate 按顺序为信号分配索引（从1开始），而不是从信号名中解析数字
        for signal_index, (signal_name, config) in enumerate(signal_types.items(), start=1):
            if config['type'] == 'enum':
                # signal_index 是显示编号（从1开始）
                # 使用这个编号作为键，与 tooltip 中的 Signal X 匹配
                # 将整数键转换为字符串键以便 JSON 序列化
                enum_labels_json[str(signal_index)] = {str(k): v for k, v in config['enum_labels'].items()}
        
        # 使用实例特定的命名空间
        enum_labels_js = json.dumps(enum_labels_json)
        
        update_script = f'''
            if (window.chartInstances && window.chartInstances[{self.instance_id}]) {{
                window.chartInstances[{self.instance_id}].updateEnumLabels({enum_labels_js});
            }}
        '''
        
        # 通过 run_javascript 执行，如果事件循环未准备好则延迟执行
        def execute_update():
            """执行更新脚本"""
            try:
                ui.run_javascript(update_script)
            except (AssertionError, RuntimeError) as e:
                # 如果事件循环未准备好，使用 add_body_html 作为备选方案
                # 注意：add_body_html 在初始化时可能返回协程，但会被 NiceGUI 自动处理
                import time
                timestamp = int(time.time() * 1000)
                script_id = f'enum-labels-{self.instance_id}-{timestamp}'
                try:
                    # 尝试使用 add_body_html（在初始化时可用）
                    result = ui.add_body_html(f'''
                    <script id="{script_id}">
                        {update_script}
                    </script>
                    ''')
                    # 如果返回协程，忽略它（NiceGUI 会在后台处理）
                    if hasattr(result, '__await__'):
                        pass  # 协程会被 NiceGUI 自动处理
                except Exception:
                    # 如果 add_body_html 也失败，使用 timer 延迟执行
                    ui.timer(0.1, lambda: ui.run_javascript(update_script), once=True)
        
        # 尝试立即执行，如果失败则延迟
        try:
            execute_update()
        except (AssertionError, RuntimeError):
            # 事件循环未准备好，延迟执行
            ui.timer(0.1, execute_update, once=True)
    
    def update_chart_option(self, new_option: Dict[str, Any], exclude_tooltip: bool = True):
        """
        更新图表配置
        
        Args:
            new_option: 新的ECharts配置选项
            exclude_tooltip: 是否排除tooltip配置（避免覆盖自定义formatter）
        """
        # 更新图表高度
        new_height = new_option.get('height', 1000)
        
        # 构建完整配置，排除tooltip和axisPointer
        update_config = {}
        for key, value in new_option.items():
            # 保留关键配置，避免覆盖
            if exclude_tooltip and key in ['tooltip', 'axisPointer']:
                continue  # 保留 JavaScript 中自定义的 tooltip formatter 和 axisPointer
            update_config[key] = value
        
        # 通过JavaScript完全替换配置（notMerge=true），然后恢复tooltip和axisPointer
        import json
        config_json = json.dumps(update_config)
        
        def execute_update():
            """执行图表更新"""
            try:
                ui.run_javascript(f'''
                const el = getElement({self.chart_element.id});
                if (el && el.chart) {{
                    const newConfig = {config_json};
                    console.log('=== Updating Chart Config ===');
                    console.log('New config has', newConfig.series ? newConfig.series.length : 0, 'series');
                    console.log('New config has', newConfig.grid ? newConfig.grid.length : 0, 'grids');
                    
                    // 第一步：完全替换配置（notMerge=true）
                    el.chart.setOption(newConfig, true, false);
                    console.log('Chart option replaced for instance {self.instance_id}');
                    
                    // 验证更新后的series数量
                    const option = el.chart.getOption();
                    console.log('After update, chart has', option.series ? option.series.length : 0, 'series');
                    
                    // 保存当前option，供tooltip使用
                    window.chartInstances[{self.instance_id}]._currentOption = option;
                    
                    // 第二步：恢复tooltip、axisPointer和x轴formatter配置
                    const xAxisConfig = [];
                    if (option.xAxis) {{
                        for (let i = 0; i < option.xAxis.length; i++) {{
                            xAxisConfig.push({{
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
                        xAxis: xAxisConfig,
                        axisPointer: {{
                            link: [{{xAxisIndex: 'all'}}],
                            label: {{
                                show: false
                            }},
                            lineStyle: {{
                                opacity: 0
                            }}
                        }},
                        tooltip: {{
                            show: true,
                            trigger: 'axis',
                            formatter: window.chartInstances[{self.instance_id}].tooltipFormatter,
                            axisPointer: {{
                                type: 'line',
                                label: {{
                                    show: false
                                }},
                                lineStyle: {{
                                    opacity: 0
                                }}
                            }},
                            confine: false,
                            appendToBody: true,
                            extraCssText: 'min-width: 280px; max-width: 600px;'
                        }}
                    }}, false, false);
                    console.log('Tooltip and axisPointer restored for instance {self.instance_id}');
                }}
            ''')
            except (AssertionError, RuntimeError) as e:
                # 事件循环未准备好，延迟执行
                ui.timer(0.1, execute_update, once=True)
                return
            except Exception as e:
                # 备用方案：直接更新options
                for key, value in update_config.items():
                    self.chart_element.options[key] = value
        
        # 尝试立即执行，如果失败则延迟
        try:
            execute_update()
        except (AssertionError, RuntimeError):
            # 事件循环未准备好，延迟执行
            ui.timer(0.1, execute_update, once=True)
        
        # 更新样式
        self.chart_element._props['style'] = f'height: {new_height}px; width: 100%; min-height: {new_height}px;'
        self.chart_element.update()
    
    def update_series_data(self, series_data: list):
        """
        更新系列数据
        
        Args:
            series_data: 系列数据列表，每个元素包含 data、showSymbol、symbolSize 等配置
        """
        # 使用JavaScript直接更新series数据，避免Python端options不同步的问题
        import json
        series_json = json.dumps(series_data)
        
        try:
            ui.run_javascript(f'''
                const el = getElement({self.chart_element.id});
                if (el && el.chart) {{
                    const seriesData = {series_json};
                    const option = el.chart.getOption();
                    
                    console.log('Updating series data:', seriesData.length, 'series');
                    console.log('Current option has', option.series ? option.series.length : 0, 'series');
                    
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
        except Exception as e:
            # 备用方案：直接更新options（可能不准确）
            for i, series_config in enumerate(series_data):
                if i < len(self.chart_element.options.get('series', [])):
                    self.chart_element.options['series'][i]['data'] = series_config['data']
                    self.chart_element.options['series'][i]['showSymbol'] = series_config['showSymbol']
                    self.chart_element.options['series'][i]['symbolSize'] = series_config['symbolSize']
            
            self.chart_element.update()
    
    def get_element(self):
        """获取图表元素（用于在UI布局中使用）"""
        return self.chart_element

