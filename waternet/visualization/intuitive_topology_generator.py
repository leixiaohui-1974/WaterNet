"""
直观系统拓扑图生成器

基于COMPLEX_HUB_IMPLEMENTATION_REPORT.md中的分层架构算法，
自动生成美观的PNG格式拓扑图。

算法特点：
1. 分层布局：按功能层级组织组件
2. 智能定位：自动避免重叠
3. 美观渲染：支持多种形状和样式
"""

try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    from matplotlib.patches import FancyBboxPatch, Rectangle, Circle, Polygon
    import numpy as np
    import matplotlib.font_manager as fm
    
    # 配置中文字体支持，解决汉字字体丢失问题
    plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    
    # 尝试查找可用的中文字体
    chinese_fonts = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS', 'WenQuanYi Micro Hei']
    available_font = None
    for font_name in chinese_fonts:
        try:
            font_path = fm.findfont(fm.FontProperties(family=font_name))
            if font_path:
                available_font = font_name
                break
        except:
            continue
            
except ImportError:
    print("Warning: matplotlib or numpy not installed. Please install with: pip install matplotlib numpy")
    plt = None
    patches = None
    FancyBboxPatch = Rectangle = Circle = Polygon = None
    np = None
    available_font = None

from typing import Dict, List, Tuple, Optional, Union
import yaml
import json


class IntuitiveTopologyGenerator:
    """直观拓扑图生成器"""
    
    def __init__(self, figsize=(14, 10)):
        """
        初始化生成器
        
        Args:
            figsize: 图形尺寸
        """
        self.figsize = figsize
        self.fig = None
        self.ax = None
        
        # 用户字体偏好设置
        self.font_preferences = {
            'chinese_scale': 3.0,      # 汉字放大倍数
            'number_scale': 2.0,       # 数字放大倍数
            'number_color': 'red',     # 数字颜色
            'base_fontsize': 8         # 基础字体大小
        }
        
        # 层级配置
        self.layer_config = {
            'spacing': 2.5,           # 层间距
            'node_spacing': 1.8,      # 节点间距
            'min_width': 1.5,         # 最小节点宽度
            'min_height': 0.8         # 最小节点高度
        }
        
        # 颜色配置
        self.color_scheme = {
            'reservoir': {'fill': '#E3F2FD', 'edge': '#1976D2', 'text': '#0D47A1'},
            'station': {'fill': '#F3E5F5', 'edge': '#7B1FA2', 'text': '#4A148C'}, 
            'junction': {'fill': '#E8F5E8', 'edge': '#388E3C', 'text': '#1B5E20'},
            'pipe': {'fill': '#FFF3E0', 'edge': '#F57C00', 'text': '#E65100'},
            'layer': {'fill': '#FAFAFA', 'edge': '#BDBDBD', 'text': '#424242'}
        }
        
    def apply_font_preferences(self, text: str, base_size: Optional[float] = None) -> dict:
        """
        应用用户字体偏好
        
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
            color = 'black'  # 汉字黑色普通显示
            fontweight = 'bold'
        else:
            fontsize = base_size
            color = 'black'
            fontweight = 'normal'
            
        # 数字特殊处理（数字翻倍并红色显示）
        if has_numbers and not has_chinese:
            fontsize *= self.font_preferences['number_scale']
            color = self.font_preferences['number_color']
            fontweight = 'bold'
            
        # 使用可用的中文字体
        font_family = available_font if available_font and has_chinese else 'DejaVu Sans'
            
        return {
            'fontsize': fontsize,
            'color': color,
            'fontweight': fontweight,
            'family': font_family
        }
        
    def create_layered_layout(self, topology_data: Dict) -> Dict:
        """
        创建分层布局
        
        基于COMPLEX_HUB_IMPLEMENTATION_REPORT.md的分层架构算法:
        - 按功能层级组织
        - 自动计算位置
        - 避免重叠
        
        Args:
            topology_data: 拓扑数据
            
        Returns:
            布局信息
        """
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
            else:
                comp_name = str(comp)
                comp_type = 'unknown'
                
            layer['components'].append(comp_name)
            
            # 计算位置
            x_pos = i * self.layer_config['node_spacing']
            y_pos = y_level * self.layer_config['spacing']
            
            layout['positions'][comp_name] = {
                'x': x_pos,
                'y': y_pos,
                'type': comp_type,
                'layer': layer_name
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
            
    def find_optimal_label_position(self, node_pos: Tuple[float, float], 
                                  node_size: Tuple[float, float],
                                  existing_positions: List[Tuple]) -> Tuple[float, float]:
        """
        智能标签定位算法
        
        尝试8个候选位置，选择最少重叠的位置
        """
        x, y = node_pos
        w, h = node_size
        
        # 8个候选位置
        candidates = [
            (x, y + h/2 + 0.3),      # 上方
            (x, y - h/2 - 0.3),      # 下方
            (x + w/2 + 0.3, y),      # 右方
            (x - w/2 - 0.3, y),      # 左方
            (x + w/2 + 0.2, y + h/2 + 0.2),  # 右上
            (x - w/2 - 0.2, y + h/2 + 0.2),  # 左上
            (x + w/2 + 0.2, y - h/2 - 0.2),  # 右下
            (x - w/2 - 0.2, y - h/2 - 0.2),  # 左下
        ]
        
        # 选择最少重叠的位置
        best_pos = candidates[0]
        min_overlaps = float('inf')
        
        for candidate in candidates:
            overlaps = sum(1 for pos in existing_positions 
                          if abs(candidate[0] - pos[0]) < 0.5 and abs(candidate[1] - pos[1]) < 0.3)
            if overlaps < min_overlaps:
                min_overlaps = overlaps
                best_pos = candidate
                
        return best_pos
        
    def draw_node(self, pos: Tuple[float, float], name: str, node_type: str, 
                  size: Optional[Tuple[float, float]] = None):
        """
        绘制节点
        
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
        self.ax.text(x, y, name, 
                    ha='center', va='center',
                    color=text_color,
                    fontsize=font_style['fontsize'],
                    fontweight=font_style['fontweight'],
                    fontfamily=font_style.get('family', 'DejaVu Sans'))
                    
    def draw_layer_background(self, layer_name: str, components_positions: List[Tuple], 
                            y_level: int):
        """绘制层背景"""
        if not components_positions or plt is None or self.ax is None or Rectangle is None:
            return
            
        # 计算边界
        xs = [pos[0] for pos in components_positions]
        min_x, max_x = min(xs) - 1, max(xs) + 1
        y_center = y_level * self.layer_config['spacing']
        
        # 绘制背景矩形
        colors = self.color_scheme['layer']
        bg_rect = Rectangle((min_x, y_center - 0.6), max_x - min_x, 1.2,
                          facecolor=colors['fill'],
                          edgecolor=colors['edge'],
                          linewidth=1,
                          alpha=0.3)
        self.ax.add_patch(bg_rect)
        
        # 添加层标签
        font_style = self.apply_font_preferences(layer_name, 10)
        text_color = colors['text']
        self.ax.text(min_x - 0.5, y_center, layer_name,
                    ha='right', va='center',
                    color=text_color,
                    fontsize=font_style['fontsize'],
                    fontweight=font_style['fontweight'])
                    
    def draw_connections(self, connections: List[Tuple[str, str]], positions: Dict):
        """绘制连接线"""
        if plt is None or self.ax is None:
            return
            
        for source, target in connections:
            if source in positions and target in positions:
                source_pos = positions[source]
                target_pos = positions[target]
                
                # 绘制连接线
                self.ax.plot([source_pos['x'], target_pos['x']], 
                           [source_pos['y'], target_pos['y']],
                           'k-', linewidth=1.5, alpha=0.6)
                           
                # 添加箭头
                dx = target_pos['x'] - source_pos['x']
                dy = target_pos['y'] - source_pos['y']
                self.ax.annotate('', xy=(target_pos['x'], target_pos['y']),
                               xytext=(source_pos['x'], source_pos['y']),
                               arrowprops=dict(arrowstyle='->', lw=1.5, color='black'))
                               
    def generate_topology_png(self, topology_data: Dict, output_path: str,
                            title: str = "直观系统拓扑图") -> str:
        """
        生成拓扑图PNG文件
        
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
        
        # 绘制层背景
        for layer in layout['layers']:
            layer_positions = []
            for comp_name in layer['components']:
                if comp_name in layout['positions']:
                    pos = layout['positions'][comp_name]
                    layer_positions.append((pos['x'], pos['y']))
            self.draw_layer_background(layer['name'], layer_positions, layer['y_level'])
            
        # 绘制节点
        for comp_name, pos_info in layout['positions'].items():
            self.draw_node((pos_info['x'], pos_info['y']), 
                          comp_name, pos_info['type'])
                          
        # 绘制连接（如果有）
        if 'connections' in topology_data:
            self.draw_connections(topology_data['connections'], layout['positions'])
            
        # 设置标题
        title_font = self.apply_font_preferences(title, 16)
        self.ax.set_title(title, fontsize=title_font['fontsize'], 
                         color=title_font['color'],
                         fontweight=title_font['fontweight'], pad=20)
        
        # 设置坐标轴
        self.ax.set_xlim(-2, max([pos['x'] for pos in layout['positions'].values()]) + 2)
        self.ax.set_ylim(-1, max([pos['y'] for pos in layout['positions'].values()]) + 1)
        self.ax.grid(True, alpha=0.3)
        
        xlabel_font = self.apply_font_preferences('系统组件分布', 12)
        self.ax.set_xlabel('系统组件分布', fontsize=xlabel_font['fontsize'], 
                          color=xlabel_font['color'])
        
        ylabel_font = self.apply_font_preferences('功能层级', 12)
        self.ax.set_ylabel('功能层级', fontsize=ylabel_font['fontsize'], 
                          color=ylabel_font['color'])
        
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
                {'name': '上游水库', 'type': 'reservoir'},
                {'name': '调节水库', 'type': 'reservoir'}
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
                {'name': '输水主管', 'type': 'pipe'},
                {'name': '泄洪渠', 'type': 'pipe'},
                {'name': '支流管道', 'type': 'pipe'},
                {'name': '连接管道', 'type': 'pipe'}
            ],
            'connections': [
                ('上游水库', '主控制枢纽'),
                ('主控制枢纽', '主分流点'),
                ('主分流点', '分水枢纽'),
                ('分水枢纽', '调节水库')
            ]
        }


def main():
    """演示拓扑图生成"""
    generator = IntuitiveTopologyGenerator()
    
    # 生成示例图
    sample_data = generator.create_sample_topology()
    output_path = "e:/OneDrive/Documents/GitHub/WaterNet/直观系统拓扑图.png"
    
    result_path = generator.generate_topology_png(
        sample_data, 
        output_path,
        "WaterNet水力建模系统拓扑图"
    )
    
    print(f"拓扑图已生成: {result_path}")
    
    # 生成架构图
    architecture_data = {}  # 空数据将使用报告中的架构
    arch_output_path = "e:/OneDrive/Documents/GitHub/WaterNet/系统架构拓扑图.png"
    
    arch_result_path = generator.generate_topology_png(
        architecture_data,
        arch_output_path, 
        "WaterNet系统架构图"
    )
    
    print(f"架构图已生成: {arch_result_path}")


if __name__ == "__main__":
    main()