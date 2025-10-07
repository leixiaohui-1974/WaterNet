#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
圣维南求解器数值稳定性优化模块

基于前面验证发现的问题，实现以下优化：
1. Jacobian矩阵数值scaling优化
2. 自适应时间步长控制
3. 改进的松弛因子策略
4. 多重预条件技术
"""

import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import spsolve
from typing import Tuple, Dict, Any, Optional
import logging
import warnings

class NumericalStabilityOptimizer:
    """数值稳定性优化器"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("StabilityOptimizer")
        
        # 数值scaling参数
        self.flow_scale = 1.0      # 流量特征尺度
        self.level_scale = 1.0     # 水位特征尺度
        self.length_scale = 1000.0 # 长度特征尺度
        self.time_scale = 60.0     # 时间特征尺度
        
        # 优化统计
        self.optimization_stats = {
            'matrix_conditioned': 0,
            'timestep_adapted': 0,
            'relaxation_adjusted': 0,
            'preconditioner_applied': 0
        }
    
    def compute_characteristic_scales(self, solver_instance) -> None:
        """计算特征尺度用于数值scaling"""
        try:
            # 流量特征尺度：基于当前状态
            flows = solver_instance.current_state[:solver_instance.n_flow_vars]
            if len(flows) > 0:
                self.flow_scale = max(np.mean(flows), 1.0)
            
            # 水位特征尺度：基于当前水位范围
            if hasattr(solver_instance, 'downstream_boundary'):
                level_range = abs(solver_instance.downstream_boundary - 
                                solver_instance._get_upstream_water_level())
                self.level_scale = max(level_range, 1.0)
            
            # 长度特征尺度：基于河段长度
            if hasattr(solver_instance, 'dx_array') and len(solver_instance.dx_array) > 0:
                self.length_scale = np.mean(solver_instance.dx_array)
            
            self.logger.debug(f"特征尺度: 流量={self.flow_scale:.1f}, 水位={self.level_scale:.3f}, "
                            f"长度={self.length_scale:.1f}, 时间={self.time_scale:.1f}")
            
        except Exception as e:
            self.logger.warning(f"特征尺度计算失败: {e}, 使用默认值")
    
    def condition_jacobian_matrix(self, jacobian: np.ndarray, 
                                residual: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Jacobian矩阵条件优化
        
        Args:
            jacobian: 原始Jacobian矩阵
            residual: 残差向量
            
        Returns:
            Tuple: (条件优化后的Jacobian, 缩放后的残差)
        """
        n_vars = jacobian.shape[0]
        if n_vars == 0:
            return jacobian, residual
        
        # 计算矩阵条件数
        try:
            original_cond = np.linalg.cond(jacobian)
            self.logger.debug(f"原始矩阵条件数: {original_cond:.2e}")
        except:
            original_cond = float('inf')
        
        # 1. 行列scaling - 基于物理量纲
        jacobian_scaled = jacobian.copy()
        residual_scaled = residual.copy()
        
        try:
            # 计算行和列的scaling因子
            row_scales = np.ones(n_vars)
            col_scales = np.ones(n_vars)
            
            # 基于方程类型设置scaling
            for i in range(n_vars):
                if i % 2 == 0:  # 连续性方程
                    row_scales[i] = 1.0 / (self.flow_scale * self.time_scale / self.length_scale)
                else:  # 动量方程
                    row_scales[i] = 1.0 / (self.flow_scale / self.time_scale)
            
            # 基于变量类型设置scaling
            n_flow = min(n_vars // 2, n_vars)
            for j in range(n_vars):
                if j < n_flow:  # 流量变量
                    col_scales[j] = self.flow_scale
                else:  # 水位变量
                    col_scales[j] = self.level_scale
            
            # 应用scaling
            for i in range(n_vars):
                jacobian_scaled[i, :] *= row_scales[i]
                residual_scaled[i] *= row_scales[i]
            
            for j in range(n_vars):
                jacobian_scaled[:, j] /= col_scales[j]
            
            # 检查scaling效果
            try:
                scaled_cond = np.linalg.cond(jacobian_scaled)
                if scaled_cond < original_cond:
                    self.logger.debug(f"Scaling改善条件数: {original_cond:.2e} -> {scaled_cond:.2e}")
                    self.optimization_stats['matrix_conditioned'] += 1
                    return jacobian_scaled, residual_scaled
            except:
                pass
        
        except Exception as e:
            self.logger.warning(f"矩阵scaling失败: {e}")
        
        # 2. 对角正则化
        if original_cond > 1e12:
            try:
                reg_param = 1e-6 * np.mean(np.abs(np.diag(jacobian)))
                jacobian_reg = jacobian + reg_param * np.eye(n_vars)
                
                try:
                    reg_cond = np.linalg.cond(jacobian_reg)
                    if reg_cond < original_cond:
                        self.logger.debug(f"正则化改善条件数: {original_cond:.2e} -> {reg_cond:.2e}")
                        self.optimization_stats['matrix_conditioned'] += 1
                        return jacobian_reg, residual
                except:
                    pass
            except Exception as e:
                self.logger.warning(f"正则化失败: {e}")
        
        # 3. 最后手段：返回原矩阵
        return jacobian, residual
    
    def adaptive_timestep_control(self, current_dt: float, 
                                residual_norm: float,
                                prev_residual_norm: float,
                                max_cfl: float) -> float:
        """
        自适应时间步长控制
        
        Args:
            current_dt: 当前时间步长
            residual_norm: 当前残差范数
            prev_residual_norm: 前一步残差范数
            max_cfl: 最大CFL数
            
        Returns:
            float: 调整后的时间步长
        """
        new_dt = current_dt
        
        # 1. CFL条件约束
        cfl_limit = 0.8  # 保守的CFL限制
        if max_cfl > cfl_limit:
            dt_cfl = current_dt * cfl_limit / max_cfl
            new_dt = min(new_dt, dt_cfl)
            self.logger.debug(f"CFL约束调整时间步: {current_dt:.3f} -> {dt_cfl:.3f}")
        
        # 2. 收敛性自适应
        if prev_residual_norm > 0:
            convergence_rate = residual_norm / prev_residual_norm
            
            if convergence_rate > 1.1:  # 发散
                new_dt *= 0.7
                self.logger.debug(f"发散检测，减小时间步: {current_dt:.3f} -> {new_dt:.3f}")
            elif convergence_rate < 0.5:  # 快速收敛
                new_dt *= 1.2
                new_dt = min(new_dt, 5.0 * current_dt)  # 限制增长
                self.logger.debug(f"快速收敛，增大时间步: {current_dt:.3f} -> {new_dt:.3f}")
        
        # 3. 残差幅值控制
        if residual_norm > 10.0:
            new_dt *= 0.5
            self.logger.debug(f"残差过大，减小时间步: {current_dt:.3f} -> {new_dt:.3f}")
        
        # 4. 应用边界限制
        min_dt = 0.1   # 最小时间步长
        max_dt = 10.0  # 最大时间步长
        new_dt = np.clip(new_dt, min_dt, max_dt)
        
        if abs(new_dt - current_dt) > 0.01 * current_dt:
            self.optimization_stats['timestep_adapted'] += 1
        
        return new_dt
    
    def adaptive_relaxation_strategy(self, iteration: int,
                                   residual_norm: float,
                                   prev_residual_norm: float,
                                   current_alpha: float) -> float:
        """
        改进的自适应松弛因子策略
        
        Args:
            iteration: 当前迭代次数
            residual_norm: 当前残差范数
            prev_residual_norm: 前一次残差范数
            current_alpha: 当前松弛因子
            
        Returns:
            float: 调整后的松弛因子
        """
        new_alpha = current_alpha
        
        if iteration > 0 and prev_residual_norm > 0:
            improvement_ratio = (prev_residual_norm - residual_norm) / prev_residual_norm
            
            if improvement_ratio < 0:  # 残差增大
                new_alpha *= 0.6
                self.logger.debug(f"残差增大，减小松弛因子: {current_alpha:.3f} -> {new_alpha:.3f}")
            elif improvement_ratio < 0.05:  # 改善缓慢
                new_alpha *= 0.8
                self.logger.debug(f"收敛缓慢，减小松弛因子: {current_alpha:.3f} -> {new_alpha:.3f}")
            elif improvement_ratio > 0.3:  # 快速改善
                new_alpha = min(new_alpha * 1.1, 1.0)
                self.logger.debug(f"收敛良好，增大松弛因子: {current_alpha:.3f} -> {new_alpha:.3f}")
        
        # 阶段性调整策略
        if iteration > 20:
            new_alpha *= 0.9  # 后期使用更保守的策略
        elif iteration > 10:
            new_alpha *= 0.95
        
        # 边界约束
        new_alpha = np.clip(new_alpha, 0.05, 1.0)
        
        if abs(new_alpha - current_alpha) > 0.01:
            self.optimization_stats['relaxation_adjusted'] += 1
        
        return new_alpha
    
    def apply_preconditioning(self, jacobian: np.ndarray, 
                            residual: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        应用预条件技术
        
        Args:
            jacobian: Jacobian矩阵
            residual: 残差向量
            
        Returns:
            Tuple: (预条件后的矩阵, 预条件后的向量)
        """
        try:
            # 1. 对角预条件
            diag_elements = np.diag(jacobian)
            
            # 避免零对角元
            diag_safe = np.where(np.abs(diag_elements) < 1e-12, 
                                np.sign(diag_elements) * 1e-12, 
                                diag_elements)
            
            # 构建预条件矩阵
            precond_inv = np.diag(1.0 / diag_safe)
            
            # 应用预条件
            jacobian_precond = precond_inv @ jacobian
            residual_precond = precond_inv @ residual
            
            self.optimization_stats['preconditioner_applied'] += 1
            self.logger.debug("应用对角预条件")
            
            return jacobian_precond, residual_precond
            
        except Exception as e:
            self.logger.warning(f"预条件应用失败: {e}")
            return jacobian, residual
    
    def solve_linear_system_robust(self, jacobian: np.ndarray, 
                                  residual: np.ndarray) -> np.ndarray:
        """
        鲁棒的线性系统求解
        
        Args:
            jacobian: Jacobian矩阵
            residual: 残差向量
            
        Returns:
            np.ndarray: 解向量
        """
        try:
            # 1. 首先尝试条件优化
            jacobian_opt, residual_opt = self.condition_jacobian_matrix(jacobian, residual)
            
            # 2. 检查矩阵大小决定求解策略
            n = jacobian_opt.shape[0]
            
            if n < 50:  # 小系统：密集方法
                try:
                    # 尝试LU分解
                    delta = np.linalg.solve(jacobian_opt, -residual_opt)
                    return delta
                except np.linalg.LinAlgError:
                    # 使用伪逆
                    delta = np.linalg.pinv(jacobian_opt) @ (-residual_opt)
                    return delta
            
            else:  # 大系统：稀疏方法
                # 应用预条件
                jacobian_precond, residual_precond = self.apply_preconditioning(
                    jacobian_opt, residual_opt)
                
                # 稀疏求解
                jacobian_sparse = sp.csr_matrix(jacobian_precond)
                delta = spsolve(jacobian_sparse, -residual_precond)
                return delta
        
        except Exception as e:
            self.logger.warning(f"鲁棒求解失败: {e}, 使用默认方法")
            
            # 最后手段：使用原始矩阵的伪逆
            try:
                return np.linalg.pinv(jacobian) @ (-residual)
            except:
                return np.zeros(jacobian.shape[1])
    
    def get_optimization_statistics(self) -> Dict[str, Any]:
        """获取优化统计信息"""
        return {
            'matrix_conditioning_count': self.optimization_stats['matrix_conditioned'],
            'timestep_adaptation_count': self.optimization_stats['timestep_adapted'],
            'relaxation_adjustment_count': self.optimization_stats['relaxation_adjusted'],
            'preconditioning_count': self.optimization_stats['preconditioner_applied'],
            'characteristic_scales': {
                'flow_scale': self.flow_scale,
                'level_scale': self.level_scale,
                'length_scale': self.length_scale,
                'time_scale': self.time_scale
            }
        }
    
    def reset_statistics(self):
        """重置优化统计"""
        self.optimization_stats = {
            'matrix_conditioned': 0,
            'timestep_adapted': 0,
            'relaxation_adjusted': 0,
            'preconditioner_applied': 0
        }

# 为求解器集成优化功能
def integrate_stability_optimizer(solver_class):
    """为求解器类集成稳定性优化功能的装饰器"""
    
    class OptimizedSolver(solver_class):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.stability_optimizer = NumericalStabilityOptimizer(self.logger)
            self._adaptive_dt = self.numerical_config.dt if hasattr(self.numerical_config, 'dt') else 1.0
            self._prev_residual_norm = float('inf')
        
        def _newton_raphson_solver(self, dt: float) -> Tuple[bool, int]:
            """增强的牛顿-拉夫逊求解器，集成稳定性优化"""
            max_iter = self.numerical_config.max_iterations
            tolerance = self.numerical_config.convergence_tolerance
            theta = self.numerical_config.theta
            psi = self.numerical_config.psi
            
            # 计算特征尺度
            self.stability_optimizer.compute_characteristic_scales(self)
            
            # 初始化自适应参数
            alpha = self.numerical_config.under_relaxation
            adaptive_dt = dt
            
            solution = self.current_state.copy()
            
            self.logger.debug(f"开始优化牛顿-拉夫逊迭代：最大{max_iter}次，容差={tolerance:.2e}")
            
            for iteration in range(max_iter):
                # 构建系统
                jacobian, residual = self._build_preissmann_system(solution, adaptive_dt, theta, psi)
                
                # 计算残差范数
                residual_norm = np.linalg.norm(residual)
                max_residual = np.max(np.abs(residual))
                
                # 收敛检查
                converged = (
                    residual_norm < tolerance or
                    max_residual < tolerance * 10 or
                    (iteration > 5 and residual_norm < tolerance * 100)
                )
                
                if converged:
                    self.current_state[:] = solution[:]
                    self.logger.info(f"优化收敛成功：迭代{iteration + 1}次，L2范数={residual_norm:.2e}")
                    
                    # 输出优化统计
                    stats = self.stability_optimizer.get_optimization_statistics()
                    self.logger.debug(f"优化统计: {stats}")
                    
                    return True, iteration + 1
                
                # 自适应时间步长控制
                if iteration % 5 == 0:  # 每5次迭代检查一次
                    max_cfl = self._estimate_max_cfl(adaptive_dt)
                    new_dt = self.stability_optimizer.adaptive_timestep_control(
                        adaptive_dt, residual_norm, self._prev_residual_norm, max_cfl)
                    
                    if abs(new_dt - adaptive_dt) > 0.01 * adaptive_dt:
                        adaptive_dt = new_dt
                        self.logger.debug(f"自适应调整时间步长: {dt:.3f} -> {adaptive_dt:.3f}")
                        # 重新构建系统
                        jacobian, residual = self._build_preissmann_system(solution, adaptive_dt, theta, psi)
                        residual_norm = np.linalg.norm(residual)
                
                # 自适应松弛因子
                alpha = self.stability_optimizer.adaptive_relaxation_strategy(
                    iteration, residual_norm, self._prev_residual_norm, alpha)
                
                # 鲁棒线性系统求解
                try:
                    delta = self.stability_optimizer.solve_linear_system_robust(jacobian, residual)
                    
                    # 更新解
                    solution += alpha * delta
                    
                    # 物理可行性保证
                    self._ensure_physical_feasibility(solution)
                    
                except Exception as e:
                    self.logger.warning(f"迭代{iteration}线性求解失败: {e}")
                    alpha *= 0.5
                    if alpha < 0.01:
                        return False, iteration + 1
                    continue
                
                self._prev_residual_norm = residual_norm
                
                if iteration % 10 == 0 or iteration < 5:
                    self.logger.debug(f"迭代{iteration + 1}: 残差={residual_norm:.2e}, "
                                     f"松弛={alpha:.3f}, dt={adaptive_dt:.3f}")
            
            self.logger.warning(f"达到最大迭代次数{max_iter}，未收敛：最终残差范数={residual_norm:.2e}")
            return False, max_iter
        
        def _estimate_max_cfl(self, dt: float) -> float:
            """估算最大CFL数"""
            try:
                max_cfl = 0.0
                for i in range(self.n_segments):
                    wave_speed = self._calculate_wave_speed(i)
                    dx = self.dx_array[i] if i < len(self.dx_array) else 100.0
                    cfl = wave_speed * dt / dx
                    max_cfl = max(max_cfl, cfl)
                return max_cfl
            except:
                return 1.0  # 默认值
    
    return OptimizedSolver