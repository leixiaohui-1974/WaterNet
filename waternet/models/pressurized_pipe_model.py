"""
有压管道模型

实现基于达西-韦茨巴赫公式的有压管道水力计算模型。
支持管道水头损失计算和流量-水位关系的联合求解。

设计原理:
1. 达西-韦茨巴赫公式：hf = f × (L/D) × (V²/2g)
2. 连续性方程：Q = A × V
3. 能量方程：H_up - H_down = hf + hm（包含局部损失）

变量定义:
- Q_{管道名}: 管道流量 (m³/s)
- V_{管道名}: 管道流速 (m/s) [中间变量]
- hf_{管道名}: 沿程损失 (m) [中间变量]

Author: WaterNet Development Team
Date: 2024-10-04
"""

import math
from typing import Dict, List, Optional, Any, Union
from ..interfaces.hydro_model import HydroModel


class PressurizedPipeModel(HydroModel):
    """
    有压管道模型
    
    基于达西-韦茨巴赫公式的有压管道水力计算模型。
    考虑沿程阻力损失和局部阻力损失。
    
    Attributes:
        upstream_node (str): 上游节点名称
        downstream_node (str): 下游节点名称
        length (float): 管道长度 (m)
        diameter (float): 管道直径 (m)
        roughness (float): 管道粗糙度 (m)
        minor_loss_coeff (float): 局部损失系数
        elevation_change (float): 高程变化 (m)，正值表示上升
    """
    
    def __init__(self, name: str, upstream_node: str, downstream_node: str,
                 length: float, diameter: float, roughness: float = 0.0001,
                 minor_loss_coeff: float = 0.0, elevation_change: float = 0.0):
        """
        初始化有压管道模型
        
        Args:
            name (str): 管道名称，在系统中必须唯一
            upstream_node (str): 上游节点名称
            downstream_node (str): 下游节点名称
            length (float): 管道长度 (m)，必须大于0
            diameter (float): 管道直径 (m)，必须大于0
            roughness (float): 管道绝对粗糙度 (m)，默认0.0001
            minor_loss_coeff (float): 局部损失系数，默认0
            elevation_change (float): 高程变化 (m)，正值表示上升
        
        Raises:
            ValueError: 当参数不合理时抛出异常
        """
        super().__init__(name, [upstream_node, downstream_node])
        
        # 参数验证
        if length <= 0:
            raise ValueError("管道长度必须大于0")
        if diameter <= 0:
            raise ValueError("管道直径必须大于0")
        if roughness < 0:
            raise ValueError("管道粗糙度不能为负值")
        
        self.upstream_node = upstream_node
        self.downstream_node = downstream_node
        self.length = float(length)
        self.diameter = float(diameter)
        self.roughness = float(roughness)
        self.minor_loss_coeff = float(minor_loss_coeff)
        self.elevation_change = float(elevation_change)
        
        # 计算管道几何参数
        self.area = math.pi * (self.diameter / 2) ** 2
        self.hydraulic_radius = self.diameter / 4
        self.relative_roughness = self.roughness / self.diameter
        
        # 预计算常用值
        self.L_over_D = self.length / self.diameter
        self.g = 9.81  # 重力加速度
    
    def get_variable_names(self) -> List[str]:
        """
        获取有压管道模型引入的变量名列表
        
        Returns:
            List[str]: 变量名列表，包含管道流量变量
        """
        return [f'Q_{self.name}']
    
    def get_equations(self, variables: Dict[str, float], dt: float,
                     prev_states: Dict[str, float]) -> Dict[str, float]:
        """
        获取有压管道模型的方程残差
        
        构建能量方程：H_up - H_down - hf - hm - Δz = 0
        其中：hf为沿程损失，hm为局部损失，Δz为高程差
        
        Args:
            variables (Dict[str, float]): 当前时步所有变量值
            dt (float): 时间步长 (s)
            prev_states (Dict[str, float]): 上一时步状态值
        
        Returns:
            Dict[str, float]: 方程残差字典
        """
        # 获取变量值
        Q = variables.get(f'Q_{self.name}', 0.0)
        H_up = variables.get(f'H_{self.upstream_node}', 0.0)
        H_down = variables.get(f'H_{self.downstream_node}', 0.0)
        
        # 计算流速
        velocity = self._calculate_velocity(Q)
        
        # 计算水头损失
        hf = self._calculate_friction_loss(velocity)
        hm = self._calculate_minor_loss(velocity)
        
        # 能量方程残差
        # H_up - H_down = hf + hm + elevation_change
        energy_residual = H_up - H_down - hf - hm - self.elevation_change
        
        equations = {
            f'energy_balance_{self.name}': energy_residual
        }
        
        return equations
    
    def _calculate_velocity(self, flow_rate: float) -> float:
        """
        计算管道流速
        
        Args:
            flow_rate (float): 流量 (m³/s)
        
        Returns:
            float: 流速 (m/s)
        """
        if self.area > 0:
            return abs(flow_rate) / self.area
        return 0.0
    
    def _calculate_friction_loss(self, velocity: float) -> float:
        """
        计算沿程水头损失
        
        使用达西-韦茨巴赫公式：hf = f × (L/D) × (V²/2g)
        摩阻系数f使用Colebrook-White公式计算
        
        Args:
            velocity (float): 流速 (m/s)
        
        Returns:
            float: 沿程损失 (m)
        """
        if velocity <= 0:
            return 0.0
        
        # 计算雷诺数
        Re = self._calculate_reynolds_number(velocity)
        
        # 计算摩阻系数
        f = self._calculate_friction_factor(Re)
        
        # 达西-韦茨巴赫公式
        head_loss = f * self.L_over_D * (velocity ** 2) / (2 * self.g)
        
        return head_loss
    
    def _calculate_minor_loss(self, velocity: float) -> float:
        """
        计算局部水头损失
        
        公式：hm = K × V²/(2g)
        
        Args:
            velocity (float): 流速 (m/s)
        
        Returns:
            float: 局部损失 (m)
        """
        if velocity <= 0 or self.minor_loss_coeff <= 0:
            return 0.0
        
        return self.minor_loss_coeff * (velocity ** 2) / (2 * self.g)
    
    def _calculate_reynolds_number(self, velocity: float) -> float:
        """
        计算雷诺数
        
        Re = V × D / ν，其中ν为运动粘度（水在20°C时约为1e-6 m²/s）
        
        Args:
            velocity (float): 流速 (m/s)
        
        Returns:
            float: 雷诺数
        """
        nu = 1e-6  # 水的运动粘度 (m²/s)
        return velocity * self.diameter / nu
    
    def _calculate_friction_factor(self, Re: float) -> float:
        """
        计算摩阻系数
        
        使用简化的经验公式，适用于工程计算
        
        Args:
            Re (float): 雷诺数
        
        Returns:
            float: 摩阻系数
        """
        if Re < 2300:
            # 层流
            return 64.0 / Re if Re > 0 else 0.064
        else:
            # 紊流：使用简化的Colebrook-White公式
            # 1/√f = -2×log10(ε/3.7D + 2.51/(Re×√f))
            # 简化为显式近似公式
            if self.relative_roughness > 0:
                # Swamee-Jain公式
                term1 = self.relative_roughness / 3.7
                term2 = 5.74 / (Re ** 0.9)
                f = 0.25 / (math.log10(term1 + term2) ** 2)
            else:
                # 光滑管道：Blasius公式
                f = 0.3164 / (Re ** 0.25)
            
            return max(0.008, min(0.1, f))  # 限制合理范围
    
    def calculate_flow_for_head_loss(self, head_loss: float) -> float:
        """
        根据水头损失计算流量
        
        Args:
            head_loss (float): 总水头损失 (m)
        
        Returns:
            float: 对应的流量 (m³/s)
        """
        if head_loss <= 0:
            return 0.0
        
        # 使用迭代方法求解
        # 初始猜测：假设摩阻系数为0.02
        f_guess = 0.02
        V = math.sqrt(2 * self.g * head_loss / (f_guess * self.L_over_D + self.minor_loss_coeff))
        
        # 迭代优化
        for _ in range(10):
            Re = self._calculate_reynolds_number(V)
            f_new = self._calculate_friction_factor(Re)
            
            # 更新流速
            V_new = math.sqrt(2 * self.g * head_loss / (f_new * self.L_over_D + self.minor_loss_coeff))
            
            if abs(V_new - V) / max(V, 1e-6) < 0.01:
                break
            V = V_new
        
        return V * self.area
    
    def get_hydraulic_properties(self, flow_rate: float) -> Dict[str, float]:
        """
        获取水力特性参数
        
        Args:
            flow_rate (float): 流量 (m³/s)
        
        Returns:
            Dict[str, float]: 水力特性字典
        """
        velocity = self._calculate_velocity(flow_rate)
        Re = self._calculate_reynolds_number(velocity)
        f = self._calculate_friction_factor(Re)
        hf = self._calculate_friction_loss(velocity)
        hm = self._calculate_minor_loss(velocity)
        
        return {
            'flow_rate': flow_rate,
            'velocity': velocity,
            'reynolds_number': Re,
            'friction_factor': f,
            'friction_loss': hf,
            'minor_loss': hm,
            'total_loss': hf + hm,
            'flow_regime': 'laminar' if Re < 2300 else 'turbulent'
        }
    
    def validate_flow_conditions(self, flow_rate: float) -> Dict[str, bool]:
        """
        验证流动条件
        
        Args:
            flow_rate (float): 流量 (m³/s)
        
        Returns:
            Dict[str, bool]: 验证结果
        """
        velocity = self._calculate_velocity(flow_rate)
        
        return {
            'velocity_reasonable': 0.1 <= velocity <= 10.0,  # 合理流速范围
            'no_cavitation': velocity <= 5.0,  # 避免气蚀
            'flow_rate_positive': flow_rate >= 0,
            'reynolds_valid': self._calculate_reynolds_number(velocity) > 100
        }
    
    def __repr__(self) -> str:
        """模型的字符串表示"""
        return (f"PressurizedPipeModel(name='{self.name}', "
                f"L={self.length:.1f}m, D={self.diameter:.3f}m, "
                f"upstream='{self.upstream_node}', downstream='{self.downstream_node}')")


def create_simple_pipe(name: str, upstream_node: str, downstream_node: str,
                      length: float, diameter: float, 
                      roughness: float = 0.0001) -> PressurizedPipeModel:
    """
    创建简单有压管道
    
    Args:
        name (str): 管道名称
        upstream_node (str): 上游节点
        downstream_node (str): 下游节点
        length (float): 长度 (m)
        diameter (float): 直径 (m)
        roughness (float): 粗糙度 (m)
    
    Returns:
        PressurizedPipeModel: 管道模型实例
    """
    return PressurizedPipeModel(name, upstream_node, downstream_node,
                               length, diameter, roughness)


def create_pipe_with_fittings(name: str, upstream_node: str, downstream_node: str,
                             length: float, diameter: float,
                             fittings: List[Dict[str, Any]],
                             roughness: float = 0.0001) -> PressurizedPipeModel:
    """
    创建带管件的有压管道
    
    Args:
        name (str): 管道名称
        upstream_node (str): 上游节点
        downstream_node (str): 下游节点
        length (float): 长度 (m)
        diameter (float): 直径 (m)
        fittings (List[Dict]): 管件列表
            格式: [{'type': str, 'loss_coeff': float, 'count': int}]
        roughness (float): 粗糙度 (m)
    
    Returns:
        PressurizedPipeModel: 管道模型实例
    """
    # 计算总局部损失系数
    total_minor_loss = 0.0
    for fitting in fittings:
        loss_coeff = fitting.get('loss_coeff', 0.0)
        count = fitting.get('count', 1)
        total_minor_loss += loss_coeff * count
    
    return PressurizedPipeModel(name, upstream_node, downstream_node,
                               length, diameter, roughness, total_minor_loss)


# 常用管件损失系数
FITTING_LOSS_COEFFICIENTS = {
    'elbow_90': 0.9,
    'elbow_45': 0.4,
    'tee_through': 0.6,
    'tee_branch': 1.8,
    'gate_valve_open': 0.2,
    'globe_valve_open': 10.0,
    'check_valve': 2.5,
    'entrance_sharp': 0.5,
    'entrance_rounded': 0.04,
    'exit': 1.0,
    'expansion_sudden': 1.0,
    'contraction_sudden': 0.5
}