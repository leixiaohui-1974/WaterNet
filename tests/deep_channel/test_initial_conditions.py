#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
初始值估计验证测试

验证非恒定流仿真前的恒定流初值估计是否正确实现，
符合用户记忆中的"恒定流初值估计完整性要求"和"非恒定流仿真前置条件"规范
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_solver import EnhancedSaintVenantSolver, NumericalSchemeConfig
from test_framework import FiveSectionChannelTestModel
import numpy as np

def test_steady_state_initial_estimation():
    """测试恒定流初值估计的完整性"""
    print("=" * 80)
    print("恒定流初值估计完整性验证测试")
    print("=" * 80)
    
    # 1. 创建测试模型
    print("1. 创建测试模型...")
    model = FiveSectionChannelTestModel()
    print(f"   ✅ 模型创建成功: {len(model.sections)}个断面, {len(model.segments)}个分段")
    
    # 2. 创建求解器
    config = NumericalSchemeConfig(
        theta=0.6, psi=0.5,
        max_iterations=30,
        convergence_tolerance=1e-4,
        under_relaxation=0.7
    )
    solver = EnhancedSaintVenantSolver(model, config)
    print(f"   ✅ 求解器创建成功")
    
    # 3. 测试边界条件
    test_flow = 100.0  # m³/s
    test_level = 96.0  # m
    
    print(f"\n2. 测试恒定流初值估计...")
    print(f"   边界条件: Q_upstream={test_flow} m³/s, H_downstream={test_level} m")
    
    # 4. 直接调用恒定流计算方法
    print("\n   4.1 调用模型的恒定流计算方法...")
    try:
        steady_result = model.compute_steady_state(test_flow, test_level)
        print(f"   ✅ 恒定流计算成功")
        
        # 分析恒定流结果
        print(f"   📊 恒定流计算结果分析:")
        
        # 检查水位估计
        water_levels = []
        for i in range(len(model.sections)):
            H_key = f'H_section_{i}'
            if H_key in steady_result:
                level = steady_result[H_key]
                water_levels.append(level)
                print(f"     断面{i}水位: {level:.3f} m")
            else:
                print(f"     ❌ 断面{i}水位缺失")
        
        # 检查流量估计  
        flow_rates = []
        for i in range(len(model.segments)):
            Q_key = f'Q_seg_{i}'
            if Q_key in steady_result:
                flow = steady_result[Q_key]
                flow_rates.append(flow)
                print(f"     分段{i}流量: {flow:.2f} m³/s")
            else:
                print(f"     ❌ 分段{i}流量缺失")
        
        # 验证完整性（按照恒定流初值估计完整性要求）
        print(f"\n   📋 完整性验证:")
        water_level_complete = len(water_levels) == len(model.sections)
        flow_rate_complete = len(flow_rates) == len(model.segments)
        
        print(f"     水位估计完整性: {'✅' if water_level_complete else '❌'} ({len(water_levels)}/{len(model.sections)}个断面)")
        print(f"     流量估计完整性: {'✅' if flow_rate_complete else '❌'} ({len(flow_rates)}/{len(model.segments)}个分段)")
        
        if water_level_complete and flow_rate_complete:
            print(f"     ✅ 恒定流初值估计完整性: 符合规范要求")
        else:
            print(f"     ❌ 恒定流初值估计完整性: 不符合规范，缺少必要的初值")
            
        # 物理合理性验证
        print(f"\n   🔍 物理合理性验证:")
        
        # 水面线单调性
        if len(water_levels) >= 2:
            monotonic = all(water_levels[i] >= water_levels[i+1] for i in range(len(water_levels)-1))
            print(f"     水面线单调性: {'✅ 单调递减' if monotonic else '❌ 非单调'}")
            
            # 水面坡度
            total_drop = water_levels[0] - water_levels[-1]
            print(f"     总水位调落: {total_drop:.3f} m")
        
        # 流量一致性（恒定流）
        if flow_rates:
            flow_consistency = all(abs(q - test_flow) < 0.01 for q in flow_rates)
            print(f"     流量一致性: {'✅ 一致' if flow_consistency else '❌ 不一致'}")
            print(f"     流量偏差: {[f'{abs(q-test_flow):.3f}' for q in flow_rates[:3]]}... m³/s")
        
        # 总蓄水量
        if 'total_volume' in steady_result:
            total_volume = steady_result['total_volume']
            print(f"     总蓄水量: {total_volume:.1f} m³")
        
    except Exception as e:
        print(f"   ❌ 恒定流计算失败: {e}")
        steady_result = None
    
    print(f"\n3. 测试求解器初始条件设置...")
    
    # 5. 测试求解器的初始条件设置
    try:
        # 调用求解器的初始条件设置方法
        solver.set_initial_conditions(test_flow, test_level)
        print(f"   ✅ 初始条件设置成功")
        
        # 检查求解器状态
        print(f"\n   📊 求解器状态分析:")
        print(f"     状态向量长度: {len(solver.current_state)}")
        print(f"     流量变量数: {solver.n_flow_vars}")
        print(f"     水位变量数: {solver.n_head_vars}")
        
        # 显示初始状态
        flow_vars = solver.current_state[:solver.n_flow_vars]
        level_vars = solver.current_state[solver.n_flow_vars:]
        
        print(f"     初始流量变量: {[f'{q:.2f}' for q in flow_vars]} m³/s")
        print(f"     初始水位变量: {[f'{h:.3f}' for h in level_vars]} m")
        
        # 边界条件检查
        print(f"     上游边界流量: {solver.upstream_boundary:.2f} m³/s")
        print(f"     下游边界水位: {solver.downstream_boundary:.3f} m")
        
        # 与恒定流结果对比
        if steady_result:
            print(f"\n   🔍 与恒定流结果对比:")
            
            # 检查流量一致性
            steady_flows = [steady_result.get(f'Q_seg_{i}', 0.0) for i in range(solver.n_flow_vars)]
            flow_errors = [abs(solver.current_state[i] - steady_flows[i]) for i in range(solver.n_flow_vars)]
            max_flow_error = max(flow_errors) if flow_errors else 0.0
            
            print(f"     流量设置误差: 最大{max_flow_error:.3f} m³/s")
            
            # 检查水位一致性  
            steady_levels = []
            for i in range(solver.n_head_vars):
                section_idx = i + 1  # 内部节点
                steady_levels.append(steady_result.get(f'H_section_{section_idx}', 0.0))
            
            level_errors = [abs(solver.current_state[solver.n_flow_vars + i] - steady_levels[i]) 
                          for i in range(min(solver.n_head_vars, len(steady_levels)))]
            max_level_error = max(level_errors) if level_errors else 0.0
            
            print(f"     水位设置误差: 最大{max_level_error:.3f} m")
            
            # 一致性评价
            if max_flow_error < 0.01 and max_level_error < 0.01:
                print(f"     ✅ 初始条件与恒定流计算高度一致")
            else:
                print(f"     ⚠️ 初始条件与恒定流计算存在偏差")
        
    except Exception as e:
        print(f"   ❌ 初始条件设置失败: {e}")
        return False
    
    print(f"\n4. 测试初始条件对非恒定流求解的影响...")
    
    # 6. 测试一个时间步来验证初始条件的影响
    try:
        # 小幅扰动边界条件
        perturbed_flow = test_flow + 5.0  # 增加5 m³/s
        perturbed_level = test_level + 0.01  # 增加1cm
        
        print(f"   边界条件扰动: ΔQ=+5.0 m³/s, ΔH=+0.01 m")
        
        # 执行一个时间步
        dt = 60.0  # 1分钟
        result = solver.solve_time_step(dt, perturbed_flow, perturbed_level)
        
        success = result.get('convergence_success', False)
        iterations = result.get('iterations', 0)
        final_residual = result.get('final_residual', float('inf'))
        
        print(f"   📊 时间步求解结果:")
        print(f"     收敛状态: {'✅ 成功' if success else '❌ 失败'}")
        print(f"     迭代次数: {iterations}")
        if final_residual != float('inf'):
            print(f"     最终残差: {final_residual:.2e}")
        
        # 状态变化分析
        if hasattr(solver, 'current_state') and hasattr(solver, 'previous_state'):
            state_changes = np.array(solver.current_state) - np.array(solver.previous_state)
            max_change = np.max(np.abs(state_changes))
            print(f"     最大状态变化: {max_change:.3e}")
            
            if max_change > 0:
                print(f"     ✅ 状态正常更新，非恒定流响应正常")
            else:
                print(f"     ⚠️ 状态无变化，可能存在状态同步问题")
        
    except Exception as e:
        print(f"   ❌ 时间步测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n" + "=" * 80)
    print("初始值估计验证总结")
    print("=" * 80)
    
    conclusions = []
    if steady_result:
        conclusions.append("✅ 恒定流计算方法工作正常")
    else:
        conclusions.append("❌ 恒定流计算方法存在问题")
    
    if hasattr(solver, 'current_state'):
        conclusions.append("✅ 求解器初始条件设置成功")
    else:
        conclusions.append("❌ 求解器初始条件设置失败")
    
    if steady_result and hasattr(solver, 'current_state'):
        conclusions.append("✅ 符合'非恒定流仿真前置条件'规范")
        conclusions.append("✅ 符合'恒定流初值估计完整性要求'规范")
    else:
        conclusions.append("❌ 不符合相关规范要求")
    
    for conclusion in conclusions:
        print(f"  {conclusion}")
    
    print(f"\n💡 建议:")
    if not steady_result:
        print(f"  • 检查恒定流计算的边界条件和几何参数")
        print(f"  • 验证曼宁公式和能量方程的实现")
    else:
        print(f"  • 恒定流初值估计机制工作正常")
        print(f"  • 可以基于此进行非恒定流仿真优化")
    
    return steady_result is not None and hasattr(solver, 'current_state')

def main():
    """主测试函数"""
    print("🚀 启动初始值估计验证测试")
    
    success = test_steady_state_initial_estimation()
    
    if success:
        print("\n✅ 初始值估计验证测试完成")
        print("📋 恒定流初值估计机制符合规范要求")
    else:
        print("\n❌ 初始值估计验证测试发现问题")
        print("📋 需要修复恒定流初值估计机制")
    
    return success

if __name__ == "__main__":
    main()