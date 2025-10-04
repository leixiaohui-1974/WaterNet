"""
复杂水力枢纽配置管理

提供复杂水力枢纽系统的配置管理功能，包括配置验证、模板生成和参数优化。
支持多种配置格式和动态配置更新。

Author: WaterNet Development Team
Date: 2024-10-04
"""

import yaml
import json
import os
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from datetime import datetime
import logging
from pathlib import Path


@dataclass
class SystemConfig:
    """系统配置基类"""
    name: str
    description: str = ""
    version: str = "1.0"
    created_time: str = ""
    
    def __post_init__(self):
        if not self.created_time:
            self.created_time = datetime.now().isoformat()


@dataclass
class ReservoirConfig:
    """水库配置"""
    name: str
    type: str = "reservoir"
    initial_level: float = 100.0
    surface_area: Optional[float] = None
    bottom_level: float = 0.0
    capacity_curve: Optional[Dict[str, Any]] = None
    nodes: Optional[List[str]] = None
    min_level: Optional[float] = None
    max_level: Optional[float] = None


@dataclass
class PipeConfig:
    """管道配置"""
    name: str
    type: str = "pipe"
    upstream_node: str = ""
    downstream_node: str = ""
    length: float = 1000.0
    diameter: float = 1.0
    roughness: float = 0.0001
    minor_loss_coeff: float = 0.0
    elevation_change: float = 0.0
    fittings: Optional[List[Dict[str, Any]]] = None


@dataclass  
class StationConfig:
    """枢纽站配置"""
    name: str
    type: str = "station"
    upstream_node: str = ""
    downstream_node: str = ""
    station_type: str = "complex"
    structures: Optional[Dict[str, List[Dict[str, Any]]]] = None
    gates: Optional[List[Dict[str, Any]]] = None
    pumps: Optional[List[Dict[str, Any]]] = None
    initial_settings: Optional[Dict[str, float]] = None


@dataclass
class JunctionConfig:
    """连接点配置"""
    name: str
    type: str = "junction" 
    connected_objects: List[str] = None
    junction_type: str = "general"
    elevation: float = 0.0
    flow_directions: Optional[Dict[str, str]] = None
    loss_coefficients: Optional[Dict[str, float]] = None
    inlet_object: Optional[str] = None
    split_ratios: Optional[Dict[str, float]] = None
    
    def __post_init__(self):
        if self.connected_objects is None:
            self.connected_objects = []


@dataclass
class NetworkConfiguration:
    """完整网络配置"""
    system: SystemConfig
    reservoirs: List[ReservoirConfig] = None
    pipes: List[PipeConfig] = None
    stations: List[StationConfig] = None
    junctions: List[JunctionConfig] = None
    initial_conditions: Optional[Dict[str, float]] = None
    simulation_settings: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.reservoirs is None:
            self.reservoirs = []
        if self.pipes is None:
            self.pipes = []
        if self.stations is None:
            self.stations = []
        if self.junctions is None:
            self.junctions = []
        if self.initial_conditions is None:
            self.initial_conditions = {}
        if self.simulation_settings is None:
            self.simulation_settings = {}


class ConfigValidator:
    """配置验证器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def validate_network_config(self, config: NetworkConfiguration) -> Dict[str, Any]:
        """
        验证网络配置
        
        Args:
            config (NetworkConfiguration): 网络配置
        
        Returns:
            Dict[str, Any]: 验证结果
        """
        result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'statistics': {}
        }
        
        # 验证系统配置
        self._validate_system_config(config.system, result)
        
        # 验证各组件配置
        self._validate_reservoirs(config.reservoirs, result)
        self._validate_pipes(config.pipes, result)
        self._validate_stations(config.stations, result)
        self._validate_junctions(config.junctions, result)
        
        # 验证连接一致性
        self._validate_connectivity(config, result)
        
        # 生成统计信息
        self._generate_statistics(config, result)
        
        return result
    
    def _validate_system_config(self, system: SystemConfig, result: Dict[str, Any]):
        """验证系统配置"""
        if not system.name:
            result['errors'].append("系统名称不能为空")
            result['is_valid'] = False
        
        if not system.version:
            result['warnings'].append("未指定系统版本")
    
    def _validate_reservoirs(self, reservoirs: List[ReservoirConfig], result: Dict[str, Any]):
        """验证水库配置"""
        names = set()
        
        for i, reservoir in enumerate(reservoirs):
            if not reservoir.name:
                result['errors'].append(f"水库 {i+1} 名称不能为空")
                result['is_valid'] = False
                continue
            
            if reservoir.name in names:
                result['errors'].append(f"水库名称重复: {reservoir.name}")
                result['is_valid'] = False
            names.add(reservoir.name)
            
            if reservoir.initial_level <= 0:
                result['warnings'].append(f"水库 {reservoir.name} 初始水位为非正值")
            
            if reservoir.surface_area is None and reservoir.capacity_curve is None:
                result['errors'].append(f"水库 {reservoir.name} 必须指定水面面积或库容曲线")
                result['is_valid'] = False
    
    def _validate_pipes(self, pipes: List[PipeConfig], result: Dict[str, Any]):
        """验证管道配置"""
        names = set()
        
        for i, pipe in enumerate(pipes):
            if not pipe.name:
                result['errors'].append(f"管道 {i+1} 名称不能为空")
                result['is_valid'] = False
                continue
            
            if pipe.name in names:
                result['errors'].append(f"管道名称重复: {pipe.name}")
                result['is_valid'] = False
            names.add(pipe.name)
            
            if not pipe.upstream_node or not pipe.downstream_node:
                result['errors'].append(f"管道 {pipe.name} 必须指定上下游节点")
                result['is_valid'] = False
            
            if pipe.length <= 0:
                result['errors'].append(f"管道 {pipe.name} 长度必须大于0")
                result['is_valid'] = False
            
            if pipe.diameter <= 0:
                result['errors'].append(f"管道 {pipe.name} 直径必须大于0")
                result['is_valid'] = False
    
    def _validate_stations(self, stations: List[StationConfig], result: Dict[str, Any]):
        """验证枢纽站配置"""
        names = set()
        
        for i, station in enumerate(stations):
            if not station.name:
                result['errors'].append(f"枢纽站 {i+1} 名称不能为空")
                result['is_valid'] = False
                continue
            
            if station.name in names:
                result['errors'].append(f"枢纽站名称重复: {station.name}")
                result['is_valid'] = False
            names.add(station.name)
            
            if not station.upstream_node or not station.downstream_node:
                result['errors'].append(f"枢纽站 {station.name} 必须指定上下游节点")
                result['is_valid'] = False
    
    def _validate_junctions(self, junctions: List[JunctionConfig], result: Dict[str, Any]):
        """验证连接点配置"""
        names = set()
        
        for i, junction in enumerate(junctions):
            if not junction.name:
                result['errors'].append(f"连接点 {i+1} 名称不能为空")
                result['is_valid'] = False
                continue
            
            if junction.name in names:
                result['errors'].append(f"连接点名称重复: {junction.name}")
                result['is_valid'] = False
            names.add(junction.name)
            
            if len(junction.connected_objects) < 2:
                result['errors'].append(f"连接点 {junction.name} 至少需要连接2个对象")
                result['is_valid'] = False
    
    def _validate_connectivity(self, config: NetworkConfiguration, result: Dict[str, Any]):
        """验证连接一致性"""
        # 收集所有节点
        all_nodes = set()
        defined_objects = set()
        
        # 水库节点
        for reservoir in config.reservoirs:
            defined_objects.add(reservoir.name)
            if reservoir.nodes:
                all_nodes.update(reservoir.nodes)
        
        # 管道节点
        for pipe in config.pipes:
            defined_objects.add(pipe.name)
            all_nodes.add(pipe.upstream_node)
            all_nodes.add(pipe.downstream_node)
        
        # 枢纽站节点
        for station in config.stations:
            defined_objects.add(station.name)
            all_nodes.add(station.upstream_node)
            all_nodes.add(station.downstream_node)
        
        # 连接点节点
        for junction in config.junctions:
            defined_objects.add(junction.name)
            all_nodes.add(junction.name)
            
            # 检查连接对象是否存在
            for obj_name in junction.connected_objects:
                if obj_name not in defined_objects:
                    result['warnings'].append(f"连接点 {junction.name} 引用了未定义的对象: {obj_name}")
    
    def _generate_statistics(self, config: NetworkConfiguration, result: Dict[str, Any]):
        """生成统计信息"""
        result['statistics'] = {
            'total_reservoirs': len(config.reservoirs),
            'total_pipes': len(config.pipes),
            'total_stations': len(config.stations),
            'total_junctions': len(config.junctions),
            'system_info': {
                'name': config.system.name,
                'version': config.system.version,
                'created_time': config.system.created_time
            }
        }


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_dir: str = "configs"):
        """
        初始化配置管理器
        
        Args:
            config_dir (str): 配置文件目录
        """
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        self.validator = ConfigValidator()
        self.logger = logging.getLogger(__name__)
    
    def save_config(self, config: NetworkConfiguration, filename: str,
                   format: str = "yaml") -> str:
        """
        保存配置到文件
        
        Args:
            config (NetworkConfiguration): 网络配置
            filename (str): 文件名（不含扩展名）
            format (str): 文件格式 ("yaml" 或 "json")
        
        Returns:
            str: 保存的文件路径
        """
        if format not in ["yaml", "json"]:
            raise ValueError("格式必须是 'yaml' 或 'json'")
        
        # 构建文件路径
        file_path = self.config_dir / f"{filename}.{format}"
        
        # 转换为字典
        config_dict = asdict(config)
        
        # 保存文件
        with open(file_path, 'w', encoding='utf-8') as f:
            if format == "yaml":
                yaml.dump(config_dict, f, default_flow_style=False, allow_unicode=True)
            else:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"配置已保存到: {file_path}")
        return str(file_path)
    
    def load_config(self, filename: str) -> NetworkConfiguration:
        """
        从文件加载配置
        
        Args:
            filename (str): 文件路径或文件名
        
        Returns:
            NetworkConfiguration: 网络配置
        """
        # 处理文件路径
        if os.path.isabs(filename):
            file_path = Path(filename)
        else:
            file_path = self.config_dir / filename
        
        if not file_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {file_path}")
        
        # 加载文件
        with open(file_path, 'r', encoding='utf-8') as f:
            if file_path.suffix.lower() in ['.yaml', '.yml']:
                config_dict = yaml.safe_load(f)
            elif file_path.suffix.lower() == '.json':
                config_dict = json.load(f)
            else:
                raise ValueError(f"不支持的文件格式: {file_path.suffix}")
        
        # 转换为配置对象
        config = self._dict_to_config(config_dict)
        
        self.logger.info(f"配置已加载: {file_path}")
        return config
    
    def _dict_to_config(self, config_dict: Dict[str, Any]) -> NetworkConfiguration:
        """将字典转换为配置对象"""
        # 系统配置
        system_dict = config_dict.get('system', {})
        system = SystemConfig(**system_dict)
        
        # 组件配置
        reservoirs = [ReservoirConfig(**r) for r in config_dict.get('reservoirs', [])]
        pipes = [PipeConfig(**p) for p in config_dict.get('pipes', [])]
        stations = [StationConfig(**s) for s in config_dict.get('stations', [])]
        junctions = [JunctionConfig(**j) for j in config_dict.get('junctions', [])]
        
        return NetworkConfiguration(
            system=system,
            reservoirs=reservoirs,
            pipes=pipes,
            stations=stations,
            junctions=junctions,
            initial_conditions=config_dict.get('initial_conditions', {}),
            simulation_settings=config_dict.get('simulation_settings', {})
        )
    
    def validate_config_file(self, filename: str) -> Dict[str, Any]:
        """
        验证配置文件
        
        Args:
            filename (str): 配置文件路径
        
        Returns:
            Dict[str, Any]: 验证结果
        """
        try:
            config = self.load_config(filename)
            return self.validator.validate_network_config(config)
        except Exception as e:
            return {
                'is_valid': False,
                'errors': [f"配置文件加载失败: {e}"],
                'warnings': [],
                'statistics': {}
            }
    
    def list_configs(self) -> List[str]:
        """
        列出所有配置文件
        
        Returns:
            List[str]: 配置文件列表
        """
        config_files = []
        for file_path in self.config_dir.glob("*.yaml"):
            config_files.append(file_path.name)
        for file_path in self.config_dir.glob("*.json"):
            config_files.append(file_path.name)
        return sorted(config_files)
    
    def create_template_config(self, template_type: str = "simple_cascade") -> NetworkConfiguration:
        """
        创建模板配置
        
        Args:
            template_type (str): 模板类型
        
        Returns:
            NetworkConfiguration: 模板配置
        """
        if template_type == "simple_cascade":
            return self._create_simple_cascade_template()
        elif template_type == "complex_network":
            return self._create_complex_network_template()
        else:
            raise ValueError(f"不支持的模板类型: {template_type}")
    
    def _create_simple_cascade_template(self) -> NetworkConfiguration:
        """创建简单梯级系统模板"""
        system = SystemConfig(
            name="简单梯级系统",
            description="包含两级水库的简单梯级系统示例",
            version="1.0"
        )
        
        reservoirs = [
            ReservoirConfig(
                name="上游水库",
                initial_level=105.0,
                surface_area=1000000.0,
                bottom_level=95.0,
                nodes=["上游水库_出口"]
            ),
            ReservoirConfig(
                name="下游水库", 
                initial_level=100.0,
                surface_area=800000.0,
                bottom_level=90.0,
                nodes=["下游水库_入口"]
            )
        ]
        
        pipes = [
            PipeConfig(
                name="连接管道",
                upstream_node="上游水库_出口",
                downstream_node="下游水库_入口",
                length=2000.0,
                diameter=2.0,
                roughness=0.0001
            )
        ]
        
        initial_conditions = {
            "H_上游水库": 105.0,
            "H_下游水库": 100.0,
            "Q_连接管道": 5.0
        }
        
        return NetworkConfiguration(
            system=system,
            reservoirs=reservoirs,
            pipes=pipes,
            initial_conditions=initial_conditions
        )
    
    def _create_complex_network_template(self) -> NetworkConfiguration:
        """创建复杂网络模板"""
        system = SystemConfig(
            name="复杂水力网络",
            description="包含多种设施的复杂水力网络示例",
            version="1.0"
        )
        
        reservoirs = [
            ReservoirConfig(
                name="主水库",
                initial_level=110.0,
                surface_area=2000000.0,
                bottom_level=100.0
            )
        ]
        
        stations = [
            StationConfig(
                name="主枢纽站",
                upstream_node="主水库_出口",
                downstream_node="分流点",
                station_type="gate_station",
                gates=[{
                    "name": "主闸门",
                    "width": 15.0,
                    "discharge_coeff": 0.7,
                    "initial_opening": 2.0
                }]
            )
        ]
        
        junctions = [
            JunctionConfig(
                name="分流点",
                connected_objects=["主枢纽站", "分支1", "分支2"],
                junction_type="splitter",
                inlet_object="主枢纽站",
                split_ratios={"分支1": 0.6, "分支2": 0.4}
            )
        ]
        
        pipes = [
            PipeConfig(
                name="分支1",
                upstream_node="分流点",
                downstream_node="终点1",
                length=1500.0,
                diameter=1.5
            ),
            PipeConfig(
                name="分支2", 
                upstream_node="分流点",
                downstream_node="终点2",
                length=1200.0,
                diameter=1.2
            )
        ]
        
        return NetworkConfiguration(
            system=system,
            reservoirs=reservoirs,
            stations=stations,
            junctions=junctions,
            pipes=pipes
        )


# 便捷函数
def create_config_manager(config_dir: str = "configs") -> ConfigManager:
    """
    创建配置管理器
    
    Args:
        config_dir (str): 配置目录
    
    Returns:
        ConfigManager: 配置管理器实例
    """
    return ConfigManager(config_dir)


def validate_config_file(filename: str) -> Dict[str, Any]:
    """
    验证配置文件
    
    Args:
        filename (str): 配置文件路径
    
    Returns:
        Dict[str, Any]: 验证结果
    """
    manager = ConfigManager()
    return manager.validate_config_file(filename)


def create_template(template_type: str = "simple_cascade", 
                   output_file: Optional[str] = None) -> NetworkConfiguration:
    """
    创建配置模板
    
    Args:
        template_type (str): 模板类型
        output_file (str, optional): 输出文件路径
    
    Returns:
        NetworkConfiguration: 模板配置
    """
    manager = ConfigManager()
    config = manager.create_template_config(template_type)
    
    if output_file:
        manager.save_config(config, output_file)
    
    return config