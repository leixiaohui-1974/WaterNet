#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试横断面图功能

验证新增的横断面图绘制功能是否正常工作
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from waternet.utils.water_surface_profile import WaterSurfaceProfileAnalyzer


def test_cross_sections_functionality():
    """测试横断面图功能"""
    print("🧪 测试横断面图功能")
    print("=" * 50)
    
    # 创建分析器
    analyzer = WaterSurfaceProfileAnalyzer(output_dir="test_outputs/cross_sections")
    
    # 测试渠道配置
    channel_config = {
        'length': 5000.0,
        'sections': 8,  # 测试8个断面（小于10个，应使用详细模式）
        'geometry': {
            'bottom_width': 15.0,
            'side_slope': 2.0,
            'roughness': 0.030
        },
        'profile': {
            'upstream_elevation': 12.0,
            'downstream_elevation': 10.0
        }
    }
    
    # 测试流量
    test_flow = 120.0
    
    print(f"1. 测试小断面数（{channel_config['sections']}个断面）...")
    
    # 计算水面线
    profile_data = analyzer.compute_profile_with_boundary(test_flow, channel_config)
    
    if profile_data:
        print("   ✅ 水面线计算成功")
        
        # 测试横断面图生成
        cross_section_path = analyzer.plot_cross_sections_combined(
            profile_data, channel_config, test_flow
        )
        
        if cross_section_path:
            print(f"   ✅ 横断面图生成成功: {cross_section_path}")
            
            # 验证文件是否存在
            import os
            if os.path.exists(cross_section_path):
                file_size = os.path.getsize(cross_section_path)
                print(f"   ✅ 文件确实存在，大小: {file_size} bytes")
            else:
                print(f"   ❌ 文件不存在: {cross_section_path}")
        else:
            print("   ❌ 横断面图生成失败")
    else:
        print("   ❌ 水面线计算失败")
    
    print("\n2. 测试大断面数（20个断面）...")
    
    # 修改为更多断面数
    channel_config['sections'] = 20
    
    # 重新计算水面线
    profile_data = analyzer.compute_profile_with_boundary(test_flow, channel_config)
    
    if profile_data:
        print("   ✅ 水面线计算成功")
        
        # 测试优化横断面图生成
        cross_section_path = analyzer.plot_cross_sections_combined(
            profile_data, channel_config, test_flow
        )
        
        if cross_section_path:
            print(f"   ✅ 优化横断面图生成成功: {cross_section_path}")
            
            # 验证文件是否存在
            import os
            if os.path.exists(cross_section_path):
                file_size = os.path.getsize(cross_section_path)
                print(f"   ✅ 文件确实存在，大小: {file_size} bytes")
            else:
                print(f"   ❌ 文件不存在: {cross_section_path}")
        else:
            print("   ❌ 优化横断面图生成失败")
    else:
        print("   ❌ 水面线计算失败")
    
    print("\n3. 测试多工况横断面图...")
    
    # 测试多流量工况
    flow_conditions = [80.0, 120.0, 160.0]
    channel_config['sections'] = 12  # 使用中等数量断面
    
    results = analyzer.compute_multiple_flow_profiles(flow_conditions, channel_config)
    
    if results:
        print(f"   ✅ 多工况计算成功，共{len(results)}个工况")
        
        for result in results:
            cross_section_path = result.get('cross_section_plot', '')
            if cross_section_path:
                print(f"   ✅ {result['case_name']} 横断面图: {cross_section_path}")
            else:
                print(f"   ⚠️ {result['case_name']} 横断面图未生成")
    else:
        print("   ❌ 多工况计算失败")
    
    print("\n✅ 横断面图功能测试完成！")


if __name__ == "__main__":
    test_cross_sections_functionality()