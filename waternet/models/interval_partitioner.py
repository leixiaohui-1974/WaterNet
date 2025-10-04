"""
区间划分器 - 二维Q-H空间分段算法

实现了基于流量和水位的物理特性的自适应二维网格划分策略。

Author: WaterNet Development Team
Date: 2024-10-04
"""

import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Optional, Callable, Any
import logging
from dataclasses import dataclass
from sklearn.cluster import KMeans

from .flow_stage_interval_system import FlowStageInterval


@dataclass
class PartitioningConfig:
    """区间划分配置参数"""
    initial_grid_size: Tuple[int, int] = (6, 6)
    max_refinement_levels: int = 3
    error_threshold: float = 0.20
    min_interval_size: Tuple[float, float] = (5.0, 0.1)  # (m³/s, m)
    max_intervals: int = 200
    refinement_strategy: str = 'adaptive'
    merge_similar_intervals: bool = True


class IntervalPartitioner:
    """区间划分器 - 负责管理Q-H空间的分段策略"""
    
    def __init__(self, config: Optional[PartitioningConfig] = None):
        self.config = config or PartitioningConfig()
        self.logger = logging.getLogger("IntervalPartitioner")
        self.Q_range: Optional[Tuple[float, float]] = None
        self.H_range: Optional[Tuple[float, float]] = None
        self.refinement_history: List[Dict] = []
    
    def create_initial_grid(self, Q_range: Tuple[float, float], 
                          H_range: Tuple[float, float]) -> List[FlowStageInterval]:
        """创建初始均匀网格"""
        self.Q_range = Q_range
        self.H_range = H_range
        
        Q_min, Q_max = Q_range
        H_min, H_max = H_range
        n_Q, n_H = self.config.initial_grid_size
        
        Q_step = (Q_max - Q_min) / n_Q
        H_step = (H_max - H_min) / n_H
        
        intervals = []
        for i in range(n_Q):
            for j in range(n_H):
                Q_left = Q_min + i * Q_step
                Q_right = Q_min + (i + 1) * Q_step
                H_bottom = H_min + j * H_step
                H_top = H_min + (j + 1) * H_step
                
                interval = FlowStageInterval(
                    interval_id=f"grid_{i}_{j}",
                    Q_bounds=(Q_left, Q_right),
                    H_bounds=(H_bottom, H_top),
                    metadata={'grid_position': (i, j), 'refinement_level': 0}
                )
                intervals.append(interval)
        
        self.logger.info(f"创建初始网格: {n_Q}×{n_H} = {len(intervals)} 个区间")
        return intervals
    
    def adaptive_refinement(self, intervals: List[FlowStageInterval], 
                          error_evaluator: Callable[[FlowStageInterval], float]) -> List[FlowStageInterval]:
        """自适应细分算法"""
        refined_intervals = []
        total_refined = 0
        
        for interval in intervals:
            error = error_evaluator(interval)
            
            if self._should_refine(interval, error):
                sub_intervals = self._subdivide_interval(interval)
                refined_intervals.extend(sub_intervals)
                total_refined += 1
            else:
                refined_intervals.append(interval)
        
        self.logger.info(f"细分完成: {len(intervals)} -> {len(refined_intervals)} 个区间")
        return refined_intervals
    
    def _should_refine(self, interval: FlowStageInterval, error: float) -> bool:
        """判断区间是否需要细分"""
        if error <= self.config.error_threshold:
            return False
        
        current_level = interval.metadata.get('refinement_level', 0)
        if current_level >= self.config.max_refinement_levels:
            return False
        
        Q_span = interval.Q_bounds[1] - interval.Q_bounds[0]
        H_span = interval.H_bounds[1] - interval.H_bounds[0]
        min_Q_size, min_H_size = self.config.min_interval_size
        
        return Q_span / 2 >= min_Q_size and H_span / 2 >= min_H_size
    
    def _subdivide_interval(self, interval: FlowStageInterval) -> List[FlowStageInterval]:
        """细分单个区间为4个子区间"""
        Q_min, Q_max = interval.Q_bounds
        H_min, H_max = interval.H_bounds
        Q_mid = (Q_min + Q_max) / 2
        H_mid = (H_min + H_max) / 2
        
        sub_intervals = []
        positions = [
            ((Q_min, Q_mid), (H_min, H_mid), 'sw'),
            ((Q_mid, Q_max), (H_min, H_mid), 'se'),
            ((Q_min, Q_mid), (H_mid, H_max), 'nw'),
            ((Q_mid, Q_max), (H_mid, H_max), 'ne')
        ]
        
        current_level = interval.metadata.get('refinement_level', 0)
        
        for Q_bounds, H_bounds, direction in positions:
            sub_interval = FlowStageInterval(
                interval_id=f"{interval.interval_id}_{direction}",
                Q_bounds=Q_bounds,
                H_bounds=H_bounds,
                metadata={
                    'parent_id': interval.interval_id,
                    'refinement_level': current_level + 1,
                    'subdivision_direction': direction
                }
            )
            sub_intervals.append(sub_interval)
        
        return sub_intervals
    
    def merge_similar_intervals(self, intervals: List[FlowStageInterval]) -> List[FlowStageInterval]:
        """合并相似区间"""
        if not self.config.merge_similar_intervals or len(intervals) < 2:
            return intervals
        
        # 简化的合并策略：基于质量评分相似性
        quality_scores = [interval.quality_score for interval in intervals]
        if len(set(quality_scores)) < 2:  # 所有区间质量相同
            return intervals
        
        # 使用K-means聚类找到相似区间
        n_clusters = min(3, len(intervals) // 2)
        if n_clusters < 2:
            return intervals
        
        features = np.array([[interval.quality_score, interval.get_area()] for interval in intervals])
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(features)
        
        merged_intervals = []
        for cluster_id in range(n_clusters):
            cluster_intervals = [intervals[i] for i in range(len(intervals)) 
                               if cluster_labels[i] == cluster_id]
            
            if len(cluster_intervals) > 1 and self._can_merge_cluster(cluster_intervals):
                merged_interval = self._merge_cluster(cluster_intervals)
                merged_intervals.append(merged_interval)
            else:
                merged_intervals.extend(cluster_intervals)
        
        self.logger.info(f"合并后: {len(intervals)} -> {len(merged_intervals)} 个区间")
        return merged_intervals
    
    def _can_merge_cluster(self, intervals: List[FlowStageInterval]) -> bool:
        """检查区间聚类是否可以合并"""
        if len(intervals) < 2:
            return False
        
        # 检查质量评分方差
        quality_scores = [interval.quality_score for interval in intervals]
        if np.var(quality_scores) > 0.01:
            return False
        
        return True
    
    def _merge_cluster(self, intervals: List[FlowStageInterval]) -> FlowStageInterval:
        """合并区间聚类"""
        # 计算包围盒
        Q_bounds = [interval.Q_bounds for interval in intervals]
        H_bounds = [interval.H_bounds for interval in intervals]
        
        Q_min = min(bounds[0] for bounds in Q_bounds)
        Q_max = max(bounds[1] for bounds in Q_bounds)
        H_min = min(bounds[0] for bounds in H_bounds)
        H_max = max(bounds[1] for bounds in H_bounds)
        
        merged_id = f"merged_{'_'.join(interval.interval_id for interval in intervals[:3])}"
        
        return FlowStageInterval(
            interval_id=merged_id,
            Q_bounds=(Q_min, Q_max),
            H_bounds=(H_min, H_max),
            quality_score=np.mean([interval.quality_score for interval in intervals]),
            metadata={
                'merged_from': [interval.interval_id for interval in intervals],
                'creation_method': 'merge',
                'original_count': len(intervals)
            }
        )
    
    def visualize_intervals(self, intervals: List[FlowStageInterval], 
                          filepath: Optional[str] = None) -> None:
        """可视化区间划分结果"""
        if not intervals:
            return
        
        fig, ax = plt.subplots(figsize=(10, 8))
        
        colors = [interval.quality_score for interval in intervals]
        max_color = max(colors) if colors else 1.0
        
        for i, interval in enumerate(intervals):
            Q_min, Q_max = interval.Q_bounds
            H_min, H_max = interval.H_bounds
            
            color_val = colors[i] / max_color if max_color > 0 else 0
            rect = plt.Rectangle((Q_min, H_min), Q_max - Q_min, H_max - H_min,
                               linewidth=1, edgecolor='black', alpha=0.7,
                               facecolor=plt.cm.viridis(color_val))
            ax.add_patch(rect)
        
        ax.set_xlabel('流量 (m³/s)')
        ax.set_ylabel('水位 (m)')
        ax.set_title(f'流量水位区间划分 ({len(intervals)} 个区间)')
        ax.grid(True, alpha=0.3)
        
        if filepath:
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            self.logger.info(f"可视化图已保存至: {filepath}")
        
        plt.tight_layout()
        plt.show()


__all__ = ['IntervalPartitioner', 'PartitioningConfig']