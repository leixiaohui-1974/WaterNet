"""
网络拓扑构建器

负责从配置文件构建完整的水力网络模型，实现配置驱动的模型实例化。
通过工厂模式和拓扑验证，确保网络模型的正确性和完整性。

设计原理:
1. 配置驱动：从YAML/JSON配置文件构建网络
2. 工厂模式：使用专门的工厂类创建不同类型的模型
3. 拓扑验证：检查网络连接的完整性和合理性
4. 依赖解析：自动处理模型之间的依赖关系

Author: WaterNet Development Team
Date: 2024-10-04
"""

import yaml
import json
import os
from typing import Dict, List, Optional, Any, Union, Type
from abc import ABC, abstractmethod
from dataclasses import dataclass
import logging

# 导入模型类
from ..interfaces.hydro_model import HydroModel
from .reservoir_model import ReservoirModel, create_simple_reservoir, create_polynomial_reservoir
from .junction_model import JunctionModel, FlowSplitterJunction, create_simple_junction
from .complex_station_model import ComplexStationModel, create_gate_station, create_pump_station
from .pressurized_pipe_model import PressurizedPipeModel, create_simple_pipe, create_pipe_with_fittings

# 导入控制结构
try:
    from ...physical_objects.control_structure import (
        ControlStructure, GateModel, PumpModel, ValveModel, TurbineModel
    )
except ImportError:
    # 如果导入失败，使用简化版本
    ControlStructure = None


@dataclass
class NetworkConfig:
    """网络配置数据类"""
    name: str
    description: str = ""
    models: List[Dict[str, Any]] = None
    connections: List[Dict[str, Any]] = None
    initial_conditions: Dict[str, float] = None
    simulation_settings: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.models is None:
            self.models = []
        if self.connections is None:
            self.connections = []
        if self.initial_conditions is None:
            self.initial_conditions = {}
        if self.simulation_settings is None:
            self.simulation_settings = {}


class ModelFactory(ABC):
    """模型工厂抽象基类"""
    
    @abstractmethod
    def create_model(self, config: Dict[str, Any]) -> HydroModel:
        """
        创建模型实例
        
        Args:
            config (Dict[str, Any]): 模型配置
        
        Returns:
            HydroModel: 模型实例
        """
        pass
    
    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        验证配置格式
        
        Args:
            config (Dict[str, Any]): 模型配置
        
        Returns:
            bool: 配置是否有效
        """
        pass
    
    @property
    @abstractmethod
    def model_type(self) -> str:
        """模型类型标识"""
        pass


class ReservoirFactory(ModelFactory):
    """水库模型工厂"""
    
    @property
    def model_type(self) -> str:
        return "reservoir"
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """验证水库配置"""
        required_fields = ['name', 'type', 'initial_level']
        
        for field in required_fields:
            if field not in config:
                return False
        
        # 检查库容曲线配置
        if 'capacity_curve' not in config and 'surface_area' not in config:
            return False
        
        return True
    
    def create_model(self, config: Dict[str, Any]) -> ReservoirModel:
        """创建水库模型"""
        name = config['name']
        nodes = config.get('nodes', [config.get('upstream_node', f'{name}_up'), 
                                    config.get('downstream_node', f'{name}_down')])
        initial_level = config['initial_level']
        
        # 处理库容曲线
        if 'capacity_curve' in config:
            return self._create_from_capacity_curve(config, name, nodes, initial_level)
        elif 'surface_area' in config:
            return self._create_simple_reservoir(config, name, nodes, initial_level)
        else:
            raise ValueError("水库配置必须包含库容曲线或水面面积")
    
    def _create_simple_reservoir(self, config: Dict[str, Any], name: str, 
                                nodes: List[str], initial_level: float) -> ReservoirModel:
        """创建简单水库（矩形库容）"""
        surface_area = config['surface_area']
        bottom_level = config.get('bottom_level', 0.0)
        upstream_node = nodes[0] if len(nodes) > 0 else f'{name}_up'
        downstream_node = nodes[1] if len(nodes) > 1 else f'{name}_down'
        
        return create_simple_reservoir(name, upstream_node, downstream_node,
                                     initial_level, bottom_level, surface_area)
    
    def _create_from_capacity_curve(self, config: Dict[str, Any], name: str,
                                   nodes: List[str], initial_level: float) -> ReservoirModel:
        """从库容曲线创建水库"""
        curve_config = config['capacity_curve']
        
        if isinstance(curve_config, str):
            # 外部文件
            curve_data = self._load_capacity_curve_file(curve_config)
        elif isinstance(curve_config, dict):
            curve_data = curve_config
        else:
            raise ValueError("库容曲线配置格式错误")
        
        if curve_data.get('type') == 'polynomial':
            coefficients = curve_data['coefficients']
            return create_polynomial_reservoir(name, nodes, coefficients, initial_level)
        else:
            # 其他类型的库容曲线
            raise NotImplementedError("暂不支持此类型的库容曲线")
    
    def _load_capacity_curve_file(self, filename: str) -> Dict[str, Any]:
        """加载库容曲线文件"""
        if not os.path.exists(filename):
            raise FileNotFoundError(f"库容曲线文件不存在: {filename}")
        
        with open(filename, 'r', encoding='utf-8') as f:
            if filename.endswith('.json'):
                return json.load(f)
            elif filename.endswith('.yaml') or filename.endswith('.yml'):
                return yaml.safe_load(f)
            else:
                raise ValueError("不支持的库容曲线文件格式")


class JunctionFactory(ModelFactory):
    """连接点模型工厂"""
    
    @property
    def model_type(self) -> str:
        return "junction"
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """验证连接点配置"""
        required_fields = ['name', 'type', 'connected_objects']
        
        for field in required_fields:
            if field not in config:
                return False
        
        if len(config['connected_objects']) < 2:
            return False
        
        return True
    
    def create_model(self, config: Dict[str, Any]) -> JunctionModel:
        """创建连接点模型"""
        name = config['name']
        connected_objects = config['connected_objects']
        
        junction_type = config.get('junction_type', 'general')
        
        if junction_type == 'splitter':
            return self._create_splitter_junction(config, name, connected_objects)
        else:
            return self._create_general_junction(config, name, connected_objects)
    
    def _create_general_junction(self, config: Dict[str, Any], name: str,
                                connected_objects: List[str]) -> JunctionModel:
        """创建一般连接点"""
        flow_directions = config.get('flow_directions', {})
        elevation = config.get('elevation', 0.0)
        loss_coefficients = config.get('loss_coefficients', {})
        
        return JunctionModel(name, connected_objects, flow_directions, 
                           elevation, loss_coefficients)
    
    def _create_splitter_junction(self, config: Dict[str, Any], name: str,
                                 connected_objects: List[str]) -> FlowSplitterJunction:
        """创建分流连接点"""
        inlet_object = config['inlet_object']
        outlet_objects = [obj for obj in connected_objects if obj != inlet_object]
        split_ratios = config.get('split_ratios', None)
        elevation = config.get('elevation', 0.0)
        
        return FlowSplitterJunction(name, inlet_object, outlet_objects,
                                  split_ratios, elevation)


class StationFactory(ModelFactory):
    """枢纽站模型工厂"""
    
    @property
    def model_type(self) -> str:
        return "station"
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """验证枢纽站配置"""
        required_fields = ['name', 'type', 'upstream_node', 'downstream_node']
        
        for field in required_fields:
            if field not in config:
                return False
        
        return True
    
    def create_model(self, config: Dict[str, Any]) -> ComplexStationModel:
        """创建枢纽站模型"""
        name = config['name']
        upstream_node = config['upstream_node']
        downstream_node = config['downstream_node']
        
        station_type = config.get('station_type', 'complex')
        
        if station_type == 'gate_station':
            return self._create_gate_station(config, name, upstream_node, downstream_node)
        elif station_type == 'pump_station':
            return self._create_pump_station(config, name, upstream_node, downstream_node)
        else:
            return self._create_complex_station(config, name, upstream_node, downstream_node)
    
    def _create_gate_station(self, config: Dict[str, Any], name: str,
                           upstream_node: str, downstream_node: str) -> ComplexStationModel:
        """创建闸门站"""
        gates_config = config.get('gates', [])
        return create_gate_station(name, upstream_node, downstream_node, gates_config)
    
    def _create_pump_station(self, config: Dict[str, Any], name: str,
                           upstream_node: str, downstream_node: str) -> ComplexStationModel:
        """创建泵站"""
        pumps_config = config.get('pumps', [])
        return create_pump_station(name, upstream_node, downstream_node, pumps_config)
    
    def _create_complex_station(self, config: Dict[str, Any], name: str,
                              upstream_node: str, downstream_node: str) -> ComplexStationModel:
        """创建复杂枢纽站"""
        # 创建基础枢纽站
        station = ComplexStationModel(name, upstream_node, downstream_node)
        
        # 添加设备
        structures_config = config.get('structures', {})
        for struct_type, struct_list in structures_config.items():
            for struct_config in struct_list:
                structure = self._create_structure(struct_type, struct_config)
                initial_setting = struct_config.get('initial_setting', 0.0)
                station.add_structure(struct_config['name'], structure, initial_setting)
        
        return station
    
    def _create_structure(self, struct_type: str, struct_config: Dict[str, Any]) -> ControlStructure:
        """创建水力设备"""
        if ControlStructure is None:
            # 使用简化的设备模型
            return self._create_simple_structure(struct_type, struct_config)
        
        # 使用完整的设备模型
        if struct_type == 'gate':
            return GateModel(
                struct_config['name'],
                struct_config.get('discharge_coeff', 0.7),
                struct_config.get('width', 10.0)
            )
        elif struct_type == 'pump':
            return PumpModel(
                struct_config['name'],
                struct_config.get('curve_coeffs', [50.0, -0.01])
            )
        elif struct_type == 'valve':
            return ValveModel(
                struct_config['name'],
                struct_config.get('valve_coeff', 1.0)
            )
        elif struct_type == 'turbine':
            return TurbineModel(struct_config['name'])
        else:
            raise ValueError(f"不支持的设备类型: {struct_type}")
    
    def _create_simple_structure(self, struct_type: str, struct_config: Dict[str, Any]):
        """创建简化设备模型"""
        # 简化实现，仅用于演示
        class SimpleStructure:
            def __init__(self, name):
                self.name = name
            
            def get_flow(self, H_up, H_down, setting):
                if setting <= 0 or H_up <= H_down:
                    return 0.0
                return setting * math.sqrt(2 * 9.81 * (H_up - H_down))
        
        return SimpleStructure(struct_config['name'])


class PipeFactory(ModelFactory):
    """管道模型工厂"""
    
    @property
    def model_type(self) -> str:
        return "pipe"
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """验证管道配置"""
        required_fields = ['name', 'type', 'upstream_node', 'downstream_node', 
                          'length', 'diameter']
        
        for field in required_fields:
            if field not in config:
                return False
        
        return True
    
    def create_model(self, config: Dict[str, Any]) -> PressurizedPipeModel:
        """创建管道模型"""
        name = config['name']
        upstream_node = config['upstream_node']
        downstream_node = config['downstream_node']
        length = config['length']
        diameter = config['diameter']
        roughness = config.get('roughness', 0.0001)
        
        # 检查是否有管件配置
        fittings = config.get('fittings', [])
        if fittings:
            return create_pipe_with_fittings(name, upstream_node, downstream_node,
                                           length, diameter, fittings, roughness)
        else:
            minor_loss_coeff = config.get('minor_loss_coeff', 0.0)
            elevation_change = config.get('elevation_change', 0.0)
            
            return PressurizedPipeModel(name, upstream_node, downstream_node,
                                      length, diameter, roughness,
                                      minor_loss_coeff, elevation_change)


class TopologyValidator:
    """拓扑验证器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def validate_network(self, models: List[HydroModel]) -> Dict[str, Any]:
        """
        验证网络拓扑
        
        Args:
            models (List[HydroModel]): 模型列表
        
        Returns:
            Dict[str, Any]: 验证结果
        """
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'statistics': {}
        }
        
        # 检查模型名称唯一性
        self._check_name_uniqueness(models, validation_result)
        
        # 检查节点连通性
        self._check_node_connectivity(models, validation_result)
        
        # 检查变量名冲突
        self._check_variable_conflicts(models, validation_result)
        
        # 生成统计信息
        self._generate_statistics(models, validation_result)
        
        return validation_result
    
    def _check_name_uniqueness(self, models: List[HydroModel], result: Dict[str, Any]):
        """检查模型名称唯一性"""
        names = [model.name for model in models]
        duplicates = [name for name in set(names) if names.count(name) > 1]
        
        if duplicates:
            result['is_valid'] = False
            result['errors'].append(f"模型名称重复: {duplicates}")
    
    def _check_node_connectivity(self, models: List[HydroModel], result: Dict[str, Any]):
        """检查节点连通性"""
        all_nodes = set()
        node_connections = {}
        
        # 收集所有节点和连接
        for model in models:
            for node in model.node_names:
                all_nodes.add(node)
                if node not in node_connections:
                    node_connections[node] = []
                node_connections[node].append(model.name)
        
        # 检查孤立节点
        isolated_nodes = [node for node, connections in node_connections.items() 
                         if len(connections) == 1]
        
        if isolated_nodes:
            result['warnings'].append(f"孤立节点: {isolated_nodes}")
        
        # 检查连通性
        if len(all_nodes) > 1:
            # 简化连通性检查
            connected_components = self._find_connected_components(models)
            if len(connected_components) > 1:
                result['warnings'].append(f"网络存在 {len(connected_components)} 个不连通的部分")
    
    def _check_variable_conflicts(self, models: List[HydroModel], result: Dict[str, Any]):
        """检查变量名冲突"""
        all_variables = []
        
        for model in models:
            variables = model.get_variable_names()
            all_variables.extend(variables)
        
        duplicates = [var for var in set(all_variables) if all_variables.count(var) > 1]
        
        if duplicates:
            result['is_valid'] = False
            result['errors'].append(f"变量名冲突: {duplicates}")
    
    def _find_connected_components(self, models: List[HydroModel]) -> List[List[str]]:
        """查找连通分量"""
        # 构建邻接表
        adjacency = {}
        for model in models:
            for i, node1 in enumerate(model.node_names):
                if node1 not in adjacency:
                    adjacency[node1] = set()
                for j, node2 in enumerate(model.node_names):
                    if i != j:
                        adjacency[node1].add(node2)
                        if node2 not in adjacency:
                            adjacency[node2] = set()
                        adjacency[node2].add(node1)
        
        # DFS查找连通分量
        visited = set()
        components = []
        
        for node in adjacency:
            if node not in visited:
                component = []
                self._dfs(node, adjacency, visited, component)
                components.append(component)
        
        return components
    
    def _dfs(self, node: str, adjacency: Dict[str, set], visited: set, component: List[str]):
        """深度优先搜索"""
        visited.add(node)
        component.append(node)
        
        for neighbor in adjacency.get(node, []):
            if neighbor not in visited:
                self._dfs(neighbor, adjacency, visited, component)
    
    def _generate_statistics(self, models: List[HydroModel], result: Dict[str, Any]):
        """生成统计信息"""
        model_types = {}
        total_variables = 0
        all_nodes = set()
        
        for model in models:
            model_type = model.__class__.__name__
            model_types[model_type] = model_types.get(model_type, 0) + 1
            total_variables += len(model.get_variable_names())
            all_nodes.update(model.node_names)
        
        result['statistics'] = {
            'total_models': len(models),
            'model_types': model_types,
            'total_variables': total_variables,
            'total_nodes': len(all_nodes)
        }


class NetworkBuilder:
    """网络拓扑构建器"""
    
    def __init__(self):
        self.factories = {
            'reservoir': ReservoirFactory(),
            'junction': JunctionFactory(),
            'station': StationFactory(),
            'pipe': PipeFactory()
        }
        self.validator = TopologyValidator()
        self.logger = logging.getLogger(__name__)
    
    def register_factory(self, model_type: str, factory: ModelFactory):
        """注册模型工厂"""
        self.factories[model_type] = factory
    
    def build_from_config(self, config: Union[Dict[str, Any], str, NetworkConfig]) -> List[HydroModel]:
        """
        从配置构建网络模型
        
        Args:
            config: 网络配置（字典、文件路径或NetworkConfig对象）
        
        Returns:
            List[HydroModel]: 模型列表
        """
        # 解析配置
        if isinstance(config, str):
            network_config = self._load_config_file(config)
        elif isinstance(config, dict):
            network_config = NetworkConfig(**config)
        elif isinstance(config, NetworkConfig):
            network_config = config
        else:
            raise ValueError("不支持的配置格式")
        
        # 构建模型
        models = []
        for model_config in network_config.models:
            try:
                model = self._create_model(model_config)
                models.append(model)
                self.logger.info(f"成功创建模型: {model.name}")
            except Exception as e:
                self.logger.error(f"创建模型失败: {model_config.get('name', 'Unknown')}, 错误: {e}")
                raise
        
        # 验证拓扑
        validation_result = self.validator.validate_network(models)
        
        if not validation_result['is_valid']:
            error_msg = "网络拓扑验证失败: " + "; ".join(validation_result['errors'])
            raise ValueError(error_msg)
        
        if validation_result['warnings']:
            for warning in validation_result['warnings']:
                self.logger.warning(warning)
        
        self.logger.info(f"网络构建完成，共 {len(models)} 个模型")
        self.logger.info(f"统计信息: {validation_result['statistics']}")
        
        return models
    
    def _load_config_file(self, filename: str) -> NetworkConfig:
        """加载配置文件"""
        if not os.path.exists(filename):
            raise FileNotFoundError(f"配置文件不存在: {filename}")
        
        with open(filename, 'r', encoding='utf-8') as f:
            if filename.endswith('.json'):
                config_data = json.load(f)
            elif filename.endswith('.yaml') or filename.endswith('.yml'):
                config_data = yaml.safe_load(f)
            else:
                raise ValueError("不支持的配置文件格式")
        
        return NetworkConfig(**config_data)
    
    def _create_model(self, model_config: Dict[str, Any]) -> HydroModel:
        """创建单个模型"""
        model_type = model_config.get('type')
        
        if model_type not in self.factories:
            raise ValueError(f"不支持的模型类型: {model_type}")
        
        factory = self.factories[model_type]
        
        if not factory.validate_config(model_config):
            raise ValueError(f"模型配置验证失败: {model_config.get('name', 'Unknown')}")
        
        return factory.create_model(model_config)
    
    def export_network_info(self, models: List[HydroModel], filename: str):
        """导出网络信息"""
        info = {
            'network_summary': {
                'total_models': len(models),
                'creation_time': str(datetime.now())
            },
            'models': []
        }
        
        for model in models:
            model_info = {
                'name': model.name,
                'type': model.__class__.__name__,
                'nodes': model.node_names,
                'variables': model.get_variable_names()
            }
            info['models'].append(model_info)
        
        with open(filename, 'w', encoding='utf-8') as f:
            if filename.endswith('.json'):
                json.dump(info, f, indent=2, ensure_ascii=False)
            elif filename.endswith('.yaml') or filename.endswith('.yml'):
                yaml.dump(info, f, default_flow_style=False, allow_unicode=True)
    
    def validate_network_only(self, config: Union[Dict[str, Any], str]) -> Dict[str, Any]:
        """仅验证网络配置，不创建模型"""
        try:
            models = self.build_from_config(config)
            return self.validator.validate_network(models)
        except Exception as e:
            return {
                'is_valid': False,
                'errors': [str(e)],
                'warnings': [],
                'statistics': {}
            }


# 便捷函数
def build_network_from_file(config_file: str) -> List[HydroModel]:
    """
    从配置文件构建网络
    
    Args:
        config_file (str): 配置文件路径
    
    Returns:
        List[HydroModel]: 模型列表
    """
    builder = NetworkBuilder()
    return builder.build_from_config(config_file)


def create_simple_cascade_system(reservoir_configs: List[Dict[str, Any]],
                                pipe_configs: List[Dict[str, Any]]) -> List[HydroModel]:
    """
    创建简单的梯级系统
    
    Args:
        reservoir_configs: 水库配置列表
        pipe_configs: 管道配置列表
    
    Returns:
        List[HydroModel]: 模型列表
    """
    builder = NetworkBuilder()
    models = []
    
    # 创建水库
    for res_config in reservoir_configs:
        res_config['type'] = 'reservoir'
        model = builder._create_model(res_config)
        models.append(model)
    
    # 创建管道
    for pipe_config in pipe_configs:
        pipe_config['type'] = 'pipe'
        model = builder._create_model(pipe_config)
        models.append(model)
    
    return models