#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
渠道几何工具

专门用于单一渠道的几何参数分析和计算，支持不同断面形状的几何特性分析。

功能特点：
1. 断面几何参数计算（面积、湿周、水力半径等）
2. 水力最优断面分析
3. 断面形状优化建议
4. 几何参数敏感性分析
5. 不同水深下的几何特性曲线

作者: WaterNet Team
日期: 2024-10-05
"""

import sys
import os
import math
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional, Callable
import yaml
import csv

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class ChannelGeometryTool:
    """渠道几何分析工具"""
    
    def __init__(self, config_path: str):
        """
        初始化几何工具
        
        Args:
            config_path (str): 渠道配置文件路径
        """
        self.config_path = config_path
        self.channel_config = self._load_channel_config()
        
    def _load_channel_config(self) -> Dict[str, Any]:
        """加载渠道配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            print(f"✓ 成功加载配置文件: {self.config_path}")
            return config
        except Exception as e:
            raise ValueError(f"加载配置文件失败: {e}")
    
    def calculate_trapezoidal_geometry(self, bottom_width: float, side_slope: float, 
                                     depth: float) -> Dict[str, float]:
        """
        计算梯形断面几何参数
        
        Args:
            bottom_width: 底宽 (m)
            side_slope: 边坡系数 (水平:垂直)
            depth: 水深 (m)
            
        Returns:
            Dict: 几何参数字典
        """
        if depth <= 0:
            return {
                'area': 0.0,
                'perimeter': bottom_width,
                'top_width': bottom_width,
                'hydraulic_radius': 0.0,
                'hydraulic_depth': 0.0,
                'section_factor': 0.0
            }
        
        # 基本几何参数
        area = bottom_width * depth + side_slope * depth * depth
        top_width = bottom_width + 2 * side_slope * depth
        perimeter = bottom_width + 2 * depth * math.sqrt(1 + side_slope * side_slope)
        
        # 水力参数
        hydraulic_radius = area / perimeter if perimeter > 0 else 0
        hydraulic_depth = area / top_width if top_width > 0 else 0
        section_factor = area * math.sqrt(hydraulic_radius) if hydraulic_radius > 0 else 0
        
        return {
            'area': area,
            'perimeter': perimeter,
            'top_width': top_width,
            'hydraulic_radius': hydraulic_radius,
            'hydraulic_depth': hydraulic_depth,
            'section_factor': section_factor,
            'depth': depth,
            'bottom_width': bottom_width,
            'side_slope': side_slope
        }
    
    def find_optimal_trapezoidal_section(self, area: float, side_slope: float) -> Dict[str, Any]:
        """
        寻找给定面积和边坡系数下的水力最优梯形断面
        
        Args:
            area: 给定断面积 (m²)
            side_slope: 边坡系数
            
        Returns:
            Dict: 最优断面参数
        """
        # 水力最优条件：dR/db = 0
        # 对于梯形断面，最优条件为：b = 2*h*(√(1+m²) - m)
        
        def objective_function(depth: float) -> float:
            """目标函数：使水力半径最大"""
            if depth <= 0:
                return -1e6
            
            # 根据给定面积计算底宽
            # A = b*h + m*h²，所以 b = A/h - m*h
            bottom_width = area / depth - side_slope * depth
            
            if bottom_width <= 0:
                return -1e6
            
            geometry = self.calculate_trapezoidal_geometry(bottom_width, side_slope, depth)
            return geometry['hydraulic_radius']
        
        # 搜索最优水深
        best_depth = 0
        best_hydraulic_radius = 0
        
        # 水深搜索范围：从0.1到10m
        for depth in [i * 0.01 for i in range(10, 1001)]:  # 0.1 to 10.0 m, step 0.01
            hr = objective_function(depth)
            if hr > best_hydraulic_radius:
                best_hydraulic_radius = hr
                best_depth = depth
        
        # 计算最优断面参数
        optimal_bottom_width = area / best_depth - side_slope * best_depth
        optimal_geometry = self.calculate_trapezoidal_geometry(
            optimal_bottom_width, side_slope, best_depth)
        
        return {
            'optimal_depth': best_depth,
            'optimal_bottom_width': optimal_bottom_width,
            'optimal_hydraulic_radius': best_hydraulic_radius,
            'area_constraint': area,
            'side_slope_constraint': side_slope,
            'geometry': optimal_geometry
        }
    
    def analyze_section_geometry(self, section_index: int, 
                               depth_range: Tuple[float, float] = (0.1, 5.0),
                               num_points: int = 50) -> Dict[str, Any]:
        """
        分析指定断面的几何特性
        
        Args:
            section_index: 断面索引
            depth_range: 水深分析范围 (m)
            num_points: 分析点数
            
        Returns:
            Dict: 几何特性分析结果
        """
        if section_index >= len(self.channel_config['sections']):
            raise ValueError(f"断面索引超出范围: {section_index}")
        
        section = self.channel_config['sections'][section_index]
        cross_section = section['cross_section']
        bottom_width = cross_section['bottom_width']
        side_slope = cross_section['side_slope']
        
        print(f"\n分析断面 {section_index + 1} 几何特性")
        print(f"底宽: {bottom_width:.2f} m, 边坡系数: {side_slope:.2f}")
        print("-" * 50)
        
        # 生成水深序列
        min_depth, max_depth = depth_range
        depth_step = (max_depth - min_depth) / (num_points - 1)
        depths = [min_depth + i * depth_step for i in range(num_points)]
        
        # 计算各水深下的几何参数
        geometry_data = []
        for depth in depths:
            geometry = self.calculate_trapezoidal_geometry(bottom_width, side_slope, depth)
            geometry_data.append(geometry)
        
        # 寻找几个特征水深
        max_efficiency_depth = max(geometry_data, key=lambda x: x['hydraulic_radius'])
        
        analysis_result = {
            'section_info': {
                'index': section_index,
                'bottom_width': bottom_width,
                'side_slope': side_slope,
                'roughness': section['roughness'],
                'elevation': section['elevation'],
                'mileage': section['mileage']
            },
            'geometry_data': geometry_data,
            'depth_range': depth_range,
            'max_efficiency': max_efficiency_depth,
            'analysis_points': num_points
        }
        
        print(f"最大水力效率水深: {max_efficiency_depth['depth']:.3f} m")
        print(f"对应水力半径: {max_efficiency_depth['hydraulic_radius']:.3f} m")
        print(f"对应断面积: {max_efficiency_depth['area']:.3f} m²")
        
        return analysis_result
    
    def compare_section_geometries(self) -> Dict[str, Any]:
        """对比所有断面的几何特性"""
        print("\n对比所有断面几何特性")
        print("=" * 60)
        
        comparison_results = {
            'sections': [],
            'summary': {}
        }
        
        print(f"{'断面':4s} {'里程':>8s} {'底宽':>8s} {'边坡':>8s} {'糙率':>8s} {'备注':>12s}")
        print(f"{'':4s} {'(m)':>8s} {'(m)':>8s} {'':>8s} {'':>8s} {'':>12s}")
        print("-" * 60)
        
        for i, section in enumerate(self.channel_config['sections']):
            cross_section = section['cross_section']
            
            # 分析该断面在标准水深(2m)下的特性
            standard_depth = 2.0
            geometry = self.calculate_trapezoidal_geometry(
                cross_section['bottom_width'], 
                cross_section['side_slope'], 
                standard_depth
            )
            
            section_result = {
                'index': i,
                'mileage': section['mileage'],
                'bottom_width': cross_section['bottom_width'],
                'side_slope': cross_section['side_slope'],
                'roughness': section['roughness'],
                'elevation': section['elevation'],
                'geometry_at_2m': geometry
            }
            
            comparison_results['sections'].append(section_result)
            
            # 判断断面特点
            if cross_section['side_slope'] < 1.0:
                note = "陡边坡"
            elif cross_section['side_slope'] > 2.0:
                note = "缓边坡"
            else:
                note = "标准边坡"
            
            print(f"{i+1:4d} {section['mileage']:8.1f} "
                  f"{cross_section['bottom_width']:8.1f} "
                  f"{cross_section['side_slope']:8.1f} "
                  f"{section['roughness']:8.3f} {note:>12s}")
        
        # 汇总统计
        bottom_widths = [s['bottom_width'] for s in comparison_results['sections']]
        side_slopes = [s['side_slope'] for s in comparison_results['sections']]
        roughnesses = [s['roughness'] for s in comparison_results['sections']]
        
        comparison_results['summary'] = {
            'bottom_width_range': (min(bottom_widths), max(bottom_widths)),
            'side_slope_range': (min(side_slopes), max(side_slopes)),
            'roughness_range': (min(roughnesses), max(roughnesses)),
            'section_count': len(comparison_results['sections'])
        }
        
        print(f"\n汇总统计:")
        print(f"  断面数量: {len(comparison_results['sections'])}")
        print(f"  底宽范围: {min(bottom_widths):.1f} - {max(bottom_widths):.1f} m")
        print(f"  边坡范围: {min(side_slopes):.1f} - {max(side_slopes):.1f}")
        print(f"  糙率范围: {min(roughnesses):.3f} - {max(roughnesses):.3f}")
        
        return comparison_results
    
    def sensitivity_analysis(self, section_index: int, 
                           parameter: str, variation_percent: float = 20.0) -> Dict[str, Any]:
        """
        几何参数敏感性分析
        
        Args:
            section_index: 断面索引
            parameter: 参数名称 ('bottom_width' 或 'side_slope')
            variation_percent: 变化百分比
            
        Returns:
            Dict: 敏感性分析结果
        """
        if section_index >= len(self.channel_config['sections']):
            raise ValueError(f"断面索引超出范围: {section_index}")
        
        section = self.channel_config['sections'][section_index]
        cross_section = section['cross_section']
        
        print(f"\n断面 {section_index + 1} {parameter} 敏感性分析")
        print(f"变化范围: ±{variation_percent}%")
        print("-" * 50)
        
        # 基准值
        base_bottom_width = cross_section['bottom_width']
        base_side_slope = cross_section['side_slope']
        test_depth = 2.0  # 测试水深
        
        # 变化范围
        variation_factors = [
            1 - variation_percent/100,
            1 - variation_percent/200,
            1.0,  # 基准
            1 + variation_percent/200,
            1 + variation_percent/100
        ]
        
        sensitivity_results = {
            'parameter': parameter,
            'base_values': {
                'bottom_width': base_bottom_width,
                'side_slope': base_side_slope
            },
            'test_depth': test_depth,
            'variation_percent': variation_percent,
            'results': []
        }
        
        print(f"{'变化':>8s} {parameter:>12s} {'面积':>8s} {'湿周':>8s} {'水力半径':>10s} {'断面系数':>10s}")
        print(f"{'(%)':>8s} {'':>12s} {'(m²)':>8s} {'(m)':>8s} {'(m)':>10s} {'':>10s}")
        print("-" * 70)
        
        for factor in variation_factors:
            if parameter == 'bottom_width':
                test_bottom_width = base_bottom_width * factor
                test_side_slope = base_side_slope
            elif parameter == 'side_slope':
                test_bottom_width = base_bottom_width
                test_side_slope = base_side_slope * factor
            else:
                raise ValueError(f"不支持的参数: {parameter}")
            
            geometry = self.calculate_trapezoidal_geometry(
                test_bottom_width, test_side_slope, test_depth)
            
            change_percent = (factor - 1) * 100
            
            result = {
                'change_percent': change_percent,
                'parameter_value': test_bottom_width if parameter == 'bottom_width' else test_side_slope,
                'geometry': geometry
            }
            
            sensitivity_results['results'].append(result)
            
            print(f"{change_percent:8.1f} "
                  f"{result['parameter_value']:12.2f} "
                  f"{geometry['area']:8.3f} "
                  f"{geometry['perimeter']:8.3f} "
                  f"{geometry['hydraulic_radius']:10.3f} "
                  f"{geometry['section_factor']:10.3f}")
        
        return sensitivity_results
    
    def export_geometry_analysis(self, results: Dict[str, Any], 
                                filename: Optional[str] = None):
        """导出几何分析结果"""
        if filename is None:
            filename = f"outputs/data/几何分析_{self.channel_config['name']}.csv"
        
        # 确保输出目录存在
        output_dir = Path(filename).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"\n导出几何分析结果: {filename}")
        
        with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)
            
            # 根据结果类型写入不同格式
            if 'geometry_data' in results:  # 单断面分析结果
                writer.writerow(['断面几何特性分析'])
                writer.writerow(['断面信息'])
                info = results['section_info']
                writer.writerow(['断面索引', '里程(m)', '底宽(m)', '边坡系数', '糙率', '高程(m)'])
                writer.writerow([info['index'], info['mileage'], info['bottom_width'], 
                               info['side_slope'], info['roughness'], info['elevation']])
                
                writer.writerow([])
                writer.writerow(['几何特性数据'])
                writer.writerow(['水深(m)', '面积(m²)', '湿周(m)', '水面宽(m)', 
                               '水力半径(m)', '水力深度(m)', '断面系数'])
                
                for data in results['geometry_data']:
                    writer.writerow([data['depth'], data['area'], data['perimeter'],
                                   data['top_width'], data['hydraulic_radius'],
                                   data['hydraulic_depth'], data['section_factor']])
            
            elif 'sections' in results:  # 多断面对比结果
                writer.writerow(['断面对比分析'])
                writer.writerow(['断面', '里程(m)', '底宽(m)', '边坡系数', '糙率', 
                               '高程(m)', '面积@2m(m²)', '水力半径@2m(m)'])
                
                for section in results['sections']:
                    geom = section['geometry_at_2m']
                    writer.writerow([section['index']+1, section['mileage'], 
                                   section['bottom_width'], section['side_slope'],
                                   section['roughness'], section['elevation'],
                                   geom['area'], geom['hydraulic_radius']])
        
        print(f"✓ 几何分析结果已导出: {filename}")
    
    def run_complete_geometry_analysis(self):
        """运行完整几何分析"""
        print("开始渠道几何综合分析")
        print("=" * 60)
        
        all_results = {}
        
        # 1. 断面对比分析
        comparison = self.compare_section_geometries()
        all_results['comparison'] = comparison
        self.export_geometry_analysis(comparison, 
                                    f"outputs/data/断面对比_{self.channel_config['name']}.csv")
        
        # 2. 逐个断面详细分析
        for i in range(len(self.channel_config['sections'])):
            section_analysis = self.analyze_section_geometry(i)
            all_results[f'section_{i}'] = section_analysis
            
            # 导出单个断面分析
            self.export_geometry_analysis(section_analysis,
                f"outputs/data/断面{i+1}_几何分析_{self.channel_config['name']}.csv")
            
            # 敏感性分析
            if i == 0:  # 仅对第一个断面进行敏感性分析做演示
                bottom_width_sensitivity = self.sensitivity_analysis(i, 'bottom_width')
                side_slope_sensitivity = self.sensitivity_analysis(i, 'side_slope')
                
                all_results[f'section_{i}_sensitivity'] = {
                    'bottom_width': bottom_width_sensitivity,
                    'side_slope': side_slope_sensitivity
                }
        
        print("\n" + "=" * 60)
        print("几何分析完成!")
        print("=" * 60)
        print("生成的文件:")
        print("  - outputs/data/断面对比_*.csv")
        print("  - outputs/data/断面*_几何分析_*.csv")
        
        return all_results


def main():
    """主函数"""
    # 配置文件路径
    config_path = "configs/complex_channel.yaml"
    
    if not os.path.exists(config_path):
        # 尝试使用标准梯形渠道配置
        config_path = "configs/trapezoidal_channel.yaml"
        if not os.path.exists(config_path):
            print("错误: 找不到渠道配置文件")
            print("请确保以下文件之一存在:")
            print("  - configs/complex_channel.yaml")
            print("  - configs/trapezoidal_channel.yaml")
            return
    
    try:
        # 创建几何分析工具
        geometry_tool = ChannelGeometryTool(config_path)
        
        # 运行完整分析
        results = geometry_tool.run_complete_geometry_analysis()
        
        print("\n几何分析完成，结果已保存到 outputs/data/ 目录")
        
    except Exception as e:
        print(f"分析过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()