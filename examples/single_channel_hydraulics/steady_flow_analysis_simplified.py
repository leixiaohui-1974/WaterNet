#!/usr/bin/env python3
"""
恒定流分析工具 (简化版)

基于WaterNet核心库的恒定流分析工具，大幅简化示例代码。

功能特点:
1. 多工况恒定流计算
2. 水头损失分析
3. 集成水面线绘制
4. 自动报告生成

运行示例:
    python steady_flow_analysis_simplified.py

Author: WaterNet Development Team
Date: 2025-01-05
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Any

# 添加WaterNet路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from waternet.models.saint_venant import SaintVenantModel
from waternet.utils import ChannelConfigManager, WaterSurfaceProfileAnalyzer


class SimplifiedSteadyFlowAnalyzer:
    """简化版恒定流分析器"""
    
    def __init__(self, config_path: str = "configs/complex_channel.yaml"):
        """初始化分析器"""
        # 使用核心库加载配置
        self.channel_config = ChannelConfigManager.load_channel_config(config_path)
        
        # 创建SaintVenant模型
        sections = ChannelConfigManager.create_saint_venant_sections(
            self.channel_config['channel'])
        
        self.model = SaintVenantModel(
            name=self.channel_config['channel']['name'],
            upstream_node="upstream",
            downstream_node="downstream", 
            sections=sections
        )
        
        # 默认分析工况
        self.flow_conditions = {
            '低流量': 10.0,
            '中流量': 25.0, 
            '高流量': 50.0
        }
        
        self.downstream_water_level = 100.5  # 下游边界水位
        
        print(f"✓ 简化版恒定流分析器初始化完成")
        print(f"  - 渠道: {self.channel_config['channel']['name']}")
        print(f"  - 分析工况: {list(self.flow_conditions.keys())}")
    
    def run_complete_analysis(self) -> Dict[str, Any]:
        """
        运行完整分析流程（一站式服务）
        
        Returns:
            Dict: 分析结果汇总
        """
        print("\n开始恒定流多工況分析...")
        
        results = {}
        
        # 1. 计算恒定流
        print("\n1. 计算恒定流工况...")
        for case_name, Q in self.flow_conditions.items():
            try:
                steady_result = self.model.compute_steady_state(
                    Q=Q, downstream_H=self.downstream_water_level)
                
                water_levels = [steady_result[f'H_section_{i}'] 
                               for i in range(len(self.model.sections))]
                
                total_loss = water_levels[0] - water_levels[-1]
                
                results[case_name] = {
                    'flow_rate': Q,
                    'upstream_level': water_levels[0],
                    'downstream_level': water_levels[-1], 
                    'total_loss': total_loss,
                    'steady_result': steady_result,
                    'success': True
                }
                
                print(f"  ✓ {case_name}: Q={Q:.1f} m³/s, 损失={total_loss:.3f} m")
                
            except Exception as e:
                results[case_name] = {
                    'flow_rate': Q,
                    'error': str(e),
                    'success': False
                }
                print(f"  ✗ {case_name}: 计算失败 - {e}")
        
        # 2. 集成水面线分析（可选）
        try:
            print("\n2. 集成水面线分析...")
            analyzer = WaterSurfaceProfileAnalyzer()
            
            flow_list = list(self.flow_conditions.values())
            profile_results = analyzer.compute_multiple_flow_profiles(
                flow_list, self.channel_config['channel'])
            
            if profile_results:
                report_path = analyzer.generate_analysis_report(
                    channel_name=self.channel_config['channel']['name'],
                    channel_length=self.channel_config['channel']['length']
                )
                print(f"  ✓ 水面线报告已生成: {report_path}")
                results['water_surface_report'] = report_path
        
        except Exception as e:
            print(f"  ⚠️ 水面线分析失败: {e}")
        
        # 3. 生成汇总
        print("\n3. 分析结果汇总:")
        print("-" * 50)
        successful_cases = [name for name, result in results.items() 
                           if isinstance(result, dict) and result.get('success')]
        
        for case_name in successful_cases:
            result = results[case_name]
            print(f"{case_name:8s}: Q={result['flow_rate']:5.1f} m³/s, "
                  f"损失={result['total_loss']:.3f} m")
        
        print(f"\n✓ 分析完成! 成功计算 {len(successful_cases)} 个工况")
        
        return results


def main():
    """主函数 - 简化版演示"""
    print("恒定流分析工具 (简化版)")
    print("=" * 50)
    
    try:
        # 创建简化版分析器
        analyzer = SimplifiedSteadyFlowAnalyzer()
        
        # 一键完整分析
        results = analyzer.run_complete_analysis()
        
        # 显示最终结果
        successful_count = sum(1 for r in results.values() 
                             if isinstance(r, dict) and r.get('success'))
        
        print(f"\n🎯 最终结果:")
        print(f"  - 成功工况: {successful_count} 个")
        print(f"  - 分析类型: 恒定流水头损失 + 水面线分析")
        if 'water_surface_report' in results:
            print(f"  - 水面线报告: {results['water_surface_report']}")
    
    except Exception as e:
        print(f"✗ 分析失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()