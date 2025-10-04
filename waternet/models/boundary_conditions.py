"""
边界条件框架

实现灵活可配置的边界条件框架，支持多种边界条件类型和时变控制信号。
通过抽象化设计实现边界条件的统一管理和动态配置。

设计原则:
1. 统一接口: 所有边界条件使用相同的方法签名
2. 类型安全: 明确的变量类型和返回值规范  
3. 动态性: 支持时变控制信号和外部调度
4. 可扩展: 支持自定义边界条件类型

主要组件:
- BoundaryCondition: 抽象基类，定义统一接口
- FlowBoundary: 流量边界条件
- StageBoundary: 水位边界条件  
- RatingCurveBoundary: 水位流量关系边界条件
- BoundaryConditionManager: 边界条件管理器

Author: WaterNet Development Team
Date: 2024-10-04
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Optional, Union, Callable, Any
from dataclasses import dataclass
import numpy as np
import pandas as pd
from scipy.interpolate import interp1d
import logging


@dataclass
class BoundaryConditionConfig:
    """边界条件配置基类"""
    name: str
    description: str = ""
    enabled: bool = True


class BoundaryCondition(ABC):
    """
    边界条件抽象基类
    
    定义所有边界条件的统一接口，包括方程生成、变量验证等核心功能。
    所有具体的边界条件类都必须继承此抽象基类。
    
    核心方法:
    - get_equation: 返回边界条件方程 (变量名, 残差值)
    - validate_variables: 验证所需变量是否存在
    - get_required_variables: 获取所需变量列表
    
    设计原则:
    - 统一接口: 所有边界条件使用相同的方法签名
    - 方程表示: 通过(变量名, 残差值)元组描述边界约束
    - 类型安全: 明确的变量类型和返回值规范
    """
    
    def __init__(self, name: str, config: BoundaryConditionConfig):
        """
        初始化边界条件
        
        Args:
            name (str): 边界条件唯一标识符
            config (BoundaryConditionConfig): 边界条件配置
        """
        self.name = name
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # 验证配置
        if not name or not isinstance(name, str):
            raise ValueError("边界条件名称必须是非空字符串")
        
        if not isinstance(config, BoundaryConditionConfig):
            raise ValueError("配置必须是BoundaryConditionConfig类型")
    
    @abstractmethod
    def get_equation(self, variables: Dict[str, float], time: float = 0.0) -> Tuple[str, float]:
        """
        获取边界条件方程
        
        这是核心接口方法，返回边界条件约束方程。方程以残差形式表示，
        残差为0表示边界条件得到满足。
        
        Args:
            variables (Dict[str, float]): 当前时步的所有变量值
                格式: {'H_Node1': 100.5, 'Q_Pipe1': 1.0, ...}
            time (float): 当前时间（秒），用于时变边界条件
        
        Returns:
            Tuple[str, float]: (方程名, 残差值)
                例如: ('boundary_flow_Node1', Q_node - Q_target)
        
        Note:
            - 残差单位应与对应的物理量一致
            - 残差值在合理的数值范围内（避免过大或过小）
        """
        pass
    
    @abstractmethod
    def get_required_variables(self) -> List[str]:
        """
        获取边界条件所需的变量列表
        
        Returns:
            List[str]: 所需变量名称列表
                例如: ['H_Node1', 'Q_Pipe1']
        """
        pass
    
    def validate_variables(self, variables: Dict[str, float]) -> bool:
        """
        验证变量完整性
        
        检查variables中是否包含所有必需的变量。
        
        Args:
            variables (Dict[str, float]): 待验证的变量字典
            
        Returns:
            bool: True表示变量完整，False表示缺少必需变量
        """
        required_vars = self.get_required_variables()
        missing_vars = [var for var in required_vars if var not in variables]
        
        if missing_vars:
            self.logger.warning(f"边界条件 {self.name} 缺少变量: {missing_vars}")
            return False
        
        return True
    
    def is_enabled(self) -> bool:
        """检查边界条件是否启用"""
        return self.config.enabled
    
    def __repr__(self) -> str:
        """边界条件的字符串表示"""
        return f"{self.__class__.__name__}(name='{self.name}', enabled={self.is_enabled()})"


class FlowBoundary(BoundaryCondition):
    """
    流量边界条件
    
    指定节点的流量值约束，支持恒定流量和时变流量。
    方程形式: Q_node - flow_value(t) = 0
    
    适用场景:
    - 上游流量边界
    - 泵站出流指定
    - 入流控制点
    """
    
    def __init__(self, name: str, node_name: str, 
                 flow_value: Union[float, Callable[[float], float]],
                 config: Optional[BoundaryConditionConfig] = None):
        """
        初始化流量边界条件
        
        Args:
            name (str): 边界条件名称
            node_name (str): 节点名称
            flow_value (Union[float, Callable]): 流量值或时变函数
            config (BoundaryConditionConfig, optional): 配置
        """
        if config is None:
            config = BoundaryConditionConfig(name=name, description=f"流量边界条件 - 节点 {node_name}")
        
        super().__init__(name, config)
        
        self.node_name = node_name
        self.flow_variable = f"Q_{node_name}"
        
        # 处理流量值
        if callable(flow_value):
            self.flow_func = flow_value
        else:
            self.flow_func = lambda t: float(flow_value)
        
        self.logger.info(f"创建流量边界条件: {name} -> {node_name}")
    
    def get_equation(self, variables: Dict[str, float], time: float = 0.0) -> Tuple[str, float]:
        """
        生成流量边界条件方程
        
        方程: Q_node - flow_value(t) = 0
        """
        if not self.validate_variables(variables):
            raise ValueError(f"流量边界条件 {self.name} 变量验证失败")
        
        Q_node = variables[self.flow_variable]
        Q_target = self.flow_func(time)
        
        residual = Q_node - Q_target
        equation_name = f"boundary_flow_{self.node_name}"
        
        return equation_name, residual
    
    def get_required_variables(self) -> List[str]:
        """返回所需的流量变量"""
        return [self.flow_variable]


class StageBoundary(BoundaryCondition):
    """
    水位边界条件
    
    指定节点的水位值约束，支持恒定水位和时变水位。
    方程形式: H_node - stage_value(t) = 0
    
    适用场景:
    - 下游水位边界
    - 水库水位控制
    - 出口水位指定
    """
    
    def __init__(self, name: str, node_name: str,
                 stage_value: Union[float, Callable[[float], float]],
                 config: Optional[BoundaryConditionConfig] = None):
        """
        初始化水位边界条件
        
        Args:
            name (str): 边界条件名称
            node_name (str): 节点名称
            stage_value (Union[float, Callable]): 水位值或时变函数
            config (BoundaryConditionConfig, optional): 配置
        """
        if config is None:
            config = BoundaryConditionConfig(name=name, description=f"水位边界条件 - 节点 {node_name}")
        
        super().__init__(name, config)
        
        self.node_name = node_name
        self.stage_variable = f"H_{node_name}"
        
        # 处理水位值
        if callable(stage_value):
            self.stage_func = stage_value
        else:
            self.stage_func = lambda t: float(stage_value)
        
        self.logger.info(f"创建水位边界条件: {name} -> {node_name}")
    
    def get_equation(self, variables: Dict[str, float], time: float = 0.0) -> Tuple[str, float]:
        """
        生成水位边界条件方程
        
        方程: H_node - stage_value(t) = 0
        """
        if not self.validate_variables(variables):
            raise ValueError(f"水位边界条件 {self.name} 变量验证失败")
        
        H_node = variables[self.stage_variable]
        H_target = self.stage_func(time)
        
        residual = H_node - H_target
        equation_name = f"boundary_stage_{self.node_name}"
        
        return equation_name, residual
    
    def get_required_variables(self) -> List[str]:
        """返回所需的水位变量"""
        return [self.stage_variable]


class RatingCurveBoundary(BoundaryCondition):
    """
    水位流量关系边界条件
    
    基于水位流量关系曲线的边界约束，支持多种曲线形式。
    方程形式: Q_node - f(H_node) = 0
    
    支持的曲线类型:
    - polynomial: 多项式形式 Q = Σ(ai * H^i)
    - weir: 堰流公式 Q = C * (H - H0)^n
    - custom: 自定义函数
    
    适用场景:
    - 堰流关系
    - 闸门特性曲线
    - 出口控制结构
    """
    
    def __init__(self, name: str, flow_node: str, stage_node: str,
                 curve_type: str = "polynomial", curve_params: Dict[str, Any] = None,
                 config: Optional[BoundaryConditionConfig] = None):
        """
        初始化水位流量关系边界条件
        
        Args:
            name (str): 边界条件名称
            flow_node (str): 流量节点名称
            stage_node (str): 水位节点名称
            curve_type (str): 曲线类型 ('polynomial', 'weir', 'custom')
            curve_params (Dict): 曲线参数
            config (BoundaryConditionConfig, optional): 配置
        """
        if config is None:
            config = BoundaryConditionConfig(
                name=name, 
                description=f"水位流量关系边界条件 - {flow_node}/{stage_node}")
        
        super().__init__(name, config)
        
        self.flow_node = flow_node
        self.stage_node = stage_node
        self.flow_variable = f"Q_{flow_node}"
        self.stage_variable = f"H_{stage_node}"
        
        self.curve_type = curve_type
        self.curve_params = curve_params or {}
        
        # 创建曲线函数
        self._create_curve_function()
        
        self.logger.info(f"创建水位流量关系边界条件: {name} ({curve_type})")
    
    def _create_curve_function(self):
        """创建曲线函数"""
        if self.curve_type == "polynomial":
            # 多项式形式: Q = Σ(ai * H^i)
            coeffs = self.curve_params.get("coefficients", [0.0, 1.0])
            def curve_func(H):
                return sum(a * (H ** i) for i, a in enumerate(coeffs))
            self.curve_func = curve_func
            
        elif self.curve_type == "weir":
            # 堰流公式: Q = C * (H - H0)^n
            C = self.curve_params.get("discharge_coefficient", 1.0)
            H0 = self.curve_params.get("reference_level", 0.0)
            n = self.curve_params.get("exponent", 1.5)
            def curve_func(H):
                return C * max(0, H - H0) ** n
            self.curve_func = curve_func
            
        elif self.curve_type == "custom":
            # 自定义函数
            custom_func = self.curve_params.get("function")
            if not callable(custom_func):
                raise ValueError("自定义曲线函数必须是可调用对象")
            self.curve_func = custom_func
            
        else:
            raise ValueError(f"不支持的曲线类型: {self.curve_type}")
    
    def get_equation(self, variables: Dict[str, float], time: float = 0.0) -> Tuple[str, float]:
        """
        生成水位流量关系边界条件方程
        
        方程: Q_node - f(H_node) = 0
        """
        if not self.validate_variables(variables):
            raise ValueError(f"水位流量关系边界条件 {self.name} 变量验证失败")
        
        Q_node = variables[self.flow_variable]
        H_node = variables[self.stage_variable]
        
        Q_curve = self.curve_func(H_node)
        
        residual = Q_node - Q_curve
        equation_name = f"boundary_rating_{self.flow_node}_{self.stage_node}"
        
        return equation_name, residual
    
    def get_required_variables(self) -> List[str]:
        """返回所需的流量和水位变量"""
        return [self.flow_variable, self.stage_variable]


class BoundaryConditionManager:
    """
    边界条件管理器
    
    统一管理多个边界条件，提供集成的接口用于求解器调用。
    支持动态添加/移除边界条件，以及批量验证和方程生成。
    """
    
    def __init__(self):
        """初始化边界条件管理器"""
        self.boundary_conditions: Dict[str, BoundaryCondition] = {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        self.logger.info("边界条件管理器初始化完成")
    
    def add_boundary_condition(self, boundary_condition: BoundaryCondition):
        """
        添加边界条件
        
        Args:
            boundary_condition (BoundaryCondition): 边界条件实例
        """
        if not isinstance(boundary_condition, BoundaryCondition):
            raise ValueError("必须是BoundaryCondition的实例")
        
        name = boundary_condition.name
        if name in self.boundary_conditions:
            self.logger.warning(f"边界条件 {name} 已存在，将被覆盖")
        
        self.boundary_conditions[name] = boundary_condition
        self.logger.info(f"添加边界条件: {name}")
    
    def remove_boundary_condition(self, name: str):
        """
        移除边界条件
        
        Args:
            name (str): 边界条件名称
        """
        if name in self.boundary_conditions:
            del self.boundary_conditions[name]
            self.logger.info(f"移除边界条件: {name}")
        else:
            self.logger.warning(f"边界条件 {name} 不存在")
    
    def get_all_equations(self, variables: Dict[str, float], time: float = 0.0) -> Dict[str, float]:
        """
        获取所有边界条件方程
        
        Args:
            variables (Dict[str, float]): 当前变量值
            time (float): 当前时间
        
        Returns:
            Dict[str, float]: 方程残差字典 {方程名: 残差值}
        """
        equations = {}
        
        for bc_name, bc in self.boundary_conditions.items():
            if not bc.is_enabled():
                continue
            
            try:
                eq_name, residual = bc.get_equation(variables, time)
                equations[eq_name] = residual
                
            except Exception as e:
                self.logger.error(f"边界条件 {bc_name} 方程生成失败: {e}")
                raise
        
        self.logger.debug(f"生成 {len(equations)} 个边界条件方程")
        return equations
    
    def get_all_required_variables(self) -> List[str]:
        """
        获取所有边界条件的必需变量
        
        Returns:
            List[str]: 去重后的变量名称列表
        """
        all_vars = set()
        
        for bc in self.boundary_conditions.values():
            if bc.is_enabled():
                all_vars.update(bc.get_required_variables())
        
        return list(all_vars)
    
    def validate_all_variables(self, variables: Dict[str, float]) -> bool:
        """
        验证所有边界条件的变量完整性
        
        Args:
            variables (Dict[str, float]): 待验证的变量字典
            
        Returns:
            bool: True表示所有边界条件变量完整
        """
        for bc_name, bc in self.boundary_conditions.items():
            if bc.is_enabled() and not bc.validate_variables(variables):
                self.logger.error(f"边界条件 {bc_name} 变量验证失败")
                return False
        
        return True
    
    def get_enabled_boundary_conditions(self) -> Dict[str, BoundaryCondition]:
        """获取启用的边界条件"""
        return {name: bc for name, bc in self.boundary_conditions.items() 
                if bc.is_enabled()}
    
    def get_boundary_condition_count(self) -> int:
        """获取启用的边界条件数量"""
        return len(self.get_enabled_boundary_conditions())
    
    def __len__(self) -> int:
        """返回边界条件总数"""
        return len(self.boundary_conditions)
    
    def __repr__(self) -> str:
        """管理器的字符串表示"""
        enabled_count = self.get_boundary_condition_count()
        total_count = len(self.boundary_conditions)
        return f"BoundaryConditionManager({enabled_count}/{total_count} enabled)"


# 工具函数
def create_time_series_function(time_values: List[float], 
                               data_values: List[float],
                               interpolation: str = "linear") -> Callable[[float], float]:
    """
    创建时间序列函数
    
    Args:
        time_values (List[float]): 时间点列表
        data_values (List[float]): 数据值列表  
        interpolation (str): 插值方法 ('linear', 'cubic', 'nearest')
    
    Returns:
        Callable[[float], float]: 时间函数
    """
    if len(time_values) != len(data_values):
        raise ValueError("时间和数据数组长度必须相等")
    
    if len(time_values) < 2:
        # 单点数据，返回常数函数
        value = data_values[0] if data_values else 0.0
        return lambda t: value
    
    # 创建插值函数
    interp_func = interp1d(time_values, data_values, 
                          kind=interpolation, 
                          bounds_error=False, 
                          fill_value=(data_values[0], data_values[-1]))
    
    return lambda t: float(interp_func(t))


def create_periodic_function(amplitude: float, period: float, 
                           phase: float = 0.0, offset: float = 0.0) -> Callable[[float], float]:
    """
    创建周期函数
    
    Args:
        amplitude (float): 振幅
        period (float): 周期（秒）
        phase (float): 相位（弧度）
        offset (float): 偏移量
    
    Returns:
        Callable[[float], float]: 周期函数
    """
    omega = 2 * np.pi / period
    
    def periodic_func(t: float) -> float:
        return offset + amplitude * np.sin(omega * t + phase)
    
    return periodic_func


def create_step_function(step_time: float, value_before: float, 
                        value_after: float) -> Callable[[float], float]:
    """
    创建阶跃函数
    
    Args:
        step_time (float): 阶跃时间
        value_before (float): 阶跃前的值
        value_after (float): 阶跃后的值
    
    Returns:
        Callable[[float], float]: 阶跃函数
    """
    def step_func(t: float) -> float:
        return value_after if t >= step_time else value_before
    
    return step_func