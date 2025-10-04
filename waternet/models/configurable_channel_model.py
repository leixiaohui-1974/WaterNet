"""
配置驱动的明渠水力计算模块

基于配置文件实现明渠段的水力计算，支持恒定流和非恒定流计算。
集成WaterNet的圣维南模型，提供配置驱动的参数设置和求解控制。

设计特点:
1. 配置驱动：渠道几何、水力参数通过配置文件定义
2. 多求解器支持：标准Preissmann格式、增强求解器等
3. 自适应网格：根据配置自动生成计算网格
4. 边界条件处理：与上下游水力结构的耦合

Author: WaterNet Development Team
Date: 2024-10-05
"""

import math
import numpy as np
from typing import Dict, List, Optional, Any, Callable, Tuple
from ..interfaces.hydro_model import HydroModel
from .saint_venant import SaintVenantModel


class ConfigurableChannelModel(HydroModel):
    """
    可配置明渠模型
    
    基于配置文件的明渠段水力计算模型。支持不同的几何形状、
    边界条件和求解器配置。自动处理网格生成和边界耦合。
    
    Attributes:
        channel_config (Dict): 明渠配置字典
        length (float): 渠道长度 (m)
        bottom_width (float): 底宽 (m)
        side_slope (float): 边坡系数
        bottom_slope (float): 底坡
        roughness (float): 曼宁糙率系数
        num_segments (int): 计算分段数
        solver_type (str): 求解器类型
        internal_nodes (List[str]): 内部节点列表
        saint_venant_model (SaintVenantModel): 底层圣维南模型
    """
    
    def __init__(self, name: str, channel_config: Dict[str, Any]):
        """
        基于配置初始化明渠模型
        
        Args:
            name (str): 明渠段名称
            channel_config (Dict): 明渠配置字典
        
        Raises:
            ValueError: 当配置参数不合理时抛出异常
        """
        # 解析配置
        self.channel_config = channel_config
        
        # 解析位置信息
        location = channel_config.get('location', {})
        upstream_node = location.get('upstream_node')
        downstream_node = location.get('downstream_node')
        
        if not upstream_node or not downstream_node:
            raise ValueError(f"明渠段 {name} 必须配置上下游节点")
        
        # 解析几何参数
        geometry = channel_config.get('geometry', {})
        self.length = float(geometry.get('length', 1000.0))
        self.bottom_width = float(geometry.get('bottom_width', 10.0))
        self.side_slope = float(geometry.get('side_slope', 1.5))
        
        # 计算底坡
        elevation_upstream = float(geometry.get('bottom_elevation_upstream', 100.0))
        elevation_downstream = float(geometry.get('bottom_elevation_downstream', 99.0))
        self.bottom_slope = (elevation_upstream - elevation_downstream) / self.length
        
        # 如果直接提供底坡，则优先使用
        if 'bottom_slope' in geometry:
            self.bottom_slope = float(geometry['bottom_slope'])
        
        # 解析水力参数
        hydraulics = channel_config.get('hydraulics', {})
        self.roughness = float(hydraulics.get('roughness_coefficient', 0.025))
        self.minimum_depth = float(hydraulics.get('minimum_depth', 0.1))
        
        # 解析离散化参数
        discretization = channel_config.get('discretization', {})
        self.num_segments = int(discretization.get('num_segments', 10))
        self.solver_type = discretization.get('solver_type', 'preissmann')
        
        # 生成内部节点
        self.upstream_node = upstream_node
        self.downstream_node = downstream_node
        self.internal_nodes = self._generate_internal_nodes(name, upstream_node, downstream_node)
        
        # 初始化基类
        super().__init__(name, self.internal_nodes)
        
        # 验证配置
        self._validate_configuration()
        
        # 创建底层圣维南模型
        self.saint_venant_model = self._create_saint_venant_model()
        
        # 内部状态
        self._steady_state_computed = False
        self._water_surface_profile = {}
        self._flow_velocities = {}
    
    def _generate_internal_nodes(self, channel_name: str, upstream_node: str, 
                                downstream_node: str) -> List[str]:
        """
        生成内部计算节点
        
        Args:
            channel_name (str): 明渠段名称
            upstream_node (str): 上游节点
            downstream_node (str): 下游节点
        
        Returns:
            List[str]: 内部节点名称列表
        """
        nodes = []
        
        for i in range(self.num_segments + 1):
            if i == 0:
                nodes.append(upstream_node)
            elif i == self.num_segments:
                nodes.append(downstream_node)
            else:
                nodes.append(f"{channel_name}_node_{i}")
        
        return nodes
    
    def _validate_configuration(self):
        """验证配置参数"""
        if self.length <= 0:
            raise ValueError("渠道长度必须为正值")
        if self.bottom_width <= 0:
            raise ValueError("底宽必须为正值")
        if self.side_slope < 0:
            raise ValueError("边坡系数不能为负")
        if self.roughness <= 0:
            raise ValueError("糙率系数必须为正值")
        if self.num_segments < 1:
            raise ValueError("分段数至少为1")
        if self.minimum_depth <= 0:
            raise ValueError("最小水深必须为正值")
    
    def _generate_sections_data(self) -> List[Dict[str, Any]]:
        """
        根据明渠配置生成断面数据
        
        Returns:
            List[Dict[str, Any]]: 断面数据列表
        """
        sections = []
        
        # 上游断面
        upstream_elevation = float(self.channel_config.get('geometry', {}).get('bottom_elevation_upstream', 100.0))
        sections.append({
            'mileage': 0.0,
            'elevation': upstream_elevation,
            'roughness': float(self.roughness),
            'area_func': self._create_area_function(),
            'top_width_func': self._create_top_width_function()
        })
        
        # 下游断面
        downstream_elevation = float(self.channel_config.get('geometry', {}).get('bottom_elevation_downstream', 99.0))
        sections.append({
            'mileage': float(self.length),
            'elevation': downstream_elevation,
            'roughness': float(self.roughness),
            'area_func': self._create_area_function(),
            'top_width_func': self._create_top_width_function()
        })
        
        return sections
    
    def _create_area_function(self) -> Callable[[float], float]:
        """创建面积函数"""
        def area_func(H: float) -> float:
            # 梯形断面面积公式: A = (b + m*h) * h
            depth = max(0.0, H)
            return (float(self.bottom_width) + float(self.side_slope) * depth) * depth
        return area_func
    
    def _create_top_width_function(self) -> Callable[[float], float]:
        """创建水面宽函数"""
        def top_width_func(H: float) -> float:
            # 梯形断面水面宽公式: T = b + 2*m*h
            depth = max(0.0, H)
            return float(self.bottom_width) + 2 * float(self.side_slope) * depth
        return top_width_func

    def _create_saint_venant_model(self) -> SaintVenantModel:
        """
        创建底层圣维南模型
        
        Returns:
            SaintVenantModel: 配置好的圣维南模型
        """
        try:
            # 根据明渠配置生成断面数据
            sections = self._generate_sections_data()
            
            model = SaintVenantModel(
                name=f"{self.name}_sv",
                upstream_node=self.upstream_node,
                downstream_node=self.downstream_node,
                sections=sections,
                solver_type=self.solver_type
            )
            return model
        except Exception as e:
            raise ValueError(f"创建圣维南模型失败: {e}")
    
    def get_variable_names(self) -> List[str]:
        """
        获取明渠模型引入的变量名列表
        
        Returns:
            List[str]: 变量名列表，包含各节点的水位和流量变量
        """
        return self.saint_venant_model.get_variable_names()
    
    def get_equations(self, variables: Dict[str, float], dt: float,
                     prev_states: Dict[str, float]) -> Dict[str, float]:
        """
        获取明渠模型的方程残差
        
        Args:
            variables (Dict[str, float]): 当前时步所有变量值
            dt (float): 时间步长 (s)
            prev_states (Dict[str, float]): 上一时步状态值
        
        Returns:
            Dict[str, float]: 方程残差字典
        """
        return self.saint_venant_model.get_equations(variables, dt, prev_states)
    
    def compute_steady_state(self, boundary_conditions: Dict[str, float]) -> Dict[str, float]:
        """
        计算恒定流水面线
        
        Args:
            boundary_conditions (Dict[str, float]): 边界条件
                格式: {节点名: 水位值(m)}
        
        Returns:
            Dict[str, float]: 恒定流解 {节点名: 水位(m)}
        """
        try:
            steady_solution = self.saint_venant_model.compute_steady_state(boundary_conditions)
            self._steady_state_computed = True
            self._water_surface_profile = steady_solution.copy()
            
            # 计算流速分布
            self._compute_velocity_distribution(steady_solution)
            
            return steady_solution
            
        except Exception as e:
            raise ValueError(f"恒定流计算失败: {e}")
    
    def _compute_velocity_distribution(self, water_levels: Dict[str, float]):
        """
        计算流速分布
        
        Args:
            water_levels (Dict[str, float]): 各节点水位
        """
        self._flow_velocities = {}
        
        # 简化流速计算（基于曼宁公式）
        for i, node in enumerate(self.internal_nodes):
            if node in water_levels:
                h = water_levels[node]
                
                # 计算底高程
                distance_ratio = i / (len(self.internal_nodes) - 1)
                bottom_elevation = (1 - distance_ratio) * self._get_upstream_elevation() + \
                                 distance_ratio * self._get_downstream_elevation()
                
                # 水深
                depth = max(0.1, h - bottom_elevation)
                
                # 水力半径（矩形+梯形断面）
                wetted_perimeter = self.bottom_width + 2 * depth * math.sqrt(1 + self.side_slope**2)
                cross_area = (self.bottom_width + self.side_slope * depth) * depth
                hydraulic_radius = cross_area / wetted_perimeter if wetted_perimeter > 0 else 0
                
                # 曼宁公式计算流速
                if hydraulic_radius > 0 and self.bottom_slope > 0:
                    velocity = (1 / self.roughness) * (hydraulic_radius ** (2/3)) * \
                              math.sqrt(self.bottom_slope)
                else:
                    velocity = 0.0
                
                self._flow_velocities[node] = velocity
    
    def _get_upstream_elevation(self) -> float:
        """获取上游底高程"""
        geometry = self.channel_config.get('geometry', {})
        return float(geometry.get('bottom_elevation_upstream', 100.0))
    
    def _get_downstream_elevation(self) -> float:
        """获取下游底高程"""
        geometry = self.channel_config.get('geometry', {})
        return float(geometry.get('bottom_elevation_downstream', 99.0))
    
    def get_water_surface_profile(self) -> Dict[str, float]:
        """
        获取水面线
        
        Returns:
            Dict[str, float]: 水面线 {节点名: 水位(m)}
        """
        return self._water_surface_profile.copy()
    
    def get_velocity_profile(self) -> Dict[str, float]:
        """
        获取流速分布
        
        Returns:
            Dict[str, float]: 流速分布 {节点名: 流速(m/s)}
        """
        return self._flow_velocities.copy()
    
    def get_cross_section_properties(self, node_name: str, water_level: float) -> Dict[str, float]:
        """
        获取指定节点的断面特性
        
        Args:
            node_name (str): 节点名称
            water_level (float): 水位 (m)
        
        Returns:
            Dict[str, float]: 断面特性字典
        """
        if node_name not in self.internal_nodes:
            raise ValueError(f"节点 {node_name} 不存在")
        
        # 计算节点位置
        node_index = self.internal_nodes.index(node_name)
        distance_ratio = node_index / (len(self.internal_nodes) - 1)
        
        # 底高程
        upstream_elev = self._get_upstream_elevation()
        downstream_elev = self._get_downstream_elevation()
        bottom_elevation = (1 - distance_ratio) * upstream_elev + distance_ratio * downstream_elev
        
        # 水深
        depth = max(0.0, water_level - bottom_elevation)
        
        # 断面几何特性
        if depth > 0:
            # 过水面积
            cross_area = (self.bottom_width + self.side_slope * depth) * depth
            
            # 湿周
            wetted_perimeter = self.bottom_width + 2 * depth * math.sqrt(1 + self.side_slope**2)
            
            # 水力半径
            hydraulic_radius = cross_area / wetted_perimeter
            
            # 水面宽度
            surface_width = self.bottom_width + 2 * self.side_slope * depth
        else:
            cross_area = 0.0
            wetted_perimeter = self.bottom_width
            hydraulic_radius = 0.0
            surface_width = self.bottom_width
        
        return {
            'node_name': node_name,
            'bottom_elevation': bottom_elevation,
            'water_level': water_level,
            'depth': depth,
            'cross_area': cross_area,
            'wetted_perimeter': wetted_perimeter,
            'hydraulic_radius': hydraulic_radius,
            'surface_width': surface_width,
            'bottom_width': self.bottom_width,
            'side_slope': self.side_slope
        }
    
    def calculate_normal_depth(self, discharge: float) -> float:
        """
        计算正常水深
        
        Args:
            discharge (float): 流量 (m³/s)
        
        Returns:
            float: 正常水深 (m)
        """
        if discharge <= 0:
            return self.minimum_depth
        
        # 使用牛顿法求解正常水深
        depth = 1.0  # 初始猜测
        
        for iteration in range(50):
            # 计算断面特性
            area = (self.bottom_width + self.side_slope * depth) * depth
            wetted_p = self.bottom_width + 2 * depth * math.sqrt(1 + self.side_slope**2)
            
            if wetted_p <= 0:
                break
            
            hydraulic_r = area / wetted_p
            
            # 曼宁公式残差
            calculated_q = (1 / self.roughness) * area * (hydraulic_r ** (2/3)) * \
                          math.sqrt(self.bottom_slope)
            
            residual = calculated_q - discharge
            
            if abs(residual) < 0.001:
                break
            
            # 计算导数
            d_area_d_depth = self.bottom_width + 2 * self.side_slope * depth
            d_wetted_d_depth = 2 * math.sqrt(1 + self.side_slope**2)
            d_hr_d_depth = (d_area_d_depth * wetted_p - area * d_wetted_d_depth) / (wetted_p**2)
            
            d_q_d_depth = (1 / self.roughness) * math.sqrt(self.bottom_slope) * \
                         (d_area_d_depth * (hydraulic_r ** (2/3)) + 
                          area * (2/3) * (hydraulic_r ** (-1/3)) * d_hr_d_depth)
            
            if abs(d_q_d_depth) > 1e-10:
                depth = depth - residual / d_q_d_depth
                depth = max(0.01, depth)  # 确保正值
            else:
                break
        
        return max(self.minimum_depth, depth)
    
    def calculate_critical_depth(self, discharge: float) -> float:
        """
        计算临界水深
        
        Args:
            discharge (float): 流量 (m³/s)
        
        Returns:
            float: 临界水深 (m)
        """
        if discharge <= 0:
            return self.minimum_depth
        
        # 临界流条件：Fr = 1，即 Q²/g = A³/T
        g = 9.81
        target = discharge**2 / g
        
        depth = 0.5  # 初始猜测
        
        for iteration in range(50):
            # 计算断面特性
            area = (self.bottom_width + self.side_slope * depth) * depth
            surface_width = self.bottom_width + 2 * self.side_slope * depth
            
            if surface_width <= 0:
                break
            
            # 临界流条件
            residual = area**3 / surface_width - target
            
            if abs(residual) < 0.001:
                break
            
            # 导数计算
            d_area_d_depth = self.bottom_width + 2 * self.side_slope * depth
            d_width_d_depth = 2 * self.side_slope
            
            d_residual_d_depth = (3 * area**2 * d_area_d_depth * surface_width - 
                                 area**3 * d_width_d_depth) / (surface_width**2)
            
            if abs(d_residual_d_depth) > 1e-10:
                depth = depth - residual / d_residual_d_depth
                depth = max(0.01, depth)
            else:
                break
        
        return max(self.minimum_depth, depth)
    
    def get_hydraulic_analysis(self, discharge: float) -> Dict[str, Any]:
        """
        获取水力分析结果
        
        Args:
            discharge (float): 设计流量 (m³/s)
        
        Returns:
            Dict[str, Any]: 水力分析结果
        """
        normal_depth = self.calculate_normal_depth(discharge)
        critical_depth = self.calculate_critical_depth(discharge)
        
        # 判断流态
        if normal_depth > critical_depth:
            flow_regime = "缓流"
        elif normal_depth < critical_depth:
            flow_regime = "急流"
        else:
            flow_regime = "临界流"
        
        # 计算流速和弗劳德数
        area_normal = (self.bottom_width + self.side_slope * normal_depth) * normal_depth
        velocity = discharge / area_normal if area_normal > 0 else 0
        
        surface_width = self.bottom_width + 2 * self.side_slope * normal_depth
        hydraulic_depth = area_normal / surface_width if surface_width > 0 else 0
        froude_number = velocity / math.sqrt(9.81 * hydraulic_depth) if hydraulic_depth > 0 else 0
        
        return {
            'discharge': discharge,
            'normal_depth': normal_depth,
            'critical_depth': critical_depth,
            'flow_regime': flow_regime,
            'velocity': velocity,
            'froude_number': froude_number,
            'cross_area': area_normal,
            'hydraulic_depth': hydraulic_depth,
            'channel_slope': self.bottom_slope,
            'roughness': self.roughness
        }
    
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
        return self.saint_venant_model.update_states(variables, dt, prev_states)
    
    def get_configuration_summary(self) -> Dict[str, Any]:
        """
        获取配置摘要
        
        Returns:
            Dict[str, Any]: 配置摘要字典
        """
        return {
            'name': self.name,
            'type': 'configurable_channel',
            'geometry': {
                'length': self.length,
                'bottom_width': self.bottom_width,
                'side_slope': self.side_slope,
                'bottom_slope': self.bottom_slope
            },
            'hydraulics': {
                'roughness': self.roughness,
                'minimum_depth': self.minimum_depth
            },
            'discretization': {
                'num_segments': self.num_segments,
                'solver_type': self.solver_type,
                'total_nodes': len(self.internal_nodes)
            },
            'nodes': {
                'upstream': self.upstream_node,
                'downstream': self.downstream_node,
                'internal_count': len(self.internal_nodes) - 2
            },
            'original_config': self.channel_config
        }
    
    def __repr__(self) -> str:
        """模型的字符串表示"""
        return (f"ConfigurableChannelModel(name='{self.name}', "
                f"length={self.length:.0f}m, "
                f"width={self.bottom_width:.1f}m, "
                f"segments={self.num_segments})")


def create_channel_from_config(channel_name: str, 
                              channel_config: Dict[str, Any]) -> ConfigurableChannelModel:
    """
    从配置字典创建明渠模型
    
    Args:
        channel_name (str): 明渠段名称
        channel_config (Dict): 明渠配置字典
    
    Returns:
        ConfigurableChannelModel: 明渠模型实例
    """
    return ConfigurableChannelModel(channel_name, channel_config)


def create_channels_from_config(channels_config: Dict[str, Dict[str, Any]]) -> Dict[str, ConfigurableChannelModel]:
    """
    从配置字典批量创建明渠模型
    
    Args:
        channels_config (Dict): 明渠配置字典，键为明渠名称，值为配置
    
    Returns:
        Dict[str, ConfigurableChannelModel]: 明渠模型字典
    """
    channels = {}
    for channel_name, channel_config in channels_config.items():
        channels[channel_name] = create_channel_from_config(channel_name, channel_config)
    
    return channels


def validate_channel_network(channels: Dict[str, ConfigurableChannelModel]) -> Dict[str, Any]:
    """
    验证明渠网络的连通性和一致性
    
    Args:
        channels (Dict[str, ConfigurableChannelModel]): 明渠模型字典
    
    Returns:
        Dict[str, Any]: 验证结果
    """
    validation_result = {
        'is_valid': True,
        'total_channels': len(channels),
        'connectivity_issues': [],
        'parameter_issues': [],
        'warnings': []
    }
    
    all_nodes = set()
    node_connections = {}
    
    # 收集所有节点和连接信息
    for channel_name, channel in channels.items():
        for node in channel.internal_nodes:
            all_nodes.add(node)
            if node not in node_connections:
                node_connections[node] = []
            node_connections[node].append(channel_name)
    
    # 检查连通性
    for node, connected_channels in node_connections.items():
        if len(connected_channels) > 2:
            validation_result['connectivity_issues'].append(
                f"节点 {node} 连接了过多渠道: {connected_channels}"
            )
        elif len(connected_channels) == 1:
            validation_result['warnings'].append(
                f"节点 {node} 只连接了一个渠道: {connected_channels[0]} (可能是边界节点)"
            )
    
    # 检查参数一致性
    for channel_name, channel in channels.items():
        if channel.bottom_slope < 0:
            validation_result['parameter_issues'].append(
                f"渠道 {channel_name} 的底坡为负值: {channel.bottom_slope}"
            )
        
        if channel.roughness > 0.1:
            validation_result['warnings'].append(
                f"渠道 {channel_name} 的糙率系数较大: {channel.roughness}"
            )
    
    # 设置验证状态
    if validation_result['connectivity_issues'] or validation_result['parameter_issues']:
        validation_result['is_valid'] = False
    
    validation_result['total_nodes'] = len(all_nodes)
    validation_result['boundary_nodes'] = [
        node for node, connections in node_connections.items() 
        if len(connections) == 1
    ]
    
    return validation_result