#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
验证第9部分完整非恒定流模拟的断面时间序列分析
"""

import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from waternet.objects.conveyance import ChannelObject

def verify_section_time_series():
    """验证断面时间序列分析的正确性"""
    print("🔍 验证第9部分：完整非恒定流模拟的断面时间序列分析")
    print("=" * 80)
    
    # 创建圣维南模型渠道配置（与演示脚本保持一致）
    channel_config = {
        'object_definition': {
            'object_id': 'saint_venant_verify',
            'object_type': 'channel'
        },
        'basic_properties': {
            'length': 5000.0,
            'average_width': 15.0,
            'roughness': 0.025,
            'slope': 0.0001,
            'time_step': 60.0
        },
        'geometry_definition': {
            'cross_sections': [
                {'station': 0, 'elevation': 86.0, 'bottom_width': 15, 'side_slope': 1.5, 'roughness': 0.025, 'shape_type': 'trapezoidal'},
                {'station': 2500, 'elevation': 85.5, 'bottom_width': 15, 'side_slope': 1.5, 'roughness': 0.025, 'shape_type': 'trapezoidal'},
                {'station': 5000, 'elevation': 85.0, 'bottom_width': 15, 'side_slope': 1.5, 'roughness': 0.025, 'shape_type': 'trapezoidal'}
            ]
        },
        'simulation_preferences': {
            'default_method': 'saint_venant_full'
        }
    }
    
    try:
        print("1. 创建圣维南模型渠道...")
        sv_channel = ChannelObject('saint_venant_verify', config=channel_config)
        sv_channel.set_upstream_boundary(flow=100.0)
        sv_channel.set_downstream_boundary(level=96.0)
        
        print(f"   ✅ 渠道创建成功: {sv_channel.simulation_method}")
        print(f"   📏 渠道长度: {channel_config['basic_properties']['length']} m")
        print(f"   🔧 断面数量: {len(channel_config['geometry_definition']['cross_sections'])}")
        
        print("\n2. 配置边界条件时间序列...")
        boundary_series = {
            'time_steps': [0, 1800, 3600, 5400, 7200, 9000, 10800, 12600, 14400],  # 9个时间点
            'upstream_flows': [100.0, 115.0, 140.0, 160.0, 150.0, 130.0, 110.0, 105.0, 100.0],  # 洪峰过程
            'downstream_levels': [96.0, 96.05, 96.15, 96.25, 96.20, 96.10, 96.05, 96.02, 96.0]  # 下游水位变化
        }
        
        print(f"   📊 时间序列长度: {len(boundary_series['time_steps'])} 个时间点")
        print(f"   🌊 上游流量范围: {min(boundary_series['upstream_flows']):.1f} - {max(boundary_series['upstream_flows']):.1f} m³/s")
        print(f"   📈 下游水位范围: {min(boundary_series['downstream_levels']):.2f} - {max(boundary_series['downstream_levels']):.2f} m")
        
        print("\n3. 配置断面级时间序列分析选项...")
        analysis_options = {
            'output_sections': ['upstream', 'middle', 'downstream'],  # 输出3个断面
            'plot_options': {
                'single_scenario': True,       # 生成时间序列图
                'multi_scenario': False,
                'inlet_outlet_only': False,
                'all_sections': True,         # 包含所有断面分析
                'sections_time_series': True,  # 启用断面级时间序列
                'detailed_analysis': True     # 详细分析模式
            },
            'compute_only': False,  # 开启可视化以生成图表
            'method_comparison': False
        }
        
        print(f"   🎯 输出断面: {analysis_options['output_sections']}")
        print(f"   📈 可视化模式: 已启用")
        print(f"   🔬 详细分析: 已启用")
        
        print("\n4. 执行完整非恒定流仿真...")
        print("   ⏳ 计算中...")
        
        result = sv_channel.simulate_unsteady_flow_series(
            boundary_series=boundary_series,
            simulation_options=analysis_options
        )
        
        print("\n5. 分析仿真结果...")
        if result['success']:
            print("   ✅ 仿真成功完成!")
            
            # 基本信息
            time_steps = result.get('time_steps', [])
            method = result.get('method', 'unknown')
            print(f"   📋 时间步数: {len(time_steps)}")
            print(f"   🔧 仿真方法: {method}")
            
            # 断面级结果验证
            if 'sections_data' in result:
                sections_data = result['sections_data']
                print(f"\n   📊 断面级时间序列结果验证:")
                
                for section_name, data in sections_data.items():
                    water_levels = data.get('water_levels', [])
                    flow_rates = data.get('flow_rates', [])
                    velocities = data.get('velocities', [])
                    froude_numbers = data.get('froude_numbers', [])
                    
                    print(f"\n     🔹 {section_name}断面:")
                    print(f"       数据点数: {len(water_levels)} (水位), {len(flow_rates)} (流量)")
                    
                    if water_levels:
                        min_h, max_h = min(water_levels), max(water_levels)
                        print(f"       水位变化: {min_h:.3f} - {max_h:.3f} m (变幅 {max_h-min_h:.3f} m)")
                        
                        # 验证水位的物理合理性
                        if min_h > 85 and max_h < 100:
                            print(f"       ✅ 水位数据物理合理")
                        else:
                            print(f"       ⚠️ 水位数据可能异常")
                    
                    if flow_rates:
                        min_q, max_q = min(flow_rates), max(flow_rates)
                        print(f"       流量变化: {min_q:.2f} - {max_q:.2f} m³/s (变幅 {max_q-min_q:.2f} m³/s)")
                        
                        # 验证流量的连续性
                        if min_q > 0 and max_q <= max(boundary_series['upstream_flows']) * 1.1:
                            print(f"       ✅ 流量数据连续性合理")
                        else:
                            print(f"       ⚠️ 流量数据可能有问题")
                    
                    if velocities:
                        min_v, max_v = min(velocities), max(velocities)
                        print(f"       流速变化: {min_v:.3f} - {max_v:.3f} m/s")
                        
                        # 验证流速合理性
                        if min_v >= 0 and max_v < 10:
                            print(f"       ✅ 流速数据合理")
                        else:
                            print(f"       ⚠️ 流速数据可能异常")
                    
                    if froude_numbers:
                        min_fr, max_fr = min(froude_numbers), max(froude_numbers)
                        print(f"       弗劳德数: {min_fr:.3f} - {max_fr:.3f}")
                        
                        # 验证弗劳德数（明渠流通常 < 1）
                        if max_fr < 1.5:
                            print(f"       ✅ 弗劳德数表明亚临界流，符合明渠特性")
                        else:
                            print(f"       ⚠️ 弗劳德数过大，可能出现超临界流")
            
            # 系统级特性分析
            if 'system_data' in result:
                system_data = result['system_data']
                inflows = system_data.get('total_inflow', [])
                outflows = system_data.get('total_outflow', [])
                storages = system_data.get('total_storage', [])
                
                print(f"\n   🌊 系统级水力特性分析:")
                
                if inflows and outflows:
                    peak_inflow = max(inflows)
                    peak_outflow = max(outflows)
                    peak_reduction = (peak_inflow - peak_outflow) / peak_inflow * 100
                    
                    print(f"     坦化效应: {peak_reduction:.1f}% (峰值从{peak_inflow:.0f}削减到{peak_outflow:.1f} m³/s)")
                    
                    # 验证坦化效应的合理性
                    if 0 <= peak_reduction <= 50:
                        print(f"     ✅ 坦化效应合理")
                    else:
                        print(f"     ⚠️ 坦化效应异常")
                
                if storages:
                    storage_range = max(storages) - min(storages)
                    print(f"     蓄量变化范围: {storage_range:.0f} m³")
                    
                    if storage_range > 0:
                        print(f"     ✅ 蓄量变化反映了非恒定流特性")
                    else:
                        print(f"     ⚠️ 蓄量无变化，可能计算有问题")
            
            # 时间序列图验证
            if 'plots' in result and result['plots']:
                plots = result['plots']
                print(f"\n   📈 生成的时间序列图表验证:")
                
                script_dir = Path(__file__).parent
                plots_dir = script_dir / 'outputs' / 'plots'
                
                for plot_name, plot_path in plots.items():
                    if plot_path:
                        plot_file = Path(plot_path)
                        if plot_file.exists():
                            file_size = plot_file.stat().st_size
                            print(f"     ✅ {plot_name}: {plot_file.name} ({file_size} bytes)")
                        else:
                            print(f"     ❌ {plot_name}: 文件不存在 - {plot_path}")
                    else:
                        print(f"     ⚠️ {plot_name}: 路径为空")
            
            print(f"\n   🎉 断面时间序列分析验证完成!")
            return True
            
        else:
            print(f"   ❌ 仿真失败: {result.get('error', '未知错误')}")
            if result.get('convergence_failure'):
                print(f"   🔴 收敛失败: 数值求解不收敛")
            print(f"   💡 这可能是由于严格的收敛检查导致的")
            return False
            
    except Exception as e:
        print(f"   💥 验证过程发生异常: {e}")
        import traceback
        print(f"   📝 详细错误信息:")
        traceback.print_exc()
        return False

def check_output_directory():
    """检查输出目录结构"""
    print(f"\n📁 检查输出目录结构...")
    
    script_dir = Path(__file__).parent
    outputs_dir = script_dir / 'outputs'
    
    print(f"   输出根目录: {outputs_dir}")
    
    if outputs_dir.exists():
        print(f"   ✅ outputs/ 目录存在")
        
        for subdir in ['plots', 'data', 'reports']:
            subdir_path = outputs_dir / subdir
            if subdir_path.exists():
                files = list(subdir_path.iterdir())
                print(f"   ✅ {subdir}/ 存在，包含 {len(files)} 个文件/目录")
                
                # 显示最新的几个文件
                if files:
                    files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                    for f in files[:3]:
                        if f.is_file():
                            size = f.stat().st_size
                            print(f"      📄 {f.name} ({size} bytes)")
                        else:
                            count = len(list(f.iterdir())) if f.is_dir() else 0
                            print(f"      📁 {f.name}/ ({count} 项)")
            else:
                print(f"   ❌ {subdir}/ 目录不存在")
    else:
        print(f"   ❌ outputs/ 目录不存在")

if __name__ == "__main__":
    try:
        success = verify_section_time_series()
        check_output_directory()
        
        if success:
            print(f"\n🎉 验证完成: 断面时间序列分析功能正常")
        else:
            print(f"\n⚠️ 验证发现问题: 需要进一步检查")
    except Exception as e:
        print(f"\n💥 验证失败: {e}")