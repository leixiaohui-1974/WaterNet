#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
横断面图功能简化测试
"""

import sys
import os
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def simple_cross_section_test():
    """简化的横断面图测试"""
    try:
        from waternet.utils.water_surface_profile import WaterSurfaceProfileAnalyzer
        
        print("🧪 横断面图功能测试")
        print("=" * 40)
        
        # 创建分析器
        analyzer = WaterSurfaceProfileAnalyzer(output_dir="test_outputs/simple_cross")
        
        # 简单的渠道配置
        channel_config = {
            'length': 2000.0,
            'sections': 5,  # 只测试5个断面
            'geometry': {
                'bottom_width': 10.0,
                'side_slope': 1.5,
                'roughness': 0.025
            },
            'profile': {
                'upstream_elevation': 15.0,
                'downstream_elevation': 10.0
            }
        }
        
        flow = 100.0
        
        print(f"测试参数：")
        print(f"  - 流量: {flow} m³/s")
        print(f"  - 断面数: {channel_config['sections']}")
        print(f"  - 渠道长度: {channel_config['length']} m")
        
        # 1. 计算水面线
        print("\n1. 计算水面线...")
        profile_data = analyzer.compute_profile_with_boundary(flow, channel_config)
        
        if profile_data:
            print("   ✅ 水面线计算成功")
            print(f"   - 断面数量: {len(profile_data['distances'])}")
            print(f"   - 水位范围: {min(profile_data['water_levels']):.2f} ~ {max(profile_data['water_levels']):.2f} m")
        else:
            print("   ❌ 水面线计算失败")
            return
        
        # 2. 生成横断面图
        print("\n2. 生成横断面图...")
        cross_section_path = analyzer.plot_cross_sections_combined(
            profile_data, channel_config, flow
        )
        
        if cross_section_path:
            print(f"   ✅ 横断面图生成成功")
            print(f"   - 文件路径: {cross_section_path}")
            
            # 检查文件
            if os.path.exists(cross_section_path):
                file_size = os.path.getsize(cross_section_path)
                print(f"   - 文件大小: {file_size} bytes")
            else:
                print("   ❌ 文件不存在")
        else:
            print("   ❌ 横断面图生成失败")
        
        print("\n✅ 测试完成！")
        
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    simple_cross_section_test()