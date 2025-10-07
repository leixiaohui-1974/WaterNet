#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分布式方法切换快速指南

这个脚本演示如何在WaterNet中快速切换不同的分布式仿真方法。

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


def quick_method_switching_guide():
    """快速方法切换指南"""
    
    print("🚀 分布式方法切换快速指南")
    print("=" * 40)
    
    # 1. 创建渠道对象
    print("\n📋 步骤1: 创建渠道对象")
    channel_config = {
        'object_definition': {
            'object_id': 'my_channel',
            'object_type': 'channel'
        },
        'geometry': {
            'length': 1000.0,
            'bottom_width': 5.0,
            'side_slope': 1.5,
            'roughness': 0.025
        },
        'simulation_preferences': {
            'default_method': 'muskingum_model'
        },
        'muskingum_parameters': {
            'K': 600.0,
            'x': 0.15
        }
    }
    
    channel = ChannelObject('my_channel', config=channel_config)
    channel.initialize()
    print(f"✅ 渠道对象创建成功: {channel.object_id}")
    
    # 2. 方法切换演示
    print("\n🔄 步骤2: 方法切换演示")
    
    # 可用的分布式方法
    methods = [
        ('saint_venant_full', '完整圣维南方程 - 最高精度'),
        ('saint_venant_simplified', '简化圣维南方程 - 工程精度'),
        ('diffusive_wave', '扩散波方程 - 中等精度'),
        ('kinematic_wave', '运动波方程 - 快速计算'),
        ('muskingum_model', '马斯京干模型 - 经典方法'),
        ('idz_model', 'IDZ模型 - 传递函数'),
        ('storage_routing', '蓄量演算法 - 物理守恒'),
        ('water_balance', '水量平衡法 - 最简单')
    ]
    
    print("💡 如何切换方法:")
    for method, description in methods:
        print(f"   • {method}: {description}")
        success = channel.set_simulation_method(method)
        if success:
            print(f"     ✅ 切换成功 → 当前方法: {channel.simulation_method}")
        else:
            print(f"     ❌ 切换失败")
        print()
    
    # 3. 通过仿真管理器配置方法
    print("\n⚙️ 步骤3: 通过仿真管理器配置方法")
    
    manager = WaterSystemSimulationManager()
    test_channel = manager.create_water_object('channel', 'managed_channel', {
        'length': 2000.0,
        'slope': 0.0002,
        'roughness': 0.025
    })
    
    print("💡 使用仿真管理器配置方法:")
    for method, description in methods[:4]:  # 测试前4种方法
        success = manager.configure_simulation_method('managed_channel', method)
        if success:
            print(f"   ✅ {method}: 配置成功")
        else:
            print(f"   ❌ {method}: 配置失败")
    
    # 4. 实用建议
    print("\n💡 步骤4: 方法选择建议")
    scenarios = [
        {
            'scenario': '洪水预警系统',
            'requirement': '快速响应 + 合理精度',
            'recommended': 'muskingum_model',
            'reason': '计算速度快，参数简单，适合实时应用'
        },
        {
            'scenario': '工程设计验证',
            'requirement': '工程精度 + 稳定性',
            'recommended': 'saint_venant_simplified',
            'reason': '精度高，计算稳定，满足工程需求'
        },
        {
            'scenario': '科研级仿真',
            'requirement': '最高精度',
            'recommended': 'saint_venant_full',
            'reason': '物理完整性最高，适合精细研究'
        },
        {
            'scenario': '大流域快速评估',
            'requirement': '计算效率',
            'recommended': 'kinematic_wave',
            'reason': '简化假设，适合长距离河道'
        }
    ]
    
    for scenario in scenarios:
        print(f"🎯 {scenario['scenario']}:")
        print(f"   需求: {scenario['requirement']}")
        print(f"   推荐: {scenario['recommended']}")
        print(f"   原因: {scenario['reason']}")
        print()
    
    # 5. 代码示例
    print("📝 步骤5: 代码示例")
    
    code_examples = '''
# 示例1: 直接切换渠道对象的方法
channel = ChannelObject('my_channel', config=my_config)
channel.initialize()

# 切换到马斯京干模型
channel.set_simulation_method('muskingum_model')

# 切换到圣维南方程
channel.set_simulation_method('saint_venant_full')

# 示例2: 通过仿真管理器配置方法
manager = WaterSystemSimulationManager()
channel = manager.create_water_object('channel', 'test_channel', config)

# 配置方法（支持额外参数）
manager.configure_simulation_method(
    object_id='test_channel',
    method='muskingum_model',
    method_config={'K': 600.0, 'x': 0.15}
)

# 示例3: 批量测试多种方法
methods = ['muskingum_model', 'idz_model', 'storage_routing']
for method in methods:
    success = channel.set_simulation_method(method)
    if success:
        print(f"方法 {method} 设置成功")
    '''
    
    print(code_examples)
    
    print("🎉 快速指南完成!")
    print("现在您可以根据需要灵活切换不同的分布式方法了!")


if __name__ == "__main__":
    quick_method_switching_guide()