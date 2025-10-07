#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
水头损失计算器

专门用于单一渠道的水头损失分析和计算，支持不同类型的损失计算和对比分析。

功能特点：
1. 摩擦损失计算（基于Manning公式）
2. 局部损失计算（基于局部阻力系数）
3. 总损失分解分析
4. 不同参数条件下的损失对比
5. 损失敏感性分析

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

from waternet.models.saint_venant import SaintVenantModel


class ChannelHeadLossCalculator:
    """渠道水头损失计算器"""
    
    def __init__(self, config_path: str):
        """
        初始化计算器
        
        Args:
            config_path (str): 渠道配置文件路径
        """
        self.config_path = config_path
        self.channel_config = self._load_channel_config()
        self.model = self._create_saint_venant_model()
        
        # 重力加速度
        self.g = 9.81
        
        # 分析结果存储
        self.analysis_results = {}
        
    def _load_channel_config(self) -> Dict[str, Any]:
        """加载渠道配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            print(f"✓ 成功加载配置文件: {self.config_path}")
            return config
        except Exception as e:
            raise ValueError(f"加载配置文件失败: {e}")
    
    def _create_cross_section_functions(self, section: Dict[str, Any]) -> Tuple[Callable[[float], float], Callable[[float], float]]:
        """创建断面的水力几何函数"""
        cross_section = section['cross_section'] 
        bottom_width = cross_section['bottom_width']
        side_slope = cross_section['side_slope']
        elevation = section['elevation']
        
        def area_func(H: float) -> float:
            if H <= elevation:
                return 1e-6
            h = H - elevation
            return bottom_width * h + side_slope * h * h
        
        def top_width_func(H: float) -> float:
            if H <= elevation:
                return bottom_width
            h = H - elevation
            return bottom_width + 2 * side_slope * h
        
        return area_func, top_width_func
    
    def _create_saint_venant_model(self) -> SaintVenantModel:
        """创建圣维南模型"""
        sections_data = []
        
        for section in self.channel_config['sections']:
            area_func, top_width_func = self._create_cross_section_functions(section)
            
            section_data = {
                'mileage': section['mileage'],
                'elevation': section['elevation'],
                'roughness': section['roughness'],
                'area_func': area_func,
                'top_width_func': top_width_func,
                'bottom_width': section['cross_section']['bottom_width'],
                'side_slope': section['cross_section']['side_slope']
            }
            sections_data.append(section_data)
        
        model = SaintVenantModel(
            name=self.channel_config['name'],
            upstream_node='upstream_boundary',
            downstream_node='downstream_boundary',
            sections=sections_data
        )
        
        print(f"✓ 成功创建水头损失计算模型")
        print(f"  渠道名称: {model.name}")  
        print(f"  总长度: {sum(seg['length'] for seg in model.segments):.0f} m")
        
        return model
    
    def calculate_friction_loss(self, Q: float, H_up: float, H_down: float, 
                               segment: Dict[str, Any], 
                               section_up: Dict[str, Any], 
                               section_down: Dict[str, Any]) -> Dict[str, float]:
        """
        计算摩擦损失（基于Manning公式）
        
        Args:
            Q: 流量 (m³/s)
            H_up: 上游水位 (m)
            H_down: 下游水位 (m)
            segment: 分段属性
            section_up: 上游断面
            section_down: 下游断面
            
        Returns:
            Dict: 摩擦损失分析结果
        """
        # 计算水力要素
        A_up = section_up['area_func'](H_up)
        A_down = section_down['area_func'](H_down)
        T_up = section_up['top_width_func'](H_up)
        T_down = section_down['top_width_func'](H_down)
        
        # 水深
        depth_up = H_up - section_up['elevation']
        depth_down = H_down - section_down['elevation']
        
        # 湿周（梯形断面）
        P_up = T_up + 2 * depth_up * math.sqrt(1 + section_up['side_slope']**2)
        P_down = T_down + 2 * depth_down * math.sqrt(1 + section_down['side_slope']**2)
        
        # 水力半径
        R_up = A_up / P_up if P_up > 0 else 0
        R_down = A_down / P_down if P_down > 0 else 0
        R_avg = (R_up + R_down) / 2
        
        # 流速
        V_up = Q / A_up if A_up > 0 else 0
        V_down = Q / A_down if A_down > 0 else 0
        V_avg = (V_up + V_down) / 2
        
        # Manning摩擦损失
        n = segment['roughness']
        L = segment['length']
        
        if R_avg > 0:
            friction_slope = n**2 * V_avg**2 / (R_avg**(4/3))
            friction_loss = friction_slope * L
        else:
            friction_slope = 0
            friction_loss = 0
        
        # 流速水头差（动能变化）
        velocity_head_up = V_up**2 / (2 * self.g)
        velocity_head_down = V_down**2 / (2 * self.g)
        velocity_head_change = velocity_head_up - velocity_head_down
        
        # 总水头损失
        total_head_loss = H_up - H_down
        
        return {
            'friction_loss': friction_loss,
            'friction_slope': friction_slope,
            'velocity_head_change': velocity_head_change,
            'total_head_loss': total_head_loss,
            'hydraulic_radius_avg': R_avg,
            'velocity_avg': V_avg,
            'roughness': n,
            'length': L
        }
    
    def analyze_roughness_sensitivity(self, Q: float, downstream_H: float, 
                                    roughness_factors: Optional[List[float]] = None) -> Dict[str, Any]:
        """
        分析糙率系数敏感性
        
        Args:
            Q: 流量 (m³/s)  
            downstream_H: 下游边界水位 (m)
            roughness_factors: 糙率系数倍数因子
            
        Returns:
            Dict: 敏感性分析结果
        """
        if roughness_factors is None:
            roughness_factors = [0.8, 0.9, 1.0, 1.1, 1.2]
        
        print(f"\n分析糙率系数敏感性 (Q = {Q:.1f} m³/s)")
        print("-" * 50)
        
        sensitivity_results = {}
        
        for factor in roughness_factors:
            print(f"糙率倍数因子: {factor:.1f}")
            
            # 创建修改糙率后的模型
            modified_sections = []
            for section in self.model.sections:
                modified_section = section.copy()
                modified_section['roughness'] = section['roughness'] * factor
                modified_sections.append(modified_section)
            
            # 创建临时模型
            temp_model = SaintVenantModel(
                name=f"{self.model.name}_n{factor}",
                upstream_node=self.model.upstream_node,
                downstream_node=self.model.downstream_node,
                sections=modified_sections
            )
            
            try:
                # 计算恒定流
                steady_result = temp_model.compute_steady_state(Q, downstream_H)
                
                # 提取水位
                water_levels = [steady_result[f'H_section_{i}'] 
                               for i in range(len(temp_model.sections))]
                
                total_loss = water_levels[0] - water_levels[-1]
                
                sensitivity_results[factor] = {
                    'total_loss': total_loss,
                    'water_levels': water_levels,
                    'success': True
                }
                
                print(f"  总水头损失: {total_loss:.3f} m")
                
            except Exception as e:
                print(f"  计算失败: {e}")
                sensitivity_results[factor] = {
                    'error': str(e),
                    'success': False
                }
        
        return sensitivity_results
    
    def analyze_slope_impact(self, Q: float, downstream_H: float,
                           slope_factors: Optional[List[float]] = None) -> Dict[str, Any]:
        """
        分析坡度影响
        
        Args:
            Q: 流量 (m³/s)
            downstream_H: 下游边界水位 (m) 
            slope_factors: 坡度倍数因子
            
        Returns:
            Dict: 坡度影响分析结果
        """
        if slope_factors is None:
            slope_factors = [0.5, 0.8, 1.0, 1.5, 2.0]
        
        print(f"\n分析坡度影响 (Q = {Q:.1f} m³/s)")
        print("-" * 50)
        
        slope_results = {}
        original_elevations = [section['elevation'] for section in self.model.sections]
        
        for factor in slope_factors:
            print(f"坡度倍数因子: {factor:.1f}")
            
            # 调整断面高程（保持下游高程不变，调整坡度）
            modified_sections = []
            for i, section in enumerate(self.model.sections):
                modified_section = section.copy()
                if i == 0:  # 上游断面
                    # 调整上游高程以改变整体坡度
                    total_length = sum(seg['length'] for seg in self.model.segments)
                    original_slope = (original_elevations[0] - original_elevations[-1]) / total_length
                    new_slope = original_slope * factor
                    modified_section['elevation'] = original_elevations[-1] + new_slope * total_length
                elif i == len(self.model.sections) - 1:  # 下游断面保持不变
                    modified_section['elevation'] = original_elevations[i]
                else:  # 中间断面线性插值
                    total_length = sum(seg['length'] for seg in self.model.segments)
                    current_distance = sum(seg['length'] for seg in self.model.segments[:i])
                    ratio = current_distance / total_length
                    
                    new_upstream_elev = original_elevations[-1] + (original_elevations[0] - original_elevations[-1]) * factor
                    modified_section['elevation'] = original_elevations[-1] + (new_upstream_elev - original_elevations[-1]) * ratio
                
                modified_sections.append(modified_section)
            
            # 重新创建几何函数
            for i, section in enumerate(modified_sections):
                area_func, top_width_func = self._create_cross_section_functions(
                    self.channel_config['sections'][i])
                modified_sections[i]['area_func'] = area_func
                modified_sections[i]['top_width_func'] = top_width_func
            
            # 创建临时模型
            temp_model = SaintVenantModel(
                name=f"{self.model.name}_slope{factor}",
                upstream_node=self.model.upstream_node,
                downstream_node=self.model.downstream_node,
                sections=modified_sections
            )
            
            try:
                # 计算恒定流
                steady_result = temp_model.compute_steady_state(Q, downstream_H)
                
                # 提取水位
                water_levels = [steady_result[f'H_section_{i}'] 
                               for i in range(len(temp_model.sections))]
                
                total_loss = water_levels[0] - water_levels[-1]
                actual_slope = sum(seg['slope'] for seg in temp_model.segments) / len(temp_model.segments)
                
                slope_results[factor] = {
                    'total_loss': total_loss,
                    'water_levels': water_levels,
                    'actual_slope': actual_slope,
                    'success': True
                }
                
                print(f"  实际平均坡度: {actual_slope:.6f}")
                print(f"  总水头损失: {total_loss:.3f} m")
                
            except Exception as e:
                print(f"  计算失败: {e}")
                slope_results[factor] = {
                    'error': str(e),
                    'success': False
                }
        
        return slope_results
    
    def detailed_loss_breakdown(self, Q: float, downstream_H: float) -> Dict[str, Any]:
        """
        详细的损失分解分析
        
        Args:
            Q: 流量 (m³/s)
            downstream_H: 下游边界水位 (m)
            
        Returns:
            Dict: 详细损失分解结果
        """
        print(f"\n详细损失分解分析 (Q = {Q:.1f} m³/s)")
        print("=" * 60)
        
        # 计算恒定流
        steady_result = self.model.compute_steady_state(Q, downstream_H)
        water_levels = [steady_result[f'H_section_{i}'] 
                       for i in range(len(self.model.sections))]
        
        breakdown_results = {
            'total_analysis': {
                'flow_rate': Q,
                'upstream_level': water_levels[0],
                'downstream_level': water_levels[-1],
                'total_head_loss': water_levels[0] - water_levels[-1]
            },
            'segment_analysis': []
        }
        
        print(f"总体分析:")
        print(f"  流量: {Q:.1f} m³/s")
        print(f"  上游水位: {water_levels[0]:.3f} m")
        print(f"  下游水位: {water_levels[-1]:.3f} m") 
        print(f"  总水头损失: {water_levels[0] - water_levels[-1]:.3f} m")
        
        print(f"\n分段损失分解:")
        print(f"{'分段':6s} {'长度':>8s} {'摩擦损失':>10s} {'摩擦坡度':>10s} {'流速变化':>10s} {'水力半径':>10s}")
        print(f"{'':6s} {'(m)':>8s} {'(m)':>10s} {'':>10s} {'(m)':>10s} {'(m)':>10s}")
        print("-" * 70)
        
        for i, segment in enumerate(self.model.segments):
            i_up = segment['upstream_section']
            i_down = segment['downstream_section']
            
            H_up = water_levels[i_up]
            H_down = water_levels[i_down]
            
            # 计算详细损失
            loss_detail = self.calculate_friction_loss(
                Q, H_up, H_down, segment, 
                self.model.sections[i_up], self.model.sections[i_down]
            )
            
            breakdown_results['segment_analysis'].append({
                'segment_index': i,
                'segment_name': f"分段{i+1}",
                'length': loss_detail['length'],
                'friction_loss': loss_detail['friction_loss'],
                'friction_slope': loss_detail['friction_slope'],
                'velocity_head_change': loss_detail['velocity_head_change'],
                'hydraulic_radius': loss_detail['hydraulic_radius_avg'],
                'total_head_loss': loss_detail['total_head_loss']
            })
            
            print(f"分段{i+1:1d} {loss_detail['length']:8.1f} "
                  f"{loss_detail['friction_loss']:10.3f} "
                  f"{loss_detail['friction_slope']:10.6f} "
                  f"{loss_detail['velocity_head_change']:10.3f} "
                  f"{loss_detail['hydraulic_radius_avg']:10.3f}")
        
        return breakdown_results
    
    def export_analysis_results(self, results: Dict[str, Any], 
                              filename: Optional[str] = None):
        """导出分析结果"""
        if filename is None:
            filename = f"outputs/data/水头损失详细分析_{self.channel_config['name']}.csv"
        
        # 确保输出目录存在
        output_dir = Path(filename).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"\n导出分析结果: {filename}")
        
        with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)
            
            # 写入总体信息
            writer.writerow(['总体分析'])
            writer.writerow(['流量(m³/s)', '上游水位(m)', '下游水位(m)', '总水头损失(m)'])
            total = results['total_analysis']
            writer.writerow([total['flow_rate'], total['upstream_level'], 
                           total['downstream_level'], total['total_head_loss']])
            
            writer.writerow([])  # 空行
            
            # 写入分段分析
            writer.writerow(['分段分析'])
            writer.writerow(['分段', '长度(m)', '摩擦损失(m)', '摩擦坡度', 
                           '流速水头变化(m)', '水力半径(m)', '总损失(m)'])
            
            for seg in results['segment_analysis']:
                writer.writerow([
                    seg['segment_name'], seg['length'], seg['friction_loss'],
                    seg['friction_slope'], seg['velocity_head_change'],
                    seg['hydraulic_radius'], seg['total_head_loss']
                ])
        
        print(f"✓ 分析结果已导出: {filename}")
    
    def run_comprehensive_analysis(self):
        """运行综合分析"""
        print("开始水头损失综合分析")
        print("="*60)
        
        # 分析参数设置
        test_flow_rates = [15.0, 30.0, 45.0]  # 测试流量
        downstream_level = 100.5  # 下游边界水位
        
        all_results = {}
        
        for Q in test_flow_rates:
            print(f"\n流量工况: Q = {Q:.1f} m³/s")
            print("="*40)
            
            # 1. 详细损失分解
            breakdown = self.detailed_loss_breakdown(Q, downstream_level)
            
            # 2. 糙率敏感性分析
            roughness_sensitivity = self.analyze_roughness_sensitivity(Q, downstream_level)
            
            # 3. 坡度影响分析  
            slope_impact = self.analyze_slope_impact(Q, downstream_level)
            
            all_results[Q] = {
                'breakdown': breakdown,
                'roughness_sensitivity': roughness_sensitivity,
                'slope_impact': slope_impact
            }
            
            # 导出单个工况结果
            self.export_analysis_results(breakdown, 
                f"outputs/data/损失分解_Q{Q:.0f}_{self.channel_config['name']}.csv")
        
        print("\n" + "="*60)
        print("综合分析完成!")
        print("="*60)
        print("生成的文件:")
        print("  - outputs/data/损失分解_Q*_*.csv")
        
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
        # 创建水头损失计算器
        calculator = ChannelHeadLossCalculator(config_path)
        
        # 运行综合分析
        results = calculator.run_comprehensive_analysis()
        
        print("\n分析完成，结果已保存到 outputs/data/ 目录")
        
    except Exception as e:
        print(f"分析过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()