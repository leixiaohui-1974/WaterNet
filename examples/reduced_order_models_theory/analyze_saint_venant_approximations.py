"""
圣维南方程近似形式与线性化方法全面分析

深入探讨圣维南方程的各种近似形式及其对应的线性化方法，
构建完整的理论框架。

Author: WaterNet Development Team
Date: 2024-10-04
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

import numpy as np


def analyze_saint_venant_approximation_hierarchy():
    """分析圣维南方程近似层次"""
    print("=" * 80)
    print("圣维南方程近似形式层次结构")
    print("=" * 80)
    
    print("\n📐 圣维南方程完整形式:")
    print("连续性方程: ∂A/∂t + ∂Q/∂x = 0")
    print("动量方程: ∂Q/∂t + ∂(Q²/A)/∂x + gA∂h/∂x + gAS_f - gAS_0 = 0")
    print("其中: S_f = n²Q|Q|/(A²R^(4/3)) (摩阻坡度)")
    
    print("\n🎯 近似形式层次结构:")
    
    approximation_hierarchy = """
    完整圣维南方程 (Full Saint-Venant)
    ├── 忽略对流项 → 准静态波方程 (Quasi-static Wave)
    ├── 忽略惯性项 → 扩散波方程 (Diffusive Wave)
    │   ├── 线性化 → 康吉法 (Muskingum-Cunge)
    │   └── 集总化 → 蓄量演算 (Storage Routing)
    ├── 忽略摩阻项 → 运动波方程 (Kinematic Wave)
    │   ├── 线性化 → 线性运动波
    │   └── 特征线法 → 特征线运动波
    └── 全面线性化 → 线性圣维南方程
        ├── 传递矩阵法
        ├── 状态空间法
        └── 频域分析法
    """
    print(approximation_hierarchy)


def analyze_diffusive_wave_theory():
    """分析扩散波理论"""
    print("\n1. 扩散波方程详细分析")
    print("-" * 60)
    
    print("🌊 扩散波方程推导:")
    print("出发点: 圣维南动量方程")
    print("∂Q/∂t + ∂(Q²/A)/∂x + gA∂h/∂x + gAS_f - gAS_0 = 0")
    
    print("\n忽略惯性项: ∂Q/∂t 和 ∂(Q²/A)/∂x")
    print("简化为: gA∂h/∂x + gAS_f - gAS_0 = 0")
    print("即: ∂h/∂x = S_0 - S_f")
    
    print("\n结合连续性方程: ∂A/∂t + ∂Q/∂x = 0")
    print("假设宽矩形河道: A = Bh, 得到:")
    print("∂h/∂t + (1/B)∂Q/∂x = 0")
    
    print("\n引入曼宁公式: Q = (A*R^(2/3)*√S_f)/n")
    print("对于宽浅河道: R ≈ h, S_f = S_0 - ∂h/∂x")
    print("得到扩散波方程:")
    print("∂h/∂t = D∂²h/∂x² - c∂h/∂x")
    print("其中: D = Q/(2*B*S_0) (扩散系数)")
    print("      c = (5/3)*Q/A (波速)")
    
    print("\n🔍 扩散波方程的物理意义:")
    print("• 第一项: 局部变化率")
    print("• 第二项: 扩散效应（类似热传导）")
    print("• 第三项: 平移效应（对流项）")
    print("• 平衡了重力、摩阻和连续性效应")


def analyze_kinematic_wave_theory():
    """分析运动波理论"""
    print("\n2. 运动波方程详细分析")
    print("-" * 60)
    
    print("🏃 运动波方程推导:")
    print("进一步简化扩散波方程，忽略扩散项 D∂²h/∂x²")
    print("得到: ∂h/∂t + c∂h/∂x = 0")
    
    print("\n或写成流量形式:")
    print("∂A/∂t + ∂Q/∂x = 0 (连续性)")
    print("Q = Q(A) (单值关系，忽略回水效应)")
    
    print("\n代入连续性方程:")
    print("∂A/∂t + (dQ/dA)∂A/∂x = 0")
    print("∂A/∂t + c∂A/∂x = 0")
    print("其中 c = dQ/dA 为运动波波速")
    
    print("\n🎯 运动波的特点:")
    print("• 纯平移现象，无扩散")
    print("• 波形保持不变，只是平移")
    print("• 适用于陡坡河道")
    print("• 计算最简单")
    
    print("\n⚖️ 扩散波 vs 运动波对比:")
    comparison = """
    +------------------+------------------+------------------+
    | 特征             | 运动波           | 扩散波           |
    +------------------+------------------+------------------+
    | 物理过程         | 纯平移           | 平移+扩散        |
    | 数学形式         | 一阶偏微分方程   | 二阶偏微分方程   |
    | 波形变化         | 保持不变         | 逐渐平滑化       |
    | 适用坡度         | 陡坡 (S₀>0.002)  | 缓坡 (S₀<0.002)  |
    | 计算复杂度       | 低               | 中等             |
    | 物理真实性       | 较低             | 较高             |
    +------------------+------------------+------------------+
    """
    print(comparison)


def analyze_linearization_methods():
    """分析各种线性化方法"""
    print("\n3. 各种线性化方法详细分析")
    print("-" * 60)
    
    print("🔢 线性化方法分类:")
    
    print("\n3.1 扩散波线性化 → 康吉法")
    print("基准状态: 均匀流 (∂h/∂x = 0, Q = Q₀)")
    print("线性化: 在Q₀附近展开")
    print("结果: 马斯京干参数 K = Δx/c, x = 0.5(1-Q/(BSc Δx))")
    
    print("\n3.2 运动波线性化")
    print("基准状态: 恒定流 Q = Q₀")
    print("线性化: c = dQ/dA ≈ c₀ (常数)")
    print("结果: ∂A/∂t + c₀∂A/∂x = 0 (线性平移方程)")
    
    print("\n3.3 完整圣维南线性化")
    print("基准状态: 恒定均匀流 (Q₀, h₀)")
    print("线性化: 对所有非线性项进行泰勒展开")
    print("结果: 线性偏微分方程组，可用矩阵方法求解")
    
    print("\n3.4 准静态线性化")
    print("忽略: ∂Q/∂t 项（局部加速度）")
    print("保留: ∂(Q²/A)/∂x 项（对流加速度）")
    print("适用: 缓慢变化的非恒定流")
    
    linearization_summary = """
    📊 线性化方法特性对比:
    
    +------------------+------------------+------------------+------------------+
    | 线性化方法       | 理论基础         | 基准状态         | 主要应用         |
    +------------------+------------------+------------------+------------------+
    | 康吉法线性化     | 扩散波方程       | 均匀流           | 天然河道演算     |
    | 运动波线性化     | 运动波方程       | 恒定流           | 陡坡渠道         |
    | 圣维南线性化     | 完整圣维南       | 恒定均匀流       | 精确分析         |
    | 准静态线性化     | 忽略局部惯性     | 缓变流           | 长波分析         |
    +------------------+------------------+------------------+------------------+
    """
    print(linearization_summary)


def demonstrate_approximation_validity():
    """演示近似有效性分析"""
    print("\n4. 近似方法有效性分析")
    print("-" * 60)
    
    print("📏 近似有效性判据:")
    
    print("\n4.1 扩散波近似有效性")
    print("判据: 惯性项 << 重力项和摩阻项")
    print("数学表达: |∂Q/∂t|, |∂(Q²/A)/∂x| << gA|S₀|, gA|S_f|")
    print("工程判据: S₀ > 0.0001, Fr < 1.0")
    
    print("\n4.2 运动波近似有效性")
    print("判据: 扩散项 << 对流项")
    print("数学表达: |D∂²h/∂x²| << |c∂h/∂x|")
    print("工程判据: S₀ > 0.002, 河道相对陡峭")
    
    print("\n4.3 线性化有效性")
    print("判据: 变量偏离基准状态较小")
    print("数学表达: |Q-Q₀|/Q₀ < 0.3, |h-h₀|/h₀ < 0.2")
    print("工程判据: 在设计工况附近运行")
    
    # 数值示例
    print("\n📊 数值示例分析:")
    print("假设河道参数: B=50m, S₀=0.001, n=0.025, Q₀=100m³/s")
    
    # 计算特征参数
    h0 = (100 * 0.025 / (50 * np.sqrt(0.001))) ** (3/5)  # 正常水深
    V0 = 100 / (50 * h0)  # 流速
    Fr = V0 / np.sqrt(9.81 * h0)  # 弗劳德数
    c = (5/3) * V0  # 波速
    D = 100 / (2 * 50 * 0.001)  # 扩散系数
    
    print(f"正常水深 h₀ = {h0:.3f} m")
    print(f"平均流速 V₀ = {V0:.3f} m/s")
    print(f"弗劳德数 Fr = {Fr:.3f}")
    print(f"波速 c = {c:.3f} m/s")
    print(f"扩散系数 D = {D:.0f} m²/s")
    
    print(f"\n有效性评估:")
    if Fr < 0.5:
        print(f"✅ 弗劳德数 {Fr:.3f} < 0.5, 扩散波近似有效")
    else:
        print(f"⚠️ 弗劳德数 {Fr:.3f} > 0.5, 扩散波近似需谨慎")
    
    if 0.001 > 0.0001:
        print(f"✅ 坡度 {0.001} > 0.0001, 重力项占主导")
    
    if 0.001 < 0.002:
        print(f"⚠️ 坡度 {0.001} < 0.002, 扩散效应不可忽略")


def analyze_practical_selection_guide():
    """分析实际选择指南"""
    print("\n5. 实际应用选择指南")
    print("-" * 60)
    
    selection_guide = """
    🎯 方法选择决策树:
    
    开始
    ├── 河道坡度 S₀ > 0.005? 
    │   ├── 是 → 运动波方法
    │   │   ├── 简单分析 → 线性运动波
    │   │   └── 精确分析 → 特征线方法
    │   └── 否 ↓
    ├── 河道坡度 S₀ > 0.0001?
    │   ├── 是 → 扩散波方法
    │   │   ├── 几何参数已知 → 康吉法
    │   │   ├── 历史数据充足 → 传统马斯京干
    │   │   └── 精度要求高 → 数值扩散波
    │   └── 否 ↓
    ├── 弗劳德数 Fr < 0.3?
    │   ├── 是 → 准静态方法
    │   └── 否 → 完整圣维南方程
    │       ├── 线性化分析 → 线性圣维南
    │       └── 非线性求解 → 数值方法
    """
    print(selection_guide)
    
    print("\n📋 具体应用场景推荐:")
    
    scenarios = [
        {
            "场景": "山区河道洪水预报",
            "特征": "陡坡、快速响应",
            "推荐": "运动波方法",
            "原因": "陡坡使扩散效应较小"
        },
        {
            "场景": "平原河网演算",
            "特征": "缓坡、复杂边界",
            "推荐": "扩散波/康吉法",
            "原因": "扩散效应显著，需考虑回水"
        },
        {
            "场景": "城市排水管网",
            "特征": "人工渠道、急流",
            "推荐": "完整圣维南",
            "原因": "几何复杂，惯性效应重要"
        },
        {
            "场景": "水库调洪演算",
            "特征": "大水体、缓变",
            "推荐": "蓄量演算",
            "原因": "水体大，可忽略传播过程"
        },
        {
            "场景": "河道工程设计",
            "特征": "精度要求高",
            "推荐": "完整圣维南",
            "原因": "设计需要考虑所有物理效应"
        }
    ]
    
    for scenario in scenarios:
        print(f"\n🏞️ {scenario['场景']}:")
        print(f"   特征: {scenario['特征']}")
        print(f"   推荐: {scenario['推荐']}")
        print(f"   原因: {scenario['原因']}")


def summarize_theoretical_framework():
    """总结理论框架"""
    print("\n6. 完整理论框架总结")
    print("-" * 60)
    
    framework_summary = """
    🏗️ 圣维南方程近似与线性化理论框架:
    
    Level 0: 完整圣维南方程
    ├── 连续性: ∂A/∂t + ∂Q/∂x = 0
    └── 动量: ∂Q/∂t + ∂(Q²/A)/∂x + gA∂h/∂x + gAS_f - gAS_0 = 0
    
    Level 1: 物理近似
    ├── 扩散波 (忽略惯性项)
    ├── 运动波 (忽略惯性+扩散项)
    ├── 准静态波 (忽略局部惯性项)
    └── 准恒定流 (忽略时间导数项)
    
    Level 2: 数学线性化
    ├── 康吉法 (扩散波线性化)
    ├── 线性运动波 (运动波线性化)
    ├── 线性圣维南 (完整方程线性化)
    └── 传递函数法 (系统理论方法)
    
    Level 3: 工程简化
    ├── 马斯京干法 (经验参数)
    ├── 蓄量演算 (集总参数)
    ├── 滞后演算 (纯延迟)
    └── 单位线法 (线性叠加)
    """
    print(framework_summary)
    
    print("\n🎯 理论层次的递进关系:")
    print("• 物理完整性: 完整方程 > 物理近似 > 数学线性化 > 工程简化")
    print("• 计算复杂度: 工程简化 < 数学线性化 < 物理近似 < 完整方程")
    print("• 参数透明度: 工程简化 < 数学线性化 < 物理近似 < 完整方程")
    print("• 适用范围: 完整方程 > 物理近似 > 数学线性化 > 工程简化")


def main():
    """主分析函数"""
    try:
        print("🌊 圣维南方程近似形式与线性化方法全面分析")
        
        # 近似层次分析
        analyze_saint_venant_approximation_hierarchy()
        
        # 扩散波理论
        analyze_diffusive_wave_theory()
        
        # 运动波理论
        analyze_kinematic_wave_theory()
        
        # 线性化方法
        analyze_linearization_methods()
        
        # 有效性分析
        demonstrate_approximation_validity()
        
        # 选择指南
        analyze_practical_selection_guide()
        
        # 理论框架总结
        summarize_theoretical_framework()
        
        print("\n" + "=" * 80)
        print("🎯 核心结论：圣维南方程近似与线性化的完整图景")
        print("=" * 80)
        
        print("1. 🏗️ 理论层次:")
        print("   物理近似 → 数学线性化 → 工程简化")
        print("   形成了完整的理论降阶体系")
        
        print("\n2. 🎯 康吉法的定位:")
        print("   扩散波理论 + 线性化 = 物理与数学的完美结合")
        print("   在理论完整性和计算效率间找到最佳平衡")
        
        print("\n3. 🔄 方法选择:")
        print("   根据坡度、弗劳德数、精度要求选择合适方法")
        print("   没有万能方法，只有合适的方法")
        
        print("\n4. 💡 发展趋势:")
        print("   • 混合方法: 不同条件下动态选择")
        print("   • 自适应近似: 根据误差自动调整近似级别")
        print("   • 智能化: 机器学习辅助方法选择")
        
        print("\n圣维南方程的近似与线性化构成了丰富的理论体系！")
        
    except Exception as e:
        print(f"分析过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()