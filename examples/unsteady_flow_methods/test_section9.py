#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试第9部分：完整非恒定流模拟"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parents[2]
sys.path.insert(0, str(project_root))

from waternet.objects.water_object import ChannelObject

def test_section9():
    """测试第9部分：完整非恒定流模拟"""
    print("测试第9部分：完整非恒定流模拟")
    
    # 圣维南模型配置
    saint_venant_config = {
        'object_type': 'channel',
        'name': 'saint_venant_channel',
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

    # 创建圣维南明渠对象
    sv_channel = ChannelObject('saint_venant_channel', config=saint_venant_config)
    sv_channel.set_upstream_boundary(flow=100.0)
    sv_channel.set_downstream_boundary(level=96.0)

    print(f"圣维南模型创建成功: {sv_channel.simulation_method}")

    # 定义边界条件时间序列
    complete_boundary_series = {
        'time_steps': [0, 1800, 3600, 5400, 7200, 9000, 10800, 12600, 14400],
        'upstream_flows': [100.0, 115.0, 140.0, 160.0, 150.0, 130.0, 110.0, 105.0, 100.0],
        'downstream_levels': [96.0, 96.05, 96.15, 96.25, 96.20, 96.10, 96.05, 96.02, 96.0]
    }

    # 断面分析选项
    sections_analysis_options = {
        'output_sections': ['upstream', 'middle', 'downstream'],
        'plot_options': {
            'single_scenario': True,
            'all_sections': True,
            'sections_time_series': True
        },
        'compute_only': False,
        'method_comparison': False
    }

    # 执行非恒定流仿真
    print("开始执行非恒定流仿真...")
    result = sv_channel.simulate_unsteady_flow_series(
        boundary_series=complete_boundary_series,
        simulation_options=sections_analysis_options
    )

    if result['success']:
        print("仿真成功!")
        sections_data = result.get('sections_data', {})
        for section_name, data in sections_data.items():
            water_levels = data.get('water_levels', [])
            flow_rates = data.get('flow_rates', [])
            velocities = data.get('velocities', [])
            if water_levels and flow_rates:
                print(f"  {section_name}断面:")
                print(f"    水位: {min(water_levels):.3f}-{max(water_levels):.3f}m")
                print(f"    流量: {min(flow_rates):.1f}-{max(flow_rates):.1f}m³/s")
                print(f"    流速: {min(velocities):.2f}-{max(velocities):.2f}m/s")
                
                # 检查非恒定流特性
                flow_variation = (max(flow_rates) - min(flow_rates)) / max(flow_rates) * 100
                print(f"    流量变幅: {flow_variation:.1f}%")
        
        # 检查物理合理性
        upstream_flows = sections_data['upstream']['flow_rates']
        downstream_flows = sections_data['downstream']['flow_rates']
        
        if upstream_flows and downstream_flows:
            upstream_max = max(upstream_flows)
            downstream_max = max(downstream_flows)
            attenuation = (upstream_max - downstream_max) / upstream_max * 100
            print(f"  坦化效应: {attenuation:.1f}%")
            
            if abs(attenuation) < 5:
                print("  警告: 坦化效应过小，可能仍在使用恒定流计算!")
            else:
                print("  非恒定流特性正常")
    else:
        print(f"仿真失败: {result.get('error', '未知错误')}")

if __name__ == "__main__":
    test_section9()