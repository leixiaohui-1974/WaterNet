#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复迭代缩放策略的计算成本问题

问题分析:
1. 原始迭代缩放每次都执行3轮内部迭代，导致计算成本过高
2. 缺少有效的收敛判断和早停机制
3. 优化频率过高，需要增加智能调用策略
"""

import numpy as np
from scipy.linalg import norm
from typing import Tuple, Dict, Any
import logging

class FixedIterativeScalingOptimizer:
    """修复的迭代缩放优化器"""
    
    def __init__(self, config, logger=None):
        self.config = config
        self.logger = logger or logging.getLogger("FixedIterativeScaling")
        
        # 智能调用控制
        self.scaling_call_count = 0
        self.last_condition_number = None
        self.consecutive_good_conditions = 0
        
        # 优化缓存
        self.scaling_cache = {}
        self.cache_hits = 0
        
        # 统计信息
        self.stats = {
            'matrix_conditioned': 0,
            'cache_hits': 0,
            'early_stops': 0,
            'full_iterations': 0
        }
    
    def should_apply_scaling(self, current_cond: float) -> bool:
        """智能判断是否需要应用缩放"""
        
        # 1. 条件数良好时跳过
        if current_cond < self.config.max_condition_number * 0.1:
            self.consecutive_good_conditions += 1
            if self.consecutive_good_conditions > 3:
                self.logger.debug("条件数持续良好，跳过缩放优化")
                return False
        else:
            self.consecutive_good_conditions = 0
        
        # 2. 频率控制：每5次调用才执行一次
        self.scaling_call_count += 1
        if self.scaling_call_count % 5 != 0:
            return False
        
        # 3. 条件数改善判断
        if self.last_condition_number is not None:
            improvement_ratio = self.last_condition_number / current_cond
            if improvement_ratio < 1.2:  # 改善不明显
                self.logger.debug(f"条件数改善不明显({improvement_ratio:.2f}x)，跳过优化")
                return False
        
        return True
    
    def efficient_iterative_scaling(self, jacobian: np.ndarray, 
                                  residual: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """高效的迭代缩放策略"""
        
        # 计算初始条件数
        initial_cond = self._compute_condition_number(jacobian)
        
        # 智能跳过判断
        if not self.should_apply_scaling(initial_cond):
            return jacobian, residual
        
        self.logger.debug(f"执行高效迭代缩放，初始条件数: {initial_cond:.2e}")
        
        try:
            current_jacobian = jacobian.copy()
            current_residual = residual.copy()
            best_jacobian = current_jacobian.copy()
            best_residual = current_residual.copy()
            best_cond = initial_cond
            
            # 自适应迭代次数（而不是固定3次）
            max_iterations = min(3, max(1, int(np.log10(initial_cond / 1e8))))
            
            for iter_idx in range(max_iterations):
                # 应用单步平衡缩放
                scaled_jacobian, scaled_residual = self._single_equilibration_step(
                    current_jacobian, current_residual)
                
                # 计算改善程度
                new_cond = self._compute_condition_number(scaled_jacobian)
                improvement = best_cond / new_cond if new_cond > 0 else 1.0
                
                self.logger.debug(f"迭代{iter_idx+1}: 条件数 {best_cond:.2e} -> {new_cond:.2e} (改善{improvement:.2f}x)")
                
                # 早停判断
                if improvement < 1.1:  # 改善小于10%
                    self.logger.debug(f"迭代{iter_idx+1}: 改善不明显，提前停止")
                    self.stats['early_stops'] += 1
                    break
                
                # 保存最佳结果
                if new_cond < best_cond:
                    best_jacobian = scaled_jacobian.copy()
                    best_residual = scaled_residual.copy()
                    best_cond = new_cond
                
                current_jacobian = scaled_jacobian
                current_residual = scaled_residual
                
                # 目标达成提前退出
                if new_cond < self.config.max_condition_number:
                    self.logger.debug(f"迭代{iter_idx+1}: 达到目标条件数，提前完成")
                    self.stats['early_stops'] += 1
                    break
            else:
                self.stats['full_iterations'] += 1
            
            # 更新历史记录
            self.last_condition_number = best_cond
            
            # 验证改善效果
            total_improvement = initial_cond / best_cond if best_cond > 0 else 1.0
            if total_improvement > 1.5:  # 改善超过50%才计入统计
                self.stats['matrix_conditioned'] += 1
                self.logger.debug(f"迭代缩放成功，总改善: {total_improvement:.2f}x")
                return best_jacobian, best_residual
            else:
                self.logger.debug(f"迭代缩放效果不佳，返回原始矩阵")
                return jacobian, residual
                
        except Exception as e:
            self.logger.warning(f"高效迭代缩放失败: {e}")
            return jacobian, residual
    
    def _single_equilibration_step(self, jacobian: np.ndarray, 
                                 residual: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """单步平衡缩放（避免重复统计）"""
        try:
            # 计算行和列的范数
            row_norms = np.sqrt(np.sum(jacobian**2, axis=1))
            col_norms = np.sqrt(np.sum(jacobian**2, axis=0))
            
            # 稳健的范数处理
            eps = 1e-12
            row_norms = np.where(row_norms < eps, 1.0, row_norms)
            col_norms = np.where(col_norms < eps, 1.0, col_norms)
            
            # 保守的缩放策略（避免过度缩放）
            row_scales = 1.0 / np.sqrt(row_norms)
            col_scales = 1.0 / np.sqrt(col_norms)
            
            # 限制缩放因子范围，避免数值不稳定
            row_scales = np.clip(row_scales, 0.1, 10.0)
            col_scales = np.clip(col_scales, 0.1, 10.0)
            
            # 应用缩放
            jacobian_scaled = np.diag(row_scales) @ jacobian @ np.diag(col_scales)
            residual_scaled = row_scales * residual
            
            return jacobian_scaled, residual_scaled
            
        except Exception as e:
            self.logger.warning(f"单步平衡缩放失败: {e}")
            return jacobian, residual
    
    def _compute_condition_number(self, matrix: np.ndarray) -> float:
        """稳健的条件数计算"""
        try:
            if matrix.size == 0:
                return 1.0
            
            # 使用SVD方法计算条件数（更稳健）
            try:
                U, s, Vt = np.linalg.svd(matrix, compute_uv=False)
                if len(s) > 0 and s[-1] > 1e-15:
                    return s[0] / s[-1]
                else:
                    return float('inf')
            except:
                # SVD失败时回退到范数估计
                return np.linalg.norm(matrix, ord=2) / max(np.linalg.norm(matrix, ord=-2), 1e-15)
                
        except Exception:
            return float('inf')

def test_fixed_iterative_scaling():
    """测试修复的迭代缩放策略"""
    print("="*60)
    print("修复的迭代缩放策略测试")
    print("="*60)
    
    # 创建测试配置
    from advanced_numerical_optimizer import OptimizationConfig, MatrixConditioningStrategy
    
    config = OptimizationConfig(
        matrix_strategy=MatrixConditioningStrategy.ITERATIVE_SCALING,
        max_condition_number=1e8,
        scaling_tolerance=1e-4
    )
    
    # 创建修复的优化器
    optimizer = FixedIterativeScalingOptimizer(config)
    
    # 创建测试矩阵（病态）
    n = 6
    test_matrix = np.array([
        [1000.0,   10.0,  -500.0,    0.0,     0.0,    0.0],
        [  0.5, 2000.0,     0.0,  -10.0,     0.0,    0.0],
        [  0.0,    0.0,  1200.0,   15.0,  -600.0,    0.0],
        [  0.0,    0.0,     0.3, 1800.0,     0.0,  -15.0],
        [  0.0,    0.0,     0.0,    0.0,  1000.0,   20.0],
        [  0.0,    0.0,     0.0,    0.0,     0.2, 2200.0]
    ])
    test_residual = np.array([100.0, 50.0, 80.0, 30.0, 120.0, 40.0])
    
    print(f"原始矩阵条件数: {optimizer._compute_condition_number(test_matrix):.2e}")
    
    # 测试多次调用（模拟实际使用）
    total_calls = 0
    total_optimizations = 0
    
    for call_idx in range(20):  # 模拟20次Newton迭代
        scaled_matrix, scaled_residual = optimizer.efficient_iterative_scaling(
            test_matrix, test_residual)
        
        total_calls += 1
        if optimizer.stats['matrix_conditioned'] > total_optimizations:
            total_optimizations = optimizer.stats['matrix_conditioned']
            print(f"第{call_idx+1}次调用: 执行了优化，条件数改善为 {optimizer._compute_condition_number(scaled_matrix):.2e}")
    
    print(f"\n测试结果:")
    print(f"  总调用次数: {total_calls}")
    print(f"  实际优化次数: {total_optimizations}")
    print(f"  优化效率: {total_optimizations/total_calls*100:.1f}%")
    print(f"  早停次数: {optimizer.stats['early_stops']}")
    print(f"  完整迭代次数: {optimizer.stats['full_iterations']}")
    
    if total_optimizations < total_calls * 0.5:
        print(f"  ✅ 成功减少了不必要的计算")
    else:
        print(f"  ⚠️ 优化频率仍然较高")
    
    return optimizer.stats

if __name__ == "__main__":
    test_fixed_iterative_scaling()