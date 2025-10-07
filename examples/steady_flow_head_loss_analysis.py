#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
恒定流多工况水头损失分析示例

基于复杂梯形断面明渠配置，计算高中低不同流量下的恒定流水面线和水头损失。
演示如何使用WaterNet计算和分析渠道在不同工况下的水力损失特性。

特点：
1. 使用examples/configs/complex_channel.yaml配置
2. 计算高中低三种流量工况（10, 25, 50 m³/s）  
3. 分析各分段水头损失分布
4. 生成详细的水力参数对比表
5. 可视化水面线和损失分布

作者: WaterNet Team
日期: 2024-10-05
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Tuple, Any, Callable, Optional
import yaml

# 可选依赖的条件导入
HAS_NUMPY = False
HAS_MATPLOTLIB = False
HAS_PANDAS = False

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    print("警告: numpy未安装，将使用Python内置math库")
    import math
    
    # 创建numpy的最小兼容层
    class NumpyCompat:
        @staticmethod
        def zeros(size):
            return [0.0] * size
        
        @staticmethod
        def arange(start, stop=None, step=1):
            if stop is None:
                stop = start
                start = 0
            return list(range(start, stop, step))
        
        @staticmethod
        def sqrt(x):
            return math.sqrt(x)
        
        @staticmethod
        def linspace(start, stop, num):
            if num == 1:
                return [start]
            step = (stop - start) / (num - 1)
            return [start + i * step for i in range(num)]
    
    np = NumpyCompat()

try:
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    print("警告: matplotlib未安装，跳过可视化功能")
    HAS_MATPLOTLIB = False

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    print("警告: pandas未安装，将输出基本格式")
    HAS_PANDAS = False

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from waternet.models.saint_venant import SaintVenantModel


class SteadyFlowHeadLossAnalyzer:
    """恒定流水头损失分析器"""
    
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
            Tuple[callable, callable]: (面积函数, 顶宽函数)
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
    
    def calculate_steady_flow_cases(self) -> Dict[str, Dict[str, float]]:
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
    
    def analyze_head_losses(self) -> pd.DataFrame:
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
                P_up = T_up + 2 * depth_up * np.sqrt(1 + section_up['side_slope']**2)
                P_down = T_down + 2 * depth_down * np.sqrt(1 + section_down['side_slope']**2)
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
        
        df = pd.DataFrame(analysis_data)
        
        # 显示汇总统计
        if len(df) > 0:
            print("\n各工况总水头损失汇总:")
            summary = df.groupby('工况').agg({
                '流量(m³/s)': 'first',
                '水头损失(m)': 'sum',
                '单位损失(m/km)': 'mean'
            }).round(3)
            print(summary.to_string())
            
            print(f"\n详细分段损失数据已生成，共 {len(df)} 条记录")
        
        return df
    
    def create_comprehensive_visualization(self, save_path: Optional[str] = None):
        """创建综合可视化图表"""
        print("\n" + "="*60)
        print("生成可视化图表")
        print("="*60)
        
        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS']
        plt.rcParams['axes.unicode_minus'] = False
        
        # 创建子图布局
        fig = plt.figure(figsize=(16, 12))
        
        # 1. 水面线对比图
        ax1 = plt.subplot(2, 3, 1)
        self._plot_water_surface_profiles(ax1)
        
        # 2. 分段水头损失对比
        ax2 = plt.subplot(2, 3, 2)
        self._plot_segment_head_losses(ax2)
        
        # 3. 单位长度损失对比
        ax3 = plt.subplot(2, 3, 3)
        self._plot_unit_head_losses(ax3)
        
        # 4. 流速分布对比
        ax4 = plt.subplot(2, 3, 4)
        self._plot_velocity_profiles(ax4)
        
        # 5. 水深分布对比
        ax5 = plt.subplot(2, 3, 5)
        self._plot_depth_profiles(ax5)
        
        # 6. 总损失汇总柱状图
        ax6 = plt.subplot(2, 3, 6)
        self._plot_total_losses_bar(ax6)
        
        plt.tight_layout()
        
        # 保存图片
        if save_path is None:
            save_path = f"恒定流多工况水头损失分析_{self.channel_config['name']}.png"
        
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"✓ 图表已保存: {save_path}")
        
        plt.show()
    
    def _plot_water_surface_profiles(self, ax):
        """绘制水面线对比"""
        colors = ['blue', 'green', 'red']
        
        for i, (case_name, result) in enumerate(self.results.items()):
            if not result['success']:
                continue
                
            steady_result = result['steady_result']
            water_levels = [steady_result[f'H_section_{j}'] 
                           for j in range(len(self.model.sections))]
            mileages = [section['mileage'] for section in self.model.sections]
            elevations = [section['elevation'] for section in self.model.sections]
            
            ax.plot(mileages, water_levels, 'o-', color=colors[i], 
                   label=f'{case_name} (Q={result["flow_rate"]:.0f}m³/s)',
                   linewidth=2, markersize=6)
        
        # 绘制河底线
        mileages = [section['mileage'] for section in self.model.sections]
        elevations = [section['elevation'] for section in self.model.sections]
        ax.plot(mileages, elevations, 'k--', label='河底高程', linewidth=1)
        
        ax.set_xlabel('里程 (m)')
        ax.set_ylabel('高程 (m)')
        ax.set_title('水面线对比')
        ax.legend()
        ax.grid(True, alpha=0.3)
    
    def _plot_segment_head_losses(self, ax):
        """绘制分段水头损失对比"""
        segment_labels = [f'分段{i+1}' for i in range(len(self.model.segments))]
        colors = ['blue', 'green', 'red']
        
        for i, (case_name, result) in enumerate(self.results.items()):
            if not result['success']:
                continue
                
            steady_result = result['steady_result']
            water_levels = [steady_result[f'H_section_{j}'] 
                           for j in range(len(self.model.sections))]
            
            # 计算各分段水头损失
            head_losses = []
            for seg in self.model.segments:
                i_up = seg['upstream_section'] 
                i_down = seg['downstream_section']
                loss = water_levels[i_up] - water_levels[i_down]
                head_losses.append(loss)
            
            x = np.arange(len(segment_labels)) + i * 0.25
            ax.bar(x, head_losses, width=0.25, color=colors[i], 
                  label=f'{case_name}', alpha=0.7)
        
        ax.set_xlabel('分段')
        ax.set_ylabel('水头损失 (m)')
        ax.set_title('分段水头损失对比')
        ax.set_xticks(np.arange(len(segment_labels)) + 0.25)
        ax.set_xticklabels(segment_labels)
        ax.legend()
        ax.grid(True, alpha=0.3)
    
    def _plot_unit_head_losses(self, ax):
        """绘制单位长度损失对比"""
        colors = ['blue', 'green', 'red']
        
        for i, (case_name, result) in enumerate(self.results.items()):
            if not result['success']:
                continue
                
            steady_result = result['steady_result']
            water_levels = [steady_result[f'H_section_{j}'] 
                           for j in range(len(self.model.sections))]
            
            # 计算各分段单位长度损失
            unit_losses = []
            mileage_centers = []
            for seg in self.model.segments:
                i_up = seg['upstream_section']
                i_down = seg['downstream_section']
                loss = water_levels[i_up] - water_levels[i_down]
                unit_loss = loss / seg['length'] * 1000  # m/km
                unit_losses.append(unit_loss)
                
                # 分段中心里程
                center = (self.model.sections[i_up]['mileage'] + 
                         self.model.sections[i_down]['mileage']) / 2
                mileage_centers.append(center)
            
            ax.plot(mileage_centers, unit_losses, 'o-', color=colors[i],
                   label=f'{case_name}', linewidth=2, markersize=6)
        
        ax.set_xlabel('里程 (m)')
        ax.set_ylabel('单位损失 (m/km)')
        ax.set_title('单位长度水头损失')
        ax.legend()
        ax.grid(True, alpha=0.3)
    
    def _plot_velocity_profiles(self, ax):
        """绘制流速分布对比"""
        colors = ['blue', 'green', 'red']
        
        for i, (case_name, result) in enumerate(self.results.items()):
            if not result['success']:
                continue
                
            Q = result['flow_rate']
            steady_result = result['steady_result']
            water_levels = [steady_result[f'H_section_{j}'] 
                           for j in range(len(self.model.sections))]
            
            # 计算各断面流速
            velocities = []
            mileages = []
            for j, section in enumerate(self.model.sections):
                H = water_levels[j]
                A = section['area_func'](H)
                V = Q / A if A > 0 else 0
                velocities.append(V)
                mileages.append(section['mileage'])
            
            ax.plot(mileages, velocities, 'o-', color=colors[i],
                   label=f'{case_name}', linewidth=2, markersize=6)
        
        ax.set_xlabel('里程 (m)')
        ax.set_ylabel('流速 (m/s)')
        ax.set_title('断面流速分布')
        ax.legend()
        ax.grid(True, alpha=0.3)
    
    def _plot_depth_profiles(self, ax):
        """绘制水深分布对比"""
        colors = ['blue', 'green', 'red']
        
        for i, (case_name, result) in enumerate(self.results.items()):
            if not result['success']:
                continue
                
            steady_result = result['steady_result']
            water_levels = [steady_result[f'H_section_{j}'] 
                           for j in range(len(self.model.sections))]
            
            # 计算各断面水深
            depths = []
            mileages = []
            for j, section in enumerate(self.model.sections):
                H = water_levels[j]
                depth = H - section['elevation']
                depths.append(depth)
                mileages.append(section['mileage'])
            
            ax.plot(mileages, depths, 'o-', color=colors[i],
                   label=f'{case_name}', linewidth=2, markersize=6)
        
        ax.set_xlabel('里程 (m)')
        ax.set_ylabel('水深 (m)')
        ax.set_title('断面水深分布')
        ax.legend()
        ax.grid(True, alpha=0.3)
    
    def _plot_total_losses_bar(self, ax):
        """绘制总损失汇总柱状图"""
        case_names = []
        total_losses = []
        flow_rates = []
        
        for case_name, result in self.results.items():
            if not result['success']:
                continue
                
            steady_result = result['steady_result']
            water_levels = [steady_result[f'H_section_{j}'] 
                           for j in range(len(self.model.sections))]
            
            total_loss = water_levels[0] - water_levels[-1]
            case_names.append(case_name)
            total_losses.append(total_loss)
            flow_rates.append(result['flow_rate'])
        
        colors = ['blue', 'green', 'red']
        bars = ax.bar(case_names, total_losses, color=colors[:len(case_names)], alpha=0.7)
        
        # 在柱子上添加数值标签
        for bar, loss, Q in zip(bars, total_losses, flow_rates):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.001,
                   f'{loss:.3f}m\n(Q={Q:.0f})', 
                   ha='center', va='bottom', fontsize=10)
        
        ax.set_ylabel('总水头损失 (m)')
        ax.set_title('总水头损失汇总')
        ax.grid(True, alpha=0.3, axis='y')
    
    def export_results_to_excel(self, filename: Optional[str] = None):
        """导出结果到Excel文件"""
        if filename is None:
            filename = f"恒定流水头损失分析_{self.channel_config['name']}.xlsx"
        
        print(f"\n导出结果到Excel文件: {filename}")
        
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            # 1. 总体汇总表
            summary_data = []
            for case_name, result in self.results.items():
                if not result['success']:
                    continue
                    
                Q = result['flow_rate']
                steady_result = result['steady_result']
                water_levels = [steady_result[f'H_section_{j}'] 
                               for j in range(len(self.model.sections))]
                
                total_loss = water_levels[0] - water_levels[-1]
                channel_length = sum(seg['length'] for seg in self.model.segments)
                avg_unit_loss = total_loss / channel_length * 1000  # m/km
                
                summary_data.append({
                    '工况名称': case_name,
                    '流量(m³/s)': Q,
                    '上游水位(m)': water_levels[0],
                    '下游水位(m)': water_levels[-1],
                    '总水头损失(m)': total_loss,
                    '渠道总长(m)': channel_length,
                    '平均单位损失(m/km)': avg_unit_loss
                })
            
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='总体汇总', index=False)
            
            # 2. 详细分段分析
            detail_df = self.analyze_head_losses()
            detail_df.to_excel(writer, sheet_name='分段详细分析', index=False)
            
            # 3. 断面水位数据
            section_data = []
            for case_name, result in self.results.items():
                if not result['success']:
                    continue
                    
                steady_result = result['steady_result']
                for i, section in enumerate(self.model.sections):
                    water_level = steady_result[f'H_section_{i}']
                    depth = water_level - section['elevation']
                    Q = result['flow_rate']
                    A = section['area_func'](water_level)
                    V = Q / A if A > 0 else 0
                    
                    section_data.append({
                        '工况': case_name,
                        '流量(m³/s)': Q,
                        '断面编号': i,
                        '里程(m)': section['mileage'],
                        '底高程(m)': section['elevation'],
                        '水位(m)': water_level,
                        '水深(m)': depth,
                        '断面积(m²)': A,
                        '断面流速(m/s)': V,
                        '底宽(m)': section['bottom_width'],
                        '边坡系数': section['side_slope'],
                        '糙率系数': section['roughness']
                    })
            
            section_df = pd.DataFrame(section_data)
            section_df.to_excel(writer, sheet_name='断面水位数据', index=False)
        
        print(f"✓ Excel文件已保存: {filename}")
    
    def run_complete_analysis(self):
        """运行完整分析流程"""
        print("开始恒定流多工况水头损失分析")
        print(f"渠道配置: {self.channel_config['name']}")
        print(f"分析工况: {list(self.flow_conditions.keys())}")
        print(f"流量范围: {min(self.flow_conditions.values()):.0f} - {max(self.flow_conditions.values()):.0f} m³/s")
        
        # 1. 计算恒定流
        self.calculate_steady_flow_cases()
        
        # 2. 分析水头损失
        loss_df = self.analyze_head_losses()
        
        # 3. 生成可视化图表
        self.create_comprehensive_visualization()
        
        # 4. 导出Excel报告
        self.export_results_to_excel()
        
        print("\n" + "="*60)
        print("分析完成!")
        print("="*60)
        print("生成的文件:")
        print("  - 可视化图表: 恒定流多工况水头损失分析_*.png")
        print("  - Excel报告: 恒定流水头损失分析_*.xlsx")
        
        return self.results, loss_df


def main():
    """主函数"""
    # 配置文件路径
    config_path = "examples/configs/complex_channel.yaml"
    
    # 检查配置文件是否存在
    if not os.path.exists(config_path):
        print(f"错误: 配置文件不存在 - {config_path}")
        print("请确保配置文件位于正确路径")
        return
    
    try:
        # 创建分析器
        analyzer = SteadyFlowHeadLossAnalyzer(config_path)
        
        # 运行完整分析
        results, loss_df = analyzer.run_complete_analysis()
        
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
        raise


if __name__ == "__main__":
    main()