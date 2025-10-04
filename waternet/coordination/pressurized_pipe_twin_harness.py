"""
PressurizedPipeTwinHarness 有压管道同步孪生协调器

基于SynchronizedTwinningHarness框架的有压管道数字孪生系统。
实现精细化模型与降阶模型的协调、在线校正和状态估计。

Author: WaterNet Development Team
Date: 2024-10-04
"""

import numpy as np
import pandas as pd
import warnings
from typing import Dict, List, Optional, Union, Any
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from physical_objects.pressurized_pipe_model import PressurizedPipeModel
from waternet.models.pressurized_pipe_rom import PressurizedPipeROM
from waternet.parameter_estimation.pipe_parameter_estimator import PipeParameterEstimator
from waternet.coordination.twinning_harness import SynchronizedTwinningHarness


class PressurizedPipeTwinHarness:
    """
    有压管道同步孪生协调器
    
    专门为有压管道系统设计的数字孪生协调器，实现物理模型与降阶模型的同步运行。
    """
    
    def __init__(self, physical_model: PressurizedPipeModel,
                 digital_twin: PressurizedPipeROM,
                 correction_interval: int = 10,
                 correction_threshold: float = 0.1):
        """
        初始化有压管道孪生协调器
        
        Args:
            physical_model: 有压管道精细化模型
            digital_twin: 有压管道降阶模型
            correction_interval: 校正间隔
            correction_threshold: 校正阈值
        """
        self.physical_model = physical_model
        self.digital_twin = digital_twin
        self.parameter_estimator = PipeParameterEstimator(physical_model)
        
        self.correction_interval = correction_interval
        self.correction_threshold = correction_threshold
        
        self.sync_results = []
        self.correction_history = []
        self.performance_metrics = {}
        
        self._step_counter = 0
        self._last_correction_step = 0
        self._recent_errors = []
        self.monitoring_window = 20
        
        print(f"有压管道孪生协调器初始化完成")
        print(f"物理模型: {physical_model.name}")
        print(f"数字孪生: {digital_twin.name}")
    
    def run_synchronized_simulation(self, Q_in_series: Union[List[float], np.ndarray],
                                   dt: float, total_time: float,
                                   enable_correction: bool = True) -> pd.DataFrame:
        """运行同步孪生仿真"""
        print(f"开始同步孪生仿真...")
        
        results = []
        n_steps = len(Q_in_series)
        
        # 初始化状态
        self._reset_simulation_state()
        
        for i, Q_in in enumerate(Q_in_series):
            # 执行同步步骤
            step_result = self._synchronized_step(Q_in, dt, i)
            results.append(step_result)
            
            # 检查在线校正
            if enable_correction and self._should_perform_correction(i):
                self._perform_online_correction(results[-self.monitoring_window:], dt)
            
            self._step_counter += 1
            
            if (i + 1) % max(1, n_steps // 10) == 0:
                progress = (i + 1) / n_steps * 100
                print(f"同步仿真进度: {progress:.1f}%")
        
        results_df = pd.DataFrame(results)
        self._compute_overall_metrics(results_df)
        
        print(f"同步孪生仿真完成!")
        print(f"流量RMSE: {self.performance_metrics.get('rmse_Q', 0):.4f} m³/s")
        
        return results_df
    
    def _synchronized_step(self, Q_in: float, dt: float, step_index: int) -> Dict[str, float]:
        """执行一步同步仿真"""
        # 简化的物理模型计算（准恒定流）
        try:
            steady_result = self.physical_model.compute_steady_state(Q_in, 95.0)
            Q_out_physical = Q_in
            H_up_physical = steady_result.get('upstream_H', 100.0)
        except Exception as e:
            warnings.warn(f"物理模型计算失败: {e}")
            Q_out_physical = Q_in
            H_up_physical = 100.0
        
        # 降阶模型计算
        try:
            rom_result = self.digital_twin.step(Q_in)
            Q_out_rom = rom_result['Q_out']
            H_up_rom = rom_result['H_out']
        except Exception as e:
            warnings.warn(f"降阶模型计算失败: {e}")
            Q_out_rom = Q_in
            H_up_rom = 100.0
        
        # 计算误差
        error_Q = abs(Q_out_physical - Q_out_rom)
        error_H = abs(H_up_physical - H_up_rom)
        
        self._recent_errors.append(error_Q)
        if len(self._recent_errors) > self.monitoring_window:
            self._recent_errors.pop(0)
        
        return {
            'time': step_index * dt,
            'step': step_index,
            'Q_in': Q_in,
            'Q_out_physical': Q_out_physical,
            'Q_out_rom': Q_out_rom,
            'H_up_physical': H_up_physical,
            'H_up_rom': H_up_rom,
            'error_Q': error_Q,
            'error_H': error_H
        }
    
    def _should_perform_correction(self, step_index: int) -> bool:
        """判断是否应该执行校正"""
        interval_check = (step_index - self._last_correction_step) >= self.correction_interval
        
        if len(self._recent_errors) >= 3:
            recent_avg_error = np.mean(self._recent_errors[-3:])
            threshold_check = recent_avg_error > self.correction_threshold
        else:
            threshold_check = False
        
        data_check = step_index >= self.monitoring_window
        
        return interval_check and threshold_check and data_check
    
    def _perform_online_correction(self, recent_results: List[Dict], dt: float):
        """执行在线参数校正"""
        try:
            print(f"执行在线校正，步骤 {self._step_counter}...")
            
            # 简化的参数更新
            if hasattr(self.digital_twin, 'model_parameters'):
                current_params = self.digital_twin.model_parameters.copy()
                
                # 基于误差调整参数（简化实现）
                recent_errors = [r['error_Q'] for r in recent_results]
                avg_error = np.mean(recent_errors)
                
                if avg_error > self.correction_threshold:
                    # 简单的比例调整
                    if 'K' in current_params:
                        current_params['K'] *= (1.0 + 0.1 * np.sign(avg_error))
                    
                    self.digital_twin.update_parameters(current_params)
                    
                    correction_record = {
                        'step': self._step_counter,
                        'avg_error': avg_error,
                        'success': True
                    }
                    print(f"校正成功，平均误差: {avg_error:.4f}")
                else:
                    correction_record = {
                        'step': self._step_counter,
                        'success': False,
                        'reason': '误差在可接受范围内'
                    }
            
            self.correction_history.append(correction_record)
            self._last_correction_step = self._step_counter
            
        except Exception as e:
            warnings.warn(f"在线校正失败: {e}")
    
    def _reset_simulation_state(self):
        """重置仿真状态"""
        self._step_counter = 0
        self._last_correction_step = 0
        self._recent_errors = []
        self.digital_twin.reset()
    
    def _compute_overall_metrics(self, results_df: pd.DataFrame):
        """计算总体性能指标"""
        Q_physical = results_df['Q_out_physical'].values
        Q_rom = results_df['Q_out_rom'].values
        
        rmse_Q = np.sqrt(np.mean((Q_physical - Q_rom)**2))
        
        if len(Q_physical) > 1 and np.std(Q_physical) > 0:
            correlation_Q = np.corrcoef(Q_physical, Q_rom)[0, 1]
        else:
            correlation_Q = 0.0
        
        self.performance_metrics = {
            'rmse_Q': rmse_Q,
            'correlation_Q': correlation_Q,
            'correction_count': len(self.correction_history)
        }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        return {
            '总体性能': self.performance_metrics,
            '校正历史': {
                '校正次数': len(self.correction_history),
                '成功次数': sum(1 for c in self.correction_history if c.get('success', False))
            }
        }


def run_twinning_demo():
    """运行同步孪生演示"""
    print("="*60)
    print("有压管道同步孪生演示")
    print("="*60)
    
    try:
        # 创建模型
        from waternet.tests.run_pipe_simulation import create_demo_pipe_model
        from waternet.models.pressurized_pipe_rom import create_pressurized_pipe_rom
        
        physical_model = create_demo_pipe_model()
        
        physical_params = {
            'L': physical_model.total_length,
            'D': 1.0, 'a': 1200.0, 'f': 0.02
        }
        
        initial_conditions = {
            'H_initial': 100.0,
            'Q_initial': 1.5,
            'V_initial': 10000.0
        }
        
        digital_twin = create_pressurized_pipe_rom(
            'muskingum_hammer', physical_params, 0.02, initial_conditions)
        
        # 创建孪生协调器
        harness = PressurizedPipeTwinHarness(
            physical_model, digital_twin,
            correction_interval=20, correction_threshold=0.05)
        
        # 运行同步仿真
        Q_in_series = [1.5] * 50 + [0.0] * 50 + [1.5] * 100  # 阶跃响应
        
        results = harness.run_synchronized_simulation(
            Q_in_series, dt=0.02, total_time=4.0, enable_correction=True)
        
        # 输出性能摘要
        summary = harness.get_performance_summary()
        print("\n性能摘要:")
        for key, value in summary.items():
            print(f"{key}: {value}")
        
        print("\n✅ 同步孪生演示完成!")
        return harness, results
        
    except Exception as e:
        print(f"\n❌ 同步孪生演示失败: {e}")
        import traceback
        traceback.print_exc()
        return None, None


if __name__ == "__main__":
    harness, results = run_twinning_demo()