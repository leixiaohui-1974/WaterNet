#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
渠道参数对比分析器

专门用于对比分析同一渠道在不同参数条件下的水头损失情况：
1. 不同坡度对比分析
2. 不同流量对比分析  
3. 不同断面参数对比分析
4. 综合参数敏感性分析

作者: WaterNet Team
日期: 2024-10-05
"""

import sys
import os
import math
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import yaml
import csv

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from waternet.models.saint_venant import SaintVenantModel


class ChannelParameterComparator:
    """渠道参数对比分析器"""
    
    def __init__(self, base_config_path: str):
        """
        初始化对比分析器
        
        Args:
            base_config_path: 基础配置文件路径
        """
        self.base_config_path = base_config_path
        self.base_config = self._load_config()
        self.downstream_level = 100.5  # 固定下游边界
        
    def _load_config(self) -> Dict[str, Any]:
        """加载基础配置"""
        with open(self.base_config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _create_model_from_config(self, config: Dict[str, Any]) -> SaintVenantModel:
        """根据配置创建模型"""
        sections_data = []
        
        for section in config['sections']:
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
            
            section_data = {
                'mileage': section['mileage'],
                'elevation': section['elevation'],
                'roughness': section['roughness'],
                'area_func': area_func,
                'top_width_func': top_width_func,
                'bottom_width': bottom_width,
                'side_slope': side_slope
            }
            sections_data.append(section_data)
        
        return SaintVenantModel(
            name=config['name'],
            upstream_node='upstream',
            downstream_node='downstream',
            sections=sections_data
        )
    
    def compare_slope_effects(self, test_flow: float = 30.0) -> Dict[str, Any]:
        """对比不同坡度下的水头损失"""
        print(f"\n=== 坡度对比分析 (Q = {test_flow:.1f} m³/s) ===")
        
        # 坡度倍数因子
        slope_factors = [0.5, 0.8, 1.0, 1.5, 2.0, 3.0]
        results = {}
        
        original_elevations = [s['elevation'] for s in self.base_config['sections']]
        
        for factor in slope_factors:
            print(f"\n坡度倍数: {factor:.1f}x")
            
            # 创建修改坡度的配置
            modified_config = self.base_config.copy()
            modified_config['sections'] = []
            
            for i, section in enumerate(self.base_config['sections']):
                new_section = section.copy()
                if i == len(self.base_config['sections']) - 1:
                    # 下游保持不变
                    new_section['elevation'] = original_elevations[i]
                else:
                    # 调整坡度
                    total_length = sum(
                        abs(self.base_config['sections'][j+1]['mileage'] - 
                            self.base_config['sections'][j]['mileage'])
                        for j in range(len(self.base_config['sections'])-1)
                    )
                    original_slope = (original_elevations[0] - original_elevations[-1]) / total_length
                    new_slope = original_slope * factor
                    
                    if i == 0:
                        new_section['elevation'] = original_elevations[-1] + new_slope * total_length
                    else:
                        # 线性插值
                        distance_from_downstream = sum(
                            abs(self.base_config['sections'][j+1]['mileage'] - 
                                self.base_config['sections'][j]['mileage'])
                            for j in range(i, len(self.base_config['sections'])-1)
                        )
                        new_section['elevation'] = original_elevations[-1] + new_slope * distance_from_downstream
                
                modified_config['sections'].append(new_section)
            
            try:
                model = self._create_model_from_config(modified_config)
                steady_result = model.compute_steady_state(test_flow, self.downstream_level)
                
                water_levels = [steady_result[f'H_section_{i}'] 
                               for i in range(len(model.sections))]
                total_loss = water_levels[0] - water_levels[-1]
                actual_slope = sum(seg['slope'] for seg in model.segments) / len(model.segments)
                
                results[factor] = {
                    'total_loss': total_loss,
                    'actual_slope': actual_slope,
                    'upstream_level': water_levels[0],
                    'success': True
                }
                
                print(f"  实际坡度: {actual_slope:.6f}")
                print(f"  总损失: {total_loss:.3f} m")
                print(f"  上游水位: {water_levels[0]:.3f} m")
                
            except Exception as e:
                print(f"  计算失败: {e}")
                results[factor] = {'success': False, 'error': str(e)}
        
        return {'test_flow': test_flow, 'slope_results': results}
    
    def compare_flow_effects(self, slope_factor: float = 1.0) -> Dict[str, Any]:
        """对比不同流量下的水头损失"""
        print(f"\n=== 流量对比分析 (坡度倍数: {slope_factor:.1f}x) ===")
        
        # 测试流量范围
        test_flows = [10.0, 20.0, 30.0, 45.0, 60.0, 80.0]
        results = {}
        
        # 创建指定坡度的配置
        modified_config = self.base_config.copy()
        if slope_factor != 1.0:
            original_elevations = [s['elevation'] for s in self.base_config['sections']]
            modified_config['sections'] = []
            
            for i, section in enumerate(self.base_config['sections']):
                new_section = section.copy()
                if i == len(self.base_config['sections']) - 1:
                    new_section['elevation'] = original_elevations[i]
                else:
                    total_length = sum(
                        abs(self.base_config['sections'][j+1]['mileage'] - 
                            self.base_config['sections'][j]['mileage'])
                        for j in range(len(self.base_config['sections'])-1)
                    )
                    original_slope = (original_elevations[0] - original_elevations[-1]) / total_length
                    new_slope = original_slope * slope_factor
                    
                    if i == 0:
                        new_section['elevation'] = original_elevations[-1] + new_slope * total_length
                    else:
                        distance_from_downstream = sum(
                            abs(self.base_config['sections'][j+1]['mileage'] - 
                                self.base_config['sections'][j]['mileage'])
                            for j in range(i, len(self.base_config['sections'])-1)
                        )
                        new_section['elevation'] = original_elevations[-1] + new_slope * distance_from_downstream
                
                modified_config['sections'].append(new_section)
        
        model = self._create_model_from_config(modified_config)
        
        for Q in test_flows:
            print(f"\n流量: {Q:.1f} m³/s")
            
            try:
                steady_result = model.compute_steady_state(Q, self.downstream_level)
                water_levels = [steady_result[f'H_section_{i}'] 
                               for i in range(len(model.sections))]
                total_loss = water_levels[0] - water_levels[-1]
                
                # 计算单位流量损失和损失系数
                unit_loss_per_flow = total_loss / Q if Q > 0 else 0
                loss_coefficient = total_loss / (Q**2) if Q > 0 else 0
                
                results[Q] = {
                    'total_loss': total_loss,
                    'upstream_level': water_levels[0],
                    'unit_loss_per_flow': unit_loss_per_flow,
                    'loss_coefficient': loss_coefficient,
                    'success': True
                }
                
                print(f"  总损失: {total_loss:.3f} m")
                print(f"  单位流量损失: {unit_loss_per_flow:.4f} m/(m³/s)")
                print(f"  损失系数: {loss_coefficient:.6f} m/(m³/s)²")
                
            except Exception as e:
                print(f"  计算失败: {e}")
                results[Q] = {'success': False, 'error': str(e)}
        
        return {'slope_factor': slope_factor, 'flow_results': results}
    
    def compare_section_effects(self, test_flow: float = 30.0) -> Dict[str, Any]:
        """对比不同断面参数的影响"""
        print(f"\n=== 断面参数对比分析 (Q = {test_flow:.1f} m³/s) ===")
        
        results = {}
        
        # 1. 底宽变化对比
        print("\n--- 底宽变化对比 ---")
        width_factors = [0.8, 0.9, 1.0, 1.1, 1.2]
        width_results = {}
        
        for factor in width_factors:
            modified_config = self.base_config.copy()
            for section in modified_config['sections']:
                section['cross_section']['bottom_width'] *= factor
            
            try:
                model = self._create_model_from_config(modified_config)
                steady_result = model.compute_steady_state(test_flow, self.downstream_level)
                water_levels = [steady_result[f'H_section_{i}'] 
                               for i in range(len(model.sections))]
                total_loss = water_levels[0] - water_levels[-1]
                
                width_results[factor] = {
                    'total_loss': total_loss,
                    'upstream_level': water_levels[0],
                    'success': True
                }
                
                print(f"  底宽倍数{factor:.1f}: 损失{total_loss:.3f}m")
                
            except Exception as e:
                width_results[factor] = {'success': False, 'error': str(e)}
        
        # 2. 边坡系数变化对比
        print("\n--- 边坡系数变化对比 ---")
        slope_coeff_factors = [0.7, 0.85, 1.0, 1.15, 1.3]
        slope_coeff_results = {}
        
        for factor in slope_coeff_factors:
            modified_config = self.base_config.copy()
            for section in modified_config['sections']:
                section['cross_section']['side_slope'] *= factor
            
            try:
                model = self._create_model_from_config(modified_config)
                steady_result = model.compute_steady_state(test_flow, self.downstream_level)
                water_levels = [steady_result[f'H_section_{i}'] 
                               for i in range(len(model.sections))]
                total_loss = water_levels[0] - water_levels[-1]
                
                slope_coeff_results[factor] = {
                    'total_loss': total_loss,
                    'upstream_level': water_levels[0],
                    'success': True
                }
                
                print(f"  边坡倍数{factor:.2f}: 损失{total_loss:.3f}m")
                
            except Exception as e:
                slope_coeff_results[factor] = {'success': False, 'error': str(e)}
        
        return {
            'test_flow': test_flow,
            'width_results': width_results,
            'slope_coeff_results': slope_coeff_results
        }
    
    def comprehensive_sensitivity_analysis(self) -> Dict[str, Any]:
        """综合敏感性分析"""
        print(f"\n=== 综合参数敏感性分析 ===")
        
        # 基准工况
        base_flow = 30.0
        base_model = self._create_model_from_config(self.base_config)
        base_result = base_model.compute_steady_state(base_flow, self.downstream_level)
        base_levels = [base_result[f'H_section_{i}'] for i in range(len(base_model.sections))]
        base_loss = base_levels[0] - base_levels[-1]
        
        print(f"基准工况 (Q={base_flow}m³/s): 损失 = {base_loss:.3f}m")
        
        # 参数敏感性测试
        sensitivity_results = {
            'base_loss': base_loss,
            'base_flow': base_flow,
            'parameters': {}
        }
        
        # 测试各参数的敏感性
        test_params = [
            ('坡度', [0.8, 1.2], lambda config, factor: self._modify_slope(config, factor)),
            ('流量', [0.8, 1.2], lambda config, factor: (config, base_flow * factor)),
            ('底宽', [0.9, 1.1], lambda config, factor: self._modify_width(config, factor)),
            ('边坡系数', [0.9, 1.1], lambda config, factor: self._modify_side_slope(config, factor)),
            ('糙率系数', [0.9, 1.1], lambda config, factor: self._modify_roughness(config, factor))
        ]
        
        for param_name, factors, modifier in test_params:
            param_sensitivity = []
            
            for factor in factors:
                if param_name == '流量':
                    config, test_flow = modifier(self.base_config.copy(), factor)
                    model = self._create_model_from_config(config)
                    result = model.compute_steady_state(test_flow, self.downstream_level)
                else:
                    config = modifier(self.base_config.copy(), factor)
                    model = self._create_model_from_config(config)
                    result = model.compute_steady_state(base_flow, self.downstream_level)
                
                levels = [result[f'H_section_{i}'] for i in range(len(model.sections))]
                loss = levels[0] - levels[-1]
                
                # 计算敏感性系数
                param_change = (factor - 1.0) * 100  # 参数变化百分比
                loss_change = (loss - base_loss) / base_loss * 100  # 损失变化百分比
                sensitivity = loss_change / param_change if param_change != 0 else 0
                
                param_sensitivity.append({
                    'factor': factor,
                    'loss': loss,
                    'param_change_percent': param_change,
                    'loss_change_percent': loss_change,
                    'sensitivity_coefficient': sensitivity
                })
            
            sensitivity_results['parameters'][param_name] = param_sensitivity
            
            # 显示结果
            avg_sensitivity = sum(p['sensitivity_coefficient'] for p in param_sensitivity) / len(param_sensitivity)
            print(f"{param_name:8s}: 平均敏感性系数 = {avg_sensitivity:6.3f}")
        
        return sensitivity_results
    
    def _modify_slope(self, config: Dict[str, Any], factor: float) -> Dict[str, Any]:
        """修改坡度"""
        original_elevations = [s['elevation'] for s in config['sections']]
        total_length = sum(
            abs(config['sections'][j+1]['mileage'] - config['sections'][j]['mileage'])
            for j in range(len(config['sections'])-1)
        )
        original_slope = (original_elevations[0] - original_elevations[-1]) / total_length
        new_slope = original_slope * factor
        
        for i, section in enumerate(config['sections']):
            if i == len(config['sections']) - 1:
                continue
            elif i == 0:
                section['elevation'] = original_elevations[-1] + new_slope * total_length
            else:
                distance_from_downstream = sum(
                    abs(config['sections'][j+1]['mileage'] - config['sections'][j]['mileage'])
                    for j in range(i, len(config['sections'])-1)
                )
                section['elevation'] = original_elevations[-1] + new_slope * distance_from_downstream
        
        return config
    
    def _modify_width(self, config: Dict[str, Any], factor: float) -> Dict[str, Any]:
        """修改底宽"""
        for section in config['sections']:
            section['cross_section']['bottom_width'] *= factor
        return config
    
    def _modify_side_slope(self, config: Dict[str, Any], factor: float) -> Dict[str, Any]:
        """修改边坡系数"""
        for section in config['sections']:
            section['cross_section']['side_slope'] *= factor
        return config
    
    def _modify_roughness(self, config: Dict[str, Any], factor: float) -> Dict[str, Any]:
        """修改糙率系数"""
        for section in config['sections']:
            section['roughness'] *= factor
        return config
    
    def export_comparison_results(self, all_results: Dict[str, Any], 
                                filename: Optional[str] = None):
        """导出对比分析结果"""
        if filename is None:
            filename = f"outputs/data/参数对比分析_{self.base_config['name']}.csv"
        
        output_dir = Path(filename).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"\n导出对比分析结果: {filename}")
        
        with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)
            
            # 写入坡度对比结果
            if 'slope_analysis' in all_results:
                writer.writerow(['坡度对比分析'])
                writer.writerow(['坡度倍数', '实际坡度', '总损失(m)', '上游水位(m)'])
                
                for factor, result in all_results['slope_analysis']['slope_results'].items():
                    if result['success']:
                        writer.writerow([factor, result['actual_slope'], 
                                       result['total_loss'], result['upstream_level']])
                writer.writerow([])
            
            # 写入流量对比结果
            if 'flow_analysis' in all_results:
                writer.writerow(['流量对比分析'])
                writer.writerow(['流量(m³/s)', '总损失(m)', '单位损失(m·s/m³)', '损失系数'])
                
                for flow, result in all_results['flow_analysis']['flow_results'].items():
                    if result['success']:
                        writer.writerow([flow, result['total_loss'], 
                                       result['unit_loss_per_flow'], result['loss_coefficient']])
                writer.writerow([])
            
            # 写入敏感性分析结果
            if 'sensitivity_analysis' in all_results:
                writer.writerow(['参数敏感性分析'])
                writer.writerow(['参数', '变化(%)', '损失变化(%)', '敏感性系数'])
                
                for param, results in all_results['sensitivity_analysis']['parameters'].items():
                    for result in results:
                        writer.writerow([param, result['param_change_percent'],
                                       result['loss_change_percent'], result['sensitivity_coefficient']])
                writer.writerow([])
        
        print(f"✓ 对比分析结果已导出: {filename}")
    
    def run_complete_comparison(self):
        """运行完整的参数对比分析"""
        print("开始渠道参数对比分析")
        print("="*60)
        print(f"基础配置: {self.base_config['name']}")
        
        all_results = {}
        
        # 1. 坡度对比分析
        slope_analysis = self.compare_slope_effects()
        all_results['slope_analysis'] = slope_analysis
        
        # 2. 流量对比分析  
        flow_analysis = self.compare_flow_effects()
        all_results['flow_analysis'] = flow_analysis
        
        # 3. 断面参数对比分析
        section_analysis = self.compare_section_effects()
        all_results['section_analysis'] = section_analysis
        
        # 4. 综合敏感性分析
        sensitivity_analysis = self.comprehensive_sensitivity_analysis()
        all_results['sensitivity_analysis'] = sensitivity_analysis
        
        # 5. 导出结果
        self.export_comparison_results(all_results)
        
        print("\n" + "="*60)
        print("参数对比分析完成!")
        print("="*60)
        print("主要发现:")
        
        # 显示关键发现
        if 'sensitivity_analysis' in all_results:
            sensitivities = {}
            for param, results in all_results['sensitivity_analysis']['parameters'].items():
                avg_sens = sum(r['sensitivity_coefficient'] for r in results) / len(results)
                sensitivities[param] = abs(avg_sens)
            
            # 按敏感性排序
            sorted_params = sorted(sensitivities.items(), key=lambda x: x[1], reverse=True)
            print("参数敏感性排序:")
            for i, (param, sens) in enumerate(sorted_params, 1):
                print(f"  {i}. {param}: {sens:.3f}")
        
        return all_results


def main():
    """主函数"""
    config_path = "configs/complex_channel.yaml"
    
    if not os.path.exists(config_path):
        config_path = "configs/trapezoidal_channel.yaml"
        if not os.path.exists(config_path):
            print("错误: 找不到渠道配置文件")
            return
    
    try:
        comparator = ChannelParameterComparator(config_path)
        results = comparator.run_complete_comparison()
        
        print(f"\n分析完成，结果已保存到 outputs/data/ 目录")
        
    except Exception as e:
        print(f"分析过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()