#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试增强求解器的收敛问题
"""

import sys
import os
import numpy as np

# 添加项目路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from enhanced_solver import EnhancedSaintVenantSolver, NumericalSchemeConfig
from waternet.models.saint_venant import SaintVenantModel

def test_convergence():
    """测试收敛性问题"""
    
    # 创建简单的断面模型，符合SaintVenantModel的接口
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

    # 修复：SaintVenantModel需要节点名称
    model = SaintVenantModel('test_channel', 'upstream_node', 'downstream_node', sections)

    # 当前参数配置
    print("=== 当前配置测试 ===")
    config = NumericalSchemeConfig(
        max_iterations=20,
        convergence_tolerance=1e-6,
        under_relaxation=0.7
    )

    solver = EnhancedSaintVenantSolver(model, config)
    solver.set_initial_conditions(100.0, 99.0)
    
    result = solver.solve_time_step(1.0, 100.0, 99.0)
    print(f'收敛状态: {result["convergence_success"]}')
    print(f'迭代次数: {result["iterations"]}')
    print(f'流量: {result["flow_variables"]}')
    print(f'水位: {result["water_levels"]}')
    
    # 增强参数配置测试
    print("\n=== 增强配置测试 ===")
    enhanced_config = NumericalSchemeConfig(
        max_iterations=50,
        convergence_tolerance=1e-4,
        under_relaxation=0.3,
        adaptive_relaxation=True
    )
    
    solver2 = EnhancedSaintVenantSolver(model, enhanced_config)
    solver2.set_initial_conditions(100.0, 99.0)
    
    result2 = solver2.solve_time_step(1.0, 100.0, 99.0)
    print(f'收敛状态: {result2["convergence_success"]}')
    print(f'迭代次数: {result2["iterations"]}')
    print(f'流量: {result2["flow_variables"]}')
    print(f'水位: {result2["water_levels"]}')

if __name__ == "__main__":
    test_convergence()