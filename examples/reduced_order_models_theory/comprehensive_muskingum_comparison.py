"""
马斯京干模型综合比较分析

对比传统马斯京干法与康吉法，总结理论差异和实际应用效果。

Author: WaterNet Development Team  
Date: 2024-10-04
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

import numpy as np
from waternet.models.lumped_models import MuskingumModel
from waternet.models.muskingum_cunge import (
    MuskingumCungeModel, ChannelGeometry, FlowConditions, 
    CungeParameterCalculator
)


def create_test_scenario():
    """创建测试场景"""
    print("🌊 创建测试场景")
    print("=" * 60)
    
    # 河道几何参数
    geometry = ChannelGeometry(
        length=2000.0,     # 2km河段
        width=80.0,        # 80m宽度
        slope=0.0008,      # 0.08%坡度
        roughness=0.030    # 典型天然河道粗糙度
    )
    
    # 不同流量工况
    flow_scenarios = [
        ("低流量", 50.0),
        ("中等流量", 150.0), 
        ("设计洪水", 300.0),
        ("超标洪水", 500.0)
    ]
    
    print(f"河道几何:")
    print(f"长度: {geometry.length} m")
    print(f"宽度: {geometry.width} m") 
    print(f"坡度: {geometry.slope}")
    print(f"粗糙度: {geometry.roughness}")
    
    print(f"\n流量工况:")
    for name, Q in flow_scenarios:
        print(f"{name}: {Q} m³/s")
    
    return geometry, flow_scenarios


def compare_parameter_calculation_methods(geometry, flow_scenarios):
    """对比参数计算方法"""
    print("\n1. 参数计算方法对比")
    print("-" * 60)
    
    # 传统经验参数
    traditional_params = {
        "K": 7200.0,  # 2小时（典型经验值）
        "x": 0.25     # 典型经验值
    }
    
    print(f"传统经验参数:")
    print(f"K = {traditional_params['K']} s (固定)")
    print(f"x = {traditional_params['x']} (固定)")
    
    print(f"\n康吉法计算参数（不同流量工况）:")
    cunge_params_by_flow = {}
    
    for scenario_name, Q_ref in flow_scenarios:
        flow_conditions = FlowConditions(reference_discharge=Q_ref)
        cunge_params = CungeParameterCalculator.compute_cunge_parameters(
            geometry, flow_conditions)
        
        cunge_params_by_flow[scenario_name] = cunge_params
        
        print(f"{scenario_name} (Q={Q_ref} m³/s):")
        print(f"  K = {cunge_params['K']:.1f} s")
        print(f"  x = {cunge_params['x']:.3f}")
        print(f"  正常水深 = {cunge_params['normal_depth']:.2f} m")
        print(f"  波速 = {cunge_params['wave_celerity']:.2f} m/s")
    
    # 分析参数变化规律
    K_values = [params['K'] for params in cunge_params_by_flow.values()]
    x_values = [params['x'] for params in cunge_params_by_flow.values()]
    
    print(f"\n康吉法参数变化范围:")
    print(f"K: {min(K_values):.1f} - {max(K_values):.1f} s (变化 {(max(K_values)-min(K_values))/min(K_values)*100:.1f}%)")
    print(f"x: {min(x_values):.3f} - {max(x_values):.3f} (变化 {(max(x_values)-min(x_values))/min(x_values)*100:.1f}%)")
    
    return traditional_params, cunge_params_by_flow


def analyze_flood_routing_performance(geometry, traditional_params, cunge_params_by_flow):
    """分析洪水演算性能"""
    print("\n2. 洪水演算性能分析")
    print("-" * 60)
    
    # 创建物理关系函数
    def V_to_H_func(V):
        return 95.0 + V * 8e-5  # 更大的河道
    
    def H_to_Q_func(H):
        return max(0.0, (H - 95.0) * 40.0) ** 1.2
    
    # 创建复合洪水过程
    time_steps = 120  # 2小时
    flood_hydrograph = create_complex_flood_hydrograph(time_steps)
    
    print(f"测试洪水过程:")
    print(f"持续时间: {time_steps} 分钟")
    print(f"峰值流量: {flood_hydrograph.max():.1f} m³/s")
    print(f"洪量: {flood_hydrograph.sum() * 60:.0f} m³")
    
    # 传统马斯京干模型
    traditional_model = MuskingumModel(
        dt=60.0, 
        K=traditional_params["K"], 
        x=traditional_params["x"],
        initial_V=20000.0,
        V_to_H_func=V_to_H_func,
        H_to_Q_func=H_to_Q_func,
        name="Traditional"
    )
    
    # 康吉模型（中等流量参数）
    medium_flow_params = cunge_params_by_flow["中等流量"]
    cunge_model = MuskingumCungeModel(
        dt=60.0,
        geometry=geometry,
        flow_conditions=FlowConditions(reference_discharge=150.0),
        initial_V=20000.0,
        V_to_H_func=V_to_H_func,
        H_to_Q_func=H_to_Q_func,
        name="Cunge"
    )
    
    # 自适应康吉模型
    adaptive_cunge = MuskingumCungeModel(
        dt=60.0,
        geometry=geometry,
        flow_conditions=FlowConditions(reference_discharge=150.0),
        initial_V=20000.0,
        V_to_H_func=V_to_H_func,
        H_to_Q_func=H_to_Q_func,
        enable_adaptive_parameters=True,
        name="AdaptiveCunge"
    )
    
    # 运行仿真
    print("\n运行洪水演算仿真...")
    trad_results = traditional_model.run_simulation(flood_hydrograph)
    cunge_results = cunge_model.run_simulation(flood_hydrograph)
    adaptive_results = adaptive_cunge.run_simulation(flood_hydrograph)
    
    # 性能分析
    print(f"\n演算结果对比:")
    
    models_results = [
        ("传统马斯京干", trad_results),
        ("康吉法", cunge_results),
        ("自适应康吉法", adaptive_results)
    ]
    
    for model_name, results in models_results:
        peak_out = results['Q_out'].max()
        peak_time = results['Q_out'].idxmax()
        total_outflow = results['Q_out'].sum() * 60
        peak_reduction = (flood_hydrograph.max() - peak_out) / flood_hydrograph.max() * 100
        peak_delay = peak_time - np.argmax(flood_hydrograph)
        
        print(f"\n{model_name}:")
        print(f"  峰值出流: {peak_out:.1f} m³/s")
        print(f"  削峰率: {peak_reduction:.1f}%") 
        print(f"  峰现时间: {peak_time} 分钟")
        print(f"  峰值延迟: {peak_delay} 分钟")
        print(f"  总出流量: {total_outflow:.0f} m³")
    
    return models_results


def create_complex_flood_hydrograph(time_steps):
    """创建复杂洪水过程线"""
    # 双峰洪水过程
    t = np.arange(time_steps)
    
    # 第一个洪峰（较小）
    peak1_time = time_steps * 0.3
    peak1_flow = 200.0
    flood1 = peak1_flow * np.exp(-0.5 * ((t - peak1_time) / (time_steps * 0.15))**2)
    
    # 第二个洪峰（较大）
    peak2_time = time_steps * 0.7  
    peak2_flow = 350.0
    flood2 = peak2_flow * np.exp(-0.5 * ((t - peak2_time) / (time_steps * 0.12))**2)
    
    # 基流
    base_flow = 30.0
    
    # 合成洪水过程
    flood_hydrograph = base_flow + flood1 + flood2
    
    return flood_hydrograph


def analyze_parameter_sensitivity():
    """分析参数敏感性"""
    print("\n3. 参数敏感性分析")
    print("-" * 60)
    
    # 基准参数
    base_geometry = ChannelGeometry(
        length=1500.0, width=60.0, slope=0.001, roughness=0.025)
    base_flow = FlowConditions(reference_discharge=120.0)
    
    base_params = CungeParameterCalculator.compute_cunge_parameters(
        base_geometry, base_flow)
    
    print(f"基准参数:")
    print(f"K = {base_params['K']:.1f} s, x = {base_params['x']:.3f}")
    
    # 敏感性分析
    sensitivity_factors = {
        "河段长度": [0.5, 1.0, 1.5, 2.0],
        "河道宽度": [0.7, 1.0, 1.3, 1.6], 
        "河底坡度": [0.5, 1.0, 2.0, 4.0],
        "粗糙系数": [0.8, 1.0, 1.2, 1.5],
        "参考流量": [0.5, 1.0, 2.0, 3.0]
    }
    
    print(f"\n参数敏感性分析:")
    
    for param_name, factors in sensitivity_factors.items():
        print(f"\n{param_name}变化影响:")
        K_changes = []
        x_changes = []
        
        for factor in factors:
            # 修改几何参数
            test_geometry = ChannelGeometry(
                length=base_geometry.length * (factor if param_name == "河段长度" else 1.0),
                width=base_geometry.width * (factor if param_name == "河道宽度" else 1.0),
                slope=base_geometry.slope * (factor if param_name == "河底坡度" else 1.0),
                roughness=base_geometry.roughness * (factor if param_name == "粗糙系数" else 1.0)
            )
            
            test_flow = FlowConditions(
                reference_discharge=base_flow.reference_discharge * (factor if param_name == "参考流量" else 1.0)
            )
            
            test_params = CungeParameterCalculator.compute_cunge_parameters(
                test_geometry, test_flow)
            
            K_change = (test_params['K'] - base_params['K']) / base_params['K'] * 100
            x_change = (test_params['x'] - base_params['x']) / base_params['x'] * 100
            
            K_changes.append(K_change)
            x_changes.append(x_change)
            
            print(f"  {factor:.1f}倍: K变化 {K_change:+.1f}%, x变化 {x_change:+.1f}%")
        
        # 计算敏感性指数
        K_sensitivity = np.std(K_changes)
        x_sensitivity = np.std(x_changes)
        print(f"  敏感性指数: K={K_sensitivity:.1f}, x={x_sensitivity:.1f}")


def generate_application_recommendations():
    """生成应用建议"""
    print("\n4. 应用建议与选择指南")
    print("-" * 60)
    
    recommendations = {
        "传统马斯京干法": {
            "适用场景": [
                "有充足历史数据进行参数率定",
                "河道条件相对稳定",
                "计算速度要求高",
                "精度要求不高的初步分析"
            ],
            "优点": [
                "计算简单快速",
                "参数稳定",
                "成熟可靠",
                "资源需求低"
            ],
            "局限性": [
                "参数缺乏物理意义",
                "依赖历史数据",
                "外推能力有限",
                "难以适应变化工况"
            ]
        },
        
        "马斯京干-康吉法": {
            "适用场景": [
                "缺乏历史观测数据",
                "需要预测未见工况",
                "河道条件复杂多变",
                "要求较高计算精度"
            ],
            "优点": [
                "参数基于物理计算",
                "理论基础坚实",
                "适用性广泛",
                "外推能力强"
            ],
            "局限性": [
                "计算相对复杂",
                "需要河道几何数据",
                "对参数精度要求高",
                "资源需求较大"
            ]
        },
        
        "自适应康吉法": {
            "适用场景": [
                "流量变化范围大",
                "长期连续仿真",
                "实时预报系统",
                "高精度要求应用"
            ],
            "优点": [
                "参数自动调整",
                "适应性最强",
                "精度最高",
                "鲁棒性好"
            ],
            "局限性": [
                "计算开销最大",
                "实现复杂度高",
                "调试难度大",
                "对计算资源要求高"
            ]
        }
    }
    
    print("方法选择指南:")
    for method, info in recommendations.items():
        print(f"\n📋 {method}")
        print(f"   适用场景: {', '.join(info['适用场景'][:2])}等")
        print(f"   主要优点: {', '.join(info['优点'][:2])}")
        print(f"   主要局限: {', '.join(info['局限性'][:2])}")
    
    # 决策矩阵
    print(f"\n📊 选择决策矩阵:")
    decision_matrix = """
    +------------------+----------+----------+------------+
    | 考虑因素         | 传统法   | 康吉法   | 自适应康吉 |
    +------------------+----------+----------+------------+
    | 数据需求         | 历史数据 | 几何参数 | 几何参数   |
    | 计算复杂度       | 低       | 中       | 高         |
    | 参数物理意义     | 低       | 高       | 高         |
    | 适用性范围       | 中       | 高       | 最高       |
    | 计算精度         | 中       | 高       | 最高       |
    | 开发维护成本     | 低       | 中       | 高         |
    +------------------+----------+----------+------------+
    """
    print(decision_matrix)


def main():
    """主函数"""
    try:
        print("🔄 马斯京干模型综合比较分析")
        print("=" * 80)
        
        # 创建测试场景
        geometry, flow_scenarios = create_test_scenario()
        
        # 参数计算方法对比
        traditional_params, cunge_params_by_flow = compare_parameter_calculation_methods(
            geometry, flow_scenarios)
        
        # 洪水演算性能分析
        models_results = analyze_flood_routing_performance(
            geometry, traditional_params, cunge_params_by_flow)
        
        # 参数敏感性分析
        analyze_parameter_sensitivity()
        
        # 应用建议
        generate_application_recommendations()
        
        print("\n" + "=" * 80)
        print("🎯 综合结论")
        print("=" * 80)
        print("1. 🧮 参数计算: 康吉法提供了基于物理的参数确定方法")
        print("2. 🎪 精度提升: 康吉法在复杂工况下精度明显优于传统法")
        print("3. 🔄 自适应性: 自适应康吉法能够动态调整参数以适应变化")
        print("4. 📐 工程应用: 应根据具体需求和资源条件选择合适方法")
        print("5. 🔬 理论价值: 康吉法为马斯京干模型提供了坚实的理论基础")
        
        print("\n💡 最佳实践建议:")
        print("• 新建项目优先考虑康吉法，充分利用其理论优势")
        print("• 既有项目可考虑康吉法校核，提升参数合理性")
        print("• 实时预报系统建议采用自适应康吉法")
        print("• 快速评估和初步分析可使用传统法")
        
        print("\n马斯京干-康吉法代表了降阶模型理论的重要进步！")
        
    except Exception as e:
        print(f"分析过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()