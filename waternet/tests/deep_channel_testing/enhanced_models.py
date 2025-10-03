"""
增强降阶模型模块

为深度测试提供增强的降阶模型实现，包括：
- 马斯京干模型增强版
- IDZ模型完整实现  
- 蓄量演算模型增强版
- 在线参数调整功能
- 多工况测试支持

Author: WaterNet Development Team
Date: 2024-10-03
"""

import numpy as np
import scipy.optimize as opt
from scipy import interpolate
import warnings
from typing import Dict, List, Callable, Optional, Tuple, Any
from dataclasses import dataclass
import logging

from ...models.lumped_models import BaseLumpedModel, MuskingumModel


@dataclass
class ModelParameterConfig:
    """模型参数配置"""
    # 马斯京干模型参数
    muskingum_K_range: Tuple[float, float] = (500.0, 5000.0)     # 滞时常数范围
    muskingum_x_range: Tuple[float, float] = (0.0, 0.5)          # 权重系数范围
    
    # IDZ模型参数  
    idz_tau_range: Tuple[float, float] = (100.0, 3600.0)         # 零点时间常数范围
    idz_T_range: Tuple[float, float] = (0.0, 1800.0)             # 延迟时间范围
    idz_alpha_range: Tuple[float, float] = (200.0, 7200.0)       # 极点时间常数范围
    
    # 蓄量演算模型参数
    storage_routing_iterations: int = 5                           # 迭代次数
    storage_routing_tolerance: float = 1e-6                      # 收敛容差


class EnhancedMuskingumModel(MuskingumModel):
    """增强型马斯京干模型"""
    
    def __init__(self, dt: float, K: float, x: float, initial_V: float,
                 V_to_H_func: Callable[[float], float],
                 H_to_Q_func: Callable[[float], float],
                 name: str = "Enhanced_Muskingum",
                 enable_parameter_tracking: bool = True):
        """
        初始化增强型马斯京干模型
        
        Parameters:
        -----------
        dt : float
            时间步长 (s)
        K : float
            滞时常数 (s)
        x : float
            权重系数 [0, 0.5]
        initial_V : float
            初始蓄水量 (m³)
        V_to_H_func : Callable
            蓄量-水位关系函数
        H_to_Q_func : Callable  
            水位-出流关系函数
        name : str
            模型名称
        enable_parameter_tracking : bool
            是否启用参数跟踪
        """
        super().__init__(dt, K, x, initial_V, V_to_H_func, H_to_Q_func, name)
        
        self.enable_parameter_tracking = enable_parameter_tracking
        self.logger = logging.getLogger(f"Enhanced_Muskingum_{name}")
        
        # 参数跟踪历史
        if enable_parameter_tracking:
            self.parameter_history = {
                'K': [K],
                'x': [x],
                'C0': [self.C0],
                'C1': [self.C1], 
                'C2': [self.C2],
                'time': [0.0]
            }
        
        # 性能指标
        self.performance_metrics = {
            'mass_balance_error': [],
            'stability_indicator': [],
            'prediction_accuracy': []
        }
    
    def update_parameters(self, new_K: float, new_x: float) -> None:
        """
        在线更新模型参数
        
        Parameters:
        -----------
        new_K : float
            新的滞时常数
        new_x : float
            新的权重系数
        """
        # 参数验证
        if new_K <= 0:
            raise ValueError(f"滞时常数K必须为正值，得到: {new_K}")
        if not (0 <= new_x <= 0.5):
            raise ValueError(f"权重系数x必须在[0, 0.5]范围内，得到: {new_x}")
        
        # 更新参数
        old_K, old_x = self.K, self.x
        self.K = new_K
        self.x = new_x
        
        # 重新计算系数
        self._compute_coefficients()
        
        # 记录参数变化
        if self.enable_parameter_tracking:
            self.parameter_history['K'].append(new_K)
            self.parameter_history['x'].append(new_x)
            self.parameter_history['C0'].append(self.C0)
            self.parameter_history['C1'].append(self.C1)
            self.parameter_history['C2'].append(self.C2)
            self.parameter_history['time'].append(self.time)
        
        self.logger.info(f"参数更新: K {old_K:.1f}->{new_K:.1f}, x {old_x:.3f}->{new_x:.3f}")
    
    def step(self, Q_in: float) -> Dict[str, float]:
        """
        增强版时步推进，包含性能指标计算
        
        Parameters:
        -----------
        Q_in : float
            入流量 (m³/s)
            
        Returns:
        --------
        Dict[str, float]: 仿真结果
        """
        # 调用父类方法
        result = super().step(Q_in)
        
        # 计算性能指标
        if len(self.history['time']) > 1:
            self._compute_performance_metrics(Q_in, result['Q_out'])
        
        return result
    
    def _compute_performance_metrics(self, Q_in: float, Q_out: float) -> None:
        """计算性能指标"""
        # 质量平衡误差
        if len(self.history['V']) >= 2:
            dV_dt = (self.history['V'][-1] - self.history['V'][-2]) / self.dt
            mass_balance_error = abs(dV_dt - (Q_in - Q_out))
            self.performance_metrics['mass_balance_error'].append(mass_balance_error)
        
        # 稳定性指标（基于系数之和）
        stability = abs(self.C0 + self.C1 + self.C2 - 1.0)
        self.performance_metrics['stability_indicator'].append(stability)
    
    def get_parameter_tracking_data(self) -> Dict[str, List]:
        """获取参数跟踪数据"""
        if not self.enable_parameter_tracking:
            return {}
        return self.parameter_history.copy()
    
    def get_performance_summary(self) -> Dict[str, float]:
        """获取性能摘要"""
        if not self.performance_metrics['mass_balance_error']:
            return {}
        
        return {
            'avg_mass_balance_error': np.mean(self.performance_metrics['mass_balance_error']),
            'max_mass_balance_error': np.max(self.performance_metrics['mass_balance_error']),
            'avg_stability_indicator': np.mean(self.performance_metrics['stability_indicator']),
            'max_stability_indicator': np.max(self.performance_metrics['stability_indicator'])
        }


class IntegralDelayZeroModel(BaseLumpedModel):
    """
    IDZ (Integral Delay Zero) 模型
    
    基于传递函数理论的降阶模型，具有积分、延迟和零点特性。
    传递函数形式：G(s) = K * (1 + τ*s) / (s * (1 + α*s)) * exp(-T*s)
    
    参数：
    - τ: 零点时间常数 (s)
    - T: 纯延迟时间 (s)  
    - α: 极点时间常数 (s)
    - K: 稳态增益（自动计算）
    """
    
    def __init__(self, dt: float, tau: float, T: float, alpha: float,
                 initial_V: float, V_to_H_func: Callable[[float], float],
                 H_to_Q_func: Callable[[float], float],
                 name: str = "IDZ_Model"):
        """
        初始化IDZ模型
        
        Parameters:
        -----------
        dt : float
            时间步长 (s)
        tau : float
            零点时间常数 (s)
        T : float
            纯延迟时间 (s)
        alpha : float
            极点时间常数 (s)
        initial_V : float
            初始蓄水量 (m³)
        V_to_H_func : Callable
            蓄量-水位关系函数
        H_to_Q_func : Callable
            水位-出流关系函数
        name : str
            模型名称
        """
        super().__init__(dt, initial_V, V_to_H_func, H_to_Q_func, name)
        
        # 验证参数
        if tau <= 0:
            raise ValueError(f"零点时间常数τ必须为正值，得到: {tau}")
        if T < 0:
            raise ValueError(f"延迟时间T不能为负值，得到: {T}")
        if alpha <= 0:
            raise ValueError(f"极点时间常数α必须为正值，得到: {alpha}")
        
        # IDZ参数
        self.tau = tau
        self.T = T
        self.alpha = alpha
        
        # 计算稳态增益（确保稳态下入流等于出流）
        self.K = 1.0
        
        # 离散化参数
        self._discretize_parameters()
        
        # 延迟缓存器
        self.delay_steps = max(1, int(np.round(T / dt)))
        self.delay_buffer = [0.0] * self.delay_steps
        
        # 内部状态变量
        self.integral_state = 0.0  # 积分器状态
        self.filter_state = 0.0   # 滤波器状态
        
        self.logger = logging.getLogger(f"IDZ_{name}")
        self.logger.info(f"IDZ模型初始化: τ={tau:.1f}s, T={T:.1f}s, α={alpha:.1f}s, 延迟步数={self.delay_steps}")
    
    def _discretize_parameters(self):
        """离散化连续时间参数"""
        # 使用双线性变换 s = 2/dt * (z-1)/(z+1)
        # 对于积分器：1/s -> dt/2 * (z+1)/(z-1)
        # 对于一阶惯性：1/(1+α*s) -> (1+α*2/dt)^(-1) * (1 + (1-α*2/dt)/(1+α*2/dt)*z^(-1))
        
        dt = self.dt
        
        # 积分器离散化参数
        self.integral_coeff = dt / 2.0
        
        # 一阶惯性环节离散化参数
        denom = 1 + self.alpha * 2 / dt
        self.filter_a0 = 1.0 / denom
        self.filter_a1 = (1 - self.alpha * 2 / dt) / denom
        
        # 零点环节离散化参数
        self.zero_b0 = 1.0
        self.zero_b1 = self.tau * 2 / dt
    
    def update_parameters(self, new_tau: float, new_T: float, new_alpha: float) -> None:
        """
        在线更新IDZ模型参数
        
        Parameters:
        -----------
        new_tau : float
            新的零点时间常数
        new_T : float
            新的延迟时间
        new_alpha : float
            新的极点时间常数
        """
        # 参数验证
        if new_tau <= 0:
            raise ValueError(f"零点时间常数τ必须为正值，得到: {new_tau}")
        if new_T < 0:
            raise ValueError(f"延迟时间T不能为负值，得到: {new_T}")
        if new_alpha <= 0:
            raise ValueError(f"极点时间常数α必须为正值，得到: {new_alpha}")
        
        old_params = (self.tau, self.T, self.alpha)
        
        # 更新参数
        self.tau = new_tau
        self.T = new_T
        self.alpha = new_alpha
        
        # 重新离散化
        self._discretize_parameters()
        
        # 更新延迟缓存器
        new_delay_steps = max(1, int(np.round(new_T / self.dt)))
        if new_delay_steps != self.delay_steps:
            if new_delay_steps > self.delay_steps:
                # 增加延迟，填充零值
                self.delay_buffer.extend([0.0] * (new_delay_steps - self.delay_steps))
            else:
                # 减少延迟，截断缓存器
                self.delay_buffer = self.delay_buffer[:new_delay_steps]
            self.delay_steps = new_delay_steps
        
        self.logger.info(f"IDZ参数更新: τ {old_params[0]:.1f}->{new_tau:.1f}, "
                        f"T {old_params[1]:.1f}->{new_T:.1f}, α {old_params[2]:.1f}->{new_alpha:.1f}")
    
    def step(self, Q_in: float) -> Dict[str, float]:
        """
        IDZ模型时步推进
        
        实现IDZ传递函数的差分方程形式
        
        Parameters:
        -----------
        Q_in : float
            入流量 (m³/s)
            
        Returns:
        --------
        Dict[str, float]: 仿真结果
        """
        # 1. 零点环节处理
        zero_output = self.zero_b0 * Q_in + self.zero_b1 * getattr(self, '_prev_Q_in', 0.0)
        
        # 2. 积分环节处理
        integral_input = zero_output
        self.integral_state += self.integral_coeff * (integral_input + getattr(self, '_prev_integral_input', 0.0))
        
        # 3. 延迟环节处理
        delayed_signal = self.delay_buffer[0]  # 取出最老的值
        self.delay_buffer[1:] = self.delay_buffer[:-1]  # 移位
        self.delay_buffer[-1] = self.integral_state  # 加入新值
        
        # 4. 一阶惯性环节处理
        filter_input = delayed_signal
        filter_output = self.filter_a0 * filter_input + self.filter_a1 * self.filter_state
        self.filter_state = filter_output
        
        # 5. 增益
        Q_out = self.K * filter_output
        Q_out = max(0.0, Q_out)  # 确保出流非负
        
        # 更新物理状态
        self._update_physical_states(Q_in, Q_out)
        
        # 更新当前出流
        self.current_Q_out = Q_out
        
        # 保存前一时步值
        self._prev_Q_in = Q_in
        self._prev_integral_input = integral_input
        
        # 记录状态
        self._record_state(Q_in)
        
        return {
            'Q_out': Q_out,
            'H_out': self.current_H,
            'V': self.current_V,
            'time': self.time,
            'integral_state': self.integral_state,
            'filter_state': self.filter_state,
            'delayed_signal': delayed_signal
        }
    
    def reset_states(self):
        """重置内部状态"""
        self.integral_state = 0.0
        self.filter_state = 0.0
        self.delay_buffer = [0.0] * self.delay_steps
        self._prev_Q_in = 0.0
        self._prev_integral_input = 0.0
    
    def get_transfer_function_response(self, input_signal: np.ndarray) -> np.ndarray:
        """
        计算传递函数对输入信号的响应
        
        Parameters:
        -----------
        input_signal : np.ndarray
            输入信号序列
            
        Returns:
        --------
        np.ndarray: 输出响应序列
        """
        # 保存当前状态
        original_state = {
            'integral_state': self.integral_state,
            'filter_state': self.filter_state,
            'delay_buffer': self.delay_buffer.copy(),
            'time': self.time
        }
        
        # 重置状态
        self.reset_states()
        self.time = 0.0
        
        # 计算响应
        output_signal = np.zeros_like(input_signal)
        for i, Q_in in enumerate(input_signal):
            result = self.step(Q_in)
            output_signal[i] = result['Q_out']
        
        # 恢复原始状态
        self.integral_state = original_state['integral_state']
        self.filter_state = original_state['filter_state']
        self.delay_buffer = original_state['delay_buffer']
        self.time = original_state['time']
        
        return output_signal


class EnhancedStorageRoutingModel(BaseLumpedModel):
    """增强型蓄量演算模型"""
    
    def __init__(self, dt: float, initial_V: float,
                 V_to_H_func: Callable[[float], float],
                 H_to_Q_func: Callable[[float], float],
                 name: str = "Enhanced_StorageRouting",
                 max_iterations: int = 10,
                 tolerance: float = 1e-6):
        """
        初始化增强型蓄量演算模型
        
        Parameters:
        -----------
        dt : float
            时间步长 (s)
        initial_V : float
            初始蓄水量 (m³)
        V_to_H_func : Callable
            蓄量-水位关系函数
        H_to_Q_func : Callable
            水位-出流关系函数
        name : str
            模型名称
        max_iterations : int
            最大迭代次数
        tolerance : float
            收敛容差
        """
        super().__init__(dt, initial_V, V_to_H_func, H_to_Q_func, name)
        
        self.max_iterations = max_iterations
        self.tolerance = tolerance
        self.logger = logging.getLogger(f"Enhanced_StorageRouting_{name}")
        
        # 迭代统计
        self.iteration_statistics = {
            'total_iterations': [],
            'convergence_flags': [],
            'final_residuals': []
        }
    
    def step(self, Q_in: float) -> Dict[str, float]:
        """
        增强版蓄量演算时步推进，使用牛顿-拉夫逊法求解
        
        Parameters:
        -----------
        Q_in : float
            入流量 (m³/s)
            
        Returns:
        --------
        Dict[str, float]: 仿真结果
        """
        V_old = self.current_V
        Q_out_old = self.current_Q_out
        
        # 牛顿-拉夫逊迭代求解
        V_new = V_old
        converged = False
        
        for iteration in range(self.max_iterations):
            # 计算残差和雅可比
            residual, jacobian = self._compute_residual_and_jacobian(V_new, V_old, Q_in)
            
            # 检查收敛
            if abs(residual) < self.tolerance:
                converged = True
                break
            
            # 牛顿更新
            if abs(jacobian) > 1e-12:
                delta_V = -residual / jacobian
                V_new += delta_V
                
                # 物理约束
                V_new = max(self._min_volume, V_new)
            else:
                self.logger.warning("雅可比矩阵奇异，使用简单迭代")
                H_new = self._safe_V_to_H(V_new)
                Q_out_new = self._safe_H_to_Q(H_new)
                V_new = V_old + (Q_in - (Q_out_old + Q_out_new) / 2.0) * self.dt
                break
        
        # 记录迭代统计
        self.iteration_statistics['total_iterations'].append(iteration + 1)
        self.iteration_statistics['convergence_flags'].append(converged)
        self.iteration_statistics['final_residuals'].append(abs(residual))
        
        if not converged:
            self.logger.warning(f"迭代未收敛，残差: {residual:.2e}")
        
        # 更新状态
        self.current_V = V_new
        self.current_H = self._safe_V_to_H(V_new)
        self.current_Q_out = self._safe_H_to_Q(self.current_H)
        
        # 记录状态
        self._record_state(Q_in)
        
        return {
            'Q_out': self.current_Q_out,
            'H_out': self.current_H,
            'V': self.current_V,
            'time': self.time,
            'iterations': iteration + 1,
            'converged': converged,
            'residual': abs(residual)
        }
    
    def _compute_residual_and_jacobian(self, V_new: float, V_old: float, 
                                     Q_in: float) -> Tuple[float, float]:
        """
        计算残差和雅可比矩阵
        
        残差函数: R(V) = V - V_old - dt * (Q_in - Q_out(V))
        """
        # 计算当前出流
        H_new = self._safe_V_to_H(V_new)
        Q_out_new = self._safe_H_to_Q(H_new)
        
        # 残差
        residual = V_new - V_old - self.dt * (Q_in - Q_out_new)
        
        # 雅可比 dR/dV = 1 + dt * dQ_out/dV
        # 使用数值微分计算 dQ_out/dV
        epsilon = 1e-3
        V_pert = V_new + epsilon
        H_pert = self._safe_V_to_H(V_pert)
        Q_out_pert = self._safe_H_to_Q(H_pert)
        
        dQ_out_dV = (Q_out_pert - Q_out_new) / epsilon
        jacobian = 1.0 + self.dt * dQ_out_dV
        
        return residual, jacobian
    
    def get_iteration_statistics(self) -> Dict[str, Any]:
        """获取迭代统计信息"""
        if not self.iteration_statistics['total_iterations']:
            return {}
        
        return {
            'average_iterations': np.mean(self.iteration_statistics['total_iterations']),
            'max_iterations': np.max(self.iteration_statistics['total_iterations']),
            'convergence_rate': np.mean(self.iteration_statistics['convergence_flags']),
            'average_residual': np.mean(self.iteration_statistics['final_residuals']),
            'max_residual': np.max(self.iteration_statistics['final_residuals'])
        }