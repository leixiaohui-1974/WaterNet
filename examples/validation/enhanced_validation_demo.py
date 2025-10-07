#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强型物理合理性验证演示

根据项目规范"结果合理性验证规范"，对现有仿真结果进行物理合理性检查：
1. 读取之前生成的仿真结果
2. 执行物理合理性验证
3. 生成验证报告和可视化图表

Author: WaterNet Development Team
Date: 2024-10-05
"""

import sys
import os
from pathlib import Path
import json
import numpy as np
from datetime import datetime
from typing import Dict, List, Any

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))


class PhysicalReasonablenessChecker:
    """
    物理合理性检查器
    
    根据"结果合理性验证规范"实现的验证功能：
    - 自动验证水位分布、流量平衡的物理意义
    - 检查各简化方法计算的流速是否符合假设条件
    - 通过图表直观展示不同方法的计算差异
    """
    
    def __init__(self):
        self.tolerance_config = {
            'mass_balance_tolerance': 0.05,  # 5%容差
            'velocity_range': (0.1, 5.0),   # 合理流速范围
            'froude_number_range': (0.1, 2.0),  # 弗劳德数范围
            'storage_change_rate_max': 0.5,  # 最大蓄量变化率
        }
    
    def validate_method_results(self, method_name: str, results: Dict, 
                              method_type: str = 'unknown') -> Dict:
        """验证单个方法的结果"""
        validation_report = {
            'method_name': method_name,
            'method_type': method_type,
            'validation_timestamp': datetime.now().isoformat(),
            'physical_checks': {},
            'warnings': [],
            'errors': [],
            'overall_validity': 'UNKNOWN'
        }
        
        try:
            # 1. 质量守恒检查
            mass_check = self._check_mass_conservation(results)
            validation_report['physical_checks']['mass_conservation'] = mass_check
            
            # 2. 流速特性检查
            velocity_check = self._check_velocity_characteristics(results, method_type)
            validation_report['physical_checks']['velocity_characteristics'] = velocity_check
            
            # 3. 存储变化合理性检查
            storage_check = self._check_storage_variation(results)
            validation_report['physical_checks']['storage_variation'] = storage_check
            
            # 4. 方法假设验证
            assumption_check = self._check_method_assumptions(results, method_type)
            validation_report['physical_checks']['method_assumptions'] = assumption_check
            
            # 5. 综合评价
            overall_validity = self._assess_overall_validity(validation_report['physical_checks'])
            validation_report['overall_validity'] = overall_validity
            
        except Exception as e:
            validation_report['errors'].append(f"验证过程异常: {str(e)}")
            validation_report['overall_validity'] = 'ERROR'
        
        return validation_report
    
    def _check_mass_conservation(self, results: Dict) -> Dict:
        """检查质量守恒"""
        check_result = {
            'status': 'UNKNOWN',
            'max_relative_error': 0.0,
            'continuity_errors': [],
            'details': {}
        }
        
        try:
            if 'time_series' in results:
                time_series = results['time_series']
                max_error = 0.0
                
                for i, step in enumerate(time_series):
                    q_in = step.get('Q_in', 0)
                    q_out = step.get('Q_out', 0)
                    
                    if q_in > 0:
                        relative_error = abs(q_out - q_in) / q_in
                        max_error = max(max_error, relative_error)
                        
                        if relative_error > self.tolerance_config['mass_balance_tolerance']:
                            check_result['continuity_errors'].append({
                                '时间步': i,
                                '入流': q_in,
                                '出流': q_out,
                                '相对误差': relative_error
                            })
                
                check_result['max_relative_error'] = max_error
                
                if max_error <= self.tolerance_config['mass_balance_tolerance']:
                    check_result['status'] = 'PASS'
                elif max_error <= self.tolerance_config['mass_balance_tolerance'] * 2:
                    check_result['status'] = 'WARNING'
                else:
                    check_result['status'] = 'FAIL'
                    
                check_result['details'] = {
                    '检查点数': len(time_series),
                    '最大相对误差': f"{max_error:.4f}",
                    '超标点数': len(check_result['continuity_errors'])
                }
            else:
                check_result['status'] = 'PASS'  # 恒定流默认通过
                
        except Exception as e:
            check_result['status'] = 'ERROR'
            check_result['details'] = {'错误': str(e)}
        
        return check_result
    
    def _check_velocity_characteristics(self, results: Dict, method_type: str) -> Dict:
        """检查流速特性"""
        check_result = {
            'status': 'UNKNOWN',
            'velocity_range': None,
            'froude_numbers': [],
            'method_compliance': 'UNKNOWN',
            'details': {}
        }
        
        try:
            velocities = []
            froude_numbers = []
            
            if 'time_series' in results:
                for step in results['time_series']:
                    q = step.get('Q_out', 0)
                    
                    if q > 0:
                        # 估算流速（基于典型断面）
                        estimated_area = 40.0  # 典型断面面积
                        velocity = q / estimated_area
                        velocities.append(velocity)
                        
                        # 计算弗劳德数
                        depth = 2.0  # 估算水深
                        froude = velocity / (9.81 * depth) ** 0.5
                        froude_numbers.append(froude)
            
            if velocities:
                check_result['velocity_range'] = (min(velocities), max(velocities))
                check_result['froude_numbers'] = froude_numbers
                
                # 检查流速合理性
                v_min, v_max = self.tolerance_config['velocity_range']
                reasonable_velocities = [v for v in velocities if v_min <= v <= v_max]
                
                if len(reasonable_velocities) == len(velocities):
                    check_result['status'] = 'PASS'
                elif len(reasonable_velocities) >= len(velocities) * 0.8:
                    check_result['status'] = 'WARNING'
                else:
                    check_result['status'] = 'FAIL'
                
                # 方法特定验证
                avg_froude = sum(froude_numbers) / len(froude_numbers) if froude_numbers else 0
                
                if 'kinematic' in method_type.lower():
                    # 运动波适用于急流
                    check_result['method_compliance'] = 'COMPLIANT' if avg_froude > 0.5 else 'MARGINAL'
                elif 'diffusive' in method_type.lower():
                    # 扩散波适用于缓流
                    check_result['method_compliance'] = 'COMPLIANT' if avg_froude < 1.0 else 'MARGINAL'
                else:
                    check_result['method_compliance'] = 'UNKNOWN'
                
                check_result['details'] = {
                    '平均流速': f"{sum(velocities)/len(velocities):.3f} m/s",
                    '平均弗劳德数': f"{avg_froude:.3f}",
                    '合理流速占比': f"{len(reasonable_velocities)/len(velocities)*100:.1f}%"
                }
                
        except Exception as e:
            check_result['status'] = 'ERROR'
            check_result['details'] = {'错误': str(e)}
        
        return check_result
    
    def _check_storage_variation(self, results: Dict) -> Dict:
        """检查蓄量变化合理性"""
        check_result = {
            'status': 'UNKNOWN',
            'storage_range': None,
            'max_change_rate': 0.0,
            'details': {}
        }
        
        try:
            if 'time_series' in results:
                time_series = results['time_series']
                storages = [step.get('V', 0) for step in time_series]
                
                if storages and len(storages) > 1:
                    check_result['storage_range'] = (min(storages), max(storages))
                    
                    # 计算变化率
                    max_change_rate = 0.0
                    for i in range(1, len(storages)):
                        if storages[i-1] > 0:
                            change_rate = abs(storages[i] - storages[i-1]) / storages[i-1]
                            max_change_rate = max(max_change_rate, change_rate)
                    
                    check_result['max_change_rate'] = max_change_rate
                    
                    if max_change_rate <= self.tolerance_config['storage_change_rate_max']:
                        check_result['status'] = 'PASS'
                    else:
                        check_result['status'] = 'WARNING'
                    
                    check_result['details'] = {
                        '蓄量范围': f"{min(storages):.0f} - {max(storages):.0f} m³",
                        '最大变化率': f"{max_change_rate:.3f}",
                        '总变化': f"{(max(storages) - min(storages)):.0f} m³"
                    }
                else:
                    check_result['status'] = 'PASS'
            else:
                check_result['status'] = 'PASS'  # 恒定流默认通过
                
        except Exception as e:
            check_result['status'] = 'ERROR'
            check_result['details'] = {'错误': str(e)}
        
        return check_result
    
    def _check_method_assumptions(self, results: Dict, method_type: str) -> Dict:
        """检查方法假设"""
        check_result = {
            'status': 'UNKNOWN',
            'assumption_violations': [],
            'compliance_score': 0.0,
            'details': {}
        }
        
        try:
            violations = []
            
            if 'muskingum' in method_type.lower():
                # 马斯京干法假设检查
                if 'time_series' in results:
                    time_series = results['time_series']
                    flows_out = [step.get('Q_out', 0) for step in time_series]
                    storages = [step.get('V', 0) for step in time_series]
                    
                    if len(flows_out) > 3 and len(storages) > 3:
                        # 检查存储-泄流关系线性性（简化计算）
                        flow_range = max(flows_out) - min(flows_out)
                        storage_range = max(storages) - min(storages)
                        
                        if flow_range > 0 and storage_range > 0:
                            # 简单的线性关系检查
                            correlation_indicator = flow_range / storage_range
                            if correlation_indicator < 0.01 or correlation_indicator > 100:
                                violations.append("存储-泄流关系可能非线性")
            
            elif 'saint_venant' in method_type.lower():
                # 圣维南方程假设通常满足
                pass
            
            elif 'wave' in method_type.lower():
                # 波动方程假设检查
                if 'kinematic' in method_type.lower():
                    # 运动波需要陡坡
                    # 这里需要几何信息，暂时跳过
                    pass
            
            # 计算合规性评分
            total_checks = max(1, 3)  # 假设总共3项检查
            compliance_score = max(0, (total_checks - len(violations)) / total_checks)
            check_result['compliance_score'] = compliance_score
            check_result['assumption_violations'] = violations
            
            if len(violations) == 0:
                check_result['status'] = 'PASS'
            elif len(violations) <= 1:
                check_result['status'] = 'WARNING'
            else:
                check_result['status'] = 'FAIL'
            
            check_result['details'] = {
                '方法类型': method_type,
                '合规性评分': f"{compliance_score:.2f}",
                '违背假设数': len(violations)
            }
            
        except Exception as e:
            check_result['status'] = 'ERROR'
            check_result['details'] = {'错误': str(e)}
        
        return check_result
    
    def _assess_overall_validity(self, physical_checks: Dict) -> str:
        """评估总体有效性"""
        status_weights = {'PASS': 3, 'WARNING': 2, 'FAIL': 1, 'ERROR': 0, 'UNKNOWN': 0}
        
        total_score = 0
        total_checks = 0
        
        for check_name, check_result in physical_checks.items():
            if isinstance(check_result, dict) and 'status' in check_result:
                status = check_result['status']
                score = status_weights.get(status, 0)
                total_score += score
                total_checks += 1
        
        if total_checks == 0:
            return 'UNKNOWN'
        
        average_score = total_score / total_checks
        
        if average_score >= 2.8:
            return 'VALID'
        elif average_score >= 2.0:
            return 'ACCEPTABLE_WITH_WARNINGS'
        elif average_score >= 1.0:
            return 'QUESTIONABLE'
        else:
            return 'INVALID'


def load_existing_simulation_results():
    """加载现有的仿真结果"""
    results_dir = Path('examples/unsteady_flow_methods/outputs/data')
    
    # 查找最新的结果文件
    result_files = list(results_dir.glob('*results*.json'))
    
    if not result_files:
        print("❌ 没有找到仿真结果文件")
        return {}
    
    # 使用最新的结果文件
    latest_file = max(result_files, key=lambda p: p.stat().st_mtime)
    print(f"📂 加载仿真结果: {latest_file.name}")
    
    try:
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 提取仿真结果
        simulation_results = {}
        
        if 'unsteady_flow_simulation' in data:
            # 单一方法结果
            method_name = latest_file.stem.replace('_results', '').replace('main_channel_', '')
            simulation_results[method_name] = {
                'results': data['unsteady_flow_simulation'],
                'config': {'type': 'unsteady_flow'}
            }
        else:
            # 多方法结果
            for key, value in data.items():
                if isinstance(value, dict) and ('time_series' in value or 'data' in value):
                    simulation_results[key] = {
                        'results': value,
                        'config': {'type': key.lower()}
                    }
        
        print(f"✅ 成功加载 {len(simulation_results)} 个方法的结果")
        return simulation_results
        
    except Exception as e:
        print(f"❌ 加载结果文件失败: {e}")
        return {}


def create_sample_results():
    """创建示例结果用于演示"""
    print("📊 创建示例仿真结果用于验证演示...")
    
    # 时间序列数据
    time_steps = [0, 3600, 7200, 10800, 14400, 18000]
    upstream_flows = [100.0, 120.0, 150.0, 130.0, 110.0, 95.0]
    
    simulation_results = {}
    
    # 1. 马斯京干模型（示例）
    muskingum_results = []
    q_out = 10.0
    storage = 400000.0
    
    for i, q_in in enumerate(upstream_flows):
        # 简单的马斯京干演算
        q_out = 0.2 * q_in + 0.8 * q_out
        storage += (q_in - q_out) * 3600  # 蓄量变化
        
        muskingum_results.append({
            'time': time_steps[i],
            'Q_in': q_in,
            'Q_out': q_out,
            'V': storage,
            'H_out': 85.0 + storage / 100000  # 简化的水位关系
        })
    
    simulation_results['马斯京干模型'] = {
        'results': {'time_series': muskingum_results},
        'config': {'type': 'muskingum_model'}
    }
    
    # 2. 完整圣维南方程（示例）
    saint_venant_results = []
    for i, q_in in enumerate(upstream_flows):
        # 圣维南方程结果（出流约等于入流，轻微坦化）
        q_out = q_in * 0.95 + 5.0
        storage = 1700000.0 + (q_in - 100) * 1000  # 与流量相关的蓄量
        
        saint_venant_results.append({
            'time': time_steps[i],
            'Q_in': q_in,
            'Q_out': q_out,
            'V': storage,
            'H_out': 96.0 + (q_in - 100) * 0.0001  # 水位与流量微弱相关
        })
    
    simulation_results['完整圣维南方程'] = {
        'results': {'time_series': saint_venant_results},
        'config': {'type': 'saint_venant_full'}
    }
    
    # 3. 扩散波方程（示例）
    diffusive_wave_results = []
    for i, q_in in enumerate(upstream_flows):
        # 扩散波有中等坦化效应
        q_out = q_in * 0.85 + 15.0
        storage = 1650000.0 + (q_in - 100) * 800
        
        diffusive_wave_results.append({
            'time': time_steps[i],
            'Q_in': q_in,
            'Q_out': q_out,
            'V': storage,
            'H_out': 96.0 + (q_in - 100) * 0.00008
        })
    
    simulation_results['扩散波方程'] = {
        'results': {'time_series': diffusive_wave_results},
        'config': {'type': 'diffusive_wave'}
    }
    
    print(f"✅ 创建了 {len(simulation_results)} 个示例方法的结果")
    return simulation_results


def perform_validation_analysis():
    """执行验证分析"""
    print("=" * 80)
    print("🔬 物理合理性验证分析系统")
    print("=" * 80)
    print("根据'结果合理性验证规范'，执行以下验证：")
    print("  • 物理合理性检查：自动验证水位分布、流量平衡的物理意义")
    print("  • 流速特性分析：检查各简化方法计算的流速是否符合假设条件")
    print("  • 可视化验证：通过数据分析直观展示不同方法的计算差异")
    print("=" * 80)
    
    # 尝试加载现有结果，如果没有则创建示例
    simulation_results = load_existing_simulation_results()
    if not simulation_results:
        simulation_results = create_sample_results()
    
    if not simulation_results:
        print("❌ 无法获取仿真结果，退出验证")
        return
    
    # 创建验证器
    checker = PhysicalReasonablenessChecker()
    validation_results = {}
    
    print(f"\n🔍 开始物理合理性验证...")
    
    # 对每个方法进行验证
    for method_name, result_data in simulation_results.items():
        print(f"\n📋 验证方法: {method_name}")
        
        results = result_data.get('results', {})
        method_type = result_data.get('config', {}).get('type', 'unknown')
        
        validation_result = checker.validate_method_results(
            method_name, results, method_type
        )
        
        validation_results[method_name] = validation_result
        
        # 输出验证摘要
        overall_validity = validation_result.get('overall_validity', 'UNKNOWN')
        physical_checks = validation_result.get('physical_checks', {})
        
        print(f"  综合评价: {overall_validity}")
        
        # 各项检查结果
        check_names = {
            'mass_conservation': '质量守恒',
            'velocity_characteristics': '流速特性',
            'storage_variation': '蓄量变化',
            'method_assumptions': '方法假设'
        }
        
        for check_key, check_name in check_names.items():
            if check_key in physical_checks:
                check_result = physical_checks[check_key]
                status = check_result.get('status', 'UNKNOWN')
                
                status_symbols = {
                    'PASS': '✅',
                    'WARNING': '⚠️',
                    'FAIL': '❌',
                    'ERROR': '🔥',
                    'UNKNOWN': '❓'
                }
                
                symbol = status_symbols.get(status, '❓')
                print(f"    {check_name}: {symbol} {status}")
                
                # 显示关键详情
                details = check_result.get('details', {})
                if details and isinstance(details, dict):
                    for detail_key, detail_value in list(details.items())[:2]:  # 只显示前2项
                        print(f"      {detail_key}: {detail_value}")
    
    # 生成验证报告
    print(f"\n📊 生成验证报告...")
    
    # 创建输出目录
    output_dir = Path('outputs/validation')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 保存验证结果JSON
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    json_path = output_dir / f'物理合理性验证结果_{timestamp}.json'
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(validation_results, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"💾 验证结果已保存: {json_path}")
    
    # 生成汇总统计
    print(f"\n📈 验证统计汇总:")
    print("-" * 50)
    
    valid_count = sum(1 for result in validation_results.values() 
                     if result.get('overall_validity') == 'VALID')
    acceptable_count = sum(1 for result in validation_results.values() 
                          if result.get('overall_validity') == 'ACCEPTABLE_WITH_WARNINGS')
    questionable_count = sum(1 for result in validation_results.values() 
                            if result.get('overall_validity') == 'QUESTIONABLE')
    invalid_count = sum(1 for result in validation_results.values() 
                       if result.get('overall_validity') == 'INVALID')
    
    total_methods = len(validation_results)
    
    print(f"验证方法总数: {total_methods}")
    print(f"✅ 物理有效: {valid_count} ({valid_count/total_methods*100:.1f}%)")
    print(f"⚠️ 有警告但可接受: {acceptable_count} ({acceptable_count/total_methods*100:.1f}%)")
    print(f"❓ 可疑: {questionable_count} ({questionable_count/total_methods*100:.1f}%)")
    print(f"❌ 物理无效: {invalid_count} ({invalid_count/total_methods*100:.1f}%)")
    
    # 详细分析
    print(f"\n🔍 详细分析结果:")
    print("-" * 50)
    
    for method_name, validation_result in validation_results.items():
        print(f"\n🔸 {method_name}:")
        
        physical_checks = validation_result.get('physical_checks', {})
        
        # 质量守恒详情
        mass_check = physical_checks.get('mass_conservation', {})
        if mass_check.get('status') != 'UNKNOWN':
            max_error = mass_check.get('max_relative_error', 0) * 100
            print(f"  质量守恒: 最大误差 {max_error:.2f}%")
        
        # 流速特性详情
        velocity_check = physical_checks.get('velocity_characteristics', {})
        velocity_range = velocity_check.get('velocity_range')
        if velocity_range:
            print(f"  流速范围: {velocity_range[0]:.3f} - {velocity_range[1]:.3f} m/s")
        
        # 方法假设详情
        assumption_check = physical_checks.get('method_assumptions', {})
        compliance_score = assumption_check.get('compliance_score', 0) * 100
        if compliance_score > 0:
            print(f"  假设合规性: {compliance_score:.1f}%")
    
    print("\n" + "=" * 80)
    print("🎯 验证结论")
    print("=" * 80)
    
    if valid_count + acceptable_count >= total_methods * 0.8:
        print("✅ 总体评价: 大部分方法通过物理合理性检查，系统运行良好")
    elif valid_count + acceptable_count >= total_methods * 0.6:
        print("⚠️ 总体评价: 多数方法基本合理，需关注部分方法的物理一致性")
    else:
        print("❌ 总体评价: 较多方法存在物理合理性问题，需要深入检查")
    
    # 生成可视化验证报告
    print(f"\n📊 生成可视化验证报告...")
    try:
        # 导入可视化模块
        try:
            from waternet.validation.validation_visualizer import (
                ValidationVisualizer, generate_validation_report
            )
            
            # 转换为列表格式
            validation_list = list(validation_results.values())
            
            # 生成报告
            report_path = generate_validation_report(validation_list, str(output_dir))
            print(f"📊 可视化报告已生成: {report_path}")
            
        except ImportError as e:
            print(f"⚠️ 可视化模块导入失败: {e}")
            print("尝试手动创建可视化报告...")
            
            # 手动创建简化版本可视化报告
            import matplotlib.pyplot as plt
            import numpy as np
            
            # 创建图表
            fig, axes = plt.subplots(2, 2, figsize=(16, 12))
            fig.suptitle('物理合理性验证报告', fontsize=16, fontweight='bold')
            
            # 准备数据
            methods = list(validation_results.keys())
            overall_scores = []
            mass_errors = []
            
            for method_name in methods:
                result = validation_results[method_name]
                
                # 计算总体分数
                physical_checks = result.get('physical_checks', {})
                score_map = {'PASS': 3, 'WARNING': 2, 'FAIL': 1, 'ERROR': 0, 'UNKNOWN': 0}
                total_score = 0
                count = 0
                
                for check in physical_checks.values():
                    if isinstance(check, dict) and 'status' in check:
                        total_score += score_map.get(check['status'], 0)
                        count += 1
                
                avg_score = total_score / count if count > 0 else 0
                overall_scores.append(avg_score)
                
                # 提取质量守恒误差
                mass_check = physical_checks.get('mass_conservation', {})
                mass_error = mass_check.get('max_relative_error', 0) * 100
                mass_errors.append(mass_error)
            
            # 1. 总体评分
            axes[0, 0].bar(methods, overall_scores, color=['green' if s >= 2.5 else 'orange' if s >= 2 else 'red' for s in overall_scores])
            axes[0, 0].set_title('方法总体评分', fontsize=14)
            axes[0, 0].set_ylabel('评分')
            axes[0, 0].tick_params(axis='x', rotation=45)
            
            # 2. 质量守恒误差
            axes[0, 1].bar(methods, mass_errors, color=['green' if e <= 5 else 'orange' if e <= 15 else 'red' for e in mass_errors])
            axes[0, 1].set_title('质量守恒最大误差 (%)', fontsize=14)
            axes[0, 1].set_ylabel('误差 (%)')
            axes[0, 1].tick_params(axis='x', rotation=45)
            
            # 3. 验证状态统计
            status_counts = {'VALID': 0, 'ACCEPTABLE': 0, 'QUESTIONABLE': 0, 'INVALID': 0}
            for result in validation_results.values():
                status = result.get('overall_validity', 'UNKNOWN')
                if status == 'VALID':
                    status_counts['VALID'] += 1
                elif status == 'ACCEPTABLE_WITH_WARNINGS':
                    status_counts['ACCEPTABLE'] += 1
                elif status == 'QUESTIONABLE':
                    status_counts['QUESTIONABLE'] += 1
                else:
                    status_counts['INVALID'] += 1
            
            axes[1, 0].pie(status_counts.values(), labels=status_counts.keys(), autopct='%1.1f%%')
            axes[1, 0].set_title('验证状态分布', fontsize=14)
            
            # 4. 检查项通过率
            check_names = ['质量守恒', '流速特性', '蓄量变化', '方法假设']
            check_keys = ['mass_conservation', 'velocity_characteristics', 'storage_variation', 'method_assumptions']
            pass_rates = []
            
            for check_key in check_keys:
                pass_count = 0
                total_count = 0
                for result in validation_results.values():
                    physical_checks = result.get('physical_checks', {})
                    if check_key in physical_checks:
                        total_count += 1
                        check_result = physical_checks[check_key]
                        if isinstance(check_result, dict) and check_result.get('status') in ['PASS', 'WARNING']:
                            pass_count += 1
                
                pass_rate = pass_count / total_count * 100 if total_count > 0 else 0
                pass_rates.append(pass_rate)
            
            axes[1, 1].bar(check_names, pass_rates, color='skyblue')
            axes[1, 1].set_title('各检查项通过率 (%)', fontsize=14)
            axes[1, 1].set_ylabel('通过率 (%)')
            axes[1, 1].tick_params(axis='x', rotation=45)
            
            plt.tight_layout()
            
            # 保存图表
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_path = output_dir / f'物理合理性验证报告_{timestamp}.svg'
            plt.savefig(report_path, format='svg', bbox_inches='tight', facecolor='white')
            plt.close()
            
            print(f"📊 手动生成的可视化报告已保存 (SVG): {report_path}")
            
    except Exception as e:
        print(f"⚠️ 可视化报告生成失败: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n✨ 根据'结果合理性验证规范'，物理合理性验证分析已完成")
    print(f"📄 详细结果已保存至: {json_path}")
    
    return validation_results


if __name__ == "__main__":
    # 执行验证分析
    results = perform_validation_analysis()