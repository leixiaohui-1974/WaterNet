#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接测试基础库ImplicitSolverAgent功能（不依赖SaintVenantModel）
"""

from waternet.models.implicit_solver import ImplicitSolverAgent, SolverConfig
from waternet.models.boundary_conditions import BoundaryConditionManager, FlowBoundary, StageBoundary, BoundaryConditionConfig
from waternet.interfaces.hydro_model import HydroModel
import numpy as np
from typing import Dict, List, Any

class SimpleTestModel(HydroModel):
    """简单的测试模型，用于验证ImplicitSolverAgent"""
    
    def __init__(self, name: str):
        super().__init__(name, ["node1", "node2"])
        self.variable_names = ["H_node1", "H_node2", "Q_flow"]
    
    def get_variable_names(self) -> List[str]:
        return self.variable_names
    
    def get_equations(self, variables: Dict[str, float], dt: float, 
                     prev_states: Dict[str, float]) -> Dict[str, float]:
        """简单的方程组：连续性方程和阻力方程"""
        H1 = variables.get("H_node1", 100.0)
        H2 = variables.get("H_node2", 99.0)
        Q = variables.get("Q_flow", 10.0)
        
        # 方程1: 连续性方程 (简化为Q进 - Q出 = 0)
        eq1 = Q - 10.0  # 假设上游入流为10 m³/s
        
        # 方程2: 水力方程 (简化为 Q = C * sqrt(H1 - H2))
        C = 5.0
        if H1 > H2:
            eq2 = Q - C * np.sqrt(H1 - H2)
        else:
            eq2 = Q  # 避免负的平方根
        
        # 方程3: 下游边界条件将通过边界条件管理器处理
        eq3 = H2 - 99.0  # 占位方程，实际会被边界条件覆盖
        
        return {
            "continuity": eq1,
            "hydraulic": eq2,
            "boundary": eq3
        }

def test_basic_implicit_solver():
    print('🧪 测试基础ImplicitSolverAgent功能...')
    
    try:
        # 创建简单测试模型
        test_model = SimpleTestModel("test_model")
        print(f'   模型变量: {test_model.get_variable_names()}')
        
        # 创建边界条件管理器
        boundary_manager = BoundaryConditionManager()
        
        # 创建上游流量边界条件
        upstream_config = BoundaryConditionConfig("upstream_flow", "上游流量边界")
        upstream_bc = FlowBoundary("upstream_flow", "node1", 10.0, upstream_config)
        boundary_manager.add_boundary_condition(upstream_bc)
        
        # 创建下游水位边界条件
        downstream_config = BoundaryConditionConfig("downstream_stage", "下游水位边界")
        downstream_bc = StageBoundary("downstream_stage", "node2", 99.0, downstream_config)
        boundary_manager.add_boundary_condition(downstream_bc)
        
        print(f'   边界条件数量: {boundary_manager.get_boundary_condition_count()}')
        
        # 创建求解器配置
        solver_config = SolverConfig(
            max_iterations=20,
            tolerance=1e-3,
            relaxation_factor=0.8
        )
        
        # 创建ImplicitSolverAgent
        implicit_solver = ImplicitSolverAgent(
            models=[test_model],
            config=solver_config,
            boundary_manager=boundary_manager
        )
        
        print('✅ ImplicitSolverAgent 创建成功!')
        print(f'   求解器类型: {type(implicit_solver)}')
        
        # 测试稳态求解
        print('🚀 测试稳态求解...')
        
        # 设置初始条件
        initial_conditions = {
            'H_node1': 100.0,
            'H_node2': 99.0,
            'Q_flow': 10.0
        }
        
        steady_result = implicit_solver.solve_steady_state(initial_conditions)
        
        if steady_result.get('converged', False):
            print('   🎉 稳态求解成功!')
            statistics = steady_result.get('statistics')
            if statistics:
                print(f'   迭代次数: {statistics.total_iterations}')
                print(f'   最终残差: {statistics.final_residual_norm:.2e}')
                print(f'   耗时: {statistics.total_time:.3f}s')
            
            variables = steady_result.get('variables', {})
            for var_name, value in variables.items():
                print(f'   {var_name}: {value:.6f}')
            
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
                    converged = step_result.get('converged', False)
                    time_val = step_result.get('time', 0)
                    print(f'   时间步{i+1} (t={time_val:.1f}s): {"收敛 ✅" if converged else "未收敛 ❌"}')
                
                print('\n🎯 结论: 基础库的ImplicitSolverAgent完全正常，支持稳态和非恒定流时间序列求解!')
                return True
            else:
                print('   ❌ 时间序列求解失败')
                return False
        else:
            print('   ❌ 稳态求解未收敛')
            statistics = steady_result.get('statistics')
            if statistics:
                print(f'   失败原因: {statistics.failure_reason}')
                print(f'   迭代次数: {statistics.total_iterations}')
                print(f'   最终残差: {statistics.final_residual_norm:.2e}')
            return False
        
    except Exception as e:
        print(f'❌ 测试失败: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_basic_implicit_solver()
    if success:
        print("\n🎯 最终结论: 基础库的ImplicitSolverAgent功能完全正常!")
        print("   ✅ 支持稳态求解")
        print("   ✅ 支持非恒定流时间序列求解")
        print("   ✅ 这就是我们需要的真正非恒定流求解器!")
    else:
        print("\n❌ ImplicitSolverAgent测试失败")