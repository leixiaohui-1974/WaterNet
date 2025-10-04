#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IDZ模型辨识分析
基于阶跃响应数据辨识水力系统的传递函数模型

IDZ模型是一种经典的系统辨识方法，用于从输入输出数据中确定系统的传递函数。
对于水力系统，可以辨识流量变化对水位响应的动态特性。
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import signal
from scipy.optimize import curve_fit, minimize
import warnings
warnings.filterwarnings('ignore')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class IDZModelIdentifier:
    """IDZ模型辨识器"""
    
    def __init__(self):
        self.identified_models = {}
        self.model_metrics = {}
        
    def load_step_response_data(self, csv_file):
        """加载阶跃响应数据"""
        df = pd.read_csv(csv_file, encoding='utf-8-sig')
        
        # 按场景和断面分组
        scenarios = df['场景'].unique()
        sections = df['断面'].unique()
        
        step_data = {}
        for scenario in scenarios:
            step_data[scenario] = {}
            for section in sections:
                mask = (df['场景'] == scenario) & (df['断面'] == section)
                section_data = df[mask].copy()
                if len(section_data) > 0:
                    step_data[scenario][section] = section_data.sort_values('时间(分钟)')
        
        return step_data
    
    def preprocess_step_response(self, time_data, output_data, input_magnitude):
        """预处理阶跃响应数据"""
        # 确保时间从0开始
        time_normalized = time_data - time_data.iloc[0]
        
        # 计算响应变化量
        initial_value = output_data.iloc[0]
        response = output_data - initial_value
        
        # 归一化响应（除以输入幅值）
        if abs(input_magnitude) > 1e-6:
            normalized_response = response / input_magnitude
        else:
            normalized_response = response
            
        return time_normalized.values, normalized_response.values
    
    def first_order_model(self, t, K, tau, td=0):
        """一阶惯性环节模型: G(s) = K / (tau*s + 1) * exp(-td*s)"""
        response = np.zeros_like(t)
        mask = t >= td
        response[mask] = K * (1 - np.exp(-(t[mask] - td) / tau))
        return response
    
    def second_order_model(self, t, K, tau1, tau2, td=0):
        """二阶模型: G(s) = K / ((tau1*s + 1)*(tau2*s + 1)) * exp(-td*s)"""
        response = np.zeros_like(t)
        mask = t >= td
        
        if abs(tau1 - tau2) < 1e-6:  # 重根情况
            response[mask] = K * (1 - (1 + (t[mask] - td) / tau1) * np.exp(-(t[mask] - td) / tau1))
        else:  # 不同根
            a1 = tau1 / (tau1 - tau2)
            a2 = tau2 / (tau2 - tau1)
            response[mask] = K * (1 - a1 * np.exp(-(t[mask] - td) / tau1) - a2 * np.exp(-(t[mask] - td) / tau2))
        
        return response
    
    def identify_first_order(self, t, y):
        """辨识一阶模型参数"""
        try:
            # 初始参数估计
            steady_state = y[-1] if len(y) > 0 else 1.0
            K_init = steady_state
            
            # 估计时间常数（63.2%响应时间）
            target_value = 0.632 * steady_state
            idx = np.argmin(np.abs(y - target_value))
            tau_init = t[idx] if idx > 0 else 1.0
            tau_init = max(tau_init, 0.1)  # 确保正值
            
            # 参数拟合
            bounds = ([0, 0.01, 0], [10*abs(K_init), 100, 10])
            popt, pcov = curve_fit(self.first_order_model, t, y, 
                                 p0=[K_init, tau_init, 0], 
                                 bounds=bounds, maxfev=2000)
            
            # 计算拟合质量
            y_pred = self.first_order_model(t, *popt)
            r2 = self.calculate_r_squared(y, y_pred)
            rmse = np.sqrt(np.mean((y - y_pred)**2))
            
            return {
                'K': popt[0], 'tau': popt[1], 'td': popt[2],
                'r2': r2, 'rmse': rmse, 'model_type': 'first_order'
            }
        except Exception as e:
            print(f"一阶模型辨识失败: {e}")
            return None
    
    def identify_second_order(self, t, y):
        """辨识二阶模型参数"""
        try:
            # 初始参数估计
            steady_state = y[-1] if len(y) > 0 else 1.0
            K_init = steady_state
            
            # 简单的时间常数估计
            tau1_init = 1.0
            tau2_init = 2.0
            
            # 参数拟合
            bounds = ([0, 0.01, 0.01, 0], [10*abs(K_init), 50, 50, 10])
            popt, pcov = curve_fit(self.second_order_model, t, y,
                                 p0=[K_init, tau1_init, tau2_init, 0],
                                 bounds=bounds, maxfev=2000)
            
            # 计算拟合质量
            y_pred = self.second_order_model(t, *popt)
            r2 = self.calculate_r_squared(y, y_pred)
            rmse = np.sqrt(np.mean((y - y_pred)**2))
            
            return {
                'K': popt[0], 'tau1': popt[1], 'tau2': popt[2], 'td': popt[3],
                'r2': r2, 'rmse': rmse, 'model_type': 'second_order'
            }
        except Exception as e:
            print(f"二阶模型辨识失败: {e}")
            return None
    
    def calculate_r_squared(self, y_true, y_pred):
        """计算决定系数R²"""
        ss_res = np.sum((y_true - y_pred) ** 2)
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
        return 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
    
    def identify_models_for_scenario(self, step_data, scenario, input_magnitude):
        """为特定场景辨识所有断面的模型"""
        scenario_models = {}
        
        if scenario not in step_data:
            return scenario_models
            
        for section, data in step_data[scenario].items():
            print(f"\n正在辨识 {scenario} - {section} 的模型...")
            
            # 预处理数据
            time_col = '时间(分钟)'
            output_col = '水位(m)' if '水位阶跃' in scenario else '流量(m³/s)'
            
            t, y = self.preprocess_step_response(
                data[time_col], data[output_col], input_magnitude
            )
            
            if len(t) < 4:  # 数据点太少
                continue
                
            # 辨识一阶和二阶模型
            first_order = self.identify_first_order(t, y)
            second_order = self.identify_second_order(t, y)
            
            # 选择最佳模型
            models = [m for m in [first_order, second_order] if m is not None]
            if models:
                # 优先选择R²更高的模型，如果差别不大则选择简单模型
                best_model = max(models, key=lambda x: x['r2'])
                if len(models) > 1:
                    r2_diff = abs(models[0]['r2'] - models[1]['r2'])
                    if r2_diff < 0.05:  # R²差别小于5%，选择一阶模型
                        best_model = first_order if first_order else second_order
                
                scenario_models[section] = {
                    'best_model': best_model,
                    'all_models': models,
                    'time_data': t,
                    'response_data': y,
                    'original_data': data
                }
                
                print(f"  最佳模型: {best_model['model_type']}, R² = {best_model['r2']:.4f}")
        
        return scenario_models
    
    def plot_model_identification_results(self, scenario_models, scenario, save_path=None):
        """绘制模型辨识结果"""
        n_sections = len(scenario_models)
        if n_sections == 0:
            return
            
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle(f'{scenario} - IDZ模型辨识结果', fontsize=16, fontweight='bold')
        
        axes = axes.flatten()
        
        for i, (section, model_data) in enumerate(scenario_models.items()):
            if i >= len(axes):
                break
                
            ax = axes[i]
            
            t = model_data['time_data']
            y_actual = model_data['response_data']
            best_model = model_data['best_model']
            
            # 绘制实际响应
            ax.plot(t, y_actual, 'bo-', label='实际响应', markersize=4)
            
            # 绘制拟合模型
            t_fine = np.linspace(0, t[-1], 100)
            if best_model['model_type'] == 'first_order':
                y_pred = self.first_order_model(t_fine, best_model['K'], 
                                              best_model['tau'], best_model['td'])
                model_str = f"$G(s) = \\frac{{{best_model['K']:.3f}}}{{s \\cdot {best_model['tau']:.2f} + 1}}$"
                if best_model['td'] > 0.01:
                    model_str += f"$e^{{-{best_model['td']:.2f}s}}$"
            else:
                y_pred = self.second_order_model(t_fine, best_model['K'], 
                                               best_model['tau1'], best_model['tau2'], best_model['td'])
                model_str = f"$G(s) = \\frac{{{best_model['K']:.3f}}}{{({best_model['tau1']:.2f}s+1)({best_model['tau2']:.2f}s+1)}}$"
            
            ax.plot(t_fine, y_pred, 'r-', label=f'辨识模型 (R²={best_model["r2"]:.3f})', linewidth=2)
            
            ax.set_title(f'{section}\n{model_str}', fontsize=10)
            ax.set_xlabel('时间 (分钟)')
            ax.set_ylabel('归一化响应')
            ax.grid(True, alpha=0.3)
            ax.legend(fontsize=8)
        
        # 隐藏多余的子图
        for i in range(n_sections, len(axes)):
            axes[i].set_visible(False)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"模型辨识结果图已保存: {save_path}")
        
        plt.show()
    
    def generate_identification_report(self, all_models, save_path=None):
        """生成辨识报告"""
        report_data = []
        
        for scenario, scenario_models in all_models.items():
            for section, model_data in scenario_models.items():
                best_model = model_data['best_model']
                
                row = {
                    '场景': scenario,
                    '断面': section,
                    '里程(km)': model_data['original_data']['里程(km)'].iloc[0],
                    '模型类型': best_model['model_type'],
                    '增益K': f"{best_model['K']:.4f}",
                    'R²': f"{best_model['r2']:.4f}",
                    'RMSE': f"{best_model['rmse']:.6f}"
                }
                
                if best_model['model_type'] == 'first_order':
                    row['时间常数τ'] = f"{best_model['tau']:.3f}"
                    row['纯延迟td'] = f"{best_model['td']:.3f}"
                    row['传递函数'] = f"K/(τs+1), K={best_model['K']:.3f}, τ={best_model['tau']:.3f}"
                else:
                    row['时间常数τ1'] = f"{best_model['tau1']:.3f}"
                    row['时间常数τ2'] = f"{best_model['tau2']:.3f}"
                    row['纯延迟td'] = f"{best_model['td']:.3f}"
                    row['传递函数'] = f"K/((τ1s+1)(τ2s+1)), K={best_model['K']:.3f}, τ1={best_model['tau1']:.3f}, τ2={best_model['tau2']:.3f}"
                
                report_data.append(row)
        
        df_report = pd.DataFrame(report_data)
        
        if save_path:
            df_report.to_csv(save_path, index=False, encoding='utf-8-sig')
            print(f"辨识报告已保存: {save_path}")
        
        return df_report

def main():
    """主函数"""
    print("=== IDZ模型辨识分析 ===\n")
    
    # 初始化辨识器
    identifier = IDZModelIdentifier()
    
    # 加载数据
    data_file = "各断面时间序列详细数据.csv"
    step_data = identifier.load_step_response_data(data_file)
    
    print(f"成功加载数据，包含场景: {list(step_data.keys())}")
    
    # 定义输入幅值（根据实际阶跃大小）
    input_magnitudes = {
        '上游正阶跃': 20.0,  # 流量从30增加到50
        '上游负阶跃': -20.0,  # 流量从50减少到30
        '下游水位阶跃': 0.5   # 水位从101.0增加到101.5
    }
    
    # 辨识所有场景的模型
    all_models = {}
    for scenario in step_data.keys():
        if scenario in input_magnitudes:
            print(f"\n{'='*50}")
            print(f"正在处理场景: {scenario}")
            print(f"输入幅值: {input_magnitudes[scenario]}")
            
            scenario_models = identifier.identify_models_for_scenario(
                step_data, scenario, input_magnitudes[scenario]
            )
            
            if scenario_models:
                all_models[scenario] = scenario_models
                
                # 绘制辨识结果
                save_path = f"{scenario}_IDZ模型辨识结果.png"
                identifier.plot_model_identification_results(
                    scenario_models, scenario, save_path
                )
    
    # 生成综合报告
    if all_models:
        print(f"\n{'='*50}")
        print("生成IDZ模型辨识综合报告...")
        
        report_df = identifier.generate_identification_report(
            all_models, "IDZ模型辨识报告.csv"
        )
        
        print("\n=== 辨识结果汇总 ===")
        print(report_df.to_string(index=False))
        
        # 绘制综合对比图
        plt.figure(figsize=(16, 12))
        
        subplot_idx = 1
        for scenario, scenario_models in all_models.items():
            plt.subplot(2, 2, subplot_idx)
            
            for section, model_data in scenario_models.items():
                best_model = model_data['best_model']
                section_name = section.replace('断面', 'S')
                plt.bar(section_name, best_model['r2'], alpha=0.7, 
                       label=f"R²={best_model['r2']:.3f}")
            
            plt.title(f'{scenario} - 模型拟合精度', fontweight='bold')
            plt.ylabel('R²')
            plt.ylim(0, 1)
            plt.grid(True, alpha=0.3)
            plt.xticks(rotation=45)
            
            subplot_idx += 1
        
        plt.tight_layout()
        plt.savefig("IDZ模型辨识精度汇总.png", dpi=300, bbox_inches='tight')
        plt.show()
        
        print(f"\n=== IDZ模型辨识完成 ===")
        print(f"共辨识了 {len(all_models)} 个场景的动态模型")
        print(f"生成了详细的传递函数参数和拟合精度评估")
    else:
        print("未能成功辨识任何模型，请检查数据质量")

if __name__ == "__main__":
    main()