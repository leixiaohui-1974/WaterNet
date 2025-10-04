"""
马斯京干-康吉模型实现

基于扩散波理论的马斯京干-康吉方法，参数可从河道物理特性自动计算。

Author: WaterNet Development Team
Date: 2024-10-04
"""

import numpy as np
import warnings
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from waternet.models.lumped_models import BaseLumpedModel


@dataclass
class ChannelGeometry:
    """河道几何参数"""
    length: float          # 河段长度 (m)
    width: float           # 河道宽度 (m)
    slope: float           # 河底坡度
    roughness: float       # 曼宁粗糙系数
    side_slope: float = 0.0  # 边坡坡度 (垂直:水平), 0为矩形


@dataclass
class FlowConditions:
    """水流条件参数"""
    reference_discharge: float  # 参考流量 (m³/s)
    reference_depth: Optional[float] = None  # 参考水深 (m)
    reference_velocity: Optional[float] = None  # 参考流速 (m/s)


class HydraulicCalculator:
    """水力学计算器"""
    
    @staticmethod
    def compute_normal_depth(Q: float, B: float, S: float, n: float, 
                           m: float = 0.0) -> float:
        """
        计算正常水深
        
        Args:
            Q: 流量 (m³/s)
            B: 底宽 (m)
            S: 坡度
            n: 曼宁系数
            m: 边坡坡度
            
        Returns:
            正常水深 (m)
        """
        # 对于矩形断面：h = (Q*n/(B*sqrt(S)))^(3/5)
        if m == 0.0:  # 矩形断面
            return (Q * n / (B * np.sqrt(S))) ** (3.0/5.0)
        else:
            # 梯形断面需要迭代求解，这里用简化公式
            h_rect = (Q * n / (B * np.sqrt(S))) ** (3.0/5.0)
            return h_rect * 0.95  # 近似修正
    
    @staticmethod
    def compute_hydraulic_parameters(h: float, B: float, m: float = 0.0) -> Dict[str, float]:
        """
        计算水力要素
        
        Args:
            h: 水深 (m)
            B: 底宽 (m)
            m: 边坡坡度
            
        Returns:
            水力要素字典
        """
        if m == 0.0:  # 矩形断面
            A = B * h  # 过水断面积
            P = B + 2 * h  # 湿周
            R = A / P  # 水力半径
            T = B  # 水面宽度
        else:  # 梯形断面
            A = (B + m * h) * h
            P = B + 2 * h * np.sqrt(1 + m**2)
            R = A / P
            T = B + 2 * m * h
        
        return {
            'area': A,
            'wetted_perimeter': P,
            'hydraulic_radius': R,
            'top_width': T
        }
    
    @staticmethod
    def compute_wave_celerity(Q: float, A: float, T: float) -> float:
        """
        计算波速
        
        Args:
            Q: 流量 (m³/s)
            A: 断面积 (m²)
            T: 水面宽度 (m)
            
        Returns:
            波速 (m/s)
        """
        # c = dQ/dA ≈ (5/3) * V  (对于宽浅河道)
        V = Q / A if A > 0 else 0.0
        return (5.0/3.0) * V


class CungeParameterCalculator:
    """康吉参数计算器"""
    
    @staticmethod
    def compute_cunge_parameters(geometry: ChannelGeometry, 
                               flow: FlowConditions) -> Dict[str, float]:
        """
        计算康吉法参数
        
        Args:
            geometry: 河道几何参数
            flow: 水流条件参数
            
        Returns:
            康吉参数字典
        """
        Q = flow.reference_discharge
        
        # 计算正常水深
        h = HydraulicCalculator.compute_normal_depth(
            Q, geometry.width, geometry.slope, geometry.roughness, 0.0)
        
        # 计算水力要素
        hydraulics = HydraulicCalculator.compute_hydraulic_parameters(
            h, geometry.width, 0.0)
        
        A = hydraulics['area']
        T = hydraulics['top_width']
        
        # 计算波速
        c = HydraulicCalculator.compute_wave_celerity(Q, A, T)
        
        # 康吉参数公式
        K = geometry.length / c if c > 0 else 3600.0
        
        # x的计算需要保证物理合理性
        denominator = geometry.width * geometry.slope * c * geometry.length
        if denominator > 0:
            x = 0.5 * (1 - Q / denominator)
            # 确保x在合理范围内
            x = max(0.0, min(0.5, x))
        else:
            x = 0.2  # 默认值
        
        return {
            'K': K,
            'x': x,
            'normal_depth': h,
            'wave_celerity': c,
            'cross_sectional_area': A,
            'flow_velocity': Q / A if A > 0 else 0.0
        }


class MuskingumCungeModel(BaseLumpedModel):
    """
    马斯京干-康吉模型
    
    基于扩散波理论的马斯京干模型，参数可从河道物理特性自动计算。
    
    特点:
    - 参数K和x基于河道物理特性计算
    - 具有明确的水力学理论基础
    - 支持自适应参数调整
    - 兼容传统马斯京干公式
    """
    
    def __init__(self, dt: float, 
                 geometry: ChannelGeometry,
                 flow_conditions: FlowConditions,
                 initial_V: float,
                 V_to_H_func: Callable[[float], float],
                 H_to_Q_func: Callable[[float], float],
                 name: str = "MuskingumCunge",
                 enable_adaptive_parameters: bool = False,
                 manual_K: Optional[float] = None,
                 manual_x: Optional[float] = None):
        """
        初始化马斯京干-康吉模型
        
        Args:
            dt: 时间步长（秒）
            geometry: 河道几何参数
            flow_conditions: 水流条件参数
            initial_V: 初始蓄水量（m³）
            V_to_H_func: 蓄量-水位关系函数
            H_to_Q_func: 水位-出流关系函数
            name: 模型名称
            enable_adaptive_parameters: 是否启用自适应参数
            manual_K: 手动指定K值（可选）
            manual_x: 手动指定x值（可选）
        """
        super().__init__(dt, initial_V, V_to_H_func, H_to_Q_func, name)
        
        self.geometry = geometry
        self.flow_conditions = flow_conditions
        self.enable_adaptive = enable_adaptive_parameters
        
        # 计算康吉参数
        if manual_K is not None and manual_x is not None:
            # 使用手动指定的参数（兼容传统模式）
            self.K = manual_K
            self.x = manual_x
            self.cunge_params = {'K': manual_K, 'x': manual_x}
            print(f"使用手动参数: K={manual_K:.1f}s, x={manual_x:.3f}")
        else:
            # 使用康吉法自动计算参数
            self.cunge_params = CungeParameterCalculator.compute_cunge_parameters(
                geometry, flow_conditions)
            self.K = self.cunge_params['K']
            self.x = self.cunge_params['x']
            print(f"康吉法计算参数: K={self.K:.1f}s, x={self.x:.3f}")
        
        # 参数验证
        if self.K <= 0:
            warnings.warn(f"K值异常: {self.K:.3f}, 使用默认值")
            self.K = 3600.0
        if not 0 <= self.x <= 0.5:
            warnings.warn(f"x值异常: {self.x:.3f}, 使用默认值")
            self.x = 0.2
        
        # 计算马斯京干系数
        self._compute_muskingum_coefficients()
        
        # 历史变量
        self.Q_in_prev = 0.0
        self.Q_out_prev = self.current_Q_out
        
        # 自适应参数相关
        self.parameter_update_interval = 10  # 每10步更新一次参数
        self.step_count = 0
    
    def _compute_muskingum_coefficients(self):
        """计算马斯京干系数"""
        denominator = self.K - self.K * self.x + 0.5 * self.dt
        
        if abs(denominator) < 1e-10:
            raise ValueError("马斯京干系数计算中分母接近零")
        
        self.C0 = (-self.K * self.x + 0.5 * self.dt) / denominator
        self.C1 = (self.K * self.x + 0.5 * self.dt) / denominator
        self.C2 = (self.K - self.K * self.x - 0.5 * self.dt) / denominator
        
        # 验证系数和为1
        coeff_sum = self.C0 + self.C1 + self.C2
        if abs(coeff_sum - 1.0) > 1e-6:
            warnings.warn(f"马斯京干系数和不为1: {coeff_sum}")
    
    def _update_adaptive_parameters(self, current_Q: float):
        """自适应参数更新"""
        if not self.enable_adaptive:
            return
        
        # 更新参考流量
        self.flow_conditions.reference_discharge = current_Q
        
        # 重新计算康吉参数
        new_params = CungeParameterCalculator.compute_cunge_parameters(
            self.geometry, self.flow_conditions)
        
        # 平滑更新参数（避免突变）
        alpha = 0.1  # 更新权重
        self.K = (1 - alpha) * self.K + alpha * new_params['K']
        self.x = (1 - alpha) * self.x + alpha * new_params['x']
        
        # 确保参数合理性
        self.K = max(self.dt, self.K)
        self.x = max(0.0, min(0.5, self.x))
        
        # 重新计算系数
        self._compute_muskingum_coefficients()
    
    def step(self, Q_in: float) -> Dict[str, float]:
        """
        模型时步推进
        
        Args:
            Q_in: 入流量
            
        Returns:
            仿真结果字典
        """
        self.step_count += 1
        
        # 自适应参数更新
        if (self.step_count % self.parameter_update_interval == 0):
            self._update_adaptive_parameters(Q_in)
        
        # 马斯京干公式计算
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
            'K': self.K,
            'x': self.x,
            'C0': self.C0,
            'C1': self.C1,
            'C2': self.C2,
            'normal_depth': self.cunge_params.get('normal_depth', 0.0),
            'wave_celerity': self.cunge_params.get('wave_celerity', 0.0)
        }
    
    def reset(self, new_initial_V: Optional[float] = None):
        """重置模型状态"""
        super().reset(new_initial_V)
        self.Q_in_prev = 0.0
        self.Q_out_prev = self.current_Q_out
        self.step_count = 0
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            'model_type': 'Muskingum-Cunge',
            'geometry': {
                'length': self.geometry.length,
                'width': self.geometry.width,
                'slope': self.geometry.slope,
                'roughness': self.geometry.roughness
            },
            'computed_parameters': self.cunge_params,
            'current_parameters': {
                'K': self.K,
                'x': self.x
            },
            'muskingum_coefficients': {
                'C0': self.C0,
                'C1': self.C1,
                'C2': self.C2
            },
            'adaptive_enabled': self.enable_adaptive
        }


# 便捷创建函数
def create_cunge_model_from_geometry(
    dt: float,
    length: float,
    width: float,
    slope: float,
    roughness: float,
    reference_discharge: float,
    initial_V: float,
    V_to_H_func: Callable[[float], float],
    H_to_Q_func: Callable[[float], float],
    **kwargs
) -> MuskingumCungeModel:
    """
    从河道几何参数创建康吉模型的便捷函数
    
    Args:
        dt: 时间步长
        length: 河段长度
        width: 河道宽度
        slope: 河底坡度
        roughness: 曼宁粗糙系数
        reference_discharge: 参考流量
        initial_V: 初始蓄水量
        V_to_H_func: 蓄量-水位函数
        H_to_Q_func: 水位-出流函数
        **kwargs: 其他参数
        
    Returns:
        配置好的康吉模型
    """
    geometry = ChannelGeometry(
        length=length,
        width=width,
        slope=slope,
        roughness=roughness
    )
    
    flow_conditions = FlowConditions(
        reference_discharge=reference_discharge
    )
    
    return MuskingumCungeModel(
        dt=dt,
        geometry=geometry,
        flow_conditions=flow_conditions,
        initial_V=initial_V,
        V_to_H_func=V_to_H_func,
        H_to_Q_func=H_to_Q_func,
        **kwargs
    )