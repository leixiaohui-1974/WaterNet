"""
WaterNet Models模块

包含所有水力模型的实现，包括传统模型和新的流量水位区间优化系统。

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

# 复杂水力枢纽模型系统
from .reservoir_model import (
    ReservoirModel,
    create_simple_reservoir,
    create_polynomial_reservoir
)

from .junction_model import (
    JunctionModel,
    FlowSplitterJunction,
    create_simple_junction,
    create_confluence_junction,
    create_bifurcation_junction
)

from .complex_station_model import (
    ComplexStationModel,
    create_gate_station,
    create_pump_station
)

from .pressurized_pipe_model import (
    PressurizedPipeModel,
    create_simple_pipe,
    create_pipe_with_fittings,
    FITTING_LOSS_COEFFICIENTS
)

from .network_builder import (
    NetworkBuilder,
    NetworkConfig,
    TopologyValidator,
    build_network_from_file,
    create_simple_cascade_system
)

from .implicit_solver import (
    ImplicitSolverAgent,
    SolverConfig,
    SolverStatistics,
    solve_hydraulic_network,
    solve_hydraulic_transient
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
    
    # 复杂水力枢纽模型系统
    'ReservoirModel',
    'create_simple_reservoir', 
    'create_polynomial_reservoir',
    'JunctionModel',
    'FlowSplitterJunction',
    'create_simple_junction',
    'create_confluence_junction',
    'create_bifurcation_junction',
    'ComplexStationModel',
    'create_gate_station',
    'create_pump_station',
    'PressurizedPipeModel',
    'create_simple_pipe',
    'create_pipe_with_fittings',
    'FITTING_LOSS_COEFFICIENTS',
    'NetworkBuilder',
    'NetworkConfig',
    'TopologyValidator',
    'build_network_from_file',
    'create_simple_cascade_system',
    'ImplicitSolverAgent',
    'SolverConfig',
    'SolverStatistics',
    'solve_hydraulic_network',
    'solve_hydraulic_transient',
    
    # 集成接口
    'FlowStageSystemIntegrator',
    'FiveSectionConfig',
    'create_five_section_interval_system',
    'integrate_with_saint_venant',
    'create_demonstration_system'
]