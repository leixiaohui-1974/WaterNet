"""
分布式方法可视化模块
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime

def create_distributed_visualization(simulation_results, time_hours, input_flows, downstream_levels):
    """创建分布式方法对比可视化"""
    try:
        # 设置中文字体和更好的可视化效果
        plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        plt.rcParams['font.size'] = 12
        
        title_fontsize = 26
        label_fontsize = 20
        legend_fontsize = 18
        tick_fontsize = 14
        
        # 创建超大型图表
        fig = plt.figure(figsize=(32, 24))
        gs = fig.add_gridspec(4, 4, height_ratios=[0.8, 1, 1, 1], width_ratios=[1, 1, 1, 1], 
                             hspace=0.3, wspace=0.3)
        
        fig.suptitle('WaterNet分布式方法综合对比分析\\n多种分布式方法、多断面、多物理量时间序列对比', 
                     fontsize=title_fontsize, fontweight='bold', y=0.95)
        
        # 1. 边界条件
        ax1 = fig.add_subplot(gs[0, :2])
        ax1.plot(time_hours, input_flows, 'k-', linewidth=4, label='上游边界条件（进口流量）', marker='o', markersize=6)
        ax1.set_xlabel('时间 (小时)', fontsize=label_fontsize)
        ax1.set_ylabel('流量 (m³/s)', fontsize=label_fontsize)
        ax1.set_title('进口边界条件', fontsize=label_fontsize)
        ax1.legend(fontsize=legend_fontsize)
        ax1.grid(True, alpha=0.3)
        
        ax2 = fig.add_subplot(gs[0, 2:])
        ax2.plot(time_hours, downstream_levels, 'b-', linewidth=4, label='下游边界条件（出口水位）', marker='s', markersize=6)
        ax2.set_xlabel('时间 (小时)', fontsize=label_fontsize)
        ax2.set_ylabel('水位 (m)', fontsize=label_fontsize)
        ax2.set_title('出口边界条件', fontsize=label_fontsize)
        ax2.legend(fontsize=legend_fontsize)
        ax2.grid(True, alpha=0.3)
        
        # 2. 各方法出流量对比
        ax3 = fig.add_subplot(gs[1, :])
        ax3.plot(time_hours, input_flows, 'k--', linewidth=2, alpha=0.7, label='入流参考')
        
        for method_name, result in simulation_results.items():
            if result['success']:
                config = result['config']
                outflows = result['states']['outflows']
                ax3.plot(time_hours, outflows, color=config['color'], linewidth=3,
                        label=method_name, marker=config['marker'], markersize=6, alpha=0.8)
        
        ax3.set_xlabel('时间 (小时)', fontsize=label_fontsize)
        ax3.set_ylabel('出流量 (m³/s)', fontsize=label_fontsize)
        ax3.set_title('多种分布式方法出流响应对比', fontsize=label_fontsize)
        ax3.legend(fontsize=legend_fontsize-2, ncol=3)
        ax3.grid(True, alpha=0.3)
        
        # 3. 断面时间序列（遵循2×2布局规范）
        section_names = ['upstream', 'middle', 'downstream']
        section_titles = ['上游断面', '中游断面', '下游断面']
        
        for section_idx, (section_name, section_title) in enumerate(zip(section_names, section_titles)):
            row_idx = section_idx + 2
            if section_idx >= 3 or row_idx >= 4:  # 防止索引越界
                break
            
            # 水位
            ax_h = fig.add_subplot(gs[row_idx, 0])
            # 流量
            ax_q = fig.add_subplot(gs[row_idx, 1])
            # 流速
            ax_v = fig.add_subplot(gs[row_idx, 2])
            # 弗劳德数
            ax_fr = fig.add_subplot(gs[row_idx, 3])
            
            for method_name, result in simulation_results.items():
                if result['success'] and 'sections' in result['states']:
                    config = result['config']
                    sections_data = result['states']['sections']
                    
                    if section_name in sections_data:
                        section_data = sections_data[section_name]
                        
                        ax_h.plot(time_hours, section_data['water_levels'], 
                                color=config['color'], linewidth=2, alpha=0.8)
                        ax_q.plot(time_hours, section_data['flows'], 
                                color=config['color'], linewidth=2, alpha=0.8)
                        ax_v.plot(time_hours, section_data['velocities'], 
                                color=config['color'], linewidth=2, alpha=0.8)
                        ax_fr.plot(time_hours, section_data['froude_numbers'], 
                                 color=config['color'], linewidth=2, alpha=0.8)
            
            ax_h.set_ylabel('水位 (m)', fontsize=label_fontsize-4)
            ax_h.set_title(f'{section_title} - 水位', fontsize=label_fontsize-4)
            ax_h.grid(True, alpha=0.3)
            
            ax_q.set_ylabel('流量 (m³/s)', fontsize=label_fontsize-4)
            ax_q.set_title(f'{section_title} - 流量', fontsize=label_fontsize-4)
            ax_q.grid(True, alpha=0.3)
            
            ax_v.set_ylabel('流速 (m/s)', fontsize=label_fontsize-4)
            ax_v.set_title(f'{section_title} - 流速', fontsize=label_fontsize-4)
            ax_v.grid(True, alpha=0.3)
            
            ax_fr.set_ylabel('弗劳德数', fontsize=label_fontsize-4)
            ax_fr.set_title(f'{section_title} - Fr', fontsize=label_fontsize-4)
            ax_fr.axhline(y=1.0, color='red', linestyle='--', alpha=0.7)
            ax_fr.grid(True, alpha=0.3)
            
            if section_idx == len(section_names) - 1:
                ax_h.set_xlabel('时间 (小时)', fontsize=label_fontsize-4)
                ax_q.set_xlabel('时间 (小时)', fontsize=label_fontsize-4)
                ax_v.set_xlabel('时间 (小时)', fontsize=label_fontsize-4)
                ax_fr.set_xlabel('时间 (小时)', fontsize=label_fontsize-4)
        
        # 使用自动调整布局，避免tight_layout警告
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            plt.tight_layout(rect=[0, 0.02, 1, 0.93])
        
        # 保存图片
        script_dir = Path(__file__).parent
        output_dir = script_dir / 'outputs' / 'plots' / 'distributed_methods'
        output_dir.mkdir(parents=True, exist_ok=True)
        save_path = output_dir / 'distributed_methods_comparison.svg'
        
        plt.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        if save_path.exists():
            file_size = save_path.stat().st_size
            print(f"   📊 分布式方法对比图生成成功: {file_size/1024/1024:.2f} MB")
            return str(save_path)
            
        return None
        
    except Exception as e:
        print(f"❌ 可视化创建失败: {e}")
        return None

def generate_distributed_report(simulation_results, plot_path):
    """生成分布式方法分析报告"""
    try:
        script_dir = Path(__file__).parent
        output_dir = script_dir / 'outputs' / 'reports'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        report_path = output_dir / 'distributed_methods_analysis_report.md'
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# WaterNet分布式方法综合对比分析报告\\n\\n")
            f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n\\n")
            
            f.write("## 1. 分析概述\\n\\n")
            f.write("本报告基于WaterNet基础库，对多种分布式非恒定流仿真方法进行了综合对比分析，")
            f.write("包括完整圣维方形程、简化圣维方形程系列（动力波、扩散波、运动波）以及集总参数方法。\\n\\n")
            
            f.write("## 2. 方法配置\\n\\n")
            f.write("| 方法名称 | 方法类型 | 计算复杂度 | 仿真精度 |\\n")
            f.write("|---------|---------|-----------|---------|\\n")
            
            for method_name, result in simulation_results.items():
                if result['success']:
                    config = result['config']
                    f.write(f"| {method_name} | {config['category']} | {config['complexity']} | {config['accuracy']} |\\n")
            
            f.write("\\n## 3. 仿真结果分析\\n\\n")
            
            for method_name, result in simulation_results.items():
                if result['success']:
                    outflows = result['states']['outflows']
                    input_flows = result['states']['inflows']
                    peak_reduction = (max(input_flows) - max(outflows)) / max(input_flows) * 100
                    
                    f.write(f"### {method_name}\\n")
                    f.write(f"- 坦化效应: {peak_reduction:.1f}%\\n")
                    f.write(f"- 方法类型: {result['config']['category']}\\n")
                    f.write(f"- 计算复杂度: {result['config']['complexity']}\\n\\n")
            
            f.write("## 4. 可视化结果\\n\\n")
            if plot_path:
                f.write(f"综合对比图已生成: `{Path(plot_path).name}`\\n\\n")
                f.write("图表内容：\\n")
                f.write("- 进出口边界条件展示\\n")
                f.write("- 多种方法出流响应对比\\n")
                f.write("- 三个断面（上游、中游、下游）的四个物理量时间序列\\n")
                f.write("- 符合断面时间序列图多物理量展示规范\\n\\n")
            
            f.write("---\\n")
            f.write("*本报告遵循多方法非恒定流时间序列对比规范和断面时间序列图多物理量展示规范*\\n")
        
        print(f"   📄 分析报告已保存: {report_path}")
        return str(report_path)
        
    except Exception as e:
        print(f"❌ 报告生成失败: {e}")
        return None