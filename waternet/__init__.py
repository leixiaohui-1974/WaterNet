"""
WaterNet: 明渠输水系统数字孪生建模框架

WaterNet是一个基于圣维南方程组的明渠水力模型接口系统，
提供高精度物理模型与多种降阶模型的统一建模框架。

主要模块:
- interfaces: 模型接口定义
- models: 物理模型和降阶模型实现  
- parameter_estimation: 参数辨识算法
- coordination: 同步孪生协调器
- utils: 工具函数和公共组件
"""

__version__ = "1.0.0"
__author__ = "WaterNet Development Team"

# 导入核心接口
from .interfaces.hydro_model import HydroModel
from .models.saint_venant import SaintVenantModel
from .models.lumped_models import (
    BaseLumpedModel,
    WaterBalanceModel, 
    StorageRoutingModel,
    MuskingumModel,
    IntegralDelayZeroModel
)
from .parameter_estimation.estimator import ParameterEstimator
from .coordination.twinning_harness import SynchronizedTwinningHarness

__all__ = [
    'HydroModel',
    'SaintVenantModel', 
    'BaseLumpedModel',
    'WaterBalanceModel',
    'StorageRoutingModel', 
    'MuskingumModel',
    'IntegralDelayZeroModel',
    'ParameterEstimator',
    'SynchronizedTwinningHarness'
]