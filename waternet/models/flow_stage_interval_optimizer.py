"""
流量水位区间优化器 - 主控制器

统筹整个区间优化过程，协调各个组件工作，实现完整的区间优化系统。

Author: WaterNet Development Team
Date: 2024-10-04
"""

import numpy as np
import time
from typing import Dict, List, Tuple, Optional, Callable, Any
import logging
from dataclasses import dataclass
import json
import warnings

from .flow_stage_interval_system import (
    FlowStageInterval, IntervalDatabase, OptimizationResults, IDZModelParameters
)
from .interval_partitioner import IntervalPartitioner, PartitioningConfig
from .idz_linearizer import IDZLinearizer, IDZLinearizationConfig
from .accuracy_validator import AccuracyValidator, ValidationConfig
from .interval_manager import IntervalManager, TransitionConfig


@dataclass
class OptimizerConfig:
    """优化器总配置"""
    # 基础设置
    error_threshold: float = 0.20                    # 全局误差阈值
    max_optimization_time: float = 3600.0           # 最大优化时间（秒）
    convergence_tolerance: float = 0.01             # 收敛容差
    max_iterations: int = 50                         # 最大迭代次数
    
    # 组件配置
    partitioning_config: Optional[PartitioningConfig] = None
    linearization_config: Optional[IDZLinearizationConfig] = None
    validation_config: Optional[ValidationConfig] = None
    transition_config: Optional[TransitionConfig] = None
    
    # 优化策略
    optimization_strategy: str = 'iterative_refinement'  # 优化策略
    parallel_processing: bool = False                    # 并行处理
    adaptive_parameters: bool = True                     # 自适应参数调整
    
    def __post_init__(self):
        """设置默认组件配置"""
        if self.partitioning_config is None:
            self.partitioning_config = PartitioningConfig()
        if self.linearization_config is None:
            self.linearization_config = IDZLinearizationConfig()
        if self.validation_config is None:
            self.validation_config = ValidationConfig()
        if self.transition_config is None:
            self.transition_config = TransitionConfig()


class FlowStageIntervalOptimizer:
    """
    流量水位区间优化器主控制器
    
    统筹整个区间优化过程，协调各组件协同工作。
    """
    
    def __init__(self, config: Optional[OptimizerConfig] = None):
        """
        初始化区间优化器
        
        Args:
            config: 优化器配置
        """
        self.config = config or OptimizerConfig()
        self.logger = logging.getLogger("FlowStageIntervalOptimizer")
        
        # 初始化组件
        self.database = IntervalDatabase()
        self.partitioner = IntervalPartitioner(self.config.partitioning_config)
        self.linearizer = IDZLinearizer(self.config.linearization_config)
        self.validator = AccuracyValidator(self.config.validation_config)
        self.manager = IntervalManager(self.database, self.config.transition_config)
        
        # 状态管理
        self.optimization_state: Dict[str, Any] = {}
        self.optimization_history: List[Dict] = []
        self.current_results: Optional[OptimizationResults] = None
        
        # 性能监控
        self.performance_monitor: Dict[str, Any] = {
            'total_optimizations': 0,
            'successful_optimizations': 0,
            'average_optimization_time': 0.0,
            'best_achievement': {'error': 1.0, 'intervals': 0}
        }
    
    def initialize_intervals(self, Q_range: Tuple[float, float], 
                           H_range: Tuple[float, float],
                           initial_grid_size: Optional[Tuple[int, int]] = None) -> List[FlowStageInterval]:
        """
        初始化区间
        
        Args:
            Q_range: 流量范围 [Q_min, Q_max]
            H_range: 水位范围 [H_min, H_max]
            initial_grid_size: 初始网格大小，如果为None则使用配置值
            
        Returns:
            List[FlowStageInterval]: 初始区间列表
        """
        self.logger.info(f"初始化区间：Q范围 {Q_range}, H范围 {H_range}")
        
        # 更新配置
        if initial_grid_size:
            self.config.partitioning_config.initial_grid_size = initial_grid_size
        
        # 创建初始网格
        intervals = self.partitioner.create_initial_grid(Q_range, H_range)
        
        # 添加到数据库
        for interval in intervals:
            self.database.add_interval(interval)
        
        # 更新邻居关系
        self.database.update_neighbors()
        
        self.logger.info(f"初始化完成，创建了 {len(intervals)} 个区间")
        
        return intervals
    
    def optimize_intervals(self, reference_model: Any, 
                         error_threshold: Optional[float] = None) -> OptimizationResults:
        """
        执行完整的区间优化
        
        Args:
            reference_model: 参考模型（圣维南模型）
            error_threshold: 误差阈值，如果为None则使用配置值
            
        Returns:
            OptimizationResults: 优化结果
        """
        start_time = time.time()
        error_threshold = error_threshold or self.config.error_threshold
        
        self.logger.info(f"开始区间优化，误差阈值: {error_threshold:.1%}")
        
        # 初始化优化状态
        self.optimization_state = {
            'iteration': 0,
            'best_error': float('inf'),
            'converged': False,
            'start_time': start_time,
            'error_threshold': error_threshold
        }
        
        intervals = self.database.get_all_intervals()
        if not intervals:
            raise ValueError("没有可优化的区间，请先调用initialize_intervals")
        
        # 执行优化循环
        for iteration in range(self.config.max_iterations):
            self.optimization_state['iteration'] = iteration
            
            self.logger.info(f"优化迭代 {iteration + 1}/{self.config.max_iterations}")
            
            # 步骤1: IDZ参数辨识
            self._optimize_idz_parameters(intervals, reference_model)
            
            # 步骤2: 精度验证
            validation_results = self._validate_intervals(intervals, reference_model)
            
            # 步骤3: 评估收敛性
            current_error = validation_results['max_error']
            self.optimization_state['current_error'] = current_error
            
            if current_error < self.optimization_state['best_error']:
                self.optimization_state['best_error'] = current_error
            
            # 检查收敛条件
            if current_error <= error_threshold:
                self.logger.info(f"优化收敛，最大误差: {current_error:.2%}")
                self.optimization_state['converged'] = True
                break
            
            # 步骤4: 自适应细分
            if self.config.optimization_strategy == 'iterative_refinement':
                intervals = self._adaptive_refinement_step(intervals, validation_results)
            
            # 步骤5: 检查时间限制
            elapsed_time = time.time() - start_time
            if elapsed_time > self.config.max_optimization_time:
                self.logger.warning(f"优化超时 ({elapsed_time:.1f}s)，停止优化")
                break
            
            # 记录迭代历史
            self._record_optimization_iteration(validation_results)
        
        # 生成最终结果
        optimization_time = time.time() - start_time
        final_results = self._generate_optimization_results(intervals, optimization_time)
        
        # 更新性能监控
        self._update_performance_monitor(final_results, optimization_time)
        
        self.current_results = final_results
        self.logger.info(f"优化完成，总耗时: {optimization_time:.2f}s")
        
        return final_results
    
    def validate_interval_quality(self, interval_id: str, 
                                reference_model: Any) -> Dict[str, float]:
        """
        验证单个区间质量
        
        Args:
            interval_id: 区间ID
            reference_model: 参考模型
            
        Returns:
            Dict[str, float]: 验证结果
        """
        interval = self.database.get_interval(interval_id)
        if not interval:
            raise ValueError(f"区间 {interval_id} 不存在")
        
        if not interval.idz_model:
            self.logger.warning(f"区间 {interval_id} 没有IDZ模型，先进行参数辨识")
            self._identify_interval_parameters(interval, reference_model)
        
        # 执行验证
        error_metrics = self.validator.evaluate_interval_accuracy(
            interval, interval.idz_model, reference_model)
        
        # 更新区间误差指标
        interval.error_metrics = error_metrics
        interval.update_quality_score(error_metrics['max_error'])
        
        return error_metrics
    
    def generate_optimization_report(self) -> str:
        """生成优化报告"""
        if not self.current_results:
            return "没有可用的优化结果"
        
        results = self.current_results
        
        report = f"""
=== 流量水位区间优化报告 ===

优化配置:
- 误差阈值: {self.config.error_threshold:.1%}
- 最大迭代次数: {self.config.max_iterations}
- 优化策略: {self.config.optimization_strategy}

优化结果:
{results.to_report()}

性能统计:
- 总优化次数: {self.performance_monitor['total_optimizations']}
- 成功率: {self.performance_monitor['successful_optimizations'] / max(self.performance_monitor['total_optimizations'], 1):.1%}
- 平均优化时间: {self.performance_monitor['average_optimization_time']:.2f}s
- 最佳成果: 误差 {self.performance_monitor['best_achievement']['error']:.2%}, 区间数 {self.performance_monitor['best_achievement']['intervals']}

组件状态:
- 区间分割器: {len(self.partitioner.refinement_history)} 次细分
- IDZ线性化器: {len(self.linearizer.get_identification_history())} 次辨识
- 精度验证器: {len(self.validator.validation_history)} 次验证
- 区间管理器: {len(self.manager.transition_history)} 次过渡

建议:
{self._generate_recommendations()}
        """
        
        return report
    
    def _optimize_idz_parameters(self, intervals: List[FlowStageInterval], reference_model: Any):
        """优化IDZ参数"""
        self.logger.info(f"开始IDZ参数辨识，处理 {len(intervals)} 个区间")
        
        successful_count = 0
        failed_intervals = []
        
        for interval in intervals:
            try:
                self._identify_interval_parameters(interval, reference_model)
                successful_count += 1
            except Exception as e:
                self.logger.warning(f"区间 {interval.interval_id} 参数辨识失败: {e}")
                failed_intervals.append(interval.interval_id)
        
        self.logger.info(f"IDZ参数辨识完成: {successful_count}/{len(intervals)} 成功")
        
        if failed_intervals:
            self.logger.warning(f"失败区间: {failed_intervals}")
    
    def _identify_interval_parameters(self, interval: FlowStageInterval, reference_model: Any):
        """辨识单个区间的参数"""
        # 计算平衡点
        equilibrium_point = self.linearizer.compute_equilibrium_point(interval)
        
        # 执行参数辨识
        idz_params = self.linearizer.identify_four_equation_parameters(
            interval, reference_model, equilibrium_point)
        
        # 创建IDZ模型实例（这里简化为存储参数）
        interval.idz_model = idz_params
        interval.equilibrium_point = equilibrium_point
        
        self.logger.debug(f"区间 {interval.interval_id} 参数辨识完成")
    
    def _validate_intervals(self, intervals: List[FlowStageInterval], 
                          reference_model: Any) -> Dict[str, float]:
        """验证所有区间"""
        self.logger.info(f"开始精度验证，处理 {len(intervals)} 个区间")
        
        all_errors = []
        valid_count = 0
        
        for interval in intervals:
            if interval.idz_model:
                try:
                    error_metrics = self.validator.evaluate_interval_accuracy(
                        interval, interval.idz_model, reference_model)
                    
                    interval.error_metrics = error_metrics
                    interval.update_quality_score(error_metrics['max_error'])
                    
                    all_errors.append(error_metrics['max_error'])
                    
                    if error_metrics['max_error'] <= self.config.error_threshold:
                        interval.validation_status = 'valid'
                        valid_count += 1
                    else:
                        interval.validation_status = 'invalid'
                        
                except Exception as e:
                    self.logger.warning(f"区间 {interval.interval_id} 验证失败: {e}")
                    interval.validation_status = 'error'
            else:
                interval.validation_status = 'pending'
        
        # 计算总体统计
        validation_results = {
            'max_error': np.max(all_errors) if all_errors else 1.0,
            'mean_error': np.mean(all_errors) if all_errors else 1.0,
            'std_error': np.std(all_errors) if all_errors else 0.0,
            'valid_count': valid_count,
            'total_count': len(intervals),
            'success_rate': valid_count / len(intervals)
        }
        
        self.logger.info(f"精度验证完成: {valid_count}/{len(intervals)} 区间满足误差要求")
        
        return validation_results
    
    def _adaptive_refinement_step(self, intervals: List[FlowStageInterval],
                                validation_results: Dict[str, float]) -> List[FlowStageInterval]:
        """自适应细分步骤"""
        # 如果整体误差可接受，不进行细分
        if validation_results['max_error'] <= self.config.error_threshold:
            return intervals
        
        self.logger.info("执行自适应细分")
        
        # 定义误差评估函数
        def error_evaluator(interval: FlowStageInterval) -> float:
            return interval.error_metrics.get('max_error', 1.0) if interval.error_metrics else 1.0
        
        # 执行自适应细分
        refined_intervals = self.partitioner.adaptive_refinement(intervals, error_evaluator)
        
        # 更新数据库
        self.database.intervals.clear()
        for interval in refined_intervals:
            self.database.add_interval(interval)
        self.database.update_neighbors()
        
        return refined_intervals
    
    def _record_optimization_iteration(self, validation_results: Dict[str, float]):
        """记录优化迭代"""
        iteration_record = {
            'iteration': self.optimization_state['iteration'],
            'timestamp': time.time(),
            'validation_results': validation_results.copy(),
            'total_intervals': validation_results['total_count'],
            'valid_intervals': validation_results['valid_count']
        }
        
        self.optimization_history.append(iteration_record)
    
    def _generate_optimization_results(self, intervals: List[FlowStageInterval],
                                     optimization_time: float) -> OptimizationResults:
        """生成优化结果"""
        results = OptimizationResults(
            total_intervals=len(intervals),
            optimization_time=optimization_time
        )
        
        # 计算统计信息
        results.compute_statistics(intervals)
        
        # 设置网格结构信息
        results.grid_structure = {
            'Q_range': self.partitioner.Q_range,
            'H_range': self.partitioner.H_range,
            'initial_grid_size': self.config.partitioning_config.initial_grid_size,
            'refinement_levels': len(self.partitioner.refinement_history)
        }
        
        # 设置性能基准
        results.performance_benchmarks = {
            'intervals_per_second': len(intervals) / optimization_time if optimization_time > 0 else 0,
            'average_identification_time': optimization_time / len(intervals) if len(intervals) > 0 else 0,
            'memory_usage_mb': self._estimate_memory_usage()
        }
        
        # 设置收敛历史
        results.convergence_history = self.optimization_history.copy()
        
        return results
    
    def _estimate_memory_usage(self) -> float:
        """估算内存使用量（MB）"""
        # 简化的内存估算
        intervals_count = len(self.database.intervals)
        
        # 每个区间大约2KB
        intervals_memory = intervals_count * 2
        
        # 历史记录内存
        history_memory = len(self.optimization_history) * 0.5
        
        # 缓存内存
        cache_memory = len(self.manager.response_cache) * 1
        
        total_memory_kb = intervals_memory + history_memory + cache_memory
        return total_memory_kb / 1024.0  # 转换为MB
    
    def _update_performance_monitor(self, results: OptimizationResults, optimization_time: float):
        """更新性能监控"""
        self.performance_monitor['total_optimizations'] += 1
        
        if results.success_rate > 0.8:  # 成功率超过80%认为成功
            self.performance_monitor['successful_optimizations'] += 1
        
        # 更新平均优化时间
        total_time = (self.performance_monitor['average_optimization_time'] * 
                     (self.performance_monitor['total_optimizations'] - 1) + optimization_time)
        self.performance_monitor['average_optimization_time'] = total_time / self.performance_monitor['total_optimizations']
        
        # 更新最佳成果
        best_error = results.accuracy_statistics.get('max_error', 1.0)
        if best_error < self.performance_monitor['best_achievement']['error']:
            self.performance_monitor['best_achievement'] = {
                'error': best_error,
                'intervals': results.total_intervals
            }
    
    def _generate_recommendations(self) -> str:
        """生成优化建议"""
        if not self.current_results:
            return "无可用结果，无法生成建议"
        
        recommendations = []
        
        # 基于成功率的建议
        success_rate = self.current_results.success_rate
        if success_rate < 0.7:
            recommendations.append("- 成功率较低，建议调整误差阈值或增加细分层级")
        
        # 基于区间数量的建议
        total_intervals = self.current_results.total_intervals
        if total_intervals > 150:
            recommendations.append("- 区间数量较多，可能影响计算效率，考虑合并相似区间")
        elif total_intervals < 20:
            recommendations.append("- 区间数量较少，可能覆盖不够充分，考虑增加初始网格密度")
        
        # 基于误差分布的建议
        error_stats = self.current_results.accuracy_statistics
        if error_stats.get('std_error', 0) > 0.05:
            recommendations.append("- 误差分布不均，建议使用误差均匀化优化策略")
        
        return '\n'.join(recommendations) if recommendations else "- 当前优化结果良好，无特殊建议"
    
    def save_optimization_results(self, filepath: str):
        """保存优化结果"""
        if not self.current_results:
            raise ValueError("没有可保存的优化结果")
        
        # 准备保存数据
        save_data = {
            'optimization_results': self.current_results.to_dict() if hasattr(self.current_results, 'to_dict') else {},
            'configuration': {
                'error_threshold': self.config.error_threshold,
                'optimization_strategy': self.config.optimization_strategy,
                'max_iterations': self.config.max_iterations
            },
            'intervals': [interval.to_dict() for interval in self.database.get_all_intervals()],
            'performance_monitor': self.performance_monitor.copy(),
            'optimization_history': self.optimization_history.copy()
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=2, ensure_ascii=False, default=str)
        
        self.logger.info(f"优化结果已保存至: {filepath}")
    
    def load_optimization_results(self, filepath: str):
        """加载优化结果"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 恢复区间数据库
            self.database.intervals.clear()
            for interval_data in data.get('intervals', []):
                interval = FlowStageInterval.from_dict(interval_data)
                self.database.add_interval(interval)
            
            # 恢复历史记录
            self.optimization_history = data.get('optimization_history', [])
            self.performance_monitor.update(data.get('performance_monitor', {}))
            
            self.logger.info(f"优化结果已从 {filepath} 加载")
            
        except Exception as e:
            self.logger.error(f"加载优化结果失败: {e}")
            raise


__all__ = ['FlowStageIntervalOptimizer', 'OptimizerConfig']