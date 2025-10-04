"""
配置驱动的水力系统构建器

根据YAML配置文件自动构建完整的水库-闸门-明渠系统。

Author: WaterNet Development Team  
Date: 2024-10-05
"""

import yaml
import os
import math
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# 导入WaterNet核心模块
from ..models.constant_level_reservoir import create_upstream_reservoir, create_downstream_reservoir
from ..models.complex_station_model import create_gate_station
from ..visualization.config_driven_visualizer import create_visualization_engine


@dataclass
class SystemConfig:
    """系统配置数据类"""
    system_info: Dict[str, Any]
    components: Dict[str, Any]
    topology: Dict[str, Any]
    simulation: Dict[str, Any]


class ChannelGeometry:
    """明渠几何配置类"""
    def __init__(self, name: str, config: Dict[str, Any]):
        location = config['location']
        geometry = config['geometry']
        hydraulics = config['hydraulics']
        discretization = config.get('discretization', {})
        
        self.name = name
        self.upstream_node = location['upstream_node']
        self.downstream_node = location['downstream_node']
        self.length = geometry['length']
        self.bottom_width = geometry['bottom_width']
        self.side_slope = geometry['side_slope']
        self.bottom_slope = geometry.get('bottom_slope', 0.001)
        self.roughness = hydraulics['roughness_coefficient']
        self.num_segments = discretization.get('num_segments', 10)
        self.upstream_elevation = geometry.get('bottom_elevation_upstream', 100.0)
        self.downstream_elevation = geometry.get('bottom_elevation_downstream', 99.0)
    
    def get_cross_section_area(self, depth: float) -> float:
        """计算过水断面面积"""
        if depth <= 0:
            return 0.0
        return self.bottom_width * depth + self.side_slope * depth * depth
    
    def get_wetted_perimeter(self, depth: float) -> float:
        """计算湿周"""
        if depth <= 0:
            return 0.0
        return self.bottom_width + 2 * depth * math.sqrt(1 + self.side_slope**2)
    
    def get_hydraulic_radius(self, depth: float) -> float:
        """计算水力半径"""
        area = self.get_cross_section_area(depth)
        perimeter = self.get_wetted_perimeter(depth)
        return area / perimeter if perimeter > 0 else 0.0
    
    def calculate_manning_flow(self, depth: float) -> float:
        """使用曼宁公式计算流量"""
        if depth <= 0:
            return 0.0
        
        area = self.get_cross_section_area(depth)
        hydraulic_radius = self.get_hydraulic_radius(depth)
        
        # 曼宁公式：Q = (1/n) * A * R^(2/3) * S^(1/2)
        flow_rate = (1.0 / self.roughness) * area * (hydraulic_radius ** (2.0/3.0)) * math.sqrt(self.bottom_slope)
        return flow_rate
    
    def __repr__(self):
        return f"ChannelGeometry(name='{self.name}', length={self.length}m, width={self.bottom_width}m)"


class ConfigDrivenSystemBuilder:
    """配置驱动的系统构建器"""
    
    def __init__(self, config_file: str):
        self.config_file = config_file
        self.config = self._load_system_config()
        self.components = {}
        self.models = {}
        self.visualizer = None
        
        self._validate_config()
    
    def _load_system_config(self) -> SystemConfig:
        """加载系统配置"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            return SystemConfig(
                system_info=config_data.get('system', {}),
                components=config_data.get('components', {}),
                topology=config_data.get('topology', {}),
                simulation=config_data.get('simulation', {})
            )
        except FileNotFoundError:
            raise FileNotFoundError(f"配置文件未找到: {self.config_file}")
        except yaml.YAMLError as e:
            raise ValueError(f"配置文件格式错误: {e}")
    
    def _validate_config(self):
        """验证配置文件"""
        if not self.config.components:
            raise ValueError("配置文件缺少组件定义")
    
    def build_system(self) -> Dict[str, Any]:
        """构建完整系统"""
        print("开始构建配置驱动的水力系统...")
        
        # 1. 创建水库
        self._build_reservoirs()
        
        # 2. 创建闸门
        self._build_gates_and_stations()
        
        # 3. 创建明渠
        self._build_channels()
        
        # 4. 初始化可视化
        self._initialize_visualization()
        
        print("系统构建完成！")
        
        return {
            'components': self.components,
            'models': self.models,
            'visualizer': self.visualizer,
            'config': self.config
        }
    
    def _build_reservoirs(self):
        """构建水库组件"""
        reservoirs_config = self.config.components.get('reservoirs', {})
        
        print(f"构建 {len(reservoirs_config)} 个水库...")
        
        for res_name, res_config in reservoirs_config.items():
            print(f"  创建水库: {res_name}")
            
            level = res_config['level']
            connected_node = res_config['connected_node']
            capacity = res_config.get('capacity', 1e6)
            reservoir_type = res_config.get('reservoir_type', 'upstream')
            
            if reservoir_type == 'upstream':
                reservoir = create_upstream_reservoir(
                    name=res_name,
                    node=connected_node,
                    constant_level=level,
                    capacity=capacity
                )
            else:
                reservoir = create_downstream_reservoir(
                    name=res_name,
                    node=connected_node,
                    constant_level=level,
                    capacity=capacity
                )
            
            self.components[res_name] = reservoir
            self.models[res_name] = reservoir
            print(f"    ✓ 水库已创建 (水位: {level}m)")
    
    def _build_gates_and_stations(self):
        """构建闸门组件"""
        # 单闸门
        gates_config = self.config.components.get('gates', {})
        for gate_name, gate_config in gates_config.items():
            print(f"  创建闸门: {gate_name}")
            
            location = gate_config['location']
            geometry = gate_config['geometry']
            hydraulics = gate_config['hydraulics']
            control = gate_config['control']
            
            gate_configs = [{
                'name': gate_name,
                'width': geometry['width'],
                'discharge_coeff': hydraulics['discharge_coefficient'],
                'initial_opening': control['initial_opening']
            }]
            
            gate_station = create_gate_station(
                name=gate_name,
                upstream_node=location['upstream_node'],
                downstream_node=location['downstream_node'],
                gate_configs=gate_configs
            )
            
            self.components[gate_name] = gate_station
            self.models[gate_name] = gate_station
            print(f"    ✓ 闸门已创建")
        
        # 闸站
        stations_config = self.config.components.get('gate_stations', {})
        for station_name, station_config in stations_config.items():
            print(f"  创建闸站: {station_name}")
            
            location = station_config['location']
            gates_data = station_config['gates']
            
            gate_configs = []
            for gate_data in gates_data:
                gate_configs.append({
                    'name': gate_data['name'],
                    'width': gate_data['width'],
                    'discharge_coeff': gate_data['discharge_coefficient'],
                    'initial_opening': gate_data['initial_opening']
                })
            
            gate_station = create_gate_station(
                name=station_name,
                upstream_node=location['upstream_node'],
                downstream_node=location['downstream_node'],
                gate_configs=gate_configs
            )
            
            self.components[station_name] = gate_station
            self.models[station_name] = gate_station
            print(f"    ✓ 闸站已创建")

    def _build_channels(self):
        """构建明渠组件"""
        channels_config = self.config.components.get('channels', {})
        
        if not channels_config:
            print("无明渠配置，跳过明渠构建")
            return
        
        print(f"构建 {len(channels_config)} 个明渠段...")
        
        for channel_name, channel_config in channels_config.items():
            print(f"  创建明渠: {channel_name}")
            
            # 创建明渠几何对象
            channel_geometry = ChannelGeometry(channel_name, channel_config)
            self.components[channel_name] = channel_geometry
            print(f"    ✓ 明渠段已创建 (长度: {channel_geometry.length}m)")
    
    def _initialize_visualization(self):
        """初始化可视化系统"""
        print("初始化可视化系统...")
        
        try:
            vis_config_file = self._find_visualization_config()
            if vis_config_file and os.path.exists(vis_config_file):
                self.visualizer = create_visualization_engine(vis_config_file)
                print("    ✓ 可视化引擎已初始化")
        except Exception as e:
            print(f"    ⚠ 可视化初始化失败: {e}")
    
    def _find_visualization_config(self) -> Optional[str]:
        """查找可视化配置文件"""
        config_dir = os.path.dirname(self.config_file)
        
        # 首先尝试简化版本
        vis_config_file = os.path.join(config_dir, "visualization_simple.yaml")
        if os.path.exists(vis_config_file):
            return vis_config_file
        
        # 再尝试完整版本
        vis_config_file = os.path.join(config_dir, "visualization_templates.yaml")
        if os.path.exists(vis_config_file):
            return vis_config_file
        
        return None
    
    def generate_system_visualization(self, output_dir: str = "output") -> Dict[str, str]:
        """生成系统可视化"""
        print("生成系统可视化...")
        
        if not self.visualizer:
            raise ValueError("可视化引擎不可用")
        
        system_data = {
            'system': self.config.system_info,
            'components': self.config.components,
            'topology': self.config.topology
        }
        
        results = self.visualizer.generate_output(system_data, output_dir)
        print(f"  ✓ 可视化文件已生成")
        return results
    
    def calculate_channel_flows(self, water_depths: Dict[str, float]) -> Dict[str, float]:
        """计算各明渠段的流量"""
        channel_flows = {}
        
        for comp_name, component in self.components.items():
            if isinstance(component, ChannelGeometry):
                depth = water_depths.get(comp_name, 1.0)  # 默认水深1m
                flow_rate = component.calculate_manning_flow(depth)
                channel_flows[comp_name] = flow_rate
        
        return channel_flows
    
    def get_system_summary(self) -> Dict[str, Any]:
        """获取系统概要"""
        components_count = {}
        for comp_type, comp_data in self.config.components.items():
            if isinstance(comp_data, dict):
                components_count[comp_type] = len(comp_data)
        
        return {
            'system_name': self.config.system_info.get('name', '未命名系统'),
            'components_count': components_count,
            'total_components': sum(components_count.values()),
            'models_count': len(self.models),
            'has_visualizer': self.visualizer is not None
        }


def create_system_from_config(config_file: str) -> ConfigDrivenSystemBuilder:
    """从配置文件创建系统"""
    return ConfigDrivenSystemBuilder(config_file)