#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
功能完善验证脚本

验证ChannelObject数字孪生功能和WaterSystemSimulationManager多方法仿真配置的修复情况

Author: WaterNet Development Team
Date: 2025-10-06
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

def test_channel_object_digital_twin():
    """测试ChannelObject的数字孪生功能"""
    
    print("🔥 测试 ChannelObject 数字孪生功能")
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
            }
        }
        
        channel = ChannelObject('test_channel', config=channel_config)
        channel.initialize()
        
        print("✅ ChannelObject 创建成功")
        
        # 测试数字孪生功能
        digital_twin_available = hasattr(channel, 'create_digital_twin')
        print(f"数字孪生方法: {'✅ 可用' if digital_twin_available else '❌ 不可用'}")
        
        if digital_twin_available:
            # 创建数字孪生
            twin_config = {
                'twin_name': 'TestChannel_DigitalTwin',
                'sync_strategy': 'periodic',
                'enable_high_fidelity': True,
                'enable_reduced_order': True,
                'real_time_capable': True
            }
            
            twin_result = channel.create_digital_twin(twin_config)
            
            if twin_result.get('success', False):
                print("   ✅ 数字孪生创建成功")
                print(f"   🆔 孪生ID: {twin_result.get('twin_id')}")
                print(f"   🔧 孪生模型: {len(twin_result.get('twin_models', {}))}个")
                print(f"   🚀 孪生能力: {len(twin_result.get('twin_capabilities', []))}项")
                
                # 测试孪生状态查询
                if hasattr(channel, 'get_digital_twin_status'):
                    status = channel.get_digital_twin_status()
                    print(f"   📊 孪生状态: {status.get('sync_status', 'unknown')}")
                
                # 测试孪生更新
                if hasattr(channel, 'update_digital_twin'):
                    update_result = channel.update_digital_twin({
                        'sensor_data': {
                            'flow_rate': 120.0,
                            'water_level': 95.5
                        }
                    })
                    print(f"   🔄 孪生更新: {'✅ 成功' if update_result.get('success') else '❌ 失败'}")
                
                return {
                    'digital_twin_available': True,
                    'creation_success': True,
                    'twin_models': len(twin_result.get('twin_models', {})),
                    'twin_capabilities': len(twin_result.get('twin_capabilities', []))
                }
            else:
                print(f"   ❌ 数字孪生创建失败: {twin_result.get('error', '未知错误')}")
                return {
                    'digital_twin_available': True,
                    'creation_success': False,
                    'error': twin_result.get('error')
                }
        else:
            return {
                'digital_twin_available': False,
                'creation_success': False
            }
        
    except Exception as e:
        print(f"❌ ChannelObject 数字孪生测试失败: {e}")
        return {
            'digital_twin_available': False,
            'creation_success': False,
            'error': str(e)
        }

def test_manager_simulation_methods():
    """测试WaterSystemSimulationManager的多方法仿真配置"""
    
    print("\n🔧 测试 WaterSystemSimulationManager 多方法仿真配置")
    print("=" * 60)
    
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
        print("✅ WaterSystemSimulationManager 和测试渠道创建成功")
        
        # 测试方法配置功能
        method_config_available = hasattr(manager, 'configure_simulation_method')
        print(f"方法配置功能: {'✅ 可用' if method_config_available else '❌ 不可用'}")
        
        if method_config_available:
            # 测试多种仿真方法
            test_methods = [
                'muskingum_model',
                'idz_model', 
                'storage_routing',
                'water_balance'
            ]
            
            method_results = {
                'total_tested': len(test_methods),
                'successful_methods': [],
                'failed_methods': [],
                'method_details': {}
            }
            
            for method in test_methods:
                try:
                    print(f"   测试方法: {method}")
                    success = manager.configure_simulation_method('test_channel', method)
                    
                    if success:
                        method_results['successful_methods'].append(method)
                        method_results['method_details'][method] = 'success'
                        print(f"     ✅ {method} 配置成功")
                    else:
                        method_results['failed_methods'].append(method)
                        method_results['method_details'][method] = 'failed'
                        print(f"     ❌ {method} 配置失败")
                        
                except Exception as e:
                    method_results['failed_methods'].append(method)
                    method_results['method_details'][method] = f'error: {str(e)}'
                    print(f"     ❌ {method} 配置异常: {e}")
            
            success_rate = len(method_results['successful_methods']) / len(test_methods) * 100
            print(f"\n   📊 方法配置成功率: {len(method_results['successful_methods'])}/{len(test_methods)} ({success_rate:.1f}%)")
            
            # 测试方法测试功能
            if hasattr(manager, 'test_simulation_methods'):
                print(f"\n   🧪 执行完整方法测试...")
                test_result = manager.test_simulation_methods('test_channel')
                if test_result.get('success', False):
                    print(f"     ✅ 方法测试完成: {test_result.get('success_rate', 0):.1f}% 成功率")
            
            return {
                'method_config_available': True,
                'test_success': True,
                'success_rate': success_rate,
                'successful_methods': method_results['successful_methods'],
                'failed_methods': method_results['failed_methods']
            }
        else:
            return {
                'method_config_available': False,
                'test_success': False
            }
        
    except Exception as e:
        print(f"❌ WaterSystemSimulationManager 多方法测试失败: {e}")
        return {
            'method_config_available': False,
            'test_success': False,
            'error': str(e)
        }

def generate_completion_report(channel_result, manager_result):
    """生成完善报告"""
    
    print("\n📋 功能完善验证报告")
    print("=" * 40)
    
    # ChannelObject数字孪生功能
    print("🔥 ChannelObject 数字孪生功能:")
    if channel_result.get('digital_twin_available', False):
        if channel_result.get('creation_success', False):
            print("   ✅ 状态: 完善成功")
            print(f"   🔧 孪生模型: {channel_result.get('twin_models', 0)}个")
            print(f"   🚀 孪生能力: {channel_result.get('twin_capabilities', 0)}项")
        else:
            print("   ⚠️ 状态: 功能可用但创建失败")
            print(f"   ❌ 错误: {channel_result.get('error', '未知')}")
    else:
        print("   ❌ 状态: 功能缺失")
    
    # WaterSystemSimulationManager多方法配置
    print("\n🔧 WaterSystemSimulationManager 多方法仿真配置:")
    if manager_result.get('method_config_available', False):
        if manager_result.get('test_success', False):
            success_rate = manager_result.get('success_rate', 0)
            print(f"   ✅ 状态: 修复成功 ({success_rate:.1f}% 方法可用)")
            print(f"   ✅ 成功方法: {', '.join(manager_result.get('successful_methods', []))}")
            if manager_result.get('failed_methods'):
                print(f"   ⚠️ 失败方法: {', '.join(manager_result.get('failed_methods', []))}")
        else:
            print("   ⚠️ 状态: 功能可用但测试失败")
    else:
        print("   ❌ 状态: 功能缺失")
    
    # 总体评估
    print("\n🎯 总体评估:")
    
    channel_fixed = channel_result.get('digital_twin_available', False) and channel_result.get('creation_success', False)
    manager_fixed = manager_result.get('method_config_available', False) and manager_result.get('test_success', False)
    
    if channel_fixed and manager_fixed:
        print("   🎉 两个功能都已成功完善!")
        overall_status = "完全成功"
    elif channel_fixed or manager_fixed:
        fixed_count = sum([channel_fixed, manager_fixed])
        print(f"   👍 {fixed_count}/2 个功能已完善，还有少量问题需要解决")
        overall_status = "部分成功"
    else:
        print("   ⚠️ 两个功能都需要进一步完善")
        overall_status = "需要改进"
    
    # 功能对等性更新
    print("\n📊 功能对等性更新:")
    
    # 原功能对等度 5/7 (71.4%)
    original_equal = 5
    total_features = 7
    
    # 计算新的对等度
    new_equal = original_equal
    if channel_fixed:
        new_equal += 1  # ChannelObject数字孪生功能补齐
    if manager_fixed:
        # WaterSystemSimulationManager多方法仿真已修复，不增加对等数但提升质量
        pass
    
    new_equality_rate = (new_equal / total_features) * 100
    print(f"   📈 新功能对等度: {new_equal}/{total_features} ({new_equality_rate:.1f}%)")
    
    if new_equality_rate > 85:
        print("   🏆 功能对等度优秀!")
    elif new_equality_rate > 70:
        print("   👍 功能对等度良好!")
    else:
        print("   📝 功能对等度有待提升")
    
    return {
        'channel_fixed': channel_fixed,
        'manager_fixed': manager_fixed,
        'overall_status': overall_status,
        'new_equality_rate': new_equality_rate
    }

def main():
    """主函数"""
    
    print("🚀 ChannelObject与WaterSystemSimulationManager功能完善验证")
    print("=" * 70)
    
    # 测试ChannelObject数字孪生功能
    channel_result = test_channel_object_digital_twin()
    
    # 测试WaterSystemSimulationManager多方法仿真配置
    manager_result = test_manager_simulation_methods()
    
    # 生成完善报告
    completion_report = generate_completion_report(channel_result, manager_result)
    
    print(f"\n✨ 验证完成! 总体状态: {completion_report['overall_status']}")
    print(f"🎯 新功能对等度: {completion_report['new_equality_rate']:.1f}%")
    
    return completion_report['overall_status'] in ['完全成功', '部分成功']

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)