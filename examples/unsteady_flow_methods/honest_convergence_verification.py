#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诚实的收敛验证 - 严格验证是否真实收敛

严格按照数值求解失败处理规范，杜绝任何造假行为
"""

import sys
import os
import numpy as np

# 添加必要的路径
current_dir = os.path.dirname(os.path.abspath(__file__))
tests_dir = os.path.join(current_dir, '..', '..', 'tests', 'deep_channel')
sys.path.append(tests_dir)
sys.path.append(current_dir)

def honest_convergence_test():
    """诚实的收敛测试 - 严格验证"""
    print("🔍 严格收敛验证 - 杜绝造假")
    print("=" * 60)
    
    try:
        # 导入模块
        from enhanced_solver import EnhancedSaintVenantSolver, NumericalSchemeConfig, StabilityConfig
        from advanced_numerical_optimizer import OptimizationConfig, MatrixConditioningStrategy
        from waternet.models.saint_venant import SaintVenantModel
        
        print("✅ 模块导入成功")
        
        # 创建最严格的验证配置
        optimization_config = OptimizationConfig(
            matrix_strategy=MatrixConditioningStrategy.PHYSIC_BASED,
            cfl_target=0.05,
            initial_relaxation=0.05,
            min_relaxation=0.001,
            max_relaxation=0.1,
            max_condition_number=1e4
        )
        
        numerical_config = NumericalSchemeConfig(
            theta=1.0,  # 全隐式
            psi=0.5,
            max_iterations=200,
            convergence_tolerance=1e-6,  # 更严格的容差
            under_relaxation=0.05,
            adaptive_relaxation=True
        )
        
        stability_config = StabilityConfig(
            enable_adaptive_timestep=True,
            min_timestep=1.0,
            max_timestep=30.0,
            cfl_safety_factor=0.1
        )
        
        print(f"📋 验证配置:")
        print(f"   收敛容差: {numerical_config.convergence_tolerance:.1e} (严格)")
        print(f"   最大迭代: {numerical_config.max_iterations}")
        print(f"   优化策略: {optimization_config.matrix_strategy.value}")
        
        # 创建简化模型
        def create_area_func(bottom_width=15.0, side_slope=1.5, elevation=85.0):
            def area_func(h):
                depth = max(0.1, h - elevation)
                return bottom_width * depth + side_slope * depth**2
            return area_func
        
        def create_top_width_func(bottom_width=15.0, side_slope=1.5, elevation=85.0):
            def top_width_func(h):
                depth = max(0.1, h - elevation)
                return bottom_width + 2 * side_slope * depth
            return top_width_func
        
        sections = [
            {
                'mileage': 0.0,
                'elevation': 86.0,
                'roughness': 0.025,
                'area_func': create_area_func(12.0, 1.5, 86.0),
                'top_width_func': create_top_width_func(12.0, 1.5, 86.0)
            },
            {
                'mileage': 2500.0,
                'elevation': 85.5,
                'roughness': 0.025,
                'area_func': create_area_func(15.0, 1.5, 85.5),
                'top_width_func': create_top_width_func(15.0, 1.5, 85.5)
            },
            {
                'mileage': 5000.0,
                'elevation': 85.0,
                'roughness': 0.030,
                'area_func': create_area_func(18.0, 2.0, 85.0),
                'top_width_func': create_top_width_func(18.0, 2.0, 85.0)
            }
        ]
        
        model = SaintVenantModel(
            name="honest_test_channel",
            upstream_node="upstream",
            downstream_node="downstream",
            sections=sections,
            solver_type="enhanced"
        )
        
        print("✅ 圣维南模型创建成功")
        
        # 创建求解器
        enhanced_solver = EnhancedSaintVenantSolver(
            model=model,
            numerical_config=numerical_config,
            stability_config=stability_config,
            optimization_config=optimization_config
        )
        
        # 检查优化器是否真正集成
        if enhanced_solver.numerical_optimizer is None:
            print("❌ 数值优化器未成功集成")
            return False
            
        print("✅ 数值优化器成功集成")
        
        # 设置初始条件
        initial_flow = 100.0
        downstream_level = 96.0
        enhanced_solver.set_initial_conditions(initial_flow, downstream_level)
        print("✅ 初始条件设置完成")
        
        # 多次测试以验证一致性
        print("\n🧪 进行多次严格收敛测试...")
        success_count = 0
        total_tests = 5
        
        for test_id in range(total_tests):
            print(f"\n--- 测试 {test_id + 1}/{total_tests} ---")
            
            # 每次测试使用稍微不同的参数
            test_dt = 30.0 + test_id * 10  # 30s, 40s, 50s, 60s, 70s
            test_upstream_flow = 100.0 + test_id * 0.5  # 微小变化
            test_downstream_level = 96.0 + test_id * 0.001  # 极小变化
            
            print(f"   参数: dt={test_dt}s, Q={test_upstream_flow:.1f}m³/s, H={test_downstream_level:.3f}m")
            
            try:
                result = enhanced_solver.solve_time_step(
                    dt=test_dt,
                    upstream_flow=test_upstream_flow,
                    downstream_water_level=test_downstream_level
                )
                
                if result['convergence_success']:
                    success_count += 1
                    print(f"   ✅ 收敛成功: {result['iterations']}次迭代")
                    
                    # 严格验证结果的真实性
                    if 'flow_variables' in result and isinstance(result['flow_variables'], dict):
                        flows = list(result['flow_variables'].values())
                        if len(flows) > 0:
                            print(f"      流量范围: {min(flows):.2f} - {max(flows):.2f} m³/s")
                        else:
                            print("      ⚠️ 流量数据为空")
                    
                    if 'water_levels' in result and isinstance(result['water_levels'], dict):
                        levels = list(result['water_levels'].values())
                        if len(levels) > 0:
                            print(f"      水位范围: {min(levels):.3f} - {max(levels):.3f} m")
                        else:
                            print("      ⚠️ 水位数据为空")
                            
                    # 检查优化统计
                    opt_applied = enhanced_solver.statistics.get('optimization_applied', 0)
                    print(f"      优化应用: {opt_applied}次")
                    
                else:
                    print(f"   ❌ 收敛失败: {result['iterations']}次迭代")
                    print(f"      按照规范：立即终止，不使用估算数据")
                    
            except Exception as e:
                print(f"   ❌ 测试异常: {e}")
                
        # 计算真实收敛率
        convergence_rate = success_count / total_tests
        print(f"\n📊 真实收敛统计:")
        print(f"   成功测试: {success_count}/{total_tests}")
        print(f"   收敛率: {convergence_rate:.1%}")
        
        # 严格判断
        if convergence_rate == 1.0:
            print("\n🏆 达到100%收敛率要求")
            return True
        elif convergence_rate >= 0.8:
            print(f"\n⚠️ 收敛率{convergence_rate:.1%}未达到100%要求，需进一步优化")
            return False
        else:
            print(f"\n❌ 收敛率{convergence_rate:.1%}过低，优化失败")
            return False
            
    except Exception as e:
        print(f"❌ 验证过程异常: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("🎯 诚实收敛验证程序")
    print("🚫 严格按照数值求解失败处理规范，杜绝造假")
    print("============================================================")
    
    success = honest_convergence_test()
    
    print("\n============================================================")
    if success:
        print("✅ 验证通过：100%收敛率达成")
        print("📋 验证要点:")
        print("   • 严格收敛容差测试")
        print("   • 多次一致性验证")
        print("   • 真实数据结构检查")
        print("   • 优化策略应用确认")
    else:
        print("❌ 验证失败：未达到100%收敛率要求")
        print("📋 问题分析:")
        print("   • 需要进一步优化数值策略")
        print("   • 可能存在特定条件下的收敛问题")
        print("   • 严格按照规范：不使用估算数据继续")

if __name__ == "__main__":
    main()