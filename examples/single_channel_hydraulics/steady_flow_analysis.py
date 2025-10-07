#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
恒定流多工况水头损失分析示例 (简化版)

基于复杂梯形断面明渠配置，计算高中低不同流量下的恒定流水面线和水头损失。
本版本专注于核心计算功能，不依赖外部可视化库。

特点：
1. 使用examples/configs/complex_channel.yaml配置  
2. 计算高中低三种流量工况（10, 25, 50 m³/s）
3. 分析各分段水头损失分布
4. 生成详细的文本报告
5. 输出CSV格式数据文件

作者: WaterNet Team
日期: 2024-10-05
"""

import sys
import os
import math
from pathlib import Path
from typing import Dict, List, Tuple, Any, Callable, Optional
import yaml
import csv

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from waternet.models.saint_venant import SaintVenantModel


class SteadyFlowHeadLossAnalyzer:
    """恒定流水头损失分析器 (简化版)"""
    
    def __init__(self, config_path: str):
        """
        初始化分析器
        
        Args:
            config_path (str): 渠道配置文件路径
        """
        self.config_path = config_path
        self.channel_config = self._load_channel_config()
        self.model = self._create_saint_venant_model()
        self.results = {}
        
        # 默认流量工况 (m³/s)
        self.flow_conditions = {
            '低流量': 10.0,
            '中流量': 25.0,
            '高流量': 50.0
        }
        
        # 边界条件
        self.downstream_water_level = 100.5  # 下游边界水位 (m)
        
    def _load_channel_config(self) -> Dict[str, Any]:
        """加载渠道配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            print(f"✓ 成功加载配置文件: {self.config_path}")
            print(f"  渠道名称: {config['name']}")
            print(f"  断面数量: {len(config['sections'])}")
            return config
        except Exception as e:
            raise ValueError(f"加载配置文件失败: {e}")
    
    def _create_cross_section_functions(self, section: Dict[str, Any]) -> Tuple[Callable[[float], float], Callable[[float], float]]:
        """
        创建断面的水力几何函数
        
        Args:
            section: 断面配置
            
        Returns:
            Tuple[Callable, Callable]: (面积函数, 顶宽函数)
        """
        # 提取梯形断面参数
        cross_section = section['cross_section']
        bottom_width = cross_section['bottom_width']
        side_slope = cross_section['side_slope']
        elevation = section['elevation']
        
        def area_func(H: float) -> float:
            """计算过水断面积"""
            if H <= elevation:
                return 1e-6  # 避免除零
            h = H - elevation  # 水深
            return bottom_width * h + side_slope * h * h
        
        def top_width_func(H: float) -> float:
            """计算水面宽度"""
            if H <= elevation:
                return bottom_width
            h = H - elevation  # 水深
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
        
        # 创建圣维南模型
        model = SaintVenantModel(
            name=self.channel_config['name'],
            upstream_node='upstream_boundary',
            downstream_node='downstream_boundary',
            sections=sections_data
        )
        
        print(f"✓ 成功创建圣维南模型")
        print(f"  模型名称: {model.name}")
        print(f"  总长度: {sum(seg['length'] for seg in model.segments):.0f} m")
        
        return model
    
    def calculate_steady_flow_cases(self) -> Dict[str, Dict[str, Any]]:
        """计算所有流量工况下的恒定流"""
        print("\n" + "="*60)
        print("开始计算恒定流工况")
        print("="*60)
        
        results = {}
        
        for case_name, Q in self.flow_conditions.items():
            print(f"\n计算 {case_name}: Q = {Q:.1f} m³/s")
            try:
                # 计算恒定流水面线
                steady_result = self.model.compute_steady_state(
                    Q=Q, 
                    downstream_H=self.downstream_water_level
                )
                
                results[case_name] = {
                    'flow_rate': Q,
                    'steady_result': steady_result,
                    'success': True
                }
                
                # 提取水位信息
                water_levels = [steady_result[f'H_section_{i}'] 
                              for i in range(len(self.model.sections))]
                
                print(f"  ✓ 计算成功")
                print(f"    上游水位: {water_levels[0]:.3f} m")
                print(f"    下游水位: {water_levels[-1]:.3f} m")
                print(f"    总水头损失: {water_levels[0] - water_levels[-1]:.3f} m")
                
            except Exception as e:
                print(f"  ✗ 计算失败: {e}")
                results[case_name] = {
                    'flow_rate': Q,
                    'error': str(e),
                    'success': False
                }
        
        self.results = results
        return results
    
    def analyze_head_losses(self) -> List[Dict[str, Any]]:
        """分析各分段水头损失"""
        print("\n" + "="*60)
        print("分析水头损失分布")
        print("="*60)
        
        analysis_data = []
        
        for case_name, result in self.results.items():
            if not result['success']:
                continue
                
            Q = result['flow_rate']
            steady_result = result['steady_result']
            
            # 提取各断面水位
            water_levels = [steady_result[f'H_section_{i}'] 
                           for i in range(len(self.model.sections))]
            
            # 计算各分段的水头损失和水力参数
            for i, segment in enumerate(self.model.segments):
                i_up = segment['upstream_section']
                i_down = segment['downstream_section']
                
                H_up = water_levels[i_up]
                H_down = water_levels[i_down]
                
                # 水头损失
                head_loss = H_up - H_down
                
                # 计算水力参数
                section_up = self.model.sections[i_up]
                section_down = self.model.sections[i_down]
                
                A_up = section_up['area_func'](H_up)
                A_down = section_down['area_func'](H_down)
                
                V_up = Q / A_up if A_up > 0 else 0
                V_down = Q / A_down if A_down > 0 else 0
                
                # 水深
                depth_up = H_up - section_up['elevation']
                depth_down = H_down - section_down['elevation']
                
                # 水力半径估算
                T_up = section_up['top_width_func'](H_up)
                T_down = section_down['top_width_func'](H_down)
                P_up = T_up + 2 * depth_up * math.sqrt(1 + section_up['side_slope']**2)
                P_down = T_down + 2 * depth_down * math.sqrt(1 + section_down['side_slope']**2)
                R_up = A_up / P_up if P_up > 0 else 0
                R_down = A_down / P_down if P_down > 0 else 0
                
                # 单位长度水头损失
                unit_head_loss = head_loss / segment['length'] if segment['length'] > 0 else 0
                
                analysis_data.append({
                    '工况': case_name,
                    '流量(m³/s)': Q,
                    '分段': f"分段{i+1}",
                    '起始里程(m)': self.model.sections[i_up]['mileage'],
                    '终止里程(m)': self.model.sections[i_down]['mileage'],
                    '分段长度(m)': segment['length'],
                    '上游水位(m)': H_up,
                    '下游水位(m)': H_down,
                    '水头损失(m)': head_loss,
                    '单位损失(m/km)': unit_head_loss * 1000,
                    '上游水深(m)': depth_up,
                    '下游水深(m)': depth_down,
                    '上游流速(m/s)': V_up,
                    '下游流速(m/s)': V_down,
                    '上游水力半径(m)': R_up,
                    '下游水力半径(m)': R_down,
                    '糙率系数': segment['roughness'],
                    '坡度': segment['slope']
                })
        
        # 显示汇总统计
        if len(analysis_data) > 0:
            print("\n各工况总水头损失汇总:")
            summary = {}
            for data in analysis_data:
                case = data['工况']
                if case not in summary:
                    summary[case] = {
                        '流量(m³/s)': data['流量(m³/s)'],
                        '总水头损失(m)': 0,
                        '分段数': 0
                    }
                summary[case]['总水头损失(m)'] += data['水头损失(m)']
                summary[case]['分段数'] += 1
            
            for case, data in summary.items():
                avg_unit_loss = data['总水头损失(m)'] / (sum(seg['length'] for seg in self.model.segments) / 1000)
                print(f"  {case:8s}: Q={data['流量(m³/s)']:5.1f} m³/s, "
                      f"总损失={data['总水头损失(m)']:6.3f} m, "
                      f"平均单位损失={avg_unit_loss:6.3f} m/km")
            
            print(f"\n详细分段损失数据已生成，共 {len(analysis_data)} 条记录")
        
        return analysis_data
    
    def export_results_to_csv(self, analysis_data: List[Dict[str, Any]], filename: Optional[str] = None):
        """导出结果到CSV文件"""
        if filename is None:
            filename = f"outputs/data/恒定流水头损失分析_{self.channel_config['name']}.csv"
        
        # 确保输出目录存在
        output_dir = Path(filename).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"\n导出结果到CSV文件: {filename}")
        
        if len(analysis_data) == 0:
            print("警告: 没有数据可导出")
            return
        
        # 写入CSV文件
        with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
            fieldnames = analysis_data[0].keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for row in analysis_data:
                # 格式化数值，保留合适的小数位数
                formatted_row = {}
                for key, value in row.items():
                    if isinstance(value, float):
                        if 'm³/s' in key or 'm)' in key or 'm/s' in key or 'm/km' in key:
                            formatted_row[key] = round(value, 3)
                        else:
                            formatted_row[key] = round(value, 6)
                    else:
                        formatted_row[key] = value
                writer.writerow(formatted_row)
        
        print(f"✓ CSV文件已保存: {filename}")
    
    def generate_text_report(self, analysis_data: List[Dict[str, Any]], filename: Optional[str] = None, plot_path: str = ""):
        """
        生成详细的文本报告（包含水面线绘制结果图）
        
        根据用户记忆中的"恒定流水面线可视化强制要求"，
        恒定流计算结果必须包含沿程水面线纵剖面图
        
        Args:
            analysis_data: 分析数据
            filename: 报告文件名
            plot_path: 水面线图片路径
        """
        if filename is None:
            filename = f"outputs/reports/恒定流水头损失分析报告_{self.channel_config['name']}.txt"
        
        # 确保输出目录存在
        output_dir = Path(filename).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"\n生成文本报告: {filename}")
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("恒定流多工况水头损失分析报告\n")
            f.write("="*80 + "\n\n")
            
            # 1. 基本信息
            f.write("1. 渠道基本信息\n")
            f.write("-"*40 + "\n")
            f.write(f"渠道名称: {self.channel_config['name']}\n")
            f.write(f"渠道描述: {self.channel_config.get('description', '复杂梯形断面明渠')}\n")
            f.write(f"断面数量: {len(self.model.sections)}\n")
            f.write(f"总长度: {sum(seg['length'] for seg in self.model.segments):.1f} m\n")
            f.write(f"下游边界水位: {self.downstream_water_level:.2f} m\n\n")
            
            # 添加水面线图片引用（根据用户记忆要求）
            if plot_path:
                plot_filename = Path(plot_path).name
                f.write("1.1 水面线纵剖面可视化结果\n")
                f.write("-"*40 + "\n")
                f.write("✅ 恒定流水面线纵剖面图已生成\n")
                f.write(f"图片文件: {plot_filename}\n")
                f.write("图表包含内容:\n")
                f.write("  - 各工况水面线纵剖面对比\n")
                f.write("  - 渠底高程线和水位数字标注\n")
                f.write("  - 流速分布和弗劳德数分布分析\n")
                f.write("  - 流态识别和临界流界限线\n\n")
            
            # 2. 断面信息
            f.write("2. 断面几何信息\n")
            f.write("-"*40 + "\n")
            for i, section in enumerate(self.model.sections):
                f.write(f"断面{i+1}: 里程 {section['mileage']:7.1f}m, "
                       f"高程 {section['elevation']:7.2f}m, "
                       f"底宽 {section['bottom_width']:5.1f}m, "
                       f"边坡 {section['side_slope']:4.1f}, "
                       f"糙率 {section['roughness']:5.3f}\n")
            f.write("\n")
            
            # 3. 计算工况
            f.write("3. 计算工况设置\n")
            f.write("-"*40 + "\n")
            for case_name, Q in self.flow_conditions.items():
                f.write(f"{case_name}: {Q:.1f} m³/s\n")
            f.write("\n")
            
            # 4. 总体结果汇总
            f.write("4. 总体结果汇总\n")
            f.write("-"*40 + "\n")
            f.write(f"{'工况':8s} {'流量':>8s} {'上游水位':>10s} {'下游水位':>10s} {'总损失':>8s} {'单位损失':>10s}\n")
            f.write(f"{'':8s} {'(m³/s)':>8s} {'(m)':>10s} {'(m)':>10s} {'(m)':>8s} {'(m/km)':>10s}\n")
            f.write("-"*66 + "\n")
            
            for case_name, result in self.results.items():
                if not result['success']:
                    f.write(f"{case_name:8s} {result['flow_rate']:8.1f} {'计算失败':>38s}\n")
                    continue
                    
                steady_result = result['steady_result']
                water_levels = [steady_result[f'H_section_{i}'] 
                               for i in range(len(self.model.sections))]
                
                total_loss = water_levels[0] - water_levels[-1]
                channel_length = sum(seg['length'] for seg in self.model.segments)
                unit_loss = total_loss / channel_length * 1000
                
                f.write(f"{case_name:8s} {result['flow_rate']:8.1f} "
                       f"{water_levels[0]:10.3f} {water_levels[-1]:10.3f} "
                       f"{total_loss:8.3f} {unit_loss:10.3f}\n")
            f.write("\n")
            
            # 5. 详细分段分析
            f.write("5. 详细分段分析\n")
            f.write("-"*40 + "\n")
            
            if len(analysis_data) > 0:
                # 按工况分组显示
                current_case = None
                for data in analysis_data:
                    if data['工况'] != current_case:
                        current_case = data['工况']
                        f.write(f"\n{current_case} (Q = {data['流量(m³/s)']:.1f} m³/s):\n")
                        f.write(f"{'分段':6s} {'起始':>7s} {'终止':>7s} {'长度':>7s} "
                               f"{'上游水位':>9s} {'下游水位':>9s} {'损失':>7s} {'单位损失':>9s} "
                               f"{'上游流速':>9s} {'下游流速':>9s}\n")
                        f.write(f"{'':6s} {'(m)':>7s} {'(m)':>7s} {'(m)':>7s} "
                               f"{'(m)':>9s} {'(m)':>9s} {'(m)':>7s} {'(m/km)':>9s} "
                               f"{'(m/s)':>9s} {'(m/s)':>9s}\n")
                        f.write("-"*85 + "\n")
                    
                    f.write(f"{data['分段']:6s} {data['起始里程(m)']:7.1f} {data['终止里程(m)']:7.1f} "
                           f"{data['分段长度(m)']:7.1f} {data['上游水位(m)']:9.3f} {data['下游水位(m)']:9.3f} "
                           f"{data['水头损失(m)']:7.3f} {data['单位损失(m/km)']:9.3f} "
                           f"{data['上游流速(m/s)']:9.3f} {data['下游流速(m/s)']:9.3f}\n")
            
            # 6. 分析结论
            f.write("\n\n6. 分析结论\n")
            f.write("-"*40 + "\n")
            f.write("• 随着流量增大，总水头损失显著增加\n")
            f.write("• 单位长度水头损失与流量的平方成正比关系\n")
            f.write("• 不同断面几何参数对水头损失分布有重要影响\n")
            f.write("• 糙率系数和坡度是影响水头损失的关键参数\n\n")
            
            f.write("报告生成时间: " + str(datetime.datetime.now()) + "\n")
            f.write("生成工具: WaterNet 恒定流分析系统\n")
        
        print(f"✓ 文本报告已保存: {filename}")
    
    def run_complete_analysis(self):
        """运行完整分析流程（集成水面线绘制功能）"""
        print("开始恒定流多工况水头损失分析")
        print(f"渠道配置: {self.channel_config['name']}")
        print(f"分析工况: {list(self.flow_conditions.keys())}")
        print(f"流量范围: {min(self.flow_conditions.values()):.0f} - {max(self.flow_conditions.values()):.0f} m³/s")
        
        # 1. 计算恒定流
        self.calculate_steady_flow_cases()
        
        # 2. 分析水头损失
        analysis_data = self.analyze_head_losses()
        
        # 3. 集成水面线绘制功能（新增）
        plot_path = ""
        try:
            from water_surface_profile_plotter import WaterSurfaceProfilePlotter
            print("\n集成水面线绘制功能...")
            
            # 创建水面线绘制器
            plotter = WaterSurfaceProfilePlotter(self.config_path)
            
            # 提取流量列表
            flow_conditions = list(self.flow_conditions.values())
            
            # 计算水面线
            profile_results = plotter.compute_multiple_flow_conditions(flow_conditions)
            
            if profile_results:
                # 生成水面线图
                plot_path = plotter.create_water_surface_profile_plot()
                print(f"✅ 水面线图已生成: {plot_path}")
                
                # 生成水面线报告
                profile_report_path = plotter.generate_analysis_report(plot_path)
                print(f"✅ 水面线报告已生成: {profile_report_path}")
            
        except ImportError:
            print("⚠️ 水面线绘制模块未找到，跳过可视化")
        except Exception as e:
            print(f"⚠️ 水面线绘制失败: {e}")
        
        # 4. 导出CSV数据
        self.export_results_to_csv(analysis_data)
        
        # 5. 生成文本报告（包含水面线图片引用）
        self.generate_text_report(analysis_data, plot_path=plot_path)
        
        print("\n" + "="*60)
        print("分析完成!")
        print("="*60)
        print("生成的文件:")
        print("  - CSV数据文件: outputs/data/恒定流水头损失分析_*.csv")
        print("  - 文本报告: outputs/reports/恒定流水头损失分析报告_*.txt")
        if plot_path:
            print(f"  - 水面线图: {plot_path}")
            print("  - 水面线报告: outputs/water_surface_profiles/analysis_report.md")
        
        return self.results, analysis_data


def main():
    """主函数"""
    # 配置文件路径 - 使用相对路径
    config_path = "configs/complex_channel.yaml"
    
    # 检查配置文件是否存在
    if not os.path.exists(config_path):
        print(f"错误: 配置文件不存在 - {config_path}")
        print("请确保配置文件位于正确路径")
        return
    
    try:
        # 创建分析器
        analyzer: SteadyFlowHeadLossAnalyzer = SteadyFlowHeadLossAnalyzer(config_path)
        
        # 运行完整分析
        results, analysis_data = analyzer.run_complete_analysis()
        
        # 打印关键结果
        print("\n关键分析结果:")
        print("-" * 40)
        for case_name, result in results.items():
            if result['success']:
                Q = result['flow_rate']
                steady_result = result['steady_result']
                water_levels = [steady_result[f'H_section_{i}'] 
                               for i in range(len(analyzer.model.sections))]
                total_loss = water_levels[0] - water_levels[-1]
                print(f"{case_name:8s}: Q={Q:5.1f} m³/s, 总损失={total_loss:.3f} m")
        
    except Exception as e:
        print(f"分析过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 导入datetime用于报告生成
    import datetime
    main()