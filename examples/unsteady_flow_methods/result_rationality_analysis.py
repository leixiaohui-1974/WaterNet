#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第9部分非恒定流模拟结果合理性深入分析
严格按照用户记忆规范进行物理合理性验证
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import math
try:
    import pandas as pd
except ImportError:
    pd = None

def analyze_result_rationality():
    """深入分析第9部分非恒定流模拟结果的合理性"""
    
    print("=" * 80)
    print("第9部分非恒定流模拟结果合理性深入分析")
    print("严格按照恒定流初值估计验证规范进行物理合理性检查")
    print("=" * 80)
    
    # 读取数据
    csv_file = Path('outputs/section_time_series/第9部分_断面时间序列数据.csv')
    if not csv_file.exists():
        print(f"❌ 数据文件不存在: {csv_file}")
        return False
    
    df = pd.read_csv(csv_file, encoding='utf-8-sig')
    print(f"✅ 数据文件读取成功，共{len(df)}行数据")
    
    # 提取断面数据
    sections_data = {}
    for section_name in df['断面名称'].unique():
        section_df = df[df['断面名称'] == section_name]
        sections_data[section_name] = {
            'times': section_df['时间(小时)'].values,
            'mileages': section_df['里程(m)'].values,
            'water_levels': section_df['水位(m)'].values,
            'flow_rates': section_df['流量(m³/s)'].values,
            'velocities': section_df['流速(m/s)'].values,
            'froude_numbers': section_df['弗劳德数'].values,
            'wetted_areas': section_df['过水面积(m²)'].values
        }
    
    # 执行8项核心物理合理性分析
    analysis_results = {}
    analysis_results['水面线单调性'] = check_water_surface_monotonicity(sections_data)
    analysis_results['亚临界流态'] = check_subcritical_flow(sections_data)
    analysis_results['流速分布'] = check_velocity_distribution(sections_data)
    analysis_results['流量连续性'] = check_flow_continuity(sections_data)
    analysis_results['能量方程'] = check_energy_equation(sections_data)
    analysis_results['非恒定流特性'] = check_unsteady_characteristics(sections_data)
    analysis_results['数值稳定性'] = check_numerical_stability(sections_data)
    analysis_results['边界条件响应'] = check_boundary_response(sections_data)
    
    # 生成综合评估报告
    generate_comprehensive_assessment(analysis_results, sections_data)
    create_rationality_verification_plots(sections_data, analysis_results)
    
    return True

def check_water_surface_monotonicity(sections_data):
    """检查水面线单调性（用户记忆规范要求）"""
    print("\n🔍 1. 水面线单调性检查")
    
    results = {}
    mileages = []
    section_names = []
    for name, data in sections_data.items():
        mileages.append(data['mileages'][0])
        section_names.append(name)
    
    # 按里程排序
    sorted_indices = np.argsort(mileages)
    sorted_names = [section_names[i] for i in sorted_indices]
    
    monotonicity_violations = 0
    time_points = sections_data[list(sections_data.keys())[0]]['times']
    
    for i, time in enumerate(time_points):
        water_levels = []
        for name in sorted_names:
            water_levels.append(sections_data[name]['water_levels'][i])
        
        # 检查是否单调递减（上游到下游水位应该降低）
        violations = 0
        for j in range(len(water_levels) - 1):
            if water_levels[j] < water_levels[j + 1]:  # 上游水位低于下游
                violations += 1
        
        if violations > 0:
            monotonicity_violations += 1
            print(f"   ⚠️ 时刻{time:.1f}h: 水面线非单调，{violations}处违反")
        else:
            print(f"   ✅ 时刻{time:.1f}h: 水面线单调递减正常")
    
    monotonicity_rate = (len(time_points) - monotonicity_violations) / len(time_points) * 100
    results['单调性符合率'] = monotonicity_rate
    results['违反次数'] = monotonicity_violations
    
    if monotonicity_rate >= 90:
        results['评级'] = '优秀'
        print(f"   🎯 水面线单调性检查: 优秀 ({monotonicity_rate:.1f}%符合)")
    elif monotonicity_rate >= 80:
        results['评级'] = '良好'
    else:
        results['评级'] = '需改进'
    
    return results

def check_subcritical_flow(sections_data):
    """检查亚临界流态确认（Fr < 1）"""
    print("\n🔍 2. 亚临界流态确认检查")
    
    results = {}
    total_points = 0
    subcritical_points = 0
    max_froude = 0
    critical_violations = []
    
    for section_name, data in sections_data.items():
        froude_numbers = data['froude_numbers']
        times = data['times']
        
        for i, (fr, time) in enumerate(zip(froude_numbers, times)):
            total_points += 1
            max_froude = max(max_froude, fr)
            
            if fr < 1.0:
                subcritical_points += 1
            else:
                critical_violations.append({
                    'section': section_name,
                    'time': time,
                    'froude': fr
                })
        
        section_max_fr = max(froude_numbers)
        section_min_fr = min(froude_numbers)
        print(f"   📍 {section_name}: Fr范围 {section_min_fr:.3f} - {section_max_fr:.3f}")
    
    subcritical_rate = subcritical_points / total_points * 100
    results['亚临界率'] = subcritical_rate
    results['最大弗劳德数'] = max_froude
    results['临界违反次数'] = len(critical_violations)
    
    if len(critical_violations) == 0:
        results['评级'] = '优秀'
        print(f"   🎯 亚临界流态检查: 优秀 (100%亚临界，最大Fr={max_froude:.3f})")
    elif subcritical_rate >= 95:
        results['评级'] = '良好'
    else:
        results['评级'] = '需改进'
    
    return results

def check_velocity_distribution(sections_data):
    """检查流速分布合理性"""
    print("\n🔍 3. 流速分布合理性评估")
    
    results = {}
    velocity_violations = []
    total_points = 0
    reasonable_points = 0
    
    for section_name, data in sections_data.items():
        velocities = data['velocities']
        for v in velocities:
            total_points += 1
            if 0.5 <= v <= 5.0:
                reasonable_points += 1
            else:
                velocity_violations.append({'section': section_name, 'velocity': v})
        
        print(f"   📍 {section_name}: 流速范围 {min(velocities):.2f} - {max(velocities):.2f} m/s")
    
    reasonable_rate = reasonable_points / total_points * 100
    results['合理率'] = reasonable_rate
    results['违反次数'] = len(velocity_violations)
    
    if len(velocity_violations) == 0:
        results['评级'] = '优秀'
        print(f"   🎯 流速分布检查: 优秀 (无异常)")
    elif reasonable_rate >= 90:
        results['评级'] = '良好'
    else:
        results['评级'] = '需改进'
    
    return results

def check_flow_continuity(sections_data):
    """检查流量连续性校验"""
    print("\n🔍 4. 流量连续性校验")
    
    results = {}
    times = sections_data[list(sections_data.keys())[0]]['times']
    continuity_violations = []
    
    for i, time in enumerate(times):
        flows = []
        for section_name, data in sections_data.items():
            flows.append(data['flow_rates'][i])
        
        max_flow = max(flows)
        min_flow = min(flows)
        flow_variation = (max_flow - min_flow) / min_flow * 100 if min_flow > 0 else 0
        
        if flow_variation > 100:  # 超过100%变化认为异常
            continuity_violations.append({'time': time, 'variation': flow_variation})
        
        print(f"   ⏰ 时刻{time:.1f}h: 流量范围 {min_flow:.1f}-{max_flow:.1f} m³/s (变化{flow_variation:.1f}%)")
    
    results['连续性违反次数'] = len(continuity_violations)
    
    if len(continuity_violations) == 0:
        results['评级'] = '优秀'
        print(f"   🎯 流量连续性检查: 优秀 (符合非恒定流调蓄特性)")
    else:
        results['评级'] = '需关注'
    
    return results

def check_energy_equation(sections_data):
    """检查能量方程合理性"""
    print("\n🔍 5. 能量方程合理性检查")
    
    results = {}
    g = 9.81  # 重力加速度
    energy_violations = []
    
    section_items = [(name, data['mileages'][0]) for name, data in sections_data.items()]
    section_items.sort(key=lambda x: x[1])  # 按里程排序
    
    times = sections_data[list(sections_data.keys())[0]]['times']
    
    for i, time in enumerate(times):
        energies = []
        for section_name, mileage in section_items:
            data = sections_data[section_name]
            h = data['water_levels'][i]
            v = data['velocities'][i]
            energy_head = h + v * v / (2 * g)
            energies.append(energy_head)
        
        violations = 0
        for j in range(len(energies) - 1):
            if energies[j] < energies[j + 1]:  # 上游能量低于下游
                violations += 1
        
        if violations > 0:
            energy_violations.append({'time': time, 'violations': violations})
        
        print(f"   ⏰ 时刻{time:.1f}h: 能量水头分布检查 ({'正常' if violations == 0 else f'{violations}处异常'})")
    
    results['能量违反次数'] = len(energy_violations)
    
    if len(energy_violations) == 0:
        results['评级'] = '优秀'
        print(f"   🎯 能量方程检查: 优秀 (能量沿程合理递减)")
    else:
        results['评级'] = '需分析'
    
    return results

def check_unsteady_characteristics(sections_data):
    """检查非恒定流特性验证"""
    print("\n🔍 6. 非恒定流特性验证")
    
    results = {}
    upstream_flows = sections_data['上游断面']['flow_rates']
    downstream_flows = sections_data['下游断面']['flow_rates']
    times = sections_data['上游断面']['times']
    
    # 计算坦化效应
    upstream_variation = (max(upstream_flows) - min(upstream_flows)) / min(upstream_flows) * 100
    downstream_variation = (max(downstream_flows) - min(downstream_flows)) / min(downstream_flows) * 100
    attenuation_rate = (upstream_variation - downstream_variation) / upstream_variation * 100
    
    # 寻找峰值传播延迟
    upstream_peak_time = times[np.argmax(upstream_flows)]
    downstream_peak_time = times[np.argmax(downstream_flows)]
    propagation_delay = downstream_peak_time - upstream_peak_time
    
    print(f"   📈 坦化效应: {attenuation_rate:.1f}% (上游变化{upstream_variation:.1f}% → 下游变化{downstream_variation:.1f}%)")
    print(f"   ⏰ 峰值传播延迟: {propagation_delay:.1f}小时")
    
    results['坦化效应'] = attenuation_rate
    results['峰值传播延迟'] = propagation_delay
    
    if 40 <= attenuation_rate <= 80 and propagation_delay >= 0:
        results['评级'] = '优秀'
        print(f"   🎯 非恒定流特性: 优秀 (坦化效应和传播延迟符合物理规律)")
    elif 20 <= attenuation_rate <= 90:
        results['评级'] = '良好'
    else:
        results['评级'] = '需分析'
    
    return results

def check_numerical_stability(sections_data):
    """检查数值稳定性评估"""
    print("\n🔍 7. 数值稳定性评估")
    
    results = {}
    oscillation_count = 0
    total_series = 0
    
    for section_name, data in sections_data.items():
        for param_name in ['water_levels', 'flow_rates', 'velocities']:
            values = data[param_name]
            total_series += 1
            
            # 检查是否有非物理的振荡
            oscillations = 0
            for i in range(2, len(values)):
                if ((values[i-2] < values[i-1] > values[i]) or 
                    (values[i-2] > values[i-1] < values[i])):
                    oscillations += 1
            
            if oscillations > len(values) * 0.3:  # 超过30%的点有振荡
                oscillation_count += 1
    
    stability_rate = (total_series - oscillation_count) / total_series * 100 if total_series > 0 else 100
    results['稳定率'] = stability_rate
    results['振荡序列数'] = oscillation_count
    
    if oscillation_count == 0:
        results['评级'] = '优秀'
        print(f"   🎯 数值稳定性: 优秀 (无振荡，变化平滑)")
    elif stability_rate >= 80:
        results['评级'] = '良好'
    else:
        results['评级'] = '需改进'
    
    return results

def check_boundary_response(sections_data):
    """检查边界条件响应分析"""
    print("\n🔍 8. 边界条件响应分析")
    
    results = {}
    upstream_flows = sections_data['上游断面']['flow_rates']
    input_variation = (max(upstream_flows) - min(upstream_flows)) / min(upstream_flows) * 100
    
    print(f"   📊 上游流量变化幅度: {input_variation:.1f}%")
    
    results['输入变化幅度'] = input_variation
    
    if input_variation >= 50:
        results['评级'] = '优秀'
        print(f"   🎯 边界条件响应: 优秀 (输入变化充分体现)")
    else:
        results['评级'] = '良好'
    
    return results

def generate_comprehensive_assessment(analysis_results, sections_data):
    """生成综合评估报告"""
    print("\n" + "=" * 80)
    print("📋 综合评估报告")
    print("=" * 80)
    
    # 计算总体评分
    evaluation_scores = {
        '水面线单调性': analysis_results['水面线单调性']['单调性符合率'],
        '亚临界流态': analysis_results['亚临界流态']['亚临界率'],
        '流速分布': analysis_results['流速分布']['合理率'],
        '数值稳定性': analysis_results['数值稳定性']['稳定率']
    }
    
    overall_score = np.mean(list(evaluation_scores.values()))
    print(f"\n🎯 总体评分: {overall_score:.1f}分 (满分100分)")
    
    # 详细评估
    print(f"\n📊 各项指标详细评估:")
    for criterion, score in evaluation_scores.items():
        grade = "优秀" if score >= 90 else "良好" if score >= 80 else "需改进"
        print(f"   {criterion}: {score:.1f}分 ({grade})")
    
    # 物理合理性总结
    print(f"\n🔬 物理合理性验证总结:")
    print(f"   ✅ 水力学基本规律:")
    print(f"     - 水面线单调性: {analysis_results['水面线单调性']['评级']}")
    print(f"     - 亚临界流态: {analysis_results['亚临界流态']['评级']}")
    print(f"     - 能量方程: {analysis_results['能量方程']['评级']}")
    
    print(f"   🌊 非恒定流特性:")
    unsteady = analysis_results['非恒定流特性']
    print(f"     - 坦化效应: {unsteady['坦化效应']:.1f}% (合理范围40-80%)")
    print(f"     - 传播延迟: {unsteady['峰值传播延迟']:.1f}小时 (体现延迟效应)")
    
    print(f"   🔢 数值计算质量:")
    print(f"     - 数值稳定性: {analysis_results['数值稳定性']['评级']}")
    print(f"     - 流量连续性: {analysis_results['流量连续性']['评级']}")
    
    # 总体结论
    print(f"\n🏁 总体结论:")
    if overall_score >= 90:
        print(f"   🎉 结果合理性: 优秀 - 完全符合物理规律和工程实际")
        print(f"   ✅ 圣维南方程非恒定流计算结果高度可信")
    elif overall_score >= 80:
        print(f"   ✅ 结果合理性: 良好 - 基本符合物理规律，可用于工程分析")
        print(f"   💡 建议关注个别指标的优化空间")
    else:
        print(f"   ⚠️ 结果合理性: 需改进 - 存在物理合理性问题")
        print(f"   🔧 建议检查模型参数和边界条件设置")
    
    # 生成报告文件
    save_assessment_report(analysis_results, overall_score)

def create_rationality_verification_plots(sections_data, analysis_results):
    """创建物理合理性验证图表"""
    print("\n📊 生成物理合理性验证图表...")
    
    # 设置中文字体（按用户记忆规范）
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    
    # 字体大小规范
    title_fontsize = 24
    label_fontsize = 18
    legend_fontsize = 16
    
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(20, 16))
    fig.suptitle('第9部分非恒定流结果物理合理性验证', fontsize=title_fontsize, fontweight='bold')
    
    times = sections_data['上游断面']['times']
    colors = {'上游断面': '#0d47a1', '中游断面': '#ff6f00', '下游断面': '#1b5e20'}
    
    # 1. 弗劳德数时间序列（亚临界流态验证）
    for section_name, data in sections_data.items():
        froude_numbers = data['froude_numbers']
        ax1.plot(times, froude_numbers, color=colors[section_name], 
                linewidth=3.0, label=section_name, marker='o', markersize=6)
    
    ax1.axhline(y=1.0, color='red', linestyle='--', linewidth=3, label='临界流线 (Fr=1)')
    ax1.set_xlabel('时间 (小时)', fontsize=label_fontsize)
    ax1.set_ylabel('弗劳德数 (-)', fontsize=label_fontsize)
    ax1.set_title('亚临界流态验证 (Fr < 1)', fontsize=label_fontsize, fontweight='bold')
    ax1.legend(fontsize=legend_fontsize)
    ax1.grid(True, alpha=0.3)
    
    # 2. 水面线纵剖面（单调性验证）
    mileages = [0, 2500, 5000]  # 各断面里程
    for i, time in enumerate([0, 1.5, 4]):  # 选择3个时刻
        time_idx = int(time * 2)  # 转换为数组索引
        if time_idx < len(times):
            water_levels = []
            for section_name in ['上游断面', '中游断面', '下游断面']:
                water_levels.append(sections_data[section_name]['water_levels'][time_idx])
            
            ax2.plot(mileages, water_levels, linewidth=3.0, marker='o', markersize=8,
                    label=f't={time}h')
    
    ax2.set_xlabel('里程 (m)', fontsize=label_fontsize)
    ax2.set_ylabel('水位 (m)', fontsize=label_fontsize)
    ax2.set_title('水面线单调性验证', fontsize=label_fontsize, fontweight='bold')
    ax2.legend(fontsize=legend_fontsize)
    ax2.grid(True, alpha=0.3)
    
    # 3. 流量传播与坦化效应
    for section_name, data in sections_data.items():
        flow_rates = data['flow_rates']
        ax3.plot(times, flow_rates, color=colors[section_name], 
                linewidth=3.0, label=section_name, marker='s', markersize=6)
    
    ax3.set_xlabel('时间 (小时)', fontsize=label_fontsize)
    ax3.set_ylabel('流量 (m³/s)', fontsize=label_fontsize)
    ax3.set_title('非恒定流传播与坦化效应验证', fontsize=label_fontsize, fontweight='bold')
    ax3.legend(fontsize=legend_fontsize)
    ax3.grid(True, alpha=0.3)
    
    # 4. 能量水头验证
    g = 9.81
    for section_name, data in sections_data.items():
        energy_heads = []
        for i in range(len(times)):
            h = data['water_levels'][i]
            v = data['velocities'][i]
            energy_head = h + v * v / (2 * g)
            energy_heads.append(energy_head)
        
        ax4.plot(times, energy_heads, color=colors[section_name], 
                linewidth=3.0, label=section_name, marker='^', markersize=6)
    
    ax4.set_xlabel('时间 (小时)', fontsize=label_fontsize)
    ax4.set_ylabel('能量水头 (m)', fontsize=label_fontsize)
    ax4.set_title('能量方程合理性验证', fontsize=label_fontsize, fontweight='bold')
    ax4.legend(fontsize=legend_fontsize)
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # 保存图表
    output_dir = Path('outputs/section_time_series')
    output_dir.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_dir / '第9部分_物理合理性验证图表.svg', dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    
    print(f"   📈 物理合理性验证图表已保存")

def save_assessment_report(analysis_results, overall_score):
    """保存评估报告"""
    output_dir = Path('outputs/section_time_series')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    report_file = output_dir / '第9部分_结果合理性评估报告.txt'
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("第9部分非恒定流模拟结果合理性评估报告\n")
        f.write("=" * 60 + "\n\n")
        
        f.write(f"总体评分: {overall_score:.1f}分 (满分100分)\n\n")
        
        f.write("详细评估结果:\n")
        for category, results in analysis_results.items():
            f.write(f"\n{category}:\n")
            f.write(f"  评级: {results['评级']}\n")
            for key, value in results.items():
                if key != '评级':
                    f.write(f"  {key}: {value}\n")
        
        f.write(f"\n结论:\n")
        if overall_score >= 90:
            f.write("结果完全符合物理规律，计算可信度高\n")
        elif overall_score >= 80:
            f.write("结果基本符合物理规律，可用于工程分析\n")
        else:
            f.write("结果存在合理性问题，需要进一步检查\n")
    
    print(f"   📄 评估报告已保存至: {report_file}")

if __name__ == "__main__":
    analyze_result_rationality()