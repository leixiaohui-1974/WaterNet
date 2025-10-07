#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
WaterSystemSimulationManager 多情景仿真演示

此脚本演示WaterSystemSimulationManager类的多情景仿真功能，包括：
1. 单对象仿真情景
2. 水网整体仿真情景
3. 恒定流和非恒定流仿真
4. 多情景对比分析
5. 报告生成

Author: WaterNet Development Team
Date: 2025-10-06
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

def main():
    """主函数 - 演示WaterSystemSimulationManager多情景仿真功能"""
    
    print("🌊 WaterSystemSimulationManager 多情景仿真演示")
    print("=" * 60)
    
    try:
        # 导入必要的模块
        from waternet.core.simulation_manager import (
            WaterSystemSimulationManager, 
            SimulationConfiguration,
            SimulationStrategy
        )
        
        # 1. 创建仿真管理器
        print("\n📋 步骤1: 创建水系统仿真管理器")
        config = SimulationConfiguration(
            project_name="MultiScenario_WaterSystem_Demo",
            strategy=SimulationStrategy.COMPREHENSIVE_ANALYSIS,
            output_directory=str(Path(__file__).parent / "outputs" / "water_system_scenarios")
        )
        
        manager = WaterSystemSimulationManager(config)
        
        # 2. 创建水系统对象
        print("\n🏗️ 步骤2: 创建水系统对象")
        
        # 创建第一个渠道对象
        channel_config_1 = {
            'length': 4000.0,
            'slope': 0.0003,
            'roughness': 0.025,
            'bottom_width': 12.0,
            'side_slope': 1.5,
            'muskingum_parameters': {'K': 250.0, 'x': 0.15}
        }
        channel1 = manager.create_water_object('channel', 'main_channel', channel_config_1)
        
        # 创建第二个渠道对象
        channel_config_2 = {
            'length': 3000.0,
            'slope': 0.0004,
            'roughness': 0.030,
            'bottom_width': 10.0,
            'side_slope': 2.0,
            'muskingum_parameters': {'K': 200.0, 'x': 0.20}
        }
        channel2 = manager.create_water_object('channel', 'branch_channel', channel_config_2)
        
        # 3. 设置水网连接关系
        print("\n🔗 步骤3: 设置水网连接关系")
        manager.add_connection('main_channel', 'branch_channel', 'flow')
        
        # 4. 定义多个仿真情景
        print("\n🎯 步骤4: 定义多个仿真情景")
        
        scenarios = [
            {
                'name': '情景1_单对象恒定流',
                'description': '主渠道单对象恒定流仿真',
                'simulation_mode': 'single_object',
                'target_object': 'main_channel',
                'boundary_conditions': {
                    'main_channel': {
                        'upstream': {'flow': 100.0},
                        'downstream': {'level': 95.0}
                    }
                }
            },
            {
                'name': '情景2_单对象高流量',
                'description': '主渠道高流量情况下的单对象仿真',
                'simulation_mode': 'single_object',
                'target_object': 'main_channel',
                'boundary_conditions': {
                    'main_channel': {
                        'upstream': {'flow': 150.0},
                        'downstream': {'level': 95.5}
                    }
                }
            },
            {
                'name': '情景3_水网整体仿真',
                'description': '完整水网系统的联立求解',
                'simulation_mode': 'network',
                'boundary_conditions': {
                    'main_channel': {
                        'upstream': {'flow': 120.0}
                    },
                    'branch_channel': {
                        'downstream': {'level': 94.0}
                    }
                }
            },
            {
                'name': '情景4_非恒定流',
                'description': '非恒定流仿真（含恒定流初值估计）',
                'simulation_mode': 'single_object',
                'target_object': 'main_channel',
                'boundary_conditions': {
                    'main_channel': {
                        'upstream': {'flow': 100.0},
                        'downstream': {'level': 95.0}
                    }
                },
                'time_series': {
                    'time_steps': [0, 1800, 3600, 5400, 7200],
                    'upstream_flows': [100.0, 120.0, 140.0, 130.0, 110.0],
                    'downstream_levels': [95.0, 95.2, 95.5, 95.3, 95.1]
                }
            }
        ]
        
        # 5. 执行恒定流多情景仿真
        print(f"\n🌊 步骤5: 执行恒定流多情景仿真 ({len(scenarios)-1}个恒定流情景)")
        
        steady_scenarios = scenarios[:3]  # 前3个是恒定流情景
        
        analysis_options = {
            'enable_comparison': True,
            'generate_report': True,
            'output_directory': str(Path(__file__).parent / 'outputs' / 'water_system_steady_scenarios'),
            'include_plots': True
        }
        
        steady_results = manager.simulate_scenarios(
            scenarios=steady_scenarios,
            simulation_type='steady',
            analysis_options=analysis_options
        )
        
        # 6. 执行非恒定流多情景仿真
        print(f"\n🌊 步骤6: 执行非恒定流多情景仿真")
        
        unsteady_scenarios = [scenarios[3]]  # 第4个是非恒定流情景
        
        unsteady_analysis_options = {
            'enable_comparison': False,  # 单情景不需要对比
            'generate_report': True,
            'output_directory': str(Path(__file__).parent / 'outputs' / 'water_system_unsteady_scenarios'),
            'include_plots': True
        }
        
        unsteady_results = manager.simulate_scenarios(
            scenarios=unsteady_scenarios,
            simulation_type='unsteady',
            analysis_options=unsteady_analysis_options
        )
        
        # 7. 显示仿真结果摘要
        print(f"\n📊 步骤7: 仿真结果摘要")
        print(f"\n恒定流仿真结果:")
        print(f"  • 总情景数: {steady_results['scenarios_count']}")
        print(f"  • 成功情景: {steady_results['execution_summary']['successful_scenarios']}")
        print(f"  • 失败情景: {steady_results['execution_summary']['failed_scenarios']}")
        
        if steady_results.get('comparison_analysis', {}).get('success', False):
            print(f"  • 对比分析: ✅ 已完成")
            recommendations = steady_results['comparison_analysis'].get('recommendations', [])
            if recommendations:
                print(f"  • 分析建议:")
                for i, rec in enumerate(recommendations[:3], 1):  # 显示前3条建议
                    print(f"    {i}. {rec}")
        
        print(f"\n非恒定流仿真结果:")
        print(f"  • 总情景数: {unsteady_results['scenarios_count']}")
        print(f"  • 成功情景: {unsteady_results['execution_summary']['successful_scenarios']}")
        print(f"  • 失败情景: {unsteady_results['execution_summary']['failed_scenarios']}")
        
        # 8. 显示报告文件位置
        print(f"\n📄 步骤8: 生成的报告文件")
        
        if steady_results.get('reports'):
            print(f"恒定流仿真报告:")
            for report_type, report_path in steady_results['reports'].items():
                if report_type != 'error':
                    print(f"  • {report_type}: {report_path}")
        
        if unsteady_results.get('reports'):
            print(f"非恒定流仿真报告:")
            for report_type, report_path in unsteady_results['reports'].items():
                if report_type != 'error':
                    print(f"  • {report_type}: {report_path}")
        
        # 9. 水网状态概要
        print(f"\n🌐 步骤9: 水网状态概要")
        network_summary = manager.get_network_summary()
        print(f"  • 对象数量: {network_summary['objects_count']}")
        print(f"  • 对象类型: {list(network_summary['objects_types'].values())}")
        print(f"  • 连接数量: {network_summary['connections_count']}")
        
        print(f"\n✅ WaterSystemSimulationManager 多情景仿真演示完成!")
        print(f"   - 恒定流情景: {steady_results['execution_summary']['successful_scenarios']}/{len(steady_scenarios)} 成功")
        print(f"   - 非恒定流情景: {unsteady_results['execution_summary']['successful_scenarios']}/{len(unsteady_scenarios)} 成功")
        print(f"   - 水网对象: {network_summary['objects_count']} 个")
        print(f"   - 功能演示: 单对象仿真 ✓, 水网仿真 ✓, 多情景对比 ✓, 报告生成 ✓")
        
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        print("请确保WaterNet库已正确安装")
        return False
        
    except Exception as e:
        print(f"❌ 演示执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 启动WaterSystemSimulationManager多情景仿真演示...")
    success = main()
    
    if success:
        print("\n🎉 演示成功完成!")
    else:
        print("\n💥 演示执行失败，请检查错误信息")
        sys.exit(1)