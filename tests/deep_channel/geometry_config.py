"""
5断面明渠几何配置模块

根据设计文档提供标准的5断面明渠几何配置，包括：
- 断面几何参数定义
- 水力要素计算函数
- 初始条件设置
- 边界条件配置

Author: WaterNet Development Team
Date: 2024-10-03
"""

import numpy as np
import math
from typing import Dict, List, Callable, Tuple
from dataclasses import dataclass


@dataclass
class CrossSectionGeometry:
    """断面几何参数类"""
    mileage: float          # 里程 (m)
    elevation: float        # 底高程 (m)
    bottom_width: float     # 底宽 (m)
    side_slope: float       # 边坡系数 (m的倒数, 1:m)
    roughness: float        # 糙率系数
    shape: str = "trapezoidal"  # 断面形状


class FiveSectionChannelConfig:
    """5断面明渠配置类"""
    
    def __init__(self):
        """初始化5断面明渠配置"""
        self._setup_geometry_parameters()
        self._setup_initial_conditions()
    
    def _setup_geometry_parameters(self):
        """设置几何参数"""
        # 根据设计文档的表格数据
        self.sections_data = [
            CrossSectionGeometry(
                mileage=0.0, elevation=100.00, bottom_width=10.0,
                side_slope=1.5, roughness=0.025
            ),
            CrossSectionGeometry(
                mileage=500.0, elevation=99.50, bottom_width=12.0,
                side_slope=1.5, roughness=0.025
            ),
            CrossSectionGeometry(
                mileage=1000.0, elevation=99.00, bottom_width=10.0,
                side_slope=2.0, roughness=0.030
            ),
            CrossSectionGeometry(
                mileage=1500.0, elevation=98.50, bottom_width=15.0,
                side_slope=1.5, roughness=0.025
            ),
            CrossSectionGeometry(
                mileage=2000.0, elevation=98.00, bottom_width=12.0,
                side_slope=2.0, roughness=0.030
            )
        ]
    
    def _setup_initial_conditions(self):
        """设置初始条件"""
        self.initial_conditions = {
            'initial_flow': 50.0,          # 初始流量 (m³/s)
            'downstream_water_level': 101.00,  # 下游边界水位 (m)
            'simulation_time': 1800.0,     # 仿真时间 (s)
            'time_step': 10.0              # 时间步长 (s)
        }
    
    def get_five_section_geometry(self) -> List[Dict]:
        """
        获取5断面几何配置（使用统一配置管理器）
        
        Returns:
        --------
        List[Dict]: 断面几何配置列表
        """
        from waternet.config.standard_five_section import StandardFiveSectionConfig
        
        # 创建统一配置管理器
        config_manager = StandardFiveSectionConfig()
        
        # 使用默认配置，但可以根据当前数据调整
        return config_manager.get_five_section_geometry()
    
    # 以下函数已统一移至 waternet.config.standard_five_section 模块
    # 保持代码的可维护性和一致性
        conveyance_func = self._create_conveyance_function(section)
        Z = section.elevation
        
        def normal_depth_calculator(Q: float, slope: float) -> float:
            """
            计算给定流量和坡度下的正常水深
            
            Parameters:
            -----------
            Q : float
                流量 (m³/s)
            slope : float
                河床坡度
                
            Returns:
            --------
            float: 正常水深 (m)
            """
            if Q <= 0 or slope <= 0:
                return 0.0
            
            # 使用二分法求解
            H_min = Z + 0.01  # 最小水位
            H_max = Z + 10.0  # 最大水位
            tolerance = 1e-6
            max_iterations = 100
            
            for _ in range(max_iterations):
                H_mid = (H_min + H_max) / 2.0
                K = conveyance_func(H_mid)
                Q_calc = K * math.sqrt(slope)
                
                if abs(Q_calc - Q) < tolerance:
                    return H_mid - Z  # 返回水深
                
                if Q_calc < Q:
                    H_min = H_mid
                else:
                    H_max = H_mid
            
            return (H_min + H_max) / 2.0 - Z  # 返回水深
        
        return normal_depth_calculator
    
    def get_initial_conditions(self) -> Dict:
        """
        获取初始条件配置
        
        Returns:
        --------
        Dict: 初始条件参数
        """
        return self.initial_conditions.copy()
    
    def compute_steady_state_profile(self) -> Dict:
        """
        计算初始恒定流水面线
        
        使用标准步进法从下游向上游计算各断面水位
        
        Returns:
        --------
        Dict: 恒定流水面线计算结果
        """
        Q0 = self.initial_conditions['initial_flow']
        H_downstream = self.initial_conditions['downstream_water_level']
        
        sections = self.get_five_section_geometry()
        n_sections = len(sections)
        
        # 初始化结果数组
        water_levels = np.zeros(n_sections)
        depths = np.zeros(n_sections)
        velocities = np.zeros(n_sections)
        froude_numbers = np.zeros(n_sections)
        total_volume = 0.0
        
        # 下游边界条件
        water_levels[n_sections-1] = H_downstream
        
        # 从下游向上游逐段计算
        for i in range(n_sections-1, 0, -1):
            section_down = sections[i]
            section_up = sections[i-1]
            
            # 下游断面水力参数
            H_down = water_levels[i]
            A_down = section_down['area_func'](H_down)
            R_down = section_down['hydraulic_radius_func'](H_down)
            V_down = Q0 / A_down if A_down > 0 else 0.0
            
            # 计算上游水位（标准步进法）
            dx = section_up['mileage'] - section_down['mileage']
            if dx == 0:
                dx = 1.0  # 避免除零
            
            # 能量方程求解上游水位
            H_up = self._solve_upstream_water_level(
                Q0, H_down, section_up, section_down, abs(dx)
            )
            
            water_levels[i-1] = H_up
        
        # 计算各断面水力参数
        for i, section in enumerate(sections):
            H = water_levels[i]
            Z = section['elevation']
            
            depths[i] = H - Z
            
            A = section['area_func'](H)
            if A > 0:
                velocities[i] = Q0 / A
                T = section['top_width_func'](H)
                if T > 0:
                    # 弗劳德数 Fr = V / sqrt(g * D)，其中 D = A/T 为水力平均深度
                    hydraulic_depth = A / T
                    froude_numbers[i] = velocities[i] / math.sqrt(9.81 * hydraulic_depth)
            
            # 累计总蓄水量
            if i < n_sections - 1:
                next_section = sections[i+1]
                reach_length = next_section['mileage'] - section['mileage']
                avg_area = (A + next_section['area_func'](water_levels[i+1])) / 2.0
                total_volume += avg_area * reach_length
        
        # 验证物理合理性
        validation_results = {
            'monotonic_water_surface': all(water_levels[i] >= water_levels[i+1] 
                                         for i in range(n_sections-1)),
            'subcritical_flow': all(fr < 0.8 for fr in froude_numbers),
            'reasonable_velocities': all(1.0 <= v <= 3.0 for v in velocities if v > 0),
            'total_volume_check': 140000 <= total_volume <= 150000  # 理论估算范围
        }
        
        return {
            'sections': [
                {
                    'section_id': i,
                    'mileage': sections[i]['mileage'],
                    'bottom_elevation': sections[i]['elevation'],
                    'water_level': water_levels[i],
                    'depth': depths[i],
                    'velocity': velocities[i],
                    'froude_number': froude_numbers[i]
                }
                for i in range(n_sections)
            ],
            'total_volume': total_volume,
            'average_velocity': np.mean(velocities),
            'max_froude_number': np.max(froude_numbers),
            'energy_loss': water_levels[0] - water_levels[-1],
            'validation': validation_results
        }
    
    def _solve_upstream_water_level(self, Q: float, H_down: float, 
                                   section_up: Dict, section_down: Dict, 
                                   dx: float) -> float:
        """
        使用标准步进法求解上游水位
        
        Parameters:
        -----------
        Q : float
            流量 (m³/s)
        H_down : float
            下游水位 (m)
        section_up : Dict
            上游断面参数
        section_down : Dict
            下游断面参数
        dx : float
            河段长度 (m)
            
        Returns:
        --------
        float: 上游水位 (m)
        """
        # 河床坡度
        dz = section_up['elevation'] - section_down['elevation']
        S0 = dz / dx if dx > 0 else 0.001
        
        # 下游断面水力参数
        A_down = section_down['area_func'](H_down)
        R_down = section_down['hydraulic_radius_func'](H_down)
        V_down = Q / A_down if A_down > 0 else 0.0
        
        # 摩阻坡度（下游）
        n_down = section_down['roughness']
        Sf_down = (n_down * V_down) ** 2 / (R_down ** (4.0/3.0)) if R_down > 0 else 0.0
        
        # 初始估计上游水位（假设水面坡度等于河床坡度）
        H_up_est = H_down + S0 * dx
        
        # 迭代求解
        tolerance = 1e-4
        max_iterations = 20
        
        for _ in range(max_iterations):
            # 上游断面水力参数
            A_up = section_up['area_func'](H_up_est)
            R_up = section_up['hydraulic_radius_func'](H_up_est)
            V_up = Q / A_up if A_up > 0 else 0.0
            
            # 摩阻坡度（上游）
            n_up = section_up['roughness']
            Sf_up = (n_up * V_up) ** 2 / (R_up ** (4.0/3.0)) if R_up > 0 else 0.0
            
            # 平均摩阻坡度
            Sf_avg = (Sf_up + Sf_down) / 2.0
            
            # 动能差
            delta_V2_2g = (V_up * V_up - V_down * V_down) / (2.0 * 9.81)
            
            # 能量方程
            H_up_new = H_down + S0 * dx + Sf_avg * dx + delta_V2_2g
            
            # 检查收敛
            if abs(H_up_new - H_up_est) < tolerance:
                return H_up_new
            
            H_up_est = H_up_new
        
        return H_up_est
    
    def get_step_response_boundary_conditions(self) -> Dict:
        """
        获取阶跃响应测试的边界条件配置
        
        Returns:
        --------
        Dict: 边界条件配置
        """
        return {
            'upstream_flow_step': {
                'initial_flow': 50.0,       # 初始流量 (m³/s)
                'final_flow': 80.0,         # 最终流量 (m³/s)
                'step_start_time': 600.0,   # 阶跃开始时间 (s)
                'step_duration': 1.0,       # 阶跃持续时间 (s)
                'downstream_boundary': 101.00  # 下游边界水位 (m)
            },
            'downstream_boundary_step': {
                'upstream_flow': 50.0,      # 上游流量 (m³/s)
                'initial_downstream_level': 101.00,  # 初始下游水位 (m)
                'final_downstream_level': 100.50,   # 最终下游水位 (m)
                'step_start_time': 600.0,   # 阶跃开始时间 (s)
                'step_duration': 1.0        # 阶跃持续时间 (s)
            }
        }
    
    def get_channel_properties_summary(self) -> Dict:
        """
        获取河道属性摘要
        
        Returns:
        --------
        Dict: 河道属性摘要
        """
        sections = self.get_five_section_geometry()
        
        return {
            'channel_length': sections[-1]['mileage'] - sections[0]['mileage'],
            'total_fall': sections[0]['elevation'] - sections[-1]['elevation'],
            'average_slope': (sections[0]['elevation'] - sections[-1]['elevation']) / 
                           (sections[-1]['mileage'] - sections[0]['mileage']),
            'section_count': len(sections),
            'bottom_width_range': [
                min(s['bottom_width'] for s in sections),
                max(s['bottom_width'] for s in sections)
            ],
            'roughness_range': [
                min(s['roughness'] for s in sections),
                max(s['roughness'] for s in sections)
            ],
            'side_slope_range': [
                min(s['side_slope'] for s in sections),
                max(s['side_slope'] for s in sections)
            ]
        }