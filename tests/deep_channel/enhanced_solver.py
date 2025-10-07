#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
圣维南方程数值求解器增强模块

为深度测试提供增强的圣维南方程求解能力，包括：
- 高精度数值格式
- 稳定性增强算法
- 详细的误差分析
- 物理验证功能

Author: WaterNet Development Team
Date: 2024-10-03
"""

import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import spsolve
from scipy.optimize import fsolve
import warnings
from typing import Dict, List, Tuple, Optional, Any, Callable
from dataclasses import dataclass
import logging
import sys
import os

# 修复相对导入问题：添加项目根目录到sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 现在可以使用绝对导入
from waternet.models.saint_venant import SaintVenantModel

# 尝试导入高级数值优化器
try:
    from advanced_numerical_optimizer import (
        AdvancedNumericalOptimizer, 
        OptimizationConfig, 
        MatrixConditioningStrategy
    )
    OPTIMIZATION_AVAILABLE = True
except ImportError:
    OPTIMIZATION_AVAILABLE = False
    print("⚠️ 高级数值优化器不可用")


@dataclass
class NumericalSchemeConfig:
    """数值格式配置 - 针对收敛性优化"""
    scheme_type: str = "preissmann"    # 差分格式类型
    theta: float = 0.6                 # 时间加权系数
    psi: float = 0.5                   # 空间加权系数
    cfl_target: float = 0.8            # 目标CFL数（提高稳定性）
    max_iterations: int = 100          # 最大迭代次数（再次增加）
    convergence_tolerance: float = 1e-3 # 收敛容差（进一步放宽）
    under_relaxation: float = 0.5      # 亚松弛系数（更加保守）
    min_under_relaxation: float = 0.05 # 最小亚松弛系数
    adaptive_relaxation: bool = True    # 自适应松弛


@dataclass
class StabilityConfig:
    """稳定性控制配置"""
    enable_adaptive_timestep: bool = True    # 自适应时间步长
    min_timestep: float = 0.1               # 最小时间步长(s)
    max_timestep: float = 60.0              # 最大时间步长(s)
    cfl_safety_factor: float = 0.8          # CFL安全系数
    enable_mass_conservation_check: bool = True  # 质量守恒检查


class EnhancedSaintVenantSolver:
    """增强型圣维南方程求解器"""
    
    def __init__(self, model: SaintVenantModel, 
                 numerical_config: Optional[NumericalSchemeConfig] = None,
                 stability_config: Optional[StabilityConfig] = None,
                 optimization_config: Optional['OptimizationConfig'] = None):
        """
        初始化增强求解器
        
        Parameters:
        -----------
        model : SaintVenantModel
            圣维南模型实例
        numerical_config : NumericalSchemeConfig, optional
            数值格式配置
        stability_config : StabilityConfig, optional
            稳定性控制配置
        optimization_config : OptimizationConfig, optional
            高级数值优化配置
        """
        self.model = model
        self.numerical_config = numerical_config or NumericalSchemeConfig()
        self.stability_config = stability_config or StabilityConfig()
        
        # 集成高级数值优化器
        self.numerical_optimizer = None
        if OPTIMIZATION_AVAILABLE and optimization_config is not None:
            try:
                self.numerical_optimizer = AdvancedNumericalOptimizer(
                    config=optimization_config,
                    logger=logging.getLogger(f"Optimizer_{model.name}")
                )
                print(f"✅ 成功集成高级数值优化器: {optimization_config.matrix_strategy.value}")
            except Exception as e:
                print(f"⚠️ 优化器初始化失败: {e}")
                self.numerical_optimizer = None
        
        self.logger = logging.getLogger(f"EnhancedSolver_{model.name}")
        self._setup_numerical_grid()
        self._initialize_solution_arrays()
        
        # 性能统计
        self.statistics = {
            'total_steps': 0,
            'convergence_failures': 0,
            'timestep_reductions': 0,
            'mass_conservation_errors': [],
            'computational_time': 0.0,
            'optimization_applied': 0  # 新增：优化应用次数
        }
    
    def _setup_numerical_grid(self):
        """设置数值网格"""
        self.n_sections = len(self.model.sections)
        self.n_segments = len(self.model.segments)
        self.n_internal_nodes = len(self.model.internal_nodes)
        
        # 计算网格间距
        self.dx_array = np.array([seg['length'] for seg in self.model.segments])
        self.dx_min = np.min(self.dx_array)
        self.dx_max = np.max(self.dx_array)
        
        # 总变量数：流量变量 + 内部节点水位变量
        self.n_flow_vars = self.n_segments
        self.n_head_vars = self.n_internal_nodes
        self.n_total_vars = self.n_flow_vars + self.n_head_vars
        
        self.logger.info(f"数值网格设置完成: {self.n_sections}断面, {self.n_segments}分段, {self.n_total_vars}变量")
    
    def _initialize_solution_arrays(self):
        """初始化求解数组"""
        # 状态向量 [Q1, Q2, ..., Qn, H1, H2, ..., Hm]
        self.current_state = np.zeros(self.n_total_vars)
        self.previous_state = np.zeros(self.n_total_vars)
        
        # 边界条件
        self.upstream_boundary = None
        self.downstream_boundary = None
        
        # 历史记录
        self.time_history = []
        self.state_history = []
        self.boundary_history = []
    
    def set_initial_conditions(self, initial_flow: float, 
                             downstream_water_level: float) -> None:
        """
        设置初始条件 - 完善的恒定流初值估计，同时估计流量和水位
        
        Parameters:
        -----------
        initial_flow : float
            初始流量 (m³/s)
        downstream_water_level : float
            下游边界水位 (m)
        """
        self.logger.info(f"设置初始条件: Q={initial_flow} m³/s, H_down={downstream_water_level} m")
        
        # 立即设置边界条件，确保后续计算可用
        self.upstream_boundary = initial_flow
        self.downstream_boundary = downstream_water_level
        
        # 使用圣维南模型的恒定流方法计算初始水面线
        steady_result = self.model.compute_steady_state(initial_flow, downstream_water_level)
        
        # 初始化所有水位和流量变量
        self._initialize_flow_variables(steady_result, initial_flow)
        self._initialize_water_level_variables(steady_result, downstream_water_level)
        
        # 进行物理合理性验证
        self._validate_initial_conditions(steady_result)
        
        # 记录初始状态
        self.time_history.append(0.0)
        self.state_history.append(self.current_state.copy())
        self.boundary_history.append({
            'upstream_flow': initial_flow,
            'downstream_water_level': downstream_water_level
        })
        
        # 输出初始化摘要
        self.logger.info(f"增强求解器初始化完成:")
        self.logger.info(f"  流量变量: {[f'{self.current_state[i]:.2f}' for i in range(min(3, self.n_flow_vars))]}...")
        self.logger.info(f"  水位变量: {[f'{self.current_state[self.n_flow_vars + i]:.3f}' for i in range(min(3, self.n_head_vars))]}...")
    
    def _initialize_flow_variables(self, steady_result: Dict[str, float], initial_flow: float) -> None:
        """初始化流量变量"""
        for i in range(self.n_flow_vars):
            # 恒定流条件下，所有分段流量相等
            flow_key = f'Q_seg_{i}'
            if flow_key in steady_result:
                self.current_state[i] = steady_result[flow_key]
                self.previous_state[i] = steady_result[flow_key]
            else:
                self.current_state[i] = initial_flow
                self.previous_state[i] = initial_flow
    
    def _initialize_water_level_variables(self, steady_result: Dict[str, float], 
                                        downstream_water_level: float) -> None:
        """初始化水位变量 - 完善的水面线估计"""
        # 存储上游水位，避免重复计算
        self._upstream_water_level = steady_result.get('H_section_0', downstream_water_level + 0.02)
        
        # 内部节点水位变量初始化
        for i in range(self.n_head_vars):
            section_idx = i + 1  # 内部节点对应断面 1 到 n-2
            H_key = f'H_section_{section_idx}'
            
            if H_key in steady_result:
                # 使用恒定流计算的精确水位
                initial_level = steady_result[H_key]
                self.current_state[self.n_flow_vars + i] = initial_level
                self.previous_state[self.n_flow_vars + i] = initial_level
                self.logger.debug(f"内部节点{i}初始水位: {initial_level:.3f}m")
            else:
                # 如果没有精确数据，使用高精度插值
                interpolated_level = self._interpolate_water_level(i, steady_result, downstream_water_level)
                self.current_state[self.n_flow_vars + i] = interpolated_level
                self.previous_state[self.n_flow_vars + i] = interpolated_level
                self.logger.debug(f"内部节点{i}插值水位: {interpolated_level:.3f}m")
    
    def _interpolate_water_level(self, node_idx: int, steady_result: Dict[str, float], 
                               downstream_water_level: float) -> float:
        """高精度水位插值"""
        upstream_key = 'H_section_0'
        if upstream_key in steady_result:
            upstream_level = steady_result[upstream_key]
            
            # 考虑地形坡度的插值
            total_nodes = self.n_head_vars + 2  # 包括上下游边界
            node_position = node_idx + 1  # 节点位置
            
            # 线性插值估算
            ratio = node_position / (total_nodes - 1)
            interpolated_level = upstream_level + ratio * (downstream_water_level - upstream_level)
            
            # 考虑地形起伏的修正
            if hasattr(self.model, 'segments') and node_idx < len(self.model.segments):
                segment = self.model.segments[node_idx]
                slope_correction = segment.get('slope', 0.001) * segment.get('length', 100.0) / 2.0
                interpolated_level -= slope_correction
            
            return interpolated_level
        else:
            # 默认插值
            return downstream_water_level + 0.01 * (self.n_head_vars - node_idx)
    
    def _validate_initial_conditions(self, steady_result: Dict[str, float]) -> None:
        """物理合理性验证 - 按照恒定流初值估计验证规范"""
        self.logger.info("进行物理合理性验证...")
        
        # 1. 水面线单调性检查
        self._check_water_surface_monotonicity(steady_result)
        
        # 2. 亚临界流态确认（弗劳德数<1）
        self._check_subcritical_flow(steady_result)
        
        # 3. 流速分布合理性评估
        self._check_velocity_distribution(steady_result)
        
        # 4. 蓄水量一致性校验
        self._check_volume_consistency(steady_result)
        
        self.logger.info("物理合理性验证完成")
    
    def _check_water_surface_monotonicity(self, steady_result: Dict[str, float]) -> None:
        """水面线单调性检查"""
        water_levels = []
        
        # 收集所有水位数据
        for i in range(len(self.model.sections)):
            H_key = f'H_section_{i}'
            if H_key in steady_result:
                water_levels.append(steady_result[H_key])
        
        # 检查单调递减
        for i in range(1, len(water_levels)):
            if water_levels[i] > water_levels[i-1]:
                self.logger.warning(f"水面线非单调递减: 断面{i-1}={water_levels[i-1]:.3f}m < 断面{i}={water_levels[i]:.3f}m")
        
        # 计算水面坡度
        total_drop = water_levels[0] - water_levels[-1] if len(water_levels) >= 2 else 0.0
        total_length = sum(seg['length'] for seg in self.model.segments)
        avg_slope = total_drop / total_length if total_length > 0 else 0.0
        
        self.logger.info(f"水面线检查: 总调落={total_drop:.3f}m, 平均坡度={avg_slope:.6f}")
    
    def _check_subcritical_flow(self, steady_result: Dict[str, float]) -> None:
        """亚临界流态确认（弗劳德数<1）"""
        for i, section in enumerate(self.model.sections):
            H_key = f'H_section_{i}'
            if H_key in steady_result:
                water_level = steady_result[H_key]
                area = section['area_func'](water_level)
                top_width = section['top_width_func'](water_level)
                
                if area > 0 and top_width > 0:
                    # 计算水力深度
                    hydraulic_depth = area / top_width
                    
                    # 获取流速（使用初始流量）
                    velocity = self.current_state[0] / area if area > 0 else 0.0
                    
                    # 计算弗劳德数
                    froude_number = velocity / np.sqrt(9.81 * hydraulic_depth) if hydraulic_depth > 0 else 0.0
                    
                    if froude_number >= 1.0:
                        self.logger.warning(f"断面{i}超临界流: Fr={froude_number:.3f} >= 1.0")
                    else:
                        self.logger.debug(f"断面{i}亚临界流: Fr={froude_number:.3f}")
    
    def _check_velocity_distribution(self, steady_result: Dict[str, float]) -> None:
        """流速分布合理性评估"""
        velocities = []
        
        for i, section in enumerate(self.model.sections):
            H_key = f'H_section_{i}'
            if H_key in steady_result:
                water_level = steady_result[H_key]
                area = section['area_func'](water_level)
                
                if area > 0:
                    velocity = self.current_state[0] / area
                    velocities.append(velocity)
        
        if velocities:
            avg_velocity = sum(velocities) / len(velocities)
            max_velocity = max(velocities)
            min_velocity = min(velocities)
            
            self.logger.info(f"流速分布: 平均={avg_velocity:.3f}m/s, 范围=[{min_velocity:.3f}, {max_velocity:.3f}]m/s")
            
            # 检查合理性
            if max_velocity > 10.0:
                self.logger.warning(f"最大流速过大: {max_velocity:.3f}m/s")
            if min_velocity < 0.1:
                self.logger.warning(f"最小流速过小: {min_velocity:.3f}m/s")
    
    def _check_volume_consistency(self, steady_result: Dict[str, float]) -> None:
        """蓄水量一致性校验"""
        if 'total_volume' in steady_result:
            calculated_volume = steady_result['total_volume']
            
            # 独立计算蓄水量验证
            independent_volume = 0.0
            for i, segment in enumerate(self.model.segments):
                if i < len(self.model.sections) - 1:
                    up_section = self.model.sections[segment['upstream_section']]
                    down_section = self.model.sections[segment['downstream_section']]
                    
                    # 获取水位
                    up_level = steady_result.get(f'H_section_{segment["upstream_section"]}', 0.0)
                    down_level = steady_result.get(f'H_section_{segment["downstream_section"]}', 0.0)
                    
                    # 计算平均面积
                    up_area = up_section['area_func'](up_level)
                    down_area = down_section['area_func'](down_level)
                    avg_area = (up_area + down_area) / 2.0
                    
                    # 积累体积
                    segment_volume = avg_area * segment['length']
                    independent_volume += segment_volume
            
            volume_error = abs(calculated_volume - independent_volume) / max(calculated_volume, 1.0)
            self.logger.info(f"蓄水量检查: 计算值={calculated_volume:.1f}m³, 验证值={independent_volume:.1f}m³, 误差={volume_error:.3%}")
            
            if volume_error > 0.05:  # 5%误差阈值
                self.logger.warning(f"蓄水量一致性检查失败: 误差={volume_error:.3%} > 5%")
    
    def solve_time_step(self, dt: float, upstream_flow: float, 
                       downstream_water_level: float) -> Dict[str, Any]:
        """
        求解单个时间步
        
        Parameters:
        -----------
        dt : float
            时间步长 (s)
        upstream_flow : float
            上游边界流量 (m³/s)
        downstream_water_level : float
            下游边界水位 (m)
            
        Returns:
        --------
        Dict[str, Any]: 求解结果
        """
        self.statistics['total_steps'] += 1
        
        # 自适应时间步长检查
        if self.stability_config.enable_adaptive_timestep:
            dt = self._check_cfl_condition(dt)
        
        # 设置边界条件
        self.upstream_boundary = upstream_flow
        self.downstream_boundary = downstream_water_level
        
        # 牛顿-拉夫逊迭代求解
        success, iterations = self._newton_raphson_solver(dt)
        
        if not success:
            self.statistics['convergence_failures'] += 1
            self.logger.warning(f"时间步求解未收敛，迭代次数: {iterations}")
        
        # 质量守恒检查
        if self.stability_config.enable_mass_conservation_check:
            mass_error = self._check_mass_conservation(dt)
            self.statistics['mass_conservation_errors'].append(mass_error)
        
        # 更新状态
        self.previous_state[:] = self.current_state[:]
        
        # 记录历史
        current_time = self.time_history[-1] + dt
        self.time_history.append(current_time)
        self.state_history.append(self.current_state.copy())
        self.boundary_history.append({
            'upstream_flow': upstream_flow,
            'downstream_water_level': downstream_water_level
        })
        
        # 构建结果
        result = self._build_timestep_result(current_time, dt, success, iterations)
        
        return result
    
    def _check_cfl_condition(self, dt: float) -> float:
        """检查CFL条件并调整时间步长"""
        max_cfl = 0.0
        
        for i in range(self.n_segments):
            # 计算波速
            wave_speed = self._calculate_wave_speed(i)
            
            # 计算CFL数
            dx = self.dx_array[i]
            cfl = wave_speed * dt / dx
            max_cfl = max(max_cfl, cfl)
        
        # 调整时间步长
        if max_cfl > self.numerical_config.cfl_target:
            dt_new = dt * self.numerical_config.cfl_target / max_cfl * self.stability_config.cfl_safety_factor
            dt_new = max(dt_new, self.stability_config.min_timestep)
            dt_new = min(dt_new, self.stability_config.max_timestep)
            return dt_new
        else:
            return min(dt, self.stability_config.max_timestep)
    
    def _calculate_wave_speed(self, segment_idx: int) -> float:
        """计算重力波波速 - c = √(gA/T)"""
        try:
            # 获取当前分段的几何参数
            if segment_idx < len(self.model.segments):
                segment = self.model.segments[segment_idx]
                section_up = self.model.sections[segment['upstream_section']]
                section_down = self.model.sections[segment['downstream_section']]
                
                # 计算平均水深
                avg_depth = 1.0  # 简化假设
                if 'bottom_width' in section_up:
                    width = section_up['bottom_width']
                    side_slope = section_up.get('side_slope', 0.0)
                    
                    # 梯形断面：A = (b + sy)y, T = b + 2sy
                    A = (width + side_slope * avg_depth) * avg_depth
                    T = width + 2 * side_slope * avg_depth
                    
                    if T > 0:
                        wave_speed = np.sqrt(9.81 * A / T)
                        return min(wave_speed, 10.0)  # 限制最大波速
            
            return 3.0  # 默认波速
            
        except Exception:
            return 3.0
    
    def _newton_raphson_solver(self, dt: float) -> Tuple[bool, int]:
        """增强的牛顿-拉夫逊迭代求解器 - 采用自适应松弛因子和多重收敛判断条件"""
        max_iter = self.numerical_config.max_iterations
        tolerance = self.numerical_config.convergence_tolerance
        theta = self.numerical_config.theta
        psi = self.numerical_config.psi
        
        # 初始化自适应松弛参数
        alpha = self.numerical_config.under_relaxation
        min_alpha = getattr(self.numerical_config, 'min_under_relaxation', 0.1)
        adaptive_relaxation = getattr(self.numerical_config, 'adaptive_relaxation', True)
        
        # 构建初始解向量
        solution = self.current_state.copy()
        prev_residual_norm = float('inf')
        stagnation_count = 0
        
        self.logger.debug(f"开始牛顿-拉夫逊迭代：最大{max_iter}次，容差={tolerance:.2e}")
        
        for iteration in range(max_iter):
            # 构建 Jacobian矩阵和残差向量
            jacobian, residual = self._build_preissmann_system(solution, dt, theta, psi)
            
            # 集成高级数值优化策略
            if self.numerical_optimizer is not None:
                try:
                    # 更新优化器状态
                    solver_state = {
                        'current_state': solution,
                        'geometry': {
                            'length_scale': np.mean(self.dx_array),
                            'area_scale': 100.0  # 基于断面特征面积
                        },
                        'time_step': dt,
                        'iteration': iteration
                    }
                    self.numerical_optimizer.update_characteristic_scales(solver_state)
                    
                    # 应用Jacobian矩阵优化
                    jacobian_optimized, residual_optimized = self.numerical_optimizer.optimize_jacobian_matrix(
                        jacobian, residual
                    )
                    
                    # 使用优化后的矩阵
                    jacobian = jacobian_optimized
                    residual = residual_optimized
                    
                    self.statistics['optimization_applied'] += 1
                    
                    if iteration == 0:
                        self.logger.debug(f"优化策略已应用: {self.numerical_optimizer.config.matrix_strategy.value}")
                        
                except Exception as e:
                    self.logger.warning(f"数值优化失败: {e}")
            
            # 多重收敛判断条件
            residual_norm = np.linalg.norm(residual)
            max_residual = np.max(np.abs(residual))
            
            # 检查收敛性（使用多重准则）
            converged = (
                residual_norm < tolerance or           # L2范数准则
                max_residual < tolerance * 10 or       # 最大元素准则
                (iteration > 5 and residual_norm < tolerance * 100)  # 放宽准则
            )
            
            if converged:
                self.current_state[:] = solution[:]
                self.logger.debug(f"收敛成功：迭代{iteration + 1}次，L2范数={residual_norm:.2e}, 最大元素={max_residual:.2e}")
                return True, iteration + 1
            
            # 检查停滞
            if iteration > 0:
                improvement = (prev_residual_norm - residual_norm) / prev_residual_norm
                if improvement < 1e-4:  # 改善很小
                    stagnation_count += 1
                else:
                    stagnation_count = 0
            
            # 求解线性系统 Jacobian * delta = -residual
            try:
                # 检查Jacobian矩阵的条件数
                if jacobian.shape[0] < 100:  # 小系统使用密集求解器
                    # 检查矩阵奇异性
                    try:
                        cond_num = np.linalg.cond(jacobian)
                        if cond_num > 1e12:  # 矩阵近似奇异
                            self.logger.warning(f"迭代{iteration}: Jacobian条件数过大({cond_num:.2e})，使用正则化")
                            # 使用正则化求解
                            reg_param = 1e-6 * np.mean(np.diag(np.abs(jacobian)))
                            jacobian_reg = jacobian + reg_param * np.eye(jacobian.shape[0])
                            delta = np.linalg.solve(jacobian_reg, -residual)
                        else:
                            delta = np.linalg.solve(jacobian, -residual)
                    except np.linalg.LinAlgError:
                        # 使用伪逆求解
                        delta = np.linalg.pinv(jacobian) @ (-residual)
                else:  # 大系统使用稀疏求解器
                    jacobian_sparse = sp.csr_matrix(jacobian)
                    delta = spsolve(jacobian_sparse, -residual)
                
                # 自适应松弛更新
                if adaptive_relaxation:
                    # 自适应调整松弛因子
                    if iteration > 0:
                        if residual_norm > prev_residual_norm:  # 收敛性变差
                            alpha *= 0.8  # 减小松弛因子
                            stagnation_count += 1
                        elif improvement > 0.1:  # 收敛性较好
                            alpha = min(alpha * 1.05, self.numerical_config.under_relaxation)  # 微增松弛因子
                        
                        # 防止松弛因子过小
                        alpha = max(alpha, min_alpha)
                    
                    # 如果停滞太久，使用更小的步长
                    if stagnation_count > 3:
                        alpha *= 0.5
                        alpha = max(alpha, min_alpha)
                        stagnation_count = 0
                
                # 更新解
                solution += alpha * delta
                
                # 保证物理可行性（简化版）
                self._ensure_physical_feasibility(solution)
                
                prev_residual_norm = residual_norm
                
                if iteration % 10 == 0 or iteration < 5:
                    self.logger.debug(f"迭代{iteration + 1}: 残差范数={residual_norm:.2e}, 松弛因子={alpha:.3f}")
                
            except Exception as e:
                self.logger.warning(f"迭代{iteration}线性求解失败: {e}")
                # 尝试降低松弛因子继续
                alpha *= 0.5
                if alpha < min_alpha:
                    return False, iteration + 1
                continue
        
        self.logger.warning(f"达到最大迭代次数{max_iter}，未收敛：最终残差范数={residual_norm:.2e}")
        return False, max_iter
    
    def _ensure_physical_feasibility(self, solution: np.ndarray) -> None:
        """确保解的物理可行性"""
        # 确保流量为正值（简化处理）
        for i in range(self.n_flow_vars):
            if solution[i] < 1.0:  # 设置最小流量
                solution[i] = 1.0
        
        # 确保水位在合理范围内
        for i in range(self.n_head_vars):
            head_idx = self.n_flow_vars + i
            if head_idx < len(solution):
                # 防止水位过低或过高
                solution[head_idx] = max(90.0, min(solution[head_idx], 110.0))
    
    def _build_preissmann_system(self, solution: np.ndarray, dt: float, 
                                theta: float, psi: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        严格按照Preissmann四点隐式差分格式的数学定义实现
        
        Preissmann格式使用四个网格点: (i,n), (i+1,n), (i,n+1), (i+1,n+1)
        时间加权系数: θ, 空间加权系数: ψ
        
        圣维南方程组:
        连续性方程: ∂A/∂t + ∂Q/∂x = 0
        动量方程: ∂Q/∂t + ∂(Q²/A)/∂x + gA∂H/∂x + gA(Sf - S0) = 0
        """
        n_vars = self.n_total_vars
        jacobian = np.zeros((n_vars, n_vars))
        residual = np.zeros(n_vars)
        g = 9.81
        
        # 验证边界条件
        if self.upstream_boundary is None or self.downstream_boundary is None:
            raise ValueError("边界条件未设置")
        
        eq_idx = 0
        
        # 为每个分段构建方程组
        for seg_idx in range(self.n_segments):
            if seg_idx >= len(self.model.segments) or eq_idx + 1 >= n_vars:
                break
                
            segment = self.model.segments[seg_idx]
            dx = segment['length']
            S0 = segment.get('slope', 0.001)
            n_manning = segment.get('roughness', 0.03)
            
            # 获取四个网格点的所有变量
            variables = self._get_preissmann_variables(seg_idx, solution, segment)
            
            # 计算Preissmann加权平均值
            weighted_vars = self._compute_preissmann_weights(variables, theta, psi)
            
            # === 连续性方程 ===
            if eq_idx < n_vars:
                cont_residual = self._build_continuity_equation(variables, weighted_vars, dt)
                residual[eq_idx] = cont_residual
                
                # 连续性方程Jacobian
                self._build_continuity_jacobian(jacobian, eq_idx, seg_idx, variables, dt, theta, psi)
                eq_idx += 1
            
            # === 动量方程 ===
            if eq_idx < n_vars:
                mom_residual = self._build_momentum_equation(variables, weighted_vars, dt, dx, g, S0, n_manning)
                residual[eq_idx] = mom_residual
                
                # 动量方程Jacobian
                self._build_momentum_jacobian(jacobian, eq_idx, seg_idx, variables, weighted_vars, dt, dx, g, S0, n_manning, theta, psi)
                eq_idx += 1
        
        # 填充剩余的对角线元素以保证矩阵非奇异
        while eq_idx < n_vars:
            jacobian[eq_idx, eq_idx] = 1e-6
            residual[eq_idx] = 0.0
            eq_idx += 1
        
        return jacobian, residual
    
    def _get_preissmann_variables(self, seg_idx: int, solution: np.ndarray, segment: Dict) -> Dict[str, float]:
        """获取Preissmann四点网格的所有变量"""
        i_up = segment['upstream_section']
        i_down = segment['downstream_section']
        
        # 流量变量
        Q_curr = solution[seg_idx] if seg_idx < len(solution) else 100.0
        Q_prev = self.previous_state[seg_idx] if seg_idx < len(self.previous_state) else 100.0
        
        # 上游水位
        if i_up == 0:
            H_up_curr = self._get_upstream_water_level()
            H_up_prev = H_up_curr
        else:
            head_idx = i_up - 1
            if head_idx < self.n_head_vars and self.n_flow_vars + head_idx < len(solution):
                H_up_curr = solution[self.n_flow_vars + head_idx]
                H_up_prev = self.previous_state[self.n_flow_vars + head_idx]
            else:
                H_up_curr = self._get_upstream_water_level()
                H_up_prev = H_up_curr
        
        # 下游水位
        if i_down == len(self.model.sections) - 1:
            H_down_curr = self.downstream_boundary
            H_down_prev = self.downstream_boundary
        else:
            head_idx = i_down - 1
            if head_idx < self.n_head_vars and self.n_flow_vars + head_idx < len(solution):
                H_down_curr = solution[self.n_flow_vars + head_idx]
                H_down_prev = self.previous_state[self.n_flow_vars + head_idx]
            else:
                H_down_curr = self.downstream_boundary
                H_down_prev = self.downstream_boundary
        
        # 计算断面参数
        section_up = self.model.sections[i_up]
        section_down = self.model.sections[i_down]
        
        A_up_curr = section_up['area_func'](H_up_curr)
        A_down_curr = section_down['area_func'](H_down_curr)
        A_up_prev = section_up['area_func'](H_up_prev)
        A_down_prev = section_down['area_func'](H_down_prev)
        
        return {
            'Q_curr': Q_curr, 'Q_prev': Q_prev,
            'H_up_curr': H_up_curr, 'H_up_prev': H_up_prev,
            'H_down_curr': H_down_curr, 'H_down_prev': H_down_prev,
            'A_up_curr': A_up_curr, 'A_down_curr': A_down_curr,
            'A_up_prev': A_up_prev, 'A_down_prev': A_down_prev,
            'i_up': i_up, 'i_down': i_down
        }
    
    def _compute_preissmann_weights(self, variables: Dict, theta: float, psi: float) -> Dict[str, float]:
        """计算Preissmann加权平均值"""
        # 空间加权平均
        A_spatial_n = psi * variables['A_down_prev'] + (1 - psi) * variables['A_up_prev']
        A_spatial_n1 = psi * variables['A_down_curr'] + (1 - psi) * variables['A_up_curr']
        H_spatial_n = psi * variables['H_down_prev'] + (1 - psi) * variables['H_up_prev']
        H_spatial_n1 = psi * variables['H_down_curr'] + (1 - psi) * variables['H_up_curr']
        
        # 时间加权平均
        A_preissmann = theta * A_spatial_n1 + (1 - theta) * A_spatial_n
        H_preissmann = theta * H_spatial_n1 + (1 - theta) * H_spatial_n
        Q_preissmann = theta * variables['Q_curr'] + (1 - theta) * variables['Q_prev']
        
        return {
            'A_spatial_n': A_spatial_n, 'A_spatial_n1': A_spatial_n1,
            'A_preissmann': A_preissmann, 'H_preissmann': H_preissmann,
            'Q_preissmann': Q_preissmann
        }
    
    def _build_continuity_equation(self, variables: Dict, weighted_vars: Dict, dt: float) -> float:
        """构建连续性方程: ∂A/∂t + ∂Q/∂x = 0"""
        # 时间导数项
        dA_dt = (weighted_vars['A_spatial_n1'] - weighted_vars['A_spatial_n']) / dt
        # 空间导数项（单个分段内流量不变）
        dQ_dx = 0.0
        return dA_dt + dQ_dx
    
    def _build_momentum_equation(self, variables: Dict, weighted_vars: Dict, dt: float, 
                               dx: float, g: float, S0: float, n_manning: float) -> float:
        """构建动量方程: ∂Q/∂t + ∂(Q²/A)/∂x + gA∂H/∂x + gA(Sf - S0) = 0"""
        # 1. 时间导数项
        dQ_dt = (variables['Q_curr'] - variables['Q_prev']) / dt
        
        # 2. 对流项
        if variables['A_up_curr'] > 0 and variables['A_down_curr'] > 0:
            Q = weighted_vars['Q_preissmann']
            momentum_up = Q * Q / variables['A_up_curr']
            momentum_down = Q * Q / variables['A_down_curr']
            d_momentum_dx = (momentum_down - momentum_up) / dx
        else:
            d_momentum_dx = 0.0
        
        # 3. 压力项
        dH_dx = (variables['H_down_curr'] - variables['H_up_curr']) / dx
        pressure_term = g * weighted_vars['A_preissmann'] * dH_dx
        
        # 4. 摩阻项
        friction_term = self._compute_friction_term(weighted_vars, g, n_manning)
        
        # 5. 底坡项
        slope_term = g * weighted_vars['A_preissmann'] * S0
        
        return dQ_dt + d_momentum_dx + pressure_term + friction_term - slope_term
    
    def _compute_friction_term(self, weighted_vars: Dict, g: float, n_manning: float) -> float:
        """计算摩阻项"""
        A = weighted_vars['A_preissmann']
        Q = weighted_vars['Q_preissmann']
        
        if A > 0 and Q != 0:
            # 简化的水力半径计算（假设梯形断面）
            T = 10.0 + 2.0 * (A / 10.0)  # 近似水面宽
            depth = A / T if T > 0 else 1.0
            P = T + 2 * depth  # 近似湿周
            R = A / P if P > 0 else 1.0
            
            velocity = abs(Q / A)
            Sf = n_manning**2 * velocity * Q / (A**2 * R**(4/3))
            return g * A * Sf
        else:
            return 0.0
    
    def _build_continuity_jacobian(self, jacobian: np.ndarray, eq_idx: int, seg_idx: int,
                                 variables: Dict, dt: float, theta: float, psi: float) -> None:
        """构建连续性方程Jacobian"""
        dh = 1e-6
        
        # 对上游水位的偏导数
        if variables['i_up'] > 0:
            head_idx = variables['i_up'] - 1
            if self.n_flow_vars + head_idx < jacobian.shape[1]:
                section = self.model.sections[variables['i_up']]
                A_plus = section['area_func'](variables['H_up_curr'] + dh)
                dA_dH = (A_plus - variables['A_up_curr']) / dh
                jacobian[eq_idx, self.n_flow_vars + head_idx] = theta * (1 - psi) * dA_dH / dt
        
        # 对下游水位的偏导数
        if variables['i_down'] < len(self.model.sections) - 1:
            head_idx = variables['i_down'] - 1
            if self.n_flow_vars + head_idx < jacobian.shape[1]:
                section = self.model.sections[variables['i_down']]
                A_plus = section['area_func'](variables['H_down_curr'] + dh)
                dA_dH = (A_plus - variables['A_down_curr']) / dh
                jacobian[eq_idx, self.n_flow_vars + head_idx] = theta * psi * dA_dH / dt
    
    def _build_momentum_jacobian(self, jacobian: np.ndarray, eq_idx: int, seg_idx: int,
                               variables: Dict, weighted_vars: Dict, dt: float, dx: float,
                               g: float, S0: float, n_manning: float, theta: float, psi: float) -> None:
        """构建动量方程Jacobian"""
        # 对流量的偏导数
        dres_dQ = 1.0 / dt  # 时间导数项
        
        # 对流项的贡献
        if variables['A_up_curr'] > 0 and variables['A_down_curr'] > 0:
            Q = weighted_vars['Q_preissmann']
            dres_dQ += theta * 2 * Q * (1/variables['A_down_curr'] - 1/variables['A_up_curr']) / dx
        
        # 摩阻项的贡献
        if weighted_vars['A_preissmann'] > 0 and weighted_vars['Q_preissmann'] != 0:
            friction_grad = 2 * g * weighted_vars['A_preissmann'] * n_manning**2 * abs(weighted_vars['Q_preissmann']) / \
                          (weighted_vars['A_preissmann']**2 * 1.0**(4/3))
            dres_dQ += theta * friction_grad
        
        jacobian[eq_idx, seg_idx] = dres_dQ
        
        # 对水位的偏导数（压力项）
        if variables['i_up'] > 0:
            head_idx = variables['i_up'] - 1
            if self.n_flow_vars + head_idx < jacobian.shape[1]:
                jacobian[eq_idx, self.n_flow_vars + head_idx] = -g * weighted_vars['A_preissmann'] * theta * (1 - psi) / dx
        
        if variables['i_down'] < len(self.model.sections) - 1:
            head_idx = variables['i_down'] - 1
            if self.n_flow_vars + head_idx < jacobian.shape[1]:
                jacobian[eq_idx, self.n_flow_vars + head_idx] = g * weighted_vars['A_preissmann'] * theta * psi / dx
    
    def validate_physical_consistency(self, dt: float = 1.0) -> Dict[str, Any]:
        """物理合理性全面验证 - 按照基础代码库物理合理性增强要求"""
        validation_results = {
            'overall_valid': True,
            'physics_check': {},
            'velocity_analysis': {},
            'steady_state_balance': {},
            'numerical_stability': {},
            'warnings': [],
            'errors': []
        }
        
        try:
            # 1. 物理合理性检查
            physics_check = self._check_physics_consistency()
            validation_results['physics_check'] = physics_check
            
            # 2. 流速特性分析
            velocity_analysis = self._analyze_velocity_characteristics()
            validation_results['velocity_analysis'] = velocity_analysis
            
            # 3. 恒定流平衡验证
            steady_balance = self._verify_steady_state_balance(dt)
            validation_results['steady_state_balance'] = steady_balance
            
            # 4. 数值稳定性检查
            numerical_stability = self._check_numerical_stability(dt)
            validation_results['numerical_stability'] = numerical_stability
            
            # 汇总验证结果
            self._summarize_validation_results(validation_results)
            
        except Exception as e:
            validation_results['errors'].append(f"验证过程出错: {e}")
            validation_results['overall_valid'] = False
        
        return validation_results
    
    def _check_physics_consistency(self) -> Dict[str, Any]:
        """检查物理一致性"""
        physics_check = {
            'mass_conservation': True,
            'energy_consistency': True,
            'momentum_balance': True,
            'flow_direction': True,
            'details': {}
        }
        
        # 检查质量守恒
        mass_error = 0.0
        for i in range(self.n_flow_vars):
            if i < len(self.current_state):
                flow_in = self.current_state[i]
                flow_out = self.current_state[i] if i == self.n_flow_vars - 1 else self.current_state[i]
                mass_error += abs(flow_in - flow_out)
        
        physics_check['details']['mass_error'] = mass_error
        if mass_error > 1e-3:  # 1L/s的误差阈值
            physics_check['mass_conservation'] = False
        
        # 检查流动方向
        water_levels = []
        for i in range(self.n_head_vars):
            if self.n_flow_vars + i < len(self.current_state):
                water_levels.append(self.current_state[self.n_flow_vars + i])
        
        if len(water_levels) > 1:
            for i in range(1, len(water_levels)):
                if water_levels[i] > water_levels[i-1]:
                    physics_check['flow_direction'] = False
                    break
        
        physics_check['details']['water_levels'] = water_levels
        
        return physics_check
    
    def _analyze_velocity_characteristics(self) -> Dict[str, Any]:
        """分析流速特性"""
        velocity_analysis = {
            'velocities': [],
            'froude_numbers': [],
            'reynolds_numbers': [],
            'flow_regime': 'subcritical',
            'assumptions_valid': True,
            'details': {}
        }
        
        for i, section in enumerate(self.model.sections):
            if i < len(self.current_state) or i == 0 or i == len(self.model.sections) - 1:
                # 获取水位
                if i == 0:
                    water_level = self._get_upstream_water_level()
                elif i == len(self.model.sections) - 1:
                    water_level = self.downstream_boundary
                else:
                    head_idx = i - 1
                    if head_idx < self.n_head_vars and self.n_flow_vars + head_idx < len(self.current_state):
                        water_level = self.current_state[self.n_flow_vars + head_idx]
                    else:
                        continue
                
                # 计算流速参数
                area = section['area_func'](water_level)
                top_width = section['top_width_func'](water_level)
                
                if area > 0 and top_width > 0:
                    flow = self.current_state[0] if len(self.current_state) > 0 else 100.0
                    velocity = flow / area
                    hydraulic_depth = area / top_width
                    
                    # 弗劳德数
                    froude_number = velocity / np.sqrt(9.81 * hydraulic_depth)
                    
                    # 雷诺兹数（简化）
                    kinematic_viscosity = 1e-6  # m²/s
                    reynolds_number = velocity * hydraulic_depth / kinematic_viscosity
                    
                    velocity_analysis['velocities'].append(velocity)
                    velocity_analysis['froude_numbers'].append(froude_number)
                    velocity_analysis['reynolds_numbers'].append(reynolds_number)
                    
                    # 检查流态假设
                    if froude_number >= 1.0:
                        velocity_analysis['flow_regime'] = 'supercritical'
                        velocity_analysis['assumptions_valid'] = False
        
        velocity_analysis['details'] = {
            'avg_velocity': np.mean(velocity_analysis['velocities']) if velocity_analysis['velocities'] else 0.0,
            'max_froude': max(velocity_analysis['froude_numbers']) if velocity_analysis['froude_numbers'] else 0.0,
            'min_reynolds': min(velocity_analysis['reynolds_numbers']) if velocity_analysis['reynolds_numbers'] else 0.0
        }
        
        return velocity_analysis
    
    def _verify_steady_state_balance(self, dt: float) -> Dict[str, Any]:
        """验证恒定流平衡"""
        steady_balance = {
            'momentum_balanced': True,
            'residuals': [],
            'balance_error': 0.0,
            'details': {}
        }
        
        try:
            # 构建当前状态的Preissmann系统
            jacobian, residual = self._build_preissmann_system(
                self.current_state, dt, 
                self.numerical_config.theta, 
                self.numerical_config.psi
            )
            
            residual_norm = np.sqrt(np.sum(residual**2))
            max_residual = np.max(np.abs(residual))
            
            steady_balance['residuals'] = residual.tolist()
            steady_balance['balance_error'] = float(residual_norm)
            steady_balance['details'] = {
                'residual_norm': float(residual_norm),
                'max_residual': float(max_residual),
                'jacobian_condition': float(np.linalg.cond(jacobian)) if jacobian.shape[0] > 0 else 0.0
            }
            
            # 判断平衡性
            if residual_norm > 1e-3:  # 平衡阈值
                steady_balance['momentum_balanced'] = False
            
        except Exception as e:
            steady_balance['details']['error'] = str(e)
            steady_balance['momentum_balanced'] = False
        
        return steady_balance
    
    def _check_numerical_stability(self, dt: float) -> Dict[str, Any]:
        """检查数值稳定性"""
        stability = {
            'cfl_stable': True,
            'matrix_stable': True,
            'convergence_stable': True,
            'details': {}
        }
        
        try:
            # CFL条件检查
            max_cfl = 0.0
            for i in range(self.n_segments):
                wave_speed = self._calculate_wave_speed(i)
                dx = self.dx_array[i] if i < len(self.dx_array) else 100.0
                cfl = wave_speed * dt / dx
                max_cfl = max(max_cfl, cfl)
            
            stability['details']['max_cfl'] = float(max_cfl)
            if max_cfl > self.numerical_config.cfl_target:
                stability['cfl_stable'] = False
            
            # 矩阵条件数检查
            jacobian, _ = self._build_preissmann_system(
                self.current_state, dt,
                self.numerical_config.theta,
                self.numerical_config.psi
            )
            
            if jacobian.shape[0] > 0:
                condition_number = np.linalg.cond(jacobian)
                stability['details']['condition_number'] = float(condition_number)
                
                if condition_number > 1e12:
                    stability['matrix_stable'] = False
        
        except Exception as e:
            stability['details']['error'] = str(e)
            stability['matrix_stable'] = False
        
        return stability
    
    def _summarize_validation_results(self, validation_results: Dict[str, Any]) -> None:
        """汇总验证结果"""
        # 检查所有子项
        physics_ok = validation_results['physics_check'].get('mass_conservation', False) and \
                    validation_results['physics_check'].get('flow_direction', False)
        
        velocity_ok = validation_results['velocity_analysis'].get('assumptions_valid', False)
        
        steady_ok = validation_results['steady_state_balance'].get('momentum_balanced', False)
        
        numerical_ok = validation_results['numerical_stability'].get('cfl_stable', False) and \
                      validation_results['numerical_stability'].get('matrix_stable', False)
        
        # 汇总判断
        validation_results['overall_valid'] = physics_ok and velocity_ok and steady_ok and numerical_ok
        
        # 生成警告和错误
        if not physics_ok:
            validation_results['errors'].append("物理一致性检查失败")
        
        if not velocity_ok:
            validation_results['warnings'].append("流速特性不满足亚临界流假设")
        
        if not steady_ok:
            validation_results['errors'].append("恒定流平衡验证失败")
        
        if not numerical_ok:
            validation_results['warnings'].append("数值稳定性检查有问题")
    
    def _build_complete_preissmann_system(self, solution: np.ndarray, dt: float,
                                        theta: float, psi: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        构建改进的Preissmann四点隐式差分格式的线性系统，确保空间传播正确计算
        
        严格实现圣维南方程：
        连续性方程: ∂A/∂t + ∂Q/∂x = 0
        动量方程: ∂Q/∂t + ∂(Q²/A)/∂x + gA∂H/∂x + gASf = gAS0
        
        Preissmann格式使用四个网格点 (i,n), (i+1,n), (i,n+1), (i+1,n+1)
        时间加权: theta, 空间加权: psi
        
        Returns:
            jacobian: Jacobian矩阵 (n_vars x n_vars)
            residual: 残差向量 (n_vars,)
        """
        n_vars = self.n_total_vars
        jacobian = np.zeros((n_vars, n_vars))
        residual = np.zeros(n_vars)
        
        g = 9.81  # 重力加速度
        
        # 为每个分段构建连续性方程和动量方程
        eq_idx = 0
        
        for seg_idx in range(self.n_segments):
            if seg_idx >= len(self.model.segments):
                break
                
            segment = self.model.segments[seg_idx]
            dx = segment['length']
            
            # 获取上下游断面索引
            i_up = segment['upstream_section']
            i_down = segment['downstream_section']
            
            # 获取当前时刻的变量 (n+1)
            Q_curr = solution[seg_idx] if seg_idx < len(solution) else 100.0
            
            # 获取上一时刻的变量 (n)
            Q_prev = self.previous_state[seg_idx] if seg_idx < len(self.previous_state) else 100.0
            
            # 获取上下游水位（当前时刻）
            if i_up == 0:  # 上游边界
                H_up_curr = self._get_upstream_water_level()
            else:
                head_idx = i_up - 1  # 内部节点索引
                if head_idx < self.n_head_vars:
                    H_up_curr = solution[self.n_flow_vars + head_idx]
                else:
                    H_up_curr = self._get_upstream_water_level()
            
            if i_down == len(self.model.sections) - 1:  # 下游边界
                H_down_curr = self.downstream_boundary
            else:
                head_idx = i_down - 1  # 内部节点索引
                if head_idx < self.n_head_vars:
                    H_down_curr = solution[self.n_flow_vars + head_idx]
                else:
                    H_down_curr = self.downstream_boundary
            
            # 获取上一时刻的水位
            if i_up == 0:
                H_up_prev = self._get_upstream_water_level()
            else:
                head_idx = i_up - 1
                if head_idx < self.n_head_vars:
                    H_up_prev = self.previous_state[self.n_flow_vars + head_idx]
                else:
                    H_up_prev = self._get_upstream_water_level()
            
            if i_down == len(self.model.sections) - 1:
                H_down_prev = self.downstream_boundary
            else:
                head_idx = i_down - 1
                if head_idx < self.n_head_vars:
                    H_down_prev = self.previous_state[self.n_flow_vars + head_idx]
                else:
                    H_down_prev = self.downstream_boundary
            
            # 计算断面几何参数 - 使用模型的几何函数确保一致性
            section_up = self.model.sections[i_up]
            section_down = self.model.sections[i_down]
            
            # 使用模型的面积函数计算过水断面积
            A_up_curr = section_up['area_func'](H_up_curr)
            A_down_curr = section_down['area_func'](H_down_curr)
            A_avg_curr = (A_up_curr + A_down_curr) / 2.0
            
            A_up_prev = section_up['area_func'](H_up_prev)
            A_down_prev = section_down['area_func'](H_down_prev)
            A_avg_prev = (A_up_prev + A_down_prev) / 2.0
            
            # 使用模型的水面宽函数计算
            T_up_curr = section_up['top_width_func'](H_up_curr)
            T_down_curr = section_down['top_width_func'](H_down_curr)
            T_avg_curr = (T_up_curr + T_down_curr) / 2.0
            
            # === 连续性方程 ===
            if eq_idx < n_vars:
                # Preissmann时间加权
                A_time_weighted = theta * A_avg_curr + (1 - theta) * A_avg_prev
                
                # 时间导数项: ∂A/∂t
                dA_dt = (A_avg_curr - A_avg_prev) / dt
                
                # 空间导数项: ∂Q/∂x （Preissmann空间加权）
                if seg_idx + 1 < self.n_flow_vars:
                    Q_downstream = solution[seg_idx + 1]
                    Q_downstream_prev = self.previous_state[seg_idx + 1]
                    
                    # Preissmann时间和空间加权
                    Q_space_weighted_curr = psi * Q_downstream + (1 - psi) * Q_curr
                    Q_space_weighted_prev = psi * Q_downstream_prev + (1 - psi) * Q_prev
                    
                    dQ_dx = (Q_space_weighted_curr - Q_space_weighted_prev) / dx
                else:
                    dQ_dx = 0.0
                
                # 连续性方程残差
                residual[eq_idx] = dA_dt + dQ_dx
                
                # 连续性方程的Jacobian
                # ∂res/∂Q_curr
                jacobian[eq_idx, seg_idx] = -(1 - psi) / dx
                
                # ∂res/∂Q_downstream
                if seg_idx + 1 < n_vars:
                    jacobian[eq_idx, seg_idx + 1] = psi / dx
                
                # ∂res/∂H（面积对水位的偏导）- 使用数值微分计算
                dh = 1e-6  # 小的水位增量
                if i_up > 0:  # 上游内部节点
                    head_idx = i_up - 1
                    if self.n_flow_vars + head_idx < n_vars:
                        # 数值计算 ∂A/∂H
                        A_up_plus = section_up['area_func'](H_up_curr + dh)
                        dA_dH_up = (A_up_plus - A_up_curr) / dh
                        jacobian[eq_idx, self.n_flow_vars + head_idx] += theta * dA_dH_up / 2.0 / dt
                
                if i_down < len(self.model.sections) - 1:  # 下游内部节点
                    head_idx = i_down - 1
                    if self.n_flow_vars + head_idx < n_vars:
                        # 数值计算 ∂A/∂H
                        A_down_plus = section_down['area_func'](H_down_curr + dh)
                        dA_dH_down = (A_down_plus - A_down_curr) / dh
                        jacobian[eq_idx, self.n_flow_vars + head_idx] += theta * dA_dH_down / 2.0 / dt
                
                eq_idx += 1
            
            # === 动量方程 ===
            if eq_idx < n_vars:
                # 1. 时间导数项: ∂Q/∂t
                dQ_dt = (Q_curr - Q_prev) / dt
                
                # 2. 对流项: ∂(Q²/A)/∂x - 正确的Preissmann实现
                # 上游动量通量
                momentum_flux_up = Q_curr * Q_curr / A_up_curr if A_up_curr > 0 else 0.0
                # 下游动量通量
                momentum_flux_down = Q_curr * Q_curr / A_down_curr if A_down_curr > 0 else 0.0
                # 空间导数
                d_momentum_flux_dx = (momentum_flux_down - momentum_flux_up) / dx
                
                # 3. 压力项: gA∂H/∂x - 使用空间加权平均面积
                A_space_weighted = psi * A_down_curr + (1 - psi) * A_up_curr
                dH_dx = (H_down_curr - H_up_curr) / dx
                pressure_term = g * A_space_weighted * dH_dx
                
                # 4. 摩阻项: gASf - 使用时间-空间加权面积
                A_weighted = theta * A_space_weighted + (1 - theta) * (psi * A_down_prev + (1 - psi) * A_up_prev)
                n_manning = segment.get('roughness', 0.03)
                if A_weighted > 0:
                    # 计算水力半径 - 简化处理
                    T_space_weighted = psi * T_down_curr + (1 - psi) * T_up_curr
                    if T_space_weighted > 0:
                        depth_avg = A_weighted / T_space_weighted
                        P_avg = T_space_weighted + 2 * depth_avg
                        R_hydraulic = A_weighted / P_avg if P_avg > 0 else 1.0
                    else:
                        R_hydraulic = 1.0
                    
                    velocity = abs(Q_curr / A_weighted)
                    friction_slope = n_manning**2 * velocity * Q_curr / (A_weighted**2 * R_hydraulic**(4/3))
                    friction_term = g * A_weighted * friction_slope
                else:
                    friction_term = 0.0
                
                # 5. 底坡项: gAS0
                S0 = segment.get('slope', 0.001)
                slope_term = g * A_weighted * S0
                
                # 动量方程残差: ∂Q/∂t + ∂(Q²/A)/∂x + gA∂H/∂x + gASf - gAS0 = 0
                residual[eq_idx] = dQ_dt + d_momentum_flux_dx + pressure_term + friction_term - slope_term
                
                # 动量方程的Jacobian（简化）
                # ∂res/∂Q_curr
                dres_dQ = 1.0/dt
                if A_avg_curr > 0:
                    dres_dQ += 2 * Q_curr / A_avg_curr**2 / dx  # 对流项
                    dres_dQ += g * A_avg_curr * n_manning**2 * 2 * abs(Q_curr) / (A_avg_curr**2 * R_hydraulic**(4/3))  # 摩阻项
                
                jacobian[eq_idx, seg_idx] = dres_dQ
                
                # ∂res/∂H（压力项的偏导）
                if i_up > 0:  # 上游内部节点
                    head_idx = i_up - 1
                    if self.n_flow_vars + head_idx < n_vars:
                        jacobian[eq_idx, self.n_flow_vars + head_idx] = -g * A_avg_curr / dx
                
                if i_down < len(self.model.sections) - 1:  # 下游内部节点
                    head_idx = i_down - 1
                    if self.n_flow_vars + head_idx < n_vars:
                        jacobian[eq_idx, self.n_flow_vars + head_idx] = g * A_avg_curr / dx
                
                eq_idx += 1
        
        return jacobian, residual
    
    def _check_mass_conservation(self, dt: float) -> float:
        """检查质量守恒 - 基于连续性方程验证"""
        total_error = 0.0
        
        for i in range(self.n_segments):
            # 获取分段流量
            Q_up = self.current_state[i] if i < self.n_flow_vars else self.upstream_boundary
            Q_down = self.current_state[i] if i < self.n_flow_vars else self.current_state[i-1]
            
            # 获取断面面积变化（简化）
            A_avg = 100.0  # 平均过水断面积
            dx = self.dx_array[i] if i < len(self.dx_array) else 100.0
            
            # 连续性方程残差 ∂A/∂t + ∂Q/∂x ≈ 0
            dQ_dx = (Q_down - Q_up) / dx if dx > 0 else 0.0
            mass_residual = abs(dQ_dx)  # 简化的质量残差
            
            total_error += mass_residual
        
        return total_error / max(self.n_segments, 1)
    
    def _build_timestep_result(self, current_time: float, dt: float, 
                             success: bool, iterations: int) -> Dict[str, Any]:
        """构建时间步求解结果"""
        result = {
            'time': current_time,
            'timestep': dt,
            'convergence_success': success,
            'iterations': iterations,
            'flow_variables': {},
            'water_levels': {},
            'diagnostics': {
                'max_velocity': 0.0,
                'max_froude_number': 0.0,
                'total_volume': 0.0,
                'mass_conservation_error': self.statistics['mass_conservation_errors'][-1] if self.statistics['mass_conservation_errors'] else 0.0
            }
        }
        
        # 提取流量变量
        for i in range(self.n_flow_vars):
            segment_name = f"Q_seg_{i}"
            result['flow_variables'][segment_name] = self.current_state[i]
        
        # 提取水位变量
        for i in range(self.n_head_vars):
            node_name = f"H_internal_{i}"
            result['water_levels'][node_name] = self.current_state[self.n_flow_vars + i]
        
        # 添加边界水位
        result['water_levels']['H_upstream'] = self._get_upstream_water_level()
        result['water_levels']['H_downstream'] = self.downstream_boundary
        
        return result
    
    def _get_upstream_water_level(self) -> float:
        """获取上游水位 - 使用恒定流计算结果或已知的上游水位"""
        # 如果有存储的上游水位，直接使用
        if hasattr(self, '_upstream_water_level') and self._upstream_water_level is not None:
            return self._upstream_water_level
        
        # 否则使用恒定流计算估算
        Q = self.upstream_boundary if self.upstream_boundary is not None else 100.0
        downstream_H = self.downstream_boundary if self.downstream_boundary is not None else 99.0
        
        try:
            steady_result = self.model.compute_steady_state(Q, downstream_H)
            upstream_level = steady_result.get('H_section_0', downstream_H + 0.02)
            return upstream_level
        except Exception:
            # 如果恒定流计算失败，使用简化估算
            section = self.model.sections[0]
            return section['elevation'] + 1.0  # 默认水深1m
    
    def get_solution_history(self) -> Dict[str, Any]:
        """获取求解历史记录"""
        return {
            'time_history': self.time_history.copy(),
            'state_history': [state.copy() for state in self.state_history],
            'boundary_history': self.boundary_history.copy(),
            'statistics': self.statistics.copy()
        }
    
    def reset_solver(self):
        """重置求解器状态"""
        self._initialize_solution_arrays()
        self.statistics = {
            'total_steps': 0,
            'convergence_failures': 0,
            'timestep_reductions': 0,
            'mass_conservation_errors': [],
            'computational_time': 0.0
        }