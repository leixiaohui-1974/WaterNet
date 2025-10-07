"""
核心枚举和常量定义

定义了水系统对象体系中使用的所有枚举类型和常量。

Author: WaterNet Development Team
Date: 2024-10-05
"""

from enum import Enum, IntEnum
from typing import Dict, List


class ObjectType(Enum):
    """水系统对象类型枚举"""
    # 输水对象
    CHANNEL = "channel"
    PIPE = "pipe"
    SIPHON = "siphon"
    
    # 存储对象
    RESERVOIR = "reservoir"
    LAKE = "lake"
    STORAGE_TANK = "storage_tank"  # 调蓄池
    
    # 调控对象
    GATE = "gate"           # 闸
    PUMP = "pump"           # 泵
    VALVE = "valve"         # 阀
    TURBINE = "turbine"     # 水轮机
    WEIR = "weir"           # 堰
    
    # 枢纽站
    HUB_STATION = "hub_station"    # 枢纽站
    PUMP_STATION = "pump_station"  # 泵站
    GATE_STATION = "gate_station"  # 闸站
    POWER_STATION = "power_station" # 电站


class SimulationMethod(Enum):
    """明渠系统仿真方法枚举"""
    # 分布式模型（Distributed Models）
    SAINT_VENANT_FULL = "saint_venant_full"
    SAINT_VENANT_SIMPLIFIED = "saint_venant_simplified"
    DIFFUSIVE_WAVE = "diffusive_wave"
    KINEMATIC_WAVE = "kinematic_wave"
    
    # 集总式模型（Lumped Models）
    IDZ_MODEL = "idz_model"
    MUSKINGUM_MODEL = "muskingum_model"
    STORAGE_ROUTING = "storage_routing"
    WATER_BALANCE = "water_balance"


class PressurizedMethod(Enum):
    """有压系统仿真方法枚举"""
    # 分布式模型（Distributed Models）
    WATER_HAMMER_FULL = "water_hammer_full"
    ELASTIC_WATER_HAMMER = "elastic_water_hammer"
    RIGID_WATER_HAMMER = "rigid_water_hammer"
    QUASI_STEADY = "quasi_steady"
    
    # 集总式模型（Lumped Models）
    TRANSFER_FUNCTION = "transfer_function"
    MUSKINGUM_HAMMER = "muskingum_hammer"
    IMPEDANCE_MODEL = "impedance_model"
    LUMPED_PARAMETER = "lumped_parameter"


class SimulationMode(Enum):
    """仿真模式枚举"""
    STEADY_FLOW = "steady_flow"
    UNSTEADY_FLOW = "unsteady_flow"
    WATER_HAMMER = "water_hammer"
    FREQUENCY_RESPONSE = "frequency_response"


class SpatialRepresentation(Enum):
    """空间表示方式枚举"""
    LUMPED = "lumped"          # 集总式：单一控制体
    DISTRIBUTED = "distributed"  # 分布式：多个断面


class FlowRegime(Enum):
    """流态类型枚举"""
    SUBCRITICAL = "subcritical"  # 缓流
    CRITICAL = "critical"        # 临界流  
    SUPERCRITICAL = "supercritical"  # 急流
    MIXED = "mixed"             # 混合流态


class PressureMode(Enum):
    """压力模式枚举"""
    FREE_SURFACE = "free_surface"  # 自由水面流
    PRESSURIZED = "pressurized"    # 有压流
    TRANSITION = "transition"      # 过渡状态


class ControlMode(Enum):
    """调控模式枚举"""
    MANUAL = "manual"           # 手动控制
    AUTOMATIC = "automatic"     # 自动控制
    SCHEDULED = "scheduled"     # 计划控制
    EMERGENCY = "emergency"     # 应急控制
    OPTIMIZATION = "optimization" # 优化控制


class StationComplexity(Enum):
    """枢纽站复杂度枚举"""
    SIMPLE = "simple"       # 简单站（单一类型设备）
    COMPOUND = "compound"   # 复合站（多类型设备）
    COMPLEX = "complex"     # 复杂站（多级联控）


class SynchronizationStrategy(Enum):
    """同步策略枚举"""
    REAL_TIME = "real_time"        # 实时同步
    PERIODIC = "periodic"          # 周期性同步
    EVENT_DRIVEN = "event_driven"  # 事件驱动同步
    ADAPTIVE = "adaptive"          # 自适应同步


# 方法支持矩阵
OPEN_CHANNEL_METHODS = {
    ObjectType.CHANNEL: [
        SimulationMethod.SAINT_VENANT_FULL,
        SimulationMethod.SAINT_VENANT_SIMPLIFIED,
        SimulationMethod.DIFFUSIVE_WAVE,
        SimulationMethod.KINEMATIC_WAVE,
        SimulationMethod.IDZ_MODEL,
        SimulationMethod.MUSKINGUM_MODEL,
        SimulationMethod.STORAGE_ROUTING,
        SimulationMethod.WATER_BALANCE
    ],
    ObjectType.SIPHON: [
        SimulationMethod.SAINT_VENANT_FULL,
        SimulationMethod.SAINT_VENANT_SIMPLIFIED,
        SimulationMethod.IDZ_MODEL,
        SimulationMethod.MUSKINGUM_MODEL
    ]
}

PRESSURIZED_METHODS = {
    ObjectType.PIPE: [
        PressurizedMethod.WATER_HAMMER_FULL,
        PressurizedMethod.ELASTIC_WATER_HAMMER,
        PressurizedMethod.RIGID_WATER_HAMMER,
        PressurizedMethod.QUASI_STEADY,
        PressurizedMethod.TRANSFER_FUNCTION,
        PressurizedMethod.MUSKINGUM_HAMMER,
        PressurizedMethod.IMPEDANCE_MODEL,
        PressurizedMethod.LUMPED_PARAMETER
    ]
}

# 模型复杂度分级
MODEL_COMPLEXITY = {
    # 分布式模型复杂度
    SimulationMethod.SAINT_VENANT_FULL: 5,
    SimulationMethod.SAINT_VENANT_SIMPLIFIED: 4,
    SimulationMethod.DIFFUSIVE_WAVE: 3,
    SimulationMethod.KINEMATIC_WAVE: 2,
    
    # 集总式模型复杂度
    SimulationMethod.IDZ_MODEL: 3,
    SimulationMethod.MUSKINGUM_MODEL: 2,
    SimulationMethod.STORAGE_ROUTING: 2,
    SimulationMethod.WATER_BALANCE: 1,
    
    # 有压模型复杂度
    PressurizedMethod.WATER_HAMMER_FULL: 5,
    PressurizedMethod.ELASTIC_WATER_HAMMER: 4,
    PressurizedMethod.RIGID_WATER_HAMMER: 3,
    PressurizedMethod.QUASI_STEADY: 2,
    PressurizedMethod.TRANSFER_FUNCTION: 3,
    PressurizedMethod.MUSKINGUM_HAMMER: 2,
    PressurizedMethod.IMPEDANCE_MODEL: 3,
    PressurizedMethod.LUMPED_PARAMETER: 1
}

# 空间表示映射
SPATIAL_REPRESENTATION_MAP = {
    # 分布式模型
    SimulationMethod.SAINT_VENANT_FULL: SpatialRepresentation.DISTRIBUTED,
    SimulationMethod.SAINT_VENANT_SIMPLIFIED: SpatialRepresentation.DISTRIBUTED,
    SimulationMethod.DIFFUSIVE_WAVE: SpatialRepresentation.DISTRIBUTED,
    SimulationMethod.KINEMATIC_WAVE: SpatialRepresentation.DISTRIBUTED,
    
    # 集总式模型
    SimulationMethod.IDZ_MODEL: SpatialRepresentation.LUMPED,
    SimulationMethod.MUSKINGUM_MODEL: SpatialRepresentation.LUMPED,
    SimulationMethod.STORAGE_ROUTING: SpatialRepresentation.LUMPED,
    SimulationMethod.WATER_BALANCE: SpatialRepresentation.LUMPED,
    
    # 有压分布式模型
    PressurizedMethod.WATER_HAMMER_FULL: SpatialRepresentation.DISTRIBUTED,
    PressurizedMethod.ELASTIC_WATER_HAMMER: SpatialRepresentation.DISTRIBUTED,
    PressurizedMethod.RIGID_WATER_HAMMER: SpatialRepresentation.DISTRIBUTED,
    PressurizedMethod.QUASI_STEADY: SpatialRepresentation.DISTRIBUTED,
    
    # 有压集总式模型
    PressurizedMethod.TRANSFER_FUNCTION: SpatialRepresentation.LUMPED,
    PressurizedMethod.MUSKINGUM_HAMMER: SpatialRepresentation.LUMPED,
    PressurizedMethod.IMPEDANCE_MODEL: SpatialRepresentation.LUMPED,
    PressurizedMethod.LUMPED_PARAMETER: SpatialRepresentation.LUMPED
}

# 默认配置常量
DEFAULT_CONFIG = {
    'time_step': 60.0,          # 默认时间步长（秒）
    'convergence_tolerance': 1e-6,  # 收敛容差
    'max_iterations': 100,      # 最大迭代次数
    'enable_twin': False,       # 默认不启用数字孪生
    'visualization_enabled': True,  # 默认启用可视化
    'result_export_format': 'csv'  # 默认结果导出格式
}

# 物理常量
PHYSICAL_CONSTANTS = {
    'gravity': 9.81,           # 重力加速度 (m/s²)
    'water_density': 1000.0,   # 水的密度 (kg/m³)
    'atmospheric_pressure': 101325.0,  # 大气压 (Pa)
    'min_water_depth': 0.001,  # 最小水深 (m)
    'max_velocity': 20.0       # 最大流速限制 (m/s)
}

# 数值稳定性参数
NUMERICAL_PARAMS = {
    'courant_number_max': 1.0,    # 最大Courant数
    'froude_number_max': 0.9,     # 最大Froude数（避免超临界流）
    'min_cross_section_area': 1e-6,  # 最小断面面积 (m²)
    'max_time_step_auto': 300.0,  # 自动时间步长最大值（秒）
    'min_time_step_auto': 1.0     # 自动时间步长最小值（秒）
}