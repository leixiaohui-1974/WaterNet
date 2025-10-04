"""
自适应时间步长算法

实现自适应时间步长控制，通过动态调整时间步长提高求解鲁棒性和效率。
收敛失败时自动减小时间步，成功时逐步恢复，并提供多种控制策略。

设计原则:
1. 鲁棒性: 处理求解失败和数值不稳定
2. 效率性: 在保证精度的前提下最大化时间步长
3. 自适应: 根据系统状态动态调整步长
4. 可配置: 提供多种控制策略和参数

主要组件:
- AdaptiveTimeStepConfig: 配置参数
- TimeStepController: 时间步长控制器
- ConversionMonitor: 收敛性监控
- StabilityAssessment: 稳定性评估

Author: WaterNet Development Team
Date: 2024-10-04
"""

import numpy as np
import math
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
import time


class TimeStepStrategy(Enum):
    """时间步长调整策略"""
    CONSERVATIVE = "conservative"  # 保守策略
    AGGRESSIVE = "aggressive"     # 激进策略
    BALANCED = "balanced"         # 平衡策略
    ADAPTIVE = "adaptive"         # 自适应策略


class ConvergenceStatus(Enum):
    """收敛状态"""
    CONVERGED = "converged"
    SLOW_CONVERGENCE = "slow_convergence"
    FAILED = "failed"
    DIVERGED = "diverged"


@dataclass
class AdaptiveTimeStepConfig:
    """自适应时间步长配置"""
    # 基本参数
    initial_dt: float = 1.0
    min_dt: float = 1e-6
    max_dt: float = 3600.0
    
    # 调整策略
    strategy: TimeStepStrategy = TimeStepStrategy.BALANCED
    reduction_factor: float = 0.5
    increase_factor: float = 1.2
    max_reduction_factor: float = 0.1
    
    # 收敛控制
    max_failed_attempts: int = 5
    min_successful_steps: int = 3
    convergence_history_length: int = 10
    
    # 稳定性控制
    enable_stability_check: bool = True
    max_residual_growth: float = 10.0
    max_variable_change: float = 0.5
    
    # CFL条件控制
    enable_cfl_control: bool = False
    target_cfl: float = 0.8
    max_cfl: float = 1.0
    
    # 误差控制
    enable_error_control: bool = False
    target_error: float = 1e-3
    error_tolerance: float = 1e-2


@dataclass
class TimeStepStatistics:
    """时间步长统计信息"""
    total_steps: int = 0
    successful_steps: int = 0
    failed_steps: int = 0
    dt_reductions: int = 0
    dt_increases: int = 0
    min_dt_used: float = float('inf')
    max_dt_used: float = 0.0
    avg_dt: float = 0.0
    total_time: float = 0.0
    convergence_history: List[ConvergenceStatus] = field(default_factory=list)
    dt_history: List[float] = field(default_factory=list)


class ConvergenceMonitor:
    """
    收敛性监控器
    
    监控求解过程的收敛性，判断收敛状态和趋势。
    """
    
    def __init__(self, config: AdaptiveTimeStepConfig):
        """
        初始化收敛性监控器
        
        Args:
            config (AdaptiveTimeStepConfig): 配置参数
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        self.residual_history = []
        self.iteration_history = []
        self.convergence_times = []
        
    def assess_convergence(self, solver_result: Dict[str, Any]) -> ConvergenceStatus:
        """
        评估收敛状态
        
        Args:
            solver_result (Dict[str, Any]): 求解器结果
            
        Returns:
            ConvergenceStatus: 收敛状态
        """
        if not solver_result.get('converged', False):
            # 检查是否发散
            if self._is_diverging(solver_result):
                return ConvergenceStatus.DIVERGED
            else:
                return ConvergenceStatus.FAILED
        
        # 检查收敛速度
        iterations = solver_result.get('statistics', {}).get('total_iterations', 0)
        final_residual = solver_result.get('statistics', {}).get('final_residual_norm', float('inf'))
        
        # 记录历史
        self.iteration_history.append(iterations)
        self.residual_history.append(final_residual)
        
        # 保持历史长度
        max_history = self.config.convergence_history_length
        if len(self.iteration_history) > max_history:
            self.iteration_history = self.iteration_history[-max_history:]
            self.residual_history = self.residual_history[-max_history:]
        
        # 判断收敛速度
        if iterations > 30:  # 迭代次数过多
            return ConvergenceStatus.SLOW_CONVERGENCE
        
        return ConvergenceStatus.CONVERGED
    
    def _is_diverging(self, solver_result: Dict[str, Any]) -> bool:
        """检查是否发散"""
        stats = solver_result.get('statistics', {})
        convergence_history = stats.get('convergence_history', [])
        
        if len(convergence_history) < 3:
            return False
        
        # 检查残差是否持续增长
        recent_residuals = convergence_history[-3:]
        growth_trend = all(recent_residuals[i] > recent_residuals[i-1] 
                          for i in range(1, len(recent_residuals)))
        
        # 检查增长幅度
        if growth_trend and len(convergence_history) > 1:
            growth_factor = convergence_history[-1] / convergence_history[0]
            return growth_factor > self.config.max_residual_growth
        
        return False
    
    def get_convergence_trend(self) -> str:
        """获取收敛趋势"""
        if len(self.iteration_history) < 3:
            return "insufficient_data"
        
        recent_iterations = self.iteration_history[-3:]
        avg_recent = np.mean(recent_iterations)
        
        if len(self.iteration_history) >= 6:
            earlier_iterations = self.iteration_history[-6:-3]
            avg_earlier = np.mean(earlier_iterations)
            
            if avg_recent < avg_earlier * 0.8:
                return "improving"
            elif avg_recent > avg_earlier * 1.2:
                return "deteriorating"
        
        return "stable"


class StabilityAssessment:
    """
    稳定性评估器
    
    评估数值稳定性，检测潜在的数值问题。
    """
    
    def __init__(self, config: AdaptiveTimeStepConfig):
        """
        初始化稳定性评估器
        
        Args:
            config (AdaptiveTimeStepConfig): 配置参数
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        self.previous_variables = None
        self.variable_change_history = []
        
    def assess_stability(self, current_variables: Dict[str, float],
                        solver_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        评估数值稳定性
        
        Args:
            current_variables (Dict[str, float]): 当前变量值
            solver_result (Dict[str, Any]): 求解器结果
            
        Returns:
            Dict[str, Any]: 稳定性评估结果
        """
        assessment = {
            'is_stable': True,
            'issues': [],
            'recommendations': [],
            'stability_score': 1.0
        }
        
        # 检查变量变化幅度
        if self.previous_variables is not None:
            variable_changes = self._calculate_variable_changes(current_variables)
            assessment.update(self._assess_variable_changes(variable_changes))
        
        # 检查残差特性
        residual_assessment = self._assess_residual_behavior(solver_result)
        assessment['residual_stability'] = residual_assessment
        
        # 检查物理合理性
        physical_assessment = self._assess_physical_validity(current_variables)
        assessment['physical_validity'] = physical_assessment
        
        # 综合稳定性评分
        assessment['stability_score'] = self._calculate_stability_score(assessment)
        assessment['is_stable'] = assessment['stability_score'] > 0.7
        
        # 更新历史
        self.previous_variables = current_variables.copy()
        
        return assessment
    
    def _calculate_variable_changes(self, current_variables: Dict[str, float]) -> Dict[str, float]:
        """计算变量变化"""
        changes = {}
        
        for var_name, current_value in current_variables.items():
            if var_name in self.previous_variables:
                prev_value = self.previous_variables[var_name]
                if abs(prev_value) > 1e-12:
                    relative_change = abs(current_value - prev_value) / abs(prev_value)
                else:
                    relative_change = abs(current_value - prev_value)
                changes[var_name] = relative_change
        
        return changes
    
    def _assess_variable_changes(self, variable_changes: Dict[str, float]) -> Dict[str, Any]:
        """评估变量变化"""
        assessment = {
            'max_change': max(variable_changes.values()) if variable_changes else 0.0,
            'avg_change': np.mean(list(variable_changes.values())) if variable_changes else 0.0,
            'large_changes': []
        }
        
        # 检查过大的变化
        for var_name, change in variable_changes.items():
            if change > self.config.max_variable_change:
                assessment['large_changes'].append((var_name, change))
        
        return assessment
    
    def _assess_residual_behavior(self, solver_result: Dict[str, Any]) -> Dict[str, Any]:
        """评估残差行为"""
        stats = solver_result.get('statistics', {})
        convergence_history = stats.get('convergence_history', [])
        
        assessment = {
            'final_residual': stats.get('final_residual_norm', float('inf')),
            'residual_reduction': 0.0,
            'monotonic_convergence': False,
            'oscillatory_behavior': False
        }
        
        if len(convergence_history) > 1:
            initial_residual = convergence_history[0]
            final_residual = convergence_history[-1]
            
            if initial_residual > 1e-15:
                assessment['residual_reduction'] = final_residual / initial_residual
            
            # 检查单调收敛
            assessment['monotonic_convergence'] = all(
                convergence_history[i] >= convergence_history[i+1] 
                for i in range(len(convergence_history)-1)
            )
            
            # 检查振荡行为
            if len(convergence_history) > 4:
                recent_residuals = convergence_history[-4:]
                ups = sum(1 for i in range(1, len(recent_residuals)) 
                         if recent_residuals[i] > recent_residuals[i-1])
                assessment['oscillatory_behavior'] = ups >= 2
        
        return assessment
    
    def _assess_physical_validity(self, variables: Dict[str, float]) -> Dict[str, Any]:
        """评估物理合理性"""
        assessment = {
            'has_nan': False,
            'has_inf': False,
            'negative_flows': [],
            'extreme_values': []
        }
        
        for var_name, value in variables.items():
            if math.isnan(value):
                assessment['has_nan'] = True
            elif math.isinf(value):
                assessment['has_inf'] = True
            elif abs(value) > 1e6:
                assessment['extreme_values'].append((var_name, value))
            elif var_name.startswith('Q_') and value < -1000:
                assessment['negative_flows'].append((var_name, value))
        
        return assessment
    
    def _calculate_stability_score(self, assessment: Dict[str, Any]) -> float:
        """计算稳定性评分"""
        score = 1.0
        
        # 变量变化扣分
        max_change = assessment.get('max_change', 0.0)
        if max_change > self.config.max_variable_change:
            score *= 0.5
        
        # 残差行为扣分
        residual_info = assessment.get('residual_stability', {})
        if residual_info.get('oscillatory_behavior', False):
            score *= 0.7
        if not residual_info.get('monotonic_convergence', True):
            score *= 0.8
        
        # 物理合理性扣分
        physical_info = assessment.get('physical_validity', {})
        if physical_info.get('has_nan', False) or physical_info.get('has_inf', False):
            score *= 0.1
        if physical_info.get('extreme_values', []):
            score *= 0.6
        
        return max(0.0, min(1.0, score))


class TimeStepController:
    """
    时间步长控制器
    
    根据收敛性和稳定性评估结果动态调整时间步长。
    """
    
    def __init__(self, config: AdaptiveTimeStepConfig = None):
        """
        初始化时间步长控制器
        
        Args:
            config (AdaptiveTimeStepConfig): 配置参数
        """
        self.config = config or AdaptiveTimeStepConfig()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        self.current_dt = self.config.initial_dt
        self.consecutive_failures = 0
        self.consecutive_successes = 0
        
        # 初始化监控组件
        self.convergence_monitor = ConvergenceMonitor(self.config)
        self.stability_assessment = StabilityAssessment(self.config)
        
        # 统计信息
        self.statistics = TimeStepStatistics()
        
        self.logger.info(f"时间步长控制器初始化: 初始dt={self.current_dt}, 策略={self.config.strategy.value}")
    
    def adjust_timestep(self, solver_result: Dict[str, Any],
                       current_variables: Dict[str, float] = None) -> Tuple[float, Dict[str, Any]]:
        """
        调整时间步长
        
        Args:
            solver_result (Dict[str, Any]): 求解器结果
            current_variables (Dict[str, float], optional): 当前变量值
            
        Returns:
            Tuple[float, Dict[str, Any]]: (新时间步长, 调整信息)
        """
        # 评估收敛性
        convergence_status = self.convergence_monitor.assess_convergence(solver_result)
        
        # 评估稳定性
        stability_info = {}
        if current_variables and self.config.enable_stability_check:
            stability_info = self.stability_assessment.assess_stability(current_variables, solver_result)
        
        # 决定调整策略
        adjustment_info = self._determine_adjustment(convergence_status, stability_info, solver_result)
        
        # 应用调整
        old_dt = self.current_dt
        self.current_dt = self._apply_adjustment(adjustment_info)
        
        # 更新统计
        self._update_statistics(convergence_status, old_dt, self.current_dt)
        
        # 记录调整信息
        adjustment_info.update({
            'old_dt': old_dt,
            'new_dt': self.current_dt,
            'convergence_status': convergence_status.value,
            'stability_score': stability_info.get('stability_score', 1.0)
        })
        
        if old_dt != self.current_dt:
            self.logger.info(f"时间步长调整: {old_dt:.6f} -> {self.current_dt:.6f} ({adjustment_info['reason']})")
        
        return self.current_dt, adjustment_info
    
    def _determine_adjustment(self, convergence_status: ConvergenceStatus,
                            stability_info: Dict[str, Any],
                            solver_result: Dict[str, Any]) -> Dict[str, Any]:
        """确定调整策略"""
        adjustment_info = {
            'action': 'maintain',
            'factor': 1.0,
            'reason': 'stable'
        }
        
        # 处理收敛失败
        if convergence_status in [ConvergenceStatus.FAILED, ConvergenceStatus.DIVERGED]:
            self.consecutive_failures += 1
            self.consecutive_successes = 0
            
            # 计算减小因子
            if convergence_status == ConvergenceStatus.DIVERGED:
                factor = self.config.max_reduction_factor
                reason = "发散"
            else:
                factor = self.config.reduction_factor ** self.consecutive_failures
                factor = max(factor, self.config.max_reduction_factor)
                reason = f"收敛失败({self.consecutive_failures}次)"
            
            adjustment_info.update({
                'action': 'reduce',
                'factor': factor,
                'reason': reason
            })
        
        # 处理收敛成功
        elif convergence_status == ConvergenceStatus.CONVERGED:
            self.consecutive_failures = 0
            self.consecutive_successes += 1
            
            # 检查是否可以增大时间步
            can_increase = (
                self.consecutive_successes >= self.config.min_successful_steps and
                stability_info.get('stability_score', 1.0) > 0.8 and
                self.current_dt < self.config.max_dt
            )
            
            if can_increase:
                factor = self._calculate_increase_factor(stability_info, solver_result)
                adjustment_info.update({
                    'action': 'increase',
                    'factor': factor,
                    'reason': f"连续成功({self.consecutive_successes}次)"
                })
        
        # 处理慢收敛
        elif convergence_status == ConvergenceStatus.SLOW_CONVERGENCE:
            self.consecutive_successes = 0
            
            if self.config.strategy in [TimeStepStrategy.CONSERVATIVE, TimeStepStrategy.BALANCED]:
                adjustment_info.update({
                    'action': 'reduce',
                    'factor': 0.8,
                    'reason': "收敛缓慢"
                })
        
        # 稳定性检查
        if stability_info.get('stability_score', 1.0) < 0.5:
            adjustment_info.update({
                'action': 'reduce',
                'factor': 0.5,
                'reason': "数值不稳定"
            })
        
        return adjustment_info
    
    def _calculate_increase_factor(self, stability_info: Dict[str, Any],
                                 solver_result: Dict[str, Any]) -> float:
        """计算增大因子"""
        base_factor = self.config.increase_factor
        
        # 根据稳定性调整
        stability_score = stability_info.get('stability_score', 1.0)
        if stability_score < 0.9:
            base_factor = min(base_factor, 1.1)
        
        # 根据收敛速度调整
        stats = solver_result.get('statistics', {})
        iterations = stats.get('total_iterations', 10)
        if iterations > 15:
            base_factor = min(base_factor, 1.05)
        elif iterations < 5:
            base_factor = min(base_factor * 1.2, self.config.increase_factor * 1.5)
        
        # 根据策略调整
        if self.config.strategy == TimeStepStrategy.CONSERVATIVE:
            base_factor = min(base_factor, 1.1)
        elif self.config.strategy == TimeStepStrategy.AGGRESSIVE:
            base_factor = min(base_factor * 1.3, 2.0)
        
        return base_factor
    
    def _apply_adjustment(self, adjustment_info: Dict[str, Any]) -> float:
        """应用时间步长调整"""
        action = adjustment_info['action']
        factor = adjustment_info['factor']
        
        if action == 'reduce':
            new_dt = self.current_dt * factor
            new_dt = max(new_dt, self.config.min_dt)
        elif action == 'increase':
            new_dt = self.current_dt * factor
            new_dt = min(new_dt, self.config.max_dt)
        else:  # maintain
            new_dt = self.current_dt
        
        return new_dt
    
    def _update_statistics(self, convergence_status: ConvergenceStatus, old_dt: float, new_dt: float):
        """更新统计信息"""
        self.statistics.total_steps += 1
        
        if convergence_status == ConvergenceStatus.CONVERGED:
            self.statistics.successful_steps += 1
        else:
            self.statistics.failed_steps += 1
        
        if new_dt < old_dt:
            self.statistics.dt_reductions += 1
        elif new_dt > old_dt:
            self.statistics.dt_increases += 1
        
        self.statistics.min_dt_used = min(self.statistics.min_dt_used, new_dt)
        self.statistics.max_dt_used = max(self.statistics.max_dt_used, new_dt)
        
        # 更新平均时间步
        total_dt = self.statistics.avg_dt * (self.statistics.total_steps - 1) + new_dt
        self.statistics.avg_dt = total_dt / self.statistics.total_steps
        
        # 记录历史
        self.statistics.convergence_history.append(convergence_status)
        self.statistics.dt_history.append(new_dt)
        
        # 保持历史长度
        max_history = self.config.convergence_history_length * 2
        if len(self.statistics.convergence_history) > max_history:
            self.statistics.convergence_history = self.statistics.convergence_history[-max_history:]
            self.statistics.dt_history = self.statistics.dt_history[-max_history:]
    
    def get_current_timestep(self) -> float:
        """获取当前时间步长"""
        return self.current_dt
    
    def get_statistics(self) -> TimeStepStatistics:
        """获取统计信息"""
        return self.statistics
    
    def reset(self, new_initial_dt: Optional[float] = None):
        """重置控制器"""
        if new_initial_dt is not None:
            self.current_dt = new_initial_dt
        else:
            self.current_dt = self.config.initial_dt
        
        self.consecutive_failures = 0
        self.consecutive_successes = 0
        self.statistics = TimeStepStatistics()
        
        self.logger.info(f"时间步长控制器重置: dt={self.current_dt}")


# 便捷函数
def create_adaptive_controller(strategy: TimeStepStrategy = TimeStepStrategy.BALANCED,
                             initial_dt: float = 1.0,
                             min_dt: float = 1e-6,
                             max_dt: float = 3600.0) -> TimeStepController:
    """
    创建自适应时间步长控制器的便捷函数
    
    Args:
        strategy (TimeStepStrategy): 调整策略
        initial_dt (float): 初始时间步长
        min_dt (float): 最小时间步长
        max_dt (float): 最大时间步长
        
    Returns:
        TimeStepController: 时间步长控制器
    """
    config = AdaptiveTimeStepConfig(
        strategy=strategy,
        initial_dt=initial_dt,
        min_dt=min_dt,
        max_dt=max_dt
    )
    
    return TimeStepController(config)


def analyze_timestep_performance(controller: TimeStepController) -> Dict[str, Any]:
    """
    分析时间步长性能
    
    Args:
        controller (TimeStepController): 时间步长控制器
        
    Returns:
        Dict[str, Any]: 性能分析结果
    """
    stats = controller.get_statistics()
    
    if stats.total_steps == 0:
        return {'message': '没有统计数据'}
    
    success_rate = stats.successful_steps / stats.total_steps
    avg_dt = stats.avg_dt
    dt_range = stats.max_dt_used - stats.min_dt_used
    
    # 计算自适应效果
    dt_changes = stats.dt_reductions + stats.dt_increases
    adaptability = dt_changes / stats.total_steps if stats.total_steps > 0 else 0
    
    return {
        'success_rate': success_rate,
        'average_timestep': avg_dt,
        'timestep_range': (stats.min_dt_used, stats.max_dt_used),
        'timestep_variability': dt_range / avg_dt if avg_dt > 0 else 0,
        'adaptability_index': adaptability,
        'total_steps': stats.total_steps,
        'reductions': stats.dt_reductions,
        'increases': stats.dt_increases,
        'performance_score': success_rate * (1 + adaptability * 0.1)
    }