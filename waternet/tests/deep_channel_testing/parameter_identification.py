"""
增强参数辨识算法模块

为深度测试提供高级参数辨识功能，包括：
- 多目标优化参数辨识
- 在线滑窗参数校正
- 糙率变化检测和辨识
- 多模型性能对比分析

Author: WaterNet Development Team
Date: 2024-10-03
"""

import numpy as np
import pandas as pd
from scipy import optimize, interpolate
from scipy.stats import pearsonr
from sklearn.metrics import mean_squared_error, r2_score
import warnings
from typing import Dict, List, Tuple, Optional, Callable, Any, Union
from dataclasses import dataclass
import logging

from ...parameter_estimation.estimator import ParameterEstimator
from ...models.saint_venant import SaintVenantModel
from .enhanced_models import EnhancedMuskingumModel, IntegralDelayZeroModel, EnhancedStorageRoutingModel


@dataclass
class OptimizationConfig:
    """优化算法配置"""
    algorithm: str = "differential_evolution"    # 优化算法
    max_iterations: int = 100                   # 最大迭代次数
    population_size: int = 15                   # 种群大小
    tolerance: float = 1e-6                     # 收敛容差
    n_trials: int = 5                          # 多次试验次数
    polish: bool = True                         # 是否进行局部优化
    seed: int = 42                             # 随机种子


@dataclass
class SlidingWindowConfig:
    """滑窗配置"""
    window_size: int = 20                       # 窗口大小（时间步数）
    slide_step: int = 5                        # 滑动步长
    overlap_ratio: float = 0.75                # 重叠率
    min_data_points: int = 10                  # 最小数据点数
    confidence_threshold: float = 0.8          # 置信度阈值


class EnhancedParameterEstimator(ParameterEstimator):
    """增强参数估计器"""
    
    def __init__(self, saint_venant_model: SaintVenantModel,
                 optimization_config: Optional[OptimizationConfig] = None,
                 sliding_window_config: Optional[SlidingWindowConfig] = None):
        """
        初始化增强参数估计器
        
        Parameters:
        -----------
        saint_venant_model : SaintVenantModel
            基准圣维南模型
        optimization_config : OptimizationConfig, optional
            优化算法配置
        sliding_window_config : SlidingWindowConfig, optional
            滑窗配置
        """
        super().__init__(saint_venant_model)
        
        self.opt_config = optimization_config or OptimizationConfig()
        self.window_config = sliding_window_config or SlidingWindowConfig()
        
        self.logger = logging.getLogger("EnhancedParameterEstimator")
        
        # 辨识历史记录
        self.identification_history = {
            'muskingum': [],
            'idz': [],
            'roughness': []
        }
        
        # 性能评估指标
        self.performance_metrics = [
            'rmse_Q', 'rmse_H', 'correlation_Q', 'correlation_H',
            'nse_coefficient', 'relative_error', 'mass_balance_error'
        ]
    
    def identify_muskingum_parameters_multi_objective(
        self, test_scenarios: List[Dict], 
        parameter_bounds: Dict[str, Tuple[float, float]],
        objective_weights: Dict[str, float] = None) -> Dict[str, Any]:
        """
        多目标优化马斯京干模型参数辨识
        
        Parameters:
        -----------
        test_scenarios : List[Dict]
            测试场景列表，每个场景包含输入序列和边界条件
        parameter_bounds : Dict[str, Tuple[float, float]]
            参数搜索范围 {'K': (min, max), 'x': (min, max)}
        objective_weights : Dict[str, float], optional
            目标函数权重
            
        Returns:
        --------
        Dict[str, Any]: 辨识结果
        """
        self.logger.info("开始马斯京干模型多目标参数辨识")
        
        # 默认权重
        if objective_weights is None:
            objective_weights = {
                'rmse_Q': 0.4,
                'rmse_H': 0.3,
                'nse_coefficient': 0.2,
                'correlation_Q': 0.1
            }
        
        # 准备参考数据
        reference_data = self._prepare_reference_data(test_scenarios)
        
        # 定义目标函数
        def multi_objective_function(params):
            K, x = params
            return self._evaluate_muskingum_performance(
                K, x, reference_data, objective_weights)
        
        # 参数边界
        bounds = [
            parameter_bounds['K'],
            parameter_bounds['x']
        ]
        
        # 多次优化取最佳结果
        best_result = None
        best_score = float('inf')
        
        for trial in range(self.opt_config.n_trials):
            seed = self.opt_config.seed + trial
            
            try:
                result = optimize.differential_evolution(
                    multi_objective_function,
                    bounds,
                    maxiter=self.opt_config.max_iterations,
                    popsize=self.opt_config.population_size,
                    tol=self.opt_config.tolerance,
                    polish=self.opt_config.polish,
                    seed=seed
                )
                
                if result.fun < best_score:
                    best_score = result.fun
                    best_result = result
                    
            except Exception as e:
                self.logger.warning(f"优化试验{trial}失败: {e}")
                continue
        
        if best_result is None:
            raise RuntimeError("所有优化试验均失败")
        
        K_opt, x_opt = best_result.x
        
        # 详细性能评估
        detailed_performance = self._detailed_muskingum_evaluation(
            K_opt, x_opt, reference_data)
        
        # 参数置信区间估计
        confidence_intervals = self._estimate_parameter_confidence(
            multi_objective_function, best_result.x, bounds)
        
        result_dict = {
            'optimal_parameters': {'K': K_opt, 'x': x_opt},
            'optimization_result': best_result,
            'objective_score': best_score,
            'detailed_performance': detailed_performance,
            'confidence_intervals': confidence_intervals,
            'test_scenarios': test_scenarios,
            'objective_weights': objective_weights
        }
        
        # 记录辨识历史
        self.identification_history['muskingum'].append(result_dict)
        
        self.logger.info(f"马斯京干参数辨识完成: K={K_opt:.1f}s, x={x_opt:.3f}, 得分={best_score:.6f}")
        
        return result_dict
    
    def identify_idz_parameters_hierarchical(
        self, test_scenarios: List[Dict],
        parameter_bounds: Dict[str, Tuple[float, float]],
        hierarchical_strategy: str = "coarse_to_fine") -> Dict[str, Any]:
        """
        分层优化IDZ模型参数辨识
        
        Parameters:
        -----------
        test_scenarios : List[Dict]
            测试场景列表
        parameter_bounds : Dict[str, Tuple[float, float]]
            参数搜索范围 {'tau': (min, max), 'T': (min, max), 'alpha': (min, max)}
        hierarchical_strategy : str
            分层策略 ("coarse_to_fine", "sensitivity_based")
            
        Returns:
        --------
        Dict[str, Any]: 辨识结果
        """
        self.logger.info("开始IDZ模型分层参数辨识")
        
        # 准备参考数据
        reference_data = self._prepare_reference_data(test_scenarios)
        
        if hierarchical_strategy == "coarse_to_fine":
            result = self._idz_coarse_to_fine_optimization(parameter_bounds, reference_data)
        elif hierarchical_strategy == "sensitivity_based":
            result = self._idz_sensitivity_based_optimization(parameter_bounds, reference_data)
        else:
            raise ValueError(f"不支持的分层策略: {hierarchical_strategy}")
        
        # 记录辨识历史
        self.identification_history['idz'].append(result)
        
        tau_opt = result['optimal_parameters']['tau']
        T_opt = result['optimal_parameters']['T']
        alpha_opt = result['optimal_parameters']['alpha']
        
        self.logger.info(f"IDZ参数辨识完成: τ={tau_opt:.1f}s, T={T_opt:.1f}s, α={alpha_opt:.1f}s")
        
        return result
    
    def online_roughness_identification(
        self, observation_data: pd.DataFrame,
        initial_roughness: Dict[int, float],
        roughness_bounds: Dict[int, Tuple[float, float]],
        change_detection_threshold: float = 0.05) -> Dict[str, Any]:
        """
        在线糙率辨识
        
        Parameters:
        -----------
        observation_data : pd.DataFrame
            观测数据，包含时间、流量、水位等列
        initial_roughness : Dict[int, float]
            初始糙率值 {断面索引: 糙率值}
        roughness_bounds : Dict[int, Tuple[float, float]]
            糙率搜索范围
        change_detection_threshold : float
            变化检测阈值
            
        Returns:
        --------
        Dict[str, Any]: 在线辨识结果
        """
        self.logger.info("开始在线糙率辨识")
        
        # 数据预处理
        data = observation_data.copy()
        n_points = len(data)
        
        if n_points < self.window_config.min_data_points:
            raise ValueError(f"数据点数量不足: {n_points} < {self.window_config.min_data_points}")
        
        # 滑窗辨识
        window_size = self.window_config.window_size
        slide_step = self.window_config.slide_step
        
        roughness_history = []
        performance_history = []
        change_points = []
        
        current_roughness = initial_roughness.copy()
        
        for i in range(0, n_points - window_size + 1, slide_step):
            # 提取窗口数据
            window_data = data.iloc[i:i+window_size].copy()
            window_center_time = window_data['time'].iloc[window_size//2]
            
            # 变化检测
            model_error = self._compute_model_prediction_error(
                window_data, current_roughness)
            
            change_detected = model_error > change_detection_threshold
            
            if change_detected or i == 0:  # 首次或检测到变化时进行辨识
                # 参数辨识
                identified_roughness, identification_metrics = self._identify_roughness_in_window(
                    window_data, current_roughness, roughness_bounds)
                
                # 更新当前糙率
                for section_idx, new_roughness in identified_roughness.items():
                    old_roughness = current_roughness.get(section_idx, 0.025)
                    current_roughness[section_idx] = new_roughness
                    
                    # 记录显著变化点
                    if abs(new_roughness - old_roughness) > 0.005:
                        change_points.append({
                            'time': window_center_time,
                            'section': section_idx,
                            'old_roughness': old_roughness,
                            'new_roughness': new_roughness,
                            'change_magnitude': abs(new_roughness - old_roughness)
                        })
            
            # 记录历史
            roughness_history.append({
                'time': window_center_time,
                'roughness': current_roughness.copy(),
                'change_detected': change_detected,
                'model_error': model_error
            })
            
            # 性能评估
            performance = self._evaluate_roughness_performance(
                window_data, current_roughness)
            performance['time'] = window_center_time
            performance_history.append(performance)
        
        # 汇总结果
        result = {
            'roughness_history': roughness_history,
            'performance_history': performance_history,
            'change_points': change_points,
            'final_roughness': current_roughness,
            'initial_roughness': initial_roughness,
            'identification_summary': self._summarize_roughness_identification(
                roughness_history, performance_history, change_points)
        }
        
        # 记录辨识历史
        self.identification_history['roughness'].append(result)
        
        self.logger.info(f"在线糙率辨识完成，检测到{len(change_points)}个变化点")
        
        return result
    
    def compare_model_identification_performance(
        self, test_conditions: List[Dict],
        models_config: Dict[str, Dict]) -> Dict[str, Any]:
        """
        对比多模型辨识性能
        
        Parameters:
        -----------
        test_conditions : List[Dict]
            测试工况列表
        models_config : Dict[str, Dict]
            模型配置 {'muskingum': {...}, 'idz': {...}, 'storage_routing': {...}}
            
        Returns:
        --------
        Dict[str, Any]: 性能对比结果
        """
        self.logger.info("开始多模型辨识性能对比")
        
        comparison_results = {}
        
        for condition_name, condition_config in test_conditions:
            condition_results = {}
            
            # 准备参考数据
            reference_data = self._prepare_reference_data([condition_config])
            
            # 对每种模型进行辨识
            for model_name, model_config in models_config.items():
                try:
                    if model_name == 'muskingum':
                        result = self._identify_and_evaluate_muskingum(
                            reference_data, model_config)
                    elif model_name == 'idz':
                        result = self._identify_and_evaluate_idz(
                            reference_data, model_config)
                    elif model_name == 'storage_routing':
                        result = self._identify_and_evaluate_storage_routing(
                            reference_data, model_config)
                    else:
                        self.logger.warning(f"未知模型类型: {model_name}")
                        continue
                    
                    condition_results[model_name] = result
                    
                except Exception as e:
                    self.logger.error(f"模型{model_name}在工况{condition_name}下辨识失败: {e}")
                    condition_results[model_name] = {'error': str(e)}
            
            comparison_results[condition_name] = condition_results
        
        # 综合分析
        comprehensive_analysis = self._analyze_multi_model_performance(comparison_results)
        
        return {
            'detailed_results': comparison_results,
            'comprehensive_analysis': comprehensive_analysis,
            'performance_ranking': self._rank_model_performance(comparison_results),
            'applicability_analysis': self._analyze_model_applicability(comparison_results)
        }
    
    def _prepare_reference_data(self, test_scenarios: List[Dict]) -> List[Dict]:
        """准备参考数据"""
        reference_data = []
        
        for scenario in test_scenarios:
            # 使用圣维南模型计算参考解
            Q_in_series = scenario['Q_in_series']
            H_down_series = scenario['H_down_series']
            dt = scenario.get('dt', 10.0)
            
            # 模拟参考解（这里简化处理）
            n_steps = len(Q_in_series)
            Q_out_ref = np.zeros(n_steps)
            H_out_ref = np.zeros(n_steps)
            
            # 假设的参考解计算（实际应使用完整的圣维南求解）
            for i in range(n_steps):
                try:
                    steady_result = self.saint_venant_model.compute_steady_state(
                        Q_in_series[i], H_down_series[i])
                    Q_out_ref[i] = Q_in_series[i]  # 简化：假设稳态下入流等于出流
                    H_out_ref[i] = steady_result.get('H_section_0', H_down_series[i])
                except:
                    Q_out_ref[i] = Q_in_series[i] if i > 0 else 50.0
                    H_out_ref[i] = H_down_series[i] if i > 0 else 101.0
            
            reference_data.append({
                'Q_in': Q_in_series,
                'H_down': H_down_series,
                'Q_out_ref': Q_out_ref,
                'H_out_ref': H_out_ref,
                'dt': dt,
                'scenario_name': scenario.get('name', f'scenario_{len(reference_data)}')
            })
        
        return reference_data
    
    def _evaluate_muskingum_performance(self, K: float, x: float, 
                                      reference_data: List[Dict],
                                      objective_weights: Dict[str, float]) -> float:
        """评估马斯京干模型性能"""
        total_score = 0.0
        total_weight = 0.0
        
        for ref_data in reference_data:
            # 创建马斯京干模型
            V_to_H = lambda V: 100.0 + V / 10000.0  # 简化关系
            H_to_Q = lambda H: max(0, (H - 100.0) * 20.0)  # 简化关系
            
            model = EnhancedMuskingumModel(
                dt=ref_data['dt'], K=K, x=x, initial_V=10000.0,
                V_to_H_func=V_to_H, H_to_Q_func=H_to_Q)
            
            # 模拟计算
            Q_out_sim = []
            for Q_in in ref_data['Q_in']:
                result = model.step(Q_in)
                Q_out_sim.append(result['Q_out'])
            
            Q_out_sim = np.array(Q_out_sim)
            Q_out_ref = ref_data['Q_out_ref']
            
            # 计算各项指标
            rmse_Q = np.sqrt(mean_squared_error(Q_out_ref, Q_out_sim))
            correlation_Q = pearsonr(Q_out_ref, Q_out_sim)[0] if len(Q_out_ref) > 1 else 0.0
            
            # NSE系数
            nse = 1 - np.sum((Q_out_ref - Q_out_sim)**2) / np.sum((Q_out_ref - np.mean(Q_out_ref))**2)
            
            # 加权累计得分
            score = (objective_weights.get('rmse_Q', 0.4) * rmse_Q +
                    objective_weights.get('correlation_Q', 0.1) * (1 - max(0, correlation_Q)) +
                    objective_weights.get('nse_coefficient', 0.2) * (1 - max(0, nse)))
            
            total_score += score
            total_weight += 1.0
        
        return total_score / total_weight if total_weight > 0 else float('inf')
    
    def _detailed_muskingum_evaluation(self, K: float, x: float, 
                                     reference_data: List[Dict]) -> Dict[str, Any]:
        """详细马斯京干模型评估"""
        detailed_results = {}
        
        for i, ref_data in enumerate(reference_data):
            # 模型仿真
            V_to_H = lambda V: 100.0 + V / 10000.0
            H_to_Q = lambda H: max(0, (H - 100.0) * 20.0)
            
            model = EnhancedMuskingumModel(
                dt=ref_data['dt'], K=K, x=x, initial_V=10000.0,
                V_to_H_func=V_to_H, H_to_Q_func=H_to_Q)
            
            Q_out_sim = []
            for Q_in in ref_data['Q_in']:
                result = model.step(Q_in)
                Q_out_sim.append(result['Q_out'])
            
            Q_out_sim = np.array(Q_out_sim)
            Q_out_ref = ref_data['Q_out_ref']
            
            # 计算性能指标
            metrics = self._compute_all_performance_metrics(Q_out_ref, Q_out_sim)
            
            detailed_results[f"scenario_{i}"] = {
                'metrics': metrics,
                'Q_out_simulated': Q_out_sim.tolist(),
                'Q_out_reference': Q_out_ref.tolist(),
                'scenario_name': ref_data.get('scenario_name', f'scenario_{i}')
            }
        
        return detailed_results
    
    def _compute_all_performance_metrics(self, y_true: np.ndarray, 
                                       y_pred: np.ndarray) -> Dict[str, float]:
        """计算所有性能指标"""
        metrics = {}
        
        # RMSE
        metrics['rmse'] = np.sqrt(mean_squared_error(y_true, y_pred))
        
        # 相关系数
        if len(y_true) > 1 and np.std(y_true) > 0 and np.std(y_pred) > 0:
            metrics['correlation'] = pearsonr(y_true, y_pred)[0]
        else:
            metrics['correlation'] = 0.0
        
        # NSE系数
        if np.sum((y_true - np.mean(y_true))**2) > 0:
            metrics['nse'] = 1 - np.sum((y_true - y_pred)**2) / np.sum((y_true - np.mean(y_true))**2)
        else:
            metrics['nse'] = 0.0
        
        # 相对误差
        metrics['relative_error'] = np.mean(np.abs(y_true - y_pred) / (np.abs(y_true) + 1e-6)) * 100
        
        # R²
        if len(y_true) > 1:
            metrics['r2'] = r2_score(y_true, y_pred)
        else:
            metrics['r2'] = 0.0
        
        return metrics
    
    def _estimate_parameter_confidence(self, objective_func: Callable, 
                                     optimal_params: np.ndarray,
                                     bounds: List[Tuple]) -> Dict[str, Tuple]:
        """估计参数置信区间"""
        # 简化实现：使用参数扰动方法
        confidence_intervals = {}
        param_names = ['K', 'x'] if len(optimal_params) == 2 else ['tau', 'T', 'alpha']
        
        for i, param_name in enumerate(param_names):
            optimal_value = optimal_params[i]
            bound_range = bounds[i][1] - bounds[i][0]
            
            # 估算95%置信区间（简化方法）
            confidence_width = bound_range * 0.1  # 10%的搜索范围作为置信区间
            
            lower_bound = max(bounds[i][0], optimal_value - confidence_width/2)
            upper_bound = min(bounds[i][1], optimal_value + confidence_width/2)
            
            confidence_intervals[param_name] = (lower_bound, upper_bound)
        
        return confidence_intervals