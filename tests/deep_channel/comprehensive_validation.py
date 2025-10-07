#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全面验证Preissmann格式的正确性
包含物理合理性检查、流速特性分析和可视化验证
"""

import sys
import os
import numpy as np
import matplotlib.pyplot as plt
import logging
from typing import Dict, Any, List

# 添加项目路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from enhanced_solver import EnhancedSaintVenantSolver, NumericalSchemeConfig
from waternet.models.saint_venant import SaintVenantModel

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

def create_validation_model():
    """创建用于验证的模型"""
    
    # 创建更合理的大断面模型 - 确保亚临界流
    def area_func(h, elevation, bottom_width=200.0, side_slope=2.0):
        depth = max(1.0, h - elevation)
        return bottom_width * depth + side_slope * depth**2
    
    def top_width_func(h, elevation, bottom_width=200.0, side_slope=2.0):
        depth = max(1.0, h - elevation)
        return bottom_width + 2 * side_slope * depth
    
    sections = [
        {
            'mileage': 0.0,
            'elevation': 100.0,
            'roughness': 0.03,
            'area_func': lambda h: area_func(h, 100.0),
            'top_width_func': lambda h: top_width_func(h, 100.0)
        },
        {
            'mileage': 2000.0,
            'elevation': 99.0,
            'roughness': 0.03,
            'area_func': lambda h: area_func(h, 99.0),
            'top_width_func': lambda h: top_width_func(h, 99.0)
        },
        {
            'mileage': 4000.0,
            'elevation': 98.0,
            'roughness': 0.03,
            'area_func': lambda h: area_func(h, 98.0),
            'top_width_func': lambda h: top_width_func(h, 98.0)
        }
    ]

    return SaintVenantModel('validation_model', 'upstream_node', 'downstream_node', sections)

def test_physical_consistency():
    """测试物理一致性"""
    print("=== 物理一致性验证 ===")
    
    model = create_validation_model()
    
    # 测试不同参数配置
    configs = [
        ("标准Preissmann", NumericalSchemeConfig(theta=0.6, psi=0.5, max_iterations=20, convergence_tolerance=1e-4)),
        ("全隐式", NumericalSchemeConfig(theta=1.0, psi=0.5, max_iterations=25, convergence_tolerance=1e-4)),
        ("Crank-Nicolson", NumericalSchemeConfig(theta=0.5, psi=0.5, max_iterations=30, convergence_tolerance=1e-5))
    ]
    
    results = {}
    
    for config_name, config in configs:
        print(f"\n--- {config_name} 配置验证 ---")
        
        solver = EnhancedSaintVenantSolver(model, config)
        
        # 使用合理的流量参数 - 确保亚临界流
        initial_flow = 100.0  # m³/s - 较小流量
        downstream_level = 102.0  # m - 较高水位
        
        try:
            # 设置初始条件
            solver.set_initial_conditions(initial_flow, downstream_level)
            
            # 进行物理合理性验证
            validation_result = solver.validate_physical_consistency(dt=1.0)
            
            results[config_name] = validation_result
            
            # 打印验证结果
            print(f"  整体验证: {'✓' if validation_result['overall_valid'] else '✗'}")
            print(f"  物理一致性: {'✓' if validation_result['physics_check'].get('mass_conservation', False) else '✗'}")
            print(f"  流速特性: {'✓' if validation_result['velocity_analysis'].get('assumptions_valid', False) else '✗'}")
            print(f"  稳态平衡: {'✓' if validation_result['steady_state_balance'].get('momentum_balanced', False) else '✗'}")
            print(f"  数值稳定性: {'✓' if validation_result['numerical_stability'].get('cfl_stable', False) else '✗'}")
            
            # 显示详细信息
            if validation_result['velocity_analysis']['details']:
                details = validation_result['velocity_analysis']['details']
                print(f"  平均流速: {details['avg_velocity']:.3f} m/s")
                print(f"  最大弗劳德数: {details['max_froude']:.3f}")
            
            if validation_result['steady_state_balance']['details']:
                balance_details = validation_result['steady_state_balance']['details']
                print(f"  残差范数: {balance_details.get('residual_norm', 0):.2e}")
            
            # 显示警告和错误
            if validation_result['warnings']:
                print(f"  警告: {'; '.join(validation_result['warnings'])}")
            if validation_result['errors']:
                print(f"  错误: {'; '.join(validation_result['errors'])}")
                
        except Exception as e:
            print(f"  配置 {config_name} 测试失败: {e}")
            results[config_name] = {'overall_valid': False, 'error': str(e)}
    
    return results

def test_convergence_behavior():
    """测试收敛行为"""
    print("\n=== 收敛行为分析 ===")
    
    model = create_validation_model()
    config = NumericalSchemeConfig(
        theta=0.6, psi=0.5, 
        max_iterations=50, 
        convergence_tolerance=1e-6,
        under_relaxation=0.3
    )
    
    solver = EnhancedSaintVenantSolver(model, config)
    
    # 测试参数 - 确保亚临界流
    initial_flow = 80.0
    downstream_level = 102.5
    
    print(f"测试参数: 流量={initial_flow} m³/s, 下游水位={downstream_level} m")
    
    try:
        # 设置初始条件
        solver.set_initial_conditions(initial_flow, downstream_level)
        
        print(f"初始化成功:")
        print(f"  流量变量: {solver.current_state[:solver.n_flow_vars]}")
        print(f"  水位变量: {solver.current_state[solver.n_flow_vars:]}")
        
        # 测试时间步求解
        convergence_history = []
        time_steps = 5
        
        for step in range(time_steps):
            print(f"\n时间步 {step + 1}:")
            
            result = solver.solve_time_step(1.0, initial_flow, downstream_level)
            
            print(f"  收敛状态: {result['convergence_success']}")
            print(f"  迭代次数: {result['iterations']}")
            
            convergence_history.append({
                'step': step + 1,
                'success': result['convergence_success'],
                'iterations': result['iterations'],
                'flows': list(result['flow_variables'].values()),
                'levels': list(result['water_levels'].values())
            })
            
            if not result['convergence_success']:
                print(f"  ⚠️ 时间步 {step + 1} 未收敛，停止测试")
                break
        
        return convergence_history
        
    except Exception as e:
        print(f"收敛测试失败: {e}")
        return []

def visualize_results(validation_results: Dict, convergence_history: List):
    """可视化验证结果"""
    print("\n=== 生成验证图表 ===")
    
    # 创建图表
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('Preissmann格式验证结果', fontsize=16, fontweight='bold')
    
    # 1. 物理一致性对比
    config_names = list(validation_results.keys())
    valid_counts = []
    
    for config_name in config_names:
        result = validation_results[config_name]
        if 'overall_valid' in result:
            # 计算通过的检查项数量
            checks = [
                result.get('physics_check', {}).get('mass_conservation', False),
                result.get('velocity_analysis', {}).get('assumptions_valid', False),
                result.get('steady_state_balance', {}).get('momentum_balanced', False),
                result.get('numerical_stability', {}).get('cfl_stable', False)
            ]
            valid_counts.append(sum(checks))
        else:
            valid_counts.append(0)
    
    ax1.bar(config_names, valid_counts, color=['green' if x >= 3 else 'orange' if x >= 2 else 'red' for x in valid_counts])
    ax1.set_title('物理一致性检查通过数量')
    ax1.set_ylabel('通过检查数')
    ax1.set_ylim(0, 4)
    for i, v in enumerate(valid_counts):
        ax1.text(i, v + 0.1, str(v), ha='center', va='bottom')
    
    # 2. 收敛历史
    if convergence_history:
        steps = [h['step'] for h in convergence_history]
        iterations = [h['iterations'] for h in convergence_history]
        success = [h['success'] for h in convergence_history]
        
        colors = ['green' if s else 'red' for s in success]
        ax2.bar(steps, iterations, color=colors, alpha=0.7)
        ax2.set_title('收敛迭代次数历史')
        ax2.set_xlabel('时间步')
        ax2.set_ylabel('迭代次数')
        ax2.grid(True, alpha=0.3)
    
    # 3. 流速分布
    velocity_data = []
    froude_data = []
    
    for config_name, result in validation_results.items():
        if 'velocity_analysis' in result and result['velocity_analysis'].get('details'):
            details = result['velocity_analysis']['details']
            velocity_data.append(details.get('avg_velocity', 0))
            froude_data.append(details.get('max_froude', 0))
        else:
            velocity_data.append(0)
            froude_data.append(0)
    
    x_pos = np.arange(len(config_names), dtype=float)
    width = np.float64(0.35)
    
    bars1 = ax3.bar(x_pos - width/2, velocity_data, width, label='平均流速 (m/s)', alpha=0.8)
    bars2 = ax3.bar(x_pos + width/2, froude_data, width, label='最大弗劳德数', alpha=0.8)
    ax3.set_title('流速特性对比')
    ax3.set_xticks(x_pos)
    ax3.set_xticklabels(config_names, rotation=45)
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # 4. 残差分析
    residual_data = []
    
    for config_name, result in validation_results.items():
        if 'steady_state_balance' in result and result['steady_state_balance'].get('details'):
            details = result['steady_state_balance']['details']
            residual_norm = details.get('residual_norm', 1e6)
            residual_data.append(residual_norm)
        else:
            residual_data.append(1e6)
    
    ax4.semilogy(config_names, residual_data, 'o-', linewidth=2, markersize=8)
    ax4.set_title('稳态平衡残差')
    ax4.set_ylabel('残差范数 (log scale)')
    ax4.grid(True, alpha=0.3)
    ax4.axhline(y=1e-3, color='red', linestyle='--', alpha=0.7, label='期望阈值')
    ax4.legend()
    
    plt.tight_layout()
    
    # 保存图表
    output_file = 'preissmann_validation_results.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"验证图表已保存: {output_file}")
    
    return output_file

def generate_validation_report(validation_results: Dict, convergence_history: List) -> str:
    """生成验证报告"""
    report = []
    report.append("# Preissmann四点隐式差分格式验证报告")
    report.append("")
    report.append("## 验证概览")
    
    # 汇总统计
    total_configs = len(validation_results)
    valid_configs = sum(1 for result in validation_results.values() 
                       if result.get('overall_valid', False))
    
    report.append(f"- 测试配置数量: {total_configs}")
    report.append(f"- 通过验证配置: {valid_configs}")
    report.append(f"- 验证通过率: {valid_configs/total_configs*100:.1f}%")
    report.append("")
    
    # 详细验证结果
    report.append("## 详细验证结果")
    
    for config_name, result in validation_results.items():
        report.append(f"### {config_name}")
        
        if 'error' in result:
            report.append(f"❌ 测试失败: {result['error']}")
        else:
            overall = "✅" if result.get('overall_valid', False) else "❌"
            report.append(f"{overall} 整体验证: {result.get('overall_valid', False)}")
            
            # 各项检查结果
            if 'physics_check' in result:
                physics = result['physics_check']
                mass_ok = "✅" if physics.get('mass_conservation', False) else "❌"
                flow_ok = "✅" if physics.get('flow_direction', False) else "❌"
                report.append(f"  {mass_ok} 质量守恒")
                report.append(f"  {flow_ok} 流动方向")
            
            if 'velocity_analysis' in result:
                velocity = result['velocity_analysis']
                vel_ok = "✅" if velocity.get('assumptions_valid', False) else "❌"
                report.append(f"  {vel_ok} 流速假设")
                if 'details' in velocity:
                    details = velocity['details']
                    report.append(f"    - 平均流速: {details.get('avg_velocity', 0):.3f} m/s")
                    report.append(f"    - 最大弗劳德数: {details.get('max_froude', 0):.3f}")
            
            if 'steady_state_balance' in result:
                balance = result['steady_state_balance']
                balance_ok = "✅" if balance.get('momentum_balanced', False) else "❌"
                report.append(f"  {balance_ok} 稳态平衡")
                if 'details' in balance:
                    details = balance['details']
                    report.append(f"    - 残差范数: {details.get('residual_norm', 0):.2e}")
            
            # 警告和错误
            if result.get('warnings'):
                report.append(f"  ⚠️ 警告: {'; '.join(result['warnings'])}")
            if result.get('errors'):
                report.append(f"  ❌ 错误: {'; '.join(result['errors'])}")
        
        report.append("")
    
    # 收敛行为分析
    if convergence_history:
        report.append("## 收敛行为分析")
        
        successful_steps = sum(1 for h in convergence_history if h['success'])
        total_steps = len(convergence_history)
        
        report.append(f"- 成功收敛步数: {successful_steps}/{total_steps}")
        report.append(f"- 收敛成功率: {successful_steps/total_steps*100:.1f}%")
        
        if successful_steps > 0:
            iterations_list = [h['iterations'] for h in convergence_history if h['success']]
            avg_iterations = sum(iterations_list) / len(iterations_list)
            report.append(f"- 平均迭代次数: {avg_iterations:.1f}")
        
        report.append("")
    
    # 结论
    report.append("## 验证结论")
    
    if valid_configs == total_configs:
        report.append("🎉 **所有配置通过验证**")
        report.append("- Preissmann四点隐式差分格式实现正确")
        report.append("- 物理一致性得到保证")
        report.append("- 数值稳定性良好")
    elif valid_configs > 0:
        report.append("⚠️ **部分配置通过验证**")
        report.append("- 基本Preissmann格式实现正确")
        report.append("- 需要进一步优化参数配置")
    else:
        report.append("❌ **验证失败**")
        report.append("- Preissmann格式实现存在问题")
        report.append("- 需要修复数值方法")
    
    return "\n".join(report)

def main():
    """主验证函数"""
    print("Preissmann四点隐式差分格式全面验证")
    print("="*50)
    
    # 按照"数值求解失败处理规范"，如果验证失败要明确报告
    try:
        # 1. 物理一致性验证
        validation_results = test_physical_consistency()
        
        # 2. 收敛行为测试
        convergence_history = test_convergence_behavior()
        
        # 3. 可视化验证结果
        chart_file = visualize_results(validation_results, convergence_history)
        
        # 4. 生成验证报告
        report = generate_validation_report(validation_results, convergence_history)
        
        # 保存报告
        report_file = 'preissmann_validation_report.md'
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\n验证报告已保存: {report_file}")
        
        # 按照"数值模拟结果真实性验证"检查整体结果
        valid_configs = sum(1 for result in validation_results.values() 
                           if result.get('overall_valid', False))
        
        if valid_configs == 0:
            print("\n❌ 严重警告: 所有配置验证失败！")
            print("根据数值求解失败处理规范，必须修复实现错误")
            return False
        elif valid_configs < len(validation_results):
            print(f"\n⚠️ 警告: 仅{valid_configs}/{len(validation_results)}配置通过验证")
            print("建议进一步优化未通过的配置")
        else:
            print("\n✅ 验证成功: 所有配置通过物理合理性检查")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 验证过程出错: {e}")
        print("根据数值求解失败处理规范，停止验证流程")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 Preissmann格式验证完成")
    else:
        print("\n💥 Preissmann格式验证失败，需要修复")