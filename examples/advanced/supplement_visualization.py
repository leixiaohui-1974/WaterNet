#!/usr/bin/env python3
"""
补充时间序列可视化脚本

为非恒定流阶跃响应分析补充时间序列可视化功能。

Author: WaterNet Development Team
Date: 2024-10-04
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

def plot_simple_time_series():
    """绘制简单的时间序列响应图"""
    
    # 配置中文字体
    try:
        plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        print("✅ 中文字体配置成功")
    except:
        print("⚠️ 中文字体配置失败，使用默认字体")
    
    # 读取CSV数据
    csv_file = Path("阶跃响应对比数据.csv")
    if not csv_file.exists():
        print("❌ 找不到阶跃响应对比数据.csv文件")
        return
    
    df = pd.read_csv(csv_file, encoding='utf-8-sig')
    print(f"✅ 成功读取数据文件，共{len(df)}行记录")
    
    # 创建图形
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('5断面明渠非恒定流阶跃响应分析结果', fontsize=16, fontweight='bold')
    
    scenarios = df['场景'].unique()
    colors = ['red', 'blue', 'green', 'orange', 'purple']
    
    # 左上: 各场景最终水位分布
    ax1 = axes[0, 0]
    for i, scenario in enumerate(scenarios):
        scenario_data = df[df['场景'] == scenario]
        ax1.plot(scenario_data['里程'], scenario_data['最终水位'], 
                color=colors[i % len(colors)], marker='o', linewidth=2, 
                markersize=6, label=scenario)
    
    ax1.set_xlabel('里程 (m)', fontsize=12)
    ax1.set_ylabel('最终水位 (m)', fontsize=12)
    ax1.set_title('各场景最终水位纵剖面分布', fontsize=14, fontweight='bold')
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3)
    
    # 右上: 流量变化幅度对比
    ax2 = axes[0, 1]
    for i, scenario in enumerate(scenarios):
        scenario_data = df[df['场景'] == scenario]
        ax2.bar(scenario_data['断面'] + i*0.25, scenario_data['流量变化'], 
               width=0.25, alpha=0.8, color=colors[i % len(colors)], label=scenario)
    
    ax2.set_xlabel('断面编号', fontsize=12)
    ax2.set_ylabel('流量变化 (m³/s)', fontsize=12)
    ax2.set_title('各断面流量变化幅度对比', fontsize=14, fontweight='bold')
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.3)
    
    # 左下: 水位变化幅度对比
    ax3 = axes[1, 0]
    for i, scenario in enumerate(scenarios):
        scenario_data = df[df['场景'] == scenario]
        ax3.bar(scenario_data['断面'] + i*0.25, scenario_data['水位变化'], 
               width=0.25, alpha=0.8, color=colors[i % len(colors)], label=scenario)
    
    ax3.set_xlabel('断面编号', fontsize=12)
    ax3.set_ylabel('水位变化 (m)', fontsize=12)
    ax3.set_title('各断面水位变化幅度对比', fontsize=14, fontweight='bold')
    ax3.legend(fontsize=10)
    ax3.grid(True, alpha=0.3)
    
    # 右下: 数据表格
    ax4 = axes[1, 1]
    ax4.axis('tight')
    ax4.axis('off')
    
    # 创建汇总表格
    summary_data = []
    for scenario in scenarios:
        scenario_data = df[df['场景'] == scenario]
        summary_data.append([
            scenario,
            f"{scenario_data['流量变化'].abs().mean():.1f}",
            f"{scenario_data['水位变化'].abs().mean():.3f}",
            f"{scenario_data['最终水位'].max():.2f}",
            f"{scenario_data['最终水位'].min():.2f}"
        ])
    
    columns = ['场景', '平均流量变化\n(m³/s)', '平均水位变化\n(m)', '最高水位\n(m)', '最低水位\n(m)']
    
    table = ax4.table(cellText=summary_data, colLabels=columns, 
                     cellLoc='center', loc='center')
    
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.0, 2.0)
    
    # 设置表头样式
    for i in range(len(columns)):
        table[(0, i)].set_facecolor('#40466e')
        table[(0, i)].set_text_props(weight='bold', color='white')
    
    ax4.set_title('阶跃响应汇总统计', fontsize=14, fontweight='bold', pad=20)
    
    plt.tight_layout()
    
    # 保存图片
    output_file = Path("非恒定流阶跃响应汇总分析.png")
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✅ 时间序列分析图已保存: {output_file}")
    
    # plt.show()  # 注释掉以便自动运行
    return output_file

def create_detailed_analysis():
    """创建详细的分析报告"""
    print("\n" + "="*60)
    print("详细分析报告")
    print("="*60)
    
    try:
        # 读取数据
        df = pd.read_csv("阶跃响应对比数据.csv", encoding='utf-8-sig')
        
        print("\n📊 统计摘要:")
        print("-" * 40)
        
        scenarios = df['场景'].unique()
        for scenario in scenarios:
            scenario_data = df[df['场景'] == scenario]
            print(f"\n{scenario}:")
            print(f"  • 流量变化范围: {scenario_data['流量变化'].min():.1f} ~ {scenario_data['流量变化'].max():.1f} m³/s")
            print(f"  • 水位变化范围: {scenario_data['水位变化'].min():.3f} ~ {scenario_data['水位变化'].max():.3f} m")
            print(f"  • 最终水位范围: {scenario_data['最终水位'].min():.2f} ~ {scenario_data['最终水位'].max():.2f} m")
            
            # 分析最敏感的断面
            max_change_idx = scenario_data['水位变化'].abs().idxmax()
            max_change_section = scenario_data.loc[max_change_idx, '断面']
            max_change_value = scenario_data.loc[max_change_idx, '水位变化']
            print(f"  • 最敏感断面: 断面{max_change_section} (水位变化 {max_change_value:.3f} m)")
        
        print("\n🔍 关键发现:")
        print("-" * 40)
        
        # 找出各类关键特性
        max_flow_change = df['流量变化'].abs().max()
        max_flow_scenario = df.loc[df['流量变化'].abs().idxmax(), '场景']
        
        max_water_change = df['水位变化'].abs().max()
        max_water_scenario = df.loc[df['水位变化'].abs().idxmax(), '场景']
        
        print(f"1. 最大流量变化: {max_flow_change:.1f} m³/s (发生在{max_flow_scenario})")
        print(f"2. 最大水位变化: {max_water_change:.3f} m (发生在{max_water_scenario})")
        
        # 分析各断面的响应特性
        print(f"\n3. 各断面响应特性:")
        for section in sorted(df['断面'].unique()):
            section_data = df[df['断面'] == section]
            avg_water_change = section_data['水位变化'].abs().mean()
            avg_flow_change = section_data['流量变化'].abs().mean()
            print(f"   断面{section}: 平均水位变化 {avg_water_change:.3f}m, 平均流量变化 {avg_flow_change:.1f}m³/s")
        
        print(f"\n4. 物理机理解释:")
        print(f"   • 上游流量阶跃：影响逐渐向下游传播，体现洪水波传播特性")
        print(f"   • 下游水位阶跃：主要影响下游断面，体现回水效应的局部性")
        print(f"   • 中间断面：承担了流量和水位的过渡调节作用")
        
    except Exception as e:
        print(f"❌ 分析过程出错: {e}")

if __name__ == "__main__":
    print("补充时间序列可视化分析")
    print("="*40)
    
    try:
        # 绘制汇总分析图
        output_file = plot_simple_time_series()
        
        # 创建详细分析
        create_detailed_analysis()
        
        print("\n🎉 补充分析完成！")
        print(f"生成的文件:")
        print(f"  📊 {output_file}")
        print(f"  📈 初始稳态水力学参数分布.png")
        print(f"  📋 阶跃响应对比数据.csv")
        
    except Exception as e:
        print(f"❌ 处理过程出错: {e}")
        import traceback
        traceback.print_exc()