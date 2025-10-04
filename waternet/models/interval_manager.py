"""
区间管理器 - 运行时切换和平滑过渡

负责运行时的区间选择和切换，实现多区间间的平滑过渡。

Author: WaterNet Development Team
Date: 2024-10-04
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Callable, Any
import logging
from dataclasses import dataclass
import warnings
from scipy.interpolate import interp1d, griddata

from .flow_stage_interval_system import FlowStageInterval, IntervalDatabase


@dataclass
class TransitionConfig:
    """过渡配置参数"""
    transition_method: str = 'linear'              # 过渡方法 ('linear', 'cubic', 'weighted')
    transition_duration: float = 300.0             # 过渡时长（秒）
    overlap_tolerance: float = 0.05                # 重叠容差
    boundary_smoothing: bool = True                # 边界平滑
    cache_size: int = 100                         # 缓存大小
    prediction_horizon: float = 180.0              # 预测时域（秒）


class IntervalManager:
    """
    区间管理器
    
    运行时的区间选择和切换，支持平滑过渡和性能优化。
    """
    
    def __init__(self, interval_database: IntervalDatabase, 
                 config: Optional[TransitionConfig] = None):
        """
        初始化区间管理器
        
        Args:
            interval_database: 区间数据库
            config: 过渡配置
        """
        self.database = interval_database
        self.config = config or TransitionConfig()
        self.logger = logging.getLogger("IntervalManager")
        
        # 状态管理
        self.current_interval: Optional[FlowStageInterval] = None
        self.previous_interval: Optional[FlowStageInterval] = None
        self.transition_state: Dict[str, Any] = {}
        
        # 性能缓存
        self.response_cache: Dict[str, Dict] = {}
        self.transition_history: List[Dict] = []
        
        # 预测和平滑
        self.trajectory_predictor: Optional[Any] = None
        self.boundary_interpolators: Dict[str, Any] = {}
    
    def select_active_interval(self, current_Q: float, current_H: float) -> Optional[FlowStageInterval]:
        """
        选择当前活跃区间
        
        Args:
            current_Q: 当前流量
            current_H: 当前水位
            
        Returns:
            FlowStageInterval: 选中的区间，如果没有合适区间则返回None
        """
        # 优先检查当前区间是否仍然适用
        if (self.current_interval and 
            self.current_interval.contains_point(current_Q, current_H)):
            return self.current_interval
        
        # 查找包含当前点的区间
        containing_interval = self.database.find_containing_interval(current_Q, current_H)
        
        if containing_interval:
            # 检查是否需要切换
            if containing_interval != self.current_interval:
                self._prepare_transition(containing_interval, current_Q, current_H)
            
            return containing_interval
        
        # 如果没有直接包含的区间，寻找最近的区间
        nearest_interval = self._find_nearest_interval(current_Q, current_H)
        
        if nearest_interval:
            distance = self._compute_distance_to_interval(current_Q, current_H, nearest_interval)
            
            # 如果距离在可接受范围内，使用最近区间
            if distance <= self.config.overlap_tolerance:
                if nearest_interval != self.current_interval:
                    self._prepare_transition(nearest_interval, current_Q, current_H)
                
                return nearest_interval
        
        # 没有找到合适的区间
        self.logger.warning(f"未找到适合点 ({current_Q:.2f}, {current_H:.3f}) 的区间")
        return None
    
    def smooth_transition_between_intervals(self, from_interval: FlowStageInterval,
                                          to_interval: FlowStageInterval,
                                          current_Q: float, current_H: float) -> Dict[str, float]:
        """
        实现区间间的平滑过渡
        
        Args:
            from_interval: 源区间
            to_interval: 目标区间
            current_Q: 当前流量
            current_H: 当前水位
            
        Returns:
            Dict: 过渡响应
        """
        transition_key = f"{from_interval.interval_id}_to_{to_interval.interval_id}"
        
        # 检查缓存
        if transition_key in self.response_cache:
            cached_response = self.response_cache[transition_key]
            if self._is_cache_valid(cached_response, current_Q, current_H):
                return cached_response['response']
        
        # 计算过渡权重
        weight = self._compute_transition_weight(from_interval, to_interval, current_Q, current_H)
        
        # 获取两个区间的响应
        from_response = self._get_interval_response(from_interval, current_Q, current_H)
        to_response = self._get_interval_response(to_interval, current_Q, current_H)
        
        # 执行加权平均
        transition_response = self._weighted_average_responses(
            from_response, to_response, weight)
        
        # 应用边界平滑
        if self.config.boundary_smoothing:
            transition_response = self._apply_boundary_smoothing(
                transition_response, from_interval, to_interval)
        
        # 缓存结果
        self._cache_transition_response(transition_key, transition_response, current_Q, current_H)
        
        # 记录过渡历史
        self._record_transition(from_interval, to_interval, weight, current_Q, current_H)
        
        return transition_response
    
    def interpolate_boundary_responses(self, Q: float, H: float, 
                                     adjacent_intervals: List[FlowStageInterval]) -> Dict[str, float]:
        """
        在区间边界处插值响应
        
        Args:
            Q: 流量
            H: 水位
            adjacent_intervals: 相邻区间列表
            
        Returns:
            Dict: 插值响应
        """
        if not adjacent_intervals:
            return {}
        
        if len(adjacent_intervals) == 1:
            return self._get_interval_response(adjacent_intervals[0], Q, H)
        
        # 收集相邻区间的响应和权重
        responses = []
        weights = []
        
        for interval in adjacent_intervals:
            response = self._get_interval_response(interval, Q, H)
            weight = self._compute_interpolation_weight(interval, Q, H)
            
            responses.append(response)
            weights.append(weight)
        
        # 归一化权重
        total_weight = sum(weights)
        if total_weight > 0:
            weights = [w / total_weight for w in weights]
        else:
            weights = [1.0 / len(weights)] * len(weights)
        
        # 加权平均
        interpolated_response = {}
        
        # 获取所有响应的键
        all_keys = set()
        for response in responses:
            all_keys.update(response.keys())
        
        for key in all_keys:
            weighted_value = 0.0
            for response, weight in zip(responses, weights):
                if key in response:
                    weighted_value += response[key] * weight
            
            interpolated_response[key] = weighted_value
        
        return interpolated_response
    
    def update_interval_database(self, new_intervals: List[FlowStageInterval]):
        """
        更新区间数据库
        
        Args:
            new_intervals: 新的区间列表
        """
        # 清空现有区间
        for interval_id in list(self.database.intervals.keys()):
            self.database.remove_interval(interval_id)
        
        # 添加新区间
        for interval in new_intervals:
            self.database.add_interval(interval)
        
        # 更新邻居关系
        self.database.update_neighbors()
        
        # 清空缓存
        self.response_cache.clear()
        self.boundary_interpolators.clear()
        
        # 重置当前状态
        self.current_interval = None
        self.previous_interval = None
        
        self.logger.info(f"区间数据库已更新，包含 {len(new_intervals)} 个区间")
    
    def _prepare_transition(self, target_interval: FlowStageInterval, Q: float, H: float):
        """准备区间过渡"""
        self.previous_interval = self.current_interval
        self.current_interval = target_interval
        
        if self.previous_interval:
            self.logger.debug(f"准备从区间 {self.previous_interval.interval_id} "
                            f"过渡到区间 {target_interval.interval_id}")
            
            # 初始化过渡状态
            self.transition_state = {
                'start_time': 0.0,  # 应该是实际时间
                'from_interval': self.previous_interval.interval_id,
                'to_interval': target_interval.interval_id,
                'transition_point': (Q, H),
                'is_active': True
            }
    
    def _find_nearest_interval(self, Q: float, H: float) -> Optional[FlowStageInterval]:
        """查找最近的区间"""
        intervals = self.database.get_valid_intervals()
        if not intervals:
            return None
        
        min_distance = float('inf')
        nearest_interval = None
        
        for interval in intervals:
            distance = self._compute_distance_to_interval(Q, H, interval)
            if distance < min_distance:
                min_distance = distance
                nearest_interval = interval
        
        return nearest_interval
    
    def _compute_distance_to_interval(self, Q: float, H: float, 
                                    interval: FlowStageInterval) -> float:
        """计算点到区间的距离"""
        Q_min, Q_max = interval.Q_bounds
        H_min, H_max = interval.H_bounds
        
        # 计算到矩形区域的距离
        dQ = 0 if Q_min <= Q <= Q_max else min(abs(Q - Q_min), abs(Q - Q_max))
        dH = 0 if H_min <= H <= H_max else min(abs(H - H_min), abs(H - H_max))
        
        # 欧几里得距离
        return np.sqrt(dQ**2 + dH**2)
    
    def _compute_transition_weight(self, from_interval: FlowStageInterval,
                                 to_interval: FlowStageInterval,
                                 Q: float, H: float) -> float:
        """
        计算过渡权重
        
        返回值为0-1之间，0表示完全使用from_interval，1表示完全使用to_interval
        """
        # 基于距离的权重计算
        dist_from = self._compute_distance_to_interval(Q, H, from_interval)
        dist_to = self._compute_distance_to_interval(Q, H, to_interval)
        
        total_dist = dist_from + dist_to
        if total_dist == 0:
            return 0.5  # 如果距离都为0，使用平均权重
        
        # 距离目标区间越近，权重越大
        weight = dist_from / total_dist
        
        # 确保权重在[0, 1]范围内
        return np.clip(weight, 0.0, 1.0)
    
    def _compute_interpolation_weight(self, interval: FlowStageInterval, Q: float, H: float) -> float:
        """计算插值权重"""
        distance = self._compute_distance_to_interval(Q, H, interval)
        
        # 反距离权重
        if distance == 0:
            return 1.0
        else:
            return 1.0 / (1.0 + distance)
    
    def _get_interval_response(self, interval: FlowStageInterval, Q: float, H: float) -> Dict[str, float]:
        """获取区间响应"""
        # 简化实现：返回基于区间特性的模拟响应
        Q_center, H_center = interval.get_center()
        
        # 基于当前点与区间中心的偏差计算响应
        Q_deviation = Q - Q_center
        H_deviation = H - H_center
        
        # 模拟响应（实际应用中应该调用IDZ模型）
        response = {
            'Q_out': Q * 0.98 + Q_deviation * 0.02,
            'H_out': H - 0.05 + H_deviation * 0.1,
            'response_time': 300.0,  # 5分钟响应时间
            'quality_factor': interval.quality_score
        }
        
        return response
    
    def _weighted_average_responses(self, response1: Dict[str, float],
                                  response2: Dict[str, float], weight: float) -> Dict[str, float]:
        """计算响应的加权平均"""
        averaged_response = {}
        
        # 获取所有键的并集
        all_keys = set(response1.keys()) | set(response2.keys())
        
        for key in all_keys:
            val1 = response1.get(key, 0.0)
            val2 = response2.get(key, 0.0)
            
            # 加权平均：weight=0使用response1，weight=1使用response2
            averaged_response[key] = (1 - weight) * val1 + weight * val2
        
        return averaged_response
    
    def _apply_boundary_smoothing(self, response: Dict[str, float],
                                from_interval: FlowStageInterval,
                                to_interval: FlowStageInterval) -> Dict[str, float]:
        """应用边界平滑"""
        # 简化的平滑实现：对响应值应用低通滤波效果
        smoothed_response = response.copy()
        
        # 对主要响应变量应用平滑
        for key in ['Q_out', 'H_out']:
            if key in smoothed_response:
                # 简单的移动平均效果
                original_value = smoothed_response[key]
                
                # 基于质量评分调整平滑程度
                from_quality = from_interval.quality_score
                to_quality = to_interval.quality_score
                avg_quality = (from_quality + to_quality) / 2.0
                
                # 质量越高，平滑越少
                smoothing_factor = 0.1 * (1.0 - avg_quality)
                smoothed_response[key] = original_value * (1 - smoothing_factor) + original_value * smoothing_factor
        
        return smoothed_response
    
    def _is_cache_valid(self, cached_response: Dict, Q: float, H: float) -> bool:
        """检查缓存是否有效"""
        if 'point' not in cached_response or 'timestamp' not in cached_response:
            return False
        
        cached_Q, cached_H = cached_response['point']
        
        # 检查点距离
        distance = np.sqrt((Q - cached_Q)**2 + (H - cached_H)**2)
        
        # 如果距离很小，认为缓存有效
        return distance < 0.1
    
    def _cache_transition_response(self, transition_key: str, response: Dict[str, float],
                                 Q: float, H: float):
        """缓存过渡响应"""
        # 限制缓存大小
        if len(self.response_cache) >= self.config.cache_size:
            # 移除最旧的缓存项
            oldest_key = next(iter(self.response_cache))
            del self.response_cache[oldest_key]
        
        self.response_cache[transition_key] = {
            'response': response,
            'point': (Q, H),
            'timestamp': 0.0  # 应该是实际时间戳
        }
    
    def _record_transition(self, from_interval: FlowStageInterval,
                         to_interval: FlowStageInterval, weight: float,
                         Q: float, H: float):
        """记录过渡历史"""
        transition_record = {
            'from_interval': from_interval.interval_id,
            'to_interval': to_interval.interval_id,
            'transition_weight': weight,
            'transition_point': (Q, H),
            'timestamp': 0.0,  # 应该是实际时间戳
            'method': self.config.transition_method
        }
        
        self.transition_history.append(transition_record)
        
        # 限制历史记录长度
        if len(self.transition_history) > 1000:
            self.transition_history = self.transition_history[-1000:]
    
    def get_transition_statistics(self) -> Dict[str, Any]:
        """获取过渡统计信息"""
        if not self.transition_history:
            return {}
        
        recent_transitions = self.transition_history[-100:]  # 最近100次过渡
        
        # 统计过渡频率
        interval_pairs = {}
        for transition in recent_transitions:
            pair = (transition['from_interval'], transition['to_interval'])
            interval_pairs[pair] = interval_pairs.get(pair, 0) + 1
        
        # 统计权重分布
        weights = [t['transition_weight'] for t in recent_transitions]
        
        return {
            'total_transitions': len(self.transition_history),
            'recent_transitions': len(recent_transitions),
            'most_common_pairs': sorted(interval_pairs.items(), key=lambda x: x[1], reverse=True)[:5],
            'weight_statistics': {
                'mean': np.mean(weights),
                'std': np.std(weights),
                'min': np.min(weights),
                'max': np.max(weights)
            },
            'cache_hit_rate': len(self.response_cache) / max(len(recent_transitions), 1)
        }
    
    def optimize_transition_performance(self):
        """优化过渡性能"""
        # 分析过渡历史，优化缓存策略
        if len(self.transition_history) < 10:
            return
        
        # 统计最频繁的过渡
        transition_counts = {}
        for transition in self.transition_history[-200:]:  # 最近200次
            key = (transition['from_interval'], transition['to_interval'])
            transition_counts[key] = transition_counts.get(key, 0) + 1
        
        # 预热频繁使用的过渡
        frequent_transitions = sorted(transition_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        for (from_id, to_id), count in frequent_transitions:
            from_interval = self.database.get_interval(from_id)
            to_interval = self.database.get_interval(to_id)
            
            if from_interval and to_interval:
                # 为频繁过渡预计算一些响应
                self._precompute_transition_responses(from_interval, to_interval)
        
        self.logger.info(f"性能优化完成，预热了 {len(frequent_transitions)} 个频繁过渡")
    
    def _precompute_transition_responses(self, from_interval: FlowStageInterval,
                                       to_interval: FlowStageInterval):
        """预计算过渡响应"""
        # 在过渡边界区域预计算几个代表点的响应
        Q1_min, Q1_max = from_interval.Q_bounds
        Q2_min, Q2_max = to_interval.Q_bounds
        H1_min, H1_max = from_interval.H_bounds
        H2_min, H2_max = to_interval.H_bounds
        
        # 找到重叠或相邻区域
        Q_overlap = (max(Q1_min, Q2_min), min(Q1_max, Q2_max))
        H_overlap = (max(H1_min, H2_min), min(H1_max, H2_max))
        
        if Q_overlap[0] <= Q_overlap[1] and H_overlap[0] <= H_overlap[1]:
            # 在重叠区域预计算几个点
            for Q in np.linspace(Q_overlap[0], Q_overlap[1], 3):
                for H in np.linspace(H_overlap[0], H_overlap[1], 3):
                    self.smooth_transition_between_intervals(from_interval, to_interval, Q, H)


__all__ = ['IntervalManager', 'TransitionConfig']