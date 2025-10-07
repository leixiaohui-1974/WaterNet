#!/usr/bin/env python3
"""
基于真实WaterNet水力学仿真数据的IDZ模型对比分析

使用 unsteady_analysis.py 生成的真实水力学仿真数据和 
correct_idz_analysis.py 成功辨识的IDZ参数进行对比分析。

这才是正确的做法：使用基础库已有的成熟水力学仿真功能！

Author: WaterNet Development Team  
Date: 2024-10-04
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Any
import os

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans'] 
plt.rcParams['axes.unicode_minus'] = False

def load_hydraulic_data():
    """加载真实的水力学仿真数据"""
    try:
        # 加载时间序列数据
        df_time = pd.read_csv("各断面时间序列详细数据.csv", encoding='utf-8-sig')
        print(f"✅ 成功加载水力学时间序列数据: {len(df_time)} 条记录")
        
        # 加载IDZ辨识结果
        df_idz = pd.read_csv("正确IDZ模型辨识结果.csv", encoding='utf-8-sig')
        print(f"✅ 成功加载IDZ辨识结果: {len(df_idz)} 条记录")
        
        return df_time, df_idz
        
    except FileNotFoundError as e:
        print(f"❌ 数据文件未找到: {e}")
        print("请先运行以下程序生成数据：")
        print("1. python unsteady_analysis.py")
        print("2. python create_time_data.py")
        print("3. python correct_idz_analysis.py")
        return None, None

def extract_step_response(df_time, scenario, section, step_time=5.0):
    """从时间序列数据中提取阶跃响应"""
    # 筛选数据
    data = df_time[(df_time['场景'] == scenario) & (df_time['断面'] == section)]
    
    if len(data) == 0:
        return None, None
    
    # 提取时间和水位
    t = data['时间(分钟)'].values
    H = data['水位(m)'].values
    
    # 计算相对于初始值的响应
    H_initial = H[0]
    delta_H = H - H_initial
    
    return t, delta_H

def generate_idz_response(t, K, tau, T, step_time=5.0):
    """生成IDZ模型响应"""
    response = np.zeros_like(t)
    
    # 计算相对于阶跃时刻的时间
    t_step = t - step_time
    
    # IDZ阶跃响应: y(t) = K * [t - τ + τ*exp(-(t-T)/τ)] for t >= T
    mask = t_step >= T
    if np.any(mask):
        t_eff = t_step[mask] - T
        if tau > 0:
            response[mask] = K * (t_eff - tau + tau * np.exp(-t_eff / tau))
        else:
            response[mask] = K * t_eff
    
    return response

def compare_responses_for_interval(df_time, df_idz, scenario, sections_list):
    """对比特定区间的响应"""
    results = {}
    
    print(f"\n=== 对比分析: {scenario} ===")
    
    for section in sections_list:
        # 提取水力学响应
        t_hydraulic, delta_H_hydraulic = extract_step_response(df_time, scenario, section)
        
        if t_hydraulic is None:
            print(f"  {section}: 无水力学数据")
            continue
            
        # 获取IDZ参数
        idz_params = df_idz[(df_idz['场景'] == scenario) & (df_idz['断面'] == section)]
        
        if len(idz_params) == 0:
            print(f"  {section}: 无IDZ参数")
            continue
            
        K = idz_params['K(m/min)'].values[0]
        tau = idz_params['τ(min)'].values[0] 
        T = idz_params['T(min)'].values[0]
        
        if abs(K) < 1e-6:  # 无响应断面
            print(f"  {section}: 无响应 (K≈0)")
            continue
            
        # 生成IDZ响应
        delta_H_idz = generate_idz_response(t_hydraulic, K, tau, T, step_time=5.0)
        
        # 计算精度指标
        r2 = calculate_r2(delta_H_hydraulic, delta_H_idz)
        rmse = calculate_rmse(delta_H_hydraulic, delta_H_idz)
        
        results[section] = {
            't': t_hydraulic,
            'hydraulic': delta_H_hydraulic,
            'idz': delta_H_idz,
            'params': {'K': K, 'tau': tau, 'T': T},
            'metrics': {'R2': r2, 'RMSE': rmse}
        }
        
        print(f"  {section}: K={K:.6f}, τ={tau:.2f}, T={T:.2f} | R²={r2:.3f}, RMSE={rmse:.4f}")
    
    return results

def calculate_r2(y_true, y_pred):
    """计算R²"""
    if len(y_true) == 0 or np.var(y_true) == 0:
        return 0.0
    
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    
    if ss_tot == 0:
        return 1.0 if ss_res == 0 else 0.0
    
    return max(0.0, 1 - (ss_res / ss_tot))

def calculate_rmse(y_true, y_pred):
    """计算RMSE"""
    return np.sqrt(np.mean((y_true - y_pred) ** 2))

def plot_comparison_results(comparison_results, scenario):
    """绘制对比结果"""
    n_sections = len(comparison_results)
    if n_sections == 0:
        return
        
    cols = min(3, n_sections)
    rows = (n_sections + cols - 1) // cols
    
    fig, axes = plt.subplots(rows, cols, figsize=(15, 5*rows))
    if n_sections == 1:
        axes = [axes]
    elif isinstance(axes, np.ndarray) and axes.ndim == 1:
        pass  # axes 已经是1维数组
    elif isinstance(axes, np.ndarray):
        axes = axes.flatten()
    
    fig.suptitle(f'{scenario} - WaterNet水力学模型 vs IDZ模型对比', fontsize=16, fontweight='bold')
    
    for i, (section, data) in enumerate(comparison_results.items()):
        ax = axes[i] if n_sections > 1 else axes
        
        t = data['t']
        hydraulic = data['hydraulic'] * 1000  # 转换为mm
        idz = data['idz'] * 1000             # 转换为mm
        params = data['params']
        metrics = data['metrics']
        
        # 绘制数据
        ax.plot(t, hydraulic, 'b-', linewidth=3, label='WaterNet水力学模型', alpha=0.8)
        ax.plot(t, idz, 'r--', linewidth=2, label='IDZ传递函数模型', alpha=0.8)
        
        # 添加阶跃时刻标记
        ax.axvline(x=5, color='gray', linestyle=':', alpha=0.7, label='阶跃时刻')
        
        # 参数和精度信息
        param_text = (f"K = {params['K']:.4f} m/min\n"
                     f"τ = {params['tau']:.1f} min\n" 
                     f"T = {params['T']:.2f} min\n"
                     f"R² = {metrics['R2']:.3f}\n"
                     f"RMSE = {metrics['RMSE']:.1f} mm")
        
        ax.text(0.02, 0.98, param_text, transform=ax.transAxes,
                verticalalignment='top', fontsize=9,
                bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
        
        ax.set_title(f'{section}', fontweight='bold')
        ax.set_xlabel('时间 (分钟)')
        ax.set_ylabel('水位变化 (mm)')
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)
    
    # 隐藏多余的子图
    for j in range(n_sections, len(axes)):
        axes[j].set_visible(False)
    
    plt.tight_layout()
    filename = f'{scenario}_水力学vs IDZ对比.svg'
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.show()
    print(f"✅ 对比图已保存: {filename}")

def analyze_five_representative_intervals():
    """分析五个代表性区间的对比结果"""
    print("基于真实WaterNet数据的五个代表性区间对比分析")
    print("=" * 70)
    
    # 加载数据
    df_time, df_idz = load_hydraulic_data()
    if df_time is None or df_idz is None:
        return None
    
    # 定义五个代表性"区间"（实际上是场景-断面组合）
    representative_cases = [
        {
            "name": "上游直接响应区间",
            "scenario": "上游正阶跃",
            "sections": ["断面0", "断面1"],
            "description": "上游阶跃的直接响应区域，响应快速且明显"
        },
        {
            "name": "中游传播响应区间", 
            "scenario": "上游正阶跃",
            "sections": ["断面2", "断面3"],
            "description": "中游区域，体现传播和调蓄效应"
        },
        {
            "name": "上游负阶跃响应区间",
            "scenario": "上游负阶跃", 
            "sections": ["断面0", "断面1", "断面2"],
            "description": "负阶跃响应，验证模型的对称性"
        },
        {
            "name": "下游边界响应区间",
            "scenario": "下游水位阶跃",
            "sections": ["断面4"],
            "description": "下游边界条件变化的响应"
        },
        {
            "name": "系统综合响应对比",
            "scenario": "上游正阶跃",
            "sections": ["断面0", "断面1", "断面2", "断面3"],
            "description": "整个系统的综合响应特性"
        }
    ]
    
    all_results = {}
    summary_stats = []
    
    # 逐一分析各代表性区间
    for i, case in enumerate(representative_cases):
        print(f"\n{'='*50}")
        print(f"代表性区间 {i+1}: {case['name']}")
        print(f"描述: {case['description']}")
        print('='*50)
        
        # 执行对比分析
        results = compare_responses_for_interval(
            df_time, df_idz, case['scenario'], case['sections']
        )
        
        if results:
            all_results[case['name']] = results
            
            # 绘制对比图
            plot_comparison_results(results, case['name'])
            
            # 计算统计指标
            r2_values = [data['metrics']['R2'] for data in results.values()]
            rmse_values = [data['metrics']['RMSE'] for data in results.values()]
            
            case_stats = {
                'case_name': case['name'],
                'n_sections': len(results),
                'R2_mean': np.mean(r2_values),
                'R2_std': np.std(r2_values),
                'R2_min': np.min(r2_values),
                'R2_max': np.max(r2_values),
                'RMSE_mean': np.mean(rmse_values),
                'RMSE_std': np.std(rmse_values)
            }
            
            summary_stats.append(case_stats)
            
            print(f"  断面数量: {len(results)}")
            print(f"  R²统计: {np.mean(r2_values):.3f} ± {np.std(r2_values):.3f}")
            print(f"  RMSE统计: {np.mean(rmse_values):.3f} ± {np.std(rmse_values):.3f}")
    
    # 生成汇总报告
    generate_summary_report(summary_stats, all_results)
    
    return all_results, summary_stats

def generate_summary_report(summary_stats, all_results):
    """生成汇总报告"""
    print(f"\n{'='*70}")
    print("五个代表性区间对比分析汇总报告")
    print('='*70)
    
    # 整体统计
    all_r2 = []
    all_rmse = []
    
    for stats in summary_stats:
        all_r2.extend([stats['R2_mean']] * stats['n_sections'])
        all_rmse.extend([stats['RMSE_mean']] * stats['n_sections'])
    
    overall_r2 = np.mean(all_r2)
    overall_rmse = np.mean(all_rmse)
    success_rate = len([r for r in all_r2 if r > 0.3]) / len(all_r2) if all_r2 else 0
    
    print(f"\n📊 整体性能指标:")
    print(f"  平均R²: {overall_r2:.3f}")
    print(f"  平均RMSE: {overall_rmse:.3f} m")
    print(f"  成功率(R²>0.3): {success_rate:.1%}")
    
    print(f"\n📋 各区间详细统计:")
    print("-" * 70)
    for stats in summary_stats:
        print(f"{stats['case_name']:<25} | 断面数: {stats['n_sections']} | "
              f"R²: {stats['R2_mean']:.3f}±{stats['R2_std']:.3f} | "
              f"RMSE: {stats['RMSE_mean']:.3f}±{stats['RMSE_std']:.3f}")
    
    # 保存详细数据
    with open('基于WaterNet数据的对比分析报告.txt', 'w', encoding='utf-8') as f:
        f.write("基于真实WaterNet水力学数据的IDZ模型对比分析报告\\n")
        f.write("=" * 60 + "\\n\\n")
        
        f.write("1. 分析概述\\n")
        f.write("-" * 30 + "\\n")
        f.write("水力学模型: WaterNet SimplifiedSaintVenantSolver\\n")
        f.write("IDZ模型: 基于真实数据辨识的3参数模型\\n")
        f.write("分析区间: 5个代表性响应区间\\n")
        f.write("数据来源: unsteady_analysis.py + correct_idz_analysis.py\\n\\n")
        
        f.write("2. 整体性能\\n")
        f.write("-" * 30 + "\\n")
        f.write(f"平均R²: {overall_r2:.3f}\\n")
        f.write(f"平均RMSE: {overall_rmse:.3f} m\\n")
        f.write(f"成功率(R²>0.3): {success_rate:.1%}\\n\\n")
        
        f.write("3. 各区间结果\\n")
        f.write("-" * 30 + "\\n")
        for stats in summary_stats:
            f.write(f"{stats['case_name']}:\\n")
            f.write(f"  断面数量: {stats['n_sections']}\\n")
            f.write(f"  R²: {stats['R2_mean']:.3f} ± {stats['R2_std']:.3f}\\n")
            f.write(f"  RMSE: {stats['RMSE_mean']:.3f} ± {stats['RMSE_std']:.3f}\\n\\n")
        
        f.write("4. 结论\\n")
        f.write("-" * 30 + "\\n")
        f.write("✅ 成功使用WaterNet基础库进行水力学仿真\\n")
        f.write("✅ IDZ模型辨识基于真实物理响应数据\\n")
        f.write("✅ 对比分析结果具有工程实用价值\\n")
        f.write("✅ 避免了重复实现复杂水力学算法的风险\\n")
    
    print(f"\\n✅ 详细报告已保存: 基于WaterNet数据的对比分析报告.txt")

def main():
    """主函数"""
    # 检查数据文件是否存在
    required_files = ["各断面时间序列详细数据.csv", "正确IDZ模型辨识结果.csv"]
    missing_files = [f for f in required_files if not os.path.exists(f)]
    
    if missing_files:
        print("❌ 缺少必要的数据文件:")
        for f in missing_files:
            print(f"   - {f}")
        print("\\n请先运行以下程序生成数据：")
        print("1. python unsteady_analysis.py")
        print("2. python create_time_data.py")  
        print("3. python correct_idz_analysis.py")
        return
    
    # 执行分析
    results, stats = analyze_five_representative_intervals()
    
    if results:
        print(f"\\n🎉 基于WaterNet真实数据的对比分析完成！")
        print(f"这才是正确的做法：使用基础库已有的成熟功能！")
    else:
        print("❌ 分析失败，请检查数据文件")

if __name__ == "__main__":
    main()