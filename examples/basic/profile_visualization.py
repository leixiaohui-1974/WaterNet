#!/usr/bin/env python3
"""
5断面精细化仿真恒定流法初值估计纵剖面可视化

展示水位、流量沿程分布的详细纵剖面图。

Author: WaterNet Development Team
Date: 2024-10-03
"""

import sys
import os
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入相关模块
from waternet.tests.deep_channel_testing.geometry_config import FiveSectionChannelConfig
from waternet.models.saint_venant import SaintVenantModel
from waternet.utils.font_config import configure_chinese_font

def create_saint_venant_model():
    """创建圣维南模型用于精细化计算"""
    config = FiveSectionChannelConfig()
    sections = config.get_five_section_geometry()
    
    # 转换为圣维南模型所需格式
    sv_sections = []
    for i, section in enumerate(sections):
        sv_section = {
            'mileage': section['mileage'],
            'elevation': section['elevation'],
            'area_func': section['area_func'],
            'top_width_func': section['top_width_func'],
            'hydraulic_radius_func': section['hydraulic_radius_func'],
            'conveyance_func': section['conveyance_func'],
            'roughness': section['roughness']
        }
        sv_sections.append(sv_section)
    
    # 创建圣维南模型
    sv_model = SaintVenantModel(
        name="FiveSectionChannel",
        upstream_node="upstream",
        downstream_node="downstream", 
        sections=sv_sections
    )
    
    return sv_model, config

def compute_detailed_steady_state():
    """计算详细的恒定流状态"""
    sv_model, config = create_saint_venant_model()
    
    # 设置计算条件
    Q_steady = 50.0      # 恒定流量 50 m³/s
    H_downstream = 101.0 # 下游水位 101.0 m
    
    print(f"计算恒定流水面线...")
    print(f"恒定流量: {Q_steady} m³/s")
    print(f"下游边界水位: {H_downstream} m")
    
    # 使用几何配置类计算恒定流水面线
    steady_profile = config.compute_steady_state_profile()
    
    # 使用圣维南模型验证计算
    try:
        sv_result = sv_model.compute_steady_state(Q_steady, H_downstream)
        print(f"✅ 圣维南模型计算成功")
        print(f"   总蓄水量: {sv_result['total_volume']:.0f} m³")
    except Exception as e:
        print(f"⚠️ 圣维南模型计算失败: {e}")
        sv_result = None
    
    # 提取纵剖面数据
    sections_data = steady_profile['sections']
    
    # 计算沿程流量分布（恒定流条件下各断面流量相等）
    flow_data = []
    for section in sections_data:
        flow_data.append({
            'mileage': section['mileage'],
            'flow_rate': Q_steady,  # 恒定流条件
            'velocity': section['velocity'],
            'cross_sectional_area': Q_steady / section['velocity'] if section['velocity'] > 0 else 0
        })
    
    return {
        'water_level_profile': sections_data,
        'flow_profile': flow_data,
        'steady_state_summary': steady_profile,
        'saint_venant_result': sv_result,
        'boundary_conditions': {
            'flow_rate': Q_steady,
            'downstream_level': H_downstream
        }
    }

def plot_longitudinal_profiles(results):
    """绘制详细的纵剖面图"""
    # 配置中文字体
    configure_chinese_font()
    
    water_profile = results['water_level_profile']
    flow_profile = results['flow_profile']
    
    # 提取数据
    mileages = [s['mileage'] for s in water_profile]
    bottom_elevations = [s['bottom_elevation'] for s in water_profile]
    water_levels = [s['water_level'] for s in water_profile]
    depths = [s['depth'] for s in water_profile]
    velocities = [s['velocity'] for s in water_profile]
    flow_rates = [f['flow_rate'] for f in flow_profile]
    areas = [f['cross_sectional_area'] for f in flow_profile]
    
    # 创建图形
    fig = plt.figure(figsize=(16, 12))
    
    # 1. 水位纵剖面图 (主要)
    ax1 = plt.subplot(3, 2, (1, 2))
    ax1.plot(mileages, bottom_elevations, 'k-', linewidth=3, label='河底高程', marker='s', markersize=6)
    ax1.plot(mileages, water_levels, 'b-', linewidth=3, label='水面线', marker='o', markersize=8)
    ax1.fill_between(mileages, bottom_elevations, water_levels, alpha=0.3, color='lightblue', label='水体')
    
    # 标注断面编号和水位
    for i, (x, y) in enumerate(zip(mileages, water_levels)):
        ax1.annotate(f'断面{i}\n{y:.2f}m', 
                    xy=(x, y), xytext=(10, 10), 
                    textcoords='offset points',
                    ha='left', va='bottom',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8),
                    fontsize=9)
    
    ax1.set_xlabel('里程 (m)', fontsize=12, fontweight='bold')
    ax1.set_ylabel('高程 (m)', fontsize=12, fontweight='bold')
    ax1.set_title('5断面明渠恒定流水面线纵剖面', fontsize=14, fontweight='bold')
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim(min(bottom_elevations) - 0.5, max(water_levels) + 1.0)
    
    # 2. 水深分布
    ax2 = plt.subplot(3, 2, 3)
    ax2.plot(mileages, depths, 'g-', linewidth=2, marker='o', markersize=6)
    ax2.set_xlabel('里程 (m)', fontsize=10)
    ax2.set_ylabel('水深 (m)', fontsize=10)
    ax2.set_title('水深沿程分布', fontsize=11, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    
    # 标注数值
    for i, (x, y) in enumerate(zip(mileages, depths)):
        ax2.annotate(f'{y:.2f}m', xy=(x, y), xytext=(0, 10), 
                    textcoords='offset points', ha='center', va='bottom', fontsize=8)
    
    # 3. 流速分布
    ax3 = plt.subplot(3, 2, 4)
    ax3.plot(mileages, velocities, 'r-', linewidth=2, marker='s', markersize=6)
    ax3.set_xlabel('里程 (m)', fontsize=10)
    ax3.set_ylabel('流速 (m/s)', fontsize=10)
    ax3.set_title('流速沿程分布', fontsize=11, fontweight='bold')
    ax3.grid(True, alpha=0.3)
    
    # 标注数值
    for i, (x, y) in enumerate(zip(mileages, velocities)):
        ax3.annotate(f'{y:.2f}m/s', xy=(x, y), xytext=(0, 10), 
                    textcoords='offset points', ha='center', va='bottom', fontsize=8)
    
    # 4. 流量分布 (恒定流)
    ax4 = plt.subplot(3, 2, 5)
    ax4.plot(mileages, flow_rates, 'purple', linewidth=2, marker='^', markersize=6)
    ax4.set_xlabel('里程 (m)', fontsize=10)
    ax4.set_ylabel('流量 (m³/s)', fontsize=10)
    ax4.set_title('流量沿程分布', fontsize=11, fontweight='bold')
    ax4.grid(True, alpha=0.3)
    ax4.set_ylim([min(flow_rates) - 1, max(flow_rates) + 1])
    
    # 添加水平参考线
    ax4.axhline(y=flow_rates[0], color='purple', linestyle='--', alpha=0.7, 
               label=f'恒定流量 = {flow_rates[0]:.1f} m³/s')
    ax4.legend()
    
    # 5. 过水断面面积
    ax5 = plt.subplot(3, 2, 6)
    ax5.plot(mileages, areas, 'orange', linewidth=2, marker='d', markersize=6)
    ax5.set_xlabel('里程 (m)', fontsize=10)
    ax5.set_ylabel('过水面积 (m²)', fontsize=10)
    ax5.set_title('过水断面面积沿程分布', fontsize=11, fontweight='bold')
    ax5.grid(True, alpha=0.3)
    
    # 标注数值
    for i, (x, y) in enumerate(zip(mileages, areas)):
        ax5.annotate(f'{y:.1f}m²', xy=(x, y), xytext=(0, 10), 
                    textcoords='offset points', ha='center', va='bottom', fontsize=8)
    
    plt.tight_layout()
    
    # 保存图片
    output_dir = Path(__file__).parent
    output_file = output_dir / '5断面恒定流纵剖面分析.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✅ 纵剖面图已保存: {output_file}")
    
    plt.show()

def print_detailed_results(results):
    """打印详细的计算结果"""
    print("\n" + "="*80)
    print("5断面精细化仿真恒定流法初值估计详细结果")
    print("="*80)
    
    # 边界条件
    bc = results['boundary_conditions']
    print(f"\n边界条件:")
    print(f"  恒定流量: {bc['flow_rate']} m³/s")
    print(f"  下游水位: {bc['downstream_level']} m")
    
    # 水位纵剖面详情
    print(f"\n水位纵剖面详情:")
    print("-" * 90)
    print(f"{'断面':>4} {'里程':>8} {'河底高程':>10} {'水位':>8} {'水深':>8} {'流速':>8} {'弗劳德数':>8} {'过水面积':>10}")
    print(f"{'':>4} {'(m)':>8} {'(m)':>10} {'(m)':>8} {'(m)':>8} {'(m/s)':>8} {'':>8} {'(m²)':>10}")
    print("-" * 90)
    
    water_profile = results['water_level_profile']
    flow_profile = results['flow_profile']
    
    for i, (wp, fp) in enumerate(zip(water_profile, flow_profile)):
        print(f"{i:>4} {wp['mileage']:>8.0f} {wp['bottom_elevation']:>10.2f} "
              f"{wp['water_level']:>8.2f} {wp['depth']:>8.2f} {wp['velocity']:>8.2f} "
              f"{wp['froude_number']:>8.3f} {fp['cross_sectional_area']:>10.1f}")
    
    # 整体统计
    summary = results['steady_state_summary']
    print(f"\n整体水力特性:")
    print("-" * 50)
    print(f"总蓄水量:     {summary['total_volume']:>12,.0f} m³")
    print(f"平均流速:     {summary['average_velocity']:>12.2f} m/s")
    print(f"最大弗劳德数: {summary['max_froude_number']:>12.3f}")
    print(f"总水头损失:   {summary['energy_loss']:>12.3f} m")
    
    # 物理验证
    validation = summary['validation']
    print(f"\n物理合理性验证:")
    print("-" * 40)
    checks = {
        'monotonic_water_surface': '水面线单调性',
        'subcritical_flow': '亚临界流态',
        'reasonable_velocities': '流速合理性',
        'total_volume_check': '蓄水量检查'
    }
    
    for key, desc in checks.items():
        status = "✅ 通过" if validation.get(key, False) else "❌ 失败"
        print(f"  {desc:12}: {status}")
    
    # 圣维南模型对比
    if results['saint_venant_result']:
        sv_result = results['saint_venant_result']
        print(f"\n圣维南模型验证:")
        print(f"  几何配置法蓄水量: {summary['total_volume']:>10.0f} m³")
        print(f"  圣维南模型蓄水量: {sv_result['total_volume']:>10.0f} m³")
        diff = abs(summary['total_volume'] - sv_result['total_volume'])
        print(f"  蓄水量差异:       {diff:>10.0f} m³ ({diff/summary['total_volume']*100:.1f}%)")

def main():
    """主函数"""
    print("5断面精细化仿真恒定流法初值估计纵剖面分析")
    print(f"="*60)
    
    try:
        # 计算恒定流状态
        results = compute_detailed_steady_state()
        
        # 打印详细结果
        print_detailed_results(results)
        
        # 绘制纵剖面图
        plot_longitudinal_profiles(results)
        
        print(f"\n🎉 恒定流纵剖面分析完成！")
        
    except Exception as e:
        print(f"❌ 分析过程出现错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())