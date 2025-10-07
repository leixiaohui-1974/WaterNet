"""
渠道类多情景仿真演示

展示渠道对象的完整仿真能力：
- 单情景恒定流仿真
- 多情景恒定流仿真与对比分析
- 单情景非恒定流仿真（先恒定流估计初值）
- 多情景非恒定流仿真与对比分析
- 自动报告生成

Author: WaterNet Development Team
Date: 2025-10-06
"""

import sys
import os
from pathlib import Path

# 添加项目根目录
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from waternet.objects.conveyance import ChannelObject
from waternet.objects.base import SimulationMethod

def demo_multi_scenario_simulations():
    """演示渠道对象的多情景仿真功能"""
    print("=" * 80)
    print("渠道类多情景仿真演示")
    print("=" * 80)
    print("🌊 展示单情景和多情景的恒定流/非恒定流仿真")
    print("📊 包含自动对比分析和报告生成")
    print("=" * 80)
    
    try:
        # 1. 创建渠道对象
        print("\n1. 创建明渠对象...")
        
        channel_config = {
            'basic_properties': {
                'length': 5000.0,
                'slope': 0.0002,
                'roughness': 0.025,
                'bottom_width': 15.0,
                'side_slope': 1.5,
                'initial_volume': 15000.0,
                'average_width': 18.0,
                'base_elevation': 85.0
            },
            'simulation_preferences': {
                'default_method': 'muskingum_model'
            },
            'muskingum_parameters': {
                'K': 3600.0,
                'x': 0.15
            }
        }
        
        channel = ChannelObject('multi_scenario_channel', config=channel_config)
        channel.initialize()
        
        print(f"   ✅ 创建成功: {channel}")
        print(f"   📏 渠道长度: {channel_config['basic_properties']['length']}m")
        print(f"   🌊 仿真方法: {channel.simulation_method}")

        # 2. 单情景恒定流仿真
        print("\n2. 单情景恒定流仿真...")
        
        single_steady_scenario = [{
            'name': '设计工况',
            'description': '设计流量下的恒定流分析',
            'boundary_conditions': {
                'upstream': {'flow': 120.0},
                'downstream': {'level': 96.0}
            }
        }]
        
        steady_result = channel.simulate_scenarios(
            scenarios=single_steady_scenario,
            simulation_type='steady',
            analysis_options={
                'enable_comparison': False,
                'generate_report': True,
                'include_plots': False
            }
        )
        
        if steady_result['success']:
            print(f"   ✅ 单情景恒定流仿真成功")
            single_result = steady_result['individual_results']['设计工况']
            if single_result['success']:
                results = single_result['results']
                print(f"   📊 水位: {results['water_level']:.2f}m")
                print(f"   📊 出流: {results['outflow']:.1f}m³/s")
                print(f"   📊 蓄量: {results['storage']:.0f}m³")
        else:
            print(f"   ❌ 单情景恒定流仿真失败: {steady_result.get('error', '未知错误')}")

        # 3. 多情景恒定流仿真对比
        print("\n3. 多情景恒定流仿真对比...")
        
        multi_steady_scenarios = [
            {
                'name': '低水位工况',
                'description': '低流量、低水位条件',
                'boundary_conditions': {
                    'upstream': {'flow': 80.0},
                    'downstream': {'level': 95.5}
                }
            },
            {
                'name': '设计工况',
                'description': '设计流量、正常水位',
                'boundary_conditions': {
                    'upstream': {'flow': 120.0},
                    'downstream': {'level': 96.0}
                }
            },
            {
                'name': '高水位工况',
                'description': '高流量、高水位条件',
                'boundary_conditions': {
                    'upstream': {'flow': 160.0},
                    'downstream': {'level': 96.5}
                }
            }
        ]
        
        multi_steady_result = channel.simulate_scenarios(
            scenarios=multi_steady_scenarios,
            simulation_type='steady',
            analysis_options={
                'enable_comparison': True,
                'generate_report': True,
                'include_plots': True,
                'output_directory': 'results/multi_steady_scenarios'
            }
        )
        
        if multi_steady_result['success']:
            print(f"   ✅ 多情景恒定流仿真成功")
            exec_summary = multi_steady_result['execution_summary']
            print(f"   📈 成功情景: {exec_summary['successful_scenarios']}/{multi_steady_result['scenarios_count']}")
            
            if 'comparison_analysis' in multi_steady_result:
                comp = multi_steady_result['comparison_analysis']
                print(f"   🔍 对比分析: {comp['scenarios_compared']}个情景")
                if 'ranking' in comp and comp['ranking']:
                    print(f"   🏆 最佳情景: {comp['ranking'][0]['scenario_name']}")
            
            if 'reports' in multi_steady_result and multi_steady_result['reports'].get('success', False):
                print(f"   📄 报告生成: {multi_steady_result['reports']['output_directory']}")
        else:
            print(f"   ❌ 多情景恒定流仿真失败: {multi_steady_result.get('error', '未知错误')}")

        # 4. 单情景非恒定流仿真（先恒定流估计初值）
        print("\n4. 单情景非恒定流仿真...")
        
        single_unsteady_scenario = [{
            'name': '洪水演进',
            'description': '洪水过程的非恒定流演进',
            'boundary_conditions': {
                'upstream': {'flow': 100.0},  # 初始流量
                'downstream': {'level': 96.0}  # 固定下游水位
            },
            'time_series': {
                'upstream_flows': [100, 110, 130, 150, 145, 130, 115, 105, 100],
                'downstream_levels': [96.0] * 9,
                'time_hours': [0, 1, 2, 3, 4, 5, 6, 7, 8]
            }
        }]
        
        unsteady_result = channel.simulate_scenarios(
            scenarios=single_unsteady_scenario,
            simulation_type='unsteady',
            analysis_options={
                'enable_comparison': False,
                'generate_report': True,
                'include_plots': False
            }
        )
        
        if unsteady_result['success']:
            print(f"   ✅ 单情景非恒定流仿真成功")
            single_unsteady = unsteady_result['individual_results']['洪水演进']
            if single_unsteady['success']:
                if 'initial_steady_state' in single_unsteady:
                    initial = single_unsteady['initial_steady_state']
                    print(f"   🔄 初值估计: 水位={initial['water_level']:.2f}m, 蓄量={initial['storage']:.0f}m³")
                
                if 'performance_metrics' in single_unsteady:
                    metrics = single_unsteady['performance_metrics']
                    print(f"   📉 洪峰削减: {metrics['peak_attenuation_percent']:.1f}%")
                    print(f"   ⏱️ 响应时间: {metrics['response_time_hours']:.1f}小时")
        else:
            print(f"   ❌ 单情景非恒定流仿真失败: {unsteady_result.get('error', '未知错误')}")

        # 5. 多情景非恒定流仿真对比
        print("\n5. 多情景非恒定流仿真对比...")
        
        multi_unsteady_scenarios = [
            {
                'name': '标准洪水',
                'description': '标准洪水过程',
                'boundary_conditions': {
                    'upstream': {'flow': 100.0},
                    'downstream': {'level': 96.0}
                },
                'time_series': {
                    'upstream_flows': [100, 110, 130, 150, 145, 130, 115, 105, 100],
                    'downstream_levels': [96.0] * 9,
                    'time_hours': [0, 1, 2, 3, 4, 5, 6, 7, 8]
                }
            },
            {
                'name': '极端洪水',
                'description': '极端洪水过程',
                'boundary_conditions': {
                    'upstream': {'flow': 120.0},
                    'downstream': {'level': 96.2}
                },
                'time_series': {
                    'upstream_flows': [120, 140, 170, 200, 185, 160, 140, 125, 120],
                    'downstream_levels': [96.2] * 9,
                    'time_hours': [0, 1, 2, 3, 4, 5, 6, 7, 8]
                }
            }
        ]
        
        multi_unsteady_result = channel.simulate_scenarios(
            scenarios=multi_unsteady_scenarios,
            simulation_type='unsteady',
            analysis_options={
                'enable_comparison': True,
                'generate_report': True,
                'include_plots': True,
                'output_directory': 'results/multi_unsteady_scenarios'
            }
        )
        
        if multi_unsteady_result['success']:
            print(f"   ✅ 多情景非恒定流仿真成功")
            exec_summary = multi_unsteady_result['execution_summary']
            print(f"   📈 成功情景: {exec_summary['successful_scenarios']}/{multi_unsteady_result['scenarios_count']}")
            
            if 'comparison_analysis' in multi_unsteady_result:
                comp = multi_unsteady_result['comparison_analysis']
                print(f"   🔍 对比分析: {comp['scenarios_compared']}个情景")
            
            if 'reports' in multi_unsteady_result and multi_unsteady_result['reports'].get('success', False):
                print(f"   📄 报告生成: {multi_unsteady_result['reports']['output_directory']}")
        else:
            print(f"   ❌ 多情景非恒定流仿真失败: {multi_unsteady_result.get('error', '未知错误')}")

        # 6. 功能总结
        print("\n6. 功能总结...")
        
        print(f"   🏆 渠道对象 {channel.object_id} 多情景仿真完成!")
        print(f"   📋 仿真功能:")
        print(f"      ✅ 单情景恒定流仿真")
        print(f"      ✅ 多情景恒定流仿真与对比")
        print(f"      ✅ 单情景非恒定流仿真（含初值估计）") 
        print(f"      ✅ 多情景非恒定流仿真与对比")
        print(f"      ✅ 自动对比分析")
        print(f"      ✅ 报告和图表生成")
        
        print(f"\n   💡 核心特性:")
        print(f"      🎯 统一仿真接口 - simulate_scenarios方法")
        print(f"      🔄 非恒定流自动初值估计 - 先恒定流计算")
        print(f"      📊 多情景自动对比分析")
        print(f"      📄 可配置报告生成（纯计算或计算+报告）")
        print(f"      🎨 可视化图表支持")
        
        return {
            'success': True,
            'channel_object': channel,
            'simulation_results': {
                'single_steady': steady_result,
                'multi_steady': multi_steady_result, 
                'single_unsteady': unsteady_result,
                'multi_unsteady': multi_unsteady_result
            }
        }
        
    except Exception as e:
        print(f"❌ 多情景仿真演示异常: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}


if __name__ == "__main__":
    print("🚀 启动渠道类多情景仿真演示...")
    
    result = demo_multi_scenario_simulations()
    
    if result['success']:
        print(f"\n🎉 演示成功完成!")
        print(f"✨ 渠道对象现在具备完整的多情景仿真能力")
        print(f"💪 可以进行单一或多情景的恒定流/非恒定流模拟")
        print(f"📈 支持自动对比分析和报告生成")
        print(f"🔄 非恒定流仿真会自动进行恒定流初值估计")
    else:
        print(f"\n💔 演示执行失败: {result.get('error', '未知错误')}")
        print(f"🔧 请检查相关模块和依赖")
    
    print("\n" + "=" * 80)