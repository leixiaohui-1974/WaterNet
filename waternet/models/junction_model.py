"""
连接点模型

实现多个水力对象汇流或分流的连接点建模，确保系统的水量守恒。
连接点基于质量守恒定律，实现不同水力构筑物之间的流量平衡。

设计原理:
1. 质量守恒：流入连接点的总流量 = 流出连接点的总流量
2. 水位一致性：所有连接对象在该点具有相同的水位
3. 无存储特性：连接点本身不存储水量

变量定义:
- H_{连接点名}: 连接点水位 (m)
- Q_{对象名}_{位置}: 各连接对象的流量 (m³/s)

Author: WaterNet Development Team
Date: 2024-10-04
"""

import math
from typing import Dict, List, Optional, Any, Union, Tuple
from ..interfaces.hydro_model import HydroModel


class JunctionModel(HydroModel):
    """
    连接点模型
    
    实现多个水力对象汇流或分流的连接点建模。基于质量守恒定律，
    确保流入连接点的总流量等于流出连接点的总流量。
    
    Attributes:
        connected_objects (List[str]): 连接的水力对象名称列表
        flow_directions (Dict[str, str]): 流向映射 {对象名: 'in'/'out'/'auto'}
        elevation (float): 连接点底标高 (m)
        loss_coefficients (Dict[str, float]): 局部水头损失系数
    """
    
    def __init__(self, name: str, connected_objects: List[str],
                 flow_directions: Optional[Dict[str, str]] = None,
                 elevation: float = 0.0,
                 loss_coefficients: Optional[Dict[str, float]] = None):
        """
        初始化连接点模型
        
        Args:
            name (str): 连接点名称，在系统中必须唯一
            connected_objects (List[str]): 连接的水力对象名称列表
            flow_directions (Dict[str, str], optional): 流向映射
                格式: {对象名: 'in'/'out'/'auto'}
                'in': 流入连接点, 'out': 流出连接点, 'auto': 自动判断
            elevation (float): 连接点底标高 (m)，默认为0
            loss_coefficients (Dict[str, float], optional): 局部水头损失系数
                格式: {对象名: 损失系数}
        
        Raises:
            ValueError: 当参数不合理时抛出异常
        """
        # 连接点的节点名称就是其自身
        super().__init__(name, [name])
        
        # 参数验证
        if not connected_objects or len(connected_objects) < 2:
            raise ValueError("连接点至少需要连接2个水力对象")
        
        for obj_name in connected_objects:
            if not isinstance(obj_name, str) or not obj_name.strip():
                raise ValueError(f"连接对象名称必须是非空字符串: {obj_name}")
        
        self.connected_objects = [obj.strip() for obj in connected_objects]
        self.elevation = float(elevation)
        
        # 流向配置
        self.flow_directions = flow_directions or {}
        for obj_name in self.connected_objects:
            if obj_name not in self.flow_directions:
                self.flow_directions[obj_name] = 'auto'  # 默认自动判断
        
        # 验证流向配置
        for obj_name, direction in self.flow_directions.items():
            if direction not in ['in', 'out', 'auto']:
                raise ValueError(f"流向必须是'in'、'out'或'auto': {obj_name}={direction}")
        
        # 局部损失系数
        self.loss_coefficients = loss_coefficients or {}
        for obj_name in self.connected_objects:
            if obj_name not in self.loss_coefficients:
                self.loss_coefficients[obj_name] = 0.0  # 默认无损失
    
    def get_variable_names(self) -> List[str]:
        """
        获取连接点模型引入的变量名列表
        
        Returns:
            List[str]: 变量名列表，包含连接点水位变量
        """
        return [f'H_{self.name}']
    
    def get_equations(self, variables: Dict[str, float], dt: float, 
                     prev_states: Dict[str, float]) -> Dict[str, float]:
        """
        获取连接点模型的方程残差
        
        构建质量守恒方程：sum(Q_in) - sum(Q_out) = 0
        
        Args:
            variables (Dict[str, float]): 当前时步所有变量值
            dt (float): 时间步长 (s)
            prev_states (Dict[str, float]): 上一时步状态值
        
        Returns:
            Dict[str, float]: 方程残差字典
        """
        # 识别和分类流量
        Q_in_list, Q_out_list = self._classify_flows(variables)
        
        # 计算总流量
        Q_in_total = sum(Q_in_list)
        Q_out_total = sum(Q_out_list)
        
        # 构建质量守恒方程残差
        mass_balance_residual = Q_in_total - Q_out_total
        
        equations = {
            f'mass_balance_{self.name}': mass_balance_residual
        }
        
        return equations
    
    def _classify_flows(self, variables: Dict[str, float]) -> Tuple[List[float], List[float]]:
        """
        分类和识别连接到此连接点的流量
        
        根据变量命名约定和流向配置，识别哪些流量是流入，哪些是流出。
        
        流量识别规则：
        1. 优先使用flow_directions配置
        2. 根据变量名后缀判断：_start/_inlet/_in -> 流入，_end/_outlet/_out -> 流出
        3. 根据流量符号判断：正值为流入，负值为流出
        
        Args:
            variables (Dict[str, float]): 当前变量值
        
        Returns:
            Tuple[List[float], List[float]]: (流入流量列表, 流出流量列表)
        """
        Q_in_list = []
        Q_out_list = []
        
        # 遍历所有流量变量
        for var_name, flow_value in variables.items():
            if not var_name.startswith('Q_'):
                continue
            
            # 检查是否与此连接点相关
            related_object = None
            for obj_name in self.connected_objects:
                if obj_name in var_name:
                    related_object = obj_name
                    break
            
            # 检查连接点自身的流量变量
            if related_object is None and self.name in var_name:
                related_object = self.name
            
            if related_object is None:
                continue
            
            # 确定流向
            direction = self._determine_flow_direction(var_name, flow_value, related_object)
            
            # 分类流量
            if direction == 'in':
                Q_in_list.append(abs(flow_value))
            elif direction == 'out':
                Q_out_list.append(abs(flow_value))
        
        return Q_in_list, Q_out_list
    
    def _determine_flow_direction(self, var_name: str, flow_value: float, 
                                obj_name: str) -> str:
        """
        确定流量方向
        
        Args:
            var_name (str): 变量名
            flow_value (float): 流量值
            obj_name (str): 对象名
        
        Returns:
            str: 'in' 或 'out'
        """
        # 方法1：使用预设的流向配置
        if obj_name in self.flow_directions and self.flow_directions[obj_name] != 'auto':
            return self.flow_directions[obj_name]
        
        # 方法2：根据变量名后缀判断
        var_lower = var_name.lower()
        
        # 流入指示符
        if any(suffix in var_lower for suffix in ['_start', '_inlet', '_in', '_upstream']):
            return 'in'
        
        # 流出指示符
        if any(suffix in var_lower for suffix in ['_end', '_outlet', '_out', '_downstream']):
            return 'out'
        
        # 连接点相关的特殊命名
        if f'_{self.name.lower()}_' in var_lower:
            if 'in' in var_lower or 'inflow' in var_lower:
                return 'in'
            elif 'out' in var_lower or 'outflow' in var_lower:
                return 'out'
        
        # 方法3：根据流量符号判断（默认）
        return 'in' if flow_value >= 0 else 'out'
    
    def get_junction_water_level(self, variables: Dict[str, float]) -> float:
        """
        获取连接点水位
        
        Args:
            variables (Dict[str, float]): 当前变量值
        
        Returns:
            float: 连接点水位 (m)
        """
        return variables.get(f'H_{self.name}', self.elevation)
    
    def calculate_head_losses(self, variables: Dict[str, float]) -> Dict[str, float]:
        """
        计算各连接对象的局部水头损失
        
        水头损失计算公式：ΔH = K × V²/(2g)，其中V = Q/A
        
        Args:
            variables (Dict[str, float]): 当前变量值
        
        Returns:
            Dict[str, float]: 水头损失字典 {对象名: 损失值(m)}
        """
        losses = {}
        g = 9.81  # 重力加速度
        
        for obj_name in self.connected_objects:
            # 查找对象流量
            flow_rate = 0.0
            for var_name, value in variables.items():
                if var_name.startswith('Q_') and obj_name in var_name:
                    flow_rate = abs(value)
                    break
            
            # 计算水头损失（假设管道面积为1m²，实际应从几何参数获取）
            K = self.loss_coefficients.get(obj_name, 0.0)
            if K > 0 and flow_rate > 0:
                # 简化计算：假设流速 = 流量（面积=1m²）
                velocity = flow_rate
                head_loss = K * velocity * velocity / (2 * g)
                losses[obj_name] = head_loss
            else:
                losses[obj_name] = 0.0
        
        return losses
    
    def validate_mass_balance(self, variables: Dict[str, float], 
                            tolerance: float = 1e-6) -> bool:
        """
        验证质量平衡是否满足
        
        Args:
            variables (Dict[str, float]): 当前变量值
            tolerance (float): 容差
        
        Returns:
            bool: True表示满足质量平衡
        """
        Q_in_list, Q_out_list = self._classify_flows(variables)
        Q_in_total = sum(Q_in_list)
        Q_out_total = sum(Q_out_list)
        
        mass_balance_error = abs(Q_in_total - Q_out_total)
        return mass_balance_error <= tolerance
    
    def get_flow_statistics(self, variables: Dict[str, float]) -> Dict[str, Any]:
        """
        获取流量统计信息
        
        Args:
            variables (Dict[str, float]): 当前变量值
        
        Returns:
            Dict[str, Any]: 统计信息字典
        """
        Q_in_list, Q_out_list = self._classify_flows(variables)
        
        stats = {
            'junction_name': self.name,
            'connected_objects': self.connected_objects,
            'total_inflow': sum(Q_in_list),
            'total_outflow': sum(Q_out_list),
            'mass_balance_error': sum(Q_in_list) - sum(Q_out_list),
            'individual_inflows': Q_in_list,
            'individual_outflows': Q_out_list,
            'water_level': self.get_junction_water_level(variables),
            'head_losses': self.calculate_head_losses(variables)
        }
        
        return stats
    
    def add_connected_object(self, object_name: str, flow_direction: str = 'auto',
                           loss_coefficient: float = 0.0):
        """
        添加连接对象
        
        Args:
            object_name (str): 对象名称
            flow_direction (str): 流向 ('in'/'out'/'auto')
            loss_coefficient (float): 局部损失系数
        """
        if object_name not in self.connected_objects:
            self.connected_objects.append(object_name)
            self.flow_directions[object_name] = flow_direction
            self.loss_coefficients[object_name] = loss_coefficient
    
    def remove_connected_object(self, object_name: str):
        """
        移除连接对象
        
        Args:
            object_name (str): 对象名称
        """
        if object_name in self.connected_objects:
            self.connected_objects.remove(object_name)
            self.flow_directions.pop(object_name, None)
            self.loss_coefficients.pop(object_name, None)
    
    def set_flow_direction(self, object_name: str, direction: str):
        """
        设置对象流向
        
        Args:
            object_name (str): 对象名称
            direction (str): 流向 ('in'/'out'/'auto')
        """
        if object_name in self.connected_objects:
            if direction in ['in', 'out', 'auto']:
                self.flow_directions[object_name] = direction
            else:
                raise ValueError(f"无效的流向: {direction}")
    
    def __repr__(self) -> str:
        """模型的字符串表示"""
        return (f"JunctionModel(name='{self.name}', "
                f"connected_objects={self.connected_objects}, "
                f"elevation={self.elevation})")


class FlowSplitterJunction(JunctionModel):
    """
    流量分配连接点
    
    特殊的连接点，支持按比例分配流量到不同的出口。
    
    Attributes:
        split_ratios (Dict[str, float]): 分流比例 {出口对象名: 比例}
    """
    
    def __init__(self, name: str, inlet_object: str, outlet_objects: List[str],
                 split_ratios: Optional[Dict[str, float]] = None,
                 elevation: float = 0.0):
        """
        初始化流量分配连接点
        
        Args:
            name (str): 连接点名称
            inlet_object (str): 入口对象名称
            outlet_objects (List[str]): 出口对象名称列表
            split_ratios (Dict[str, float], optional): 分流比例，总和应为1.0
            elevation (float): 连接点标高
        """
        all_objects = [inlet_object] + outlet_objects
        super().__init__(name, all_objects, elevation=elevation)
        
        self.inlet_object = inlet_object
        self.outlet_objects = outlet_objects
        
        # 设置流向
        self.flow_directions[inlet_object] = 'in'
        for outlet in outlet_objects:
            self.flow_directions[outlet] = 'out'
        
        # 分流比例
        if split_ratios is None:
            # 默认等比例分流
            ratio = 1.0 / len(outlet_objects)
            self.split_ratios = {outlet: ratio for outlet in outlet_objects}
        else:
            self.split_ratios = split_ratios.copy()
            # 验证比例总和
            total_ratio = sum(self.split_ratios.values())
            if abs(total_ratio - 1.0) > 1e-6:
                raise ValueError(f"分流比例总和必须为1.0，当前为{total_ratio}")
    
    def get_equations(self, variables: Dict[str, float], dt: float,
                     prev_states: Dict[str, float]) -> Dict[str, float]:
        """
        获取分流连接点的方程残差
        
        除了质量守恒方程外，还包括分流比例约束方程。
        """
        equations = super().get_equations(variables, dt, prev_states)
        
        # 获取入口流量
        Q_inlet = 0.0
        for var_name, value in variables.items():
            if var_name.startswith('Q_') and self.inlet_object in var_name:
                Q_inlet = abs(value)
                break
        
        # 添加分流比例约束方程
        for outlet_obj in self.outlet_objects:
            # 查找出口流量
            Q_outlet = 0.0
            for var_name, value in variables.items():
                if var_name.startswith('Q_') and outlet_obj in var_name:
                    Q_outlet = abs(value)
                    break
            
            # 分流比例约束：Q_outlet - ratio * Q_inlet = 0
            expected_flow = self.split_ratios.get(outlet_obj, 0.0) * Q_inlet
            residual = Q_outlet - expected_flow
            equations[f'split_ratio_{outlet_obj}'] = residual
        
        return equations
    
    def update_split_ratios(self, new_ratios: Dict[str, float]):
        """
        更新分流比例
        
        Args:
            new_ratios (Dict[str, float]): 新的分流比例
        """
        total_ratio = sum(new_ratios.values())
        if abs(total_ratio - 1.0) > 1e-6:
            raise ValueError(f"分流比例总和必须为1.0，当前为{total_ratio}")
        
        self.split_ratios.update(new_ratios)


def create_simple_junction(name: str, *connected_objects: str) -> JunctionModel:
    """
    创建简单的连接点模型
    
    Args:
        name (str): 连接点名称
        *connected_objects (str): 连接的对象名称
    
    Returns:
        JunctionModel: 连接点模型实例
    """
    return JunctionModel(name, list(connected_objects))


def create_confluence_junction(name: str, upstream_objects: List[str],
                             downstream_object: str) -> JunctionModel:
    """
    创建汇流连接点（多入一出）
    
    Args:
        name (str): 连接点名称
        upstream_objects (List[str]): 上游对象名称列表
        downstream_object (str): 下游对象名称
    
    Returns:
        JunctionModel: 连接点模型实例
    """
    all_objects = upstream_objects + [downstream_object]
    flow_directions = {}
    
    # 设置流向
    for obj in upstream_objects:
        flow_directions[obj] = 'in'
    flow_directions[downstream_object] = 'out'
    
    return JunctionModel(name, all_objects, flow_directions)


def create_bifurcation_junction(name: str, upstream_object: str,
                               downstream_objects: List[str],
                               split_ratios: Optional[Dict[str, float]] = None) -> FlowSplitterJunction:
    """
    创建分流连接点（一入多出）
    
    Args:
        name (str): 连接点名称
        upstream_object (str): 上游对象名称
        downstream_objects (List[str]): 下游对象名称列表
        split_ratios (Dict[str, float], optional): 分流比例
    
    Returns:
        FlowSplitterJunction: 分流连接点模型实例
    """
    return FlowSplitterJunction(name, upstream_object, downstream_objects, split_ratios)