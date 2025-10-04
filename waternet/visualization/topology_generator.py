#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用拓扑图生成器 - 核心架构

支持多种可视化方式：
1. 文本ASCII艺术风格（优先级最高，用户偏好）
2. 图形化拓扑图（matplotlib后端）
3. 表格式系统信息
4. 自动降级策略确保总有一种方式能工作

Created by: Qoder AI Assistant
Date: 2025-10-04
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)


class RenderMode(Enum):
    """渲染模式枚举"""
    TEXT_ASCII = "text_ascii"          # 文本ASCII艺术风格
    GRAPH_MATPLOTLIB = "graph_matplotlib"  # matplotlib图形化
    TABLE_FORMAT = "table_format"      # 表格式
    HYBRID_MODE = "hybrid_mode"        # 混合模式


class ComponentType(Enum):
    """组件类型枚举"""
    RESERVOIR = "reservoir"     # 水库
    STATION = "station"         # 枢纽站
    JUNCTION = "junction"       # 连接点
    PIPE = "pipe"              # 管道
    PUMP = "pump"              # 泵站
    VALVE = "valve"            # 阀门
    TURBINE = "turbine"        # 水轮机


@dataclass
class NodeData:
    """节点数据结构"""
    id: str
    name: str
    type: ComponentType
    position: Tuple[float, float] = (0.0, 0.0)
    properties: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EdgeData:
    """边数据结构"""
    id: str
    name: str
    source_id: str
    target_id: str
    edge_type: str = "flow"
    properties: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TopologyConfig:
    """拓扑图配置"""
    title: str = "系统拓扑图"
    description: str = ""
    nodes: List[NodeData] = field(default_factory=list)
    edges: List[EdgeData] = field(default_factory=list)
    layout_config: Dict[str, Any] = field(default_factory=dict)
    render_config: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class TopologyRenderer(ABC):
    """拓扑图渲染器抽象基类"""
    
    def __init__(self, config: TopologyConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def can_render(self) -> bool:
        """检查当前环境是否支持此渲染器"""
        pass
    
    @abstractmethod
    def render(self, output_path: Optional[str] = None) -> bool:
        """渲染拓扑图"""
        pass
    
    @abstractmethod
    def get_render_info(self) -> Dict[str, Any]:
        """获取渲染信息"""
        pass
    
    def validate_config(self) -> List[str]:
        """验证配置有效性"""
        errors = []
        
        if not self.config.nodes:
            errors.append("节点列表不能为空")
        
        # 验证边的连接有效性
        node_ids = {node.id for node in self.config.nodes}
        for edge in self.config.edges:
            if edge.source_id not in node_ids:
                errors.append(f"边 {edge.id} 的源节点 {edge.source_id} 不存在")
            if edge.target_id not in node_ids:
                errors.append(f"边 {edge.id} 的目标节点 {edge.target_id} 不存在")
        
        return errors


class ConfigLoader:
    """配置文件加载器"""
    
    @staticmethod
    def load_from_file(file_path: Union[str, Path]) -> TopologyConfig:
        """从文件加载配置"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_path.suffix.lower() in ['.yaml', '.yml']:
                    data = yaml.safe_load(f)
                elif file_path.suffix.lower() == '.json':
                    data = json.load(f)
                else:
                    raise ValueError(f"不支持的配置文件格式: {file_path.suffix}")
            
            return ConfigLoader._parse_config_data(data)
        
        except Exception as e:
            logger.error(f"加载配置文件失败: {file_path}, 错误: {e}")
            raise
    
    @staticmethod
    def _parse_config_data(data: Dict[str, Any]) -> TopologyConfig:
        """解析配置数据"""
        # 解析节点
        nodes = []
        for node_data in data.get('nodes', []):
            node = NodeData(
                id=node_data['id'],
                name=node_data['name'],
                type=ComponentType(node_data['type']),
                position=tuple(node_data.get('position', [0.0, 0.0])),
                properties=node_data.get('properties', {}),
                metadata=node_data.get('metadata', {})
            )
            nodes.append(node)
        
        # 解析边
        edges = []
        for edge_data in data.get('edges', []):
            edge = EdgeData(
                id=edge_data['id'],
                name=edge_data['name'],
                source_id=edge_data['source'],
                target_id=edge_data['target'],
                edge_type=edge_data.get('type', 'flow'),
                properties=edge_data.get('properties', {}),
                metadata=edge_data.get('metadata', {})
            )
            edges.append(edge)
        
        return TopologyConfig(
            title=data.get('title', '系统拓扑图'),
            description=data.get('description', ''),
            nodes=nodes,
            edges=edges,
            layout_config=data.get('layout', {}),
            render_config=data.get('render', {}),
            metadata=data.get('metadata', {})
        )


class TopologyGenerator:
    """通用拓扑图生成器主类"""
    
    def __init__(self):
        self.renderers: Dict[RenderMode, type] = {}
        self.fallback_order = [
            RenderMode.TEXT_ASCII,      # 优先使用文本模式（用户偏好）
            RenderMode.TABLE_FORMAT,    # 表格模式作为备选
            RenderMode.GRAPH_MATPLOTLIB # 图形模式最后
        ]
        self.logger = logging.getLogger(__name__)
    
    def register_renderer(self, mode: RenderMode, renderer_class: type):
        """注册渲染器"""
        self.renderers[mode] = renderer_class
        self.logger.info(f"注册渲染器: {mode.value} -> {renderer_class.__name__}")
    
    def generate_topology(
        self, 
        config: TopologyConfig, 
        preferred_modes: Optional[List[RenderMode]] = None,
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """生成拓扑图"""
        
        if preferred_modes is None:
            preferred_modes = self.fallback_order
        
        results = {
            'success_modes': [],
            'failed_modes': [],
            'outputs': {},
            'errors': {}
        }
        
        # 按优先级尝试每种渲染方式
        for mode in preferred_modes:
            if mode not in self.renderers:
                self.logger.warning(f"渲染器未注册: {mode.value}")
                results['failed_modes'].append(mode.value)
                continue
            
            try:
                renderer_class = self.renderers[mode]
                renderer = renderer_class(config)
                
                # 检查是否支持
                if not renderer.can_render():
                    self.logger.warning(f"当前环境不支持渲染器: {mode.value}")
                    results['failed_modes'].append(mode.value)
                    continue
                
                # 验证配置
                validation_errors = renderer.validate_config()
                if validation_errors:
                    error_msg = f"配置验证失败: {'; '.join(validation_errors)}"
                    self.logger.error(error_msg)
                    results['failed_modes'].append(mode.value)
                    results['errors'][mode.value] = error_msg
                    continue
                
                # 执行渲染
                success = renderer.render(output_path)
                if success:
                    results['success_modes'].append(mode.value)
                    results['outputs'][mode.value] = renderer.get_render_info()
                    self.logger.info(f"渲染成功: {mode.value}")
                else:
                    results['failed_modes'].append(mode.value)
                    self.logger.error(f"渲染失败: {mode.value}")
                    
            except Exception as e:
                error_msg = f"渲染器执行异常: {str(e)}"
                self.logger.error(error_msg)
                results['failed_modes'].append(mode.value)
                results['errors'][mode.value] = error_msg
        
        return results
    
    def load_and_generate(
        self, 
        config_path: Union[str, Path],
        preferred_modes: Optional[List[RenderMode]] = None,
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """从配置文件加载并生成拓扑图"""
        
        try:
            config = ConfigLoader.load_from_file(config_path)
            return self.generate_topology(config, preferred_modes, output_path)
        except Exception as e:
            self.logger.error(f"加载配置文件失败: {config_path}, 错误: {e}")
            return {
                'success_modes': [],
                'failed_modes': [],
                'outputs': {},
                'errors': {'config_load': str(e)}
            }


# 全局拓扑生成器实例
topology_generator = TopologyGenerator()


def get_generator() -> TopologyGenerator:
    """获取全局拓扑生成器实例"""
    return topology_generator


if __name__ == "__main__":
    # 基本使用示例
    logging.basicConfig(level=logging.INFO)
    
    # 创建简单的演示配置
    demo_config = TopologyConfig(
        title="演示系统拓扑图",
        description="这是一个演示用的水力系统拓扑图",
        nodes=[
            NodeData("reservoir1", "上游水库", ComponentType.RESERVOIR, (0, 0)),
            NodeData("station1", "主控站", ComponentType.STATION, (1, 0)),
            NodeData("junction1", "分流点", ComponentType.JUNCTION, (2, 0)),
            NodeData("reservoir2", "下游水库", ComponentType.RESERVOIR, (3, 0))
        ],
        edges=[
            EdgeData("edge1", "进水管", "reservoir1", "station1"),
            EdgeData("edge2", "主管道", "station1", "junction1"),
            EdgeData("edge3", "出水管", "junction1", "reservoir2")
        ]
    )
    
    generator = get_generator()
    print("拓扑图生成器架构创建完成!")
    print(f"配置包含 {len(demo_config.nodes)} 个节点和 {len(demo_config.edges)} 条边")