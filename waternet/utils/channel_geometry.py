#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
渠道几何工具 - WaterNet核心库

提供通用的渠道几何参数计算和分析功能，支持不同断面形状的几何特性分析。

核心功能：
1. 断面几何参数计算（面积、湿周、水力半径等）
2. 水力最优断面分析
3. 断面形状优化计算
4. 几何参数函数生成

Author: WaterNet Development Team
Date: 2025-01-05
"""

import math
from typing import Dict, List, Tuple, Any, Optional, Callable


class ChannelGeometry:
    """渠道几何计算工具类"""
    
    @staticmethod
    def calculate_trapezoidal_geometry(bottom_width: float, side_slope: float, 
                                     depth: float) -> Dict[str, float]:
        """
        计算梯形断面几何参数
        
        Args:
            bottom_width: 底宽 (m)
            side_slope: 边坡系数 (水平:垂直)
            depth: 水深 (m)
            
        Returns:
            Dict: 几何参数字典，包含面积、湿周、水力半径等
        """
        if depth <= 0:
            return {
                'area': 0.0,
                'perimeter': bottom_width,
                'top_width': bottom_width,
                'hydraulic_radius': 0.0,
                'hydraulic_depth': 0.0,
                'section_factor': 0.0
            }
        
        # 基本几何参数
        area = bottom_width * depth + side_slope * depth * depth
        top_width = bottom_width + 2 * side_slope * depth
        perimeter = bottom_width + 2 * depth * math.sqrt(1 + side_slope * side_slope)
        
        # 水力参数
        hydraulic_radius = area / perimeter if perimeter > 0 else 0
        hydraulic_depth = area / top_width if top_width > 0 else 0
        section_factor = area * math.sqrt(hydraulic_radius) if hydraulic_radius > 0 else 0
        
        return {
            'area': area,
            'perimeter': perimeter,
            'top_width': top_width,
            'hydraulic_radius': hydraulic_radius,
            'hydraulic_depth': hydraulic_depth,
            'section_factor': section_factor,
            'depth': depth,
            'bottom_width': bottom_width,
            'side_slope': side_slope
        }
    
    @staticmethod
    def calculate_rectangular_geometry(width: float, depth: float) -> Dict[str, float]:
        """
        计算矩形断面几何参数
        
        Args:
            width: 断面宽度 (m)
            depth: 水深 (m)
            
        Returns:
            Dict: 几何参数字典
        """
        if depth <= 0:
            return {
                'area': 0.0,
                'perimeter': width,
                'top_width': width,
                'hydraulic_radius': 0.0,
                'hydraulic_depth': 0.0,
                'section_factor': 0.0
            }
        
        area = width * depth
        perimeter = width + 2 * depth
        hydraulic_radius = area / perimeter if perimeter > 0 else 0
        section_factor = area * math.sqrt(hydraulic_radius) if hydraulic_radius > 0 else 0
        
        return {
            'area': area,
            'perimeter': perimeter,
            'top_width': width,
            'hydraulic_radius': hydraulic_radius,
            'hydraulic_depth': depth,
            'section_factor': section_factor,
            'depth': depth,
            'width': width
        }
    
    @staticmethod
    def find_optimal_trapezoidal_section(area: float, side_slope: float) -> Dict[str, Any]:
        """
        寻找给定面积和边坡系数下的水力最优梯形断面
        
        Args:
            area: 给定断面积 (m²)
            side_slope: 边坡系数
            
        Returns:
            Dict: 最优断面参数
        """
        def objective_function(depth: float) -> float:
            """目标函数：使水力半径最大"""
            if depth <= 0:
                return -1e6
            
            # 根据给定面积计算底宽：A = b*h + m*h²，所以 b = A/h - m*h
            bottom_width = area / depth - side_slope * depth
            
            if bottom_width <= 0:
                return -1e6
            
            geometry = ChannelGeometry.calculate_trapezoidal_geometry(
                bottom_width, side_slope, depth)
            return geometry['hydraulic_radius']
        
        # 搜索最优水深
        best_depth = 0
        best_hydraulic_radius = 0
        
        # 水深搜索范围：从0.1到10m
        for depth in [i * 0.01 for i in range(10, 1001)]:  # 0.1 to 10.0 m, step 0.01
            hr = objective_function(depth)
            if hr > best_hydraulic_radius:
                best_hydraulic_radius = hr
                best_depth = depth
        
        # 计算最优断面参数
        optimal_bottom_width = area / best_depth - side_slope * best_depth
        optimal_geometry = ChannelGeometry.calculate_trapezoidal_geometry(
            optimal_bottom_width, side_slope, best_depth)
        
        return {
            'optimal_depth': best_depth,
            'optimal_bottom_width': optimal_bottom_width,
            'optimal_hydraulic_radius': best_hydraulic_radius,
            'area_constraint': area,
            'side_slope_constraint': side_slope,
            'geometry': optimal_geometry
        }
    
    @staticmethod
    def solve_normal_depth(Q: float, b: float, m: float, S: float, n: float) -> float:
        """
        使用牛顿迭代法求解梯形断面正常水深
        
        Args:
            Q: 流量 (m³/s)
            b: 底宽 (m)
            m: 边坡系数
            S: 底坡
            n: 糙率系数
            
        Returns:
            float: 正常水深 (m)
        """
        # 初始估值
        h = max(1.0, Q / (b * 3.0))  # 基于流量的初始估计
        
        # 牛顿迭代
        for i in range(25):
            # 计算水力要素
            A = b * h + m * h ** 2  # 断面面积
            P = b + 2 * h * math.sqrt(1 + m ** 2)  # 湿周
            R = A / P if P > 0 else 0  # 水力半径
            
            # 曼宁公式: Q = (1/n) * A * R^(2/3) * S^(1/2)
            Q_calc = (1.0 / n) * A * (R ** (2.0/3.0)) * (S ** 0.5) if R > 0 else 0
            
            # 计算误差
            error = Q_calc - Q
            
            if abs(error) < 0.001:  # 收敛判断
                break
            
            # 计算导数 dQ/dh
            dA_dh = b + 2 * m * h
            dP_dh = 2 * math.sqrt(1 + m ** 2)
            dR_dh = (dA_dh * P - A * dP_dh) / (P ** 2) if P > 0 else 0
            
            if R > 0:
                dQ_dh = (1.0 / n) * (S ** 0.5) * (
                    dA_dh * (R ** (2.0/3.0)) + 
                    A * (2.0/3.0) * (R ** (-1.0/3.0)) * dR_dh
                )
            else:
                dQ_dh = 1.0  # 避免零除
            
            # 牛顿迭代公式
            if abs(dQ_dh) > 1e-10:
                h_new = h - error / dQ_dh
                h = max(0.1, min(10.0, h_new))  # 限制水深范围
            else:
                break
        
        return h
    
    @staticmethod
    def create_geometry_functions(bottom_width: float, side_slope: float, 
                                elevation: float, roughness: float) -> Dict[str, Callable]:
        """
        创建几何函数（用于SaintVenant模型）
        
        Args:
            bottom_width: 底宽 (m)
            side_slope: 边坡系数
            elevation: 底部高程 (m)
            roughness: 糙率系数
            
        Returns:
            Dict: 包含几何函数的字典
        """
        def area_func(H: float) -> float:
            if H <= elevation:
                return 0.01  # 避免零值
            h = H - elevation
            return bottom_width * h + side_slope * h * h
        
        def top_width_func(H: float) -> float:
            if H <= elevation:
                return bottom_width
            h = H - elevation
            return bottom_width + 2 * side_slope * h
        
        def conveyance_func(H: float) -> float:
            A = area_func(H)
            if A <= 0:
                return 0
            
            h = H - elevation
            if h <= 0:
                return 0
            
            # 湿周计算
            P = bottom_width + 2 * h * math.sqrt(1 + side_slope * side_slope)
            R = A / P if P > 0 else 0
            
            return A * (R ** (2/3)) / roughness if R > 0 else 0
        
        return {
            'area_func': area_func,
            'top_width_func': top_width_func,
            'conveyance_func': conveyance_func
        }


class HeadLossCalculator:
    """水头损失计算工具类"""
    
    @staticmethod
    def calculate_manning_head_loss(flow: float, length: float, bottom_width: float,
                                  side_slope: float, bottom_slope: float, 
                                  roughness: float) -> Dict[str, float]:
        """
        基于曼宁公式计算水头损失
        
        Args:
            flow: 流量 (m³/s)
            length: 渠道长度 (m)
            bottom_width: 底宽 (m)
            side_slope: 边坡系数
            bottom_slope: 底坡
            roughness: 糙率系数
            
        Returns:
            Dict: 水头损失计算结果
        """
        # 计算正常水深
        normal_depth = ChannelGeometry.solve_normal_depth(
            flow, bottom_width, side_slope, bottom_slope, roughness)
        
        # 计算水力参数
        geometry = ChannelGeometry.calculate_trapezoidal_geometry(
            bottom_width, side_slope, normal_depth)
        
        velocity = flow / geometry['area'] if geometry['area'] > 0 else 0
        
        # 计算摩阻坡度
        if geometry['hydraulic_radius'] > 0:
            friction_slope = (roughness * velocity) ** 2 / (geometry['hydraulic_radius'] ** (4/3))
        else:
            friction_slope = 0.001  # 默认值
        
        # 水头损失 = 摩阻损失 + 局部损失
        friction_loss = friction_slope * length
        local_loss = 0.1 * friction_loss  # 局部损失约为摩阻损失的10%
        total_loss = friction_loss + local_loss
        
        return {
            'normal_depth': normal_depth,
            'velocity': velocity,
            'friction_slope': friction_slope,
            'friction_loss': friction_loss,
            'local_loss': local_loss,
            'total_loss': total_loss
        }
    
    @staticmethod
    def analyze_hydraulic_properties(distances: List[float], water_levels: List[float], 
                                   bottom_elevations: List[float], velocities: List[float],
                                   flow: float) -> Dict[str, Any]:
        """
        分析水力学性质
        
        Args:
            distances: 距离列表
            water_levels: 水位列表
            bottom_elevations: 底部高程列表
            velocities: 流速列表
            flow: 流量
            
        Returns:
            Dict: 水力学分析结果
        """
        if not distances or not water_levels:
            return {}
        
        depths = [wl - be for wl, be in zip(water_levels, bottom_elevations)]
        
        # 计算弗劳德数
        froude_numbers = []
        specific_energies = []
        
        for depth, velocity in zip(depths, velocities):
            if depth > 0 and velocity > 0:
                froude = velocity / math.sqrt(9.81 * depth)
                froude_numbers.append(froude)
                specific_energy = depth + velocity ** 2 / (2 * 9.81)
                specific_energies.append(specific_energy)
            else:
                froude_numbers.append(0.0)
                specific_energies.append(0.0)
        
        # 流态分析
        flow_regime = 'subcritical' if all(fr < 1.0 for fr in froude_numbers if fr > 0) else 'mixed'
        
        # 计算总水头损失
        total_head_loss = water_levels[0] - water_levels[-1] if len(water_levels) > 1 else 0
        channel_length = distances[-1] - distances[0] if len(distances) > 1 else 0
        average_slope = total_head_loss / channel_length if channel_length > 0 else 0
        
        return {
            'froude_numbers': froude_numbers,
            'specific_energies': specific_energies,
            'flow_regime': flow_regime,
            'total_head_loss': total_head_loss,
            'channel_length': channel_length,
            'average_slope': average_slope,
            'max_depth': max(depths) if depths else 0,
            'min_depth': min(depths) if depths else 0,
            'max_velocity': max(velocities) if velocities else 0,
            'min_velocity': min(velocities) if velocities else 0,
            'max_froude': max(froude_numbers) if froude_numbers else 0
        }