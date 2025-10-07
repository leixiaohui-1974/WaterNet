#!/usr/bin/env python3
"""
单一渠道水面线绘制工具 (简化版)

基于WaterNet核心库的水面线绘制工具，大幅简化示例代码。

功能特点:
1. 多工况水面线对比
2. 专业可视化报告生成 
3. 水力学性质分析

运行示例:
    python water_surface_profile_plotter_simplified.py

Author: WaterNet Development Team  
Date: 2025-01-05
"""

import sys
import os
from pathlib import Path
from typing import List

# 添加WaterNet路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from waternet.utils import ChannelConfigManager, WaterSurfaceProfileAnalyzer


class SimplifiedWaterSurfacePlotter:
    """
    简化版水面线绘制器
    
    使用WaterNet核心库的通用功能，大幅简化示例代码
    """
    
    def __init__(self, config_path: str = "configs/trapezoidal_channel.yaml"):
        """初始化绘制器"""
        # 使用核心库加载配置
        self.channel_config = ChannelConfigManager.load_channel_config(config_path)
        
        # 创建水面线分析器
        self.analyzer = WaterSurfaceProfileAnalyzer()
        
        print(f"✓ 水面线绘制器初始化完成")
        print(f"  - 配置文件: {config_path}")
        print(f"  - 渠道名称: {self.channel_config['channel']['name']}")
    
    def compute_and_plot(self, flow_conditions: List[float] | None = None) -> tuple[str, str]:
        """
        计算并绘制水面线（一站式服务）
        
        Args:
            flow_conditions: 流量工况列表 (m³/s)
            
        Returns:
            tuple: (图片路径, 报告路径)
        """
        if flow_conditions is None:
            flow_conditions = [25.0, 50.0, 75.0, 100.0]
        
        print(f"\n开始计算多工况水面线: {flow_conditions} m³/s")
        
        # 使用核心库计算水面线
        results = self.analyzer.compute_multiple_flow_profiles(
            flow_conditions, self.channel_config['channel'])
        
        if not results:
            print("✗ 水面线计算失败")
            return "", ""
        
        print(f"✓ 计算完成，共 {len(results)} 个工况")
        
        # 生成报告（使用核心库）
        report_path = self.analyzer.generate_analysis_report(
            channel_name=self.channel_config['channel']['name'],
            channel_length=self.channel_config['channel']['length']
        )
        
        print(f"✓ 分析报告已生成: {report_path}")
        
        # 注意：图片绘制功能需要matplotlib，这里返回空字符串
        print("⚠️ 图片绘制需要matplotlib支持")
        plot_path = ""
        
        return plot_path, report_path


def main():
    """主函数 - 简化版演示"""
    print("单一渠道水面线绘制工具 (简化版)")
    print("=" * 50)
    
    try:
        # 创建简化版水面线绘制器
        plotter = SimplifiedWaterSurfacePlotter()
        
        # 一键计算和绘制
        plot_path, report_path = plotter.compute_and_plot([25.0, 50.0, 75.0, 100.0])
        
        print(f"\n✅ 水面线分析完成！")
        print(f"  - 输出目录: {plotter.analyzer.output_dir}")
        if report_path:
            print(f"  - 分析报告: {report_path}")
    
    except Exception as e:
        print(f"✗ 程序执行失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()