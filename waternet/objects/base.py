"""
水系统对象基类

定义了所有水系统对象的统一抽象基类和核心子类。

基类层次：
- WaterSystemObject: 所有水系统对象的根基类
- ConveyanceObject: 输水对象基类（河道、管道、渠道、倒虹吸）
- StorageObject: 存储对象基类（水库、湖泊、调蓄池）

Features:
- 统一的对象接口和生命周期管理
- 配置驱动的对象创建和参数设置
- 多层次建模方法支持
- 数字孪生功能
- 可视化和结果管理

Author: WaterNet Development Team
Date: 2024-10-05
"""

import numpy as np
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union, Callable, Tuple
from datetime import datetime
import logging

from .core import (
    ObjectType, SimulationMethod, PressurizedMethod, 
    SpatialRepresentation, SPATIAL_REPRESENTATION_MAP,
    OPEN_CHANNEL_METHODS, PRESSURIZED_METHODS
)
from .config import ConfigManager, ValidationResult
from .state import StateManager, StateResult
from .results import ResultManager, ProfileData, VisualizationResult, ExportResult


class WaterSystemObject(ABC):
    """
    水系统对象抽象基类
    
    所有水系统对象的根基类，定义统一接口和通用功能。
    提供配置管理、状态管理、结果管理等核心功能。
    
    Features:
    - 统一的对象标识和类型管理
    - 配置驱动的参数设置
    - 状态变量管理和历史记录
    - 结果数据管理和可视化
    - 数字孪生对象支持
    - 阶跃响应分析
    
    Attributes:
        object_id (str): 对象唯一标识符
        object_type (ObjectType): 对象类型
        config (ConfigManager): 配置管理器
        state (StateManager): 状态管理器
        results (ResultManager): 结果管理器
        twin_object (Optional[WaterSystemObject]): 数字孪生对象引用
    """
    
    def __init__(self, object_id: str, object_type: ObjectType, 
                 config_path: Optional[str] = None, **kwargs):
        """
        初始化水系统对象
        
        Args:
            object_id: 对象唯一标识符
            object_type: 对象类型
            config_path: 配置文件路径
            **kwargs: 额外的初始化参数
        """
        # 基本属性
        self.object_id = object_id
        self.object_type = object_type
        self.logger = logging.getLogger(f"{__name__}.{object_id}")
        
        # 管理器初始化
        self.config = ConfigManager()
        self.state = StateManager(object_id)
        self.results = ResultManager(object_id)
        
        # 数字孪生支持
        self.twin_object: Optional[WaterSystemObject] = None
        self.is_twin = kwargs.get('is_twin', False)
        
        # 对象配置 - 优先级：外部配置 > 配置文件 > 默认配置
        self._object_config = {}
        self._load_configuration(config_path, **kwargs)
        
        # 验证配置
        validation_result = self.validate_config()
        if not validation_result.is_valid:
            error_msg = "; ".join(validation_result.errors)
            raise ValueError(f"对象配置验证失败: {error_msg}")
        
        # 延迟初始化标志，子类可以控制何时完成初始化
        self._initialization_completed = False
    
    def _load_configuration(self, config_path: Optional[str] = None, **kwargs):
        """
        加载对象配置，支持多种配置来源的优先级合并
        
        优先级：外部配置（kwargs中的config） > 配置文件 > 默认配置
        
        Args:
            config_path: 配置文件路径
            **kwargs: 额外参数，可能包含config配置
        """
        # 1. 首先设置默认配置
        self._object_config = self.config.create_object_config(
            self.object_id, self.object_type, **kwargs
        )
        
        # 2. 如果有配置文件，覆盖默认配置
        if config_path:
            self.load_config(config_path)
        
        # 3. 如果kwargs中有config，优先级最高
        if 'config' in kwargs:
            external_config = kwargs['config']
            if isinstance(external_config, dict):
                self._object_config.update(external_config)
    
    def complete_initialization(self):
        """
        完成对象初始化
        
        子类可以在准备就绪后调用此方法完成初始化
        """
        if not self._initialization_completed:
            self.initialize()
            self._initialization_completed = True
    
    def load_config(self, config_path: str) -> bool:
        """
        从配置文件加载对象参数
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            是否加载成功
        """
        try:
            self._object_config = self.config.load_config(config_path)
            self.logger.info(f"配置加载成功: {config_path}")
            return True
        except Exception as e:
            self.logger.error(f"配置加载失败: {e}")
            return False
    
    def validate_config(self) -> ValidationResult:
        """
        验证配置参数有效性
        
        Returns:
            验证结果
        """
        return self.config.validate_config(self._object_config, self.object_type)
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        初始化对象状态
        
        子类必须实现此方法来执行特定的初始化逻辑
        
        Returns:
            是否初始化成功
        """
        pass
    
    @abstractmethod
    def update_state(self, **kwargs) -> StateResult:
        """
        更新对象状态
        
        子类必须实现此方法来更新特定的状态变量
        
        Returns:
            状态更新结果
        """
        pass
    
    def get_profile(self) -> ProfileData:
        """
        获取纵剖面数据
        
        返回对象的纵向剖面信息，包括距离、高程、水位等
        
        Returns:
            纵剖面数据对象
        """
        # 默认实现，子类可以重写
        profile = self.results.get_profile_data()
        if profile is None:
            # 创建基本的剖面数据
            profile = ProfileData(
                distances=np.array([0.0]),
                elevations=np.array([0.0]),
                metadata={'object_id': self.object_id, 'object_type': self.object_type.value}
            )
        return profile
    
    def visualize(self, template: str = "default", **kwargs) -> VisualizationResult:
        """
        生成可视化图表
        
        Args:
            template: 可视化模板名称
            **kwargs: 额外的可视化参数
            
        Returns:
            可视化结果
        """
        return self.results.visualize(
            template=template, 
            object_type=self.object_type,
            **kwargs
        )
    
    def export_results(self, format: str = "csv", **kwargs) -> ExportResult:
        """
        导出计算结果
        
        Args:
            format: 导出格式
            **kwargs: 额外的导出参数
            
        Returns:
            导出结果
        """
        return self.results.export_results(format=format, **kwargs)
    
    def step_response(self, disturbance_type: str = "flow", 
                     magnitude: float = 10.0, 
                     duration: float = 3600.0) -> Dict[str, Any]:
        """
        执行阶跃响应分析
        
        Args:
            disturbance_type: 扰动类型
            magnitude: 扰动幅度
            duration: 分析持续时间
            
        Returns:
            响应分析结果
        """
        return self.results.step_response_analysis(
            disturbance_type=disturbance_type,
            magnitude=magnitude,
            duration=duration
        )
    
    def create_twin(self, model_type: Optional[str] = None, 
                   auto_identification: bool = True,
                   **kwargs) -> 'WaterSystemObject':
        """
        创建数字孪生对象
        
        Args:
            model_type: 孪生模型类型
            auto_identification: 是否自动参数辨识
            **kwargs: 额外的创建参数
            
        Returns:
            数字孪生对象
        """
        # 这是一个框架方法，具体实现需要在子类中完成
        raise NotImplementedError("子类必须实现create_twin方法")
    
    def get_object_info(self) -> Dict[str, Any]:
        """
        获取对象基本信息
        
        Returns:
            对象信息字典
        """
        return {
            'object_id': self.object_id,
            'object_type': self.object_type.value,
            'has_twin': self.twin_object is not None,
            'is_twin': self.is_twin,
            'config_summary': self._get_config_summary(),
            'state_summary': self._get_state_summary(),
            'model_info': self.get_model_info()
        }
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        获取底层模型状态信息
        
        这个方法封装了模型状态检查的通用逻辑，避免在示例代码中重复实现
        
        Returns:
            模型信息字典
        """
        # 检查子类是否有 underlying_model 属性
        if hasattr(self, 'underlying_model'):
            model = getattr(self, 'underlying_model')
            if model is not None:
                return {
                    'has_model': True,
                    'model_type': type(model).__name__,
                    'model_class': model.__class__.__module__ + '.' + model.__class__.__name__,
                    'is_initialized': True
                }
            else:
                return {
                    'has_model': False,
                    'model_type': None,
                    'model_class': None,
                    'is_initialized': False,
                    'reason': '底层模型未创建'
                }
        else:
            return {
                'has_model': False,
                'model_type': None,
                'model_class': None,
                'is_initialized': False,
                'reason': '对象不支持底层模型'
            }
    
    def _get_config_summary(self) -> Dict[str, Any]:
        """获取配置摘要"""
        return {
            'object_definition': self._object_config.get('object_definition', {}),
            'basic_properties': self._object_config.get('basic_properties', {}),
            'simulation_preferences': self._object_config.get('simulation_preferences', {})
        }
    
    def _get_state_summary(self) -> Dict[str, Any]:
        """获取状态摘要"""
        current_state = self.state.get_current_state()
        return {
            'instantaneous_vars': len(current_state.get('instantaneous', {})),
            'cumulative_vars': len(current_state.get('cumulative', {})),
            'last_update': current_state.get('system', {}).get('last_update'),
            'operation_mode': current_state.get('system', {}).get('operation_mode')
        }
    
    def __repr__(self) -> str:
        """对象的字符串表示"""
        return f"{self.__class__.__name__}(id='{self.object_id}', type='{self.object_type.value}')"
    
    def __str__(self) -> str:
        """对象的可读字符串表示"""
        return f"水系统对象 '{self.object_id}' ({self.object_type.value})"


class ConveyanceObject(WaterSystemObject):
    """
    输水对象基类
    
    所有输水对象（河道、管道、渠道、倒虹吸）的抽象基类。
    根据空间表示方式分为集总式对象和分布式对象。
    
    Features:
    - 多种仿真方法支持
    - 边界条件管理
    - 几何参数管理
    - 空间表示方式分类
    
    Attributes:
        simulation_method: 当前仿真方法
        spatial_representation: 空间表示方式（集总式/分布式）
        boundaries: 边界条件管理器
        geometry: 几何参数管理器
    """
    
    def __init__(self, object_id: str, object_type: ObjectType, **kwargs):
        """
        初始化输水对象
        
        Args:
            object_id: 对象唯一标识符
            object_type: 对象类型
            **kwargs: 额外的初始化参数
        """
        super().__init__(object_id, object_type, **kwargs)
        
        # 仿真方法相关
        self.simulation_method: Optional[Union[SimulationMethod, PressurizedMethod]] = None
        self.spatial_representation: Optional[SpatialRepresentation] = None
        
        # 边界条件和几何参数
        self.boundaries = {}
        self.geometry = {}
        
        # 根据对象类型设置支持的方法
        self.supported_methods = self._get_supported_methods()
        
        # 设置仿真方法（优先使用配置中的方法）
        self._setup_simulation_method()
        
        # 完成初始化
        self.complete_initialization()
    
    def _get_supported_methods(self) -> List[Union[SimulationMethod, PressurizedMethod]]:
        """获取对象支持的仿真方法"""
        if self.object_type in OPEN_CHANNEL_METHODS:
            return OPEN_CHANNEL_METHODS[self.object_type]
        elif self.object_type in PRESSURIZED_METHODS:
            return PRESSURIZED_METHODS[self.object_type]
        else:
            return []
    
    def _setup_simulation_method(self):
        """
        设置仿真方法，优先使用配置中的方法
        """
        # 优先使用配置中的方法
        default_method = self._object_config.get('simulation_preferences', {}).get('default_method')
        if default_method:
            if self.set_simulation_method(default_method):
                return  # 设置成功，返回
        
        # 如果配置中没有指定或设置失败，使用默认方法
        if self.supported_methods:
            self.simulation_method = self.supported_methods[0]
            self.spatial_representation = SPATIAL_REPRESENTATION_MAP.get(self.simulation_method)
    
    def set_simulation_method(self, method: Union[str, SimulationMethod, PressurizedMethod]) -> bool:
        """
        设置仿真方法
        
        Args:
            method: 仿真方法
            
        Returns:
            是否设置成功
        """
        # 字符串转换为枚举
        if isinstance(method, str):
            # 尝试明渠方法
            try:
                method = SimulationMethod(method)
            except ValueError:
                # 尝试有压方法
                try:
                    method = PressurizedMethod(method)
                except ValueError:
                    self.logger.error(f"无效的仿真方法: {method}")
                    return False
        
        # 验证方法是否支持
        if method not in self.supported_methods:
            self.logger.error(f"对象类型 {self.object_type} 不支持方法 {method}")
            return False
        
        self.simulation_method = method
        self.spatial_representation = SPATIAL_REPRESENTATION_MAP.get(method)
        
        self.logger.info(f"仿真方法设置为: {method.value}")
        return True
    
    def set_upstream_boundary(self, **conditions):
        """
        设置上游边界条件
        
        Args:
            **conditions: 边界条件参数（flow, level, pressure等）
        """
        self.boundaries['upstream'] = conditions
        self.state.update_state({
            'boundary': {f'BC_upstream_{k}': v for k, v in conditions.items()}
        })
    
    def set_downstream_boundary(self, **conditions):
        """
        设置下游边界条件
        
        Args:
            **conditions: 边界条件参数（flow, level, pressure等）
        """
        self.boundaries['downstream'] = conditions
        self.state.update_state({
            'boundary': {f'BC_downstream_{k}': v for k, v in conditions.items()}
        })
    
    @abstractmethod
    def solve_steady_flow(self) -> Dict[str, Any]:
        """
        恒定流计算
        
        子类必须实现此方法
        
        Returns:
            恒定流计算结果
        """
        pass
    
    def get_longitudinal_profile(self) -> ProfileData:
        """
        获取纵剖面数据
        
        Returns:
            纵剖面数据
        """
        return self.get_profile()
    
    def initialize(self) -> bool:
        """初始化输水对象"""
        try:
            # 初始化几何参数
            self._initialize_geometry()
            
            # 初始化边界条件
            self._initialize_boundaries()
            
            # 初始化状态变量
            self._initialize_state_variables()
            
            return True
        except Exception as e:
            self.logger.error(f"初始化失败: {e}")
            return False
    
    def _initialize_geometry(self):
        """初始化几何参数"""
        # 确保geometry属性存在（防止初始化顺序问题）
        if not hasattr(self, 'geometry'):
            self.geometry = {}
            
        basic_props = self._object_config.get('basic_properties', {})
        geometry_def = self._object_config.get('geometry_definition', {})
        
        self.geometry.update(basic_props)
        self.geometry.update(geometry_def)
    
    def _initialize_boundaries(self):
        """初始化边界条件"""
        boundary_config = self._object_config.get('boundary_conditions', {})
        
        if 'upstream' in boundary_config:
            self.set_upstream_boundary(**boundary_config['upstream'])
        
        if 'downstream' in boundary_config:
            self.set_downstream_boundary(**boundary_config['downstream'])
    
    def _initialize_state_variables(self):
        """初始化状态变量"""
        # 基本状态变量
        initial_state = {
            'instantaneous': {
                'Q_in': 0.0,
                'Q_out': 0.0,
                'H_upstream': 0.0,
                'H_downstream': 0.0
            },
            'cumulative': {
                'V_total': 0.0,
                'total_inflow': 0.0,
                'total_outflow': 0.0
            }
        }
        
        self.state.update_state(initial_state)


class StorageObject(WaterSystemObject):
    """
    存储对象基类
    
    水库、湖泊、调蓄池等存储对象的抽象基类。
    
    Features:
    - 库容曲线管理
    - 水量平衡计算
    - 运行规则应用
    - 线性化降阶模型
    
    Attributes:
        capacity_curve: 库容曲线函数
        water_balance: 水量平衡计算器
        operation_rules: 运行规则
    """
    
    def __init__(self, object_id: str, object_type: ObjectType, **kwargs):
        """
        初始化存储对象
        
        Args:
            object_id: 对象唯一标识符
            object_type: 对象类型
            **kwargs: 额外的初始化参数
        """
        super().__init__(object_id, object_type, **kwargs)
        
        # 存储对象特有属性
        self.capacity_curve: Optional[Callable[[float], float]] = None
        self.water_balance = {}
        self.operation_rules = {}
        
        # 设置默认的库容曲线
        self._setup_capacity_curve()
    
    def _setup_capacity_curve(self):
        """设置库容曲线"""
        capacity_config = self._object_config.get('capacity_curve', {})
        
        if 'points' in capacity_config:
            # 基于离散点的库容曲线
            points = capacity_config['points']
            levels = [p['level'] for p in points]
            volumes = [p['volume'] for p in points]
            
            # 创建插值函数
            from scipy.interpolate import interp1d
            self.capacity_curve = interp1d(
                volumes, levels, 
                kind='linear', 
                fill_value='extrapolate'
            )
        else:
            # 默认线性库容曲线
            base_level = capacity_config.get('base_level', 0.0)
            area = capacity_config.get('surface_area', 1000.0)
            
            self.capacity_curve = lambda V: base_level + V / area
    
    @abstractmethod
    def compute_water_balance(self, **kwargs) -> Dict[str, Any]:
        """
        水量平衡计算
        
        子类必须实现此方法
        
        Returns:
            水量平衡计算结果
        """
        pass
    
    def update_storage(self, volume_change: float) -> StateResult:
        """
        更新蓄水量
        
        Args:
            volume_change: 蓄水量变化
            
        Returns:
            状态更新结果
        """
        current_volume = self.state.get_current_state('cumulative').get('V_storage', 0.0)
        new_volume = max(0.0, current_volume + volume_change)
        
        # 计算对应的水位（安全访问capacity_curve属性）
        if hasattr(self, 'capacity_curve') and self.capacity_curve:
            new_level = self.capacity_curve(new_volume)
        else:
            new_level = 0.0
        
        # 更新状态
        return self.state.update_state({
            'cumulative': {'V_storage': new_volume},
            'instantaneous': {'H_level': new_level}
        })
    
    def apply_operation_rules(self, **conditions) -> Dict[str, Any]:
        """
        应用运行规则
        
        Args:
            **conditions: 运行条件
            
        Returns:
            运行规则应用结果
        """
        # 这是一个框架方法，子类可以重写实现具体的运行规则
        return {
            'action': 'none',
            'reason': 'no operation rules defined',
            'conditions': conditions
        }
    
    def initialize(self) -> bool:
        """初始化存储对象"""
        try:
            # 初始化存储参数
            self._initialize_storage_parameters()
            
            # 初始化水量平衡
            self._initialize_water_balance()
            
            # 初始化状态变量
            self._initialize_state_variables()
            
            return True
        except Exception as e:
            self.logger.error(f"初始化失败: {e}")
            return False
    
    def _initialize_storage_parameters(self):
        """初始化存储参数"""
        # 确保water_balance属性存在（防止初始化顺序问题）
        if not hasattr(self, 'water_balance'):
            self.water_balance = {}
            
        basic_props = self._object_config.get('basic_properties', {})
        
        # 设置基本存储参数
        self.water_balance['initial_volume'] = basic_props.get('initial_volume', 0.0)
        self.water_balance['max_volume'] = basic_props.get('max_volume', 1e6)
        self.water_balance['min_volume'] = basic_props.get('min_volume', 0.0)
    
    def _initialize_water_balance(self):
        """初始化水量平衡"""
        # 确保water_balance属性存在（防止初始化顺序问题）
        if not hasattr(self, 'water_balance'):
            self.water_balance = {}
        
        # 设置水量平衡参数
        self.water_balance.update({
            'inflow_rate': 0.0,
            'outflow_rate': 0.0,
            'evaporation_rate': 0.0,
            'precipitation_rate': 0.0
        })
    
    def _initialize_state_variables(self):
        """初始化状态变量"""
        initial_volume = self.water_balance.get('initial_volume', 0.0)
        
        # 安全访问capacity_curve属性（防止初始化顺序问题）
        if hasattr(self, 'capacity_curve') and self.capacity_curve:
            initial_level = self.capacity_curve(initial_volume)
        else:
            initial_level = 0.0
        
        initial_state = {
            'cumulative': {
                'V_storage': initial_volume,
                'total_inflow': 0.0,
                'total_outflow': 0.0
            },
            'instantaneous': {
                'H_level': initial_level,
                'Q_inflow': 0.0,
                'Q_outflow': 0.0
            }
        }
        
        self.state.update_state(initial_state)
    
    def update_state(self, **kwargs) -> StateResult:
        """更新存储对象状态"""
        # 处理流量变化
        if 'inflow' in kwargs:
            self.water_balance['inflow_rate'] = kwargs['inflow']
        
        if 'outflow' in kwargs:
            self.water_balance['outflow_rate'] = kwargs['outflow']
        
        # 计算蓄量变化
        dt = kwargs.get('dt', 1.0)
        net_flow = (self.water_balance['inflow_rate'] - 
                   self.water_balance['outflow_rate'])
        volume_change = net_flow * dt
        
        # 更新蓄水量
        return self.update_storage(volume_change)