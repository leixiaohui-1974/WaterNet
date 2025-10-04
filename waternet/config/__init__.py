"""
WaterNet 配置管理系统

提供统一的配置文件加载、验证和管理功能。
支持YAML格式的配置文件，用于渠道几何、模型参数等。

Author: WaterNet Development Team
Date: 2024-10-03
"""

import yaml
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod
import numpy as np


@dataclass
class ChannelGeometryConfig:
    """渠道几何配置"""
    mileage: float
    elevation: float
    roughness: float
    cross_section: Dict[str, Any]  # 断面参数
    
    def to_section_dict(self) -> Dict[str, Any]:
        """转换为断面字典格式"""
        section = {
            'mileage': self.mileage,
            'elevation': self.elevation,
            'roughness': self.roughness
        }
        
        # 根据断面类型创建面积和宽度函数
        cs_type = self.cross_section.get('type', 'rectangular')
        
        if cs_type == 'rectangular':
            width = self.cross_section.get('width', 10.0)
            section['area_func'] = lambda h: max(0, h - self.elevation) * width
            section['top_width_func'] = lambda h: width if h > self.elevation else 0
            
        elif cs_type == 'trapezoidal':
            bottom_width = self.cross_section.get('bottom_width', 8.0)
            side_slope = self.cross_section.get('side_slope', 2.0)
            
            def trap_area(h):
                if h <= self.elevation:
                    return 0.0
                depth = h - self.elevation
                return depth * (bottom_width + side_slope * depth)
            
            def trap_width(h):
                if h <= self.elevation:
                    return 0.0
                depth = h - self.elevation
                return bottom_width + 2 * side_slope * depth
            
            section['area_func'] = trap_area
            section['top_width_func'] = trap_width
            
        else:
            raise ValueError(f"不支持的断面类型: {cs_type}")
        
        return section


@dataclass
class ModelParametersConfig:
    """模型参数配置"""
    model_type: str  # 'saint_venant', 'muskingum', 'storage_routing', 'idz'
    parameters: Dict[str, Any]
    solver_config: Optional[Dict[str, Any]] = None


@dataclass
class PhysicalRelationsConfig:
    """物理关系配置"""
    V_to_H: Dict[str, Any]  # 蓄量-水位关系参数
    H_to_Q: Dict[str, Any]  # 水位-出流关系参数


@dataclass
class BoundaryConditionsConfig:
    """边界条件配置"""
    upstream_type: str  # 'flow' 或 'level'
    downstream_type: str  # 'flow' 或 'level'
    upstream_values: Union[float, List[float]]
    downstream_values: Union[float, List[float]]
    time_series: Optional[List[float]] = None


@dataclass
class SimulationConfig:
    """仿真配置"""
    simulation_type: str  # 'steady', 'unsteady', 'parameter_estimation', 'digital_twin'
    time_step: Optional[float] = None
    total_time: Optional[float] = None
    output_interval: Optional[float] = None


class ConfigValidator(ABC):
    """配置验证器基类"""
    
    @abstractmethod
    def validate(self, config: Dict[str, Any]) -> bool:
        """验证配置"""
        pass
    
    @abstractmethod
    def get_errors(self) -> List[str]:
        """获取验证错误信息"""
        pass


class ChannelConfigValidator(ConfigValidator):
    """渠道配置验证器"""
    
    def __init__(self):
        self.errors = []
    
    def validate(self, config: Dict[str, Any]) -> bool:
        """验证渠道配置"""
        self.errors = []
        
        # 检查必需字段
        if 'sections' not in config:
            self.errors.append("缺少 'sections' 字段")
            return False
        
        sections = config['sections']
        if not isinstance(sections, list) or len(sections) < 2:
            self.errors.append("至少需要2个断面")
            return False
        
        # 验证每个断面
        for i, section in enumerate(sections):
            if not self._validate_section(section, i):
                return False
        
        # 检查里程排序
        mileages = [s['mileage'] for s in sections]
        if mileages != sorted(mileages):
            self.errors.append("断面里程必须按升序排列")
            return False
        
        return True
    
    def _validate_section(self, section: Dict[str, Any], index: int) -> bool:
        """验证单个断面"""
        required_fields = ['mileage', 'elevation', 'roughness', 'cross_section']
        
        for field in required_fields:
            if field not in section:
                self.errors.append(f"断面{index}缺少字段: {field}")
                return False
        
        # 验证数值类型
        try:
            float(section['mileage'])
            float(section['elevation'])
            float(section['roughness'])
        except (ValueError, TypeError):
            self.errors.append(f"断面{index}数值字段格式错误")
            return False
        
        # 验证断面参数
        cs = section['cross_section']
        if 'type' not in cs:
            self.errors.append(f"断面{index}缺少断面类型")
            return False
        
        return True
    
    def get_errors(self) -> List[str]:
        """获取验证错误"""
        return self.errors


class ModelConfigValidator(ConfigValidator):
    """模型配置验证器"""
    
    def __init__(self):
        self.errors = []
    
    def validate(self, config: Dict[str, Any]) -> bool:
        """验证模型配置"""
        self.errors = []
        
        if 'model_type' not in config:
            self.errors.append("缺少模型类型")
            return False
        
        model_type = config['model_type']
        supported_types = ['saint_venant', 'muskingum', 'storage_routing', 'idz']
        
        if model_type not in supported_types:
            self.errors.append(f"不支持的模型类型: {model_type}")
            return False
        
        # 验证模型特定参数
        if 'parameters' not in config:
            self.errors.append("缺少模型参数")
            return False
        
        return self._validate_model_parameters(model_type, config['parameters'])
    
    def _validate_model_parameters(self, model_type: str, params: Dict[str, Any]) -> bool:
        """验证模型参数"""
        if model_type == 'muskingum':
            required = ['K', 'x', 'dt', 'initial_V']
            for param in required:
                if param not in params:
                    self.errors.append(f"马斯京干模型缺少参数: {param}")
                    return False
            
            # 参数范围检查
            if not (0 <= params['x'] <= 0.5):
                self.errors.append("马斯京干模型x参数必须在[0, 0.5]范围内")
                return False
        
        elif model_type == 'idz':
            required = ['tau', 'T_delay', 'alpha', 'dt', 'initial_V']
            for param in required:
                if param not in params:
                    self.errors.append(f"IDZ模型缺少参数: {param}")
                    return False
        
        return True
    
    def get_errors(self) -> List[str]:
        """获取验证错误"""
        return self.errors


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_dir: Optional[Union[str, Path]] = None):
        """
        初始化配置管理器
        
        Args:
            config_dir: 配置文件目录，默认为当前目录下的configs
        """
        if config_dir is None:
            config_dir = Path.cwd() / 'configs'
        
        self.config_dir = Path(config_dir)
        self.validators = {
            'channel': ChannelConfigValidator(),
            'model': ModelConfigValidator()
        }
        
        # 确保配置目录存在
        self.config_dir.mkdir(exist_ok=True)
    
    def load_config(self, config_file: Union[str, Path]) -> Dict[str, Any]:
        """
        加载配置文件
        
        Args:
            config_file: 配置文件路径
            
        Returns:
            Dict[str, Any]: 配置数据
        """
        config_path = self._resolve_config_path(config_file)
        
        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            if config_path.suffix.lower() == '.yaml' or config_path.suffix.lower() == '.yml':
                config = yaml.safe_load(f)
            elif config_path.suffix.lower() == '.json':
                config = json.load(f)
            else:
                raise ValueError(f"不支持的配置文件格式: {config_path.suffix}")
        
        return config
    
    def save_config(self, config: Dict[str, Any], config_file: Union[str, Path]):
        """
        保存配置文件
        
        Args:
            config: 配置数据
            config_file: 配置文件路径
        """
        config_path = self._resolve_config_path(config_file)
        
        # 确保目录存在
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, 'w', encoding='utf-8') as f:
            if config_path.suffix.lower() == '.yaml' or config_path.suffix.lower() == '.yml':
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            elif config_path.suffix.lower() == '.json':
                json.dump(config, f, indent=2, ensure_ascii=False)
            else:
                raise ValueError(f"不支持的配置文件格式: {config_path.suffix}")
    
    def validate_config(self, config: Dict[str, Any], config_type: str) -> bool:
        """
        验证配置
        
        Args:
            config: 配置数据
            config_type: 配置类型 ('channel', 'model', etc.)
            
        Returns:
            bool: 验证是否通过
        """
        if config_type not in self.validators:
            raise ValueError(f"不支持的配置类型: {config_type}")
        
        validator = self.validators[config_type]
        return validator.validate(config)
    
    def get_validation_errors(self, config_type: str) -> List[str]:
        """获取验证错误信息"""
        if config_type not in self.validators:
            return ["不支持的配置类型"]
        
        return self.validators[config_type].get_errors()
    
    def create_channel_sections(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        从配置创建断面列表
        
        Args:
            config: 渠道配置
            
        Returns:
            List[Dict[str, Any]]: 断面数据列表
        """
        if not self.validate_config(config, 'channel'):
            errors = self.get_validation_errors('channel')
            raise ValueError(f"渠道配置验证失败: {errors}")
        
        sections = []
        for section_config in config['sections']:
            geometry_config = ChannelGeometryConfig(
                mileage=section_config['mileage'],
                elevation=section_config['elevation'],
                roughness=section_config['roughness'],
                cross_section=section_config['cross_section']
            )
            sections.append(geometry_config.to_section_dict())
        
        return sections
    
    def create_physical_relations(self, config: Dict[str, Any]):
        """
        从配置创建物理关系函数
        
        Args:
            config: 物理关系配置
            
        Returns:
            Tuple[Callable, Callable]: V_to_H_func, H_to_Q_func
        """
        V_to_H_config = config.get('V_to_H', {})
        H_to_Q_config = config.get('H_to_Q', {})
        
        # 创建V-H关系函数
        v2h_type = V_to_H_config.get('type', 'linear')
        if v2h_type == 'linear':
            base_level = V_to_H_config.get('base_level', 99.0)
            coefficient = V_to_H_config.get('coefficient', 1e-4)
            V_to_H_func = lambda V: base_level + coefficient * V
        else:
            raise ValueError(f"不支持的V-H关系类型: {v2h_type}")
        
        # 创建H-Q关系函数
        h2q_type = H_to_Q_config.get('type', 'weir')
        if h2q_type == 'weir':
            threshold = H_to_Q_config.get('threshold', 99.0)
            coefficient = H_to_Q_config.get('coefficient', 25.0)
            exponent = H_to_Q_config.get('exponent', 1.5)
            
            def H_to_Q_func(H):
                if H <= threshold:
                    return 0.0
                return coefficient * (H - threshold) ** exponent
        else:
            raise ValueError(f"不支持的H-Q关系类型: {h2q_type}")
        
        return V_to_H_func, H_to_Q_func
    
    def _resolve_config_path(self, config_file: Union[str, Path]) -> Path:
        """解析配置文件路径"""
        config_path = Path(config_file)
        
        if not config_path.is_absolute():
            config_path = self.config_dir / config_path
        
        return config_path
    
    def list_configs(self, pattern: str = "*.yaml") -> List[Path]:
        """列出配置文件"""
        return list(self.config_dir.glob(pattern))
    
    def create_default_configs(self):
        """创建默认配置文件"""
        self._create_default_channel_config()
        self._create_default_model_configs()
        self._create_default_simulation_config()
    
    def _create_default_channel_config(self):
        """创建默认渠道配置"""
        config = {
            'name': 'simple_rectangular_channel',
            'description': '简单矩形明渠',
            'sections': [
                {
                    'mileage': 0.0,
                    'elevation': 100.0,
                    'roughness': 0.025,
                    'cross_section': {
                        'type': 'rectangular',
                        'width': 10.0
                    }
                },
                {
                    'mileage': 500.0,
                    'elevation': 99.5,
                    'roughness': 0.025,
                    'cross_section': {
                        'type': 'rectangular',
                        'width': 10.0
                    }
                },
                {
                    'mileage': 1000.0,
                    'elevation': 99.0,
                    'roughness': 0.025,
                    'cross_section': {
                        'type': 'rectangular',
                        'width': 10.0
                    }
                }
            ]
        }
        
        self.save_config(config, 'simple_channel.yaml')
    
    def _create_default_model_configs(self):
        """创建默认模型配置"""
        # 马斯京干模型配置
        muskingum_config = {
            'model_type': 'muskingum',
            'parameters': {
                'K': 3600.0,
                'x': 0.2,
                'dt': 60.0,
                'initial_V': 12000.0
            },
            'physical_relations': {
                'V_to_H': {
                    'type': 'linear',
                    'base_level': 99.0,
                    'coefficient': 1.25e-4
                },
                'H_to_Q': {
                    'type': 'weir',
                    'threshold': 99.0,
                    'coefficient': 25.0,
                    'exponent': 1.5
                }
            }
        }
        
        self.save_config(muskingum_config, 'muskingum_model.yaml')
        
        # IDZ模型配置
        idz_config = {
            'model_type': 'idz',
            'parameters': {
                'tau': 1800.0,
                'T_delay': 600.0,
                'alpha': 3600.0,
                'dt': 60.0,
                'initial_V': 12000.0
            },
            'physical_relations': {
                'V_to_H': {
                    'type': 'linear',
                    'base_level': 99.0,
                    'coefficient': 1.25e-4
                },
                'H_to_Q': {
                    'type': 'weir',
                    'threshold': 99.0,
                    'coefficient': 25.0,
                    'exponent': 1.5
                }
            }
        }
        
        self.save_config(idz_config, 'idz_model.yaml')
    
    def _create_default_simulation_config(self):
        """创建默认仿真配置"""
        config = {
            'simulation_type': 'unsteady',
            'time_step': 60.0,
            'total_time': 3600.0,
            'output_interval': 60.0,
            'boundary_conditions': {
                'upstream_type': 'flow',
                'downstream_type': 'level',
                'upstream_values': [8.0, 10.0, 12.0, 15.0, 12.0, 10.0, 8.0],
                'downstream_values': 99.4
            }
        }
        
        self.save_config(config, 'simulation_config.yaml')