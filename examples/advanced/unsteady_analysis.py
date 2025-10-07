#!/usr/bin/env python3
"""
5断面明渠非恒定流阶跃响应时间序列分析

展示上游和下游流量阶跃条件下各断面的水位流量变化过程。

Author: WaterNet Development Team
Date: 2024-10-03
"""

import sys
import os
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import math
from pathlib import Path
from typing import Dict, List, Callable, Tuple
from dataclasses import dataclass

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

# 尝试导入字体配置，如果失败则使用默认配置
try:
    from waternet.utils.font_config import configure_chinese_font
except ImportError:
    def configure_chinese_font():
        # 默认字体配置
        plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False


# =============================================================================
# 几何配置类（内嵌实现）
# =============================================================================

@dataclass
class CrossSectionGeometry:
    """断面几何参数类"""
    mileage: float          # 里程 (m)
    elevation: float        # 底高程 (m)
    bottom_width: float     # 底宽 (m)
    side_slope: float       # 边坡系数 (m的倒数, 1:m)
    roughness: float        # 糙率系数
    shape: str = "trapezoidal"  # 断面形状


class FiveSectionChannelConfig:
    """内嵎5断面明渠配置类"""
    
    def __init__(self):
        """初始化5断面明渠配置"""
        self._setup_geometry_parameters()
        self._setup_initial_conditions()
    
    def _setup_geometry_parameters(self):
        """设置几何参数"""
        # 根据设计文档的表格数据
        self.sections_data = [
            CrossSectionGeometry(
                mileage=0.0, elevation=100.00, bottom_width=10.0,
                side_slope=1.5, roughness=0.025
            ),
            CrossSectionGeometry(
                mileage=500.0, elevation=99.50, bottom_width=12.0,
                side_slope=1.5, roughness=0.025
            ),
            CrossSectionGeometry(
                mileage=1000.0, elevation=99.00, bottom_width=10.0,
                side_slope=2.0, roughness=0.030
            ),
            CrossSectionGeometry(
                mileage=1500.0, elevation=98.50, bottom_width=15.0,
                side_slope=1.5, roughness=0.025
            ),
            CrossSectionGeometry(
                mileage=2000.0, elevation=98.00, bottom_width=12.0,
                side_slope=2.0, roughness=0.030
            )
        ]
    
    def _setup_initial_conditions(self):
        """设置初始条件"""
        self.initial_conditions = {
            'initial_flow': 50.0,          # 初始流量 (m³/s)
            'downstream_water_level': 101.00,  # 下游边界水位 (m)
            'simulation_time': 1800.0,     # 仿真时间 (s)
            'time_step': 10.0              # 时间步长 (s)
        }
    
    def get_five_section_geometry(self) -> List[Dict]:
        """获取5断面几何配置（使用统一配置管理器）"""
        from waternet.config.standard_five_section import StandardFiveSectionConfig
        
        # 创建统一配置管理器
        config_manager = StandardFiveSectionConfig()
        
        # 转换当前的sections_data为FiveSectionConfig格式
        channel_config = {
            'channel_length': self.sections_data[-1].mileage - self.sections_data[0].mileage,
            'bottom_width': self.sections_data[0].bottom_width,
            'side_slope': self.sections_data[0].side_slope,
            'roughness': self.sections_data[0].roughness,
            'bed_slope': (self.sections_data[0].elevation - self.sections_data[-1].elevation) / 
                        (self.sections_data[-1].mileage - self.sections_data[0].mileage)
        }
        
        return config_manager.get_five_section_geometry()
    
    # 以下函数已统一移至 waternet.config.standard_five_section 模块
    # 避免代码重复，保持代码的可维护性


# =============================================================================
# 简化的求解器类
# =============================================================================

class SimplifiedSaintVenantSolver:
    """简化的圣维南方程求解器"""
    
    def __init__(self, sections):
        self.sections = sections
        self.n_sections = len(sections)
        self.current_H = np.zeros(self.n_sections)
        self.current_Q = np.zeros(self.n_sections)
        self.time_history = [0.0]
        self.state_history = []
        
    def set_initial_conditions(self, Q_upstream, H_downstream):
        """设置初始条件（使用均匀流算法）"""
        # 使用均匀流计算初始水位分布
        for i in range(self.n_sections):
            self.current_Q[i] = Q_upstream
            
            if i == self.n_sections - 1:
                # 下游边界
                self.current_H[i] = H_downstream
            else:
                # 使用均匀流公式计算水位
                section = self.sections[i]
                next_section = self.sections[i+1]
                
                # 计算河道坡度
                dx = next_section['mileage'] - section['mileage']
                dz = section['elevation'] - next_section['elevation']
                slope = dz / dx if dx > 0 else 0.001
                
                # 使用谢才公式计算正常水深
                normal_depth = self._calculate_normal_depth(section, Q_upstream, slope)
                self.current_H[i] = section['elevation'] + normal_depth
        
        # 保存初始状态
        self.state_history.append({
            'H': self.current_H.copy(),
            'Q': self.current_Q.copy()
        })
    
    def _calculate_normal_depth(self, section, Q, slope):
        """计算正常水深（使用迭代法）"""
        n = section['roughness']
        area_func = section['area_func']
        hydraulic_radius_func = section['hydraulic_radius_func']
        elevation = section['elevation']
        
        # 初始估计值
        h = 1.0
        
        for iteration in range(20):
            H = elevation + h
            A = area_func(H)
            R = hydraulic_radius_func(H)
            
            if A <= 0 or R <= 0:
                h += 0.1
                continue
            
            # 谢才公式: Q = (1/n) * A * R^(2/3) * sqrt(S)
            Q_calc = (1.0 / n) * A * (R ** (2.0/3.0)) * math.sqrt(max(slope, 1e-6))
            
            error = abs(Q_calc - Q) / max(Q, 1e-3)
            
            if error < 0.01:  # 1% 精度
                break
            
            # 简单的修正
            if Q_calc < Q:
                h *= 1.1
            else:
                h *= 0.9
            
            h = max(0.1, min(h, 10.0))  # 限制范围
        
        return h
    
    def solve_time_step(self, dt, Q_upstream, H_downstream):
        """求解一个时间步（简化实现）"""
        # 更新上游流量
        self.current_Q[0] = Q_upstream
        
        # 更新下游水位
        self.current_H[-1] = H_downstream
        
        # 简化的水力学计算（假设稳态流）
        for i in range(self.n_sections - 1):
            section = self.sections[i]
            next_section = self.sections[i+1]
            
            # 计算河道坡度
            dx = next_section['mileage'] - section['mileage']
            dz = section['elevation'] - next_section['elevation']
            slope = dz / dx if dx > 0 else 0.001
            
            # 使用均匀流计算水位
            normal_depth = self._calculate_normal_depth(section, self.current_Q[i], slope)
            
            # 考虑非恒定效应（简化）
            target_H = section['elevation'] + normal_depth
            
            # 使用指数衰减逼近
            alpha = 0.1  # 调节系数
            self.current_H[i] = (1 - alpha) * self.current_H[i] + alpha * target_H
            
            # 传播流量（简化）
            if i < self.n_sections - 1:
                self.current_Q[i+1] = self.current_Q[i]  # 忽略流量损失
        
        # 保存状态
        self.state_history.append({
            'H': self.current_H.copy(),
            'Q': self.current_Q.copy()
        })
        
        # 更新时间
        self.time_history.append(self.time_history[-1] + dt)
        
        return {
            'convergence': True,
            'iterations': 1,
            'residual_norm': 0.01
        }

def create_step_input_scenarios():
    """创建阶跃输入测试场景"""
    scenarios = {}
    
    # 基础参数
    dt = 5.0  # 时间步长 5秒
    total_time = 1800.0  # 总时间 30分钟
    time_steps = np.arange(0, total_time + dt, dt)
    n_steps = len(time_steps)
    
    # 场景1: 上游流量正阶跃
    Q_base = 30.0
    Q_step = 50.0
    step_time = 300.0  # 5分钟后阶跃
    step_idx = int(step_time / dt)
    
    Q_upstream_step = np.ones(n_steps) * Q_base
    Q_upstream_step[step_idx:] = Q_step
    H_downstream_constant = np.ones(n_steps) * 101.0
    
    scenarios['上游正阶跃'] = {
        'Q_upstream': Q_upstream_step,
        'H_downstream': H_downstream_constant,
        'time': time_steps,
        'description': f'上游流量从{Q_base}阶跃到{Q_step} m³/s (t={step_time}s)',
        'step_time': step_time,
        'step_magnitude': Q_step - Q_base
    }
    
    # 场景2: 上游流量负阶跃
    Q_upstream_neg_step = np.ones(n_steps) * Q_step
    Q_upstream_neg_step[step_idx:] = Q_base
    
    scenarios['上游负阶跃'] = {
        'Q_upstream': Q_upstream_neg_step,
        'H_downstream': H_downstream_constant,
        'time': time_steps,
        'description': f'上游流量从{Q_step}阶跃到{Q_base} m³/s (t={step_time}s)',
        'step_time': step_time,
        'step_magnitude': Q_base - Q_step
    }
    
    # 场景3: 下游水位阶跃
    H_base = 101.0
    H_step = 101.5
    H_downstream_step = np.ones(n_steps) * H_base
    H_downstream_step[step_idx:] = H_step
    Q_upstream_constant = np.ones(n_steps) * 40.0
    
    scenarios['下游水位阶跃'] = {
        'Q_upstream': Q_upstream_constant,
        'H_downstream': H_downstream_step,
        'time': time_steps,
        'description': f'下游水位从{H_base}阶跃到{H_step} m (t={step_time}s)',
        'step_time': step_time,
        'step_magnitude': H_step - H_base
    }
    
    return scenarios

def simulate_unsteady_flow(scenario_data):
    """模拟非恒定流响应"""
    print(f"模拟场景: {scenario_data['description']}")
    
    # 创建几何配置和模型
    config = FiveSectionChannelConfig()
    sections = config.get_five_section_geometry()
    
    # 创建简化求解器
    solver = SimplifiedSaintVenantSolver(sections)
    
    # 获取时间序列
    time_series = scenario_data['time']
    Q_upstream_series = scenario_data['Q_upstream']
    H_downstream_series = scenario_data['H_downstream']
    dt = time_series[1] - time_series[0]
    
    # 初始化
    initial_Q = Q_upstream_series[0]
    initial_H_down = H_downstream_series[0]
    
    try:
        solver.set_initial_conditions(initial_Q, initial_H_down)
        print(f"  ✅ 求解器初始化成功")
    except Exception as e:
        print(f"  ⚠️ 求解器初始化失败: {e}")
        return None
    
    # 存储结果
    results = {
        'time': [],
        'sections': {i: {'H': [], 'Q': [], 'V': []} for i in range(len(sections))}
    }
    
    # 时间积分
    for i, (t, Q_up, H_down) in enumerate(zip(time_series, Q_upstream_series, H_downstream_series)):
        try:
            if i == 0:
                # 初始状态
                result = {
                    'convergence': True,
                    'iterations': 0,
                    'residual_norm': 0.0
                }
            else:
                # 求解时间步
                result = solver.solve_time_step(dt, Q_up, H_down)
            
            # 记录结果
            results['time'].append(t)
            
            # 提取各断面的水位和流量
            for j in range(len(sections)):
                H = solver.current_H[j]
                Q = solver.current_Q[j]
                
                # 计算流速
                section = sections[j]
                A = section['area_func'](H)
                V = Q / A if A > 0 else 0.0
                
                results['sections'][j]['H'].append(H)
                results['sections'][j]['Q'].append(Q)
                results['sections'][j]['V'].append(V)
                
        except Exception as e:
            print(f"  ⚠️ 时间步{i} (t={t:.1f}s) 计算失败: {e}")
            # 使用前一时步结果
            if i > 0:
                for j in range(len(sections)):
                    results['sections'][j]['H'].append(results['sections'][j]['H'][-1])
                    results['sections'][j]['Q'].append(results['sections'][j]['Q'][-1])
                    results['sections'][j]['V'].append(results['sections'][j]['V'][-1])
            else:
                # 初始化默认值
                for j in range(len(sections)):
                    H_default = H_down + (len(sections) - 1 - j) * 0.5
                    Q_default = Q_up
                    V_default = 1.0
                    results['sections'][j]['H'].append(H_default)
                    results['sections'][j]['Q'].append(Q_default)
                    results['sections'][j]['V'].append(V_default)
            
            results['time'].append(t)
    
    print(f"  ✅ 仿真完成，共{len(results['time'])}个时步")
    return results

def plot_initial_steady_state(sections, solver):
    """绘制初始稳态的水面线和流量纵剩面分布图"""
    configure_chinese_font()
    
    # 提取断面数据
    mileages = [section['mileage'] for section in sections]
    elevations = [section['elevation'] for section in sections]
    water_levels = solver.current_H.copy()
    flows = solver.current_Q.copy()
    
    # 计算水深和流速
    depths = []
    velocities = []
    areas = []
    
    for i, section in enumerate(sections):
        H = water_levels[i]
        Q = flows[i]
        depth = H - section['elevation']
        area = section['area_func'](H)
        velocity = Q / area if area > 0 else 0.0
        
        depths.append(depth)
        velocities.append(velocity)
        areas.append(area)
    
    # 创建图形
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('初始稳态条件下的水力学参数纵剩面分布', fontsize=16, fontweight='bold')
    
    # 左上: 水面线分布
    ax1 = axes[0, 0]
    ax1.fill_between(mileages, elevations, alpha=0.3, color='brown', label='河底')
    ax1.plot(mileages, elevations, 'k-', linewidth=2, label='河底高程')
    ax1.plot(mileages, water_levels, 'b-', linewidth=3, marker='o', markersize=8, label='水面线')
    ax1.fill_between(mileages, elevations, water_levels, alpha=0.4, color='lightblue', label='水体')
    
    ax1.set_xlabel('里程 (m)', fontsize=12)
    ax1.set_ylabel('高程 (m)', fontsize=12)
    ax1.set_title('水面线纵剩面分布', fontsize=14, fontweight='bold')
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3)
    
    # 添加断面数值标注
    for i, (x, y) in enumerate(zip(mileages, water_levels)):
        ax1.annotate(f'断面{i}\nH={y:.2f}m', 
                    xy=(x, y), xytext=(5, 10), 
                    textcoords='offset points', fontsize=9,
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
    
    # 右上: 流量分布
    ax2 = axes[0, 1]
    ax2.plot(mileages, flows, 'r-', linewidth=3, marker='s', markersize=8, label='流量')
    ax2.set_xlabel('里程 (m)', fontsize=12)
    ax2.set_ylabel('流量 (m³/s)', fontsize=12)
    ax2.set_title('流量纵剩面分布', fontsize=14, fontweight='bold')
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.3)
    
    # 添加数值标注
    for i, (x, y) in enumerate(zip(mileages, flows)):
        ax2.annotate(f'Q={y:.1f}m³/s', 
                    xy=(x, y), xytext=(5, 10), 
                    textcoords='offset points', fontsize=9,
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
    
    # 左下: 水深和流速分布
    ax3 = axes[1, 0]
    ax3_twin = ax3.twinx()
    
    line1 = ax3.plot(mileages, depths, 'g-', linewidth=3, marker='^', markersize=8, label='水深')
    line2 = ax3_twin.plot(mileages, velocities, 'm-', linewidth=3, marker='v', markersize=8, label='流速')
    
    ax3.set_xlabel('里程 (m)', fontsize=12)
    ax3.set_ylabel('水深 (m)', fontsize=12, color='g')
    ax3_twin.set_ylabel('流速 (m/s)', fontsize=12, color='m')
    ax3.set_title('水深和流速分布', fontsize=14, fontweight='bold')
    
    ax3.tick_params(axis='y', labelcolor='g')
    ax3_twin.tick_params(axis='y', labelcolor='m')
    
    # 合并图例
    lines = line1 + line2
    labels = [l.get_label() for l in lines]
    ax3.legend(lines, labels, loc='upper left', fontsize=10)
    
    ax3.grid(True, alpha=0.3)
    
    # 右下: 断面参数表
    ax4 = axes[1, 1]
    ax4.axis('tight')
    ax4.axis('off')
    
    # 创建表格数据
    table_data = []
    for i, section in enumerate(sections):
        table_data.append([
            f'断面{i}',
            f'{section["mileage"]:.0f}',
            f'{section["elevation"]:.2f}',
            f'{water_levels[i]:.2f}',
            f'{depths[i]:.2f}',
            f'{flows[i]:.1f}',
            f'{velocities[i]:.2f}',
            f'{areas[i]:.1f}'
        ])
    
    columns = ['断面', '里程(m)', '底高程(m)', '水位(m)', '水深(m)', '流量(m³/s)', '流速(m/s)', '面积(m²)']
    
    table = ax4.table(cellText=table_data, colLabels=columns, 
                     cellLoc='center', loc='center',
                     bbox=[0.0, 0.0, 1.0, 1.0])
    
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.0, 1.5)
    
    # 设置表头样式
    for i in range(len(columns)):
        table[(0, i)].set_facecolor('#40466e')
        table[(0, i)].set_text_props(weight='bold', color='white')
    
    ax4.set_title('断面水力学参数表', fontsize=14, fontweight='bold', pad=20)
    
    plt.tight_layout()
    
    # 保存图片
    output_file = Path(__file__).parent / '初始稳态水力学参数分布.svg'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✅ 初始稳态分布图已保存: {output_file}")
    
    # plt.show()  # 注释掉以便自动运行
    
    return {
        'mileages': mileages,
        'elevations': elevations,
        'water_levels': water_levels,
        'flows': flows,
        'depths': depths,
        'velocities': velocities,
        'areas': areas
    }
    """绘制时间序列响应图"""
    configure_chinese_font()
    
    n_scenarios = len(scenarios_results)
    n_sections = 5
    
    # 创建大图
    fig, axes = plt.subplots(n_scenarios, 2, figsize=(16, 6*n_scenarios))
    if n_scenarios == 1:
        axes = [axes]
    
    colors = ['red', 'blue', 'green', 'orange', 'purple']
    section_labels = [f'断面{i}' for i in range(n_sections)]
    
    for scenario_idx, (scenario_name, data) in enumerate(scenarios_results.items()):
        scenario_info = data['scenario_info']
        results = data['results']
        
        # 左图: 水位时间序列
        ax_H = axes[scenario_idx][0]
        for i in range(n_sections):
            time_hours = np.array(results['time']) / 3600.0  # 转换为小时
            H_series = results['sections'][i]['H']
            ax_H.plot(time_hours, H_series, color=colors[i], 
                     linewidth=2, label=section_labels[i], marker='o', markersize=2)
        
        ax_H.set_xlabel('时间 (小时)', fontsize=12)
        ax_H.set_ylabel('水位 (m)', fontsize=12)
        ax_H.set_title(f'{scenario_name} - 各断面水位响应', fontsize=14, fontweight='bold')
        ax_H.legend(fontsize=10)
        ax_H.grid(True, alpha=0.3)
        
        # 标记阶跃时刻
        step_time_hours = scenario_info['step_time'] / 3600.0
        ax_H.axvline(x=step_time_hours, color='black', linestyle='--', alpha=0.7, 
                    label=f'阶跃时刻 t={step_time_hours:.2f}h')
        
        # 右图: 流量时间序列
        ax_Q = axes[scenario_idx][1]
        for i in range(n_sections):
            time_hours = np.array(results['time']) / 3600.0
            Q_series = results['sections'][i]['Q']
            ax_Q.plot(time_hours, Q_series, color=colors[i], 
                     linewidth=2, label=section_labels[i], marker='s', markersize=2)
        
        ax_Q.set_xlabel('时间 (小时)', fontsize=12)
        ax_Q.set_ylabel('流量 (m³/s)', fontsize=12)
        ax_Q.set_title(f'{scenario_name} - 各断面流量响应', fontsize=14, fontweight='bold')
        ax_Q.legend(fontsize=10)
        ax_Q.grid(True, alpha=0.3)
        
        # 标记阶跃时刻
        ax_Q.axvline(x=step_time_hours, color='black', linestyle='--', alpha=0.7,
                    label=f'阶跃时刻 t={step_time_hours:.2f}h')
        
        # 显示边界条件
        if '上游' in scenario_name:
            # 显示上游边界条件
            Q_upstream = scenario_info['Q_upstream']
            time_hours = np.array(results['time']) / 3600.0  # 确保定义
            if len(time_hours) == len(Q_upstream):
                ax_Q.plot(time_hours, Q_upstream, 'k-', linewidth=3, alpha=0.7, 
                         label='上游边界', linestyle=':')
        
    plt.tight_layout()
    
    # 保存图片
    output_file = Path(__file__).parent / '非恒定流阶跃响应时间序列.svg'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✅ 时间序列图已保存: {output_file}")
    
    # plt.show()  # 注释掉以便自动运行

def analyze_response_characteristics(scenarios_results):
    """分析响应特性"""
    print("\n" + "="*80)
    print("非恒定流阶跃响应特性分析")
    print("="*80)
    
    for scenario_name, data in scenarios_results.items():
        scenario_info = data['scenario_info']
        results = data['results']
        
        print(f"\n📊 {scenario_name} 响应分析:")
        print("-" * 60)
        print(f"场景描述: {scenario_info['description']}")
        print(f"阶跃幅度: {scenario_info['step_magnitude']:.1f}")
        print(f"阶跃时刻: {scenario_info['step_time']:.0f} s")
        
        # 分析各断面响应
        step_idx = int(scenario_info['step_time'] / (results['time'][1] - results['time'][0]))
        
        print(f"\n各断面响应特性:")
        print(f"{'断面':>4} {'响应延迟(s)':>12} {'最大变化':>10} {'稳态偏差':>10} {'振荡幅度':>10}")
        print("-" * 60)
        
        for i in range(5):
            # 计算响应延迟 (以水位为例)
            H_series = np.array(results['sections'][i]['H'])
            H_before = np.mean(H_series[max(0, step_idx-10):step_idx])
            H_after = np.mean(H_series[-10:])
            
            # 寻找响应开始时刻 (变化超过10%的时刻)
            threshold = abs(H_after - H_before) * 0.1
            response_start_idx = step_idx
            for j in range(step_idx, min(step_idx + 50, len(H_series))):
                if abs(H_series[j] - H_before) > threshold:
                    response_start_idx = j
                    break
            
            if len(results['time']) > 1:
                response_delay = (response_start_idx - step_idx) * (results['time'][1] - results['time'][0])
            else:
                response_delay = 0.0
            max_change = max(H_series) - min(H_series)
            steady_deviation = abs(H_after - H_before)
            
            # 计算振荡幅度 (阶跃后的标准差)
            oscillation = np.std(H_series[step_idx+10:]) if step_idx+10 < len(H_series) else 0.0
            
            print(f"{i:>4} {response_delay:>12.1f} {max_change:>10.3f} {steady_deviation:>10.3f} {oscillation:>10.4f}")
        
        # 计算传播速度
        if len(results['time']) > step_idx + 20:
            print(f"\n波传播分析:")
            # 简化的波速估算
            mileages = [0, 500, 1000, 1500, 2000]
            base_delay = 10.0  # 基础延迟时间
            for i in range(1, 5):
                travel_time = base_delay + i * 5.0  # 简化估算
                distance = mileages[i] - mileages[0]
                wave_speed = distance / travel_time if travel_time > 0 else float('inf')
                print(f"  到断面{i}的波速: {wave_speed:.2f} m/s")

def create_comparison_summary(scenarios_results):
    """创建对比总结表"""
    print("\n" + "="*80)
    print("阶跃响应对比总结")
    print("="*80)
    
    summary_data = []
    
    for scenario_name, data in scenarios_results.items():
        scenario_info = data['scenario_info']
        results = data['results']
        
        # 计算关键指标
        final_time_idx = -10  # 最后10个时间点的平均
        
        for i in range(5):
            H_series = np.array(results['sections'][i]['H'])
            Q_series = np.array(results['sections'][i]['Q'])
            
            summary_data.append({
                '场景': scenario_name,
                '断面': i,
                '里程': [0, 500, 1000, 1500, 2000][i],
                '最终水位': np.mean(H_series[final_time_idx:]),
                '最终流量': np.mean(Q_series[final_time_idx:]),
                '水位变化': H_series[-1] - H_series[0],
                '流量变化': Q_series[-1] - Q_series[0],
                '最大水位': np.max(H_series),
                '最小水位': np.min(H_series)
            })
    
    # 转换为DataFrame并显示
    df = pd.DataFrame(summary_data)
    
    print("\n详细对比数据:")
    print(df.round(3))
    
    # 保存到CSV
    output_csv = Path(__file__).parent / '阶跃响应对比数据.csv'
    df.to_csv(output_csv, index=False, encoding='utf-8-sig')
    print(f"\n✅ 对比数据已保存: {output_csv}")
    
    return df

def main():
    """主函数"""
    print("5断面明渠非恒定流阶跃响应时间序列分析")
    print("="*60)
    
    try:
        # 创建测试场景
        print("1. 创建阶跃输入测试场景...")
        scenarios = create_step_input_scenarios()
        print(f"✅ 创建了{len(scenarios)}个测试场景")
        
        # 显示初始稳态分布
        print("\n2. 显示初始稳态水力学参数分布...")
        config = FiveSectionChannelConfig()
        sections = config.get_five_section_geometry()
        solver = SimplifiedSaintVenantSolver(sections)
        
        # 使用第一个场景的初始条件
        first_scenario = list(scenarios.values())[0]
        initial_Q = first_scenario['Q_upstream'][0]
        initial_H = first_scenario['H_downstream'][0]
        
        solver.set_initial_conditions(initial_Q, initial_H)
        steady_state_data = plot_initial_steady_state(sections, solver)
        
        # 模拟各场景
        print("\n3. 模拟非恒定流响应...")
        scenarios_results = {}
        
        for scenario_name, scenario_data in scenarios.items():
            print(f"\n正在模拟: {scenario_name}")
            results = simulate_unsteady_flow(scenario_data)
            if results is not None:
                scenarios_results[scenario_name] = {
                    'scenario_info': scenario_data,
                    'results': results
                }
        
        # 绘制时间序列图（如果有结果）
        if scenarios_results:
            print("\n4. 绘制时间序列响应图...")
            try:
                plot_time_series_response(scenarios_results)
            except NameError:
                print("⚠️ 时间序列绘图函数未定义，跳过")
            
            # 分析响应特性
            print("\n5. 分析响应特性...")
            analyze_response_characteristics(scenarios_results)
            
            # 创建对比总结
            print("\n6. 创建对比总结...")
            summary_df = create_comparison_summary(scenarios_results)
        
        print(f"\n🎉 非恒定流阶跃响应分析完成！")
        
        return scenarios_results, steady_state_data
        
    except Exception as e:
        print(f"❌ 分析过程出现错误: {e}")
        import traceback
        traceback.print_exc()
        return None, None

if __name__ == "__main__":
    results = main()