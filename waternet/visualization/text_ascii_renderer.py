#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文本ASCII艺术风格拓扑图渲染器

基于用户偏好，优先实现文本形式的直观系统图展示。
支持多种ASCII艺术风格和中文显示。

Created by: Qoder AI Assistant  
Date: 2025-10-04
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import sys
import io
from contextlib import redirect_stdout

try:
    from .topology_generator import TopologyRenderer, TopologyConfig, NodeData, EdgeData, ComponentType
except ImportError:
    from topology_generator import TopologyRenderer, TopologyConfig, NodeData, EdgeData, ComponentType

logger = logging.getLogger(__name__)


@dataclass
class TextRenderConfig:
    """文本渲染配置"""
    width: int = 80
    height: int = 20
    style: str = "box_drawing"  # "box_drawing", "ascii_art", "simple"
    show_icons: bool = True
    show_values: bool = True
    show_flow_direction: bool = True
    encoding: str = "utf-8"
    node_width: int = 12
    connector_style: str = "arrows"  # "arrows", "lines", "pipes"


class TextASCIIRenderer(TopologyRenderer):
    """文本ASCII艺术风格渲染器"""
    
    def __init__(self, config: TopologyConfig):
        super().__init__(config)
        self.render_config = self._parse_render_config()
        self.canvas: List[List[str]] = []
        self.node_positions: Dict[str, Tuple[int, int]] = {}
        
        # 组件图标映射
        self.component_icons = {
            ComponentType.RESERVOIR: "🏞️ ",
            ComponentType.STATION: "🏗️ ",
            ComponentType.JUNCTION: "🔀",
            ComponentType.PIPE: "🚰",
            ComponentType.PUMP: "⚡",
            ComponentType.VALVE: "🚰",
            ComponentType.TURBINE: "🌀"
        }
        
        # ASCII艺术字符
        self.box_chars = {
            'horizontal': '─',
            'vertical': '│',
            'top_left': '┌',
            'top_right': '┐',
            'bottom_left': '└',
            'bottom_right': '┘',
            'cross': '┼',
            'tee_up': '┴',
            'tee_down': '┬',
            'tee_left': '┤',
            'tee_right': '├',
            'arrow_right': '→',
            'arrow_left': '←',
            'arrow_up': '↑',
            'arrow_down': '↓'
        }
        
        self.simple_chars = {
            'horizontal': '-',
            'vertical': '|',
            'top_left': '+',
            'top_right': '+',
            'bottom_left': '+',
            'bottom_right': '+',
            'cross': '+',
            'tee_up': '+',
            'tee_down': '+',
            'tee_left': '+',
            'tee_right': '+',
            'arrow_right': '>',
            'arrow_left': '<',
            'arrow_up': '^',
            'arrow_down': 'v'
        }
    
    def _parse_render_config(self) -> TextRenderConfig:
        """解析文本渲染配置"""
        render_cfg = self.config.render_config.get('text_ascii', {})
        layout_cfg = self.config.layout_config.get('text_layout', {})
        
        # 根据节点数量动态调整画布大小
        node_count = len(self.config.nodes)
        min_width = max(60, node_count * 16)  # 最小宽度
        min_height = max(15, 8)  # 最小高度
        
        return TextRenderConfig(
            width=max(layout_cfg.get('width', 100), min_width),
            height=max(layout_cfg.get('height', 25), min_height),
            style=render_cfg.get('style', 'box_drawing'),
            show_icons=render_cfg.get('show_icons', True),
            show_values=render_cfg.get('show_values', True),
            show_flow_direction=render_cfg.get('flow_arrows', True),
            node_width=min(layout_cfg.get('node_width', 14), 20),  # 限制节点宽度
            connector_style=layout_cfg.get('connector_style', 'arrows')
        )
    
    def can_render(self) -> bool:
        """检查是否支持文本渲染"""
        try:
            # 检查编码支持
            test_text = "测试中文显示🏞️"
            test_text.encode(self.render_config.encoding)
            return True
        except Exception as e:
            self.logger.warning(f"文本渲染环境检查失败: {e}")
            return False
    
    def render(self, output_path: Optional[str] = None) -> bool:
        """渲染文本拓扑图"""
        try:
            # 初始化画布
            self._init_canvas()
            
            # 计算节点位置
            self._calculate_positions()
            
            # 绘制连接线
            self._draw_connections()
            
            # 绘制节点
            self._draw_nodes()
            
            # 添加标题和说明
            self._add_header()
            
            # 添加图例和统计信息
            self._add_legend()
            
            # 输出结果
            output_text = self._generate_output()
            
            if output_path:
                with open(output_path, 'w', encoding=self.render_config.encoding) as f:
                    f.write(output_text)
                self.logger.info(f"文本拓扑图已保存到: {output_path}")
            else:
                print(output_text)
            
            return True
            
        except Exception as e:
            self.logger.error(f"文本渲染失败: {e}")
            return False
    
    def _init_canvas(self):
        """初始化画布"""
        self.canvas = [[' ' for _ in range(self.render_config.width)] 
                      for _ in range(self.render_config.height)]
    
    def _calculate_positions(self):
        """计算节点在画布上的位置"""
        if not self.config.nodes:
            return
        
        # 获取配置中的位置信息
        positions = [(node.position[0], node.position[1]) for node in self.config.nodes]
        
        if len(set(positions)) == 1:  # 所有节点位置相同，需要重新布局
            self._auto_layout_linear()
        else:
            self._manual_layout_with_scaling()
    
    def _auto_layout_linear(self):
        """线性自动布局"""
        node_count = len(self.config.nodes)
        if node_count == 0:
            return
        
        # 计算画布可用空间
        canvas_width = self.render_config.width - 4
        canvas_height = self.render_config.height - 8
        
        if node_count == 1:
            # 单个节点居中
            center_x = canvas_width // 2
            center_y = canvas_height // 2 + 4
            self.node_positions[self.config.nodes[0].id] = (center_x, center_y)
        else:
            # 多个节点水平排列
            spacing = max(self.render_config.node_width + 2, canvas_width // node_count)
            start_x = max(2, (canvas_width - (node_count - 1) * spacing) // 2)
            center_y = canvas_height // 2 + 4
            
            for i, node in enumerate(self.config.nodes):
                x = start_x + i * spacing
                self.node_positions[node.id] = (x, center_y)
    
    def _manual_layout_with_scaling(self):
        """手动布局带缩放"""
        # 获取配置中的位置信息
        min_x = min(node.position[0] for node in self.config.nodes)
        max_x = max(node.position[0] for node in self.config.nodes)
        min_y = min(node.position[1] for node in self.config.nodes)
        max_y = max(node.position[1] for node in self.config.nodes)
        
        # 计算缩放比例
        canvas_width = self.render_config.width - 4 - self.render_config.node_width
        canvas_height = self.render_config.height - 8
        
        if max_x > min_x:
            scale_x = canvas_width / (max_x - min_x)
        else:
            scale_x = 1
            
        if max_y > min_y:
            scale_y = min(canvas_height / (max_y - min_y), 3)  # 限制垂直缩放
        else:
            scale_y = 1
        
        # 映射到画布坐标
        for node in self.config.nodes:
            if max_x > min_x:
                canvas_x = int(2 + (node.position[0] - min_x) * scale_x)
            else:
                canvas_x = self.render_config.width // 2 - self.render_config.node_width // 2
                
            if max_y > min_y:
                canvas_y = int(4 + (node.position[1] - min_y) * scale_y)
            else:
                canvas_y = self.render_config.height // 2
            
            # 确保在画布范围内且避免重叠
            canvas_x = max(1, min(canvas_x, self.render_config.width - self.render_config.node_width - 1))
            canvas_y = max(3, min(canvas_y, self.render_config.height - 4))
            
            # 检查是否与其他节点重叠
            original_x, original_y = canvas_x, canvas_y
            attempt = 0
            while self._position_occupied(canvas_x, canvas_y) and attempt < 10:
                if attempt < 5:
                    canvas_x = original_x + (attempt + 1) * (self.render_config.node_width + 1)
                else:
                    canvas_y = original_y + (attempt - 4)
                canvas_x = max(1, min(canvas_x, self.render_config.width - self.render_config.node_width - 1))
                canvas_y = max(3, min(canvas_y, self.render_config.height - 4))
                attempt += 1
            
            self.node_positions[node.id] = (canvas_x, canvas_y)
    
    def _position_occupied(self, x: int, y: int) -> bool:
        """检查位置是否被其他节点占用"""
        for existing_pos in self.node_positions.values():
            ex, ey = existing_pos
            # 检查是否重叠（考虑节点大小）
            if (abs(x - ex) < self.render_config.node_width and 
                abs(y - ey) < 3):  # 节点高度约为3行
                return True
        return False
    
    def _draw_connections(self):
        """绘制连接线"""
        chars = self.box_chars if self.render_config.style == 'box_drawing' else self.simple_chars
        
        for edge in self.config.edges:
            if edge.source_id not in self.node_positions or edge.target_id not in self.node_positions:
                continue
            
            source_pos = self.node_positions[edge.source_id]
            target_pos = self.node_positions[edge.target_id]
            
            # 计算连接点（节点边缘）
            source_x = source_pos[0] + self.render_config.node_width
            source_y = source_pos[1] + 1  # 节点中心
            target_x = target_pos[0] - 1
            target_y = target_pos[1] + 1  # 节点中心
            
            # 直接水平连接
            if source_y == target_y and source_x < target_x:
                # 绘制水平线段
                for x in range(source_x, target_x):
                    if self._is_valid_pos(x, source_y) and not self._is_node_area(x, source_y):
                        self.canvas[source_y][x] = chars['horizontal']
                
                # 添加箭头
                if (self.render_config.show_flow_direction and 
                    self._is_valid_pos(target_x - 1, source_y) and 
                    not self._is_node_area(target_x - 1, source_y)):
                    self.canvas[source_y][target_x - 1] = chars['arrow_right']
            
            # 垂直或斜向连接（使用L形路径）
            elif source_y != target_y:
                # 计算中间点
                mid_x = (source_x + target_x) // 2
                
                # 水平段：从源到中间点
                for x in range(min(source_x, mid_x), max(source_x, mid_x) + 1):
                    if self._is_valid_pos(x, source_y) and not self._is_node_area(x, source_y):
                        self.canvas[source_y][x] = chars['horizontal']
                
                # 垂直段：从源高度到目标高度
                for y in range(min(source_y, target_y), max(source_y, target_y) + 1):
                    if self._is_valid_pos(mid_x, y) and not self._is_node_area(mid_x, y):
                        self.canvas[y][mid_x] = chars['vertical']
                
                # 水平段：从中间点到目标
                for x in range(min(mid_x, target_x), max(mid_x, target_x) + 1):
                    if self._is_valid_pos(x, target_y) and not self._is_node_area(x, target_y):
                        self.canvas[target_y][x] = chars['horizontal']
                
                # 连接点
                if self._is_valid_pos(mid_x, source_y) and not self._is_node_area(mid_x, source_y):
                    if source_y < target_y:
                        self.canvas[source_y][mid_x] = chars['tee_down']
                    else:
                        self.canvas[source_y][mid_x] = chars['tee_up']
                
                if self._is_valid_pos(mid_x, target_y) and not self._is_node_area(mid_x, target_y):
                    self.canvas[target_y][mid_x] = chars['tee_right']
                
                # 添加箭头
                if (self.render_config.show_flow_direction and 
                    self._is_valid_pos(target_x - 1, target_y) and 
                    not self._is_node_area(target_x - 1, target_y)):
                    self.canvas[target_y][target_x - 1] = chars['arrow_right']
    
    def _is_node_area(self, x: int, y: int) -> bool:
        """检查位置是否在节点区域内"""
        for node_id, pos in self.node_positions.items():
            node_x, node_y = pos
            if (node_x <= x < node_x + self.render_config.node_width and 
                node_y <= y < node_y + 3):  # 节点高度约为3行
                return True
        return False
    
    def _draw_nodes(self):
        """绘制节点"""
        for node in self.config.nodes:
            if node.id not in self.node_positions:
                continue
            
            x, y = self.node_positions[node.id]
            
            # 绘制节点框
            self._draw_node_box(x, y, node)
    
    def _draw_node_box(self, x: int, y: int, node: NodeData):
        """绘制单个节点框"""
        chars = self.box_chars if self.render_config.style == 'box_drawing' else self.simple_chars
        
        # 节点内容
        icon = self.component_icons.get(node.type, "⭕") if self.render_config.show_icons else ""
        name = node.name[:self.render_config.node_width - len(icon) - 2]
        
        # 获取关键属性值
        value_text = ""
        if self.render_config.show_values and node.properties:
            if 'flow_rate' in node.properties:
                value_text = f"{node.properties['flow_rate']:.1f}"
            elif 'water_level' in node.properties:
                value_text = f"{node.properties['water_level']:.1f}m"
        
        # 绘制顶部边框
        if self._is_valid_pos(x, y):
            self.canvas[y][x] = chars['top_left']
        for i in range(1, self.render_config.node_width - 1):
            if self._is_valid_pos(x + i, y):
                self.canvas[y][x + i] = chars['horizontal']
        if self._is_valid_pos(x + self.render_config.node_width - 1, y):
            self.canvas[y][x + self.render_config.node_width - 1] = chars['top_right']
        
        # 绘制内容行
        content = f"{icon}{name}"
        if self._is_valid_pos(x, y + 1):
            self.canvas[y + 1][x] = chars['vertical']
        for i, char in enumerate(content[:self.render_config.node_width - 2]):
            if self._is_valid_pos(x + 1 + i, y + 1):
                self.canvas[y + 1][x + 1 + i] = char
        if self._is_valid_pos(x + self.render_config.node_width - 1, y + 1):
            self.canvas[y + 1][x + self.render_config.node_width - 1] = chars['vertical']
        
        # 绘制数值行（如果有）
        if value_text:
            if self._is_valid_pos(x, y + 2):
                self.canvas[y + 2][x] = chars['vertical']
            for i, char in enumerate(value_text[:self.render_config.node_width - 2]):
                if self._is_valid_pos(x + 1 + i, y + 2):
                    self.canvas[y + 2][x + 1 + i] = char
            if self._is_valid_pos(x + self.render_config.node_width - 1, y + 2):
                self.canvas[y + 2][x + self.render_config.node_width - 1] = chars['vertical']
            bottom_y = y + 3
        else:
            bottom_y = y + 2
        
        # 绘制底部边框
        if self._is_valid_pos(x, bottom_y):
            self.canvas[bottom_y][x] = chars['bottom_left']
        for i in range(1, self.render_config.node_width - 1):
            if self._is_valid_pos(x + i, bottom_y):
                self.canvas[bottom_y][x + i] = chars['horizontal']
        if self._is_valid_pos(x + self.render_config.node_width - 1, bottom_y):
            self.canvas[bottom_y][x + self.render_config.node_width - 1] = chars['bottom_right']
    
    def _is_valid_pos(self, x: int, y: int) -> bool:
        """检查位置是否在画布范围内"""
        return 0 <= x < self.render_config.width and 0 <= y < self.render_config.height
    
    def _add_header(self):
        """添加标题和说明"""
        title = self.config.title
        separator = "=" * len(title)
        
        # 居中标题
        title_x = (self.render_config.width - len(title)) // 2
        separator_x = (self.render_config.width - len(separator)) // 2
        
        # 写入标题
        for i, char in enumerate(title):
            if self._is_valid_pos(title_x + i, 0):
                self.canvas[0][title_x + i] = char
        
        for i, char in enumerate(separator):
            if self._is_valid_pos(separator_x + i, 1):
                self.canvas[1][separator_x + i] = char
    
    def _add_legend(self):
        """添加图例"""
        # 统计信息
        node_count = len(self.config.nodes)
        edge_count = len(self.config.edges)
        
        stats_text = f"节点: {node_count} | 连接: {edge_count}"
        stats_y = self.render_config.height - 2
        
        for i, char in enumerate(stats_text):
            if self._is_valid_pos(i, stats_y):
                self.canvas[stats_y][i] = char
    
    def _generate_output(self) -> str:
        """生成最终输出文本"""
        lines = []
        
        # 转换画布为文本
        for row in self.canvas:
            line = ''.join(row).rstrip()
            lines.append(line)
        
        # 添加详细信息
        lines.append("")
        lines.append("组件详细信息:")
        lines.append("-" * 50)
        
        # 按类型分组显示组件信息
        component_groups = {}
        for node in self.config.nodes:
            type_name = self._get_type_display_name(node.type)
            if type_name not in component_groups:
                component_groups[type_name] = []
            component_groups[type_name].append(node)
        
        for type_name, nodes in component_groups.items():
            lines.append(f"{type_name}:")
            for node in nodes:
                icon = self.component_icons.get(node.type, "⭕")
                properties_text = self._format_node_properties(node)
                lines.append(f"   • {node.name}: {properties_text}")
            lines.append("")
        
        return '\n'.join(lines)
    
    def _get_type_display_name(self, component_type: ComponentType) -> str:
        """获取组件类型显示名称"""
        type_names = {
            ComponentType.RESERVOIR: "🏞️  水库系统",
            ComponentType.STATION: "🏗️  枢纽站系统", 
            ComponentType.JUNCTION: "🔀  连接点系统",
            ComponentType.PIPE: "🚰  管道系统",
            ComponentType.PUMP: "⚡  泵站系统",
            ComponentType.VALVE: "🚰  阀门系统",
            ComponentType.TURBINE: "🌀  水轮机系统"
        }
        return type_names.get(component_type, f"未知系统 ({component_type.value})")
    
    def _format_node_properties(self, node: NodeData) -> str:
        """格式化节点属性显示"""
        props = []
        
        if 'water_level' in node.properties:
            props.append(f"水位 {node.properties['water_level']:.1f}m")
        if 'flow_rate' in node.properties:
            props.append(f"流量 {node.properties['flow_rate']:.1f}m³/s")
        if 'diameter' in node.properties:
            props.append(f"直径 {node.properties['diameter']:.1f}m")
        if 'length' in node.properties:
            props.append(f"长度 {node.properties['length']:.0f}m")
        if 'velocity' in node.properties:
            props.append(f"流速 {node.properties['velocity']:.1f}m/s")
        
        return ", ".join(props) if props else "无详细信息"
    
    def get_render_info(self) -> Dict[str, Any]:
        """获取渲染信息"""
        return {
            'renderer_type': 'text_ascii',
            'canvas_size': (self.render_config.width, self.render_config.height),
            'style': self.render_config.style,
            'nodes_rendered': len(self.node_positions),
            'edges_rendered': len([e for e in self.config.edges 
                                 if e.source_id in self.node_positions 
                                 and e.target_id in self.node_positions]),
            'encoding': self.render_config.encoding,
            'features': {
                'icons': self.render_config.show_icons,
                'values': self.render_config.show_values,
                'flow_direction': self.render_config.show_flow_direction
            }
        }


if __name__ == "__main__":
    # 测试代码
    from topology_generator import TopologyConfig, NodeData, EdgeData, ComponentType
    
    # 创建测试配置
    test_config = TopologyConfig(
        title="文本渲染器测试",
        nodes=[
            NodeData("n1", "水库", ComponentType.RESERVOIR, (0, 1), {"water_level": 100.0}),
            NodeData("n2", "泵站", ComponentType.PUMP, (2, 1), {"flow_rate": 50.0}),
            NodeData("n3", "阀门", ComponentType.VALVE, (4, 1), {"opening": 75.0})
        ],
        edges=[
            EdgeData("e1", "进水管", "n1", "n2"),
            EdgeData("e2", "出水管", "n2", "n3")
        ]
    )
    
    renderer = TextASCIIRenderer(test_config)
    if renderer.can_render():
        renderer.render()
        print("\n文本渲染器测试完成！")
    else:
        print("文本渲染器环境检查失败！")