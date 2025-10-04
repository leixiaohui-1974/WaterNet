"""
康吉法与IDZ模型深入对比分析

详细分析马斯京干-康吉法与IDZ模型的理论差异、建模哲学和应用场景。

Author: WaterNet Development Team
Date: 2024-10-04
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

import numpy as np
from waternet.models.lumped_models import IntegralDelayZeroModel, MuskingumModel
from waternet.models.muskingum_cunge import MuskingumCungeModel, ChannelGeometry, FlowConditions


def analyze_theoretical_foundations():
    """分析理论基础差异"""
    print("=" * 80)
    print("康吉法与IDZ模型理论基础对比")
    print("=" * 80)
    
    print("\n1. 理论推导路径对比")
    print("-" * 60)
    
    print("🌊 马斯京干-康吉法:")
    print("推导路径: 圣维南方程 → 扩散波近似 → 康吉参数推导 → 马斯京干形式")
    print("理论基础: 扩散波理论（连续性方程 + 简化动量方程）")
    print("物理假设: 忽略惯性项，重力≈摩阻（接近均匀流）")
    print("参数意义: K=Δx/c（波传播时间），x=扩散系数")
    
    print("\n🎛️ IDZ模型:")
    print("推导路径: 系统响应理论 → 传递函数设计 → 时域实现")
    print("理论基础: 控制系统理论（传递函数G(s) = (τs+1)e^(-Ts)/(s(αs+1))）")
    print("物理假设: 线性时不变系统，输入-输出关系")
    print("参数意义: τ(零点)、T(延迟)、α(极点) - 系统动态特性")
    
    print("\n2. 建模哲学差异")
    print("-" * 60)
    
    philosophy_comparison = """
    +-------------------+----------------------+------------------------+
    | 建模方面          | 康吉法               | IDZ模型                |
    +-------------------+----------------------+------------------------+
    | 理论起源          | 水力学扩散波理论     | 控制系统传递函数       |
    | 物理基础          | 明确（均匀流近似）   | 抽象（系统响应特性）   |
    | 参数来源          | 河道几何计算         | 系统辨识或经验确定     |
    | 适用对象          | 天然河道水流         | 一般线性系统           |
    | 精度特点          | 中等（扩散波限制）   | 高（灵活传递函数）     |
    | 计算复杂度        | 中等（需水力计算）   | 高（状态空间实现）     |
    | 参数调整          | 基于几何改变         | 基于响应特性调整       |
    +-------------------+----------------------+------------------------+
    """
    print(philosophy_comparison)


def demonstrate_parameter_relationships():
    """演示参数关系和转换"""
    print("\n3. 参数关系与转换分析")
    print("-" * 60)
    
    # 创建示例河道
    geometry = ChannelGeometry(
        length=2000.0, width=60.0, slope=0.0008, roughness=0.025
    )
    flow_conditions = FlowConditions(reference_discharge=120.0)
    
    # 创建物理关系函数
    def V_to_H_func(V):
        return 98.0 + V / 8000.0
    
    def H_to_Q_func(H):
        return max(0.0, (H - 98.0) * 30.0) ** 1.2
    
    # 康吉法模型
    cunge_model = MuskingumCungeModel(
        dt=60.0, geometry=geometry, flow_conditions=flow_conditions,
        initial_V=18000.0, V_to_H_func=V_to_H_func, H_to_Q_func=H_to_Q_func
    )
    
    # 获取康吉参数
    cunge_info = cunge_model.get_model_info()
    K_cunge = cunge_info['current_parameters']['K']
    x_cunge = cunge_info['current_parameters']['x']
    
    print(f"康吉法参数:")
    print(f"K = {K_cunge:.1f} s (波传播时间)")
    print(f"x = {x_cunge:.3f} (扩散系数)")
    
    # 基于项目记忆的参数转换关系
    print(f"\n基于参数转换关系的IDZ近似参数:")
    alpha_approx = K_cunge  # K≈α（主导时间常数）
    tau_approx = x_cunge * alpha_approx  # x效应≈τ/α
    T_delay_approx = K_cunge * 0.3  # 传播延迟≈T（经验关系）
    
    print(f"α ≈ {alpha_approx:.1f} s (近似主导时间常数)")
    print(f"τ ≈ {tau_approx:.1f} s (近似零点时间常数)")
    print(f"T ≈ {T_delay_approx:.1f} s (近似传播延迟)")
    
    # 创建近似IDZ模型
    idz_model = IntegralDelayZeroModel(
        dt=60.0, tau=max(tau_approx, 100.0), T_delay=T_delay_approx, alpha=alpha_approx,
        initial_V=18000.0, V_to_H_func=V_to_H_func, H_to_Q_func=H_to_Q_func
    )
    
    print(f"\n⚠️ 参数转换的局限性:")
    print(f"• 转换关系具有近似性，需结合实际工况调整")
    print(f"• 康吉法基于物理计算，IDZ基于系统响应特性")
    print(f"• 不同建模哲学导致参数物理意义不完全对应")
    
    return cunge_model, idz_model


def compare_response_characteristics(cunge_model, idz_model):
    """对比响应特性"""
    print("\n4. 系统响应特性对比")
    print("-" * 60)
    
    # 设计测试信号
    # 阶跃响应测试
    step_input = np.concatenate([
        np.ones(10) * 50.0,  # 基础流量
        np.ones(20) * 150.0,  # 阶跃增加
        np.ones(20) * 50.0   # 回落
    ])
    
    # 运行仿真
    cunge_results = cunge_model.run_simulation(step_input)
    idz_results = idz_model.run_simulation(step_input)
    
    # 分析响应特性
    print("阶跃响应分析 (50→150→50 m³/s):")
    
    # 稳态增益
    steady_gain_cunge = cunge_results['Q_out'].iloc[-5:].mean() / step_input[-1]
    steady_gain_idz = idz_results['Q_out'].iloc[-5:].mean() / step_input[-1]
    
    # 峰值响应
    peak_cunge = cunge_results['Q_out'].max()
    peak_idz = idz_results['Q_out'].max()
    
    # 峰值时间
    peak_time_cunge = cunge_results['Q_out'].idxmax()
    peak_time_idz = idz_results['Q_out'].idxmax()
    
    print(f"\n响应特性对比:")
    print(f"{'指标':<15} {'康吉法':<15} {'IDZ模型':<15}")
    print("-" * 50)
    print(f"{'稳态增益':<15} {steady_gain_cunge:<15.3f} {steady_gain_idz:<15.3f}")
    print(f"{'峰值出流':<15} {peak_cunge:<15.1f} {peak_idz:<15.1f}")
    print(f"{'峰值时间':<15} {peak_time_cunge:<15d} {peak_time_idz:<15d}")
    
    # 超调和振荡分析
    overshoot_cunge = (peak_cunge - step_input[30]) / step_input[30] * 100
    overshoot_idz = (peak_idz - step_input[30]) / step_input[30] * 100
    
    print(f"{'超调量(%)':<15} {overshoot_cunge:<15.1f} {overshoot_idz:<15.1f}")
    
    print(f"\n🔍 响应特性分析:")
    print(f"• 康吉法: 基于扩散波理论，响应相对平滑")
    print(f"• IDZ模型: 传递函数设计，可能出现超调或振荡")
    print(f"• 稳态性能: 两者最终都满足质量守恒")
    print(f"• 动态性能: IDZ模型可通过参数调整获得更复杂的动态特性")


def analyze_applicability_and_limitations():
    """分析适用性和局限性"""
    print("\n5. 适用性与局限性分析")
    print("-" * 60)
    
    applicability_analysis = """
    🌊 马斯京干-康吉法:
    
    ✅ 适用场景:
    • 天然河道洪水演算
    • 具有明确几何参数的渠道
    • 需要物理参数可解释性的场合
    • 扩散占主导的流动过程
    • 中等精度要求的工程应用
    
    ❌ 局限性:
    • 仍受线性化假设限制
    • 忽略惯性项，不适用于快速变化流
    • 对河道几何规则性有要求
    • 扩散波假设在某些条件下不成立
    • 参数固定，难以适应复杂非线性响应
    
    🎛️ IDZ模型:
    
    ✅ 适用场景:
    • 需要精确系统动态特性建模
    • 控制系统设计和分析
    • 复杂的输入-输出响应关系
    • 系统辨识和参数优化
    • 高精度要求的仿真分析
    
    ❌ 局限性:
    • 参数缺乏直观的物理意义
    • 需要系统辨识或经验确定参数
    • 计算复杂度相对较高
    • 过度拟合风险（参数过多）
    • 对于简单系统可能过于复杂
    """
    
    print(applicability_analysis)
    
    print("\n📊 选择决策指南:")
    decision_matrix = """
    +------------------+------------------+------------------+
    | 考虑因素         | 康吉法           | IDZ模型          |
    +------------------+------------------+------------------+
    | 物理可解释性     | 高（明确物理基础）| 低（抽象数学模型）|
    | 参数获取难度     | 低（几何计算）   | 高（系统辨识）   |
    | 模型精度         | 中等             | 高               |
    | 计算复杂度       | 中等             | 高               |
    | 适用范围         | 水力学专门领域   | 通用系统理论     |
    | 参数调整灵活性   | 低（受物理约束） | 高（数学优化）   |
    +------------------+------------------+------------------+
    """
    print(decision_matrix)


def demonstrate_hybrid_approach():
    """演示混合方法"""
    print("\n6. 混合建模方法探讨")
    print("-" * 60)
    
    print("🔄 康吉法-IDZ混合建模思路:")
    print("\n方法1: 康吉法初始化 + IDZ精化")
    print("• 步骤1: 用康吉法计算物理合理的初始参数")
    print("• 步骤2: 将康吉参数转换为IDZ参数作为起始值")
    print("• 步骤3: 基于观测数据优化IDZ参数")
    print("• 优点: 结合物理基础和系统优化能力")
    
    print("\n方法2: 分段建模策略")
    print("• 恒定流阶段: 使用康吉法（物理明确）")
    print("• 非恒定流阶段: 切换到IDZ模型（动态精确）")
    print("• 过渡处理: 平滑切换机制")
    print("• 优点: 充分利用各自优势")
    
    print("\n方法3: 集成预测系统")
    print("• 康吉法: 提供物理约束和先验知识")
    print("• IDZ模型: 处理复杂动态响应")
    print("• 权重融合: 基于置信度动态调整")
    print("• 优点: 提高预测鲁棒性")


def main():
    """主分析函数"""
    try:
        print("🔄 康吉法与IDZ模型深入对比分析")
        
        # 理论基础分析
        analyze_theoretical_foundations()
        
        # 参数关系演示
        cunge_model, idz_model = demonstrate_parameter_relationships()
        
        # 响应特性对比
        compare_response_characteristics(cunge_model, idz_model)
        
        # 适用性分析
        analyze_applicability_and_limitations()
        
        # 混合方法探讨
        demonstrate_hybrid_approach()
        
        print("\n" + "=" * 80)
        print("🎯 核心结论：康吉法与IDZ模型的本质差异")
        print("=" * 80)
        
        print("1. 🏗️ 建模哲学:")
        print("   • 康吉法: 物理驱动（扩散波理论）")
        print("   • IDZ模型: 数学驱动（传递函数理论）")
        
        print("\n2. 🔧 参数特征:")
        print("   • 康吉法: 参数可从几何计算，物理意义明确")
        print("   • IDZ模型: 参数需系统辨识，数学意义抽象")
        
        print("\n3. 🎯 应用场景:")
        print("   • 康吉法: 天然河道，物理约束明确")
        print("   • IDZ模型: 复杂系统，动态特性重要")
        
        print("\n4. 🔄 发展方向:")
        print("   • 混合建模: 结合两者优势")
        print("   • 自适应选择: 根据条件动态切换")
        print("   • 参数转换: 建立更精确的映射关系")
        
        print("\n💡 两种方法代表了不同的建模思路:")
        print("康吉法强调物理真实性，IDZ模型强调数学灵活性！")
        
    except Exception as e:
        print(f"分析过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()