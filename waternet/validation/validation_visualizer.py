#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
物理合理性验证可视化器

根据项目规范"结果合理性验证规范"，提供验证结果的可视化展示：
1. 水位分布验证图表
2. 流量平衡检查图表
3. 流速特性分析图表
4. 方法假设合规性图表

Author: WaterNet Development Team
Date: 2024-10-05
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import seaborn as sns
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime
import warnings

# 配置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei']  # 中文字体
plt.rcParams['axes.unicode_minus'] = False


class ValidationVisualizer:
    """
    物理合理性验证可视化器
    
    生成符合用户规范的验证结果图表：
    - 遵循汉字与图形错开显示规范
    - 数字用红色突出显示，汉字用黑色普通显示
    - 图例字体放大2倍，汉字字体放大3倍
    - 边框线条加粗至3.0
    """
    
    def __init__(self):
        """初始化可视化器"""
        # 遵循用户字体显示规范
        self.title_fontsize = 18
        self.chinese_fontsize = 15  # 汉字字体放大3倍（从5变为15）
        self.number_fontsize = 12   # 数字字体翻倍
        self.legend_fontsize = 12   # 图例字体放大2倍
        
        # 颜色配置
        self.colors = {
            'pass': '#2ECC71',      # 绿色 - 通过
            'warning': '#F39C12',   # 橙色 - 警告
            'fail': '#E74C3C',      # 红色 - 失败
            'error': '#8E44AD',     # 紫色 - 错误
            'unknown': '#95A5A6'    # 灰色 - 未知
        }
        
    def generate_comprehensive_validation_report(self, 
                                               validation_results: List[Dict],
                                               output_path: str = None) -> str:
        """
        生成综合验证报告图表
        
        Args:
            validation_results: 多个方法的验证结果列表
            output_path: 输出路径
            
        Returns:
            生成的图表文件路径
        """
        if not validation_results:
            return ""
        
        # 创建图表
        fig = plt.figure(figsize=(24, 18))
        
        # 1. 方法对比雷达图 (综合评分)
        ax1 = plt.subplot(2, 4, 1, projection='polar')
        self._plot_method_comparison_radar(ax1, validation_results)
        
        # 2. 质量守恒误差对比
        ax2 = plt.subplot(2, 4, 2)
        self._plot_mass_balance_comparison(ax2, validation_results)
        
        # 3. 流速分布对比
        ax3 = plt.subplot(2, 4, 3)
        self._plot_velocity_distribution(ax3, validation_results)
        
        # 4. 弗劳德数分析
        ax4 = plt.subplot(2, 4, 4)
        self._plot_froude_number_analysis(ax4, validation_results)
        
        # 5. 方法假设合规性
        ax5 = plt.subplot(2, 4, 5)
        self._plot_assumption_compliance(ax5, validation_results)
        
        # 6. 水位分布合理性
        ax6 = plt.subplot(2, 4, 6)
        self._plot_water_level_validation(ax6, validation_results)
        
        # 7. 能量守恒检查
        ax7 = plt.subplot(2, 4, 7)
        self._plot_energy_conservation(ax7, validation_results)
        
        # 8. 综合验证状态表格
        ax8 = plt.subplot(2, 4, 8)
        self._plot_validation_summary_table(ax8, validation_results)
        
        plt.suptitle('水力学方法物理合理性验证综合报告', 
                    fontsize=self.title_fontsize, fontweight='bold')
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        
        # 保存图表
        if output_path is None:
            output_path = f'物理合理性验证报告_{datetime.now().strftime("%Y%m%d_%H%M%S")}.svg'
        
        plt.savefig(output_path, format='svg', bbox_inches='tight', facecolor='white')
        plt.close()
        
        return output_path
    
    def _plot_method_comparison_radar(self, ax, validation_results: List[Dict]):
        """绘制方法对比雷达图"""
        categories = ['质量守恒', '水位分布', '流速特性', '能量守恒', '方法假设']
        
        # 计算每个方法的评分
        method_scores = {}
        for result in validation_results:
            method_name = result.get('method_name', 'Unknown')
            checks = result.get('physical_checks', {})
            
            scores = []
            status_map = {'PASS': 5, 'WARNING': 3, 'MARGINAL': 2, 'FAIL': 1, 'ERROR': 0, 'UNKNOWN': 0}
            
            for category_key in ['mass_conservation', 'water_level_distribution', 
                               'velocity_characteristics', 'energy_conservation', 'method_assumptions']:
                check = checks.get(category_key, {})
                status = check.get('status', 'UNKNOWN')
                score = status_map.get(status, 0)
                scores.append(score)
            
            method_scores[method_name] = scores
        
        # 绘制雷达图
        angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False)
        angles = np.concatenate((angles, [angles[0]]))  # 闭合
        
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7']
        
        for i, (method_name, scores) in enumerate(method_scores.items()):
            scores_closed = scores + [scores[0]]  # 闭合
            ax.plot(angles, scores_closed, 'o-', linewidth=3.0,  # 线条加粗
                   label=method_name, color=colors[i % len(colors)])
            ax.fill(angles, scores_closed, alpha=0.25, color=colors[i % len(colors)])
        
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, fontsize=self.chinese_fontsize, color='black')
        ax.set_ylim(0, 5)
        ax.set_yticks([1, 2, 3, 4, 5])
        ax.set_yticklabels(['1', '2', '3', '4', '5'], 
                          fontsize=self.number_fontsize, color='red', fontweight='bold')
        ax.grid(True, linewidth=1.5)
        ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0), 
                 fontsize=self.legend_fontsize, edgecolor='black', fancybox=False, shadow=False)
        ax.set_title('方法综合评分对比', fontsize=self.chinese_fontsize+2, 
                    fontweight='bold', color='black')
    
    def _plot_mass_balance_comparison(self, ax, validation_results: List[Dict]):
        """绘制质量守恒误差对比"""
        methods = []
        errors = []
        colors = []
        
        for result in validation_results:
            method_name = result.get('method_name', 'Unknown')
            mass_check = result.get('physical_checks', {}).get('mass_conservation', {})
            max_error = mass_check.get('max_relative_error', 0) * 100  # 转换为百分比
            
            methods.append(method_name)
            errors.append(max_error)
            
            # 根据误差大小设置颜色
            if max_error <= 5:
                colors.append(self.colors['pass'])
            elif max_error <= 15:
                colors.append(self.colors['warning'])
            else:
                colors.append(self.colors['fail'])
        
        bars = ax.bar(methods, errors, color=colors, alpha=0.7, 
                     edgecolor='black', linewidth=3.0)  # 边框加粗
        
        # 添加数值标签（红色突出显示）
        for bar, error in zip(bars, errors):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + max(errors) * 0.02,
                   f'{error:.2f}%', ha='center', va='bottom', 
                   fontsize=self.number_fontsize, color='red', fontweight='bold')
        
        ax.set_ylabel('最大相对误差 (%)', fontsize=self.chinese_fontsize, color='black')
        ax.set_title('质量守恒验证', fontsize=self.chinese_fontsize+2, 
                    fontweight='bold', color='black')
        ax.set_ylim(0, max(errors) * 1.2 if errors else 1)
        ax.tick_params(axis='x', labelrotation=45, labelsize=self.chinese_fontsize-2, labelcolor='black')
        ax.tick_params(axis='y', labelsize=self.number_fontsize, labelcolor='red')
        ax.grid(True, alpha=0.3, linewidth=1.0)
        
        # 添加容差线
        tolerance_line = 5.0  # 5%容差
        ax.axhline(y=tolerance_line, color='red', linestyle='--', linewidth=2.0, 
                  label=f'容差线 ({tolerance_line}%)')
        ax.legend(fontsize=self.legend_fontsize, edgecolor='black', fancybox=False, shadow=False)
    
    def _plot_velocity_distribution(self, ax, validation_results: List[Dict]):
        """绘制流速分布对比"""
        methods = []
        velocity_ranges = []
        colors = []
        
        for result in validation_results:
            method_name = result.get('method_name', 'Unknown')
            velocity_check = result.get('physical_checks', {}).get('velocity_characteristics', {})
            velocity_range = velocity_check.get('velocity_range', (0, 0))
            status = velocity_check.get('status', 'UNKNOWN')
            
            methods.append(method_name)
            velocity_ranges.append(velocity_range)
            
            # 根据状态设置颜色
            if status == 'PASS':
                colors.append(self.colors['pass'])
            elif status == 'WARNING':
                colors.append(self.colors['warning'])
            elif status == 'FAIL':
                colors.append(self.colors['fail'])
            else:
                colors.append(self.colors['unknown'])
        
        # 绘制流速范围条形图
        if velocity_ranges:
            mins = [vr[0] for vr in velocity_ranges]
            maxs = [vr[1] for vr in velocity_ranges]
            ranges = [vr[1] - vr[0] for vr in velocity_ranges]
            
            bars = ax.bar(methods, ranges, bottom=mins, 
                         color=colors, alpha=0.7, 
                         edgecolor='black', linewidth=3.0)
            
            # 添加数值标签
            for i, (bar, vr) in enumerate(zip(bars, velocity_ranges)):
                # 最小值标签
                ax.text(bar.get_x() + bar.get_width()/2., vr[0] - 0.1,
                       f'{vr[0]:.2f}', ha='center', va='top', 
                       fontsize=self.number_fontsize, color='red', fontweight='bold')
                # 最大值标签
                ax.text(bar.get_x() + bar.get_width()/2., vr[1] + 0.1,
                       f'{vr[1]:.2f}', ha='center', va='bottom', 
                       fontsize=self.number_fontsize, color='red', fontweight='bold')
        
        ax.set_ylabel('流速 (m/s)', fontsize=self.chinese_fontsize, color='black')
        ax.set_title('流速分布验证', fontsize=self.chinese_fontsize+2, 
                    fontweight='bold', color='black')
        ax.tick_params(axis='x', labelrotation=45, labelsize=self.chinese_fontsize-2, labelcolor='black')
        ax.tick_params(axis='y', labelsize=self.number_fontsize, labelcolor='red')
        ax.grid(True, alpha=0.3, linewidth=1.0)
        
        # 添加合理范围线
        ax.axhline(y=0.1, color='green', linestyle='--', linewidth=2.0, alpha=0.7, label='最小合理流速')
        ax.axhline(y=5.0, color='red', linestyle='--', linewidth=2.0, alpha=0.7, label='最大合理流速')
        ax.legend(fontsize=self.legend_fontsize, edgecolor='black', fancybox=False, shadow=False)
    
    def _plot_froude_number_analysis(self, ax, validation_results: List[Dict]):
        """绘制弗劳德数分析"""
        methods = []
        froude_numbers = []
        
        for result in validation_results:
            method_name = result.get('method_name', 'Unknown')
            velocity_check = result.get('physical_checks', {}).get('velocity_characteristics', {})
            froudes = velocity_check.get('froude_numbers', [])
            
            if froudes:
                methods.append(method_name)
                froude_numbers.append(froudes)
        
        if methods and froude_numbers:
            # 绘制箱线图
            bp = ax.boxplot(froude_numbers, labels=methods, patch_artist=True,
                           boxprops=dict(linewidth=3.0),
                           whiskerprops=dict(linewidth=2.0),
                           capprops=dict(linewidth=2.0))
            
            # 设置颜色
            colors_cycle = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7']
            for patch, color in zip(bp['boxes'], colors_cycle):
                patch.set_facecolor(color)
                patch.set_alpha(0.7)
        
        ax.set_ylabel('弗劳德数', fontsize=self.chinese_fontsize, color='black')
        ax.set_title('弗劳德数分析', fontsize=self.chinese_fontsize+2, 
                    fontweight='bold', color='black')
        ax.tick_params(axis='x', labelrotation=45, labelsize=self.chinese_fontsize-2, labelcolor='black')
        ax.tick_params(axis='y', labelsize=self.number_fontsize, labelcolor='red')
        ax.grid(True, alpha=0.3, linewidth=1.0)
        
        # 添加流态分界线
        ax.axhline(y=1.0, color='red', linestyle='--', linewidth=3.0, 
                  label='临界流 (Fr=1.0)')
        ax.axhline(y=0.5, color='orange', linestyle='--', linewidth=2.0, 
                  label='缓流区界限 (Fr=0.5)')
        ax.legend(fontsize=self.legend_fontsize, edgecolor='black', fancybox=False, shadow=False)
    
    def _plot_assumption_compliance(self, ax, validation_results: List[Dict]):
        """绘制方法假设合规性"""
        methods = []
        compliance_scores = []
        compliance_status = []
        
        for result in validation_results:
            method_name = result.get('method_name', 'Unknown')
            assumption_check = result.get('physical_checks', {}).get('method_assumptions', {})
            score = assumption_check.get('compliance_score', 0) * 100  # 转换为百分比
            status = assumption_check.get('status', 'UNKNOWN')
            
            methods.append(method_name)
            compliance_scores.append(score)
            compliance_status.append(status)
        
        # 设置颜色
        colors = []
        for status in compliance_status:
            if status == 'PASS':
                colors.append(self.colors['pass'])
            elif status == 'WARNING':
                colors.append(self.colors['warning'])
            elif status == 'FAIL':
                colors.append(self.colors['fail'])
            else:
                colors.append(self.colors['unknown'])
        
        bars = ax.bar(methods, compliance_scores, color=colors, alpha=0.7,
                     edgecolor='black', linewidth=3.0)
        
        # 添加数值标签
        for bar, score in zip(bars, compliance_scores):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 2,
                   f'{score:.1f}%', ha='center', va='bottom', 
                   fontsize=self.number_fontsize, color='red', fontweight='bold')
        
        ax.set_ylabel('合规性评分 (%)', fontsize=self.chinese_fontsize, color='black')
        ax.set_title('方法假设合规性', fontsize=self.chinese_fontsize+2, 
                    fontweight='bold', color='black')
        ax.set_ylim(0, 105)
        ax.tick_params(axis='x', labelrotation=45, labelsize=self.chinese_fontsize-2, labelcolor='black')
        ax.tick_params(axis='y', labelsize=self.number_fontsize, labelcolor='red')
        ax.grid(True, alpha=0.3, linewidth=1.0)
        
        # 添加合格线
        ax.axhline(y=70, color='orange', linestyle='--', linewidth=2.0, 
                  label='及格线 (70%)')
        ax.axhline(y=90, color='green', linestyle='--', linewidth=2.0, 
                  label='优秀线 (90%)')
        ax.legend(fontsize=self.legend_fontsize, edgecolor='black', fancybox=False, shadow=False)
    
    def _plot_water_level_validation(self, ax, validation_results: List[Dict]):
        """绘制水位分布合理性"""
        methods = []
        slopes = []
        negative_depths = []
        
        for result in validation_results:
            method_name = result.get('method_name', 'Unknown')
            water_level_check = result.get('physical_checks', {}).get('water_level_distribution', {})
            slope = water_level_check.get('water_surface_slope', 0)
            neg_depth_count = water_level_check.get('negative_depth_count', 0)
            
            methods.append(method_name)
            slopes.append(abs(slope) * 1000)  # 转换为千分比
            negative_depths.append(neg_depth_count)
        
        # 双轴图：水面坡度和负水深数量
        ax2 = ax.twinx()
        
        # 水面坡度条形图
        bars1 = ax.bar([x - 0.2 for x in range(len(methods))], slopes, 
                       width=0.4, color=self.colors['pass'], alpha=0.7,
                       edgecolor='black', linewidth=2.0, label='水面坡度')
        
        # 负水深数量条形图
        bars2 = ax2.bar([x + 0.2 for x in range(len(methods))], negative_depths, 
                        width=0.4, color=self.colors['fail'], alpha=0.7,
                        edgecolor='black', linewidth=2.0, label='负水深数量')
        
        # 添加数值标签
        for bar, slope in zip(bars1, slopes):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                   f'{slope:.3f}‰', ha='center', va='bottom', 
                   fontsize=self.number_fontsize, color='red', fontweight='bold')
        
        for bar, neg_depth in zip(bars2, negative_depths):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                    f'{neg_depth}', ha='center', va='bottom', 
                    fontsize=self.number_fontsize, color='red', fontweight='bold')
        
        ax.set_xlabel('方法', fontsize=self.chinese_fontsize, color='black')
        ax.set_ylabel('水面坡度 (‰)', fontsize=self.chinese_fontsize, color='black')
        ax2.set_ylabel('负水深数量', fontsize=self.chinese_fontsize, color='black')
        ax.set_title('水位分布合理性', fontsize=self.chinese_fontsize+2, 
                    fontweight='bold', color='black')
        
        ax.set_xticks(range(len(methods)))
        ax.set_xticklabels(methods, rotation=45, fontsize=self.chinese_fontsize-2, color='black')
        ax.tick_params(axis='y', labelsize=self.number_fontsize, labelcolor='red')
        ax2.tick_params(axis='y', labelsize=self.number_fontsize, labelcolor='red')
        
        # 添加图例
        ax.legend(loc='upper left', fontsize=self.legend_fontsize, 
                 edgecolor='black', fancybox=False, shadow=False)
        ax2.legend(loc='upper right', fontsize=self.legend_fontsize, 
                  edgecolor='black', fancybox=False, shadow=False)
    
    def _plot_energy_conservation(self, ax, validation_results: List[Dict]):
        """绘制能量守恒检查"""
        methods = []
        energy_status = []
        
        for result in validation_results:
            method_name = result.get('method_name', 'Unknown')
            energy_check = result.get('physical_checks', {}).get('energy_conservation', {})
            status = energy_check.get('status', 'UNKNOWN')
            
            methods.append(method_name)
            energy_status.append(status)
        
        # 统计各状态数量
        status_counts = {}
        for status in ['PASS', 'WARNING', 'FAIL', 'ERROR', 'UNKNOWN']:
            status_counts[status] = energy_status.count(status)
        
        # 绘制饼图
        if any(count > 0 for count in status_counts.values()):
            labels = []
            sizes = []
            colors = []
            
            for status, count in status_counts.items():
                if count > 0:
                    labels.append(f'{status}\n({count}个)')
                    sizes.append(count)
                    colors.append(self.colors.get(status.lower(), self.colors['unknown']))
            
            wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors, 
                                             autopct='%1.1f%%', startangle=90,
                                             wedgeprops=dict(linewidth=3.0, edgecolor='black'))
            
            # 设置文字格式
            for text in texts:
                text.set_fontsize(self.chinese_fontsize-2)
                text.set_color('black')
            for autotext in autotexts:
                autotext.set_fontsize(self.number_fontsize)
                autotext.set_color('red')
                autotext.set_weight('bold')
        
        ax.set_title('能量守恒检查', fontsize=self.chinese_fontsize+2, 
                    fontweight='bold', color='black')
    
    def _plot_validation_summary_table(self, ax, validation_results: List[Dict]):
        """绘制验证状态汇总表格"""
        # 准备表格数据
        table_data = []
        headers = ['方法名称', '质量守恒', '水位分布', '流速特性', '能量守恒', '方法假设', '综合评价']
        
        for result in validation_results:
            method_name = result.get('method_name', 'Unknown')
            checks = result.get('physical_checks', {})
            overall = result.get('overall_validity', 'UNKNOWN')
            
            row = [method_name]
            
            # 各项检查状态
            for check_key in ['mass_conservation', 'water_level_distribution', 
                            'velocity_characteristics', 'energy_conservation', 'method_assumptions']:
                check = checks.get(check_key, {})
                status = check.get('status', 'UNKNOWN')
                
                # 状态映射为符号
                status_symbols = {
                    'PASS': '✅',
                    'WARNING': '⚠️', 
                    'FAIL': '❌',
                    'ERROR': '🔥',
                    'UNKNOWN': '❓'
                }
                row.append(status_symbols.get(status, '❓'))
            
            # 综合评价映射
            overall_symbols = {
                'VALID': '✅优秀',
                'ACCEPTABLE_WITH_WARNINGS': '⚠️合格',
                'QUESTIONABLE': '❌可疑',
                'INVALID': '🔥无效',
                'UNKNOWN': '❓未知'
            }
            row.append(overall_symbols.get(overall, '❓'))
            
            table_data.append(row)
        
        # 绘制表格
        ax.axis('tight')
        ax.axis('off')
        
        table = ax.table(cellText=table_data, colLabels=headers,
                        cellLoc='center', loc='center',
                        colWidths=[0.18] * len(headers))
        
        # 设置表格样式（遵循用户规范）
        table.auto_set_font_size(False)
        table.set_fontsize(self.chinese_fontsize-2)
        table.scale(1.2, 2.5)
        
        # 设置标题行样式
        for i in range(len(headers)):
            cell = table[0, i]
            cell.set_facecolor('#4ECDC4')
            cell.set_text_props(weight='bold', color='black', fontsize=self.chinese_fontsize)
            cell.set_edgecolor('black')
            cell.set_linewidth(3.0)  # 边框加粗符合用户规范
        
        # 设置数据行样式
        for i in range(1, len(table_data) + 1):
            for j in range(len(headers)):
                cell = table[i, j]
                if j == 0:  # 方法名称列
                    cell.set_text_props(color='black', fontsize=self.chinese_fontsize-1)
                else:  # 其他列
                    cell.set_text_props(fontsize=self.number_fontsize)
                cell.set_edgecolor('black')
                cell.set_linewidth(3.0)  # 边框加粗符合用户规范
        
        ax.set_title('验证状态汇总表', fontsize=self.chinese_fontsize+2, 
                    fontweight='bold', color='black', pad=20)


def generate_validation_report(validation_results: List[Dict], 
                             output_dir: str = "outputs/validation") -> str:
    """
    生成物理合理性验证报告
    
    Args:
        validation_results: 验证结果列表
        output_dir: 输出目录
        
    Returns:
        生成的报告文件路径
    """
    # 创建输出目录
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # 生成可视化报告
    visualizer = ValidationVisualizer()
    output_path = Path(output_dir) / f"物理合理性验证报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.svg"
    
    report_path = visualizer.generate_comprehensive_validation_report(
        validation_results, str(output_path)
    )
    
    return report_path


if __name__ == "__main__":
    print("🎨 物理合理性验证可视化器已初始化")
    print("支持的可视化功能：")
    print("  • 方法对比雷达图")
    print("  • 质量守恒误差对比")
    print("  • 流速分布验证")
    print("  • 弗劳德数分析")
    print("  • 方法假设合规性")
    print("  • 水位分布合理性")
    print("  • 能量守恒检查")
    print("  • 验证状态汇总表")