#!/usr/bin/env python3
"""
调试纵剖面问题的简单测试脚本
"""

import sys
from pathlib import Path

# 添加路径
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

from waternet.objects.conveyance import ChannelObject

def debug_profile_issue():
    """调试纵剖面生成问题"""
    print("🔍 调试纵剖面生成问题")
    print("=" * 50)
    
    # 创建一个简单的渠道配置，使用合理的底高程
    channel_config = {
        'simulation_method': 'saint_venant_simplified',
        'basic_properties': {
            'length': 5000.0,
            'slope': 0.0003,
            'roughness': 0.030,
            'bottom_width': 15.0,
            'side_slope': 2.0
        },
        'cross_sections': [
            {
                'station': 0.0,
                'bottom_elevation': 100.0,  # 上游底高程：100m
                'bottom_width': 15.0,
                'side_slope': 2.0,
                'roughness': 0.030
            },
            {
                'station': 2500.0,
                'bottom_elevation': 98.5,   # 中间断面：98.5m
                'bottom_width': 15.0,
                'side_slope': 2.0,
                'roughness': 0.030
            },
            {
                'station': 5000.0,
                'bottom_elevation': 97.0,   # 下游底高程：97m（坡降：3m/5000m = 0.0006）
                'bottom_width': 15.0,
                'side_slope': 2.0,
                'roughness': 0.030
            }
        ]
    }
    
    # 创建渠道对象
    channel = ChannelObject('debug_channel', config=channel_config)
    channel.initialize()
    
    print(f"✅ 渠道对象创建成功: {channel.object_id}")
    
    # 设置边界条件
    print("\n🔧 设置边界条件:")
    upstream_flow = 120.0  # 上游流量 120 m³/s
    downstream_level = 98.5  # 下游水位 98.5m（底高程97m + 1.5m水深）
    
    print(f"   上游流量: {upstream_flow} m³/s")
    print(f"   下游水位: {downstream_level} m")
    
    channel.set_upstream_boundary(flow=upstream_flow)
    channel.set_downstream_boundary(level=downstream_level)
    
    # 检查断面数据
    print("\n📊 检查断面配置:")
    sections = channel._prepare_sections_data()
    
    for i, section in enumerate(sections):
        print(f"   断面 {i+1}: 里程={section['mileage']}m, 底高程={section['elevation']}m")
    
    # 调用_compute_steady_flow_profile方法
    print("\n🧮 执行恒定流水面线计算:")
    try:
        profile_data = channel._compute_steady_flow_profile(sections, upstream_flow, downstream_level)
        
        print("   💧 计算结果:")
        distances = profile_data['distances']
        bed_elevations = profile_data['bed_elevations']
        water_levels = profile_data['water_levels']
        
        for i, (dist, bed, water) in enumerate(zip(distances, bed_elevations, water_levels)):
            water_depth = water - bed
            print(f"     断面 {i+1}: 里程={dist}m, 底高程={bed:.2f}m, 水位={water:.2f}m, 水深={water_depth:.2f}m")
        
        # 检查异常值
        max_water = max(water_levels)
        min_water = min(water_levels)
        max_bed = max(bed_elevations)
        min_bed = min(bed_elevations)
        
        print(f"\n   📈 数值范围检查:")
        print(f"     水位范围: {min_water:.2f} ~ {max_water:.2f} m")
        print(f"     底高程范围: {min_bed:.2f} ~ {max_bed:.2f} m")
        
        if max_water > 1000 or min_water < 0:
            print("   ⚠️ 发现异常水位数值！")
            
            # 检查计算逻辑
            print("   🔍 详细调试计算过程:")
            current_level = downstream_level
            print(f"     初始下游水位: {current_level:.2f}m")
            
            for i in range(1, len(sections)):
                section = sections[i]
                prev_section = sections[i-1]
                
                dx = abs(section['mileage'] - prev_section['mileage'])
                roughness = section['roughness']
                
                # 计算水深和水力半径
                h = current_level - section['elevation']
                h = max(0.1, h)  # 确保最小水深
                
                print(f"     断面 {i+1}: 水深={h:.2f}m (水位{current_level:.2f} - 底高程{section['elevation']:.2f})")
                
                # 梯形断面水力计算
                bottom_width = section.get('bottom_width', 15.0)
                side_slope = section.get('side_slope', 2.0)
                A = h * (bottom_width + side_slope * h)
                P = bottom_width + 2 * h * (1 + side_slope**2)**0.5
                R = A / P if P > 0 else 0
                
                print(f"       过水面积A={A:.2f}m², 湿周P={P:.2f}m, 水力半径R={R:.2f}m")
                
                # 基于曼宁公式计算所需坡度
                if A > 0 and R > 0:
                    V = upstream_flow / A
                    friction_slope = (roughness * V / (R**(2/3)))**2
                    print(f"       流速V={V:.2f}m/s, 摩阻坡度={friction_slope:.6f}")
                else:
                    friction_slope = 0.001
                    print(f"       使用默认摩阻坡度={friction_slope:.6f}")
                
                # 计算水头损失
                head_loss = friction_slope * dx
                print(f"       距离dx={dx}m, 水头损失={head_loss:.4f}m")
                
                # 更新水位（向上游推算）
                current_level += head_loss
                print(f"       更新后水位: {current_level:.2f}m")
            
        else:
            print("   ✅ 水位数值正常")
        
        return profile_data
        
    except Exception as e:
        print(f"   ❌ 计算失败: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    debug_profile_issue()