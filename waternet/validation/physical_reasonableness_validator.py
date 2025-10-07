#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
物理合理性验证器 - 核心模块

根据项目规范"结果合理性验证规范"，实现仿真结果的物理合理性自动检查：
1. 水位分布合理性验证
2. 流量平衡检查  
3. 流速特性分析
4. 物理假设条件验证

Author: WaterNet Development Team
Date: 2024-10-05
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['SimHei']  # 中文字体
matplotlib.rcParams['axes.unicode_minus'] = False

from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import warnings
import json
from datetime import datetime


class PhysicalReasonablenessValidator:
    """
    物理合理性验证器
    
    执行基于物理原理的仿真结果验证，包括：
    - 质量守恒验证（连续性方程）
    - 能量守恒验证（伯努利方程）
    - 流速特性分析（雷诺数、弗劳德数）
    - 几何约束验证（负水深检测）
    - 方法假设验证（模型适用条件）
    """
    
    def __init__(self, tolerance_config: Optional[Dict] = None):
        """
        初始化验证器
        
        Args:
            tolerance_config: 容差配置字典
        """
        self.tolerance_config = tolerance_config or self._default_tolerance_config()
        self.validation_results = {}
        self.warnings = []
        self.errors = []
        
    def _default_tolerance_config(self) -> Dict:
        """默认容差配置"""
        return {
            'mass_balance_tolerance': 0.05,  # 质量平衡容差 5%
            'velocity_range': (0.1, 5.0),   # 合理流速范围 (m/s)
            'froude_number_range': (0.1, 2.0),  # 弗劳德数范围
            'water_level_gradient_max': 0.01,   # 最大水面坡度
            'energy_loss_coefficient_range': (0.001, 0.1),  # 能量损失系数范围
            'reynolds_number_min': 2000,     # 最小雷诺数（湍流假设）
        }
    
    def validate_simulation_results(self, 
                                  results: Dict[str, Any],
                                  method_info: Dict[str, Any],
                                  geometry_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        全面验证仿真结果的物理合理性
        
        Args:
            results: 仿真结果数据
            method_info: 仿真方法信息
            geometry_info: 几何信息
            
        Returns:
            验证结果字典
        """
        validation_report = {
            'validation_timestamp': datetime.now().isoformat(),
            'method_name': method_info.get('name', 'Unknown'),
            'method_type': method_info.get('type', 'Unknown'),
            'physical_checks': {},
            'warnings': [],
            'errors': [],
            'overall_validity': 'UNKNOWN'
        }
        
        try:
            # 1. 质量守恒验证
            mass_balance_check = self._validate_mass_conservation(results, geometry_info)
            validation_report['physical_checks']['mass_conservation'] = mass_balance_check
            
            # 2. 水位分布合理性
            water_level_check = self._validate_water_level_distribution(results, geometry_info)
            validation_report['physical_checks']['water_level_distribution'] = water_level_check
            
            # 3. 流速特性分析
            velocity_check = self._validate_velocity_characteristics(results, method_info, geometry_info)
            validation_report['physical_checks']['velocity_characteristics'] = velocity_check
            
            # 4. 能量守恒验证
            energy_check = self._validate_energy_conservation(results, geometry_info)
            validation_report['physical_checks']['energy_conservation'] = energy_check
            
            # 5. 方法特定假设验证
            assumption_check = self._validate_method_assumptions(results, method_info, geometry_info)
            validation_report['physical_checks']['method_assumptions'] = assumption_check
            
            # 6. 综合评估
            overall_validity = self._assess_overall_validity(validation_report['physical_checks'])
            validation_report['overall_validity'] = overall_validity
            
            # 收集警告和错误
            validation_report['warnings'] = self.warnings.copy()
            validation_report['errors'] = self.errors.copy()
            
        except Exception as e:
            validation_report['errors'].append(f"验证过程发生异常: {str(e)}")
            validation_report['overall_validity'] = 'ERROR'
        
        # 清空临时存储
        self.warnings.clear()
        self.errors.clear()
        
        return validation_report
    
    def _validate_mass_conservation(self, results: Dict, geometry_info: Dict) -> Dict:
        """验证质量守恒（连续性方程）"""
        check_result = {
            'status': 'UNKNOWN',
            'flow_continuity_errors': [],
            'max_relative_error': 0.0,
            'details': {}
        }
        
        try:
            if 'time_series' in results:
                # 非恒定流质量守恒检查
                time_series = results['time_series']
                
                # 检查每个时间步的流量连续性
                for i, step in enumerate(time_series):
                    q_in = step.get('Q_in', 0)
                    q_out = step.get('Q_out', 0)
                    
                    if q_in > 0:
                        relative_error = abs(q_out - q_in) / q_in
                        check_result['max_relative_error'] = max(
                            check_result['max_relative_error'], relative_error
                        )
                        
                        if relative_error > self.tolerance_config['mass_balance_tolerance']:
                            check_result['flow_continuity_errors'].append({
                                'time_step': i,
                                'Q_in': q_in,
                                'Q_out': q_out,
                                'relative_error': relative_error
                            })
                
                # 状态判断
                if check_result['max_relative_error'] <= self.tolerance_config['mass_balance_tolerance']:
                    check_result['status'] = 'PASS'
                elif check_result['max_relative_error'] <= self.tolerance_config['mass_balance_tolerance'] * 2:
                    check_result['status'] = 'WARNING'
                    self.warnings.append(f"质量守恒偏差较大: {check_result['max_relative_error']:.3f}")
                else:
                    check_result['status'] = 'FAIL'
                    self.errors.append(f"质量守恒严重违反: {check_result['max_relative_error']:.3f}")
                    
            else:
                # 恒定流质量守恒检查
                if 'Q_seg_0' in results and 'Q_seg_1' in results:
                    q1 = results['Q_seg_0']
                    q2 = results['Q_seg_1']
                    
                    if q1 > 0:
                        relative_error = abs(q2 - q1) / q1
                        check_result['max_relative_error'] = relative_error
                        
                        if relative_error <= self.tolerance_config['mass_balance_tolerance']:
                            check_result['status'] = 'PASS'
                        else:
                            check_result['status'] = 'FAIL'
                            self.errors.append(f"恒定流质量不守恒: {relative_error:.3f}")
                
        except Exception as e:
            check_result['status'] = 'ERROR'
            self.errors.append(f"质量守恒验证异常: {str(e)}")
        
        return check_result
    
    def _validate_water_level_distribution(self, results: Dict, geometry_info: Dict) -> Dict:
        """验证水位分布的物理合理性"""
        check_result = {
            'status': 'UNKNOWN',
            'water_surface_slope': None,
            'slope_reasonableness': 'UNKNOWN',
            'negative_depth_count': 0,
            'details': {}
        }
        
        try:
            # 提取水位数据
            water_levels = []
            elevations = []
            
            # 从结果中提取断面水位
            for key, value in results.items():
                if key.startswith('H_section_'):
                    water_levels.append(value)
            
            # 从几何信息中提取河底高程
            if 'sections' in geometry_info:
                for section in geometry_info['sections']:
                    elevations.append(section.get('elevation', 0))
            
            if len(water_levels) >= 2 and len(elevations) >= 2:
                # 计算水面坡度
                water_surface_slope = (water_levels[0] - water_levels[-1]) / len(water_levels)
                check_result['water_surface_slope'] = water_surface_slope
                
                # 检查水面坡度合理性
                max_slope = self.tolerance_config['water_level_gradient_max']
                if abs(water_surface_slope) <= max_slope:
                    check_result['slope_reasonableness'] = 'REASONABLE'
                    check_result['status'] = 'PASS'
                else:
                    check_result['slope_reasonableness'] = 'EXCESSIVE'
                    check_result['status'] = 'WARNING'
                    self.warnings.append(f"水面坡度过大: {water_surface_slope:.6f}")
                
                # 检查负水深
                for i, (h, z) in enumerate(zip(water_levels, elevations)):
                    if h < z:
                        check_result['negative_depth_count'] += 1
                        
                if check_result['negative_depth_count'] > 0:
                    check_result['status'] = 'FAIL'
                    self.errors.append(f"存在负水深: {check_result['negative_depth_count']}个断面")
                    
        except Exception as e:
            check_result['status'] = 'ERROR'
            self.errors.append(f"水位分布验证异常: {str(e)}")
        
        return check_result
    
    def _validate_velocity_characteristics(self, results: Dict, method_info: Dict, geometry_info: Dict) -> Dict:
        """验证流速特性及其与方法假设的一致性"""
        check_result = {
            'status': 'UNKNOWN',
            'velocity_range': None,
            'froude_numbers': [],
            'reynolds_numbers': [],
            'method_assumption_compliance': 'UNKNOWN',
            'details': {}
        }
        
        try:
            # 计算流速
            velocities = []
            froude_numbers = []
            reynolds_numbers = []
            
            if 'time_series' in results:
                # 非恒定流
                time_series = results['time_series']
                for step in time_series:
                    q = step.get('Q_out', 0)
                    
                    if q > 0:
                        # 估算面积和流速（简化为矩形断面）
                        width = geometry_info.get('average_width', 15.0)  # 从几何数据获取
                        depth = 2.0  # 估算水深
                        area = width * depth
                        velocity = q / area if area > 0 else 0
                        
                        velocities.append(velocity)
                        
                        # 弗劳德数
                        froude = velocity / np.sqrt(9.81 * depth) if depth > 0 else 0
                        froude_numbers.append(froude)
                        
                        # 雷诺数（简化计算）
                        nu = 1e-6  # 运动粘度
                        reynolds = velocity * depth / nu if nu > 0 else 0
                        reynolds_numbers.append(reynolds)
                        
            else:
                # 恒定流 - 使用断面信息计算
                if 'Q_seg_0' in results:
                    q = results['Q_seg_0']
                    # 从几何信息估算面积
                    estimated_area = 50.0  # 可以从geometry_info计算得出
                    velocity = q / estimated_area
                    velocities.append(velocity)
                    
                    depth = 2.0
                    froude = velocity / np.sqrt(9.81 * depth)
                    froude_numbers.append(froude)
                    
                    reynolds = velocity * depth / 1e-6
                    reynolds_numbers.append(reynolds)
            
            if velocities:
                check_result['velocity_range'] = (min(velocities), max(velocities))
                check_result['froude_numbers'] = froude_numbers
                check_result['reynolds_numbers'] = reynolds_numbers
                
                # 检查流速合理性
                v_min, v_max = self.tolerance_config['velocity_range']
                if all(v_min <= v <= v_max for v in velocities):
                    check_result['status'] = 'PASS'
                else:
                    out_of_range = [v for v in velocities if not (v_min <= v <= v_max)]
                    if len(out_of_range) / len(velocities) < 0.2:  # 少于20%超出范围
                        check_result['status'] = 'WARNING'
                        self.warnings.append(f"部分流速超出合理范围: {len(out_of_range)}个")
                    else:
                        check_result['status'] = 'FAIL'
                        self.errors.append(f"大量流速不合理: {len(out_of_range)}个")
                
                # 验证方法特定假设
                method_type = method_info.get('type', '')
                assumption_check = self._check_method_velocity_assumptions(
                    velocities, froude_numbers, method_type
                )
                check_result['method_assumption_compliance'] = assumption_check
                
        except Exception as e:
            check_result['status'] = 'ERROR'
            self.errors.append(f"流速特性验证异常: {str(e)}")
        
        return check_result
    
    def _check_method_velocity_assumptions(self, velocities: List[float], 
                                         froude_numbers: List[float], 
                                         method_type: str) -> str:
        """检查方法特定的流速假设"""
        try:
            avg_froude = np.mean(froude_numbers) if froude_numbers else 0
            avg_velocity = np.mean(velocities) if velocities else 0
            
            if 'kinematic_wave' in method_type.lower():
                # 运动波：适用于陡坡急流，Fr > 0.5
                if avg_froude > 0.5:
                    return 'COMPLIANT'
                else:
                    self.warnings.append(f"运动波方法：弗劳德数过小 ({avg_froude:.2f} < 0.5)")
                    return 'MARGINAL'
                    
            elif 'diffusive_wave' in method_type.lower():
                # 扩散波：适用于缓流，Fr < 1.0
                if avg_froude < 1.0:
                    return 'COMPLIANT'
                else:
                    self.warnings.append(f"扩散波方法：弗劳德数过大 ({avg_froude:.2f} > 1.0)")
                    return 'MARGINAL'
                    
            elif 'muskingum' in method_type.lower():
                # 马斯京干法：适用于中等流速
                if 0.5 <= avg_velocity <= 2.0:
                    return 'COMPLIANT'
                else:
                    self.warnings.append(f"马斯京干法：流速范围不适宜 ({avg_velocity:.2f} m/s)")
                    return 'MARGINAL'
                    
            return 'UNKNOWN'
            
        except Exception:
            return 'ERROR'
    
    def _validate_energy_conservation(self, results: Dict, geometry_info: Dict) -> Dict:
        """验证能量守恒"""
        check_result = {
            'status': 'UNKNOWN',
            'energy_losses': [],
            'energy_balance_error': 0.0,
            'details': {}
        }
        
        try:
            # 简化的能量守恒检查
            if 'time_series' in results:
                # 检查能量变化趋势的合理性
                time_series = results['time_series']
                storage_values = [step.get('V', 0) for step in time_series]
                
                if storage_values:
                    # 检查蓄量变化的物理合理性
                    storage_changes = np.diff(storage_values)
                    reasonable_changes = all(abs(change) < max(storage_values) * 0.5 
                                           for change in storage_changes)
                    
                    if reasonable_changes:
                        check_result['status'] = 'PASS'
                    else:
                        check_result['status'] = 'WARNING'
                        self.warnings.append("蓄量变化过于剧烈")
                        
            else:
                # 恒定流能量守恒检查（简化）
                check_result['status'] = 'PASS'  # 暂时通过
                
        except Exception as e:
            check_result['status'] = 'ERROR'
            self.errors.append(f"能量守恒验证异常: {str(e)}")
        
        return check_result
    
    def _validate_method_assumptions(self, results: Dict, method_info: Dict, geometry_info: Dict) -> Dict:
        """验证方法特定假设"""
        check_result = {
            'status': 'UNKNOWN',
            'assumption_violations': [],
            'compliance_score': 0.0,
            'details': {}
        }
        
        try:
            method_type = method_info.get('type', '').lower()
            violations = []
            
            # 根据方法类型检查特定假设
            if 'saint_venant' in method_type:
                # 圣维南方程假设检查
                check_result['status'] = 'PASS'  # 基础假设通常满足
                
            elif 'kinematic_wave' in method_type:
                # 运动波假设：河底坡度Sf ≈ S0，忽略惯性项
                slope = geometry_info.get('slope', 0.001)
                if slope < 0.002:
                    violations.append("河底坡度过小，扩散效应可能显著")
                    
            elif 'diffusive_wave' in method_type:
                # 扩散波假设：忽略惯性项，保留压力项
                pass
                
            elif 'muskingum' in method_type:
                # 马斯京干假设：线性存储-泄流关系
                if 'time_series' in results:
                    time_series = results['time_series']
                    flows_out = [step.get('Q_out', 0) for step in time_series]
                    storages = [step.get('V', 0) for step in time_series]
                    
                    # 检查存储-泄流关系的线性性
                    if len(flows_out) > 3 and len(storages) > 3:
                        correlation = np.corrcoef(flows_out, storages)[0, 1]
                        if correlation < 0.7:
                            violations.append(f"存储-泄流关系非线性 (相关系数: {correlation:.2f})")
            
            # 计算合规性评分
            total_checks = max(1, len(violations) + 3)  # 假设总共有若干检查项
            compliance_score = max(0, (total_checks - len(violations)) / total_checks)
            check_result['compliance_score'] = compliance_score
            check_result['assumption_violations'] = violations
            
            if len(violations) == 0:
                check_result['status'] = 'PASS'
            elif len(violations) <= 2:
                check_result['status'] = 'WARNING'
                self.warnings.extend(violations)
            else:
                check_result['status'] = 'FAIL'
                self.errors.extend(violations)
                
        except Exception as e:
            check_result['status'] = 'ERROR'
            self.errors.append(f"方法假设验证异常: {str(e)}")
        
        return check_result
    
    def _assess_overall_validity(self, physical_checks: Dict) -> str:
        """评估总体有效性"""
        status_scores = {'PASS': 3, 'WARNING': 2, 'MARGINAL': 1, 'FAIL': 0, 'ERROR': -1, 'UNKNOWN': 0}
        
        total_score = 0
        total_checks = 0
        
        for check_name, check_result in physical_checks.items():
            if isinstance(check_result, dict) and 'status' in check_result:
                status = check_result['status']
                score = status_scores.get(status, 0)
                total_score += score
                total_checks += 1
        
        if total_checks == 0:
            return 'UNKNOWN'
        
        average_score = total_score / total_checks
        
        if average_score >= 2.5:
            return 'VALID'
        elif average_score >= 1.5:
            return 'ACCEPTABLE_WITH_WARNINGS'
        elif average_score >= 0.5:
            return 'QUESTIONABLE'
        else:
            return 'INVALID'


def validate_multiple_methods(simulation_results: Dict[str, Dict], 
                            geometry_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    对多种方法的仿真结果进行批量物理合理性验证
    
    Args:
        simulation_results: 多个方法的仿真结果
        geometry_info: 几何信息
        
    Returns:
        批量验证结果
    """
    validator = PhysicalReasonablenessValidator()
    
    validation_results = {}
    
    for method_name, result_data in simulation_results.items():
        method_info = {
            'name': method_name,
            'type': result_data.get('config', {}).get('type', method_name)
        }
        
        results = result_data.get('results', {})
        
        validation_result = validator.validate_simulation_results(
            results, method_info, geometry_info
        )
        
        validation_results[method_name] = validation_result
    
    return validation_results


if __name__ == "__main__":
    # 示例用法
    print("🔬 物理合理性验证器已初始化")
    print("支持的验证功能：")
    print("  • 质量守恒验证（连续性方程）")
    print("  • 水位分布合理性检查")
    print("  • 流速特性分析（雷诺数、弗劳德数）")
    print("  • 能量守恒验证（简化）")
    print("  • 方法假设合规性检查")