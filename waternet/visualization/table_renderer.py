#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
表格形式的系统信息渲染器

提供可靠的表格形式展示，作为图形化渲染失败时的备选方案。
支持简洁清晰的文本表格和结构化信息展示。

Created by: Qoder AI Assistant
Date: 2025-10-04
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import sys
from collections import defaultdict

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.columns import Columns
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

try:
    from .topology_generator import TopologyRenderer, TopologyConfig, NodeData, EdgeData, ComponentType
except ImportError:
    from topology_generator import TopologyRenderer, TopologyConfig, NodeData, EdgeData, ComponentType

logger = logging.getLogger(__name__)


@dataclass
class TableRenderConfig:
    """表格渲染配置"""
    format: str = "rich"  # "rich", "plain", "markdown"
    show_summary: bool = True
    group_by_type: bool = True
    show_properties: bool = True
    show_connections: bool = True
    max_width: int = 120
    encoding: str = "utf-8"


class TableRenderer(TopologyRenderer):
    """表格形式渲染器"""
    
    def __init__(self, config: TopologyConfig):
        super().__init__(config)
        self.render_config = self._parse_render_config()
        self.console = None
        if RICH_AVAILABLE:
            self.console = Console(width=self.render_config.max_width)
    
    def _parse_render_config(self) -> TableRenderConfig:
        """解析表格渲染配置"""
        render_cfg = self.config.render_config.get('table', {})
        
        return TableRenderConfig(
            format=render_cfg.get('format', 'rich' if RICH_AVAILABLE else 'plain'),
            show_summary=render_cfg.get('show_summary', True),
            group_by_type=render_cfg.get('group_by_type', True),
            show_properties=render_cfg.get('show_properties', True),
            show_connections=render_cfg.get('show_connections', True),
            max_width=render_cfg.get('max_width', 120),
            encoding=render_cfg.get('encoding', 'utf-8')
        )
    
    def can_render(self) -> bool:
        """检查是否支持表格渲染"""
        try:
            # 表格渲染基本总是可用的
            test_text = "测试中文显示"
            test_text.encode(self.render_config.encoding)
            return True
        except Exception as e:
            self.logger.warning(f"表格渲染环境检查失败: {e}")
            return False
    
    def render(self, output_path: Optional[str] = None) -> bool:
        """渲染表格形式的拓扑图"""
        try:
            if self.render_config.format == "rich" and RICH_AVAILABLE:
                output_text = self._render_rich_format()
            elif self.render_config.format == "markdown":
                output_text = self._render_markdown_format()
            else:
                output_text = self._render_plain_format()
            
            if output_path:
                with open(output_path, 'w', encoding=self.render_config.encoding) as f:
                    f.write(output_text)
                self.logger.info(f"表格拓扑图已保存到: {output_path}")
            else:
                print(output_text)
            
            return True
            
        except Exception as e:
            self.logger.error(f"表格渲染失败: {e}")
            return False
    
    def _render_rich_format(self) -> str:
        """使用Rich库渲染彩色表格"""
        if not RICH_AVAILABLE:
            return self._render_plain_format()
        
        output_parts = []
        
        # 标题
        title_panel = Panel(
            Text(self.config.title, style="bold cyan", justify="center"),
            style="blue"
        )
        output_parts.append(self._capture_rich_output(self.console.print, title_panel))
        
        if self.config.description:
            desc_panel = Panel(self.config.description, style="dim")
            output_parts.append(self._capture_rich_output(self.console.print, desc_panel))
        
        # 系统概览
        if self.render_config.show_summary:
            summary_table = self._create_summary_table_rich()
            output_parts.append(self._capture_rich_output(self.console.print, summary_table))
        
        # 组件表格
        if self.render_config.group_by_type:
            component_tables = self._create_component_tables_rich()
            for table in component_tables:
                output_parts.append(self._capture_rich_output(self.console.print, table))
        else:
            all_nodes_table = self._create_all_nodes_table_rich()
            output_parts.append(self._capture_rich_output(self.console.print, all_nodes_table))
        
        # 连接关系表格
        if self.render_config.show_connections:
            connections_table = self._create_connections_table_rich()
            output_parts.append(self._capture_rich_output(self.console.print, connections_table))
        
        return '\n\n'.join(output_parts)
    
    def _capture_rich_output(self, func, *args, **kwargs) -> str:
        """捕获Rich输出为字符串"""
        import io
        from contextlib import redirect_stdout
        
        buffer = io.StringIO()
        temp_console = Console(file=buffer, width=self.render_config.max_width)
        
        if args and hasattr(args[0], '__rich__'):
            temp_console.print(args[0])
        else:
            func(*args, **kwargs)
        
        return buffer.getvalue().strip()
    
    def _create_summary_table_rich(self) -> Table:
        """创建系统概览表格（Rich格式）"""
        table = Table(title="🏗️ 系统概览", show_header=True, header_style="bold magenta")
        table.add_column("项目", style="cyan", width=20)
        table.add_column("数量", justify="right", style="green", width=10)
        table.add_column("详情", style="dim", width=50)
        
        # 统计各类型组件
        type_counts = defaultdict(int)
        for node in self.config.nodes:
            type_counts[node.type] += 1
        
        table.add_row("总节点数", str(len(self.config.nodes)), f"包含 {len(type_counts)} 种类型")
        table.add_row("总连接数", str(len(self.config.edges)), "节点间的连接关系")
        
        for comp_type, count in type_counts.items():
            type_name = self._get_component_type_name(comp_type)
            table.add_row(type_name, str(count), f"{comp_type.value} 类型组件")
        
        return table
    
    def _create_component_tables_rich(self) -> List[Table]:
        """创建按类型分组的组件表格（Rich格式）"""
        tables = []
        
        # 按类型分组
        type_groups = defaultdict(list)
        for node in self.config.nodes:
            type_groups[node.type].append(node)
        
        for comp_type, nodes in type_groups.items():
            type_name = self._get_component_type_name(comp_type)
            icon = self._get_component_icon(comp_type)
            
            table = Table(title=f"{icon} {type_name}", show_header=True, header_style="bold blue")
            table.add_column("名称", style="cyan", width=20)
            table.add_column("ID", style="dim", width=15)
            table.add_column("位置", justify="center", style="yellow", width=12)
            
            if self.render_config.show_properties:
                table.add_column("主要属性", style="green", width=40)
            
            for node in nodes:
                position_str = f"({node.position[0]:.1f}, {node.position[1]:.1f})"
                
                if self.render_config.show_properties:
                    properties_str = self._format_properties(node.properties)
                    table.add_row(node.name, node.id, position_str, properties_str)
                else:
                    table.add_row(node.name, node.id, position_str)
            
            tables.append(table)
        
        return tables
    
    def _create_connections_table_rich(self) -> Table:
        """创建连接关系表格（Rich格式）"""
        table = Table(title="🔗 连接关系", show_header=True, header_style="bold green")
        table.add_column("连接名称", style="cyan", width=20)
        table.add_column("源组件", style="blue", width=20)
        table.add_column("目标组件", style="magenta", width=20)
        table.add_column("类型", justify="center", style="yellow", width=10)
        
        if self.render_config.show_properties:
            table.add_column("属性", style="green", width=30)
        
        for edge in self.config.edges:
            source_node = self._find_node_by_id(edge.source_id)
            target_node = self._find_node_by_id(edge.target_id)
            
            source_name = source_node.name if source_node else edge.source_id
            target_name = target_node.name if target_node else edge.target_id
            
            if self.render_config.show_properties:
                properties_str = self._format_properties(edge.properties)
                table.add_row(edge.name, source_name, target_name, edge.edge_type, properties_str)
            else:
                table.add_row(edge.name, source_name, target_name, edge.edge_type)
        
        return table
    
    def _render_plain_format(self) -> str:
        """渲染纯文本格式"""
        lines = []
        
        # 标题
        title = self.config.title
        lines.append("=" * len(title))
        lines.append(title)
        lines.append("=" * len(title))
        lines.append("")
        
        if self.config.description:
            lines.append(self.config.description)
            lines.append("")
        
        # 系统概览
        if self.render_config.show_summary:
            lines.extend(self._create_summary_plain())
            lines.append("")
        
        # 组件信息
        if self.render_config.group_by_type:
            lines.extend(self._create_component_tables_plain())
        else:
            lines.extend(self._create_all_nodes_table_plain())
        
        # 连接关系
        if self.render_config.show_connections:
            lines.append("")
            lines.extend(self._create_connections_table_plain())
        
        return '\n'.join(lines)
    
    def _create_summary_plain(self) -> List[str]:
        """创建系统概览（纯文本）"""
        lines = ["🏗️ 系统概览:", "-" * 20]
        
        type_counts = defaultdict(int)
        for node in self.config.nodes:
            type_counts[node.type] += 1
        
        lines.append(f"总节点数: {len(self.config.nodes)}")
        lines.append(f"总连接数: {len(self.config.edges)}")
        
        for comp_type, count in type_counts.items():
            type_name = self._get_component_type_name(comp_type)
            lines.append(f"{type_name}: {count}")
        
        return lines
    
    def _create_component_tables_plain(self) -> List[str]:
        """创建组件表格（纯文本）"""
        lines = []
        
        # 按类型分组
        type_groups = defaultdict(list)
        for node in self.config.nodes:
            type_groups[node.type].append(node)
        
        for comp_type, nodes in type_groups.items():
            type_name = self._get_component_type_name(comp_type)
            icon = self._get_component_icon(comp_type)
            
            lines.append(f"{icon} {type_name}:")
            lines.append("-" * (len(type_name) + 4))
            
            for node in nodes:
                position_str = f"({node.position[0]:.1f}, {node.position[1]:.1f})"
                lines.append(f"  • {node.name} (ID: {node.id}) 位置: {position_str}")
                
                if self.render_config.show_properties and node.properties:
                    properties_str = self._format_properties(node.properties)
                    lines.append(f"    属性: {properties_str}")
            
            lines.append("")
        
        return lines
    
    def _create_connections_table_plain(self) -> List[str]:
        """创建连接关系表格（纯文本）"""
        lines = ["🔗 连接关系:", "-" * 15]
        
        for edge in self.config.edges:
            source_node = self._find_node_by_id(edge.source_id)
            target_node = self._find_node_by_id(edge.target_id)
            
            source_name = source_node.name if source_node else edge.source_id
            target_name = target_node.name if target_node else edge.target_id
            
            lines.append(f"  • {edge.name}: {source_name} → {target_name} ({edge.edge_type})")
            
            if self.render_config.show_properties and edge.properties:
                properties_str = self._format_properties(edge.properties)
                lines.append(f"    属性: {properties_str}")
        
        return lines
    
    def _render_markdown_format(self) -> str:
        """渲染Markdown格式"""
        lines = []
        
        # 标题
        lines.append(f"# {self.config.title}")
        lines.append("")
        
        if self.config.description:
            lines.append(self.config.description)
            lines.append("")
        
        # 系统概览
        if self.render_config.show_summary:
            lines.append("## 🏗️ 系统概览")
            lines.append("")
            
            type_counts = defaultdict(int)
            for node in self.config.nodes:
                type_counts[node.type] += 1
            
            lines.append("| 项目 | 数量 | 详情 |")
            lines.append("|------|------|------|")
            lines.append(f"| 总节点数 | {len(self.config.nodes)} | 包含 {len(type_counts)} 种类型 |")
            lines.append(f"| 总连接数 | {len(self.config.edges)} | 节点间的连接关系 |")
            
            for comp_type, count in type_counts.items():
                type_name = self._get_component_type_name(comp_type)
                lines.append(f"| {type_name} | {count} | {comp_type.value} 类型组件 |")
            
            lines.append("")
        
        # 组件信息
        lines.append("## 📋 组件信息")
        lines.append("")
        
        if self.render_config.group_by_type:
            # 按类型分组
            type_groups = defaultdict(list)
            for node in self.config.nodes:
                type_groups[node.type].append(node)
            
            for comp_type, nodes in type_groups.items():
                type_name = self._get_component_type_name(comp_type)
                icon = self._get_component_icon(comp_type)
                
                lines.append(f"### {icon} {type_name}")
                lines.append("")
                lines.append("| 名称 | ID | 位置 | 主要属性 |")
                lines.append("|------|----|----- |----------|")
                
                for node in nodes:
                    position_str = f"({node.position[0]:.1f}, {node.position[1]:.1f})"
                    properties_str = self._format_properties(node.properties) if self.render_config.show_properties else ""
                    lines.append(f"| {node.name} | {node.id} | {position_str} | {properties_str} |")
                
                lines.append("")
        
        # 连接关系
        if self.render_config.show_connections:
            lines.append("## 🔗 连接关系")
            lines.append("")
            lines.append("| 连接名称 | 源组件 | 目标组件 | 类型 | 属性 |")
            lines.append("|----------|--------|----------|------|------|")
            
            for edge in self.config.edges:
                source_node = self._find_node_by_id(edge.source_id)
                target_node = self._find_node_by_id(edge.target_id)
                
                source_name = source_node.name if source_node else edge.source_id
                target_name = target_node.name if target_node else edge.target_id
                properties_str = self._format_properties(edge.properties) if self.render_config.show_properties else ""
                
                lines.append(f"| {edge.name} | {source_name} | {target_name} | {edge.edge_type} | {properties_str} |")
        
        return '\n'.join(lines)
    
    def _get_component_type_name(self, comp_type: ComponentType) -> str:
        """获取组件类型中文名称"""
        type_names = {
            ComponentType.RESERVOIR: "水库系统",
            ComponentType.STATION: "枢纽站系统",
            ComponentType.JUNCTION: "连接点系统", 
            ComponentType.PIPE: "管道系统",
            ComponentType.PUMP: "泵站系统",
            ComponentType.VALVE: "阀门系统",
            ComponentType.TURBINE: "水轮机系统"
        }
        return type_names.get(comp_type, f"未知系统 ({comp_type.value})")
    
    def _get_component_icon(self, comp_type: ComponentType) -> str:
        """获取组件类型图标"""
        icons = {
            ComponentType.RESERVOIR: "🏞️",
            ComponentType.STATION: "🏗️",
            ComponentType.JUNCTION: "🔀",
            ComponentType.PIPE: "🚰",
            ComponentType.PUMP: "⚡",
            ComponentType.VALVE: "🚰",
            ComponentType.TURBINE: "🌀"
        }
        return icons.get(comp_type, "⭕")
    
    def _format_properties(self, properties: Dict[str, Any]) -> str:
        """格式化属性显示"""
        if not properties:
            return ""
        
        formatted = []
        for key, value in properties.items():
            if isinstance(value, float):
                formatted.append(f"{key}: {value:.2f}")
            else:
                formatted.append(f"{key}: {value}")
        
        return ", ".join(formatted)
    
    def _find_node_by_id(self, node_id: str) -> Optional[NodeData]:
        """根据ID查找节点"""
        for node in self.config.nodes:
            if node.id == node_id:
                return node
        return None
    
    def get_render_info(self) -> Dict[str, Any]:
        """获取渲染信息"""
        return {
            'renderer_type': 'table',
            'format': self.render_config.format,
            'rich_available': RICH_AVAILABLE,
            'max_width': self.render_config.max_width,
            'nodes_rendered': len(self.config.nodes),
            'edges_rendered': len(self.config.edges),
            'features': {
                'summary': self.render_config.show_summary,
                'grouped': self.render_config.group_by_type,
                'properties': self.render_config.show_properties,
                'connections': self.render_config.show_connections
            }
        }


if __name__ == "__main__":
    # 测试代码
    from topology_generator import TopologyConfig, NodeData, EdgeData, ComponentType
    
    # 创建测试配置
    test_config = TopologyConfig(
        title="表格渲染器测试",
        description="这是一个测试用的系统配置",
        nodes=[
            NodeData("r1", "上游水库", ComponentType.RESERVOIR, (0, 1), {"water_level": 100.0, "capacity": 5000}),
            NodeData("s1", "主控站", ComponentType.STATION, (2, 1), {"flow_rate": 50.0, "power": 200}),
            NodeData("j1", "分流点", ComponentType.JUNCTION, (4, 1), {"type": "split", "outlets": 2})
        ],
        edges=[
            EdgeData("e1", "进水管", "r1", "s1", properties={"diameter": 1.2, "length": 100}),
            EdgeData("e2", "出水管", "s1", "j1", properties={"diameter": 1.0, "length": 150})
        ]
    )
    
    renderer = TableRenderer(test_config)
    if renderer.can_render():
        print("=== Rich格式测试 ===")
        renderer.render_config.format = "rich"
        renderer.render()
        
        print("\n=== 纯文本格式测试 ===")
        renderer.render_config.format = "plain"
        renderer.render()
        
        print("\n表格渲染器测试完成！")
    else:
        print("表格渲染器环境检查失败！")