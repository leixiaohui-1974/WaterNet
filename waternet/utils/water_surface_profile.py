#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
水面线绘制工具 - WaterNet核心库

提供通用的水面线计算和绘制功能，支持多工况对比分析。

核心功能：
1. 多工况水面线计算
2. 专业可视化图表生成
3. 水力学性质分析
4. 报告生成

Author: WaterNet Development Team
Date: 2025-01-05
"""

import time
import math
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
import matplotlib
matplotlib.use('Agg')  # 设置非交互式后端
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.patches import Rectangle
import numpy as np
from .channel_geometry import ChannelGeometry, HeadLossCalculator


class WaterSurfaceProfileAnalyzer:
    """水面线分析器核心类"""
    
    def __init__(self, output_dir: str = "outputs/water_surface_profiles"):
        """
        初始化水面线分析器
        
        Args:
            output_dir: 输出目录路径
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.profile_results = []
    
    def _calculate_critical_depth(self, flow: float, bottom_width: float, side_slope: float) -> float:
        """
        计算临界水深（用于自然出流边界条件）
        
        基于弗劳德数 Fr = 1 的条件计算临界水深
        对于梯形断面：Fr = V/sqrt(g*D) = Q/(A*sqrt(g*A/T)) = 1
        
        物理意义：临界水深是明渠中能量最小、流速等于重力波传播速度的特殊状态
        常用于自由出流、跌水、堰等边界条件
        
        Args:
            flow: 流量 (m3/s)
            bottom_width: 底宽 (m)
            side_slope: 边坡系数
            
        Returns:
            float: 临界水深 (m)
        """
        try:
            # 使用迭代法求解临界水深
            # 对于梯形断面：A = h*(b + m*h), T = b + 2*m*h
            # Fr = Q/(A*sqrt(g*A/T)) = 1
            
            h_c = (flow**2 / (9.81 * bottom_width**2))**(1/3)  # 矩形断面初值
            
            # 迭代求解梯形断面临界水深
            for _ in range(10):
                A = h_c * (bottom_width + side_slope * h_c)
                T = bottom_width + 2 * side_slope * h_c
                
                if A > 0 and T > 0:
                    # 新的临界水深估值
                    Fr_squared = (flow / A)**2 / (9.81 * A / T)
                    
                    if abs(Fr_squared - 1.0) < 0.001:
                        break
                    
                    # 调整水深
                    if Fr_squared > 1.0:
                        h_c *= 1.05
                    else:
                        h_c *= 0.95
                else:
                    break
            
            return max(0.1, h_c)  # 确保最小值
            
        except Exception as e:
            # 如果计算失败，返回经验值
            return max(0.5, (flow / bottom_width)**0.4)

    def compute_profile_with_boundary(self, flow: float, channel_config: Dict[str, Any], 
                                     downstream_level: Optional[float] = None) -> Dict[str, Any]:
        """
        水面线计算方法（支持指定下游水位边界条件）
        
        基于曼宁公式和逐步推算法
        
        Args:
            flow: 流量 (m³/s)
            channel_config: 渠道配置
            downstream_level: 下游水位 (m)，如为None则使用改进的自动边界条件
            
        Returns:
            Dict: 水面线数据
        """
        length = channel_config['length']
        n_sections = channel_config.get('sections', 11)
        geometry = channel_config['geometry']
        profile = channel_config['profile']
        
        bottom_width = geometry['bottom_width']
        side_slope = geometry['side_slope']
        roughness = geometry['roughness']
        
        upstream_elevation = profile['upstream_elevation']
        downstream_elevation = profile['downstream_elevation']
        bottom_slope = (upstream_elevation - downstream_elevation) / length
        
        # 计算正常水深和临界水深
        normal_depth = ChannelGeometry.solve_normal_depth(
            flow, bottom_width, side_slope, bottom_slope, roughness)
        
        # 改进的下游边界条件设置
        if downstream_level is not None:
            downstream_H = downstream_level  # 用户指定的下游水位
        else:
            # 自动边界条件：自然出流边界（无闸门控制）
            # 根据明渠水力学原理，选择合理的下游边界条件
            critical_depth = self._calculate_critical_depth(flow, bottom_width, side_slope)
            
            # 比较正常水深和临界水深，选择物理上合理的边界
            if normal_depth > critical_depth:
                # 缓流：下游边界采用临界水深（自由出流或跌水）
                downstream_H = downstream_elevation + critical_depth
            else:
                # 急流：下游边界采用正常水深（长渠道自然流动）
                downstream_H = downstream_elevation + normal_depth
            
            # 微调：考虑出口损失，略微降低下游水位
            # 模拟自然出流的水头损失（约0.1-0.2倍流速水头）
            area = critical_depth * (bottom_width + side_slope * critical_depth)
            velocity = flow / area if area > 0 else 0
            velocity_head = velocity * velocity / (2 * 9.81)
            exit_loss = 0.15 * velocity_head  # 出口损失系数约0.15
            
            downstream_H = downstream_H - exit_loss

        # 逐步推算水面线
        distances = []
        water_levels = []
        bottom_elevations = []
        depths = []
        velocities = []
        froude_numbers = []
        
        dx = length / (n_sections - 1)  # 距离步长
        current_H = downstream_H
        
        for i in range(n_sections):
            # 当前位置（从下游向上游）
            x = i * dx
            ratio = x / length
            elevation = downstream_elevation + ratio * (upstream_elevation - downstream_elevation)
            
            distances.append(x)
            water_levels.append(current_H)
            bottom_elevations.append(elevation)
            
            # 计算水深和流速
            depth = current_H - elevation
            depths.append(depth)
            
            if depth > 0:
                area = bottom_width * depth + side_slope * depth * depth
                velocity = flow / area if area > 0 else 0
                velocities.append(velocity)
                
                # 计算弗劳德数
                froude = velocity / math.sqrt(9.81 * depth) if depth > 0 else 0
                froude_numbers.append(froude)
                
                # 计算下一断面水位（向上游推算）
                if i < n_sections - 1:
                    # 计算摩阻坡度
                    wetted_perimeter = bottom_width + 2 * depth * math.sqrt(1 + side_slope * side_slope)
                    hydraulic_radius = area / wetted_perimeter if wetted_perimeter > 0 else 0
                    
                    friction_slope = (roughness * velocity) ** 2 / (hydraulic_radius ** (4/3)) if hydraulic_radius > 0 else 0.001
                    
                    # 水面坡度 = 底坡 - 摩阻坡度（逐渐变水流）
                    water_surface_slope = bottom_slope - friction_slope
                    
                    # 计算上游断面水位
                    current_H = current_H + water_surface_slope * dx
            else:
                velocities.append(0)
                froude_numbers.append(0)
                current_H = elevation + normal_depth  # 如果出现负水深，重置为正常深度
        
        return {
            'distances': distances,
            'water_levels': water_levels,
            'bottom_elevations': bottom_elevations,
            'depths': depths,
            'velocities': velocities,
            'froude_numbers': froude_numbers,
            'normal_depth': normal_depth,
            'downstream_boundary': downstream_H,
            'method': 'flow_and_level_calculation'
        }
        """
        简化水面线计算方法
        
        基于曼宁公式和逐步推算法
        
        Args:
            flow: 流量 (m³/s)
            channel_config: 渠道配置
            
        Returns:
            Dict: 水面线数据
        """
        length = channel_config['length']
        n_sections = channel_config.get('sections', 11)
        geometry = channel_config['geometry']
        profile = channel_config['profile']
        
        bottom_width = geometry['bottom_width']
        side_slope = geometry['side_slope']
        roughness = geometry['roughness']
        
        upstream_elevation = profile['upstream_elevation']
        downstream_elevation = profile['downstream_elevation']
        bottom_slope = (upstream_elevation - downstream_elevation) / length
        
        # 计算正常水深
        normal_depth = ChannelGeometry.solve_normal_depth(
            flow, bottom_width, side_slope, bottom_slope, roughness)
        
        # 下游边界条件
        downstream_H = downstream_elevation + normal_depth * 1.1  # 稍微高于正常水深
        
        # 逐步推算水面线
        distances = []
        water_levels = []
        bottom_elevations = []
        depths = []
        velocities = []
        
        dx = length / (n_sections - 1)  # 距离步长
        current_H = downstream_H
        
        for i in range(n_sections):
            # 当前位置（从下游向上游）
            x = i * dx
            ratio = x / length
            elevation = downstream_elevation + ratio * (upstream_elevation - downstream_elevation)
            
            distances.append(x)
            water_levels.append(current_H)
            bottom_elevations.append(elevation)
            
            # 计算水深和流速
            depth = current_H - elevation
            depths.append(depth)
            
            if depth > 0:
                area = bottom_width * depth + side_slope * depth * depth
                velocity = flow / area if area > 0 else 0
                velocities.append(velocity)
                
                # 计算下一断面水位（向上游推算）
                if i < n_sections - 1:
                    # 计算摩阻坡度
                    wetted_perimeter = bottom_width + 2 * depth * math.sqrt(1 + side_slope * side_slope)
                    hydraulic_radius = area / wetted_perimeter if wetted_perimeter > 0 else 0
                    
                    friction_slope = (roughness * velocity) ** 2 / (hydraulic_radius ** (4/3)) if hydraulic_radius > 0 else 0.001
                    
                    # 水面坡度 = 底坡 - 摩阻坡度（逐渐变水流）
                    water_surface_slope = bottom_slope - friction_slope
                    
                    # 计算上游断面水位
                    current_H = current_H + water_surface_slope * dx
            else:
                velocities.append(0)
                current_H = elevation + normal_depth  # 如果出现负水深，重置为正常深度
        
        return {
            'distances': distances,
            'water_levels': water_levels,
            'bottom_elevations': bottom_elevations,
            'depths': depths,
            'velocities': velocities,
            'normal_depth': normal_depth,
            'method': 'simplified_calculation'
        }
    
    def compute_multiple_flow_profiles(self, flow_conditions: List[float], 
                                     channel_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        计算多个流量工况的水面线（增强版：同时生成横断面图）
        
        Args:
            flow_conditions: 流量工况列表 (m³/s)
            channel_config: 渤0道配置
            
        Returns:
            List[Dict]: 各工况的水面线结果（包含横断面图路径）
        """
        self.profile_results = []
        
        for i, flow in enumerate(flow_conditions):
            # 计算单个工况的水面线
            profile_data = self.compute_profile_with_boundary(flow, channel_config)
            
            if profile_data:
                # 分析水力学性质
                hydraulic_analysis = HeadLossCalculator.analyze_hydraulic_properties(
                    profile_data['distances'],
                    profile_data['water_levels'],
                    profile_data['bottom_elevations'],
                    profile_data['velocities'],
                    flow
                )
                
                # 生成横断面图（新增功能）
                cross_section_plot_path = ""
                try:
                    cross_section_plot_path = self.plot_cross_sections_combined(
                        profile_data, channel_config, flow
                    )
                    if cross_section_plot_path:
                        print(f"✓ 横断面图生成成功: {cross_section_plot_path}")
                except Exception as e:
                    print(f"⚠️ 横断面图生成失败: {e}")
                
                result = {
                    'case_name': f"工况{i+1}",
                    'flow': flow,
                    'profile_data': profile_data,
                    'hydraulic_analysis': hydraulic_analysis,
                    'cross_section_plot': cross_section_plot_path,  # 新增横断面图路径
                    'computation_time': time.time()
                }
                
                self.profile_results.append(result)
        
        return self.profile_results
    
    def compute_flow_and_level_profiles(self, scenario_conditions: List[Dict[str, Any]], 
                                       channel_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        计算多个流量和水位工况的水面线
        
        Args:
            scenario_conditions: 工况条件列表，每个工况包含:
                {
                    'flow': 流量 (m³/s),
                    'downstream_level': 下游水位 (m) 或 None,
                    'name': '工况名称'
                }
            channel_config: 渠道配置
            
        Returns:
            List[Dict]: 各工况的水面线结果
        """
        self.profile_results = []
        
        for i, condition in enumerate(scenario_conditions):
            flow = condition['flow']
            downstream_level = condition.get('downstream_level', None)
            case_name = condition.get('name', f"工况{i+1}")
            
            # 计算单个工况的水面线
            profile_data = self.compute_profile_with_boundary(flow, channel_config, downstream_level)
            
            if profile_data:
                # 分析水力学性质
                hydraulic_analysis = HeadLossCalculator.analyze_hydraulic_properties(
                    profile_data['distances'],
                    profile_data['water_levels'],
                    profile_data['bottom_elevations'],
                    profile_data['velocities'],
                    flow
                )
                
                # 添加弗劳德数分析
                if 'froude_numbers' in profile_data:
                    hydraulic_analysis['froude_numbers'] = profile_data['froude_numbers']
                    hydraulic_analysis['max_froude'] = max(profile_data['froude_numbers'])
                    hydraulic_analysis['min_froude'] = min(profile_data['froude_numbers'])
                    hydraulic_analysis['avg_froude'] = sum(profile_data['froude_numbers']) / len(profile_data['froude_numbers'])
                
                result = {
                    'case_name': case_name,
                    'flow': flow,
                    'downstream_level': downstream_level,
                    'profile_data': profile_data,
                    'hydraulic_analysis': hydraulic_analysis,
                    'computation_time': time.time()
                }
                
                self.profile_results.append(result)
        
        return self.profile_results
    
    def compute_profile_with_boundary(self, flow: float, channel_config: Dict[str, Any], 
                                     downstream_level: Optional[float] = None) -> Dict[str, Any]:
        """
        水面线计算方法（支持指定下游水位边界条件）
        
        基于曼宁公式和逐步推算法
        
        Args:
            flow: 流量 (m³/s)
            channel_config: 渠道配置
            downstream_level: 下游水位 (m)，如为None则使用正常水深计算
            
        Returns:
            Dict: 水面线数据
        """
        length = channel_config['length']
        n_sections = channel_config.get('sections', 11)
        geometry = channel_config['geometry']
        profile = channel_config['profile']
        
        bottom_width = geometry['bottom_width']
        side_slope = geometry['side_slope']
        roughness = geometry['roughness']
        
        upstream_elevation = profile['upstream_elevation']
        downstream_elevation = profile['downstream_elevation']
        bottom_slope = (upstream_elevation - downstream_elevation) / length
        
        # 计算正常水深
        normal_depth = ChannelGeometry.solve_normal_depth(
            flow, bottom_width, side_slope, bottom_slope, roughness)
        
        # 下游边界条件：用户指定或自动计算
        if downstream_level is not None:
            downstream_H = downstream_level  # 用户指定的下游水位
        else:
            downstream_H = downstream_elevation + normal_depth * 1.1  # 稍微高于正常水深
        
        # 逐步推算水面线
        distances = []
        water_levels = []
        bottom_elevations = []
        depths = []
        velocities = []
        froude_numbers = []
        
        dx = length / (n_sections - 1)  # 距离步长
        current_H = downstream_H
        
        for i in range(n_sections):
            # 当前位置（从下游向上游）
            x = i * dx
            ratio = x / length
            elevation = downstream_elevation + ratio * (upstream_elevation - downstream_elevation)
            
            distances.append(x)
            water_levels.append(current_H)
            bottom_elevations.append(elevation)
            
            # 计算水深和流速
            depth = current_H - elevation
            depths.append(depth)
            
            if depth > 0:
                area = bottom_width * depth + side_slope * depth * depth
                velocity = flow / area if area > 0 else 0
                velocities.append(velocity)
                
                # 计算弗劳德数
                froude = velocity / math.sqrt(9.81 * depth) if depth > 0 else 0
                froude_numbers.append(froude)
                
                # 计算下一断面水位（向上游推算）
                if i < n_sections - 1:
                    # 计算摩阻坡度
                    wetted_perimeter = bottom_width + 2 * depth * math.sqrt(1 + side_slope * side_slope)
                    hydraulic_radius = area / wetted_perimeter if wetted_perimeter > 0 else 0
                    
                    friction_slope = (roughness * velocity) ** 2 / (hydraulic_radius ** (4/3)) if hydraulic_radius > 0 else 0.001
                    
                    # 水面坡度 = 底坡 - 摩阻坡度（逐渐变水流）
                    water_surface_slope = bottom_slope - friction_slope
                    
                    # 计算上游断面水位
                    current_H = current_H + water_surface_slope * dx
            else:
                velocities.append(0)
                froude_numbers.append(0)
                current_H = elevation + normal_depth  # 如果出现负水深，重置为正常深度
        
        return {
            'distances': distances,
            'water_levels': water_levels,
            'bottom_elevations': bottom_elevations,
            'depths': depths,
            'velocities': velocities,
            'froude_numbers': froude_numbers,
            'normal_depth': normal_depth,
            'downstream_boundary': downstream_H,
            'method': 'flow_and_level_calculation'
        }
    
    def generate_analysis_report(self, channel_name: str = "标准渠道", 
                               channel_length: float = 1000.0, 
                               plot_filename: str = "") -> str:
        """
        生成分析报告（包含图片引用）
        
        Args:
            channel_name: 渠道名称
            channel_length: 渠道长度
            plot_filename: 图片文件名
            
        Returns:
            str: 报告文件路径
        """
        if not self.profile_results:
            return "无计算结果"
        
        report_lines = [
            "# 渠道水面线分析报告",
            f"\n生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"渠道配置: {channel_name}",
            f"渠道长度: {channel_length:.0f}m",
            f"计算工况数量: {len(self.profile_results)}个"
        ]
        
        # 添加水面线纵剖面图（根据用户记忆要求）
        if plot_filename:
            # 实际生成水面线对比图
            try:
                actual_plot_path = self.plot_multi_scenario_comparison(plot_filename)
                if actual_plot_path:
                    print(f"✓ 水面线对比图生成成功: {actual_plot_path}")
                    # 验证文件是否存在
                    import os
                    if os.path.exists(actual_plot_path):
                        file_size = os.path.getsize(actual_plot_path)
                        print(f"✓ 文件确实存在，大小: {file_size} bytes")
                    else:
                        print(f"⚠️ 文件路径不存在: {actual_plot_path}")
                else:
                    print("⚠️ 水面线对比图生成失败")
            except Exception as e:
                print(f"⚠️ 水面线绘图错误: {e}")
            
            report_lines.extend([
                "\n## 水面线纵剖面对比图 📊",
                f"\n**恒定流水面线可视化结果**：",
                f"\n![水面线纵剖面对比图]({plot_filename})",
                "\n*图表说明：*",
                "- 左上图：各工况水面线纵剖面对比，包含渠底高程线",
                "- 右上图：流速分布对比分析",
                "- 左下图：弗劳德数分布对比分析",
                "- 右下图：水深分布对比分析",
                "- 水位数字标注：红色数字显示关键断面水位（单位：m）",
                "- 流态分析：Fr<1为亚临界流，Fr≥1为临界或超临界流"
            ])
        
        report_lines.extend([
            "\n## 各工况结果汇总",
            "\n| 工况 | 流量(m3/s) | 最大水深(m) | 最大流速(m/s) | 最大Fr数 | 水头损失(m) | 流态 |",
            "| --- | --- | --- | --- | --- | --- | --- |"
        ])
        
        # 工况数据表格
        for result in self.profile_results:
            case_name = result['case_name']
            flow = result['flow']
            hydraulic = result['hydraulic_analysis']
            
            max_depth = hydraulic.get('max_depth', 0)
            max_velocity = hydraulic.get('max_velocity', 0)
            max_froude = hydraulic.get('max_froude', 0)
            head_loss = hydraulic.get('total_head_loss', 0)
            flow_regime = hydraulic.get('flow_regime', 'unknown')
            
            report_lines.append(
                f"| {case_name} | {flow:.1f} | {max_depth:.2f} | {max_velocity:.2f} | "
                f"{max_froude:.3f} | {head_loss:.2f} | {flow_regime} |"
            )
        
        # 添加详细水力学分析
        report_lines.extend([
            "\n## 水力学特性分析",
            "\n### 流态特征"
        ])
        
        # 流态分析
        subcritical_count = sum(1 for r in self.profile_results 
                               if r['hydraulic_analysis'].get('flow_regime') == 'subcritical')
        if subcritical_count == len(self.profile_results):
            report_lines.append("✅ **全部工况均为亚临界流**：流动稳定，水面平缓")
        else:
            report_lines.append("⚠️ **存在临界或超临界流工况**：需注意流态转换")
        
        # 参数敏感性分析
        if len(self.profile_results) > 1:
            flows = [r['flow'] for r in self.profile_results]
            head_losses = [r['hydraulic_analysis'].get('total_head_loss', 0) for r in self.profile_results]
            
            flow_range = max(flows) - min(flows)
            loss_range = max(head_losses) - min(head_losses)
            
            if flow_range > 0:
                sensitivity = loss_range / flow_range  # m/(m³/s)
                report_lines.extend([
                    "\n### 参数敏感性",
                    f"- 流量变化范围: {min(flows):.1f} - {max(flows):.1f} m3/s",
                    f"- 水头损失变化范围: {min(head_losses):.2f} - {max(head_losses):.2f} m",
                    f"- 敏感性系数: {sensitivity:.3f} m/(m3/s)",
                    f"- **结论**: 流量每增加1 m3/s，水头损失约增加{sensitivity:.3f} m"
                ])
        
        # 工程建议
        max_flow_result = max(self.profile_results, key=lambda x: x['flow'])
        max_froude = max_flow_result['hydraulic_analysis'].get('max_froude', 0)
        
        report_lines.extend([
            "\n## 工程建议",
            "\n### 设计参考"
        ])
        
        if max_froude < 0.5:
            report_lines.append("✅ **推荐设计流量**: 当前最大流量工况下流态良好，可作为设计流量")
        elif max_froude < 0.8:
            report_lines.append("⚠️ **注意设计流量**: 接近临界流态，建议适当降低设计流量")
        else:
            report_lines.append("❌ **超出推荐范围**: 弗劳德数过高，强烈建议降低设计流量")
        
        # 添加计算方法说明
        report_lines.extend([
            "\n### 计算方法",
            "- **水面线计算**: 基于曼宁公式和逐步推算法",
            "- **弗劳德数**: Fr = V/√(gD)，其中V为流速，D为水深",
            "- **流态判断**: Fr<1亚临界流，Fr=1临界流，Fr>1超临界流"
        ])
        
        # 保存报告
        report_path = self.output_dir / 'analysis_report.md'
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))
        
        return str(report_path)
    
    def plot_single_profile(self, profile_data: Dict[str, Any], flow: float, 
                           channel_name: str = "渠道", save_path: Optional[str] = None) -> str:
        """
        绘制单工况水面线图（符合用户记忆规范）
        
        Args:
            profile_data: 水面线数据
            flow: 流量 (m³/s)
            channel_name: 渠道名称
            save_path: 保存路径
            
        Returns:
            str: 图片文件路径
        """
        try:
            # 设置中文字体（默认使用系统字体）
            plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False
            
            # 提取数据（修正方向：左边上游，右边下游）
            distances = np.array(profile_data['distances']) / 1000  # 转换为km
            # 反转距离，使左边为上游（0km），右边为下游
            distances = distances[::-1]
            distances = distances.max() - distances  # 重新计算距离，上游为0
            
            water_levels = np.array(profile_data['water_levels'])[::-1]  # 同步反转
            bottom_elevations = np.array(profile_data['bottom_elevations'])[::-1]
            velocities = np.array(profile_data['velocities'])[::-1]
            froude_numbers = np.array(profile_data.get('froude_numbers', [0] * len(distances)))[::-1]
            
            # 创建图形（符合水面线对比图标准化输出要求）
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
            fig.suptitle(f'{channel_name} 水面线纵剖面图 (Q={flow:.1f}m3/s)', 
                        fontsize=18, fontweight='bold', color='black')  # 汉字黑色显示，m3替代m³
            
            # 图1: 水位和底高程综合图
            ax1.plot(distances, water_levels, 'b-', linewidth=3.0, label='水面线', color='#1f77b4')
            ax1.plot(distances, bottom_elevations, 'k-', linewidth=3.0, label='渠底线', color='#8B4513')
            ax1.fill_between(distances, bottom_elevations, water_levels, alpha=0.3, color='lightblue', label='水体')
            
            # 水位数字显示（符合规范：红色数字，偏移显示）
            for i in range(0, len(distances), max(1, len(distances)//5)):  # 显示5个关键点
                # 数字置于节点下方，偏移距离 = 节点半径 + 0.5 单位
                ax1.annotate(f'{water_levels[i]:.1f}m', 
                           xy=(distances[i], water_levels[i]), 
                           xytext=(distances[i], water_levels[i] - 0.8),  # 下方偏移0.8m
                           fontsize=14, color='red', fontweight='bold',  # 红色突出显示数字
                           ha='center', va='top',
                           bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
            
            ax1.set_xlabel('距离 (km) - 左：上游，右：下游', fontsize=14, color='black')  # 明确标注方向
            ax1.set_ylabel('高程 (m)', fontsize=14, color='black')
            ax1.set_title('水位和底高程分布', fontsize=16, color='black')  # 汉字黑色
            ax1.legend(fontsize=12, loc='upper right')  # 图例字体放大2倍
            ax1.grid(True, alpha=0.3)
            
            # 图2: 流速分布
            ax2.plot(distances, velocities, 'g-', linewidth=3.0, color='#2ca02c')
            ax2.fill_between(distances, 0, velocities, alpha=0.3, color='lightgreen')
            ax2.set_xlabel('距离 (km) - 左：上游，右：下游', fontsize=14, color='black')
            ax2.set_ylabel('流速 (m/s)', fontsize=14, color='black')
            ax2.set_title('流速分布', fontsize=16, color='black')
            ax2.grid(True, alpha=0.3)
            
            # 流速数字标注（红色数字）
            for i in range(0, len(distances), max(1, len(distances)//3)):
                ax2.annotate(f'{velocities[i]:.2f}', 
                           xy=(distances[i], velocities[i]), 
                           xytext=(distances[i], velocities[i] + max(velocities)*0.1),
                           fontsize=12, color='red', fontweight='bold',
                           ha='center', va='bottom',
                           bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.8))
            
            # 图3: 弗劳德数分布
            colors = ['green' if fr < 1.0 else 'orange' if fr < 1.2 else 'red' for fr in froude_numbers]
            ax3.scatter(distances, froude_numbers, c=colors, s=60, alpha=0.8)
            ax3.plot(distances, froude_numbers, 'r--', linewidth=2.0, alpha=0.6)
            ax3.axhline(y=1.0, color='red', linestyle='--', linewidth=2.0, alpha=0.7, label='Fr=1(临界流)')
            ax3.set_xlabel('距离 (km) - 左：上游，右：下游', fontsize=14, color='black')
            ax3.set_ylabel('弗劳德数 Fr', fontsize=14, color='black')
            ax3.set_title('弗劳德数分布', fontsize=16, color='black')
            ax3.legend(fontsize=12)
            ax3.grid(True, alpha=0.3)
            
            # Fr数数字标注（红色数字）
            for i in range(0, len(distances), max(1, len(distances)//3)):
                ax3.annotate(f'{froude_numbers[i]:.3f}', 
                           xy=(distances[i], froude_numbers[i]), 
                           xytext=(distances[i], froude_numbers[i] + max(froude_numbers)*0.1),
                           fontsize=12, color='red', fontweight='bold',
                           ha='center', va='bottom',
                           bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.8))
            
            # 图4: 水深分布
            depths = water_levels - bottom_elevations
            ax4.fill_between(distances, 0, depths, alpha=0.4, color='lightblue')
            ax4.plot(distances, depths, 'b-', linewidth=3.0)
            ax4.set_xlabel('距离 (km) - 左：上游，右：下游', fontsize=14, color='black')
            ax4.set_ylabel('水深 (m)', fontsize=14, color='black')
            ax4.set_title('水深分布', fontsize=16, color='black')
            ax4.grid(True, alpha=0.3)
            
            # 调整布局以避免重叠
            plt.tight_layout(rect=[0, 0.03, 1, 0.95])
            
            # 保存图片
            if save_path is None:
                save_path = self.output_dir / f'single_profile_Q{flow:.0f}.svg'
            
            plt.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
            plt.close()
            
            return str(save_path)
            
        except Exception as e:
            print(f"绘制单工况水面线图失败: {e}")
            return ""
    
    def plot_cross_sections_combined(self, profile_data: Dict[str, Any], 
                                    channel_config: Dict[str, Any],
                                    flow: float,
                                    save_path: Optional[str] = None) -> str:
        """
        绘制所有断面的横断面图（统一在一张图上）
        
        根据断面数量自动优化绘制方法：
        - 断面数量 <= 10: 每个断面单独展示
        - 断面数量 > 10: 按区间分组或显示关键断面
        
        Args:
            profile_data: 水面线数据
            channel_config: 渠道配置
            flow: 流量 (m³/s)
            save_path: 保存路径
            
        Returns:
            str: 图片文件路径
        """
        try:
            # 获取渠道几何参数
            geometry = channel_config['geometry']
            bottom_width = geometry['bottom_width']
            side_slope = geometry['side_slope']
            
            # 获取断面数据
            distances = np.array(profile_data['distances'])
            water_levels = np.array(profile_data['water_levels'])
            bottom_elevations = np.array(profile_data['bottom_elevations'])
            depths = water_levels - bottom_elevations
            n_sections = len(distances)
            
            # 设置中文字体
            plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False
            
            # 根据断面数量决定绘制策略
            if n_sections <= 10:
                # 少于10个断面：每个断面单独展示
                return self._plot_detailed_cross_sections(profile_data, channel_config, flow, save_path)
            else:
                # 超过10个断面：优化绘制
                return self._plot_optimized_cross_sections(profile_data, channel_config, flow, save_path)
                
        except Exception as e:
            print(f"绘制横断面图失败: {e}")
            return ""
    
    def _plot_detailed_cross_sections(self, profile_data: Dict[str, Any], 
                                    channel_config: Dict[str, Any],
                                    flow: float,
                                    save_path: Optional[str] = None) -> str:
        """
        绘制详细横断面图（适用于断面数量 <= 10）
        """
        # 获取数据
        geometry = channel_config['geometry']
        bottom_width = geometry['bottom_width']
        side_slope = geometry['side_slope']
        
        distances = np.array(profile_data['distances'])
        water_levels = np.array(profile_data['water_levels'])
        bottom_elevations = np.array(profile_data['bottom_elevations'])
        depths = water_levels - bottom_elevations
        velocities = np.array(profile_data['velocities'])
        n_sections = len(distances)
        
        # 计算子图布局
        cols = min(5, n_sections)  # 最多5列
        rows = (n_sections + cols - 1) // cols  # 计算需要的行数
        
        # 创建图形（符合拓扑图字体显示规范）
        fig, axes = plt.subplots(rows, cols, figsize=(4*cols, 3*rows))
        if n_sections == 1:
            axes = [axes]
        elif rows == 1:
            axes = [axes] if cols == 1 else axes
        else:
            axes = axes.flatten()
        
        fig.suptitle(f'横断面图集合 (Q={flow:.1f}m3/s)', 
                    fontsize=24, fontweight='bold', color='black')  # 汉字字体放大3倍
        
        # 绘制每个断面
        for i in range(n_sections):
            ax = axes[i]
            
            # 计算断面坐标
            depth = depths[i]
            water_level = water_levels[i]
            bottom_elev = bottom_elevations[i]
            
            # 横断面坐标（以渠道中心为原点）
            y_coords = []
            z_coords = []
            
            # 左岸
            left_top_width = bottom_width/2 + depth * side_slope
            y_coords.extend([-left_top_width, -bottom_width/2, bottom_width/2, left_top_width])
            z_coords.extend([water_level, bottom_elev, bottom_elev, water_level])
            
            # 绘制渠道轮廓
            ax.plot(y_coords, z_coords, 'k-', linewidth=3.0, label='渠道边界')  # 边框加粗至3.0
            
            # 填充水体区域
            if depth > 0:
                water_y = [-bottom_width/2 - depth * side_slope, -bottom_width/2, 
                          bottom_width/2, bottom_width/2 + depth * side_slope]
                water_z = [water_level, bottom_elev, bottom_elev, water_level]
                ax.fill(water_y, water_z, alpha=0.3, color='lightblue', label='水体')
                
                # 水面线
                ax.plot([water_y[0], water_y[-1]], [water_level, water_level], 
                       linewidth=3.0, label='水面线', color='#1f77b4')
            
            # 水位数字显示（符合规范：红色数字，与图形分离）
            ax.text(0, water_level + 0.2, f'{water_level:.2f}m', 
                   ha='center', va='bottom', fontsize=16, color='red', fontweight='bold',  # 数字字体翻倍
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.9))
            
            # 流速数字显示
            if velocities[i] > 0:
                ax.text(0, bottom_elev - 0.5, f'v={velocities[i]:.2f}m/s', 
                       ha='center', va='top', fontsize=16, color='red', fontweight='bold',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.9))
            
            # 设置标题和标签
            section_distance = distances[i] / 1000  # 转换为km
            ax.set_title(f'断面 {i+1} (x={section_distance:.2f}km)', 
                        fontsize=18, color='black', fontweight='bold')  # 汉字字体放大3倍
            ax.set_xlabel('横向距离 (m)', fontsize=14, color='black')
            ax.set_ylabel('高程 (m)', fontsize=14, color='black')
            
            # 设置等比例坐标轴
            ax.set_aspect('equal')
            ax.grid(True, alpha=0.3)
            
            # 只在第一个子图显示图例
            if i == 0:
                ax.legend(fontsize=12, loc='upper right')  # 图例字体放大2倍
        
        # 隐藏多余的子图
        for i in range(n_sections, len(axes)):
            axes[i].set_visible(False)
        
        # 调整布局
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        
        # 保存图片
        if save_path is None:
            save_path = self.output_dir / f'cross_sections_detailed_Q{flow:.0f}.svg'
        
        plt.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        return str(save_path)
    
    def _plot_optimized_cross_sections(self, profile_data: Dict[str, Any], 
                                     channel_config: Dict[str, Any],
                                     flow: float,
                                     save_path: Optional[str] = None) -> str:
        """
        绘制优化横断面图（适用于断面数量 > 10）
        优化策略：显示关键断面（上下游、中间、最大水深点等）
        """
        # 获取数据
        geometry = channel_config['geometry']
        bottom_width = geometry['bottom_width']
        side_slope = geometry['side_slope']
        
        distances = np.array(profile_data['distances'])
        water_levels = np.array(profile_data['water_levels'])
        bottom_elevations = np.array(profile_data['bottom_elevations'])
        depths = water_levels - bottom_elevations
        velocities = np.array(profile_data['velocities'])
        n_sections = len(distances)
        
        # 选择关键断面
        key_indices = self._select_key_cross_sections(depths, n_sections)
        n_key_sections = len(key_indices)
        
        # 计算子图布局
        cols = min(4, n_key_sections)  # 最多4列
        rows = (n_key_sections + cols - 1) // cols
        
        # 创建图形
        fig, axes = plt.subplots(rows, cols, figsize=(5*cols, 4*rows))
        if n_key_sections == 1:
            axes = [axes]
        elif rows == 1:
            axes = [axes] if cols == 1 else axes
        else:
            axes = axes.flatten()
        
        fig.suptitle(f'关键断面横断面图 ({n_sections}个断面中选择{n_key_sections}个) - Q={flow:.1f}m3/s', 
                    fontsize=24, fontweight='bold', color='black')  # 汉字字体放大3倍
        
        # 绘制关键断面
        for plot_idx, section_idx in enumerate(key_indices):
            ax = axes[plot_idx]
            
            # 计算断面坐标
            depth = depths[section_idx]
            water_level = water_levels[section_idx]
            bottom_elev = bottom_elevations[section_idx]
            velocity = velocities[section_idx]
            
            # 横断面坐标
            y_coords = []
            z_coords = []
            
            # 梯形断面坐标
            left_top_width = bottom_width/2 + depth * side_slope
            y_coords.extend([-left_top_width, -bottom_width/2, bottom_width/2, left_top_width])
            z_coords.extend([water_level, bottom_elev, bottom_elev, water_level])
            
            # 绘制渠道轮廓
            ax.plot(y_coords, z_coords, 'k-', linewidth=3.0, label='渠道边界')  # 边框线条加粗至3.0
            
            # 填充水体区域
            if depth > 0:
                water_y = [-bottom_width/2 - depth * side_slope, -bottom_width/2, 
                          bottom_width/2, bottom_width/2 + depth * side_slope]
                water_z = [water_level, bottom_elev, bottom_elev, water_level]
                ax.fill(water_y, water_z, alpha=0.3, color='lightblue', label='水体')
                
                # 水面线
                ax.plot([water_y[0], water_y[-1]], [water_level, water_level], 
                       linewidth=3.0, label='水面线', color='#1f77b4')
            
            # 水位数字显示（红色数字，与图形分离）
            ax.text(0, water_level + 0.3, f'{water_level:.2f}m', 
                   ha='center', va='bottom', fontsize=16, color='red', fontweight='bold',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.9))
            
            # 流速数字显示
            if velocity > 0:
                ax.text(0, bottom_elev - 0.6, f'v={velocity:.2f}m/s', 
                       ha='center', va='top', fontsize=16, color='red', fontweight='bold',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.9))
            
            # 断面类型标识
            section_type = self._get_section_type(section_idx, depths, n_sections)
            section_distance = distances[section_idx] / 1000  # km
            
            ax.set_title(f'{section_type} (x={section_distance:.2f}km, 第{section_idx+1}断面)', 
                        fontsize=18, color='black', fontweight='bold')  # 汉字字体放大3倍
            ax.set_xlabel('横向距离 (m)', fontsize=14, color='black')
            ax.set_ylabel('高程 (m)', fontsize=14, color='black')
            
            # 设置等比例坐标轴
            ax.set_aspect('equal')
            ax.grid(True, alpha=0.3)
            
            # 只在第一个子图显示图例
            if plot_idx == 0:
                ax.legend(fontsize=12, loc='upper right')  # 图例字体放大2倍
        
        # 隐藏多余的子图
        for i in range(n_key_sections, len(axes)):
            axes[i].set_visible(False)
        
        # 调整布局
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        
        # 保存图片
        if save_path is None:
            save_path = self.output_dir / f'cross_sections_optimized_Q{flow:.0f}.svg'
        
        plt.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        return str(save_path)
    
    def _select_key_cross_sections(self, depths: np.ndarray, n_sections: int) -> List[int]:
        """
        选择关键断面索引
        
        选择策略：
        1. 上下游端点
        2. 最大水深点
        3. 最小水深点
        4. 中间点
        5. 均匀分布的其他点
        """
        key_indices = set()
        
        # 1. 上下游端点
        key_indices.add(0)  # 下游
        key_indices.add(n_sections - 1)  # 上游
        
        # 2. 最大水深点
        max_depth_idx = np.argmax(depths)
        key_indices.add(max_depth_idx)
        
        # 3. 最小水深点
        min_depth_idx = np.argmin(depths)
        key_indices.add(min_depth_idx)
        
        # 4. 中间点
        mid_idx = n_sections // 2
        key_indices.add(mid_idx)
        
        # 5. 如果还不足，按均匀分布添加
        target_count = min(8, n_sections)  # 最多8个关键断面
        if len(key_indices) < target_count:
            # 均匀分布添加更多点
            step = n_sections // (target_count - len(key_indices) + 1)
            for i in range(step, n_sections, step):
                if len(key_indices) >= target_count:
                    break
                key_indices.add(i)
        
        # 转换为排序列表
        return sorted(list(key_indices))
    
    def _get_section_type(self, section_idx: int, depths: np.ndarray, n_sections: int) -> str:
        """
        获取断面类型描述
        """
        if section_idx == 0:
            return '下游断面'
        elif section_idx == n_sections - 1:
            return '上游断面'
        elif section_idx == np.argmax(depths):
            return '最大水深断面'
        elif section_idx == np.argmin(depths):
            return '最小水深断面'
        elif section_idx == n_sections // 2:
            return '中间断面'
        else:
            return '关键断面'
    
    def plot_multi_scenario_comparison(self, save_filename: str = "flow_comparison.svg") -> str:
        """
        绘制多工况对比图（符合用户记忆规范）
        
        Args:
            save_filename: 保存文件名
            
        Returns:
            str: 图片文件路径
        """
        if not self.profile_results:
            return ""
        
        try:
            # 设置中文字体
            plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False
            
            # 创建图形（符合水面线对比图标准化输出要求）
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(18, 14))
            fig.suptitle('多工况水面线对比分析', 
                        fontsize=20, fontweight='bold', color='black')  # 汉字黑色显示
            
            # 颜色和样式设置
            colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
            line_styles = ['-', '--', '-.', ':', '-', '--']
            
            # 绘制每个工况的数据
            for i, result in enumerate(self.profile_results):
                profile_data = result['profile_data']
                case_name = result['case_name']
                flow = result['flow']
                
                # 修正方向：左边上游，右边下游
                distances = np.array(profile_data['distances']) / 1000  # km
                distances = distances[::-1]  # 反转
                distances = distances.max() - distances  # 重新计算，上游为0
                
                water_levels = np.array(profile_data['water_levels'])[::-1]
                bottom_elevations = np.array(profile_data['bottom_elevations'])[::-1]
                velocities = np.array(profile_data['velocities'])[::-1]
                froude_numbers = np.array(profile_data.get('froude_numbers', [0] * len(distances)))[::-1]
                
                color = colors[i % len(colors)]
                style = line_styles[i % len(line_styles)]
                
                # 图1: 水面线对比（符合渠道水面线多工况对比可视化原则）
                ax1.plot(distances, water_levels, color=color, linestyle=style, 
                        linewidth=3.0, label=f'{case_name} (Q={flow:.0f}m3/s)', alpha=0.8)  # m3替代m³
                
                # 仅第一个工况显示渠底线（避免重复）
                if i == 0:
                    ax1.plot(distances, bottom_elevations, linewidth=3.0, 
                            label='渠底线', color='#8B4513', alpha=0.8)
                
                # 图2: 流速对比
                ax2.plot(distances, velocities, color=color, linestyle=style, 
                        linewidth=2.5, label=f'{case_name}', alpha=0.8)
                
                # 图3: 弗劳德数对比
                ax3.plot(distances, froude_numbers, color=color, linestyle=style, 
                        linewidth=2.5, label=f'{case_name}', alpha=0.8)
                
                # 图4: 水深对比
                depths = water_levels - bottom_elevations
                ax4.plot(distances, depths, color=color, linestyle=style, 
                        linewidth=2.5, label=f'{case_name}', alpha=0.8)
            
            # 设置图1：水面线对比
            ax1.set_xlabel('距离 (km) - 左：上游，右：下游', fontsize=14, color='black')  # 明确标注方向
            ax1.set_ylabel('高程 (m)', fontsize=14, color='black')
            ax1.set_title('水面线纵剖面对比', fontsize=16, color='black')
            ax1.legend(fontsize=10, loc='best')  # 图例字体放大2倍
            ax1.grid(True, alpha=0.3)
            
            # 水位数字标注（仅在关键点显示，避免过于繁杂）
            if len(self.profile_results) <= 3:  # 只在工况较少时显示数字
                for i, result in enumerate(self.profile_results[:2]):  # 只显示前2个工况
                    profile_data = result['profile_data']
                    distances_km = np.array(profile_data['distances']) / 1000
                    water_levels = np.array(profile_data['water_levels'])
                    
                    # 只显示端点数字
                    for j in [0, -1]:  # 上下游端点
                        ax1.annotate(f'{water_levels[j]:.1f}', 
                                   xy=(distances_km[j], water_levels[j]), 
                                   xytext=(distances_km[j], water_levels[j] + 0.3),
                                   fontsize=11, color='red', fontweight='bold',
                                   ha='center', va='bottom',
                                   bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.9))
            
            # 设置图2：流速对比
            ax2.set_xlabel('距离 (km) - 左：上游，右：下游', fontsize=14, color='black')
            ax2.set_ylabel('流速 (m/s)', fontsize=14, color='black')
            ax2.set_title('流速分布对比', fontsize=16, color='black')
            ax2.legend(fontsize=10, loc='best')
            ax2.grid(True, alpha=0.3)
            
            # 设置图3：弗劳德数对比
            ax3.axhline(y=1.0, color='red', linestyle='--', linewidth=2.0, alpha=0.7, label='Fr=1(临界流)')
            ax3.set_xlabel('距离 (km) - 左：上游，右：下游', fontsize=14, color='black')
            ax3.set_ylabel('弗劳德数 Fr', fontsize=14, color='black')
            ax3.set_title('弗劳德数分布对比', fontsize=16, color='black')
            ax3.legend(fontsize=10, loc='best')
            ax3.grid(True, alpha=0.3)
            
            # 设置图4：水深对比
            ax4.set_xlabel('距离 (km) - 左：上游，右：下游', fontsize=14, color='black')
            ax4.set_ylabel('水深 (m)', fontsize=14, color='black')
            ax4.set_title('水深分布对比', fontsize=16, color='black')
            ax4.legend(fontsize=10, loc='best')
            ax4.grid(True, alpha=0.3)
            
            # 调整布局以避免汉字与图形重叠
            plt.tight_layout(rect=[0, 0.03, 1, 0.95])
            
            # 保存图片
            save_path = str(self.output_dir / save_filename)
            print(f"调试: 准备保存图片到: {save_path}")
            
            # 确保目录存在
            import os
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            try:
                plt.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
                print(f"调试: matplotlib savefig 调用完成")
                
                # 验证文件是否生成
                if os.path.exists(save_path):
                    file_size = os.path.getsize(save_path)
                    print(f"调试: 文件成功生成，大小: {file_size} bytes")
                else:
                    print(f"调试: 文件未生成: {save_path}")
                    
            except Exception as save_error:
                print(f"调试: 保存文件时出错: {save_error}")
                return ""
            
            plt.close()
            
            return save_path
            
        except Exception as e:
            print(f"绘制多工况对比图失败: {e}")
            return ""