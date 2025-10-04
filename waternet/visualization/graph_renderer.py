#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图形化拓扑图渲染器 (matplotlib后端)

提供专业的图形化拓扑图生成，支持自动布局和美观的可视化效果。
作为文本渲染的补充，提供更直观的图形化展示。

Created by: Qoder AI Assistant
Date: 2025-10-04
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import math
import random

try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    from matplotlib.patches import FancyBboxPatch, ConnectionPatch
    import matplotlib.font_manager as fm
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

try:
    from .topology_generator import TopologyRenderer, TopologyConfig, NodeData, EdgeData, ComponentType
except ImportError:
    from topology_generator import TopologyRenderer, TopologyConfig, NodeData, EdgeData, ComponentType

logger = logging.getLogger(__name__)


@dataclass 
class GraphRenderConfig:
    """图形渲染配置"""
    figure_size: Tuple[float, float] = (12, 8)
    dpi: int = 300
    font_size: int = 2  # 大幅缩小到极小字体（2像素）
    node_size: float = 400  # 进一步缩小节点大小
    edge_width: float = 2.0
    node_spacing: float = 2.0
    edge_curve: float = 0.1
    show_labels: bool = True
    show_icons: bool = True
    show_values: bool = True
    auto_layout: bool = True
    background_color: str = "white"
    save_format: str = "png"


class GraphRenderer(TopologyRenderer):
    """图形化拓扑图渲染器"""
    
    def __init__(self, config: TopologyConfig):
        super().__init__(config)
        self.render_config = self._parse_render_config()
        self.fig = None
        self.ax = None
        self.node_positions = {}
        
        # 组件颜色映射
        self.component_colors = {
            ComponentType.RESERVOIR: "#4A90E2",    # 蓝色
            ComponentType.STATION: "#F5A623",     # 橙色
            ComponentType.JUNCTION: "#BD10E0",    # 紫色
            ComponentType.PIPE: "#50E3C2",        # 青色
            ComponentType.PUMP: "#F5A623",        # 橙色
            ComponentType.VALVE: "#7ED321",       # 绿色
            ComponentType.TURBINE: "#9013FE"      # 深紫色
        }
        
        # 组件形状映射
        self.component_shapes = {
            ComponentType.RESERVOIR: "ellipse",
            ComponentType.STATION: "square",
            ComponentType.JUNCTION: "diamond", 
            ComponentType.PIPE: "rectangle",
            ComponentType.PUMP: "circle",
            ComponentType.VALVE: "hexagon",
            ComponentType.TURBINE: "circle"
        }
        
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
    
    def _parse_render_config(self) -> GraphRenderConfig:
        """解析图形渲染配置"""
        render_cfg = self.config.render_config.get('matplotlib', {})
        
        return GraphRenderConfig(
            figure_size=tuple(render_cfg.get('figure_size', [12, 8])),
            dpi=render_cfg.get('dpi', 300),
            font_size=render_cfg.get('font_size', 10),
            node_size=render_cfg.get('node_size', 1000),
            edge_width=render_cfg.get('edge_width', 2.0),
            node_spacing=render_cfg.get('node_spacing', 2.0),
            show_labels=render_cfg.get('show_labels', True),
            show_icons=render_cfg.get('show_icons', True),
            show_values=render_cfg.get('show_values', True),
            auto_layout=render_cfg.get('auto_layout', True),
            save_format=render_cfg.get('save_format', 'png')
        )
    
    def can_render(self) -> bool:
        """检查是否支持图形渲染"""
        if not MATPLOTLIB_AVAILABLE:
            self.logger.warning("matplotlib不可用，无法进行图形渲染")
            return False
        
        try:
            # 测试matplotlib基本功能
            fig, ax = plt.subplots(figsize=(1, 1))
            plt.close(fig)
            return True
        except Exception as e:
            self.logger.warning(f"matplotlib测试失败: {e}")
            return False
    
    def render(self, output_path: Optional[str] = None) -> bool:
        """渲染图形化拓扑图"""
        if not MATPLOTLIB_AVAILABLE:
            return False
        
        try:
            # 设置中文字体
            self._setup_chinese_font()
            
            # 创建图形
            self.fig, self.ax = plt.subplots(figsize=self.render_config.figure_size, 
                                           dpi=self.render_config.dpi)
            
            # 计算布局
            if self.render_config.auto_layout:
                self._auto_layout()
            else:
                self._manual_layout()
            
            # 绘制边
            self._draw_edges()
            
            # 绘制节点
            self._draw_nodes()
            
            # 设置图形属性
            self._setup_plot()
            
            # 添加标题和图例
            self._add_title_and_legend()
            
            # 保存或显示
            if output_path:
                self.fig.savefig(output_path, format=self.render_config.save_format,
                               dpi=self.render_config.dpi, bbox_inches='tight', 
                               pad_inches=0.2)  # 减少内边距
                self.logger.info(f"图形拓扑图已保存到: {output_path}")
                plt.close(self.fig)
            else:
                # 调整布局以适应图例
                plt.tight_layout()
                plt.subplots_adjust(right=0.8)  # 为右侧图例留出空间
                plt.show()
            
            return True
            
        except Exception as e:
            self.logger.error(f"图形渲染失败: {e}")
            if self.fig:
                plt.close(self.fig)
            return False
    
    def _setup_chinese_font(self):
        """设置中文字体"""
        try:
            # 尝试设置中文字体
            chinese_fonts = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
            
            for font_name in chinese_fonts:
                try:
                    plt.rcParams['font.sans-serif'] = [font_name]
                    plt.rcParams['axes.unicode_minus'] = False
                    break
                except:
                    continue
            
        except Exception as e:
            self.logger.warning(f"中文字体设置失败: {e}")
    
    def _auto_layout(self):
        """自动布局算法"""
        if not self.config.nodes:
            return
        
        # 检查布局类型
        layout_type = self.config.render_config.get('graph', {}).get('layout', 'spring')
        
        if layout_type == 'hierarchical':
            self._hierarchical_layout()
        elif layout_type == 'horizontal':
            self._horizontal_layout()
        elif layout_type == 'circular':
            self._circular_layout()
        else:
            self._spring_layout()
    
    def _hierarchical_layout(self):
        """层次结构布局 - 避免节点叠加"""
        if not self.config.nodes:
            return
        
        # 构建层次结构
        layers = self._build_hierarchy()
        
        # 进一步增大间距确保不重叠
        layer_spacing = 12.0  # 大幅增加层间距
        min_node_spacing = 8.0  # 大幅增加最小节点间距
        
        for layer_idx, layer_nodes in enumerate(layers):
            y_pos = -layer_idx * layer_spacing
            
            if len(layer_nodes) == 1:
                # 单个节点居中
                x_pos = 0.0
                self.node_positions[layer_nodes[0]] = (x_pos, y_pos)
            else:
                # 计算合适的节点间距
                node_spacing = max(min_node_spacing, len(layer_nodes) * 1.8)  # 大幅增大间距系数
                total_width = (len(layer_nodes) - 1) * node_spacing
                start_x = -total_width / 2
                
                for i, node_id in enumerate(layer_nodes):
                    x_pos = start_x + i * node_spacing
                    self.node_positions[node_id] = (x_pos, y_pos)
    
    def _horizontal_layout(self):
        """水平布局"""
        if not self.config.nodes:
            return
        
        # 根据节点数量动态调整间距
        n_nodes = len(self.config.nodes)
        min_spacing = 10.0  # 大幅增大最小间距
        node_spacing = max(min_spacing, n_nodes * 1.8)  # 大幅增大间距系数
        
        total_width = (n_nodes - 1) * node_spacing
        start_x = -total_width / 2
        
        for i, node in enumerate(self.config.nodes):
            x_pos = start_x + i * node_spacing
            y_pos = 0.0
            self.node_positions[node.id] = (x_pos, y_pos)
    
    def _circular_layout(self):
        """环形布局"""
        if not self.config.nodes:
            return
        
        n_nodes = len(self.config.nodes)
        if n_nodes == 1:
            self.node_positions[self.config.nodes[0].id] = (0, 0)
            return
        
        # 计算半径确保节点不重叠
        # 根据圆周需要的最小间距计算半径
        min_arc_length = 6.0  # 大幅增大每个节点需要的最小弧长
        required_circumference = n_nodes * min_arc_length
        min_radius = required_circumference / (2 * math.pi)
        
        # 确保半径不小于基础值
        radius = max(12.0, min_radius)  # 大幅增大最小半径
        
        for i, node in enumerate(self.config.nodes):
            angle = 2 * math.pi * i / n_nodes
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
            self.node_positions[node.id] = (x, y)
    
    def _spring_layout(self):
        """弹簧布局算法"""
        if not self.config.nodes:
            return
        
        n_nodes = len(self.config.nodes)
        
        if n_nodes == 1:
            self.node_positions[self.config.nodes[0].id] = (0, 0)
            return
        
        # 初始化位置（网格分布，确保足够间距）
        grid_size = math.ceil(math.sqrt(n_nodes))
        spacing = 15.0  # 大幅增大初始间距
        
        for i, node in enumerate(self.config.nodes):
            row = i // grid_size
            col = i % grid_size
            x = (col - grid_size/2) * spacing
            y = (row - grid_size/2) * spacing
            self.node_positions[node.id] = (x, y)
        
        # 迭代优化位置
        for iteration in range(150):  # 增加迭代次数
            forces = {}
            
            # 初始化力
            for node in self.config.nodes:
                forces[node.id] = [0.0, 0.0]
            
            # 计算强化排斥力
            for i, node1 in enumerate(self.config.nodes):
                for j, node2 in enumerate(self.config.nodes):
                    if i >= j:
                        continue
                    
                    pos1 = self.node_positions[node1.id]
                    pos2 = self.node_positions[node2.id]
                    
                    dx = pos1[0] - pos2[0]
                    dy = pos1[1] - pos2[1]
                    distance = math.sqrt(dx*dx + dy*dy)
                    
                    # 强制最小距离
                    min_distance = 7.0  # 大幅增大最小距离
                    if distance < min_distance:
                        # 如果距离太近，强制分开
                        if distance < 0.1:
                            distance = 0.1
                            dx = (random.random() - 0.5) * 0.2
                            dy = (random.random() - 0.5) * 0.2
                        
                        force = 20.0 / (distance * distance)  # 增强排斥力
                    else:
                        force = 8.0 / (distance * distance)
                    
                    fx = force * dx / distance
                    fy = force * dy / distance
                    
                    forces[node1.id][0] += fx
                    forces[node1.id][1] += fy
                    forces[node2.id][0] -= fx
                    forces[node2.id][1] -= fy
            
            # 计算适度的吸引力（只对连接的节点）
            for edge in self.config.edges:
                if edge.source_id in self.node_positions and edge.target_id in self.node_positions:
                    pos1 = self.node_positions[edge.source_id]
                    pos2 = self.node_positions[edge.target_id]
                    
                    dx = pos2[0] - pos1[0]
                    dy = pos2[1] - pos1[1]
                    distance = math.sqrt(dx*dx + dy*dy)
                    
                    if distance > 0:
                        # 适度吸引力，但不要太强
                        optimal_distance = 6.0
                        force = (distance - optimal_distance) * 0.02
                        fx = force * dx / distance
                        fy = force * dy / distance
                        
                        forces[edge.source_id][0] += fx
                        forces[edge.source_id][1] += fy
                        forces[edge.target_id][0] -= fx
                        forces[edge.target_id][1] -= fy
            
            # 应用力并更新位置
            max_displacement = 0
            for node in self.config.nodes:
                fx, fy = forces[node.id]
                
                # 限制最大步长
                displacement = math.sqrt(fx*fx + fy*fy)
                max_step = 0.5  # 增大允许的步长
                if displacement > max_step:
                    fx = fx * max_step / displacement
                    fy = fy * max_step / displacement
                    displacement = max_step
                
                max_displacement = max(max_displacement, displacement)
                
                old_pos = self.node_positions[node.id]
                self.node_positions[node.id] = (old_pos[0] + fx, old_pos[1] + fy)
            
            # 收敛检查
            if max_displacement < 0.003:
                break
        
        # 最后检查并调整重叠节点
        self._fix_overlapping_nodes()
    
    def _calculate_smart_text_positions(self, node: NodeData, node_pos: Tuple[float, float], node_radius: float) -> Dict[str, Tuple[float, float]]:
        """智能计算文字位置，避免与连接线和其他节点重叠"""
        base_offset = node_radius + 1.0  # 基础偏移距离
        
        # 获取与该节点相连的边
        connected_edges = [edge for edge in self.config.edges 
                          if edge.source_id == node.id or edge.target_id == node.id]
        
        # 计算连接线的方向角度
        blocked_angles = []
        for edge in connected_edges:
            if edge.source_id == node.id and edge.target_id in self.node_positions:
                target_pos = self.node_positions[edge.target_id]
                dx = target_pos[0] - node_pos[0]
                dy = target_pos[1] - node_pos[1]
                if dx != 0 or dy != 0:
                    angle = math.atan2(dy, dx)
                    blocked_angles.append(angle)
            elif edge.target_id == node.id and edge.source_id in self.node_positions:
                source_pos = self.node_positions[edge.source_id]
                dx = source_pos[0] - node_pos[0]
                dy = source_pos[1] - node_pos[1]
                if dx != 0 or dy != 0:
                    angle = math.atan2(dy, dx)
                    blocked_angles.append(angle)
        
        # 计算其他节点的方向角度
        nearby_angles = []
        for other_node in self.config.nodes:
            if other_node.id != node.id and other_node.id in self.node_positions:
                other_pos = self.node_positions[other_node.id]
                dx = other_pos[0] - node_pos[0]
                dy = other_pos[1] - node_pos[1]
                distance = math.sqrt(dx*dx + dy*dy)
                if distance < 3.0 and distance > 0:  # 距离很近的节点
                    angle = math.atan2(dy, dx)
                    nearby_angles.append(angle)
        
        # 定义可选的文字位置方向（八个方向）
        candidate_directions = [
            (0, 1),      # 上
            (0.707, 0.707),   # 右上
            (1, 0),      # 右
            (0.707, -0.707),  # 右下
            (0, -1),     # 下
            (-0.707, -0.707), # 左下
            (-1, 0),     # 左
            (-0.707, 0.707)   # 左上
        ]
        
        # 评估每个方向的合适性
        direction_scores = []
        for dx, dy in candidate_directions:
            direction_angle = math.atan2(dy, dx)
            
            # 计算与被阻塞角度的最小差异
            min_blocked_diff = float('inf')
            for blocked_angle in blocked_angles:
                diff = abs(direction_angle - blocked_angle)
                diff = min(diff, 2*math.pi - diff)  # 处理循环角度
                min_blocked_diff = min(min_blocked_diff, diff)
            
            # 计算与附近节点的最小差异
            min_nearby_diff = float('inf')
            for nearby_angle in nearby_angles:
                diff = abs(direction_angle - nearby_angle)
                diff = min(diff, 2*math.pi - diff)
                min_nearby_diff = min(min_nearby_diff, diff)
            
            # 综合评分：距离被阻塞方向越远越好
            score = min_blocked_diff * 2 + min_nearby_diff
            direction_scores.append((score, dx, dy))
        
        # 排序并选择最佳方向
        direction_scores.sort(reverse=True)  # 分数越高越好
        
        # 选择汉字和数字的位置（使用不同的最佳方向）
        chinese_direction = direction_scores[0]  # 最佳方向
        number_direction = direction_scores[1] if len(direction_scores) > 1 else direction_scores[0]  # 次佳方向
        
        chinese_pos = (
            node_pos[0] + chinese_direction[1] * base_offset,
            node_pos[1] + chinese_direction[2] * base_offset
        )
        
        number_pos = (
            node_pos[0] + number_direction[1] * base_offset,
            node_pos[1] + number_direction[2] * base_offset
        )
        
        return {
            'chinese': chinese_pos,
            'number': number_pos
        }
    
    def _calculate_smart_edge_label_position(self, source_pos: Tuple[float, float], 
                                           target_pos: Tuple[float, float], 
                                           edge: EdgeData) -> Tuple[float, float]:
        """智能计算边标签位置，避免与其他元素重叠"""
        # 基础中点位置
        mid_x = (source_pos[0] + target_pos[0]) / 2
        mid_y = (source_pos[1] + target_pos[1]) / 2
        
        # 计算线条方向
        dx = target_pos[0] - source_pos[0]
        dy = target_pos[1] - source_pos[1]
        length = math.sqrt(dx*dx + dy*dy)
        
        if length == 0:
            return (mid_x, mid_y)
        
        # 单位化线条方向向量
        line_dx = dx / length
        line_dy = dy / length
        
        # 计算垂直方向向量
        perp_dx = -line_dy
        perp_dy = line_dx
        
        # 检查不同偏移位置的可行性
        offset_distances = [0.6, -0.6, 1.0, -1.0]  # 多个可选偏移距离
        best_position = (mid_x, mid_y)
        best_score = 0
        
        for offset_dist in offset_distances:
            # 计算候选位置
            candidate_x = mid_x + perp_dx * offset_dist
            candidate_y = mid_y + perp_dy * offset_dist
            
            # 评估这个位置的好坐程度
            score = self._evaluate_label_position(candidate_x, candidate_y)
            
            if score > best_score:
                best_score = score
                best_position = (candidate_x, candidate_y)
        
        return best_position
    
    def _evaluate_label_position(self, x: float, y: float) -> float:
        """评估标签位置的质量分数"""
        score = 100.0  # 基础分数
        
        # 检查与所有节点的距离
        for node_id, node_pos in self.node_positions.items():
            distance = math.sqrt((x - node_pos[0])**2 + (y - node_pos[1])**2)
            if distance < 1.5:  # 太近节点
                score -= (1.5 - distance) * 50  # 大幅减分
        
        # 检查与其他边的距离（简化检查）
        for edge in self.config.edges:
            if (edge.source_id in self.node_positions and edge.target_id in self.node_positions):
                edge_mid_x = (self.node_positions[edge.source_id][0] + self.node_positions[edge.target_id][0]) / 2
                edge_mid_y = (self.node_positions[edge.source_id][1] + self.node_positions[edge.target_id][1]) / 2
                distance = math.sqrt((x - edge_mid_x)**2 + (y - edge_mid_y)**2)
                if distance < 0.8:  # 太近其他边的中点
                    score -= (0.8 - distance) * 30
        
        return score
    
    def _fix_overlapping_nodes(self):
        """修复重叠节点"""
        min_distance = 6.0  # 大幅增大最小距离
        max_attempts = 20  # 增加尝试次数
        
        for attempt in range(max_attempts):
            overlaps_fixed = 0
            
            for i, node1 in enumerate(self.config.nodes):
                for j, node2 in enumerate(self.config.nodes):
                    if i >= j:
                        continue
                    
                    pos1 = self.node_positions[node1.id]
                    pos2 = self.node_positions[node2.id]
                    
                    dx = pos1[0] - pos2[0]
                    dy = pos1[1] - pos2[1]
                    distance = math.sqrt(dx*dx + dy*dy)
                    
                    if distance < min_distance:
                        # 分开重叠的节点
                        if distance < 0.1:
                            # 如果完全重叠，随机分开
                            angle = random.random() * 2 * math.pi
                            dx = math.cos(angle) * min_distance
                            dy = math.sin(angle) * min_distance
                        else:
                            # 沿着连线方向分开
                            scale = min_distance / distance
                            dx *= scale
                            dy *= scale
                        
                        # 移动两个节点
                        mid_x = (pos1[0] + pos2[0]) / 2
                        mid_y = (pos1[1] + pos2[1]) / 2
                        
                        self.node_positions[node1.id] = (mid_x + dx/2, mid_y + dy/2)
                        self.node_positions[node2.id] = (mid_x - dx/2, mid_y - dy/2)
                        
                        overlaps_fixed += 1
            
            # 如果没有重叠了，退出
            if overlaps_fixed == 0:
                break
    
    def _build_hierarchy(self):
        """构建层次结构"""
        # 构建邻接表
        adjacency = {node.id: [] for node in self.config.nodes}
        for edge in self.config.edges:
            if edge.source_id in adjacency:
                adjacency[edge.source_id].append(edge.target_id)
        
        # 寻找根节点（没有入度的节点）
        has_incoming = set()
        for node_id, neighbors in adjacency.items():
            for neighbor in neighbors:
                has_incoming.add(neighbor)
        
        roots = [node.id for node in self.config.nodes if node.id not in has_incoming]
        
        if not roots:
            # 如果没有明显的根节点，选择第一个
            roots = [self.config.nodes[0].id]
        
        # BFS构建层次
        layers = []
        visited = set()
        current_layer = roots
        
        while current_layer:
            layers.append(current_layer[:])
            visited.update(current_layer)
            
            next_layer = []
            for node_id in current_layer:
                for neighbor in adjacency.get(node_id, []):
                    if neighbor not in visited and neighbor not in next_layer:
                        next_layer.append(neighbor)
            
            current_layer = next_layer
        
        # 添加未访问的节点
        unvisited = [node.id for node in self.config.nodes if node.id not in visited]
        if unvisited:
            layers.append(unvisited)
        
        return layers
    
    def _manual_layout(self):
        """手动布局（使用配置中的位置）"""
        for node in self.config.nodes:
            self.node_positions[node.id] = node.position
    
    def _draw_edges(self):
        """绘制边"""
        for edge in self.config.edges:
            if edge.source_id not in self.node_positions or edge.target_id not in self.node_positions:
                continue
            
            source_pos = self.node_positions[edge.source_id]
            target_pos = self.node_positions[edge.target_id]
            
            # 绘制连接线
            if edge.edge_type == "flow":
                self._draw_flow_edge(source_pos, target_pos, edge)
            else:
                self._draw_simple_edge(source_pos, target_pos, edge)
    
    def _draw_flow_edge(self, source_pos: Tuple[float, float], target_pos: Tuple[float, float], edge: EdgeData):
        """绘制流量边"""
        # 计算箭头
        dx = target_pos[0] - source_pos[0]
        dy = target_pos[1] - source_pos[1]
        
        # 绘制箭头（大幅缩小箭头）
        arrow = patches.FancyArrowPatch(
            source_pos, target_pos,
            arrowstyle='->', 
            mutation_scale=8,  # 大幅缩小箭头大小从20→8
            linewidth=1.0,  # 缩小线宽
            color='#333333',
            alpha=0.8,
            connectionstyle="arc3,rad=0.05"  # 减小弧度
        )
        self.ax.add_patch(arrow)
        
        # 添加标签（智能定位模式）
        if self.render_config.show_labels:
            # 计算智能标签位置
            label_pos = self._calculate_smart_edge_label_position(source_pos, target_pos, edge)
            
            # 区分汉字和数字显示
            if self.render_config.show_values and 'flow_rate' in edge.properties:
                # 数字使用的更大字体和红色
                label_text = f"{edge.properties['flow_rate']:.0f}"
                self.ax.text(label_pos[0], label_pos[1], label_text, 
                            ha='center', va='center',
                            fontsize=4,  # 数字字体翻倍
                            fontweight='bold',
                            color='red',  # 数字使用红色
                            bbox=dict(boxstyle="round,pad=0.15", facecolor='white', alpha=0.95, 
                                    edgecolor='red', linewidth=0.5))
            else:
                # 汉字使用的更大字体和黑色
                label_text = edge.name[:2] if len(edge.name) > 2 else edge.name
                self.ax.text(label_pos[0], label_pos[1], label_text, 
                            ha='center', va='center',
                            fontsize=3,  # 汉字字体放大3倍（从1→3像素）
                            fontweight='normal',
                            color='black',
                            bbox=dict(boxstyle="round,pad=0.15", facecolor='white', alpha=0.95, 
                                    edgecolor='gray', linewidth=0.5))
    
    def _draw_simple_edge(self, source_pos: Tuple[float, float], target_pos: Tuple[float, float], edge: EdgeData):
        """绘制简单边"""
        self.ax.plot([source_pos[0], target_pos[0]], [source_pos[1], target_pos[1]], 
                    linewidth=self.render_config.edge_width, color='#666666', alpha=0.7)
    
    def _draw_nodes(self):
        """绘制节点"""
        for node in self.config.nodes:
            if node.id not in self.node_positions:
                continue
            
            pos = self.node_positions[node.id]
            color = self.component_colors.get(node.type, '#CCCCCC')
            shape = self.component_shapes.get(node.type, 'circle')
            
            # 绘制节点形状
            node_radius = 0.4  # 大幅缩小节点显示大小
            if shape == 'circle':
                circle = patches.Circle(pos, node_radius, facecolor=color, edgecolor='black', linewidth=0.8, alpha=0.9)
                self.ax.add_patch(circle)
            elif shape == 'square':
                square = patches.Rectangle((pos[0]-node_radius, pos[1]-node_radius), node_radius*2, node_radius*2, 
                                         facecolor=color, edgecolor='black', linewidth=0.8, alpha=0.9)
                self.ax.add_patch(square)
            elif shape == 'diamond':
                diamond = patches.RegularPolygon(pos, 4, radius=node_radius*1.1, orientation=math.pi/4,
                                               facecolor=color, edgecolor='black', linewidth=0.8, alpha=0.9)
                self.ax.add_patch(diamond)
            elif shape == 'ellipse':
                ellipse = patches.Ellipse(pos, node_radius*2.2, node_radius*1.4, facecolor=color, edgecolor='black', linewidth=0.8, alpha=0.9)
                self.ax.add_patch(ellipse)
            elif shape == 'hexagon':
                hexagon = patches.RegularPolygon(pos, 6, radius=node_radius*1.0,
                                               facecolor=color, edgecolor='black', linewidth=0.8, alpha=0.9)
                self.ax.add_patch(hexagon)
            else:  # rectangle
                rect = patches.Rectangle((pos[0]-node_radius*1.3, pos[1]-node_radius*0.5), node_radius*2.6, node_radius*1.0,
                                       facecolor=color, edgecolor='black', linewidth=0.8, alpha=0.9)
                self.ax.add_patch(rect)
            
            # 添加标签（只显示最关键信息）
            if self.render_config.show_labels:
                # 极简显示模式
                short_name = node.name
                if len(short_name) > 3:
                    short_name = short_name[:2] + "."
                
                # 只显示最重要的数值
                value_text = ""
                if self.render_config.show_values and node.properties:
                    if 'flow_rate' in node.properties:
                        value_text = f"{node.properties['flow_rate']:.0f}"
                    elif 'water_level' in node.properties:
                        value_text = f"{node.properties['water_level']:.0f}m"
                
                # 分别绘制汉字和数字，使用不同字体大小
                chinese_fontsize = 3  # 汉字字体放大3倍（从1→3像素）
                number_fontsize = 4   # 数字字体翻倍（从2→4）
                
                # 智能计算文字位置，避免与连接线和其他节点重叠
                text_positions = self._calculate_smart_text_positions(node, pos, node_radius)
                
                # 绘制汉字（智能定位）
                if short_name:
                    self.ax.text(text_positions['chinese'][0], text_positions['chinese'][1], short_name,
                               ha='center', va='center',
                               fontsize=chinese_fontsize,
                               fontweight='normal',
                               color='black',
                               bbox=dict(boxstyle="round,pad=0.1", facecolor='white', alpha=0.9, edgecolor='gray', linewidth=0.5))
                
                # 绘制数字（智能定位）
                if value_text:
                    self.ax.text(text_positions['number'][0], text_positions['number'][1], value_text,
                               ha='center', va='center',
                               fontsize=number_fontsize,
                               fontweight='bold',
                               color='red',
                               bbox=dict(boxstyle="round,pad=0.1", facecolor='white', alpha=0.9, edgecolor='red', linewidth=0.5))
    
    def _get_node_value_text(self, node: NodeData) -> str:
        """获取节点数值文本"""
        if not node.properties:
            return ""
        
        if 'flow_rate' in node.properties:
            return f"{node.properties['flow_rate']:.1f} m³/s"
        elif 'water_level' in node.properties:
            return f"{node.properties['water_level']:.1f} m"
        elif 'power' in node.properties:
            return f"{node.properties['power']:.0f} kW"
        
        return ""
    
    def _is_dark_color(self, color: str) -> bool:
        """判断颜色是否为深色"""
        # 简单的亮度判断
        if color.startswith('#'):
            hex_color = color[1:]
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            brightness = (r * 299 + g * 587 + b * 114) / 1000
            return brightness < 128
        return False
    
    def _setup_plot(self):
        """设置图形属性"""
        # 设置坐标轴
        self.ax.set_aspect('equal')
        
        # 计算边界（增加更大的边距）
        if self.node_positions:
            x_coords = [pos[0] for pos in self.node_positions.values()]
            y_coords = [pos[1] for pos in self.node_positions.values()]
            
            margin = 4.0  # 增大边距
            x_min, x_max = min(x_coords) - margin, max(x_coords) + margin
            y_min, y_max = min(y_coords) - margin, max(y_coords) + margin
            
            self.ax.set_xlim(x_min, x_max)
            self.ax.set_ylim(y_min, y_max)
        
        # 隐藏坐标轴
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        
        # 设置背景
        self.ax.set_facecolor(self.render_config.background_color)
        
        # 移除边框
        for spine in self.ax.spines.values():
            spine.set_visible(False)
    
    def _add_title_and_legend(self):
        """添加标题和图例"""
        # 添加标题
        self.fig.suptitle(self.config.title, fontsize=max(6, self.render_config.font_size + 4), fontweight='bold')
        
        # 添加图例
        legend_elements = []
        used_types = set(node.type for node in self.config.nodes)
        
        for comp_type in used_types:
            color = self.component_colors.get(comp_type, '#CCCCCC')
            icon = self.component_icons.get(comp_type, "⭕")
            type_name = self._get_type_name(comp_type)
            
            legend_elements.append(
                patches.Patch(color=color, label=f'{icon} {type_name}')
            )
        
        if legend_elements:
            # 将图例移到右上角边缘外部
            legend = self.ax.legend(handles=legend_elements, 
                                  loc='upper left', 
                                  bbox_to_anchor=(1.02, 1.0),  # 移到右侧边缘外
                                  fontsize=4,  # 图例字体放大2倍（从2→4）
                                  frameon=True,
                                  fancybox=True,
                                  shadow=True)
            legend.get_frame().set_alpha(0.9)
    
    def _get_type_name(self, comp_type: ComponentType) -> str:
        """获取组件类型名称"""
        type_names = {
            ComponentType.RESERVOIR: "水库",
            ComponentType.STATION: "枢纽站",
            ComponentType.JUNCTION: "连接点",
            ComponentType.PIPE: "管道",
            ComponentType.PUMP: "泵站",
            ComponentType.VALVE: "阀门",
            ComponentType.TURBINE: "水轮机"
        }
        return type_names.get(comp_type, comp_type.value)
    
    def get_render_info(self) -> Dict[str, Any]:
        """获取渲染信息"""
        return {
            'renderer_type': 'graph_matplotlib',
            'matplotlib_available': MATPLOTLIB_AVAILABLE,
            'figure_size': self.render_config.figure_size,
            'dpi': self.render_config.dpi,
            'nodes_rendered': len(self.node_positions),
            'edges_rendered': len([e for e in self.config.edges 
                                 if e.source_id in self.node_positions 
                                 and e.target_id in self.node_positions]),
            'auto_layout': self.render_config.auto_layout,
            'features': {
                'labels': self.render_config.show_labels,
                'icons': self.render_config.show_icons,
                'values': self.render_config.show_values
            }
        }


if __name__ == "__main__":
    # 测试代码
    from topology_generator import TopologyConfig, NodeData, EdgeData, ComponentType
    
    # 创建测试配置
    test_config = TopologyConfig(
        title="图形渲染器测试",
        nodes=[
            NodeData("r1", "水库", ComponentType.RESERVOIR, (0, 2), {"water_level": 100.0}),
            NodeData("s1", "泵站", ComponentType.PUMP, (2, 2), {"flow_rate": 50.0}),
            NodeData("j1", "分流点", ComponentType.JUNCTION, (4, 2), {"type": "split"}),
            NodeData("p1", "管道1", ComponentType.PIPE, (6, 3), {"diameter": 1.0}),
            NodeData("p2", "管道2", ComponentType.PIPE, (6, 1), {"diameter": 0.8}),
            NodeData("r2", "目标", ComponentType.RESERVOIR, (8, 2), {"water_level": 95.0})
        ],
        edges=[
            EdgeData("e1", "进水", "r1", "s1", properties={"flow_rate": 50.0}),
            EdgeData("e2", "提升", "s1", "j1", properties={"flow_rate": 50.0}),
            EdgeData("e3", "分流1", "j1", "p1", properties={"flow_rate": 30.0}),
            EdgeData("e4", "分流2", "j1", "p2", properties={"flow_rate": 20.0}),
            EdgeData("e5", "汇流1", "p1", "r2", properties={"flow_rate": 30.0}),
            EdgeData("e6", "汇流2", "p2", "r2", properties={"flow_rate": 20.0})
        ]
    )
    
    renderer = GraphRenderer(test_config)
    if renderer.can_render():
        renderer.render()
        print("图形渲染器测试完成！")
    else:
        print("图形渲染器环境检查失败！")