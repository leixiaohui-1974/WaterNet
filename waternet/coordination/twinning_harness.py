"""
SynchronizedTwinningHarness 同步孪生协调器

实现精细化模型与降阶模型的同步运行和协调管理。
提供在线校正、性能监控和数据记录功能。

核心功能:
1. 双模型同步仿真
2. 在线参数校正
3. 性能对比分析
4. 自适应调整策略

Author: WaterNet Development Team
Date: 2024-10-03
"""

import numpy as np
import pandas as pd
import warnings
from typing import Dict, List, Optional, Union, Any
from scipy.stats import pearsonr

from ..models.saint_venant import SaintVenantModel
from ..models.lumped_models import BaseLumpedModel
from ..parameter_estimation.estimator import ParameterEstimator


class SynchronizedTwinningHarness:
    """
    同步孪生协调器
    
    管理精细化模型与降阶模型的同步运行，实现数字孪生系统的
    核心协调功能。
    
    主要特性:
    - 实时同步仿真
    - 在线参数校正  
    - 性能监控与分析
    - 自适应优化策略
    - 结果对比与可视化
    
    Attributes:
        saint_venant_model (SaintVenantModel): 精细化物理模型
        reduced_order_model (BaseLumpedModel): 降阶模型
        parameter_estimator (ParameterEstimator): 参数估计器
        sync_results (List): 同步仿真结果历史
        correction_history (List): 校正历史记录
    """
    
    def __init__(self, saint_venant_model: SaintVenantModel,
                 reduced_order_model: BaseLumpedModel,
                 correction_interval: int = 10,
                 correction_threshold: float = 0.1):
        """
        初始化同步孪生协调器
        
        Args:
            saint_venant_model (SaintVenantModel): 精细化模型
            reduced_order_model (BaseLumpedModel): 降阶模型
            correction_interval (int): 校正间隔（时间步数）
            correction_threshold (float): 触发校正的误差阈值
            
        Raises:
            TypeError: 当模型类型不正确时
        """
        if not isinstance(saint_venant_model, SaintVenantModel):
            raise TypeError("需要SaintVenantModel类型的精细化模型")
        if not isinstance(reduced_order_model, BaseLumpedModel):
            raise TypeError("需要BaseLumpedModel类型的降阶模型")
            
        self.saint_venant_model = saint_venant_model
        self.reduced_order_model = reduced_order_model
        
        # 创建参数估计器
        self.parameter_estimator = ParameterEstimator(saint_venant_model)
        
        # 校正配置
        self.correction_interval = correction_interval
        self.correction_threshold = correction_threshold
        
        # 状态记录
        self.sync_results = []
        self.correction_history = []
        self.performance_metrics = {}
        
        # 校正计数器
        self._step_counter = 0
        self._last_correction_step = 0
        
        # 性能监控窗口
        self.monitoring_window = 20  # 监控最近20步的性能
        self._recent_errors = []
        
        print(f"同步孪生协调器初始化完成")
        print(f"精细化模型: {saint_venant_model.name}")
        print(f"降阶模型: {reduced_order_model.name}")
        print(f"校正间隔: {correction_interval} 步")
    
    def run_synchronized_simulation(self, Q_in_series: Union[List[float], np.ndarray],
                                   H_down_series: Union[List[float], np.ndarray],
                                   dt: float,
                                   enable_correction: bool = True) -> pd.DataFrame:
        """
        运行同步孪生仿真
        
        Args:
            Q_in_series (Union[List, np.ndarray]): 入流时间序列
            H_down_series (Union[List, np.ndarray]): 下游水位序列
            dt (float): 时间步长（秒）
            enable_correction (bool): 是否启用在线校正
            
        Returns:
            pd.DataFrame: 同步仿真结果数据框
            
        Raises:
            ValueError: 当输入序列长度不匹配时
        """
        Q_in_array = np.array(Q_in_series)
        H_down_array = np.array(H_down_series)
        
        if len(Q_in_array) != len(H_down_array):
            raise ValueError("入流和下游水位序列长度必须相等")
        
        if len(Q_in_array) == 0:
            raise ValueError("输入序列不能为空")
        
        print(f"开始同步孪生仿真...")
        print(f"仿真步数: {len(Q_in_array)}")
        print(f"时间步长: {dt} 秒")
        print(f"在线校正: {'启用' if enable_correction else '禁用'}")
        
        # 重置状态
        self._reset_simulation_state()
        
        # 仿真循环
        results = []
        for i, (Q_in, H_down) in enumerate(zip(Q_in_array, H_down_array)):
            
            # 执行一步同步仿真
            step_result = self._synchronized_step(Q_in, H_down, dt, i)
            results.append(step_result)
            
            # 检查是否需要校正
            if enable_correction and self._should_perform_correction(i):
                self._perform_online_correction(results[-self.monitoring_window:], dt)
            
            self._step_counter += 1
        
        # 转换为DataFrame
        results_df = pd.DataFrame(results)
        
        # 计算总体性能指标
        self._compute_overall_metrics(results_df)
        
        # 保存结果
        self.sync_results.append(results_df)
        
        print(f"同步孪生仿真完成!")
        print(f"流量RMSE: {self.performance_metrics.get('rmse_Q', 0):.4f} m³/s")
        print(f"相关系数: {self.performance_metrics.get('correlation_Q', 0):.3f}")
        
        return results_df
    
    def _reset_simulation_state(self):
        """重置仿真状态"""
        self._step_counter = 0
        self._last_correction_step = 0
        self._recent_errors = []
        
        # 重置降阶模型状态
        self.reduced_order_model.reset()
    
    def _synchronized_step(self, Q_in: float, H_down: float, dt: float, 
                          step_index: int) -> Dict[str, float]:
        """
        执行一步同步仿真
        
        Args:
            Q_in (float): 入流量
            H_down (float): 下游水位
            dt (float): 时间步长
            step_index (int): 时间步索引
            
        Returns:
            Dict[str, float]: 单步仿真结果
        """
        # 1. 圣维南模型计算（简化为准恒定流）
        try:
            sv_result = self.saint_venant_model.compute_steady_state(Q_in, H_down)
            Q_out_sv = Q_in  # 简化假设
            H_up_sv = sv_result.get('H_section_0', H_down + 0.1)
            V_sv = sv_result['total_volume']
        except Exception as e:
            warnings.warn(f"圣维南模型计算失败，步骤{step_index}: {e}")
            Q_out_sv = Q_in
            H_up_sv = H_down + 0.1
            V_sv = 10000.0
        
        # 2. 降阶模型计算
        try:
            rom_result = self.reduced_order_model.step(Q_in)
            Q_out_rom = rom_result['Q_out']
            H_up_rom = rom_result['H_out']
            V_rom = rom_result['V']
        except Exception as e:
            warnings.warn(f"降阶模型计算失败，步骤{step_index}: {e}")
            Q_out_rom = Q_in
            H_up_rom = H_down + 0.1
            V_rom = 10000.0
        
        # 3. 计算误差指标
        error_Q = abs(Q_out_sv - Q_out_rom)
        error_H = abs(H_up_sv - H_up_rom)
        relative_error_Q = error_Q / max(Q_out_sv, 1e-6) * 100
        
        # 4. 更新监控窗口
        self._recent_errors.append(error_Q)
        if len(self._recent_errors) > self.monitoring_window:
            self._recent_errors.pop(0)
        
        # 5. 构建结果字典
        result = {
            'time': step_index * dt,
            'step': step_index,
            'Q_in': Q_in,
            'H_down': H_down,
            
            # 圣维南模型结果
            'Q_out_sv': Q_out_sv,
            'H_up_sv': H_up_sv,
            'V_sv': V_sv,
            
            # 降阶模型结果
            'Q_out_rom': Q_out_rom,
            'H_up_rom': H_up_rom,
            'V_rom': V_rom,
            
            # 误差指标
            'error_Q': error_Q,
            'error_H': error_H,
            'relative_error_Q': relative_error_Q
        }
        
        return result
    
    def _should_perform_correction(self, step_index: int) -> bool:
        """
        判断是否应该执行在线校正
        
        Args:
            step_index (int): 当前时间步索引
            
        Returns:
            bool: True表示应该执行校正
        """
        # 条件1: 达到校正间隔
        interval_check = (step_index - self._last_correction_step) >= self.correction_interval
        
        # 条件2: 误差超过阈值
        if len(self._recent_errors) >= 3:
            recent_avg_error = np.mean(self._recent_errors[-3:])
            threshold_check = recent_avg_error > self.correction_threshold
        else:
            threshold_check = False
        
        # 条件3: 有足够的数据进行校正
        data_check = step_index >= self.monitoring_window
        
        return interval_check and threshold_check and data_check
    
    def _perform_online_correction(self, recent_results: List[Dict], dt: float):
        """
        执行在线参数校正
        
        Args:
            recent_results (List[Dict]): 最近的仿真结果
            dt (float): 时间步长
        """
        try:
            print(f"执行在线校正，步骤 {self._step_counter}...")
            
            # 准备校正数据
            correction_data = self._prepare_correction_data(recent_results, dt)
            
            # 获取当前模型类型
            model_class = type(self.reduced_order_model)
            
            # 执行参数辨识
            correction_result = self.parameter_estimator.identify_dynamic_parameters(
                correction_data, model_class)
            
            if correction_result['success']:
                # 更新模型参数
                self._update_model_parameters(correction_result['best_parameters'])
                
                # 记录校正历史
                correction_record = {
                    'step': self._step_counter,
                    'time': self._step_counter * dt,
                    'old_params': self._get_current_parameters(),
                    'new_params': correction_result['best_parameters'],
                    'improvement': correction_result['best_score'],
                    'success': True
                }
                
                self._last_correction_step = self._step_counter
                print(f"校正成功，新参数: {correction_result['best_parameters']}")
                
            else:
                correction_record = {
                    'step': self._step_counter,
                    'time': self._step_counter * dt,
                    'success': False,
                    'reason': '参数优化失败'
                }
                print("校正失败")
            
            self.correction_history.append(correction_record)
            
        except Exception as e:
            warnings.warn(f"在线校正执行失败: {e}")
            correction_record = {
                'step': self._step_counter,
                'time': self._step_counter * dt,
                'success': False,
                'reason': str(e)
            }
            self.correction_history.append(correction_record)
    
    def _prepare_correction_data(self, recent_results: List[Dict], dt: float) -> Dict[str, Any]:
        """准备校正数据"""
        Q_in = [r['Q_in'] for r in recent_results]
        H_down = [r['H_down'] for r in recent_results]
        
        return {
            'Q_in': Q_in,
            'H_down': H_down,
            'dt': dt
        }
    
    def _update_model_parameters(self, new_params: Dict[str, float]):
        """更新降阶模型参数"""
        # 这里需要根据具体的模型类型来更新参数
        # 由于参数更新涉及模型内部状态，这里提供一个通用框架
        
        model_type = type(self.reduced_order_model).__name__
        
        if model_type == 'MuskingumModel':
            if 'K' in new_params:
                self.reduced_order_model.K = new_params['K']
            if 'x' in new_params:
                self.reduced_order_model.x = new_params['x']
            # 重新计算系数
            self.reduced_order_model._compute_muskingum_coefficients()
            
        elif model_type == 'IntegralDelayZeroModel':
            if 'tau' in new_params:
                self.reduced_order_model.tau = new_params['tau']
            if 'T_delay' in new_params:
                self.reduced_order_model.T_delay = new_params['T_delay']
            if 'alpha' in new_params:
                self.reduced_order_model.alpha = new_params['alpha']
            # 重新计算离散化系数
            self.reduced_order_model._compute_discrete_coefficients()
    
    def _get_current_parameters(self) -> Dict[str, float]:
        """获取当前模型参数"""
        model_type = type(self.reduced_order_model).__name__
        
        if model_type == 'MuskingumModel':
            return {
                'K': self.reduced_order_model.K,
                'x': self.reduced_order_model.x
            }
        elif model_type == 'IntegralDelayZeroModel':
            return {
                'tau': self.reduced_order_model.tau,
                'T_delay': self.reduced_order_model.T_delay,
                'alpha': self.reduced_order_model.alpha
            }
        else:
            return {}
    
    def _compute_overall_metrics(self, results_df: pd.DataFrame):
        """计算总体性能指标"""
        Q_sv = results_df['Q_out_sv'].values
        Q_rom = results_df['Q_out_rom'].values
        
        # RMSE
        rmse_Q = np.sqrt(np.mean((Q_sv - Q_rom)**2))
        
        # 相关系数
        if len(Q_sv) > 1 and np.std(Q_sv) > 0 and np.std(Q_rom) > 0:
            correlation_Q, _ = pearsonr(Q_sv, Q_rom)
        else:
            correlation_Q = 0.0
        
        # 平均相对误差
        relative_errors = np.abs(Q_sv - Q_rom) / np.maximum(Q_sv, 1e-6) * 100
        mean_relative_error = np.mean(relative_errors)
        
        # 最大误差
        max_error = np.max(np.abs(Q_sv - Q_rom))
        
        self.performance_metrics = {
            'rmse_Q': rmse_Q,
            'correlation_Q': correlation_Q,
            'mean_relative_error': mean_relative_error,
            'max_error': max_error,
            'total_steps': len(results_df),
            'correction_count': len(self.correction_history)
        }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        if not self.performance_metrics:
            return {'message': '尚未运行仿真'}
        
        return {
            '总体性能': self.performance_metrics,
            '校正历史': {
                '校正次数': len(self.correction_history),
                '成功次数': sum(1 for c in self.correction_history if c.get('success', False)),
                '最近校正': self.correction_history[-1] if self.correction_history else None
            },
            '模型信息': {
                '精细化模型': self.saint_venant_model.name,
                '降阶模型': self.reduced_order_model.name,
                '当前参数': self._get_current_parameters()
            }
        }
    
    def reset(self):
        """重置协调器状态"""
        self._step_counter = 0
        self._last_correction_step = 0
        self._recent_errors = []
        self.sync_results = []
        self.correction_history = []
        self.performance_metrics = {}
        
        # 重置降阶模型
        self.reduced_order_model.reset()