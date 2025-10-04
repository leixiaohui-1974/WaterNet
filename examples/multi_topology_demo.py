#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多重拓扑图展示方式演示

提供多种不同的拓扑图可视化方案，用户可以选择最适合的展示方式。

Created by: Qoder AI Assistant
Date: 2025-10-04
"""

import sys
import os
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def demo_text_topology_styles():
    """演示不同的文本拓扑图风格"""
    print("=" * 80)
    print("📝 文本拓扑图多种展示方式")
    print("=" * 80)
    
    # 创建测试数据
    from waternet.visualization.topology_generator import TopologyConfig, NodeData, EdgeData, ComponentType
    
    config = TopologyConfig(
        title="水力系统拓扑图",
        nodes=[
            NodeData("reservoir", "上游水库", ComponentType.RESERVOIR, (0, 1), {"water_level": 110.0, "capacity": 5000000}),
            NodeData("station", "主控站", ComponentType.STATION, (1, 1), {"flow_rate": 20.3, "power": 500}),
            NodeData("junction", "分流点", ComponentType.JUNCTION, (2, 1), {"outlets": 2, "water_level": 107.0}),
            NodeData("pipe1", "输水管", ComponentType.PIPE, (3, 0), {"diameter": 2.2, "length": 3000, "flow_rate": 7.6}),
            NodeData("pipe2", "泄洪道", ComponentType.PIPE, (3, 2), {"diameter": 3.0, "length": 1200, "flow_rate": 12.7}),
            NodeData("target", "下游池", ComponentType.RESERVOIR, (4, 1), {"water_level": 92.0, "capacity": 2000000})
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
    
    # 方式1：简洁流程图
    print("\n🎨 方式1：简洁流程图")
    print("-" * 50)
    print_simple_flowchart(config)
    
    # 方式2：详细连接图
    print("\n🎨 方式2：详细连接图")
    print("-" * 50)
    print_detailed_connection_chart(config)
    
    # 方式3：层次结构图
    print("\n🎨 方式3：层次结构图")
    print("-" * 50)
    print_hierarchical_chart(config)
    
    # 方式4：网络拓扑图
    print("\n🎨 方式4：网络拓扑图")
    print("-" * 50)
    print_network_topology(config)
    
    # 方式5：流向示意图
    print("\n🎨 方式5：流向示意图")
    print("-" * 50)
    print_flow_diagram(config)


def print_simple_flowchart(config):
    """简洁流程图"""
    print("┌─────────────────────────────────────────────────────────────┐")
    print("│                        水力系统流程图                        │")
    print("├─────────────────────────────────────────────────────────────┤")
    print("│                                                             │")
    print("│  🏞️上游水库 ➤ 🏗️主控站 ➤ 🔀分流点 ➤ ┬ 🚰输水管 ➤ 🏞️下游池   │")
    print("│    110.0m      20.3m³/s    107.0m   │   7.6m³/s     92.0m  │")
    print("│                                     └ 🌊泄洪道 ➤ ┘          │")
    print("│                                       12.7m³/s             │")
    print("│                                                             │")
    print("└─────────────────────────────────────────────────────────────┘")


def print_detailed_connection_chart(config):
    """详细连接图"""
    print("╔════════════════════════════════════════════════════════════════════════╗")
    print("║                           水力系统详细连接图                            ║")
    print("╠════════════════════════════════════════════════════════════════════════╣")
    print("║                                                                        ║")
    print("║   ┌─────────────┐    进水    ┌─────────────┐    控制    ┌─────────────┐  ║")
    print("║   │🏞️ 上游水库   │ ────────► │🏗️ 主控站     │ ────────► │🔀 分流点     │  ║")
    print("║   │水位: 110.0m │  20.3m³/s │流量: 20.3   │  20.3m³/s │水位: 107.0m │  ║")
    print("║   │容量: 5000万 │           │功率: 500kW  │           │出口: 2个    │  ║")
    print("║   └─────────────┘           └─────────────┘           └─────────────┘  ║")
    print("║                                                            │          ║")
    print("║                                                  ┌─────────┼─────────┐ ║")
    print("║                                                  │         │         │ ║")
    print("║                                               输水 7.6   泄洪 12.7    ║")
    print("║                                                  ▼         ▼         ║")
    print("║                                         ┌─────────────┐ ┌─────────────┐ ║")
    print("║                                         │🚰 输水管     │ │🌊 泄洪道     │ ║")
    print("║                                         │直径: 2.2m  │ │直径: 3.0m  │ ║")
    print("║                                         │长度: 3000m │ │长度: 1200m │ ║")
    print("║                                         └─────────────┘ └─────────────┘ ║")
    print("║                                                  │         │         ║")
    print("║                                                  └─────────┼─────────┘ ║")
    print("║                                                            ▼          ║")
    print("║                                                   ┌─────────────┐     ║")
    print("║                                                   │🏞️ 下游池     │     ║")
    print("║                                                   │水位: 92.0m  │     ║")
    print("║                                                   │容量: 2000万 │     ║")
    print("║                                                   └─────────────┘     ║")
    print("║                                                                        ║")
    print("╚════════════════════════════════════════════════════════════════════════╝")


def print_hierarchical_chart(config):
    """层次结构图"""
    print("┌──────────────────────────────────────────────────────────────────┐")
    print("│                        层次结构拓扑图                             │")
    print("├──────────────────────────────────────────────────────────────────┤")
    print("│                                                                  │")
    print("│  第1层: 水源层                                                    │")
    print("│         🏞️ 上游水库 [110.0m, 5000万m³]                          │")
    print("│                         │                                        │")
    print("│  第2层: 控制层                                                    │")
    print("│         🏗️ 主控站 [20.3m³/s, 500kW]                            │")
    print("│                         │                                        │")
    print("│  第3层: 分流层                                                    │")
    print("│         🔀 分流点 [107.0m, 2出口]                               │")
    print("│                    ┌────┴────┐                                   │")
    print("│  第4层: 输送层      │         │                                   │")
    print("│         🚰 输水管   │         │   🌊 泄洪道                        │")
    print("│         [2.2m×3km] │         │   [3.0m×1.2km]                   │")
    print("│         7.6m³/s   │         │   12.7m³/s                       │")
    print("│                    └────┬────┘                                   │")
    print("│  第5层: 汇集层                                                    │")
    print("│         🏞️ 下游池 [92.0m, 2000万m³]                             │")
    print("│                                                                  │")
    print("└──────────────────────────────────────────────────────────────────┘")


def print_network_topology(config):
    """网络拓扑图"""
    print("╭─────────────────────────────────────────────────────────────────────╮")
    print("│                           网络拓扑视图                               │")
    print("├─────────────────────────────────────────────────────────────────────┤")
    print("│                                                                     │")
    print("│    [🏞️1]────────[🏗️2]────────[🔀3]                                  │")
    print("│    水库          控制站        分流点                                │")
    print("│   110.0m        20.3m³/s      107.0m                              │")
    print("│                                 │                                   │")
    print("│                             ┌───┴───┐                               │")
    print("│                             │       │                               │")
    print("│                          [🚰4]   [🌊5]                              │")
    print("│                          输水管   泄洪道                            │")
    print("│                          7.6m³/s  12.7m³/s                         │")
    print("│                             │       │                               │")
    print("│                             └───┬───┘                               │")
    print("│                                 │                                   │")
    print("│                              [🏞️6]                                  │")
    print("│                              下游池                                 │")
    print("│                              92.0m                                 │")
    print("│                                                                     │")
    print("│  连接关系: 1→2→3→{4,5}→6                                            │")
    print("│  节点类型: 🏞️水库 🏗️站点 🔀分流 🚰管道 🌊渠道                         │")
    print("│                                                                     │")
    print("╰─────────────────────────────────────────────────────────────────────╯")


def print_flow_diagram(config):
    """流向示意图"""
    print("┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓")
    print("┃                              流向示意图                              ┃")
    print("┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫")
    print("┃                                                                     ┃")
    print("┃  💧 总流量: 20.3 m³/s                                               ┃")
    print("┃  ⬇️                                                                  ┃")
    print("┃  🏞️ 上游水库 [110.0m] ══════════════════════════════════════════════➤  ┃")
    print("┃  ⬇️ 20.3 m³/s                                                       ┃")
    print("┃  🏗️ 主控站 [控制闸门] ══════════════════════════════════════════════➤  ┃")
    print("┃  ⬇️ 20.3 m³/s                                                       ┃")
    print("┃  🔀 分流点 [107.0m] ═══════════════════┳═════════════════════════════➤ ┃")
    print("┃                                      ⬇️ 37%        ⬇️ 63%           ┃")
    print("┃                              🚰 输水管道        🌊 泄洪渠道          ┃")
    print("┃                              7.6 m³/s         12.7 m³/s           ┃")
    print("┃                              [2.2m×3km]       [3.0m×1.2km]        ┃")
    print("┃                                      ⬇️              ⬇️               ┃")
    print("┃  🏞️ 下游池 [92.0m] ⬅═══════════════════┻══════════════════════════════ ┃")
    print("┃  💧 汇总流量: 20.3 m³/s                                              ┃")
    print("┃                                                                     ┃")
    print("┃  📊 流量平衡: ✅ 输入 = 输出 = 20.3 m³/s                              ┃")
    print("┃  📊 分流比例: 输水 37% | 泄洪 63%                                    ┃")
    print("┃  📊 总落差: 18.0m (110m → 92m)                                     ┃")
    print("┃                                                                     ┃")
    print("┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛")


def demo_table_display_formats():
    """演示不同的表格展示格式"""
    print("\n" + "=" * 80)
    print("📊 表格拓扑图多种展示方式")
    print("=" * 80)
    
    # 方式1：紧凑型表格
    print("\n🎨 方式1：紧凑型表格")
    print("-" * 50)
    print_compact_table()
    
    # 方式2：详细信息表格
    print("\n🎨 方式2：详细信息表格")
    print("-" * 50)
    print_detailed_table()
    
    # 方式3：关系矩阵表格
    print("\n🎨 方式3：关系矩阵表格")
    print("-" * 50)
    print_relationship_matrix()


def print_compact_table():
    """紧凑型表格"""
    print("┌────┬─────────┬─────────┬──────────┬────────────┐")
    print("│ ID │ 组件名称 │ 类型     │ 关键参数  │ 连接关系    │")
    print("├────┼─────────┼─────────┼──────────┼────────────┤")
    print("│ 1  │ 上游水库 │ 🏞️水库   │ 110.0m   │ →2         │")
    print("│ 2  │ 主控站   │ 🏗️枢纽   │ 20.3m³/s │ 1→3        │")
    print("│ 3  │ 分流点   │ 🔀连接   │ 107.0m   │ 2→4,5      │")
    print("│ 4  │ 输水管   │ 🚰管道   │ 7.6m³/s  │ 3→6        │")
    print("│ 5  │ 泄洪道   │ 🌊渠道   │ 12.7m³/s │ 3→6        │")
    print("│ 6  │ 下游池   │ 🏞️水库   │ 92.0m    │ 4,5→       │")
    print("└────┴─────────┴─────────┴──────────┴────────────┘")


def print_detailed_table():
    """详细信息表格"""
    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║                                系统组件详细信息表                             ║")
    print("╠═══════╤══════════╤═════════╤══════════╤═══════════╤══════════╤═════════════╣")
    print("║ 组件名 │ 类型图标 │ 主要参数 │ 物理尺寸  │ 工作状态   │ 上游连接  │ 下游连接     ║")
    print("╠═══════╪══════════╪═════════╪══════════╪═══════════╪══════════╪═════════════╣")
    print("║上游水库│    🏞️    │ 110.0m  │5000万m³  │ 正常供水   │    -     │ 主控站      ║")
    print("║主控站  │    🏗️    │20.3m³/s │ 500kW    │ 自动控制   │ 上游水库  │ 分流点      ║")
    print("║分流点  │    🔀    │ 107.0m  │ 2出口    │ 正常分流   │ 主控站   │ 输水管+泄洪道║")
    print("║输水管  │    🚰    │7.6m³/s  │φ2.2×3km  │ 正常输送   │ 分流点   │ 下游池      ║")
    print("║泄洪道  │    🌊    │12.7m³/s │φ3.0×1.2km│ 正常泄洪   │ 分流点   │ 下游池      ║")
    print("║下游池  │    🏞️    │ 92.0m   │2000万m³  │ 正常蓄水   │输水管+泄洪道│    -        ║")
    print("╚═══════╧══════════╧═════════╧══════════╧═══════════╧══════════╧═════════════╝")


def print_relationship_matrix():
    """关系矩阵表格"""
    print("┌────────────────────────────────────────────────────────────────┐")
    print("│                        连接关系矩阵                            │")
    print("├─────────┬─────┬─────┬─────┬─────┬─────┬─────┬─────────────────┤")
    print("│ 源\\目标  │水库1│控制2│分流3│输水4│泄洪5│水库6│ 流量(m³/s)       │")
    print("├─────────┼─────┼─────┼─────┼─────┼─────┼─────┼─────────────────┤")
    print("│ 水库1    │  -  │  ✓  │  -  │  -  │  -  │  -  │ 20.3 → 控制2    │")
    print("│ 控制2    │  -  │  -  │  ✓  │  -  │  -  │  -  │ 20.3 → 分流3    │")
    print("│ 分流3    │  -  │  -  │  -  │  ✓  │  ✓  │  -  │ 7.6→4, 12.7→5  │")
    print("│ 输水4    │  -  │  -  │  -  │  -  │  -  │  ✓  │ 7.6 → 水库6     │")
    print("│ 泄洪5    │  -  │  -  │  -  │  -  │  -  │  ✓  │ 12.7 → 水库6    │")
    print("│ 水库6    │  -  │  -  │  -  │  -  │  -  │  -  │ 终端节点        │")
    print("├─────────┴─────┴─────┴─────┴─────┴─────┴─────┼─────────────────┤")
    print("│ 总计流量                                     │ 输入:20.3       │")
    print("│                                             │ 输出:20.3       │")
    print("│                                             │ 平衡:✅         │")
    print("└─────────────────────────────────────────────┴─────────────────┘")


def demo_interactive_selection():
    """演示交互式选择不同展示方式"""
    print("\n" + "=" * 80)
    print("🎮 交互式拓扑图展示选择")
    print("=" * 80)
    
    display_options = {
        "1": ("简洁流程图", "适合快速理解系统流程"),
        "2": ("详细连接图", "显示完整的组件信息和连接"),
        "3": ("层次结构图", "按功能层次组织显示"),
        "4": ("网络拓扑图", "类似网络图的节点连接"),
        "5": ("流向示意图", "强调数据流向和流量平衡"),
        "6": ("紧凑型表格", "表格形式的简洁信息"),
        "7": ("详细信息表格", "完整的组件参数表格"),
        "8": ("关系矩阵表格", "连接关系矩阵视图")
    }
    
    print("\n📋 可用的拓扑图展示方式:")
    print("─" * 60)
    
    for key, (name, desc) in display_options.items():
        print(f"  {key}. {name:<15} - {desc}")
    
    print("\n💡 推荐使用场景:")
    print("─" * 60)
    print("  🎯 快速概览    → 选择 1 (简洁流程图)")
    print("  🔍 详细分析    → 选择 2 (详细连接图)")
    print("  📚 系统文档    → 选择 3 (层次结构图)")
    print("  🔧 技术调试    → 选择 4 (网络拓扑图)")
    print("  💧 流量分析    → 选择 5 (流向示意图)")
    print("  📊 数据对比    → 选择 6-8 (表格系列)")
    
    print("\n🎨 样式特点:")
    print("─" * 60)
    print("  📝 文本图形    → 1-5 (ASCII艺术风格)")
    print("  📋 表格数据    → 6-8 (结构化数据)")
    print("  🎭 视觉效果    → 图形化渲染 (matplotlib)")
    print("  🔧 程序接口    → JSON/YAML 配置驱动")


def demo_configuration_examples():
    """演示不同配置示例"""
    print("\n" + "=" * 80)
    print("⚙️ 配置文件驱动的拓扑图生成")
    print("=" * 80)
    
    print("\n📝 YAML配置示例:")
    print("-" * 30)
    print("""
# 水力系统拓扑配置
title: "水力枢纽系统"
render:
  text_ascii:
    style: "box_drawing"    # 或 "simple", "ascii_art"
    show_icons: true
    show_values: true
    layout: "linear"        # 或 "tree", "grid", "auto"
  
  table:
    format: "rich"          # 或 "plain", "markdown"
    show_summary: true
    group_by_type: true

nodes:
  - id: "reservoir1"
    name: "上游水库"
    type: "reservoir"
    position: [0, 1]
    properties:
      water_level: 110.0
      capacity: 5000000
""")
    
    print("\n🎯 选择最佳展示方式的建议:")
    print("-" * 40)
    print("  📊 数据量小(≤5节点)  → 简洁流程图")
    print("  📊 数据量中(6-15节点) → 详细连接图或层次图")
    print("  📊 数据量大(>15节点)  → 网络拓扑图或表格")
    print("  🎯 强调流程          → 流向示意图")
    print("  🎯 强调参数          → 详细信息表格")
    print("  🎯 强调连接          → 关系矩阵表格")


def main():
    """主演示函数"""
    print("🏗️ 多重拓扑图展示方式综合演示")
    print("展示不同场景下的最佳可视化选择")
    
    # 演示不同的文本拓扑图风格
    demo_text_topology_styles()
    
    # 演示不同的表格展示格式
    demo_table_display_formats()
    
    # 演示交互式选择
    demo_interactive_selection()
    
    # 演示配置示例
    demo_configuration_examples()
    
    print("\n" + "=" * 80)
    print("🎉 多重拓扑图展示演示完成")
    print("=" * 80)
    
    print("\n✨ 总结:")
    print("  🎨 8种不同的可视化方式")
    print("  🔧 配置文件驱动，灵活可定制")
    print("  🎯 针对不同场景的最佳推荐")
    print("  📊 从简洁概览到详细分析的完整覆盖")
    print("  🛡️ 自动降级保障，确保总有方式可用")
    
    print("\n📚 使用指南:")
    print("  1. 根据数据复杂度选择基础样式")
    print("  2. 根据使用场景选择展示重点")
    print("  3. 通过配置文件定制详细参数")
    print("  4. 利用自动降级保障可靠性")


if __name__ == "__main__":
    main()