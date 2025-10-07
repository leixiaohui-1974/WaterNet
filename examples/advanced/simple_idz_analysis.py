#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
3参数IDZ模型精确辨识
严格按照积分、时滞、极点3个参数的IDZ模型形式
G(s) = K / [s * (τs + 1)] * exp(-T*s)
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
import warnings
warnings.filterwarnings('ignore')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

def idz_response(t, K, tau, T):
    """
    3参数IDZ模型阶跃响应
    G(s) = K / [s * (τs + 1)] * exp(-T*s)
    """
    response = np.zeros_like(t)
    mask = t >= T
    t_eff = t[mask] - T
    response[mask] = K * (t_eff - tau + tau * np.exp(-t_eff / tau))
    return response

def analyze_idz_parameters():
    """分析IDZ模型参数"""
    # 加载数据
    df = pd.read_csv("各断面时间序列详细数据.csv", encoding='utf-8-sig')
    
    results = []
    
    # 分析各场景
    for scenario in df['场景'].unique():
        scenario_data = df[df['场景'] == scenario]
        
        print(f"\n=== 分析场景: {scenario} ===")
        
        for section in scenario_data['断面'].unique():
            section_data = scenario_data[scenario_data['断面'] == section]
            
            if len(section_data) < 5:
                continue
                
            # 提取数据
            t = section_data['时间(分钟)'].values
            if '水位' in scenario:
                y = section_data['水位(m)'].values
            else:
                y = section_data['水位(m)'].values  # 流量阶跃看水位响应
            
            distance = section_data['里程(km)'].iloc[0]
            
            # 计算增量响应
            y_delta = y - y[0]
            
            # 检查是否有响应
            if np.std(y_delta) < 1e-6:
                print(f"{section}: 无响应")
                results.append({
                    '场景': scenario, '断面': section, '距离': distance,
                    'K': 0, 'τ': 0, 'T': 0, 'R²': 1.0, 'RMSE': 0
                })
                continue
            
            # 参数估计
            try:
                # 初值估计
                final_val = y_delta[-1]
                final_time = t[-1]
                K_init = final_val / final_time if final_time > 0 else 0.001
                tau_init = 25.0  # 基于经验
                T_init = distance * 8.33  # 传播延迟
                
                # 拟合
                bounds = ([-0.1, 1, 0], [0.1, 100, 30])
                popt, _ = curve_fit(idz_response, t, y_delta, 
                                  p0=[K_init, tau_init, T_init],
                                  bounds=bounds, maxfev=3000)
                
                K_fit, tau_fit, T_fit = popt
                
                # 计算拟合质量
                y_pred = idz_response(t, *popt)
                ss_res = np.sum((y_delta - y_pred) ** 2)
                ss_tot = np.sum((y_delta - np.mean(y_delta)) ** 2)
                r2 = 1 - (ss_res / ss_tot) if ss_tot > 1e-10 else 0
                rmse = np.sqrt(np.mean((y_delta - y_pred) ** 2))
                
                print(f"{section}: K={K_fit:.6f}, τ={tau_fit:.2f}min, T={T_fit:.2f}min, R²={r2:.4f}")
                
                results.append({
                    '场景': scenario, '断面': section, '距离': distance,
                    'K': K_fit, 'τ': tau_fit, 'T': T_fit, 'R²': r2, 'RMSE': rmse
                })
                
            except Exception as e:
                print(f"{section}: 拟合失败 - {e}")
                results.append({
                    '场景': scenario, '断面': section, '距离': distance,
                    'K': 0, 'τ': 0, 'T': 0, 'R²': 0, 'RMSE': 999
                })
    
    # 保存结果
    df_results = pd.DataFrame(results)
    df_results.to_csv("3参数IDZ模型辨识结果.csv", index=False, encoding='utf-8-sig')
    
    print(f"\n=== 3参数IDZ模型辨识结果 ===")
    print(df_results.to_string(index=False))
    
    # 绘制结果
    plot_idz_results(df_results)
    
    return df_results

def plot_idz_results(df):
    """绘制IDZ辨识结果"""
    scenarios = df['场景'].unique()
    
    for scenario in scenarios:
        scenario_data = df[df['场景'] == scenario]
        
        if len(scenario_data) == 0:
            continue
            
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle(f'{scenario} - 3参数IDZ模型辨识结果', fontsize=14, fontweight='bold')
        
        distances = scenario_data['距离'].values
        K_values = scenario_data['K'].values
        tau_values = scenario_data['τ'].values  
        T_values = scenario_data['T'].values
        r2_values = scenario_data['R²'].values
        
        # 积分增益K
        ax1.plot(distances, K_values, 'bo-', linewidth=2, markersize=8)
        ax1.set_title('积分增益K随距离变化')
        ax1.set_xlabel('距离 (km)')
        ax1.set_ylabel('积分增益K')
        ax1.grid(True, alpha=0.3)
        
        # 时间常数τ
        ax2.plot(distances, tau_values, 'ro-', linewidth=2, markersize=8)
        ax2.set_title('时间常数τ随距离变化')
        ax2.set_xlabel('距离 (km)')
        ax2.set_ylabel('时间常数τ (分钟)')
        ax2.grid(True, alpha=0.3)
        
        # 纯时滞T
        ax3.plot(distances, T_values, 'go-', linewidth=2, markersize=8)
        ax3.set_title('纯时滞T随距离变化')
        ax3.set_xlabel('距离 (km)')
        ax3.set_ylabel('纯时滞T (分钟)')
        ax3.grid(True, alpha=0.3)
        
        # 拟合精度R²
        ax4.bar(range(len(r2_values)), r2_values, color='purple', alpha=0.7)
        ax4.set_title('拟合精度R²')
        ax4.set_xlabel('断面')
        ax4.set_ylabel('R²')
        ax4.set_xticks(range(len(scenario_data)))
        ax4.set_xticklabels([f"断面{i}" for i in range(len(scenario_data))])
        ax4.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        plt.savefig(f"{scenario}_3参数IDZ辨识结果.svg", dpi=300, bbox_inches='tight')
        plt.show()

def main():
    """主函数"""
    print("=== 3参数IDZ模型精确辨识 ===")
    print("G(s) = K / [s * (τs + 1)] * exp(-T*s)")
    print("包含: 积分增益K, 时间常数τ, 纯时滞T")
    
    results = analyze_idz_parameters()
    
    print(f"\n=== 总结 ===")
    for scenario in results['场景'].unique():
        scenario_data = results[results['场景'] == scenario]
        valid_data = scenario_data[scenario_data['R²'] > 0]
        
        if len(valid_data) > 0:
            print(f"\n{scenario}:")
            print(f"  平均K: {valid_data['K'].mean():.6f}")
            print(f"  平均τ: {valid_data['τ'].mean():.2f} 分钟")
            print(f"  平均T: {valid_data['T'].mean():.2f} 分钟")
            print(f"  平均R²: {valid_data['R²'].mean():.4f}")

if __name__ == "__main__":
    main()