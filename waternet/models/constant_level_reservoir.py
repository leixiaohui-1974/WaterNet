"""
恒定水位水库模型

实现设计文档中的恒定水位边界条件，用于水库-闸门-明渠系统建模。
该模型维持水库水位恒定，通过自动调节流入/流出量实现。

设计特点:
1. 水位始终保持恒定值，不受流量变化影响
2. 上游水库作为无限水源，自动补给维持水位
3. 下游水库作为无限汇点，自动泄放维持水位
4. 支持与闸门、明渠等其他水力模型的耦合

变量系统:
- H_{水库名}: 水库水位，固定为设定值 (m)
- Q_boundary_{水库名}: 边界调节流量 (m³/s)

Author: WaterNet Development Team
Date: 2024-10-05
"""

import math
from typing import Dict, List, Optional, Any, Callable
from ..interfaces.hydro_model import HydroModel


class ConstantLevelReservoir(HydroModel):
    """
    恒定水位水库模型
    
    维持水库水位恒定的边界条件模型。通过自动调节边界流量，
    确保水库水位始终保持在设定值，不受下游流量变化影响。
    
    Attributes:
        constant_level (float): 恒定水位值 (m)
        reservoir_type (str): 水库类型 ('upstream' 或 'downstream')
        capacity (float): 水库容量 (m³)
        connected_structures (List[str]): 连接的水力结构名称列表
        enable_boundary_adjustment (bool): 是否启用边界流量自动调节
        max_adjustment_rate (float): 最大调节流量 (m³/s)
    """
    
    def __init__(self, name: str, nodes: List[str], constant_level: float,
                 reservoir_type: str = 'upstream',
                 capacity: float = 1e6,
                 connected_structures: Optional[List[str]] = None,
                 enable_boundary_adjustment: bool = True,
                 max_adjustment_rate: float = 1000.0):
        """
        初始化恒定水位水库模型
        
        Args:
            name (str): 水库名称，在系统中必须唯一
            nodes (List[str]): 连接节点名称列表
            constant_level (float): 恒定水位值 (m)
            reservoir_type (str): 水库类型，'upstream' 或 'downstream'
            capacity (float): 水库容量 (m³)，用于统计计算
            connected_structures (List[str], optional): 连接的水力结构名称列表
            enable_boundary_adjustment (bool): 是否启用边界流量自动调节
            max_adjustment_rate (float): 最大调节流量 (m³/s)
        
        Raises:
            ValueError: 当参数不合理时抛出异常
        """
        super().__init__(name, nodes)
        
        # 参数验证
        if not isinstance(constant_level, (int, float)) or math.isnan(constant_level):
            raise ValueError("恒定水位必须是有效数值")
        if reservoir_type not in ['upstream', 'downstream']:
            raise ValueError("水库类型必须是 'upstream' 或 'downstream'")
        if capacity <= 0:
            raise ValueError("水库容量必须为正值")
        if max_adjustment_rate <= 0:
            raise ValueError("最大调节流量必须为正值")
        
        self.constant_level = float(constant_level)
        self.reservoir_type = reservoir_type
        self.capacity = float(capacity)
        self.connected_structures = connected_structures or []
        self.enable_boundary_adjustment = enable_boundary_adjustment
        self.max_adjustment_rate = float(max_adjustment_rate)
        
        # 内部状态
        self._cumulative_volume_change = 0.0  # 累积蓄量变化
        self._boundary_flow_history = []      # 边界流量历史
    
    def get_variable_names(self) -> List[str]:
        """
        获取恒定水位水库模型引入的变量名列表
        
        Returns:
            List[str]: 变量名列表，包含水位变量和边界调节流量变量
        """
        variables = [f'H_{self.name}']
        
        if self.enable_boundary_adjustment:
            variables.append(f'Q_boundary_{self.name}')
        
        return variables
    
    def get_equations(self, variables: Dict[str, float], dt: float,
                     prev_states: Dict[str, float]) -> Dict[str, float]:
        """
        获取恒定水位水库模型的方程残差
        
        构建方程系统：
        1. 水位恒定约束：H_reservoir - constant_level = 0
        2. 边界流量平衡方程（可选）：计算维持恒定水位所需的边界调节流量
        
        Args:
            variables (Dict[str, float]): 当前时步所有变量值
            dt (float): 时间步长 (s)
            prev_states (Dict[str, float]): 上一时步状态值
        
        Returns:
            Dict[str, float]: 方程残差字典
        """
        equations = {}
        
        # 获取当前水位变量
        H_current = variables.get(f'H_{self.name}', self.constant_level)
        
        # 方程1：水位恒定约束
        # H_reservoir - constant_level = 0
        level_constraint = H_current - self.constant_level
        equations[f'constant_level_{self.name}'] = level_constraint
        
        # 方程2：边界流量平衡（如果启用）
        if self.enable_boundary_adjustment:
            boundary_flow_residual = self._calculate_boundary_flow_equation(
                variables, dt, prev_states)
            equations[f'boundary_flow_{self.name}'] = boundary_flow_residual
        
        return equations
    
    def _calculate_boundary_flow_equation(self, variables: Dict[str, float], 
                                        dt: float, prev_states: Dict[str, float]) -> float:
        """
        计算边界流量平衡方程残差
        
        边界调节流量 = 维持恒定水位所需的净流量补偿
        
        Args:
            variables (Dict[str, float]): 当前变量值
            dt (float): 时间步长
            prev_states (Dict[str, float]): 前一时步状态
        
        Returns:
            float: 边界流量方程残差
        """
        # 计算与连接结构的流量平衡
        net_structure_flow = self._calculate_net_structure_flow(variables)
        
        # 获取边界调节流量变量
        Q_boundary = variables.get(f'Q_boundary_{self.name}', 0.0)
        
        # 边界流量平衡方程
        if self.reservoir_type == 'upstream':
            # 上游水库：边界流量 + 结构流出量 = 0（维持水位恒定）
            residual = Q_boundary + net_structure_flow
        else:  # downstream
            # 下游水库：边界流量 - 结构流入量 = 0（维持水位恒定）
            residual = Q_boundary - net_structure_flow
        
        # 限制边界流量在合理范围内
        if abs(Q_boundary) > self.max_adjustment_rate:
            residual += 100.0 * (abs(Q_boundary) - self.max_adjustment_rate)
        
        return residual
    
    def _calculate_net_structure_flow(self, variables: Dict[str, float]) -> float:
        """
        计算与连接结构的净流量
        
        Args:
            variables (Dict[str, float]): 当前变量值
        
        Returns:
            float: 净流量 (m³/s)，正值表示流出水库，负值表示流入水库
        """
        net_flow = 0.0
        
        # 方法1：通过连接结构名称识别相关流量
        for struct_name in self.connected_structures:
            # 查找与该结构相关的流量变量
            for var_name, flow_value in variables.items():
                if var_name.startswith('Q_') and struct_name in var_name:
                    # 根据水库类型和变量命名判断流向
                    flow_direction = self._determine_flow_direction(
                        var_name, struct_name, flow_value)
                    net_flow += flow_direction * abs(flow_value)
        
        # 方法2：检查直接相关的边界流量变量
        for var_name, flow_value in variables.items():
            if var_name.startswith('Q_') and self.name in var_name:
                if var_name != f'Q_boundary_{self.name}':  # 排除自身的边界调节流量
                    # 根据命名约定判断流向
                    if 'in' in var_name or 'inlet' in var_name:
                        net_flow -= abs(flow_value)  # 流入水库
                    elif 'out' in var_name or 'outlet' in var_name:
                        net_flow += abs(flow_value)  # 流出水库
                    else:
                        # 根据流量符号判断
                        net_flow += flow_value
        
        return net_flow
    
    def _determine_flow_direction(self, var_name: str, struct_name: str, 
                                flow_value: float) -> int:
        """
        判断流量的方向相对于水库
        
        Args:
            var_name (str): 流量变量名
            struct_name (str): 结构名称
            flow_value (float): 流量值
        
        Returns:
            int: +1表示流出水库，-1表示流入水库
        """
        # 根据变量命名约定判断流向
        if self.reservoir_type == 'upstream':
            # 上游水库：通常结构流量为正表示流出水库
            if 'outlet' in var_name or 'out' in var_name:
                return +1  # 流出
            elif 'inlet' in var_name or 'in' in var_name:
                return -1  # 流入
            else:
                return +1 if flow_value >= 0 else -1
        else:  # downstream
            # 下游水库：通常结构流量为正表示流入水库
            if 'inlet' in var_name or 'in' in var_name:
                return -1  # 流入
            elif 'outlet' in var_name or 'out' in var_name:
                return +1  # 流出
            else:
                return -1 if flow_value >= 0 else +1
    
    def get_water_level(self) -> float:
        """
        获取恒定水位值
        
        Returns:
            float: 恒定水位 (m)
        """
        return self.constant_level
    
    def set_water_level(self, new_level: float):
        """
        更新恒定水位设定值
        
        Args:
            new_level (float): 新的恒定水位 (m)
        """
        if not isinstance(new_level, (int, float)) or math.isnan(new_level):
            raise ValueError("新水位必须是有效数值")
        self.constant_level = float(new_level)
    
    def get_boundary_flow_requirement(self, variables: Dict[str, float]) -> float:
        """
        计算维持恒定水位所需的边界调节流量
        
        Args:
            variables (Dict[str, float]): 当前变量值
        
        Returns:
            float: 所需边界调节流量 (m³/s)
        """
        net_structure_flow = self._calculate_net_structure_flow(variables)
        
        if self.reservoir_type == 'upstream':
            # 上游水库需要补充流出的水量
            return -net_structure_flow
        else:  # downstream
            # 下游水库需要排除流入的水量
            return net_structure_flow
    
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
        
        # 水位状态始终保持恒定
        new_states[f'H_{self.name}'] = self.constant_level
        
        # 更新累积蓄量变化（用于统计）
        if self.enable_boundary_adjustment:
            Q_boundary = variables.get(f'Q_boundary_{self.name}', 0.0)
            volume_change = Q_boundary * dt
            self._cumulative_volume_change += volume_change
            new_states[f'cumulative_volume_change_{self.name}'] = self._cumulative_volume_change
        
        # 记录边界流量历史
        if len(self._boundary_flow_history) > 100:  # 保持最近100个记录
            self._boundary_flow_history.pop(0)
        self._boundary_flow_history.append(
            variables.get(f'Q_boundary_{self.name}', 0.0))
        
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
        net_structure_flow = self._calculate_net_structure_flow(variables)
        boundary_flow = variables.get(f'Q_boundary_{self.name}', 0.0)
        
        stats = {
            'name': self.name,
            'type': 'constant_level_reservoir',
            'reservoir_type': self.reservoir_type,
            'constant_level': self.constant_level,
            'current_level': self.constant_level,  # 始终保持恒定
            'net_structure_flow': net_structure_flow,
            'boundary_adjustment_flow': boundary_flow,
            'cumulative_volume_change': self._cumulative_volume_change,
            'boundary_flow_active': self.enable_boundary_adjustment,
            'max_adjustment_capacity': self.max_adjustment_rate,
            'connected_structures': self.connected_structures.copy()
        }
        
        # 边界流量统计
        if self._boundary_flow_history:
            stats['boundary_flow_statistics'] = {
                'current': self._boundary_flow_history[-1],
                'average': sum(self._boundary_flow_history) / len(self._boundary_flow_history),
                'max': max(self._boundary_flow_history),
                'min': min(self._boundary_flow_history)
            }
        
        return stats
    
    def validate_operation(self, variables: Dict[str, float]) -> Dict[str, Any]:
        """
        验证运行状态
        
        Args:
            variables (Dict[str, float]): 当前变量值
        
        Returns:
            Dict[str, Any]: 验证结果
        """
        H_current = variables.get(f'H_{self.name}', self.constant_level)
        boundary_flow = variables.get(f'Q_boundary_{self.name}', 0.0)
        
        validation = {
            'level_constant': abs(H_current - self.constant_level) < 1e-6,
            'boundary_flow_reasonable': abs(boundary_flow) <= self.max_adjustment_rate,
            'physical_consistency': True,  # 恒定水位总是物理一致的
            'connected_structures_count': len(self.connected_structures),
            'warnings': []
        }
        
        # 检查警告条件
        if abs(boundary_flow) > 0.8 * self.max_adjustment_rate:
            validation['warnings'].append('边界调节流量接近最大值')
        
        if abs(self._cumulative_volume_change) > 0.1 * self.capacity:
            validation['warnings'].append('累积蓄量变化较大')
        
        return validation
    
    def __repr__(self) -> str:
        """模型的字符串表示"""
        return (f"ConstantLevelReservoir(name='{self.name}', "
                f"level={self.constant_level:.2f}m, "
                f"type='{self.reservoir_type}', "
                f"nodes={self.node_names})")


def create_upstream_reservoir(name: str, node: str, constant_level: float,
                            capacity: float = 5e6) -> ConstantLevelReservoir:
    """
    创建上游恒定水位水库（无限水源）
    
    Args:
        name (str): 水库名称
        node (str): 连接节点名称
        constant_level (float): 恒定水位 (m)
        capacity (float): 水库容量 (m³)
    
    Returns:
        ConstantLevelReservoir: 上游水库模型实例
    """
    return ConstantLevelReservoir(
        name=name,
        nodes=[node],
        constant_level=constant_level,
        reservoir_type='upstream',
        capacity=capacity,
        enable_boundary_adjustment=True,
        max_adjustment_rate=10000.0  # 大容量调节能力
    )


def create_downstream_reservoir(name: str, node: str, constant_level: float,
                              capacity: float = 3e6) -> ConstantLevelReservoir:
    """
    创建下游恒定水位水库（无限汇点）
    
    Args:
        name (str): 水库名称
        node (str): 连接节点名称
        constant_level (float): 恒定水位 (m)
        capacity (float): 水库容量 (m³)
    
    Returns:
        ConstantLevelReservoir: 下游水库模型实例
    """
    return ConstantLevelReservoir(
        name=name,
        nodes=[node],
        constant_level=constant_level,
        reservoir_type='downstream',
        capacity=capacity,
        enable_boundary_adjustment=True,
        max_adjustment_rate=10000.0  # 大容量调节能力
    )


def create_dual_reservoir_system(upstream_level: float = 120.0,
                               downstream_level: float = 100.0) -> tuple[ConstantLevelReservoir, ConstantLevelReservoir]:
    """
    创建设计文档中的双水库系统
    
    Args:
        upstream_level (float): 上游水库恒定水位 (m)
        downstream_level (float): 下游水库恒定水位 (m)
    
    Returns:
        tuple: (上游水库模型, 下游水库模型)
    """
    upstream_reservoir = create_upstream_reservoir(
        name='上游水库',
        node='上游节点',
        constant_level=upstream_level,
        capacity=5e6  # 5000万m³
    )
    
    downstream_reservoir = create_downstream_reservoir(
        name='下游水库',
        node='下游节点',
        constant_level=downstream_level,
        capacity=3e6  # 3000万m³
    )
    
    return upstream_reservoir, downstream_reservoir