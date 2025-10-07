"""
水网系统演示程序

展示水网整体系统的完整功能，包括：
1. 配置驱动的水网创建
2. 多种求解策略的比较
3. 数字孪生系统演示
4. 降阶模型的联立求解分析

Author: WaterNet Development Team
Date: 2024-10-05
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import time
import logging
from pathlib import Path
import sys

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from waternet.network import (
    WaterNetworkSystem, SolutionStrategy, ModelCouplingStrength
)

# 设置matplotlib中文字体
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def create_sample_network_config():
    """创建示例水网配置"""
    config_path = project_root / "configs" / "sample_network.yaml"
    
    config_content = """
# 示例水网配置 - 演示不同降阶模型的联立求解
metadata:
  name: "降阶模型联立求解演示系统"
  description: "包含不同耦合强度的水网对象，演示自适应求解策略"

objects:
  # 强耦合对象 - IDZ模型
  channel_idz:
    type: "channel"
    simulation_method: "idz"
    length: 5000.0
    bottom_width: 20.0
    side_slope: 1.5
    bottom_slope: 0.0005
    manning_coefficient: 0.03
    
  # 中等耦合对象 - 蓄量演算
  reservoir_storage:
    type: "reservoir"
    simulation_method: "storage_routing"
    capacity: 1000000.0
    initial_volume: 500000.0
    surface_area: 50000.0
    
  # 弱耦合对象 - 马斯京干
  channel_muskingum:
    type: "channel"
    simulation_method: "muskingum"
    length: 3000.0
    bottom_width: 15.0
    side_slope: 1.0
    bottom_slope: 0.0008
    manning_coefficient: 0.025
    
  # 解耦对象 - 水量平衡
  pipe_balance:
    type: "pipe"
    simulation_method: "water_balance"
    length: 1000.0
    diameter: 2.0
    
  # 强耦合调控对象
  gate_control:
    type: "gate"
    simulation_method: "hydraulic_control"
    gate_width: 5.0
    gate_height: 3.0
    control_mode: "automatic"

connections:
  - from: "reservoir_storage"
    to: "channel_idz"
  - from: "channel_idz"
    to: "gate_control"
  - from: "gate_control"
    to: "channel_muskingum"
  - from: "channel_muskingum"
    to: "pipe_balance"

solution:
  strategy: "adaptive"
  time_step: 60.0
  max_iterations: 30
  tolerance: 1e-6

boundary_conditions:
  reservoir_storage:
    inflow: 10.0
    initial_water_level: 100.0
    
  pipe_balance:
    downstream_water_level: 50.0
"""
    
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, 'w', encoding='utf-8') as f:
        f.write(config_content)
    
    return config_path


def demonstrate_coupling_analysis(network: WaterNetworkSystem):
    """演示耦合强度分析"""
    print("\n" + "="*60)
    print("🔗 降阶模型耦合强度分析")
    print("="*60)
    
    # 获取耦合强度分析
    coupling_strengths = network.topology.analyze_coupling_strength()
    
    print("各对象的耦合强度：")
    for obj_id, strength in coupling_strengths.items():
        obj = network.topology.objects[obj_id]
        method = getattr(obj, 'simulation_method', 'unknown')
        print(f"  {obj_id:20} | {strength.value:12} | {method}")
    
    # 统计分布
    strength_counts = {}
    for strength in ModelCouplingStrength:
        count = sum(1 for s in coupling_strengths.values() if s == strength)
        strength_counts[strength.value] = count
    
    print(f"\n耦合强度分布：")
    for strength, count in strength_counts.items():
        print(f"  {strength:12}: {count} 个对象")
    
    # 绘制分布图
    plt.figure(figsize=(10, 6))
    
    plt.subplot(1, 2, 1)
    labels = list(strength_counts.keys())
    sizes = list(strength_counts.values())
    colors = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99']
    plt.pie(sizes, labels=labels, autopct='%1.1f%%', colors=colors)
    plt.title('耦合强度分布')
    
    plt.subplot(1, 2, 2)
    plt.bar(labels, sizes, color=colors)
    plt.title('耦合强度统计')
    plt.ylabel('对象数量')
    plt.xticks(rotation=45)
    
    plt.tight_layout()
    plt.savefig(project_root / 'results' / 'coupling_analysis.svg', dpi=300, bbox_inches='tight')
    plt.show()
    
    return coupling_strengths


def compare_solution_strategies(network: WaterNetworkSystem):
    """比较不同求解策略的性能"""
    print("\n" + "="*60)
    print("⚡ 求解策略性能比较")
    print("="*60)
    
    strategies = [
        SolutionStrategy.SEQUENTIAL,
        SolutionStrategy.PARALLEL,
        SolutionStrategy.COUPLED_SIMPLIFIED,
        SolutionStrategy.ADAPTIVE
    ]
    
    boundary_conditions = {
        'reservoir_storage': {'inflow': 15.0},
        'pipe_balance': {'downstream_water_level': 45.0}
    }
    
    results = {}
    performance_data = []
    
    for strategy in strategies:
        print(f"\n测试策略: {strategy.value}")
        
        # 设置求解策略
        network.solution_config.strategy = strategy
        network.solver = network.solver.__class__(network.topology, network.solution_config)
        
        # 运行短期仿真测试性能
        start_time = time.time()
        
        try:
            # 运行10个时间步
            step_times = []
            for i in range(10):
                step_start = time.time()
                step_result = network.solver.solve_time_step(60.0, boundary_conditions)
                step_time = time.time() - step_start
                step_times.append(step_time)
            
            total_time = time.time() - start_time
            avg_step_time = np.mean(step_times)
            
            results[strategy.value] = {
                'total_time': total_time,
                'avg_step_time': avg_step_time,
                'success': True
            }
            
            performance_data.append({
                'Strategy': strategy.value,
                'Total Time (s)': total_time,
                'Avg Step Time (s)': avg_step_time,
                'Success': 'Yes'
            })
            
            print(f"  ✓ 总耗时: {total_time:.4f}s")
            print(f"  ✓ 平均步长耗时: {avg_step_time:.4f}s")
            
        except Exception as e:
            print(f"  ❌ 策略失败: {e}")
            results[strategy.value] = {
                'total_time': float('inf'),
                'avg_step_time': float('inf'),
                'success': False
            }
            performance_data.append({
                'Strategy': strategy.value,
                'Total Time (s)': float('inf'),
                'Avg Step Time (s)': float('inf'),
                'Success': 'No'
            })
    
    # 创建性能比较图
    plt.figure(figsize=(12, 8))
    
    df = pd.DataFrame(performance_data)
    df_success = df[df['Success'] == 'Yes']
    
    if len(df_success) > 0:
        plt.subplot(2, 2, 1)
        plt.bar(df_success['Strategy'], df_success['Total Time (s)'])
        plt.title('总耗时比较')
        plt.ylabel('时间 (秒)')
        plt.xticks(rotation=45)
        
        plt.subplot(2, 2, 2)
        plt.bar(df_success['Strategy'], df_success['Avg Step Time (s)'])
        plt.title('平均步长耗时比较')
        plt.ylabel('时间 (秒)')
        plt.xticks(rotation=45)
        
        plt.subplot(2, 2, 3)
        # 性能评分（倒数）
        scores = 1.0 / (df_success['Avg Step Time (s)'] + 1e-6)
        plt.bar(df_success['Strategy'], scores)
        plt.title('性能评分 (越高越好)')
        plt.ylabel('评分')
        plt.xticks(rotation=45)
        
        plt.subplot(2, 2, 4)
        # 成功率
        success_counts = df['Success'].value_counts()
        plt.pie(success_counts.values, labels=success_counts.index, autopct='%1.1f%%')
        plt.title('求解成功率')
    
    plt.tight_layout()
    plt.savefig(project_root / 'results' / 'strategy_comparison.svg', dpi=300, bbox_inches='tight')
    plt.show()
    
    return results


def demonstrate_digital_twin(network: WaterNetworkSystem):
    """演示数字孪生功能"""
    print("\n" + "="*60)
    print("👥 数字孪生系统演示")
    print("="*60)
    
    # 创建精细化模型（主系统）
    print("创建精细化模型...")
    detailed_config = network.solution_config
    detailed_config.strategy = SolutionStrategy.COUPLED_SIMPLIFIED
    detailed_network = WaterNetworkSystem()
    detailed_network.topology = network.topology
    detailed_network.solution_config = detailed_config
    
    # 创建简化模型（孪生系统）
    print("创建简化模型...")
    simplified_config = network.solution_config
    simplified_config.strategy = SolutionStrategy.PARALLEL
    simplified_network = WaterNetworkSystem()
    simplified_network.topology = network.topology
    simplified_network.solution_config = simplified_config
    
    # 创建数字孪生
    twin_config = {
        'sync_interval': 180.0,  # 3分钟同步
        'enable_correction': True
    }
    
    twin_system = detailed_network.create_digital_twin(simplified_network, twin_config)
    
    print("运行数字孪生仿真...")
    
    boundary_conditions = {
        'reservoir_storage': {'inflow': 12.0},
        'pipe_balance': {'downstream_water_level': 48.0}
    }
    
    # 运行同步仿真
    try:
        detailed_results, simplified_results = twin_system.run_synchronized_simulation(
            duration=1800.0,  # 30分钟
            primary_bc=boundary_conditions,
            secondary_bc=boundary_conditions
        )
        
        print("✓ 数字孪生仿真完成")
        print(f"  精细化模型结果: {len(detailed_results)} 个时间点")
        print(f"  简化模型结果: {len(simplified_results)} 个时间点")
        
        # 绘制比较图
        if len(detailed_results) > 0 and len(simplified_results) > 0:
            plt.figure(figsize=(12, 8))
            
            # 选择一个对象进行比较
            obj_id = list(network.topology.objects.keys())[0]
            
            if f'{obj_id}_Q' in detailed_results.columns and f'{obj_id}_Q' in simplified_results.columns:
                plt.subplot(2, 1, 1)
                plt.plot(detailed_results['time'], detailed_results[f'{obj_id}_Q'], 
                        label='精细化模型', linewidth=2)
                plt.plot(simplified_results['time'], simplified_results[f'{obj_id}_Q'], 
                        label='简化模型', linestyle='--', linewidth=2)
                plt.xlabel('时间 (s)')
                plt.ylabel('流量 (m³/s)')
                plt.title(f'{obj_id} 流量对比')
                plt.legend()
                plt.grid(True)
                
                plt.subplot(2, 1, 2)
                if f'{obj_id}_H' in detailed_results.columns:
                    plt.plot(detailed_results['time'], detailed_results[f'{obj_id}_H'], 
                            label='精细化模型', linewidth=2)
                    plt.plot(simplified_results['time'], simplified_results[f'{obj_id}_H'], 
                            label='简化模型', linestyle='--', linewidth=2)
                    plt.xlabel('时间 (s)')
                    plt.ylabel('水位 (m)')
                    plt.title(f'{obj_id} 水位对比')
                    plt.legend()
                    plt.grid(True)
            
            plt.tight_layout()
            plt.savefig(project_root / 'results' / 'digital_twin_comparison.svg', dpi=300, bbox_inches='tight')
            plt.show()
        
    except Exception as e:
        print(f"❌ 数字孪生仿真失败: {e}")


def analyze_reduced_order_coupling():
    """分析降阶模型的联立求解需求"""
    print("\n" + "="*60)
    print("🧮 降阶模型联立求解需求分析")
    print("="*60)
    
    # 基于项目记忆的分析结果
    model_analysis = {
        '水量平衡模型': {
            'coupling_strength': 'DECOUPLED',
            'coupling_reason': 'Q_out = Q_in，完全解耦',
            'joint_solve_needed': False,
            'solve_strategy': '独立并行求解'
        },
        '马斯京干模型': {
            'coupling_strength': 'WEAK',
            'coupling_reason': '河段间流量连续性，但无回水效应',
            'joint_solve_needed': False,
            'solve_strategy': '按拓扑顺序串行求解'
        },
        '蓄量演算模型': {
            'coupling_strength': 'MODERATE',
            'coupling_reason': '基于连续性方程dV/dt = Q_in - Q_out，需要迭代',
            'joint_solve_needed': False,
            'solve_strategy': '迭代求解但可串行处理'
        },
        'IDZ模型': {
            'coupling_strength': 'STRONG',
            'coupling_reason': '四方程耦合系统，包含回水效应G12(s)和G21(s)',
            'joint_solve_needed': True,
            'solve_strategy': '联立求解传递函数矩阵'
        },
        '圣维南方程': {
            'coupling_strength': 'STRONG',
            'coupling_reason': '完整水力方程组，强非线性耦合',
            'joint_solve_needed': True,
            'solve_strategy': '全联立求解或分段联立'
        }
    }
    
    print("📊 各降阶模型的联立求解需求分析：")
    print("-" * 80)
    print(f"{'模型名称':<15} {'耦合强度':<12} {'需要联立':<8} {'求解策略'}")
    print("-" * 80)
    
    for model, info in model_analysis.items():
        needed = "是" if info['joint_solve_needed'] else "否"
        print(f"{model:<15} {info['coupling_strength']:<12} {needed:<8} {info['solve_strategy']}")
    
    print("-" * 80)
    
    # 创建分析图表
    plt.figure(figsize=(14, 10))
    
    # 耦合强度分布
    plt.subplot(2, 2, 1)
    coupling_counts = {}
    for info in model_analysis.values():
        strength = info['coupling_strength']
        coupling_counts[strength] = coupling_counts.get(strength, 0) + 1
    
    plt.pie(coupling_counts.values(), labels=coupling_counts.keys(), autopct='%1.1f%%')
    plt.title('降阶模型耦合强度分布')
    
    # 联立求解需求
    plt.subplot(2, 2, 2)
    joint_needed = sum(1 for info in model_analysis.values() if info['joint_solve_needed'])
    joint_not_needed = len(model_analysis) - joint_needed
    
    plt.pie([joint_needed, joint_not_needed], 
            labels=['需要联立求解', '无需联立求解'], 
            autopct='%1.1f%%',
            colors=['#ff6b6b', '#4ecdc4'])
    plt.title('联立求解需求分析')
    
    # 模型复杂度对比
    plt.subplot(2, 2, 3)
    models = list(model_analysis.keys())
    complexity_scores = [0, 1, 2, 4, 5]  # 复杂度评分
    
    plt.barh(models, complexity_scores, color=['green', 'yellow', 'orange', 'red', 'darkred'])
    plt.xlabel('复杂度评分')
    plt.title('模型计算复杂度对比')
    
    # 求解策略分类
    plt.subplot(2, 2, 4)
    strategy_counts = {}
    for info in model_analysis.values():
        strategy = '联立求解' if info['joint_solve_needed'] else '串行/并行求解'
        strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
    
    plt.bar(strategy_counts.keys(), strategy_counts.values(), 
            color=['#ff6b6b', '#4ecdc4'])
    plt.title('推荐求解策略分布')
    plt.ylabel('模型数量')
    
    plt.tight_layout()
    plt.savefig(project_root / 'results' / 'reduced_order_analysis.svg', dpi=300, bbox_inches='tight')
    plt.show()
    
    # 总结建议
    print("\n📋 降阶模型联立求解建议：")
    print("1. 强耦合模型（IDZ、圣维南）：必须联立求解")
    print("2. 中等耦合模型（蓄量演算）：可串行迭代求解")
    print("3. 弱耦合模型（马斯京干）：按拓扑顺序串行求解")
    print("4. 解耦模型（水量平衡）：完全并行求解")
    print("\n💡 自适应策略：根据耦合强度分布自动选择最优求解方式")


def main():
    """主演示程序"""
    print("🌊 WaterNet 水网整体系统演示程序")
    print("=" * 60)
    
    # 创建结果目录
    results_dir = project_root / 'results'
    results_dir.mkdir(exist_ok=True)
    
    try:
        # 1. 创建示例配置
        print("📁 创建示例水网配置...")
        config_path = create_sample_network_config()
        print(f"✓ 配置文件已创建: {config_path}")
        
        # 2. 加载水网系统
        print("\n🏗️ 加载水网系统...")
        network = WaterNetworkSystem(str(config_path))
        print("✓ 水网系统加载完成")
        
        # 输出系统概要
        summary = network.get_system_summary()
        print(f"   对象总数: {summary['total_objects']}")
        print(f"   网络复杂度: {summary['network_complexity']}")
        print(f"   求解策略: {summary['solution_strategy']}")
        
        # 3. 分析降阶模型联立求解需求（理论分析）
        analyze_reduced_order_coupling()
        
        # 4. 耦合强度分析
        coupling_strengths = demonstrate_coupling_analysis(network)
        
        # 5. 求解策略比较
        performance_results = compare_solution_strategies(network)
        
        # 6. 数字孪生演示
        demonstrate_digital_twin(network)
        
        print("\n" + "="*60)
        print("✅ 演示程序执行完成！")
        print("📊 结果图表已保存到 results/ 目录")
        print("="*60)
        
    except Exception as e:
        logger.error(f"演示程序执行失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()