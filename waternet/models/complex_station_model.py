"""
复杂枢纽站模型

实现包含多种水力机械设备的复杂枢纽站建模，如包含闸门、泵站、船闸等设备的综合枢纽。
采用层次化建模策略，处理设备特性、控制逻辑和系统级水量平衡。

设计策略:
1. 设备层：建模各种水力机械的流量特性
2. 控制层：处理设备的运行状态和控制逻辑  
3. 系统层：实现整体水量平衡和边界条件

变量系统:
- Q_{设备名}: 各水力设备的流量 (m³/s)
- H_{上游节点}: 上游水位边界条件 (m)
- H_{下游节点}: 下游水位边界条件 (m)
- Setting_{设备名}: 设备操作参数

Author: WaterNet Development Team
Date: 2024-10-04
"""

import math
from typing import Dict, List, Optional, Any, Union, Tuple
from ..interfaces.hydro_model import HydroModel

# 导入水力设备基类
try:
    from ...physical_objects.control_structure import (
        ControlStructure, GateModel, PumpModel, ValveModel, TurbineModel
    )
except ImportError:
    # 如果导入失败，定义本地基类
    from abc import ABC, abstractmethod
    
    class ControlStructure(ABC):
        def __init__(self, name: str):
            self.name = name
        
        @abstractmethod
        def get_flow(self, H_up: float, H_down: float, setting: float) -> float:
            pass


class ComplexStationModel(HydroModel):
    """
    复杂枢纽站模型
    
    用于建模包含多种水力机械设备的复杂枢纽，如包含闸门、泵站、船闸等设备的综合枢纽。
    通过层次化建模实现设备特性、控制逻辑和系统水量平衡的统一描述。
    
    Attributes:
        upstream_node (str): 上游连接节点
        downstream_node (str): 下游连接节点
        structures (Dict[str, ControlStructure]): 水力设备字典
        structure_settings (Dict[str, float]): 设备操作设置
        external_inflows (Dict[str, float]): 外部流入量
        external_outflows (Dict[str, float]): 外部流出量
        enable_mass_balance (bool): 是否启用质量守恒检查
    """
    
    def __init__(self, name: str, upstream_node: str, downstream_node: str,
                 structures: Optional[Dict[str, ControlStructure]] = None,
                 structure_settings: Optional[Dict[str, float]] = None,
                 external_inflows: Optional[Dict[str, float]] = None,
                 external_outflows: Optional[Dict[str, float]] = None,
                 enable_mass_balance: bool = True):
        """
        初始化复杂枢纽站模型
        
        Args:
            name (str): 枢纽站名称，在系统中必须唯一
            upstream_node (str): 上游连接节点名称
            downstream_node (str): 下游连接节点名称
            structures (Dict[str, ControlStructure], optional): 水力设备字典
            structure_settings (Dict[str, float], optional): 设备操作设置
            external_inflows (Dict[str, float], optional): 外部流入量配置
            external_outflows (Dict[str, float], optional): 外部流出量配置
            enable_mass_balance (bool): 是否启用质量守恒检查，默认True
        
        Raises:
            ValueError: 当参数不合理时抛出异常
        """
        super().__init__(name, [upstream_node, downstream_node])
        
        # 参数验证
        if not upstream_node or not isinstance(upstream_node, str):
            raise ValueError("上游节点名称必须是非空字符串")
        if not downstream_node or not isinstance(downstream_node, str):
            raise ValueError("下游节点名称必须是非空字符串")
        if upstream_node == downstream_node:
            raise ValueError("上游和下游节点不能相同")
        
        self.upstream_node = upstream_node.strip()
        self.downstream_node = downstream_node.strip()
        self.enable_mass_balance = enable_mass_balance
        
        # 初始化设备字典
        self.structures = structures or {}
        self.structure_settings = structure_settings or {}
        
        # 确保每个设备都有设置
        for struct_name in self.structures.keys():
            if struct_name not in self.structure_settings:
                self.structure_settings[struct_name] = 0.0  # 默认设置
        
        # 外部流量
        self.external_inflows = external_inflows or {}
        self.external_outflows = external_outflows or {}
        
        # 验证设备
        self._validate_structures()
    
    def _validate_structures(self):
        """验证水力设备配置"""
        for struct_name, structure in self.structures.items():
            if not isinstance(structure, ControlStructure):
                raise ValueError(f"设备 {struct_name} 必须是 ControlStructure 的实例")
            if structure.name != struct_name:
                raise ValueError(f"设备内部名称({structure.name})与字典键名({struct_name})不匹配")
    
    def get_variable_names(self) -> List[str]:
        """
        获取复杂枢纽站模型引入的变量名列表
        
        Returns:
            List[str]: 变量名列表，包含各设备的流量变量
        """
        variables = []
        
        # 各设备的流量变量
        for struct_name in self.structures.keys():
            variables.append(f'Q_{struct_name}')
        
        return variables
    
    def get_equations(self, variables: Dict[str, float], dt: float,
                     prev_states: Dict[str, float]) -> Dict[str, float]:
        """
        获取复杂枢纽站模型的方程残差
        
        构建方程系统：
        1. 设备特性方程：Q_设备 - get_flow(H_up, H_down, setting) = 0
        2. 总体水量平衡方程：sum(Q_in) - sum(Q_out) = 0 （可选）
        
        Args:
            variables (Dict[str, float]): 当前时步所有变量值
            dt (float): 时间步长 (s)
            prev_states (Dict[str, float]): 上一时步状态值
        
        Returns:
            Dict[str, float]: 方程残差字典
        """
        equations = {}
        
        # 获取上下游水位
        H_up = variables.get(f'H_{self.upstream_node}', 0.0)
        H_down = variables.get(f'H_{self.downstream_node}', 0.0)
        
        # 为每个设备构建特性方程
        for struct_name, structure in self.structures.items():
            Q_var_name = f'Q_{struct_name}'
            Q_actual = variables.get(Q_var_name, 0.0)
            
            # 获取设备设置
            setting = self.structure_settings.get(struct_name, 0.0)
            
            # 计算设备特性流量
            try:
                Q_characteristic = structure.get_flow(H_up, H_down, setting)
                
                # 设备特性方程残差
                residual = Q_actual - Q_characteristic
                equations[f'structure_flow_{struct_name}'] = residual
                
            except Exception as e:
                # 设备特性计算失败，使用大残差
                equations[f'structure_flow_{struct_name}'] = 1000.0
        
        # 可选的总体水量平衡方程
        if self.enable_mass_balance:
            mass_balance_residual = self._calculate_mass_balance(variables)
            equations[f'mass_balance_{self.name}'] = mass_balance_residual
        
        return equations
    
    def _calculate_mass_balance(self, variables: Dict[str, float]) -> float:
        """
        计算质量平衡残差
        
        质量平衡：总流入量 - 总流出量 = 0
        
        Args:
            variables (Dict[str, float]): 当前变量值
        
        Returns:
            float: 质量平衡残差
        """
        total_inflow = 0.0
        total_outflow = 0.0
        
        # 设备流量分类
        for struct_name in self.structures.keys():
            Q_struct = variables.get(f'Q_{struct_name}', 0.0)
            
            # 简化假设：根据设备类型判断流向
            # 实际应用中可能需要更复杂的逻辑
            if Q_struct >= 0:
                # 正流量视为从上游到下游
                total_outflow += Q_struct
            else:
                # 负流量视为从下游到上游
                total_inflow += abs(Q_struct)
        
        # 外部流量
        for inflow_name, inflow_rate in self.external_inflows.items():
            inflow_value = variables.get(inflow_name, inflow_rate)
            total_inflow += max(0.0, inflow_value)
        
        for outflow_name, outflow_rate in self.external_outflows.items():
            outflow_value = variables.get(outflow_name, outflow_rate)
            total_outflow += max(0.0, outflow_value)
        
        return total_inflow - total_outflow
    
    def add_structure(self, name: str, structure: ControlStructure, 
                     initial_setting: float = 0.0):
        """
        添加水力设备
        
        Args:
            name (str): 设备名称
            structure (ControlStructure): 水力设备实例
            initial_setting (float): 初始设置值
        """
        if not isinstance(structure, ControlStructure):
            raise ValueError("设备必须是 ControlStructure 的实例")
        
        self.structures[name] = structure
        self.structure_settings[name] = initial_setting
    
    def remove_structure(self, name: str):
        """
        移除水力设备
        
        Args:
            name (str): 设备名称
        """
        self.structures.pop(name, None)
        self.structure_settings.pop(name, None)
    
    def set_structure_setting(self, name: str, setting: float):
        """
        设置设备操作参数
        
        Args:
            name (str): 设备名称
            setting (float): 设置值
        """
        if name in self.structures:
            self.structure_settings[name] = setting
        else:
            raise ValueError(f"设备 {name} 不存在")
    
    def get_structure_setting(self, name: str) -> float:
        """
        获取设备操作参数
        
        Args:
            name (str): 设备名称
        
        Returns:
            float: 设置值
        """
        return self.structure_settings.get(name, 0.0)
    
    def calculate_total_capacity(self, H_up: float, H_down: float) -> float:
        """
        计算枢纽站总通过能力
        
        Args:
            H_up (float): 上游水位 (m)
            H_down (float): 下游水位 (m)
        
        Returns:
            float: 总通过能力 (m³/s)
        """
        total_capacity = 0.0
        
        for struct_name, structure in self.structures.items():
            try:
                # 假设设备在最大设置下运行
                max_setting = self._get_max_setting_for_structure(structure)
                capacity = structure.get_flow(H_up, H_down, max_setting)
                total_capacity += max(0.0, capacity)
            except:
                continue
        
        return total_capacity
    
    def _get_max_setting_for_structure(self, structure: ControlStructure) -> float:
        """
        获取设备的最大设置值
        
        Args:
            structure (ControlStructure): 水力设备
        
        Returns:
            float: 最大设置值
        """
        # 根据设备类型返回合理的最大设置
        if hasattr(structure, 'width'):  # 闸门
            return 10.0  # 假设最大开度10m
        elif 'Pump' in structure.__class__.__name__:  # 泵
            return 1.0   # 全速运行
        elif 'Valve' in structure.__class__.__name__:  # 阀门
            return 1.0   # 全开
        elif 'Turbine' in structure.__class__.__name__:  # 水轮机
            return 100.0  # 假设最大流量100m³/s
        else:
            return 1.0   # 默认值
    
    def get_operation_statistics(self, variables: Dict[str, float],
                               H_up: float, H_down: float) -> Dict[str, Any]:
        """
        获取运行统计信息
        
        Args:
            variables (Dict[str, float]): 当前变量值
            H_up (float): 上游水位 (m)
            H_down (float): 下游水位 (m)
        
        Returns:
            Dict[str, Any]: 统计信息字典
        """
        stats = {
            'station_name': self.name,
            'upstream_level': H_up,
            'downstream_level': H_down,
            'head_difference': H_up - H_down,
            'total_flow': 0.0,
            'structure_flows': {},
            'structure_settings': self.structure_settings.copy(),
            'mass_balance_error': 0.0,
            'total_capacity': self.calculate_total_capacity(H_up, H_down)
        }
        
        # 各设备流量统计
        for struct_name in self.structures.keys():
            Q_struct = variables.get(f'Q_{struct_name}', 0.0)
            stats['structure_flows'][struct_name] = Q_struct
            stats['total_flow'] += Q_struct
        
        # 质量平衡误差
        if self.enable_mass_balance:
            stats['mass_balance_error'] = self._calculate_mass_balance(variables)
        
        return stats
    
    def validate_operating_conditions(self, H_up: float, H_down: float) -> Dict[str, bool]:
        """
        验证运行条件
        
        Args:
            H_up (float): 上游水位 (m)
            H_down (float): 下游水位 (m)
        
        Returns:
            Dict[str, bool]: 验证结果 {设备名: 是否满足运行条件}
        """
        validation_results = {}
        
        for struct_name, structure in self.structures.items():
            try:
                setting = self.structure_settings.get(struct_name, 0.0)
                
                # 尝试计算流量，检查是否出现异常
                flow = structure.get_flow(H_up, H_down, setting)
                
                # 基本合理性检查
                is_valid = (
                    not math.isnan(flow) and 
                    not math.isinf(flow) and
                    flow >= 0  # 假设流量非负
                )
                
                validation_results[struct_name] = is_valid
                
            except Exception:
                validation_results[struct_name] = False
        
        return validation_results
    
    def optimize_settings(self, target_flow: float, H_up: float, H_down: float,
                         max_iterations: int = 50) -> Dict[str, float]:
        """
        优化设备设置以达到目标流量
        
        简化的优化算法，实际应用中可能需要更复杂的优化方法。
        
        Args:
            target_flow (float): 目标总流量 (m³/s)
            H_up (float): 上游水位 (m)
            H_down (float): 下游水位 (m)
            max_iterations (int): 最大迭代次数
        
        Returns:
            Dict[str, float]: 优化后的设置 {设备名: 设置值}
        """
        if not self.structures:
            return {}
        
        # 简化优化：假设所有设备按比例调节
        optimized_settings = self.structure_settings.copy()
        
        for iteration in range(max_iterations):
            # 计算当前总流量
            current_flow = 0.0
            for struct_name, structure in self.structures.items():
                setting = optimized_settings.get(struct_name, 0.0)
                try:
                    flow = structure.get_flow(H_up, H_down, setting)
                    current_flow += max(0.0, flow)
                except:
                    continue
            
            # 检查收敛
            if abs(current_flow - target_flow) < 0.01:
                break
            
            # 简单调节：按比例缩放所有设置
            if current_flow > 0:
                scale_factor = target_flow / current_flow
                scale_factor = max(0.1, min(2.0, scale_factor))  # 限制调节幅度
                
                for struct_name in optimized_settings:
                    optimized_settings[struct_name] *= scale_factor
                    # 限制设置范围
                    optimized_settings[struct_name] = max(0.0, 
                        min(self._get_max_setting_for_structure(self.structures[struct_name]),
                            optimized_settings[struct_name]))
        
        return optimized_settings
    
    def __repr__(self) -> str:
        """模型的字符串表示"""
        return (f"ComplexStationModel(name='{self.name}', "
                f"upstream='{self.upstream_node}', downstream='{self.downstream_node}', "
                f"structures={list(self.structures.keys())})")


def create_gate_station(name: str, upstream_node: str, downstream_node: str,
                       gate_configs: List[Dict[str, Any]]) -> ComplexStationModel:
    """
    创建闸门站
    
    Args:
        name (str): 站名
        upstream_node (str): 上游节点
        downstream_node (str): 下游节点
        gate_configs (List[Dict]): 闸门配置列表
            格式: [{'name': str, 'width': float, 'discharge_coeff': float, 'initial_opening': float}]
    
    Returns:
        ComplexStationModel: 闸门站模型
    """
    structures = {}
    settings = {}
    
    for config in gate_configs:
        gate_name = config['name']
        width = config.get('width', 10.0)
        coeff = config.get('discharge_coeff', 0.7)
        opening = config.get('initial_opening', 0.0)
        
        # 创建简化闸门模型
        class SimpleGate(ControlStructure):
            def __init__(self, name, width, coeff):
                super().__init__(name)
                self.width = width
                self.coeff = coeff
            
            def get_flow(self, H_up, H_down, setting):
                if setting <= 0 or H_up <= H_down:
                    return 0.0
                area = self.width * setting
                return self.coeff * area * math.sqrt(2 * 9.81 * (H_up - H_down))
        
        structures[gate_name] = SimpleGate(gate_name, width, coeff)
        settings[gate_name] = opening
    
    return ComplexStationModel(name, upstream_node, downstream_node, 
                              structures, settings)


def create_pump_station(name: str, upstream_node: str, downstream_node: str,
                       pump_configs: List[Dict[str, Any]]) -> ComplexStationModel:
    """
    创建泵站
    
    Args:
        name (str): 站名
        upstream_node (str): 上游节点
        downstream_node (str): 下游节点
        pump_configs (List[Dict]): 泵配置列表
            格式: [{'name': str, 'curve_coeffs': List[float], 'initial_speed': float}]
    
    Returns:
        ComplexStationModel: 泵站模型
    """
    structures = {}
    settings = {}
    
    for config in pump_configs:
        pump_name = config['name']
        curve_coeffs = config.get('curve_coeffs', [50.0, -0.01])  # 默认特性曲线
        speed = config.get('initial_speed', 0.0)
        
        # 创建简化泵模型
        class SimplePump(ControlStructure):
            def __init__(self, name, coeffs):
                super().__init__(name)
                self.coeffs = coeffs
            
            def get_flow(self, H_up, H_down, setting):
                if setting <= 0:
                    return 0.0
                
                H_required = H_down - H_up
                # 简化求解：假设线性特性曲线 H = c0 + c1*Q
                if len(self.coeffs) >= 2:
                    c0, c1 = self.coeffs[0], self.coeffs[1]
                    if abs(c1) > 1e-10:
                        Q = (c0 - H_required) / (-c1)
                        return max(0.0, Q * setting)  # setting为速度比例
                return 0.0
        
        structures[pump_name] = SimplePump(pump_name, curve_coeffs)
        settings[pump_name] = speed
    
    return ComplexStationModel(name, upstream_node, downstream_node, 
                              structures, settings)