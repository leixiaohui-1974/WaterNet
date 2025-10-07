#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整圣维南方程方法测试

测试完整圣维南方程方法的切换和运行。
基于用户记忆的面向对象实现要求和非恒定流数值方法规范。

Author: WaterNet Development Team
Date: 2024-10-06
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from waternet.objects.conveyance import ChannelObject
from waternet.core.simulation_manager import WaterSystemSimulationManager


def test_saint_venant_switching():
    """测试完整圣维南方程方法的切换"""
    
    print("🧪 完整圣维南方程方法切换测试")
    print("=" * 40)
    
    # 1. 直接创建ChannelObject并切换到圣维南方程
    print("\n📋 测试1: 直接ChannelObject方法切换")
    
    # 创建基础渠道配置
    basic_config = {
        'object_definition': {
            'object_id': 'test_channel',
            'object_type': 'channel'
        },
        'geometry': {
            'length': 2000.0,
            'bottom_width': 10.0,
            'side_slope': 1.5,
            'bottom_elevation': 100.0,
            'roughness': 0.025
        },
        'simulation_preferences': {
            'default_method': 'muskingum_model'
        },
        'muskingum_parameters': {
            'K': 600.0,
            'x': 0.15
        },
        # 添加河道断面配置（圣维南方程所必需）
        'cross_sections': [
            {
                'station': 0.0,
                'bottom_elevation': 100.0,
                'bottom_width': 10.0,
                'side_slope': 1.5,
                'roughness': 0.025
            },
            {
                'station': 1000.0,
                'bottom_elevation': 99.8,
                'bottom_width': 10.0,
                'side_slope': 1.5,
                'roughness': 0.025
            },
            {
                'station': 2000.0,
                'bottom_elevation': 99.6,
                'bottom_width': 10.0,
                'side_slope': 1.5,
                'roughness': 0.025
            }
        ]
    }
    
    try:
        # 创建渠道对象
        channel = ChannelObject('test_channel', config=basic_config)
        channel.initialize()
        print(f"✅ 渠道对象创建成功: {channel.object_id}")
        print(f"🔧 初始方法: {channel.simulation_method}")
        
        # 切换到完整圣维南方程
        print(f"\n🔄 切换到完整圣维南方程...")
        success = channel.set_simulation_method('saint_venant_full')
        
        if success:
            print(f"✅ 方法切换成功!")
            print(f"🎯 当前方法: {channel.simulation_method}")
            print(f"📊 底层模型: {type(channel.underlying_model).__name__ if channel.underlying_model else 'None'}")
            
            # 测试简单仿真
            try:
                channel.set_upstream_boundary(flow=80.0)
                channel.set_downstream_boundary(level=103.0)
                result = channel.solve_steady_flow()
                print(f"🧪 恒定流测试: {'✅ 成功' if result['success'] else '❌ 失败'}")
            except Exception as sim_e:
                print(f"⚠️ 仿真测试异常: {sim_e}")
            
        else:
            print(f"❌ 方法切换失败")
            
    except Exception as e:
        print(f"❌ 测试1失败: {e}")
    
    # 2. 通过SimulationManager切换到圣维南方程
    print(f"\n📋 测试2: SimulationManager方法配置")
    
    try:
        # 创建仿真管理器
        manager = WaterSystemSimulationManager()
        
        # 创建渠道配置（包含断面信息）
        channel_config = {
            'length': 3000.0,
            'slope': 0.0003,
            'roughness': 0.025,
            'bottom_width': 12.0,
            'side_slope': 2.0,
            'simulation_method': 'saint_venant_full',
            # 圣维南方程数值求解参数
            'saint_venant_parameters': {
                'dx': 100.0,  # 空间步长
                'courant_number': 0.5,  # CFL条件
                'max_iterations': 50,
                'convergence_tolerance': 1e-4
            },
            # 河道断面配置（圣维南方程所必需）
            'cross_sections': [
                {
                    'station': 0.0,
                    'bottom_elevation': 100.0,
                    'bottom_width': 12.0,
                    'side_slope': 2.0,
                    'roughness': 0.025
                },
                {
                    'station': 1500.0,
                    'bottom_elevation': 99.55,
                    'bottom_width': 12.0,
                    'side_slope': 2.0,
                    'roughness': 0.025
                },
                {
                    'station': 3000.0,
                    'bottom_elevation': 99.1,
                    'bottom_width': 12.0,
                    'side_slope': 2.0,
                    'roughness': 0.025
                }
            ]
        }
        
        # 通过管理器创建渠道对象
        channel = manager.create_water_object('channel', 'sv_channel', channel_config)
        print(f"✅ 管理器创建渠道成功: {channel.object_id}")
        print(f"🔧 仿真方法: {channel.simulation_method}")
        print(f"📊 底层模型: {type(channel.underlying_model).__name__ if channel.underlying_model else 'None'}")
        
        # 验证配置是否正确应用
        if hasattr(channel, 'cross_sections') and channel.cross_sections:
            print(f"📏 断面数量: {len(channel.cross_sections)}")
        
        # 测试方法配置功能
        print(f"\n🔧 测试方法配置功能...")
        config_success = manager.configure_simulation_method(
            'sv_channel', 
            'saint_venant_full',
            method_config={'dx': 80.0, 'courant_number': 0.4}
        )
        print(f"⚙️ 方法配置: {'✅ 成功' if config_success else '❌ 失败'}")
        
    except Exception as e:
        print(f"❌ 测试2失败: {e}")
    
    # 3. 不同圣维南方程模式对比
    print(f"\n📋 测试3: 圣维南方程模式对比")
    
    saint_venant_methods = [
        'saint_venant_full',
        'saint_venant_simplified', 
        'diffusive_wave',
        'kinematic_wave'
    ]
    
    success_count = 0
    for method in saint_venant_methods:
        try:
            # 创建测试渠道
            test_config = basic_config.copy()
            test_config['simulation_preferences']['default_method'] = method
            
            test_channel = ChannelObject(f'test_{method}', config=test_config)
            test_channel.initialize()
            
            # 切换到指定方法
            switch_success = test_channel.set_simulation_method(method)
            
            if switch_success:
                print(f"✅ {method}: 切换成功")
                success_count += 1
            else:
                print(f"❌ {method}: 切换失败")
                
        except Exception as e:
            print(f"❌ {method}: 异常 - {e}")
    
    print(f"\n📊 圣维南方程模式测试结果:")
    print(f"🎯 成功率: {success_count}/{len(saint_venant_methods)} ({100*success_count/len(saint_venant_methods):.1f}%)")
    
    # 4. 总结
    print(f"\n📋 测试总结")
    print("=" * 20)
    
    if success_count > 0:
        print("✅ 完整圣维南方程方法切换测试完成!")
        print("💡 使用建议:")
        print("   • saint_venant_full: 最高精度，适合科研级仿真")
        print("   • saint_venant_simplified: 工程精度，平衡性能")
        print("   • diffusive_wave: 中等精度，忽略惯性项")
        print("   • kinematic_wave: 快速计算，适合长距离河道")
        print("\n🔧 关键配置要点:")
        print("   • 必须提供至少2个河道断面")
        print("   • 设置合适的空间步长(dx)和CFL条件")
        print("   • 根据应用需求选择数值求解参数")
    else:
        print("⚠️ 圣维南方程方法切换可能需要进一步配置")
    
    return success_count > 0


if __name__ == "__main__":
    test_saint_venant_switching()