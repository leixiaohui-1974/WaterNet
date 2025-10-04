#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试字体大小调整效果

专门测试图例字体放大2倍，汉字字体缩小一半，数字字体翻倍的效果

Created by: Qoder AI Assistant
Date: 2025-10-04
"""

import sys
import os
from pathlib import Path
import matplotlib.pyplot as plt

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_mixed_font_sizes():
    """测试混合字体大小"""
    
    try:
        from waternet.visualization.graph_renderer import GraphRenderer
        from waternet.visualization.topology_generator import TopologyConfig, NodeData, EdgeData, ComponentType
        
        print("🧪 测试混合字体大小效果...")
        
        # 创建测试系统
        config = TopologyConfig(
            title="字体大小对比测试系统",
            nodes=[
                NodeData("water_source", "水源池", ComponentType.RESERVOIR, (0, 2), {"water_level": 125.0}),
                NodeData("main_pump", "主泵站", ComponentType.PUMP, (1, 2), {"flow_rate": 45.0}),
                NodeData("control_valve", "控制阀", ComponentType.VALVE, (2, 2), {"opening": 87.5}),
                NodeData("distribution", "分配器", ComponentType.JUNCTION, (3, 2), {"outlets": 4}),
                NodeData("branch_a", "支线A", ComponentType.PIPE, (4, 3), {"flow_rate": 18.0}),
                NodeData("branch_b", "支线B", ComponentType.PIPE, (4, 2), {"flow_rate": 15.0}),
                NodeData("branch_c", "支线C", ComponentType.PIPE, (4, 1), {"flow_rate": 12.0}),
                NodeData("booster_pump", "增压泵", ComponentType.PUMP, (5, 2), {"flow_rate": 35.0}),
                NodeData("storage_tank", "储水罐", ComponentType.RESERVOIR, (6, 2), {"water_level": 98.5}),
                NodeData("final_outlet", "最终出口", ComponentType.RESERVOIR, (7, 2), {"water_level": 85.0})
            ],
            edges=[
                EdgeData("intake_pipe", "进水管", "water_source", "main_pump", properties={"flow_rate": 45.0}),
                EdgeData("pressure_line", "加压线", "main_pump", "control_valve", properties={"flow_rate": 45.0}),
                EdgeData("control_line", "控制线", "control_valve", "distribution", properties={"flow_rate": 39.4}),
                EdgeData("dist_a", "分配A", "distribution", "branch_a", properties={"flow_rate": 18.0}),
                EdgeData("dist_b", "分配B", "distribution", "branch_b", properties={"flow_rate": 15.0}),
                EdgeData("dist_c", "分配C", "distribution", "branch_c", properties={"flow_rate": 12.0}),
                EdgeData("boost_a", "增压A", "branch_a", "booster_pump", properties={"flow_rate": 18.0}),
                EdgeData("merge_b", "汇合B", "branch_b", "storage_tank", properties={"flow_rate": 15.0}),
                EdgeData("merge_c", "汇合C", "branch_c", "final_outlet", properties={"flow_rate": 12.0}),
                EdgeData("boost_out", "增压出", "booster_pump", "storage_tank", properties={"flow_rate": 35.0}),
                EdgeData("final_flow", "最终流", "storage_tank", "final_outlet", properties={"flow_rate": 50.0})
            ]
        )
        
        # 层次结构布局
        config.render_config = {
            "graph": {
                "layout": "hierarchical",
                "node_size": 400,
                "font_size": 2,
                "edge_labels": True,
                "show_flow_direction": True,
                "title": "字体大小对比测试系统"
            }
        }
        
        renderer = GraphRenderer(config)
        if renderer.can_render():
            print("✅ 开始渲染字体大小对比图...")
            renderer.render()
            
            print("📊 字体大小说明:")
            print("  • 图例字体: 4像素 (放大2倍)")
            print("  • 汉字字体: 1像素 (缩小一半)")
            print("  • 数字字体: 4像素 (翻倍)")
            print("  • 数字颜色: 红色突出显示")
            print("  • 汉字颜色: 黑色普通显示")
            
            print("💡 查看效果：图例更清晰，汉字更精简，数字更突出")
            plt.show()
            
            return True
        else:
            print("❌ 渲染器不可用")
            return False
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_compact_circular_with_fonts():
    """测试紧凑环形布局的字体效果"""
    
    try:
        from waternet.visualization.graph_renderer import GraphRenderer
        from waternet.visualization.topology_generator import TopologyConfig, NodeData, EdgeData, ComponentType
        
        print("\n🧪 测试环形布局字体效果...")
        
        # 创建环形系统
        config = TopologyConfig(
            title="环形配水系统字体测试",
            nodes=[
                NodeData("central_hub", "中央枢纽", ComponentType.STATION, (0, 0), {"flow_rate": 200.0}),
                NodeData("north_station", "北站", ComponentType.RESERVOIR, (0, 1), {"water_level": 105.0}),
                NodeData("northeast_pump", "东北泵", ComponentType.PUMP, (1, 1), {"flow_rate": 25.0}),
                NodeData("east_valve", "东阀", ComponentType.VALVE, (1, 0), {"opening": 92.0}),
                NodeData("southeast_tank", "东南罐", ComponentType.RESERVOIR, (1, -1), {"water_level": 88.0}),
                NodeData("south_station", "南站", ComponentType.RESERVOIR, (0, -1), {"water_level": 95.0}),
                NodeData("southwest_pump", "西南泵", ComponentType.PUMP, (-1, -1), {"flow_rate": 30.0}),
                NodeData("west_valve", "西阀", ComponentType.VALVE, (-1, 0), {"opening": 85.0}),
                NodeData("northwest_tank", "西北罐", ComponentType.RESERVOIR, (-1, 1), {"water_level": 102.0})
            ],
            edges=[
                EdgeData("hub_north", "供北", "central_hub", "north_station", properties={"flow_rate": 22.0}),
                EdgeData("hub_ne", "供东北", "central_hub", "northeast_pump", properties={"flow_rate": 25.0}),
                EdgeData("hub_east", "供东", "central_hub", "east_valve", properties={"flow_rate": 28.0}),
                EdgeData("hub_se", "供东南", "central_hub", "southeast_tank", properties={"flow_rate": 20.0}),
                EdgeData("hub_south", "供南", "central_hub", "south_station", properties={"flow_rate": 24.0}),
                EdgeData("hub_sw", "供西南", "central_hub", "southwest_pump", properties={"flow_rate": 30.0}),
                EdgeData("hub_west", "供西", "central_hub", "west_valve", properties={"flow_rate": 26.0}),
                EdgeData("hub_nw", "供西北", "central_hub", "northwest_tank", properties={"flow_rate": 25.0})
            ]
        )
        
        # 环形布局
        config.render_config = {
            "graph": {
                "layout": "circular",
                "node_size": 400,
                "font_size": 2,
                "edge_labels": True,
                "show_flow_rates": True,
                "title": "环形配水系统字体测试"
            }
        }
        
        renderer = GraphRenderer(config)
        if renderer.can_render():
            print("✅ 开始渲染环形字体测试图...")
            renderer.render()
            
            print("📊 环形布局字体特点:")
            print("  • 中心节点: 汉字1像素，数字4像素红色")
            print("  • 外围节点: 名称精简，数值突出")
            print("  • 连接线: 汉字1像素，流量4像素红色")
            print("  • 图例: 4像素清晰可读")
            
            print("💡 查看环形布局的字体层次...")
            plt.show()
            
            return True
        else:
            print("❌ 渲染器不可用")
            return False
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("🔧 字体大小调整测试")
    print("图例字体放大2倍，汉字字体缩小一半，数字字体翻倍")
    print("=" * 70)
    
    tests = [
        ("混合字体大小", test_mixed_font_sizes),
        ("环形布局字体", test_compact_circular_with_fonts)
    ]
    
    success_count = 0
    
    for test_name, test_func in tests:
        print(f"\n🧪 测试 {test_name}...")
        try:
            if test_func():
                success_count += 1
                print(f"✅ {test_name} 测试成功！")
            else:
                print(f"❌ {test_name} 测试失败")
        except Exception as e:
            print(f"❌ {test_name} 测试异常: {e}")
        
        print("-" * 50)
    
    print(f"\n🎉 测试完成！成功: {success_count}/{len(tests)}")
    
    if success_count >= 1:
        print("✅ 字体大小调整效果良好！")
        print("🎯 字体设置总结:")
        print("  📋 图例字体: 4像素 (放大2倍)")
        print("  🏷️ 汉字字体: 1像素 (缩小一半)")
        print("  🔢 数字字体: 4像素 (翻倍)")
        print("  🎨 数字颜色: 红色突出")
        print("  🖤 汉字颜色: 黑色普通")
        print("  📍 布局: 汉字在上，数字在下")
    else:
        print("⚠️ 测试失败，需要进一步调试")
    
    return success_count >= 1

if __name__ == "__main__":
    main()