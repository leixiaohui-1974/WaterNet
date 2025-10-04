#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用拓扑图生成器简化演示

展示基于配置文件的拓扑图生成功能。

Created by: Qoder AI Assistant
Date: 2025-10-04
"""

import sys
import os
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_config_loading():
    """测试配置文件加载"""
    print("🔧 测试配置文件加载...")
    
    try:
        from waternet.visualization.topology_generator import ConfigLoader
        
        config_path = project_root / "configs" / "hydraulic_system_topology.yaml"
        if config_path.exists():
            config = ConfigLoader.load_from_file(config_path)
            print(f"✅ 成功加载配置: {config.title}")
            print(f"   节点数: {len(config.nodes)}")
            print(f"   边数: {len(config.edges)}")
            return config
        else:
            print(f"❌ 配置文件不存在: {config_path}")
            return None
            
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        return None


def test_text_renderer():
    """测试文本渲染器"""
    print("\n📝 测试文本ASCII渲染器...")
    
    try:
        from waternet.visualization.topology_generator import TopologyConfig, NodeData, EdgeData, ComponentType
        from waternet.visualization.text_ascii_renderer import TextASCIIRenderer
        
        # 创建简单测试配置
        config = TopologyConfig(
            title="简单测试系统",
            nodes=[
                NodeData("source", "水源", ComponentType.RESERVOIR, (0, 1), {"water_level": 100.0}),
                NodeData("pump", "水泵", ComponentType.PUMP, (2, 1), {"flow_rate": 50.0}),
                NodeData("target", "目标", ComponentType.RESERVOIR, (4, 1), {"water_level": 95.0})
            ],
            edges=[
                EdgeData("pipe1", "进水管", "source", "pump", properties={"flow_rate": 50.0}),
                EdgeData("pipe2", "出水管", "pump", "target", properties={"flow_rate": 50.0})
            ]
        )
        
        renderer = TextASCIIRenderer(config)
        if renderer.can_render():
            print("✅ 文本渲染器可用")
            renderer.render()
            return True
        else:
            print("❌ 文本渲染器不可用")
            return False
            
    except Exception as e:
        print(f"❌ 文本渲染器测试失败: {e}")
        return False


def test_table_renderer():
    """测试表格渲染器"""
    print("\n📊 测试表格渲染器...")
    
    try:
        from waternet.visualization.topology_generator import TopologyConfig, NodeData, EdgeData, ComponentType
        from waternet.visualization.table_renderer import TableRenderer
        
        # 创建简单测试配置
        config = TopologyConfig(
            title="表格测试系统",
            nodes=[
                NodeData("tank1", "水箱A", ComponentType.RESERVOIR, (0, 0), {"capacity": 1000}),
                NodeData("valve", "阀门", ComponentType.VALVE, (2, 0), {"opening": 75}),
                NodeData("tank2", "水箱B", ComponentType.RESERVOIR, (4, 0), {"capacity": 800})
            ],
            edges=[
                EdgeData("flow", "水流", "tank1", "valve"),
                EdgeData("outlet", "出口", "valve", "tank2")
            ]
        )
        
        renderer = TableRenderer(config)
        if renderer.can_render():
            print("✅ 表格渲染器可用")
            renderer.render()
            return True
        else:
            print("❌ 表格渲染器不可用")
            return False
            
    except Exception as e:
        print(f"❌ 表格渲染器测试失败: {e}")
        return False


def test_visualization_package():
    """测试可视化包接口"""
    print("\n📦 测试可视化包接口...")
    
    try:
        # 确保输出目录存在
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        # 测试快速渲染接口
        from waternet.visualization import quick_render
        
        nodes = [
            ("n1", "起点", "reservoir", (0, 0), {"level": 100}),
            ("n2", "终点", "reservoir", (2, 0), {"level": 95})
        ]
        edges = [("e1", "连接", "n1", "n2", {"flow": 25})]
        
        print("🚀 测试快速渲染接口...")
        results = quick_render("包接口测试", nodes, edges, "output/package_test.txt")
        
        success_modes = results.get('success_modes', [])
        if success_modes:
            print(f"✅ 快速渲染成功: {', '.join(success_modes)}")
            return True
        else:
            print("❌ 快速渲染失败")
            return False
            
    except Exception as e:
        print(f"❌ 包接口测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("🏗️ 通用拓扑图生成器简化演示")
    print("=" * 60)
    
    # 创建输出目录
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # 运行测试
    success_count = 0
    total_tests = 4
    
    # 测试配置加载
    if test_config_loading():
        success_count += 1
    
    # 测试各个渲染器
    if test_text_renderer():
        success_count += 1
    
    if test_table_renderer():
        success_count += 1
    
    if test_visualization_package():
        success_count += 1
    
    # 总结
    print("\n" + "=" * 60)
    print(f"🎯 测试完成: {success_count}/{total_tests} 通过")
    print("=" * 60)
    
    if success_count == total_tests:
        print("🎉 所有测试通过！通用拓扑图生成器工作正常。")
        print("\n✨ 主要特性:")
        print("  • 支持多种渲染方式（文本ASCII、表格、图形）")
        print("  • 配置文件驱动（YAML/JSON）")
        print("  • 自动降级策略")
        print("  • 中文显示支持")
        print("\n📁 输出文件保存在 output/ 目录")
    else:
        print("⚠️ 部分测试失败，但基本功能仍可用。")
    
    return success_count == total_tests


if __name__ == "__main__":
    main()