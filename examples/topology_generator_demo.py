#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用拓扑图生成器演示

展示多种可视化方式和自动降级策略，演示如何基于配置文件生成不同类型的拓扑图。
即使某种渲染方式失败，也会自动降级到其他可用方式。

Created by: Qoder AI Assistant
Date: 2025-10-04
"""

import sys
import os
import logging
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from waternet.visualization import (
    create_topology_from_config, 
    quick_render, 
    get_generator,
    RenderMode,
    ComponentType
)

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def demo_config_based_generation():
    """演示基于配置文件的拓扑图生成"""
    print("=" * 80)
    print("🏗️ 通用拓扑图生成器演示")
    print("=" * 80)
    print()
    
    config_dir = project_root / "configs"
    
    # 测试复杂水力枢纽系统
    print("📋 测试1: 复杂水力枢纽系统（从YAML配置）")
    print("-" * 50)
    
    hydraulic_config = config_dir / "hydraulic_system_topology.yaml"
    if hydraulic_config.exists():
        results = create_topology_from_config(
            str(hydraulic_config),
            output_path="output/hydraulic_system_topology.txt"
        )
        print_results("复杂水力枢纽系统", results)
    else:
        print(f"❌ 配置文件不存在: {hydraulic_config}")
    
    print()
    
    # 测试简单管道系统  
    print("📋 测试2: 简单管道系统（从JSON配置）")
    print("-" * 50)
    
    pipeline_config = config_dir / "simple_pipeline_topology.json"
    if pipeline_config.exists():
        results = create_topology_from_config(
            str(pipeline_config),
            output_path="output/simple_pipeline_topology.txt"
        )
        print_results("简单管道系统", results)
    else:
        print(f"❌ 配置文件不存在: {pipeline_config}")


def demo_quick_render():
    """演示快速渲染功能"""
    print()
    print("📋 测试3: 快速渲染演示")
    print("-" * 50)
    
    # 定义简单系统
    nodes = [
        ("tank1", "水箱A", "reservoir", (0, 0), {"capacity": 1000, "water_level": 50}),
        ("pump1", "增压泵", "pump", (2, 0), {"power": 150, "efficiency": 0.85}),
        ("valve1", "控制阀", "valve", (4, 0), {"opening": 75, "cv_value": 100}),
        ("tank2", "水箱B", "reservoir", (6, 0), {"capacity": 800, "water_level": 45})
    ]
    
    edges = [
        ("pipe1", "进水管", "tank1", "pump1", {"diameter": 0.3, "flow_rate": 40}),
        ("pipe2", "压力管", "pump1", "valve1", {"diameter": 0.25, "flow_rate": 40}),
        ("pipe3", "出水管", "valve1", "tank2", {"diameter": 0.2, "flow_rate": 30})
    ]
    
    results = quick_render(
        title="快速渲染示例系统",
        nodes=nodes,
        edges=edges,
        output_path="output/quick_render_demo.txt"
    )
    
    print_results("快速渲染演示", results)


def demo_render_mode_priority():
    """演示渲染模式优先级和降级策略"""
    print()
    print("📋 测试4: 渲染模式优先级演示")
    print("-" * 50)
    
    # 创建测试配置
    nodes = [
        ("src", "源头", "reservoir", (0, 1), {"water_level": 100}),
        ("dst", "目标", "reservoir", (4, 1), {"water_level": 95})
    ]
    edges = [("flow", "水流", "src", "dst", {"flow_rate": 25})]
    
    generator = get_generator()
    
    # 测试不同的渲染模式优先级
    test_cases = [
        ("文本ASCII优先", [RenderMode.TEXT_ASCII, RenderMode.TABLE_FORMAT]),
        ("表格优先", [RenderMode.TABLE_FORMAT, RenderMode.TEXT_ASCII]),
        ("图形优先", [RenderMode.GRAPH_MATPLOTLIB, RenderMode.TEXT_ASCII, RenderMode.TABLE_FORMAT]),
        ("全部尝试", [RenderMode.TEXT_ASCII, RenderMode.TABLE_FORMAT, RenderMode.GRAPH_MATPLOTLIB])
    ]
    
    for test_name, preferred_modes in test_cases:
        print(f"\n🔄 {test_name}:")
        results = quick_render(
            title=f"优先级测试 - {test_name}",
            nodes=nodes,
            edges=edges
        )
        
        success_modes = results.get('success_modes', [])
        failed_modes = results.get('failed_modes', [])
        
        print(f"  ✅ 成功: {', '.join(success_modes) if success_modes else '无'}")
        print(f"  ❌ 失败: {', '.join(failed_modes) if failed_modes else '无'}")


def demo_error_handling():
    """演示错误处理和自动降级"""
    print()
    print("📋 测试5: 错误处理演示")
    print("-" * 50)
    
    # 测试无效配置
    print("🔍 测试无效配置处理:")
    results = create_topology_from_config("nonexistent_config.yaml")
    print_results("无效配置", results)
    
    # 测试空系统
    print("\n🔍 测试空系统处理:")
    results = quick_render("空系统测试", [], [])
    print_results("空系统", results)
    
    # 测试不连通系统
    print("\n🔍 测试不连通系统:")
    nodes = [
        ("isolated1", "孤立节点1", "reservoir", (0, 0)),
        ("isolated2", "孤立节点2", "pump", (5, 5))
    ]
    results = quick_render("不连通系统", nodes, [])
    print_results("不连通系统", results)


def print_results(test_name: str, results: dict):
    """打印测试结果"""
    success_modes = results.get('success_modes', [])
    failed_modes = results.get('failed_modes', [])
    errors = results.get('errors', {})
    
    print(f"🎯 {test_name} 结果:")
    
    if success_modes:
        print(f"  ✅ 渲染成功: {', '.join(success_modes)}")
        
        # 显示详细信息
        outputs = results.get('outputs', {})
        for mode in success_modes:
            if mode in outputs:
                info = outputs[mode]
                if 'nodes_rendered' in info:
                    print(f"     {mode}: 节点 {info['nodes_rendered']}, 边 {info['edges_rendered']}")
    else:
        print("  ❌ 所有渲染模式都失败了")
    
    if failed_modes:
        print(f"  ⚠️  渲染失败: {', '.join(failed_modes)}")
        
        # 显示错误信息
        for mode in failed_modes:
            if mode in errors:
                print(f"     {mode}: {errors[mode]}")
    
    if 'config_load' in errors:
        print(f"  ❌ 配置加载失败: {errors['config_load']}")


def show_available_renderers():
    """显示可用的渲染器"""
    print()
    print("📊 可用渲染器状态:")
    print("-" * 30)
    
    generator = get_generator()
    
    for mode in RenderMode:
        if mode in generator.renderers:
            renderer_class = generator.renderers[mode]
            try:
                # 创建临时实例测试
                from waternet.visualization.topology_generator import TopologyConfig
                test_config = TopologyConfig()
                renderer = renderer_class(test_config)
                can_render = renderer.can_render()
                status = "✅ 可用" if can_render else "⚠️  不可用"
            except Exception as e:
                status = f"❌ 错误: {str(e)[:50]}..."
            
            print(f"  {mode.value}: {status}")
        else:
            print(f"  {mode.value}: ❌ 未注册")


def create_output_directory():
    """创建输出目录"""
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    return output_dir


def main():
    """主函数"""
    try:
        # 创建输出目录
        create_output_directory()
        
        # 显示可用渲染器
        show_available_renderers()
        
        # 运行演示
        demo_config_based_generation()
        demo_quick_render()
        demo_render_mode_priority()
        demo_error_handling()
        
        print()
        print("=" * 80)
        print("🎉 演示完成！")
        print("=" * 80)
        print()
        print("特性说明:")
        print("✨ 支持多种渲染方式：文本ASCII、表格、图形化")
        print("✨ 自动降级策略：确保总有一种方式能工作")
        print("✨ 配置文件驱动：支持YAML和JSON格式")
        print("✨ 快速渲染接口：适合程序化生成")
        print("✨ 错误处理完善：友好的错误提示和恢复")
        print("✨ 中文字体支持：完整的中文显示")
        print()
        print("输出文件已保存到 output/ 目录")
        
    except Exception as e:
        logger.error(f"演示运行失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()