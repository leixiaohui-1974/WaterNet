#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
生成各个断面的时间序列图
验证第9部分非恒定流断面时间序列分析结果
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

def generate_section_time_series_plot():
    """生成各个断面的时间序列图表"""
    print("=" * 80)
    print("生成各个断面的时间序列图表")
    print("=" * 80)
    
    try:
        # 1. 创建圣维南明渠对象
        print("1. 创建圣维南明渠对象...")
        channel_config = {
            'object_type': 'channel',
            'name': 'section_analysis_channel',
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
        
        channel = ChannelObject('section_analysis_channel', config=channel_config)
        print(f"   ✅ 对象创建成功: {channel.object_id}")
        print(f"   🎯 仿真方法: {channel.simulation_method}")
        
        # 2. 设置边界条件
        print("\n2. 设置边界条件...")
        channel.set_boundary_condition('upstream', 'flow', 100.0)
        channel.set_boundary_condition('downstream', 'level', 96.0)
        
        # 3. 定义三角形洪水过程
        print("\n3. 定义边界条件时间序列...")
        boundary_series = {
            'time_steps': [0, 1800, 3600, 5400, 7200, 9000, 10800, 12600, 14400],  # 9个时间点，每0.5小时
            'upstream_flows': [100.0, 115.0, 140.0, 160.0, 150.0, 130.0, 110.0, 105.0, 100.0],  # 三角形洪水过程
            'downstream_levels': [96.0, 96.05, 96.15, 96.25, 96.20, 96.10, 96.05, 96.02, 96.0]  # 水位变化
        }
        
        # 4. 配置断面分析选项
        print("\n4. 配置断面级时间序列分析选项...")
        sections_analysis_options = {
            'output_sections': ['upstream', 'middle', 'downstream'],  # 输出3个断面
            'plot_options': {
                'single_scenario': True,   # 生成单方法时间序列图
                'multi_scenario': False,
                'all_sections': True,     # 包含所有断面分析
                'sections_time_series': True  # 启用断面级时间序列
            },
            'compute_only': False,  # 必须设为False才能生成图表
            'method_comparison': False
        }
        
        # 5. 设置输出路径
        output_dir = Path(__file__).parent / 'outputs' / 'section_time_series'
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"   📁 输出目录: {output_dir}")
        
        # 6. 执行非恒定流仿真
        print("\n5. 执行非恒定流仿真...")
        results = channel.simulate_unsteady_flow_series(
            boundary_series=boundary_series,
            simulation_options=sections_analysis_options,
            output_dir=str(output_dir)
        )
        
        # 7. 分析结果
        if results['success']:
            print(f"\n✅ 仿真成功!")
            print(f"   📊 时间步数: {len(results.get('time_steps', []))}")
            
            # 手动生成断面时间序列图
            plot_file = create_detailed_section_plots(results, output_dir)
            print(f"\n📈 断面时间序列图已生成:")
            print(f"   {plot_file}")
            
            # 分析断面数据
            analyze_section_data(results)
            
        else:
            print(f"❌ 仿真失败: {results.get('error', '未知错误')}")
            
    except Exception as e:
        print(f"❌ 生成过程出错: {e}")
        import traceback
        traceback.print_exc()

def create_detailed_section_plots(results, output_dir):
    """创建详细的断面时间序列图表"""
    
    # 设置中文字体（根据用户记忆规范）
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    
    # 根据用户记忆规范设置字体大小
    title_fontsize = 24  # 汉字字体放大3倍
    label_fontsize = 18  # 汉字字体放大3倍 
    legend_fontsize = 16  # 图例字体放大2倍
    number_fontsize = 16  # 数字字体翻倍，红色突出显示
    
    # 创建2x2子图布局
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(20, 16))
    fig.suptitle('各个断面时间序列分析结果', fontsize=title_fontsize, fontweight='bold', color='black')
    
    # 提取时间和断面数据
    time_steps = results.get('time_steps', [])
    sections_data = results.get('sections_data', {})
    time_hours = np.array(time_steps) / 3600.0  # 转换为小时
    
    # 断面颜色（符合用户规范，颜色加深）
    colors = {
        'upstream': '#0d47a1',    # 深蓝色
        'middle': '#ff6f00',      # 深橙色  
        'downstream': '#1b5e20'   # 深绿色
    }
    
    # 1. 水位时间序列
    ax1.set_title('断面水位时间序列', fontsize=label_fontsize, color='black', fontweight='bold')
    for section_name, data in sections_data.items():
        water_levels = data.get('water_levels', [])
        if water_levels:
            time_subset = time_hours[:len(water_levels)]
            line = ax1.plot(time_subset, water_levels, 
                           color=colors.get(section_name, 'gray'), 
                           linewidth=3.0, label=f'{section_name}断面', 
                           marker='o', markersize=6)
            
            # 数字标注（红色突出显示，符合用户规范）
            for i, (x, y) in enumerate(zip(time_subset, water_levels)):
                if i % 2 == 0:  # 每隔2个点标注一次
                    ax1.text(x, y + 0.01, f'{y:.2f}', ha='center', va='bottom', 
                           fontsize=number_fontsize, color='red', fontweight='bold')
    
    ax1.set_xlabel('时间 (小时)', fontsize=label_fontsize, color='black')
    ax1.set_ylabel('水位 (m)', fontsize=label_fontsize, color='black')
    ax1.legend(fontsize=legend_fontsize)
    ax1.grid(True, alpha=0.3)
    
    # 2. 流量时间序列
    ax2.set_title('断面流量时间序列', fontsize=label_fontsize, color='black', fontweight='bold')
    for section_name, data in sections_data.items():
        flow_rates = data.get('flow_rates', [])
        if flow_rates:
            time_subset = time_hours[:len(flow_rates)]
            ax2.plot(time_subset, flow_rates, 
                    color=colors.get(section_name, 'gray'), 
                    linewidth=3.0, label=f'{section_name}断面', 
                    marker='s', markersize=6)
            
            # 数字标注（红色突出显示）
            for i, (x, y) in enumerate(zip(time_subset, flow_rates)):
                if i % 2 == 0:
                    ax2.text(x, y + 2, f'{y:.0f}', ha='center', va='bottom', 
                           fontsize=number_fontsize, color='red', fontweight='bold')
    
    ax2.set_xlabel('时间 (小时)', fontsize=label_fontsize, color='black')
    ax2.set_ylabel('流量 (m³/s)', fontsize=label_fontsize, color='black')
    ax2.legend(fontsize=legend_fontsize)
    ax2.grid(True, alpha=0.3)
    
    # 3. 流速时间序列
    ax3.set_title('断面流速时间序列', fontsize=label_fontsize, color='black', fontweight='bold')
    for section_name, data in sections_data.items():
        velocities = data.get('velocities', [])
        if velocities:
            time_subset = time_hours[:len(velocities)]
            ax3.plot(time_subset, velocities, 
                    color=colors.get(section_name, 'gray'), 
                    linewidth=3.0, label=f'{section_name}断面', 
                    marker='^', markersize=6)
    
    ax3.set_xlabel('时间 (小时)', fontsize=label_fontsize, color='black')
    ax3.set_ylabel('流速 (m/s)', fontsize=label_fontsize, color='black')
    ax3.legend(fontsize=legend_fontsize)
    ax3.grid(True, alpha=0.3)
    
    # 4. 弗兰德数时间序列
    ax4.set_title('弗兰德数时间序列', fontsize=label_fontsize, color='black', fontweight='bold')
    for section_name, data in sections_data.items():
        froude_numbers = data.get('froude_numbers', [])
        if froude_numbers:
            time_subset = time_hours[:len(froude_numbers)]
            ax4.plot(time_subset, froude_numbers, 
                    color=colors.get(section_name, 'gray'), 
                    linewidth=3.0, label=f'{section_name}断面', 
                    marker='d', markersize=6)
    
    # 添加临界流参考线
    ax4.axhline(y=1.0, color='red', linestyle='--', alpha=0.7, linewidth=2, label='临界流')
    ax4.set_xlabel('时间 (小时)', fontsize=label_fontsize, color='black')
    ax4.set_ylabel('弗兰德数 (-)', fontsize=label_fontsize, color='black')
    ax4.legend(fontsize=legend_fontsize)
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # 保存图表
    plot_file = output_dir / '各个断面时间序列图.svg'
    plt.savefig(plot_file, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    
    print(f"✅ 图表保存成功: {plot_file}")
    return plot_file

def analyze_section_data(results):
    """分析断面时间序列数据"""
    print(f"\n📊 断面时间序列数据分析:")
    
    sections_data = results.get('sections_data', {})
    
    for section_name, data in sections_data.items():
        print(f"\n   📍 {section_name}断面:")
        
        water_levels = data.get('water_levels', [])
        flow_rates = data.get('flow_rates', [])
        velocities = data.get('velocities', [])
        froude_numbers = data.get('froude_numbers', [])
        
        if water_levels:
            print(f"     🌊 水位范围: {min(water_levels):.3f} - {max(water_levels):.3f} m")
            print(f"     💧 流量范围: {min(flow_rates):.1f} - {max(flow_rates):.1f} m³/s")
            print(f"     ⚡ 流速范围: {min(velocities):.2f} - {max(velocities):.2f} m/s")
            print(f"     🌀 弗兰德数: {min(froude_numbers):.3f} - {max(froude_numbers):.3f}")
            
            # 物理合理性检查
            avg_froude = sum(froude_numbers) / len(froude_numbers)
            if avg_froude < 1.0:
                print(f"     ✅ 亚临界流 (Fr={avg_froude:.2f})")
            else:
                print(f"     ⚠️ 超临界流 (Fr={avg_froude:.2f})")

if __name__ == "__main__":
    generate_section_time_series_plot()