"""
联合求解器集成

实现复杂水力网络的联合求解器，支持多个HydroModel的耦合求解。
通过Newton-Raphson方法求解非线性方程组，实现系统级的水力计算。

设计原理:
1. 变量收集：从各个模型收集所有未知变量
2. 方程组装：组装所有模型的方程残差
3. 雅可比矩阵：数值计算雅可比矩阵
4. Newton-Raphson迭代：求解非线性方程组

Author: WaterNet Development Team
Date: 2024-10-04
"""

import numpy as np
import math
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass
import logging
import time
from ..interfaces.hydro_model import HydroModel


@dataclass
class SolverConfig:
    """联合求解器配置"""
    max_iterations: int = 50
    tolerance: float = 1e-6
    relaxation_factor: float = 1.0
    numerical_jacobian_step: float = 1e-8
    enable_line_search: bool = False
    line_search_factor: float = 0.5
    min_step_size: float = 1e-10
    enable_diagnostics: bool = False
    max_condition_number: float = 1e12


@dataclass
class SolverStatistics:
    """求解器统计信息"""
    total_iterations: int = 0
    total_time: float = 0.0
    convergence_history: List[float] = None
    final_residual_norm: float = float('inf')
    jacobian_condition_number: float = 0.0
    success: bool = False
    failure_reason: str = ""
    
    def __post_init__(self):
        if self.convergence_history is None:
            self.convergence_history = []


class ImplicitSolverAgent:
    """
    隐式联合求解器
    
    用于求解由多个HydroModel组成的复杂水力网络。
    通过Newton-Raphson方法求解耦合的非线性方程组。
    
    Attributes:
        models (List[HydroModel]): 参与求解的模型列表
        config (SolverConfig): 求解器配置
        logger (logging.Logger): 日志记录器
    """
    
    def __init__(self, models: List[HydroModel], config: Optional[SolverConfig] = None):
        """
        初始化联合求解器
        
        Args:
            models (List[HydroModel]): 参与求解的模型列表
            config (SolverConfig, optional): 求解器配置
        
        Raises:
            ValueError: 当模型列表为空或存在冲突时
        """
        if not models:
            raise ValueError("模型列表不能为空")
        
        self.models = models
        self.config = config or SolverConfig()
        self.logger = logging.getLogger(__name__)
        
        # 初始化变量映射
        self._build_variable_mapping()
        
        # 验证系统完整性
        self._validate_system()
    
    def _build_variable_mapping(self):
        """构建变量映射"""
        self.variable_names = []
        self.variable_to_index = {}
        self.model_variable_ranges = {}
        
        current_index = 0
        
        for model in self.models:
            model_vars = model.get_variable_names()
            start_index = current_index
            
            for var_name in model_vars:
                if var_name in self.variable_to_index:
                    raise ValueError(f"变量名冲突: {var_name}")
                
                self.variable_names.append(var_name)
                self.variable_to_index[var_name] = current_index
                current_index += 1
            
            self.model_variable_ranges[model.name] = (start_index, current_index)
        
        self.total_variables = len(self.variable_names)
        self.logger.info(f"系统变量总数: {self.total_variables}")
    
    def _validate_system(self):
        """验证系统完整性"""
        # 检查方程和变量数量匹配
        total_equations = 0
        
        for model in self.models:
            try:
                # 使用零值测试获取方程数量
                test_vars = {name: 0.0 for name in self.variable_names}
                test_states = {}
                equations = model.get_equations(test_vars, 1.0, test_states)
                total_equations += len(equations)
            except Exception as e:
                self.logger.warning(f"模型 {model.name} 方程测试失败: {e}")
        
        if total_equations != self.total_variables:
            self.logger.warning(
                f"方程数量({total_equations})与变量数量({self.total_variables})不匹配")
        
        self.logger.info(f"系统验证完成，方程数: {total_equations}")
    
    def solve_steady_state(self, initial_guess: Optional[Dict[str, float]] = None,
                          boundary_conditions: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """
        求解稳态问题
        
        Args:
            initial_guess (Dict[str, float], optional): 初始猜测值
            boundary_conditions (Dict[str, float], optional): 边界条件
        
        Returns:
            Dict[str, Any]: 求解结果
        """
        self.logger.info("开始稳态求解")
        start_time = time.time()
        
        # 初始化变量
        variables = self._initialize_variables(initial_guess, boundary_conditions)
        prev_states = {}  # 稳态问题不需要历史状态
        
        # Newton-Raphson迭代
        stats = SolverStatistics()
        
        for iteration in range(self.config.max_iterations):
            # 计算残差
            residuals = self._calculate_residuals(variables, 0.0, prev_states)
            residual_norm = np.linalg.norm(residuals)
            
            stats.convergence_history.append(residual_norm)
            
            self.logger.debug(f"迭代 {iteration}: 残差范数 = {residual_norm:.2e}")
            
            # 检查收敛性
            if residual_norm < self.config.tolerance:
                stats.success = True
                break
            
            # 计算雅可比矩阵
            jacobian = self._calculate_jacobian(variables, 0.0, prev_states)
            
            # 求解线性系统
            try:
                delta_vars = self._solve_linear_system(jacobian, residuals)
            except Exception as e:
                stats.failure_reason = f"线性系统求解失败: {e}"
                break
            
            # 更新变量
            variables = self._update_variables(variables, delta_vars)
        
        else:
            stats.failure_reason = "达到最大迭代次数"
        
        # 完成统计
        stats.total_iterations = iteration + 1
        stats.total_time = time.time() - start_time
        stats.final_residual_norm = residual_norm
        
        self.logger.info(f"稳态求解完成: 迭代 {stats.total_iterations} 次, "
                        f"耗时 {stats.total_time:.2f}s, 收敛: {stats.success}")
        
        return {
            'variables': variables,
            'statistics': stats,
            'converged': stats.success
        }
    
    def solve_time_series(self, time_steps: List[float], dt: float,
                         initial_conditions: Dict[str, float],
                         boundary_conditions: Dict[str, Callable[[float], float]] = None) -> List[Dict[str, Any]]:
        """
        求解时间序列问题
        
        Args:
            time_steps (List[float]): 时间点列表
            dt (float): 时间步长
            initial_conditions (Dict[str, float]): 初始条件
            boundary_conditions (Dict[str, Callable]): 边界条件函数
        
        Returns:
            List[Dict[str, Any]]: 时间序列结果
        """
        self.logger.info(f"开始时间序列求解: {len(time_steps)} 个时间步")
        
        results = []
        current_variables = initial_conditions.copy()
        current_states = initial_conditions.copy()
        
        for i, t in enumerate(time_steps):
            self.logger.debug(f"求解时间步 {i+1}/{len(time_steps)}: t = {t:.3f}s")
            
            # 更新边界条件
            if boundary_conditions:
                for var_name, bc_func in boundary_conditions.items():
                    if var_name in current_variables:
                        current_variables[var_name] = bc_func(t)
            
            # 求解当前时间步
            step_result = self._solve_time_step(current_variables, dt, current_states)
            
            if not step_result['converged']:
                self.logger.error(f"时间步 {i+1} 求解失败")
                break
            
            # 更新状态
            current_variables = step_result['variables']
            current_states = self._update_states(current_variables, dt, current_states)
            
            # 记录结果
            step_result['time'] = t
            step_result['timestep'] = i + 1
            results.append(step_result)
        
        self.logger.info(f"时间序列求解完成: {len(results)} 个成功时间步")
        return results
    
    def _solve_time_step(self, variables: Dict[str, float], dt: float,
                        prev_states: Dict[str, float]) -> Dict[str, Any]:
        """求解单个时间步"""
        stats = SolverStatistics()
        
        for iteration in range(self.config.max_iterations):
            # 计算残差
            residuals = self._calculate_residuals(variables, dt, prev_states)
            residual_norm = np.linalg.norm(residuals)
            
            stats.convergence_history.append(residual_norm)
            
            # 检查收敛性
            if residual_norm < self.config.tolerance:
                stats.success = True
                break
            
            # 计算雅可比矩阵
            jacobian = self._calculate_jacobian(variables, dt, prev_states)
            
            # 求解线性系统
            try:
                delta_vars = self._solve_linear_system(jacobian, residuals)
            except Exception as e:
                stats.failure_reason = f"线性系统求解失败: {e}"
                break
            
            # 更新变量
            variables = self._update_variables(variables, delta_vars)
        
        else:
            stats.failure_reason = "达到最大迭代次数"
        
        stats.total_iterations = iteration + 1
        stats.final_residual_norm = residual_norm
        
        return {
            'variables': variables,
            'statistics': stats,
            'converged': stats.success
        }
    
    def _initialize_variables(self, initial_guess: Optional[Dict[str, float]],
                             boundary_conditions: Optional[Dict[str, float]]) -> Dict[str, float]:
        """初始化变量"""
        variables = {}
        
        # 设置默认值
        for var_name in self.variable_names:
            if var_name.startswith('H_'):
                variables[var_name] = 100.0  # 默认水位
            elif var_name.startswith('Q_'):
                variables[var_name] = 1.0    # 默认流量
            else:
                variables[var_name] = 0.0
        
        # 应用初始猜测
        if initial_guess:
            variables.update(initial_guess)
        
        # 应用边界条件
        if boundary_conditions:
            variables.update(boundary_conditions)
        
        return variables
    
    def _calculate_residuals(self, variables: Dict[str, float], dt: float,
                           prev_states: Dict[str, float]) -> np.ndarray:
        """计算所有模型的残差"""
        all_residuals = []
        
        for model in self.models:
            try:
                model_residuals = model.get_equations(variables, dt, prev_states)
                
                # 按变量顺序排列残差
                model_vars = model.get_variable_names()
                for var_name in model_vars:
                    # 查找对应的方程残差
                    residual = 0.0
                    for eq_name, eq_residual in model_residuals.items():
                        if var_name in eq_name:
                            residual = eq_residual
                            break
                    all_residuals.append(residual)
                
            except Exception as e:
                self.logger.error(f"模型 {model.name} 残差计算失败: {e}")
                # 使用大残差表示错误
                model_vars = model.get_variable_names()
                all_residuals.extend([1000.0] * len(model_vars))
        
        return np.array(all_residuals)
    
    def _calculate_jacobian(self, variables: Dict[str, float], dt: float,
                          prev_states: Dict[str, float]) -> np.ndarray:
        """数值计算雅可比矩阵"""
        n = self.total_variables
        jacobian = np.zeros((n, n))
        
        # 基准残差
        f0 = self._calculate_residuals(variables, dt, prev_states)
        
        # 数值微分
        for j, var_name in enumerate(self.variable_names):
            # 扰动变量
            h = max(abs(variables[var_name]) * self.config.numerical_jacobian_step,
                   self.config.numerical_jacobian_step)
            
            variables_plus = variables.copy()
            variables_plus[var_name] += h
            
            # 计算扰动后的残差
            f_plus = self._calculate_residuals(variables_plus, dt, prev_states)
            
            # 计算偏导数
            jacobian[:, j] = (f_plus - f0) / h
        
        return jacobian
    
    def _solve_linear_system(self, jacobian: np.ndarray, residuals: np.ndarray) -> np.ndarray:
        """求解线性系统"""
        try:
            # 检查条件数
            cond_num = np.linalg.cond(jacobian)
            if cond_num > self.config.max_condition_number:
                self.logger.warning(f"雅可比矩阵条件数过大: {cond_num:.2e}")
            
            # 求解线性系统
            delta_vars = np.linalg.solve(jacobian, -residuals)
            
            # 应用松弛因子
            delta_vars *= self.config.relaxation_factor
            
            return delta_vars
            
        except np.linalg.LinAlgError:
            # 矩阵奇异，使用伪逆
            self.logger.warning("雅可比矩阵奇异，使用伪逆求解")
            delta_vars = np.linalg.pinv(jacobian) @ (-residuals)
            delta_vars *= self.config.relaxation_factor
            return delta_vars
    
    def _update_variables(self, variables: Dict[str, float], delta_vars: np.ndarray) -> Dict[str, float]:
        """更新变量"""
        new_variables = variables.copy()
        
        for i, var_name in enumerate(self.variable_names):
            new_variables[var_name] += delta_vars[i]
            
            # 物理约束
            if var_name.startswith('Q_'):
                # 流量可以为负，但避免极值
                new_variables[var_name] = max(-1000.0, min(1000.0, new_variables[var_name]))
            elif var_name.startswith('H_'):
                # 水位通常为正
                new_variables[var_name] = max(0.0, new_variables[var_name])
        
        return new_variables
    
    def _update_states(self, variables: Dict[str, float], dt: float,
                      prev_states: Dict[str, float]) -> Dict[str, float]:
        """更新状态变量"""
        new_states = prev_states.copy()
        
        # 更新各模型的状态
        for model in self.models:
            if hasattr(model, 'update_states'):
                model_states = model.update_states(variables, dt, prev_states)
                new_states.update(model_states)
        
        return new_states
    
    def get_system_statistics(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        return {
            'total_models': len(self.models),
            'total_variables': self.total_variables,
            'model_types': [model.__class__.__name__ for model in self.models],
            'variable_distribution': {
                model.name: len(model.get_variable_names()) 
                for model in self.models
            }
        }
    
    def validate_solution(self, variables: Dict[str, float], 
                         tolerance: float = 1e-3) -> Dict[str, Any]:
        """
        验证解的有效性
        
        Args:
            variables (Dict[str, float]): 变量值
            tolerance (float): 容差
        
        Returns:
            Dict[str, Any]: 验证结果
        """
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'residual_check': {},
            'physical_check': {}
        }
        
        # 检查残差
        try:
            residuals = self._calculate_residuals(variables, 0.0, {})
            max_residual = np.max(np.abs(residuals))
            
            validation_result['residual_check'] = {
                'max_residual': float(max_residual),
                'residual_norm': float(np.linalg.norm(residuals)),
                'satisfies_tolerance': max_residual < tolerance
            }
            
            if max_residual >= tolerance:
                validation_result['is_valid'] = False
                validation_result['errors'].append(f"最大残差 {max_residual:.2e} 超过容差 {tolerance:.2e}")
        
        except Exception as e:
            validation_result['is_valid'] = False
            validation_result['errors'].append(f"残差计算失败: {e}")
        
        # 物理合理性检查
        for var_name, value in variables.items():
            if math.isnan(value) or math.isinf(value):
                validation_result['is_valid'] = False
                validation_result['errors'].append(f"变量 {var_name} 值异常: {value}")
            elif var_name.startswith('H_') and value < 0:
                validation_result['warnings'].append(f"水位 {var_name} 为负值: {value}")
        
        return validation_result


# 便捷函数
def solve_hydraulic_network(models: List[HydroModel], 
                          initial_conditions: Dict[str, float],
                          solver_config: Optional[SolverConfig] = None) -> Dict[str, Any]:
    """
    求解水力网络稳态问题
    
    Args:
        models (List[HydroModel]): 模型列表
        initial_conditions (Dict[str, float]): 初始条件
        solver_config (SolverConfig, optional): 求解器配置
    
    Returns:
        Dict[str, Any]: 求解结果
    """
    solver = ImplicitSolverAgent(models, solver_config)
    return solver.solve_steady_state(initial_conditions)


def solve_hydraulic_transient(models: List[HydroModel],
                            time_steps: List[float],
                            dt: float,
                            initial_conditions: Dict[str, float],
                            boundary_conditions: Dict[str, Callable] = None,
                            solver_config: Optional[SolverConfig] = None) -> List[Dict[str, Any]]:
    """
    求解水力网络瞬态问题
    
    Args:
        models (List[HydroModel]): 模型列表
        time_steps (List[float]): 时间步列表
        dt (float): 时间步长
        initial_conditions (Dict[str, float]): 初始条件
        boundary_conditions (Dict[str, Callable], optional): 边界条件
        solver_config (SolverConfig, optional): 求解器配置
    
    Returns:
        List[Dict[str, Any]]: 时间序列结果
    """
    solver = ImplicitSolverAgent(models, solver_config)
    return solver.solve_time_series(time_steps, dt, initial_conditions, boundary_conditions)