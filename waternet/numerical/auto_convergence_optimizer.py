#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AutoConvergenceOptimizer 自动收敛优化器

作为数值解的基础功能，集成到WaterNet基础类库中，
提供透明的自动收敛优化，无需用户手动尝试不同策略。

设计原则：
1. 基于理论分析的最佳实践默认值
2. 渐进式自定义，降低使用门槛
3. 多重策略自动切换，确保收敛性
4. 物理意义优先，数值稳定性保障

Author: WaterNet Development Team
Date: 2024-12-23
"""

import numpy as np
import warnings
from typing import Dict, List, Tuple, Optional, Any, Union
from enum import Enum
from dataclasses import dataclass
import logging


class ConvergenceStrategy(Enum):
    """收敛策略枚举"""
    CONSERVATIVE = "conservative"      # 保守策略：稳定性优先
    BALANCED = "balanced"             # 平衡策略：性能与稳定性兼顾
    AGGRESSIVE = "aggressive"         # 激进策略：性能优先
    ADAPTIVE = "adaptive"             # 自适应策略：动态调整


@dataclass
class AutoConvergenceConfig:
    """自动收敛优化配置
    
    基于"简化参数设计规范"，所有参数都有理论最佳默认值
    用户可以渐进式自定义，无需深入了解数值细节
    """
    
    # 收敛策略选择（用户唯一需要关心的参数）
    strategy: ConvergenceStrategy = ConvergenceStrategy.ADAPTIVE
    
    # 高级用户自定义参数（可选）
    max_attempts: int = 5              # 最大尝试次数
    convergence_tolerance: float = 1e-6  # 收敛容差
    stability_margin: float = 0.8      # 稳定性安全边际
    
    # 专家级参数（几乎不需要修改）
    matrix_conditioning_threshold: float = 1e12
    cfl_safety_factor: float = 0.8
    relaxation_bounds: Tuple[float, float] = (0.01, 0.9)
    
    def __post_init__(self):
        """参数验证"""
        if not 0 < self.stability_margin <= 1.0:
            raise ValueError("稳定性安全边际必须在(0,1]范围内")
        if self.max_attempts < 1:
            raise ValueError("最大尝试次数必须大于0")


class AutoConvergenceOptimizer:
    """
    自动收敛优化器
    
    作为数值解的基础功能，实现：
    1. 智能策略选择和自动切换
    2. 物理量纲scaling优化
    3. 自适应参数调整
    4. 多重收敛检测
    5. 透明的优化过程
    
    用户无需了解数值细节，只需选择收敛策略即可获得稳定的求解性能。
    """
    
    def __init__(self, config: Optional[AutoConvergenceConfig] = None,
                 logger: Optional[logging.Logger] = None):
        """
        初始化自动收敛优化器
        
        Args:
            config: 优化配置，默认使用自适应策略
            logger: 日志记录器
        """
        self.config = config or AutoConvergenceConfig()
        self.logger = logger or logging.getLogger("AutoConvergenceOptimizer")
        
        # 运行时状态
        self.current_attempt = 0
        self.convergence_history = []
        self.strategy_performance = {strategy: [] for strategy in ConvergenceStrategy}
        
        # 物理特征尺度（自动计算）
        self.characteristic_scales = {
            'flow': 100.0,      # 典型流量 [m³/s]
            'level': 1.0,       # 典型水位变化 [m]
            'length': 1000.0,   # 典型长度 [m]
            'velocity': 1.0,    # 典型流速 [m/s]
            'time': 60.0        # 典型时间步 [s]
        }
        
        # 策略参数库（基于理论分析的最佳实践）
        self._initialize_strategy_parameters()
    
    def _initialize_strategy_parameters(self):
        """初始化各策略的参数库"""
        self.strategy_params = {
            ConvergenceStrategy.CONSERVATIVE: {
                'theta': 1.0,               # 全隐式格式
                'max_iterations': 200,      # 充足的迭代次数
                'under_relaxation': 0.3,    # 保守的松弛因子
                'cfl_target': 0.2,          # 小CFL数
                'matrix_scaling': 'equilibration',  # 平衡缩放
                'timestep_reduction': 0.5   # 快速时间步减小
            },
            ConvergenceStrategy.BALANCED: {
                'theta': 0.6,               # 半隐式格式
                'max_iterations': 100,      # 平衡的迭代次数
                'under_relaxation': 0.6,    # 标准松弛因子
                'cfl_target': 0.5,          # 标准CFL数
                'matrix_scaling': 'physics_based',  # 物理量纲缩放
                'timestep_reduction': 0.7   # 适中的时间步减小
            },
            ConvergenceStrategy.AGGRESSIVE: {
                'theta': 0.5,               # 显式偏向格式
                'max_iterations': 50,       # 较少迭代次数
                'under_relaxation': 0.8,    # 较大松弛因子
                'cfl_target': 0.8,          # 较大CFL数
                'matrix_scaling': 'geometric',  # 几何缩放
                'timestep_reduction': 0.9   # 慢时间步减小
            },
            ConvergenceStrategy.ADAPTIVE: {
                'theta': 0.6,               # 起始值
                'max_iterations': 100,      # 起始值
                'under_relaxation': 0.6,    # 起始值
                'cfl_target': 0.5,          # 起始值
                'matrix_scaling': 'adaptive',  # 自适应选择
                'timestep_reduction': 0.7   # 起始值
            }
        }
    
    def update_characteristic_scales(self, solver_state: Dict[str, Any]):
        """
        自动更新物理特征尺度
        
        Args:
            solver_state: 求解器状态信息
        """
        try:
            # 从求解器状态自动提取特征尺度
            if 'current_state' in solver_state:
                state = solver_state['current_state']
                if len(state) > 0:
                    # 流量特征尺度
                    n_flow = len(state) // 2 if len(state) > 1 else 1
                    flows = state[:n_flow]
                    self.characteristic_scales['flow'] = max(np.mean(np.abs(flows)), 1.0)
            
            if 'geometry' in solver_state:
                geom = solver_state['geometry']
                if 'length_scale' in geom:
                    self.characteristic_scales['length'] = geom['length_scale']
                if 'water_level_range' in geom:
                    self.characteristic_scales['level'] = max(geom['water_level_range'], 0.1)
            
            # 推导其他尺度
            self.characteristic_scales['velocity'] = (
                self.characteristic_scales['flow'] / 
                (self.characteristic_scales['length'] * self.characteristic_scales['level'])
            )
            
            self.logger.debug(f"自动更新特征尺度: {self.characteristic_scales}")
            
        except Exception as e:
            self.logger.warning(f"特征尺度更新失败，使用默认值: {e}")
    
    def optimize_for_convergence(self, jacobian: np.ndarray, residual: np.ndarray,
                                solver_state: Dict[str, Any]) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
        """
        执行自动收敛优化
        
        这是核心方法，集成所有优化策略，自动选择和应用最佳方法。
        
        Args:
            jacobian: Jacobian矩阵
            residual: 残差向量
            solver_state: 求解器状态
            
        Returns:
            Tuple[优化后的Jacobian, 优化后的残差, 优化信息]
        """
        # 更新特征尺度
        self.update_characteristic_scales(solver_state)
        
        # 选择当前策略
        current_strategy = self._select_optimal_strategy(solver_state)
        
        # 应用矩阵优化
        optimized_jacobian, optimized_residual = self._apply_matrix_optimization(
            jacobian, residual, current_strategy
        )
        
        # 生成优化建议
        optimization_info = self._generate_optimization_advice(
            solver_state, current_strategy
        )
        
        # 记录性能
        self._record_performance(current_strategy, solver_state)
        
        return optimized_jacobian, optimized_residual, optimization_info
    
    def _select_optimal_strategy(self, solver_state: Dict[str, Any]) -> ConvergenceStrategy:
        """智能策略选择"""
        if self.config.strategy != ConvergenceStrategy.ADAPTIVE:
            return self.config.strategy
        
        # 自适应策略选择逻辑
        iteration = solver_state.get('iteration', 0)
        condition_number = solver_state.get('condition_number', 1.0)
        convergence_rate = solver_state.get('convergence_rate', 1.0)
        
        # 基于当前状态智能选择策略
        if condition_number > 1e10 or convergence_rate > 1.5:
            # 数值困难情况，使用保守策略
            return ConvergenceStrategy.CONSERVATIVE
        elif iteration > 50 and convergence_rate > 1.1:
            # 收敛缓慢，切换到平衡策略
            return ConvergenceStrategy.BALANCED
        elif iteration < 10 and convergence_rate < 0.5:
            # 快速收敛，可以使用激进策略
            return ConvergenceStrategy.AGGRESSIVE
        else:
            # 标准情况，使用平衡策略
            return ConvergenceStrategy.BALANCED
    
    def _apply_matrix_optimization(self, jacobian: np.ndarray, residual: np.ndarray,
                                  strategy: ConvergenceStrategy) -> Tuple[np.ndarray, np.ndarray]:
        """应用矩阵优化"""
        strategy_params = self.strategy_params[strategy]
        scaling_method = strategy_params['matrix_scaling']
        
        if scaling_method == 'equilibration':
            return self._equilibration_scaling(jacobian, residual)
        elif scaling_method == 'physics_based':
            return self._physics_based_scaling(jacobian, residual)
        elif scaling_method == 'geometric':
            return self._geometric_scaling(jacobian, residual)
        elif scaling_method == 'adaptive':
            # 自适应选择最佳scaling方法
            return self._adaptive_scaling(jacobian, residual)
        else:
            return jacobian, residual
    
    def _equilibration_scaling(self, jacobian: np.ndarray, residual: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """平衡缩放 - 最稳定的scaling方法"""
        try:
            # 计算行列范数
            row_norms = np.sqrt(np.sum(jacobian**2, axis=1))
            col_norms = np.sqrt(np.sum(jacobian**2, axis=0))
            
            # 防止零除
            row_norms = np.where(row_norms < 1e-14, 1.0, row_norms)
            col_norms = np.where(col_norms < 1e-14, 1.0, col_norms)
            
            # 构建缩放因子
            row_scales = 1.0 / np.sqrt(row_norms)
            col_scales = 1.0 / np.sqrt(col_norms)
            
            # 应用缩放
            jacobian_scaled = np.diag(row_scales) @ jacobian @ np.diag(col_scales)
            residual_scaled = row_scales * residual
            
            self.logger.debug("应用平衡缩放优化")
            return jacobian_scaled, residual_scaled
            
        except Exception as e:
            self.logger.warning(f"平衡缩放失败，使用原矩阵: {e}")
            return jacobian, residual
    
    def _physics_based_scaling(self, jacobian: np.ndarray, residual: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """基于物理量纲的scaling"""
        try:
            n_vars = jacobian.shape[0]
            row_scales = np.ones(n_vars)
            col_scales = np.ones(n_vars)
            
            # 基于圣维南方程的物理scaling
            for i in range(n_vars):
                if i % 2 == 0:  # 连续性方程
                    scale = self.characteristic_scales['flow'] / self.characteristic_scales['length']
                    row_scales[i] = 1.0 / scale
                else:  # 动量方程
                    scale = self.characteristic_scales['velocity']**2
                    row_scales[i] = 1.0 / scale
            
            # 变量scaling
            n_flow = n_vars // 2
            for j in range(n_vars):
                if j < n_flow:  # 流量变量
                    col_scales[j] = self.characteristic_scales['flow']
                else:  # 水位变量
                    col_scales[j] = self.characteristic_scales['level']
            
            # 应用scaling
            jacobian_scaled = jacobian.copy()
            residual_scaled = residual.copy()
            
            for i in range(n_vars):
                jacobian_scaled[i, :] *= row_scales[i]
                residual_scaled[i] *= row_scales[i]
            
            for j in range(n_vars):
                jacobian_scaled[:, j] /= col_scales[j]
            
            self.logger.debug("应用物理量纲scaling优化")
            return jacobian_scaled, residual_scaled
            
        except Exception as e:
            self.logger.warning(f"物理量纲scaling失败，使用原矩阵: {e}")
            return jacobian, residual
    
    def _geometric_scaling(self, jacobian: np.ndarray, residual: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """几何平均scaling"""
        try:
            # 计算几何平均
            row_geo_mean = np.exp(np.mean(np.log(np.abs(jacobian) + 1e-14), axis=1))
            col_geo_mean = np.exp(np.mean(np.log(np.abs(jacobian) + 1e-14), axis=0))
            
            # 构建缩放因子
            row_scales = 1.0 / row_geo_mean
            col_scales = 1.0 / col_geo_mean
            
            # 应用缩放
            jacobian_scaled = np.diag(row_scales) @ jacobian @ np.diag(col_scales)
            residual_scaled = row_scales * residual
            
            self.logger.debug("应用几何scaling优化")
            return jacobian_scaled, residual_scaled
            
        except Exception as e:
            self.logger.warning(f"几何scaling失败，使用原矩阵: {e}")
            return jacobian, residual
    
    def _adaptive_scaling(self, jacobian: np.ndarray, residual: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """自适应scaling - 自动选择最佳方法"""
        original_cond = self._safe_condition_number(jacobian)
        
        # 尝试不同scaling方法
        methods = [
            ('equilibration', self._equilibration_scaling),
            ('physics_based', self._physics_based_scaling),
            ('geometric', self._geometric_scaling)
        ]
        
        best_jacobian, best_residual = jacobian, residual
        best_cond = original_cond
        best_method = 'none'
        
        for method_name, method_func in methods:
            try:
                scaled_jac, scaled_res = method_func(jacobian, residual)
                scaled_cond = self._safe_condition_number(scaled_jac)
                
                if scaled_cond < best_cond:
                    best_jacobian, best_residual = scaled_jac, scaled_res
                    best_cond = scaled_cond
                    best_method = method_name
                    
            except Exception:
                continue
        
        self.logger.debug(f"自适应选择了{best_method}方法，条件数改善: {original_cond:.2e} -> {best_cond:.2e}")
        return best_jacobian, best_residual
    
    def _safe_condition_number(self, matrix: np.ndarray) -> float:
        """安全计算条件数"""
        try:
            if matrix.size == 0:
                return 1.0
            cond = np.linalg.cond(matrix)
            return float(cond) if np.isfinite(cond) else 1e16
        except:
            return 1e16
    
    def _generate_optimization_advice(self, solver_state: Dict[str, Any], 
                                    strategy: ConvergenceStrategy) -> Dict[str, Any]:
        """生成优化建议"""
        advice = {
            'strategy_used': strategy.value,
            'recommended_params': self.strategy_params[strategy].copy(),
            'characteristic_scales': self.characteristic_scales.copy(),
            'optimization_applied': True
        }
        
        # 基于当前状态提供动态建议
        iteration = solver_state.get('iteration', 0)
        condition_number = solver_state.get('condition_number', 1.0)
        
        if condition_number > self.config.matrix_conditioning_threshold:
            advice['warnings'] = ['Matrix condition number too large, consider reducing time step']
        
        if iteration > 50:
            advice['suggestions'] = ['Consider switching to more conservative strategy']
        
        return advice
    
    def _record_performance(self, strategy: ConvergenceStrategy, solver_state: Dict[str, Any]):
        """记录策略性能"""
        performance_data = {
            'iteration': solver_state.get('iteration', 0),
            'condition_number': solver_state.get('condition_number', 1.0),
            'convergence_rate': solver_state.get('convergence_rate', 1.0),
            'timestamp': solver_state.get('timestamp', 0)
        }
        
        self.strategy_performance[strategy].append(performance_data)
        
        # 保持历史记录长度
        if len(self.strategy_performance[strategy]) > 100:
            self.strategy_performance[strategy].pop(0)
    
    def get_convergence_statistics(self) -> Dict[str, Any]:
        """获取收敛统计信息"""
        stats = {
            'total_optimizations': len(self.convergence_history),
            'strategy_performance': {},
            'current_config': {
                'strategy': self.config.strategy.value,
                'max_attempts': self.config.max_attempts,
                'convergence_tolerance': self.config.convergence_tolerance
            }
        }
        
        # 计算各策略的平均性能
        for strategy, history in self.strategy_performance.items():
            if history:
                avg_iterations = np.mean([h['iteration'] for h in history])
                avg_cond_num = np.mean([h['condition_number'] for h in history])
                stats['strategy_performance'][strategy.value] = {
                    'average_iterations': avg_iterations,
                    'average_condition_number': avg_cond_num,
                    'usage_count': len(history)
                }
        
        return stats
    
    def reset_performance_history(self):
        """重置性能历史记录"""
        self.convergence_history.clear()
        for strategy in ConvergenceStrategy:
            self.strategy_performance[strategy].clear()
        self.current_attempt = 0
        self.logger.info("性能历史记录已重置")


def create_auto_convergence_optimizer(strategy: str = "adaptive",
                                    max_attempts: int = 5,
                                    **kwargs) -> AutoConvergenceOptimizer:
    """
    便捷工厂函数，创建自动收敛优化器
    
    Args:
        strategy: 收敛策略 ("conservative", "balanced", "aggressive", "adaptive")
        max_attempts: 最大尝试次数
        **kwargs: 其他配置参数
        
    Returns:
        AutoConvergenceOptimizer: 配置好的优化器实例
    """
    try:
        strategy_enum = ConvergenceStrategy(strategy)
    except ValueError:
        warnings.warn(f"未知策略 '{strategy}'，使用自适应策略")
        strategy_enum = ConvergenceStrategy.ADAPTIVE
    
    config = AutoConvergenceConfig(
        strategy=strategy_enum,
        max_attempts=max_attempts,
        **kwargs
    )
    
    return AutoConvergenceOptimizer(config)