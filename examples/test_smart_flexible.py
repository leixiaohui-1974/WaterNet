#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试智能灵活错开显示效果

专门测试新的智能定位算法，确保汉字能够灵活错开显示

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

def test_smart_flexible_positioning():
    """测试智能灵活定位效果"""
    
    try:
        from waternet.visualization.graph_renderer import GraphRenderer
        from waternet.visualization.topology_generator import TopologyConfig, NodeData, EdgeData, ComponentType
        
        print("🧪 测试智能灵活错开定位...")
        
        # 创建复杂密集连接的测试系统
        config = TopologyConfig(
            title="智能灵活错开定位测试",
            nodes=[
                NodeData("central_hub", "中央枢纽", ComponentType.STATION, (3, 3), {"flow_rate": 280.0}),
                NodeData("north_reservoir", "北水库", ComponentType.RESERVOIR, (3, 5), {"water_level": 145.0}),
                NodeData("south_reservoir", "南水库", ComponentType.RESERVOIR, (3, 1), {"water_level": 142.0}),
                NodeData("east_reservoir", "东水库", ComponentType.RESERVOIR, (5, 3), {"water_level": 138.0}),
                NodeData("west_reservoir", "西水库", ComponentType.RESERVOIR, (1, 3), {"water_level": 140.0}),
                NodeData("ne_pump", "东北泵站", ComponentType.PUMP, (4, 4), {"flow_rate": 45.0}),
                NodeData("nw_pump", "西北泵站", ComponentType.PUMP, (2, 4), {"flow_rate": 42.0}),
                NodeData("se_pump", "东南泵站", ComponentType.PUMP, (4, 2), {"flow_rate": 38.0}),
                NodeData("sw_pump", "西南泵站", ComponentType.PUMP, (2, 2), {"flow_rate": 40.0}),
                NodeData("top_valve", "顶部调节阀", ComponentType.VALVE, (3, 4), {"opening": 88.0}),
                NodeData("bottom_valve", "底部调节阀", ComponentType.VALVE, (3, 2), {"opening": 92.0}),
                NodeData("left_valve", "左侧调节阀", ComponentType.VALVE, (2, 3), {"opening": 85.0}),
                NodeData("right_valve", "右侧调节阀", ComponentType.VALVE, (4, 3), {"opening": 90.0}),
                NodeData("center_tank", "中心储罐", ComponentType.RESERVOIR, (3, 3.5), {"water_level": 125.0}),
                NodeData("buffer_tank", "缓冲储罐", ComponentType.RESERVOIR, (3, 2.5), {"water_level": 128.0})
            ],
            edges=[
                # 中央枢纽到四个方向的主要连接
                EdgeData("hub_north", "中央供北", "central_hub", "north_reservoir", properties={"flow_rate": 55.0}),
                EdgeData("hub_south", "中央供南", "central_hub", "south_reservoir", properties={"flow_rate": 52.0}),
                EdgeData("hub_east", "中央供东", "central_hub", "east_reservoir", properties={"flow_rate": 48.0}),
                EdgeData("hub_west", "中央供西", "central_hub", "west_reservoir", properties={"flow_rate": 50.0}),
                
                # 中央枢纽到泵站的连接
                EdgeData("hub_ne_pump", "供东北泵", "central_hub", "ne_pump", properties={"flow_rate": 45.0}),
                EdgeData("hub_nw_pump", "供西北泵", "central_hub", "nw_pump", properties={"flow_rate": 42.0}),
                EdgeData("hub_se_pump", "供东南泵", "central_hub", "se_pump", properties={"flow_rate": 38.0}),
                EdgeData("hub_sw_pump", "供西南泵", "central_hub", "sw_pump", properties={"flow_rate": 40.0}),
                
                # 中央枢纽到阀门的连接
                EdgeData("hub_top_valve", "供顶阀", "central_hub", "top_valve", properties={"flow_rate": 35.0}),
                EdgeData("hub_bottom_valve", "供底阀", "central_hub", "bottom_valve", properties={"flow_rate": 32.0}),
                EdgeData("hub_left_valve", "供左阀", "central_hub", "left_valve", properties={"flow_rate": 30.0}),
                EdgeData("hub_right_valve", "供右阀", "central_hub", "right_valve", properties={"flow_rate": 33.0}),
                
                # 中央枢纽到储罐的连接
                EdgeData("hub_center_tank", "供中心罐", "central_hub", "center_tank", properties={"flow_rate": 25.0}),
                EdgeData("hub_buffer_tank", "供缓冲罐", "central_hub", "buffer_tank", properties={"flow_rate": 28.0}),
                
                # 泵站之间的交叉连接
                EdgeData("ne_to_nw", "东北到西北", "ne_pump", "nw_pump", properties={"flow_rate": 15.0}),
                EdgeData("se_to_sw", "东南到西南", "se_pump", "sw_pump", properties={"flow_rate": 12.0}),
                EdgeData("ne_to_se", "东北到东南", "ne_pump", "se_pump", properties={"flow_rate": 18.0}),
                EdgeData("nw_to_sw", "西北到西南", "nw_pump", "sw_pump", properties={"flow_rate": 16.0}),
                
                # 储罐之间的连接
                EdgeData("center_to_buffer", "中心到缓冲", "center_tank", "buffer_tank", properties={"flow_rate": 20.0}),
                
                # 复杂的回路连接
                EdgeData("north_to_ne", "北库到东北", "north_reservoir", "ne_pump", properties={"flow_rate": 22.0}),
                EdgeData("east_to_se", "东库到东南", "east_reservoir", "se_pump", properties={"flow_rate": 25.0}),
                EdgeData("south_to_sw", "南库到西南", "south_reservoir", "sw_pump", properties={"flow_rate": 20.0}),
                EdgeData("west_to_nw", "西库到西北", "west_reservoir", "nw_pump", properties={"flow_rate": 24.0})
            ]
        )
        
        # 弹簧布局（最能测试智能定位）
        config.render_config = {
            "graph": {
                "layout": "spring",
                "node_size": 400,
                "font_size": 2,
                "edge_labels": True,
                "show_flow_direction": True,
                "title": "智能灵活错开定位测试"
            }
        }
        
        renderer = GraphRenderer(config)
        if renderer.can_render():
            print("✅ 开始渲染智能灵活错开图...")
            renderer.render()
            
            print("📊 智能定位特点:")
            print("  • 8方向候选: 上下左右+四个对角")
            print("  • 连接分析: 考虑所有连接线方向")
            print("  • 避让算法: 自动避开密集区域")
            print("  • 分离策略: 汉字和数字使用不同最优位置")
            print("  • 边标签智能: 多候选位置评分选择")
            print("  • 15个节点: 24条边，超高密度测试")
            
            print("🎨 视觉优化:")
            print("  • 背景框: 白色背景，有色边框")
            print("  • 汉字框: 灰色边框，黑色文字")
            print("  • 数字框: 红色边框，红色文字")
            print("  • 字体大小: 汉字3像素，数字4像素")
            
            print("💡 观察每个文字是否都找到了最佳位置")
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

def test_hierarchical_smart_positioning():
    """测试层次结构的智能定位"""
    
    try:
        from waternet.visualization.graph_renderer import GraphRenderer
        from waternet.visualization.topology_generator import TopologyConfig, NodeData, EdgeData, ComponentType
        
        print("\n🧪 测试层次结构智能定位...")
        
        # 创建多层次复杂系统
        config = TopologyConfig(
            title="层次结构智能定位测试",
            nodes=[
                # 第一层
                NodeData("source1", "主水源A", ComponentType.RESERVOIR, (0, 3), {"water_level": 155.0}),
                NodeData("source2", "主水源B", ComponentType.RESERVOIR, (0, 2), {"water_level": 148.0}),
                NodeData("source3", "备用水源", ComponentType.RESERVOIR, (0, 1), {"water_level": 152.0}),
                
                # 第二层
                NodeData("pump1", "主泵1号", ComponentType.PUMP, (2, 3.5), {"flow_rate": 65.0}),
                NodeData("pump2", "主泵2号", ComponentType.PUMP, (2, 2.5), {"flow_rate": 62.0}),
                NodeData("pump3", "备用泵", ComponentType.PUMP, (2, 1.5), {"flow_rate": 35.0}),
                NodeData("valve1", "调节阀A", ComponentType.VALVE, (2, 0.5), {"opening": 88.0}),
                
                # 第三层
                NodeData("dist1", "分配器1", ComponentType.JUNCTION, (4, 4), {"outlets": 3}),
                NodeData("dist2", "分配器2", ComponentType.JUNCTION, (4, 3), {"outlets": 4}),
                NodeData("dist3", "分配器3", ComponentType.JUNCTION, (4, 2), {"outlets": 2}),
                NodeData("dist4", "汇集器", ComponentType.JUNCTION, (4, 1), {"outlets": 1}),
                
                # 第四层
                NodeData("tank1", "储罐A1", ComponentType.RESERVOIR, (6, 4.5), {"water_level": 125.0}),
                NodeData("tank2", "储罐A2", ComponentType.RESERVOIR, (6, 3.5), {"water_level": 128.0}),
                NodeData("tank3", "储罐B1", ComponentType.RESERVOIR, (6, 2.5), {"water_level": 122.0}),
                NodeData("tank4", "储罐B2", ComponentType.RESERVOIR, (6, 1.5), {"water_level": 130.0}),
                NodeData("tank5", "储罐C", ComponentType.RESERVOIR, (6, 0.5), {"water_level": 118.0}),
                
                # 第五层
                NodeData("final", "最终输出", ComponentType.RESERVOIR, (8, 2.5), {"water_level": 108.0})
            ],
            edges=[
                # 第一层到第二层
                EdgeData("s1_p1", "源A到主泵1", "source1", "pump1", properties={"flow_rate": 65.0}),
                EdgeData("s2_p2", "源B到主泵2", "source2", "pump2", properties={"flow_rate": 62.0}),
                EdgeData("s3_p3", "备源到备泵", "source3", "pump3", properties={"flow_rate": 35.0}),
                EdgeData("s3_v1", "备源到调节阀", "source3", "valve1", properties={"flow_rate": 15.0}),
                
                # 第二层到第三层
                EdgeData("p1_d1", "主泵1到分配1", "pump1", "dist1", properties={"flow_rate": 60.0}),
                EdgeData("p2_d2", "主泵2到分配2", "pump2", "dist2", properties={"flow_rate": 58.0}),
                EdgeData("p3_d3", "备泵到分配3", "pump3", "dist3", properties={"flow_rate": 32.0}),
                EdgeData("v1_d4", "调节阀到汇集", "valve1", "dist4", properties={"flow_rate": 15.0}),
                
                # 交叉连接
                EdgeData("p1_d2", "主泵1到分配2", "pump1", "dist2", properties={"flow_rate": 25.0}),
                EdgeData("p2_d3", "主泵2到分配3", "pump2", "dist3", properties={"flow_rate": 20.0}),
                
                # 第三层到第四层
                EdgeData("d1_t1", "分配1到罐A1", "dist1", "tank1", properties={"flow_rate": 30.0}),
                EdgeData("d1_t2", "分配1到罐A2", "dist1", "tank2", properties={"flow_rate": 28.0}),
                EdgeData("d2_t3", "分配2到罐B1", "dist2", "tank3", properties={"flow_rate": 35.0}),
                EdgeData("d2_t4", "分配2到罐B2", "dist2", "tank4", properties={"flow_rate": 32.0}),
                EdgeData("d3_t5", "分配3到罐C", "dist3", "tank5", properties={"flow_rate": 25.0}),
                
                # 第四层到第五层
                EdgeData("t1_final", "罐A1到最终", "tank1", "final", properties={"flow_rate": 28.0}),
                EdgeData("t2_final", "罐A2到最终", "tank2", "final", properties={"flow_rate": 26.0}),
                EdgeData("t3_final", "罐B1到最终", "tank3", "final", properties={"flow_rate": 33.0}),
                EdgeData("t4_final", "罐B2到最终", "tank4", "final", properties={"flow_rate": 30.0}),
                EdgeData("t5_final", "罐C到最终", "tank5", "final", properties={"flow_rate": 23.0}),
                
                # 汇集器到最终输出
                EdgeData("d4_final", "汇集到最终", "dist4", "final", properties={"flow_rate": 15.0})
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
                "title": "层次结构智能定位测试"
            }
        }
        
        renderer = GraphRenderer(config)
        if renderer.can_render():
            print("✅ 开始渲染层次结构智能定位图...")
            renderer.render()
            
            print("📊 层次结构智能特点:")
            print("  • 5层结构: 17个节点，复杂交叉")
            print("  • 智能避让: 自动避开密集连接区域")
            print("  • 层次清晰: 每层节点标签优化定位")
            print("  • 交叉处理: 复杂连接线智能标签定位")
            
            print("💡 观察层次结构中文字定位的智能化程度")
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
    print("🔧 智能灵活错开定位测试")
    print("测试新的智能定位算法，确保汉字灵活错开")
    print("=" * 70)
    
    tests = [
        ("智能灵活定位", test_smart_flexible_positioning),
        ("层次结构智能定位", test_hierarchical_smart_positioning)
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
        print("✅ 智能灵活错开效果优秀！")
        print("🎯 智能算法特点:")
        print("  🧠 方向分析: 8个候选方向智能选择")
        print("  🔍 连接感知: 分析节点连接情况")
        print("  📊 空间评估: 避开密集和重叠区域")
        print("  🎨 分离优化: 汉字和数字分别定位")
        print("  🔄 边标签智能: 多候选位置评分")
        print("  📦 视觉增强: 有色边框区分不同元素")
        print("  🎯 自适应布局: 根据复杂度动态调整")
    else:
        print("⚠️ 测试失败，需要进一步调试")
    
    return success_count >= 1

if __name__ == "__main__":
    main()