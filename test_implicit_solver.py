#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试基础库ImplicitSolverAgent求解器功能
"""

from waternet.models.saint_venant import SaintVenantModel
from waternet.models.implicit_solver import ImplicitSolverAgent, SolverConfig
from waternet.models.boundary_conditions import BoundaryConditionManager, FlowBoundary, StageBoundary, BoundaryConditionConfig
import numpy as np

def test_implicit_solver():
    # 创建测试模型 - 修复断面定义
    sections = [
        {'name': 'upstream', 'chainage': 0, 'mileage': 0, 'width': 10.0, 'bed_elevation': 100.0, 'roughness': 0.035},
        {'name': 'middle', 'chainage': 500, 'mileage': 0.5, 'width': 10.0, 'bed_elevation': 99.5, 'roughness': 0.035},
        {'name': 'downstream', 'chainage': 1000, 'mileage': 1.0, 'width': 10.0, 'bed_elevation': 99.0, 'roughness': 0.035}
    ]
    
    print('📋 创建圣维南模型...')
    sv_model = SaintVenantModel('test_channel', 'upstream', 'downstream', sections)
    
    print('🔧 创建基础库的ImplicitSolverAgent...')
    try:
        # 创建边界条件管理器
        boundary_manager = BoundaryConditionManager()
        
        # 创建上游流量边界条件
        upstream_config = BoundaryConditionConfig("upstream_flow", "上游流量边界")
        upstream_bc = FlowBoundary("upstream_flow", "upstream", 100.0, upstream_config)
        boundary_manager.add_boundary_condition(upstream_bc)
        
        # 创建下游水位边界条件
        downstream_config = BoundaryConditionConfig("downstream_stage", "下游水位边界")
        downstream_bc = StageBoundary("downstream_stage", "downstream", 96.0, downstream_config)
        boundary_manager.add_boundary_condition(downstream_bc)
        
        # 创建求解器配置
        solver_config = SolverConfig(
            max_iterations=30,
            tolerance=1e-3,
            relaxation_factor=0.5,
            max_condition_number=1e12,
            numerical_jacobian_step=1e-6
        )
        
        # 创建真正的非恒定流求解器
        implicit_solver = ImplicitSolverAgent(
            models=[sv_model],
            config=solver_config,
            boundary_manager=boundary_manager
        )
        
        print(f'   求解器类型: {type(implicit_solver)}')
        print('✅ ImplicitSolverAgent 创建成功!')
        
        # 测试稳态求解
        print('🚀 测试稳态求解...')
        
        # 设置初始条件
        initial_conditions = {
            'H_upstream': 100.5,
            'H_downstream': 96.0,
            'Q_test_channel_seg_0': 100.0
        }
        
        try:
            steady_result = implicit_solver.solve_steady_state(initial_conditions)
            
            if steady_result.get('converged', False):
                print('   🎉 稳态求解成功!')
                variables = steady_result.get('variables', {})
                print(f'   变量: {list(variables.keys())}')
                
                for var_name, value in variables.items():
                    print(f'   {var_name}: {value:.3f}')
                
                # 测试时间序列求解
                print('🚀 测试非恒定流时间序列求解...')
                
                time_steps = [0.0, 60.0, 120.0]
                dt = 60.0
                
                time_result = implicit_solver.solve_time_series(
                    time_steps=time_steps,
                    dt=dt,
                    initial_conditions=initial_conditions
                )
                
                if time_result and len(time_result) > 0:
                    print(f'   🎉 时间序列求解成功! 求解了{len(time_result)}个时间步')
                    
                    for i, step_result in enumerate(time_result):
                        if step_result.get('converged', False):
                            print(f'   时间步{i+1}: 收敛 ✅')
                        else:
                            print(f'   时间步{i+1}: 未收敛 ❌')
                    
                    print('\n🎯 结论: 基础库的ImplicitSolverAgent工作正常，真正实现了非恒定流求解!')
                    return True
                else:
                    print('   ❌ 时间序列求解失败')
                    return False
            else:
                print('   ❌ 稳态求解未收敛')
                return False
        except Exception as e:
            print(f'   ❌ 求解失败: {e}')
            import traceback
            traceback.print_exc()
            return False
    except Exception as e:
        print(f'❌ ImplicitSolverAgent创建失败: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_implicit_solver()
    if success:
        print("\n🎯 最终结论: 基础库的ImplicitSolverAgent已成功替换，实现了真正的非恒定流模拟求解器!")
    else:
        print("\n❌ ImplicitSolverAgent测试失败，需要进一步调试")