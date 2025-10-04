"""
优化版拓扑图生成器

解决汉字字体丢失问题，将图例放到边上，避免与其他对象重叠。
严格遵循用户字体显示规范和错开显示要求。
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Rectangle, Circle, Polygon
import numpy as np
import matplotlib.font_manager as fm
from typing import Dict, List, Tuple, Optional
import yaml
import json

# 配置中文字体支持，解决汉字字体丢失问题
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 尝试查找可用的中文字体
chinese_fonts = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS', 'WenQuanYi Micro Hei']
available_font = None
for font_name in chinese_fonts:
    try:
        font_path = fm.findfont(fm.FontProperties(family=font_name))
        if font_path and font_name.lower() in font_path.lower():
            available_font = font_name
            break
    except:
        continue

if available_font:
    print(f"找到可用中文字体: {available_font}")
else:
    print("警告: 未找到专用中文字体，将使用默认字体")
    available_font = 'DejaVu Sans'


class OptimizedTopologyGenerator:
    """优化版拓扑图生成器"""
    
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
        
        # 图例配置
        self.legend_config = {
            'position': 'right',       # 图例位置：右侧
            'spacing': 0.8,           # 图例项间距
            'margin': 0.5,            # 图例与图形边距
            'background_alpha': 0.9,   # 背景透明度
            'border_width': 1.5       # 边框宽度
        }
        
        # 颜色配置（加深加粗图例符号）
        self.color_scheme = {
            'reservoir': {'fill': '#BBDEFB', 'edge': '#0D47A1', 'text': '#0D47A1'},  # 更深的蓝色
            'station': {'fill': '#E1BEE7', 'edge': '#4A148C', 'text': '#4A148C'},   # 更深的紫色
            'junction': {'fill': '#C8E6C9', 'edge': '#1B5E20', 'text': '#1B5E20'},  # 更深的绿色
            'pipe': {'fill': '#FFE0B2', 'edge': '#BF360C', 'text': '#BF360C'},      # 更深的橙色
            'layer': {'fill': '#E0E0E0', 'edge': '#424242', 'text': '#424242'}      # 更深的灰色
        }
        
        # 层级配置
        self.layer_config = {
            'spacing': 2.5,           # 层间距
            'node_spacing': 2.0,      # 节点间距（增加间距避免重叠）
            'min_width': 1.8,         # 最小节点宽度
            'min_height': 1.0         # 最小节点高度
        }
        
    def apply_font_preferences(self, text: str, base_size: Optional[float] = None) -> dict:
        """
        应用用户字体偏好，解决汉字字体丢失问题
        
        Args:
            text: 文本内容
            base_size: 基础字体大小
            
        Returns:
            字体样式配置
        """
        if base_size is None:
            base_size = self.font_preferences['base_fontsize']
            
        # 检测文本类型
        has_chinese = any('\u4e00' <= char <= '\u9fff' for char in text)
        has_numbers = any(char.isdigit() for char in text)
        
        # 应用缩放（严格按照用户规范）
        if has_chinese:
            fontsize = base_size * self.font_preferences['chinese_scale']  # 汉字放大3倍
            color = self.font_preferences['chinese_color']  # 汉字黑色普通显示
            fontweight = 'bold'
            family = available_font  # 使用可用的中文字体
        else:
            fontsize = base_size
            color = 'black'
            fontweight = 'normal'
            family = 'DejaVu Sans'
            
        # 数字特殊处理（数字翻倍并红色显示）
        if has_numbers and not has_chinese:
            fontsize *= self.font_preferences['number_scale']
            color = self.font_preferences['number_color']
            fontweight = 'bold'
            
        return {
            'fontsize': fontsize,
            'color': color,
            'fontweight': fontweight,
            'family': family
        }
        
    def create_legend(self, layout: Dict) -> None:
        """
        创建图例，放置在右侧避免与其他对象重叠
        
        Args:
            layout: 布局信息
        """
        if not self.ax:
            return
            
        # 统计不同类型的组件
        component_types = {}
        for comp_name, pos_info in layout['positions'].items():
            comp_type = pos_info['type']
            if comp_type not in component_types:
                component_types[comp_type] = []
            component_types[comp_type].append(comp_name)
            
        # 计算图例位置（右侧）
        all_x = [pos['x'] for pos in layout['positions'].values()]
        all_y = [pos['y'] for pos in layout['positions'].values()]
        
        legend_x = max(all_x) + self.legend_config['margin'] + 2
        legend_y_start = max(all_y)
        
        # 类型名称映射
        type_names = {
            'reservoir': '水库',
            'station': '枢纽站',
            'junction': '连接点',
            'pipe': '管道',
            'component': '组件'
        }
        
        # 绘制图例标题
        title_font = self.apply_font_preferences('图例', 
                                               self.font_preferences['base_fontsize'] * self.font_preferences['legend_scale'])
        self.ax.text(legend_x, legend_y_start + 0.5, '图例', 
                    fontsize=title_font['fontsize'],
                    color=title_font['color'],
                    fontweight='bold',
                    fontfamily=title_font['family'],
                    ha='left', va='center')
        
        # 绘制图例项
        legend_y = legend_y_start
        for i, (comp_type, comp_list) in enumerate(component_types.items()):
            colors = self.color_scheme.get(comp_type, self.color_scheme['layer'])
            type_name = type_names.get(comp_type, comp_type)
            
            # 绘制图例符号
            if comp_type == 'reservoir':
                # 水库用圆角矩形
                legend_rect = FancyBboxPatch(
                    (legend_x, legend_y - 0.2), 0.4, 0.4,
                    boxstyle="round,pad=0.05",
                    facecolor=colors['fill'],
                    edgecolor=colors['edge'],
                    linewidth=3.0  # 加粗边框
                )
                self.ax.add_patch(legend_rect)
            elif comp_type == 'junction':
                # 连接点用圆形
                legend_circle = Circle((legend_x + 0.2, legend_y), 0.2,
                                     facecolor=colors['fill'],
                                     edgecolor=colors['edge'],
                                     linewidth=3.0)  # 加粗边框
                self.ax.add_patch(legend_circle)
            elif comp_type == 'station':
                # 枢纽站用六边形
                angles = np.linspace(0, 2*np.pi, 7)
                vertices = [(legend_x + 0.2 + 0.2 * np.cos(angle), legend_y + 0.2 * np.sin(angle)) 
                           for angle in angles[:-1]]
                legend_polygon = Polygon(vertices,
                                       facecolor=colors['fill'],
                                       edgecolor=colors['edge'],
                                       linewidth=3.0)  # 加粗边框
                self.ax.add_patch(legend_polygon)
            else:
                # 默认用矩形
                legend_rect = Rectangle((legend_x, legend_y - 0.2), 0.4, 0.4,
                                      facecolor=colors['fill'],
                                      edgecolor=colors['edge'],
                                      linewidth=3.0)  # 加粗边框
                self.ax.add_patch(legend_rect)
                
            # 添加图例文字（应用字体规范）
            label_font = self.apply_font_preferences(f'{type_name} ({len(comp_list)}个)', 
                                                   self.font_preferences['base_fontsize'] * self.font_preferences['legend_scale'])
            self.ax.text(legend_x + 0.6, legend_y, f'{type_name} ({len(comp_list)}个)', 
                        fontsize=label_font['fontsize'],
                        color=label_font['color'],
                        fontweight=label_font['fontweight'],
                        fontfamily=label_font['family'],
                        ha='left', va='center')
            
            legend_y -= self.legend_config['spacing']
            
        # 绘制图例背景框
        legend_height = len(component_types) * self.legend_config['spacing'] + 1
        legend_bg = Rectangle((legend_x - 0.2, legend_y_start + 0.8 - legend_height), 
                            2.5, legend_height,
                            facecolor='white',
                            edgecolor='gray',
                            alpha=self.legend_config['background_alpha'],
                            linewidth=self.legend_config['border_width'])
        self.ax.add_patch(legend_bg)
        
    def draw_node_with_improved_font(self, pos: Tuple[float, float], name: str, 
                                   node_type: str, node_data: dict = None,
                                   size: Tuple[float, float] = None):
        """
        绘制节点，使用改进的字体配置
        
        支持多种形状：矩形、圆形、三角形
        """
        if plt is None or self.ax is None:
            print("Error: matplotlib not available or axes not initialized")
            return
            
        if size is None:
            size = (self.layer_config['min_width'], self.layer_config['min_height'])
            
        x, y = pos
        w, h = size
        
        # 获取颜色配置
        colors = self.color_scheme.get(node_type, self.color_scheme['layer'])
        
        # 根据类型选择形状
        if node_type == 'reservoir' and FancyBboxPatch is not None:
            # 水库用圆角矩形
            fancy_box = FancyBboxPatch(
                (x - w/2, y - h/2), w, h,
                boxstyle="round,pad=0.1",
                facecolor=colors['fill'],
                edgecolor=colors['edge'],
                linewidth=2
            )
            self.ax.add_patch(fancy_box)
        elif node_type == 'junction' and Circle is not None:
            # 连接点用圆形
            circle = Circle((x, y), min(w, h)/2,
                          facecolor=colors['fill'],
                          edgecolor=colors['edge'],
                          linewidth=2)
            self.ax.add_patch(circle)
        elif node_type == 'station' and Polygon is not None and np is not None:
            # 枢纽站用六边形
            angles = np.linspace(0, 2*np.pi, 7)
            vertices = [(x + w/2 * np.cos(angle), y + h/2 * np.sin(angle)) 
                       for angle in angles[:-1]]
            polygon = Polygon(vertices,
                            facecolor=colors['fill'],
                            edgecolor=colors['edge'],
                            linewidth=2)
            self.ax.add_patch(polygon)
        elif Rectangle is not None:
            # 默认用矩形
            rect = Rectangle((x - w/2, y - h/2), w, h,
                           facecolor=colors['fill'],
                           edgecolor=colors['edge'],
                           linewidth=2)
            self.ax.add_patch(rect)
            
        # 添加文本标签（使用改进的字体配置）
        font_style = self.apply_font_preferences(name)
        text_color = colors['text']
        
        # 节点标签偏移显示（节点半径+0.8单位）
        label_offset = max(w, h)/2 + 0.8
        label_y = y + label_offset
        
        # 添加文字背景框确保清晰可读
        text_bg = Rectangle((x - len(name) * font_style['fontsize'] * 0.3, label_y - font_style['fontsize'] * 0.6), 
                          len(name) * font_style['fontsize'] * 0.6, font_style['fontsize'] * 1.2,
                          facecolor='white', edgecolor='gray', alpha=0.8, linewidth=0.5)
        self.ax.add_patch(text_bg)
        
        self.ax.text(x, label_y, name, 
                    ha='center', va='center',
                    color=text_color,
                    fontsize=font_style['fontsize'],
                    fontweight=font_style['fontweight'],
                    fontfamily=font_style['family'])
                    
        # 如果有水位数据，分离显示（节点半径+0.5单位，顶部对齐）
        if node_data and 'level' in node_data:
            water_level = node_data['level']
            level_offset = max(w, h)/2 + 0.5
            level_y = y - level_offset
            
            # 水位数字按规范显示（红色，2倍大小）
            level_font = self.apply_font_preferences(str(water_level))
            
            # 添加水位背景
            level_bg = Rectangle((x - 0.5, level_y - 0.3), 1.0, 0.6,
                               facecolor='white', edgecolor='red', alpha=0.9, linewidth=1)
            self.ax.add_patch(level_bg)
            
            self.ax.text(x, level_y, f"{water_level}m",
                        ha='center', va='top',
                        color=level_font['color'],
                        fontsize=level_font['fontsize'],
                        fontweight=level_font['fontweight'],
                        fontfamily=level_font['family'])
                        
    def create_layered_layout(self, topology_data: Dict) -> Dict:
        """创建分层布局"""
        layout = {
            'layers': [],
            'positions': {},
            'connections': []
        }
        
        # 定义层级结构（基于报告中的架构）
        layer_hierarchy = [
            {
                'name': '配置管理层',
                'components': ['ConfigManager', 'ConfigValidator', 'NetworkConfiguration'],
                'y_level': 0
            },
            {
                'name': '网络构建层', 
                'components': ['NetworkBuilder', 'TopologyValidator', 'ModelFactory系列'],
                'y_level': 1
            },
            {
                'name': '求解层',
                'components': ['ImplicitSolverAgent', 'SolverConfig'],
                'y_level': 2
            },
            {
                'name': '水力建模层',
                'components': ['ReservoirModel', 'ComplexStationModel', 'JunctionModel', 'PressurizedPipeModel'],
                'y_level': 3
            }
        ]
        
        # 处理实际的拓扑数据
        if 'reservoirs' in topology_data:
            self._add_data_layer(layout, '水库层', topology_data['reservoirs'], 4)
        if 'stations' in topology_data:
            self._add_data_layer(layout, '枢纽站层', topology_data['stations'], 3)
        if 'junctions' in topology_data:
            self._add_data_layer(layout, '连接点层', topology_data['junctions'], 2)
        if 'pipes' in topology_data:
            self._add_data_layer(layout, '管道层', topology_data['pipes'], 1)
            
        # 如果没有实际数据，使用报告中的架构
        if not any(key in topology_data for key in ['reservoirs', 'stations', 'junctions', 'pipes']):
            for layer_info in layer_hierarchy:
                self._add_architecture_layer(layout, layer_info)
                
        return layout
        
    def _add_data_layer(self, layout: Dict, layer_name: str, components: List, y_level: int):
        """添加数据层"""
        layer = {
            'name': layer_name,
            'components': [],
            'y_level': y_level
        }
        
        # 处理组件
        for i, comp in enumerate(components):
            if isinstance(comp, dict):
                comp_name = comp.get('name', f'Component_{i}')
                comp_type = comp.get('type', 'unknown')
                comp_data = comp
            else:
                comp_name = str(comp)
                comp_type = 'unknown'
                comp_data = {}
                
            layer['components'].append(comp_name)
            
            # 计算位置（增加间距避免重叠）
            x_pos = i * self.layer_config['node_spacing']
            y_pos = y_level * self.layer_config['spacing']
            
            layout['positions'][comp_name] = {
                'x': x_pos,
                'y': y_pos,
                'type': comp_type,
                'layer': layer_name,
                'data': comp_data
            }
            
        layout['layers'].append(layer)
        
    def _add_architecture_layer(self, layout: Dict, layer_info: Dict):
        """添加架构层"""
        layer = {
            'name': layer_info['name'],
            'components': layer_info['components'].copy(),
            'y_level': layer_info['y_level']
        }
        
        # 计算组件位置
        for i, comp_name in enumerate(layer_info['components']):
            x_pos = i * self.layer_config['node_spacing']
            y_pos = layer_info['y_level'] * self.layer_config['spacing']
            
            layout['positions'][comp_name] = {
                'x': x_pos,
                'y': y_pos,
                'type': self._infer_component_type(comp_name),
                'layer': layer_info['name']
            }
            
        layout['layers'].append(layer)
        
    def _infer_component_type(self, comp_name: str) -> str:
        """推断组件类型"""
        name_lower = comp_name.lower()
        if 'reservoir' in name_lower or '水库' in comp_name:
            return 'reservoir'
        elif 'station' in name_lower or '枢纽' in comp_name:
            return 'station'
        elif 'junction' in name_lower or '连接' in comp_name:
            return 'junction'
        elif 'pipe' in name_lower or '管道' in comp_name:
            return 'pipe'
        else:
            return 'component'
            
    def generate_optimized_topology_png(self, topology_data: Dict, output_path: str,
                                      title: str = "优化版拓扑图") -> str:
        """
        生成优化版拓扑图PNG文件
        
        Args:
            topology_data: 拓扑数据
            output_path: 输出路径
            title: 图标题
            
        Returns:
            生成的文件路径
        """
        if plt is None:
            print("Error: matplotlib not available. Please install with: pip install matplotlib")
            return ""
            
        # 创建图形
        self.fig, self.ax = plt.subplots(figsize=self.figsize)
        self.ax.set_aspect('equal')
        
        # 生成布局
        layout = self.create_layered_layout(topology_data)
        
        # 绘制节点（使用改进的字体）
        for comp_name, pos_info in layout['positions'].items():
            node_data = pos_info.get('data', {})
            self.draw_node_with_improved_font(
                (pos_info['x'], pos_info['y']),
                comp_name,
                pos_info['type'],
                node_data
            )
            
        # 绘制连接（如果有）
        if 'connections' in topology_data:
            for source, target in topology_data['connections']:
                if source in layout['positions'] and target in layout['positions']:
                    source_pos = (layout['positions'][source]['x'], layout['positions'][source]['y'])
                    target_pos = (layout['positions'][target]['x'], layout['positions'][target]['y'])
                    
                    # 绘制连接线
                    self.ax.plot([source_pos[0], target_pos[0]], 
                               [source_pos[1], target_pos[1]],
                               'k-', linewidth=2.0, alpha=0.7)  # 加粗连接线
                               
                    # 添加箭头
                    self.ax.annotate('', xy=target_pos, xytext=source_pos,
                                   arrowprops=dict(arrowstyle='->', lw=1.5, color='black'))
                                   
        # 创建图例（放置在右侧）
        self.create_legend(layout)
        
        # 设置标题（应用图例字体规范）
        title_font = self.apply_font_preferences(title, 
                                               self.font_preferences['base_fontsize'] * self.font_preferences['legend_scale'])
        self.ax.set_title(title, 
                         fontsize=title_font['fontsize'],
                         color=title_font['color'],
                         fontweight=title_font['fontweight'],
                         fontfamily=title_font['family'],
                         pad=20)
        
        # 设置坐标轴（为图例留出空间）
        all_x = [pos['x'] for pos in layout['positions'].values()]
        all_y = [pos['y'] for pos in layout['positions'].values()]
        
        margin = 2
        legend_space = 4  # 为图例预留空间
        self.ax.set_xlim(min(all_x) - margin, max(all_x) + margin + legend_space)
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
        
    def create_sample_topology(self) -> Dict:
        """创建示例拓扑数据"""
        return {
            'reservoirs': [
                {'name': '上游水库', 'type': 'reservoir', 'level': 125.3},
                {'name': '调节水库', 'type': 'reservoir', 'level': 118.7}
            ],
            'stations': [
                {'name': '主控制枢纽', 'type': 'station'},
                {'name': '分水枢纽', 'type': 'station'}
            ],
            'junctions': [
                {'name': '主分流点', 'type': 'junction'},
                {'name': '汇流点', 'type': 'junction'}
            ],
            'pipes': [
                {'name': '输水主管', 'type': 'pipe', 'flow': 45.8},
                {'name': '泄洪渠', 'type': 'pipe', 'flow': 32.1},
                {'name': '支流管道', 'type': 'pipe', 'flow': 18.5},
                {'name': '连接管道', 'type': 'pipe', 'flow': 26.3}
            ],
            'connections': [
                ('上游水库', '主控制枢纽'),
                ('主控制枢纽', '主分流点'),
                ('主分流点', '分水枢纽'),
                ('分水枢纽', '调节水库')
            ]
        }


def main():
    """演示优化版拓扑图生成"""
    generator = OptimizedTopologyGenerator()
    
    # 生成示例图
    sample_data = generator.create_sample_topology()
    output_path = "e:/OneDrive/Documents/GitHub/WaterNet/优化版拓扑图.png"
    
    result_path = generator.generate_optimized_topology_png(
        sample_data, 
        output_path,
        "WaterNet优化版拓扑图"
    )
    
    print(f"优化版拓扑图已生成: {result_path}")
    print("改进特点:")
    print("1. 解决了汉字字体丢失问题")
    print("2. 图例移至右侧，避免与其他对象重叠")
    print("3. 严格遵循用户字体显示规范")
    print("4. 增加节点间距，避免重叠")
    print("5. 文字背景框提升可读性")


if __name__ == "__main__":
    main()