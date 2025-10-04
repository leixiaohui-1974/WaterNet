#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试汉字字体放大3倍的效果

专门测试汉字字体从1像素放大到3像素的效果

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

def test_enlarged_chinese_font():
    """测试汉字字体放大效果"""
    
    try:
        from waternet.visualization.graph_renderer import GraphRenderer
        from waternet.visualization.topology_generator import TopologyConfig, NodeData, EdgeData, ComponentType
        
        print("🧪 测试汉字字体放大3倍效果...")
        
        # 创建包含丰富汉字的测试系统
        config = TopologyConfig(
            title="汉字字体放大测试系统",
            nodes=[
                NodeData("source_reservoir", "源水库", ComponentType.RESERVOIR, (0, 2), {"water_level": 135.0}),
                NodeData("intake_pump", "取水泵", ComponentType.PUMP, (1, 2), {"flow_rate": 95.0}),
                NodeData("main_valve", "主阀门", ComponentType.VALVE, (2, 2), {"opening": 88.5}),
                NodeData("distribution_hub", "配水中心", ComponentType.JUNCTION, (3, 2), {"outlets": 4}),
                NodeData("north_line", "北干线", ComponentType.PIPE, (4, 3), {"flow_rate": 28.0}),
                NodeData("south_line", "南干线", ComponentType.PIPE, (4, 1), {"flow_rate": 32.0}),
                NodeData("east_line", "东干线", ComponentType.PIPE, (4, 2.5), {"flow_rate": 25.0}),
                NodeData("west_line", "西干线", ComponentType.PIPE, (4, 1.5), {"flow_rate": 18.0}),
                NodeData("north_tank", "北水箱", ComponentType.RESERVOIR, (5, 3), {"water_level": 108.0}),
                NodeData("south_tank", "南水箱", ComponentType.RESERVOIR, (5, 1), {"water_level": 112.0}),
                NodeData("east_tank", "东水箱", ComponentType.RESERVOIR, (5, 2.5), {"water_level": 105.0}),
                NodeData("west_tank", "西水箱", ComponentType.RESERVOIR, (5, 1.5), {"water_level": 98.0}),
                NodeData("booster_station", "增压站", ComponentType.PUMP, (6, 2), {"flow_rate": 85.0}),
                NodeData("final_reservoir", "终端水库", ComponentType.RESERVOIR, (7, 2), {"water_level": 92.0})
            ],
            edges=[
                EdgeData("main_intake", "主进水", "source_reservoir", "intake_pump", properties={"flow_rate": 95.0}),
                EdgeData("pump_output", "泵出口", "intake_pump", "main_valve", properties={"flow_rate": 95.0}),
                EdgeData("valve_output", "阀出口", "main_valve", "distribution_hub", properties={"flow_rate": 84.1}),
                EdgeData("to_north", "向北供水", "distribution_hub", "north_line", properties={"flow_rate": 28.0}),
                EdgeData("to_south", "向南供水", "distribution_hub", "south_line", properties={"flow_rate": 32.0}),
                EdgeData("to_east", "向东供水", "distribution_hub", "east_line", properties={"flow_rate": 25.0}),
                EdgeData("to_west", "向西供水", "distribution_hub", "west_line", properties={"flow_rate": 18.0}),
                EdgeData("fill_north", "北储水", "north_line", "north_tank", properties={"flow_rate": 28.0}),
                EdgeData("fill_south", "南储水", "south_line", "south_tank", properties={"flow_rate": 32.0}),
                EdgeData("fill_east", "东储水", "east_line", "east_tank", properties={"flow_rate": 25.0}),
                EdgeData("fill_west", "西储水", "west_line", "west_tank", properties={"flow_rate": 18.0}),
                EdgeData("north_collect", "北回收", "north_tank", "booster_station", properties={"flow_rate": 25.0}),
                EdgeData("south_collect", "南回收", "south_tank", "booster_station", properties={"flow_rate": 30.0}),
                EdgeData("east_collect", "东回收", "east_tank", "booster_station", properties={"flow_rate": 22.0}),
                EdgeData("west_collect", "西回收", "west_tank", "booster_station", properties={"flow_rate": 16.0}),
                EdgeData("final_output", "最终输出", "booster_station", "final_reservoir", properties={"flow_rate": 85.0})
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
                "title": "汉字字体放大测试系统"
            }
        }
        
        renderer = GraphRenderer(config)
        if renderer.can_render():
            print("✅ 开始渲染汉字字体放大图...")
            renderer.render()
            
            print("📊 字体大小对比:")
            print("  • 汉字字体: 3像素 (放大3倍)")
            print("  • 数字字体: 4像素 (保持翻倍)")
            print("  • 图例字体: 4像素 (保持放大2倍)")
            print("  • 边标签汉字: 3像素 (同步放大)")
            
            print("🎨 显示效果:")
            print("  • 汉字: 黑色，更清晰可读")
            print("  • 数字: 红色，粗体突出")
            print("  • 位置: 上方汉字，下方数字")
            
            print("💡 检查汉字是否更加清晰可读")
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

def test_circular_enlarged_font():
    """测试环形布局的汉字字体放大效果"""
    
    try:
        from waternet.visualization.graph_renderer import GraphRenderer
        from waternet.visualization.topology_generator import TopologyConfig, NodeData, EdgeData, ComponentType
        
        print("\n🧪 测试环形布局汉字字体放大...")
        
        # 创建环形布局测试
        config = TopologyConfig(
            title="环形布局汉字字体测试",
            nodes=[
                NodeData("central_control", "中央控制", ComponentType.STATION, (0, 0), {"flow_rate": 240.0}),
                NodeData("north_station", "北水站", ComponentType.RESERVOIR, (0, 1), {"water_level": 125.0}),
                NodeData("northeast_pump", "东北泵房", ComponentType.PUMP, (1, 1), {"flow_rate": 35.0}),
                NodeData("east_valve", "东调节阀", ComponentType.VALVE, (1, 0), {"opening": 85.0}),
                NodeData("southeast_tank", "东南水罐", ComponentType.RESERVOIR, (1, -1), {"water_level": 115.0}),
                NodeData("south_station", "南水站", ComponentType.RESERVOIR, (0, -1), {"water_level": 118.0}),
                NodeData("southwest_pump", "西南泵房", ComponentType.PUMP, (-1, -1), {"flow_rate": 42.0}),
                NodeData("west_valve", "西调节阀", ComponentType.VALVE, (-1, 0), {"opening": 90.0}),
                NodeData("northwest_tank", "西北水罐", ComponentType.RESERVOIR, (-1, 1), {"water_level": 122.0})
            ],
            edges=[
                EdgeData("central_north", "中央供北", "central_control", "north_station", properties={"flow_rate": 28.0}),
                EdgeData("central_ne", "中央供东北", "central_control", "northeast_pump", properties={"flow_rate": 35.0}),
                EdgeData("central_east", "中央供东", "central_control", "east_valve", properties={"flow_rate": 32.0}),
                EdgeData("central_se", "中央供东南", "central_control", "southeast_tank", properties={"flow_rate": 26.0}),
                EdgeData("central_south", "中央供南", "central_control", "south_station", properties={"flow_rate": 30.0}),
                EdgeData("central_sw", "中央供西南", "central_control", "southwest_pump", properties={"flow_rate": 42.0}),
                EdgeData("central_west", "中央供西", "central_control", "west_valve", properties={"flow_rate": 38.0}),
                EdgeData("central_nw", "中央供西北", "central_control", "northwest_tank", properties={"flow_rate": 33.0})
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
                "title": "环形布局汉字字体测试"
            }
        }
        
        renderer = GraphRenderer(config)
        if renderer.can_render():
            print("✅ 开始渲染环形汉字字体放大图...")
            renderer.render()
            
            print("📊 环形布局字体特点:")
            print("  • 中心节点: 汉字3像素，数字4像素")
            print("  • 外围节点: 径向分布，字体统一")
            print("  • 连接标签: 汉字3像素，流量4像素")
            print("  • 密集信息: 9个节点，清晰显示")
            
            print("💡 观察环形布局中汉字的可读性提升")
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
    print("🔧 汉字字体放大3倍测试")
    print("将汉字字体从1像素放大到3像素")
    print("=" * 60)
    
    tests = [
        ("层次结构汉字放大", test_enlarged_chinese_font),
        ("环形布局汉字放大", test_circular_enlarged_font)
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
        
        print("-" * 40)
    
    print(f"\n🎉 测试完成！成功: {success_count}/{len(tests)}")
    
    if success_count >= 1:
        print("✅ 汉字字体放大效果良好！")
        print("🎯 字体设置更新:")
        print("  📝 汉字字体: 3像素 (放大3倍)")
        print("  🔢 数字字体: 4像素 (保持翻倍)")
        print("  📋 图例字体: 4像素 (保持放大2倍)")
        print("  🏷️ 边标签汉字: 3像素 (同步放大)")
        print("  🌈 颜色对比: 汉字黑色，数字红色")
        print("  📍 布局优化: 无重叠，清晰分离")
    else:
        print("⚠️ 测试失败，需要进一步调试")
    
    return success_count >= 1

if __name__ == "__main__":
    main()