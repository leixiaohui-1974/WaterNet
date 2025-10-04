"""
WaterNet Models模块

包含所有水力模型的实现，包括传统模型、有压管道模型和新的流量水位区间优化系统。

Author: WaterNet Development Team
Date: 2024-10-04
"""

# 传统模型
from .lumped_models import (
    BaseLumpedModel,
    WaterBalanceModel,
    StorageRoutingModel,
    MuskingumModel,
    IntegralDelayZeroModel
)

# 有压管道降阶模型
from .pressurized_pipe_rom import (
    PressurizedPipeROM,
    LinearHammerModel,
    MuskingumHammerModel,
    ElasticPipeModel,
    create_pressurized_pipe_rom
)

from .saint_venant import SaintVenantModel
from .simplified_saint_venant import SimplifiedSaintVenantModel, ApproximationMode
from .approximation_selector import (
    ApproximationSelector,
    HydraulicConditions,
    GeometryComplexity,
    AccuracyRequirement
)
from .muskingum_cunge import MuskingumCungeModel
from .solvers import SolverFactory, solve_with_auto_solver

# 流量水位区间优化系统
from .flow_stage_interval_system import (
    FlowStageInterval,
    OptimizationResults,
    IDZModelParameters,
    IntervalDatabase
)

from .interval_partitioner import (
    IntervalPartitioner,
    PartitioningConfig
)

from .idz_linearizer import (
    IDZLinearizer,
    IDZLinearizationConfig
)

from .accuracy_validator import (
    AccuracyValidator,
    ValidationConfig
)

from .interval_manager import (
    IntervalManager,
    TransitionConfig
)

from .flow_stage_interval_optimizer import (
    FlowStageIntervalOptimizer,
    OptimizerConfig
)

# 集成接口
from .integration_interface import (
    FlowStageSystemIntegrator,
    FiveSectionConfig,
    create_five_section_interval_system,
    integrate_with_saint_venant,
    create_demonstration_system
)

__all__ = [
    # 传统模型
    'BaseLumpedModel',
    'WaterBalanceModel', 
    'StorageRoutingModel',
    'MuskingumModel',
    'IntegralDelayZeroModel',
    'SaintVenantModel',
    
    # 有压管道降阶模型
    'PressurizedPipeROM',
    'LinearHammerModel',
    'MuskingumHammerModel', 
    'ElasticPipeModel',
    'create_pressurized_pipe_rom',
    
    # 简化模式系统
    'SimplifiedSaintVenantModel',
    'ApproximationMode',
    'ApproximationSelector',
    'HydraulicConditions',
    'GeometryComplexity',
    'AccuracyRequirement',
    
    'MuskingumCungeModel',
    'SolverFactory',
    'solve_with_auto_solver',
    
    # 流量水位区间优化系统
    'FlowStageInterval',
    'OptimizationResults',
    'IDZModelParameters',
    'IntervalDatabase',
    'IntervalPartitioner',
    'PartitioningConfig',
    'IDZLinearizer',
    'IDZLinearizationConfig',
    'AccuracyValidator',
    'ValidationConfig',
    'IntervalManager',
    'TransitionConfig',
    'FlowStageIntervalOptimizer',
    'OptimizerConfig',
    
    # 集成接口
    'FlowStageSystemIntegrator',
    'FiveSectionConfig',
    'create_five_section_interval_system',
    'integrate_with_saint_venant',
    'create_demonstration_system'
]