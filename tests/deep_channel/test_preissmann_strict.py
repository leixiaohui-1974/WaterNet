#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试严格Preissmann格式的收敛性 - 使用合理参数
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

def test_preissmann_convergence():
    """测试严格Preissmann格式的收敛性"""
    
    print("=== 测试严格Preissmann格式 ===\n")
    
    # 创建更大的断面以匹配合理的流量
    def area_func(h, elevation, bottom_width=50.0, side_slope=2.0):
        depth = max(0.5, h - elevation)
        return bottom_width * depth + side_slope * depth**2
    
    def top_width_func(h, elevation, bottom_width=50.0, side_slope=2.0):
        depth = max(0.5, h - elevation)
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
            'mileage': 500.0,
            'elevation': 99.0,
            'roughness': 0.03,
            'area_func': lambda h: area_func(h, 99.0),
            'top_width_func': lambda h: top_width_func(h, 99.0)
        },
        {
            'mileage': 1000.0,
            'elevation': 98.0,
            'roughness': 0.03,
            'area_func': lambda h: area_func(h, 98.0),
            'top_width_func': lambda h: top_width_func(h, 98.0)
        }
    ]

    model = SaintVenantModel('test_preissmann', 'upstream_node', 'downstream_node', sections)
    
    # 使用合理的流量和更严格的参数配置
    initial_flow = 50.0  # 减小流量到合理范围
    downstream_level = 99.0  # 下游水位
    
    print(f"测试参数:")
    print(f"  初始流量: {initial_flow} m³/s")
    print(f"  下游水位: {downstream_level} m")
    print(f"  断面底宽: 50m, 边坡: 2:1")
    
    # 严格的Preissmann配置
    config = NumericalSchemeConfig(
        max_iterations=20,
        convergence_tolerance=1e-4,
        under_relaxation=0.3,
        theta=0.6,  # 时间加权系数
        psi=0.5     # 空间加权系数
    )
    
    solver = EnhancedSaintVenantSolver(model, config)
    
    print(f"\nPreissmann配置:")
    print(f"  时间加权θ: {config.theta}")
    print(f"  空间加权ψ: {config.psi}")
    print(f"  收敛容差: {config.convergence_tolerance}")
    print(f"  亚松弛系数: {config.under_relaxation}")
    
    # 设置初始条件并检查物理合理性
    solver.set_initial_conditions(initial_flow, downstream_level)
    
    print(f"\n初始化后状态:")
    print(f"  流量: {solver.current_state[:solver.n_flow_vars]}")
    print(f"  水位: {solver.current_state[solver.n_flow_vars:]}")
    
    # 测试恒定流条件下的平衡
    print(f"\n=== 恒定流平衡测试 ===")
    result = solver.solve_time_step(1.0, initial_flow, downstream_level)
    
    print(f"求解结果:")
    print(f"  收敛状态: {result['convergence_success']}")
    print(f"  迭代次数: {result['iterations']}")
    
    if result['convergence_success']:
        print("✓ 严格Preissmann格式收敛成功！")
        
        # 继续测试几个时间步
        print(f"\n=== 时间步进测试 ===")
        for step in range(1, 4):
            result = solver.solve_time_step(1.0, initial_flow, downstream_level)
            print(f"时间步{step+1}: 收敛={result['convergence_success']}, 迭代={result['iterations']}")
            
            if not result['convergence_success']:
                print(f"时间步{step+1}收敛失败")
                break
        
        return True
    else:
        print("✗ 严格Preissmann格式仍未收敛")
        
        # 分析残差
        print(f"\n=== 残差分析 ===")
        # 手动构建Preissmann系统进行分析
        try:
            jacobian, residual = solver._build_preissmann_system(
                solver.current_state, 1.0, config.theta, config.psi)
            
            residual_norm = np.linalg.norm(residual)
            print(f"残差L2范数: {residual_norm:.2e}")
            print(f"残差最大值: {np.max(np.abs(residual)):.2e}")
            print(f"残差分布: {residual}")
            
            # 检查每个方程的残差
            for i, res in enumerate(residual):
                if i % 2 == 0:
                    print(f"  连续性方程{i//2}: {res:.2e}")
                else:
                    print(f"  动量方程{i//2}: {res:.2e}")
                    
        except Exception as e:
            print(f"残差分析失败: {e}")
        
        return False

if __name__ == "__main__":
    success = test_preissmann_convergence()
    if success:
        print("\n✓ 严格Preissmann格式验证通过")
    else:
        print("\n✗ 严格Preissmann格式仍需优化")