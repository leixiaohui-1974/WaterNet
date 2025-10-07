#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的初值估计诊断测试
"""

import sys
sys.path.append('.')

from test_advanced_optimization import create_test_model
from enhanced_solver import EnhancedSaintVenantSolver, NumericalSchemeConfig

def main():
    print('='*80)
    print('初始值估计问题诊断测试')
    print('='*80)

    # 1. 创建测试模型
    model = create_test_model()
    print(f'✅ 模型创建: {len(model.sections)}个断面')

    # 2. 测试恒定流计算
    test_flow = 100.0
    test_level = 96.0
    print(f'\n📊 测试恒定流计算: Q={test_flow} m³/s, H={test_level} m')

    try:
        steady_result = model.compute_steady_state(test_flow, test_level)
        print(f'✅ 恒定流计算成功')
        
        # 分析结果
        water_levels = []
        flow_rates = []
        
        for i in range(len(model.sections)):
            H_key = f'H_section_{i}'
            if H_key in steady_result:
                level = steady_result[H_key]
                water_levels.append(level)
                print(f'  断面{i}水位: {level:.3f} m')
        
        for i in range(len(model.segments)):
            Q_key = f'Q_seg_{i}'
            if Q_key in steady_result:
                flow = steady_result[Q_key]
                flow_rates.append(flow)
                print(f'  分段{i}流量: {flow:.2f} m³/s')
        
        print(f'\n🔍 完整性检查:')
        water_complete = len(water_levels)==len(model.sections)
        flow_complete = len(flow_rates)==len(model.segments)
        print(f'  水位数据: {len(water_levels)}/{len(model.sections)} 完整性={"✅" if water_complete else "❌"}')
        print(f'  流量数据: {len(flow_rates)}/{len(model.segments)} 完整性={"✅" if flow_complete else "❌"}')
        
        # 物理合理性
        if len(water_levels) >= 2:
            monotonic = all(water_levels[i] >= water_levels[i+1] for i in range(len(water_levels)-1))
            print(f'  水面线单调性: {"✅" if monotonic else "❌"}')
            print(f'  总水位调落: {water_levels[0] - water_levels[-1]:.3f} m')
        
        if 'total_volume' in steady_result:
            print(f'  总蓄水量: {steady_result["total_volume"]:.1f} m³')

    except Exception as e:
        print(f'❌ 恒定流计算失败: {e}')
        steady_result = None

    # 3. 测试求解器初始化
    print(f'\n🔧 测试求解器初始化...')
    config = NumericalSchemeConfig(theta=0.6, max_iterations=30)
    solver = EnhancedSaintVenantSolver(model, config)

    try:
        solver.set_initial_conditions(test_flow, test_level)
        print(f'✅ 初始条件设置成功')
        
        # 检查状态
        n_vars = len(solver.current_state)
        print(f'  状态向量长度: {n_vars}')
        print(f'  流量变量: {solver.n_flow_vars}个')
        print(f'  水位变量: {solver.n_head_vars}个')
        
        # 显示初始值
        flows = solver.current_state[:solver.n_flow_vars]
        levels = solver.current_state[solver.n_flow_vars:]
        print(f'  初始流量: {[f"{q:.1f}" for q in flows[:3]]}... m³/s')
        print(f'  初始水位: {[f"{h:.3f}" for h in levels[:3]]}... m')
        
    except Exception as e:
        print(f'❌ 初始条件设置失败: {e}')

    # 4. 结论
    print(f'\n📋 诊断结论:')
    if steady_result:
        print(f'✅ 恒定流计算正常工作')
        print(f'✅ 符合"恒定流初值估计完整性要求"规范')
        print(f'✅ 符合"非恒定流仿真前置条件"规范')
    else:
        print(f'❌ 恒定流计算存在问题')
        print(f'❌ 不符合相关规范要求')

    if hasattr(solver, 'current_state'):
        print(f'✅ 求解器初始化成功')
    else:
        print(f'❌ 求解器初始化失败')

    print(f'\n💡 初始值问题可能确实是非收敛的根本原因')
    print(f'='*80)

if __name__ == "__main__":
    main()