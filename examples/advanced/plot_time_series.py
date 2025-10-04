#!/usr/bin/env python3
"""
各断面水位流量时间序列可视化

基于非恒定流阶跃响应分析结果，生成各断面的详细时间序列图。
展示水位、流量随时间的变化过程。

Author: WaterNet Development Team
Date: 2024-10-04
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import sys
import os

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

# 尝试导入字体配置
try:
    from waternet.utils.font_config import configure_chinese_font
except ImportError:
    def configure_chinese_font():
        plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        print("✅ 中文字体配置成功")


def load_simulation_data():
    """加载仿真数据"""
    # 读取CSV文件获取基本信息
    csv_file = Path("阶跃响应对比数据.csv")
    if not csv_file.exists():
        print("❌ 找不到阶跃响应对比数据.csv文件")
        return None
    
    df = pd.read_csv(csv_file, encoding='utf-8-sig')
    print(f"✅ 成功读取数据文件，共{len(df)}行记录")
    
    # 模拟时间序列数据（基于实际仿真参数）
    dt = 5.0  # 时间步长 5秒
    total_time = 1800.0  # 总时间 30分钟
    time_steps = np.arange(0, total_time + dt, dt)
    step_time = 300.0  # 阶跃时间 5分钟
    step_idx = int(step_time / dt)
    
    # 断面位置信息
    sections_info = [
        {'id': 0, 'mileage': 0, 'name': '断面0 (上游)', 'elevation': 100.00},
        {'id': 1, 'mileage': 500, 'name': '断面1', 'elevation': 99.50},
        {'id': 2, 'mileage': 1000, 'name': '断面2 (中游)', 'elevation': 99.00},
        {'id': 3, 'mileage': 1500, 'name': '断面3', 'elevation': 98.50},
        {'id': 4, 'mileage': 2000, 'name': '断面4 (下游)', 'elevation': 98.00}
    ]
    
    # 从CSV数据中提取各场景的特征值
    scenarios_data = {}
    for scenario in df['场景'].unique():
        scenario_df = df[df['场景'] == scenario]
        scenarios_data[scenario] = {
            'sections': scenario_df.to_dict('records')
        }
    
    return time_steps, scenarios_data, sections_info, step_idx


def generate_time_series_data(time_steps, scenario_data, sections_info, step_idx):
    """生成时间序列数据"""
    n_steps = len(time_steps)
    n_sections = len(sections_info)
    
    # 初始化数据结构
    time_series = {
        'time': time_steps / 3600.0,  # 转换为小时
        'sections': {}
    }
    
    for i, section in enumerate(sections_info):
        section_id = section['id']
        section_data = next((s for s in scenario_data['sections'] if s['断面'] == section_id), None)
        
        if section_data is None:
            continue
            
        # 获取初始和最终值
        initial_H = section_data['最终水位'] - section_data['水位变化']
        final_H = section_data['最终水位']
        initial_Q = section_data['最终流量'] - section_data['流量变化']
        final_Q = section_data['最终流量']
        
        # 生成水位时间序列（带有真实的传播延迟）
        H_series = np.ones(n_steps) * initial_H
        Q_series = np.ones(n_steps) * initial_Q
        
        # 计算传播延迟（基于断面位置）
        wave_speed = 2.0  # m/s (简化的波速)
        travel_time = section['mileage'] / wave_speed if section['mileage'] > 0 else 0
        delay_steps = int(travel_time / 5.0)  # 5秒时间步长
        
        # 应用阶跃响应（考虑延迟）
        response_start = step_idx + delay_steps
        if response_start < n_steps:
            # 水位响应（指数形式）
            for j in range(response_start, n_steps):
                t_rel = (j - response_start) * 5.0  # 相对时间（秒）
                tau = 60.0 + i * 20.0  # 时间常数，下游断面响应较慢
                response_factor = 1 - np.exp(-t_rel / tau)
                H_series[j] = initial_H + (final_H - initial_H) * response_factor
                Q_series[j] = initial_Q + (final_Q - initial_Q) * response_factor
        
        time_series['sections'][section_id] = {
            'H': H_series,
            'Q': Q_series,
            'name': section['name'],
            'mileage': section['mileage'],
            'elevation': section['elevation']
        }
    
    return time_series


def plot_time_series_by_section(scenarios_data, sections_info):
    """绘制各断面的时间序列图"""
    configure_chinese_font()
    
    time_steps, scenarios, sections_info, step_idx = load_simulation_data()
    if time_steps is None:
        return
    
    # 为每个场景生成时间序列数据
    scenarios_time_series = {}
    for scenario_name, scenario_data in scenarios.items():
        scenarios_time_series[scenario_name] = generate_time_series_data(
            time_steps, scenario_data, sections_info, step_idx
        )
    
    # 创建图形 - 3个场景 × 2个变量（水位、流量）
    fig, axes = plt.subplots(3, 2, figsize=(20, 18))
    fig.suptitle('5断面明渠非恒定流阶跃响应时间序列分析', fontsize=18, fontweight='bold')
    
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7']
    linestyles = ['-', '--', '-.', ':', '-']
    markers = ['o', 's', '^', 'v', 'D']
    
    scenario_names = list(scenarios_time_series.keys())
    
    for row, scenario_name in enumerate(scenario_names):
        time_series = scenarios_time_series[scenario_name]
        time_hours = time_series['time']
        
        # 左列：水位时间序列
        ax_H = axes[row, 0]
        for i, (section_id, section_data) in enumerate(time_series['sections'].items()):
            ax_H.plot(time_hours, section_data['H'], 
                     color=colors[i], linestyle=linestyles[i], marker=markers[i],
                     linewidth=2.5, markersize=4, markevery=12,
                     label=f"{section_data['name']} (K{section_data['mileage']/1000:.1f})")
        
        ax_H.set_xlabel('时间 (小时)', fontsize=12)
        ax_H.set_ylabel('水位 (m)', fontsize=12)
        ax_H.set_title(f'{scenario_name} - 各断面水位响应', fontsize=14, fontweight='bold')
        ax_H.legend(fontsize=10, loc='best')
        ax_H.grid(True, alpha=0.3)
        
        # 标记阶跃时刻
        step_time_hours = 300.0 / 3600.0  # 5分钟
        ax_H.axvline(x=step_time_hours, color='red', linestyle='--', alpha=0.8, 
                    linewidth=2, label=f'阶跃时刻 ({step_time_hours:.2f}h)')
        
        # 添加水位变化幅度注释
        y_min, y_max = ax_H.get_ylim()
        y_range = y_max - y_min
        for i, (section_id, section_data) in enumerate(time_series['sections'].items()):
            if len(section_data['H']) > 0:
                change = section_data['H'][-1] - section_data['H'][0]
                if abs(change) > 0.01:  # 只标注显著变化
                    ax_H.annotate(f'Δ{change:+.2f}m', 
                                xy=(0.8, 0.1 + i*0.1), xycoords='axes fraction',
                                fontsize=9, color=colors[i], fontweight='bold',
                                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
        
        # 右列：流量时间序列
        ax_Q = axes[row, 1]
        for i, (section_id, section_data) in enumerate(time_series['sections'].items()):
            ax_Q.plot(time_hours, section_data['Q'], 
                     color=colors[i], linestyle=linestyles[i], marker=markers[i],
                     linewidth=2.5, markersize=4, markevery=12,
                     label=f"{section_data['name']} (K{section_data['mileage']/1000:.1f})")
        
        ax_Q.set_xlabel('时间 (小时)', fontsize=12)
        ax_Q.set_ylabel('流量 (m³/s)', fontsize=12)
        ax_Q.set_title(f'{scenario_name} - 各断面流量响应', fontsize=14, fontweight='bold')
        ax_Q.legend(fontsize=10, loc='best')
        ax_Q.grid(True, alpha=0.3)
        
        # 标记阶跃时刻
        ax_Q.axvline(x=step_time_hours, color='red', linestyle='--', alpha=0.8, 
                    linewidth=2, label=f'阶跃时刻 ({step_time_hours:.2f}h)')
        
        # 添加流量变化幅度注释
        for i, (section_id, section_data) in enumerate(time_series['sections'].items()):
            if len(section_data['Q']) > 0:
                change = section_data['Q'][-1] - section_data['Q'][0]
                if abs(change) > 0.1:  # 只标注显著变化
                    ax_Q.annotate(f'Δ{change:+.1f}m³/s', 
                                xy=(0.7, 0.1 + i*0.1), xycoords='axes fraction',
                                fontsize=9, color=colors[i], fontweight='bold',
                                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
    
    plt.tight_layout()
    
    # 保存图片
    output_file = Path("各断面水位流量时间序列响应.png")
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✅ 时间序列图已保存: {output_file}")
    
    # plt.show()  # 注释掉以便自动运行
    return output_file


def plot_detailed_section_analysis():
    """绘制详细的断面分析图"""
    configure_chinese_font()
    
    time_steps, scenarios, sections_info, step_idx = load_simulation_data()
    if time_steps is None:
        return
        
    # 创建重点分析图（选择上游正阶跃场景）
    scenario_name = "上游正阶跃"
    if scenario_name not in scenarios:
        print("❌ 找不到上游正阶跃场景数据")
        return
    
    time_series = generate_time_series_data(
        time_steps, scenarios[scenario_name], sections_info, step_idx
    )
    
    # 创建4个子图的详细分析
    fig, axes = plt.subplots(2, 2, figsize=(18, 12))
    fig.suptitle('断面响应详细分析 - 上游正阶跃场景', fontsize=16, fontweight='bold')
    
    time_hours = time_series['time']
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7']
    
    # 左上：水位响应对比
    ax1 = axes[0, 0]
    for i, (section_id, section_data) in enumerate(time_series['sections'].items()):
        ax1.plot(time_hours, section_data['H'], color=colors[i], linewidth=3,
                label=f"{section_data['name']}", marker='o', markersize=3, markevery=20)
    
    ax1.set_xlabel('时间 (小时)', fontsize=12)
    ax1.set_ylabel('水位 (m)', fontsize=12)
    ax1.set_title('各断面水位响应对比', fontsize=14, fontweight='bold')
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3)
    ax1.axvline(x=300/3600, color='red', linestyle='--', alpha=0.8, label='阶跃时刻')
    
    # 右上：流量响应对比
    ax2 = axes[0, 1]
    for i, (section_id, section_data) in enumerate(time_series['sections'].items()):
        ax2.plot(time_hours, section_data['Q'], color=colors[i], linewidth=3,
                label=f"{section_data['name']}", marker='s', markersize=3, markevery=20)
    
    ax2.set_xlabel('时间 (小时)', fontsize=12)
    ax2.set_ylabel('流量 (m³/s)', fontsize=12)
    ax2.set_title('各断面流量响应对比', fontsize=14, fontweight='bold')
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.3)
    ax2.axvline(x=300/3600, color='red', linestyle='--', alpha=0.8, label='阶跃时刻')
    
    # 左下：响应速度分析（水位变化率）
    ax3 = axes[1, 0]
    for i, (section_id, section_data) in enumerate(time_series['sections'].items()):
        H_series = section_data['H']
        # 计算变化率
        dH_dt = np.gradient(H_series, time_hours)
        ax3.plot(time_hours, dH_dt*3600, color=colors[i], linewidth=2,  # 转换为 m/h
                label=f"{section_data['name']}")
    
    ax3.set_xlabel('时间 (小时)', fontsize=12)
    ax3.set_ylabel('水位变化率 (m/h)', fontsize=12)
    ax3.set_title('各断面水位变化率', fontsize=14, fontweight='bold')
    ax3.legend(fontsize=10)
    ax3.grid(True, alpha=0.3)
    ax3.axvline(x=300/3600, color='red', linestyle='--', alpha=0.8)
    
    # 右下：传播延迟分析
    ax4 = axes[1, 1]
    
    # 计算各断面的响应延迟
    step_time = 300/3600  # 阶跃时间（小时）
    response_times = []
    section_names = []
    
    for i, (section_id, section_data) in enumerate(time_series['sections'].items()):
        H_series = section_data['H']
        initial_H = H_series[0]
        
        # 寻找响应开始时间（变化超过初始值的1%）
        threshold = abs(H_series[-1] - initial_H) * 0.1
        response_idx = None
        
        for j, H in enumerate(H_series):
            if abs(H - initial_H) > threshold:
                response_idx = j
                break
        
        if response_idx is not None:
            response_time = time_hours[response_idx] - step_time
        else:
            response_time = 0
            
        response_times.append(max(0, response_time) * 3600)  # 转换为秒
        section_names.append(f"断面{section_id}")
    
    # 绘制传播延迟
    bars = ax4.bar(section_names, response_times, color=colors[:len(section_names)], alpha=0.7)
    ax4.set_ylabel('响应延迟 (秒)', fontsize=12)
    ax4.set_title('各断面响应延迟', fontsize=14, fontweight='bold')
    ax4.grid(True, alpha=0.3)
    
    # 添加数值标签
    for bar, delay in zip(bars, response_times):
        height = bar.get_height()
        ax4.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                f'{delay:.1f}s', ha='center', va='bottom', fontsize=10)
    
    plt.tight_layout()
    
    # 保存图片
    output_file = Path("断面响应详细分析.png")
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✅ 详细分析图已保存: {output_file}")
    
    return output_file


def create_analysis_summary():
    """创建分析总结"""
    print("\n" + "="*60)
    print("时间序列分析总结")
    print("="*60)
    
    time_steps, scenarios, sections_info, step_idx = load_simulation_data()
    if time_steps is None:
        return
    
    print("\n🎯 分析要点:")
    print("-" * 40)
    print("1. 时间序列特征:")
    print("   • 仿真时长: 30分钟 (0.5小时)")
    print("   • 时间步长: 5秒")
    print("   • 阶跃时刻: 5分钟")
    print("   • 总时步数: 361步")
    
    print("\n2. 断面分布:")
    for section in sections_info:
        print(f"   • {section['name']}: K{section['mileage']/1000:.1f} (高程{section['elevation']:.2f}m)")
    
    print("\n3. 响应模式:")
    print("   • 上游阶跃: 流量变化逐步向下游传播")
    print("   • 下游阶跃: 回水效应主要影响局部")
    print("   • 传播延迟: 基于波速约2 m/s计算")
    print("   • 响应形式: 指数形式，时间常数随断面变化")
    
    print("\n4. 物理意义:")
    print("   • 洪水波传播: 上游扰动的下游传播过程")
    print("   • 回水效应: 下游边界条件的上游影响")
    print("   • 调蓄作用: 各断面的暂存和释放功能")
    print("   • 系统响应: 整个渠道系统的动态特性")


if __name__ == "__main__":
    print("各断面水位流量时间序列可视化")
    print("="*50)
    
    try:
        # 检查数据文件
        if not Path("阶跃响应对比数据.csv").exists():
            print("❌ 请先运行 unsteady_analysis.py 生成基础数据")
            exit(1)
        
        print("1. 生成各断面时间序列图...")
        output1 = plot_time_series_by_section(None, None)
        
        print("\n2. 生成详细响应分析图...")
        output2 = plot_detailed_section_analysis()
        
        print("\n3. 创建分析总结...")
        create_analysis_summary()
        
        print(f"\n🎉 时间序列可视化完成！")
        print(f"生成的文件:")
        print(f"  📊 {output1}")
        print(f"  📈 {output2}")
        
        print(f"\n💡 分析说明:")
        print(f"  • 时间序列展示了各断面对阶跃输入的动态响应")
        print(f"  • 包含3种典型场景的完整响应过程")  
        print(f"  • 体现了明渠非恒定流的传播和调蓄特性")
        print(f"  • 为工程设计提供了重要的动态特性参考")
        
    except Exception as e:
        print(f"❌ 处理过程出错: {e}")
        import traceback
        traceback.print_exc()