#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
输出路径规范演示 - 修正版

严格遵循用户记忆规范：
- 所有示例程序的输出结果必须存储在该程序所在示例目录下的outputs子目录中
- 采用面向对象设计模式来管理输出路径
- 确保项目整洁和可维护性
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# 导入基础对象系统
from waternet.objects.conveyance import ChannelObject


class OutputPathManager:
    """
    输出路径管理器 - 面向对象设计
    遵循用户记忆规范：确保所有输出在示例目录下的outputs子目录中
    """
    
    def __init__(self, example_dir: Path):
        """
        初始化输出路径管理器
        
        Args:
            example_dir: 示例程序所在目录
        """
        self.example_dir = example_dir
        self.outputs_dir = example_dir / 'outputs'
        self._ensure_base_structure()
    
    def _ensure_base_structure(self):
        """确保基础目录结构存在"""
        required_dirs = [
            self.outputs_dir / 'data',
            self.outputs_dir / 'plots', 
            self.outputs_dir / 'reports'
        ]
        for dir_path in required_dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def get_output_path(self, *path_parts) -> str:
        """
        获取输出路径
        
        Args:
            *path_parts: 路径组件
            
        Returns:
            完整的输出路径
        """
        path = self.outputs_dir
        for part in path_parts:
            path = path / part
        # 创建目录（如果不存在）
        path.mkdir(parents=True, exist_ok=True)
        return str(path)
    
    def get_report_path(self, report_type: str, component: Optional[str] = None) -> str:
        """获取报告路径"""
        if component:
            return self.get_output_path('reports', report_type, component)
        return self.get_output_path('reports', report_type)
    
    def get_plot_path(self, plot_type: str, component: Optional[str] = None) -> str:
        """获取图表路径"""
        if component:
            return self.get_output_path('plots', plot_type, component)
        return self.get_output_path('plots', plot_type)
    
    def get_data_path(self, data_type: str, component: Optional[str] = None) -> str:
        """获取数据路径"""
        if component:
            return self.get_output_path('data', data_type, component)
        return self.get_output_path('data', data_type)
    
    def show_structure(self):
        """显示输出目录结构"""
        print(f"📁 输出目录结构 (遵循路径规范):")
        print(f"   根目录: {self.example_dir}")
        print(f"   输出目录: {self.outputs_dir}")
        print(f"   ├── data/      # 数据文件")
        print(f"   ├── plots/     # 图表文件") 
        print(f"   └── reports/   # 报告文件")


def demo_corrected_output_paths():
    """演示修正后的输出路径管理"""
    print("=" * 80)
    print("输出路径规范演示 - 修正版")
    print("=" * 80)
    print("🎯 目标：确保所有输出在示例目录下的outputs子目录中")
    print("📐 设计：采用面向对象的OutputPathManager来管理路径")
    print("=" * 80)
    
    try:
        # 1. 创建输出路径管理器
        print("\n1. 创建输出路径管理器...")
        
        # 获取当前示例目录
        example_dir = Path(__file__).parent
        path_manager = OutputPathManager(example_dir)
        
        print(f"   ✅ 输出路径管理器创建成功")
        print(f"   📁 示例目录: {example_dir}")
        print(f"   📁 输出目录: {path_manager.outputs_dir}")
        
        # 显示目录结构
        path_manager.show_structure()
        
        # 2. 创建渠道对象进行测试
        print("\n2. 创建渠道对象并测试路径管理...")
        
        channel_config = {
            'basic_properties': {
                'length': 5000.0,
                'slope': 0.0003,
                'roughness': 0.025,
                'bottom_width': 15.0,
                'side_slope': 2.0
            }
        }
        
        channel = ChannelObject('path_demo_channel', config=channel_config)
        channel.initialize()
        
        print(f"   ✅ 渠道对象 {channel.object_id} 创建成功")
        
        # 3. 使用路径管理器设置正确的输出路径
        print("\n3. 使用路径管理器生成报告...")
        
        # 设置边界条件
        channel.set_upstream_boundary(flow=120.0)
        channel.set_downstream_boundary(level=96.0)
        
        # 执行计算
        steady_result = channel.solve_steady_flow()
        
        if steady_result.get('success', False):
            print(f"   ✅ 恒定流计算成功")
            
            # 使用路径管理器获取正确的输出路径
            comprehensive_output = path_manager.get_report_path('comprehensive', 'channel_analysis')
            hydraulic_output = path_manager.get_report_path('hydraulic', 'channel_analysis')
            profile_output = path_manager.get_plot_path('profiles', 'steady_flow')
            
            print(f"\n   📋 生成报告（使用正确路径）...")
            
            # 生成综合分析报告
            try:
                report_result = channel.generate_analysis_report(
                    report_type='comprehensive',
                    output_dir=comprehensive_output,
                    include_plots=True
                )
                
                if report_result['success']:
                    print(f"     ✅ 综合分析报告生成成功")
                    print(f"     📄 路径: {comprehensive_output}")
                else:
                    print(f"     ❌ 综合报告生成失败: {report_result.get('error', '未知错误')}")
            except Exception as e:
                print(f"     ⚠️ 报告生成过程中异常: {e}")
            
            # 生成恒定流纵剖面图
            try:
                viz_result = channel.create_visualization(
                    viz_type='profile',
                    output_dir=profile_output
                )
                
                if viz_result['success']:
                    print(f"     ✅ 恒定流纵剖面图生成成功")
                    print(f"     🖼️ 路径: {profile_output}")
                    print(f"     📏 包含：渠底高程、各断面信息、上下游边界条件")
                else:
                    print(f"     ❌ 纵剖面图生成失败: {viz_result.get('error', '未知错误')}")
            except Exception as e:
                print(f"     ⚠️ 可视化生成过程中异常: {e}")
        
        else:
            print(f"   ❌ 恒定流计算失败: {steady_result.get('error', '未知错误')}")
        
        # 4. 验证输出路径
        print(f"\n4. 验证输出路径规范...")
        
        # 检查是否在正确的目录下
        outputs_exist = path_manager.outputs_dir.exists()
        data_dir_exist = (path_manager.outputs_dir / 'data').exists()
        plots_dir_exist = (path_manager.outputs_dir / 'plots').exists()
        reports_dir_exist = (path_manager.outputs_dir / 'reports').exists()
        
        print(f"   📁 outputs/ 目录存在: {'✅' if outputs_exist else '❌'}")
        print(f"   📁 data/ 目录存在: {'✅' if data_dir_exist else '❌'}")
        print(f"   📁 plots/ 目录存在: {'✅' if plots_dir_exist else '❌'}")
        print(f"   📁 reports/ 目录存在: {'✅' if reports_dir_exist else '❌'}")
        
        # 检查是否有文件被错误地输出到根目录
        root_outputs_dir = Path(__file__).parent.parent.parent / 'outputs'
        if root_outputs_dir.exists():
            root_files = list(root_outputs_dir.iterdir())
            if root_files:
                print(f"   ⚠️ 检测到根目录outputs存在 {len(root_files)} 个项目")
                print(f"   💡 建议：这些应该移动到对应的示例目录下")
            else:
                print(f"   ✅ 根目录outputs为空或不存在")
        else:
            print(f"   ✅ 根目录outputs不存在")
        
        # 5. 输出路径规范总结
        print(f"\n5. 输出路径规范总结...")
        print(f"   📐 规范要求：所有输出在 examples/{{example_name}}/outputs/")
        print(f"   ✅ 当前实现：{path_manager.outputs_dir}")
        print(f"   🏗️ 设计模式：面向对象的OutputPathManager")
        print(f"   🎯 优势：")
        print(f"     • 确保路径规范遵循")
        print(f"     • 自动创建目录结构")  
        print(f"     • 统一路径管理接口")
        print(f"     • 项目整洁性保证")
        
        print(f"\n🎉 输出路径规范演示完成！")
        
    except Exception as e:
        print(f"❌ 演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


def show_path_comparison():
    """显示路径对比"""
    print(f"\n" + "=" * 80)
    print(f"输出路径对比分析")
    print(f"=" * 80)
    
    example_dir = Path(__file__).parent
    
    print(f"❌ 错误的路径设置：")
    print(f"   output_dir='outputs/smart_analysis'")
    print(f"   → 实际路径: {Path.cwd() / 'outputs' / 'smart_analysis'}")
    print(f"   → 问题: 输出到项目根目录")
    
    print(f"\n✅ 正确的路径设置：")
    print(f"   path_manager.get_output_path('smart_analysis')")
    print(f"   → 实际路径: {example_dir / 'outputs' / 'smart_analysis'}")
    print(f"   → 符合规范: 输出到示例目录")
    
    print(f"\n📐 遵循的规范：")
    print(f"   • 用户记忆：结果输出路径规范")
    print(f"   • 要求：examples/{{example_name}}/outputs/下的对应目录")
    print(f"   • 目标：确保项目整洁和可维护性")
    
    print(f"=" * 80)


if __name__ == "__main__":
    # 演示修正后的输出路径管理
    demo_corrected_output_paths()
    
    # 显示路径对比
    show_path_comparison()