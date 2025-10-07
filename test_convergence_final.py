#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
专门测试非恒定流收敛性的脚本
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from waternet.models.saint_venant import SaintVenantModel
from waternet.objects.conveyance import ChannelObject
from waternet.models.lumped_models import MuskingumModel
from waternet.enums import SimulationMethod, SpatialRepresentation
import time

def test_saint_venant_convergence():
    """测试圣维南模型的非恒定流收敛性"""
    print("=== 圣维南非恒定流收敛性测试 ===")
    
    # 创建标准断面
    sections = [
        {
            'name': 'upstream', 
            'mileage': 0, 
            'elevation': 100.0, 
            'roughness': 0.035,
            'area_func': lambda h: max(0.1, (h - 100.0) * 10.0) if h > 100.0 else 0.1,
            'top_width_func': lambda h: 10.0
        },
        {
            'name': 'middle', 
            'mileage': 0.5, 
            'elevation': 99.5, 
            'roughness': 0.035,
            'area_func': lambda h: max(0.1, (h - 99.5) * 10.0) if h > 99.5 else 0.1,
            'top_width_func': lambda h: 10.0
        },
        {
            'name': 'downstream', 
            'mileage': 1.0, 
            'elevation': 99.0, 
            'roughness': 0.035,
            'area_func': lambda h: max(0.1, (h - 99.0) * 10.0) if h > 99.0 else 0.1,
            'top_width_func': lambda h: 10.0
        }
    ]
    
    # 创建圣维南模型
    sv_model = SaintVenantModel('convergence_test', 'upstream', 'downstream', sections)
    
    # 测试多个时间步的收敛性
    test_cases = [
        {"Q_in": 100.0, "H_down": 96.0, "dt": 60.0},
        {"Q_in": 120.0, "H_down": 96.2, "dt": 60.0},
        {"Q_in": 80.0, "H_down": 95.8, "dt": 60.0},
        {"Q_in": 150.0, "H_down": 96.5, "dt": 60.0},
        {"Q_in": 60.0, "H_down": 95.5, "dt": 60.0}
    ]
    
    success_count = 0
    total_time = 0
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n--- 测试案例 {i} ---")
        print(f"输入: Q_in={case['Q_in']}, H_down={case['H_down']}, dt={case['dt']}")
        
        try:
            start_time = time.time()
            result = sv_model.step(Q_in=case['Q_in'], 
                                 downstream_level=case['H_down'], 
                                 dt=case['dt'])
            calc_time = time.time() - start_time
            total_time += calc_time
            
            print(f"✅ 收敛成功!")
            print(f"   Q_out: {result.get('Q_out', 'N/A'):.2f} m³/s")
            print(f"   H_out: {result.get('H_out', 'N/A'):.2f} m") 
            print(f"   V: {result.get('V', 'N/A'):.0f} m³")
            print(f"   计算时间: {calc_time:.3f}s")
            
            success_count += 1
            
        except Exception as e:
            print(f"❌ 收敛失败: {e}")
    
    print(f"\n=== 收敛性统计 ===")
    print(f"成功案例: {success_count}/{len(test_cases)}")
    print(f"成功率: {success_count/len(test_cases)*100:.1f}%")
    print(f"平均计算时间: {total_time/len(test_cases):.3f}s")
    
    return success_count == len(test_cases)

def test_channel_object_convergence():
    """测试渠道对象的非恒定流收敛性"""
    print("\n=== 渠道对象非恒定流收敛性测试 ===")
    
    try:
        # 创建渠道对象，使用圣维南方法
        channel = ChannelObject(
            name="test_sv_channel",
            simulation_method=SimulationMethod.SAINT_VENANT_FULL,
            spatial_representation=SpatialRepresentation.DISTRIBUTED
        )
        
        # 设置几何参数
        channel.set_geometry(
            length=1000.0,
            width=10.0,
            bottom_elevation=99.0,
            roughness=0.035,
            slope=0.001
        )
        
        # 初始化
        if not channel.initialize():
            print("❌ 渠道对象初始化失败")
            return False
        
        print("✅ 渠道对象初始化成功")
        
        # 设置边界条件
        channel.set_upstream_boundary(flow=100.0)
        channel.set_downstream_boundary(level=96.0)
        
        # 测试恒定流计算
        steady_result = channel.solve_steady_flow()
        if steady_result and steady_result.get('success', False):
            print(f"✅ 恒定流计算成功: 出流={steady_result.get('outflow', 'N/A'):.2f}")
        else:
            print("❌ 恒定流计算失败")
        
        # 测试简单的非恒定流序列
        boundary_series = {
            'time_steps': [0, 300, 600, 900],
            'upstream_flows': [100.0, 120.0, 110.0, 95.0],
            'downstream_levels': [96.0, 96.1, 96.05, 95.95]
        }
        
        # 纯计算模式
        options = {
            'output_sections': ['upstream', 'downstream'],
            'plot_options': {
                'single_scenario': False,
                'multi_scenario': False,
                'inlet_outlet_only': False,
                'all_sections': False
            },
            'compute_only': True,
            'method_comparison': False
        }
        
        print("开始非恒定流序列计算...")
        start_time = time.time()
        
        result = channel.simulate_unsteady_flow_series(
            boundary_series=boundary_series,
            simulation_options=options
        )
        
        calc_time = time.time() - start_time
        
        if result and result.get('success', False):
            print(f"✅ 非恒定流序列计算成功!")
            print(f"   时间步数: {len(result.get('time_steps', []))}")
            print(f"   方法: {result.get('method', 'unknown')}")
            print(f"   计算时间: {calc_time:.3f}s")
            return True
        else:
            error_msg = result.get('error', '未知错误') if result else '无结果'
            print(f"❌ 非恒定流序列计算失败: {error_msg}")
            return False
            
    except Exception as e:
        print(f"❌ 渠道对象测试异常: {e}")
        return False

def main():
    """主测试函数"""
    print("开始完整的非恒定流收敛性验证...")
    
    # 测试1: 直接圣维南模型
    sv_success = test_saint_venant_convergence()
    
    # 测试2: 渠道对象非恒定流
    channel_success = test_channel_object_convergence()
    
    print(f"\n{'='*50}")
    print("🎯 最终收敛性验证结果:")
    print(f"  圣维南模型直接测试: {'✅ 通过' if sv_success else '❌ 失败'}")
    print(f"  渠道对象非恒定流测试: {'✅ 通过' if channel_success else '❌ 失败'}")
    
    if sv_success and channel_success:
        print("🎉 非恒定流收敛性验证完全成功!")
        return True
    else:
        print("⚠️ 部分测试未通过，需要进一步优化")
        return False

if __name__ == "__main__":
    success = main()
    print(f"\n程序退出，成功: {success}")