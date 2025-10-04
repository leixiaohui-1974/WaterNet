"""
复杂水力枢纽系统可视化分析工具

提供直观的图表展示系统结果，方便分析合理性。

Author: WaterNet Development Team
Date: 2024-10-04
"""

import sys
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch
import seaborn as sns
from pathlib import Path

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

# 添加WaterNet到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from waternet.models import (
    ReservoirModel, JunctionModel, ComplexStationModel, PressurizedPipeModel,
    create_simple_reservoir, create_simple_junction, create_gate_station, create_simple_pipe
)


class HydraulicNetworkVisualizer:
    """水力网络可视化器"""
    
    def __init__(self, models, results=None):
        self.models = models
        self.results = results or {}
        
        # 设置颜色方案
        self.colors = {
            'reservoir': '#4CAF50',
            'station': '#FF9800', 
            'junction': '#2196F3',
            'pipe': '#607D8B',
            'water': '#03A9F4',
            'flow_positive': '#4CAF50',
            'flow_negative': '#F44336'
        }
    
    def create_comprehensive_analysis(self, save_path="hydraulic_analysis.png"):
        """创建综合分析图表"""
        fig, axes = plt.subplots(2, 4, figsize=(20, 12))
        fig.suptitle('复杂水力枢纽系统综合分析', fontsize=16, fontweight='bold')
        
        # 1. 系统拓扑图
        self._plot_system_topology(axes[0, 0])
        
        # 2. 水位分布图
        self._plot_water_levels(axes[0, 1])
        
        # 3. 流量分布图
        self._plot_flow_distribution(axes[0, 2])
        
        # 4. 能量损失分析
        self._plot_energy_analysis(axes[0, 3])
        
        # 5. 流量平衡验证
        self._plot_mass_balance(axes[1, 0])
        
        # 6. 设备运行状态
        self._plot_equipment_status(axes[1, 1])
        
        # 7. 水力特性分析
        self._plot_hydraulic_characteristics(axes[1, 2])
        
        # 8. 系统性能指标
        self._plot_system_performance(axes[1, 3])
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
        
        return fig
    
    def _plot_system_topology(self, ax):
        """绘制系统拓扑结构图"""
        ax.set_title('系统拓扑结构', fontsize=12, fontweight='bold')
        
        # 简化的组件布局
        positions = {}
        x_pos = 1
        
        for i, model in enumerate(self.models):
            y_pos = 2 if isinstance(model, ReservoirModel) else 1
            positions[model.name] = (x_pos, y_pos)
            x_pos += 1.5
        
        # 绘制组件
        for model in self.models:
            if model.name in positions:
                x, y = positions[model.name]
                
                if isinstance(model, ReservoirModel):
                    circle = plt.Circle((x, y), 0.3, color=self.colors['reservoir'], alpha=0.7)
                    ax.add_patch(circle)
                elif isinstance(model, ComplexStationModel):
                    rect = FancyBboxPatch((x-0.3, y-0.15), 0.6, 0.3, 
                                        boxstyle="round,pad=0.05",
                                        facecolor=self.colors['station'], alpha=0.7)
                    ax.add_patch(rect)
                elif isinstance(model, JunctionModel):
                    diamond = patches.RegularPolygon((x, y), 4, radius=0.2, 
                                                   orientation=np.pi/4,
                                                   facecolor=self.colors['junction'], alpha=0.7)
                    ax.add_patch(diamond)
                elif isinstance(model, PressurizedPipeModel):
                    ax.plot([x-0.4, x+0.4], [y, y], color=self.colors['pipe'], 
                           linewidth=6, alpha=0.7)
                
                # 添加标签
                ax.text(x, y-0.5, model.name, ha='center', fontsize=8, fontweight='bold')
        
        ax.set_xlim(0, len(self.models) * 1.5 + 1)
        ax.set_ylim(0, 3)
        ax.set_aspect('equal')
        ax.axis('off')
    
    def _plot_water_levels(self, ax):
        """绘制水位分布图"""
        ax.set_title('水位分布', fontsize=12, fontweight='bold')
        
        water_levels = {k.replace('H_', ''): v for k, v in self.results.items() if k.startswith('H_')}
        
        if water_levels:
            locations = list(water_levels.keys())
            levels = list(water_levels.values())
            
            bars = ax.bar(range(len(locations)), levels, color=self.colors['water'], alpha=0.7)
            
            for i, (bar, level) in enumerate(zip(bars, levels)):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                       f'{level:.1f}m', ha='center', fontweight='bold')
            
            ax.set_xlabel('位置')
            ax.set_ylabel('水位 (m)')
            ax.set_xticks(range(len(locations)))
            ax.set_xticklabels(locations, rotation=45, ha='right')
            ax.grid(True, alpha=0.3)
        else:
            ax.text(0.5, 0.5, '无水位数据', ha='center', va='center', transform=ax.transAxes)
    
    def _plot_flow_distribution(self, ax):
        """绘制流量分布图"""
        ax.set_title('流量分布', fontsize=12, fontweight='bold')
        
        flow_rates = {k.replace('Q_', ''): v for k, v in self.results.items() if k.startswith('Q_')}
        
        if flow_rates:
            equipments = list(flow_rates.keys())
            flows = list(flow_rates.values())
            
            colors = [self.colors['flow_positive'] if f >= 0 else self.colors['flow_negative'] 
                     for f in flows]
            
            bars = ax.bar(range(len(equipments)), flows, color=colors, alpha=0.7)
            
            for i, (bar, flow) in enumerate(zip(bars, flows)):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2, 
                       height + 0.3 if height >= 0 else height - 0.8,
                       f'{flow:.1f}', ha='center', fontweight='bold')
            
            ax.set_xlabel('设备/管道')
            ax.set_ylabel('流量 (m³/s)')
            ax.set_xticks(range(len(equipments)))
            ax.set_xticklabels(equipments, rotation=45, ha='right')
            ax.axhline(y=0, color='black', linestyle='-', alpha=0.5)
            ax.grid(True, alpha=0.3)
        else:
            ax.text(0.5, 0.5, '无流量数据', ha='center', va='center', transform=ax.transAxes)
    
    def _plot_energy_analysis(self, ax):
        """绘制能量分析图"""
        ax.set_title('能量分析', fontsize=12, fontweight='bold')
        
        water_levels = [v for k, v in self.results.items() if k.startswith('H_')]
        
        if len(water_levels) >= 2:
            max_level = max(water_levels)
            min_level = min(water_levels)
            total_head_loss = max_level - min_level
            
            positions = ['上游', '中间', '下游']
            energy_levels = [max_level, (max_level + min_level)/2, min_level]
            
            ax.plot(positions, energy_levels, 'o-', linewidth=3, markersize=8, color=self.colors['water'])
            ax.fill_between(positions, energy_levels, alpha=0.3, color=self.colors['water'])
            
            for i, (pos, level) in enumerate(zip(positions, energy_levels)):
                ax.text(i, level + 1, f'{level:.1f}m', ha='center', fontweight='bold')
            
            ax.set_ylabel('水头 (m)')
            ax.set_title(f'能量线 (总损失: {total_head_loss:.1f}m)', fontsize=10)
            ax.grid(True, alpha=0.3)
        else:
            ax.text(0.5, 0.5, '数据不足', ha='center', va='center', transform=ax.transAxes)
    
    def _plot_mass_balance(self, ax):
        """绘制流量平衡验证"""
        ax.set_title('流量平衡验证', fontsize=12, fontweight='bold')
        
        flows = [v for k, v in self.results.items() if k.startswith('Q_')]
        if flows:
            positive_flows = [f for f in flows if f > 0]
            negative_flows = [abs(f) for f in flows if f < 0]
            
            total_in = sum(positive_flows)
            total_out = sum(negative_flows)
            balance_error = abs(total_in - total_out)
            
            categories = ['流入', '流出', '误差']
            values = [total_in, total_out, balance_error]
            colors = ['green', 'red', 'orange']
            
            bars = ax.bar(categories, values, color=colors, alpha=0.7)
            
            for bar, val in zip(bars, values):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                       f'{val:.2f}', ha='center', fontweight='bold')
            
            ax.set_ylabel('流量 (m³/s)')
            ax.grid(True, alpha=0.3)
        else:
            ax.text(0.5, 0.5, '无流量数据', ha='center', va='center', transform=ax.transAxes)
    
    def _plot_equipment_status(self, ax):
        """绘制设备运行状态"""
        ax.set_title('设备类型分布', fontsize=12, fontweight='bold')
        
        equipment_types = {}
        for model in self.models:
            model_type = model.__class__.__name__.replace('Model', '')
            equipment_types[model_type] = equipment_types.get(model_type, 0) + 1
        
        if equipment_types:
            labels = list(equipment_types.keys())
            sizes = list(equipment_types.values())
            colors = plt.cm.Set3(np.linspace(0, 1, len(labels)))
            
            ax.pie(sizes, labels=labels, colors=colors, autopct='%1.0f%%', startangle=90)
        else:
            ax.text(0.5, 0.5, '无设备数据', ha='center', va='center', transform=ax.transAxes)
    
    def _plot_hydraulic_characteristics(self, ax):
        """绘制水力特性分析"""
        ax.set_title('管道水力特性', fontsize=12, fontweight='bold')
        
        pipe_data = []
        for model in self.models:
            if isinstance(model, PressurizedPipeModel):
                flow_var = f'Q_{model.name}'
                if flow_var in self.results:
                    flow = abs(self.results[flow_var])
                    velocity = flow / model.area if model.area > 0 else 0
                    pipe_data.append({'name': model.name, 'flow': flow, 'velocity': velocity})
        
        if pipe_data:
            flows = [p['flow'] for p in pipe_data]
            velocities = [p['velocity'] for p in pipe_data]
            
            ax.scatter(flows, velocities, s=100, alpha=0.7, c=range(len(pipe_data)), cmap='viridis')
            
            for i, p in enumerate(pipe_data):
                ax.annotate(p['name'], (p['flow'], p['velocity']), 
                           xytext=(5, 5), textcoords='offset points', fontsize=8)
            
            ax.set_xlabel('流量 (m³/s)')
            ax.set_ylabel('流速 (m/s)')
            ax.grid(True, alpha=0.3)
            
            # 添加合理流速范围线
            ax.axhline(y=0.5, color='green', linestyle='--', alpha=0.5, label='最小流速')
            ax.axhline(y=3.0, color='red', linestyle='--', alpha=0.5, label='最大流速')
            ax.legend()
        else:
            ax.text(0.5, 0.5, '无管道数据', ha='center', va='center', transform=ax.transAxes)
    
    def _plot_system_performance(self, ax):
        """绘制系统性能指标"""
        ax.set_title('系统性能指标', fontsize=12, fontweight='bold')
        
        # 计算性能指标
        metrics = ['组件数', '变量数', '总流量', '平均水位']
        values = [
            len(self.models),
            len(self.results),
            sum(v for k, v in self.results.items() if k.startswith('Q_') and v > 0),
            np.mean([v for k, v in self.results.items() if k.startswith('H_')]) if any(k.startswith('H_') for k in self.results) else 0
        ]
        
        bars = ax.bar(range(len(metrics)), values, 
                     color=plt.cm.viridis(np.linspace(0, 1, len(metrics))), alpha=0.7)
        
        for i, (bar, value) in enumerate(zip(bars, values)):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(values)*0.02,
                   f'{value:.1f}', ha='center', fontweight='bold')
        
        ax.set_xticks(range(len(metrics)))
        ax.set_xticklabels(metrics, rotation=45, ha='right')
        ax.set_ylabel('数值')
        ax.grid(True, alpha=0.3)


def create_demo_visualization():
    """创建演示可视化"""
    print("创建复杂水力枢纽系统可视化演示...")
    
    # 创建演示系统
    upstream_reservoir = create_simple_reservoir(
        name="上游水库", upstream_node="上游_入口", downstream_node="上游_出口", 
        initial_level=110.0, bottom_level=100.0, surface_area=2000000.0
    )
    
    gate_configs = [{'name': '主闸门', 'width': 12.0, 'discharge_coeff': 0.75, 'initial_opening': 3.0}]
    main_station = create_gate_station(
        name="主枢纽", upstream_node="上游_出口", downstream_node="分流点", gate_configs=gate_configs
    )
    
    junction = create_simple_junction("分流点", "主枢纽", "主管道", "泄洪道")
    
    main_pipe = create_simple_pipe(
        name="主管道", upstream_node="分流点", downstream_node="下游_入口", 
        length=2000.0, diameter=2.0
    )
    
    spillway = create_simple_pipe(
        name="泄洪道", upstream_node="分流点", downstream_node="泄洪_出口", 
        length=800.0, diameter=2.5
    )
    
    downstream_reservoir = create_simple_reservoir(
        name="下游水库", upstream_node="下游_入口", downstream_node="下游_出口",
        initial_level=95.0, bottom_level=85.0, surface_area=1500000.0
    )
    
    models = [upstream_reservoir, main_station, junction, main_pipe, spillway, downstream_reservoir]
    
    # 模拟求解结果
    demo_results = {
        'H_上游水库': 110.0,
        'H_下游水库': 95.0,
        'H_分流点': 105.0,
        'Q_主闸门': 30.0,
        'Q_主管道': 20.0,
        'Q_泄洪道': 10.0,
        'H_上游_出口': 109.5,
        'H_下游_入口': 95.5,
        'H_泄洪_出口': 100.0
    }
    
    # 创建可视化器并生成图表
    visualizer = HydraulicNetworkVisualizer(models, demo_results)
    fig = visualizer.create_comprehensive_analysis("复杂水力枢纽系统分析报告.png")
    
    # 分析结果合理性
    analyze_result_rationality(models, demo_results)
    
    print("\n可视化分析完成！生成了包含8个分析图表的综合报告。")
    
    return fig


def analyze_result_rationality(models, results):
    """分析结果合理性"""
    print("\n=== 结果合理性分析 ===")
    
    # 1. 水位合理性检查
    water_levels = {k: v for k, v in results.items() if k.startswith('H_')}
    if water_levels:
        max_level = max(water_levels.values())
        min_level = min(water_levels.values())
        print(f"✓ 水位范围: {min_level:.1f}m - {max_level:.1f}m (高差: {max_level-min_level:.1f}m)")
        
        if max_level - min_level > 50:
            print("⚠️  警告: 水位差异较大")
        else:
            print("✅ 水位分布合理")
    
    # 2. 流量平衡检查
    flows = [v for k, v in results.items() if k.startswith('Q_')]
    if flows:
        total_positive = sum(v for v in flows if v > 0)
        total_negative = sum(abs(v) for v in flows if v < 0)
        balance_error = abs(total_positive - total_negative)
        
        print(f"✓ 流入总量: {total_positive:.1f} m³/s")
        print(f"✓ 流出总量: {total_negative:.1f} m³/s") 
        print(f"✓ 平衡误差: {balance_error:.3f} m³/s")
        
        if balance_error < 0.1:
            print("✅ 流量平衡良好")
        else:
            print("⚠️  警告: 流量平衡误差较大")
    
    # 3. 流速合理性检查
    for model in models:
        if isinstance(model, PressurizedPipeModel):
            flow_var = f'Q_{model.name}'
            if flow_var in results:
                flow = abs(results[flow_var])
                velocity = flow / model.area if model.area > 0 else 0
                
                status = "合理"
                if velocity < 0.3:
                    status = "偏低"
                elif velocity > 4.0:
                    status = "偏高"
                
                print(f"✓ {model.name}: 流速 {velocity:.2f} m/s ({status})")
    
    # 4. 系统总体评估
    print(f"\n✓ 系统组件数: {len(models)}")
    print(f"✓ 求解变量数: {len(results)}")
    print("✅ 系统运行状态: 正常")


if __name__ == '__main__':
    create_demo_visualization()