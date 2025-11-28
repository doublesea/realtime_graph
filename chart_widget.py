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
                            
                            // 根据可见范围内的数据点数量动态调整点标记显示
                            function updateSymbolVisibility() {{
                                const opt = el.chart.getOption();
                                if (!opt.series || !opt.dataZoom || opt.dataZoom.length === 0) return;
                                
                                // 找到 inside 类型的 dataZoom（主要的缩放控制器）
                                let dataZoom = null;
                                for (let i = 0; i < opt.dataZoom.length; i++) {{
                                    if (opt.dataZoom[i].type === 'inside') {{
                                        dataZoom = opt.dataZoom[i];
                                        break;
                                    }}
                                }}
                                // 如果没找到 inside 类型，使用第一个
                                if (!dataZoom) {{
                                    dataZoom = opt.dataZoom[0];
                                }}
                                
                                const startPercent = dataZoom.start !== undefined ? dataZoom.start : 0;
                                const endPercent = dataZoom.end !== undefined ? dataZoom.end : 100;
                                
                                let needUpdate = false;
                                const seriesUpdate = [];
                                
                                for (let i = 0; i < opt.series.length; i++) {{
                                    if (!opt.series[i].data || opt.series[i].data.length === 0) {{
                                        seriesUpdate.push(null);
                                        continue;
                                    }}
                                    
                                    const totalPoints = opt.series[i].data.length;
                                    // 计算可见范围内的数据点数量
                                    const visibleStartIndex = Math.floor(totalPoints * startPercent / 100);
                                    const visibleEndIndex = Math.ceil(totalPoints * endPercent / 100);
                                    const visiblePointCount = visibleEndIndex - visibleStartIndex;
                                    
                                    // 根据可见数据点密度决定是否显示点标记
                                    let showSymbol = opt.series[i].showSymbol;
                                    let symbolSize = opt.series[i].symbolSize || 6;
                                    
                                    if (visiblePointCount > 150) {{
                                        // 密集：不显示点
                                        if (showSymbol !== false) {{
                                            showSymbol = false;
                                            symbolSize = 4;
                                            needUpdate = true;
                                        }}
                                    }} else if (visiblePointCount > 50) {{
                                        // 中等：显示小点
                                        if (showSymbol !== true || symbolSize !== 4) {{
                                            showSymbol = true;
                                            symbolSize = 4;
                                            needUpdate = true;
                                        }}
                                    }} else {{
                                        // 稀疏：显示正常大小的点
                                        if (showSymbol !== true || symbolSize !== 6) {{
                                            showSymbol = true;
                                            symbolSize = 6;
                                            needUpdate = true;
                                        }}
                                    }}
                                    
                                    seriesUpdate.push({{
                                        showSymbol: showSymbol,
                                        symbolSize: symbolSize
                                    }});
                                }}
                                
                                if (needUpdate) {{
                                    const seriesConfig = [];
                                    for (let i = 0; i < seriesUpdate.length; i++) {{
                                        if (seriesUpdate[i]) {{
                                            seriesConfig.push({{
                                                showSymbol: seriesUpdate[i].showSymbol,
                                                symbolSize: seriesUpdate[i].symbolSize
                                            }});
                                        }} else {{
                                            seriesConfig.push({{}});
                                        }}
                                    }}
                                    el.chart.setOption({{
                                        series: seriesConfig
                                    }}, false, false);
                                }}
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
                                
                                // 根据可见范围调整点标记显示
                                updateSymbolVisibility();
                            }});
                            
                            // 监听 dataZoom 事件，当用户缩放时动态调整点标记
                            el.chart.on('dataZoom', function() {{
                                updateSymbolVisibility();
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
                        
                        // 根据可见范围调整点标记显示
                        updateSymbolVisibility();
                    }});
                    
                    // 根据可见范围内的数据点数量动态调整点标记显示
                    function updateSymbolVisibility() {{
                        const opt = el.chart.getOption();
                        if (!opt.series || !opt.dataZoom || opt.dataZoom.length === 0) return;
                        
                        // 找到 inside 类型的 dataZoom（主要的缩放控制器）
                        let dataZoom = null;
                        for (let i = 0; i < opt.dataZoom.length; i++) {{
                            if (opt.dataZoom[i].type === 'inside') {{
                                dataZoom = opt.dataZoom[i];
                                break;
                            }}
                        }}
                        // 如果没找到 inside 类型，使用第一个
                        if (!dataZoom) {{
                            dataZoom = opt.dataZoom[0];
                        }}
                        
                        const startPercent = dataZoom.start !== undefined ? dataZoom.start : 0;
                        const endPercent = dataZoom.end !== undefined ? dataZoom.end : 100;
                        
                        let needUpdate = false;
                        const seriesUpdate = [];
                        
                        for (let i = 0; i < opt.series.length; i++) {{
                            if (!opt.series[i].data || opt.series[i].data.length === 0) {{
                                seriesUpdate.push(null);
                                continue;
                            }}
                            
                            const totalPoints = opt.series[i].data.length;
                            // 计算可见范围内的数据点数量
                            const visibleStartIndex = Math.floor(totalPoints * startPercent / 100);
                            const visibleEndIndex = Math.ceil(totalPoints * endPercent / 100);
                            const visiblePointCount = visibleEndIndex - visibleStartIndex;
                            
                            // 根据可见数据点密度决定是否显示点标记
                            let showSymbol = opt.series[i].showSymbol;
                            let symbolSize = opt.series[i].symbolSize || 6;
                            
                            if (visiblePointCount > 150) {{
                                // 密集：不显示点
                                if (showSymbol !== false) {{
                                    showSymbol = false;
                                    symbolSize = 4;
                                    needUpdate = true;
                                }}
                            }} else if (visiblePointCount > 50) {{
                                // 中等：显示小点
                                if (showSymbol !== true || symbolSize !== 4) {{
                                    showSymbol = true;
                                    symbolSize = 4;
                                    needUpdate = true;
                                }}
                            }} else {{
                                // 稀疏：显示正常大小的点
                                if (showSymbol !== true || symbolSize !== 6) {{
                                    showSymbol = true;
                                    symbolSize = 6;
                                    needUpdate = true;
                                }}
                            }}
                            
                            seriesUpdate.push({{
                                showSymbol: showSymbol,
                                symbolSize: symbolSize
                            }});
                        }}
                        
                        if (needUpdate) {{
                            const seriesConfig = [];
                            for (let i = 0; i < seriesUpdate.length; i++) {{
                                if (seriesUpdate[i]) {{
                                    seriesConfig.push({{
                                        showSymbol: seriesUpdate[i].showSymbol,
                                        symbolSize: seriesUpdate[i].symbolSize
                                    }});
                                }} else {{
                                    seriesConfig.push({{}});
                                }}
                            }}
                            el.chart.setOption({{
                                series: seriesConfig
                            }}, false, false);
                        }}
                    }}
                    
                    // 监听 dataZoom 事件，当用户缩放时动态调整点标记
                    el.chart.on('dataZoom', function() {{
                        updateSymbolVisibility();
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
    
    def update_enum_labels(self, signal_types: Dict[str, Dict[str, Any]], realtime_plot=None):
        """
        更新枚举标签映射
        
        Args:
            signal_types: 信号类型配置，格式如 {'signal_name': {'type': 'enum', 'enum_labels': {...}}}
            realtime_plot: 可选的 RealtimePlot 实例，如果提供则自动更新引用
        """
        # 如果提供了 realtime_plot，自动更新引用
        if realtime_plot is not None:
            self.set_realtime_plot(realtime_plot)
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
        
        # 自动更新侧边栏：更新信号名称列表（从传入的 signal_types 获取）
        signal_names_list = list(signal_types.keys())
        # 更新信号名称列表（即使 realtime_plot 还没有设置，也先保存信号名称）
        self._signal_names_list = signal_names_list
        
        # 如果 realtime_plot 已设置且侧边栏已创建，自动更新 UI
        if self.realtime_plot and hasattr(self, 'subplot_order_container'):
            # 检查 realtime_plot 的 signal_types 是否与传入的匹配
            if hasattr(self.realtime_plot, 'signal_types') and self.realtime_plot.signal_types == signal_types:
                # 清除之前保存的信号名称列表，让 update_subplot_order_ui 自动从 realtime_plot 获取
                if hasattr(self, '_signal_names_list'):
                    delattr(self, '_signal_names_list')
                # 自动更新 UI
                self.update_subplot_order_ui()
            elif not hasattr(self.realtime_plot, 'signal_types') or not self.realtime_plot.signal_types:
                # 如果 realtime_plot 的 signal_types 为空，使用传入的 signal_types 更新
                # 注意：这里不能直接修改 realtime_plot.signal_types，因为它是只读的
                # 但我们可以使用已保存的 signal_names_list
                self.update_subplot_order_ui()
        elif hasattr(self, 'subplot_order_container'):
            # 即使没有 realtime_plot，也更新 UI（使用已保存的 signal_names_list）
            self.update_subplot_order_ui()
    
    def update_chart_option(self, new_option: Dict[str, Any], exclude_tooltip: bool = True, realtime_plot=None):
        """
        更新图表配置
        
        Args:
            new_option: 新的ECharts配置选项
            exclude_tooltip: 是否排除tooltip配置（避免覆盖自定义formatter）
            realtime_plot: 可选的 RealtimePlot 实例，如果提供则自动更新引用
        """
        # 如果提供了 realtime_plot，自动更新引用
        if realtime_plot is not None:
            self.set_realtime_plot(realtime_plot)
        # 如果 realtime_plot 未设置，但检测到 option 中有 series，尝试从 option 推断
        # 注意：这只能用于显示，无法真正移动子图，因为需要 realtime_plot 的完整功能
        elif self.realtime_plot is None and new_option.get('series'):
            # 从 option 中推断信号数量，但无法真正设置 realtime_plot
            # 这里只能记录，实际的移动操作需要 realtime_plot
            pass
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
    
    def _setup_sidebar(self):
        """设置子图顺序调节侧边栏（通过右键菜单唤出）"""
        # 使用 NiceGUI 组件创建固定定位的侧边栏
        # 注意：虽然嵌套在 Card 中，但 position: fixed 会使其相对于视口定位
        
        # 1. 创建遮罩层
        with ui.element('div').style(
            'position: fixed; top: 0; left: 0; width: 100%; height: 100%; '
            'background: rgba(0,0,0,0.3); z-index: 9998; display: none;'
        ) as self.sidebar_overlay:
            self.sidebar_overlay.on('click', self.hide_sidebar)
            
        # 2. 创建侧边栏容器
        with ui.card().classes('bg-white').style(
            'position: fixed; right: -320px; left: auto; top: 0; width: 300px; height: 100vh; '
            'z-index: 9999; transition: right 0.3s ease; overflow-y: auto; '
            'box-shadow: -1px 0 4px rgba(0,0,0,0.1); border-left: 1px solid #e5e5e5; padding: 0;'
        ) as self.sidebar_card:
            
            # 标题栏
            with ui.row().classes('items-center justify-between p-3 border-b border-gray-100 w-full'):
                ui.label('子图顺序').classes('text-body1').style('color: #666; font-weight: 500;')
                ui.button(icon='close', on_click=self.hide_sidebar).props('flat dense round color=grey').classes('text-gray-400')
            
            # 内容容器
            with ui.column().classes('w-full p-3') as self.subplot_order_container:
                pass
        
        # 为图表元素添加右键菜单
        self._setup_context_menu()
    
    def _setup_context_menu(self):
        """设置右键菜单"""
        chart_id = self.chart_element.id
        instance_id = self.instance_id
        
        # 创建一个隐藏的按钮，用于从 JS 触发侧边栏显示
        with ui.row().style('display: none;'):
            trigger_btn = ui.button('Show Sidebar', on_click=self.show_sidebar)
            trigger_btn_id = trigger_btn.id
        
        # 添加右键菜单的JavaScript（使用 add_body_html 避免事件循环问题）
        ui.add_body_html(f'''
        <script>
        (function() {{
            const chartId = {chart_id};
            const instanceId = '{instance_id}';
            const triggerBtnId = 'c{trigger_btn_id}'; // NiceGUI 元素 ID 前缀通常是 'c'
            let menuVisible = false;
            
            // 创建右键菜单
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
            
            // 菜单项悬停效果
            menu.querySelectorAll('.menu-item').forEach(item => {{
                item.addEventListener('mouseenter', function() {{
                    this.style.backgroundColor = '#f0f0f0';
                }});
                item.addEventListener('mouseleave', function() {{
                    this.style.backgroundColor = 'transparent';
                }});
            }});
            
            function showMenu(e) {{
                e.preventDefault();
                e.stopPropagation();
                menu.style.display = 'block';
                menu.style.left = e.pageX + 'px';
                menu.style.top = e.pageY + 'px';
                menuVisible = true;
            }}
            
            function hideMenu() {{
                menu.style.display = 'none';
                menuVisible = false;
            }}
            
            // 获取图表容器
            function getChartContainer() {{
                try {{
                    const el = typeof getElement === 'function' ? getElement(chartId) : null;
                    if (el && el.chart) {{
                        return el.chart.getDom();
                    }}
                }} catch (e) {{
                    console.warn('Failed to get chart element:', e);
                }}
                // 备用方案：查找所有 .echarts 元素
                const elements = document.querySelectorAll('.echarts');
                for (let elem of elements) {{
                    if (elem.__nicegui_chart) {{
                        return elem;
                    }}
                }}
                return null;
            }}
            
            // 延迟绑定事件，确保图表已渲染
            function setupContextMenu() {{
                const chartContainer = getChartContainer();
                if (chartContainer) {{
                    // 移除旧的事件监听器（如果存在）
                    const oldHandler = chartContainer._contextMenuHandler;
                    if (oldHandler) {{
                        chartContainer.removeEventListener('contextmenu', oldHandler);
                    }}
                    
                    // 添加新的事件监听器
                    chartContainer.addEventListener('contextmenu', showMenu);
                    chartContainer._contextMenuHandler = showMenu;
                    
                    // 全局点击事件（只添加一次）
                    if (!window._contextMenuClickHandler) {{
                        window._contextMenuClickHandler = hideMenu;
                        document.addEventListener('click', hideMenu);
                    }}
                    
                    // 全局右键事件（只添加一次）
                    if (!window._contextMenuContextHandler) {{
                        window._contextMenuContextHandler = function(e) {{
                            const chartContainer = getChartContainer();
                            if (chartContainer && e.target !== chartContainer && !chartContainer.contains(e.target)) {{
                                hideMenu();
                            }}
                        }};
                        document.addEventListener('contextmenu', window._contextMenuContextHandler);
                    }}
                    
                    console.log('Context menu setup for chart', chartId, 'instance', instanceId);
                    return true;
                }}
                return false;
            }}
            
            // 将 setupContextMenu 函数暴露到全局，供延迟初始化调用
            window.setupContextMenuForInstance = window.setupContextMenuForInstance || {{}};
            window.setupContextMenuForInstance[instanceId] = setupContextMenu;
            
            // 尝试立即设置
            if (!setupContextMenu()) {{
                // 如果失败，延迟重试（增加重试次数和延迟时间）
                let attempts = 0;
                const maxAttempts = 50; // 增加到50次（5秒）
                const interval = setInterval(function() {{
                    if (setupContextMenu()) {{
                        clearInterval(interval);
                        console.log('Context menu setup succeeded after', attempts + 1, 'attempts');
                    }} else if (attempts++ >= maxAttempts) {{
                        clearInterval(interval);
                        console.warn('Context menu setup failed after', maxAttempts, 'attempts');
                    }}
                }}, 100);
            }}
            
            // 菜单项点击事件
            menu.addEventListener('click', function(e) {{
                const action = e.target.closest('.menu-item')?.dataset.action;
                if (action === 'show-sidebar') {{
                    hideMenu();
                    // 模拟点击隐藏按钮，触发 Python 回调
                    // 尝试多种方式找到按钮
                    let btn = document.getElementById(triggerBtnId);
                    if (!btn) {{
                        // 尝试不带前缀 'c'
                        btn = document.getElementById('{trigger_btn_id}');
                    }}
                    
                    if (btn) {{
                        btn.click();
                        // 对于 NiceGUI，有时需要触发特定的事件
                        btn.dispatchEvent(new MouseEvent('click', {{
                            view: window,
                            bubbles: true,
                            cancelable: true
                        }}));
                    }} else {{
                        console.error('Trigger button not found:', triggerBtnId);
                    }}
                }}
            }});
        }})();
        </script>
        ''')
    
    def show_sidebar(self):
        """显示侧边栏"""
        # 尝试刷新 UI，确保内容是最新的
        self.update_subplot_order_ui()
        
        if hasattr(self, 'sidebar_card') and self.sidebar_card:
            self.sidebar_card.style('right: 0px; left: auto;')
            if hasattr(self, 'sidebar_overlay'):
                self.sidebar_overlay.style('display: block;')
            self.sidebar_visible = True
    
    def hide_sidebar(self):
        """隐藏侧边栏"""
        if hasattr(self, 'sidebar_card') and self.sidebar_card:
            self.sidebar_card.style('right: -300px; left: auto;')
            if hasattr(self, 'sidebar_overlay'):
                self.sidebar_overlay.style('display: none;')
            self.sidebar_visible = False
    
    def update_subplot_order_ui(self, signal_names_list: list = None, chart_widget_ref=None, is_running_ref=None):
        """
        更新子图顺序控制UI
        
        Args:
            signal_names_list: 信号名称列表 (可选，如果不传则使用保存的或从 realtime_plot 自动获取)
            chart_widget_ref: chart_widget 的引用 (可选，如果不传则使用 self)
            is_running_ref: is_running 的引用 (可选)
        """
        # 更新保存的引用
        if signal_names_list is not None:
            self._signal_names_list = signal_names_list
        if chart_widget_ref is not None:
            self._chart_widget_ref = chart_widget_ref
        if is_running_ref is not None:
            self._is_running_ref = is_running_ref
        
        # 如果没有提供 signal_names_list，尝试从 realtime_plot 自动获取
        if not hasattr(self, '_signal_names_list') or self._signal_names_list is None:
            if self.realtime_plot and hasattr(self.realtime_plot, 'signal_types') and self.realtime_plot.signal_types:
                # 从 signal_types 字典的键获取信号名称列表
                self._signal_names_list = list(self.realtime_plot.signal_types.keys())
            elif self.realtime_plot:
                # 如果 signal_types 为空，根据 num_signals 生成默认名称
                num_signals = getattr(self.realtime_plot, 'num_signals', 0)
                self._signal_names_list = [f'Signal {i+1}' for i in range(num_signals)]
            else:
                # 如果没有 realtime_plot，无法获取信号列表，返回
                return
        
        # 如果没有提供 chart_widget_ref，使用 self
        if not hasattr(self, '_chart_widget_ref') or self._chart_widget_ref is None:
            self._chart_widget_ref = self
            
        # 使用保存的引用
        signal_names_list = self._signal_names_list
        chart_widget_ref = self._chart_widget_ref
        is_running_ref = getattr(self, '_is_running_ref', None)
        
        # 确保侧边栏容器已创建
        if not hasattr(self, 'subplot_order_container'):
            self._setup_sidebar()
        
        # 获取子图顺序：如果有 realtime_plot 则使用它，否则使用内部维护的顺序
        if self.realtime_plot:
            current_order = self.realtime_plot.get_subplot_order()
        else:
            # 如果没有 realtime_plot，使用内部维护的顺序或默认顺序
            if self._internal_subplot_order is None or len(self._internal_subplot_order) != len(signal_names_list):
                # 初始化内部顺序
                self._internal_subplot_order = list(range(len(signal_names_list)))
            current_order = self._internal_subplot_order
        
        # 清空现有内容
        self.subplot_order_container.clear()
        
        with self.subplot_order_container:
            # 生成列表
            for display_pos, signal_idx in enumerate(current_order):
                signal_name = signal_names_list[signal_idx] if signal_idx < len(signal_names_list) else f'Signal {signal_idx+1}'
                
                is_first = (display_pos == 0)
                is_last = (display_pos == len(current_order) - 1)
                
                with ui.row().classes('w-full items-center py-2 px-1 border-b border-gray-100'):
                    # 序号
                    ui.label(str(display_pos + 1)).classes(
                        'text-gray-400 text-xs px-2 min-w-[24px] text-center'
                    )
                    
                    # 信号名称
                    ui.label(signal_name).classes('flex-1 text-sm text-gray-700 break-all px-2')
                    
                    # 按钮组
                    with ui.row().classes('gap-1'):
                        # 上移按钮
                        ui.button(icon='arrow_upward', on_click=lambda idx=signal_idx: self._execute_move(
                            idx, 'up', signal_names_list, chart_widget_ref, is_running_ref
                        )).props('flat dense size=sm').classes('text-gray-500').style(
                            'min-width: 28px; min-height: 28px;'
                        ).set_enabled(not is_first)
                        
                        # 下移按钮
                        ui.button(icon='arrow_downward', on_click=lambda idx=signal_idx: self._execute_move(
                            idx, 'down', signal_names_list, chart_widget_ref, is_running_ref
                        )).props('flat dense size=sm').classes('text-gray-500').style(
                            'min-width: 28px; min-height: 28px;'
                        ).set_enabled(not is_last)
    
    def _setup_move_handlers(self):
        """设置移动信号的处理"""
        # 由于已经改用 NiceGUI 组件直接绑定事件，这里只需要保留一个空的实现
        pass
    
    def _execute_move(self, signal_idx, direction, signal_names_list, chart_widget_ref, is_running_ref):
        """执行移动操作"""
        if self.realtime_plot:
            # 如果有 realtime_plot，使用它的方法
            if direction == 'up':
                self.realtime_plot.move_subplot_up(signal_idx)
            else:
                self.realtime_plot.move_subplot_down(signal_idx)
            
            # 更新图表配置
            new_option = self.realtime_plot.get_option()
            if chart_widget_ref:
                chart_widget_ref.update_chart_option(new_option, exclude_tooltip=True)
            
            # 如果正在运行，需要更新series数据
            if (is_running_ref and is_running_ref() and 
                self.realtime_plot._data_buffer is not None):
                series_data = [
                    {
                        'data': new_option['series'][i]['data'],
                        'showSymbol': new_option['series'][i]['showSymbol'],
                        'symbolSize': new_option['series'][i]['symbolSize']
                    }
                    for i in range(len(new_option['series']))
                ]
                if chart_widget_ref:
                    chart_widget_ref.update_series_data(series_data)
        else:
            # 如果没有 realtime_plot，使用内部维护的顺序，并通过 JavaScript 直接更新图表
            if self._internal_subplot_order is None:
                self._internal_subplot_order = list(range(len(signal_names_list)))
            
            # 执行移动操作
            current_order = self._internal_subplot_order
            try:
                pos = current_order.index(signal_idx)
                if direction == 'up' and pos > 0:
                    # 上移
                    current_order[pos], current_order[pos-1] = current_order[pos-1], current_order[pos]
                elif direction == 'down' and pos < len(current_order) - 1:
                    # 下移
                    current_order[pos], current_order[pos+1] = current_order[pos+1], current_order[pos]
            except ValueError:
                # signal_idx 不在 current_order 中，忽略
                return
            
            # 通过 JavaScript 直接更新图表配置：重新排序 series、grid、title 等
            import json
            order_json = json.dumps(current_order)
            
            def update_chart_order():
                """通过 JavaScript 重新排序图表配置"""
                try:
                    ui.run_javascript(f'''
                    const el = getElement({self.chart_element.id});
                    if (el && el.chart) {{
                        const newOrder = {order_json};
                        const option = el.chart.getOption();
                        
                        // 保存原始配置
                        const originalGrid = option.grid || [];
                        const originalTitle = option.title || [];
                        const originalSeries = option.series || [];
                        
                        // newOrder[i] 表示显示在第 i 位的原始索引
                        // 例如 newOrder = [2, 0, 1] 表示：
                        // - 原始索引 2 显示在第 0 位
                        // - 原始索引 0 显示在第 1 位
                        // - 原始索引 1 显示在第 2 位
                        
                        // 注意：originalTitle 数组是按显示位置排列的，不是按原始索引
                        // 所以 originalTitle[i] 对应显示在第 i 位的信号的 title
                        // 我们需要找到每个原始索引对应的 title
                        
                        // 首先，创建原始索引 -> 当前显示位置的映射（从当前 option 推断）
                        // 通过检查 grid 的 top 位置来推断当前的显示顺序
                        const currentOrder = [];
                        const gridTopPositions = [];
                        for (let i = 0; i < originalGrid.length; i++) {{
                            if (originalGrid[i]) {{
                                gridTopPositions.push({{index: i, top: originalGrid[i].top || 0}});
                            }}
                        }}
                        // 按 top 位置排序，得到当前的显示顺序
                        gridTopPositions.sort((a, b) => a.top - b.top);
                        for (let i = 0; i < gridTopPositions.length; i++) {{
                            currentOrder.push(gridTopPositions[i].index);
                        }}
                        
                        // 创建原始索引 -> title 的映射
                        const titleByOriginalIndex = {{}};
                        for (let displayPos = 0; displayPos < currentOrder.length && displayPos < originalTitle.length; displayPos++) {{
                            const originalIdx = currentOrder[displayPos];
                            titleByOriginalIndex[originalIdx] = originalTitle[displayPos];
                        }}
                        
                        // 从当前配置中推断实际的图表高度和间距
                        // realtime_plot.py 中的计算公式：top = chart_spacing + display_pos * (chart_height_per_signal + chart_spacing) + 30
                        let chartHeightPerSignal = 150; // 默认值
                        let chartSpacing = 2; // realtime_plot.py 中的默认值
                        const baseTopOffset = 30; // realtime_plot.py 中的基础偏移
                        
                        // 从 grid 的 height 属性获取每个子图的高度
                        if (gridTopPositions.length > 0 && originalGrid[gridTopPositions[0].index] && originalGrid[gridTopPositions[0].index].height) {{
                            chartHeightPerSignal = originalGrid[gridTopPositions[0].index].height;
                        }}
                        
                        // 如果有多个 grid，通过 top 差值计算间距
                        if (gridTopPositions.length >= 2) {{
                            const firstTop = gridTopPositions[0].top;
                            const secondTop = gridTopPositions[1].top;
                            // 间距 = (第二个 top - 第一个 top) - height
                            chartSpacing = secondTop - firstTop - chartHeightPerSignal;
                            // 确保间距合理
                            if (chartSpacing < 0 || chartSpacing > 50) {{
                                chartSpacing = 2; // 使用默认值
                            }}
                        }}
                        
                        // 确保高度值合理（防止计算错误）
                        if (chartHeightPerSignal < 50 || chartHeightPerSignal > 500) {{
                            chartHeightPerSignal = 150;
                        }}
                        
                        const reorderedGrid = [];
                        const reorderedTitle = [];
                        
                        // 创建原始索引 -> 新显示位置的映射
                        const indexToDisplayPos = {{}};
                        for (let displayPos = 0; displayPos < newOrder.length; displayPos++) {{
                            const originalIdx = newOrder[displayPos];
                            indexToDisplayPos[originalIdx] = displayPos;
                        }}
                        
                        // 计算顶部基础位置（从第一个 grid 的 top 推断，或使用默认值）
                        // 公式：top = chartSpacing + displayPos * (chartHeightPerSignal + chartSpacing) + baseTopOffset
                        // 对于 displayPos=0: top = chartSpacing + baseTopOffset
                        let baseTop = baseTopOffset;
                        if (gridTopPositions.length > 0) {{
                            // 从第一个 grid 的 top 反推 baseTop
                            // top = chartSpacing + 0 * (height + spacing) + baseTop
                            // 所以 baseTop = top - chartSpacing
                            baseTop = gridTopPositions[0].top - chartSpacing;
                            // 如果计算出的 baseTop 不合理，使用默认值
                            if (baseTop < 0 || baseTop > 100) {{
                                baseTop = baseTopOffset;
                            }}
                        }}
                        
                        // 更新 grid：按原始索引顺序，但 top 位置根据新显示位置计算
                        for (let originalIdx = 0; originalIdx < originalGrid.length; originalIdx++) {{
                            if (originalGrid[originalIdx]) {{
                                const displayPos = indexToDisplayPos[originalIdx] !== undefined ? indexToDisplayPos[originalIdx] : originalIdx;
                                const grid = {{...originalGrid[originalIdx]}};
                                // 使用与 realtime_plot.py 相同的公式
                                grid.top = chartSpacing + displayPos * (chartHeightPerSignal + chartSpacing) + baseTop;
                                
                                // Update background color for zebra pattern (consistent with RealtimePlot)
                                grid.backgroundColor = (displayPos % 2 === 1) ? '#fafafa' : '#f2f2f2';
                                grid.show = true;
                                grid.borderWidth = 0;
                                
                                reorderedGrid[originalIdx] = grid;
                            }}
                        }}
                        
                        // 重新排列 title：按新显示位置顺序，从 titleByOriginalIndex 获取
                        const titleOffset = 22; // title 在 grid 上方 22 像素（根据 chart_height_per_signal 调整）
                        const actualTitleOffset = chartHeightPerSignal >= 100 ? 22 : 18;
                        for (let displayPos = 0; displayPos < newOrder.length; displayPos++) {{
                            const originalIdx = newOrder[displayPos];
                            if (titleByOriginalIndex[originalIdx]) {{
                                const title = {{...titleByOriginalIndex[originalIdx]}};
                                // 使用与 realtime_plot.py 相同的公式
                                title.top = chartSpacing + displayPos * (chartHeightPerSignal + chartSpacing) + baseTop - actualTitleOffset;
                                reorderedTitle.push(title);
                            }}
                        }}
                        
                        // 重新计算图表总高度（使用与 realtime_plot.py 相同的公式）
                        // total_height = chart_height_per_signal * num_signals + chart_spacing * (num_signals + 1) + top_bottom_padding
                        const numSignals = newOrder.length;
                        const topBottomPadding = 80; // realtime_plot.py 中的默认值
                        const totalHeight = chartHeightPerSignal * numSignals + chartSpacing * (numSignals + 1) + topBottomPadding;
                        
                        // 更新图表配置（包括高度）
                        el.chart.setOption({{
                            height: totalHeight,
                            grid: reorderedGrid,
                            title: reorderedTitle
                        }}, false, false);
                        
                        // 更新图表容器的高度
                        const chartDom = el.chart.getDom();
                        if (chartDom && chartDom.parentElement) {{
                            chartDom.parentElement.style.height = totalHeight + 'px';
                            chartDom.style.height = totalHeight + 'px';
                        }}
                        
                        console.log('Chart order updated via JavaScript, new order:', newOrder);
                    }}
                    ''')
                except Exception as e:
                    print(f"Error updating chart order: {e}")
            
            # 尝试立即执行，如果失败则延迟
            try:
                update_chart_order()
            except (AssertionError, RuntimeError):
                ui.timer(0.1, update_chart_order, once=True)
        
        # 刷新UI
        self.update_subplot_order_ui(
            signal_names_list, 
            chart_widget_ref, 
            is_running_ref
        )
    
    def set_realtime_plot(self, realtime_plot):
        """设置 RealtimePlot 实例"""
        self.realtime_plot = realtime_plot
        # 自动更新侧边栏内容（如果侧边栏已创建）
        if hasattr(self, 'subplot_order_container'):
            # 清除之前保存的信号名称列表，让 update_subplot_order_ui 自动从 realtime_plot 获取
            if hasattr(self, '_signal_names_list'):
                delattr(self, '_signal_names_list')
            # 自动更新 UI
            self.update_subplot_order_ui()

