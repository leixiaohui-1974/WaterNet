#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证object_system_demo.py中的收敛问题，并应用我们开发的数值优化策略
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'tests', 'deep_channel'))

from object_system_demo import create_channel_config

# 导入我们开发的优化策略
try:
    from advanced_numerical_optimizer import AdvancedNumericalOptimizer, OptimizationConfig, MatrixConditioningStrategy
    from solve_iterative_scaling_issue import ImprovedAdvancedNumericalOptimizer
    from enhanced_solver import EnhancedSaintVenantSolver, NumericalSchemeConfig
    optimization_available = True
    print("✅ 成功导入高级数值优化模块")
except ImportError as e:
    print(f"⚠️ 无法导入优化模块: {e}")
    optimization_available = False

def test_demo_convergence_issue():
    """测试demo中的收敛问题"""
    print("="*80)
    print("object_system_demo收敛问题验证和优化测试")
    print("="*80)
    
    # 1. 重现问题
    print("1. 重现原始收敛问题...")
    channel_config = create_channel_config()
    print(f"   使用配置: {channel_config['object_definition']['name']}")
    
    # 2. 验证我们的优化策略是否可用
    if not optimization_available:
        print("   ❌ 数值优化模块不可用，无法应用优化策略")
        return
    
    print("2. 应用高级数值优化策略...")
    
    # 创建测试场景（与demo中第9部分相同的边界条件）
    demo_boundary_series = {
        'time_steps': [i * 600 for i in range(21)],  # 0, 600, 1200, ..., 12000秒
        'upstream_flows': [
            100.0, 105.0, 115.0, 125.0, 140.0, 155.0, 170.0, 180.0, 175.0, 160.0,
            145.0, 130.0, 120.0, 110.0, 105.0, 102.0, 100.0, 98.0, 96.0, 95.0, 95.0
        ],
        'downstream_levels': [
            96.0, 96.02, 96.05, 96.08, 96.12, 96.18, 96.25, 96.30, 96.28, 96.22,
            96.15, 96.10, 96.08, 96.05, 96.03, 96.02, 96.01, 96.005, 96.0, 95.98, 95.98
        ]
    }
    
    print(f"   边界条件: {len(demo_boundary_series['time_steps'])}个时间点")
    print(f"   流量范围: {min(demo_boundary_series['upstream_flows'])}-{max(demo_boundary_series['upstream_flows'])} m³/s")
    print(f"   水位范围: {min(demo_boundary_series['downstream_levels'])}-{max(demo_boundary_series['downstream_levels'])} m")
    
    # 3. 使用我们的优化策略
    print("\n3. 配置优化求解器...")
    
    # 使用最成功的配置（极保守物理scaling）
    base_config = NumericalSchemeConfig(
        theta=1.0,  # 全隐式，最稳定
        psi=0.5,
        max_iterations=50,
        convergence_tolerance=1e-3,
        under_relaxation=0.2
    )
    
    opt_config = OptimizationConfig(
        matrix_strategy=MatrixConditioningStrategy.PHYSIC_BASED,
        cfl_target=0.2,
        initial_relaxation=0.2,
        min_relaxation=0.01,
        max_relaxation=0.5,
        dt_growth_limit=1.1,
        dt_reduction_factor=0.5,
        min_timestep=5.0,
        max_timestep=30.0,
        max_condition_number=1e8
    )
    
    print(f"   ✅ 基础配置: 全隐式格式，50次最大迭代")
    print(f"   ✅ 优化配置: 物理量纲scaling，CFL=0.2，极保守松弛")
    
    # 4. 创建简化的测试模型（基于demo配置）
    print("\n4. 创建测试模型...")
    try:
        from test_advanced_optimization import create_test_model
        model = create_test_model()
        
        # 使用改进的优化器
        solver = EnhancedSaintVenantSolver(model, base_config)
        
        # 替换为改进的优化器（如果可用）
        try:
            solver.advanced_optimizer = ImprovedAdvancedNumericalOptimizer(opt_config)
            print(f"   ✅ 使用改进的数值优化器")
        except:
            solver.advanced_optimizer = AdvancedNumericalOptimizer(opt_config)
            print(f"   ✅ 使用标准数值优化器")
        
        print(f"   模型: {len(model.sections)}个断面，{len(model.segments)}个分段")
        
    except Exception as e:
        print(f"   ❌ 模型创建失败: {e}")
        return
    
    # 5. 设置初始条件（与demo一致）
    print("\n5. 设置初始条件...")
    try:
        initial_flow = demo_boundary_series['upstream_flows'][0]  # 100.0
        initial_level = demo_boundary_series['downstream_levels'][0]  # 96.0
        
        solver.set_initial_conditions(initial_flow, initial_level)
        print(f"   ✅ 初始条件: Q={initial_flow} m³/s, H={initial_level} m")
        
    except Exception as e:
        print(f"   ❌ 初始条件设置失败: {e}")
        return
    
    # 6. 测试关键时间步（demo中失败的场景）
    print("\n6. 测试关键时间步收敛性...")
    
    test_steps = [
        {"step": 1, "dt": 600.0, "Q": 105.0, "H": 96.02},
        {"step": 5, "dt": 600.0, "Q": 140.0, "H": 96.12},
        {"step": 8, "dt": 600.0, "Q": 180.0, "H": 96.30}  # 峰值流量
    ]
    
    successful_steps = 0
    
    for test in test_steps:
        print(f"\n   --- 时间步 {test['step']} ---")
        print(f"   边界条件: Q={test['Q']} m³/s, H={test['H']} m, dt={test['dt']}s")
        
        try:
            result = solver.solve_time_step(test['dt'], test['Q'], test['H'])
            
            success = result.get('convergence_success', False)
            iterations = result.get('iterations', 0)
            final_residual = result.get('final_residual', float('inf'))
            
            print(f"   收敛状态: {'✅ 成功' if success else '❌ 失败'}")
            print(f"   迭代次数: {iterations}")
            if final_residual != float('inf'):
                print(f"   最终残差: {final_residual:.2e}")
            
            if hasattr(solver, 'advanced_optimizer'):
                stats = solver.advanced_optimizer.stats
                total_opt = sum(stats.values())
                print(f"   优化次数: {total_opt}")
            
            if success:
                successful_steps += 1
                print(f"   🎉 时间步 {test['step']} 收敛成功!")
            else:
                print(f"   ⚠️ 时间步 {test['step']} 仍未收敛")
                
        except Exception as e:
            print(f"   ❌ 时间步 {test['step']} 测试失败: {e}")
    
    # 7. 结果总结
    print(f"\n{'='*80}")
    print("收敛性验证总结")
    print(f"{'='*80}")
    
    success_rate = successful_steps / len(test_steps)
    print(f"成功收敛率: {successful_steps}/{len(test_steps)} ({success_rate*100:.1f}%)")
    
    if success_rate > 0.5:
        print(f"✅ 数值优化策略有效改善了demo中的收敛问题!")
        print(f"📈 建议在object_system_demo.py中集成这些优化策略")
    elif success_rate > 0:
        print(f"⚠️ 部分改善，建议进一步调优参数")
    else:
        print(f"❌ 优化策略未能解决收敛问题，需要更深层的改进")
    
    print(f"\n💡 建议的改进措施:")
    if success_rate > 0:
        print(f"  1. 在圣维南求解器中集成物理量纲scaling策略")
        print(f"  2. 使用更保守的数值参数（CFL<0.2, α<0.2）")
        print(f"  3. 增加预条件技术和早停机制")
    print(f"  4. 考虑细化网格或使用更稳健的数值格式")
    print(f"  5. 验证初始条件的物理合理性")
    
    return success_rate

def main():
    """主程序"""
    print("🚀 启动object_system_demo收敛问题验证")
    
    try:
        success_rate = test_demo_convergence_issue()
        
        if success_rate is not None and success_rate > 0:
            print(f"\n✅ 验证完成，优化策略在demo场景中有效")
            print(f"🎯 可以考虑将优化策略集成到主系统中")
        else:
            print(f"\n⚠️ 验证完成，需要进一步研究收敛问题")
            print(f"🔍 建议深入分析Jacobian矩阵的数值特性")
        
        return success_rate
        
    except Exception as e:
        print(f"❌ 验证过程出错: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    main()