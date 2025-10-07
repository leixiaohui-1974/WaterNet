"""
配置管理体系

提供分层的配置文件管理、验证、合并和参数解析功能。

Features:
- 支持YAML/JSON多种配置格式
- 分层配置文件合并
- 配置参数验证
- 模板支持和参数替换
- 配置缓存和版本管理

Author: WaterNet Development Team
Date: 2024-10-05
"""

import yaml
import json
import os
from typing import Dict, Any, List, Optional, Union, Callable
from dataclasses import dataclass, field
from pathlib import Path
import logging

from .core import ObjectType, SimulationMethod, PressurizedMethod, DEFAULT_CONFIG


@dataclass
class ValidationResult:
    """配置验证结果"""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def add_error(self, message: str):
        """添加错误信息"""
        self.errors.append(message)
        self.is_valid = False
    
    def add_warning(self, message: str):
        """添加警告信息"""
        self.warnings.append(message)


class ConfigManager:
    """
    配置管理器
    
    负责配置文件的加载、验证、合并和管理。
    支持分层配置文件结构和参数模板替换。
    
    Features:
    - 多格式支持（YAML, JSON）
    - 分层配置合并
    - 参数验证
    - 模板替换
    - 配置缓存
    """
    
    def __init__(self, config_root: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_root: 配置文件根目录，默认为当前目录下的configs
        """
        self.config_root = Path(config_root) if config_root else Path("configs")
        self.config_cache = {}
        self.template_vars = {}
        self.logger = logging.getLogger(__name__)
        
        # 配置验证器注册表
        self.validators = {
            'object_definition': self._validate_object_definition,
            'basic_properties': self._validate_basic_properties,
            'geometry_definition': self._validate_geometry_definition,
            'simulation_preferences': self._validate_simulation_preferences,
            'boundary_conditions': self._validate_boundary_conditions
        }
    
    def load_config(self, config_path: Union[str, Path], 
                   use_cache: bool = True) -> Dict[str, Any]:
        """
        加载配置文件
        
        Args:
            config_path: 配置文件路径
            use_cache: 是否使用缓存
            
        Returns:
            配置字典
            
        Raises:
            FileNotFoundError: 配置文件不存在
            ValueError: 配置文件格式错误
        """
        config_path = Path(config_path)
        
        # 检查缓存
        if use_cache and str(config_path) in self.config_cache:
            return self.config_cache[str(config_path)]
        
        # 检查文件存在性
        if not config_path.exists():
            # 尝试在配置根目录下查找
            full_path = self.config_root / config_path
            if not full_path.exists():
                raise FileNotFoundError(f"配置文件不存在: {config_path}")
            config_path = full_path
        
        # 根据文件扩展名选择解析器
        suffix = config_path.suffix.lower()
        try:
            if suffix in ['.yaml', '.yml']:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
            elif suffix == '.json':
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            else:
                raise ValueError(f"不支持的配置文件格式: {suffix}")
                
        except Exception as e:
            raise ValueError(f"配置文件解析失败 {config_path}: {e}")
        
        # 应用模板替换
        if self.template_vars:
            config = self._apply_template_substitution(config)
        
        # 缓存结果
        if use_cache:
            self.config_cache[str(config_path)] = config
        
        return config
    
    def load_layered_config(self, config_files: List[Union[str, Path]]) -> Dict[str, Any]:
        """
        加载并合并多层配置文件
        
        Args:
            config_files: 配置文件列表，按优先级排序（后面的覆盖前面的）
            
        Returns:
            合并后的配置字典
        """
        merged_config = {}
        
        for config_file in config_files:
            config = self.load_config(config_file)
            merged_config = self._deep_merge_dict(merged_config, config)
        
        return merged_config
    
    def validate_config(self, config: Dict[str, Any], 
                       object_type: Optional[ObjectType] = None) -> ValidationResult:
        """
        验证配置参数的完整性和有效性
        
        Args:
            config: 待验证的配置字典
            object_type: 对象类型，用于特定验证
            
        Returns:
            验证结果
        """
        result = ValidationResult(is_valid=True)
        
        # 基础结构验证
        for section_name, validator in self.validators.items():
            if section_name in config:
                try:
                    validator(config[section_name], result)
                except Exception as e:
                    result.add_error(f"{section_name}验证失败: {e}")
        
        # 对象类型特定验证
        if object_type:
            self._validate_object_specific(config, object_type, result)
        
        return result
    
    def create_object_config(self, object_id: str, object_type: ObjectType,
                           template_name: Optional[str] = None,
                           **kwargs) -> Dict[str, Any]:
        """
        基于模板创建对象配置
        
        Args:
            object_id: 对象唯一标识符
            object_type: 对象类型
            template_name: 模板名称
            **kwargs: 额外的配置参数
            
        Returns:
            对象配置字典
        """
        # 加载基础模板
        if template_name:
            template_path = self.config_root / "templates" / f"{template_name}.yaml"
            if template_path.exists():
                base_config = self.load_config(template_path)
            else:
                self.logger.warning(f"模板文件不存在: {template_path}")
                base_config = {}
        else:
            base_config = {}
        
        # 创建基本配置结构
        config = {
            'object_definition': {
                'object_id': object_id,
                'object_type': object_type.value,
                'name': kwargs.get('name', object_id),
                'description': kwargs.get('description', f'{object_type.value}对象')
            },
            'basic_properties': {},
            'simulation_preferences': {
                'default_method': self._get_default_method(object_type),
                'enable_twin': kwargs.get('enable_twin', False)
            }
        }
        
        # 合并模板配置
        config = self._deep_merge_dict(base_config, config)
        
        # 应用额外参数
        for key, value in kwargs.items():
            if key not in ['name', 'description', 'enable_twin']:
                # 将额外参数放入basic_properties中
                config['basic_properties'][key] = value
        
        return config
    
    def set_template_variable(self, name: str, value: Any):
        """设置模板变量"""
        self.template_vars[name] = value
    
    def set_template_variables(self, variables: Dict[str, Any]):
        """批量设置模板变量"""
        self.template_vars.update(variables)
    
    def clear_cache(self):
        """清空配置缓存"""
        self.config_cache.clear()
    
    def _apply_template_substitution(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """应用模板变量替换"""
        import copy
        result = copy.deepcopy(config)
        
        def replace_recursive(obj):
            if isinstance(obj, dict):
                return {k: replace_recursive(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [replace_recursive(item) for item in obj]
            elif isinstance(obj, str):
                # 简单的模板替换 ${var_name}
                for var_name, var_value in self.template_vars.items():
                    obj = obj.replace(f"${{{var_name}}}", str(var_value))
                return obj
            else:
                return obj
        
        return replace_recursive(result)
    
    def _deep_merge_dict(self, base: Dict, overlay: Dict) -> Dict:
        """深度合并字典"""
        import copy
        result = copy.deepcopy(base)
        
        for key, value in overlay.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge_dict(result[key], value)
            else:
                result[key] = copy.deepcopy(value)
        
        return result
    
    def _get_default_method(self, object_type: ObjectType) -> str:
        """获取对象类型的默认仿真方法"""
        default_methods = {
            ObjectType.CHANNEL: SimulationMethod.SAINT_VENANT_FULL.value,
            ObjectType.PIPE: PressurizedMethod.WATER_HAMMER_FULL.value,
            ObjectType.SIPHON: SimulationMethod.SAINT_VENANT_FULL.value,
            ObjectType.RESERVOIR: SimulationMethod.STORAGE_ROUTING.value
        }
        return default_methods.get(object_type, SimulationMethod.WATER_BALANCE.value)
    
    # 验证器方法
    def _validate_object_definition(self, config: Dict[str, Any], result: ValidationResult):
        """验证对象定义配置"""
        required_fields = ['object_id', 'object_type']
        for field in required_fields:
            if field not in config:
                result.add_error(f"object_definition缺少必需字段: {field}")
        
        # 验证对象类型
        if 'object_type' in config:
            try:
                ObjectType(config['object_type'])
            except ValueError:
                result.add_error(f"无效的对象类型: {config['object_type']}")
    
    def _validate_basic_properties(self, config: Dict[str, Any], result: ValidationResult):
        """验证基本属性配置"""
        # 验证数值类型
        numeric_fields = ['length', 'design_flow', 'design_velocity']
        for field in numeric_fields:
            if field in config:
                try:
                    value = float(config[field])
                    if value <= 0:
                        result.add_warning(f"{field}应为正值，当前值: {value}")
                except (ValueError, TypeError):
                    result.add_error(f"{field}应为数值类型: {config[field]}")
    
    def _validate_geometry_definition(self, config: Dict[str, Any], result: ValidationResult):
        """验证几何定义配置"""
        if 'cross_sections' in config:
            sections = config['cross_sections']
            if not isinstance(sections, list) or len(sections) < 2:
                result.add_error("cross_sections应为包含至少2个元素的列表")
            
            for i, section in enumerate(sections):
                required_fields = ['station', 'elevation', 'shape_type']
                for field in required_fields:
                    if field not in section:
                        result.add_error(f"断面{i}缺少必需字段: {field}")
    
    def _validate_simulation_preferences(self, config: Dict[str, Any], result: ValidationResult):
        """验证仿真偏好配置"""
        if 'default_method' in config:
            method = config['default_method']
            # 尝试验证是否为有效的仿真方法
            try:
                SimulationMethod(method)
            except ValueError:
                try:
                    PressurizedMethod(method)
                except ValueError:
                    result.add_error(f"无效的仿真方法: {method}")
    
    def _validate_boundary_conditions(self, config: Dict[str, Any], result: ValidationResult):
        """验证边界条件配置"""
        if 'upstream' in config:
            upstream = config['upstream']
            if not any(key in upstream for key in ['flow', 'level']):
                result.add_warning("上游边界条件应指定flow或level")
        
        if 'downstream' in config:
            downstream = config['downstream']
            if not any(key in downstream for key in ['flow', 'level']):
                result.add_warning("下游边界条件应指定flow或level")
    
    def _validate_object_specific(self, config: Dict[str, Any], 
                                 object_type: ObjectType, result: ValidationResult):
        """对象类型特定验证"""
        if object_type == ObjectType.CHANNEL:
            # 明渠特定验证 - 放宽要求
            if 'geometry_definition' not in config:
                result.add_warning("明渠对象建议提供geometry_definition配置")
        
        elif object_type == ObjectType.PIPE:
            # 管道特定验证 - 放宽要求
            basic_props = config.get('basic_properties', {})
            if 'diameter' not in basic_props and 'area' not in basic_props:
                result.add_warning("管道对象建议指定diameter或area")
        
        elif object_type == ObjectType.RESERVOIR:
            # 水库特定验证
            if 'capacity_curve' not in config:
                result.add_warning("水库对象建议提供capacity_curve配置")