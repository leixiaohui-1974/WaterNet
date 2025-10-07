#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
深度分析动量方程初始残差问题
"""

import sys
import os
import numpy as np
import logging

# 添加项目路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from enhanced_solver import EnhancedSaintVenantSolver, NumericalSchemeConfig
from waternet.models.saint_venant import SaintVenantModel

def analyze_momentum_residual():
    """分析动量方程初始残差问题"""
    
    print("=== 分析动量方程初始残差 ===\n")
    
    # 创建模型
    def area_func(h, elevation, bottom_width=10.0, side_slope=1.0):
        depth = max(0.1, h - elevation)
        return bottom_width * depth + side_slope * depth**2
    
    def top_width_func(h, elevation, bottom_width=10.0, side_slope=1.0):
        depth = max(0.1, h - elevation)
        return bottom_width + 2 * side_slope * depth
    
    sections = [
        {
            'mileage': 0.0,
            'elevation': 100.0,
            'roughness': 0.03,
            'area_func': lambda h: area_func(h, 100.0),
            'top_width_func': lambda h: top_width_func(h, 100.0)
        },
        {
            'mileage': 100.0,
            'elevation': 99.5,
            'roughness': 0.03,
            'area_func': lambda h: area_func(h, 99.5),
            'top_width_func': lambda h: top_width_func(h, 99.5)
        },
        {
            'mileage': 200.0,
            'elevation': 99.0,
            'roughness': 0.03,
            'area_func': lambda h: area_func(h, 99.0),
            'top_width_func': lambda h: top_width_func(h, 99.0)
        }
    ]

    model = SaintVenantModel('test_channel', 'upstream_node', 'downstream_node', sections)
    config = NumericalSchemeConfig(max_iterations=5, convergence_tolerance=1e-4)
    solver = EnhancedSaintVenantSolver(model, config)
    
    # 设置初始条件
    initial_flow = 100.0
    downstream_level = 99.0
    solver.set_initial_conditions(initial_flow, downstream_level)
    
    # 手动分析动量方程各项
    print("=== 手动分析动量方程各项 ===")
    
    # 获取第一个分段的参数
    seg_idx = 0
    segment = model.segments[seg_idx]
    dx = segment['length']  # 100m
    dt = 1.0  # 时间步长
    g = 9.81
    
    print(f"分段{seg_idx}参数:")
    print(f"  长度: {dx}m")
    print(f"  底坡: {segment.get('slope', 0.001)}")
    print(f"  糙率: {segment.get('roughness', 0.03)}")
    
    # 获取流量和水位
    Q_curr = solver.current_state[seg_idx]  # 100 m³/s
    Q_prev = solver.previous_state[seg_idx]  # 100 m³/s
    
    i_up = segment['upstream_section']    # 0
    i_down = segment['downstream_section'] # 1
    
    # 上游水位
    H_up_curr = solver._get_upstream_water_level()  # 应该是99.02m
    H_up_prev = H_up_curr
    
    # 下游水位  
    H_down_curr = solver.current_state[solver.n_flow_vars + 0]  # 99.01m (内部节点)
    H_down_prev = H_down_curr
    
    print(f"\n水位和流量:")
    print(f"  上游水位: {H_up_curr:.3f}m")
    print(f"  下游水位: {H_down_curr:.3f}m")
    print(f"  当前流量: {Q_curr:.2f}m³/s")
    print(f"  前一时刻流量: {Q_prev:.2f}m³/s")
    
    # 计算各断面参数
    section_up = model.sections[i_up]
    section_down = model.sections[i_down]
    
    base_width = 10.0
    side_slope = 1.0
    
    depth_up = max(0.5, H_up_curr - section_up['elevation'])
    depth_down = max(0.5, H_down_curr - section_down['elevation'])
    
    A_up = base_width * depth_up + side_slope * depth_up**2
    A_down = base_width * depth_down + side_slope * depth_down**2
    A_avg = (A_up + A_down) / 2.0
    
    print(f"\n断面参数:")
    print(f"  上游水深: {depth_up:.3f}m, 面积: {A_up:.2f}m²")
    print(f"  下游水深: {depth_down:.3f}m, 面积: {A_down:.2f}m²")
    print(f"  平均面积: {A_avg:.2f}m²")
    
    # 动量方程各项计算
    print(f"\n=== 动量方程各项分析 ===")
    
    # 1. 时间导数项: ∂Q/∂t
    dQ_dt = (Q_curr - Q_prev) / dt
    print(f"1. 时间导数项 ∂Q/∂t = {dQ_dt:.3f}")
    
    # 2. 对流项: ∂(Q²/A)/∂x  
    if A_avg > 0:
        velocity = Q_curr / A_avg
        velocity_sq = velocity**2
        print(f"2. 对流项分析:")
        print(f"   平均流速: {velocity:.3f}m/s")
        print(f"   流速平方: {velocity_sq:.3f}m²/s²")
        # 简化：假设下游流速相同
        convection_term = 0.0  # 恒定流时对流项为0
        print(f"   对流项 ∂(Q²/A)/∂x ≈ {convection_term:.3f}")
    
    # 3. 压力项: gA∂H/∂x
    dH_dx = (H_down_curr - H_up_curr) / dx
    pressure_term = g * A_avg * dH_dx
    print(f"3. 压力项:")
    print(f"   水面坡度 ∂H/∂x = {dH_dx:.6f}")
    print(f"   压力项 gA∂H/∂x = {pressure_term:.3f}")
    
    # 4. 摩阻项: gASf
    n_manning = segment.get('roughness', 0.03)
    if A_avg > 0:
        P_avg = base_width + 2 * (depth_up + depth_down) / 2.0 * np.sqrt(1 + side_slope**2)
        R_hydraulic = A_avg / P_avg
        velocity_abs = abs(Q_curr / A_avg)
        friction_slope = n_manning**2 * velocity_abs * Q_curr / (A_avg**2 * R_hydraulic**(4/3))
        friction_term = g * A_avg * friction_slope
        print(f"4. 摩阻项:")
        print(f"   湿周: {P_avg:.2f}m")
        print(f"   水力半径: {R_hydraulic:.3f}m")
        print(f"   摩阻坡度: {friction_slope:.6f}")
        print(f"   摩阻项 gASf = {friction_term:.3f}")
    
    # 5. 底坡项: gAS0
    S0 = segment.get('slope', 0.001)
    slope_term = g * A_avg * S0
    print(f"5. 底坡项:")
    print(f"   底坡 S0 = {S0:.6f}")
    print(f"   底坡项 gAS0 = {slope_term:.3f}")
    
    # 动量方程残差
    residual = dQ_dt + convection_term + pressure_term + friction_term - slope_term
    print(f"\n=== 动量方程残差分析 ===")
    print(f"残差 = {dQ_dt:.3f} + {convection_term:.3f} + {pressure_term:.3f} + {friction_term:.3f} - {slope_term:.3f}")
    print(f"残差 = {residual:.3f}")
    
    # 分析为什么残差这么大
    print(f"\n=== 问题分析 ===")
    
    # 恒定流理论上应该满足：gAS0 = gASf + gA∂H/∂x
    # 即：底坡项 = 摩阻项 + 压力项
    theoretical_balance = slope_term - friction_term - pressure_term
    print(f"理论恒定流平衡检查:")
    print(f"底坡项 - 摩阻项 - 压力项 = {theoretical_balance:.3f}")
    
    if abs(theoretical_balance) > 0.1:
        print("⚠ 恒定流平衡不满足！这说明初始条件不是真正的恒定流状态")
        
        # 检查可能的原因
        print("\n可能原因分析:")
        
        # 1. 几何参数不一致
        print("1. 几何参数一致性检查:")
        print(f"   Preissmann系统中的底宽: {base_width}m")
        print(f"   Preissmann系统中的边坡: {side_slope}")
        
        # 2. 恒定流计算与Preissmann系统的差异
        print("2. 恒定流计算使用的是模型自带的面积函数")
        print("   而Preissmann系统使用的是简化的梯形断面公式")
        print("   这可能导致不一致")
        
        # 3. 建议的修复方案
        print("\n=== 建议的修复方案 ===")
        print("1. 统一几何计算：让Preissmann系统使用与恒定流计算相同的面积函数")
        print("2. 或者：调整恒定流初始条件，使其更接近Preissmann系统的假设")
        print("3. 或者：在初始化后进行一次Newton迭代以调整到真正的平衡状态")
        
        return False
    else:
        print("✓ 恒定流平衡基本满足")
        return True

if __name__ == "__main__":
    success = analyze_momentum_residual()
    if success:
        print("\n✓ 动量方程初始状态合理")
    else:
        print("\n✗ 动量方程初始状态存在问题，需要修复")