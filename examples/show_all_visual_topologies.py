#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
逐个展示所有图形化拓扑图形式

专门用于逐个弹出图形界面，展示不同的拓扑图样式

Created by: Qoder AI Assistant
Date: 2025-10-04
"""

import sys
import os
import time
from pathlib import Path
import matplotlib.pyplot as plt

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def show_style_1_simple_network():
    """样式1: 简单网络图"""
    print("\n🎨 正在显示样式1: 简单网络图...")
    
    try:
        from waternet.visualization.graph_renderer import GraphRenderer
        from waternet.visualization.topology_generator import TopologyConfig, NodeData, EdgeData, ComponentType
        
        config = TopologyConfig(
            title="样式1: 简单网络拓扑图",
            nodes=[
                NodeData("source", "水源", ComponentType.RESERVOIR, (0, 0), {"water_level": 100.0}),
                NodeData("pump", "水泵", ComponentType.PUMP, (2, 0), {"flow_rate": 25.0}),
                NodeData("valve", "控制阀", ComponentType.VALVE, (4, 0), {"opening": 80.0}),
                NodeData("target", "目标池", ComponentType.RESERVOIR, (6, 0), {"water_level": 95.0})
            ],
            edges=[
                EdgeData("pipe1", "进水管", "source", "pump", properties={"flow_rate": 25.0}),
                EdgeData("pipe2", "压力管", "pump", "valve", properties={"flow_rate": 25.0}),
                EdgeData("pipe3", "出水管", "valve", "target", properties={"flow_rate": 20.0})
            ]
        )
        
        config.render_config = {
            "graph": {
                "layout": "horizontal",
                "node_size": 2000,
                "font_size": 10,
                "edge_labels": True,
                "title": "样式1: 简单网络拓扑图"
            }
        }
        
        renderer = GraphRenderer(config)
        renderer.render()
        plt.show()
        
        return True
    except Exception as e:
        print(f"❌ 样式1生成失败: {e}")
        return False


def show_style_2_hierarchical():
    """样式2: 层次结构图"""
    print("\n🎨 正在显示样式2: 层次结构图...")
    
    try:
        from waternet.visualization.graph_renderer import GraphRenderer
        from waternet.visualization.topology_generator import TopologyConfig, NodeData, EdgeData, ComponentType
        
        config = TopologyConfig(
            title="样式2: 层次结构拓扑图",
            nodes=[
                NodeData("reservoir", "上游水库", ComponentType.RESERVOIR, (0, 2), {"water_level": 110.0}),
                NodeData("station", "泵站", ComponentType.STATION, (1, 2), {"flow_rate": 30.0}),
                NodeData("junction", "分流点", ComponentType.JUNCTION, (2, 2), {"outlets": 3}),
                NodeData("branch1", "支管1", ComponentType.PIPE, (3, 3), {"flow_rate": 12.0}),
                NodeData("branch2", "支管2", ComponentType.PIPE, (3, 2), {"flow_rate": 10.0}),
                NodeData("branch3", "支管3", ComponentType.PIPE, (3, 1), {"flow_rate": 8.0}),
                NodeData("target1", "目标1", ComponentType.RESERVOIR, (4, 3), {"water_level": 95.0}),
                NodeData("target2", "目标2", ComponentType.RESERVOIR, (4, 2), {"water_level": 92.0}),
                NodeData("target3", "目标3", ComponentType.RESERVOIR, (4, 1), {"water_level": 90.0})
            ],
            edges=[
                EdgeData("e1", "主管", "reservoir", "station", properties={"flow_rate": 30.0}),
                EdgeData("e2", "输送", "station", "junction", properties={"flow_rate": 30.0}),
                EdgeData("e3", "分支1", "junction", "branch1", properties={"flow_rate": 12.0}),
                EdgeData("e4", "分支2", "junction", "branch2", properties={"flow_rate": 10.0}),
                EdgeData("e5", "分支3", "junction", "branch3", properties={"flow_rate": 8.0}),
                EdgeData("e6", "到达1", "branch1", "target1", properties={"flow_rate": 12.0}),
                EdgeData("e7", "到达2", "branch2", "target2", properties={"flow_rate": 10.0}),
                EdgeData("e8", "到达3", "branch3", "target3", properties={"flow_rate": 8.0})
            ]
        )
        
        config.render_config = {
            "graph": {
                "layout": "hierarchical",
                "node_size": 1500,
                "font_size": 9,
                "edge_labels": True,
                "show_flow_direction": True,
                "title": "样式2: 层次结构拓扑图"
            }
        }
        
        renderer = GraphRenderer(config)
        renderer.render()
        plt.show()
        
        return True
    except Exception as e:
        print(f"❌ 样式2生成失败: {e}")
        return False


def show_style_3_circular():
    """样式3: 环形布局图"""
    print("\n🎨 正在显示样式3: 环形布局图...")
    
    try:
        from waternet.visualization.graph_renderer import GraphRenderer
        from waternet.visualization.topology_generator import TopologyConfig, NodeData, EdgeData, ComponentType
        
        config = TopologyConfig(
            title="样式3: 环形布局拓扑图",
            nodes=[
                NodeData("center", "中央控制", ComponentType.STATION, (0, 0), {"flow_rate": 50.0}),
                NodeData("north", "北区", ComponentType.RESERVOIR, (0, 2), {"water_level": 100.0}),
                NodeData("east", "东区", ComponentType.RESERVOIR, (2, 0), {"water_level": 95.0}),
                NodeData("south", "南区", ComponentType.RESERVOIR, (0, -2), {"water_level": 98.0}),
                NodeData("west", "西区", ComponentType.RESERVOIR, (-2, 0), {"water_level": 102.0}),
                NodeData("pump_n", "北泵", ComponentType.PUMP, (0, 1), {"flow_rate": 12.0}),
                NodeData("pump_e", "东泵", ComponentType.PUMP, (1, 0), {"flow_rate": 15.0}),
                NodeData("pump_s", "南泵", ComponentType.PUMP, (0, -1), {"flow_rate": 10.0}),
                NodeData("pump_w", "西泵", ComponentType.PUMP, (-1, 0), {"flow_rate": 13.0})
            ],
            edges=[
                EdgeData("e1", "北线", "center", "pump_n", properties={"flow_rate": 12.0}),
                EdgeData("e2", "东线", "center", "pump_e", properties={"flow_rate": 15.0}),
                EdgeData("e3", "南线", "center", "pump_s", properties={"flow_rate": 10.0}),
                EdgeData("e4", "西线", "center", "pump_w", properties={"flow_rate": 13.0}),
                EdgeData("e5", "供北", "pump_n", "north", properties={"flow_rate": 12.0}),
                EdgeData("e6", "供东", "pump_e", "east", properties={"flow_rate": 15.0}),
                EdgeData("e7", "供南", "pump_s", "south", properties={"flow_rate": 10.0}),
                EdgeData("e8", "供西", "pump_w", "west", properties={"flow_rate": 13.0})
            ]
        )
        
        config.render_config = {
            "graph": {
                "layout": "circular",
                "node_size": 1800,
                "font_size": 8,
                "edge_labels": True,
                "show_flow_rates": True,
                "title": "样式3: 环形布局拓扑图"
            }
        }
        
        renderer = GraphRenderer(config)
        renderer.render()
        plt.show()
        
        return True
    except Exception as e:
        print(f"❌ 样式3生成失败: {e}")
        return False


def show_style_4_spring():
    """样式4: 弹簧布局图"""
    print("\n🎨 正在显示样式4: 弹簧布局图...")
    
    try:
        from waternet.visualization.graph_renderer import GraphRenderer
        from waternet.visualization.topology_generator import TopologyConfig, NodeData, EdgeData, ComponentType
        
        config = TopologyConfig(
            title="样式4: 弹簧布局拓扑图",
            nodes=[
                NodeData("main_res", "主水库", ComponentType.RESERVOIR, (0, 0), {"water_level": 120.0}),
                NodeData("pump1", "一级泵", ComponentType.PUMP, (1, 1), {"flow_rate": 25.0}),
                NodeData("pump2", "二级泵", ComponentType.PUMP, (2, 1), {"flow_rate": 20.0}),
                NodeData("valve1", "调节阀1", ComponentType.VALVE, (1, 0), {"opening": 90.0}),
                NodeData("valve2", "调节阀2", ComponentType.VALVE, (2, 0), {"opening": 85.0}),
                NodeData("tank1", "储水罐1", ComponentType.RESERVOIR, (3, 1), {"water_level": 85.0}),
                NodeData("tank2", "储水罐2", ComponentType.RESERVOIR, (3, 0), {"water_level": 88.0}),
                NodeData("junction1", "汇流点", ComponentType.JUNCTION, (4, 0.5), {"outlets": 1}),
                NodeData("final", "最终目标", ComponentType.RESERVOIR, (5, 0.5), {"water_level": 75.0})
            ],
            edges=[
                EdgeData("e1", "取水", "main_res", "pump1", properties={"flow_rate": 25.0}),
                EdgeData("e2", "调压", "main_res", "valve1", properties={"flow_rate": 15.0}),
                EdgeData("e3", "提升", "pump1", "pump2", properties={"flow_rate": 20.0}),
                EdgeData("e4", "分流1", "valve1", "valve2", properties={"flow_rate": 12.0}),
                EdgeData("e5", "供罐1", "pump2", "tank1", properties={"flow_rate": 20.0}),
                EdgeData("e6", "供罐2", "valve2", "tank2", properties={"flow_rate": 12.0}),
                EdgeData("e7", "汇合1", "tank1", "junction1", properties={"flow_rate": 18.0}),
                EdgeData("e8", "汇合2", "tank2", "junction1", properties={"flow_rate": 10.0}),
                EdgeData("e9", "输出", "junction1", "final", properties={"flow_rate": 28.0})
            ]
        )
        
        config.render_config = {
            "graph": {
                "layout": "spring",
                "node_size": 1600,
                "font_size": 8,
                "edge_labels": True,
                "show_flow_rates": True,
                "title": "样式4: 弹簧布局拓扑图"
            }
        }
        
        renderer = GraphRenderer(config)
        renderer.render()
        plt.show()
        
        return True
    except Exception as e:
        print(f"❌ 样式4生成失败: {e}")
        return False


def show_style_5_detailed():
    """样式5: 详细信息图"""
    print("\n🎨 正在显示样式5: 详细信息图...")
    
    try:
        from waternet.visualization.graph_renderer import GraphRenderer
        from waternet.visualization.topology_generator import TopologyConfig, NodeData, EdgeData, ComponentType
        
        config = TopologyConfig(
            title="样式5: 详细信息拓扑图",
            nodes=[
                NodeData("source", "原水池", ComponentType.RESERVOIR, (0, 0), 
                        {"water_level": 115.0, "capacity": 5000, "quality": "A级"}),
                NodeData("filter", "过滤站", ComponentType.STATION, (1, 0), 
                        {"flow_rate": 35.0, "efficiency": 95.5, "status": "正常"}),
                NodeData("booster", "增压站", ComponentType.PUMP, (2, 0), 
                        {"flow_rate": 35.0, "pressure": 4.5, "power": 750}),
                NodeData("storage", "清水池", ComponentType.RESERVOIR, (3, 0), 
                        {"water_level": 105.0, "capacity": 8000, "quality": "优质"})
            ],
            edges=[
                EdgeData("e1", "原水管", "source", "filter", 
                        properties={"flow_rate": 35.0, "diameter": 800, "material": "钢管"}),
                EdgeData("e2", "净水管", "filter", "booster", 
                        properties={"flow_rate": 33.25, "diameter": 700, "material": "球墨铸铁"}),
                EdgeData("e3", "输送管", "booster", "storage", 
                        properties={"flow_rate": 33.25, "diameter": 700, "material": "球墨铸铁"})
            ]
        )
        
        config.render_config = {
            "graph": {
                "layout": "horizontal",
                "node_size": 2500,
                "font_size": 9,
                "edge_labels": True,
                "show_detailed_info": True,
                "show_flow_rates": True,
                "title": "样式5: 详细信息拓扑图"
            }
        }
        
        renderer = GraphRenderer(config)
        renderer.render()
        plt.show()
        
        return True
    except Exception as e:
        print(f"❌ 样式5生成失败: {e}")
        return False


def main():
    """主函数 - 逐个展示所有图形化拓扑图"""
    print("🎬 逐个展示所有图形化拓扑图形式")
    print("每个窗口将依次弹出，请关闭当前窗口查看下一个...")
    print("=" * 80)
    
    styles = [
        ("样式1: 简单网络图", show_style_1_simple_network),
        ("样式2: 层次结构图", show_style_2_hierarchical),
        ("样式3: 环形布局图", show_style_3_circular),
        ("样式4: 弹簧布局图", show_style_4_spring),
        ("样式5: 详细信息图", show_style_5_detailed)
    ]
    
    success_count = 0
    
    for i, (name, func) in enumerate(styles, 1):
        print(f"\n📊 [{i}/5] {name}")
        print("⏳ 正在生成...")
        
        try:
            if func():
                success_count += 1
                print(f"✅ {name} 生成成功！")
                print("💡 请关闭图形窗口查看下一个样式...")
                
                # 等待用户关闭窗口
                input("👆 按Enter继续下一个样式...")
            else:
                print(f"❌ {name} 生成失败")
        except Exception as e:
            print(f"❌ {name} 发生错误: {e}")
        
        print("-" * 50)
    
    # 显示总结
    print(f"\n🎉 图形化拓扑图展示完成！")
    print(f"📊 成功展示: {success_count}/5 种样式")
    
    if success_count >= 4:
        print("✅ 大部分样式展示成功！")
        print("\n🎯 您看到的不同样式特点:")
        print("  📝 样式1 → 简洁清晰，适合简单系统")
        print("  🌳 样式2 → 层次分明，适合分流系统")
        print("  🔄 样式3 → 环形布局，适合多点分布")
        print("  🌸 样式4 → 自由布局，适合复杂网络")
        print("  📋 样式5 → 详细信息，适合技术分析")
    else:
        print("⚠️ 部分样式展示失败，可能需要检查依赖")
    
    return success_count >= 3


if __name__ == "__main__":
    main()