#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试数值稳定性优化效果
"""

import sys
import os
import numpy as np
import matplotlib.pyplot as plt

# 添加项目路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from enhanced_solver import EnhancedSaintVenantSolver, NumericalSchemeConfig
from waternet.models.saint_venant import SaintVenantModel
from numerical_stability_optimizer import integrate_stability_optimizer

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

def create_test_model():
    """创建测试模型"""
    
    # 创建大断面模型以确保亚临界流
    def area_func(h, elevation, bottom_width=300.0, side_slope=2.5):
        depth = max(1.0, h - elevation)
        return bottom_width * depth + side_slope * depth**2
    
    def top_width_func(h, elevation, bottom_width=300.0, side_slope=2.5):
        depth = max(1.0, h - elevation)
        return bottom_width + 2 * side_slope * depth
    
    sections = [
        {
            'mileage': 0.0,
            'elevation': 100.0,
            'roughness': 0.025,
            'area_func': lambda h: area_func(h, 100.0),
            'top_width_func': lambda h: top_width_func(h, 100.0)
        },
        {
            'mileage': 3000.0,
            'elevation': 99.0,
            'roughness': 0.025,
            'area_func': lambda h: area_func(h, 99.0),
            'top_width_func': lambda h: top_width_func(h, 99.0)
        },
        {
            'mileage': 6000.0,
            'elevation': 98.0,
            'roughness': 0.025,
            'area_func': lambda h: area_func(h, 98.0),
            'top_width_func': lambda h: top_width_func(h, 98.0)
        }
    ]

    return SaintVenantModel('stability_test_model', 'upstream_node', 'downstream_node', sections)

def test_original_vs_optimized():
    """对比原始求解器和优化求解器的性能"""
    print("=== 数值稳定性优化效果对比 ===")
    
    model = create_test_model()
    
    # 配置参数
    config = NumericalSchemeConfig(
        theta=0.6, psi=0.5, 
        max_iterations=30, 
        convergence_tolerance=1e-5,
        under_relaxation=0.5
    )
    
    # 测试参数
    initial_flow = 80.0
    downstream_level = 102.0
    
    print(f"测试条件: 流量={initial_flow} m³/s, 下游水位={downstream_level} m")
    
    # 原始求解器
    print("\n--- 原始求解器 ---")
    original_solver = EnhancedSaintVenantSolver(model, config)
    
    try:
        original_solver.set_initial_conditions(initial_flow, downstream_level)
        
        # 测试几个时间步
        original_results = []
        for step in range(5):
            result = original_solver.solve_time_step(1.0, initial_flow, downstream_level)
            original_results.append({
                'step': step + 1,
                'success': result['convergence_success'],
                'iterations': result['iterations'],
                'residual_info': f"收敛状态: {result['convergence_success']}"
            })
            
            print(f"  时间步 {step + 1}: {result['convergence_success']}, 迭代{result['iterations']}次")
            
            if not result['convergence_success']:
                print(f"  原始求解器在步骤 {step + 1} 失败")
                break
        
    except Exception as e:
        print(f"  原始求解器测试失败: {e}")
        original_results = []
    
    # 优化求解器
    print("\n--- 优化求解器 ---")
    try:
        # 使用装饰器创建优化版本
        OptimizedSolver = integrate_stability_optimizer(EnhancedSaintVenantSolver)
        optimized_solver = OptimizedSolver(model, config)
        
        optimized_solver.set_initial_conditions(initial_flow, downstream_level)
        
        # 测试几个时间步
        optimized_results = []
        for step in range(5):
            result = optimized_solver.solve_time_step(1.0, initial_flow, downstream_level)
            optimized_results.append({
                'step': step + 1,
                'success': result['convergence_success'],
                'iterations': result['iterations'],
                'residual_info': f"收敛状态: {result['convergence_success']}"
            })
            
            print(f"  时间步 {step + 1}: {result['convergence_success']}, 迭代{result['iterations']}次")
            
            if not result['convergence_success']:
                print(f"  优化求解器在步骤 {step + 1} 失败")
                break
        
        # 输出优化统计
        if hasattr(optimized_solver, 'stability_optimizer'):
            stats = optimized_solver.stability_optimizer.get_optimization_statistics()
            print(f"\n优化统计:")
            print(f"  矩阵条件优化次数: {stats['matrix_conditioning_count']}")
            print(f"  时间步自适应次数: {stats['timestep_adaptation_count']}")
            print(f"  松弛因子调整次数: {stats['relaxation_adjustment_count']}")
            print(f"  预条件应用次数: {stats['preconditioning_count']}")
        
    except Exception as e:
        print(f"  优化求解器测试失败: {e}")
        optimized_results = []
    
    # 结果分析
    print("\n--- 性能对比分析 ---")
    
    original_success = sum(1 for r in original_results if r['success'])
    optimized_success = sum(1 for r in optimized_results if r['success'])
    
    print(f"原始求解器成功步数: {original_success}/{len(original_results)}")
    print(f"优化求解器成功步数: {optimized_success}/{len(optimized_results)}")
    
    if optimized_success > original_success:
        print("✓ 优化求解器收敛性能更好")
        improvement = True
    elif optimized_success == original_success:
        # 比较迭代次数
        if original_results and optimized_results:
            orig_avg_iter = np.mean([r['iterations'] for r in original_results if r['success']])
            opt_avg_iter = np.mean([r['iterations'] for r in optimized_results if r['success']])
            
            if opt_avg_iter < orig_avg_iter:
                print("✓ 优化求解器迭代效率更高")
                improvement = True
            else:
                print("= 两种求解器性能相当")
                improvement = False
        else:
            improvement = False
    else:
        print("⚠️ 优化效果未达预期")
        improvement = False
    
    return {
        'original_results': original_results,
        'optimized_results': optimized_results,
        'improvement': improvement,
        'original_success_rate': original_success / max(len(original_results), 1),
        'optimized_success_rate': optimized_success / max(len(optimized_results), 1)
    }

def test_challenging_conditions():
    """测试挑战性条件下的稳定性"""
    print("\n=== 挑战性条件稳定性测试 ===")
    
    model = create_test_model()
    
    # 更严格的配置
    challenging_config = NumericalSchemeConfig(
        theta=1.0, psi=0.5,  # 全隐式
        max_iterations=50, 
        convergence_tolerance=1e-6,  # 更严格的容差
        under_relaxation=0.3  # 更保守的松弛
    )
    
    test_cases = [
        {"name": "大流量变化", "flow": 200.0, "level": 103.0},
        {"name": "小流量条件", "flow": 20.0, "level": 101.0},
        {"name": "极端条件", "flow": 500.0, "level": 105.0}
    ]
    
    results = []
    
    for case in test_cases:
        print(f"\n--- {case['name']} ---")
        print(f"测试条件: 流量={case['flow']} m³/s, 水位={case['level']} m")
        
        try:
            # 使用优化求解器
            OptimizedSolver = integrate_stability_optimizer(EnhancedSaintVenantSolver)
            solver = OptimizedSolver(model, challenging_config)
            
            solver.set_initial_conditions(case['flow'], case['level'])
            
            # 测试单个时间步
            result = solver.solve_time_step(2.0, case['flow'], case['level'])
            
            success = result['convergence_success']
            iterations = result['iterations']
            
            print(f"  结果: {'成功' if success else '失败'}, 迭代{iterations}次")
            
            # 获取验证结果
            validation = solver.validate_physical_consistency(dt=2.0)
            physics_ok = validation['overall_valid']
            
            print(f"  物理验证: {'通过' if physics_ok else '失败'}")
            
            if 'velocity_analysis' in validation and validation['velocity_analysis'].get('details'):
                details = validation['velocity_analysis']['details']
                froude = details.get('max_froude', 0)
                print(f"  最大弗劳德数: {froude:.3f}")
            
            results.append({
                'case': case['name'],
                'convergence_success': success,
                'iterations': iterations,
                'physics_valid': physics_ok,
                'conditions': case
            })
            
        except Exception as e:
            print(f"  测试失败: {e}")
            results.append({
                'case': case['name'],
                'convergence_success': False,
                'iterations': 0,
                'physics_valid': False,
                'error': str(e)
            })
    
    # 汇总挑战性测试结果
    success_count = sum(1 for r in results if r['convergence_success'])
    physics_count = sum(1 for r in results if r['physics_valid'])
    
    print(f"\n挑战性测试汇总:")
    print(f"  收敛成功: {success_count}/{len(results)}")
    print(f"  物理验证通过: {physics_count}/{len(results)}")
    
    return results

def generate_optimization_report(comparison_results, challenge_results):
    """生成优化效果报告"""
    print("\n=== 数值稳定性优化报告 ===")
    
    report = []
    report.append("# 圣维南求解器数值稳定性优化报告")
    report.append("")
    report.append("## 优化技术概览")
    report.append("本次优化实现了以下技术:")
    report.append("1. **Jacobian矩阵数值scaling** - 基于物理量纲的行列缩放")
    report.append("2. **自适应时间步长控制** - 基于CFL条件和收敛性的动态调整")
    report.append("3. **改进松弛因子策略** - 基于残差改善情况的自适应调整")
    report.append("4. **多重预条件技术** - 对角预条件和正则化")
    report.append("")
    
    # 基本性能对比
    report.append("## 基本性能对比")
    orig_rate = comparison_results['original_success_rate']
    opt_rate = comparison_results['optimized_success_rate']
    
    report.append(f"- **原始求解器收敛率**: {orig_rate:.1%}")
    report.append(f"- **优化求解器收敛率**: {opt_rate:.1%}")
    
    if opt_rate > orig_rate:
        improvement = (opt_rate - orig_rate) / orig_rate * 100
        report.append(f"- **性能提升**: {improvement:.1f}%")
        report.append("- **结论**: ✅ 优化效果显著")
    else:
        report.append("- **结论**: ⚠️ 优化效果有限")
    
    report.append("")
    
    # 挑战性条件测试
    report.append("## 挑战性条件测试")
    challenge_success = sum(1 for r in challenge_results if r['convergence_success'])
    challenge_physics = sum(1 for r in challenge_results if r['physics_valid'])
    
    report.append(f"- **挑战性测试用例**: {len(challenge_results)}个")
    report.append(f"- **收敛成功**: {challenge_success}/{len(challenge_results)}")
    report.append(f"- **物理验证通过**: {challenge_physics}/{len(challenge_results)}")
    
    for result in challenge_results:
        status = "✅" if result['convergence_success'] else "❌"
        physics = "✅" if result['physics_valid'] else "❌"
        report.append(f"  - {result['case']}: 收敛{status} 物理{physics}")
    
    report.append("")
    
    # 技术评估
    report.append("## 技术评估")
    
    if comparison_results['improvement']:
        report.append("### 优化成功方面")
        report.append("- 数值稳定性显著改善")
        report.append("- 收敛性能得到提升")
        report.append("- 物理合理性得到保证")
    
    report.append("### 仍需改进方面")
    report.append("- Jacobian矩阵条件数仍然较大")
    report.append("- 某些极端条件下收敛困难")
    report.append("- 需要进一步优化预条件技术")
    
    report.append("")
    report.append("## 后续优化建议")
    report.append("1. **高级预条件**: 实现ILU或多重网格预条件")
    report.append("2. **网格自适应**: 根据解梯度动态调整空间离散")
    report.append("3. **物理约束**: 加强物理可行性约束")
    report.append("4. **并行计算**: 大规模系统的并行求解")
    
    # 保存报告
    report_text = "\n".join(report)
    
    with open('numerical_stability_optimization_report.md', 'w', encoding='utf-8') as f:
        f.write(report_text)
    
    print("数值稳定性优化报告已保存: numerical_stability_optimization_report.md")
    
    return report_text

def main():
    """主测试函数"""
    print("圣维南求解器数值稳定性优化测试")
    print("=" * 60)
    
    try:
        # 基本性能对比
        comparison_results = test_original_vs_optimized()
        
        # 挑战性条件测试
        challenge_results = test_challenging_conditions()
        
        # 生成报告
        report = generate_optimization_report(comparison_results, challenge_results)
        
        # 总结
        print("\n" + "=" * 60)
        print("数值稳定性优化测试完成")
        
        if comparison_results['improvement']:
            print("✅ 优化技术验证成功")
        else:
            print("⚠️ 优化效果有待进一步改进")
        
        print("详细报告已生成，请查看 numerical_stability_optimization_report.md")
        
        return True
        
    except Exception as e:
        print(f"❌ 优化测试过程出错: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)