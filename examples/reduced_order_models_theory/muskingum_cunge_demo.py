"""
马斯京干-康吉法演示脚本

对比传统马斯京干法与康吉法的差异，演示康吉法的优势。

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
    create_cunge_model_from_geometry
)


def create_physical_relations():
    """创建物理关系函数"""
    def V_to_H_func(V):
        return 100.0 + V / 10000.0
    
    def H_to_Q_func(H):
        return max(0.0, (H - 100.0) * 25.0)
    
    return V_to_H_func, H_to_Q_func


def demo_parameter_comparison():
    """演示参数计算方法对比"""
    print("\n1. 参数计算方法对比")
    print("-" * 50)
    
    # 河道参数
    length = 1000.0      # 河段长度 (m)
    width = 50.0         # 河道宽度 (m)
    slope = 0.001        # 河底坡度
    roughness = 0.025    # 曼宁系数
    ref_discharge = 100.0 # 参考流量 (m³/s)
    
    print(f"河道参数:")
    print(f"长度: {length} m, 宽度: {width} m")
    print(f"坡度: {slope}, 粗糙系数: {roughness}")
    print(f"参考流量: {ref_discharge} m³/s")
    
    # 传统马斯京干法（经验参数）
    K_traditional = 3600.0  # 经验值
    x_traditional = 0.2     # 经验值
    
    print(f"\n传统马斯京干法（经验参数）:")
    print(f"K = {K_traditional} s")
    print(f"x = {x_traditional}")
    
    # 康吉法（物理计算）
    geometry = ChannelGeometry(
        length=length, width=width, slope=slope, roughness=roughness)
    flow_conditions = FlowConditions(reference_discharge=ref_discharge)
    
    V_to_H, H_to_Q = create_physical_relations()
    
    cunge_model = MuskingumCungeModel(
        dt=60.0, geometry=geometry, flow_conditions=flow_conditions,
        initial_V=15000.0, V_to_H_func=V_to_H, H_to_Q_func=H_to_Q
    )
    
    cunge_info = cunge_model.get_model_info()
    K_cunge = cunge_info['current_parameters']['K']
    x_cunge = cunge_info['current_parameters']['x']
    
    print(f"\n康吉法（物理计算）:")
    print(f"K = {K_cunge:.1f} s")
    print(f"x = {x_cunge:.3f}")
    
    # 计算康吉法的水力参数
    computed_params = cunge_info['computed_parameters']
    print(f"\n康吉法计算的水力参数:")
    print(f"正常水深: {computed_params.get('normal_depth', 0):.3f} m")
    print(f"波速: {computed_params.get('wave_celerity', 0):.3f} m/s")
    print(f"断面积: {computed_params.get('cross_sectional_area', 0):.1f} m²")
    print(f"流速: {computed_params.get('flow_velocity', 0):.3f} m/s")
    
    return cunge_model, K_traditional, x_traditional


def demo_simulation_comparison():
    """演示仿真结果对比"""
    print("\n2. 仿真结果对比")
    print("-" * 50)
    
    # 创建模型
    V_to_H, H_to_Q = create_physical_relations()
    
    # 传统马斯京干模型
    traditional_model = MuskingumModel(
        dt=60.0, K=3600.0, x=0.2, initial_V=15000.0,
        V_to_H_func=V_to_H, H_to_Q_func=H_to_Q, name="Traditional"
    )
    
    # 康吉模型
    cunge_model = create_cunge_model_from_geometry(
        dt=60.0, length=1000.0, width=50.0, slope=0.001, roughness=0.025,
        reference_discharge=100.0, initial_V=15000.0,
        V_to_H_func=V_to_H, H_to_Q_func=H_to_Q, name="Cunge"
    )
    
    # 创建测试流量序列（洪水过程）
    time_steps = 60
    flood_input = []
    for i in range(time_steps):
        t = i * 60  # 时间（秒）
        # 三角形洪水波
        if t <= 1800:  # 上升段
            Q = 50 + (150 - 50) * t / 1800
        elif t <= 3600:  # 下降段
            Q = 150 - (150 - 50) * (t - 1800) / 1800
        else:  # 退水段
            Q = 50
        flood_input.append(Q)
    
    flood_input = np.array(flood_input)
    
    print(f"测试洪水过程: 峰值{flood_input.max():.1f} m³/s")
    
    # 运行仿真
    traditional_results = traditional_model.run_simulation(flood_input)
    cunge_results = cunge_model.run_simulation(flood_input)
    
    # 对比结果
    print(f"\n仿真结果对比:")
    print(f"传统法峰值出流: {traditional_results['Q_out'].max():.2f} m³/s")
    print(f"康吉法峰值出流: {cunge_results['Q_out'].max():.2f} m³/s")
    
    # 计算峰值延迟
    trad_peak_time = traditional_results['Q_out'].idxmax() * 60
    cunge_peak_time = cunge_results['Q_out'].idxmax() * 60
    
    print(f"传统法峰值时间: {trad_peak_time/60:.1f} 分钟")
    print(f"康吉法峰值时间: {cunge_peak_time/60:.1f} 分钟")
    print(f"峰值延迟差异: {abs(trad_peak_time - cunge_peak_time)/60:.1f} 分钟")
    
    return traditional_results, cunge_results


def demo_adaptive_parameters():
    """演示自适应参数功能"""
    print("\n3. 自适应参数演示")
    print("-" * 50)
    
    V_to_H, H_to_Q = create_physical_relations()
    
    # 创建启用自适应的康吉模型
    adaptive_model = create_cunge_model_from_geometry(
        dt=60.0, length=1000.0, width=50.0, slope=0.001, roughness=0.025,
        reference_discharge=50.0, initial_V=15000.0,
        V_to_H_func=V_to_H, H_to_Q_func=H_to_Q,
        enable_adaptive_parameters=True, name="Adaptive"
    )
    
    print("启用自适应参数调整的康吉模型")
    
    # 变化流量测试
    varying_flow = [50, 75, 100, 150, 200, 150, 100, 75, 50]
    
    print(f"\n测试流量序列: {varying_flow}")
    print(f"参数变化跟踪:")
    
    K_history = []
    x_history = []
    
    for i, Q_in in enumerate(varying_flow):
        result = adaptive_model.step(Q_in)
        K_history.append(result['K'])
        x_history.append(result['x'])
        
        if i % 2 == 0:  # 每隔一步显示
            print(f"步骤 {i+1}: Q_in={Q_in} m³/s, K={result['K']:.1f}s, x={result['x']:.3f}")
    
    print(f"\nK值变化范围: {min(K_history):.1f} - {max(K_history):.1f} s")
    print(f"x值变化范围: {min(x_history):.3f} - {max(x_history):.3f}")
    
    return K_history, x_history


def demo_compatibility_mode():
    """演示兼容传统模式"""
    print("\n4. 传统模式兼容性演示")
    print("-" * 50)
    
    V_to_H, H_to_Q = create_physical_relations()
    
    # 创建使用手动参数的康吉模型（兼容传统模式）
    geometry = ChannelGeometry(1000.0, 50.0, 0.001, 0.025)
    flow_conditions = FlowConditions(100.0)
    
    manual_cunge = MuskingumCungeModel(
        dt=60.0, geometry=geometry, flow_conditions=flow_conditions,
        initial_V=15000.0, V_to_H_func=V_to_H, H_to_Q_func=H_to_Q,
        manual_K=3600.0, manual_x=0.2, name="ManualCunge"
    )
    
    # 传统马斯京干模型
    traditional = MuskingumModel(
        dt=60.0, K=3600.0, x=0.2, initial_V=15000.0,
        V_to_H_func=V_to_H, H_to_Q_func=H_to_Q, name="Traditional"
    )
    
    # 测试相同输入
    test_input = [80, 100, 120, 100, 80]
    
    manual_results = manual_cunge.run_simulation(test_input)
    trad_results = traditional.run_simulation(test_input)
    
    print("手动参数康吉模型 vs 传统马斯京干模型:")
    print("输入序列:", test_input)
    print(f"康吉模型出流: {manual_results['Q_out'].values}")
    print(f"传统模型出流: {trad_results['Q_out'].values}")
    
    # 计算差异
    diff = np.abs(manual_results['Q_out'].values - trad_results['Q_out'].values)
    print(f"最大差异: {diff.max():.6f} m³/s (应该接近0)")
    print("✓ 兼容性验证通过" if diff.max() < 1e-6 else "✗ 兼容性验证失败")


def main():
    """主演示函数"""
    try:
        print("🌊 马斯京干-康吉法演示")
        print("=" * 60)
        
        # 参数对比演示
        cunge_model, K_trad, x_trad = demo_parameter_comparison()
        
        # 仿真对比演示
        trad_results, cunge_results = demo_simulation_comparison()
        
        # 自适应参数演示
        K_hist, x_hist = demo_adaptive_parameters()
        
        # 兼容性演示
        demo_compatibility_mode()
        
        print("\n" + "=" * 60)
        print("总结: 马斯京干-康吉法的主要优势")
        print("=" * 60)
        print("1. 🎯 理论基础: 基于扩散波方程，物理意义明确")
        print("2. 🔧 参数计算: 可从河道物理特性自动计算K和x")
        print("3. 🔄 自适应性: 支持根据流量变化动态调整参数")
        print("4. 🔗 兼容性: 完全兼容传统马斯京干模型")
        print("5. 📊 精度提升: 在复杂工况下表现更优")
        
        # 显示模型信息
        model_info = cunge_model.get_model_info()
        print(f"\n康吉模型配置信息:")
        geometry = model_info['geometry']
        print(f"河段: {geometry['length']}m × {geometry['width']}m")
        print(f"坡度: {geometry['slope']}, 粗糙度: {geometry['roughness']}")
        
        params = model_info['current_parameters']
        print(f"当前参数: K={params['K']:.1f}s, x={params['x']:.3f}")
        print(f"自适应模式: {'启用' if model_info['adaptive_enabled'] else '禁用'}")
        
        print("\n康吉法为马斯京干模型提供了坚实的物理理论基础！")
        
    except Exception as e:
        print(f"演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()