"""
水库模型

实现基于水量平衡的水库动态建模，支持与其他水力模型的联合求解。
水库模型通过蓄水量-水位关系和水量守恒定律描述水库的动态行为。

设计原理:
1. 水量平衡方程：蓄水量变化 = 流入量 - 流出量
2. 库容曲线：蓄水量与水位之间的非线性关系
3. 边界耦合：通过连接节点与其他水力模型交互

变量定义:
- H_{水库名}: 水库水位 (m)
- V_current: 当前蓄水量 (m³) [中间变量]
- Q_in_total: 总流入量 (m³/s) [边界条件]
- Q_out_total: 总流出量 (m³/s) [边界条件]

Author: WaterNet Development Team
Date: 2024-10-04
"""

import math
from typing import Dict, List, Callable, Optional, Any, Union
from ..interfaces.hydro_model import HydroModel


class ReservoirModel(HydroModel):
    """
    水库模型
    
    基于水量平衡原理的水库模型，通过蓄水量-水位关系和水量守恒定律
    描述水库的动态行为。支持与其他水力模型联合求解。
    
    Attributes:
        V_to_H_func (Callable): 蓄水量到水位的转换函数 V(m³) -> H(m)
        H_to_V_func (Callable): 水位到蓄水量的转换函数 H(m) -> V(m³)
        initial_volume (float): 初始蓄水量 (m³)
        min_volume (float): 最小蓄水量限制 (m³)
        max_volume (float): 最大蓄水量限制 (m³)
        connected_objects (List[str]): 连接的水力对象名称列表
    """
    
    def __init__(self, name: str, nodes: List[str], 
                 V_to_H_func: Callable[[float], float],
                 initial_volume: float,
                 connected_objects: Optional[List[str]] = None,
                 H_to_V_func: Optional[Callable[[float], float]] = None,
                 min_volume: float = 0.0,
                 max_volume: float = float('inf')):
        """
        初始化水库模型
        
        Args:
            name (str): 水库名称，在系统中必须唯一
            nodes (List[str]): 连接节点名称列表
            V_to_H_func (Callable): 蓄水量到水位转换函数 V(m³) -> H(m)
            initial_volume (float): 初始蓄水量 (m³)
            connected_objects (List[str], optional): 连接的水力对象名称列表
            H_to_V_func (Callable, optional): 水位到蓄水量转换函数
            min_volume (float): 最小蓄水量限制，默认0
            max_volume (float): 最大蓄水量限制，默认无限制
        
        Raises:
            ValueError: 当参数不合理时抛出异常
        """
        super().__init__(name, nodes)
        
        # 参数验证
        if not callable(V_to_H_func):
            raise ValueError("V_to_H_func必须是可调用对象")
        if initial_volume < 0:
            raise ValueError("初始蓄水量不能为负值")
        if min_volume < 0:
            raise ValueError("最小蓄水量不能为负值")
        if max_volume <= min_volume:
            raise ValueError("最大蓄水量必须大于最小蓄水量")
        if not (min_volume <= initial_volume <= max_volume):
            raise ValueError("初始蓄水量必须在允许范围内")
        
        self.V_to_H_func = V_to_H_func
        self.H_to_V_func = H_to_V_func
        self.initial_volume = initial_volume
        self.min_volume = min_volume
        self.max_volume = max_volume
        self.connected_objects = connected_objects or []
        
        # 验证库容曲线函数
        try:
            test_h = self.V_to_H_func(initial_volume)
            if not isinstance(test_h, (int, float)) or math.isnan(test_h) or math.isinf(test_h):
                raise ValueError("库容曲线函数返回值异常")
        except Exception as e:
            raise ValueError(f"库容曲线函数测试失败: {e}")
    
    def get_variable_names(self) -> List[str]:
        """
        获取水库模型引入的变量名列表
        
        Returns:
            List[str]: 变量名列表，包含水库水位变量
        """
        return [f'H_{self.name}']
    
    def get_equations(self, variables: Dict[str, float], dt: float, 
                     prev_states: Dict[str, float]) -> Dict[str, float]:
        """
        获取水库模型的方程残差
        
        构建两个核心方程：
        1. 离散化水量平衡方程：V_current - V_prev - (Q_in - Q_out) * dt = 0
        2. 库容曲线约束方程：H_reservoir - V_to_H_func(V_current) = 0
        
        Args:
            variables (Dict[str, float]): 当前时步所有变量值
            dt (float): 时间步长 (s)
            prev_states (Dict[str, float]): 上一时步状态值
        
        Returns:
            Dict[str, float]: 方程残差字典
        """
        # 获取当前水位变量
        H_current = variables.get(f'H_{self.name}', 0.0)
        
        # 获取上一时步蓄水量
        V_prev = prev_states.get(f'V_{self.name}', self.initial_volume)
        
        # 计算流量平衡
        Q_in_total, Q_out_total = self._calculate_flow_balance(variables)
        
        # 计算当前蓄水量（通过水量平衡）
        V_current = V_prev + (Q_in_total - Q_out_total) * dt
        
        # 检查物理约束
        if not self._validate_physical_constraints(V_current, H_current):
            # 如果违反约束，增加惩罚项
            penalty = 1000.0
        else:
            penalty = 0.0
        
        # 构建方程残差
        equations = {}
        
        # 方程1：库容曲线约束
        # H_reservoir - V_to_H_func(V_current) = 0
        try:
            H_from_volume = self.V_to_H_func(V_current)
            equations[f'capacity_curve_{self.name}'] = H_current - H_from_volume + penalty
        except Exception as e:
            # 库容曲线计算失败，使用大残差
            equations[f'capacity_curve_{self.name}'] = 1000.0
        
        return equations
    
    def _calculate_flow_balance(self, variables: Dict[str, float]) -> tuple[float, float]:
        """
        计算水库的流量平衡
        
        通过分析连接对象的流量变量，确定流入和流出水库的总流量。
        流向判断规则：
        - 对象名_start/inlet -> 流入水库
        - 对象名_end/outlet -> 流出水库
        - 无后缀或其他后缀 -> 根据流量符号判断
        
        Args:
            variables (Dict[str, float]): 当前变量值
        
        Returns:
            tuple[float, float]: (总流入量, 总流出量) (m³/s)
        """
        Q_in_total = 0.0
        Q_out_total = 0.0
        
        # 遍历所有流量变量，识别与水库相关的流量
        for var_name, flow_value in variables.items():
            if not var_name.startswith('Q_'):
                continue
            
            # 检查是否与水库相关的流量
            is_related = False
            is_inflow = False
            
            # 方法1：检查连接对象列表
            for obj_name in self.connected_objects:
                if obj_name in var_name:
                    is_related = True
                    # 判断流向
                    if ('_start' in var_name or '_inlet' in var_name or 
                        var_name.endswith('_in')):
                        is_inflow = True
                    elif ('_end' in var_name or '_outlet' in var_name or 
                          var_name.endswith('_out')):
                        is_inflow = False
                    else:
                        # 根据流量符号判断
                        is_inflow = flow_value >= 0
                    break
            
            # 方法2：检查是否直接包含水库名称
            if not is_related and self.name in var_name:
                is_related = True
                # 假设流向水库的为正，流出的为负
                is_inflow = flow_value >= 0
            
            # 累加流量
            if is_related:
                if is_inflow:
                    Q_in_total += abs(flow_value)
                else:
                    Q_out_total += abs(flow_value)
        
        # 处理边界流量（如果存在）
        boundary_inflow = variables.get(f'Q_in_{self.name}', 0.0)
        boundary_outflow = variables.get(f'Q_out_{self.name}', 0.0)
        
        Q_in_total += max(0.0, boundary_inflow)
        Q_out_total += max(0.0, boundary_outflow)
        
        return Q_in_total, Q_out_total
    
    def _validate_physical_constraints(self, V: float, H: float) -> bool:
        """
        验证物理约束条件
        
        Args:
            V (float): 蓄水量 (m³)
            H (float): 水位 (m)
        
        Returns:
            bool: True表示满足约束，False表示违反约束
        """
        # 检查蓄水量范围
        if V < self.min_volume or V > self.max_volume:
            return False
        
        # 检查水位合理性
        if H < 0 or math.isnan(H) or math.isinf(H):
            return False
        
        # 检查库容曲线一致性（如果有反函数）
        if self.H_to_V_func is not None:
            try:
                V_check = self.H_to_V_func(H)
                relative_error = abs(V - V_check) / max(abs(V), 1.0)
                if relative_error > 0.1:  # 允许10%的误差
                    return False
            except:
                pass  # 反函数计算失败时忽略此检查
        
        return True
    
    def get_current_volume(self, variables: Dict[str, float], dt: float,
                          prev_states: Dict[str, float]) -> float:
        """
        获取当前蓄水量
        
        Args:
            variables: 当前变量值
            dt: 时间步长
            prev_states: 前一时步状态
        
        Returns:
            float: 当前蓄水量 (m³)
        """
        V_prev = prev_states.get(f'V_{self.name}', self.initial_volume)
        Q_in_total, Q_out_total = self._calculate_flow_balance(variables)
        V_current = V_prev + (Q_in_total - Q_out_total) * dt
        return max(self.min_volume, min(self.max_volume, V_current))
    
    def get_water_level(self, volume: float) -> float:
        """
        根据蓄水量计算水位
        
        Args:
            volume (float): 蓄水量 (m³)
        
        Returns:
            float: 水位 (m)
        """
        try:
            return self.V_to_H_func(volume)
        except Exception:
            return 0.0
    
    def get_volume_from_level(self, water_level: float) -> float:
        """
        根据水位计算蓄水量
        
        Args:
            water_level (float): 水位 (m)
        
        Returns:
            float: 蓄水量 (m³)
        """
        if self.H_to_V_func is not None:
            try:
                return self.H_to_V_func(water_level)
            except Exception:
                return self.initial_volume
        else:
            # 如果没有反函数，使用数值方法求解
            return self._numerical_inverse_volume(water_level)
    
    def _numerical_inverse_volume(self, target_level: float, 
                                 tolerance: float = 1e-6) -> float:
        """
        数值求解库容曲线的反函数
        
        Args:
            target_level (float): 目标水位 (m)
            tolerance (float): 收敛容差
        
        Returns:
            float: 对应的蓄水量 (m³)
        """
        # 简单的二分法求解
        V_min = self.min_volume
        V_max = self.max_volume
        
        if V_max == float('inf'):
            V_max = self.initial_volume * 10  # 使用合理的上界
        
        for _ in range(50):  # 最大迭代次数
            V_mid = (V_min + V_max) / 2
            try:
                H_mid = self.V_to_H_func(V_mid)
                if abs(H_mid - target_level) < tolerance:
                    return V_mid
                elif H_mid < target_level:
                    V_min = V_mid
                else:
                    V_max = V_mid
            except:
                break
        
        return self.initial_volume  # 求解失败时返回初始值
    
    def update_states(self, variables: Dict[str, float], dt: float,
                     prev_states: Dict[str, float]) -> Dict[str, float]:
        """
        更新状态变量
        
        Args:
            variables: 当前变量值
            dt: 时间步长
            prev_states: 前一时步状态
        
        Returns:
            Dict[str, float]: 更新后的状态字典
        """
        new_states = prev_states.copy()
        
        # 更新蓄水量状态
        new_volume = self.get_current_volume(variables, dt, prev_states)
        new_states[f'V_{self.name}'] = new_volume
        
        # 更新水位状态（用于状态记录）
        new_states[f'H_{self.name}'] = variables.get(f'H_{self.name}', 0.0)
        
        return new_states
    
    def get_statistics(self, variables: Dict[str, float], dt: float,
                      prev_states: Dict[str, float]) -> Dict[str, Any]:
        """
        获取水库统计信息
        
        Args:
            variables: 当前变量值
            dt: 时间步长
            prev_states: 前一时步状态
        
        Returns:
            Dict[str, Any]: 统计信息字典
        """
        current_volume = self.get_current_volume(variables, dt, prev_states)
        current_level = variables.get(f'H_{self.name}', 0.0)
        Q_in, Q_out = self._calculate_flow_balance(variables)
        
        return {
            'name': self.name,
            'current_volume': current_volume,
            'current_level': current_level,
            'inflow_rate': Q_in,
            'outflow_rate': Q_out,
            'net_flow': Q_in - Q_out,
            'volume_change_rate': (Q_in - Q_out),
            'capacity_utilization': current_volume / self.max_volume if self.max_volume != float('inf') else None
        }
    
    def __repr__(self) -> str:
        """模型的字符串表示"""
        return (f"ReservoirModel(name='{self.name}', "
                f"initial_volume={self.initial_volume:.0f}, "
                f"nodes={self.node_names})")


def create_simple_reservoir(name: str, upstream_node: str, downstream_node: str,
                           initial_level: float, bottom_level: float = 0.0,
                           surface_area: float = 1000000.0) -> ReservoirModel:
    """
    创建简单的水库模型（矩形库容曲线）
    
    Args:
        name (str): 水库名称
        upstream_node (str): 上游节点
        downstream_node (str): 下游节点
        initial_level (float): 初始水位 (m)
        bottom_level (float): 库底高程 (m)
        surface_area (float): 水面面积 (m²)，假设为常数
    
    Returns:
        ReservoirModel: 水库模型实例
    """
    def V_to_H(volume):
        """蓄水量到水位转换（矩形库容）"""
        return bottom_level + volume / surface_area
    
    def H_to_V(level):
        """水位到蓄水量转换（矩形库容）"""
        return max(0.0, (level - bottom_level) * surface_area)
    
    initial_volume = H_to_V(initial_level)
    
    return ReservoirModel(
        name=name,
        nodes=[upstream_node, downstream_node],
        V_to_H_func=V_to_H,
        initial_volume=initial_volume,
        H_to_V_func=H_to_V,
        min_volume=0.0,
        max_volume=surface_area * 100.0  # 假设最大深度100m
    )


def create_polynomial_reservoir(name: str, nodes: List[str],
                               capacity_coefficients: List[float],
                               initial_level: float) -> ReservoirModel:
    """
    创建多项式库容曲线的水库模型
    
    V = c0 + c1*H + c2*H² + c3*H³ + ...
    
    Args:
        name (str): 水库名称
        nodes (List[str]): 连接节点列表
        capacity_coefficients (List[float]): 库容曲线系数 [c0, c1, c2, ...]
        initial_level (float): 初始水位 (m)
    
    Returns:
        ReservoirModel: 水库模型实例
    """
    if len(capacity_coefficients) < 2:
        raise ValueError("库容曲线至少需要2个系数")
    
    def H_to_V(level):
        """多项式库容曲线：V = c0 + c1*H + c2*H² + ..."""
        volume = 0.0
        for i, coeff in enumerate(capacity_coefficients):
            volume += coeff * (level ** i)
        return max(0.0, volume)
    
    def V_to_H(volume):
        """数值反解水位"""
        # 简化求解：使用牛顿法
        H = initial_level  # 初始猜测
        for _ in range(20):
            f = H_to_V(H) - volume
            if abs(f) < 1e-6:
                break
            # 计算导数
            df_dH = 0.0
            for i, coeff in enumerate(capacity_coefficients[1:], 1):
                df_dH += i * coeff * (H ** (i-1))
            if abs(df_dH) > 1e-12:
                H = H - f / df_dH
            else:
                break
        return max(0.0, H)
    
    initial_volume = H_to_V(initial_level)
    
    return ReservoirModel(
        name=name,
        nodes=nodes,
        V_to_H_func=V_to_H,
        initial_volume=initial_volume,
        H_to_V_func=H_to_V
    )