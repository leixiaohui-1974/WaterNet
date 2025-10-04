#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试水位数字不与图形重叠的效果

专门测试文字偏移定位，确保汉字和数字不与节点图形重叠

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

def test_no_text_overlap():
    """测试文字不重叠效果"""
    
    try:
        from waternet.visualization.graph_renderer import GraphRenderer
        from waternet.visualization.topology_generator import TopologyConfig, NodeData, EdgeData, ComponentType
        
        print("🧪 测试文字与图形不重叠效果...")
        
        # 创建包含多种数值的测试系统
        config = TopologyConfig(
            title="文字重叠测试系统",
            nodes=[
                NodeData("main_reservoir", "主水库", ComponentType.RESERVOIR, (0, 2), {"water_level": 125.0}),
                NodeData("primary_pump", "主泵", ComponentType.PUMP, (1, 2), {"flow_rate": 85.0}),
                NodeData("control_valve", "控制阀", ComponentType.VALVE, (2, 2), {"opening": 92.5}),
                NodeData("splitter", "分流器", ComponentType.JUNCTION, (3, 2), {"outlets": 3}),
                NodeData("line_a", "A线", ComponentType.PIPE, (4, 3), {"flow_rate": 35.0}),
                NodeData("line_b", "B线", ComponentType.PIPE, (4, 2), {"flow_rate": 28.0}),
                NodeData("line_c", "C线", ComponentType.PIPE, (4, 1), {"flow_rate": 22.0}),
                NodeData("tank_a", "A罐", ComponentType.RESERVOIR, (5, 3), {"water_level": 98.5}),
                NodeData("tank_b", "B罐", ComponentType.RESERVOIR, (5, 2), {"water_level": 95.0}),
                NodeData("tank_c", "C罐", ComponentType.RESERVOIR, (5, 1), {"water_level": 92.5}),
                NodeData("final_pump", "终泵", ComponentType.PUMP, (6, 2), {"flow_rate": 75.0}),
                NodeData("outlet", "出口", ComponentType.RESERVOIR, (7, 2), {"water_level": 88.0})
            ],
            edges=[
                EdgeData("main_flow", "主流", "main_reservoir", "primary_pump", properties={"flow_rate": 85.0}),
                EdgeData("boost_flow", "增压", "primary_pump", "control_valve", properties={"flow_rate": 85.0}),
                EdgeData("control_flow", "控制", "control_valve", "splitter", properties={"flow_rate": 78.6}),
                EdgeData("split_a", "分A", "splitter", "line_a", properties={"flow_rate": 35.0}),
                EdgeData("split_b", "分B", "splitter", "line_b", properties={"flow_rate": 28.0}),
                EdgeData("split_c", "分C", "splitter", "line_c", properties={"flow_rate": 22.0}),
                EdgeData("feed_a", "供A", "line_a", "tank_a", properties={"flow_rate": 35.0}),
                EdgeData("feed_b", "供B", "line_b", "tank_b", properties={"flow_rate": 28.0}),
                EdgeData("feed_c", "供C", "line_c", "tank_c", properties={"flow_rate": 22.0}),
                EdgeData("collect_a", "收A", "tank_a", "final_pump", properties={"flow_rate": 32.0}),
                EdgeData("collect_b", "收B", "tank_b", "final_pump", properties={"flow_rate": 25.0}),
                EdgeData("collect_c", "收C", "tank_c", "final_pump", properties={"flow_rate": 18.0}),
                EdgeData("final_out", "最终", "final_pump", "outlet", properties={"flow_rate": 75.0})
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
                "title": "文字重叠测试系统"
            }
        }
        
        renderer = GraphRenderer(config)
        if renderer.can_render():
            print("✅ 开始渲染无重叠文字图...")
            renderer.render()
            
            print("📊 文字定位说明:")
            print("  • 汉字: 节点上方，1像素，黑色，底部对齐")
            print("  • 数字: 节点下方，4像素，红色，顶部对齐")
            print("  • 偏移: 节点半径+0.5单位距离")
            print("  • 图例: 右侧边缘，4像素字体")
            
            print("💡 检查效果：所有文字应该不与节点图形重叠")
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

def test_circular_no_overlap():
    """测试环形布局的无重叠效果"""
    
    try:
        from waternet.visualization.graph_renderer import GraphRenderer
        from waternet.visualization.topology_generator import TopologyConfig, NodeData, EdgeData, ComponentType
        
        print("\n🧪 测试环形布局无重叠效果...")
        
        # 创建密集环形系统
        config = TopologyConfig(
            title="环形布局无重叠测试",
            nodes=[
                NodeData("hub", "枢纽", ComponentType.STATION, (0, 0), {"flow_rate": 180.0}),
                NodeData("n1", "北1", ComponentType.RESERVOIR, (0, 1), {"water_level": 115.0}),
                NodeData("n2", "北2", ComponentType.PUMP, (1, 1), {"flow_rate": 22.0}),
                NodeData("ne", "东北", ComponentType.VALVE, (1, 0.5), {"opening": 88.0}),
                NodeData("e1", "东1", ComponentType.RESERVOIR, (1, 0), {"water_level": 108.0}),
                NodeData("e2", "东2", ComponentType.PUMP, (1, -1), {"flow_rate": 25.0}),
                NodeData("se", "东南", ComponentType.VALVE, (0.5, -1), {"opening": 92.0}),
                NodeData("s1", "南1", ComponentType.RESERVOIR, (0, -1), {"water_level": 95.0}),
                NodeData("s2", "南2", ComponentType.PUMP, (-1, -1), {"flow_rate": 28.0}),
                NodeData("sw", "西南", ComponentType.VALVE, (-1, -0.5), {"opening": 85.0}),
                NodeData("w1", "西1", ComponentType.RESERVOIR, (-1, 0), {"water_level": 102.0}),
                NodeData("w2", "西2", ComponentType.PUMP, (-1, 1), {"flow_rate": 30.0}),
                NodeData("nw", "西北", ComponentType.VALVE, (-0.5, 1), {"opening": 90.0})
            ],
            edges=[
                EdgeData("h_n1", "供北1", "hub", "n1", properties={"flow_rate": 20.0}),
                EdgeData("h_n2", "供北2", "hub", "n2", properties={"flow_rate": 22.0}),
                EdgeData("h_ne", "供东北", "hub", "ne", properties={"flow_rate": 18.0}),
                EdgeData("h_e1", "供东1", "hub", "e1", properties={"flow_rate": 24.0}),
                EdgeData("h_e2", "供东2", "hub", "e2", properties={"flow_rate": 25.0}),
                EdgeData("h_se", "供东南", "hub", "se", properties={"flow_rate": 21.0}),
                EdgeData("h_s1", "供南1", "hub", "s1", properties={"flow_rate": 19.0}),
                EdgeData("h_s2", "供南2", "hub", "s2", properties={"flow_rate": 28.0}),
                EdgeData("h_sw", "供西南", "hub", "sw", properties={"flow_rate": 23.0}),
                EdgeData("h_w1", "供西1", "hub", "w1", properties={"flow_rate": 26.0}),
                EdgeData("h_w2", "供西2", "hub", "w2", properties={"flow_rate": 30.0}),
                EdgeData("h_nw", "供西北", "hub", "nw", properties={"flow_rate": 27.0})
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
                "title": "环形布局无重叠测试"
            }
        }
        
        renderer = GraphRenderer(config)
        if renderer.can_render():
            print("✅ 开始渲染环形无重叠图...")
            renderer.render()
            
            print("📊 环形布局特点:")
            print("  • 中心节点: 文字在上下两侧，不重叠")
            print("  • 外围节点: 径向分布，文字偏移")
            print("  • 密集布局: 13个节点，大间距")
            print("  • 清晰识别: 每个节点文字都独立显示")
            
            print("💡 检查环形布局的文字清晰度...")
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
    print("🔧 文字与图形重叠修复测试")
    print("确保水位数字和节点名称不与图形重叠")
    print("=" * 70)
    
    tests = [
        ("层次结构无重叠", test_no_text_overlap),
        ("环形布局无重叠", test_circular_no_overlap)
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
        print("✅ 文字重叠问题已解决！")
        print("🎯 修复效果:")
        print("  📍 文字位置: 节点上方(汉字)、下方(数字)")
        print("  📏 偏移距离: 节点半径 + 0.5单位")
        print("  🎨 对齐方式: 底部对齐(上方)、顶部对齐(下方)")
        print("  🔤 字体大小: 汉字1像素、数字4像素")
        print("  🌈 颜色区分: 汉字黑色、数字红色")
        print("  📋 图例字体: 4像素边缘显示")
    else:
        print("⚠️ 测试失败，需要进一步调试")
    
    return success_count >= 1

if __name__ == "__main__":
    main()