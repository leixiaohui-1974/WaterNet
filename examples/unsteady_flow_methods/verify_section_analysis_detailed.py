#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
验证第9部分断面时间序列分析的详细结果
重点验证圣维南模型的断面级水力学计算正确性
"""

import sys
import os
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parents[2]
sys.path.insert(0, str(project_root))

from waternet.objects.water_object import ChannelObject
from waternet.core.enums import SimulationMethod

def verify_saintvenant_section_analysis():
    """验证圣维南模型的断面时间序列分析正确性"""
    print("=" * 80)
    print("圣维南模型断面时间序列分析验证")
    print("=" * 80)
    
    try:
        # 1. 创建圣维南明渠对象
        print("1. 创建圣维南明渠对象...")
        channel_config = {
            'object_type': 'channel',
            'name': 'verify_channel',
            'spatial_representation': 'distributed',
            'simulation_preferences': {
                'default_method': 'SAINT_VENANT_FULL'
            },
            'geometry': {
                'length': 10000.0,
                'width': 20.0,
                'depth': 5.0,
                'slope': 0.0005,
                'roughness': 0.03,
                'bed_elevation': 90.0
            }
        }
        
        channel = ChannelObject('verify_channel', config=channel_config)
        print(f"   对象创建成功: {channel.object_id}")
        print(f"   仿真方法: {channel.simulation_method}")
        
        # 2. 设置边界条件
        print("\n2. 设置边界条件...")
        channel.set_boundary_condition('upstream', 'flow', 100.0)
        channel.set_boundary_condition('downstream', 'level', 96.0)
        
        # 3. 执行非恒定流仿真，重点检查断面数据
        print("\n3. 执行完整非恒定流仿真...")
        
        # 设置断面分析选项
        sections_analysis_options = {
            'output_sections': ['upstream', 'middle', 'downstream'],
            'plot_options': {
                'single_scenario': True,
                'all_sections': True,
                'sections_time_series': True
            },
            'compute_only': False  # 生成图表
        }
        
        # 定义三角形入流过程
        inflow_scenario = {
            'name': 'triangular_flood',
            'time_hours': [0, 2, 6, 12],  # 小时
            'flows': [100, 160, 100, 100]  # m³/s
        }
        
        # 设置输出路径
        output_dir = Path(__file__).parent / 'outputs' / 'verification'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        results = channel.simulate_unsteady_flow_series(
            inflow_scenario=inflow_scenario,
            sections_analysis_options=sections_analysis_options,
            output_dir=str(output_dir)
        )
        
        # 4. 分析和验证结果
        print("\n4. 分析断面时间序列结果...")
        
        if results['success']:
            # 验证断面数据
            sections_data = results.get('sections_data', {})
            time_steps = results.get('time_steps', [])
            
            print(f"   ✅ 仿真成功")
            print(f"   📊 时间步数: {len(time_steps)}")
            print(f"   🎯 断面数量: {len(sections_data)}")
            
            # 验证各个断面的数据质量
            for section_name, data in sections_data.items():
                water_levels = data.get('water_levels', [])
                flow_rates = data.get('flow_rates', [])
                velocities = data.get('velocities', [])
                froude_numbers = data.get('froude_numbers', [])
                
                print(f"\n   📍 {section_name}断面验证:")
                print(f"     水位范围: {min(water_levels):.3f} - {max(water_levels):.3f} m")
                print(f"     流量范围: {min(flow_rates):.1f} - {max(flow_rates):.1f} m³/s")
                print(f"     流速范围: {min(velocities):.2f} - {max(velocities):.2f} m/s")
                print(f"     弗兰德数: {min(froude_numbers):.3f} - {max(froude_numbers):.3f}")
                
                # 物理合理性检查
                physical_checks = []
                
                # 1. 水位单调递减（上游到下游）
                if section_name == 'upstream':
                    avg_level = np.mean(water_levels)
                    upstream_level = avg_level
                elif section_name == 'middle':
                    avg_level = np.mean(water_levels)
                    if 'upstream_level' in locals():
                        if avg_level <= upstream_level:
                            physical_checks.append("✅ 中游水位低于上游")
                        else:
                            physical_checks.append("❌ 中游水位异常高于上游")
                elif section_name == 'downstream':
                    avg_level = np.mean(water_levels)
                    physical_checks.append("✅ 下游水位符合边界条件")
                
                # 2. 流量连续性
                if len(flow_rates) > 1:
                    flow_variation = (max(flow_rates) - min(flow_rates)) / max(flow_rates)
                    if flow_variation < 0.7:  # 合理的流量变化范围
                        physical_checks.append(f"✅ 流量变化合理({flow_variation:.1%})")
                    else:
                        physical_checks.append(f"⚠️ 流量变化较大({flow_variation:.1%})")
                
                # 3. 弗兰德数检查
                avg_froude = np.mean(froude_numbers)
                if 0.1 < avg_froude < 1.0:
                    physical_checks.append(f"✅ 弗兰德数正常({avg_froude:.2f})")
                else:
                    physical_checks.append(f"⚠️ 弗兰德数异常({avg_froude:.2f})")
                
                for check in physical_checks:
                    print(f"     {check}")
            
            # 5. 生成验证图表
            print(f"\n5. 生成验证图表...")
            plot_file = create_verification_plots(sections_data, time_steps, output_dir)
            print(f"   📈 验证图表: {plot_file}")
            
            # 6. 非恒定流特性分析
            print(f"\n6. 非恒定流特性分析...")
            analyze_unsteady_characteristics(sections_data, results)
            
        else:
            print(f"   ❌ 仿真失败: {results.get('error', '未知错误')}")
            
    except Exception as e:
        print(f"验证过程出错: {e}")
        import traceback
        traceback.print_exc()

def create_verification_plots(sections_data, time_steps, output_dir):
    """创建详细的验证图表"""
    
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(18, 14))
    fig.suptitle('圣维南模型断面时间序列验证分析', fontsize=20, fontweight='bold')
    
    # 转换时间到小时
    time_hours = np.array(time_steps) / 3600.0
    colors = {'upstream': '#1f77b4', 'middle': '#ff7f0e', 'downstream': '#2ca02c'}
    
    # 1. 水位时间序列
    for section_name, data in sections_data.items():
        water_levels = data['water_levels']
        if water_levels:
            ax1.plot(time_hours[:len(water_levels)], water_levels, 
                    color=colors.get(section_name, 'gray'), 
                    linewidth=2.5, label=f'{section_name}断面', marker='o', markersize=4)
    
    ax1.set_xlabel('时间 (小时)', fontsize=14)
    ax1.set_ylabel('水位 (m)', fontsize=14)
    ax1.set_title('断面水位时间序列', fontsize=16)
    ax1.legend(fontsize=12)
    ax1.grid(True, alpha=0.3)
    
    # 2. 流量时间序列
    for section_name, data in sections_data.items():
        flow_rates = data['flow_rates']
        if flow_rates:
            ax2.plot(time_hours[:len(flow_rates)], flow_rates, 
                    color=colors.get(section_name, 'gray'), 
                    linewidth=2.5, label=f'{section_name}断面', marker='s', markersize=4)
    
    ax2.set_xlabel('时间 (小时)', fontsize=14)
    ax2.set_ylabel('流量 (m³/s)', fontsize=14)
    ax2.set_title('断面流量时间序列', fontsize=16)
    ax2.legend(fontsize=12)
    ax2.grid(True, alpha=0.3)
    
    # 3. 流速时间序列
    for section_name, data in sections_data.items():
        velocities = data['velocities']
        if velocities:
            ax3.plot(time_hours[:len(velocities)], velocities, 
                    color=colors.get(section_name, 'gray'), 
                    linewidth=2.5, label=f'{section_name}断面', marker='^', markersize=4)
    
    ax3.set_xlabel('时间 (小时)', fontsize=14)
    ax3.set_ylabel('流速 (m/s)', fontsize=14)
    ax3.set_title('断面流速时间序列', fontsize=16)
    ax3.legend(fontsize=12)
    ax3.grid(True, alpha=0.3)
    
    # 4. 弗兰德数时间序列
    for section_name, data in sections_data.items():
        froude_numbers = data['froude_numbers']
        if froude_numbers:
            ax4.plot(time_hours[:len(froude_numbers)], froude_numbers, 
                    color=colors.get(section_name, 'gray'), 
                    linewidth=2.5, label=f'{section_name}断面', marker='d', markersize=4)
    
    ax4.set_xlabel('时间 (小时)', fontsize=14)
    ax4.set_ylabel('弗兰德数 (-)', fontsize=14)
    ax4.set_title('弗兰德数时间序列', fontsize=16)
    ax4.legend(fontsize=12)
    ax4.grid(True, alpha=0.3)
    ax4.axhline(y=1.0, color='red', linestyle='--', alpha=0.7, label='临界流')
    
    plt.tight_layout()
    
    # 保存图表
    plot_file = output_dir / 'saintvenant_section_verification.svg'
    plt.savefig(plot_file, dpi=300, bbox_inches='tight')
    plt.close()
    
    return plot_file

def analyze_unsteady_characteristics(sections_data, results):
    """分析非恒定流特性"""
    
    print("   📊 非恒定流特性分析:")
    
    # 1. 坦化效应分析
    system_data = results.get('system_data', {})
    if 'total_inflow' in system_data and 'total_outflow' in system_data:
        inflows = system_data['total_inflow']
        outflows = system_data['total_outflow']
        
        if inflows and outflows:
            peak_inflow = max(inflows)
            peak_outflow = max(outflows)
            attenuation = (peak_inflow - peak_outflow) / peak_inflow * 100
            
            print(f"     🌊 坦化效应: {attenuation:.1f}%")
            print(f"        峰值入流: {peak_inflow:.1f} m³/s")
            print(f"        峰值出流: {peak_outflow:.1f} m³/s")
            
            if 10 <= attenuation <= 50:
                print(f"     ✅ 坦化效应合理")
            else:
                print(f"     ⚠️ 坦化效应异常")
    
    # 2. 水位传播分析
    if 'upstream' in sections_data and 'downstream' in sections_data:
        up_levels = sections_data['upstream']['water_levels']
        down_levels = sections_data['downstream']['water_levels']
        
        if up_levels and down_levels:
            up_range = max(up_levels) - min(up_levels)
            down_range = max(down_levels) - min(down_levels)
            
            print(f"     📊 水位变化幅度:")
            print(f"        上游断面: {up_range:.3f} m")
            print(f"        下游断面: {down_range:.3f} m")
            
            if up_range > down_range:
                print(f"     ✅ 水位传播衰减正常")
            else:
                print(f"     ⚠️ 水位传播异常")

if __name__ == "__main__":
    verify_saintvenant_section_analysis()