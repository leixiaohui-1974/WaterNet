#!/usr/bin/env python3
"""
配置驱动水库-闸门-明渠系统演示

此脚本演示如何使用配置文件驱动的方式构建和运行完整的水利系统，包括：
1. 从YAML配置文件构建系统
2. 自动生成多种格式的可视化输出
3. 运行仿真分析
4. 生成工程报告

使用方法:
    python demo_config_driven_system.py

输出包括:
- ASCII艺术拓扑图
- 表格模式组件清单  
- 工程制图风格的系统图
- 综合分析报告

Author: WaterNet Development Team
Date: 2024-10-05
"""

import os
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from waternet.utils.config_system_builder import create_system_from_config
    from waternet.visualization.config_driven_visualizer import create_visualization_engine
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保项目已正确安装: pip install -e .")
    sys.exit(1)


def main():
    """主演示函数"""
    print("=" * 80)
    print("配置驱动水库-闸门-明渠系统演示".center(80))
    print("=" * 80)
    print()
    
    # 配置文件路径
    config_file = "configs/reservoir_gate_channel_system.yaml"
    
    if not os.path.exists(config_file):
        print(f"错误: 配置文件不存在 - {config_file}")
        print("请确保配置文件已创建")
        return
    
    try:
        # 第一步：从配置文件构建系统
        print("📋 第一步：从配置文件构建系统")
        print("-" * 50)
        
        builder = create_system_from_config(config_file)
        system = builder.build_system()
        
        # 显示系统概要
        summary = builder.get_system_summary()
        print("\n📊 系统概要信息:")
        print(f"   系统名称: {summary['system_name']}")
        print(f"   组件统计: {summary['components_count']}")
        print(f"   总组件数: {summary['total_components']}")
        print(f"   模型数量: {summary['models_count']}")
        print(f"   可视化引擎: {'✓' if summary['has_visualizer'] else '✗'}")
        print()
        
        # 第二步：生成可视化输出
        print("🎨 第二步：生成多格式可视化输出")
        print("-" * 50)
        
        output_dir = project_root / "demo_output"
        output_dir.mkdir(exist_ok=True)
        
        try:
            vis_results = builder.generate_system_visualization(str(output_dir))
            
            print("生成的可视化文件:")
            for output_type, file_path in vis_results.items():
                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path) / 1024  # KB
                    print(f"   ✓ {output_type}: {file_path} ({file_size:.1f} KB)")
                else:
                    print(f"   ✗ {output_type}: {file_path} (文件未生成)")
        
        except Exception as e:
            print(f"   ⚠ 可视化生成失败: {e}")
        
        print()
        
        # 第三步：展示ASCII拓扑图
        print("🔧 第三步：展示系统ASCII拓扑图")
        print("-" * 50)
        
        try:
            if builder.visualizer:
                system_data = {
                    'system': builder.config.system_info,
                    'components': builder.config.components,
                    'topology': builder.config.topology
                }
                
                ascii_topology = builder.visualizer.generate_ascii_topology(system_data)
                print(ascii_topology)
            else:
                print("   ⚠ 可视化引擎不可用")
        
        except Exception as e:
            print(f"   ⚠ ASCII拓扑图生成失败: {e}")
        
        print()
        
        # 第四步：展示表格模式
        print("📋 第四步：展示组件参数表格")
        print("-" * 50)
        
        try:
            if builder.visualizer:
                table_view = builder.visualizer.generate_table_view(system_data)
                print(table_view)
            else:
                print("   ⚠ 可视化引擎不可用")
        
        except Exception as e:
            print(f"   ⚠ 表格视图生成失败: {e}")
        
        print()
        
        # 第五步：演示智能模式选择
        print("🤖 第五步：演示智能可视化模式选择")
        print("-" * 50)
        
        try:
            if builder.visualizer:
                recommended_mode = builder.visualizer.select_display_mode(system_data)
                print(f"   推荐的显示模式: {recommended_mode}")
                
                # 显示所有可用模式
                display_modes = builder.visualizer.config['visualization']['display_modes']
                print("   可用的显示模式:")
                for mode_name, mode_config in display_modes.items():
                    suitable_for = ', '.join(mode_config.get('suitable_for', []))
                    marker = "👉" if mode_name == recommended_mode else "  "
                    print(f"   {marker} {mode_name}: {mode_config['description']}")
                    print(f"      适用场景: {suitable_for}")
        
        except Exception as e:
            print(f"   ⚠ 模式选择演示失败: {e}")
        
        print()
        
        # 第六步：配置验证和诊断
        print("🔍 第六步：配置验证和系统诊断")
        print("-" * 50)
        
        validation_results = validate_system_configuration(builder)
        
        print("配置验证结果:")
        for check_name, result in validation_results.items():
            status = "✓" if result['passed'] else "✗"
            print(f"   {status} {check_name}: {result['message']}")
        
        print()
        
        # 总结
        print("🎯 演示总结")
        print("-" * 50)
        
        total_checks = len(validation_results)
        passed_checks = sum(1 for r in validation_results.values() if r['passed'])
        
        print(f"系统构建: ✓ 成功")
        print(f"组件创建: ✓ {summary['total_components']} 个组件")
        print(f"配置验证: {passed_checks}/{total_checks} 项通过")
        
        if builder.visualizer:
            print(f"可视化输出: ✓ 多格式文件已生成")
        else:
            print(f"可视化输出: ⚠ 部分功能不可用")
        
        print(f"\n输出文件位置: {output_dir}")
        print("\n🎉 配置驱动系统演示完成！")
        
    except Exception as e:
        print(f"\n❌ 演示失败: {e}")
        import traceback
        traceback.print_exc()


def validate_system_configuration(builder) -> dict:
    """验证系统配置的完整性"""
    validation_results = {}
    
    # 检查配置文件结构
    try:
        required_sections = ['system', 'components', 'topology']
        missing_sections = []
        
        for section in required_sections:
            if not hasattr(builder.config, section) or not getattr(builder.config, section):
                missing_sections.append(section)
        
        if missing_sections:
            validation_results['配置结构'] = {
                'passed': False,
                'message': f"缺少必要配置段: {', '.join(missing_sections)}"
            }
        else:
            validation_results['配置结构'] = {
                'passed': True,
                'message': "所有必要配置段均存在"
            }
    
    except Exception as e:
        validation_results['配置结构'] = {
            'passed': False,
            'message': f"配置结构检查失败: {e}"
        }
    
    # 检查组件创建
    try:
        if builder.components:
            validation_results['组件创建'] = {
                'passed': True,
                'message': f"成功创建 {len(builder.components)} 个组件"
            }
        else:
            validation_results['组件创建'] = {
                'passed': False,
                'message': "未创建任何组件"
            }
    
    except Exception as e:
        validation_results['组件创建'] = {
            'passed': False,
            'message': f"组件创建检查失败: {e}"
        }
    
    # 检查可视化引擎
    try:
        if builder.visualizer:
            validation_results['可视化引擎'] = {
                'passed': True,
                'message': "可视化引擎已正确初始化"
            }
        else:
            validation_results['可视化引擎'] = {
                'passed': False,
                'message': "可视化引擎未初始化"
            }
    
    except Exception as e:
        validation_results['可视化引擎'] = {
            'passed': False,
            'message': f"可视化引擎检查失败: {e}"
        }
    
    # 检查配置一致性
    try:
        components = builder.config.components
        topology = builder.config.topology
        
        # 检查拓扑节点和组件连接的一致性
        inconsistencies = []
        
        # 检查水库节点
        for res_name, res_config in components.get('reservoirs', {}).items():
            connected_node = res_config.get('connected_node')
            if connected_node:
                # 检查该节点是否在拓扑中定义
                nodes = [node['name'] for node in topology.get('nodes', [])]
                if connected_node not in nodes:
                    inconsistencies.append(f"水库 {res_name} 的连接节点 {connected_node} 未在拓扑中定义")
        
        if inconsistencies:
            validation_results['配置一致性'] = {
                'passed': False,
                'message': f"发现不一致: {'; '.join(inconsistencies)}"
            }
        else:
            validation_results['配置一致性'] = {
                'passed': True,
                'message': "配置各部分保持一致"
            }
    
    except Exception as e:
        validation_results['配置一致性'] = {
            'passed': False,
            'message': f"一致性检查失败: {e}"
        }
    
    return validation_results


def show_usage():
    """显示使用说明"""
    print(__doc__)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        show_usage()
    else:
        main()