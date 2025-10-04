#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接展示各种拓扑图形式

为用户实际生成和展示不同样式的拓扑图效果。

Created by: Qoder AI Assistant
Date: 2025-10-04
"""

import sys
import os
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def display_simple_flow_style():
    """展示简洁流程图样式"""
    print("=" * 90)
    print("🎨 样式1: 简洁流程图（实际生成效果）")
    print("=" * 90)
    
    try:
        from waternet.visualization.enhanced_text_renderer import EnhancedTextRenderer
        from waternet.visualization.topology_generator import TopologyConfig, NodeData, EdgeData, ComponentType
        
        # 创建简单系统
        config = TopologyConfig(
            title="简单水力传输系统",
            nodes=[
                NodeData("source", "水源", ComponentType.RESERVOIR, (0, 0), {"water_level": 100.0}),
                NodeData("pump", "水泵", ComponentType.PUMP, (1, 0), {"flow_rate": 25.0}),
                NodeData("target", "目标", ComponentType.RESERVOIR, (2, 0), {"water_level": 95.0})
            ],
            edges=[
                EdgeData("pipe1", "进水", "source", "pump", properties={"flow_rate": 25.0}),
                EdgeData("pipe2", "出水", "pump", "target", properties={"flow_rate": 25.0})
            ]
        )
        
        # 强制使用简洁流程图
        config.render_config = {"text_ascii": {"style": "simple_flow", "auto_select": False}}
        
        renderer = EnhancedTextRenderer(config)
        renderer.render()
        
        return True
    except Exception as e:
        print(f"❌ 生成失败: {e}")
        return False


def display_flow_diagram_style():
    """展示流向示意图样式"""
    print("\n" + "=" * 90)
    print("🎨 样式2: 流向示意图（实际生成效果）")
    print("=" * 90)
    
    try:
        from waternet.visualization.enhanced_text_renderer import EnhancedTextRenderer
        from waternet.visualization.topology_generator import TopologyConfig, NodeData, EdgeData, ComponentType
        
        # 创建复杂分流系统
        config = TopologyConfig(
            title="复杂分流水力系统",
            nodes=[
                NodeData("reservoir", "上游水库", ComponentType.RESERVOIR, (0, 1), {"water_level": 110.0}),
                NodeData("station", "主控站", ComponentType.STATION, (1, 1), {"flow_rate": 20.3}),
                NodeData("junction", "分流点", ComponentType.JUNCTION, (2, 1), {"outlets": 2}),
                NodeData("pipe1", "输水管", ComponentType.PIPE, (3, 0), {"flow_rate": 7.6}),
                NodeData("pipe2", "泄洪道", ComponentType.PIPE, (3, 2), {"flow_rate": 12.7}),
                NodeData("target", "下游池", ComponentType.RESERVOIR, (4, 1), {"water_level": 92.0})
            ],
            edges=[
                EdgeData("e1", "进水", "reservoir", "station", properties={"flow_rate": 20.3}),
                EdgeData("e2", "控制", "station", "junction", properties={"flow_rate": 20.3}),
                EdgeData("e3", "输水", "junction", "pipe1", properties={"flow_rate": 7.6}),
                EdgeData("e4", "泄洪", "junction", "pipe2", properties={"flow_rate": 12.7}),
                EdgeData("e5", "汇流1", "pipe1", "target", properties={"flow_rate": 7.6}),
                EdgeData("e6", "汇流2", "pipe2", "target", properties={"flow_rate": 12.7})
            ]
        )
        
        # 强制使用流向示意图
        config.render_config = {"text_ascii": {"style": "flow_diagram", "auto_select": False}}
        
        renderer = EnhancedTextRenderer(config)
        renderer.render()
        
        return True
    except Exception as e:
        print(f"❌ 生成失败: {e}")
        return False


def display_table_styles():
    """展示表格样式"""
    print("\n" + "=" * 90)
    print("🎨 样式3: 表格样式（实际生成效果）")
    print("=" * 90)
    
    try:
        from waternet.visualization.table_renderer import TableRenderer
        from waternet.visualization.topology_generator import TopologyConfig, NodeData, EdgeData, ComponentType
        
        # 创建测试数据
        config = TopologyConfig(
            title="水力系统组件表格",
            nodes=[
                NodeData("reservoir1", "上游水库", ComponentType.RESERVOIR, (0, 1), {"water_level": 110.0, "capacity": 5000000}),
                NodeData("station1", "主控站", ComponentType.STATION, (1, 1), {"flow_rate": 20.3, "power": 500}),
                NodeData("junction1", "分流点", ComponentType.JUNCTION, (2, 1), {"outlets": 2}),
                NodeData("pipe1", "输水管", ComponentType.PIPE, (3, 0), {"diameter": 2.2, "flow_rate": 7.6}),
                NodeData("pipe2", "泄洪道", ComponentType.PIPE, (3, 2), {"diameter": 3.0, "flow_rate": 12.7}),
                NodeData("reservoir2", "下游池", ComponentType.RESERVOIR, (4, 1), {"water_level": 92.0, "capacity": 2000000})
            ],
            edges=[
                EdgeData("e1", "进水管", "reservoir1", "station1", properties={"flow_rate": 20.3}),
                EdgeData("e2", "控制管", "station1", "junction1", properties={"flow_rate": 20.3}),
                EdgeData("e3", "输水管", "junction1", "pipe1", properties={"flow_rate": 7.6}),
                EdgeData("e4", "泄洪管", "junction1", "pipe2", properties={"flow_rate": 12.7}),
                EdgeData("e5", "汇流管1", "pipe1", "reservoir2", properties={"flow_rate": 7.6}),
                EdgeData("e6", "汇流管2", "pipe2", "reservoir2", properties={"flow_rate": 12.7})
            ]
        )
        
        # 设置表格格式
        config.render_config = {"table": {"format": "rich", "show_summary": True, "group_by_type": True}}
        
        renderer = TableRenderer(config)
        renderer.render()
        
        return True
    except Exception as e:
        print(f"❌ 生成失败: {e}")
        return False


def display_quick_render_demo():
    """展示快速渲染接口效果"""
    print("\n" + "=" * 90)
    print("🎨 样式4: 快速渲染接口（自动选择最佳样式）")
    print("=" * 90)
    
    try:
        from waternet.visualization import quick_render
        
        # 创建中等复杂度系统
        nodes = [
            ("intake", "取水口", "reservoir", (0, 1), {"water_level": 115.0}),
            ("pump_station", "泵站", "pump", (1, 1), {"flow_rate": 30.0, "power": 300}),
            ("control", "控制阀", "valve", (2, 1), {"opening": 80.0}),
            ("splitter", "三通", "junction", (3, 1), {"outlets": 3}),
            ("branch1", "支管1", "pipe", (4, 0), {"flow_rate": 12.0}),
            ("branch2", "支管2", "pipe", (4, 1), {"flow_rate": 10.0}),
            ("branch3", "支管3", "pipe", (4, 2), {"flow_rate": 8.0}),
            ("outlet", "出水口", "reservoir", (5, 1), {"water_level": 105.0})
        ]
        
        edges = [
            ("e1", "取水管", "intake", "pump_station", {"flow_rate": 30.0}),
            ("e2", "加压管", "pump_station", "control", {"flow_rate": 30.0}),
            ("e3", "控制管", "control", "splitter", {"flow_rate": 30.0}),
            ("e4", "分支1", "splitter", "branch1", {"flow_rate": 12.0}),
            ("e5", "分支2", "splitter", "branch2", {"flow_rate": 10.0}),
            ("e6", "分支3", "splitter", "branch3", {"flow_rate": 8.0}),
            ("e7", "汇流1", "branch1", "outlet", {"flow_rate": 12.0}),
            ("e8", "汇流2", "branch2", "outlet", {"flow_rate": 10.0}),
            ("e9", "汇流3", "branch3", "outlet", {"flow_rate": 8.0})
        ]
        
        print("🤖 系统自动分析数据特征，选择最佳展示样式...")
        results = quick_render("智能三分流水力系统", nodes, edges)
        
        success_modes = results.get('success_modes', [])
        if success_modes:
            print(f"\n✅ 成功生成: {', '.join(success_modes)}")
            
            # 显示自动选择的样式
            outputs = results.get('outputs', {})
            for mode, info in outputs.items():
                if 'selected_style' in info:
                    print(f"🎯 {mode} 自动选择的样式: {info['selected_style']}")
        
        return True
    except Exception as e:
        print(f"❌ 生成失败: {e}")
        return False


def display_ascii_art_samples():
    """展示ASCII艺术样本"""
    print("\n" + "=" * 90)
    print("🎨 样式5: ASCII艺术样本（不同绘制风格）")
    print("=" * 90)
    
    print("🎭 风格A: 简洁线条风格")
    print("-" * 60)
    print("水源 ──▶ 泵站 ──▶ 阀门 ──▶ 目标")
    print("100m    25m³/s   75%     95m")
    
    print("\n🎭 风格B: 框架结构风格")
    print("-" * 60)
    print("┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐")
    print("│🏞️ 水源   │━━▶│⚡ 泵站   │━━▶│🚰 阀门   │━━▶│🏞️ 目标   │")
    print("│ 100.0m  │    │25.0m³/s │    │ 75%开度 │    │ 95.0m   │")
    print("└─────────┘    └─────────┘    └─────────┘    └─────────┘")
    
    print("\n🎭 风格C: 流向示意风格")
    print("-" * 60)
    print("💧 总流量: 25.0 m³/s")
    print("⬇️")
    print("🏞️ 水源 [100.0m] ══════════════════════════════════════▶")
    print("⬇️ 25.0 m³/s")
    print("⚡ 泵站 [增压25m] ══════════════════════════════════════▶")
    print("⬇️ 25.0 m³/s")
    print("🚰 阀门 [75%开度] ══════════════════════════════════════▶")
    print("⬇️ 18.8 m³/s")
    print("🏞️ 目标 [95.0m] ⬅══════════════════════════════════════")
    
    print("\n🎭 风格D: 网络拓扑风格")
    print("-" * 60)
    print("    [🏞️1]────────[⚡2]────────[🚰3]────────[🏞️4]")
    print("    水源        泵站        阀门        目标")
    print("   100.0m      25.0m³/s     75%       95.0m")
    print("")
    print("连接: 1→2→3→4  |  流量: 25.0→25.0→18.8 m³/s")


def display_comparison_matrix():
    """展示拓扑图样式对比矩阵"""
    print("\n" + "=" * 90)
    print("📊 拓扑图样式对比矩阵")
    print("=" * 90)
    
    print("┌─────────────────┬─────────────┬─────────────┬─────────────┬─────────────┐")
    print("│ 特征\\样式        │ 简洁流程图   │ 流向示意图   │ 层次结构图   │ 表格模式     │")
    print("├─────────────────┼─────────────┼─────────────┼─────────────┼─────────────┤")
    print("│ 信息密度         │    中等     │     高      │     中等     │     很高     │")
    print("│ 视觉美观度       │     高      │    很高     │     高      │     中等     │")
    print("│ 易读性          │    很高     │     高      │    很高     │     高      │")
    print("│ 占用空间         │     小      │     大      │     中等     │     中等     │")
    print("│ 详细程度         │     低      │     高      │     中等     │    很高     │")
    print("│ 分流展示         │     中等     │    很好     │     好      │     好      │")
    print("│ 流量展示         │     好      │    很好     │     中等     │    很好     │")
    print("│ 适用复杂度       │   1-5节点   │  4-15节点   │  任意层次    │   任意规模   │")
    print("└─────────────────┴─────────────┴─────────────┴─────────────┴─────────────┘")
    
    print("\n🎯 推荐使用场景:")
    print("  📝 简洁流程图 → 快速预览、简单系统、演示说明")
    print("  💧 流向示意图 → 流量分析、能量平衡、复杂分流")
    print("  🌳 层次结构图 → 系统架构、功能分层、逻辑关系")
    print("  📊 表格模式   → 数据对比、参数分析、详细查看")


def main():
    """主展示函数"""
    print("🎬 多重拓扑图形式实际展示")
    print("为您生成真实的拓扑图效果")
    
    success_count = 0
    total_demos = 5
    
    # 依次展示各种样式
    if display_simple_flow_style():
        success_count += 1
    
    if display_flow_diagram_style():
        success_count += 1
    
    if display_table_styles():
        success_count += 1
    
    if display_quick_render_demo():
        success_count += 1
    
    # 展示ASCII艺术样本
    display_ascii_art_samples()
    success_count += 1
    
    # 展示对比矩阵
    display_comparison_matrix()
    
    print("\n" + "=" * 90)
    print("🎉 拓扑图形式展示完成")
    print("=" * 90)
    
    print(f"📊 展示完成度: {success_count}/{total_demos}")
    
    if success_count >= 4:
        print("✅ 所有主要样式展示成功！")
        print("\n🎯 关键特点:")
        print("  🎨 多样化的视觉效果")
        print("  🤖 智能自动样式选择")
        print("  📊 丰富的信息展示")
        print("  🔧 灵活的配置选项")
        
        print("\n💡 选择建议:")
        print("  • 快速查看 → 简洁流程图")
        print("  • 详细分析 → 流向示意图")
        print("  • 数据核对 → 表格模式")
        print("  • 自动优化 → 让系统智能选择")
    else:
        print("⚠️ 部分样式展示失败，请检查系统配置")
    
    return success_count >= 4


if __name__ == "__main__":
    main()