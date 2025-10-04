#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改进的IDZ模型辨识分析
专门针对水力系统的阶跃响应特性进行优化

考虑到水力系统的特殊性：
1. 可能存在波浪传播延迟
2. 响应可能不是纯指数形式
3. 需要考虑空间传播特性
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

class HydraulicIDZIdentifier:
    """水力系统专用IDZ模型辨识器"""
    
    def __init__(self):
        self.identified_models = {}
        self.wave_velocities = {}
        
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
    
    def analyze_wave_propagation(self, step_data, scenario):
        """分析波浪传播特性"""
        if scenario not in step_data:
            return {}
            
        # 找到各断面的响应开始时间（50%变化点）
        response_times = {}
        distances = {}
        
        for section, data in step_data[scenario].items():
            # 获取初始和最终值
            if '水位阶跃' in scenario:
                values = data['水位(m)'].values
            else:
                values = data['流量(m³/s)'].values
            
            times = data['时间(分钟)'].values
            
            if len(values) < 3:
                continue
                
            initial_val = values[0]
            final_val = values[-1]
            
            # 如果没有明显变化，跳过
            if abs(final_val - initial_val) < 1e-6:
                continue
                
            # 找到50%变化点
            target_val = initial_val + 0.5 * (final_val - initial_val)
            
            # 找最接近目标值的时间点
            idx = np.argmin(np.abs(values - target_val))
            response_time = times[idx]
            
            response_times[section] = response_time
            distances[section] = data['里程(km)'].iloc[0]
        
        # 计算波速
        wave_velocities = []
        if len(response_times) > 1:
            sections_sorted = sorted(response_times.keys(), 
                                   key=lambda x: distances[x])
            
            for i in range(1, len(sections_sorted)):
                s1, s2 = sections_sorted[i-1], sections_sorted[i]
                dt = response_times[s2] - response_times[s1]  # 分钟
                dx = (distances[s2] - distances[s1]) * 1000  # 转换为米
                
                if dt > 0:
                    velocity = dx / (dt * 60)  # m/s
                    wave_velocities.append(velocity)
        
        avg_velocity = np.mean(wave_velocities) if wave_velocities else 1.0
        
        return {
            'response_times': response_times,
            'distances': distances,
            'wave_velocities': wave_velocities,
            'avg_velocity': avg_velocity
        }
    
    def hydraulic_response_model(self, t, K, tau, td, alpha=1.0):
        """
        水力系统响应模型
        考虑传播延迟和可能的非指数响应
        G(s) = K * exp(-td*s) / (tau*s + 1)^alpha
        """
        response = np.zeros_like(t)
        mask = t >= td
        
        if alpha == 1.0:
            # 标准一阶响应
            response[mask] = K * (1 - np.exp(-(t[mask] - td) / tau))
        else:
            # 分数阶响应（近似）
            t_eff = (t[mask] - td) / tau
            response[mask] = K * (1 - np.exp(-t_eff) * (1 + alpha * t_eff / 2))
        
        return response
    
    def pade_approximation_model(self, t, K, tau1, tau2, td):
        """
        Pade近似模型，适用于有传输延迟的系统
        G(s) = K * (1 - tau2*s) / (1 + tau1*s) * exp(-td*s)
        """
        response = np.zeros_like(t)
        mask = t >= td
        
        t_eff = t[mask] - td
        # 简化的Pade近似响应
        if tau1 > 0:
            exp_term = np.exp(-t_eff / tau1)
            response[mask] = K * (1 - exp_term * (1 + t_eff * tau2 / tau1))
        
        return response
    
    def identify_hydraulic_model(self, t, y, distance=0):
        """辨识水力系统模型"""
        models = []
        
        # 基本参数估计
        steady_state = y[-1] if len(y) > 0 else 1.0
        K_init = steady_state
        
        # 估计响应时间
        response_63 = 0.632 * abs(steady_state)
        try:
            idx_63 = np.argmin(np.abs(np.abs(y) - response_63))
            tau_init = max(t[idx_63], 0.5)
        except:
            tau_init = 2.0
        
        # 估计传播延迟
        response_10 = 0.1 * abs(steady_state)
        try:
            idx_10 = np.argmin(np.abs(np.abs(y) - response_10))
            td_init = max(t[idx_10] - 0.5, 0)
        except:
            td_init = distance * 0.1  # 基于距离的粗略估计
        
        # 模型1: 标准一阶系统
        try:
            def model1(t, K, tau, td):
                return self.hydraulic_response_model(t, K, tau, td, alpha=1.0)
            
            bounds = ([0, 0.1, 0], [10*abs(K_init), 20, 10])
            popt1, _ = curve_fit(model1, t, y, p0=[K_init, tau_init, td_init], 
                               bounds=bounds, maxfev=3000)
            
            y_pred1 = model1(t, *popt1)
            r2_1 = self.calculate_r_squared(y, y_pred1)
            
            models.append({
                'type': 'first_order',
                'params': {'K': popt1[0], 'tau': popt1[1], 'td': popt1[2]},
                'r2': r2_1,
                'rmse': np.sqrt(np.mean((y - y_pred1)**2)),
                'predict_func': lambda t: model1(t, *popt1)
            })
        except Exception as e:
            print(f"  一阶模型拟合失败: {e}")
        
        # 模型2: Pade近似模型
        try:
            bounds = ([0, 0.1, 0.01, 0], [10*abs(K_init), 10, 10, 10])
            popt2, _ = curve_fit(self.pade_approximation_model, t, y,
                               p0=[K_init, tau_init, tau_init*0.5, td_init],
                               bounds=bounds, maxfev=3000)
            
            y_pred2 = self.pade_approximation_model(t, *popt2)
            r2_2 = self.calculate_r_squared(y, y_pred2)
            
            models.append({
                'type': 'pade',
                'params': {'K': popt2[0], 'tau1': popt2[1], 'tau2': popt2[2], 'td': popt2[3]},
                'r2': r2_2,
                'rmse': np.sqrt(np.mean((y - y_pred2)**2)),
                'predict_func': lambda t: self.pade_approximation_model(t, *popt2)
            })
        except Exception as e:
            print(f"  Pade模型拟合失败: {e}")
        
        # 模型3: 简单线性趋势模型（作为基准）
        try:
            if len(t) > 2:
                # 线性拟合
                coeffs = np.polyfit(t, y, 1)
                y_pred3 = np.polyval(coeffs, t)
                r2_3 = self.calculate_r_squared(y, y_pred3)
                
                models.append({
                    'type': 'linear',
                    'params': {'slope': coeffs[0], 'intercept': coeffs[1]},
                    'r2': r2_3,
                    'rmse': np.sqrt(np.mean((y - y_pred3)**2)),
                    'predict_func': lambda t: np.polyval(coeffs, t)
                })
        except Exception as e:
            print(f"  线性模型拟合失败: {e}")
        
        # 选择最佳模型
        if models:
            best_model = max(models, key=lambda x: x['r2'])
            return best_model, models
        else:
            return None, []
    
    def calculate_r_squared(self, y_true, y_pred):
        """计算决定系数R²"""
        ss_res = np.sum((y_true - y_pred) ** 2)
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
        return 1 - (ss_res / ss_tot) if ss_tot > 1e-10 else 0
    
    def preprocess_response_data(self, time_data, output_data, input_magnitude):
        """预处理响应数据"""
        # 时间归一化
        time_normalized = time_data - time_data.iloc[0]
        
        # 计算相对变化
        initial_value = output_data.iloc[0]
        final_value = output_data.iloc[-1]
        
        # 归一化响应
        if abs(input_magnitude) > 1e-6:
            response = (output_data - initial_value) / abs(input_magnitude)
        else:
            response = output_data - initial_value
            
        return time_normalized.values, response.values, initial_value, final_value
    
    def identify_all_models(self, step_data, input_magnitudes):
        """辨识所有场景的模型"""
        all_models = {}
        
        for scenario, magnitude in input_magnitudes.items():
            if scenario not in step_data:
                continue
                
            print(f"\n{'='*60}")
            print(f"正在分析场景: {scenario}")
            
            # 分析波浪传播特性
            wave_info = self.analyze_wave_propagation(step_data, scenario)
            self.wave_velocities[scenario] = wave_info
            
            if wave_info['avg_velocity'] > 0:
                print(f"平均波速: {wave_info['avg_velocity']:.2f} m/s")
            
            scenario_models = {}
            
            for section, data in step_data[scenario].items():
                print(f"\n正在辨识 {section} 的模型...")
                
                # 确定输出变量
                if '水位阶跃' in scenario:
                    output_col = '水位(m)'
                else:
                    output_col = '流量(m³/s)'
                
                # 预处理数据
                t, y, initial_val, final_val = self.preprocess_response_data(
                    data['时间(分钟)'], data[output_col], magnitude
                )
                
                distance = data['里程(km)'].iloc[0]
                
                if len(t) < 4:
                    print(f"  数据点不足，跳过")
                    continue
                
                # 检查是否有实际响应
                if np.std(y) < 1e-6:
                    print(f"  无明显响应，创建零响应模型")
                    scenario_models[section] = {
                        'best_model': {
                            'type': 'no_response',
                            'params': {'K': 0},
                            'r2': 1.0,
                            'rmse': 0.0
                        },
                        'time_data': t,
                        'response_data': y,
                        'original_data': data,
                        'initial_value': initial_val,
                        'final_value': final_val
                    }
                    continue
                
                # 辨识模型
                best_model, all_model_attempts = self.identify_hydraulic_model(t, y, distance)
                
                if best_model:
                    scenario_models[section] = {
                        'best_model': best_model,
                        'all_models': all_model_attempts,
                        'time_data': t,
                        'response_data': y,
                        'original_data': data,
                        'initial_value': initial_val,
                        'final_value': final_val
                    }
                    
                    print(f"  最佳模型: {best_model['type']}, R² = {best_model['r2']:.4f}")
                    if best_model['type'] == 'first_order':
                        params = best_model['params']
                        print(f"    传递函数: G(s) = {params['K']:.3f} / ({params['tau']:.2f}s + 1) * exp(-{params['td']:.2f}s)")
                else:
                    print(f"  模型辨识失败")
            
            if scenario_models:
                all_models[scenario] = scenario_models
        
        return all_models
    
    def plot_identification_results(self, all_models):
        """绘制辨识结果"""
        for scenario, scenario_models in all_models.items():
            n_sections = len(scenario_models)
            if n_sections == 0:
                continue
                
            fig, axes = plt.subplots(2, 3, figsize=(18, 12))
            fig.suptitle(f'{scenario} - 改进IDZ模型辨识结果', fontsize=16, fontweight='bold')
            
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
                
                # 绘制拟合结果
                if best_model['type'] != 'no_response':
                    t_fine = np.linspace(0, t[-1], 100)
                    try:
                        y_pred = best_model['predict_func'](t_fine)
                        ax.plot(t_fine, y_pred, 'r-', 
                               label=f'{best_model["type"]} (R²={best_model["r2"]:.3f})', 
                               linewidth=2)
                    except:
                        pass
                
                # 添加模型信息
                params = best_model['params']
                if best_model['type'] == 'first_order':
                    title = f'{section}\nG(s)={params["K"]:.3f}/({params["tau"]:.2f}s+1)·e^{{-{params["td"]:.2f}s}}'
                elif best_model['type'] == 'pade':
                    title = f'{section}\nPade近似模型 (R²={best_model["r2"]:.3f})'
                elif best_model['type'] == 'linear':
                    title = f'{section}\n线性模型 (R²={best_model["r2"]:.3f})'
                else:
                    title = f'{section}\n无响应模型'
                
                ax.set_title(title, fontsize=10)
                ax.set_xlabel('时间 (分钟)')
                ax.set_ylabel('归一化响应')
                ax.grid(True, alpha=0.3)
                ax.legend(fontsize=8)
            
            # 隐藏多余的子图
            for i in range(n_sections, len(axes)):
                axes[i].set_visible(False)
            
            plt.tight_layout()
            save_path = f"{scenario}_改进IDZ模型辨识结果.png"
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"模型辨识结果图已保存: {save_path}")
            plt.show()
    
    def generate_comprehensive_report(self, all_models, save_path=None):
        """生成综合辨识报告"""
        report_data = []
        
        for scenario, scenario_models in all_models.items():
            for section, model_data in scenario_models.items():
                best_model = model_data['best_model']
                
                row = {
                    '场景': scenario,
                    '断面': section,
                    '里程(km)': model_data['original_data']['里程(km)'].iloc[0],
                    '模型类型': best_model['type'],
                    'R²': f"{best_model['r2']:.4f}",
                    'RMSE': f"{best_model['rmse']:.6f}",
                    '初始值': f"{model_data['initial_value']:.3f}",
                    '最终值': f"{model_data['final_value']:.3f}"
                }
                
                params = best_model['params']
                if best_model['type'] == 'first_order':
                    row.update({
                        '增益K': f"{params['K']:.4f}",
                        '时间常数τ': f"{params['tau']:.3f}",
                        '纯延迟td': f"{params['td']:.3f}",
                        '传递函数': f"G(s) = {params['K']:.3f} / ({params['tau']:.2f}s + 1) * exp(-{params['td']:.2f}s)"
                    })
                elif best_model['type'] == 'pade':
                    row.update({
                        '增益K': f"{params['K']:.4f}",
                        'τ1': f"{params['tau1']:.3f}",
                        'τ2': f"{params['tau2']:.3f}",
                        '纯延迟td': f"{params['td']:.3f}",
                        '传递函数': f"Pade近似模型"
                    })
                elif best_model['type'] == 'linear':
                    row.update({
                        '斜率': f"{params['slope']:.6f}",
                        '截距': f"{params['intercept']:.6f}",
                        '传递函数': f"线性趋势模型"
                    })
                else:
                    row.update({
                        '传递函数': "无响应"
                    })
                
                report_data.append(row)
        
        df_report = pd.DataFrame(report_data)
        
        if save_path:
            df_report.to_csv(save_path, index=False, encoding='utf-8-sig')
            print(f"综合辨识报告已保存: {save_path}")
        
        return df_report

def main():
    """主函数"""
    print("=== 改进的水力系统IDZ模型辨识分析 ===\n")
    
    # 初始化辨识器
    identifier = HydraulicIDZIdentifier()
    
    # 加载数据
    data_file = "各断面时间序列详细数据.csv"
    step_data = identifier.load_step_response_data(data_file)
    
    print(f"成功加载数据，包含场景: {list(step_data.keys())}")
    
    # 定义输入幅值
    input_magnitudes = {
        '上游正阶跃': 20.0,    # 流量从30增加到50
        '上游负阶跃': -20.0,   # 流量从50减少到30
        '下游水位阶跃': 0.5     # 水位从101.0增加到101.5
    }
    
    # 辨识所有模型
    all_models = identifier.identify_all_models(step_data, input_magnitudes)
    
    if all_models:
        # 绘制辨识结果
        identifier.plot_identification_results(all_models)
        
        # 生成综合报告
        report_df = identifier.generate_comprehensive_report(
            all_models, "改进IDZ模型辨识报告.csv"
        )
        
        print(f"\n{'='*60}")
        print("=== 改进IDZ模型辨识结果汇总 ===")
        print(report_df.to_string(index=False))
        
        # 生成波速分析报告
        print(f"\n{'='*60}")
        print("=== 波浪传播特性分析 ===")
        for scenario, wave_info in identifier.wave_velocities.items():
            print(f"\n{scenario}:")
            if wave_info['avg_velocity'] > 0:
                print(f"  平均波速: {wave_info['avg_velocity']:.2f} m/s")
                print(f"  响应时间分布: {wave_info['response_times']}")
            else:
                print(f"  未检测到明显的波浪传播特性")
        
        print(f"\n=== 改进IDZ模型辨识完成 ===")
        print(f"成功辨识了 {len(all_models)} 个场景的动态模型")
        print(f"考虑了水力系统的传播延迟和非线性特性")
    else:
        print("未能成功辨识任何模型，请检查数据质量")

if __name__ == "__main__":
    main()