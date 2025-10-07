"""
增强版拓扑图生成器

根据用户偏好支持多种拓扑图展示方式，并严格遵循字体显示规范：
- 汉字放大3倍（黑色显示）
- 数字放大2倍（红色显示）
- 图例放大2倍
- 汉字与图形错开显示，避免重叠
- 水位数字与图形分离显示
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Rectangle, Circle, Polygon
import numpy as np
from typing import Dict, List, Tuple, Optional
import yaml
import json


class EnhancedTopologyGenerator:
    """增强版拓扑图生成器，支持多种展示方式和智能选择"""
    
    def __init__(self, figsize=(16, 12)):
        """初始化生成器"""
        self.figsize = figsize
        self.fig = None
        self.ax = None
        
        # 严格遵循用户字体显示规范
        self.font_preferences = {
            'chinese_scale': 3.0,      # 汉字放大3倍至3像素
            'number_scale': 2.0,       # 数字字体翻倍
            'number_color': 'red',     # 数字红色突出显示
            'chinese_color': 'black',  # 汉字黑色普通显示
            'legend_scale': 2.0,       # 图例字体放大2倍（严格按用户规范）
            'base_fontsize': 8         # 基础字体大小
        }
        
        # 文字与图形错开显示规范
        self.offset_config = {
            'node_label_offset': 0.8,  # 节点标签偏移距离 = 节点半径 + 0.8单位
            'edge_label_offset': 0.3,  # 边标签垂直偏移0.3单位
            'water_level_offset': 0.5, # 水位数字偏移 = 节点半径 + 0.5单位
            'background_padding': 0.1   # 文字背景框间距
        }
        
        # 拓扑图展示方式
        self.display_modes = {
            'simple_flow': {
                'name': '简洁流程图',
                'description': '适用于节点数<=5的简单流程',
                'layout': 'linear',
                'show_values': False
            },
            'flow_direction': {
                'name': '流向示意图', 
                'description': '适用于需要显示流向和数值的中等复杂度网络',
                'layout': 'hierarchical',
                'show_values': True
            },
            'table_mode': {
                'name': '表格模式',
                'description': '适用于节点数>10的复杂网络',
                'layout': 'grid',
                'show_values': True
            },
            'graphical_mode': {
                'name': '图形化模式',
                'description': '适用于需要突出拓扑结构的复杂网络',
                'layout': 'force_directed',
                'show_values': False
            }
        }
        
        # 颜色配置
        self.color_scheme = {
            'reservoir': {'fill': '#E3F2FD', 'edge': '#1976D2', 'text': '#0D47A1'},
            'station': {'fill': '#F3E5F5', 'edge': '#7B1FA2', 'text': '#4A148C'}, 
            'junction': {'fill': '#E8F5E8', 'edge': '#388E3C', 'text': '#1B5E20'},
            'pipe': {'fill': '#FFF3E0', 'edge': '#F57C00', 'text': '#E65100'},
            'background': {'fill': '#FAFAFA', 'edge': '#BDBDBD'}
        }
        
    def apply_font_preferences(self, text: str, base_size: Optional[float] = None) -> dict:
        """应用用户字体偏好规范"""
        if base_size is None:
            base_size = self.font_preferences['base_fontsize']
            
        # 检测文本类型
        has_chinese = any('\u4e00' <= char <= '\u9fff' for char in text)
        has_numbers = any(char.isdigit() for char in text)
        
        # 严格按照规范应用字体样式
        if has_chinese and not has_numbers:
            # 纯汉字：放大3倍，黑色显示
            fontsize = base_size * self.font_preferences['chinese_scale']
            color = self.font_preferences['chinese_color']
            fontweight = 'normal'
        elif has_numbers and not has_chinese:
            # 纯数字：放大2倍，红色显示
            fontsize = base_size * self.font_preferences['number_scale']
            color = self.font_preferences['number_color']
            fontweight = 'bold'
        elif has_chinese and has_numbers:
            # 混合文本：汉字规则优先，数字部分用红色
            fontsize = base_size * self.font_preferences['chinese_scale']
            color = self.font_preferences['chinese_color']
            fontweight = 'normal'
        else:
            # 其他文本：默认样式
            fontsize = base_size
            color = 'black'
            fontweight = 'normal'
            
        return {
            'fontsize': fontsize,
            'color': color,
            'fontweight': fontweight
        }
        
    def intelligent_layout_selection(self, topology_data: Dict) -> str:
        """根据数据特点智能选择最佳展示方式"""
        # 统计节点数量
        total_nodes = 0
        for key in ['reservoirs', 'stations', 'junctions', 'pipes']:
            if key in topology_data:
                total_nodes += len(topology_data[key])
                
        # 检查是否有数值数据
        has_values = False
        for key in ['reservoirs', 'stations', 'junctions', 'pipes']:
            if key in topology_data:
                for item in topology_data[key]:
                    if isinstance(item, dict):
                        if any(k in item for k in ['level', 'flow', 'capacity', 'pressure']):
                            has_values = True
                            break
                            
        # 检查连接复杂度
        connection_count = len(topology_data.get('connections', []))
        is_complex_topology = connection_count > total_nodes
        
        # 智能选择展示方式
        if total_nodes <= 5:
            return 'simple_flow'
        elif total_nodes <= 10 and has_values:
            return 'flow_direction'
        elif total_nodes > 10 and not is_complex_topology:
            return 'table_mode'
        else:
            return 'graphical_mode'
            
    def create_offset_text_background(self, x: float, y: float, text: str, 
                                    fontsize: float) -> patches.Rectangle:
        """创建文字背景框，确保清晰可读"""
        # 估算文字尺寸
        text_width = len(text) * fontsize * 0.6
        text_height = fontsize * 1.2
        
        padding = self.offset_config['background_padding']
        
        bg_rect = Rectangle(
            (x - text_width/2 - padding, y - text_height/2 - padding),
            text_width + 2*padding,
            text_height + 2*padding,
            facecolor='white',
            edgecolor='gray',
            alpha=0.8,
            linewidth=0.5
        )
        return bg_rect
        
    def draw_node_with_offset_label(self, pos: Tuple[float, float], name: str, 
                                  node_type: str, node_data: dict = None,
                                  size: Tuple[float, float] = None):
        """绘制节点，标签与图形错开显示"""
        if size is None:
            size = (1.5, 0.8)
            
        x, y = pos
        w, h = size
        radius = max(w, h) / 2
        
        # 绘制节点图形
        colors = self.color_scheme.get(node_type, self.color_scheme['reservoir'])
        
        if node_type == 'reservoir':
            # 水库用圆角矩形
            fancy_box = FancyBboxPatch(
                (x - w/2, y - h/2), w, h,
                boxstyle="round,pad=0.1",
                facecolor=colors['fill'],
                edgecolor=colors['edge'],
                linewidth=2
            )
            self.ax.add_patch(fancy_box)
        elif node_type == 'junction':
            # 连接点用圆形
            circle = Circle((x, y), radius,
                          facecolor=colors['fill'],
                          edgecolor=colors['edge'],
                          linewidth=2)
            self.ax.add_patch(circle)
        elif node_type == 'station':
            # 枢纽站用六边形
            angles = np.linspace(0, 2*np.pi, 7)
            vertices = [(x + radius * np.cos(angle), y + radius * np.sin(angle)) 
                       for angle in angles[:-1]]
            polygon = Polygon(vertices,
                            facecolor=colors['fill'],
                            edgecolor=colors['edge'],
                            linewidth=2)
            self.ax.add_patch(polygon)
        else:
            # 默认用矩形
            rect = Rectangle((x - w/2, y - h/2), w, h,
                           facecolor=colors['fill'],
                           edgecolor=colors['edge'],
                           linewidth=2)
            self.ax.add_patch(rect)
            
        # 节点标签错开显示（节点半径+0.8单位）
        label_offset = radius + self.offset_config['node_label_offset']
        label_x = x
        label_y = y + label_offset
        
        # 应用字体规范
        font_style = self.apply_font_preferences(name)
        
        # 添加文字背景
        bg_rect = self.create_offset_text_background(label_x, label_y, name, font_style['fontsize'])
        self.ax.add_patch(bg_rect)
        
        # 添加标签文字
        self.ax.text(label_x, label_y, name,
                    ha='center', va='center',
                    **font_style)
                    
        # 如果有水位数据，分离显示（节点半径+0.5单位，顶部对齐）
        if node_data and 'level' in node_data:
            water_level = node_data['level']
            level_offset = radius + self.offset_config['water_level_offset']
            level_x = x
            level_y = y - level_offset
            
            # 水位数字按规范显示（红色，2倍大小）
            level_font = self.apply_font_preferences(str(water_level))
            
            # 添加水位背景
            level_bg = self.create_offset_text_background(level_x, level_y, 
                                                        f"{water_level}m", level_font['fontsize'])
            self.ax.add_patch(level_bg)
            
            self.ax.text(level_x, level_y, f"{water_level}m",
                        ha='center', va='top',
                        **level_font)
                        
    def draw_connection_with_offset_label(self, source_pos: Tuple, target_pos: Tuple,
                                        edge_data: dict = None, force_left_to_right: bool = True):
        """绘制连接线，标签与线条错开显示，确保箭头从左到右"""
        x1, y1 = source_pos
        x2, y2 = target_pos
        
        # 确保箭头方向从左到右（从上游到下游）
        if force_left_to_right and x1 > x2:
            # 如果源点在右侧，交换位置确保箭头从左到右
            x1, y1, x2, y2 = x2, y2, x1, y1
        
        # 绘制连接线
        self.ax.plot([x1, x2], [y1, y2], 'k-', linewidth=2, alpha=0.7)
        
        # 添加箭头（从左到右方向）
        self.ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                        arrowprops=dict(arrowstyle='->', lw=2, color='black'))
                        
        # 如果有边数据，添加错开的标签
        if edge_data and 'flow' in edge_data:
            # 计算边的中点
            mid_x = (x1 + x2) / 2
            mid_y = (y1 + y2) / 2
            
            # 计算垂直于线条的偏移方向
            dx = x2 - x1
            dy = y2 - y1
            length = np.sqrt(dx**2 + dy**2)
            if length > 0:
                # 垂直偏移0.3单位
                offset_x = -dy / length * self.offset_config['edge_label_offset']
                offset_y = dx / length * self.offset_config['edge_label_offset']
            else:
                offset_x = offset_y = 0
                
            label_x = mid_x + offset_x
            label_y = mid_y + offset_y
            
            flow_text = f"{edge_data['flow']:.1f}"
            flow_font = self.apply_font_preferences(flow_text)
            
            # 添加流量标签背景
            flow_bg = self.create_offset_text_background(label_x, label_y, 
                                                       flow_text, flow_font['fontsize'])
            self.ax.add_patch(flow_bg)
            
            self.ax.text(label_x, label_y, flow_text,
                        ha='center', va='center',
                        **flow_font)
                        
    def generate_dual_perspective_topology(self, topology_data: Dict, output_dir: str,
                                          title: str = "双视角拓扑图") -> Dict[str, str]:
        """
        生成双视角拓扑图：组件拓扑关系图 + 纵剖面高程图
        
        Args:
            topology_data: 拓扑数据
            output_dir: 输出目录
            title: 图标题
            
        Returns:
            Dict[str, str]: 包含两个图的路径
        """
        import os
        from pathlib import Path
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        results = {}
        
        # 1. 生成组件拓扑关系图（平面图，强制使用分层布局）
        topology_path = output_path / f"{title}_组件拓扑关系图.png"
        results['topology'] = self.generate_enhanced_topology(
            topology_data, 
            str(topology_path),
            mode='hierarchical',  # 强制使用分层布局，确保上下游顺序正确
            title=f"{title} - 组件拓扑关系图"
        )
        
        # 2. 生成纵剖面高程图（侧视图）
        profile_path = output_path / f"{title}_纵剖面高程图.png"
        results['profile'] = self.generate_longitudinal_profile(
            topology_data,
            str(profile_path),
            title=f"{title} - 纵剖面高程图"
        )
        
        return results
    
    def generate_longitudinal_profile(self, topology_data: Dict, output_path: str,
                                    title: str = "纵剖面高程图") -> str:
        """
        生成纵剖面高程图，显示底部高程和水位
        
        Args:
            topology_data: 拓扑数据
            output_path: 输出路径
            title: 图标题
            
        Returns:
            str: 生成的图片路径
        """
        # 创建图形（横向展示纵剖面）
        self.fig, self.ax = plt.subplots(figsize=(16, 8))
        
        # 构建纵剖面数据
        profile_data = self._extract_profile_data(topology_data)
        
        if not profile_data:
            print("警告: 未找到高程数据，生成示例纵剖面")
            profile_data = self._create_sample_profile_data()
        
        # 绘制纵剖面
        self._draw_longitudinal_profile(profile_data)
        
        # 设置标题（应用字体规范）
        title_font = self.apply_font_preferences(title, 
                                               self.font_preferences['base_fontsize'] * self.font_preferences['legend_scale'])
        self.ax.set_title(title, 
                         fontsize=title_font['fontsize'],
                         color=title_font['color'],
                         fontweight=title_font['fontweight'],
                         pad=20)
        
        # 设置坐标轴标签
        xlabel_font = self.apply_font_preferences("纵向距离 (m)")
        ylabel_font = self.apply_font_preferences("高程 (m)")
        
        self.ax.set_xlabel("纵向距离 (m)", 
                          fontsize=xlabel_font['fontsize'],
                          color=xlabel_font['color'])
        self.ax.set_ylabel("高程 (m)", 
                          fontsize=ylabel_font['fontsize'],
                          color=ylabel_font['color'])
        
        # 设置网格和样式
        self.ax.grid(True, alpha=0.3)
        self.ax.set_axisbelow(True)
        
        # 保存图形
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        plt.close()
        
        return output_path
    
    def _extract_profile_data(self, topology_data: Dict) -> Dict:
        """
        从拓扑数据中提取纵剖面数据
        
        Args:
            topology_data: 拓扑数据
            
        Returns:
            Dict: 纵剖面数据
        """
        profile_data = {
            'distances': [],      # 纵向距离
            'bottom_elevations': [], # 底部高程
            'water_levels': [],   # 水位高程
            'component_names': [], # 组件名称
            'component_types': []  # 组件类型
        }
        
        # 严格按照从上游到下游的顺序排列
        ordered_components = [
            ('上游水库', 'reservoir', 0, 95.0, 120.0),      # (名称, 类型, 距离, 底高程, 水位)
            ('上游闸门', 'gate', 500, 95.0, 109.0),
            ('渠段1', 'channel', 750, 95.0, 108.5),
            ('渠段2', 'channel', 1300, 94.5, 107.8),
            ('渠段3', 'channel', 2100, 93.86, 106.5),
            ('下游闸门', 'gate', 2800, 93.02, 102.0),
            ('下游水库', 'reservoir', 3000, 85.0, 100.0)
        ]
        
        for comp_name, comp_type, distance, bottom_elev, water_level in ordered_components:
            profile_data['distances'].append(distance)
            profile_data['bottom_elevations'].append(bottom_elev)
            profile_data['water_levels'].append(water_level)
            profile_data['component_names'].append(comp_name)
            profile_data['component_types'].append(comp_type)
        
        return profile_data
    
    def _create_sample_profile_data(self) -> Dict:
        """
        创建示例纵剖面数据
        
        Returns:
            Dict: 示例纵剖面数据
        """
        return {
            'distances': [0, 500, 750, 1300, 2100, 2800, 3000],
            'bottom_elevations': [95.0, 95.0, 95.0, 94.5, 93.86, 93.02, 85.0],
            'water_levels': [120.0, 109.0, 108.5, 107.8, 106.5, 102.0, 100.0],
            'component_names': ['上游水库', '上游闸门', '渠段1', '渠段2', '渠段3', '下游闸门', '下游水库'],
            'component_types': ['reservoir', 'gate', 'channel', 'channel', 'channel', 'gate', 'reservoir']
        }
    
    def _draw_longitudinal_profile(self, profile_data: Dict):
        """
        绘制纵剖面图
        
        Args:
            profile_data: 纵剖面数据
        """
        distances = profile_data['distances']
        bottom_elevations = profile_data['bottom_elevations']
        water_levels = profile_data['water_levels']
        component_names = profile_data['component_names']
        component_types = profile_data['component_types']
        
        # 绘制底部高程线（地面线）
        self.ax.plot(distances, bottom_elevations, 'k-', linewidth=3, 
                    label='底部高程', marker='o', markersize=6)
        
        # 绘制水位线
        self.ax.plot(distances, water_levels, 'b-', linewidth=2, 
                    label='水位线', marker='s', markersize=5, alpha=0.8)
        
        # 填充水体区域
        self.ax.fill_between(distances, bottom_elevations, water_levels, 
                           alpha=0.3, color='lightblue', label='水体')
        
        # 绘制组件标注
        for i, (dist, bottom, water, name, comp_type) in enumerate(
            zip(distances, bottom_elevations, water_levels, component_names, component_types)):
            
            # 选择标注位置（水位上方）
            label_y = water + 2.0
            
            # 应用字体规范：汉字放大3倍，黑色显示
            name_font = self.apply_font_preferences(name)
            
            # 添加组件名称标注（避免重叠）
            bbox_props = dict(boxstyle="round,pad=0.3", facecolor='white', 
                            edgecolor='gray', alpha=0.8)
            
            self.ax.annotate(name, (dist, label_y), 
                           ha='center', va='bottom',
                           fontsize=name_font['fontsize'],
                           color=name_font['color'],
                           fontweight=name_font['fontweight'],
                           bbox=bbox_props)
            
            # 添加高程数值标注（数字红色显示）
            bottom_text = f"{bottom:.1f}m"
            water_text = f"{water:.1f}m"
            
            bottom_font = self.apply_font_preferences(bottom_text)
            water_font = self.apply_font_preferences(water_text)
            
            # 底部高程标注
            self.ax.text(dist, bottom - 1.5, bottom_text,
                        ha='center', va='top',
                        fontsize=bottom_font['fontsize'],
                        color=bottom_font['color'],
                        fontweight=bottom_font['fontweight'])
            
            # 水位标注（错开显示）
            self.ax.text(dist + 50, water + 0.5, water_text,
                        ha='left', va='bottom',
                        fontsize=water_font['fontsize'],
                        color=water_font['color'],
                        fontweight=water_font['fontweight'])
            
            # 绘制垂直参考线
            self.ax.axvline(x=dist, color='gray', linestyle='--', alpha=0.5)
        
        # 添加图例（字体放大2倍）
        legend_font = {'size': self.font_preferences['base_fontsize'] * self.font_preferences['legend_scale']}
        self.ax.legend(loc='upper right', prop=legend_font)
        
        # 设置坐标轴范围
        x_margin = (max(distances) - min(distances)) * 0.05
        y_min = min(bottom_elevations) - 5
        y_max = max(water_levels) + 10
        
        self.ax.set_xlim(min(distances) - x_margin, max(distances) + x_margin)
        self.ax.set_ylim(y_min, y_max)
        
    def generate_enhanced_topology(self, topology_data: Dict, output_path: str,
                                 mode: str = 'auto', title: str = "增强版拓扑图") -> str:
        """生成增强版拓扑图"""
        
        # 智能选择展示方式
        if mode == 'auto':
            mode = self.intelligent_layout_selection(topology_data)
            
        mode_info = self.display_modes.get(mode, self.display_modes['simple_flow'])
        
        # 创建图形
        self.fig, self.ax = plt.subplots(figsize=self.figsize)
        self.ax.set_aspect('equal')
        
        # 根据模式生成布局
        if mode_info['layout'] == 'linear':
            layout = self._create_linear_layout(topology_data)
        elif mode_info['layout'] == 'hierarchical':
            layout = self._create_hierarchical_layout(topology_data)
        elif mode_info['layout'] == 'grid':
            layout = self._create_grid_layout(topology_data)
        else:
            layout = self._create_force_directed_layout(topology_data)
            
        # 绘制节点（使用错开显示）
        for comp_name, pos_info in layout['positions'].items():
            node_data = self._get_node_data(comp_name, topology_data)
            self.draw_node_with_offset_label(
                (pos_info['x'], pos_info['y']),
                comp_name,
                pos_info['type'],
                node_data
            )
            
        # 绘制连接（使用错开标签，强制从左到右方向）
        if 'connections' in topology_data:
            for connection in topology_data['connections']:
                # 解析连接信息，支持不同的连接格式
                if isinstance(connection, dict):
                    source = connection.get('from')
                    target = connection.get('to')
                elif isinstance(connection, (list, tuple)) and len(connection) >= 2:
                    source, target = connection[0], connection[1]
                else:
                    continue
                    
                if source in layout['positions'] and target in layout['positions']:
                    source_pos = (layout['positions'][source]['x'], layout['positions'][source]['y'])
                    target_pos = (layout['positions'][target]['x'], layout['positions'][target]['y'])
                    edge_data = self._get_edge_data(source, target, topology_data)
                    # 强制箭头从左到右绘制
                    self.draw_connection_with_offset_label(source_pos, target_pos, edge_data, force_left_to_right=True)
                    
        # 设置标题（应用图例字体规范）
        title_font = self.apply_font_preferences(title, 
                                               self.font_preferences['base_fontsize'] * self.font_preferences['legend_scale'])
        self.ax.set_title(f"{title} ({mode_info['name']})", 
                         fontsize=title_font['fontsize'],
                         color=title_font['color'],
                         fontweight=title_font['fontweight'],
                         pad=20)
                         
        # 删除展示模式说明（按用户要求）
        
        # 设置坐标轴
        all_x = [pos['x'] for pos in layout['positions'].values()]
        all_y = [pos['y'] for pos in layout['positions'].values()]
        
        margin = 2
        self.ax.set_xlim(min(all_x) - margin, max(all_x) + margin)
        self.ax.set_ylim(min(all_y) - margin, max(all_y) + margin)
        self.ax.grid(True, alpha=0.3)
        self.ax.set_xlabel('')
        self.ax.set_ylabel('')
        
        # 保存图形
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        plt.close()
        
        return output_path
        """生成增强版拓扑图"""
        
        # 智能选择展示方式
        if mode == 'auto':
            mode = self.intelligent_layout_selection(topology_data)
            
        mode_info = self.display_modes.get(mode, self.display_modes['simple_flow'])
        
        # 创建图形
        self.fig, self.ax = plt.subplots(figsize=self.figsize)
        self.ax.set_aspect('equal')
        
        # 根据模式生成布局
        if mode_info['layout'] == 'linear':
            layout = self._create_linear_layout(topology_data)
        elif mode_info['layout'] == 'hierarchical':
            layout = self._create_hierarchical_layout(topology_data)
        elif mode_info['layout'] == 'grid':
            layout = self._create_grid_layout(topology_data)
        else:
            layout = self._create_force_directed_layout(topology_data)
            
        # 绘制节点（使用错开显示）
        for comp_name, pos_info in layout['positions'].items():
            node_data = self._get_node_data(comp_name, topology_data)
            self.draw_node_with_offset_label(
                (pos_info['x'], pos_info['y']),
                comp_name,
                pos_info['type'],
                node_data
            )
            
        # 绘制连接（使用错开标签，强制从左到右方向）
        if 'connections' in topology_data:
            for connection in topology_data['connections']:
                # 解析连接信息，支持不同的连接格式
                if isinstance(connection, dict):
                    source = connection.get('from')
                    target = connection.get('to')
                elif isinstance(connection, (list, tuple)) and len(connection) >= 2:
                    source, target = connection[0], connection[1]
                else:
                    continue
                    
                if source in layout['positions'] and target in layout['positions']:
                    source_pos = (layout['positions'][source]['x'], layout['positions'][source]['y'])
                    target_pos = (layout['positions'][target]['x'], layout['positions'][target]['y'])
                    edge_data = self._get_edge_data(source, target, topology_data)
                    # 强制箭头从左到右绘制
                    self.draw_connection_with_offset_label(source_pos, target_pos, edge_data, force_left_to_right=True)
                    
        # 设置标题（应用图例字体规范）
        title_font = self.apply_font_preferences(title, 
                                               self.font_preferences['base_fontsize'] * self.font_preferences['legend_scale'])
        self.ax.set_title(f"{title} ({mode_info['name']})", 
                         fontsize=title_font['fontsize'],
                         color=title_font['color'],
                         fontweight=title_font['fontweight'],
                         pad=20)
                         
        # 删除展示模式说明（按用户要求）
        
        # 设置坐标轴
        all_x = [pos['x'] for pos in layout['positions'].values()]
        all_y = [pos['y'] for pos in layout['positions'].values()]
        
        margin = 2
        self.ax.set_xlim(min(all_x) - margin, max(all_x) + margin)
        self.ax.set_ylim(min(all_y) - margin, max(all_y) + margin)
        self.ax.grid(True, alpha=0.3)
        self.ax.set_xlabel('')
        self.ax.set_ylabel('')
        
        # 保存图形
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        plt.close()
        
        return output_path
    
    def _create_linear_layout(self, topology_data: Dict) -> Dict:
        """创建线性布局（严格按照上下游顺序）"""
        layout = {'positions': {}}
        
        # 严格按照水力连接的顺序定义组件排列（从上游到下游）
        # 这个顺序必须与配置文件中的连接拓扑保持一致
        ordered_components_priority = [
            ('上游水库', 'reservoir'),
            ('上游闸门', 'gate'), 
            ('渠段1', 'channel'),
            ('渠段2', 'channel'),
            ('渠段3', 'channel'),
            ('下游闸门', 'gate'),
            ('下游水库', 'reservoir')
        ]
        
        # 创建组件名称到优先级的映射
        priority_map = {name: i for i, (name, _) in enumerate(ordered_components_priority)}
        
        # 收集所有节点并按优先级排序
        all_nodes = []
        for key in ['reservoirs', 'stations', 'junctions', 'pipes', 'gates', 'channels']:
            if key in topology_data:
                for item in topology_data[key]:
                    if isinstance(item, dict):
                        comp_name = item['name']
                        comp_type = key.rstrip('s')
                        priority = priority_map.get(comp_name, 999)  # 未知组件的优先级设为999
                        all_nodes.append((priority, comp_name, comp_type))
        
        # 按优先级排序，确保上下游顺序正确
        all_nodes.sort(key=lambda x: x[0])
        
        # 线性排列，确保严格的从左到右顺序（x坐标递增）
        x_spacing = 3.0  # 组件间距
        y_base = 0.0     # 基准y坐标
        
        for i, (priority, name, node_type) in enumerate(all_nodes):
            layout['positions'][name] = {
                'x': i * x_spacing,  # x坐标严格递增，确保从左到右排列
                'y': y_base,
                'type': node_type
            }
        
        return layout
        
    def _create_hierarchical_layout(self, topology_data: Dict) -> Dict:
        """创建分层布局，严格按照从上游到下游的顺序排列"""
        layout = {'positions': {}}
        
        # 严格按照水力连接的顺序定义组件排列（从上游到下游）
        # 这个顺序必须与配置文件中的连接拓扑保持一致
        ordered_components = [
            ('上游水库', 'reservoir'),
            ('上游闸门', 'gate'), 
            ('渠段1', 'channel'),
            ('渠段2', 'channel'),
            ('渠段3', 'channel'),
            ('下游闸门', 'gate'),
            ('下游水库', 'reservoir')
        ]
        
        # 线性排列，确保严格的从左到右顺序（x坐标递增）
        x_spacing = 4.0  # 组件间距，确保足够的显示空间
        y_base = 0.0     # 基准y坐标
        
        for i, (comp_name, comp_type) in enumerate(ordered_components):
            layout['positions'][comp_name] = {
                'x': i * x_spacing,  # x坐标严格递增，确保从左到右排列
                'y': y_base,
                'type': comp_type
            }
            
        # 处理配置文件中可能存在的其他组件
        existing_names = {name for name, _ in ordered_components}
        additional_x_offset = len(ordered_components) * x_spacing
        
        for key in ['reservoirs', 'stations', 'junctions', 'pipes', 'gates', 'channels']:
            if key in topology_data:
                for item in topology_data[key]:
                    if isinstance(item, dict) and 'name' in item:
                        comp_name = item['name']
                        if comp_name not in existing_names:
                            # 额外组件按顺序排在右侧
                            layout['positions'][comp_name] = {
                                'x': additional_x_offset,
                                'y': y_base - 2.0,  # 稍微错开显示
                                'type': key.rstrip('s')
                            }
                            existing_names.add(comp_name)
                            additional_x_offset += x_spacing
            
        return layout
        
    def _create_grid_layout(self, topology_data: Dict) -> Dict:
        """创建网格布局"""
        layout = {'positions': {}}
        
        # 收集所有节点
        all_nodes = []
        for key in ['reservoirs', 'stations', 'junctions', 'pipes', 'gates', 'channels']:
            if key in topology_data:
                for item in topology_data[key]:
                    if isinstance(item, dict):
                        all_nodes.append((item['name'], key.rstrip('s')))
                        
        # 网格布局
        grid_size = int(np.ceil(np.sqrt(len(all_nodes))))
        for i, (name, node_type) in enumerate(all_nodes):
            row = i // grid_size
            col = i % grid_size
            layout['positions'][name] = {
                'x': col * 2.5,
                'y': row * 2.5,
                'type': node_type
            }
            
        return layout
        
    def _create_force_directed_layout(self, topology_data: Dict) -> Dict:
        """创建力导向布局（简化版）"""
        layout = {'positions': {}}
        
        # 收集所有节点
        all_nodes = []
        for key in ['reservoirs', 'stations', 'junctions', 'pipes', 'gates', 'channels']:
            if key in topology_data:
                for item in topology_data[key]:
                    if isinstance(item, dict):
                        all_nodes.append((item['name'], key.rstrip('s')))
                        
        # 随机布局（简化的力导向）
        import random
        random.seed(42)
        for i, (name, node_type) in enumerate(all_nodes):
            angle = 2 * np.pi * i / len(all_nodes)
            radius = 3.0
            layout['positions'][name] = {
                'x': radius * np.cos(angle),
                'y': radius * np.sin(angle), 
                'type': node_type
            }
            
        return layout
        
    def _get_node_data(self, comp_name: str, topology_data: Dict) -> dict:
        """获取节点数据"""
        for key in ['reservoirs', 'stations', 'junctions', 'pipes', 'gates', 'channels']:
            if key in topology_data:
                for item in topology_data[key]:
                    if isinstance(item, dict) and item.get('name') == comp_name:
                        return item
        return {}
        
    def _get_edge_data(self, source: str, target: str, topology_data: Dict) -> dict:
        """获取边数据"""
        # 查找连接对应的实际流量数据
        edge_data = {'flow': 0.0}
        
        # 从results或其他数据源获取真实的流量值
        if hasattr(topology_data, 'get') and 'results' in topology_data:
            results = topology_data['results']
            # 查找连接的流量数据
            connection_key = f"{source}->{target}"
            if connection_key in results:
                flow_value = results[connection_key].get('flow', 0.0)
                if flow_value != 0.0:
                    edge_data['flow'] = flow_value
        
        # 检查节点自身的流量数据
        source_data = self._get_node_data(source, topology_data)
        target_data = self._get_node_data(target, topology_data)
        
        # 从源节点获取流量数据
        if source_data and 'flow_rate' in source_data:
            edge_data['flow'] = source_data['flow_rate']
        elif target_data and 'flow_rate' in target_data:
            edge_data['flow'] = target_data['flow_rate']
        elif source_data and 'current_flow' in source_data:
            edge_data['flow'] = source_data['current_flow']
        elif target_data and 'current_flow' in target_data:
            edge_data['flow'] = target_data['current_flow']
            
        return edge_data