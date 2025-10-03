"""
增强数字孪生协调器模块

为深度测试提供高级数字孪生协调功能。

Author: WaterNet Development Team
Date: 2024-10-03
"""

import numpy as np
import pandas as pd
from scipy.stats import pearsonr
from sklearn.metrics import mean_squared_error
import warnings
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
import logging
import time

from ...coordination.twinning_harness import SynchronizedTwinningHarness
from ...models.saint_venant import SaintVenantModel
from ...models.lumped_models import BaseLumpedModel
from .enhanced_models import EnhancedMuskingumModel, IntegralDelayZeroModel


@dataclass
class TwinningConfig:
    """孪生配置参数"""
    correction_interval: int = 10
    correction_threshold: float = 0.1
    monitoring_window: int = 20
    adaptive_correction: bool = True


@dataclass
class PerformanceTarget:
    """性能目标"""
    rmse_Q_target: float = 5.0
    correlation_Q_target: float = 0.85
    nse_target: float = 0.75


class EnhancedTwinningCoordinator:
    """增强数字孪生协调器"""
    
    def __init__(self, host_model: Union[SaintVenantModel, BaseLumpedModel],
                 twin_model: BaseLumpedModel,
                 config: Optional[TwinningConfig] = None):
        """
        初始化协调器
        
        Parameters:
        -----------
        host_model : 本体模型
        twin_model : 孪生模型  
        config : 配置参数
        """
        self.host_model = host_model
        self.twin_model = twin_model
        self.config = config or TwinningConfig()
        
        self.logger = logging.getLogger(f"TwinCoordinator_{host_model.name}_{twin_model.name}")
        
        # 确定孪生类型
        self.twin_type = self._determine_twin_type()
        
        # 状态变量
        self.simulation_state = {
            'current_time': 0.0,
            'step_count': 0,
            'correction_count': 0
        }
        
        # 历史记录
        self.simulation_history = []
        self.correction_history = []
        
        self.logger.info(f"增强孪生协调器初始化完成 - 类型: {self.twin_type}")
    
    def _determine_twin_type(self) -> str:
        """确定孪生类型"""
        host_type = "SV" if isinstance(self.host_model, SaintVenantModel) else "ROM"
        
        if isinstance(self.twin_model, EnhancedMuskingumModel):
            twin_type = "Musk"
        elif isinstance(self.twin_model, IntegralDelayZeroModel):
            twin_type = "IDZ"
        else:
            twin_type = "ROM"
        
        return f"{host_type}-{twin_type}"
    
    def run_synchronized_simulation(self, input_scenario: Dict[str, Any],
                                   enable_correction: bool = True) -> Dict[str, Any]:
        """
        运行同步仿真
        
        Parameters:
        -----------
        input_scenario : Dict
            输入场景
        enable_correction : bool
            是否启用校正
            
        Returns:
        --------
        Dict: 仿真结果
        """
        self.logger.info("开始增强同步仿真")
        
        # 解析输入
        Q_in_series = np.array(input_scenario['Q_in_series'])
        H_down_series = np.array(input_scenario['H_down_series'])
        dt = input_scenario.get('dt', 10.0)
        
        # 重置状态
        self._reset_simulation_state()
        
        start_time = time.time()
        
        # 仿真循环
        simulation_results = []
        for i in range(len(Q_in_series)):
            step_result = self._execute_synchronized_step(
                Q_in_series[i], H_down_series[i], dt, i)
            simulation_results.append(step_result)
            
            # 检查校正
            if enable_correction and self._should_trigger_correction(i, step_result):
                self._execute_correction(simulation_results[-self.config.monitoring_window:])
        
        total_time = time.time() - start_time
        
        # 后处理
        return self._post_process_results(simulation_results, total_time)
    
    def _reset_simulation_state(self):
        """重置仿真状态"""
        self.simulation_state = {
            'current_time': 0.0,
            'step_count': 0,
            'correction_count': 0
        }
        
        self.simulation_history.clear()
        self.correction_history.clear()
        
        # 重置模型
        if hasattr(self.twin_model, 'reset_states'):
            self.twin_model.reset_states()
    
    def _execute_synchronized_step(self, Q_in: float, H_down: float, 
                                  dt: float, step_index: int) -> Dict[str, Any]:
        """执行同步时步"""
        # 本体模型计算
        host_result = self._compute_host_model(Q_in, H_down)
        
        # 孪生模型计算
        twin_result = self._compute_twin_model(Q_in)
        
        # 计算误差
        error_metrics = self._compute_error_metrics(host_result, twin_result)
        
        # 构建结果
        step_result = {
            'time': self.simulation_state['current_time'],
            'step': step_index,
            'Q_in': Q_in,
            'H_down': H_down,
            'host_Q_out': host_result['Q_out'],
            'host_H_out': host_result['H_out'],
            'twin_Q_out': twin_result['Q_out'],
            'twin_H_out': twin_result['H_out'],
            **error_metrics
        }
        
        # 更新状态
        self.simulation_state['current_time'] += dt
        self.simulation_state['step_count'] += 1
        
        return step_result
    
    def _compute_host_model(self, Q_in: float, H_down: float) -> Dict[str, Any]:
        """计算本体模型"""
        try:
            if isinstance(self.host_model, SaintVenantModel):
                steady_result = self.host_model.compute_steady_state(Q_in, H_down)
                return {
                    'Q_out': Q_in,
                    'H_out': steady_result.get('H_section_0', H_down + 0.1),
                    'V': steady_result['total_volume']
                }
            else:
                rom_result = self.host_model.step(Q_in)
                return {
                    'Q_out': rom_result['Q_out'],
                    'H_out': rom_result['H_out'],
                    'V': rom_result['V']
                }
        except Exception as e:
            self.logger.warning(f"本体模型计算失败: {e}")
            return {'Q_out': Q_in, 'H_out': H_down + 0.1, 'V': 10000.0}
    
    def _compute_twin_model(self, Q_in: float) -> Dict[str, Any]:
        """计算孪生模型"""
        try:
            result = self.twin_model.step(Q_in)
            return {
                'Q_out': result['Q_out'],
                'H_out': result['H_out'],
                'V': result['V']
            }
        except Exception as e:
            self.logger.warning(f"孪生模型计算失败: {e}")
            return {'Q_out': Q_in, 'H_out': 100.0, 'V': 10000.0}
    
    def _compute_error_metrics(self, host_result: Dict, twin_result: Dict) -> Dict[str, float]:
        """计算误差指标"""
        Q_host = host_result['Q_out']
        Q_twin = twin_result['Q_out']
        H_host = host_result['H_out']
        H_twin = twin_result['H_out']
        
        return {
            'error_Q': abs(Q_host - Q_twin),
            'error_H': abs(H_host - H_twin),
            'relative_error_Q': abs(Q_host - Q_twin) / max(abs(Q_host), 1e-6) * 100
        }
    
    def _should_trigger_correction(self, step_index: int, step_result: Dict) -> bool:
        """判断是否触发校正"""
        # 间隔检查
        steps_since_correction = step_index - self.simulation_state.get('last_correction_step', -self.config.correction_interval)
        interval_check = steps_since_correction >= self.config.correction_interval
        
        # 误差检查
        error_check = step_result['error_Q'] > self.config.correction_threshold
        
        # 数据充足检查
        data_check = step_index >= self.config.monitoring_window
        
        return interval_check and error_check and data_check
    
    def _execute_correction(self, recent_results: List[Dict]) -> bool:
        """执行校正"""
        try:
            self.logger.info(f"执行校正 - 步骤 {self.simulation_state['step_count']}")
            
            # 简化的参数调整
            avg_error = np.mean([r['error_Q'] for r in recent_results[-5:]])
            
            if isinstance(self.twin_model, EnhancedMuskingumModel):
                # 调整马斯京干参数
                current_K = self.twin_model.K
                current_x = self.twin_model.x
                
                new_K = current_K * (1.0 + 0.1 * np.random.uniform(-1, 1))
                new_x = np.clip(current_x + 0.05 * np.random.uniform(-1, 1), 0.0, 0.5)
                
                self.twin_model.update_parameters(new_K, new_x)
                
            elif isinstance(self.twin_model, IntegralDelayZeroModel):
                # 调整IDZ参数
                current_tau = self.twin_model.tau
                new_tau = current_tau * (1.0 + 0.05 * np.random.uniform(-1, 1))
                new_T = max(0, self.twin_model.T + 10 * np.random.uniform(-1, 1))
                new_alpha = self.twin_model.alpha * (1.0 + 0.05 * np.random.uniform(-1, 1))
                
                self.twin_model.update_parameters(new_tau, new_T, new_alpha)
            
            # 记录校正
            self.correction_history.append({
                'step': self.simulation_state['step_count'],
                'avg_error_before': avg_error,
                'success': True
            })
            
            self.simulation_state['correction_count'] += 1
            self.simulation_state['last_correction_step'] = self.simulation_state['step_count']
            
            return True
            
        except Exception as e:
            self.logger.error(f"校正失败: {e}")
            return False
    
    def _post_process_results(self, simulation_results: List[Dict], 
                            total_time: float) -> Dict[str, Any]:
        """后处理结果"""
        results_df = pd.DataFrame(simulation_results)
        
        # 计算性能指标
        Q_host = results_df['host_Q_out'].values
        Q_twin = results_df['twin_Q_out'].values
        
        metrics = {}
        if len(Q_host) > 1:
            metrics['rmse_Q'] = np.sqrt(mean_squared_error(Q_host, Q_twin))
            metrics['correlation_Q'] = pearsonr(Q_host, Q_twin)[0] if np.std(Q_host) > 0 and np.std(Q_twin) > 0 else 0.0
            metrics['nse_Q'] = 1 - np.sum((Q_host - Q_twin)**2) / np.sum((Q_host - np.mean(Q_host))**2) if np.var(Q_host) > 0 else 0.0
        
        return {
            'twin_type': self.twin_type,
            'simulation_data': results_df,
            'performance_metrics': metrics,
            'correction_history': self.correction_history,
            'simulation_summary': {
                'total_steps': len(simulation_results),
                'total_time': total_time,
                'correction_count': self.simulation_state['correction_count']
            }
        }


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, window_size: int = 20):
        self.window_size = window_size
        self.error_history = []
        self.performance_history = []
    
    def update(self, step_result: Dict):
        """更新监控数据"""
        self.error_history.append(step_result['error_Q'])
        if len(self.error_history) > self.window_size:
            self.error_history.pop(0)
    
    def get_recent_average_error(self) -> float:
        """获取最近平均误差"""
        return np.mean(self.error_history) if self.error_history else 0.0
    
    def reset(self):
        """重置监控器"""
        self.error_history.clear()
        self.performance_history.clear()


class AdaptiveCorrectionStrategy:
    """自适应校正策略"""
    
    def __init__(self, config: TwinningConfig, target: PerformanceTarget, model: BaseLumpedModel):
        self.config = config
        self.target = target
        self.model = model
        self.correction_attempts = 0
    
    def should_trigger_correction(self, step_index: int, step_result: Dict,
                                simulation_state: Dict, monitor: PerformanceMonitor) -> bool:
        """判断是否应触发校正"""
        if not self.config.adaptive_correction:
            return False
        
        # 基本条件检查
        error_threshold_exceeded = step_result['error_Q'] > self.config.correction_threshold
        sufficient_data = step_index >= self.config.monitoring_window
        
        # 自适应条件
        recent_avg_error = monitor.get_recent_average_error()
        error_trend_increasing = recent_avg_error > self.config.correction_threshold * 1.2
        
        return error_threshold_exceeded and sufficient_data and error_trend_increasing
    
    def reset(self):
        """重置策略"""
        self.correction_attempts = 0