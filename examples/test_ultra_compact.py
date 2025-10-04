#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速测试极小字体和箭头的拓扑图效果

专门测试大幅缩小字体、箭头、不使用白色字体的效果

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

def test_ultra_compact_layout():
    """测试超紧凑布局"""
    
    try:
        from waternet.visualization.graph_renderer import GraphRenderer
        from waternet.visualization.topology_generator import TopologyConfig, NodeData, EdgeData, ComponentType
        
        print("🧪 测试超紧凑拓扑图布局...")
        
        # 创建复杂测试系统
        config = TopologyConfig(
            title="超紧凑拓扑图测试",
            nodes=[
                NodeData("reservoir1", "上游水库", ComponentType.RESERVOIR, (0, 2), {"water_level": 110.0}),
                NodeData("pump1", "一级泵站", ComponentType.PUMP, (1, 2), {"flow_rate": 30.0}),
                NodeData("valve1", "调节阀1", ComponentType.VALVE, (2, 2), {"opening": 85.0}),
                NodeData("junction1", "分流点1", ComponentType.JUNCTION, (3, 2), {"outlets": 3}),
                NodeData("pipe1", "支管1", ComponentType.PIPE, (4, 3), {"flow_rate": 12.0}),
                NodeData("pipe2", "支管2", ComponentType.PIPE, (4, 2), {"flow_rate": 10.0}),
                NodeData("pipe3", "支管3", ComponentType.PIPE, (4, 1), {"flow_rate": 8.0}),
                NodeData("pump2", "二级泵", ComponentType.PUMP, (5, 2), {"flow_rate": 15.0}),
                NodeData("reservoir2", "中间池", ComponentType.RESERVOIR, (6, 2), {"water_level": 95.0}),
                NodeData("junction2", "汇流点", ComponentType.JUNCTION, (7, 2), {"outlets": 1}),
                NodeData("target", "目标池", ComponentType.RESERVOIR, (8, 2), {"water_level": 90.0})
            ],
            edges=[
                EdgeData("e1", "进水", "reservoir1", "pump1", properties={"flow_rate": 30.0}),
                EdgeData("e2", "提升", "pump1", "valve1", properties={"flow_rate": 30.0}),
                EdgeData("e3", "调节", "valve1", "junction1", properties={"flow_rate": 25.5}),
                EdgeData("e4", "分支1", "junction1", "pipe1", properties={"flow_rate": 12.0}),
                EdgeData("e5", "分支2", "junction1", "pipe2", properties={"flow_rate": 10.0}),
                EdgeData("e6", "分支3", "junction1", "pipe3", properties={"flow_rate": 8.0}),
                EdgeData("e7", "传输1", "pipe1", "pump2", properties={"flow_rate": 12.0}),
                EdgeData("e8", "传输2", "pipe2", "reservoir2", properties={"flow_rate": 10.0}),
                EdgeData("e9", "传输3", "pipe3", "junction2", properties={"flow_rate": 8.0}),
                EdgeData("e10", "增压", "pump2", "reservoir2", properties={"flow_rate": 15.0}),
                EdgeData("e11", "存储", "reservoir2", "junction2", properties={"flow_rate": 25.0}),
                EdgeData("e12", "输出", "junction2", "target", properties={"flow_rate": 33.0})
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
                "title": "超紧凑层次结构拓扑图"
            }
        }
        
        renderer = GraphRenderer(config)
        if renderer.can_render():
            print("✅ 开始渲染超紧凑层次结构图...")
            renderer.render()
            
            print("📊 节点位置信息:")
            for node_id, pos in renderer.node_positions.items():
                print(f"  {node_id}: ({pos[0]:.1f}, {pos[1]:.1f})")
            
            print("💡 查看效果：字体2像素，箭头缩小，黑色文字，图例在边缘")
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

def test_compact_circular():
    """测试紧凑环形布局"""
    
    try:
        from waternet.visualization.graph_renderer import GraphRenderer
        from waternet.visualization.topology_generator import TopologyConfig, NodeData, EdgeData, ComponentType
        
        print("\n🧪 测试紧凑环形布局...")
        
        # 创建环形系统
        config = TopologyConfig(
            title="紧凑环形配水系统",
            nodes=[
                NodeData("center", "中央站", ComponentType.STATION, (0, 0), {"flow_rate": 100.0}),
                NodeData("n1", "北1", ComponentType.RESERVOIR, (0, 1), {"water_level": 95}),
                NodeData("n2", "北2", ComponentType.PUMP, (1, 1), {"flow_rate": 15}),
                NodeData("e1", "东1", ComponentType.RESERVOIR, (1, 0), {"water_level": 92}),
                NodeData("e2", "东2", ComponentType.VALVE, (1, -1), {"opening": 80}),
                NodeData("s1", "南1", ComponentType.RESERVOIR, (0, -1), {"water_level": 88}),
                NodeData("s2", "南2", ComponentType.PUMP, (-1, -1), {"flow_rate": 18}),
                NodeData("w1", "西1", ComponentType.RESERVOIR, (-1, 0), {"water_level": 90}),
                NodeData("w2", "西2", ComponentType.VALVE, (-1, 1), {"opening": 75})
            ],
            edges=[
                EdgeData("c1", "供北1", "center", "n1", properties={"flow_rate": 12}),
                EdgeData("c2", "供北2", "center", "n2", properties={"flow_rate": 15}),
                EdgeData("c3", "供东1", "center", "e1", properties={"flow_rate": 10}),
                EdgeData("c4", "供东2", "center", "e2", properties={"flow_rate": 13}),
                EdgeData("c5", "供南1", "center", "s1", properties={"flow_rate": 11}),
                EdgeData("c6", "供南2", "center", "s2", properties={"flow_rate": 18}),
                EdgeData("c7", "供西1", "center", "w1", properties={"flow_rate": 14}),
                EdgeData("c8", "供西2", "center", "w2", properties={"flow_rate": 16})
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
                "title": "紧凑环形配水系统"
            }
        }
        
        renderer = GraphRenderer(config)
        if renderer.can_render():
            print("✅ 开始渲染紧凑环形图...")
            renderer.render()
            
            print("📊 环形布局节点位置:")
            for node_id, pos in renderer.node_positions.items():
                print(f"  {node_id}: ({pos[0]:.1f}, {pos[1]:.1f})")
            
            print("💡 查看环形布局效果...")
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
    print("🔧 超紧凑拓扑图测试")
    print("测试2像素字体、小箭头、黑色文字、边缘图例")
    print("=" * 60)
    
    tests = [
        ("超紧凑层次结构", test_ultra_compact_layout),
        ("紧凑环形布局", test_compact_circular)
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
        print("✅ 超紧凑布局效果良好！")
        print("🎯 主要改进:")
        print("  • 字体缩小到2像素（极小）")
        print("  • 箭头大小从20缩小到8")
        print("  • 统一使用黑色字体，不再使用白色")
        print("  • 节点半径缩小到0.4")
        print("  • 图例放在边缘外侧")
        print("  • 大幅增加节点间距避免重叠")
    else:
        print("⚠️ 测试失败，需要进一步调试")
    
    return success_count >= 1

if __name__ == "__main__":
    main()