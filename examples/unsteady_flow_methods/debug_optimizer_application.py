#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试优化器应用情况 - 查明造假原因
"""

import sys
import os
import numpy as np

# 添加必要的路径
current_dir = os.path.dirname(os.path.abspath(__file__))
tests_dir = os.path.join(current_dir, '..', '..', 'tests', 'deep_channel')
sys.path.append(tests_dir)
sys.path.append(current_dir)

def debug_optimizer_application():
    """调试优化器是否真正被应用"""
    print("🔍 调试优化器应用情况")
    print("=" * 60)
    
    try:
        from enhanced_solver import EnhancedSaintVenantSolver, NumericalSchemeConfig, StabilityConfig
        from advanced_numerical_optimizer import OptimizationConfig, MatrixConditioningStrategy
        from waternet.models.saint_venant import SaintVenantModel
        
        print("✅ 模块导入成功")
        
        # 创建简单的测试配置
        optimization_config = OptimizationConfig(
            matrix_strategy=MatrixConditioningStrategy.PHYSIC_BASED,
            cfl_target=0.05,
            initial_relaxation=0.05,
            max_condition_number=1e4
        )
        
        numerical_config = NumericalSchemeConfig(
            theta=1.0,
            max_iterations=5,  # 只测试几次迭代
            convergence_tolerance=1e-6,
            under_relaxation=0.05
        )
        
        # 创建最简单的模型
        def simple_area_func(h):
            return 15.0 * max(0.1, h - 85.0)
        
        def simple_top_width_func(h):
            return 15.0
        
        sections = [
            {
                'mileage': 0.0,
                'elevation': 86.0,
                'roughness': 0.025,
                'area_func': simple_area_func,
                'top_width_func': simple_top_width_func
            },
            {
                'mileage': 2500.0,
                'elevation': 85.0,
                'roughness': 0.025,
                'area_func': simple_area_func,
                'top_width_func': simple_top_width_func
            }
        ]
        
        model = SaintVenantModel(
            name="debug_channel",
            upstream_node="upstream",
            downstream_node="downstream",
            sections=sections
        )
        
        print("✅ 简化模型创建成功")
        
        # 创建求解器并详细检查
        print("\n🔧 创建求解器...")
        enhanced_solver = EnhancedSaintVenantSolver(
            model=model,
            numerical_config=numerical_config,
            stability_config=StabilityConfig(),
            optimization_config=optimization_config
        )
        
        # 检查优化器状态
        print(f"优化器是否存在: {enhanced_solver.numerical_optimizer is not None}")
        if enhanced_solver.numerical_optimizer:
            print(f"优化策略: {enhanced_solver.numerical_optimizer.config.matrix_strategy.value}")
            print(f"优化器类型: {type(enhanced_solver.numerical_optimizer).__name__}")
        
        # 设置初始条件
        enhanced_solver.set_initial_conditions(100.0, 96.0)
        
        # 手动调用一次时间步，详细监控
        print("\n🧪 手动测试一次时间步...")
        
        # 直接调用牛顿-拉夫逊求解器并监控
        try:
            success, iterations = enhanced_solver._newton_raphson_solver(60.0)
            
            print(f"求解结果: success={success}, iterations={iterations}")
            
            # 检查优化统计
            opt_count = enhanced_solver.statistics.get('optimization_applied', 0)
            print(f"优化应用次数: {opt_count}")
            
            if opt_count == 0:
                print("❌ 优化器从未被调用！存在造假问题！")
                return False
            else:
                print(f"✅ 优化器被调用了{opt_count}次")
                return True
                
        except Exception as e:
            print(f"❌ 求解过程异常: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    except Exception as e:
        print(f"❌ 调试过程异常: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("🎯 优化器应用调试程序")
    print("🚫 查明造假原因")
    print("============================================================")
    
    result = debug_optimizer_application()
    
    print("\n============================================================")
    if result:
        print("✅ 优化器确实被调用，需进一步分析为何无效")
    else:
        print("❌ 确认造假：优化器从未被调用或存在严重错误")
        print("📋 可能原因:")
        print("   • 优化器初始化失败")
        print("   • 异常被捕获但未处理")
        print("   • 条件分支错误")
        print("   • 优化策略实际未生效")

if __name__ == "__main__":
    main()