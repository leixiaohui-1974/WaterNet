"""
马斯京干模型理论基础和稳态分析

深入分析马斯京干模型的理论基础：
1. 作为圣维南方程的线性化简化
2. 稳态点的物理含义
3. 初始蓄量的意义和计算
4. 与圣维南方程的关系

Author: WaterNet Development Team
Date: 2024-10-04
"""

import numpy as np
from waternet.models.lumped_models import MuskingumModel


def analyze_muskingum_theory():
    """分析马斯京干模型的理论基础"""
    print("=" * 80)
    print("马斯京干模型理论基础分析")
    print("=" * 80)
    
    # 1. 马斯京干模型的理论基础
    print("\\n1. 马斯京干模型的理论基础")
    print("-" * 50)
    print("马斯京干模型是圣维南方程的线性化简化形式：")
    print("• 圣维南方程组（非线性偏微分方程）：")
    print("  连续性: ∂A/∂t + ∂Q/∂x = 0")
    print("  动量:   ∂Q/∂t + ∂(Q²/A)/∂x + gA∂H/∂x = gA(S₀ - Sf)")
    print("\\n• 马斯京干简化（线性常微分方程）：")
    print("  假设: 惯性项忽略，压力项线性化")
    print("  结果: Q_out = C₀×Q_in + C₁×Q_in_prev + C₂×Q_out_prev")
    
    # 2. 稳态分析
    print("\\n2. 马斯京干模型的稳态点")
    print("-" * 50)
    
    # 创建示例模型
    def V_to_H_func(V):
        return 100.0 + V / 10000.0
    
    def H_to_Q_func(H):
        return max(0.0, (H - 100.0) * 25.0)
    
    model = MuskingumModel(
        dt=60.0, K=3600.0, x=0.2, initial_V=15000.0,
        V_to_H_func=V_to_H_func, H_to_Q_func=H_to_Q_func,
        name="Theory_Analysis"
    )
    
    print(f"模型参数: K={model.K}s, x={model.x}")
    print(f"马斯京干系数: C₀={model.C0:.4f}, C₁={model.C1:.4f}, C₂={model.C2:.4f}")
    print(f"系数验证: C₀+C₁+C₂ = {model.C0+model.C1+model.C2:.6f} (应该=1)")
    
    # 稳态条件分析
    print("\\n稳态条件分析:")
    print("当 Q_in = Q_out = Q_steady 时：")
    print("Q_steady = C₀×Q_steady + C₁×Q_steady + C₂×Q_steady")
    print("Q_steady = (C₀ + C₁ + C₂) × Q_steady = 1 × Q_steady")
    print("✓ 稳态点：任何恒定入流下，最终出流都等于入流")
    
    # 验证稳态特性
    steady_flows = [5.0, 10.0, 15.0, 20.0, 25.0]
    print("\\n稳态验证:")
    print("恒定入流(m³/s)  最终出流(m³/s)  相对误差(%)")
    print("-" * 50)
    
    for Q_steady in steady_flows:
        # 运行长时间仿真达到稳态
        Q_series = np.ones(100) * Q_steady
        results = model.run_simulation(Q_series)
        final_Q_out = results['Q_out'].iloc[-1]
        error_percent = abs(final_Q_out - Q_steady) / Q_steady * 100
        
        print(f"{Q_steady:13.1f}  {final_Q_out:13.1f}  {error_percent:10.3f}")
        
        # 重置模型为下次计算
        model.reset()
    
    return model


def analyze_initial_volume_meaning():
    """分析初始蓄量的物理含义"""
    print("\\n\\n3. 初始蓄量的物理含义")
    print("-" * 50)
    
    print("在马斯京干模型中，初始蓄量的作用：")
    print("• 建立V-H关系的起点")
    print("• 确定初始水位和出流")
    print("• 影响过渡过程的响应特性")
    print("• 但不影响最终稳态值")
    
    # 创建不同初始蓄量的模型
    def V_to_H_func(V):
        return 100.0 + V / 10000.0
    
    def H_to_Q_func(H):
        return max(0.0, (H - 100.0) * 25.0)
    
    initial_volumes = [5000.0, 15000.0, 25000.0]
    models = []
    
    for V_init in initial_volumes:
        model = MuskingumModel(
            dt=60.0, K=3600.0, x=0.2, initial_V=V_init,
            V_to_H_func=V_to_H_func, H_to_Q_func=H_to_Q_func,
            name=f"V_init_{V_init}"
        )
        models.append(model)
    
    # 分析初始状态
    print("\\n不同初始蓄量的影响:")
    print("初始蓄量(m³)  初始水位(m)  初始出流(m³/s)")
    print("-" * 48)
    
    for i, (V_init, model) in enumerate(zip(initial_volumes, models)):
        initial_H = model.current_H
        initial_Q = model.current_Q_out
        print(f"{V_init:11.0f}  {initial_H:11.3f}  {initial_Q:13.3f}")
    
    # 测试过渡过程
    print("\\n过渡过程分析 (阶跃输入从0到20 m³/s):")
    Q_step = np.concatenate([np.zeros(10), np.ones(90) * 20.0])
    
    all_results = []
    for model in models:
        results = model.run_simulation(Q_step)
        all_results.append(results)
        model.reset()  # 重置模型
    
    # 分析过渡过程特性
    print("初始蓄量(m³)  响应时间(min)  最终出流(m³/s)")
    print("-" * 48)
    
    for i, (V_init, results) in enumerate(zip(initial_volumes, all_results)):
        # 计算90%响应时间
        final_Q = results['Q_out'].iloc[-1]
        target_Q = 0.9 * final_Q
        
        response_index = np.where(results['Q_out'] >= target_Q)[0]
        if len(response_index) > 0:
            response_time = results['time'].iloc[response_index[0]] / 60.0
        else:
            response_time = np.inf
        
        print(f"{V_init:11.0f}  {response_time:11.1f}  {final_Q:13.3f}")
    
    return all_results


def compare_with_saint_venant():
    """与圣维南模型对比分析"""
    print("\\n\\n4. 与圣维南模型的关系")
    print("-" * 50)
    
    print("马斯京干模型的简化假设:")
    print("• 忽略惯性项: ∂Q/∂t ≈ 0")
    print("• 忽略对流项: ∂(Q²/A)/∂x ≈ 0") 
    print("• 线性化压力项: gA∂H/∂x → 线性关系")
    print("• 简化摩阻项: Sf ≈ 常数梯度")
    
    print("\\n适用条件:")
    print("• 河道坡度较缓 (S₀ < 0.002)")
    print("• 弗劳德数较小 (Fr < 0.5)")
    print("• 流量变化相对缓慢")
    print("• 河道几何相对均匀")
    
    print("\\n马斯京干参数的物理意义:")
    print("• K (滞时常数): 洪峰传播时间，单位：秒")
    print("  K ≈ L/c (河段长度/波速)")
    print("• x (权重系数): 楔形蓄量的影响，0 ≤ x ≤ 0.5")
    print("  x=0: 纯水库效应")
    print("  x=0.5: 纯传播效应")
    
    # 从圣维南模型反推马斯京干参数
    print("\\n从圣维南模型反推马斯京干参数的方法:")
    print("1. 恒定流法计算不同流量下的传播时间 → K")
    print("2. 洪水演进对比分析优化 → x")
    print("3. 参数估计算法自动标定")


def analyze_volume_calculation_in_muskingum():
    """分析马斯京干模型中蓄量计算的简化"""
    print("\\n\\n5. 马斯京干模型中蓄量计算的简化")
    print("-" * 50)
    
    print("马斯京干模型的蓄量处理方式:")
    print("• 原始马斯京干: 只计算流量，不直接计算水位和蓄量")
    print("• 本框架增强: 通过V-H和H-Q关系维持物理一致性")
    print("• 连续性约束: dV/dt = Q_in - Q_out")
    
    # 演示蓄量更新过程
    def V_to_H_func(V):
        return 100.0 + V / 10000.0
    
    def H_to_Q_func(H):
        return max(0.0, (H - 100.0) * 25.0)
    
    model = MuskingumModel(
        dt=60.0, K=1800.0, x=0.3, initial_V=12000.0,
        V_to_H_func=V_to_H_func, H_to_Q_func=H_to_Q_func,
        name="Volume_Analysis"
    )
    
    print(f"\\n初始状态:")
    print(f"蓄量: {model.current_V:.0f} m³")
    print(f"水位: {model.current_H:.3f} m")
    print(f"出流: {model.current_Q_out:.3f} m³/s")
    
    # 单步演示
    Q_in = 15.0
    result = model.step(Q_in)
    
    print(f"\\n单步演进后 (Q_in = {Q_in} m³/s):")
    print(f"蓄量: {result['V']:.0f} m³")
    print(f"水位: {result['H_out']:.3f} m")
    print(f"出流: {result['Q_out']:.3f} m³/s")
    
    # 显示蓄量更新的步骤
    print(f"\\n蓄量更新机制:")
    print(f"1. 马斯京干公式计算出流: Q_out = {result['Q_out']:.3f} m³/s")
    print(f"2. 连续性方程更新蓄量: dV = (Q_in - Q_out) × dt")
    print(f"3. V-H关系计算水位: H = f(V)")
    print(f"4. 保持物理一致性检查")
    
    print("\\n这种处理方式的优缺点:")
    print("优点:")
    print("• 计算简单高效")
    print("• 参数物理意义明确")
    print("• 稳定性好")
    print("缺点:")
    print("• 精度相对较低")
    print("• 几何形状简化")
    print("• 不能反映复杂水力现象")


def main():
    """主分析函数"""
    try:
        # 理论基础分析
        model = analyze_muskingum_theory()
        
        # 初始蓄量含义分析
        results = analyze_initial_volume_meaning()
        
        # 与圣维南模型对比
        compare_with_saint_venant()
        
        # 蓄量计算简化分析
        analyze_volume_calculation_in_muskingum()
        
        print("\\n" + "=" * 80)
        print("总结：马斯京干模型的核心要点")
        print("=" * 80)
        print("1. 稳态点：任何恒定入流下，最终出流等于入流 (质量守恒)")
        print("2. 初始蓄量：确定起始状态，影响过渡过程，不影响稳态")
        print("3. 线性化简化：忽略惯性和对流项，适用于缓坡河道")
        print("4. 参数意义：K反映传播时间，x反映楔形蓄量影响")
        print("5. 计算效率：相比圣维南方程大幅简化，计算速度快")
        print("\\n基于记忆的Q-H耦合改进使模型更加符合物理实际！")
        
    except Exception as e:
        print(f"分析过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()