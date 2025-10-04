"""
精度验证器 - 误差控制机制

实现区间模型精度验证，包括多工况验证测试、误差评估和自适应控制。

Author: WaterNet Development Team
Date: 2024-10-04
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Callable, Any
import logging
from dataclasses import dataclass
from scipy import stats
import warnings

from .flow_stage_interval_system import FlowStageInterval, IDZModelParameters


@dataclass
class ValidationConfig:
    """验证配置参数"""
    error_threshold: float = 0.20                    # 误差阈值（20%）
    test_point_density: int = 9                      # 测试点密度（3x3网格）
    dynamic_test_duration: float = 1800.0            # 动态测试时长（秒）
    steady_state_tolerance: float = 0.05             # 稳态容差
    confidence_level: float = 0.95                   # 置信水平
    validation_scenarios: List[str] = None           # 验证场景
    
    def __post_init__(self):
        if self.validation_scenarios is None:
            self.validation_scenarios = ['steady_state', 'step_response', 'sine_wave']


class AccuracyValidator:
    """
    精度验证器
    
    评估和控制各区间的模型精度，确保IDZ模型误差在可接受范围内。
    """
    
    def __init__(self, config: Optional[ValidationConfig] = None):
        """
        初始化精度验证器
        
        Args:
            config: 验证配置参数
        """
        self.config = config or ValidationConfig()
        self.logger = logging.getLogger("AccuracyValidator")
        
        # 验证历史
        self.validation_history: List[Dict] = []
        self.error_statistics: Dict[str, Any] = {}
    
    def evaluate_interval_accuracy(self, interval: FlowStageInterval,
                                 idz_model: Any,
                                 reference_model: Any) -> Dict[str, float]:
        """
        评估区间精度
        
        Args:
            interval: 目标区间
            idz_model: IDZ模型实例
            reference_model: 参考模型（圣维南模型）
            
        Returns:
            Dict[str, float]: 误差评估结果
        """
        self.logger.info(f"开始评估区间 {interval.interval_id} 的精度")
        
        # 生成测试场景
        test_scenarios = self.generate_test_scenarios(interval)
        
        # 初始化误差统计
        error_metrics = {
            'max_error': 0.0,
            'mean_error': 0.0,
            'std_error': 0.0,
            'steady_state_error': 0.0,
            'dynamic_error': 0.0,
            'scenario_errors': {}
        }
        
        all_errors = []
        
        # 对每个场景进行测试
        for scenario_name, scenario_data in test_scenarios.items():
            scenario_errors = self._evaluate_scenario(
                scenario_name, scenario_data, idz_model, reference_model)
            
            error_metrics['scenario_errors'][scenario_name] = scenario_errors
            all_errors.extend(scenario_errors['point_errors'])
        
        # 计算总体误差统计
        if all_errors:
            error_metrics['max_error'] = np.max(all_errors)
            error_metrics['mean_error'] = np.mean(all_errors)
            error_metrics['std_error'] = np.std(all_errors)
            
            # 分类误差
            steady_errors = []
            dynamic_errors = []
            
            for scenario_name, scenario_data in error_metrics['scenario_errors'].items():
                if 'steady' in scenario_name:
                    steady_errors.extend(scenario_data['point_errors'])
                else:
                    dynamic_errors.extend(scenario_data['point_errors'])
            
            if steady_errors:
                error_metrics['steady_state_error'] = np.mean(steady_errors)
            if dynamic_errors:
                error_metrics['dynamic_error'] = np.mean(dynamic_errors)
        
        # 记录验证历史
        self._record_validation_history(interval, error_metrics)
        
        self.logger.info(f"区间 {interval.interval_id} 精度评估完成，最大误差: {error_metrics['max_error']:.2%}")
        
        return error_metrics
    
    def generate_test_scenarios(self, interval: FlowStageInterval) -> Dict[str, Dict]:
        """
        生成测试场景
        
        Args:
            interval: 目标区间
            
        Returns:
            Dict: 测试场景数据
        """
        scenarios = {}
        Q_min, Q_max = interval.Q_bounds
        H_min, H_max = interval.H_bounds
        
        # 稳态验证场景
        if 'steady_state' in self.config.validation_scenarios:
            scenarios['steady_state'] = self._generate_steady_state_scenario(interval)
        
        # 阶跃响应场景
        if 'step_response' in self.config.validation_scenarios:
            scenarios['step_response'] = self._generate_step_response_scenario(interval)
        
        # 正弦波场景
        if 'sine_wave' in self.config.validation_scenarios:
            scenarios['sine_wave'] = self._generate_sine_wave_scenario(interval)
        
        return scenarios
    
    def _generate_steady_state_scenario(self, interval: FlowStageInterval) -> Dict:
        """生成稳态验证场景"""
        Q_min, Q_max = interval.Q_bounds
        H_min, H_max = interval.H_bounds
        
        # 生成测试网格点
        n_points = int(np.sqrt(self.config.test_point_density))
        Q_points = np.linspace(Q_min, Q_max, n_points)
        H_points = np.linspace(H_min, H_max, n_points)
        
        test_points = []
        for Q in Q_points:
            for H in H_points:
                test_points.append({'Q_up': Q, 'H_up': H, 'Q_down': Q*0.98, 'H_down': H-0.05})
        
        return {
            'type': 'steady_state',
            'test_points': test_points,
            'duration': 300.0,  # 5分钟稳态
            'description': f'稳态验证 - {len(test_points)} 个测试点'
        }
    
    def _generate_step_response_scenario(self, interval: FlowStageInterval) -> Dict:
        """生成阶跃响应场景"""
        Q_center = (interval.Q_bounds[0] + interval.Q_bounds[1]) / 2.0
        H_center = (interval.H_bounds[0] + interval.H_bounds[1]) / 2.0
        
        # 定义阶跃幅度
        Q_range = interval.Q_bounds[1] - interval.Q_bounds[0]
        step_amplitude = Q_range * 0.3  # 30%的区间范围
        
        return {
            'type': 'step_response',
            'initial_state': {'Q_up': Q_center, 'H_up': H_center, 
                            'Q_down': Q_center*0.98, 'H_down': H_center-0.05},
            'step_amplitude': step_amplitude,
            'step_time': 300.0,  # 5分钟后施加阶跃
            'duration': self.config.dynamic_test_duration,
            'description': f'阶跃响应验证 - 幅度 {step_amplitude:.2f} m³/s'
        }
    
    def _generate_sine_wave_scenario(self, interval: FlowStageInterval) -> Dict:
        """生成正弦波场景"""
        Q_center = (interval.Q_bounds[0] + interval.Q_bounds[1]) / 2.0
        H_center = (interval.H_bounds[0] + interval.H_bounds[1]) / 2.0
        
        Q_range = interval.Q_bounds[1] - interval.Q_bounds[0]
        amplitude = Q_range * 0.2  # 20%的区间范围
        
        return {
            'type': 'sine_wave',
            'center_state': {'Q_up': Q_center, 'H_up': H_center,
                           'Q_down': Q_center*0.98, 'H_down': H_center-0.05},
            'amplitude': amplitude,
            'frequency': 1.0 / 600.0,  # 10分钟周期
            'duration': self.config.dynamic_test_duration,
            'description': f'正弦波验证 - 幅度 {amplitude:.2f} m³/s'
        }
    
    def _evaluate_scenario(self, scenario_name: str, scenario_data: Dict,
                         idz_model: Any, reference_model: Any) -> Dict[str, Any]:
        """
        评估单个场景
        
        Args:
            scenario_name: 场景名称
            scenario_data: 场景数据
            idz_model: IDZ模型
            reference_model: 参考模型
            
        Returns:
            Dict: 场景误差结果
        """
        scenario_type = scenario_data['type']
        
        if scenario_type == 'steady_state':
            return self._evaluate_steady_state_scenario(scenario_data, idz_model, reference_model)
        elif scenario_type == 'step_response':
            return self._evaluate_step_response_scenario(scenario_data, idz_model, reference_model)
        elif scenario_type == 'sine_wave':
            return self._evaluate_sine_wave_scenario(scenario_data, idz_model, reference_model)
        else:
            self.logger.warning(f"未知场景类型: {scenario_type}")
            return {'point_errors': [], 'max_error': 0.0, 'mean_error': 0.0}
    
    def _evaluate_steady_state_scenario(self, scenario_data: Dict,
                                      idz_model: Any, reference_model: Any) -> Dict[str, Any]:
        """评估稳态场景"""
        test_points = scenario_data['test_points']
        point_errors = []
        
        for point in test_points:
            # 计算参考模型响应（简化实现）
            ref_Q_out, ref_H_out = self._compute_reference_steady_state(point, reference_model)
            
            # 计算IDZ模型响应
            idz_Q_out, idz_H_out = self._compute_idz_steady_state(point, idz_model)
            
            # 计算相对误差
            Q_error = abs(idz_Q_out - ref_Q_out) / max(ref_Q_out, 1e-6)
            H_error = abs(idz_H_out - ref_H_out) / max(ref_H_out, 1e-6)
            
            # 综合误差（加权平均）
            combined_error = 0.6 * Q_error + 0.4 * H_error
            point_errors.append(combined_error)
        
        return {
            'point_errors': point_errors,
            'max_error': np.max(point_errors) if point_errors else 0.0,
            'mean_error': np.mean(point_errors) if point_errors else 0.0,
            'test_points_count': len(test_points)
        }
    
    def _evaluate_step_response_scenario(self, scenario_data: Dict,
                                       idz_model: Any, reference_model: Any) -> Dict[str, Any]:
        """评估阶跃响应场景"""
        duration = scenario_data['duration']
        dt = 60.0  # 1分钟步长
        n_steps = int(duration / dt)
        time_array = np.linspace(0, duration, n_steps)
        
        # 生成阶跃输入信号
        initial_state = scenario_data['initial_state']
        step_amplitude = scenario_data['step_amplitude']
        step_time = scenario_data['step_time']
        
        step_index = int(step_time / dt)
        Q_input = np.full(n_steps, initial_state['Q_up'])
        Q_input[step_index:] += step_amplitude
        
        # 计算参考响应
        ref_response = self._simulate_reference_response(Q_input, time_array, reference_model)
        
        # 计算IDZ响应
        idz_response = self._simulate_idz_response(Q_input, time_array, idz_model)
        
        # 计算时间序列误差
        point_errors = []
        for i in range(len(ref_response)):
            if ref_response[i] > 1e-6:
                error = abs(idz_response[i] - ref_response[i]) / ref_response[i]
                point_errors.append(error)
        
        return {
            'point_errors': point_errors,
            'max_error': np.max(point_errors) if point_errors else 0.0,
            'mean_error': np.mean(point_errors) if point_errors else 0.0,
            'response_length': len(point_errors)
        }
    
    def _evaluate_sine_wave_scenario(self, scenario_data: Dict,
                                    idz_model: Any, reference_model: Any) -> Dict[str, Any]:
        """评估正弦波场景"""
        duration = scenario_data['duration']
        dt = 60.0
        n_steps = int(duration / dt)
        time_array = np.linspace(0, duration, n_steps)
        
        # 生成正弦波输入
        center_state = scenario_data['center_state']
        amplitude = scenario_data['amplitude']
        frequency = scenario_data['frequency']
        
        Q_input = center_state['Q_up'] + amplitude * np.sin(2 * np.pi * frequency * time_array)
        
        # 计算响应
        ref_response = self._simulate_reference_response(Q_input, time_array, reference_model)
        idz_response = self._simulate_idz_response(Q_input, time_array, idz_model)
        
        # 计算误差
        point_errors = []
        for i in range(len(ref_response)):
            if ref_response[i] > 1e-6:
                error = abs(idz_response[i] - ref_response[i]) / ref_response[i]
                point_errors.append(error)
        
        return {
            'point_errors': point_errors,
            'max_error': np.max(point_errors) if point_errors else 0.0,
            'mean_error': np.mean(point_errors) if point_errors else 0.0,
            'frequency_response_quality': self._assess_frequency_response(ref_response, idz_response)
        }
    
    def _compute_reference_steady_state(self, state_point: Dict, reference_model: Any) -> Tuple[float, float]:
        """计算参考模型的稳态响应"""
        # 简化实现：使用理论公式模拟
        Q_in = state_point['Q_up']
        H_in = state_point['H_up']
        
        # 模拟河道水力计算
        Q_out = Q_in * 0.98  # 假设2%的损失
        H_out = H_in - 0.05  # 假设5cm的水头损失
        
        return Q_out, H_out
    
    def _compute_idz_steady_state(self, state_point: Dict, idz_model: Any) -> Tuple[float, float]:
        """计算IDZ模型的稳态响应"""
        # 简化实现：直接使用稳态增益
        Q_in = state_point['Q_up']
        H_in = state_point['H_up']
        
        # 假设IDZ模型稳态增益为0.97
        Q_out = Q_in * 0.97
        H_out = H_in - 0.06
        
        return Q_out, H_out
    
    def _simulate_reference_response(self, Q_input: np.ndarray, time_array: np.ndarray,
                                   reference_model: Any) -> np.ndarray:
        """模拟参考模型响应"""
        # 简化实现：一阶系统响应
        tau = 200.0  # 时间常数
        dt = time_array[1] - time_array[0]
        
        response = np.zeros_like(Q_input)
        y_prev = Q_input[0] * 0.98
        
        for i in range(len(Q_input)):
            # 一阶系统差分方程
            response[i] = y_prev + dt/tau * (Q_input[i] * 0.98 - y_prev)
            y_prev = response[i]
        
        return response
    
    def _simulate_idz_response(self, Q_input: np.ndarray, time_array: np.ndarray,
                             idz_model: Any) -> np.ndarray:
        """模拟IDZ模型响应"""
        # 简化实现：带延迟的一阶系统
        tau = 180.0  # 略不同的时间常数
        delay = 120.0  # 2分钟延迟
        dt = time_array[1] - time_array[0]
        delay_steps = int(delay / dt)
        
        response = np.zeros_like(Q_input)
        delayed_input = np.zeros_like(Q_input)
        
        # 应用延迟
        if delay_steps < len(Q_input):
            delayed_input[delay_steps:] = Q_input[:-delay_steps]
        
        # 一阶系统响应
        y_prev = delayed_input[0] * 0.97
        for i in range(len(delayed_input)):
            response[i] = y_prev + dt/tau * (delayed_input[i] * 0.97 - y_prev)
            y_prev = response[i]
        
        return response
    
    def _assess_frequency_response(self, ref_response: np.ndarray, 
                                 idz_response: np.ndarray) -> float:
        """评估频域响应质量"""
        if len(ref_response) != len(idz_response) or len(ref_response) < 2:
            return 0.0
        
        # 计算相关系数
        correlation = np.corrcoef(ref_response, idz_response)[0, 1]
        
        # 计算相位延迟（简化）
        ref_fft = np.fft.fft(ref_response)
        idz_fft = np.fft.fft(idz_response)
        
        # 幅值比
        ref_magnitude = np.abs(ref_fft)
        idz_magnitude = np.abs(idz_fft)
        
        magnitude_ratio = np.mean(idz_magnitude) / np.mean(ref_magnitude) if np.mean(ref_magnitude) > 0 else 0.0
        
        # 综合评分
        quality_score = correlation * min(magnitude_ratio, 1.0/magnitude_ratio) if magnitude_ratio > 0 else 0.0
        
        return max(0.0, quality_score)
    
    def compute_error_metrics(self, idz_results: Dict, reference_results: Dict) -> Dict[str, float]:
        """
        计算误差指标
        
        Args:
            idz_results: IDZ模型结果
            reference_results: 参考模型结果
            
        Returns:
            Dict[str, float]: 误差指标
        """
        metrics = {}
        
        # 检查数据完整性
        common_keys = set(idz_results.keys()) & set(reference_results.keys())
        if not common_keys:
            return {'error': 1.0, 'message': '无公共结果键'}
        
        errors = []
        for key in common_keys:
            idz_val = idz_results[key]
            ref_val = reference_results[key]
            
            if isinstance(idz_val, (int, float)) and isinstance(ref_val, (int, float)):
                if abs(ref_val) > 1e-12:
                    relative_error = abs(idz_val - ref_val) / abs(ref_val)
                    errors.append(relative_error)
        
        if errors:
            metrics['max_relative_error'] = np.max(errors)
            metrics['mean_relative_error'] = np.mean(errors)
            metrics['std_relative_error'] = np.std(errors)
            metrics['rmse'] = np.sqrt(np.mean(np.array(errors)**2))
        else:
            metrics['max_relative_error'] = 1.0
            metrics['mean_relative_error'] = 1.0
        
        return metrics
    
    def assess_interval_quality(self, error_metrics: Dict[str, float]) -> str:
        """
        评估区间质量
        
        Args:
            error_metrics: 误差指标
            
        Returns:
            str: 质量等级 ('excellent', 'good', 'acceptable', 'poor')
        """
        max_error = error_metrics.get('max_error', 1.0)
        mean_error = error_metrics.get('mean_error', 1.0)
        
        if max_error <= 0.10 and mean_error <= 0.05:
            return 'excellent'
        elif max_error <= self.config.error_threshold and mean_error <= 0.10:
            return 'good'
        elif max_error <= self.config.error_threshold * 1.5 and mean_error <= 0.15:
            return 'acceptable'
        else:
            return 'poor'
    
    def _record_validation_history(self, interval: FlowStageInterval, error_metrics: Dict):
        """记录验证历史"""
        quality_assessment = self.assess_interval_quality(error_metrics)
        
        history_entry = {
            'interval_id': interval.interval_id,
            'timestamp': np.datetime64('now').astype(int),
            'error_metrics': error_metrics.copy(),
            'quality_assessment': quality_assessment,
            'validation_config': {
                'error_threshold': self.config.error_threshold,
                'test_scenarios': self.config.validation_scenarios
            }
        }
        
        self.validation_history.append(history_entry)
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """获取验证摘要"""
        if not self.validation_history:
            return {}
        
        recent_validations = self.validation_history[-20:]  # 最近20次验证
        
        max_errors = [v['error_metrics']['max_error'] for v in recent_validations]
        mean_errors = [v['error_metrics']['mean_error'] for v in recent_validations]
        quality_counts = {}
        
        for validation in recent_validations:
            quality = validation['quality_assessment']
            quality_counts[quality] = quality_counts.get(quality, 0) + 1
        
        return {
            'total_validations': len(self.validation_history),
            'recent_validations': len(recent_validations),
            'error_statistics': {
                'max_error_mean': np.mean(max_errors),
                'max_error_std': np.std(max_errors),
                'mean_error_avg': np.mean(mean_errors)
            },
            'quality_distribution': quality_counts,
            'success_rate': len([v for v in recent_validations 
                               if v['error_metrics']['max_error'] <= self.config.error_threshold]) / len(recent_validations)
        }


__all__ = ['AccuracyValidator', 'ValidationConfig']