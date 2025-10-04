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
                                        edge_data: dict = None):
        """绘制连接线，标签与线条错开显示"""
        x1, y1 = source_pos
        x2, y2 = target_pos
        
        # 绘制连接线
        self.ax.plot([x1, x2], [y1, y2], 'k-', linewidth=2, alpha=0.7)
        
        # 添加箭头
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
            
        # 绘制连接（使用错开标签）
        if 'connections' in topology_data:
            for source, target in topology_data['connections']:
                if source in layout['positions'] and target in layout['positions']:
                    source_pos = (layout['positions'][source]['x'], layout['positions'][source]['y'])
                    target_pos = (layout['positions'][target]['x'], layout['positions'][target]['y'])
                    edge_data = self._get_edge_data(source, target, topology_data)
                    self.draw_connection_with_offset_label(source_pos, target_pos, edge_data)
                    
        # 设置标题（应用图例字体规范）
        title_font = self.apply_font_preferences(title, 
                                               self.font_preferences['base_fontsize'] * self.font_preferences['legend_scale'])
        self.ax.set_title(f"{title} ({mode_info['name']})", 
                         fontsize=title_font['fontsize'],
                         color=title_font['color'],
                         fontweight=title_font['fontweight'],
                         pad=20)
                         
        # 添加模式说明
        mode_text = f"展示模式: {mode_info['description']}"
        mode_font = self.apply_font_preferences(mode_text, 10)
        self.ax.text(0.02, 0.98, mode_text,
                    transform=self.ax.transAxes,
                    verticalalignment='top',
                    bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8),
                    **mode_font)
        
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