#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
解决圣维南求解器收敛问题的根本性改进

重点：让所有三种优化策略都能收敛，而不是比较它们的相对表现
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from advanced_numerical_optimizer import AdvancedNumericalOptimizer, OptimizationConfig, MatrixConditioningStrategy
from test_advanced_optimization import OptimizedSaintVenantSolver, create_test_model
from enhanced_solver import NumericalSchemeConfig
import numpy as np

def create_convergence_focused_config():
    """创建专注于收敛性的配置"""
    # 基础求解器配置 - 更保守的设置
    base_config = NumericalSchemeConfig(
        theta=1.0,  # 全隐式，最稳定
        psi=0.5,    # 中心差分
        max_iterations=50,  # 增加迭代次数
        convergence_tolerance=1e-3,  # 放宽收敛容差
        under_relaxation=0.3  # 非常保守的松弛因子
    )
    
    return base_config

def create_robust_optimization_configs():
    """创建健壮的优化配置"""
    configs = []
    
    # 配置1: 极保守的物理量纲scaling
    config1 = OptimizationConfig(
        matrix_strategy=MatrixConditioningStrategy.PHYSIC_BASED,
        cfl_target=0.2,  # 非常小的CFL数
        initial_relaxation=0.2,  # 极保守
        min_relaxation=0.01,
        max_relaxation=0.5,  # 限制最大松弛因子
        dt_growth_limit=1.1,  # 极慢的时间步增长
        dt_reduction_factor=0.5,  # 快速减小时间步
        min_timestep=5.0,  # 更小的最小时间步
        max_timestep=30.0,  # 更小的最大时间步
        max_condition_number=1e8  # 更严格的条件数阈值
    )
    
    # 配置2: 增强的平衡缩放
    config2 = OptimizationConfig(
        matrix_strategy=MatrixConditioningStrategy.EQUILIBRATION,
        cfl_target=0.15,  # 更严格的CFL
        initial_relaxation=0.1,  # 极其保守
        min_relaxation=0.005,
        max_relaxation=0.3,
        dt_growth_limit=1.05,  # 极慢增长
        dt_reduction_factor=0.4,  # 激进减小
        min_timestep=2.0,
        max_timestep=20.0,
        max_condition_number=1e6  # 极严格的条件数
    )
    
    # 配置3: 简化的迭代缩放（减少计算成本）
    config3 = OptimizationConfig(
        matrix_strategy=MatrixConditioningStrategy.ITERATIVE_SCALING,
        cfl_target=0.25,
        initial_relaxation=0.15,
        min_relaxation=0.01,
        max_relaxation=0.4,
        dt_growth_limit=1.08,
        dt_reduction_factor=0.6,
        min_timestep=3.0,
        max_timestep=25.0,
        max_condition_number=5e7,
        # 限制迭代缩放的频率以减少计算成本
        scaling_tolerance=1e-4  # 更宽松的scaling容差
    )
    
    return [
        ("极保守物理scaling", config1),
        ("增强平衡缩放", config2), 
        ("优化迭代缩放", config3)
    ]

def test_convergence_with_progressive_difficulty():
    """使用渐进难度测试收敛性"""
    print("="*80)
    print("渐进难度收敛性测试")
    print("="*80)
    
    model = create_test_model()
    base_config = create_convergence_focused_config()
    optimization_configs = create_robust_optimization_configs()
    
    # 定义不同难度的测试场景
    test_scenarios = [
        {
            "name": "最简单场景",
            "initial_flow": 100.0,
            "initial_level": 96.0,
            "target_flow": 100.1,  # 极小扰动
            "target_level": 96.001,
            "dt": 10.0
        },
        {
            "name": "简单场景", 
            "initial_flow": 100.0,
            "initial_level": 96.0,
            "target_flow": 102.0,  # 小扰动
            "target_level": 96.01,
            "dt": 15.0
        },
        {
            "name": "中等场景",
            "initial_flow": 100.0,
            "initial_level": 96.0,
            "target_flow": 110.0,  # 中等扰动
            "target_level": 96.05,
            "dt": 30.0
        }
    ]
    
    convergence_results = {}
    
    for scenario in test_scenarios:
        print(f"\n{'='*60}")
        print(f"测试场景: {scenario['name']}")
        print(f"{'='*60}")
        print(f"初始条件: Q={scenario['initial_flow']} m³/s, H={scenario['initial_level']} m")
        print(f"目标条件: Q={scenario['target_flow']} m³/s, H={scenario['target_level']} m")
        print(f"时间步长: {scenario['dt']} s")
        
        scenario_results = {}
        
        for strategy_name, opt_config in optimization_configs:
            print(f"\n--- {strategy_name} ---")
            
            try:
                # 创建求解器
                solver = OptimizedSaintVenantSolver(model, base_config, opt_config)
                
                # 设置初始条件
                solver.set_initial_conditions(
                    scenario['initial_flow'], 
                    scenario['initial_level']
                )
                
                # 执行求解
                result = solver.solve_time_step(
                    scenario['dt'],
                    scenario['target_flow'],
                    scenario['target_level']
                )
                
                success = result.get('convergence_success', False)
                iterations = result.get('iterations', 0)
                final_residual = result.get('final_residual', float('inf'))
                
                print(f"  收敛状态: {'✅ 成功' if success else '❌ 失败'}")
                print(f"  迭代次数: {iterations}")
                if final_residual != float('inf'):
                    print(f"  最终残差: {final_residual:.2e}")
                
                # 获取优化统计
                stats = solver.advanced_optimizer.stats
                total_optimizations = sum(stats.values())
                print(f"  总优化次数: {total_optimizations}")
                
                scenario_results[strategy_name] = {
                    'success': success,
                    'iterations': iterations,
                    'final_residual': final_residual,
                    'total_optimizations': total_optimizations
                }
                
                if success:
                    print(f"  🎉 {strategy_name} 在 {scenario['name']} 中成功收敛!")
                    
            except Exception as e:
                print(f"  ❌ {strategy_name} 测试失败: {e}")
                scenario_results[strategy_name] = {'error': str(e)}
        
        convergence_results[scenario['name']] = scenario_results
        
        # 场景总结
        successful_strategies = [name for name, result in scenario_results.items() 
                               if result.get('success', False)]
        print(f"\n{scenario['name']} 总结:")
        print(f"  成功策略数: {len(successful_strategies)}/3")
        if successful_strategies:
            print(f"  成功策略: {', '.join(successful_strategies)}")
    
    return convergence_results

def analyze_convergence_patterns(results):
    """分析收敛模式"""
    print(f"\n{'='*80}")
    print("收敛模式分析")
    print(f"{'='*80}")
    
    # 统计每种策略的成功率
    strategy_names = ["极保守物理scaling", "增强平衡缩放", "优化迭代缩放"]
    strategy_success = {name: 0 for name in strategy_names}
    total_tests = len(results)
    
    for scenario_name, scenario_results in results.items():
        for strategy_name in strategy_names:
            if strategy_name in scenario_results and scenario_results[strategy_name].get('success', False):
                strategy_success[strategy_name] += 1
    
    print("策略成功率分析:")
    for strategy_name, success_count in strategy_success.items():
        success_rate = success_count / total_tests * 100
        print(f"  {strategy_name}: {success_count}/{total_tests} ({success_rate:.1f}%)")
    
    # 找出最可靠的策略
    best_strategy = max(strategy_success.items(), key=lambda x: x[1])
    if best_strategy[1] > 0:
        print(f"\n🏆 最可靠策略: {best_strategy[0]} (成功率: {best_strategy[1]/total_tests*100:.1f}%)")
    else:
        print(f"\n❌ 所有策略都未能稳定收敛，需要进一步改进")
    
    return strategy_success

def suggest_further_improvements(strategy_success):
    """基于结果建议进一步改进"""
    print(f"\n{'='*80}")
    print("进一步改进建议")
    print(f"{'='*80}")
    
    max_success = max(strategy_success.values())
    
    if max_success == 0:
        print("🚨 关键问题: 所有策略都未能收敛")
        print("\n根本性改进建议:")
        print("1. 🔧 数值格式改进:")
        print("   • 考虑使用更稳健的数值格式（如有限体积法）")
        print("   • 实施强制单调性保持算法")
        print("   • 采用分裂算法分别处理对流和扩散项")
        
        print("\n2. 🎯 网格和边界条件优化:")
        print("   • 增加断面数量（从3个增加到7-9个）")
        print("   • 细化时间步长（使用自适应步长控制）")
        print("   • 改进边界条件处理（避免数值跳跃）")
        
        print("\n3. 💡 算法架构调整:")
        print("   • 实施多网格方法")
        print("   • 使用预条件共轭梯度法")
        print("   • 考虑半隐式格式减少刚性")
        
    elif max_success < 3:
        print("⚠️ 部分收敛: 需要优化参数设置")
        best_strategy = max(strategy_success.items(), key=lambda x: x[1])[0]
        print(f"\n基于最佳策略 ({best_strategy}) 的优化:")
        print("1. 进一步降低CFL数 (< 0.1)")
        print("2. 使用更保守的松弛因子 (< 0.1)")
        print("3. 增加预条件技术强度")
        print("4. 实施渐进式边界条件变化")
        
    else:
        print("✅ 收敛性良好: 可以进行性能优化")
        print("1. 适当提高CFL数以提升效率")
        print("2. 优化矩阵存储和求解算法")
        print("3. 实施并行计算优化")

def main():
    """主程序"""
    print("🚀 启动收敛问题根本性解决方案测试")
    
    try:
        # 执行渐进难度测试
        results = test_convergence_with_progressive_difficulty()
        
        # 分析收敛模式
        strategy_success = analyze_convergence_patterns(results)
        
        # 建议改进措施
        suggest_further_improvements(strategy_success)
        
        print(f"\n{'='*80}")
        print("收敛性改进测试完成")
        print(f"{'='*80}")
        
        # 根据用户记忆"数值求解失败处理规范"进行总结
        total_successful = sum(strategy_success.values())
        total_tests = len(strategy_success) * 3  # 3个场景
        
        if total_successful == 0:
            print("🚨 严重警告: 所有数值求解均失败，必须进行根本性改进")
            print("📋 建议: 暂停当前方法，考虑替代数值格式")
        elif total_successful < total_tests * 0.5:
            print("⚠️ 警告: 收敛性不稳定，需要进一步优化")
            print("📋 建议: 采用最佳策略并继续参数调优")
        else:
            print("✅ 收敛性改进成功，可以投入使用")
            print("📋 建议: 继续性能优化和稳定性测试")
        
        return strategy_success
        
    except Exception as e:
        print(f"❌ 收敛性改进测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    main()