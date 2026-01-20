from typing import Dict, List, Callable, Any
from nicegui import ui

class SignalGroupManager:
    """信号分组管理控件"""
    
    def __init__(self, all_signals: Dict[str, Any], on_selection_change: Callable[[], None]):
        self.all_signals = all_signals  # {id: {label, type, ...}}
        self.on_selection_change = on_selection_change
        
        # 数据结构: 分组列表
        self.groups: List[Dict[str, Any]] = [
            {'name': '默认分组', 'signals': list(all_signals.keys()), 'expanded': True}
        ]
        
        # 记录每个信号的选中状态 (在分组树中使用)
        self.selection: Dict[str, bool] = {sig_id: False for sig_id in all_signals.keys()}
        self.search_query = ''
        
        # 全量列表页的选中状态 (用于批量添加)
        self.list_selection: Dict[str, bool] = {sig_id: False for sig_id in all_signals.keys()}
        self.all_list_query = ''
        
        # UI 组件引用
        self.sidebar_container = None
        self.main_list_container = None
        self.group_select_widget = None
        self.expansion_widgets = []

    def render_sidebar(self):
        """渲染侧边栏的分组管理视图"""
        self.sidebar_container = ui.column().classes('w-full gap-2 p-1')
        self._refresh_sidebar()
        return self.sidebar_container

    def render_main_list(self):
        """渲染主体区域的全量信号列表视图"""
        self.main_list_container = ui.column().classes('w-full h-full gap-4 p-4')
        self._refresh_main_list()
        return self.main_list_container

    def _refresh_sidebar(self):
        if not self.sidebar_container:
            return
        self.sidebar_container.clear()
        self.expansion_widgets.clear()
        
        with self.sidebar_container:
            # 顶部工具栏：添加分组和全展开/收缩放在左侧，搜索框放在右侧
            with ui.row().classes('w-full items-center gap-1 p-1'):
                with ui.row().classes('gap-0 no-wrap'):
                    ui.button(icon='add_circle', on_click=self._show_add_group_dialog).props('flat dense color=primary').tooltip('添加分组')
                    ui.button(icon='expand', on_click=self.expand_all).props('flat dense').tooltip('全展开')
                    ui.button(icon='compress', on_click=self.collapse_all).props('flat dense').tooltip('全收缩')
                
                ui.input(placeholder='搜索...', on_change=lambda e: self._set_search(e.value)) \
                    .classes('flex-grow').props('dense outlined clearable icon=search')

            # 分组列表容器
            self.groups_list_container = ui.column().classes('w-full gap-1 p-1')
            self._render_groups_list()

    def _refresh_main_list(self):
        if not self.main_list_container:
            return
        self.main_list_container.clear()
        
        with self.main_list_container:
            with ui.card().classes('w-full p-4 gap-4'):
                ui.label('📋 信号全量列表').classes('text-h6')
                
                # 搜索和批量操作
                with ui.row().classes('w-full items-center gap-4'):
                    ui.input(placeholder='在数千个信号中搜索...', on_change=lambda e: self._filter_all_list(e.value)) \
                        .classes('w-1/2').props('outlined clearable icon=search')
                    
                    with ui.row().classes('items-center gap-2 bg-blue-50 p-2 rounded flex-grow shadow-sm'):
                        ui.label('批量操作:').classes('font-bold text-blue-800')
                        self.group_select_widget = ui.select(
                            options={i: g['name'] for i, g in enumerate(self.groups)},
                            value=0
                        ).props('outlined options-dense').classes('min-w-[150px] bg-white')
                        
                        ui.button('添加到分组', icon='add_circle', on_click=lambda: self._add_selected_to_group(self.group_select_widget.value)) \
                            .props('elevated color=primary')
                        
                        ui.button('全选', icon='check_box', on_click=self._select_all_list).props('flat color=primary')
                        ui.button('清除', icon='check_box_outline_blank', on_click=self._deselect_all_list).props('flat color=primary')

                # 信号列表
                self.all_list_content = ui.column().classes('w-full gap-0 border rounded divide-y overflow-y-auto').style('max-height: 60vh;')
                self._render_all_list_content()

    def _render_all_list_content(self):
        if not hasattr(self, 'all_list_content'): return
        self.all_list_content.clear()
        
        with self.all_list_content:
            count = 0
            for sig_id, config in self.all_signals.items():
                if self.all_list_query and self.all_list_query not in sig_id.lower() and \
                   self.all_list_query not in config['label'].lower():
                    continue
                
                count += 1
                with ui.row().classes('w-full items-center hover:bg-gray-50 py-2 px-4 flex-nowrap gap-4 transition-colors'):
                    ui.checkbox(value=self.list_selection.get(sig_id, False), 
                               on_change=lambda e, sid=sig_id: self.list_selection.update({sid: e.value})) \
                        .props('dense')
                    
                    with ui.column().classes('gap-0 flex-grow'):
                        ui.label(config['label']).classes('text-sm font-bold truncate')
                        ui.label(sig_id).classes('text-xs text-gray-500 font-mono')
                    
                    # 显示所属分组
                    belonging_groups = [g['name'] for g in self.groups if sig_id in g['signals']]
                    if belonging_groups:
                        with ui.row().classes('gap-1'):
                            for gn in belonging_groups[:2]:
                                ui.badge(gn, color='blue-100').classes('text-blue-800 text-[10px]')
                            if len(belonging_groups) > 2:
                                ui.badge(f'+{len(belonging_groups)-2}', color='gray-100').classes('text-gray-600 text-[10px]')
            
            if count == 0:
                ui.label('未找到匹配的信号').classes('w-full text-center py-8 text-gray-400 italic')

    def _filter_all_list(self, query):
        self.all_list_query = query.lower() if query else ''
        self._render_all_list_content()

    def _select_all_list(self):
        for sid in self.list_selection: self.list_selection[sid] = True
        self._render_all_list_content()

    def _deselect_all_list(self):
        for sid in self.list_selection: self.list_selection[sid] = False
        self._render_all_list_content()

    def _add_selected_to_group(self, group_idx):
        target_group = self.groups[group_idx]
        added_count = 0
        for sig_id, selected in self.list_selection.items():
            if selected:
                if sig_id not in target_group['signals']:
                    target_group['signals'].append(sig_id)
                    added_count += 1
                self.list_selection[sig_id] = False # 添加后自动取消选中
        
        if added_count > 0:
            ui.notify(f'成功添加 {added_count} 个信号到 {target_group["name"]}', type='positive')
            self._render_groups_list() # 更新侧边栏
            self._render_all_list_content() # 更新主列表状态（显示新标签）
        else:
            ui.notify('未选择任何信号或信号已在组中', type='warning')

    def _set_search(self, query: str):
        self.search_query = query.lower() if query else ''
        self._render_groups_list()

    def _render_groups_list(self):
        if not hasattr(self, 'groups_list_container'): return
        self.groups_list_container.clear()
        self.expansion_widgets.clear()
        
        with self.groups_list_container:
            for idx, group in enumerate(self.groups):
                filtered_signals = [
                    sig_id for sig_id in group['signals']
                    if self.search_query in sig_id.lower() or 
                       self.search_query in self.all_signals[sig_id]['label'].lower()
                ]
                
                if self.search_query and not filtered_signals and self.search_query not in group['name'].lower():
                    continue

                with ui.expansion(value=group.get('expanded', True)) \
                    .classes('w-full border rounded') as exp:
                    exp.on_value_change(lambda e, g=group: g.update({'expanded': e.value}))
                    self.expansion_widgets.append(exp)
                    group['widget'] = exp
                    
                    with exp.add_slot('header'):
                        with ui.row().classes('items-center w-full gap-2 no-wrap'):
                            ui.icon('folder').classes('text-gray-500')
                            ui.label(group['name']).classes('font-bold flex-grow cursor-pointer truncate') \
                                .on('dblclick', lambda g=group: self._show_rename_group_dialog(g))
                            
                            with ui.row().classes('items-center gap-0 no-wrap'):
                                ui.button(icon='done_all', on_click=lambda g=group: self._toggle_group_selection(g)) \
                                    .props('flat dense size=sm color=gray').tooltip('组内全选/取消')
                                ui.button(icon='edit', on_click=lambda g=group: self._show_rename_group_dialog(g)) \
                                    .props('flat dense size=sm color=gray').tooltip('重命名')
                                ui.button(icon='arrow_upward', on_click=lambda g_idx=idx: self._move_group(g_idx, -1)) \
                                    .props('flat dense size=sm').classes('text-gray-400')
                                ui.button(icon='arrow_downward', on_click=lambda g_idx=idx: self._move_group(g_idx, 1)) \
                                    .props('flat dense size=sm').classes('text-gray-400')
                                ui.button(icon='add', on_click=lambda g=group: self._show_add_signal_dialog(g)) \
                                    .props('flat dense size=sm color=primary').tooltip('添加信号')
                                ui.button(icon='delete', on_click=lambda g=group: self._delete_group(g)) \
                                    .props('flat dense size=sm color=negative').tooltip('删除分组')
                    
                    with ui.column().classes('w-full pl-2 pr-1 pb-1 gap-0'):
                        if not filtered_signals:
                            ui.label('无信号').classes('text-gray-400 text-xs italic p-1')
                        else:
                            for sig_id in filtered_signals:
                                real_idx = group['signals'].index(sig_id)
                                self._render_signal_item(group, sig_id, real_idx, len(group['signals']))

    def _render_signal_item(self, group, sig_id, s_idx, total_count):
        config = self.all_signals[sig_id]
        label = config['label']
        with ui.row().classes('w-full items-center hover:bg-blue-50 py-0.5 px-1 rounded group flex-nowrap gap-1'):
            ui.checkbox(value=self.selection[sig_id], 
                       on_change=lambda e, sid=sig_id: self._on_sig_toggle(sid, e.value)) \
                .props('dense').classes('scale-90 m-0 p-0')
            with ui.column().classes('gap-0 flex-grow overflow-hidden'):
                ui.label(label).classes('text-xs font-medium leading-tight truncate w-full').tooltip(label)
                ui.label(sig_id).classes('text-[10px] text-gray-400 leading-tight truncate w-full')
            with ui.row().classes('flex-shrink-0 ml-auto gap-0 opacity-0 group-hover:opacity-100 transition-opacity flex-nowrap items-center'):
                ui.button(icon='arrow_upward', on_click=lambda: self._move_signal(group, s_idx, -1)) \
                    .props('flat dense size=xs').classes('text-gray-400 p-0 w-6')
                ui.button(icon='arrow_downward', on_click=lambda: self._move_signal(group, s_idx, 1)) \
                    .props('flat dense size=xs').classes('text-gray-400 p-0 w-6')
                ui.button(icon='close', on_click=lambda: self._remove_signal_from_group(group, sig_id)) \
                    .props('flat dense size=xs color=negative').classes('p-0 w-6').tooltip('从组中移除')

    def _on_sig_toggle(self, sig_id, value):
        self.selection[sig_id] = value
        self.on_selection_change()

    def _toggle_group_selection(self, group):
        if not group['signals']: return
        all_selected = all(self.selection[sig_id] for sig_id in group['signals'])
        new_state = not all_selected
        for sig_id in group['signals']: self.selection[sig_id] = new_state
        self._render_groups_list()
        self.on_selection_change()

    def _show_rename_group_dialog(self, group):
        with ui.dialog() as dialog, ui.card():
            ui.label('重命名分组').classes('text-h6')
            name_input = ui.input('新名称', value=group['name']).classes('w-full')
            with ui.row().classes('w-full justify-end'):
                ui.button('取消', on_click=dialog.close).props('flat')
                ui.button('确定', on_click=lambda: self._rename_group(group, name_input.value, dialog))
        dialog.open()

    def _rename_group(self, group, new_name, dialog):
        if not new_name: return
        group['name'] = new_name
        dialog.close()
        self._sync_all_views()

    def _sync_all_views(self):
        """同步所有视图的 UI"""
        if self.group_select_widget:
            self.group_select_widget.options = {i: g['name'] for i, g in enumerate(self.groups)}
            self.group_select_widget.update()
        self._render_groups_list()
        self._render_all_list_content()

    def expand_all(self):
        for exp in self.expansion_widgets: exp.value = True
        for group in self.groups: group['expanded'] = True

    def collapse_all(self):
        for exp in self.expansion_widgets: exp.value = False
        for group in self.groups: group['expanded'] = False

    def _show_add_group_dialog(self):
        with ui.dialog() as dialog, ui.card():
            ui.label('添加新分组').classes('text-h6')
            name_input = ui.input('分组名称').classes('w-full')
            with ui.row().classes('w-full justify-end'):
                ui.button('取消', on_click=dialog.close).props('flat')
                ui.button('确定', on_click=lambda: self._add_group(name_input.value, dialog))
        dialog.open()

    def _add_group(self, name, dialog):
        if not name: return
        self.groups.append({'name': name, 'signals': [], 'expanded': True})
        dialog.close()
        self._sync_all_views()

    def _delete_group(self, group):
        if len(self.groups) <= 1: return
        target_group = self.groups[1] if group == self.groups[0] else self.groups[0]
        for sig_id in group['signals']:
            if not any(sig_id in g['signals'] for g in self.groups if g != group):
                target_group['signals'].append(sig_id)
        self.groups.remove(group)
        self._sync_all_views()

    def _show_add_signal_dialog(self, group):
        available_signals = {sid: cfg['label'] for sid, cfg in self.all_signals.items() if sid not in group['signals']}
        if not available_signals: return
        with ui.dialog() as dialog, ui.card().style('width: 400px; max-height: 80vh;'):
            ui.label(f'添加信号到: {group["name"]}').classes('text-h6')
            search = ui.input('过滤信号...').classes('w-full').props('dense outlined icon=search')
            scroll = ui.scroll_area().classes('w-full h-64 border rounded p-2')
            with scroll:
                checks = {}
                def update_list(q=''):
                    scroll.clear()
                    with scroll:
                        for sid, label in available_signals.items():
                            if not q or q.lower() in sid.lower() or q.lower() in label.lower():
                                with ui.row().classes('items-center w-full'):
                                    checks[sid] = ui.checkbox(f"{label} ({sid})").props('dense')
                update_list(); search.on_value_change(lambda e: update_list(e.value))
            with ui.row().classes('w-full justify-end mt-4'):
                ui.button('取消', on_click=dialog.close).props('flat')
                ui.button('确定', on_click=lambda: self._add_signals_to_group(group, checks, dialog))
        dialog.open()

    def _add_signals_to_group(self, group, checks, dialog):
        added = False
        for sid, cb in checks.items():
            if cb.value and sid not in group['signals']:
                group['signals'].append(sid); added = True
        if added: dialog.close(); self._sync_all_views()

    def _remove_signal_from_group(self, group, sig_id):
        group['signals'].remove(sig_id)
        if not any(sig_id in g['signals'] for g in self.groups if g != group) and self.groups[0] != group:
            self.groups[0]['signals'].append(sig_id)
        self._sync_all_views()

    def _move_group(self, idx, direction):
        new_idx = idx + direction
        if 0 <= new_idx < len(self.groups):
            self.groups[idx], self.groups[new_idx] = self.groups[new_idx], self.groups[idx]
            self._sync_all_views()

    def _move_signal(self, group, s_idx, direction):
        signals = group['signals']
        new_idx = s_idx + direction
        if 0 <= new_idx < len(signals):
            signals[s_idx], signals[new_idx] = signals[new_idx], signals[s_idx]
            self._sync_all_views()

    def get_selected_signals(self) -> List[str]:
        return [sid for sid, selected in self.selection.items() if selected]

    def set_selected_signals(self, signal_ids: List[str]):
        for sid in self.selection: self.selection[sid] = sid in signal_ids
        self._render_groups_list()

    def set_enabled(self, enabled: bool):
        for container in [self.sidebar_container, self.main_list_container]:
            if container:
                if enabled: container.classes(remove='pointer-events-none opacity-50')
                else: container.classes('pointer-events-none opacity-50')
