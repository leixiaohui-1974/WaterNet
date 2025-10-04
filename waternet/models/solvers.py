"""
统一求解器模块

为WaterNet提供统一的数值求解器接口，整合标准求解器和增强求解器功能。
支持不同复杂度级别的求解需求。

Author: WaterNet Development Team
Date: 2024-10-03
"""

import numpy as np
import warnings
from typing import Dict, List, Tuple, Optional, Any, Union
from abc import ABC, abstractmethod
from dataclasses import dataclass
import logging


@dataclass
class SolverConfig:
    """求解器配置基类"""
    max_iterations: int = 10
    tolerance: float = 1e-6
    relaxation_factor: float = 0.8
    enable_diagnostics: bool = False


@dataclass  
class StandardSolverConfig(SolverConfig):
    """标准求解器配置"""
    use_newton_method: bool = True
    adaptive_relaxation: bool = False


@dataclass
class EnhancedSolverConfig(SolverConfig):
    """增强求解器配置"""
    scheme_type: str = "preissmann"
    theta: float = 0.6
    psi: float = 0.5
    cfl_target: float = 0.5
    enable_adaptive_timestep: bool = True
    enable_mass_conservation_check: bool = True


class BaseSolver(ABC):
    """求解器基类"""
    
    def __init__(self, config: SolverConfig, name: str = "BaseSolver"):
        self.config = config
        self.name = name
        self.logger = logging.getLogger(f"Solver_{name}")
        
        # 统计信息
        self.stats = {
            'total_steps': 0,
            'convergence_failures': 0,
            'average_iterations': 0.0,
            'max_iterations': 0
        }
    
    @abstractmethod
    def solve_step(self, *args, **kwargs) -> Dict[str, Any]:
        """求解单步"""
        pass
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取求解统计信息"""
        return self.stats.copy()
    
    def reset_statistics(self):
        """重置统计信息"""
        self.stats = {
            'total_steps': 0,
            'convergence_failures': 0,
            'average_iterations': 0.0,
            'max_iterations': 0
        }


class StandardSolver(BaseSolver):
    """标准求解器"""
    
    def __init__(self, config: Optional[StandardSolverConfig] = None):
        config = config or StandardSolverConfig()
        super().__init__(config, "StandardSolver")
    
    def solve_step(self, residual_func, jacobian_func=None, 
                   initial_guess=None, **kwargs) -> Dict[str, Any]:
        """
        标准求解器步骤
        
        Args:
            residual_func: 残差函数
            jacobian_func: 雅可比函数（可选）
            initial_guess: 初始猜测值
            
        Returns:
            Dict[str, Any]: 求解结果
        """
        self.stats['total_steps'] += 1
        
        if initial_guess is None:
            initial_guess = 0.0
        
        x = initial_guess
        converged = False
        iterations = 0
        
        for iterations in range(self.config.max_iterations):
            residual = residual_func(x)
            
            if abs(residual) < self.config.tolerance:
                converged = True
                break
            
            if self.config.use_newton_method and jacobian_func is not None:
                # 牛顿法
                jacobian = jacobian_func(x)
                if abs(jacobian) > 1e-12:
                    dx = -residual / jacobian
                    x += self.config.relaxation_factor * dx
                else:
                    # 雅可比接近零，使用割线法
                    x += self.config.relaxation_factor * (-residual * 0.01)
            else:
                # 简单不动点迭代
                x += self.config.relaxation_factor * (-residual * 0.01)
        
        if not converged:
            self.stats['convergence_failures'] += 1
        
        # 更新统计信息
        self.stats['max_iterations'] = max(self.stats['max_iterations'], iterations + 1)
        total_iter = self.stats['average_iterations'] * (self.stats['total_steps'] - 1) + (iterations + 1)
        self.stats['average_iterations'] = total_iter / self.stats['total_steps']
        
        return {
            'solution': x,
            'converged': converged,
            'iterations': iterations + 1,
            'final_residual': abs(residual) if 'residual' in locals() else float('inf')
        }
    
    def solve_steady_state(self, model, Q: float, downstream_H: float) -> Dict[str, float]:
        """
        求解恒定流问题
        
        Args:
            model: 水力模型
            Q: 流量
            downstream_H: 下游水位
            
        Returns:
            Dict[str, float]: 求解结果
        """
        try:
            result = model.compute_steady_state(Q, downstream_H)
            return result
        except Exception as e:
            self.logger.error(f"恒定流求解失败: {e}")
            return {}
    
    def solve_unsteady_flow(self, model, boundary_conditions: Dict,
                           time_series: List[float], dt: float) -> List[Dict[str, Any]]:
        """
        求解非恒定流问题（简化版）
        
        Args:
            model: 水力模型
            boundary_conditions: 边界条件
            time_series: 时间序列
            dt: 时间步长
            
        Returns:
            List[Dict[str, Any]]: 时间序列结果
        """
        results = []
        current_state = boundary_conditions.copy()
        
        for t in time_series:
            # 简化的非恒定流求解
            # 这里使用准恒定流近似
            Q_in = boundary_conditions.get('Q_upstream', 10.0)
            H_down = boundary_conditions.get('H_downstream', 99.0)
            
            try:
                step_result = self.solve_steady_state(model, Q_in, H_down)
                step_result['time'] = t
                results.append(step_result)
            except Exception as e:
                self.logger.warning(f"时间步 {t} 求解失败: {e}")
                results.append({'time': t, 'error': str(e)})
        
        return results


class EnhancedSolver(BaseSolver):
    """增强求解器（简化版本）"""
    
    def __init__(self, config: Optional[EnhancedSolverConfig] = None):
        config = config or EnhancedSolverConfig()
        super().__init__(config, "EnhancedSolver")
    
    def solve_step(self, equations_func, variables: Dict[str, float], 
                   dt: float, prev_states: Dict[str, float]) -> Dict[str, Any]:
        """
        增强求解器步骤
        
        Args:
            equations_func: 方程组函数
            variables: 当前变量值
            dt: 时间步长
            prev_states: 前一时步状态
            
        Returns:
            Dict[str, Any]: 求解结果
        """
        self.stats['total_steps'] += 1
        
        # 牛顿-拉夫逊迭代
        converged = False
        iterations = 0
        current_vars = variables.copy()
        
        for iterations in range(self.config.max_iterations):
            # 计算残差
            residuals = equations_func(current_vars, dt, prev_states)
            
            # 检查收敛性
            max_residual = max(abs(r) for r in residuals.values())
            if max_residual < self.config.tolerance:
                converged = True
                break
            
            # 简化的更新（实际实现会计算雅可比矩阵）
            for var_name in current_vars:
                if var_name in residuals:
                    current_vars[var_name] -= self.config.relaxation_factor * residuals[var_name] * 0.01
        
        if not converged:
            self.stats['convergence_failures'] += 1
        
        # 更新统计信息
        self.stats['max_iterations'] = max(self.stats['max_iterations'], iterations + 1)
        total_iter = self.stats['average_iterations'] * (self.stats['total_steps'] - 1) + (iterations + 1)
        self.stats['average_iterations'] = total_iter / self.stats['total_steps']
        
        return {
            'variables': current_vars,
            'converged': converged,
            'iterations': iterations + 1,
            'max_residual': max_residual if 'max_residual' in locals() else float('inf')
        }
    
    def solve_unsteady_flow_advanced(self, model, Q_in_series: List[float],
                                   H_down_series: List[float], dt: float,
                                   initial_conditions: Dict[str, float]) -> List[Dict[str, Any]]:
        """
        高级非恒定流求解
        
        Args:
            model: 圣维南模型
            Q_in_series: 入流序列
            H_down_series: 下游水位序列
            dt: 时间步长
            initial_conditions: 初始条件
            
        Returns:
            List[Dict[str, Any]]: 求解结果序列
        """
        if not hasattr(model, 'get_equations'):
            raise ValueError("模型必须支持get_equations方法")
        
        results = []
        current_time = 0.0
        
        # 初始化变量
        variables = {}
        prev_states = initial_conditions.copy()
        
        # 初始化模型变量
        for var_name in model.get_variable_names():
            variables[var_name] = initial_conditions.get(var_name, 0.0)
        
        for i, (Q_in, H_down) in enumerate(zip(Q_in_series, H_down_series)):
            # 设置边界条件
            variables[f'H_{model.upstream_node}'] = initial_conditions.get('H_upstream', 100.0)
            variables[f'H_{model.downstream_node}'] = H_down
            
            # 求解时间步
            step_result = self.solve_step(
                model.get_equations, variables, dt, prev_states)
            
            # 更新结果
            result = {
                'time': current_time,
                'timestep': dt,
                'Q_in': Q_in,
                'H_down': H_down,
                'converged': step_result['converged'],
                'iterations': step_result['iterations']
            }
            
            # 添加求解变量
            result.update(step_result['variables'])
            results.append(result)
            
            # 准备下一时步
            prev_states = step_result['variables'].copy()
            variables = step_result['variables'].copy()
            current_time += dt
        
        return results


class SolverFactory:
    """求解器工厂"""
    
    @staticmethod
    def create_solver(solver_type: str = "standard", 
                     config: Optional[SolverConfig] = None) -> BaseSolver:
        """
        创建求解器
        
        Args:
            solver_type: 求解器类型 ('standard' 或 'enhanced')
            config: 求解器配置
            
        Returns:
            BaseSolver: 求解器实例
        """
        if solver_type.lower() == "standard":
            config = config or StandardSolverConfig()
            return StandardSolver(config)
        elif solver_type.lower() == "enhanced":
            config = config or EnhancedSolverConfig()
            return EnhancedSolver(config)
        else:
            raise ValueError(f"不支持的求解器类型: {solver_type}")
    
    @staticmethod
    def create_enhanced_solver_from_deep_testing():
        """
        从深度测试模块创建增强求解器（如果可用）
        
        Returns:
            Enhanced solver instance or None
        """
        try:
            from ..tests.deep_channel_testing.enhanced_solver import (
                EnhancedSaintVenantSolver, NumericalSchemeConfig, StabilityConfig)
            
            # 返回工厂函数而不是实例
            def create_enhanced(model):
                return EnhancedSaintVenantSolver(
                    model, NumericalSchemeConfig(), StabilityConfig())
            
            return create_enhanced
        except ImportError:
            warnings.warn("增强求解器模块不可用")
            return None


def solve_with_auto_solver(model, solver_type: str = "auto", **kwargs) -> Dict[str, Any]:
    """
    自动选择求解器进行求解
    
    Args:
        model: 水力模型
        solver_type: 求解器类型 ("auto", "standard", "enhanced")
        **kwargs: 求解参数
        
    Returns:
        Dict[str, Any]: 求解结果
    """
    # 自动选择求解器
    if solver_type == "auto":
        # 根据模型类型和问题复杂度选择求解器
        if hasattr(model, 'solver_type') and model.solver_type == "enhanced":
            solver_type = "enhanced"
        else:
            solver_type = "standard"
    
    # 创建求解器
    solver = SolverFactory.create_solver(solver_type)
    
    # 根据问题类型选择求解方法
    if 'Q_in_series' in kwargs:
        # 非恒定流问题
        if solver_type == "enhanced":
            return solver.solve_unsteady_flow_advanced(model, **kwargs)
        else:
            return solver.solve_unsteady_flow(model, **kwargs)
    else:
        # 恒定流问题
        Q = kwargs.get('Q', kwargs.get('flow', 10.0))
        H_down = kwargs.get('downstream_H', kwargs.get('H_downstream', 99.0))
        return solver.solve_steady_state(model, Q, H_down)