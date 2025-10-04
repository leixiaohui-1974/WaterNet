"""
直观的水力系统图表展示

提供清晰易懂的系统拓扑图和文本描述，方便理解水力网络结构。

Author: WaterNet Development Team  
Date: 2024-10-04
"""

import sys
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Circle, Rectangle, Polygon
import matplotlib.lines as mlines

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

# 添加WaterNet到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from waternet.models import (
    ReservoirModel, JunctionModel, ComplexStationModel, PressurizedPipeModel
)


def print_system_text_diagram(models, results):
    """打印文本形式的系统图"""
    print("\n" + "="*80)
    print("复杂水力枢纽系统拓扑结构图 (文本版)")
    print("="*80)
    
    # 系统流程描述
    print("""
    [上游水库] ──→ [主控闸站] ──→ [分流枢纽] ──┬──→ [输水干管] ──→ [下游调节池]
         ↑              ↓              │                    ↓
    入库流量        控制流量        └──→ [泄洪渠道] ──→   出库流量
                                         ↓
                                   泄洪口出流
    """)
    
    print("\n组件详细信息:")
    print("-" * 80)
    
    # 按类型分组显示组件
    reservoirs = [m for m in models if isinstance(m, ReservoirModel)]
    stations = [m for m in models if isinstance(m, ComplexStationModel)]
    junctions = [m for m in models if isinstance(m, JunctionModel)]
    pipes = [m for m in models if isinstance(m, PressurizedPipeModel)]
    
    # 显示水库信息
    if reservoirs:
        print("🏞️  水库系统:")
        for res in reservoirs:
            level = results.get(f'H_{res.name}', 0)
            print(f"   • {res.name}: 水位 {level:.1f}m")
            if hasattr(res, 'surface_area'):
                print(f"     - 水面面积: {res.surface_area/1000000:.1f}万m²")
    
    # 显示枢纽站信息
    if stations:
        print("\n🏗️  枢纽站系统:")
        for station in stations:
            print(f"   • {station.name}:")
            print(f"     - 上游节点: {station.upstream_node}")
            print(f"     - 下游节点: {station.downstream_node}")
            for struct_name in station.structures.keys():
                flow = results.get(f'Q_{struct_name}', 0)
                print(f"     - {struct_name}: 流量 {flow:.1f}m³/s")
    
    # 显示连接点信息
    if junctions:
        print("\n🔀  连接点系统:")
        for junction in junctions:
            level = results.get(f'H_{junction.name}', 0)
            print(f"   • {junction.name}: 水位 {level:.1f}m")
            print(f"     - 连接对象: {', '.join(junction.connected_objects)}")
    
    # 显示管道信息
    if pipes:
        print("\n🚰  管道系统:")
        for pipe in pipes:
            flow = results.get(f'Q_{pipe.name}', 0)
            velocity = abs(flow) / pipe.area if pipe.area > 0 else 0
            print(f"   • {pipe.name}:")
            print(f"     - 长度: {pipe.length:.0f}m, 直径: {pipe.diameter:.1f}m")
            print(f"     - 流量: {flow:.1f}m³/s, 流速: {velocity:.2f}m/s")
            print(f"     - 上游: {pipe.upstream_node} → 下游: {pipe.downstream_node}")
    
    print("\n" + "="*80)


def create_intuitive_topology_diagram(models, results, save_path="直观系统拓扑图.png"):
    """创建直观的拓扑图"""
    fig, ax = plt.subplots(1, 1, figsize=(16, 10))
    
    # 设置画布
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 10)
    ax.set_aspect('equal')
    ax.axis('off')
    
    # 定义颜色
    colors = {
        'water': '#4FC3F7',
        'structure': '#FF7043', 
        'pipe': '#66BB6A',
        'junction': '#FFD54F',
        'flow': '#E91E63'
    }
    
    # 1. 绘制上游水库 (左侧)
    reservoir_x, reservoir_y = 2, 7
    
    # 水库主体
    reservoir_body = Rectangle((reservoir_x-1, reservoir_y-1), 2, 2, 
                              facecolor=colors['water'], alpha=0.7, edgecolor='black')
    ax.add_patch(reservoir_body)
    
    # 水库标签和数据
    ax.text(reservoir_x, reservoir_y+1.5, '上游水库', ha='center', fontsize=12, fontweight='bold')
    upstream_level = results.get('H_上游水库', 110)
    ax.text(reservoir_x, reservoir_y-0.3, f'水位: {upstream_level:.1f}m', ha='center', fontsize=10)
    
    # 入库流量箭头
    inflow = results.get('Q_入库流量', 0)
    ax.arrow(reservoir_x-2, reservoir_y, 0.8, 0, head_width=0.2, head_length=0.1, 
             fc=colors['flow'], ec=colors['flow'])
    ax.text(reservoir_x-2.5, reservoir_y+0.3, f'入库\n{inflow:.1f}m³/s', ha='center', fontsize=9)
    
    # 2. 绘制主控闸站 (中左)
    gate_x, gate_y = 5, 7
    
    # 闸站结构
    gate_structure = FancyBboxPatch((gate_x-0.8, gate_y-0.5), 1.6, 1, 
                                   boxstyle="round,pad=0.1",
                                   facecolor=colors['structure'], alpha=0.7, edgecolor='black')
    ax.add_patch(gate_structure)
    
    ax.text(gate_x, gate_y+0.8, '主控闸站', ha='center', fontsize=12, fontweight='bold')
    gate_flow = results.get('Q_主控闸门', 0)
    ax.text(gate_x, gate_y-0.1, f'闸门流量\n{gate_flow:.1f}m³/s', ha='center', fontsize=10)
    
    # 水库到闸站的连接
    ax.arrow(reservoir_x+1, reservoir_y, gate_x-reservoir_x-1.8, 0, 
             head_width=0.15, head_length=0.1, fc='blue', ec='blue', linewidth=2)
    
    # 3. 绘制分流枢纽 (中心)
    junction_x, junction_y = 8, 7
    
    # 分流点
    junction_circle = Circle((junction_x, junction_y), 0.5, 
                           facecolor=colors['junction'], alpha=0.7, edgecolor='black')
    ax.add_patch(junction_circle)
    
    ax.text(junction_x, junction_y+1, '分流枢纽', ha='center', fontsize=12, fontweight='bold')
    junction_level = results.get('H_分流枢纽', 0)
    ax.text(junction_x, junction_y-0.8, f'水位: {junction_level:.1f}m', ha='center', fontsize=10)
    
    # 闸站到分流点的连接
    ax.arrow(gate_x+0.8, gate_y, junction_x-gate_x-1.3, 0,
             head_width=0.15, head_length=0.1, fc='blue', ec='blue', linewidth=2)
    
    # 4. 绘制输水干管 (中右上)
    pipe1_start_x, pipe1_start_y = junction_x+0.5, junction_y+0.3
    pipe1_end_x, pipe1_end_y = 12, 8
    
    # 输水干管
    ax.plot([pipe1_start_x, pipe1_end_x], [pipe1_start_y, pipe1_end_y], 
            color=colors['pipe'], linewidth=8, alpha=0.7)
    ax.arrow(pipe1_start_x+0.5, pipe1_start_y+0.1, 2, 0.4, 
             head_width=0.15, head_length=0.1, fc=colors['flow'], ec=colors['flow'])
    
    # 管道标签
    pipe1_mid_x = (pipe1_start_x + pipe1_end_x) / 2
    pipe1_mid_y = (pipe1_start_y + pipe1_end_y) / 2
    ax.text(pipe1_mid_x, pipe1_mid_y+0.5, '输水干管', ha='center', fontsize=11, fontweight='bold')
    
    main_flow = results.get('Q_输水干管', 0)
    main_velocity = main_flow / (np.pi * (2.2/2)**2) if main_flow > 0 else 0
    ax.text(pipe1_mid_x, pipe1_mid_y-0.3, f'{main_flow:.1f}m³/s\n{main_velocity:.1f}m/s', 
            ha='center', fontsize=9)
    
    # 5. 绘制泄洪渠道 (中右下)
    pipe2_start_x, pipe2_start_y = junction_x+0.3, junction_y-0.5
    pipe2_end_x, pipe2_end_y = 12, 5
    
    # 泄洪渠道
    ax.plot([pipe2_start_x, pipe2_end_x], [pipe2_start_y, pipe2_end_y], 
            color=colors['pipe'], linewidth=8, alpha=0.7)
    ax.arrow(pipe2_start_x+0.5, pipe2_start_y-0.1, 2, -1.2, 
             head_width=0.15, head_length=0.1, fc=colors['flow'], ec=colors['flow'])
    
    # 管道标签
    pipe2_mid_x = (pipe2_start_x + pipe2_end_x) / 2
    pipe2_mid_y = (pipe2_start_y + pipe2_end_y) / 2
    ax.text(pipe2_mid_x, pipe2_mid_y-0.5, '泄洪渠道', ha='center', fontsize=11, fontweight='bold')
    
    spillway_flow = results.get('Q_泄洪渠道', 0)
    spillway_velocity = spillway_flow / (np.pi * (3.0/2)**2) if spillway_flow > 0 else 0
    ax.text(pipe2_mid_x, pipe2_mid_y+0.3, f'{spillway_flow:.1f}m³/s\n{spillway_velocity:.1f}m/s', 
            ha='center', fontsize=9)
    
    # 6. 绘制下游调节池 (右侧)
    downstream_x, downstream_y = 14, 8
    
    # 调节池
    downstream_body = Rectangle((downstream_x-0.8, downstream_y-0.8), 1.6, 1.6, 
                               facecolor=colors['water'], alpha=0.7, edgecolor='black')
    ax.add_patch(downstream_body)
    
    ax.text(downstream_x, downstream_y+1.2, '下游调节池', ha='center', fontsize=12, fontweight='bold')
    downstream_level = results.get('H_下游调节池', 92)
    ax.text(downstream_x, downstream_y-0.3, f'水位: {downstream_level:.1f}m', ha='center', fontsize=10)
    
    # 输水干管到调节池的连接
    ax.arrow(pipe1_end_x, pipe1_end_y, downstream_x-pipe1_end_x-0.8, downstream_y-pipe1_end_y,
             head_width=0.15, head_length=0.1, fc='blue', ec='blue', linewidth=2)
    
    # 出库流量箭头
    outflow = results.get('Q_调节池出口', 0)
    ax.arrow(downstream_x+0.8, downstream_y, 0.8, 0, head_width=0.2, head_length=0.1, 
             fc=colors['flow'], ec=colors['flow'])
    ax.text(downstream_x+1.5, downstream_y+0.3, f'出库\n{abs(outflow):.1f}m³/s', ha='center', fontsize=9)
    
    # 7. 绘制泄洪出口
    spillway_outlet_x, spillway_outlet_y = 14, 5
    
    # 泄洪出口
    outlet_triangle = Polygon([(spillway_outlet_x-0.3, spillway_outlet_y-0.3), 
                              (spillway_outlet_x+0.3, spillway_outlet_y-0.3),
                              (spillway_outlet_x, spillway_outlet_y+0.3)],
                             facecolor=colors['structure'], alpha=0.7, edgecolor='black')
    ax.add_patch(outlet_triangle)
    
    ax.text(spillway_outlet_x, spillway_outlet_y-0.8, '泄洪出口', ha='center', fontsize=11, fontweight='bold')
    
    # 泄洪渠道到出口的连接
    ax.arrow(pipe2_end_x, pipe2_end_y, spillway_outlet_x-pipe2_end_x-0.3, spillway_outlet_y-pipe2_end_y,
             head_width=0.15, head_length=0.1, fc='blue', ec='blue', linewidth=2)
    
    # 泄洪出流箭头
    spillway_outflow = results.get('Q_泄洪口出流', spillway_flow)
    ax.arrow(spillway_outlet_x+0.3, spillway_outlet_y, 0.8, 0, head_width=0.2, head_length=0.1, 
             fc=colors['flow'], ec=colors['flow'])
    ax.text(spillway_outlet_x+1.3, spillway_outlet_y+0.3, f'泄洪\n{abs(spillway_outflow):.1f}m³/s', 
            ha='center', fontsize=9)
    
    # 8. 添加水位高程线
    # 绘制水位线参考
    water_levels = [
        (reservoir_x, upstream_level, '上游'),
        (junction_x, junction_level, '分流点'),
        (downstream_x, downstream_level, '下游')
    ]
    
    # 水位参考线
    for i, (x, level, label) in enumerate(water_levels):
        y_pos = 2 + i * 0.5  # 底部位置
        ax.plot([x-0.5, x+0.5], [y_pos, y_pos], 'k-', linewidth=2)
        ax.text(x, y_pos-0.3, f'{label}\n{level:.1f}m', ha='center', fontsize=9)
    
    # 9. 添加图例
    legend_elements = [
        patches.Patch(color=colors['water'], label='水库/调节池'),
        patches.Patch(color=colors['structure'], label='控制结构'),
        patches.Patch(color=colors['pipe'], label='输水管道'),
        patches.Patch(color=colors['junction'], label='分流枢纽'),
        mlines.Line2D([], [], color='blue', linewidth=2, label='水流方向')
    ]
    
    ax.legend(handles=legend_elements, loc='upper left', fontsize=10)
    
    # 10. 添加标题和说明
    ax.text(8, 9.5, '复杂水力枢纽系统拓扑图', ha='center', fontsize=16, fontweight='bold')
    ax.text(8, 0.5, '系统特点: 一库入流 → 闸门控制 → 分流枢纽 → 双路出流 (输水+泄洪)', 
            ha='center', fontsize=12, style='italic')
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.show()
    
    return fig


def create_flow_balance_diagram(models, results, save_path="流量平衡图.png"):
    """创建流量平衡分析图"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
    
    # 左图：系统流量桑基图概念
    ax1.set_xlim(0, 10)
    ax1.set_ylim(0, 10)
    ax1.set_title('系统流量分配图', fontsize=14, fontweight='bold')
    
    # 获取流量数据
    inflow = results.get('Q_入库流量', 0)
    gate_flow = results.get('Q_主控闸门', 0)
    main_flow = results.get('Q_输水干管', 0)
    spillway_flow = results.get('Q_泄洪渠道', 0)
    main_outflow = abs(results.get('Q_调节池出口', 0))
    spillway_outflow = abs(results.get('Q_泄洪口出流', spillway_flow))
    
    # 绘制流量条
    y_levels = [8, 6, 4, 2]
    flow_data = [
        ('系统入流', inflow, 'green'),
        ('闸门流量', gate_flow, 'blue'),
        ('输水干管', main_flow, 'orange'),
        ('泄洪渠道', spillway_flow, 'red')
    ]
    
    max_flow = max([inflow, gate_flow, main_flow, spillway_flow]) if any([inflow, gate_flow, main_flow, spillway_flow]) else 1
    
    for i, (label, flow, color) in enumerate(flow_data):
        width = (flow / max_flow) * 6  # 按比例缩放宽度
        rect = Rectangle((2, y_levels[i]-0.2), width, 0.4, 
                        facecolor=color, alpha=0.7, edgecolor='black')
        ax1.add_patch(rect)
        ax1.text(1.5, y_levels[i], label, ha='right', va='center', fontsize=10, fontweight='bold')
        ax1.text(2+width+0.1, y_levels[i], f'{flow:.1f}m³/s', ha='left', va='center', fontsize=10)
    
    ax1.set_xlim(0, 10)
    ax1.axis('off')
    
    # 右图：质量守恒验证
    ax2.set_title('质量守恒验证', fontsize=14, fontweight='bold')
    
    # 计算平衡
    total_inflow = inflow
    total_outflow = main_outflow + spillway_outflow
    balance_error = total_inflow - total_outflow
    
    categories = ['总入流', '总出流', '平衡误差']
    values = [total_inflow, total_outflow, abs(balance_error)]
    colors_balance = ['green', 'red', 'orange']
    
    bars = ax2.bar(categories, values, color=colors_balance, alpha=0.7)
    
    # 添加数值标签
    for bar, value in zip(bars, values):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + max(values)*0.01,
                f'{value:.2f}m³/s', ha='center', va='bottom', fontsize=11, fontweight='bold')
    
    ax2.set_ylabel('流量 (m³/s)')
    ax2.grid(True, alpha=0.3)
    
    # 添加平衡状态文字
    if abs(balance_error) < 0.1:
        status_text = "✅ 质量守恒: 满足"
        status_color = 'green'
    else:
        status_text = "⚠️ 质量守恒: 需检查"
        status_color = 'red'
    
    ax2.text(1, max(values)*0.9, status_text, ha='center', fontsize=12, 
             fontweight='bold', color=status_color,
             bbox=dict(boxstyle="round,pad=0.3", facecolor='white', edgecolor=status_color))
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.show()
    
    return fig


def demonstrate_intuitive_visualization():
    """演示直观的可视化"""
    print("创建直观的水力系统可视化...")
    
    # 使用修正系统的数据
    from corrected_hydraulic_system import create_physically_correct_system, calculate_physically_correct_results
    
    # 获取系统和结果
    models = create_physically_correct_system()
    results = calculate_physically_correct_results(models)
    
    # 1. 打印文本图
    print_system_text_diagram(models, results)
    
    # 2. 创建直观拓扑图
    print("\n正在生成直观拓扑图...")
    topo_fig = create_intuitive_topology_diagram(models, results)
    
    # 3. 创建流量平衡图
    print("正在生成流量平衡图...")
    balance_fig = create_flow_balance_diagram(models, results)
    
    print("\n✅ 直观可视化完成!")
    print("生成的图表:")
    print("1. 直观系统拓扑图.png - 清晰的系统结构图")
    print("2. 流量平衡图.png - 质量守恒验证图")
    print("3. 控制台文本图 - 详细的组件信息")
    
    return topo_fig, balance_fig


if __name__ == '__main__':
    demonstrate_intuitive_visualization()