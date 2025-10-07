"""
配置驱动的边界条件模块

实现YAML配置文件驱动的边界条件和控制调度管理。
支持从配置文件创建复杂的边界条件组合和时变控制策略。

设计原则:
1. 声明式配置: 通过YAML文件描述边界条件
2. 类型安全: 强类型配置验证和解析
3. 灵活组合: 支持多种边界条件和控制设备组合
4. 默认值: 合理的默认值和配置简化

主要组件:
- BoundaryConfigParser: 配置解析器
- ControlConfigParser: 控制配置解析器
- ConfigValidator: 配置验证器
- ConfigFactory: 配置工厂类

Author: WaterNet Development Team
Date: 2024-10-04
"""

import yaml
from typing import Dict, List, Any, Optional, Union, Callable, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import logging
from datetime import datetime
import numpy as np

from .boundary_conditions import (
    BoundaryCondition, FlowBoundary, StageBoundary, RatingCurveBoundary,
    BoundaryConditionManager, BoundaryConditionConfig,
    create_time_series_function, create_periodic_function, create_step_function
)
from .control_signals import (
    ControlDevice, GateDevice, PumpDevice, ValveDevice,
    ControlSignalManager, ControlSchedule, ControlDeviceType,
    create_gate_device, create_pump_device, create_valve_device
)


@dataclass 
class ConfigMetadata:
    """配置元数据"""
    version: str = "1.0"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    description: str = ""
    author: str = ""
    
    
class ConfigValidator:
    """
    配置验证器
    
    验证YAML配置文件的格式和内容有效性。
    """
    
    def __init__(self):
        """初始化配置验证器"""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.errors = []
        self.warnings = []
    
    def validate_boundary_config(self, config: Dict[str, Any]) -> bool:
        """
        验证边界条件配置
        
        Args:
            config (Dict[str, Any]): 边界条件配置字典
            
        Returns:
            bool: True表示配置有效
        """
        self.errors.clear()
        self.warnings.clear()
        
        # 验证必需字段
        if 'boundary_conditions' not in config:
            self.errors.append("缺少 'boundary_conditions' 字段")
            return False
        
        boundary_conditions = config['boundary_conditions']
        if not isinstance(boundary_conditions, list):
            self.errors.append("'boundary_conditions' 必须是列表")
            return False
        
        # 验证每个边界条件
        for i, bc_config in enumerate(boundary_conditions):
            self._validate_single_boundary_condition(bc_config, i)
        
        # 验证控制配置（如果存在）
        if 'control_signals' in config:
            self._validate_control_config(config['control_signals'])
        
        if self.errors:
            self.logger.error(f"配置验证失败: {len(self.errors)} 个错误")
            for error in self.errors:
                self.logger.error(f"  - {error}")
            return False
        
        if self.warnings:
            self.logger.warning(f"配置验证警告: {len(self.warnings)} 个警告")
            for warning in self.warnings:
                self.logger.warning(f"  - {warning}")
        
        return True
    
    def _validate_single_boundary_condition(self, bc_config: Dict[str, Any], index: int):
        """验证单个边界条件配置"""
        prefix = f"边界条件[{index}]"
        
        # 验证必需字段
        required_fields = ['name', 'type']
        for field in required_fields:
            if field not in bc_config:
                self.errors.append(f"{prefix}: 缺少必需字段 '{field}'")
        
        # 验证类型
        bc_type = bc_config.get('type')
        valid_types = ['flow_boundary', 'stage_boundary', 'rating_curve_boundary']
        if bc_type not in valid_types:
            self.errors.append(f"{prefix}: 无效的边界条件类型 '{bc_type}', 有效类型: {valid_types}")
        
        # 根据类型验证特定字段
        if bc_type == 'flow_boundary':
            self._validate_flow_boundary_config(bc_config, prefix)
        elif bc_type == 'stage_boundary':
            self._validate_stage_boundary_config(bc_config, prefix)
        elif bc_type == 'rating_curve_boundary':
            self._validate_rating_curve_config(bc_config, prefix)
    
    def _validate_flow_boundary_config(self, config: Dict[str, Any], prefix: str):
        """验证流量边界条件配置"""
        if 'node_name' not in config:
            self.errors.append(f"{prefix}: 流量边界条件缺少 'node_name'")
        
        if 'flow_value' not in config and 'flow_function' not in config:
            self.errors.append(f"{prefix}: 流量边界条件必须指定 'flow_value' 或 'flow_function'")
        
        # 验证流量函数配置
        if 'flow_function' in config:
            self._validate_function_config(config['flow_function'], f"{prefix}.flow_function")
    
    def _validate_stage_boundary_config(self, config: Dict[str, Any], prefix: str):
        """验证水位边界条件配置"""
        if 'node_name' not in config:
            self.errors.append(f"{prefix}: 水位边界条件缺少 'node_name'")
        
        if 'stage_value' not in config and 'stage_function' not in config:
            self.errors.append(f"{prefix}: 水位边界条件必须指定 'stage_value' 或 'stage_function'")
        
        # 验证水位函数配置
        if 'stage_function' in config:
            self._validate_function_config(config['stage_function'], f"{prefix}.stage_function")
    
    def _validate_rating_curve_config(self, config: Dict[str, Any], prefix: str):
        """验证水位流量关系配置"""
        required_fields = ['flow_node', 'stage_node', 'curve_type']
        for field in required_fields:
            if field not in config:
                self.errors.append(f"{prefix}: 水位流量关系缺少 '{field}'")
        
        curve_type = config.get('curve_type')
        valid_curve_types = ['polynomial', 'weir', 'custom']
        if curve_type not in valid_curve_types:
            self.errors.append(f"{prefix}: 无效的曲线类型 '{curve_type}', 有效类型: {valid_curve_types}")
        
        if 'curve_params' not in config:
            self.warnings.append(f"{prefix}: 缺少 'curve_params', 将使用默认参数")
    
    def _validate_function_config(self, func_config: Dict[str, Any], prefix: str):
        """验证函数配置"""
        if 'type' not in func_config:
            self.errors.append(f"{prefix}: 函数配置缺少 'type'")
            return
        
        func_type = func_config['type']
        valid_func_types = ['constant', 'time_series', 'periodic', 'step']
        if func_type not in valid_func_types:
            self.errors.append(f"{prefix}: 无效的函数类型 '{func_type}', 有效类型: {valid_func_types}")
    
    def _validate_control_config(self, control_config: Dict[str, Any]):
        """验证控制配置"""
        if 'devices' in control_config:
            devices = control_config['devices']
            if not isinstance(devices, list):
                self.errors.append("control_signals.devices 必须是列表")
            else:
                for i, device_config in enumerate(devices):
                    self._validate_device_config(device_config, i)
        
        if 'schedule' in control_config:
            self._validate_schedule_config(control_config['schedule'])
    
    def _validate_device_config(self, device_config: Dict[str, Any], index: int):
        """验证设备配置"""
        prefix = f"控制设备[{index}]"
        
        required_fields = ['device_id', 'device_type']
        for field in required_fields:
            if field not in device_config:
                self.errors.append(f"{prefix}: 缺少必需字段 '{field}'")
        
        device_type = device_config.get('device_type')
        valid_device_types = ['gate', 'pump', 'valve']
        if device_type not in valid_device_types:
            self.errors.append(f"{prefix}: 无效的设备类型 '{device_type}', 有效类型: {valid_device_types}")
    
    def _validate_schedule_config(self, schedule_config: Dict[str, Any]):
        """验证调度配置"""
        if 'type' not in schedule_config:
            self.errors.append("调度配置缺少 'type'")
            return
        
        schedule_type = schedule_config['type']
        valid_schedule_types = ['time_series', 'step_schedule', 'csv_file']
        if schedule_type not in valid_schedule_types:
            self.errors.append(f"无效的调度类型 '{schedule_type}', 有效类型: {valid_schedule_types}")


class BoundaryConfigParser:
    """
    边界条件配置解析器
    
    解析YAML配置文件并创建边界条件对象。
    """
    
    def __init__(self):
        """初始化边界条件配置解析器"""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.validator = ConfigValidator()
    
    def parse_from_file(self, config_file: Union[str, Path]) -> BoundaryConditionManager:
        """
        从配置文件解析边界条件
        
        Args:
            config_file (Union[str, Path]): 配置文件路径
            
        Returns:
            BoundaryConditionManager: 边界条件管理器
            
        Raises:
            FileNotFoundError: 配置文件不存在
            yaml.YAMLError: YAML格式错误
            ValueError: 配置内容无效
        """
        config_path = Path(config_file)
        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        
        self.logger.info(f"解析边界条件配置文件: {config_path}")
        
        # 读取YAML文件
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"YAML格式错误: {e}")
        
        return self.parse_from_dict(config)
    
    def parse_from_dict(self, config: Dict[str, Any]) -> BoundaryConditionManager:
        """
        从配置字典解析边界条件
        
        Args:
            config (Dict[str, Any]): 配置字典
            
        Returns:
            BoundaryConditionManager: 边界条件管理器
        """
        # 验证配置
        if not self.validator.validate_boundary_config(config):
            raise ValueError("边界条件配置验证失败")
        
        # 创建边界条件管理器
        boundary_manager = BoundaryConditionManager()
        
        # 解析边界条件
        boundary_conditions = config.get('boundary_conditions', [])
        for bc_config in boundary_conditions:
            boundary_condition = self._create_boundary_condition(bc_config)
            boundary_manager.add_boundary_condition(boundary_condition)
        
        self.logger.info(f"成功解析 {len(boundary_conditions)} 个边界条件")
        
        return boundary_manager
    
    def _create_boundary_condition(self, bc_config: Dict[str, Any]) -> BoundaryCondition:
        """创建单个边界条件"""
        bc_type = bc_config['type']
        name = bc_config['name']
        
        # 创建配置对象
        description = bc_config.get('description', f"{bc_type} - {name}")
        enabled = bc_config.get('enabled', True)
        config_obj = BoundaryConditionConfig(
            name=name,
            description=description,
            enabled=enabled
        )
        
        if bc_type == 'flow_boundary':
            return self._create_flow_boundary(bc_config, config_obj)
        elif bc_type == 'stage_boundary':
            return self._create_stage_boundary(bc_config, config_obj)
        elif bc_type == 'rating_curve_boundary':
            return self._create_rating_curve_boundary(bc_config, config_obj)
        else:
            raise ValueError(f"不支持的边界条件类型: {bc_type}")
    
    def _create_flow_boundary(self, bc_config: Dict[str, Any], 
                            config_obj: BoundaryConditionConfig) -> FlowBoundary:
        """创建流量边界条件"""
        node_name = bc_config['node_name']
        
        # 处理流量值
        if 'flow_value' in bc_config:
            flow_value = float(bc_config['flow_value'])
        elif 'flow_function' in bc_config:
            flow_value = self._create_function(bc_config['flow_function'])
        else:
            flow_value = 0.0
        
        return FlowBoundary(config_obj.name, node_name, flow_value, config_obj)
    
    def _create_stage_boundary(self, bc_config: Dict[str, Any],
                             config_obj: BoundaryConditionConfig) -> StageBoundary:
        """创建水位边界条件"""
        node_name = bc_config['node_name']
        
        # 处理水位值
        if 'stage_value' in bc_config:
            stage_value = float(bc_config['stage_value'])
        elif 'stage_function' in bc_config:
            stage_value = self._create_function(bc_config['stage_function'])
        else:
            stage_value = 100.0
        
        return StageBoundary(config_obj.name, node_name, stage_value, config_obj)
    
    def _create_rating_curve_boundary(self, bc_config: Dict[str, Any],
                                    config_obj: BoundaryConditionConfig) -> RatingCurveBoundary:
        """创建水位流量关系边界条件"""
        flow_node = bc_config['flow_node']
        stage_node = bc_config['stage_node']
        curve_type = bc_config['curve_type']
        curve_params = bc_config.get('curve_params', {})
        
        return RatingCurveBoundary(
            config_obj.name, flow_node, stage_node, 
            curve_type, curve_params, config_obj
        )
    
    def _create_function(self, func_config: Dict[str, Any]) -> Callable[[float], float]:
        """创建时变函数"""
        func_type = func_config['type']
        
        if func_type == 'constant':
            value = float(func_config.get('value', 0.0))
            return lambda t: value
        
        elif func_type == 'time_series':
            times = func_config['times']
            values = func_config['values']
            interpolation = func_config.get('interpolation', 'linear')
            return create_time_series_function(times, values, interpolation)
        
        elif func_type == 'periodic':
            amplitude = float(func_config.get('amplitude', 1.0))
            period = float(func_config.get('period', 3600.0))
            phase = float(func_config.get('phase', 0.0))
            offset = float(func_config.get('offset', 0.0))
            return create_periodic_function(amplitude, period, phase, offset)
        
        elif func_type == 'step':
            step_time = float(func_config.get('step_time', 0.0))
            value_before = float(func_config.get('value_before', 0.0))
            value_after = float(func_config.get('value_after', 1.0))
            return create_step_function(step_time, value_before, value_after)
        
        else:
            raise ValueError(f"不支持的函数类型: {func_type}")


class ControlConfigParser:
    """
    控制配置解析器
    
    解析控制设备和调度配置。
    """
    
    def __init__(self):
        """初始化控制配置解析器"""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def parse_control_config(self, config: Dict[str, Any]) -> ControlSignalManager:
        """
        解析控制配置
        
        Args:
            config (Dict[str, Any]): 控制配置字典
            
        Returns:
            ControlSignalManager: 控制信号管理器
        """
        control_manager = ControlSignalManager()
        
        # 解析控制设备
        if 'devices' in config:
            devices_config = config['devices']
            for device_config in devices_config:
                device = self._create_control_device(device_config)
                control_manager.add_device(device)
        
        # 解析控制调度
        if 'schedule' in config:
            schedule = self._create_control_schedule(config['schedule'])
            control_manager.set_schedule(schedule)
        
        return control_manager
    
    def _create_control_device(self, device_config: Dict[str, Any]) -> ControlDevice:
        """创建控制设备"""
        device_id = device_config['device_id']
        device_type = device_config['device_type']
        
        min_value = float(device_config.get('min_value', 0.0))
        max_value = float(device_config.get('max_value', 1.0))
        default_value = float(device_config.get('default_value', 0.0))
        
        if device_type == 'gate':
            return create_gate_device(device_id, min_value, max_value, default_value)
        elif device_type == 'pump':
            return create_pump_device(device_id, min_value, max_value, default_value)
        elif device_type == 'valve':
            return create_valve_device(device_id, min_value, max_value, default_value)
        else:
            raise ValueError(f"不支持的设备类型: {device_type}")
    
    def _create_control_schedule(self, schedule_config: Dict[str, Any]) -> ControlSchedule:
        """创建控制调度"""
        schedule_type = schedule_config['type']
        interpolation = schedule_config.get('interpolation', 'linear')
        
        if schedule_type == 'time_series':
            data = schedule_config['data']
            return ControlSchedule(data, interpolation)
        
        elif schedule_type == 'step_schedule':
            devices = schedule_config['devices']
            step_times = schedule_config['step_times']
            step_values = schedule_config['step_values']
            return ControlSchedule.create_step_schedule(devices, step_times, step_values, interpolation)
        
        elif schedule_type == 'csv_file':
            csv_file = schedule_config['file']
            time_column = schedule_config.get('time_column', 'time')
            return ControlSchedule.from_csv(csv_file, time_column, interpolation)
        
        else:
            raise ValueError(f"不支持的调度类型: {schedule_type}")


class ConfigFactory:
    """
    配置工厂类
    
    提供便捷的配置创建和管理功能。
    """
    
    def __init__(self):
        """初始化配置工厂"""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.boundary_parser = BoundaryConfigParser()
        self.control_parser = ControlConfigParser()
    
    def create_from_config_file(self, config_file: Union[str, Path]) -> Tuple[BoundaryConditionManager, ControlSignalManager]:
        """
        从配置文件创建完整的边界条件和控制系统
        
        Args:
            config_file (Union[str, Path]): 配置文件路径
            
        Returns:
            Tuple[BoundaryConditionManager, ControlSignalManager]: 边界条件管理器和控制信号管理器
        """
        config_path = Path(config_file)
        self.logger.info(f"从配置文件创建系统: {config_path}")
        
        # 读取配置
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 创建边界条件管理器
        boundary_manager = BoundaryConditionManager()
        if 'boundary_conditions' in config:
            boundary_manager = self.boundary_parser.parse_from_dict(config)
        
        # 创建控制信号管理器
        control_manager = ControlSignalManager()
        if 'control_signals' in config:
            control_manager = self.control_parser.parse_control_config(config['control_signals'])
        
        return boundary_manager, control_manager
    
    def save_config_template(self, output_file: Union[str, Path]):
        """
        保存配置模板文件
        
        Args:
            output_file (Union[str, Path]): 输出文件路径
        """
        template = self._create_config_template()
        
        output_path = Path(output_file)
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(template, f, default_flow_style=False, allow_unicode=True, indent=2)
        
        self.logger.info(f"配置模板已保存到: {output_path}")
    
    def _create_config_template(self) -> Dict[str, Any]:
        """创建配置模板"""
        return {
            'metadata': {
                'version': '1.0',
                'description': 'WaterNet边界条件和控制信号配置模板',
                'author': 'WaterNet用户',
                'created_at': datetime.now().isoformat()
            },
            'boundary_conditions': [
                {
                    'name': '上游流量边界',
                    'type': 'flow_boundary',
                    'description': '上游入流边界条件',
                    'enabled': True,
                    'node_name': '上游节点',
                    'flow_function': {
                        'type': 'time_series',
                        'times': [0, 3600, 7200],
                        'values': [50.0, 60.0, 55.0],
                        'interpolation': 'linear'
                    }
                },
                {
                    'name': '下游水位边界',
                    'type': 'stage_boundary', 
                    'description': '下游水位边界条件',
                    'enabled': True,
                    'node_name': '下游节点',
                    'stage_value': 100.0
                },
                {
                    'name': '堰流关系',
                    'type': 'rating_curve_boundary',
                    'description': '堰流水位流量关系',
                    'enabled': True,
                    'flow_node': '出口流量',
                    'stage_node': '出口水位',
                    'curve_type': 'weir',
                    'curve_params': {
                        'discharge_coefficient': 2.5,
                        'reference_level': 99.0,
                        'exponent': 1.5
                    }
                }
            ],
            'control_signals': {
                'devices': [
                    {
                        'device_id': '主闸门',
                        'device_type': 'gate',
                        'min_value': 0.0,
                        'max_value': 1.0,
                        'default_value': 0.5
                    },
                    {
                        'device_id': '辅助泵',
                        'device_type': 'pump',
                        'min_value': 0.0,
                        'max_value': 1.0,
                        'default_value': 0.0
                    }
                ],
                'schedule': {
                    'type': 'step_schedule',
                    'devices': ['主闸门', '辅助泵'],
                    'step_times': [0, 1800, 3600],
                    'step_values': [
                        {'主闸门': 0.5, '辅助泵': 0.0},
                        {'主闸门': 0.8, '辅助泵': 0.5},
                        {'主闸门': 1.0, '辅助泵': 1.0}
                    ],
                    'interpolation': 'linear'
                }
            }
        }


# 便捷函数
def load_boundary_config(config_file: Union[str, Path]) -> BoundaryConditionManager:
    """
    从配置文件加载边界条件的便捷函数
    
    Args:
        config_file (Union[str, Path]): 配置文件路径
        
    Returns:
        BoundaryConditionManager: 边界条件管理器
    """
    parser = BoundaryConfigParser()
    return parser.parse_from_file(config_file)


def load_control_config(config_file: Union[str, Path]) -> ControlSignalManager:
    """
    从配置文件加载控制配置的便捷函数
    
    Args:
        config_file (Union[str, Path]): 配置文件路径
        
    Returns:
        ControlSignalManager: 控制信号管理器
    """
    config_path = Path(config_file)
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    if 'control_signals' not in config:
        raise ValueError("配置文件中缺少 'control_signals' 部分")
    
    parser = ControlConfigParser()
    return parser.parse_control_config(config['control_signals'])


def create_complete_system(config_file: Union[str, Path]) -> Tuple[BoundaryConditionManager, ControlSignalManager]:
    """
    从配置文件创建完整系统的便捷函数
    
    Args:
        config_file (Union[str, Path]): 配置文件路径
        
    Returns:
        Tuple[BoundaryConditionManager, ControlSignalManager]: 管理器元组
    """
    factory = ConfigFactory()
    return factory.create_from_config_file(config_file)


def generate_config_template(output_file: Union[str, Path]):
    """
    生成配置模板文件的便捷函数
    
    Args:
        output_file (Union[str, Path]): 输出文件路径
    """
    factory = ConfigFactory()
    factory.save_config_template(output_file)