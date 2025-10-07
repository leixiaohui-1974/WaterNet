#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ChannelObject vs WaterSystemSimulationManager 功能对比演示

验证两个类的功能对等性，确保都能支持：
1. 分布式/集总式多方法仿真
2. 参数优化、辨识
3. 敏感性分析
4. 实时校正
5. 数字孪生
6. 多情景仿真
7. 水网联立求解（ChannelObject新增功能）

Author: WaterNet Development Team
Date: 2025-10-06
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

def test_channel_object_capabilities():
    """测试ChannelObject类的完整功能"""
    
    print("🧪 测试 ChannelObject 类功能")
    print("=" * 50)
    
    try:
        from waternet.objects.conveyance import ChannelObject
        
        # 创建渠道对象
        channel_config = {
            'basic_properties': {
                'length': 4000.0,
                'slope': 0.0003,
                'roughness': 0.025,
                'bottom_width': 12.0,
                'side_slope': 1.5
            },
            'simulation_preferences': {
                'default_method': 'muskingum_model'
            },
            'muskingum_parameters': {
                'K': 300.0,
                'x': 0.15
            }
        }
        
        channel = ChannelObject('test_channel', config=channel_config)
        channel.initialize()
        
        print("✅ ChannelObject 创建成功")
        
        # 测试功能列表
        capabilities = {
            '多方法仿真': [],
            '参数优化': False,
            '敏感性分析': False,
            '实时校正': False,
            '数字孪生': False,
            '多情景仿真': False,
            '水网联立求解': False
        }
        
        # 1. 测试多方法仿真支持
        available_methods = [
            'saint_venant_full', 'muskingum_model', 'idz_model', 
            'storage_routing', 'water_balance'
        ]
        
        for method in available_methods:
            try:
                success = channel.set_simulation_method(method)
                if success:
                    capabilities['多方法仿真'].append(method)
            except:
                pass
        
        # 2. 测试参数优化
        if hasattr(channel, 'parameter_optimization'):
            capabilities['参数优化'] = True
        
        # 3. 测试敏感性分析
        if hasattr(channel, 'sensitivity_analysis'):
            capabilities['敏感性分析'] = True
        
        # 4. 测试实时校正
        if hasattr(channel, 'real_time_calibration'):
            capabilities['实时校正'] = True
        
        # 5. 测试数字孪生
        if hasattr(channel, 'create_digital_twin'):
            capabilities['数字孪生'] = True
        
        # 6. 测试多情景仿真
        if hasattr(channel, 'simulate_scenarios'):
            capabilities['多情景仿真'] = True
        
        # 7. 测试水网联立求解
        if hasattr(channel, 'solve_network_coupled'):
            capabilities['水网联立求解'] = True
        
        return capabilities
        
    except Exception as e:
        print(f"❌ ChannelObject 测试失败: {e}")
        return {}

def test_water_system_manager_capabilities():
    """测试WaterSystemSimulationManager类的完整功能"""
    
    print("🧪 测试 WaterSystemSimulationManager 类功能")
    print("=" * 50)
    
    try:
        from waternet.core.simulation_manager import WaterSystemSimulationManager
        
        # 创建仿真管理器
        manager = WaterSystemSimulationManager()
        
        # 创建测试渠道
        channel_config = {
            'length': 4000.0,
            'slope': 0.0003,
            'roughness': 0.025,
            'bottom_width': 12.0,
            'side_slope': 1.5
        }
        
        channel = manager.create_water_object('channel', 'test_channel', channel_config)
        
        print("✅ WaterSystemSimulationManager 创建成功")
        
        # 测试功能列表
        capabilities = {
            '多方法仿真': [],
            '参数优化': False,
            '敏感性分析': False,
            '实时校正': False,
            '数字孪生': False,
            '多情景仿真': False,
            '水网联立求解': False
        }
        
        # 1. 测试多方法仿真支持
        if hasattr(manager, 'configure_simulation_method'):
            available_methods = [
                'saint_venant_full', 'muskingum_model', 'idz_model',
                'storage_routing', 'water_balance'
            ]
            
            for method in available_methods:
                try:
                    success = manager.configure_simulation_method('test_channel', method)
                    if success:
                        capabilities['多方法仿真'].append(method)
                except:
                    pass
        
        # 2. 测试参数优化
        if hasattr(manager, 'parameter_optimization'):
            capabilities['参数优化'] = True
        
        # 3. 测试敏感性分析
        if hasattr(manager, 'sensitivity_analysis'):
            capabilities['敏感性分析'] = True
        
        # 4. 测试实时校正
        if hasattr(manager, 'real_time_calibration'):
            capabilities['实时校正'] = True
        
        # 5. 测试数字孪生
        if hasattr(manager, 'create_digital_twin'):
            capabilities['数字孪生'] = True
        
        # 6. 测试多情景仿真
        if hasattr(manager, 'simulate_scenarios'):
            capabilities['多情景仿真'] = True
        
        # 7. 测试水网联立求解
        if hasattr(manager, 'simulate_water_network'):
            capabilities['水网联立求解'] = True
        
        return capabilities
        
    except Exception as e:
        print(f"❌ WaterSystemSimulationManager 测试失败: {e}")
        return {}

def compare_capabilities(channel_caps, manager_caps):
    """对比两个类的功能"""
    
    print("\n📊 功能对比分析")
    print("=" * 60)
    
    all_features = set(channel_caps.keys()) | set(manager_caps.keys())
    
    comparison_table = []
    for feature in sorted(all_features):
        channel_support = channel_caps.get(feature, False)
        manager_support = manager_caps.get(feature, False)
        
        # 特殊处理多方法仿真
        if feature == '多方法仿真':
            channel_count = len(channel_support) if isinstance(channel_support, list) else 0
            manager_count = len(manager_support) if isinstance(manager_support, list) else 0
            
            channel_status = f"✅ {channel_count}种" if channel_count > 0 else "❌ 不支持"
            manager_status = f"✅ {manager_count}种" if manager_count > 0 else "❌ 不支持"
            
            gap_analysis = "功能对等" if channel_count > 0 and manager_count > 0 else \
                          "Channel领先" if channel_count > manager_count else \
                          "Manager领先" if manager_count > channel_count else "都需完善"
        else:
            channel_status = "✅ 支持" if channel_support else "❌ 不支持"
            manager_status = "✅ 支持" if manager_support else "❌ 不支持"
            
            gap_analysis = "功能对等" if channel_support == manager_support else \
                          "Channel领先" if channel_support and not manager_support else \
                          "Manager领先" if manager_support and not channel_support else "都需完善"
        
        comparison_table.append({
            'feature': feature,
            'channel': channel_status,
            'manager': manager_status,
            'gap': gap_analysis
        })
    
    # 打印对比表格
    print(f"{'功能领域':<15} {'ChannelObject':<15} {'WaterSystemManager':<20} {'差距分析':<15}")
    print("-" * 75)
    
    for row in comparison_table:
        print(f"{row['feature']:<15} {row['channel']:<15} {row['manager']:<20} {row['gap']:<15}")
    
    return comparison_table

def generate_improvement_recommendations(comparison_table):
    """生成改进建议"""
    
    print("\n💡 改进建议")
    print("=" * 40)
    
    channel_needs_improvement = []
    manager_needs_improvement = []
    
    for row in comparison_table:
        feature = row['feature']
        gap = row['gap']
        
        if gap == "Manager领先":
            channel_needs_improvement.append(feature)
        elif gap == "Channel领先":
            manager_needs_improvement.append(feature)
    
    if channel_needs_improvement:
        print("🔧 ChannelObject 需要完善的功能:")
        for feature in channel_needs_improvement:
            print(f"   • {feature}")
    
    if manager_needs_improvement:
        print("🔧 WaterSystemSimulationManager 需要完善的功能:")
        for feature in manager_needs_improvement:
            print(f"   • {feature}")
    
    if not channel_needs_improvement and not manager_needs_improvement:
        print("🎉 两个类的功能已经基本对等!")
        
    # 具体建议
    print("\n📋 具体实现建议:")
    
    if '多方法仿真' in channel_needs_improvement:
        print("   • ChannelObject: 添加 configure_simulation_method() 接口")
    
    if '多方法仿真' in manager_needs_improvement:
        print("   • WaterSystemManager: 完善 configure_simulation_method() 实现")
    
    if '水网联立求解' in channel_needs_improvement:
        print("   • ChannelObject: 添加 solve_network_coupled() 方法")
        
    if '参数优化' in manager_needs_improvement:
        print("   • WaterSystemManager: 完善 parameter_optimization() 实现")

def main():
    """主函数"""
    
    print("🚀 ChannelObject vs WaterSystemSimulationManager 功能对比")
    print("=" * 70)
    
    # 测试两个类的功能
    print("\n第一阶段: 功能测试")
    channel_capabilities = test_channel_object_capabilities()
    manager_capabilities = test_water_system_manager_capabilities()
    
    if not channel_capabilities or not manager_capabilities:
        print("❌ 功能测试失败，无法进行对比")
        return False
    
    # 对比功能
    print("\n第二阶段: 功能对比")
    comparison_table = compare_capabilities(channel_capabilities, manager_capabilities)
    
    # 生成改进建议
    print("\n第三阶段: 改进建议")
    generate_improvement_recommendations(comparison_table)
    
    # 总结
    print("\n📝 对比总结")
    print("=" * 40)
    
    total_features = len(comparison_table)
    equal_features = len([row for row in comparison_table if row['gap'] == '功能对等'])
    
    equality_percentage = (equal_features / total_features) * 100
    
    print(f"功能对等度: {equal_features}/{total_features} ({equality_percentage:.1f}%)")
    
    if equality_percentage >= 80:
        print("🎉 两个类的功能基本对等，满足用户需求!")
    elif equality_percentage >= 60:
        print("👍 两个类的功能大部分对等，还有少量差距")
    else:
        print("⚠️ 两个类存在较大功能差距，需要进一步完善")
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)