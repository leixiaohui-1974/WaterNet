"""
IDZ线性化器 - 四方程IDZ双断面耦合参数辨识

实现四方程IDZ模型的参数辨识和双断面耦合关系建模。
基于稳态物理条件的平衡点理论，支持上下游双向耦合。

Author: WaterNet Development Team  
Date: 2024-10-04
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Callable, Any
import logging
from dataclasses import dataclass
from scipy.optimize import minimize, differential_evolution
from scipy.signal import lti, step, impulse
import warnings

from .flow_stage_interval_system import FlowStageInterval, IDZModelParameters


@dataclass
class IDZLinearizationConfig:
    """IDZ线性化配置参数"""
    # 参数搜索边界
    tau_bounds: Tuple[float, float] = (50.0, 500.0)      # 零点时间常数范围
    T_bounds: Tuple[float, float] = (0.0, 1200.0)        # 延迟时间范围  
    alpha_bounds: Tuple[float, float] = (200.0, 800.0)   # 极点时间常数范围
    
    # 物理约束
    enforce_causality: bool = True                        # 强制因果性
    enforce_stability: bool = True                        # 强制稳定性
    
    # 优化设置
    optimization_method: str = 'differential_evolution'   # 优化算法
    max_iterations: int = 1000                           # 最大迭代次数
    tolerance: float = 1e-6                             # 收敛容差
    population_size: int = 15                            # 种群大小（用于遗传算法）
    
    # 测试信号设置
    test_signal_duration: float = 3600.0                # 测试信号时长（秒）
    test_signal_dt: float = 60.0                        # 测试信号时间步长（秒）
    test_signal_types: Optional[List[str]] = None                  # 测试信号类型
    
    def __post_init__(self):
        if self.test_signal_types is None:
            self.test_signal_types = ['step', 'impulse', 'ramp']


class IDZLinearizer:
    """
    IDZ线性化器
    
    为每个区间执行四方程IDZ模型辨识，建立双断面耦合关系。
    """
    
    def __init__(self, config: Optional[IDZLinearizationConfig] = None):
        """
        初始化IDZ线性化器
        
        Args:
            config: IDZ线性化配置
        """
        self.config = config or IDZLinearizationConfig()
        self.logger = logging.getLogger("IDZLinearizer")
        
        # 缓存变量
        self._parameter_cache: Dict[str, IDZModelParameters] = {}
        self._identification_history: List[Dict] = []
    
    def compute_equilibrium_point(self, interval: FlowStageInterval, 
                                method: str = 'geometric_center') -> Dict[str, float]:
        """
        计算区间的双断面平衡点
        
        Args:
            interval: 目标区间
            method: 计算方法 ('geometric_center', 'weighted_center', 'optimal_center')
            
        Returns:
            Dict: 双断面平衡点 {Q_up, H_up, Q_down, H_down}
        """
        Q_min, Q_max = interval.Q_bounds
        H_min, H_max = interval.H_bounds
        
        if method == 'geometric_center':
            Q_center = (Q_min + Q_max) / 2.0
            H_center = (H_min + H_max) / 2.0
            
            equilibrium = {
                'Q_up': Q_center,
                'H_up': H_center,
                'Q_down': Q_center * 0.98,    # 下游略小（考虑损失）
                'H_down': H_center - 0.05     # 下游略低（考虑坡度）
            }
            
        elif method == 'weighted_center':
            # 基于物理重要性的加权平均
            Q_center = Q_min * 0.3 + Q_max * 0.7  # 偏向大流量
            H_center = (H_min + H_max) / 2.0
            
            equilibrium = {
                'Q_up': Q_center,
                'H_up': H_center,
                'Q_down': Q_center * 0.96,
                'H_down': H_center - 0.08
            }
            
        elif method == 'optimal_center':
            # 最小化区间内最大误差的最优点（简化实现）
            Q_opt = Q_min + (Q_max - Q_min) * 0.618  # 黄金分割点
            H_opt = H_min + (H_max - H_min) * 0.618
            
            equilibrium = {
                'Q_up': Q_opt,
                'H_up': H_opt,
                'Q_down': Q_opt * 0.94,
                'H_down': H_opt - 0.1
            }
            
        else:
            raise ValueError(f"未知的平衡点计算方法: {method}")
        
        self.logger.debug(f"区间 {interval.interval_id} 平衡点: {equilibrium}")
        return equilibrium
    
    def identify_four_equation_parameters(self, interval: FlowStageInterval,
                                        reference_model: Any,
                                        equilibrium_point: Optional[Dict[str, float]] = None) -> IDZModelParameters:
        """
        辨识四方程IDZ参数
        
        Args:
            interval: 目标区间
            reference_model: 参考模型（圣维南模型）
            equilibrium_point: 平衡点，如果为None则自动计算
            
        Returns:
            IDZModelParameters: 辨识的参数
        """
        if equilibrium_point is None:
            equilibrium_point = self.compute_equilibrium_point(interval)
        
        # 生成测试数据
        test_data = self._generate_test_data(interval, equilibrium_point)
        
        # 计算参考响应
        reference_responses = self._compute_reference_responses(
            reference_model, test_data, equilibrium_point)
        
        # 参数优化
        optimal_params = self._optimize_parameters(test_data, reference_responses, equilibrium_point)
        
        # 验证参数
        self._validate_parameters(optimal_params)
        
        # 记录辨识历史
        self._record_identification_history(interval, optimal_params, reference_responses)
        
        return optimal_params
    
    def _generate_test_data(self, interval: FlowStageInterval, 
                          equilibrium_point: Dict[str, float]) -> Dict[str, np.ndarray]:
        """
        生成测试数据
        
        为四个传递函数生成多样化的测试信号
        """
        duration = self.config.test_signal_duration
        dt = self.config.test_signal_dt
        n_steps = int(duration / dt)
        time_array = np.linspace(0, duration, n_steps)
        
        Q0_up = equilibrium_point['Q_up']
        Q0_down = equilibrium_point['Q_down']
        
        # 生成扰动幅度（相对于平衡点的10-30%）
        Q_range = interval.Q_bounds[1] - interval.Q_bounds[0]
        disturbance_amplitude = min(Q_range * 0.2, Q0_up * 0.3)
        
        test_signals = {}
        
        signal_types = self.config.test_signal_types or ['step', 'impulse', 'ramp']
        for signal_type in signal_types:
            if signal_type == 'step':
                # 阶跃信号
                signal_up = np.zeros(n_steps)
                signal_down = np.zeros(n_steps)
                
                # 上游阶跃（1/4处开始）
                step_start = n_steps // 4
                signal_up[step_start:] = disturbance_amplitude
                
                # 下游阶跃（1/2处开始）
                step_start_down = n_steps // 2
                signal_down[step_start_down:] = disturbance_amplitude * 0.7
                
                test_signals[f'{signal_type}_up'] = signal_up
                test_signals[f'{signal_type}_down'] = signal_down
                
            elif signal_type == 'impulse':
                # 脉冲信号
                signal_up = np.zeros(n_steps)
                signal_down = np.zeros(n_steps)
                
                # 上游脉冲
                pulse_start = n_steps // 3
                pulse_duration = n_steps // 10
                signal_up[pulse_start:pulse_start+pulse_duration] = disturbance_amplitude * 1.5
                
                # 下游脉冲
                pulse_start_down = 2 * n_steps // 3
                signal_down[pulse_start_down:pulse_start_down+pulse_duration] = disturbance_amplitude
                
                test_signals[f'{signal_type}_up'] = signal_up
                test_signals[f'{signal_type}_down'] = signal_down
                
            elif signal_type == 'ramp':
                # 斜坡信号
                signal_up = np.zeros(n_steps)
                signal_down = np.zeros(n_steps)
                
                # 上游斜坡
                ramp_start = n_steps // 6
                ramp_end = n_steps // 2
                ramp_steps = ramp_end - ramp_start
                signal_up[ramp_start:ramp_end] = np.linspace(0, disturbance_amplitude, ramp_steps)
                signal_up[ramp_end:] = disturbance_amplitude
                
                test_signals[f'{signal_type}_up'] = signal_up
                test_signals[f'{signal_type}_down'] = signal_down
        
        test_signals['time'] = time_array
        test_signals['equilibrium'] = equilibrium_point
        
        return test_signals
    
    def _compute_reference_responses(self, reference_model: Any, 
                                   test_data: Dict[str, np.ndarray],
                                   equilibrium_point: Dict[str, float]) -> Dict[str, np.ndarray]:
        """
        计算参考模型的响应
        
        使用圣维南模型计算对测试信号的响应，作为IDZ模型辨识的目标
        """
        responses = {}
        
        # 这里应该调用圣维南模型进行计算
        # 简化实现：使用理论响应模拟
        time_array = test_data['time']
        dt = time_array[1] - time_array[0]
        
        for signal_name, signal_data in test_data.items():
            if signal_name in ['time', 'equilibrium']:
                continue
                
            # 模拟理论响应（实际应用中应调用圣维南模型）
            if 'step' in signal_name:
                # 阶跃响应：一阶系统响应
                tau_sim = 300.0  # 模拟时间常数
                response = signal_data[0] * (1 - np.exp(-time_array / tau_sim))
                
                # 添加延迟
                if 'up' in signal_name:
                    delay_steps = int(60 / dt)  # 1分钟延迟
                else:
                    delay_steps = int(300 / dt)  # 5分钟延迟
                
                delayed_response = np.zeros_like(response)
                if delay_steps < len(response):
                    delayed_response[delay_steps:] = response[:-delay_steps]
                
                response = delayed_response
                
            elif 'impulse' in signal_name:
                # 脉冲响应：衰减振荡
                tau_decay = 400.0
                omega = 0.01  # 振荡频率
                
                response = np.zeros_like(time_array)
                pulse_idx = np.where(signal_data > 0)[0]
                if len(pulse_idx) > 0:
                    t_response = time_array[pulse_idx[0]:] - time_array[pulse_idx[0]]
                    impulse_response = np.exp(-t_response / tau_decay) * np.cos(omega * t_response)
                    response[pulse_idx[0]:pulse_idx[0]+len(impulse_response)] = impulse_response * signal_data[pulse_idx[0]]
                
            else:  # ramp
                # 斜坡响应：积分特性
                response = np.cumsum(signal_data) * dt / 100.0
            
            responses[signal_name] = response
        
        return responses
    
    def _optimize_parameters(self, test_data: Dict[str, np.ndarray],
                           reference_responses: Dict[str, np.ndarray],
                           equilibrium_point: Dict[str, float]) -> IDZModelParameters:
        """
        优化IDZ参数
        
        使用优化算法寻找最佳的四方程IDZ参数
        """
        # 定义参数边界
        tau_min, tau_max = self.config.tau_bounds
        T_min, T_max = self.config.T_bounds
        alpha_min, alpha_max = self.config.alpha_bounds
        
        bounds = [
            (tau_min, tau_max),    # tau11
            (T_min, T_max),        # T11
            (alpha_min, alpha_max), # alpha11
            (tau_min, tau_max),    # tau12
            (T_min, T_max),        # T12
            (alpha_min, alpha_max), # alpha12
            (tau_min, tau_max),    # tau21
            (T_min, T_max),        # T21
            (alpha_min, alpha_max), # alpha21
            (tau_min, tau_max),    # tau22
            (T_min, T_max),        # T22
            (alpha_min, alpha_max)  # alpha22
        ]
        
        # 目标函数
        def objective_function(params):
            try:
                # 构建参数对象
                idz_params = IDZModelParameters(
                    tau11=params[0], T11=params[1], alpha11=params[2],
                    tau12=params[3], T12=params[4], alpha12=params[4],
                    tau21=params[6], T21=params[7], alpha21=params[8],
                    tau22=params[9], T22=params[10], alpha22=params[11]
                )
                
                # 计算模型响应
                model_responses = self._simulate_idz_responses(idz_params, test_data, equilibrium_point)
                
                # 计算误差
                total_error = 0.0
                count = 0
                
                for signal_name in reference_responses:
                    if signal_name in model_responses:
                        ref_response = reference_responses[signal_name]
                        model_response = model_responses[signal_name]
                        
                        # 确保长度匹配
                        min_len = min(len(ref_response), len(model_response))
                        ref_response = ref_response[:min_len]
                        model_response = model_response[:min_len]
                        
                        # 计算均方根误差
                        mse = np.mean((ref_response - model_response) ** 2)
                        total_error += mse
                        count += 1
                
                return total_error / count if count > 0 else 1e6
                
            except Exception as e:
                self.logger.warning(f"参数评估失败: {e}")
                return 1e6
        
        # 执行优化
        if self.config.optimization_method == 'differential_evolution':
            result = differential_evolution(
                objective_function,
                bounds,
                seed=42,
                maxiter=self.config.max_iterations,
                popsize=self.config.population_size,
                tol=self.config.tolerance
            )
        else:
            # 使用scipy.minimize
            x0 = [(b[0] + b[1]) / 2 for b in bounds]  # 初始值设为边界中点
            result = minimize(
                objective_function,
                x0,
                bounds=bounds,
                method='L-BFGS-B',
                options={'maxiter': self.config.max_iterations}
            )
        
        if not result.success:
            self.logger.warning(f"参数优化未收敛: {result.message}")
        
        # 构建最优参数
        optimal_params = IDZModelParameters(
            tau11=result.x[0], T11=result.x[1], alpha11=result.x[2],
            tau12=result.x[3], T12=result.x[4], alpha12=result.x[5],
            tau21=result.x[6], T21=result.x[7], alpha21=result.x[8],
            tau22=result.x[9], T22=result.x[10], alpha22=result.x[11]
        )
        
        self.logger.info(f"参数优化完成，最终误差: {result.fun:.6f}")
        
        return optimal_params
    
    def _simulate_idz_responses(self, params: IDZModelParameters,
                              test_data: Dict[str, np.ndarray],
                              equilibrium_point: Dict[str, float]) -> Dict[str, np.ndarray]:
        """
        模拟IDZ模型响应
        
        基于给定参数计算四方程IDZ模型对测试信号的响应
        """
        responses = {}
        time_array = test_data['time']
        dt = time_array[1] - time_array[0]
        
        # 为每个传递函数创建离散化系统
        transfer_functions = {
            'G11': params.get_transfer_function_params('G11'),
            'G12': params.get_transfer_function_params('G12'),
            'G21': params.get_transfer_function_params('G21'),
            'G22': params.get_transfer_function_params('G22')
        }
        
        for signal_name, signal_data in test_data.items():
            if signal_name in ['time', 'equilibrium']:
                continue
            
            # 简化的IDZ响应计算
            tau, T, alpha = transfer_functions['G11']  # 使用G11作为示例
            
            # 离散化传递函数（简化）
            if alpha > 0:
                # 一阶惯性环节的离散化
                a = np.exp(-dt / alpha)
                b = (1 - a) / alpha * tau
                
                # 添加延迟
                delay_steps = int(T / dt)
                
                # 数字滤波实现
                response = np.zeros_like(signal_data)
                delayed_input = np.zeros_like(signal_data)
                
                # 应用延迟
                if delay_steps < len(signal_data):
                    delayed_input[delay_steps:] = signal_data[:-delay_steps]
                
                # 递归滤波
                y_prev = 0.0
                for i in range(len(delayed_input)):
                    response[i] = a * y_prev + b * delayed_input[i]
                    y_prev = response[i]
                
                responses[signal_name] = response
        
        return responses
    
    def _validate_parameters(self, params: IDZModelParameters):
        """验证参数的物理合理性"""
        # 检查因果性约束
        if self.config.enforce_causality:
            if params.T11 < 0 or params.T12 < 0 or params.T21 < 0 or params.T22 < 0:
                raise ValueError("延迟时间不能为负（违反因果性）")
        
        # 检查稳定性约束
        if self.config.enforce_stability:
            if (params.alpha11 <= 0 or params.alpha12 <= 0 or 
                params.alpha21 <= 0 or params.alpha22 <= 0):
                raise ValueError("极点时间常数必须为正（保证稳定性）")
        
        # 物理合理性检查
        if params.T21 <= params.T12:
            warnings.warn("正向传播延迟T21通常应大于回水延迟T12")
    
    def _record_identification_history(self, interval: FlowStageInterval,
                                     params: IDZModelParameters,
                                     reference_responses: Dict[str, np.ndarray]):
        """记录辨识历史"""
        history_entry = {
            'interval_id': interval.interval_id,
            'parameters': params.to_dict(),
            'timestamp': np.datetime64('now').astype(int),
            'response_quality': self._assess_response_quality(reference_responses)
        }
        
        self._identification_history.append(history_entry)
    
    def _assess_response_quality(self, responses: Dict[str, np.ndarray]) -> float:
        """评估响应质量"""
        # 简化的质量评估：基于响应的平滑度和收敛性
        total_quality = 0.0
        count = 0
        
        for signal_name, response in responses.items():
            if len(response) > 1:
                # 计算响应的平滑度（方差）
                smoothness = 1.0 / (1.0 + np.var(np.diff(response)))
                
                # 计算收敛性（最后10%的标准差）
                end_portion = response[int(0.9 * len(response)):]
                convergence = 1.0 / (1.0 + np.std(end_portion))
                
                quality = (smoothness + convergence) / 2.0
                total_quality += quality
                count += 1
        
        return total_quality / count if count > 0 else 0.0
    
    def get_identification_history(self) -> List[Dict]:
        """获取辨识历史"""
        return self._identification_history.copy()
    
    def clear_cache(self):
        """清空缓存"""
        self._parameter_cache.clear()
        self.logger.debug("参数缓存已清空")


__all__ = ['IDZLinearizer', 'IDZLinearizationConfig']