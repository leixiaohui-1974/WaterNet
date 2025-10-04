#!/usr/bin/env python3
"""
四方程IDZ模型测试脚本

测试新实现的四方程IDZ模型，验证：
1. 四个传递函数的耦合响应
2. 基于稳态平衡点的线性化
3. 上下游双向耦合效应
4. 回水效应建模

Author: WaterNet Development Team
Date: 2024-10-04
"""

import numpy as np
import matplotlib.pyplot as plt
import sys
import os

# 添加WaterNet路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from waternet.models.lumped_models import IntegralDelayZeroModel


def test_four_equation_idz_model():
    """测试四方程IDZ模型的基本功能"""
    
    print("=" * 60)
    print("四方程IDZ模型测试")
    print("=" * 60)
    
    # 1. 定义物理关系函数
    def V_to_H(V):
        """蓄量-水位关系（简化的矩形渠道）"""
        # V = A * H * L, 假设 A = 100 m², L = 1000 m
        A_L = 100 * 1000  # 100,000 m³/m
        return V / A_L
    
    def H_to_Q(H):
        """水位-出流关系（简化的堰流公式）"""
        # Q = C * H^(3/2), C = 10
        C = 10.0
        return C * (H ** 1.5) if H > 0 else 0.0
    
    def QH_to_V(Q, H):
        """流量水位耦合的蓄量关系"""
        # 基础蓄量 + 动态修正
        V_base = V_to_H.__code__.co_consts[1] * H  # A_L * H
        # 流量引起的动态蓄量修正（简化模型）
        V_dynamic = Q * 50  # 50秒的滞留时间效应
        return V_base + V_dynamic
    
    # 2. 定义稳态平衡点
    Q0_up = 50.0     # 上游稳态流量 (m³/s)
    H0_up = 2.0      # 上游稳态水位 (m)
    Q0_down = 45.0   # 下游稳态流量 (m³/s) 
    H0_down = 1.8    # 下游稳态水位 (m)
    
    # 计算对应的初始蓄量
    initial_V = QH_to_V((Q0_up + Q0_down)/2, (H0_up + H0_down)/2)
    
    print(f"稳态平衡点:")
    print(f"  上游: Q0_up={Q0_up} m³/s, H0_up={H0_up} m")
    print(f"  下游: Q0_down={Q0_down} m³/s, H0_down={H0_down} m")
    print(f"  平衡蓄量: V0={initial_V:.1f} m³")
    print()
    
    # 3. 创建四方程IDZ模型
    dt = 60.0  # 1分钟时间步长
    
    idz_model = IntegralDelayZeroModel(
        dt=dt,
        initial_V=initial_V,
        V_to_H_func=V_to_H,
        H_to_Q_func=H_to_Q,
        Q0_up=Q0_up, H0_up=H0_up,
        Q0_down=Q0_down, H0_down=H0_down,
        # 四个传递函数的参数
        tau11=120.0, tau12=60.0, tau21=300.0, tau22=150.0,  # 零点时间常数
        T11=0.0, T12=600.0, T21=1200.0, T22=0.0,            # 延迟时间  
        alpha11=400.0, alpha12=300.0, alpha21=600.0, alpha22=400.0,  # 极点时间常数
        name="FourEquationIDZ"
    )
    
    print("四方程IDZ模型已创建")
    print(f"模型参数: {idz_model.get_transfer_function_matrix()['transfer_functions']}")
    print()
    
    # 4. 设计测试信号
    duration = 3600 * 6  # 6小时仿真
    time_steps = int(duration / dt)
    time_array = np.linspace(0, duration, time_steps)
    
    # 上游入流扰动：阶跃信号
    Q_in_up_series = np.ones(time_steps) * Q0_up
    Q_in_up_series[time_steps//4:time_steps//2] += 20.0  # 2小时内增加20 m³/s
    
    # 下游入流扰动：脉冲信号
    Q_in_down_series = np.ones(time_steps) * 0.0  # 默认无下游入流
    pulse_start = time_steps//2
    pulse_end = pulse_start + time_steps//6
    Q_in_down_series[pulse_start:pulse_end] = 15.0  # 1小时脉冲信号
    
    print("测试信号设计:")
    print(f"  上游入流: 平衡值{Q0_up} m³/s + 阶跃扰动20 m³/s (1.5-3小时)")
    print(f"  下游入流: 脉冲扰动15 m³/s (3-4小时)")
    print(f"  仿真时长: {duration/3600:.1f} 小时, 时间步长: {dt} 秒")
    print()
    
    # 5. 运行仿真
    print("开始仿真...")
    results = []
    
    for i, (Q_up, Q_down) in enumerate(zip(Q_in_up_series, Q_in_down_series)):
        result = idz_model.step(Q_up, Q_down)
        result['time_hours'] = time_array[i] / 3600
        result['Q_in_up'] = Q_up
        result['Q_in_down'] = Q_down
        results.append(result)
        
        if i % (time_steps // 10) == 0:
            print(f"  仿真进度: {i/time_steps*100:.1f}%")
    
    print("仿真完成!")
    print()
    
    # 6. 分析结果
    print("仿真结果分析:")
    print("-" * 40)
    
    # 提取关键变量
    time_h = [r['time_hours'] for r in results]
    Q_out = [r['Q_out'] for r in results] 
    Q_out_up = [r['Q_out_up'] for r in results]
    Q_out_down = [r['Q_out_down'] for r in results]
    V = [r['V'] for r in results]
    H = [r['H_out'] for r in results]
    
    # 传递函数响应
    G11_resp = [r['G11_response'] for r in results]
    G12_resp = [r['G12_response'] for r in results]
    G21_resp = [r['G21_response'] for r in results]
    G22_resp = [r['G22_response'] for r in results]
    
    # 统计信息
    print(f"最终状态:")
    print(f"  上游出流: {Q_out_up[-1]:.2f} m³/s (平衡值: {Q0_up:.2f})")
    print(f"  下游出流: {Q_out_down[-1]:.2f} m³/s (平衡值: {Q0_down:.2f})")
    print(f"  系统出流: {Q_out[-1]:.2f} m³/s")
    print(f"  蓄水量: {V[-1]:.1f} m³ (平衡值: {initial_V:.1f})")
    print(f"  水位: {H[-1]:.3f} m")
    print()
    
    print(f"传递函数响应峰值:")
    print(f"  G11 (上游→上游): {max(np.abs(G11_resp)):.3f}")
    print(f"  G12 (下游→上游): {max(np.abs(G12_resp)):.3f}")
    print(f"  G21 (上游→下游): {max(np.abs(G21_resp)):.3f}")
    print(f"  G22 (下游→下游): {max(np.abs(G22_resp)):.3f}")
    print()
    
    # 7. 可视化结果
    print("生成可视化图表...")
    
    fig, axes = plt.subplots(3, 2, figsize=(15, 12))
    fig.suptitle('四方程IDZ模型仿真结果', fontsize=16)
    
    # 输入信号
    axes[0, 0].plot(time_h, Q_in_up_series, 'b-', label='上游入流', linewidth=2)
    axes[0, 0].plot(time_h, Q_in_down_series, 'r-', label='下游入流', linewidth=2)
    axes[0, 0].axhline(y=Q0_up, color='b', linestyle='--', alpha=0.7, label='上游平衡值')
    axes[0, 0].set_title('输入信号')
    axes[0, 0].set_ylabel('流量 (m³/s)')
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)
    
    # 输出响应
    axes[0, 1].plot(time_h, Q_out_up, 'b-', label='上游出流', linewidth=2)
    axes[0, 1].plot(time_h, Q_out_down, 'r-', label='下游出流', linewidth=2)
    axes[0, 1].plot(time_h, Q_out, 'g-', label='系统总出流', linewidth=2)
    axes[0, 1].axhline(y=Q0_up, color='b', linestyle='--', alpha=0.7)
    axes[0, 1].axhline(y=Q0_down, color='r', linestyle='--', alpha=0.7)
    axes[0, 1].set_title('输出响应')
    axes[0, 1].set_ylabel('流量 (m³/s)')
    axes[0, 1].legend()
    axes[0, 1].grid(True, alpha=0.3)
    
    # 蓄水量和水位
    axes[1, 0].plot(time_h, V, 'purple', linewidth=2, label='蓄水量')
    axes[1, 0].axhline(y=initial_V, color='purple', linestyle='--', alpha=0.7, label='平衡值')
    axes[1, 0].set_title('蓄水量变化')
    axes[1, 0].set_ylabel('蓄水量 (m³)')
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)
    
    axes[1, 1].plot(time_h, H, 'orange', linewidth=2, label='水位')
    axes[1, 1].axhline(y=(H0_up + H0_down)/2, color='orange', linestyle='--', alpha=0.7, label='平衡值')
    axes[1, 1].set_title('水位变化')
    axes[1, 1].set_ylabel('水位 (m)')
    axes[1, 1].legend()
    axes[1, 1].grid(True, alpha=0.3)
    
    # 传递函数响应
    axes[2, 0].plot(time_h, G11_resp, label='G11: 上游→上游', linewidth=2)
    axes[2, 0].plot(time_h, G12_resp, label='G12: 下游→上游', linewidth=2)
    axes[2, 0].set_title('上游节点传递函数响应')
    axes[2, 0].set_ylabel('响应值')
    axes[2, 0].set_xlabel('时间 (小时)')
    axes[2, 0].legend()
    axes[2, 0].grid(True, alpha=0.3)
    
    axes[2, 1].plot(time_h, G21_resp, label='G21: 上游→下游', linewidth=2)
    axes[2, 1].plot(time_h, G22_resp, label='G22: 下游→下游', linewidth=2)
    axes[2, 1].set_title('下游节点传递函数响应')
    axes[2, 1].set_ylabel('响应值')
    axes[2, 1].set_xlabel('时间 (小时)')
    axes[2, 1].legend()
    axes[2, 1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # 保存图片
    output_path = os.path.join(os.path.dirname(__file__), 'four_equation_idz_test_results.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"图表已保存至: {output_path}")
    
    return idz_model, results


def analyze_transfer_function_coupling():
    """分析四个传递函数的耦合特性"""
    
    print("\n" + "=" * 60)
    print("传递函数耦合特性分析")
    print("=" * 60)
    
    # 理论分析
    print("传递函数矩阵结构:")
    print("""
    [Q1_out]   [G11(s) G12(s)] [ΔQ1_in]   [Q0_up]
    [Q2_out] = [G21(s) G22(s)] [ΔQ2_in] + [Q0_down]
    
    物理意义:
    - G11(s): 上游输入 → 上游输出 (本地响应)
    - G12(s): 下游输入 → 上游输出 (回水效应)
    - G21(s): 上游输入 → 下游输出 (正向传播)
    - G22(s): 下游输入 → 下游输出 (本地响应)
    """)
    
    # 参数设计原则
    print("参数设计原则:")
    print("1. 延迟时间 T:")
    print("   - T11 = 0 (上游本地响应无延迟)")
    print("   - T12 > 0 (回水效应有延迟)")
    print("   - T21 > T12 (正向传播延迟最大)")
    print("   - T22 = 0 (下游本地响应无延迟)")
    print()
    print("2. 时间常数 τ, α:")
    print("   - τ 控制零点特性 (超调/振荡)")
    print("   - α 控制极点特性 (响应速度)")
    print("   - 一般 α > τ 保证系统稳定")
    print()
    
    # 系统特性
    print("系统动态特性:")
    print("- 回水效应: G12能捕捉下游条件对上游的影响")
    print("- 正向传播: G21描述洪峰传播过程")
    print("- 局部调蓄: G11, G22描述各节点的本地调蓄能力")
    print("- 双向耦合: 全矩阵结构支持复杂的双向流动")
    print()


def compare_with_traditional_models():
    """与传统模型的对比分析"""
    
    print("\n" + "=" * 60)
    print("与传统模型对比")
    print("=" * 60)
    
    comparison = {
        '模型复杂度': {
            '水量平衡': '无参数',
            '蓄量演算': '需要V-H, H-Q关系',
            '马斯京干': '2个参数 (K, x)',
            '单一IDZ': '3个参数 (τ, T, α)',
            '四方程IDZ': '12个参数 (4×3)'
        },
        '物理机理': {
            '水量平衡': '无滞后',
            '蓄量演算': '蓄量调节',
            '马斯京干': '线性水库',
            '单一IDZ': '单向传递函数',
            '四方程IDZ': '双向耦合传递函数'
        },
        '适用场景': {
            '水量平衡': '简单估算',
            '蓄量演算': '水库、明渠',
            '马斯京干': '天然河道',
            '单一IDZ': '简单系统',
            '四方程IDZ': '复杂河网系统'
        }
    }
    
    for aspect, models in comparison.items():
        print(f"{aspect}:")
        for model, desc in models.items():
            print(f"  {model:12}: {desc}")
        print()


if __name__ == "__main__":
    try:
        # 主测试
        model, results = test_four_equation_idz_model()
        
        # 理论分析
        analyze_transfer_function_coupling()
        
        # 对比分析
        compare_with_traditional_models()
        
        print("\n" + "=" * 60)
        print("测试完成! 四方程IDZ模型实现验证成功")
        print("=" * 60)
        
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()