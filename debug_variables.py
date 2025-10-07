#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试SaintVenantModel的变量名
"""

from waternet.models.saint_venant import SaintVenantModel

def debug_saint_venant_variables():
    # 创建测试模型 - 修复断面定义
    sections = [
        {
            'name': 'upstream', 
            'mileage': 0, 
            'elevation': 100.0, 
            'roughness': 0.035,
            'area_func': lambda h: max(0.1, (h - 100.0) * 10.0) if h > 100.0 else 0.1,
            'top_width_func': lambda h: 10.0
        },
        {
            'name': 'middle', 
            'mileage': 0.5, 
            'elevation': 99.5, 
            'roughness': 0.035,
            'area_func': lambda h: max(0.1, (h - 99.5) * 10.0) if h > 99.5 else 0.1,
            'top_width_func': lambda h: 10.0
        },
        {
            'name': 'downstream', 
            'mileage': 1.0, 
            'elevation': 99.0, 
            'roughness': 0.035,
            'area_func': lambda h: max(0.1, (h - 99.0) * 10.0) if h > 99.0 else 0.1,
            'top_width_func': lambda h: 10.0
        }
    ]
    
    print('📋 创建圣维南模型...')
    sv_model = SaintVenantModel('test_channel', 'upstream', 'downstream', sections)
    
    print('🔍 检查变量名...')
    variable_names = sv_model.get_variable_names()
    print(f'   变量总数: {len(variable_names)}')
    for i, var_name in enumerate(variable_names):
        print(f'   变量{i+1}: {var_name}')
    
    print('🔧 创建ImplicitSolverAgent...')
    enhanced_solver = sv_model.create_enhanced_solver()
    if enhanced_solver:
        print(f'   求解器类型: {type(enhanced_solver)}')
        
        # 检查求解器的变量映射
        if hasattr(enhanced_solver, 'variable_names'):
            print(f'   求解器变量总数: {len(enhanced_solver.variable_names)}')
            for i, var_name in enumerate(enhanced_solver.variable_names):
                print(f'   求解器变量{i+1}: {var_name}')
        
        # 检查边界条件
        if hasattr(enhanced_solver, 'boundary_manager'):
            boundary_count = enhanced_solver.boundary_manager.get_boundary_condition_count()
            print(f'   边界条件总数: {boundary_count}')
    else:
        print('   ❌ 求解器创建失败')

if __name__ == "__main__":
    debug_saint_venant_variables()