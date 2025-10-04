"""
配置驱动的闸门过流计算模型

基于YAML配置文件实现闸门水力特性建模，支持流态判别和自适应公式选择。
遵循简化参数设计规范，提供最佳实践默认值，支持渐进式自定义。

设计特点:
1. 配置驱动：所有参数通过配置文件定义，支持灵活配置
2. 流态自动判别：自动识别自由出流和淹没出流
3. 自适应公式选择：根据水力条件自动切换计算公式
4. 简化参数设计：提供理论分析的默认值，降低使用门槛

Author: WaterNet Development Team
Date: 2024-10-05
"""

import math
from typing import Dict, List, Optional, Any, Union
from ..interfaces.hydro_model import HydroModel


class ConfigurableGateModel(HydroModel):
    """
    可配置闸门模型
    
    基于配置文件的闸门过流计算模型，支持多种流态和计算公式。
    通过配置文件灵活定义闸门几何参数、水力特性和控制策略。
    
    Attributes:
        gate_config (Dict): 闸门配置字典
        upstream_node (str): 上游节点名称
        downstream_node (str): 下游节点名称
        width (float): 闸门宽度 (m)
        bottom_elevation (float): 闸底高程 (m)
        discharge_coefficient (float): 流量系数
        submerged_threshold (float): 淹没出流判别阈值
        current_opening (float): 当前开度 (m)
        max_opening (float): 最大开度 (m)
        min_opening (float): 最小开度 (m)
    """
    
    def __init__(self, name: str, gate_config: Dict[str, Any]):
        """
        基于配置初始化闸门模型
        
        Args:
            name (str): 闸门名称
            gate_config (Dict): 闸门配置字典，包含所有必要参数
        
        Raises:
            ValueError: 当配置参数不合理时抛出异常
        """
        # 解析位置配置
        location = gate_config.get('location', {})
        upstream_node = location.get('upstream_node')
        downstream_node = location.get('downstream_node')
        
        if not upstream_node or not downstream_node:
            raise ValueError(f"闸门 {name} 必须配置上下游节点")
        
        super().__init__(name, [upstream_node, downstream_node])
        
        # 存储完整配置
        self.gate_config = gate_config
        self.upstream_node = upstream_node
        self.downstream_node = downstream_node
        
        # 解析几何参数（带默认值）
        geometry = gate_config.get('geometry', {})
        self.width = float(geometry.get('width', 10.0))
        self.bottom_elevation = float(geometry.get('bottom_elevation', 0.0))
        
        # 解析水力参数（带理论最佳默认值）
        hydraulics = gate_config.get('hydraulics', {})
        self.discharge_coefficient = float(hydraulics.get('discharge_coefficient', 0.65))
        self.submerged_threshold = float(hydraulics.get('submerged_threshold', 0.7))
        self.free_flow_formula = hydraulics.get('free_flow_formula', 'orifice')
        self.submerged_flow_formula = hydraulics.get('submerged_flow_formula', 'submerged_orifice')
        
        # 解析控制参数
        control = gate_config.get('control', {})
        self.current_opening = float(control.get('initial_opening', 0.0))
        self.max_opening = float(control.get('max_opening', 5.0))
        self.min_opening = float(control.get('min_opening', 0.0))
        
        # 参数验证
        self._validate_configuration()
        
        # 内部状态
        self._flow_regime_history = []  # 流态历史
        self._discharge_history = []    # 流量历史
    
    def _validate_configuration(self):
        """验证配置参数的合理性"""
        if self.width <= 0:
            raise ValueError("闸门宽度必须为正值")
        if self.discharge_coefficient <= 0 or self.discharge_coefficient > 1.0:
            raise ValueError("流量系数必须在 (0, 1] 范围内")
        if self.submerged_threshold <= 0 or self.submerged_threshold >= 1.0:
            raise ValueError("淹没判别阈值必须在 (0, 1) 范围内")
        if self.max_opening <= self.min_opening:
            raise ValueError("最大开度必须大于最小开度")
        if not (self.min_opening <= self.current_opening <= self.max_opening):
            raise ValueError("初始开度必须在允许范围内")
    
    def get_variable_names(self) -> List[str]:
        """
        获取闸门模型引入的变量名列表
        
        Returns:
            List[str]: 变量名列表，包含流量变量和开度变量
        """
        return [
            f'Q_{self.name}',      # 闸门流量
            f'a_{self.name}'       # 闸门开度
        ]
    
    def get_equations(self, variables: Dict[str, float], dt: float,
                     prev_states: Dict[str, float]) -> Dict[str, float]:
        """
        获取闸门模型的方程残差
        
        构建闸门过流特性方程：
        Q_gate - calculate_discharge(H_up, H_down, opening) = 0
        
        Args:
            variables (Dict[str, float]): 当前时步所有变量值
            dt (float): 时间步长 (s)
            prev_states (Dict[str, float]): 上一时步状态值
        
        Returns:
            Dict[str, float]: 方程残差字典
        """
        equations = {}
        
        # 获取变量值
        Q_gate = variables.get(f'Q_{self.name}', 0.0)
        opening = variables.get(f'a_{self.name}', self.current_opening)
        
        # 获取上下游水位
        H_upstream = variables.get(f'H_{self.upstream_node}', self.bottom_elevation + 1.0)
        H_downstream = variables.get(f'H_{self.downstream_node}', self.bottom_elevation)
        
        # 计算理论流量
        try:
            Q_theoretical = self.calculate_discharge(H_upstream, H_downstream, opening)
            
            # 过流特性方程残差
            discharge_residual = Q_gate - Q_theoretical
            equations[f'gate_discharge_{self.name}'] = discharge_residual
            
        except Exception as e:
            # 计算失败时使用大残差
            equations[f'gate_discharge_{self.name}'] = 1000.0
        
        return equations
    
    def calculate_discharge(self, H_upstream: float, H_downstream: float, 
                          opening: float) -> float:
        """
        计算闸门过流量
        
        自动判别流态并选择相应的计算公式：
        1. 判断是否为有效过流条件
        2. 计算淹没度，判别流态
        3. 选择相应公式计算流量
        
        Args:
            H_upstream (float): 上游水位 (m)
            H_downstream (float): 下游水位 (m)
            opening (float): 闸门开度 (m)
        
        Returns:
            float: 闸门流量 (m³/s)
        """
        # 检查基本过流条件
        if not self._check_flow_conditions(H_upstream, H_downstream, opening):
            return 0.0
        
        # 计算相对水头
        H_up_rel = max(0.0, H_upstream - self.bottom_elevation)
        H_down_rel = max(0.0, H_downstream - self.bottom_elevation)
        
        # 流态判别
        flow_regime = self._determine_flow_regime(H_up_rel, H_down_rel, opening)
        
        # 记录流态历史
        self._flow_regime_history.append(flow_regime)
        if len(self._flow_regime_history) > 100:
            self._flow_regime_history.pop(0)
        
        # 根据流态计算流量
        if flow_regime == 'free_flow':
            discharge = self._calculate_free_flow(H_up_rel, opening)
        elif flow_regime == 'submerged_flow':
            discharge = self._calculate_submerged_flow(H_up_rel, H_down_rel, opening)
        else:  # transitional_flow
            discharge = self._calculate_transitional_flow(H_up_rel, H_down_rel, opening)
        
        # 记录流量历史
        self._discharge_history.append(discharge)
        if len(self._discharge_history) > 100:
            self._discharge_history.pop(0)
        
        return max(0.0, discharge)
    
    def _check_flow_conditions(self, H_upstream: float, H_downstream: float, 
                             opening: float) -> bool:
        """
        检查基本过流条件
        
        Args:
            H_upstream (float): 上游水位 (m)
            H_downstream (float): 下游水位 (m)
            opening (float): 闸门开度 (m)
        
        Returns:
            bool: True表示满足过流条件
        """
        # 开度检查
        if opening <= 0 or opening < self.min_opening:
            return False
        
        # 水位检查
        if H_upstream <= self.bottom_elevation:
            return False
        
        # 水头差检查（允许小的负值，用于数值稳定性）
        if H_upstream < H_downstream - 0.01:
            return False
        
        return True
    
    def _determine_flow_regime(self, H_up: float, H_down: float, 
                             opening: float) -> str:
        """
        判别流态
        
        根据淹没度和几何条件判别流态：
        - 自由出流：下游水位不影响流量
        - 淹没出流：下游水位显著影响流量
        - 过渡流态：介于两者之间
        
        Args:
            H_up (float): 上游相对水头 (m)
            H_down (float): 下游相对水头 (m)
            opening (float): 闸门开度 (m)
        
        Returns:
            str: 流态类型 ('free_flow', 'submerged_flow', 'transitional_flow')
        """
        if H_up <= 0:
            return 'free_flow'  # 默认流态
        
        # 计算淹没度
        submergence_ratio = H_down / H_up
        
        # 计算开度比
        opening_ratio = opening / H_up
        
        # 流态判别逻辑
        if submergence_ratio < self.submerged_threshold * 0.9:
            return 'free_flow'
        elif submergence_ratio > self.submerged_threshold * 1.1:
            return 'submerged_flow'
        else:
            return 'transitional_flow'
    
    def _calculate_free_flow(self, H_up: float, opening: float) -> float:
        """
        计算自由出流流量
        
        使用孔口流公式：Q = Cd * A * √(2g * H)
        
        Args:
            H_up (float): 上游相对水头 (m)
            opening (float): 闸门开度 (m)
        
        Returns:
            float: 自由出流流量 (m³/s)
        """
        if self.free_flow_formula == 'orifice':
            # 标准孔口流公式
            effective_area = self.width * opening
            velocity_head = math.sqrt(2 * 9.81 * H_up)
            return self.discharge_coefficient * effective_area * velocity_head
        
        elif self.free_flow_formula == 'weir':
            # 堰流公式（当开度较小时）
            if opening < 0.67 * H_up:  # 薄壁堰条件
                return self.discharge_coefficient * self.width * math.pow(H_up, 1.5) * math.sqrt(2 * 9.81)
            else:
                # 退化为孔口流
                return self._calculate_free_flow_orifice(H_up, opening)
        
        else:
            # 默认使用孔口流
            return self._calculate_free_flow_orifice(H_up, opening)
    
    def _calculate_free_flow_orifice(self, H_up: float, opening: float) -> float:
        """标准孔口流计算"""
        effective_area = self.width * opening
        velocity_head = math.sqrt(2 * 9.81 * H_up)
        return self.discharge_coefficient * effective_area * velocity_head
    
    def _calculate_submerged_flow(self, H_up: float, H_down: float, 
                                opening: float) -> float:
        """
        计算淹没出流流量
        
        使用淹没孔口流公式：Q = Cd * A * √(2g * (H_up - H_down))
        
        Args:
            H_up (float): 上游相对水头 (m)
            H_down (float): 下游相对水头 (m)
            opening (float): 闸门开度 (m)
        
        Returns:
            float: 淹没出流流量 (m³/s)
        """
        if self.submerged_flow_formula == 'submerged_orifice':
            # 标准淹没孔口流公式
            effective_area = self.width * opening
            head_difference = max(0.001, H_up - H_down)  # 避免零水头差
            velocity_head = math.sqrt(2 * 9.81 * head_difference)
            
            # 淹没修正系数
            submergence_ratio = H_down / H_up
            correction_factor = self._get_submergence_correction(submergence_ratio)
            
            return correction_factor * self.discharge_coefficient * effective_area * velocity_head
        
        else:
            # 默认淹没计算
            return self._calculate_submerged_flow_default(H_up, H_down, opening)
    
    def _calculate_submerged_flow_default(self, H_up: float, H_down: float, 
                                        opening: float) -> float:
        """默认淹没流计算"""
        effective_area = self.width * opening
        head_difference = max(0.001, H_up - H_down)
        velocity_head = math.sqrt(2 * 9.81 * head_difference)
        return self.discharge_coefficient * effective_area * velocity_head
    
    def _get_submergence_correction(self, submergence_ratio: float) -> float:
        """
        获取淹没修正系数
        
        根据淹没度调整流量系数，考虑淹没对流量的影响
        
        Args:
            submergence_ratio (float): 淹没度 (H_down/H_up)
        
        Returns:
            float: 修正系数
        """
        if submergence_ratio <= 0.5:
            return 1.0
        elif submergence_ratio >= 0.9:
            return 0.8
        else:
            # 线性插值
            return 1.0 - 0.5 * (submergence_ratio - 0.5) / 0.4
    
    def _calculate_transitional_flow(self, H_up: float, H_down: float, 
                                   opening: float) -> float:
        """
        计算过渡流态流量
        
        在自由出流和淹没出流之间进行加权平均
        
        Args:
            H_up (float): 上游相对水头 (m)
            H_down (float): 下游相对水头 (m)
            opening (float): 闸门开度 (m)
        
        Returns:
            float: 过渡流态流量 (m³/s)
        """
        # 计算自由出流和淹没出流流量
        Q_free = self._calculate_free_flow(H_up, opening)
        Q_submerged = self._calculate_submerged_flow(H_up, H_down, opening)
        
        # 计算权重因子
        submergence_ratio = H_down / H_up if H_up > 0 else 0
        
        # 线性插值权重
        threshold_low = self.submerged_threshold * 0.9
        threshold_high = self.submerged_threshold * 1.1
        
        if submergence_ratio <= threshold_low:
            weight_submerged = 0.0
        elif submergence_ratio >= threshold_high:
            weight_submerged = 1.0
        else:
            weight_submerged = (submergence_ratio - threshold_low) / (threshold_high - threshold_low)
        
        weight_free = 1.0 - weight_submerged
        
        return weight_free * Q_free + weight_submerged * Q_submerged
    
    def set_opening(self, new_opening: float):
        """
        设置闸门开度
        
        Args:
            new_opening (float): 新开度 (m)
        
        Raises:
            ValueError: 当开度超出允许范围时抛出异常
        """
        if not (self.min_opening <= new_opening <= self.max_opening):
            raise ValueError(f"开度 {new_opening} 超出允许范围 [{self.min_opening}, {self.max_opening}]")
        
        self.current_opening = float(new_opening)
    
    def get_current_opening(self) -> float:
        """获取当前开度"""
        return self.current_opening
    
    def get_flow_regime_statistics(self) -> Dict[str, Any]:
        """
        获取流态统计信息
        
        Returns:
            Dict[str, Any]: 流态统计字典
        """
        if not self._flow_regime_history:
            return {'no_data': True}
        
        regime_counts = {}
        for regime in self._flow_regime_history:
            regime_counts[regime] = regime_counts.get(regime, 0) + 1
        
        total_count = len(self._flow_regime_history)
        regime_percentages = {k: v/total_count*100 for k, v in regime_counts.items()}
        
        return {
            'total_records': total_count,
            'regime_counts': regime_counts,
            'regime_percentages': regime_percentages,
            'current_regime': self._flow_regime_history[-1],
            'regime_transitions': self._count_regime_transitions()
        }
    
    def _count_regime_transitions(self) -> int:
        """统计流态转换次数"""
        if len(self._flow_regime_history) < 2:
            return 0
        
        transitions = 0
        for i in range(1, len(self._flow_regime_history)):
            if self._flow_regime_history[i] != self._flow_regime_history[i-1]:
                transitions += 1
        
        return transitions
    
    def get_discharge_statistics(self) -> Dict[str, Any]:
        """
        获取流量统计信息
        
        Returns:
            Dict[str, Any]: 流量统计字典
        """
        if not self._discharge_history:
            return {'no_data': True}
        
        discharges = self._discharge_history
        return {
            'count': len(discharges),
            'current': discharges[-1],
            'average': sum(discharges) / len(discharges),
            'maximum': max(discharges),
            'minimum': min(discharges),
            'standard_deviation': self._calculate_std(discharges)
        }
    
    def _calculate_std(self, values: List[float]) -> float:
        """计算标准差"""
        if len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean)**2 for x in values) / (len(values) - 1)
        return math.sqrt(variance)
    
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
        
        # 更新开度状态
        new_opening = variables.get(f'a_{self.name}', self.current_opening)
        new_states[f'a_{self.name}'] = new_opening
        
        # 更新流量状态
        new_states[f'Q_{self.name}'] = variables.get(f'Q_{self.name}', 0.0)
        
        return new_states
    
    def get_configuration_summary(self) -> Dict[str, Any]:
        """
        获取配置摘要
        
        Returns:
            Dict[str, Any]: 配置摘要字典
        """
        return {
            'name': self.name,
            'type': 'configurable_gate',
            'nodes': {
                'upstream': self.upstream_node,
                'downstream': self.downstream_node
            },
            'geometry': {
                'width': self.width,
                'bottom_elevation': self.bottom_elevation
            },
            'hydraulics': {
                'discharge_coefficient': self.discharge_coefficient,
                'submerged_threshold': self.submerged_threshold,
                'free_flow_formula': self.free_flow_formula,
                'submerged_flow_formula': self.submerged_flow_formula
            },
            'control': {
                'current_opening': self.current_opening,
                'max_opening': self.max_opening,
                'min_opening': self.min_opening
            },
            'original_config': self.gate_config
        }
    
    def __repr__(self) -> str:
        """模型的字符串表示"""
        return (f"ConfigurableGateModel(name='{self.name}', "
                f"width={self.width:.1f}m, "
                f"opening={self.current_opening:.2f}m, "
                f"nodes=['{self.upstream_node}', '{self.downstream_node}'])")


def create_gate_from_config(gate_name: str, gate_config: Dict[str, Any]) -> ConfigurableGateModel:
    """
    从配置字典创建闸门模型
    
    Args:
        gate_name (str): 闸门名称
        gate_config (Dict): 闸门配置字典
    
    Returns:
        ConfigurableGateModel: 闸门模型实例
    """
    return ConfigurableGateModel(gate_name, gate_config)


def create_gates_from_config(gates_config: Dict[str, Dict[str, Any]]) -> Dict[str, ConfigurableGateModel]:
    """
    从配置字典批量创建闸门模型
    
    Args:
        gates_config (Dict): 闸门配置字典，键为闸门名称，值为配置
    
    Returns:
        Dict[str, ConfigurableGateModel]: 闸门模型字典
    """
    gates = {}
    for gate_name, gate_config in gates_config.items():
        gates[gate_name] = create_gate_from_config(gate_name, gate_config)
    
    return gates