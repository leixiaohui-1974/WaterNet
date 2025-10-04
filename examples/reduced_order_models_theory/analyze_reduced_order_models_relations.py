"""
降阶模型理论关系分析：IDZ、马斯京干和蓄量演算模型

深入分析三个降阶模型之间的理论关系：
1. IDZ模型与马斯京干模型的关系
2. 蓄量演算模型与其他两个模型的关系
3. 从系统理论角度的统一框架
4. 应用场景和选择准则

Author: WaterNet Development Team
Date: 2024-10-04
"""

import numpy as np
from waternet.models.lumped_models import (
    MuskingumModel, StorageRoutingModel, IntegralDelayZeroModel
)


def analyze_model_theoretical_relations():
    """分析三个降阶模型的理论关系"""
    print("=" * 80)
    print("降阶模型理论关系分析")
    print("=" * 80)
    
    print("\\n1. 系统理论视角下的模型分类")
    print("-" * 50)
    
    print("从系统理论角度，三个模型具有不同的理论基础：")
    print("\\n📊 马斯京干模型 (Muskingum):")
    print("• 理论基础: 圣维南方程的线性化简化")
    print("• 系统特性: 线性时不变系统 (LTI)")
    print("• 传递函数: 一阶惯性环节的离散化形式")
    print("• 物理本质: 河道的滞蓄和传播效应")
    
    print("\\n🔄 蓄量演算模型 (Storage Routing):")
    print("• 理论基础: 连续性方程 + 蓄泄关系")
    print("• 系统特性: 非线性系统 (依赖V-H, H-Q关系)")
    print("• 物理本质: 直接的水量平衡计算")
    print("• 适用范围: 水库、渠池等明显蓄水体")
    
    print("\\n⚡ IDZ模型 (Integral Delay Zero):")
    print("• 理论基础: 控制系统传递函数理论")
    print("• 系统特性: 包含积分、延迟、零点的复合系统")
    print("• 传递函数: G(s) = K(τs+1)e^(-Ts)/(s(αs+1))")
    print("• 物理本质: 系统动态响应的数学抽象")


def analyze_idz_muskingum_relation():
    """分析IDZ模型与马斯京干模型的关系"""
    print("\\n\\n2. IDZ模型与马斯京干模型的关系")
    print("-" * 50)
    
    print("🔗 理论联系:")
    print("• 都属于线性系统理论范畴")
    print("• 都可用传递函数描述")
    print("• 马斯京干可视为IDZ的特殊情况")
    
    print("\\n📐 数学关系:")
    print("马斯京干传递函数:  G_musk(s) ≈ K/(1 + Ks)")
    print("IDZ传递函数:       G_idz(s) = K(τs+1)e^(-Ts)/(s(αs+1))")
    print("\\n当IDZ参数满足特定条件时:")
    print("• τ → 0 (零点效应消失)")
    print("• T → 0 (延迟消失)")
    print("• 积分器1/s被近似为常数")
    print("• 则 G_idz → G_musk")
    
    # 数值验证这种关系
    print("\\n🧮 数值验证:")
    
    # 创建物理关系函数
    def V_to_H_func(V):
        return 100.0 + V / 10000.0
    
    def H_to_Q_func(H):
        return max(0.0, (H - 100.0) * 25.0)
    
    # 马斯京干模型
    muskingum = MuskingumModel(
        dt=60.0, K=1800.0, x=0.3, initial_V=15000.0,
        V_to_H_func=V_to_H_func, H_to_Q_func=H_to_Q_func,
        name="Muskingum_Analysis"
    )
    
    # IDZ模型 (调整参数使其接近马斯京干)
    idz = IntegralDelayZeroModel(
        dt=60.0, tau=100.0, T_delay=0.0, alpha=1800.0,  # α接近K
        initial_V=15000.0, V_to_H_func=V_to_H_func, H_to_Q_func=H_to_Q_func,
        name="IDZ_Analysis"
    )
    
    # 测试阶跃响应
    step_input = np.concatenate([np.zeros(10), np.ones(50) * 20.0])
    
    # 马斯京干响应
    musk_results = muskingum.run_simulation(step_input)
    muskingum.reset()
    
    # IDZ响应
    idz_results = idz.run_simulation(step_input)
    
    # 比较响应特性
    musk_final = musk_results['Q_out'].iloc[-10:].mean()
    idz_final = idz_results['Q_out'].iloc[-10:].mean()
    
    print(f"阶跃响应比较 (输入: 20 m³/s):")
    print(f"马斯京干最终值: {musk_final:.3f} m³/s")
    print(f"IDZ最终值:     {idz_final:.3f} m³/s")
    print(f"相对误差:      {abs(musk_final-idz_final)/20.0*100:.2f}%")
    
    return musk_results, idz_results


def analyze_storage_routing_relations():
    """分析蓄量演算与其他模型的关系"""
    print("\\n\\n3. 蓄量演算模型与其他模型的关系")
    print("-" * 50)
    
    print("🏗️ 与马斯京干的关系:")
    print("• 物理基础不同: 蓄量演算基于质量守恒，马斯京干基于线性化")
    print("• 非线性 vs 线性: 蓄量演算保留非线性特性")
    print("• 参数获取: 蓄量演算参数有明确物理意义")
    print("• 精度差异: 蓄量演算在大范围变化时更准确")
    
    print("\\n🔧 与IDZ的关系:")
    print("• 理论框架完全不同: 物理守恒 vs 系统响应")
    print("• 复杂度差异: 蓄量演算更直接，IDZ更抽象")
    print("• 参数标定: 蓄量演算基于测量，IDZ基于系统辨识")
    
    # 数值比较
    def V_to_H_func(V):
        return 100.0 + V / 10000.0
    
    def H_to_Q_func(H):
        return max(0.0, (H - 100.0) * 25.0)
    
    # 创建三个模型
    storage = StorageRoutingModel(
        dt=60.0, initial_V=15000.0,
        V_to_H_func=V_to_H_func, H_to_Q_func=H_to_Q_func,
        name="Storage_Analysis"
    )
    
    muskingum = MuskingumModel(
        dt=60.0, K=1800.0, x=0.2, initial_V=15000.0,
        V_to_H_func=V_to_H_func, H_to_Q_func=H_to_Q_func,
        name="Musk_Comparison"
    )
    
    idz = IntegralDelayZeroModel(
        dt=60.0, tau=600.0, T_delay=300.0, alpha=1500.0,
        initial_V=15000.0, V_to_H_func=V_to_H_func, H_to_Q_func=H_to_Q_func,
        name="IDZ_Comparison"
    )
    
    # 测试复杂输入
    complex_input = []
    for i in range(60):
        t = i * 60
        # 复合波形：基础流量 + 正弦变化 + 阶跃
        base_flow = 15.0
        sine_component = 5.0 * np.sin(2 * np.pi * t / 1800)  # 30分钟周期
        step_component = 10.0 if t > 1800 else 0.0  # 30分钟后阶跃
        Q = base_flow + sine_component + step_component
        complex_input.append(max(Q, 1.0))
    
    complex_input = np.array(complex_input)
    
    # 运行仿真
    storage_results = storage.run_simulation(complex_input)
    muskingum_results = muskingum.run_simulation(complex_input)
    idz_results = idz.run_simulation(complex_input)
    
    print("\\n📈 复杂输入响应比较:")
    print("模型类型        峰值出流(m³/s)  谷值出流(m³/s)  动态范围")
    print("-" * 60)
    
    models_data = [
        ("蓄量演算", storage_results),
        ("马斯京干", muskingum_results),
        ("IDZ模型", idz_results)
    ]
    
    for name, results in models_data:
        peak_flow = results['Q_out'].max()
        min_flow = results['Q_out'].min()
        dynamic_range = peak_flow - min_flow
        print(f"{name:10s}  {peak_flow:13.2f}  {min_flow:13.2f}  {dynamic_range:8.2f}")
    
    return storage_results, muskingum_results, idz_results


def analyze_unified_framework():
    """从系统理论角度分析统一框架"""
    print("\\n\\n4. 系统理论统一框架")
    print("-" * 50)
    
    print("🎯 统一的系统观:")
    print("三个模型都可以看作是从不同角度对同一物理系统的建模：")
    
    print("\\n1️⃣ 从简化程度看:")
    print("   水量平衡 < 马斯京干 < 蓄量演算 < IDZ < 圣维南")
    print("   (计算简单) ←→ (物理精确)")
    
    print("\\n2️⃣ 从参数获取看:")
    print("   • 蓄量演算: 直接测量 (V-H, H-Q关系)")
    print("   • 马斯京干: 洪水演进分析 (K, x参数)")
    print("   • IDZ: 系统辨识 (τ, T, α参数)")
    
    print("\\n3️⃣ 从适用条件看:")
    print("   • 蓄量演算: 明显蓄水特性，非线性关系重要")
    print("   • 马斯京干: 天然河道，线性假设合理")
    print("   • IDZ: 复杂动态特性，需要精确控制")
    
    print("\\n🔄 模型选择准则:")
    print("根据实际需求和数据条件选择合适的模型：")
    
    scenarios = [
        ("水库调洪演算", "蓄量演算", "V-H关系明确，非线性效应显著"),
        ("河道洪水预报", "马斯京干", "参数易获取，计算效率要求高"),
        ("精细控制分析", "IDZ", "需要准确描述系统动态特性"),
        ("快速工程估算", "水量平衡", "精度要求不高，计算简便")
    ]
    
    print("\\n应用场景        推荐模型    理由")
    print("-" * 55)
    for scenario, model, reason in scenarios:
        print(f"{scenario:12s}  {model:8s}  {reason}")


def demonstrate_parameter_relationships():
    """演示参数间的关系"""
    print("\\n\\n5. 参数间的物理关系")
    print("-" * 50)
    
    print("🔗 跨模型参数转换的可能性:")
    
    print("\\n马斯京干 → 蓄量演算:")
    print("• K (滞时常数) ←→ 河段特征时间")
    print("• x (权重系数) ←→ 楔形蓄量影响")
    print("• 可通过恒定流计算建立V-H关系")
    
    print("\\n蓄量演算 → IDZ:")
    print("• 蓄水体时间常数 ←→ α (极点时间常数)")
    print("• 入流延迟时间 ←→ T (纯延迟)")
    print("• 系统增益特性 ←→ τ (零点时间常数)")
    
    print("\\n马斯京干 → IDZ:")
    print("• K ≈ α (主导时间常数)")
    print("• x效应 ≈ τ/α (零极点比)")
    print("• 传播延迟 ≈ T")
    
    print("\\n⚠️ 转换的局限性:")
    print("• 参数转换是近似的，有一定误差")
    print("• 不同模型的适用条件不同")
    print("• 需要结合实际工程经验调整")


def theoretical_conclusions():
    """理论结论总结"""
    print("\\n\\n6. 理论结论与工程指导")
    print("-" * 50)
    
    print("📋 主要结论:")
    print("\\n1. 理论关系:")
    print("   • IDZ是最通用的形式，马斯京干是其特殊情况")
    print("   • 蓄量演算独立于前两者，基于物理守恒原理")
    print("   • 三者在特定条件下可以相互近似")
    
    print("\\n2. 选择策略:")
    print("   • 优先考虑物理意义明确的模型 (蓄量演算)")
    print("   • 数据充足时选择精度高的模型 (IDZ)")
    print("   • 工程应用中平衡精度与效率 (马斯京干)")
    
    print("\\n3. 发展方向:")
    print("   • 混合模型：结合不同模型的优点")
    print("   • 自适应模型：根据条件自动切换")
    print("   • 数据驱动：基于机器学习的参数优化")
    
    print("\\n🎯 基于项目记忆的优化:")
    print("   • 结合马斯京干模型线性化平衡点理论")
    print("   • 保持降阶模型物理一致性")
    print("   • 利用高性能计算优势 (28698时间步/秒)")


def main():
    """主分析函数"""
    try:
        # 理论关系分析
        analyze_model_theoretical_relations()
        
        # IDZ与马斯京干关系
        musk_results, idz_results = analyze_idz_muskingum_relation()
        
        # 蓄量演算关系分析
        storage_results, muskingum_results, idz_results = analyze_storage_routing_relations()
        
        # 统一框架分析
        analyze_unified_framework()
        
        # 参数关系演示
        demonstrate_parameter_relationships()
        
        # 理论结论
        theoretical_conclusions()
        
    except Exception as e:
        print(f"分析过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()