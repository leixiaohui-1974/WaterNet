"""
PressurizedPipeROM 有压管道降阶模型

基于BaseLumpedModel框架的有压管道降阶模型集合。
支持多种降阶模型类型，包括线性化水锤模型、水锤马斯京干模型等。

特点:
- 完全继承BaseLumpedModel的成熟架构
- 利用Q-H耦合蓄水量理论，支持更精确的物理关系
- 统一的step()仿真接口和状态管理
- 支持不同复杂度的降阶模型

Author: WaterNet Development Team
Date: 2024-10-04
"""

import numpy as np
import pandas as pd
import warnings
from abc import ABC, abstractmethod
from typing import Dict, List, Callable, Optional, Union, Any
from scipy import signal
from scipy.integrate import odeint

from .lumped_models import BaseLumpedModel


class PressurizedPipeROM(BaseLumpedModel):
    """
    有压管道降阶模型基类
    
    基于BaseLumpedModel框架，为有压管道系统提供统一的降阶模型接口。
    支持多种模型类型的无缝切换和参数更新。
    
    Attributes:
        model_type (str): 模型类型标识
        physical_params (Dict): 物理参数字典
        L (float): 管道长度 (m)
        D (float): 管道直径 (m)
        a (float): 水锤波速 (m/s)
        f (float): 达西摩擦系数
        A (float): 管道截面积 (m²)
    """
    
    def __init__(self, model_type: str, physical_params: Dict[str, float],
                 dt: float, initial_conditions: Dict[str, float], 
                 name: str = "PressurizedPipeROM"):
        """
        初始化有压管道降阶模型基类
        
        Args:
            model_type (str): 模型类型 ('linear_hammer', 'muskingum_hammer', 'transfer_function')
            physical_params (Dict): 物理参数字典，包含:
                - 'L': 管道长度 (m)
                - 'D': 管道直径 (m) 
                - 'a': 水锤波速 (m/s)
                - 'f': 达西摩擦系数
            dt (float): 时间步长 (s)
            initial_conditions (Dict): 初始条件，包含:
                - 'H_initial': 初始水位 (m)
                - 'Q_initial': 初始流量 (m³/s)
                - 'V_initial': 初始蓄水量 (m³)
            name (str): 模型名称
            
        Raises:
            ValueError: 当参数不合理时
        """
        # 验证物理参数
        required_params = ['L', 'D', 'a', 'f']
        for param in required_params:
            if param not in physical_params:
                raise ValueError(f"缺少必需的物理参数: {param}")
            if physical_params[param] <= 0:
                raise ValueError(f"物理参数{param}必须为正值，得到: {physical_params[param]}")
        
        # 验证初始条件
        required_initial = ['H_initial', 'Q_initial', 'V_initial']
        for param in required_initial:
            if param not in initial_conditions:
                raise ValueError(f"缺少必需的初始条件: {param}")
        
        # 提取物理参数
        self.model_type = model_type
        self.physical_params = physical_params.copy()
        self.L = physical_params['L']
        self.D = physical_params['D']
        self.a = physical_params['a']
        self.f = physical_params['f']
        self.A = np.pi * (self.D / 2.0) ** 2
        
        # 初始条件
        H_initial = initial_conditions['H_initial']
        Q_initial = initial_conditions['Q_initial']
        V_initial = initial_conditions['V_initial']
        
        # 创建简化的V-H和H-Q关系函数
        V_to_H_func = self._create_V_to_H_function(H_initial, V_initial)
        H_to_Q_func = self._create_H_to_Q_function(H_initial, Q_initial)
        QH_to_V_func = self._create_QH_to_V_function(Q_initial, H_initial, V_initial)
        
        # 初始化基类
        super().__init__(
            dt=dt,
            initial_V=V_initial,
            V_to_H_func=V_to_H_func,
            H_to_Q_func=H_to_Q_func,
            name=name,
            QH_to_V_func=QH_to_V_func
        )\n        
        # 模型特定的初始化
        self._initialize_model_specific_components()
        
        # 线性化工作点
        self.Q_op = Q_initial
        self.H_op = H_initial
        self.linearized = False
        
        print(f"有压管道降阶模型'{name}'初始化完成:")
        print(f"  模型类型: {model_type}")
        print(f"  管道长度: {self.L} m")
        print(f"  管道直径: {self.D} m") 
        print(f"  波速: {self.a} m/s")
        print(f"  摩擦系数: {self.f}")
    
    def _create_V_to_H_function(self, H_ref: float, V_ref: float) -> Callable[[float], float]:
        """创建蓄量-水位关系函数"""
        # 简化的线性关系：H = H_ref + (V - V_ref) / C
        # 其中C是蓄量系数，基于管道几何估算
        C = self.A * self.L / 10.0  # 简化系数
        
        def V_to_H(V: float) -> float:
            return H_ref + (V - V_ref) / C
        
        return V_to_H
    
    def _create_H_to_Q_function(self, H_ref: float, Q_ref: float) -> Callable[[float], float]:
        """创建水位-出流关系函数"""
        # 简化的线性关系：Q = Q_ref + k * (H - H_ref)
        # 其中k是基于管道阻力特性的系数
        k = Q_ref / max(0.1, H_ref)  # 简化系数
        
        def H_to_Q(H: float) -> float:
            return max(0.0, Q_ref + k * (H - H_ref))
        
        return H_to_Q
    
    def _create_QH_to_V_function(self, Q_ref: float, H_ref: float, 
                                V_ref: float) -> Callable[[float, float], float]:
        """创建Q-H耦合的蓄量关系函数"""
        # 考虑流量对蓄量的影响：V = V_base(H) * (1 + α * ΔQ/Q_ref)
        alpha = 0.1  # 耦合系数
        
        def QH_to_V(Q: float, H: float) -> float:
            # 基础蓄量（仅依赖水位）
            V_base = V_ref + self.A * (H - H_ref)
                        
            # 流量修正项
            if abs(Q_ref) > 1e-6:
                Q_correction = alpha * (Q - Q_ref) / Q_ref
            else:
                Q_correction = 0.0
            
            # 最终蓄量
            V = V_base * (1 + Q_correction)
            return max(0.0, V)
        
        return QH_to_V
    
    def _initialize_model_specific_components(self):
        """初始化模型特定组件（由子类实现）"""
        # 基类提供默认实现，子类可以重写
        self.model_parameters = {}
        self.internal_states = {}
        pass
    
    def linearize_around_operating_point(self, Q_op: float, H_op: float):
        """
        在指定工作点附近线性化
        
        Args:
            Q_op (float): 工作点流量 (m³/s)
            H_op (float): 工作点水位 (m)
        """
        self.Q_op = Q_op
        self.H_op = H_op
        self.linearized = True
        
        # 子类可以重写此方法以实现具体的线性化逻辑
        self._compute_linearized_parameters()
        
        print(f"模型已在工作点(Q={Q_op:.3f}, H={H_op:.3f})附近线性化")
    
    def _compute_linearized_parameters(self):
        """计算线性化参数（由子类实现）"""
        pass
    
    def update_parameters(self, new_params: Dict[str, float]):
        """
        更新模型参数
        
        Args:
            new_params (Dict[str, float]): 新参数字典
        """
        # 更新物理参数
        for key, value in new_params.items():
            if key in self.physical_params:
                self.physical_params[key] = value
                setattr(self, key, value)
        
        # 更新模型特定参数
        self.model_parameters.update(new_params)
        
        # 重新计算派生参数
        if hasattr(self, 'D'):
            self.A = np.pi * (self.D / 2.0) ** 2
        
        # 如果已线性化，需要重新线性化
        if self.linearized:
            self._compute_linearized_parameters()
        
        print(f"参数更新完成: {new_params}")
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        获取模型信息
        
        Returns:
            Dict[str, Any]: 模型信息字典
        """
        return {
            'model_type': self.model_type,
            'physical_params': self.physical_params,
            'model_parameters': getattr(self, 'model_parameters', {}),
            'linearized': self.linearized,
            'operating_point': {'Q_op': self.Q_op, 'H_op': self.H_op} if self.linearized else None,
            'current_state': self.get_current_state()
        }
    
    @abstractmethod
    def step(self, Q_in: float) -> Dict[str, float]:
        """
        执行一个时间步的仿真（抽象方法，由具体模型实现）
        
        Args:
            Q_in (float): 入流量 (m³/s)
            
        Returns:
            Dict[str, float]: 仿真结果字典
        """
        pass


class LinearHammerModel(PressurizedPipeROM):
    """
    线性化水锤模型
    
    基于传递函数的线性化水锤模型，适用于小扰动条件。
    传递函数形式：G(s) = (τ₁s² + τ₂s + 1) / (α₁s² + α₂s + 1)
    
    特点:
    - 基于频域分析的线性化处理
    - 适用于小扰动和稳态附近的分析
    - 计算效率高，数值稳定性好
    """
    
    def __init__(self, physical_params: Dict[str, float], dt: float,
                 initial_conditions: Dict[str, float], name: str = "LinearHammerModel"):
        """初始化线性化水锤模型"""
        super().__init__('linear_hammer', physical_params, dt, initial_conditions, name)
    
    def _initialize_model_specific_components(self):
        """初始化传递函数参数"""
        # 基于物理参数计算传递函数系数
        self._compute_transfer_function_parameters()
        
        # 初始化状态空间表示
        self._setup_state_space_representation()
    
    def _compute_transfer_function_parameters(self):
        """计算传递函数参数"""
        # 精确传递函数的有理分式近似
        # G(s) = (τ₁s² + τ₂s + 1) / (α₁s² + α₂s + 1)
        
        # 零点参数
        tau1 = self.L**2 / (6 * self.a**2)
        tau2 = self.f * self.L / (2 * self.D * self.a)
        
        # 极点参数
        alpha1 = self.L**2 / (np.pi**2 * self.a**2)
        alpha2 = self.f * self.L / (self.D * self.a)
        
        self.model_parameters = {
            'tau1': tau1,
            'tau2': tau2,
            'alpha1': alpha1,
            'alpha2': alpha2
        }
        
        print(f"传递函数参数: τ1={tau1:.2e}, τ2={tau2:.2e}, α1={alpha1:.2e}, α2={alpha2:.2e}")
    
    def _setup_state_space_representation(self):
        """建立状态空间表示"""
        # 连续时间传递函数
        num = [self.model_parameters['tau1'], self.model_parameters['tau2'], 1.0]
        den = [self.model_parameters['alpha1'], self.model_parameters['alpha2'], 1.0]
        
        # 转换为状态空间形式
        self.continuous_system = signal.TransferFunction(num, den)
        
        # 离散化（零阶保持器）
        self.discrete_system = self.continuous_system.to_discrete(self.dt, method='zoh')
        
        # 提取离散化系数
        self.A_discrete = self.discrete_system.A
        self.B_discrete = self.discrete_system.B
        self.C_discrete = self.discrete_system.C
        self.D_discrete = self.discrete_system.D
        
        # 初始化状态向量
        self.state_vector = np.zeros(self.A_discrete.shape[0])
    
    def step(self, Q_in: float) -> Dict[str, float]:
        """
        线性化水锤模型的时步推进
        
        使用状态空间表示进行数值积分：
        x(k+1) = A*x(k) + B*u(k)
        y(k) = C*x(k) + D*u(k)
        
        Args:
            Q_in (float): 入流量扰动
            
        Returns:
            Dict[str, float]: 仿真结果
        """
        # 计算流量扰动（相对于工作点）
        if self.linearized:
            dQ_in = Q_in - self.Q_op
        else:
            dQ_in = Q_in
        
        # 状态空间更新
        input_vector = np.array([dQ_in])
        
        # 更新状态：x(k+1) = A*x(k) + B*u(k)
        self.state_vector = (self.A_discrete @ self.state_vector + 
                           self.B_discrete @ input_vector).flatten()
        
        # 计算输出：y(k) = C*x(k) + D*u(k)
        output_vector = (self.C_discrete @ self.state_vector + 
                        self.D_discrete @ input_vector).flatten()
        
        # 输出流量扰动
        dQ_out = output_vector[0] if len(output_vector) > 0 else 0.0
        
        # 转换为绝对值（加上工作点）
        if self.linearized:
            Q_out = self.Q_op + dQ_out
        else:
            Q_out = dQ_out
        
        # 确保流量非负
        Q_out = max(0.0, Q_out)
        
        # 更新物理状态
        Q_avg = (Q_in + Q_out) / 2.0
        self._update_physical_states(Q_in, Q_out)
        
        # 更新当前出流
        self.current_Q_out = Q_out
        
        # 记录状态
        self._record_state(Q_in)
        
        return {
            'Q_out': Q_out,
            'H_out': self.current_H,
            'V': self.current_V,
            'time': self.time,
            'dQ_in': dQ_in,
            'dQ_out': dQ_out,
            'state_norm': np.linalg.norm(self.state_vector)
        }


class MuskingumHammerModel(PressurizedPipeROM):
    """
    水锤马斯京干模型
    
    基于经典马斯京干模型扩展以适应压力波传播效应。
    考虑水锤波速和摩擦效应的修正马斯京干参数。
    
    特点:
    - 基于物理参数的自动参数计算
    - 考虑压力波传播和摩擦效应
    - 数值稳定性好，适用范围广
    """
    
    def __init__(self, physical_params: Dict[str, float], dt: float,
                 initial_conditions: Dict[str, float], name: str = "MuskingumHammerModel"):
        """初始化水锤马斯京干模型"""
        super().__init__('muskingum_hammer', physical_params, dt, initial_conditions, name)
    
    def _initialize_model_specific_components(self):
        """初始化马斯京干参数"""
        # 基于物理参数计算马斯京干参数
        self._compute_muskingum_parameters()
        
        # 计算马斯京干系数
        self._compute_muskingum_coefficients()
        
        # 初始化历史变量
        self.Q_in_prev = self.physical_params.get('Q_initial', 0.0)
        self.Q_out_prev = self.physical_params.get('Q_initial', 0.0)
    
    def _compute_muskingum_parameters(self):
        """计算有压管道的马斯京干参数"""
        # 传播时间：K = L/a（基于水锤波速）
        K = self.L / self.a
        
        # 权重系数：x = 0.5 - f*L/(4*D*a)（考虑摩擦效应）
        x = 0.5 - (self.f * self.L) / (4 * self.D * self.a)
        x = np.clip(x, 0.0, 0.5)  # 确保在合理范围内
        
        self.model_parameters = {
            'K': K,
            'x': x
        }
        
        print(f"马斯京干参数: K={K:.1f}s, x={x:.3f}")
    
    def _compute_muskingum_coefficients(self):
        """计算马斯京干系数"""
        K = self.model_parameters['K']
        x = self.model_parameters['x']
        
        denominator = K - K * x + 0.5 * self.dt
        
        if abs(denominator) < 1e-10:
            warnings.warn("马斯京干系数计算中分母接近零，使用简化系数")
            self.C0 = 0.0
            self.C1 = 1.0
            self.C2 = 0.0
        else:
            self.C0 = (-K * x + 0.5 * self.dt) / denominator
            self.C1 = (K * x + 0.5 * self.dt) / denominator
            self.C2 = (K - K * x - 0.5 * self.dt) / denominator
        
        # 验证系数和
        coeff_sum = self.C0 + self.C1 + self.C2
        if abs(coeff_sum - 1.0) > 1e-6:
            warnings.warn(f"马斯京干系数和不为1: {coeff_sum}")
        
        print(f"马斯京干系数: C0={self.C0:.3f}, C1={self.C1:.3f}, C2={self.C2:.3f}")
    
    def step(self, Q_in: float) -> Dict[str, float]:
        """
        水锤马斯京干模型的时步推进
        
        使用修正的马斯京干公式：
        Q_out = C0*Q_in + C1*Q_in_prev + C2*Q_out_prev
        
        Args:
            Q_in (float): 入流量
            
        Returns:
            Dict[str, float]: 仿真结果
        """
        # 马斯京干公式
        Q_out = (self.C0 * Q_in + 
                self.C1 * self.Q_in_prev + 
                self.C2 * self.Q_out_prev)
        
        # 数值保护
        Q_out = max(0.0, Q_out)
        
        # 更新物理状态
        Q_in_avg = (Q_in + self.Q_in_prev) / 2.0
        Q_out_avg = (Q_out + self.Q_out_prev) / 2.0
        self._update_physical_states(Q_in_avg, Q_out_avg)
        
        # 更新历史变量
        self.Q_in_prev = Q_in
        self.Q_out_prev = Q_out
        self.current_Q_out = Q_out
        
        # 记录状态
        self._record_state(Q_in)
        
        return {
            'Q_out': Q_out,
            'H_out': self.current_H,
            'V': self.current_V,
            'time': self.time,
            'C0': self.C0,
            'C1': self.C1,
            'C2': self.C2,
            'K': self.model_parameters['K'],
            'x': self.model_parameters['x']
        }


class ElasticPipeModel(PressurizedPipeROM):
    """
    弹性管道模型
    
    考虑管道弹性变形效应的降阶模型，基于延迟-扩散传递函数。
    适用于长期仿真和复杂边界条件。
    
    传递函数形式：G(s) = K(1 + τ₁s)e^(-Ts) / (1 + α₁s)(1 + α₂s)
    
    特点:
    - 考虑管道弹性变形
    - 支持延迟和扩散效应
    - 数值稳定性好，适合长期计算
    """
    
    def __init__(self, physical_params: Dict[str, float], dt: float,
                 initial_conditions: Dict[str, float], name: str = "ElasticPipeModel"):
        """初始化弹性管道模型"""
        super().__init__('elastic_pipe', physical_params, dt, initial_conditions, name)
    
    def _initialize_model_specific_components(self):
        """初始化弹性管道参数"""
        # 基于物理参数计算传递函数参数
        self._compute_elastic_parameters()
        
        # 设置延迟缓冲区
        self._setup_delay_buffer()
    
    def _compute_elastic_parameters(self):
        """计算弹性管道参数"""
        # 稳态增益
        K = 1.0
        
        # 传播延迟
        T_delay = self.L / self.a
        
        # 零点时间常数（影响超调特性）
        tau1 = self.f * self.L / (4 * self.D * self.a)
        
        # 极点时间常数（影响整体动态）
        alpha1 = self.L / (2 * self.a)
        alpha2 = self.f * self.L / (self.D * self.a)
        
        self.model_parameters = {
            'K': K,
            'T_delay': T_delay,
            'tau1': tau1,
            'alpha1': alpha1,
            'alpha2': alpha2
        }
        
        print(f"弹性管道参数: K={K}, T={T_delay:.1f}s, τ1={tau1:.2f}s")
    
    def _setup_delay_buffer(self):
        """设置延迟缓冲区"""
        T_delay = self.model_parameters['T_delay']
        delay_steps = int(np.ceil(T_delay / self.dt))
        self.delay_buffer = [0.0] * max(1, delay_steps)
        
        # 内部状态（用于传递函数的极点）
        self.internal_state1 = 0.0
        self.internal_state2 = 0.0
    
    def step(self, Q_in: float) -> Dict[str, float]:
        """
        弹性管道模型的时步推进
        
        使用延迟-扩散传递函数处理：
        G(s) = K(1 + τ₁s)e^(-Ts) / (1 + α₁s)(1 + α₂s)
        
        Args:
            Q_in (float): 入流量
            
        Returns:
            Dict[str, float]: 仿真结果
        """
        # 延迟处理
        delayed_input = self.delay_buffer[0]
        self.delay_buffer = self.delay_buffer[1:] + [Q_in]
        
        # 零点处理 (1 + τ₁s)
        tau1 = self.model_parameters['tau1']
        zero_output = delayed_input + tau1 * (Q_in - delayed_input) / self.dt
        
        # 第一个极点处理 (1 + α₁s)
        alpha1 = self.model_parameters['alpha1']
        a1 = np.exp(-self.dt / alpha1)
        self.internal_state1 = a1 * self.internal_state1 + (1 - a1) * zero_output
        
        # 第二个极点处理 (1 + α₂s)
        alpha2 = self.model_parameters['alpha2']
        a2 = np.exp(-self.dt / alpha2)
        self.internal_state2 = a2 * self.internal_state2 + (1 - a2) * self.internal_state1
        
        # 应用增益
        K = self.model_parameters['K']
        Q_out = K * self.internal_state2
        
        # 数值保护
        Q_out = max(0.0, Q_out)
        
        # 更新物理状态
        self._update_physical_states(Q_in, Q_out)
        
        # 更新当前出流
        self.current_Q_out = Q_out
        
        # 记录状态
        self._record_state(Q_in)
        
        return {
            'Q_out': Q_out,
            'H_out': self.current_H,
            'V': self.current_V,
            'time': self.time,
            'delayed_input': delayed_input,
            'internal_state1': self.internal_state1,
            'internal_state2': self.internal_state2
        }


def create_pressurized_pipe_rom(model_type: str, physical_params: Dict[str, float],
                               dt: float, initial_conditions: Dict[str, float],
                               name: str = None) -> PressurizedPipeROM:
    """
    创建有压管道降阶模型的工厂函数
    
    Args:
        model_type (str): 模型类型
        physical_params (Dict): 物理参数
        dt (float): 时间步长
        initial_conditions (Dict): 初始条件
        name (str): 模型名称
        
    Returns:
        PressurizedPipeROM: 相应的降阶模型实例
        
    Raises:
        ValueError: 当模型类型不支持时
    """
    if name is None:
        name = f"{model_type.title()}Model"
    
    model_classes = {
        'linear_hammer': LinearHammerModel,
        'muskingum_hammer': MuskingumHammerModel,
        'elastic_pipe': ElasticPipeModel
    }
    
    if model_type not in model_classes:
        raise ValueError(f"不支持的模型类型: {model_type}. 支持的类型: {list(model_classes.keys())}")
    
    model_class = model_classes[model_type]
    return model_class(physical_params, dt, initial_conditions, name)