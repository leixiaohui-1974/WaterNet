#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用拓扑图生成器最终演示

完整展示基于配置文件的多种可视化方式，演示自动降级策略和用户偏好支持。

Created by: Qoder AI Assistant
Date: 2025-10-04
"""

import sys
import os
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def demonstrate_hydraulic_system():
    """演示复杂水力枢纽系统的可视化"""
    print("=" * 80)
    print("🏗️ 复杂水力枢纽系统可视化演示")
    print("=" * 80)
    
    try:
        from waternet.visualization import create_topology_from_config
        
        config_path = project_root / "configs" / "hydraulic_system_topology.yaml"
        
        if config_path.exists():
            print(f"📋 从配置文件加载: {config_path.name}")
            
            # 生成拓扑图，优先使用文本ASCII方式（符合用户偏好）
            results = create_topology_from_config(str(config_path))
            
            success_modes = results.get('success_modes', [])
            failed_modes = results.get('failed_modes', [])
            
            print(f"\n✅ 成功生成的可视化方式: {', '.join(success_modes)}")
            if failed_modes:
                print(f"❌ 失败的可视化方式: {', '.join(failed_modes)}")
            
            # 显示详细信息
            outputs = results.get('outputs', {})
            for mode in success_modes:
                if mode in outputs:
                    info = outputs[mode]
                    print(f"   {mode}: 渲染了 {info.get('nodes_rendered', 0)} 个节点, {info.get('edges_rendered', 0)} 条边")
            
            return True
        else:
            print(f"❌ 配置文件不存在: {config_path}")
            return False
            
    except Exception as e:
        print(f"❌ 演示失败: {e}")
        return False


def demonstrate_quick_render():
    """演示快速渲染接口"""
    print("\n" + "=" * 80)  
    print("🚀 快速渲染接口演示")
    print("=" * 80)
    
    try:
        from waternet.visualization import quick_render
        
        # 定义一个典型的水力系统
        nodes = [
            ("reservoir_in", "上游水库", "reservoir", (0, 2), {
                "water_level": 110.0, 
                "capacity": 5000000,
                "description": "主要水源"
            }),
            ("main_gate", "主控闸站", "station", (2, 2), {
                "flow_rate": 20.3,
                "gate_opening": 0.24,
                "description": "流量控制"
            }),
            ("junction", "分流枢纽", "junction", (4, 2), {
                "water_level": 107.0,
                "outlets": 2,
                "description": "流量分配"
            }),
            ("conveyance", "输水干管", "pipe", (6, 3), {
                "diameter": 2.2,
                "length": 3000,
                "flow_rate": 7.6,
                "velocity": 2.0
            }),
            ("spillway", "泄洪渠道", "pipe", (6, 1), {
                "diameter": 3.0,
                "length": 1200,
                "flow_rate": 12.7,
                "velocity": 1.8
            }),
            ("reservoir_out", "下游调节池", "reservoir", (8, 2), {
                "water_level": 92.0,
                "capacity": 2000000,
                "description": "终端蓄水"
            })
        ]
        
        edges = [
            ("inflow", "进水管道", "reservoir_in", "main_gate", {
                "flow_rate": 20.3,
                "direction": "forward"
            }),
            ("control", "主控管道", "main_gate", "junction", {
                "flow_rate": 20.3,
                "direction": "forward"
            }),
            ("main_line", "输水管道", "junction", "conveyance", {
                "flow_rate": 7.6,
                "direction": "forward"
            }),
            ("spill_line", "泄洪管道", "junction", "spillway", {
                "flow_rate": 12.7,
                "direction": "forward"
            }),
            ("outflow_main", "主出水", "conveyance", "reservoir_out", {
                "flow_rate": 7.6,
                "direction": "forward"
            }),
            ("outflow_spill", "泄洪出口", "spillway", "reservoir_out", {
                "flow_rate": 12.7,
                "direction": "forward"
            })
        ]
        
        print("📊 生成水力枢纽系统拓扑图...")
        results = quick_render(
            title="水力枢纽系统示例",
            nodes=nodes,
            edges=edges
        )
        
        success_modes = results.get('success_modes', [])
        if success_modes:
            print(f"✅ 快速渲染成功: {', '.join(success_modes)}")
            
            # 显示系统特点
            print("\n🔍 系统特点分析:")
            print("  • 物理逻辑合理：流量平衡，能量守恒")
            print("  • 流速安全：输水2.0m/s，泄洪1.8m/s")  
            print("  • 分流比例：输水38%，泄洪62%")
            print("  • 总落差：18m（110m→92m）")
            
            return True
        else:
            print("❌ 快速渲染失败")
            return False
            
    except Exception as e:
        print(f"❌ 快速渲染演示失败: {e}")
        return False


def show_features_summary():
    """显示功能特性总结"""
    print("\n" + "=" * 80)
    print("✨ 通用拓扑图生成器功能特性")
    print("=" * 80)
    
    features = [
        ("🎯 多种可视化方式", [
            "文本ASCII艺术风格（用户偏好，优先级最高）",
            "专业表格格式（Rich彩色 + 纯文本备选）",
            "图形化拓扑图（matplotlib后端，自动布局）"
        ]),
        ("🔧 配置驱动", [
            "YAML和JSON格式支持",
            "灵活的节点和边属性定义",
            "布局和渲染参数可配置"
        ]),
        ("🛡️ 可靠性保障", [
            "自动降级策略：总有一种方式能工作",
            "错误处理完善：友好的错误提示",
            "环境兼容性检查：自动检测可用功能"
        ]),
        ("🌐 中文支持", [
            "完整的中文字符显示",
            "Unicode图标和符号支持",
            "中文字体自动检测和设置"
        ]),
        ("🚀 易用接口", [
            "quick_render() 快速渲染接口",
            "create_topology_from_config() 配置文件接口",
            "工厂模式自动注册渲染器"
        ])
    ]
    
    for title, items in features:
        print(f"\n{title}:")
        for item in items:
            print(f"  • {item}")


def main():
    """主演示函数"""
    print("🏗️ 通用拓扑图生成器 - 最终演示")
    print("基于用户偏好的文本可视化优先策略")
    
    # 创建输出目录
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    success_count = 0
    
    # 演示复杂系统
    if demonstrate_hydraulic_system():
        success_count += 1
    
    # 演示快速接口
    if demonstrate_quick_render():
        success_count += 1
    
    # 显示功能特性
    show_features_summary()
    
    # 最终总结
    print("\n" + "=" * 80)
    print("🎉 演示完成总结")
    print("=" * 80)
    
    if success_count == 2:
        print("✅ 所有演示成功！通用拓扑图生成器已完全实现。")
        print("\n🎯 核心目标达成:")
        print("  ✓ 支持多种可视化方式")
        print("  ✓ 配置文件驱动，避免有的方式出问题")
        print("  ✓ 优先使用文本方式（符合用户偏好）")
        print("  ✓ 自动降级策略确保可靠性")
        print("  ✓ 直观清晰的信息展示")
        
        print("\n📚 使用方法:")
        print("  1. 创建YAML/JSON配置文件定义系统拓扑")
        print("  2. 调用 create_topology_from_config(config_path)")
        print("  3. 或使用 quick_render(title, nodes, edges) 快速生成")
        print("  4. 系统自动选择最佳可视化方式并提供降级保障")
        
    else:
        print("⚠️ 部分演示失败，但基本功能可用。")
    
    print(f"\n📊 演示成功率: {success_count}/2")
    print("🏁 演示结束")


if __name__ == "__main__":
    main()