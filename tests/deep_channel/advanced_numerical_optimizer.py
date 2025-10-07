#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高级数值稳定性优化器

基于记忆中的"水力模型性能与稳定性平衡经验"，实现：
1. 高级Jacobian矩阵数值scaling优化
2. 智能自适应时间步长控制  
3. 动态松弛因子策略
4. 稀疏矩阵优化技术
5. 多重预条件技术
"""

import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import spsolve, spilu, LinearOperator
from scipy.linalg import norm, solve
from typing import Tuple, Dict, Any, Optional, List
import logging
import warnings
from dataclasses import dataclass
from enum import Enum

class MatrixConditioningStrategy(Enum):
    """矩阵条件策略枚举"""
    EQUILIBRATION = "equilibration"  # 平衡缩放
    GEOMETRIC_SCALING = "geometric"  # 几何缩放
    ITERATIVE_SCALING = "iterative"  # 迭代缩放
    PHYSIC_BASED = "physics"        # 基于物理量纲

@dataclass
class OptimizationConfig:
    """优化配置参数"""
    # Jacobian条件优化
    matrix_strategy: MatrixConditioningStrategy = MatrixConditioningStrategy.PHYSIC_BASED
    max_condition_number: float = 1e12
    scaling_tolerance: float = 1e-6
    
    # 自适应时间步长
    cfl_target: float = 0.5
    cfl_safety_factor: float = 0.8
    dt_growth_limit: float = 1.5
    dt_reduction_factor: float = 0.7
    min_timestep: float = 0.01
    max_timestep: float = 10.0
    
    # 松弛因子策略
    initial_relaxation: float = 0.7
    min_relaxation: float = 0.01
    max_relaxation: float = 1.0
    relaxation_adaptation_rate: float = 0.1
    convergence_memory: int = 3  # 收敛历史记忆长度
    
    # 稀疏矩阵优化
    sparsity_threshold: float = 0.3  # 稀疏度阈值
    use_sparse_solver: bool = True
    preconditioner_type: str = "ilu"  # ilu, diagonal, none
    
    # 收敛控制
    residual_history_length: int = 5
    stagnation_threshold: float = 1e-3
    divergence_threshold: float = 2.0

class AdvancedNumericalOptimizer:
    """高级数值稳定性优化器"""
    
    def __init__(self, config: Optional[OptimizationConfig] = None, 
                 logger: Optional[logging.Logger] = None):
        self.config = config or OptimizationConfig()
        self.logger = logger or logging.getLogger("AdvancedOptimizer")
        
        # 特征尺度
        self.characteristic_scales = {
            'flow': 1.0,
            'level': 1.0,
            'length': 1000.0,
            'time': 60.0,
            'velocity': 1.0,
            'area': 100.0
        }
        
        # 历史信息
        self.residual_history: List[float] = []
        self.timestep_history: List[float] = []
        self.relaxation_history: List[float] = []
        
        # 统计信息
        self.stats = {
            'matrix_conditioned': 0,
            'timestep_adapted': 0,
            'relaxation_adjusted': 0,
            'sparse_solver_used': 0,
            'preconditioning_applied': 0,
            'convergence_improved': 0
        }
        
        # 预条件器缓存
        self._preconditioner_cache = None
        self._last_jacobian_pattern = None
    
    def update_characteristic_scales(self, solver_state: Dict[str, Any]) -> None:
        """更新特征尺度"""
        try:
            # 从求解器状态中提取特征尺度
            if 'current_state' in solver_state:
                state = solver_state['current_state']
                if len(state) > 0:
                    flows = state[:len(state)//2] if len(state) > 1 else [state[0]]
                    self.characteristic_scales['flow'] = max(np.mean(np.abs(flows)), 1.0)
            
            if 'water_levels' in solver_state:
                levels = list(solver_state['water_levels'].values())
                if levels:
                    level_range = max(levels) - min(levels)
                    self.characteristic_scales['level'] = max(level_range, 0.1)
            
            if 'geometry' in solver_state:
                geom = solver_state['geometry']
                if 'length_scale' in geom:
                    self.characteristic_scales['length'] = geom['length_scale']
                if 'area_scale' in geom:
                    self.characteristic_scales['area'] = geom['area_scale']
            
            # 推导其他尺度
            self.characteristic_scales['velocity'] = (
                self.characteristic_scales['flow'] / 
                max(self.characteristic_scales['area'], 1.0)
            )
            
            self.logger.debug(f"更新特征尺度: {self.characteristic_scales}")
            
        except Exception as e:
            self.logger.warning(f"特征尺度更新失败: {e}")
    
    def optimize_jacobian_matrix(self, jacobian: np.ndarray, 
                                residual: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        高级Jacobian矩阵优化
        
        实现多种scaling策略和条件改善技术
        """
        if jacobian.size == 0:
            return jacobian, residual
        
        n_vars = jacobian.shape[0]
        original_cond = self._compute_condition_number(jacobian)
        
        self.logger.debug(f"原始矩阵: {n_vars}x{n_vars}, 条件数: {original_cond:.2e}")
        
        # 策略选择
        if self.config.matrix_strategy == MatrixConditioningStrategy.PHYSIC_BASED:
            return self._physics_based_scaling(jacobian, residual)
        elif self.config.matrix_strategy == MatrixConditioningStrategy.EQUILIBRATION:
            return self._equilibration_scaling(jacobian, residual)
        elif self.config.matrix_strategy == MatrixConditioningStrategy.GEOMETRIC_SCALING:
            return self._geometric_scaling(jacobian, residual)
        elif self.config.matrix_strategy == MatrixConditioningStrategy.ITERATIVE_SCALING:
            return self._iterative_scaling(jacobian, residual)
        else:
            return jacobian, residual
    
    def _physics_based_scaling(self, jacobian: np.ndarray, 
                              residual: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """基于物理量纲的scaling"""
        n_vars = jacobian.shape[0]
        
        # 构建scaling矩阵
        row_scales = np.ones(n_vars)
        col_scales = np.ones(n_vars)
        
        # 基于方程物理意义设置行scaling
        for i in range(n_vars):
            if i % 2 == 0:  # 连续性方程 [L³/T]/[L] = [L²/T]
                scale = self.characteristic_scales['flow'] / self.characteristic_scales['length']
                row_scales[i] = 1.0 / scale
            else:  # 动量方程 [L²/T²]
                scale = self.characteristic_scales['velocity']**2
                row_scales[i] = 1.0 / scale
        
        # 基于变量类型设置列scaling  
        n_flow = n_vars // 2
        for j in range(n_vars):
            if j < n_flow:  # 流量变量 [L³/T]
                col_scales[j] = self.characteristic_scales['flow']
            else:  # 水位变量 [L]
                col_scales[j] = self.characteristic_scales['level']
        
        # 应用scaling
        jacobian_scaled = jacobian.copy()
        residual_scaled = residual.copy()
        
        # 行scaling
        for i in range(n_vars):
            jacobian_scaled[i, :] *= row_scales[i]
            residual_scaled[i] *= row_scales[i]
        
        # 列scaling
        for j in range(n_vars):
            jacobian_scaled[:, j] /= col_scales[j]
        
        # 验证改善效果
        scaled_cond = self._compute_condition_number(jacobian_scaled)
        original_cond = self._compute_condition_number(jacobian)
        
        # 强制使用优化后的矩阵，特别是对于无穷大条件数
        if original_cond == float('inf') or scaled_cond < original_cond:
            self.stats['matrix_conditioned'] += 1
            self.logger.debug(f"物理scaling改善条件数: {original_cond:.2e} -> {scaled_cond:.2e}")
            return jacobian_scaled, residual_scaled
        elif scaled_cond < original_cond * 0.8:  # 20%改善阈值
            self.stats['matrix_conditioned'] += 1
            self.logger.debug(f"物理scaling显著改善条件数: {original_cond:.2e} -> {scaled_cond:.2e}")
            return jacobian_scaled, residual_scaled
        else:
            # 对于极端情况，仍然使用优化后的矩阵
            self.logger.debug(f"物理scaling改善有限，但仍使用: {original_cond:.2e} -> {scaled_cond:.2e}")
            return jacobian_scaled, residual_scaled
    
    def _equilibration_scaling(self, jacobian: np.ndarray, 
                              residual: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """平衡缩放策略"""
        try:
            # 计算行和列的2-范数
            row_norms = np.sqrt(np.sum(jacobian**2, axis=1))
            col_norms = np.sqrt(np.sum(jacobian**2, axis=0))
            
            # 避免零范数
            row_norms = np.where(row_norms < 1e-14, 1.0, row_norms)
            col_norms = np.where(col_norms < 1e-14, 1.0, col_norms)
            
            # 构建缩放矩阵
            row_scales = 1.0 / np.sqrt(row_norms)
            col_scales = 1.0 / np.sqrt(col_norms)
            
            # 应用缩放
            jacobian_scaled = np.diag(row_scales) @ jacobian @ np.diag(col_scales)
            residual_scaled = row_scales * residual
            
            self.stats['matrix_conditioned'] += 1
            self.logger.debug("应用平衡缩放")
            
            return jacobian_scaled, residual_scaled
            
        except Exception as e:
            self.logger.warning(f"平衡缩放失败: {e}")
            return jacobian, residual
    
    def _geometric_scaling(self, jacobian: np.ndarray, 
                          residual: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """几何平均缩放"""
        try:
            n = jacobian.shape[0]
            
            # 计算几何平均
            row_geo_mean = np.exp(np.mean(np.log(np.abs(jacobian) + 1e-14), axis=1))
            col_geo_mean = np.exp(np.mean(np.log(np.abs(jacobian) + 1e-14), axis=0))
            
            # 构建缩放因子
            row_scales = 1.0 / row_geo_mean
            col_scales = 1.0 / col_geo_mean
            
            # 应用缩放
            jacobian_scaled = np.diag(row_scales) @ jacobian @ np.diag(col_scales)
            residual_scaled = row_scales * residual
            
            self.stats['matrix_conditioned'] += 1
            self.logger.debug("应用几何缩放")
            
            return jacobian_scaled, residual_scaled
            
        except Exception as e:
            self.logger.warning(f"几何缩放失败: {e}")
            return jacobian, residual
    
    def _iterative_scaling(self, jacobian: np.ndarray, 
                          residual: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """迭代缩放策略"""
        try:
            current_jacobian = jacobian.copy()
            current_residual = residual.copy()
            
            # 迭代改善
            for iter in range(3):  # 最多3次迭代
                # 计算当前条件数
                current_cond = self._compute_condition_number(current_jacobian)
                
                if current_cond < self.config.max_condition_number:
                    break
                
                # 应用一步平衡缩放
                current_jacobian, current_residual = self._equilibration_scaling(
                    current_jacobian, current_residual)
            
            self.stats['matrix_conditioned'] += 1
            return current_jacobian, current_residual
            
        except Exception as e:
            self.logger.warning(f"迭代缩放失败: {e}")
            return jacobian, residual
    
    def _compute_condition_number(self, matrix: np.ndarray) -> float:
        """安全计算条件数"""
        try:
            if matrix.size == 0:
                return 1.0
            return float(np.linalg.cond(matrix))
        except:
            return float('inf')
    
    def adaptive_timestep_control(self, current_dt: float, 
                                 residual_norm: float,
                                 cfl_number: float,
                                 iteration_count: int) -> float:
        """
        智能自适应时间步长控制
        
        基于CFL条件、收敛性和稀疏矩阵特性动态调整
        """
        new_dt = current_dt
        
        # 更新历史
        self.residual_history.append(residual_norm)
        self.timestep_history.append(current_dt)
        
        # 保持历史长度
        if len(self.residual_history) > self.config.residual_history_length:
            self.residual_history.pop(0)
            self.timestep_history.pop(0)
        
        # 1. CFL条件约束
        if cfl_number > self.config.cfl_target:
            dt_cfl = current_dt * self.config.cfl_target / cfl_number * self.config.cfl_safety_factor
            new_dt = min(new_dt, dt_cfl)
            self.logger.debug(f"CFL约束: {cfl_number:.3f} -> dt={dt_cfl:.3f}")
        
        # 2. 收敛性分析
        if len(self.residual_history) >= 2:
            convergence_trend = self._analyze_convergence_trend()
            
            if convergence_trend == "diverging":
                new_dt *= self.config.dt_reduction_factor
                self.logger.debug(f"发散检测，减小时间步: {new_dt:.3f}")
            elif convergence_trend == "fast_converging":
                new_dt *= self.config.dt_growth_limit
                self.logger.debug(f"快速收敛，增大时间步: {new_dt:.3f}")
            elif convergence_trend == "stagnating":
                new_dt *= 0.9  # 轻微减小
                self.logger.debug(f"收敛停滞，轻微减小时间步: {new_dt:.3f}")
        
        # 3. 迭代次数控制
        if iteration_count > 15:
            new_dt *= 0.8  # 迭代过多，减小时间步
        elif iteration_count < 5:
            new_dt = min(new_dt * 1.1, current_dt * self.config.dt_growth_limit)
        
        # 4. 残差幅值控制
        if residual_norm > 100.0:
            new_dt *= 0.5
        elif residual_norm < 0.01:
            new_dt *= 1.2
        
        # 应用边界限制
        new_dt = np.clip(new_dt, self.config.min_timestep, self.config.max_timestep)
        
        # 记录统计
        if abs(new_dt - current_dt) > 0.01 * current_dt:
            self.stats['timestep_adapted'] += 1
        
        return new_dt
    
    def _analyze_convergence_trend(self) -> str:
        """分析收敛趋势"""
        if len(self.residual_history) < 2:
            return "unknown"
        
        recent_residuals = self.residual_history[-3:]
        
        # 计算变化率
        if len(recent_residuals) >= 2:
            rate = recent_residuals[-1] / recent_residuals[-2] if recent_residuals[-2] > 0 else 1.0
            
            if rate > self.config.divergence_threshold:
                return "diverging"
            elif rate < 0.1:
                return "fast_converging"
            elif abs(rate - 1.0) < self.config.stagnation_threshold:
                return "stagnating"
            else:
                return "normal_converging"
        
        return "unknown"
    
    def dynamic_relaxation_strategy(self, iteration: int,
                                   residual_norm: float,
                                   jacobian_cond: float,
                                   current_alpha: float) -> float:
        """
        动态松弛因子策略
        
        基于收敛历史、矩阵条件数和迭代阶段智能调整
        """
        # 更新历史
        self.relaxation_history.append(current_alpha)
        if len(self.relaxation_history) > self.config.convergence_memory:
            self.relaxation_history.pop(0)
        
        new_alpha = current_alpha
        
        # 1. 基于收敛历史的调整
        if len(self.residual_history) >= 2:
            improvement_ratio = self._calculate_improvement_ratio()
            
            if improvement_ratio < -0.1:  # 明显恶化
                new_alpha *= 0.5
                self.logger.debug(f"收敛恶化，减小松弛: {current_alpha:.3f} -> {new_alpha:.3f}")
            elif improvement_ratio > 0.5:  # 快速改善
                new_alpha = min(new_alpha * 1.2, self.config.max_relaxation)
                self.logger.debug(f"快速改善，增大松弛: {current_alpha:.3f} -> {new_alpha:.3f}")
            elif 0 < improvement_ratio < 0.05:  # 缓慢改善
                new_alpha *= 0.9
        
        # 2. 基于矩阵条件数的调整
        if jacobian_cond > 1e15:  # 条件数过大
            new_alpha *= 0.7
            self.logger.debug(f"条件数过大({jacobian_cond:.2e})，保守松弛: {new_alpha:.3f}")
        elif jacobian_cond < 1e8:  # 条件数良好
            new_alpha = min(new_alpha * 1.1, self.config.max_relaxation)
        
        # 3. 迭代阶段策略
        if iteration < 3:  # 初始阶段
            new_alpha = max(new_alpha, 0.3)  # 不过于保守
        elif iteration > 20:  # 后期阶段
            new_alpha *= 0.95  # 更加保守
        
        # 4. 自适应学习
        if len(self.relaxation_history) >= 3:
            # 如果最近几次调整都在减小，说明系统敏感
            recent_changes = [self.relaxation_history[i] - self.relaxation_history[i-1] 
                            for i in range(1, len(self.relaxation_history))]
            if all(change < 0 for change in recent_changes[-2:]):
                new_alpha *= 0.9  # 进一步保守
        
        # 应用边界限制
        new_alpha = np.clip(new_alpha, self.config.min_relaxation, self.config.max_relaxation)
        
        # 记录统计
        if abs(new_alpha - current_alpha) > 0.01:
            self.stats['relaxation_adjusted'] += 1
        
        return new_alpha
    
    def _calculate_improvement_ratio(self) -> float:
        """计算改善率"""
        if len(self.residual_history) < 2:
            return 0.0
        
        current = self.residual_history[-1]
        previous = self.residual_history[-2]
        
        if previous > 0:
            return (previous - current) / previous
        return 0.0
    
    def solve_with_sparse_optimization(self, jacobian: np.ndarray, 
                                     residual: np.ndarray) -> np.ndarray:
        """
        稀疏矩阵优化求解
        
        根据矩阵稀疏度自动选择最优求解策略
        """
        n = jacobian.shape[0]
        
        # 计算稀疏度
        sparsity = np.count_nonzero(jacobian) / jacobian.size
        
        if sparsity < self.config.sparsity_threshold and n > 50:
            # 使用稀疏求解器
            return self._sparse_solve(jacobian, residual)
        else:
            # 使用密集求解器
            return self._dense_solve(jacobian, residual)
    
    def _sparse_solve(self, jacobian: np.ndarray, residual: np.ndarray) -> np.ndarray:
        """稀疏矩阵求解"""
        try:
            # 转换为稀疏格式
            jacobian_sparse = sp.csr_matrix(jacobian)
            
            # 预条件器
            if self.config.preconditioner_type == "ilu":
                preconditioner = self._get_ilu_preconditioner(jacobian_sparse)
                if preconditioner is not None:
                    # 使用预条件GMRES
                    from scipy.sparse.linalg import gmres
                    delta, info = gmres(jacobian_sparse, -residual, M=preconditioner, 
                                      maxiter=50, tol=1e-6)
                    if info == 0:
                        self.stats['sparse_solver_used'] += 1
                        self.stats['preconditioning_applied'] += 1
                        return delta
            
            # 直接稀疏求解
            delta = spsolve(jacobian_sparse, -residual)
            self.stats['sparse_solver_used'] += 1
            return delta
            
        except Exception as e:
            self.logger.warning(f"稀疏求解失败: {e}, 回退到密集求解")
            return self._dense_solve(jacobian, residual)
    
    def _dense_solve(self, jacobian: np.ndarray, residual: np.ndarray) -> np.ndarray:
        """密集矩阵求解"""
        try:
            # 首先尝试标准LU分解
            delta = solve(jacobian, -residual)
            return delta
        except np.linalg.LinAlgError:
            try:
                # 使用SVD求解
                U, s, Vt = np.linalg.svd(jacobian, full_matrices=False)
                # 去除小奇异值
                s_thresh = np.max(s) * 1e-12
                s_inv = np.where(s > s_thresh, 1.0/s, 0.0)
                delta = Vt.T @ (s_inv * (U.T @ (-residual)))
                return delta
            except:
                # 最后手段：伪逆
                delta = np.linalg.pinv(jacobian) @ (-residual)
                return delta
    
    def _get_ilu_preconditioner(self, sparse_matrix):
        """获取ILU预条件器"""
        try:
            # 检查缓存
            current_pattern = (sparse_matrix.nnz, sparse_matrix.shape)
            if (self._preconditioner_cache is not None and 
                current_pattern == self._last_jacobian_pattern):
                return self._preconditioner_cache
            
            # 计算ILU分解
            ilu = spilu(sparse_matrix, drop_tol=1e-4, fill_factor=10)
            
            # 构建预条件器
            def preconditioner_solve(x):
                return ilu.solve(x)
            
            preconditioner = LinearOperator(sparse_matrix.shape, 
                                          matvec=preconditioner_solve)
            
            # 更新缓存
            self._preconditioner_cache = preconditioner
            self._last_jacobian_pattern = current_pattern
            
            return preconditioner
            
        except Exception as e:
            self.logger.warning(f"ILU预条件器构建失败: {e}")
            return None
    
    def get_optimization_report(self) -> Dict[str, Any]:
        """获取优化报告"""
        total_operations = sum(self.stats.values())
        
        report = {
            'optimization_statistics': self.stats.copy(),
            'total_optimizations': total_operations,
            'characteristic_scales': self.characteristic_scales.copy(),
            'current_config': {
                'matrix_strategy': self.config.matrix_strategy.value,
                'cfl_target': self.config.cfl_target,
                'relaxation_range': [self.config.min_relaxation, self.config.max_relaxation],
                'sparse_threshold': self.config.sparsity_threshold
            },
            'performance_metrics': {
                'avg_residual': np.mean(self.residual_history) if self.residual_history else 0.0,
                'convergence_trend': self._analyze_convergence_trend(),
                'timestep_stability': np.std(self.timestep_history) if len(self.timestep_history) > 1 else 0.0
            }
        }
        
        return report
    
    def reset_optimization_state(self):
        """重置优化状态"""
        self.residual_history.clear()
        self.timestep_history.clear()
        self.relaxation_history.clear()
        self._preconditioner_cache = None
        self._last_jacobian_pattern = None
        
        # 重置统计
        for key in self.stats:
            self.stats[key] = 0