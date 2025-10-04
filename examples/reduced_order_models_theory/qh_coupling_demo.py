"""
Q-H耦合蓄水量计算演示

展示如何使用改进后的降阶模型来实现更精确的
流量-水位耦合的蓄水量计算方法。

这解决了原有设计中只考虑V=f(H)关系的局限性，
现在支持更物理准确的V=f(Q,H)关系。

Author: WaterNet Development Team
Date: 2024-10-04
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from waternet.models.lumped_models import StorageRoutingModel, MuskingumModel


def create_traditional_functions():
    """创建传统的V-H和H-Q关系函数"""
    def V_to_H_traditional(V):
        """传统的蓄量-水位关系"""
        base_level = 100.0
        storage_coeff = 1.0 / 10000.0
        return base_level + V * storage_coeff
    
    def H_to_Q_traditional(H):
        """传统的水位-出流关系"""
        threshold = 100.0
        if H <= threshold:
            return 0.0
        return 30.0 * (H - threshold) ** 1.5
    
    return V_to_H_traditional, H_to_Q_traditional


def create_QH_coupling_function():
    """创建Q-H耦合的蓄水量关系函数"""
    def QH_to_V_coupling(Q, H):
        """
        考虑流量影响的蓄水量计算
        
        物理原理：
        - 大流量时，水面线较陡，相同水位下蓄水量较小
        - 小流量时，水面线较缓，相同水位下蓄水量较大
        
        Args:
            Q (float): 流量 (m³/s)
            H (float): 水位 (m)
            
        Returns:
            float: 修正后的蓄水量 (m³)
        """
        base_level = 100.0
        depth = max(0, H - base_level)
        
        # 基础蓄水量（矩形断面近似）
        base_volume = depth * 1000.0 * 500.0  # 深度 × 长度 × 宽度
        
        # 流量修正系数（考虑水面线形状）
        if Q > 0:
            # 弗劳德数效应：Fr = V/√(gH)
            velocity = Q / (depth * 500.0) if depth > 0.01 else 0
            froude_number = velocity / np.sqrt(9.81 * depth) if depth > 0.01 else 0
            
            # 流量大时，动量大，水面线较陡，蓄水量减少
            flow_correction = 1.0 - 0.1 * min(froude_number, 0.5)
        else:
            flow_correction = 1.0
        
        return base_volume * flow_correction
    
    return QH_to_V_coupling


def demo_comparison():
    """对比传统方法和Q-H耦合方法"""
    print("=" * 60)
    print("Q-H耦合蓄水量计算方法演示")
    print("=" * 60)
    
    # 创建物理关系函数
    V_to_H_func, H_to_Q_func = create_traditional_functions()
    QH_to_V_func = create_QH_coupling_function()
    
    # 模型参数
    dt = 60.0  # 1分钟时间步长
    initial_V = 15000.0  # 初始蓄水量
    
    # 创建传统模型（只考虑V-H关系）
    traditional_model = StorageRoutingModel(
        dt=dt,
        initial_V=initial_V,
        V_to_H_func=V_to_H_func,
        H_to_Q_func=H_to_Q_func,
        name="Traditional_SR"
    )
    
    # 创建Q-H耦合模型
    qh_coupling_model = StorageRoutingModel(
        dt=dt,
        initial_V=initial_V,
        V_to_H_func=V_to_H_func,
        H_to_Q_func=H_to_Q_func,
        name="QH_Coupling_SR",
        QH_to_V_func=QH_to_V_func  # 使用Q-H耦合函数
    )
    
    print(f"传统模型使用Q-H耦合: {traditional_model.use_QH_coupling}")
    print(f"耦合模型使用Q-H耦合: {qh_coupling_model.use_QH_coupling}")
    
    # 设计入流过程（洪水过程）
    time_steps = 30  # 30分钟
    time_array = np.arange(0, time_steps * dt, dt)
    
    # 梯形洪水过程
    Q_in_series = []
    for t in time_array:
        if t <= 600:  # 前10分钟：上涨段
            Q = 5.0 + (25.0 - 5.0) * t / 600.0
        elif t <= 1200:  # 中间10分钟：峰值段
            Q = 25.0
        else:  # 后10分钟：下降段
            Q = 25.0 - (25.0 - 5.0) * (t - 1200) / 600.0
        Q_in_series.append(Q)
    
    print(f"\\n入流过程: {len(Q_in_series)}个时步")
    print(f"峰值流量: {max(Q_in_series):.1f} m³/s")
    
    # 运行仿真
    traditional_results = traditional_model.run_simulation(Q_in_series)
    qh_coupling_results = qh_coupling_model.run_simulation(Q_in_series)
    
    # 计算差异
    volume_diff = qh_coupling_results['V'] - traditional_results['V']
    max_volume_diff = np.max(np.abs(volume_diff))
    avg_volume_diff = np.mean(np.abs(volume_diff))
    
    print(f"\\n结果对比:")
    print(f"最大蓄水量差异: {max_volume_diff:.1f} m³")
    print(f"平均蓄水量差异: {avg_volume_diff:.1f} m³")
    print(f"相对差异: {max_volume_diff/initial_V*100:.2f}%")
    
    # 分析物理合理性
    print(f"\\n物理合理性分析:")
    traditional_final_V = traditional_results['V'].iloc[-1]
    qh_coupling_final_V = qh_coupling_results['V'].iloc[-1]
    
    print(f"传统方法最终蓄水量: {traditional_final_V:.1f} m³")
    print(f"Q-H耦合最终蓄水量: {qh_coupling_final_V:.1f} m³")
    
    if qh_coupling_final_V < traditional_final_V:
        print("✓ Q-H耦合方法考虑了流量对水面线的影响，结果更合理")
    
    return traditional_results, qh_coupling_results, time_array


def demo_physical_significance():
    """展示Q-H耦合的物理意义"""
    print("\\n" + "=" * 60)
    print("Q-H耦合的物理意义演示")
    print("=" * 60)
    
    QH_to_V_func = create_QH_coupling_function()
    
    # 固定水位，不同流量
    H_fixed = 101.5  # 固定水位
    Q_range = np.array([5, 10, 15, 20, 25, 30])  # 不同流量
    
    print(f"\\n固定水位 H = {H_fixed:.1f} m 时，不同流量对应的蓄水量:")
    print("流量(m³/s)  蓄水量(m³)  差异(%)")
    print("-" * 35)
    
    V_base = QH_to_V_func(Q_range[0], H_fixed)
    for Q in Q_range:
        V = QH_to_V_func(Q, H_fixed)
        diff_percent = (V - V_base) / V_base * 100
        print(f"{Q:8.1f}  {V:10.1f}  {diff_percent:+6.2f}")
    
    # 固定流量，不同水位
    Q_fixed = 20.0  # 固定流量
    H_range = np.arange(100.5, 102.1, 0.2)  # 不同水位
    
    print(f"\\n固定流量 Q = {Q_fixed:.1f} m³/s 时，不同水位对应的蓄水量:")
    print("水位(m)    蓄水量(m³)   dV/dH(m²)")
    print("-" * 38)
    
    for i, H in enumerate(H_range):
        V = QH_to_V_func(Q_fixed, H)
        if i > 0:
            dV_dH = (V - V_prev) / (H - H_range[i-1])
            print(f"{H:7.1f}  {V:12.1f}  {dV_dH:8.1f}")
        else:
            print(f"{H:7.1f}  {V:12.1f}       -")
        V_prev = V


def main():
    """主演示函数"""
    try:
        # 对比演示
        traditional_results, qh_coupling_results, time_array = demo_comparison()
        
        # 物理意义演示
        demo_physical_significance()
        
        print("\\n" + "=" * 60)
        print("总结")
        print("=" * 60)
        print("1. Q-H耦合方法考虑了流量对蓄水体积的影响")
        print("2. 大流量时水面线较陡，相同水位下蓄水量较小")
        print("3. 这种方法更符合实际的水力学原理")
        print("4. 特别适用于非恒定流和复杂边界条件的模拟")
        print("5. 向后兼容：不提供QH_to_V_func时自动使用传统方法")
        
    except Exception as e:
        print(f"演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()