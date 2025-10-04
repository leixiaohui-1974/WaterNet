"""
PipeParameterEstimator 管道参数估计器

基于ParameterEstimator框架的有压管道参数辨识算法。
支持波速辨识、摩擦系数辨识和降阶模型参数辨识。

核心功能:
- 波速辨识（基于互相关分析）
- 摩擦系数辨识（基于稳态能量方程）
- 降阶模型参数辨识（基于动态响应数据）
- 不确定性量化和敏感性分析

Author: WaterNet Development Team
Date: 2024-10-04
"""

import numpy as np
import pandas as pd
import warnings
from typing import Dict, List, Tuple, Optional, Any
from scipy import signal
from scipy.optimize import minimize, differential_evolution
from scipy.stats import pearsonr
import sys
import os

# 添加路径以导入模块
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from physical_objects.pressurized_pipe_model import PressurizedPipeModel
from waternet.parameter_estimation.estimator import ParameterEstimator
from waternet.models.pressurized_pipe_rom import create_pressurized_pipe_rom


class PipeParameterEstimator:
    """
    管道参数估计器
    
    为有压管道系统提供专门的参数辨识功能，包括物理参数和模型参数的估计。
    
    Attributes:
        pipe_model (PressurizedPipeModel): 作为基准的有压管道模型
        estimation_results (Dict): 参数估计结果
        optimization_history (List): 优化历史记录
    """
    
    def __init__(self, pipe_model: PressurizedPipeModel):
        """
        初始化管道参数估计器
        
        Args:
            pipe_model (PressurizedPipeModel): 作为基准的有压管道模型
        """
        if not isinstance(pipe_model, PressurizedPipeModel):
            raise TypeError("需要PressurizedPipeModel类型的管道模型")
        
        self.pipe_model = pipe_model
        self.estimation_results = {}
        self.optimization_history = []
        
        print(f"管道参数估计器初始化完成:")
        print(f"  管道模型: {pipe_model.name}")
        print(f"  管道长度: {pipe_model.total_length} m")
        print(f"  当前波速: {pipe_model.wave_speed} m/s")
    
    def identify_friction_factor(self, measured_data: List[Dict[str, float]]) -> Dict[str, Any]:
        """
        基于稳态测量数据辨识摩擦系数
        
        使用达西-魏斯巴赫公式的反算方法：
        f = (2g × h_f × D) / (L × V²)
        
        Args:
            measured_data (List[Dict]): 稳态测量数据列表
                每个字典包含: {'Q': 流量, 'H_up': 上游水头, 'H_down': 下游水头}
                
        Returns:
            Dict[str, Any]: 摩擦系数辨识结果
        """
        if len(measured_data) < 2:
            raise ValueError("至少需要2个稳态测量点")
        
        print(f"开始摩擦系数辨识，数据点数: {len(measured_data)}")
        
        friction_factors = []
        valid_data = []
        
        for i, data_point in enumerate(measured_data):
            try:
                Q = data_point['Q']
                H_up = data_point['H_up']
                H_down = data_point['H_down']
                
                if Q <= 0:
                    warnings.warn(f"数据点{i}: 流量非正值，跳过")
                    continue
                
                # 计算平均管道参数
                avg_diameter = np.mean([seg['diameter'] for seg in self.pipe_model.segments])
                avg_area = np.pi * (avg_diameter / 2.0) ** 2
                total_length = self.pipe_model.total_length
                
                # 计算水头损失
                h_f = H_up - H_down
                
                # 去除高程差影响
                elevation_diff = (self.pipe_model.nodes[0]['elevation'] - 
                                self.pipe_model.nodes[-1]['elevation'])
                friction_loss = h_f - elevation_diff
                
                if friction_loss <= 0:
                    warnings.warn(f"数据点{i}: 摩擦损失非正值，可能数据有误")
                    continue
                
                # 计算流速
                velocity = Q / avg_area
                
                # 反算摩擦系数: f = (2g × h_f × D) / (L × V²)
                f_calculated = (2 * 9.81 * friction_loss * avg_diameter) / (total_length * velocity**2)
                
                if 0.005 <= f_calculated <= 0.1:  # 合理范围检查
                    friction_factors.append(f_calculated)
                    valid_data.append({
                        'Q': Q, 'H_up': H_up, 'H_down': H_down,
                        'friction_loss': friction_loss, 'velocity': velocity,
                        'f_calculated': f_calculated
                    })
                else:
                    warnings.warn(f"数据点{i}: 计算的摩擦系数{f_calculated:.4f}超出合理范围")
                    
            except Exception as e:
                warnings.warn(f"数据点{i}处理失败: {e}")
                continue
        
        if len(friction_factors) == 0:
            raise ValueError("没有有效的数据点用于摩擦系数计算")
        
        # 统计分析
        f_mean = np.mean(friction_factors)
        f_std = np.std(friction_factors)
        f_median = np.median(friction_factors)
        
        # 加权平均（根据流量大小加权）
        weights = [data['Q'] for data in valid_data]
        f_weighted = np.average(friction_factors, weights=weights)
        
        # 异常值检测和过滤
        z_scores = np.abs((np.array(friction_factors) - f_mean) / max(f_std, 1e-6))
        valid_indices = z_scores < 3.0  # 3-sigma规则
        f_filtered = np.array(friction_factors)[valid_indices]
        
        if len(f_filtered) > 0:
            f_final = np.mean(f_filtered)
            confidence_interval = [f_final - 1.96 * f_std / np.sqrt(len(f_filtered)),
                                 f_final + 1.96 * f_std / np.sqrt(len(f_filtered))]
        else:
            f_final = f_mean
            confidence_interval = [f_mean - 1.96 * f_std, f_mean + 1.96 * f_std]
        
        # 拟合质量评估
        try:
            # 计算R²值
            observed_losses = [data['friction_loss'] for data in valid_data]
            predicted_losses = []
            
            for data in valid_data:
                V = data['velocity']
                L = self.pipe_model.total_length
                D = np.mean([seg['diameter'] for seg in self.pipe_model.segments])
                predicted_loss = f_final * (L / D) * (V**2 / (2 * 9.81))
                predicted_losses.append(predicted_loss)
            
            correlation, _ = pearsonr(observed_losses, predicted_losses)
            r_squared = correlation**2
            
        except Exception:
            r_squared = 0.0
        
        result = {
            'friction_factor': f_final,
            'confidence_interval': confidence_interval,
            'statistics': {
                'mean': f_mean,
                'median': f_median,
                'std': f_std,
                'weighted_mean': f_weighted,
                'r_squared': r_squared
            },
            'data_summary': {
                'total_points': len(measured_data),
                'valid_points': len(valid_data),
                'filtered_points': len(f_filtered)
            },
            'raw_data': valid_data
        }
        
        self.estimation_results['friction_factor'] = result
        
        print(f"摩擦系数辨识完成:")
        print(f"  最终值: {f_final:.4f}")
        print(f"  置信区间: [{confidence_interval[0]:.4f}, {confidence_interval[1]:.4f}]")
        print(f"  R²: {r_squared:.3f}")
        
        return result
    
    def identify_wave_speed(self, unsteady_data: pd.DataFrame) -> Dict[str, Any]:
        """
        基于瞬变数据辨识水锤波速
        
        使用互相关分析方法计算压力波在管道中的传播时间，进而反算波速。
        
        Args:
            unsteady_data (pd.DataFrame): 瞬变仿真数据，包含:
                - 'time': 时间序列
                - 'H_upstream': 上游水头时间序列
                - 'H_downstream': 下游水头时间序列
                或内部节点数据
                
        Returns:
            Dict[str, Any]: 波速辨识结果
        """
        print("开始波速辨识...")
        
        # 检查数据完整性
        required_columns = ['time']
        for col in required_columns:
            if col not in unsteady_data.columns:
                raise ValueError(f"缺少必需的数据列: {col}")
        
        # 提取时间序列
        time = unsteady_data['time'].values
        dt = time[1] - time[0] if len(time) > 1 else 0.01
        
        # 寻找合适的压力测点
        pressure_columns = [col for col in unsteady_data.columns if col.startswith('H_')]
        if len(pressure_columns) < 2:
            raise ValueError("至少需要两个压力测点数据")
        
        # 选择上游和下游（或最远距离的两个点）
        if 'H_upstream' in unsteady_data.columns and 'H_downstream' in unsteady_data.columns:
            p1_col, p2_col = 'H_upstream', 'H_downstream'
            distance = self.pipe_model.total_length
        elif len(pressure_columns) >= 2:
            p1_col, p2_col = pressure_columns[0], pressure_columns[-1]
            # 估算距离（简化）
            distance = self.pipe_model.total_length
        else:
            raise ValueError("无法找到合适的压力测点组合")
        
        H1 = unsteady_data[p1_col].values
        H2 = unsteady_data[p2_col].values
        
        print(f"使用测点: {p1_col} 和 {p2_col}")
        print(f"估算距离: {distance} m")
        
        # 数据预处理
        # 去除趋势（线性去趋势）
        H1_detrended = signal.detrend(H1, type='linear')
        H2_detrended = signal.detrend(H2, type='linear')
        
        # 应用窗函数以减少边界效应
        window = signal.windows.hann(len(H1_detrended))
        H1_windowed = H1_detrended * window
        H2_windowed = H2_detrended * window
        
        # 互相关分析
        try:
            # 计算互相关
            correlation = signal.correlate(H2_windowed, H1_windowed, mode='full')
            correlation = correlation / (np.linalg.norm(H1_windowed) * np.linalg.norm(H2_windowed))
            
            # 创建时间延迟轴
            n = len(H1_windowed)
            lags = np.arange(-n + 1, n) * dt
            
            # 寻找最大相关性对应的时间延迟
            max_corr_idx = np.argmax(np.abs(correlation))
            time_delay = lags[max_corr_idx]
            max_correlation = correlation[max_corr_idx]
            
            # 计算波速
            if abs(time_delay) > 1e-6:
                wave_speed = distance / abs(time_delay)
            else:
                raise ValueError("计算出的时间延迟过小，无法可靠估算波速")
            
            print(f"检测到时间延迟: {time_delay:.3f} s")
            print(f"最大相关系数: {max_correlation:.3f}")
            
        except Exception as e:
            warnings.warn(f"互相关分析失败: {e}")
            # 尝试简化方法：峰值检测
            wave_speed, time_delay, max_correlation = self._fallback_wave_speed_estimation(
                H1, H2, time, distance)
        
        # 波速合理性检查
        if not (100 <= wave_speed <= 2000):  # 水锤波速的合理范围
            warnings.warn(f"计算的波速{wave_speed:.1f} m/s 可能不合理")
        
        # 估算不确定性
        # 基于相关系数和信噪比估算
        noise_level = np.std(H1_detrended - np.mean(H1_detrended))
        signal_level = np.std(H1_detrended)
        snr = signal_level / max(noise_level, 1e-6)
        
        # 不确定性估算（经验公式）
        uncertainty_factor = max(0.05, 0.2 / max(abs(max_correlation), 0.1))
        wave_speed_uncertainty = wave_speed * uncertainty_factor
        
        confidence_interval = [wave_speed - 1.96 * wave_speed_uncertainty,
                             wave_speed + 1.96 * wave_speed_uncertainty]
        
        result = {
            'wave_speed': wave_speed,
            'time_delay': abs(time_delay),
            'max_correlation': abs(max_correlation),
            'confidence_interval': confidence_interval,
            'uncertainty': wave_speed_uncertainty,
            'statistics': {
                'distance': distance,
                'signal_to_noise_ratio': snr,
                'correlation_method': 'cross_correlation'
            },
            'analysis_details': {
                'sampling_rate': 1/dt,
                'data_points': len(H1),
                'measurement_points': [p1_col, p2_col]
            }
        }
        
        self.estimation_results['wave_speed'] = result
        
        print(f"波速辨识完成:")
        print(f"  波速: {wave_speed:.1f} m/s")
        print(f"  不确定性: ±{wave_speed_uncertainty:.1f} m/s")
        print(f"  置信区间: [{confidence_interval[0]:.1f}, {confidence_interval[1]:.1f}] m/s")
        
        return result
    
    def _fallback_wave_speed_estimation(self, H1: np.ndarray, H2: np.ndarray, 
                                      time: np.ndarray, distance: float) -> Tuple[float, float, float]:
        """备用波速估算方法（基于峰值检测）"""
        try:
            # 寻找显著变化点
            dH1_dt = np.gradient(H1, time)
            dH2_dt = np.gradient(H2, time)
            
            # 寻找最大梯度点
            max_grad1_idx = np.argmax(np.abs(dH1_dt))
            max_grad2_idx = np.argmax(np.abs(dH2_dt))
            
            time_delay = abs(time[max_grad2_idx] - time[max_grad1_idx])
            
            if time_delay > 1e-6:
                wave_speed = distance / time_delay
                # 简单的相关性估算
                correlation = np.corrcoef(H1, H2)[0, 1]
            else:
                wave_speed = 1200.0  # 默认值
                time_delay = distance / wave_speed
                correlation = 0.5
            
            return wave_speed, time_delay, correlation
            
        except Exception:
            # 最终回退到理论估算
            return 1200.0, distance / 1200.0, 0.3
    
    def identify_rom_parameters(self, steady_data: List[Dict[str, float]], 
                               dynamic_data: pd.DataFrame, 
                               rom_type: str = 'muskingum_hammer') -> Dict[str, Any]:
        """
        基于稳态和动态数据辨识降阶模型参数
        
        Args:
            steady_data (List[Dict]): 稳态数据点
            dynamic_data (pd.DataFrame): 动态响应数据
            rom_type (str): 降阶模型类型
            
        Returns:
            Dict[str, Any]: 降阶模型参数辨识结果
        """
        print(f"开始{rom_type}降阶模型参数辨识...")
        
        # 基于已辨识的物理参数创建基础参数字典
        physical_params = {
            'L': self.pipe_model.total_length,
            'D': np.mean([seg['diameter'] for seg in self.pipe_model.segments]),
            'a': self.estimation_results.get('wave_speed', {}).get('wave_speed', self.pipe_model.wave_speed),
            'f': self.estimation_results.get('friction_factor', {}).get('friction_factor', 0.02)
        }
        
        if rom_type == 'muskingum_hammer':
            return self._identify_muskingum_hammer_parameters(physical_params, dynamic_data)
        elif rom_type == 'linear_hammer':
            return self._identify_linear_hammer_parameters(physical_params, dynamic_data)
        elif rom_type == 'elastic_pipe':
            return self._identify_elastic_pipe_parameters(physical_params, dynamic_data)
        else:
            raise ValueError(f"不支持的降阶模型类型: {rom_type}")
    
    def _identify_muskingum_hammer_parameters(self, physical_params: Dict[str, float], 
                                            dynamic_data: pd.DataFrame) -> Dict[str, Any]:
        """辨识马斯京干水锤模型参数"""
        L, D, a, f = physical_params['L'], physical_params['D'], physical_params['a'], physical_params['f']
        
        # 理论计算初始值
        K_theory = L / a
        x_theory = 0.5 - (f * L) / (4 * D * a)
        x_theory = np.clip(x_theory, 0.0, 0.5)
        
        print(f"理论参数: K={K_theory:.1f}s, x={x_theory:.3f}")
        
        # 如果有动态数据，进行优化
        if len(dynamic_data) > 10:
            try:
                optimized_params = self._optimize_muskingum_parameters(
                    dynamic_data, K_theory, x_theory, physical_params)
                
                result = {
                    'K': optimized_params['K'],
                    'x': optimized_params['x'],
                    'method': 'optimized',
                    'optimization_result': optimized_params,
                    'theoretical_values': {'K': K_theory, 'x': x_theory}
                }
            except Exception as e:
                warnings.warn(f"参数优化失败，使用理论值: {e}")
                result = {
                    'K': K_theory,
                    'x': x_theory,
                    'method': 'theoretical',
                    'optimization_error': str(e)
                }
        else:
            result = {
                'K': K_theory,
                'x': x_theory,
                'method': 'theoretical',
                'note': '数据不足，使用理论计算值'
            }
        
        self.estimation_results[f'{rom_type}_parameters'] = result
        return result
    
    def _optimize_muskingum_parameters(self, dynamic_data: pd.DataFrame, 
                                     K_init: float, x_init: float,
                                     physical_params: Dict[str, float]) -> Dict[str, Any]:
        """优化马斯京干参数"""
        
        # 提取输入输出数据
        time = dynamic_data['time'].values
        dt = time[1] - time[0]
        
        # 寻找输入和输出信号
        input_col = None
        output_col = None
        
        for col in dynamic_data.columns:
            if 'Q_in' in col or col == 'Q_in':
                input_col = col
            elif 'Q_seg_0' in col:
                output_col = col
        
        if input_col is None or output_col is None:
            raise ValueError("无法找到合适的输入输出数据列")
        
        Q_in = dynamic_data[input_col].values
        Q_out = dynamic_data[output_col].values
        
        # 定义目标函数
        def objective(params):
            K, x = params
            try:
                # 计算马斯京干系数
                denominator = K - K * x + 0.5 * dt
                if abs(denominator) < 1e-10:
                    return 1e6
                
                C0 = (-K * x + 0.5 * dt) / denominator
                C1 = (K * x + 0.5 * dt) / denominator
                C2 = (K - K * x - 0.5 * dt) / denominator
                
                # 仿真
                Q_sim = np.zeros_like(Q_out)
                Q_sim[0] = Q_out[0]
                
                for i in range(1, len(Q_sim)):
                    Q_sim[i] = (C0 * Q_in[i] + 
                               C1 * Q_in[i-1] + 
                               C2 * Q_sim[i-1])
                
                # 计算误差
                rmse = np.sqrt(np.mean((Q_sim - Q_out)**2))
                return rmse
                
            except Exception:
                return 1e6
        
        # 参数边界
        bounds = [(K_init * 0.5, K_init * 2.0), (0.0, 0.5)]
        
        # 优化
        result = differential_evolution(objective, bounds, seed=42, maxiter=100)
        
        if result.success:
            K_opt, x_opt = result.x
            final_rmse = result.fun
            
            return {
                'K': K_opt,
                'x': x_opt,
                'rmse': final_rmse,
                'success': True,
                'iterations': result.nit
            }
        else:
            raise ValueError("参数优化未收敛")
    
    def _identify_linear_hammer_parameters(self, physical_params: Dict[str, float], 
                                         dynamic_data: pd.DataFrame) -> Dict[str, Any]:
        """辨识线性化水锤模型参数"""
        L, D, a, f = physical_params['L'], physical_params['D'], physical_params['a'], physical_params['f']
        
        # 计算传递函数参数
        tau1 = L**2 / (6 * a**2)
        tau2 = f * L / (2 * D * a)
        alpha1 = L**2 / (np.pi**2 * a**2)
        alpha2 = f * L / (D * a)
        
        result = {
            'tau1': tau1,
            'tau2': tau2,
            'alpha1': alpha1,
            'alpha2': alpha2,
            'method': 'analytical',
            'transfer_function': f'G(s) = ({tau1:.2e}s² + {tau2:.2e}s + 1) / ({alpha1:.2e}s² + {alpha2:.2e}s + 1)'
        }
        
        return result
    
    def _identify_elastic_pipe_parameters(self, physical_params: Dict[str, float], 
                                        dynamic_data: pd.DataFrame) -> Dict[str, Any]:
        """辨识弹性管道模型参数"""
        L, D, a, f = physical_params['L'], physical_params['D'], physical_params['a'], physical_params['f']
        
        # 计算参数
        K = 1.0
        T_delay = L / a
        tau1 = f * L / (4 * D * a)
        alpha1 = L / (2 * a)
        alpha2 = f * L / (D * a)
        
        result = {
            'K': K,
            'T_delay': T_delay,
            'tau1': tau1,
            'alpha1': alpha1,
            'alpha2': alpha2,
            'method': 'analytical'
        }
        
        return result
    
    def get_estimation_summary(self) -> Dict[str, Any]:
        """获取参数估计摘要"""
        summary = {
            'pipe_model': self.pipe_model.name,
            'estimated_parameters': self.estimation_results,
            'recommendations': []
        }
        
        # 添加建议
        if 'friction_factor' in self.estimation_results:
            f_result = self.estimation_results['friction_factor']
            if f_result['statistics']['r_squared'] < 0.8:
                summary['recommendations'].append("摩擦系数拟合质量较差，建议检查数据质量")
        
        if 'wave_speed' in self.estimation_results:
            a_result = self.estimation_results['wave_speed']
            if a_result['max_correlation'] < 0.5:
                summary['recommendations'].append("波速辨识的相关性较低，结果可能不够可靠")
        
        return summary


def run_parameter_identification_demo():
    """运行参数辨识演示"""
    print("="*60)  
    print("有压管道参数辨识演示")
    print("="*60)
    
    try:
        # 创建演示管道模型
        from waternet.tests.run_pipe_simulation import create_demo_pipe_model
        pipe_model = create_demo_pipe_model()
        
        # 创建参数估计器
        estimator = PipeParameterEstimator(pipe_model)
        
        # 1. 摩擦系数辨识演示
        print("\n1. 摩擦系数辨识演示")
        steady_data = [
            {'Q': 1.0, 'H_up': 105.1, 'H_down': 95.0},
            {'Q': 1.5, 'H_up': 106.8, 'H_down': 95.0},
            {'Q': 2.0, 'H_up': 109.2, 'H_down': 95.0},
            {'Q': 2.5, 'H_up': 112.5, 'H_down': 95.0}
        ]
        
        friction_result = estimator.identify_friction_factor(steady_data)
        
        # 2. 如果有仿真数据，进行波速辨识
        print("\n2. 检查是否有仿真数据进行波速辨识...")
        
        # 尝试读取仿真结果
        csv_path = os.path.join(os.path.dirname(__file__), '..', 'tests', 'pipe_hammer_response.csv')
        if os.path.exists(csv_path):
            print("找到仿真数据，进行波速辨识...")
            dynamic_data = pd.read_csv(csv_path)
            wave_speed_result = estimator.identify_wave_speed(dynamic_data)
            
            # 3. 降阶模型参数辨识
            print("\n3. 降阶模型参数辨识...")
            rom_result = estimator.identify_rom_parameters(
                steady_data, dynamic_data, 'muskingum_hammer')
            
        else:
            print("未找到仿真数据，跳过波速辨识")
        
        # 4. 输出摘要
        print("\n4. 参数估计摘要")
        summary = estimator.get_estimation_summary()
        
        print("\n参数辨识结果:")
        for param_type, result in summary['estimated_parameters'].items():
            print(f"\n{param_type}:")
            if isinstance(result, dict):
                for key, value in result.items():
                    if isinstance(value, (int, float)):
                        print(f"  {key}: {value:.4f}")
                    elif isinstance(value, list) and len(value) == 2:
                        print(f"  {key}: [{value[0]:.4f}, {value[1]:.4f}]")
        
        if summary['recommendations']:
            print("\n建议:")
            for rec in summary['recommendations']:
                print(f"  - {rec}")
        
        print("\n✅ 参数辨识演示完成!")
        return estimator, summary
        
    except Exception as e:
        print(f"\n❌ 参数辨识演示失败: {e}")
        import traceback
        traceback.print_exc()
        return None, None


if __name__ == "__main__":
    estimator, summary = run_parameter_identification_demo()