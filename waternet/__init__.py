"""
WaterNet - 明渠水力模型数字孪生建模框架

提供统一的API入口，包括核心模型、参数估计、数字孪生和配置管理功能。

Author: WaterNet Development Team
Date: 2024-10-03
Version: 1.0.0
"""

# 核心模型
from .models import (
    SaintVenantModel,
    SimplifiedSaintVenantModel,
    ApproximationMode,
    ApproximationSelector,
    HydraulicConditions,
    GeometryComplexity,
    AccuracyRequirement,
    MuskingumModel, 
    StorageRoutingModel,
    IntegralDelayZeroModel,
    WaterBalanceModel,
    SolverFactory,
    solve_with_auto_solver
)

# 配置管理
from .config import ConfigManager

# 新增：统一配置管理
try:
    from .config.standard_five_section import StandardFiveSectionConfig
except ImportError:
    StandardFiveSectionConfig = None

# 新增：精度对比器
try:
    from .utils.accuracy_comparator import AccuracyComparator
except ImportError:
    AccuracyComparator = None

# 参数估计
try:
    from .parameter_estimation.estimator import ParameterEstimator
except ImportError:
    ParameterEstimator = None

# 数字孪生协调
try:
    from .coordination.twinning_harness import SynchronizedTwinningHarness
except ImportError:
    SynchronizedTwinningHarness = None

# 简化API工厂函数
from .utils.model_factory import (
    create_simple_muskingum,
    create_simple_storage_routing,
    create_simple_idz,
    create_default_physical_relations
)

# 版本信息
__version__ = "1.0.0"
__author__ = "WaterNet Development Team"
__email__ = "waternet@example.com"
__license__ = "MIT"

# 对外接口
__all__ = [
    # 核心模型
    'SaintVenantModel',
    'SimplifiedSaintVenantModel',
    'ApproximationMode',
    'ApproximationSelector',
    'HydraulicConditions',
    'GeometryComplexity', 
    'AccuracyRequirement',
    'MuskingumModel',
    'StorageRoutingModel', 
    'IntegralDelayZeroModel',
    'WaterBalanceModel',
    
    # 求解器
    'SolverFactory',
    'solve_with_auto_solver',
    
    # 配置管理
    'ConfigManager',
    'StandardFiveSectionConfig',
    
    # 高级功能
    'ParameterEstimator',
    'SynchronizedTwinningHarness',
    'AccuracyComparator',
    
    # 简化API
    'create_simple_muskingum',
    'create_simple_storage_routing',
    'create_simple_idz',
    'create_default_physical_relations',
    'create_model_by_scenario',
    'quick_muskingum',
    'quick_storage',
    'quick_idz',
    'auto_model',
    
    # 元信息
    '__version__',
    '__author__',
]