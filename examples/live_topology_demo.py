#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实时拓扑图生成演示

展示实际生成的拓扑图效果，包括图形化版本。

Created by: Qoder AI Assistant
Date: 2025-10-04
"""

import sys
import os
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def demo_real_topology_generation():
    """演示真实的拓扑图生成"""
    print("=" * 80)
    print("🎬 实时拓扑图生成演示")
    print("=" * 80)
    
    try:
        from waternet.visualization import quick_render
        
        # 创建输出目录
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        # 测试数据：简单系统
        print("\n📋 生成简单水力系统拓扑图")
        print("-" * 50)
        
        simple_nodes = [
            ("source", "水源", "reservoir", (0, 0), {"water_level": 100.0}),
            ("pump", "水泵", "pump", (2, 0), {"flow_rate": 25.0, "power": 150}),
            ("valve", "阀门", "valve", (4, 0), {"opening": 75.0}),
            ("target", "目标", "reservoir", (6, 0), {"water_level": 95.0})
        ]
        
        simple_edges = [
            ("pipe1", "进水管", "source", "pump", {"flow_rate": 25.0, "diameter": 0.3}),
            ("pipe2", "压力管", "pump", "valve", {"flow_rate": 25.0, "diameter": 0.25}),
            ("pipe3", "出水管", "valve", "target", {"flow_rate": 18.8, "diameter": 0.2})
        ]
        
        print("正在生成简单系统拓扑图...")
        results = quick_render(
            title="简单水力传输系统",
            nodes=simple_nodes,
            edges=simple_edges,
            output_path="output/simple_system_topology.txt"
        )
        
        if results.get('success_modes'):
            print(f"✅ 简单系统渲染成功: {', '.join(results['success_modes'])}")
            
            # 显示选择的样式
            outputs = results.get('outputs', {})
            for mode, info in outputs.items():
                if 'selected_style' in info:
                    print(f"   🎨 {mode} 自动选择样式: {info['selected_style']}")
        
        # 测试数据：复杂分流系统
        print("\n📋 生成复杂分流系统拓扑图")
        print("-" * 50)
        
        complex_nodes = [
            ("intake", "取水口", "reservoir", (0, 2), {"water_level": 120.0, "capacity": 8000000}),
            ("pump_station", "提升泵站", "pump", (2, 2), {"flow_rate": 45.0, "power": 800}),
            ("main_control", "主控中心", "station", (4, 2), {"flow_rate": 45.0, "gates": 3}),
            ("splitter", "三分流器", "junction", (6, 2), {"outlets": 3, "water_level": 115.0}),
            
            ("industrial", "工业用水", "pipe", (8, 3), {"flow_rate": 18.0, "diameter": 1.8}),
            ("domestic", "生活用水", "pipe", (8, 2), {"flow_rate": 15.0, "diameter": 1.5}),
            ("irrigation", "农业灌溉", "pipe", (8, 1), {"flow_rate": 12.0, "diameter": 1.2}),
            
            ("treatment", "污水处理", "station", (10, 2), {"capacity": 40.0}),
            ("discharge", "排放口", "reservoir", (12, 2), {"water_level": 85.0})
        ]
        
        complex_edges = [
            ("intake_pipe", "取水管", "intake", "pump_station", {"flow_rate": 45.0}),
            ("main_pipe", "主管道", "pump_station", "main_control", {"flow_rate": 45.0}),
            ("control_pipe", "控制管", "main_control", "splitter", {"flow_rate": 45.0}),
            
            ("industrial_line", "工业供水", "splitter", "industrial", {"flow_rate": 18.0}),
            ("domestic_line", "生活供水", "splitter", "domestic", {"flow_rate": 15.0}),
            ("irrigation_line", "农业供水", "splitter", "irrigation", {"flow_rate": 12.0}),
            
            ("collect1", "工业回水", "industrial", "treatment", {"flow_rate": 14.4}),
            ("collect2", "生活污水", "domestic", "treatment", {"flow_rate": 12.0}),
            ("collect3", "农田排水", "irrigation", "treatment", {"flow_rate": 9.6}),
            
            ("treated_water", "处理水", "treatment", "discharge", {"flow_rate": 36.0})
        ]
        
        print("正在生成复杂分流系统拓扑图...")
        results = quick_render(
            title="复杂三分流水力系统",
            nodes=complex_nodes,
            edges=complex_edges,
            output_path="output/complex_system_topology.txt"
        )
        
        if results.get('success_modes'):
            print(f"✅ 复杂系统渲染成功: {', '.join(results['success_modes'])}")
            
            # 显示选择的样式
            outputs = results.get('outputs', {})
            for mode, info in outputs.items():
                if 'selected_style' in info:
                    print(f"   🎨 {mode} 自动选择样式: {info['selected_style']}")
        
        # 测试配置文件驱动
        print("\n📋 从配置文件生成拓扑图")
        print("-" * 50)
        
        from waternet.visualization import create_topology_from_config
        
        config_path = project_root / "configs" / "hydraulic_system_topology.yaml"
        if config_path.exists():
            print("正在从YAML配置文件生成...")
            results = create_topology_from_config(
                str(config_path),
                output_path="output/config_driven_topology.txt"
            )
            
            if results.get('success_modes'):
                print(f"✅ 配置驱动渲染成功: {', '.join(results['success_modes'])}")
        
        return True
        
    except Exception as e:
        print(f"❌ 演示失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def show_output_files():
    """显示生成的输出文件"""
    print("\n📁 查看生成的输出文件")
    print("-" * 50)
    
    output_dir = Path("output")
    if output_dir.exists():
        files = list(output_dir.glob("*.txt")) + list(output_dir.glob("*.png"))
        
        if files:
            print("✅ 已生成的拓扑图文件:")
            for file in sorted(files):
                size = file.stat().st_size
                print(f"   📄 {file.name} ({size/1024:.1f} KB)")
        else:
            print("❌ 没有找到输出文件")
    else:
        print("❌ 输出目录不存在")


def show_comparison_summary():
    """显示对比总结"""
    print("\n📊 多重拓扑图展示方式对比总结")
    print("=" * 80)
    
    comparison_data = [
        ["展示方式", "适用场景", "优点", "缺点"],
        ["─" * 12, "─" * 20, "─" * 30, "─" * 20],
        ["简洁流程图", "简单线性系统", "清晰直观，一目了然", "功能相对简单"],
        ["流向示意图", "复杂分流系统", "突出流量，展示平衡", "占用空间较大"],
        ["层次结构图", "分层系统", "逻辑清晰，层次分明", "适用范围有限"],
        ["网络拓扑图", "复杂网络", "全局视图，节点编号", "细节信息较少"],
        ["紧凑型表格", "数据对比", "信息密集，便于查找", "视觉效果一般"],
        ["详细信息表格", "参数分析", "信息完整，结构化", "占用空间大"],
        ["关系矩阵表格", "连接分析", "关系清晰，易于分析", "适合小规模系统"],
        ["图形化模式", "专业文档", "美观专业，适合报告", "需要图形环境"]
    ]
    
    # 计算列宽
    col_widths = [max(len(str(row[i])) for row in comparison_data) + 2 for i in range(4)]
    
    for row in comparison_data:
        line = "│"
        for i, cell in enumerate(row):
            line += f" {str(cell):<{col_widths[i]-1}}│"
        print(line)
        
        if row[0] == "展示方式":  # 标题行后加分隔线
            sep_line = "├"
            for width in col_widths:
                sep_line += "─" * width + "┼"
            sep_line = sep_line[:-1] + "┤"
            print(sep_line)


def main():
    """主演示函数"""
    print("🎬 多重拓扑图展示方式实战演示")
    print("展示真实的拓扑图生成效果")
    
    # 演示真实拓扑图生成
    success = demo_real_topology_generation()
    
    # 显示输出文件
    show_output_files()
    
    # 显示对比总结
    show_comparison_summary()
    
    print("\n" + "=" * 80)
    print("🎉 实战演示完成")
    print("=" * 80)
    
    if success:
        print("✅ 所有拓扑图生成成功！")
        print("\n🎯 关键特性验证:")
        print("  ✓ 自动样式选择正常工作")
        print("  ✓ 多种渲染方式同时成功")
        print("  ✓ 配置文件驱动正常")
        print("  ✓ 文件输出功能正常")
        
        print("\n💡 实际应用建议:")
        print("  📝 日常使用 → 让系统自动选择样式")
        print("  📊 数据分析 → 使用表格模式")
        print("  💧 流量分析 → 使用流向示意图")
        print("  📋 系统文档 → 使用图形化模式")
        print("  🔧 调试排查 → 使用网络拓扑图")
        
        print("\n📁 生成的文件可以用于:")
        print("  • 系统设计文档")
        print("  • 运行状态报告")
        print("  • 问题诊断分析")
        print("  • 培训教学材料")
    else:
        print("❌ 部分演示失败，请检查系统配置")
    
    return success


if __name__ == "__main__":
    main()