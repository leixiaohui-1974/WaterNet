"""
WaterNet对象系统模块

基于设计文档重构的水系统对象体系，提供统一的面向对象接口。

模块结构：
- core: 核心基类和枚举
- base: 抽象基类 (WaterSystemObject, ConveyanceObject, StorageObject)
- conveyance: 输水对象实现 (ChannelObject, PipeObject, SiphonObject)
- storage: 存储对象实现 (ReservoirObject, LakeObject)
- control: 调控对象实现 (GateObject, PumpObject, ValveObject, TurbineObject)
- station: 枢纽站实现 (HubStationObject, PumpStationObject, etc.)
- simulation: 仿真引擎体系
- config: 配置管理器
- state: 状态管理器
- results: 结果管理器
- twinning: 数字孪生协调机制

Author: WaterNet Development Team
Date: 2024-10-05
"""

from .core import (
    SimulationMethod,
    PressurizedMethod,
    ObjectType,
    SimulationMode,
    ControlMode,
    StationComplexity
)

from .base import (
    WaterSystemObject,
    ConveyanceObject,
    StorageObject
)

from .conveyance import (
    ChannelObject,
    PipeObject,
    SiphonObject
)

from .storage import (
    ReservoirObject,
    LakeObject
)

from .control import (
    ControlObject,
    GateObject,
    PumpObject,
    ValveObject,
    TurbineObject
)

from .station import (
    HubStationObject,
    PumpStationObject,
    GateStationObject,
    PowerStationObject
)

from .config import (
    ConfigManager,
    ValidationResult
)

from .state import (
    StateManager,
    StateResult
)

from .results import (
    ResultManager,
    ProfileData,
    VisualizationResult,
    ExportResult
)

__all__ = [
    # Core enums
    'SimulationMethod',
    'PressurizedMethod', 
    'ObjectType',
    'SimulationMode',
    'ControlMode',
    'StationComplexity',
    
    # Base classes
    'WaterSystemObject',
    'ConveyanceObject',
    'StorageObject',
    
    # Conveyance objects
    'ChannelObject',
    'PipeObject',
    'SiphonObject',
    
    # Storage objects
    'ReservoirObject',
    'LakeObject',
    
    # Control objects
    'ControlObject',
    'GateObject',
    'PumpObject',
    'ValveObject',
    'TurbineObject',
    
    # Station objects
    'HubStationObject',
    'PumpStationObject',
    'GateStationObject',
    'PowerStationObject',
    
    # Management classes
    'ConfigManager',
    'StateManager',
    'ResultManager',
    
    # Data classes
    'ValidationResult',
    'StateResult',
    'ProfileData',
    'VisualizationResult',
    'ExportResult'
]

__version__ = "1.0.0"

# 对象创建工厂函数
def create_water_object(object_type: str, object_id: str, **kwargs) -> WaterSystemObject:
    """
    工厂函数：根据类型创建水系统对象
    
    Args:
        object_type: 对象类型字符串
        object_id: 对象唯一标识符
        **kwargs: 额外的创建参数
        
    Returns:
        创建的水系统对象
        
    Raises:
        ValueError: 不支持的对象类型
    """
    object_classes = {
        'channel': ChannelObject,
        'pipe': PipeObject,
        'siphon': SiphonObject,
        'reservoir': ReservoirObject,
        'lake': LakeObject,
        'storage_tank': ReservoirObject,  # 调蓄池使用水库对象
        'gate': GateObject,
        'pump': PumpObject,
        'valve': ValveObject,
        'turbine': TurbineObject,
        'hub_station': HubStationObject,
        'pump_station': PumpStationObject,
        'gate_station': GateStationObject,
        'power_station': PowerStationObject
    }
    
    if object_type not in object_classes:
        raise ValueError(f"不支持的对象类型: {object_type}")
    
    object_class = object_classes[object_type]
    return object_class(object_id, **kwargs)