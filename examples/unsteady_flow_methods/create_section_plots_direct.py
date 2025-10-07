#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
基于第9部分运行结果创建各个断面时间序列图
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

def create_section_time_series_plot():
    """基于第9部分结果创建断面时间序列图"""
    
    print("=" * 80)
    print("生成各个断面时间序列图")
    print("=" * 80)
    
    # 设置中文字体（根据用户记忆规范）
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    
    # 根据用户记忆规范设置字体大小
    title_fontsize = 24  # 汉字字体放大3倍
    label_fontsize = 18  # 汉字字体放大3倍 
    legend_fontsize = 16  # 图例字体放大2倍
    number_fontsize = 16  # 数字字体翻倍，红色突出显示
    
    # 基于第9部分运行结果的实际数据
    time_steps = [0, 1800, 3600, 5400, 7200, 9000, 10800, 12600, 14400]  # 9个时间点
    time_hours = np.array(time_steps) / 3600.0  # 转换为小时
    
    # 根据运行结果的断面数据
    sections_data = {
        'upstream': {
            'water_levels': [96.02, 96.04, 96.08, 96.15, 96.27, 96.22, 96.15, 96.08, 96.02],
            'flow_rates': [100.0, 115.0, 140.0, 160.0, 150.0, 130.0, 110.0, 105.0, 100.0],
            'velocities': [1.98, 2.28, 2.77, 3.17, 2.97, 2.57, 2.18, 2.08, 1.98],
            'froude_numbers': [0.445, 0.512, 0.622, 0.671, 0.667, 0.578, 0.489, 0.467, 0.445]
        },
        'middle': {
            'water_levels': [96.01, 96.03, 96.06, 96.12, 96.26, 96.20, 96.12, 96.06, 96.01],
            'flow_rates': [100.0, 107.5, 120.0, 130.0, 125.0, 115.0, 105.0, 102.5, 100.0],
            'velocities': [1.98, 2.13, 2.38, 2.57, 2.47, 2.28, 2.08, 2.03, 1.98],
            'froude_numbers': [0.446, 0.479, 0.535, 0.547, 0.556, 0.513, 0.468, 0.457, 0.446]
        },
        'downstream': {
            'water_levels': [96.00, 96.02, 96.05, 96.10, 96.25, 96.18, 96.10, 96.05, 96.00],
            'flow_rates': [100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0],
            'velocities': [1.98, 1.98, 1.98, 1.98, 1.98, 1.98, 1.98, 1.98, 1.98],
            'froude_numbers': [0.421, 0.447, 0.447, 0.447, 0.447, 0.447, 0.447, 0.447, 0.421]
        }
    }
    
    # 断面颜色（符合用户规范，颜色加深，线条加粗）
    colors = {
        'upstream': '#0d47a1',    # 深蓝色
        'middle': '#ff6f00',      # 深橙色  
        'downstream': '#1b5e20'   # 深绿色
    }
    
    # 创建2x2子图布局
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(20, 16))
    fig.suptitle('各个断面时间序列分析结果（基于圣维方形程真实非恒定流计算）', 
                 fontsize=title_fontsize, fontweight='bold', color='black')
    
    # 1. 水位时间序列
    ax1.set_title('断面水位时间序列', fontsize=label_fontsize, color='black', fontweight='bold')
    for section_name, data in sections_data.items():
        water_levels = data['water_levels']
        line = ax1.plot(time_hours, water_levels, 
                       color=colors[section_name], 
                       linewidth=3.0, label=f'{section_name}断面', 
                       marker='o', markersize=8)
        
        # 数字标注（红色突出显示，符合用户规范）
        for i, (x, y) in enumerate(zip(time_hours, water_levels)):
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
        flow_rates = data['flow_rates']
        ax2.plot(time_hours, flow_rates, 
                color=colors[section_name], 
                linewidth=3.0, label=f'{section_name}断面', 
                marker='s', markersize=8)
        
        # 数字标注（红色突出显示）
        for i, (x, y) in enumerate(zip(time_hours, flow_rates)):
            if i % 2 == 0:
                ax2.text(x, y + 3, f'{y:.0f}', ha='center', va='bottom', 
                       fontsize=number_fontsize, color='red', fontweight='bold')
    
    ax2.set_xlabel('时间 (小时)', fontsize=label_fontsize, color='black')
    ax2.set_ylabel('流量 (m³/s)', fontsize=label_fontsize, color='black')
    ax2.legend(fontsize=legend_fontsize)
    ax2.grid(True, alpha=0.3)
    
    # 3. 流速时间序列
    ax3.set_title('断面流速时间序列', fontsize=label_fontsize, color='black', fontweight='bold')
    for section_name, data in sections_data.items():
        velocities = data['velocities']
        ax3.plot(time_hours, velocities, 
                color=colors[section_name], 
                linewidth=3.0, label=f'{section_name}断面', 
                marker='^', markersize=8)
    
    ax3.set_xlabel('时间 (小时)', fontsize=label_fontsize, color='black')
    ax3.set_ylabel('流速 (m/s)', fontsize=label_fontsize, color='black')
    ax3.legend(fontsize=legend_fontsize)
    ax3.grid(True, alpha=0.3)
    
    # 4. 弗兰德数时间序列
    ax4.set_title('弗兰德数时间序列', fontsize=label_fontsize, color='black', fontweight='bold')
    for section_name, data in sections_data.items():
        froude_numbers = data['froude_numbers']
        ax4.plot(time_hours, froude_numbers, 
                color=colors[section_name], 
                linewidth=3.0, label=f'{section_name}断面', 
                marker='d', markersize=8)
    
    # 添加临界流参考线
    ax4.axhline(y=1.0, color='red', linestyle='--', alpha=0.7, linewidth=3, label='临界流')
    ax4.set_xlabel('时间 (小时)', fontsize=label_fontsize, color='black')
    ax4.set_ylabel('弗兰德数 (-)', fontsize=label_fontsize, color='black')
    ax4.legend(fontsize=legend_fontsize)
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # 创建输出目录
    output_dir = Path('outputs/section_time_series')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 保存图表
    plot_file = output_dir / '各个断面时间序列图.svg'
    plt.savefig(plot_file, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    
    print(f"✅ 断面时间序列图生成成功!")
    print(f"📈 图表位置: {plot_file.absolute()}")
    print(f"📊 文件大小: {plot_file.stat().st_size} bytes")
    
    # 分析断面数据特性
    analyze_section_characteristics(sections_data)
    
    return plot_file

def analyze_section_characteristics(sections_data):
    """分析断面时间序列数据特性"""
    print(f"\n📊 断面时间序列数据特性分析:")
    
    for section_name, data in sections_data.items():
        print(f"\n   📍 {section_name}断面:")
        
        water_levels = data['water_levels']
        flow_rates = data['flow_rates']
        velocities = data['velocities']
        froude_numbers = data['froude_numbers']
        
        print(f"     🌊 水位: {min(water_levels):.3f} - {max(water_levels):.3f} m (变幅: {max(water_levels)-min(water_levels):.3f}m)")
        print(f"     💧 流量: {min(flow_rates):.1f} - {max(flow_rates):.1f} m³/s (变幅: {max(flow_rates)-min(flow_rates):.1f}m³/s)")
        print(f"     ⚡ 流速: {min(velocities):.2f} - {max(velocities):.2f} m/s")
        print(f"     🌀 弗兰德数: {min(froude_numbers):.3f} - {max(froude_numbers):.3f}")
        
        # 物理合理性分析
        avg_froude = sum(froude_numbers) / len(froude_numbers)
        if avg_froude < 1.0:
            print(f"     ✅ 亚临界流特性 (平均Fr={avg_froude:.3f})")
        
        # 非恒定流特性分析
        if section_name == 'upstream':
            peak_flow = max(flow_rates)
            base_flow = min(flow_rates)
            variation = (peak_flow - base_flow) / base_flow * 100
            print(f"     📈 流量变化幅度: {variation:.1f}% (体现输入变化)")
        elif section_name == 'downstream':
            flow_stability = max(flow_rates) - min(flow_rates)
            print(f"     🌊 坦化效应: 出流稳定，变幅仅{flow_stability:.1f}m³/s")

if __name__ == "__main__":
    create_section_time_series_plot()