#!/usr/bin/env python3
"""
四方程IDZ模型简化使用示例

演示如何简单快速地使用新实现的四方程IDZ模型
包括参数设置、模型创建、仿真运行和结果分析的完整流程

Author: WaterNet Development Team  
Date: 2024-10-04
"""

import sys
import os
import numpy as np

# 添加WaterNet路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from waternet.models.lumped_models import IntegralDelayZeroModel


def create_simple_idz_model():
    """创建一个简单的四方程IDZ模型示例"""
    
    print("=" * 50)
    print("四方程IDZ模型简化使用示例")
    print("=" * 50)
    
    # 1. 定义基本的物理关系函数
    def simple_V_to_H(V):
        """简单的蓄量-水位关系"""
        return V / 50000  # 假设渠道容积系数为50000 m³/m
    
    def simple_H_to_Q(H):
        """简单的水位-流量关系"""
        return 15 * (H ** 1.2) if H > 0 else 0.0
    
    # 2. 设定稳态平衡点（这是新模型的关键改进）
    Q0_up = 30.0     # 上游稳态流量 30 m³/s
    H0_up = 1.5      # 上游稳态水位 1.5 m
    Q0_down = 28.0   # 下游稳态流量 28 m³/s（有2 m³/s的损失或分流）
    H0_down = 1.4    # 下游稳态水位 1.4 m
    
    # 计算初始蓄量
    initial_V = simple_V_to_H.__code__.co_consts[1] * (H0_up + H0_down) / 2
    
    print(f"稳态平衡点设定:")
    print(f"  上游: Q={Q0_up} m³/s, H={H0_up} m")
    print(f"  下游: Q={Q0_down} m³/s, H={H0_down} m")
    print(f"  初始蓄量: {initial_V} m³")
    print()
    
    # 3. 创建四方程IDZ模型（使用推荐的参数设置）
    idz_model = IntegralDelayZeroModel(
        dt=30.0,  # 30秒时间步长
        initial_V=initial_V,
        V_to_H_func=simple_V_to_H,
        H_to_Q_func=simple_H_to_Q,
        
        # 稳态平衡点
        Q0_up=Q0_up, H0_up=H0_up,
        Q0_down=Q0_down, H0_down=H0_down,
        
        # 四个传递函数参数（简化设置）
        tau11=80, tau12=40, tau21=150, tau22=80,      # 零点时间常数
        T11=0, T12=300, T21=600, T22=0,               # 延迟时间
        alpha11=200, alpha12=150, alpha21=300, alpha22=200,  # 极点时间常数
        
        name="SimpleIDZ"
    )
    
    print("四方程IDZ模型创建成功!")
    print("模型特点:")
    print("- G11: 上游本地响应，无延迟，快速调节")
    print("- G12: 回水效应，5分钟延迟，影响上游")
    print("- G21: 正向传播，10分钟延迟，主要传播路径")  
    print("- G22: 下游本地响应，无延迟，快速调节")
    print()
    
    return idz_model


def run_simple_simulation(model):
    """运行简单的仿真示例"""
    
    print("开始简单仿真...")
    
    # 创建测试信号：2小时仿真
    duration = 2 * 3600  # 2小时
    dt = 30.0
    time_steps = int(duration / dt)
    
    # 上游流量：1小时后增加10 m³/s，持续30分钟
    Q_up_series = np.full(time_steps, 30.0)  # 基础流量30 m³/s
    start_idx = time_steps // 2  # 1小时后
    end_idx = start_idx + time_steps // 4  # 持续30分钟
    Q_up_series[start_idx:end_idx] += 10.0  # 增加10 m³/s
    
    # 下游流量：无额外输入（实际河道中通常如此）
    Q_down_series = np.zeros(time_steps)
    
    print(f"测试信号:")
    print(f"  上游: 基础30 m³/s, 1-1.5小时期间增加10 m³/s")
    print(f"  下游: 无额外输入")
    print(f"  仿真时长: 2小时")
    
    # 运行仿真
    results = []
    for i, (Q_up, Q_down) in enumerate(zip(Q_up_series, Q_down_series)):
        result = model.step(Q_up, Q_down)
        result['time_min'] = i * dt / 60  # 转换为分钟
        result['Q_in_up'] = Q_up
        results.append(result)
        
        if i % (time_steps // 8) == 0:  # 显示进度
            print(f"  进度: {i/time_steps*100:.0f}%")
    
    print("仿真完成!")
    return results


def analyze_simple_results(results):
    """分析仿真结果"""
    
    print("\n" + "=" * 50)
    print("仿真结果分析")
    print("=" * 50)
    
    # 提取关键数据
    times = [r['time_min'] for r in results]
    Q_out_up = [r['Q_out_up'] for r in results]
    Q_out_down = [r['Q_out_down'] for r in results]
    Q_system = [r['Q_out'] for r in results]
    volumes = [r['V'] for r in results]
    
    # 传递函数响应
    G11 = [r['G11_response'] for r in results]
    G12 = [r['G12_response'] for r in results]
    G21 = [r['G21_response'] for r in results]
    G22 = [r['G22_response'] for r in results]
    
    print(f"初始状态 (t=0):")
    print(f"  上游出流: {Q_out_up[0]:.2f} m³/s")
    print(f"  下游出流: {Q_out_down[0]:.2f} m³/s")
    print(f"  系统出流: {Q_system[0]:.2f} m³/s")
    print(f"  蓄水量: {volumes[0]:.0f} m³")
    print()
    
    print(f"最大响应 (扰动期间):")
    print(f"  上游出流峰值: {max(Q_out_up):.2f} m³/s")
    print(f"  下游出流峰值: {max(Q_out_down):.2f} m³/s")
    print(f"  系统出流峰值: {max(Q_system):.2f} m³/s")
    print(f"  蓄水量峰值: {max(volumes):.0f} m³")
    print()
    
    print(f"传递函数响应特性:")
    print(f"  G11最大响应: {max(np.abs(G11)):.3f} (上游本地)")
    print(f"  G12最大响应: {max(np.abs(G12)):.3f} (回水效应)")
    print(f"  G21最大响应: {max(np.abs(G21)):.3f} (正向传播)")
    print(f"  G22最大响应: {max(np.abs(G22)):.3f} (下游本地)")
    print()
    
    # 寻找峰值时间
    Q_up_peak_idx = np.argmax(Q_out_up)
    Q_down_peak_idx = np.argmax(Q_out_down)
    
    print(f"响应时间分析:")
    print(f"  扰动开始时间: 60分钟")
    print(f"  上游峰值时间: {times[Q_up_peak_idx]:.1f}分钟")
    print(f"  下游峰值时间: {times[Q_down_peak_idx]:.1f}分钟")
    print(f"  传播延迟: {times[Q_down_peak_idx] - times[Q_up_peak_idx]:.1f}分钟")
    print()
    
    # 简单的文本图表
    print("简化时间序列 (每15分钟一个点):")
    print("时间(min) | 上游出流 | 下游出流 | 系统出流")
    print("-" * 45)
    
    for i in range(0, len(times), 30):  # 每30个点显示一次（15分钟）
        t = times[i]
        q_up = Q_out_up[i]
        q_down = Q_out_down[i]
        q_sys = Q_system[i]
        print(f"{t:8.0f}  | {q_up:8.2f} | {q_down:8.2f} | {q_sys:8.2f}")


def demonstrate_equilibrium_update():
    """演示平衡点更新功能"""
    
    print("\n" + "=" * 50)
    print("平衡点更新演示")
    print("=" * 50)
    
    # 创建模型
    model = create_simple_idz_model()
    
    print("原始平衡点:")
    params = model.get_transfer_function_matrix()
    eq_point = params['equilibrium_point']
    for key, value in eq_point.items():
        print(f"  {key}: {value}")
    print()
    
    # 更新平衡点（模拟不同的运行条件）
    new_Q0_up = 40.0
    new_H0_up = 1.8
    new_Q0_down = 38.0
    new_H0_down = 1.7
    
    print("更新平衡点到新的运行条件:")
    print(f"  新上游条件: Q={new_Q0_up} m³/s, H={new_H0_up} m")
    print(f"  新下游条件: Q={new_Q0_down} m³/s, H={new_H0_down} m")
    
    model.update_equilibrium_point(new_Q0_up, new_H0_up, new_Q0_down, new_H0_down)
    
    print("\n更新后的平衡点:")
    params = model.get_transfer_function_matrix()
    eq_point = params['equilibrium_point']
    for key, value in eq_point.items():
        print(f"  {key}: {value}")
    
    print("\n平衡点更新功能说明:")
    print("- 可以根据实际运行条件动态调整平衡点")
    print("- 无需重新创建模型，保持历史状态")
    print("- 适用于多工况分析和自适应控制")


if __name__ == "__main__":
    try:
        print("四方程IDZ模型简化使用示例\n")
        
        # 1. 创建模型
        model = create_simple_idz_model()
        
        # 2. 运行仿真
        results = run_simple_simulation(model)
        
        # 3. 分析结果
        analyze_simple_results(results)
        
        # 4. 演示平衡点更新
        demonstrate_equilibrium_update()
        
        print("\n" + "=" * 50)
        print("示例演示完成!")
        print("=" * 50)
        print("\n关键改进总结:")
        print("1. 平衡点基于稳态物理条件，无需假设")
        print("2. 四方程完整描述双向耦合效应")
        print("3. 支持动态平衡点更新")
        print("4. 传递函数参数物理意义明确")
        print("5. 适用于复杂河网系统建模")
        
    except Exception as e:
        print(f"示例运行出错: {e}")
        import traceback
        traceback.print_exc()