"""
WaterNet 核心库模块

集成了通用功能模块，包括非恒定流分析、参数优化、仿真管理等核心功能。
根据用户记忆中的"核心库模块化重构规范"和"通用功能核心库化"要求实现。

主要模块:
- UnsteadyFlowAnalyzer: 非恒定流分析核心模块
- ParameterOptimizer: 参数自动调优核心模块
- WaterSystemSimulationManager: 智能水系统仿真管理器

Author: WaterNet Development Team
Date: 2025-10-07
"""

from .unsteady_flow_analyzer import UnsteadyFlowAnalyzer
from .parameter_optimizer import ParameterOptimizer, OptimizationObjective, OptimizationResult
from .simulation_manager import (
    WaterSystemSimulationManager,
    SimulationStrategy,
    SimulationStatus,
    SimulationConfiguration,
    SimulationResult
)

__all__ = [
    # 非恒定流分析
    'UnsteadyFlowAnalyzer',
    
    # 参数优化
    'ParameterOptimizer',
    'OptimizationObjective',
    'OptimizationResult',
    
    # 仿真管理
    'WaterSystemSimulationManager',
    'SimulationStrategy',
    'SimulationStatus', 
    'SimulationConfiguration',
    'SimulationResult'
]