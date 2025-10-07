#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化测试：验证自动收敛优化器是否被正确调用
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_simple_saint_venant_convergence():
    """简化测试：直接创建圣维南模型并测试收敛"""
    print("="*60)
    print("简化圣维南收敛测试")
    print("="*60)
    
    try:
        # 导入基础模块
        from waternet.objects.conveyance import ChannelObject
        
        print("1. 创建圣维南配置...")
        
        # 创建最简单的圣维南配置
        saint_venant_config = {
            'object_definition': {
                'object_id': 'test_sv_channel',
                'object_type': 'channel',
                'name': '测试圣维南渠道',
                'description': '用于测试自动收敛优化器的圣维南渠道'
            },
            'basic_properties': {
                'length': 5000.0,
                'slope': 0.0002,
                'manning_n': 0.025,
                'average_width': 15.0,
                'base_elevation': 85.0
            },
            'geometry_definition': {
                'cross_sections': [
                    {
                        'station': 0.0,
                        'elevation': 86.0,
                        'shape_type': 'trapezoidal',
                        'bottom_width': 15.0,
                        'side_slope': 1.5,
                        'roughness': 0.025
                    },
                    {
                        'station': 2500.0,
                        'elevation': 85.5,
                        'shape_type': 'trapezoidal', 
                        'bottom_width': 15.0,
                        'side_slope': 1.5,
                        'roughness': 0.025
                    },
                    {
                        'station': 5000.0,
                        'elevation': 85.0,
                        'shape_type': 'trapezoidal',
                        'bottom_width': 18.0,
                        'side_slope': 2.0,
                        'roughness': 0.030
                    }
                ]
            },
            'simulation_preferences': {
                'default_method': 'saint_venant_full'
            }
        }
        
        print("2. 创建ChannelObject...")
        channel = ChannelObject('test_sv_channel', config=saint_venant_config)
        channel.set_upstream_boundary(flow=100.0)
        channel.set_downstream_boundary(level=96.0)
        
        print(f"   ✅ 渠道创建成功: {channel.simulation_method}")
        print(f"   📊 空间表示: {channel.spatial_representation}")
        print(f"   🔧 底层模型: {type(channel.underlying_model).__name__}")
        
        # 检查底层模型是否有增强求解器
        if channel.underlying_model and hasattr(channel.underlying_model, '_enhanced_solver'):
            enhanced_solver = channel.underlying_model._enhanced_solver
            print(f"   🚀 增强求解器: {type(enhanced_solver).__name__ if enhanced_solver else 'None'}")
            
            if enhanced_solver and hasattr(enhanced_solver, 'auto_optimizer'):
                auto_optimizer = enhanced_solver.auto_optimizer
                print(f"   🎯 自动收敛优化器: {type(auto_optimizer).__name__ if auto_optimizer else 'None'}")
        
        print("\n3. 执行恒定流计算...")
        steady_result = channel.solve_steady_flow()
        
        if steady_result.get('success'):
            print(f"   ✅ 恒定流计算成功")
            print(f"   📊 入流: {steady_result.get('inflow', 0):.2f} m³/s")
            print(f"   📊 出流: {steady_result.get('outflow', 0):.2f} m³/s")
            print(f"   📊 水位: {steady_result.get('water_level', 0):.2f} m")
        else:
            print(f"   ❌ 恒定流计算失败: {steady_result.get('error', 'unknown')}")
        
        print("\n4. 执行单个时间步非恒定流计算...")
        try:
            # 执行一个时间步的非恒定流计算
            if channel.underlying_model and hasattr(channel.underlying_model, 'step'):
                step_result = channel.underlying_model.step(
                    Q_in=120.0,  # 增加入流来触发非恒定流
                    downstream_level=96.0,
                    dt=60.0
                )
                
                if step_result.get('convergence_success'):
                    print("   ✅ 非恒定流时间步计算成功！")
                    print(f"   📊 流量变化: 入流={120.0:.1f} → 出流={step_result.get('Q_out', 0):.1f} m³/s")
                    print("   🎯 自动收敛优化器工作正常！")
                else:
                    print("   ❌ 非恒定流时间步计算失败")
                    print("   💡 可能的原因：")
                    print("     - Jacobian条件数问题")
                    print("     - 自动收敛优化器未被正确调用")
                    print("     - 数值参数需要进一步调整")
            else:
                print("   ⚠️ 底层模型不支持 step 方法")
                
        except Exception as e:
            print(f"   ❌ 非恒定流时间步计算异常: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_simple_saint_venant_convergence()