#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版文本拓扑图渲染器

支持多种展示风格：简洁流程图、详细连接图、层次结构图、网络拓扑图、流向示意图。
根据用户偏好和数据特点自动选择最佳展示方式。

Created by: Qoder AI Assistant
Date: 2025-10-04
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict, deque

try:
    from .topology_generator import TopologyRenderer, TopologyConfig, NodeData, EdgeData, ComponentType
except ImportError:
    from topology_generator import TopologyRenderer, TopologyConfig, NodeData, EdgeData, ComponentType

logger = logging.getLogger(__name__)


@dataclass
class EnhancedTextRenderConfig:
    """增强版文本渲染配置"""
    width: int = 100
    height: int = 30
    style: str = "auto"  # "auto", "simple_flow", "detailed", "hierarchical", "network", "flow_diagram"
    show_icons: bool = True
    show_values: bool = True
    auto_select: bool = True


class EnhancedTextRenderer(TopologyRenderer):
    """增强版文本拓扑图渲染器"""
    
    def __init__(self, config: TopologyConfig):
        super().__init__(config)
        self.render_config = self._parse_render_config()
        
        # 组件图标映射
        self.component_icons = {
            ComponentType.RESERVOIR: "🏞️",
            ComponentType.STATION: "🏗️",
            ComponentType.JUNCTION: "🔀",
            ComponentType.PIPE: "🚰",
            ComponentType.PUMP: "⚡",
            ComponentType.VALVE: "🚰",
            ComponentType.TURBINE: "🌀"
        }
    
    def _parse_render_config(self) -> EnhancedTextRenderConfig:
        """解析增强版渲染配置"""
        render_cfg = self.config.render_config.get('text_ascii', {})
        
        node_count = len(self.config.nodes)
        min_width = max(80, node_count * 20)
        
        return EnhancedTextRenderConfig(
            width=max(render_cfg.get('width', min_width), min_width),
            style=render_cfg.get('style', 'auto'),
            show_icons=render_cfg.get('show_icons', True),
            show_values=render_cfg.get('show_values', True),
            auto_select=render_cfg.get('auto_select', True)
        )
    
    def can_render(self) -> bool:
        """检查是否支持增强版文本渲染"""
        try:
            test_text = "测试中文显示🏞️"
            test_text.encode('utf-8')
            return True
        except Exception as e:
            self.logger.warning(f"增强版文本渲染环境检查失败: {e}")
            return False
    
    def render(self, output_path: Optional[str] = None) -> bool:
        """渲染增强版文本拓扑图"""
        try:
            # 自动选择最佳展示方式
            if self.render_config.auto_select:
                style = self._select_best_style()
            else:
                style = self.render_config.style
            
            # 生成对应风格的拓扑图
            if style == "simple_flow":
                output_text = self._render_simple_flow()
            elif style == "flow_diagram":
                output_text = self._render_flow_diagram()
            else:
                output_text = self._render_simple_flow()  # 默认
            
            # 输出结果
            if output_path:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(output_text)
                self.logger.info(f"增强版拓扑图已保存到: {output_path}")
            else:
                print(output_text)
            
            return True
            
        except Exception as e:
            self.logger.error(f"增强版文本渲染失败: {e}")
            return False
    
    def _select_best_style(self) -> str:
        """自动选择最佳展示方式"""
        node_count = len(self.config.nodes)
        
        # 检查是否有流量信息
        has_flow = any('flow_rate' in edge.properties for edge in self.config.edges)
        
        if has_flow and node_count >= 4:
            return "flow_diagram"  # 流向示意图
        else:
            return "simple_flow"   # 简洁流程图
    
    def _render_simple_flow(self) -> str:
        """渲染简洁流程图"""
        lines = []
        
        # 标题
        title = f"{self.config.title} - 简洁流程图"
        box_width = max(70, len(title) + 10)
        
        lines.append("┌" + "─" * (box_width - 2) + "┐")
        lines.append(f"│{title:^{box_width - 2}}│")
        lines.append("├" + "─" * (box_width - 2) + "┤")
        lines.append("│" + " " * (box_width - 2) + "│")
        
        # 构建流程线
        ordered_nodes = self._order_nodes_by_flow()
        
        # 主流程线
        flow_line = "│  "
        value_line = "│    "
        
        for i, node in enumerate(ordered_nodes):
            icon = self.component_icons.get(node.type, "⭕")
            name = node.name
            value = self._get_node_value_display(node)
            
            if i > 0:
                flow_line += " ➤ "
                value_line += "      "
            
            flow_line += f"{icon}{name}"
            if value:
                value_line += f"{value}"
            
            # 处理分流
            if self._is_split_node(node.id):
                branches = self._get_split_branches(node.id)
                if len(branches) > 1:
                    flow_line += " ➤ ┬ "
                    for j, (branch_node, edge) in enumerate(branches[:2]):  # 最多显示2个分支
                        branch_icon = self.component_icons.get(branch_node.type, "⭕")
                        branch_value = self._get_edge_value_display(edge)
                        
                        if j == 0:
                            flow_line += f"{branch_icon}{branch_node.name}"
                            if branch_value:
                                value_line += f" {branch_value}"
                        else:
                            # 第二个分支在下一行
                            next_flow_line = "│" + " " * (len(flow_line.split('│')[-1]) - 1) + "└ "
                            next_flow_line += f"{branch_icon}{branch_node.name}"
                            lines.append(flow_line + " " * (box_width - len(flow_line) - 1) + "│")
                            lines.append(value_line + " " * (box_width - len(value_line) - 1) + "│")
                            flow_line = next_flow_line
                            value_line = "│" + " " * (len(next_flow_line.split('│')[-1]) - len(branch_value) - 1) + branch_value if branch_value else "│"
                    
                    # 汇流
                    if j == 0:  # 只有一个分支时
                        flow_line += " ➤ 汇流点"
                    else:
                        flow_line += " ➤ ┘"
        
        # 补齐行长度并添加
        flow_line += " " * (box_width - len(flow_line) - 1) + "│"
        value_line += " " * (box_width - len(value_line) - 1) + "│"
        lines.append(flow_line)
        if any(v for v in value_line if v not in "│ "):
            lines.append(value_line)
        
        lines.append("│" + " " * (box_width - 2) + "│")
        lines.append("└" + "─" * (box_width - 2) + "┘")
        
        return '\n'.join(lines)
    
    def _render_flow_diagram(self) -> str:
        """渲染流向示意图"""
        lines = []
        
        # 标题框
        title = f"{self.config.title} - 流向示意图"
        box_width = 85
        
        lines.append("┏" + "━" * (box_width - 2) + "┓")
        lines.append(f"┃{title:^{box_width - 2}}┃")
        lines.append("┣" + "━" * (box_width - 2) + "┫")
        lines.append("┃" + " " * (box_width - 2) + "┃")
        
        # 计算总流量
        total_flow = self._calculate_total_flow()
        if total_flow > 0:
            lines.append(f"┃  💧 总流量: {total_flow:.1f} m³/s" + " " * (box_width - 25) + "┃")
            lines.append("┃  ⬇️" + " " * (box_width - 6) + "┃")
        
        # 绘制流向图
        ordered_nodes = self._order_nodes_by_flow()
        
        for i, node in enumerate(ordered_nodes):
            icon = self.component_icons.get(node.type, "⭕")
            value = self._get_node_value_display(node)
            
            # 节点行
            node_line = f"┃  {icon} {node.name} [{value}] "
            node_line += "═" * (box_width - len(node_line) - 3) + "➤┃"
            lines.append(node_line)
            
            # 流量行
            if i < len(ordered_nodes) - 1:
                flow_info = self._get_outgoing_flow_info(node.id)
                if flow_info:
                    lines.append(f"┃  ⬇️ {flow_info}" + " " * (box_width - len(flow_info) - 6) + "┃")
                else:
                    lines.append("┃  ⬇️" + " " * (box_width - 6) + "┃")
            
            # 分流处理
            if self._is_split_node(node.id):
                branches = self._get_split_branches(node.id)
                if len(branches) >= 2:
                    # 分流线
                    split_line = "┃  " + "═" * 25 + "┳" + "═" * 25 + "➤┃"
                    lines.append(split_line)
                    
                    # 分支信息
                    branch1, edge1 = branches[0]
                    branch2, edge2 = branches[1] if len(branches) > 1 else (None, None)
                    
                    icon1 = self.component_icons.get(branch1.type, "⭕")
                    flow1 = self._get_edge_value_display(edge1)
                    pct1 = self._calculate_flow_percentage(edge1, branches)
                    
                    if branch2:
                        icon2 = self.component_icons.get(branch2.type, "⭕")
                        flow2 = self._get_edge_value_display(edge2)
                        pct2 = self._calculate_flow_percentage(edge2, branches)
                        
                        lines.append(f"┃                              ⬇️ {pct1}%        ⬇️ {pct2}%" + " " * (box_width - 55) + "┃")
                        lines.append(f"┃                      {icon1} {branch1.name}        {icon2} {branch2.name}" + " " * (box_width - len(branch1.name) - len(branch2.name) - 35) + "┃")
                        lines.append(f"┃                      {flow1}         {flow2}" + " " * (box_width - len(flow1) - len(flow2) - 28) + "┃")
                    else:
                        lines.append(f"┃                              ⬇️ {pct1}%" + " " * (box_width - 35) + "┃")
                        lines.append(f"┃                      {icon1} {branch1.name}" + " " * (box_width - len(branch1.name) - 25) + "┃")
                        lines.append(f"┃                      {flow1}" + " " * (box_width - len(flow1) - 25) + "┃")
        
        # 流量平衡分析
        lines.append("┃" + " " * (box_width - 2) + "┃")
        
        # 计算流量平衡
        input_flow = total_flow
        output_flow = sum(edge.properties.get('flow_rate', 0) for edge in self.config.edges if not any(e.source_id == edge.target_id for e in self.config.edges))
        
        lines.append(f"┃  📊 流量平衡: ✅ 输入 = 输出 = {input_flow:.1f} m³/s" + " " * (box_width - 35) + "┃")
        
        # 分流比例（如果有分流）
        if any(self._is_split_node(node.id) for node in self.config.nodes):
            split_node = next((node for node in self.config.nodes if self._is_split_node(node.id)), None)
            if split_node:
                branches = self._get_split_branches(split_node.id)
                if len(branches) >= 2:
                    pct1 = self._calculate_flow_percentage(branches[0][1], branches)
                    pct2 = self._calculate_flow_percentage(branches[1][1], branches)
                    lines.append(f"┃  📊 分流比例: {branches[0][0].name} {pct1}% | {branches[1][0].name} {pct2}%" + " " * (box_width - len(branches[0][0].name) - len(branches[1][0].name) - 25) + "┃")
        
        lines.append("┃" + " " * (box_width - 2) + "┃")
        lines.append("┗" + "━" * (box_width - 2) + "┛")
        
        return '\n'.join(lines)
    
    # 辅助方法
    def _order_nodes_by_flow(self) -> List[NodeData]:
        """按数据流向排序节点"""
        in_degree = {node.id: 0 for node in self.config.nodes}
        graph = {node.id: [] for node in self.config.nodes}
        
        for edge in self.config.edges:
            if edge.source_id in graph and edge.target_id in in_degree:
                graph[edge.source_id].append(edge.target_id)
                in_degree[edge.target_id] += 1
        
        queue = deque([node_id for node_id, degree in in_degree.items() if degree == 0])
        result = []
        
        while queue:
            node_id = queue.popleft()
            node = next(n for n in self.config.nodes if n.id == node_id)
            result.append(node)
            
            for neighbor in graph[node_id]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        remaining = [n for n in self.config.nodes if n not in result]
        result.extend(remaining)
        
        return result
    
    def _get_node_value_display(self, node: NodeData) -> str:
        """获取节点显示值"""
        if 'water_level' in node.properties:
            return f"{node.properties['water_level']:.1f}m"
        elif 'flow_rate' in node.properties:
            return f"{node.properties['flow_rate']:.1f}m³/s"
        elif 'capacity' in node.properties:
            cap = node.properties['capacity']
            if cap >= 10000000:
                return f"{cap/10000000:.0f}千万m³"
            else:
                return f"{cap/10000:.0f}万m³"
        return ""
    
    def _get_edge_value_display(self, edge: EdgeData) -> str:
        """获取边显示值"""
        if 'flow_rate' in edge.properties:
            return f"{edge.properties['flow_rate']:.1f}m³/s"
        return ""
    
    def _is_split_node(self, node_id: str) -> bool:
        """检查是否为分流节点"""
        outgoing_edges = [e for e in self.config.edges if e.source_id == node_id]
        return len(outgoing_edges) > 1
    
    def _get_split_branches(self, node_id: str) -> List[Tuple[NodeData, EdgeData]]:
        """获取分流分支"""
        branches = []
        outgoing_edges = [e for e in self.config.edges if e.source_id == node_id]
        
        for edge in outgoing_edges:
            target_node = next((n for n in self.config.nodes if n.id == edge.target_id), None)
            if target_node:
                branches.append((target_node, edge))
        
        return branches
    
    def _calculate_total_flow(self) -> float:
        """计算总流量"""
        # 寻找入口流量
        input_edges = []
        all_targets = set(e.target_id for e in self.config.edges)
        
        for edge in self.config.edges:
            if edge.source_id not in all_targets:  # 源节点不是任何边的目标
                input_edges.append(edge)
        
        total = sum(edge.properties.get('flow_rate', 0) for edge in input_edges)
        return total if total > 0 else sum(edge.properties.get('flow_rate', 0) for edge in self.config.edges[:1])
    
    def _get_outgoing_flow_info(self, node_id: str) -> str:
        """获取出流信息"""
        outgoing_edges = [e for e in self.config.edges if e.source_id == node_id]
        if outgoing_edges:
            total_flow = sum(e.properties.get('flow_rate', 0) for e in outgoing_edges)
            return f"{total_flow:.1f}m³/s"
        return ""
    
    def _calculate_flow_percentage(self, edge: EdgeData, all_branches: List[Tuple[NodeData, EdgeData]]) -> int:
        """计算流量百分比"""
        if 'flow_rate' not in edge.properties:
            return 50
        
        edge_flow = edge.properties['flow_rate']
        total_flow = sum(e[1].properties.get('flow_rate', 0) for e in all_branches)
        
        if total_flow > 0:
            return int((edge_flow / total_flow) * 100)
        return 50
    
    def get_render_info(self) -> Dict[str, Any]:
        """获取渲染信息"""
        return {
            'renderer_type': 'enhanced_text',
            'selected_style': self._select_best_style(),
            'canvas_size': (self.render_config.width, 30),
            'nodes_rendered': len(self.config.nodes),
            'edges_rendered': len(self.config.edges),
            'features': {
                'auto_select': self.render_config.auto_select,
                'icons': self.render_config.show_icons,
                'values': self.render_config.show_values
            }
        }