#!/usr/bin/env python3
"""
简单测试纵剖面图生成
"""

import sys
from pathlib import Path

# 添加路径
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

from waternet.objects.conveyance import ChannelObject

def test_profile_generation():
    """测试纵剖面图生成"""
    print("🧪 测试纵剖面图生成")
    print("=" * 50)
    
    # 创建渠道配置
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
                'bottom_elevation': 97.0,   # 下游底高程：97m
                'bottom_width': 15.0,
                'side_slope': 2.0,
                'roughness': 0.030
            }
        ]
    }
    
    # 创建渠道对象
    channel = ChannelObject('profile_test', config=channel_config)
    channel.initialize()
    
    print(f"✅ 渠道对象创建成功: {channel.object_id}")
    
    # 设置边界条件
    upstream_flow = 120.0
    downstream_level = 98.5  # 下游水位98.5m
    
    channel.set_upstream_boundary(flow=upstream_flow)
    channel.set_downstream_boundary(level=downstream_level)
    
    print(f"🔧 边界条件: 上游流量={upstream_flow}m³/s, 下游水位={downstream_level}m")
    
    # 创建输出目录
    output_dir = current_dir / 'test_outputs'
    output_dir.mkdir(exist_ok=True)
    
    # 直接调用纵剖面图生成方法
    try:
        plot_dir = output_dir / 'plots'
        plot_dir.mkdir(exist_ok=True)
        
        # 调用内部的纵剖面图创建方法
        result = channel._create_enhanced_steady_flow_profile_visualization(plot_dir)
        
        if result.get('success', False):
            print(f"✅ 纵剖面图生成成功!")
            print(f"📁 文件路径: {result['file_path']}")
            
            # 检查文件大小
            file_path = Path(result['file_path'])
            if file_path.exists():
                file_size = file_path.stat().st_size
                print(f"📊 文件大小: {file_size:,} bytes")
            
        else:
            print(f"❌ 纵剖面图生成失败: {result.get('error', '未知错误')}")
            
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_profile_generation()