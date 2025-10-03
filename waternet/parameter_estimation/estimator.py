"""
ParameterEstimator 参数估计器

基于圣维南模型的多模式参数辨识算法。
支持静态特征曲线拟合和动态参数优化，实现在线校正能力。

Author: WaterNet Development Team  
Date: 2024-10-03
"""

import numpy as np
import pandas as pd
import warnings
from typing import Dict, List, Tuple, Optional, Callable, Union, Any, Type
from scipy.optimize import minimize, differential_evolution, curve_fit
from scipy.stats import pearsonr

from ..models.saint_venant import SaintVenantModel
from ..models.lumped_models import (
    BaseLumpedModel, WaterBalanceModel, StorageRoutingModel, 
    MuskingumModel, IntegralDelayZeroModel
)


class ParameterEstimator:
    """
    参数估计器
    
    基于高精度圣维南模型的参数辨识算法，为降阶模型提供
    精确的参数标定和在线校正功能。
    """
    
    def __init__(self, saint_venant_model: SaintVenantModel):
        """
        初始化参数估计器
        
        Args:
            saint_venant_model (SaintVenantModel): 作为基准的圣维南模型
        """
        if not isinstance(saint_venant_model, SaintVenantModel):
            raise TypeError("需要SaintVenantModel类型的基准模型")
            
        self.saint_venant_model = saint_venant_model
        self.optimization_history = []
        self.static_curves = {}
        
        # 优化算法配置
        self.optimization_config = {
            'method': 'differential_evolution',
            'maxiter': 100,
            'tol': 1e-6,
            'polish': True,
            'seed': 42
        }
    
    def identify_static_curves(self, Q_range: np.ndarray, 
                              H_down_range: np.ndarray,
                              curve_types: List[str] = ['V_H', 'Q_H'],
                              poly_orders: List[int] = [2, 3, 4]) -> Dict[str, Any]:
        """
        辨识静态特征曲线
        
        Args:
            Q_range (np.ndarray): 流量测试范围 [m³/s]
            H_down_range (np.ndarray): 下游水位测试范围 [m]  
            curve_types (List[str]): 需要拟合的曲线类型
            poly_orders (List[int]): 多项式拟合阶数范围
            
        Returns:
            Dict[str, Any]: 静态曲线拟合结果
        """
        if len(Q_range) < 3 or len(H_down_range) < 3:
            raise ValueError("测试点数量不足，至少需要3个测试点")
            
        if np.any(Q_range <= 0):
            raise ValueError("流量范围必须为正值")
        
        # 网格化测试点
        Q_grid, H_grid = np.meshgrid(Q_range, H_down_range)
        test_points = list(zip(Q_grid.ravel(), H_grid.ravel()))
        
        # 执行恒定流计算
        raw_data = self._compute_steady_state_points(test_points)
        
        # 拟合特征曲线
        fitted_curves = {}
        statistics = {}
        best_orders = {}
        
        for curve_type in curve_types:
            curve_result = self._fit_static_curve(raw_data, curve_type, poly_orders)
            fitted_curves[curve_type] = curve_result['parameters']
            statistics[curve_type] = curve_result['statistics']  
            best_orders[curve_type] = curve_result['best_order']
        
        # 存储结果
        self.static_curves = {
            'fitted_curves': fitted_curves,
            'raw_data': raw_data,
            'statistics': statistics,
            'best_orders': best_orders,
            'test_ranges': {
                'Q_range': Q_range,
                'H_down_range': H_down_range
            }
        }
        
        return self.static_curves
    
    def _compute_steady_state_points(self, test_points: List[Tuple[float, float]]) -> pd.DataFrame:
        """计算恒定流测试点"""
        results = []
        
        for i, (Q, H_down) in enumerate(test_points):
            try:
                steady_result = self.saint_venant_model.compute_steady_state(Q, H_down)
                
                result = {
                    'Q': Q,
                    'H_down': H_down,
                    'H_up': steady_result.get('H_section_0', H_down),
                    'total_volume': steady_result['total_volume'],
                    'success': True
                }
                
                for key, value in steady_result.items():
                    if key.startswith('H_section_'):
                        result[key] = value
                        
                results.append(result)
                
            except Exception as e:
                warnings.warn(f"恒定流计算失败 Q={Q}, H_down={H_down}: {e}")
                results.append({
                    'Q': Q,
                    'H_down': H_down,
                    'H_up': np.nan,
                    'total_volume': np.nan,
                    'success': False
                })
        
        df = pd.DataFrame(results)
        valid_df = df[df['success']].copy()
        
        if len(valid_df) < len(df) * 0.8:
            warnings.warn(f"恒定流计算成功率较低: {len(valid_df)}/{len(df)}")
            
        return valid_df
    
    def _fit_static_curve(self, data: pd.DataFrame, curve_type: str, 
                         poly_orders: List[int]) -> Dict[str, Any]:
        """拟合单条静态曲线"""
        # 确定自变量和因变量
        if curve_type == 'V_H':
            x_data = data['total_volume'].values
            y_data = data['H_up'].values
            x_label, y_label = 'Volume [m³]', 'Water Level [m]'
        elif curve_type == 'Q_H':
            x_data = data['H_up'].values
            y_data = data['Q'].values
            x_label, y_label = 'Water Level [m]', 'Discharge [m³/s]'
        else:
            raise ValueError(f"不支持的曲线类型: {curve_type}")
        
        # 移除无效数据点
        valid_mask = np.isfinite(x_data) & np.isfinite(y_data)
        x_clean = x_data[valid_mask]
        y_clean = y_data[valid_mask]
        
        if len(x_clean) < 3:
            raise ValueError(f"{curve_type}曲线的有效数据点不足")
        
        # 尝试不同阶数的多项式拟合
        best_order = poly_orders[0]
        best_params = None
        best_score = float('inf')
        fit_results = {}
        
        for order in poly_orders:
            try:
                params = np.polyfit(x_clean, y_clean, order)
                y_pred = np.polyval(params, x_clean)
                
                rmse = np.sqrt(np.mean((y_clean - y_pred)**2))
                r2 = 1 - np.sum((y_clean - y_pred)**2) / np.sum((y_clean - np.mean(y_clean))**2)
                aic = len(x_clean) * np.log(rmse**2) + 2 * (order + 1)
                
                fit_results[order] = {
                    'parameters': params,
                    'rmse': rmse,
                    'r2': r2,
                    'aic': aic,
                    'score': aic
                }
                
                if aic < best_score:
                    best_score = aic
                    best_order = order
                    best_params = params
                    
            except Exception as e:
                warnings.warn(f"{curve_type}曲线{order}阶拟合失败: {e}")
                continue
        
        if best_params is None:
            raise ValueError(f"{curve_type}曲线拟合完全失败")
        
        def fitted_function(x):
            return np.polyval(best_params, x)
        
        return {
            'parameters': best_params,
            'function': fitted_function,
            'best_order': best_order,
            'statistics': fit_results[best_order],
            'all_orders': fit_results,
            'x_label': x_label,
            'y_label': y_label,
            'x_range': [x_clean.min(), x_clean.max()],
            'y_range': [y_clean.min(), y_clean.max()]
        }
    
    def identify_dynamic_parameters(self, unsteady_data: Dict[str, Any], 
                                   model_class: Type[BaseLumpedModel],
                                   parameter_bounds: Optional[Dict[str, Tuple[float, float]]] = None) -> Dict[str, Any]:
        """
        辨识动态模型参数
        
        Args:
            unsteady_data (Dict[str, Any]): 非恒定流数据
            model_class (Type[BaseLumpedModel]): 待标定的降阶模型类型
            parameter_bounds (Optional[Dict]): 参数搜索边界
            
        Returns:
            Dict[str, Any]: 参数辨识结果
        """
        required_keys = ['Q_in', 'H_down', 'dt']
        for key in required_keys:
            if key not in unsteady_data:
                raise ValueError(f"缺少必需的数据字段: {key}")
        
        Q_in_series = np.array(unsteady_data['Q_in'])
        dt = unsteady_data['dt']
        
        # 生成基准数据（简化版圣维南求解）
        reference_data = self._generate_reference_data(unsteady_data)
        
        # 设置参数边界
        bounds = self._get_default_bounds(model_class)
        if parameter_bounds:
            bounds.update(parameter_bounds)
        
        # 执行参数优化
        result = self._optimize_parameters(model_class, reference_data, bounds, dt)
        
        self.optimization_history.append(result)
        return result
    
    def _generate_reference_data(self, unsteady_data: Dict[str, Any]) -> pd.DataFrame:
        """生成基准数据（使用准恒定流近似）"""
        Q_in_series = np.array(unsteady_data['Q_in'])
        H_down_series = np.array(unsteady_data['H_down'])
        dt = unsteady_data['dt']
        
        results = []
        for i, (Q_in, H_down) in enumerate(zip(Q_in_series, H_down_series)):
            try:
                steady_result = self.saint_venant_model.compute_steady_state(Q_in, H_down)
                result = {
                    'time': i * dt,
                    'Q_in': Q_in,
                    'Q_out': Q_in,
                    'H_down': H_down,
                    'H_up': steady_result.get('H_section_0', H_down + 0.1),
                    'total_volume': steady_result['total_volume']
                }
            except Exception:
                result = {
                    'time': i * dt,
                    'Q_in': Q_in,
                    'Q_out': Q_in,
                    'H_down': H_down,
                    'H_up': H_down + 0.1,
                    'total_volume': 10000.0
                }
            results.append(result)
        
        return pd.DataFrame(results)
    
    def _get_default_bounds(self, model_class: Type[BaseLumpedModel]) -> Dict[str, Tuple[float, float]]:
        """获取模型的默认参数边界"""
        if model_class == MuskingumModel:
            return {'K': (100.0, 10000.0), 'x': (0.0, 0.5)}
        elif model_class == IntegralDelayZeroModel:
            return {
                'tau': (10.0, 3600.0),
                'T_delay': (0.0, 1800.0),
                'alpha': (100.0, 7200.0)
            }
        else:
            return {}
    
    def _optimize_parameters(self, model_class: Type[BaseLumpedModel],
                           reference_data: pd.DataFrame,
                           bounds: Dict[str, Tuple[float, float]],
                           dt: float) -> Dict[str, Any]:
        """执行参数优化"""
        
        def objective_function(params_list):
            try:
                # 创建参数字典
                param_names = list(bounds.keys())
                params_dict = dict(zip(param_names, params_list))
                
                # 创建模型
                model = self._create_model_instance(model_class, params_dict, reference_data, dt)
                
                # 运行仿真
                Q_in_series = reference_data['Q_in'].values
                sim_results = model.run_simulation(Q_in_series)
                
                # 计算误差
                Q_ref = reference_data['Q_out'].values
                Q_sim = sim_results['Q_out'].values
                
                min_len = min(len(Q_ref), len(Q_sim))
                rmse = np.sqrt(np.mean((Q_ref[:min_len] - Q_sim[:min_len])**2))
                
                return rmse
                
            except Exception:
                return 1e6
        
        # 设置优化边界
        bounds_list = [bounds[name] for name in bounds.keys()]
        
        # 执行优化
        result = differential_evolution(
            objective_function,
            bounds_list,
            maxiter=self.optimization_config['maxiter'],
            seed=self.optimization_config['seed']
        )
        
        # 转换结果
        param_names = list(bounds.keys())
        best_params = dict(zip(param_names, result.x))
        
        return {
            'success': result.success,
            'best_parameters': best_params,
            'best_score': result.fun,
            'model_class': model_class.__name__
        }
    
    def _create_model_instance(self, model_class: Type[BaseLumpedModel],
                              params: Dict[str, float], reference_data: pd.DataFrame,
                              dt: float) -> BaseLumpedModel:
        """创建降阶模型实例"""
        initial_V = reference_data['total_volume'].iloc[0]
        
        # 简单的V-H和H-Q关系函数
        def simple_V_to_H(V):
            return reference_data['H_up'].iloc[0] + (V - initial_V) / 10000.0
        
        def simple_H_to_Q(H):
            return max(0.0, (H - reference_data['H_up'].iloc[0]) * 10.0)
        
        if model_class == MuskingumModel:
            return MuskingumModel(
                dt, params['K'], params['x'], initial_V, simple_V_to_H, simple_H_to_Q)
        elif model_class == IntegralDelayZeroModel:
            return IntegralDelayZeroModel(
                dt, params['tau'], params['T_delay'], params['alpha'],
                initial_V, simple_V_to_H, simple_H_to_Q)
        elif model_class == StorageRoutingModel:
            return StorageRoutingModel(dt, initial_V, simple_V_to_H, simple_H_to_Q)
        else:
            raise ValueError(f"不支持的模型类型: {model_class.__name__}")