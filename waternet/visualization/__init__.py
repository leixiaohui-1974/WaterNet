#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用拓扑图生成器包初始化

提供统一的接口和自动降级策略，确保在任何环境下都能生成可视化结果。

Created by: Qoder AI Assistant
Date: 2025-10-04
"""

from .topology_generator import (
    TopologyGenerator, TopologyConfig, NodeData, EdgeData, 
    ComponentType, RenderMode, get_generator
)

# 自动注册所有可用的渲染器
def _register_all_renderers():
    """自动注册所有可用的渲染器"""
    generator = get_generator()
    
    # 注册增强版文本ASCII渲染器（最高优先级，用户偏好）
    try:
        from .enhanced_text_renderer import EnhancedTextRenderer
        generator.register_renderer(RenderMode.TEXT_ASCII, EnhancedTextRenderer)
        print("✅ 增强版文本ASCII渲染器已注册")
    except ImportError as e:
        print(f"❌ 增强版文本ASCII渲染器加载失败，尝试标准版: {e}")
        try:
            from .text_ascii_renderer import TextASCIIRenderer
            generator.register_renderer(RenderMode.TEXT_ASCII, TextASCIIRenderer)
            print("✅ 标准文本ASCII渲染器已注册")
        except ImportError as e2:
            print(f"❌ 文本ASCII渲染器加载失败: {e2}")
    
    # 注册表格渲染器（可靠的备选方案）
    try:
        from .table_renderer import TableRenderer
        generator.register_renderer(RenderMode.TABLE_FORMAT, TableRenderer)
        print("✅ 表格渲染器已注册")
    except ImportError as e:
        print(f"❌ 表格渲染器加载失败: {e}")
    
    # 注册图形渲染器（需要matplotlib）
    try:
        from .graph_renderer import GraphRenderer
        generator.register_renderer(RenderMode.GRAPH_MATPLOTLIB, GraphRenderer)
        print("✅ 图形渲染器已注册")
    except ImportError as e:
        print(f"❌ 图形渲染器加载失败: {e}")

# 延迟注册，避免循环导入
_registered = False

def _ensure_registered():
    global _registered
    if not _registered:
        _register_all_renderers()
        _registered = True

# 导出主要接口
__all__ = [
    'TopologyGenerator',
    'TopologyConfig', 
    'NodeData',
    'EdgeData',
    'ComponentType',
    'RenderMode',
    'get_generator',
    'create_topology_from_config',
    'quick_render'
]


def create_topology_from_config(config_path: str, output_path: str = None, preferred_modes: list = None):
    """
    从配置文件快速创建拓扑图
    
    Args:
        config_path: 配置文件路径 
        output_path: 输出文件路径（可选）
        preferred_modes: 优先渲染模式列表（可选）
    
    Returns:
        dict: 渲染结果
    """
    _ensure_registered()
    generator = get_generator()
    return generator.load_and_generate(config_path, preferred_modes, output_path)


def quick_render(title: str, nodes: list, edges: list, output_path: str = None):
    """
    快速渲染简单拓扑图
    
    Args:
        title: 图标题
        nodes: 节点列表 [(id, name, type, position), ...]
        edges: 边列表 [(id, name, source, target), ...]
        output_path: 输出路径（可选）
    
    Returns:
        dict: 渲染结果
    """
    _ensure_registered()
    
    # 创建节点数据
    node_objects = []
    for node_data in nodes:
        if len(node_data) >= 4:
            node_id, name, comp_type, position = node_data[:4]
            properties = node_data[4] if len(node_data) > 4 else {}
            
            if isinstance(comp_type, str):
                comp_type = ComponentType(comp_type)
            
            node_objects.append(NodeData(node_id, name, comp_type, position, properties))
    
    # 创建边数据
    edge_objects = []
    for edge_data in edges:
        if len(edge_data) >= 4:
            edge_id, name, source, target = edge_data[:4]
            properties = edge_data[4] if len(edge_data) > 4 else {}
            
            edge_objects.append(EdgeData(edge_id, name, source, target, properties=properties))
    
    # 创建配置
    config = TopologyConfig(
        title=title,
        nodes=node_objects,
        edges=edge_objects
    )
    
    # 生成拓扑图
    generator = get_generator()
    return generator.generate_topology(config, output_path=output_path)