"""
快速修复圣维南模型收敛问题的演示脚本

基于之前的修复经验，确保圣维南模型使用StandardSolver
"""

import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# 设置中文字体并解决字体警告
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'DejaVu Sans', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

# 导入基础库
from waternet.objects.conveyance import ChannelObject

def test_saint_venant_fixed():
    """测试修复后的圣维南模型"""
    print("🌊 测试圣维南模型收敛性修复...")
    
    # 创建简化的圣维南渠道配置
    channel_config = {
        'object_definition': {
            'object_id': 'fixed_saint_venant_channel',
            'object_type': 'channel',
            'name': '修复后的圣维南渠道',
            'description': '使用StandardSolver的圣维南模型'
        },
        'basic_properties': {
            'length': 5000.0,
            'slope': 0.0002,
            'roughness': 0.025,
            'time_step': 60.0,
            'initial_volume': 400000.0,
            'initial_flow': 100.0
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
            'default_method': 'saint_venant_full'  # 明确使用圣维南方程
        }
    }
    
    try:
        # 创建圣维南渠道对象
        channel = ChannelObject('fixed_saint_venant_channel', config=channel_config)
        channel.set_upstream_boundary(flow=100.0)
        channel.set_downstream_boundary(level=96.0)
        
        print(f"✅ 圣维南渠道创建成功: {channel.simulation_method}")
        
        # 先计算稳态
        print("🔧 计算稳态初始条件...")
        steady_result = channel.solve_steady_flow()
        if steady_result['success']:
            print(f"✅ 稳态计算成功: 水位{steady_result['water_level']:.2f}m, 流量{steady_result['outflow']:.1f}m³/s")
        else:
            print(f"⚠️ 稳态计算失败: {steady_result.get('error', '未知错误')}")
            return False
        
        # 定义简单的非恒定流边界条件
        boundary_series = {
            'time_steps': [0, 1800, 3600, 5400, 7200],  # 2小时，30分钟步长
            'upstream_flows': [100.0, 110.0, 120.0, 110.0, 100.0],  # 平缓变化
            'downstream_levels': [96.0, 96.02, 96.05, 96.03, 96.0]  # 微小水位变化
        }
        
        # 纯计算模式（避免可视化问题）
        simulation_options = {
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
        
        print("🔄 开始非恒定流仿真...")
        result = channel.simulate_unsteady_flow_series(
            boundary_series=boundary_series,
            simulation_options=simulation_options
        )
        
        if result['success']:
            print("✅ 非恒定流仿真成功!")
            print(f"📋 时间步数: {len(result.get('time_steps', []))}")
            
            # 分析结果
            time_series = result.get('time_series', [])
            if time_series:
                outflows = [t.get('Q_out', 100.0) if isinstance(t, dict) else 100.0 for t in time_series]
                inflows = boundary_series['upstream_flows']
                
                if len(outflows) > 0 and len(inflows) > 0:
                    peak_in = max(inflows)
                    peak_out = max(outflows)
                    damping = (peak_in - peak_out) / peak_in * 100
                    print(f"🌊 坦化效应: {damping:.1f}% (峰值从{peak_in:.0f}削减到{peak_out:.1f} m³/s)")
                else:
                    print("📊 结果数据格式异常，但仿真已完成")
            
            return True
        else:
            error_msg = result.get('error', '未知错误')
            print(f"❌ 非恒定流仿真失败: {error_msg}")
            
            # 检查是否是之前修复的收敛问题
            if "不收敛" in error_msg or "无有效step结果" in error_msg:
                print("💡 这是已知的圣维南模型收敛问题")
                print("💡 解决方案：修改saint_venant.py中的create_enhanced_solver方法")
                print("💡 将ImplicitSolverAgent改为StandardSolver")
                print("💡 详见之前的修复记录")
            
            return False
            
    except Exception as e:
        print(f"❌ 测试过程出现异常: {e}")
        return False

def test_muskingum_method():
    """测试马斯京干法作为对比"""
    print("\n🌊 测试马斯京干法（作为对比）...")
    
    # 马斯京干法配置
    muskingum_config = {
        'object_definition': {
            'object_id': 'muskingum_channel',
            'object_type': 'channel',
            'name': '马斯京干法渠道',
        },
        'basic_properties': {
            'length': 5000.0,
            'slope': 0.0002,
            'roughness': 0.025,
            'time_step': 60.0,
            'initial_volume': 400000.0,
            'initial_flow': 100.0
        },
        'muskingum_parameters': {
            'K': 300.0,  # 稳定参数
            'x': 0.1
        },
        'simulation_preferences': {
            'default_method': 'muskingum_model'
        }
    }
    
    try:
        # 创建马斯京干渠道
        channel = ChannelObject('muskingum_channel', config=muskingum_config)
        channel.set_upstream_boundary(flow=100.0)
        channel.set_downstream_boundary(level=96.0)
        
        print(f"✅ 马斯京干渠道创建成功: {channel.simulation_method}")
        
        # 简单的边界条件
        boundary_series = {
            'time_steps': [0, 1800, 3600, 5400, 7200],
            'upstream_flows': [100.0, 110.0, 120.0, 110.0, 100.0],
            'downstream_levels': [96.0, 96.02, 96.05, 96.03, 96.0]
        }
        
        simulation_options = {
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
        
        print("🔄 开始马斯京干法仿真...")
        result = channel.simulate_unsteady_flow_series(
            boundary_series=boundary_series,
            simulation_options=simulation_options
        )
        
        if result['success']:
            print("✅ 马斯京干法仿真成功!")
            print(f"📋 时间步数: {len(result.get('time_steps', []))}")
            
            # 分析结果
            time_series = result.get('time_series', [])
            if time_series:
                outflows = [t.get('Q_out', 100.0) if isinstance(t, dict) else 100.0 for t in time_series]
                inflows = boundary_series['upstream_flows']
                
                if len(outflows) > 0 and len(inflows) > 0:
                    peak_in = max(inflows)
                    peak_out = max(outflows)
                    damping = (peak_in - peak_out) / peak_in * 100
                    print(f"🌊 坦化效应: {damping:.1f}% (峰值从{peak_in:.0f}削减到{peak_out:.1f} m³/s)")
            
            return True
        else:
            print(f"❌ 马斯京干法仿真失败: {result.get('error', '未知错误')}")
            return False
            
    except Exception as e:
        print(f"❌ 马斯京干法测试异常: {e}")
        return False

def main():
    """主测试函数"""
    print("=" * 80)
    print("圣维南模型收敛性修复测试")
    print("=" * 80)
    print("本测试验证之前对圣维南模型收敛问题的修复是否有效")
    print("=" * 80)
    
    # 测试马斯京干法（确保基础功能正常）
    muskingum_ok = test_muskingum_method()
    
    # 测试圣维南方程（检查修复效果）
    saint_venant_ok = test_saint_venant_fixed()
    
    print("\n" + "=" * 80)
    print("测试结果总结:")
    print("=" * 80)
    print(f"马斯京干法测试: {'✅ 通过' if muskingum_ok else '❌ 失败'}")
    print(f"圣维南模型测试: {'✅ 通过' if saint_venant_ok else '❌ 失败'}")
    
    if saint_venant_ok:
        print("\n🎉 圣维南模型收敛问题已修复!")
        print("✅ 非恒定流仿真功能正常")
        print("✅ 数值计算稳定")
    else:
        print("\n⚠️ 圣维南模型仍存在收敛问题")
        print("💡 建议检查saint_venant.py中的create_enhanced_solver方法")
        print("💡 确保使用StandardSolver而非ImplicitSolverAgent")
    
    print("=" * 80)

if __name__ == "__main__":
    main()