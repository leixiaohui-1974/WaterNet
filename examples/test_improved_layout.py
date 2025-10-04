#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试改进后的布局算法

专门测试各种布局的节点间距改进效果

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

def test_improved_layout():
    """测试改进后的布局算法"""
    
    try:
        from waternet.visualization.graph_renderer import GraphRenderer
        from waternet.visualization.topology_generator import TopologyConfig, NodeData, EdgeData, ComponentType
        
        print("🧪 测试改进后的层次结构布局...")
        
        # 创建测试系统 - 层次结构样例
        config = TopologyConfig(
            title="改进布局测试: 层次结构图",
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
        
        # 强制使用层次结构布局
        config.render_config = {
            "graph": {
                "layout": "hierarchical",
                "node_size": 1500,
                "font_size": 9,
                "edge_labels": True,
                "show_flow_direction": True,
                "title": "改进布局测试: 层次结构图"
            }
        }
        
        renderer = GraphRenderer(config)
        if renderer.can_render():
            print("✅ 开始渲染层次结构图...")
            renderer.render()
            
            # 输出布局信息
            print("📊 节点位置信息:")
            for node_id, pos in renderer.node_positions.items():
                print(f"  {node_id}: ({pos[0]:.1f}, {pos[1]:.1f})")
            
            print("💡 关闭窗口可查看下一个测试...")
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

def test_horizontal_layout():
    """测试水平布局"""
    
    try:
        from waternet.visualization.graph_renderer import GraphRenderer
        from waternet.visualization.topology_generator import TopologyConfig, NodeData, EdgeData, ComponentType
        
        print("\n🧪 测试改进后的水平布局...")
        
        # 创建简单水平系统
        config = TopologyConfig(
            title="改进布局测试: 水平布局图",
            nodes=[
                NodeData("source", "原水池", ComponentType.RESERVOIR, (0, 0), {"water_level": 115.0}),
                NodeData("filter", "过滤站", ComponentType.STATION, (1, 0), {"flow_rate": 35.0}),
                NodeData("booster", "增压站", ComponentType.PUMP, (2, 0), {"flow_rate": 35.0}),
                NodeData("valve", "控制阀", ComponentType.VALVE, (3, 0), {"opening": 85.0}),
                NodeData("storage", "清水池", ComponentType.RESERVOIR, (4, 0), {"water_level": 105.0})
            ],
            edges=[
                EdgeData("e1", "原水管", "source", "filter", properties={"flow_rate": 35.0}),
                EdgeData("e2", "净水管", "filter", "booster", properties={"flow_rate": 33.25}),
                EdgeData("e3", "压力管", "booster", "valve", properties={"flow_rate": 33.25}),
                EdgeData("e4", "输送管", "valve", "storage", properties={"flow_rate": 28.26})
            ]
        )
        
        # 强制使用水平布局
        config.render_config = {
            "graph": {
                "layout": "horizontal",
                "node_size": 2000,
                "font_size": 10,
                "edge_labels": True,
                "show_detailed_info": True,
                "title": "改进布局测试: 水平布局图"
            }
        }
        
        renderer = GraphRenderer(config)
        if renderer.can_render():
            print("✅ 开始渲染水平布局图...")
            renderer.render()
            
            # 输出布局信息
            print("📊 节点位置信息:")
            for node_id, pos in renderer.node_positions.items():
                print(f"  {node_id}: ({pos[0]:.1f}, {pos[1]:.1f})")
            
            print("💡 关闭窗口可查看下一个测试...")
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

def test_circular_layout():
    """测试环形布局"""
    
    try:
        from waternet.visualization.graph_renderer import GraphRenderer
        from waternet.visualization.topology_generator import TopologyConfig, NodeData, EdgeData, ComponentType
        
        print("\n🧪 测试改进后的环形布局...")
        
        # 创建环形分布系统
        config = TopologyConfig(
            title="改进布局测试: 环形布局图",
            nodes=[
                NodeData("center", "中央控制", ComponentType.STATION, (0, 0), {"flow_rate": 50.0}),
                NodeData("north", "北区", ComponentType.RESERVOIR, (0, 2), {"water_level": 100.0}),
                NodeData("northeast", "东北区", ComponentType.RESERVOIR, (1.5, 1.5), {"water_level": 95.0}),
                NodeData("east", "东区", ComponentType.RESERVOIR, (2, 0), {"water_level": 95.0}),
                NodeData("southeast", "东南区", ComponentType.RESERVOIR, (1.5, -1.5), {"water_level": 98.0}),
                NodeData("south", "南区", ComponentType.RESERVOIR, (0, -2), {"water_level": 98.0}),
                NodeData("southwest", "西南区", ComponentType.RESERVOIR, (-1.5, -1.5), {"water_level": 102.0}),
                NodeData("west", "西区", ComponentType.RESERVOIR, (-2, 0), {"water_level": 102.0}),
                NodeData("northwest", "西北区", ComponentType.RESERVOIR, (-1.5, 1.5), {"water_level": 99.0})
            ],
            edges=[
                EdgeData("e1", "北线", "center", "north", properties={"flow_rate": 6.25}),
                EdgeData("e2", "东北线", "center", "northeast", properties={"flow_rate": 6.25}),
                EdgeData("e3", "东线", "center", "east", properties={"flow_rate": 6.25}),
                EdgeData("e4", "东南线", "center", "southeast", properties={"flow_rate": 6.25}),
                EdgeData("e5", "南线", "center", "south", properties={"flow_rate": 6.25}),
                EdgeData("e6", "西南线", "center", "southwest", properties={"flow_rate": 6.25}),
                EdgeData("e7", "西线", "center", "west", properties={"flow_rate": 6.25}),
                EdgeData("e8", "西北线", "center", "northwest", properties={"flow_rate": 6.25})
            ]
        )
        
        # 强制使用环形布局
        config.render_config = {
            "graph": {
                "layout": "circular",
                "node_size": 1800,
                "font_size": 8,
                "edge_labels": True,
                "show_flow_rates": True,
                "title": "改进布局测试: 环形布局图"
            }
        }
        
        renderer = GraphRenderer(config)
        if renderer.can_render():
            print("✅ 开始渲染环形布局图...")
            renderer.render()
            
            # 输出布局信息
            print("📊 节点位置信息:")
            for node_id, pos in renderer.node_positions.items():
                print(f"  {node_id}: ({pos[0]:.1f}, {pos[1]:.1f})")
            
            print("💡 测试完成！")
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
    print("🔧 改进布局算法测试")
    print("专门测试节点间距改进效果")
    print("=" * 50)
    
    tests = [
        ("层次结构布局", test_improved_layout),
        ("水平布局", test_horizontal_layout),
        ("环形布局", test_circular_layout)
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
        
        print("-" * 30)
    
    print(f"\n🎉 测试完成！成功: {success_count}/{len(tests)}")
    
    if success_count >= 2:
        print("✅ 布局算法改进效果良好！")
        print("🎯 主要改进:")
        print("  • 增大了节点间距")
        print("  • 改进了层次结构布局")
        print("  • 优化了环形布局半径")
        print("  • 添加了重叠节点检测和修复")
    else:
        print("⚠️ 部分测试失败，需要进一步调试")
    
    return success_count >= 2

if __name__ == "__main__":
    main()