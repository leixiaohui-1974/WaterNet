"""
基于入口-出口双断面分段线性化的流量水位区间优化系统

这个模块实现了针对明渠水力系统入口和出口两个断面的分段线性化流量水位区间优化。
系统通过优化流量和水位的离散步长，在每个区间内使用四方程IDZ模型进行双断面耦合线性化辨识，
确保每个区间的线性化模型与原精细化圣维南模型的误差控制在20%以内。

主要功能：
1. 基于5断面明渠的入口和出口断面，建立双节点四方程IDZ耦合模型
2. 实现流量水位二维空间的智能分段，为每个区间确定最优的双断面平衡点
3. 辨识四个传递函数参数，完整描述入口-出口间的双向耦合关系
4. 建立误差控制机制，确保各区间线性化模型误差小于20%
5. 构建区间切换和平滑过渡机制，保证系统稳定性

Author: WaterNet Development Team
Date: 2024-10-04
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Callable, Any, Union
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import warnings
import logging
from scipy.optimize import minimize, differential_evolution
from scipy.interpolate import RegularGridInterpolator
import json
import time
from copy import deepcopy


@dataclass
class FlowStageInterval:
    """
    流量水位区间数据结构
    
    表示二维Q-H空间中的一个区间，包含该区间的几何边界、
    物理平衡点、IDZ模型参数、精度指标等完整信息。
    
    Attributes:
        interval_id (str): 区间唯一标识符
        Q_bounds (Tuple[float, float]): 流量边界 [Q_min, Q_max] (m³/s)
        H_bounds (Tuple[float, float]): 水位边界 [H_min, H_max] (m)
        equilibrium_point (Dict[str, float]): 双断面平衡点
        idz_model (Optional[Any]): IDZ四方程模型实例
        error_metrics (Dict[str, float]): 误差评估结果
        quality_score (float): 区间质量评分 [0, 1]
        neighboring_intervals (List[str]): 相邻区间ID列表
        creation_time (float): 区间创建时间
        last_updated (float): 最后更新时间
        validation_status (str): 验证状态
        metadata (Dict[str, Any]): 扩展元数据
    """
    
    interval_id: str
    Q_bounds: Tuple[float, float]
    H_bounds: Tuple[float, float]
    equilibrium_point: Dict[str, float] = field(default_factory=dict)
    idz_model: Optional[Any] = None
    error_metrics: Dict[str, float] = field(default_factory=dict)
    quality_score: float = 0.0
    neighboring_intervals: List[str] = field(default_factory=list)
    creation_time: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)
    validation_status: str = "pending"  # pending, valid, invalid, expired
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """初始化后的验证和设置"""
        self._validate_bounds()
        if not self.equilibrium_point:
            self._compute_default_equilibrium()
    
    def _validate_bounds(self):
        """验证区间边界的合理性"""
        Q_min, Q_max = self.Q_bounds
        H_min, H_max = self.H_bounds
        
        if Q_min >= Q_max:
            raise ValueError(f"流量边界不合理: Q_min={Q_min} >= Q_max={Q_max}")
        if H_min >= H_max:
            raise ValueError(f"水位边界不合理: H_min={H_min} >= H_max={H_max}")
        if Q_min < 0:
            raise ValueError(f"流量不能为负: Q_min={Q_min}")
    
    def _compute_default_equilibrium(self):
        """计算默认的平衡点（几何中心）"""
        Q_center = (self.Q_bounds[0] + self.Q_bounds[1]) / 2.0
        H_center = (self.H_bounds[0] + self.H_bounds[1]) / 2.0
        
        self.equilibrium_point = {
            'Q_up': Q_center,
            'H_up': H_center,
            'Q_down': Q_center * 0.95,  # 假设下游略小
            'H_down': H_center - 0.05   # 假设下游略低
        }
    
    def contains_point(self, Q: float, H: float) -> bool:
        """检查给定的(Q, H)点是否在区间内"""
        Q_min, Q_max = self.Q_bounds
        H_min, H_max = self.H_bounds
        return Q_min <= Q <= Q_max and H_min <= H <= H_max
    
    def get_center(self) -> Tuple[float, float]:
        """获取区间中心点"""
        Q_center = (self.Q_bounds[0] + self.Q_bounds[1]) / 2.0
        H_center = (self.H_bounds[0] + self.H_bounds[1]) / 2.0
        return Q_center, H_center
    
    def get_area(self) -> float:
        """计算区间面积"""
        Q_span = self.Q_bounds[1] - self.Q_bounds[0]
        H_span = self.H_bounds[1] - self.H_bounds[0]
        return Q_span * H_span
    
    def update_quality_score(self, max_error: float, target_error: float = 0.20):
        """
        基于误差指标更新质量评分
        
        Args:
            max_error (float): 区间内最大误差
            target_error (float): 目标误差阈值（默认20%）
        """
        if max_error <= target_error:
            self.quality_score = 1.0 - (max_error / target_error) * 0.5
        else:
            self.quality_score = 0.5 * np.exp(-(max_error - target_error) * 2)
        
        self.last_updated = time.time()
    
    def is_neighbor(self, other: 'FlowStageInterval') -> bool:
        """检查与另一个区间是否相邻"""
        # 简化的相邻性检查：边界相接或重叠
        Q1_min, Q1_max = self.Q_bounds
        H1_min, H1_max = self.H_bounds
        Q2_min, Q2_max = other.Q_bounds
        H2_min, H2_max = other.H_bounds
        
        # 检查是否在Q或H方向上相邻
        Q_adjacent = (abs(Q1_max - Q2_min) < 1e-6 or abs(Q2_max - Q1_min) < 1e-6)
        H_adjacent = (abs(H1_max - H2_min) < 1e-6 or abs(H2_max - H1_min) < 1e-6)
        
        # 检查是否在另一个维度上有重叠
        Q_overlap = not (Q1_max < Q2_min or Q2_max < Q1_min)
        H_overlap = not (H1_max < H2_min or H2_max < H1_min)
        
        return (Q_adjacent and H_overlap) or (H_adjacent and Q_overlap)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'interval_id': self.interval_id,
            'Q_bounds': self.Q_bounds,
            'H_bounds': self.H_bounds,
            'equilibrium_point': self.equilibrium_point,
            'error_metrics': self.error_metrics,
            'quality_score': self.quality_score,
            'neighboring_intervals': self.neighboring_intervals,
            'creation_time': self.creation_time,
            'last_updated': self.last_updated,
            'validation_status': self.validation_status,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FlowStageInterval':
        """从字典创建实例"""
        # 移除不需要的字段
        data_copy = deepcopy(data)
        if 'idz_model' in data_copy:
            del data_copy['idz_model']  # 模型实例不能直接序列化
        
        return cls(**data_copy)


@dataclass
class OptimizationResults:
    """
    区间优化结果数据结构
    
    记录整个区间优化过程的结果和统计信息。
    
    Attributes:
        total_intervals (int): 总区间数量
        grid_structure (Dict[str, Any]): 网格结构描述
        optimization_time (float): 优化总耗时（秒）
        accuracy_statistics (Dict[str, float]): 精度统计信息
        parameter_distribution (Dict[str, Any]): 参数分布分析
        performance_benchmarks (Dict[str, float]): 性能基准测试
        convergence_history (List[Dict]): 收敛历史记录
        success_rate (float): 成功率
        failed_intervals (List[str]): 失败区间ID列表
        quality_distribution (Dict[str, float]): 质量分布统计
    """
    
    total_intervals: int
    grid_structure: Dict[str, Any] = field(default_factory=dict)
    optimization_time: float = 0.0
    accuracy_statistics: Dict[str, float] = field(default_factory=dict)
    parameter_distribution: Dict[str, Any] = field(default_factory=dict)
    performance_benchmarks: Dict[str, float] = field(default_factory=dict)
    convergence_history: List[Dict] = field(default_factory=list)
    success_rate: float = 0.0
    failed_intervals: List[str] = field(default_factory=list)
    quality_distribution: Dict[str, float] = field(default_factory=dict)
    
    def compute_statistics(self, intervals: List[FlowStageInterval]):
        """基于区间列表计算统计信息"""
        if not intervals:
            return
        
        # 精度统计
        quality_scores = [interval.quality_score for interval in intervals]
        error_values = []
        for interval in intervals:
            if 'max_error' in interval.error_metrics:
                error_values.append(interval.error_metrics['max_error'])
        
        self.accuracy_statistics = {
            'mean_quality_score': np.mean(quality_scores),
            'median_quality_score': np.median(quality_scores),
            'std_quality_score': np.std(quality_scores),
            'min_quality_score': np.min(quality_scores),
            'max_quality_score': np.max(quality_scores)
        }
        
        if error_values:
            self.accuracy_statistics.update({
                'mean_error': np.mean(error_values),
                'median_error': np.median(error_values),
                'max_error': np.max(error_values),
                'error_percentile_95': np.percentile(error_values, 95)
            })
        
        # 成功率统计
        valid_intervals = [i for i in intervals if i.validation_status == 'valid']
        self.success_rate = len(valid_intervals) / len(intervals)
        self.failed_intervals = [i.interval_id for i in intervals 
                               if i.validation_status in ['invalid', 'expired']]
        
        # 质量分布
        high_quality = len([s for s in quality_scores if s >= 0.8])
        medium_quality = len([s for s in quality_scores if 0.5 <= s < 0.8])
        low_quality = len([s for s in quality_scores if s < 0.5])
        
        total = len(intervals)
        self.quality_distribution = {
            'high_quality_rate': high_quality / total,
            'medium_quality_rate': medium_quality / total,
            'low_quality_rate': low_quality / total
        }
    
    def to_report(self) -> str:
        """生成文本报告"""
        report = f"""
=== 流量水位区间优化结果报告 ===

总体统计:
- 区间总数: {self.total_intervals}
- 优化耗时: {self.optimization_time:.2f} 秒
- 成功率: {self.success_rate:.1%}

精度统计:
- 平均质量评分: {self.accuracy_statistics.get('mean_quality_score', 0):.3f}
- 最大误差: {self.accuracy_statistics.get('max_error', 0):.1%}
- 95%分位误差: {self.accuracy_statistics.get('error_percentile_95', 0):.1%}

质量分布:
- 高质量区间(≥0.8): {self.quality_distribution.get('high_quality_rate', 0):.1%}
- 中等质量区间(0.5-0.8): {self.quality_distribution.get('medium_quality_rate', 0):.1%}
- 低质量区间(<0.5): {self.quality_distribution.get('low_quality_rate', 0):.1%}

失败区间数: {len(self.failed_intervals)}
        """
        return report


@dataclass 
class IDZModelParameters:
    """
    四方程IDZ模型参数结构
    
    存储四个传递函数G11, G12, G21, G22的所有参数。
    
    Attributes:
        各传递函数的参数：
        - tau: 零点时间常数（秒）
        - T: 延迟时间（秒）
        - alpha: 极点时间常数（秒）
    """
    
    # G11: 上游输入 → 上游输出 (本地响应)
    tau11: float = 120.0
    T11: float = 0.0
    alpha11: float = 300.0
    
    # G12: 下游输入 → 上游输出 (回水效应)
    tau12: float = 60.0
    T12: float = 600.0
    alpha12: float = 250.0
    
    # G21: 上游输入 → 下游输出 (正向传播)
    tau21: float = 200.0
    T21: float = 1200.0
    alpha21: float = 400.0
    
    # G22: 下游输入 → 下游输出 (本地响应)
    tau22: float = 100.0
    T22: float = 0.0
    alpha22: float = 280.0
    
    def __post_init__(self):
        """参数验证"""
        self._validate_parameters()
    
    def _validate_parameters(self):
        """验证参数的物理合理性"""
        # 检查所有时间常数为正
        time_constants = [self.tau11, self.tau12, self.tau21, self.tau22,
                         self.alpha11, self.alpha12, self.alpha21, self.alpha22]
        if any(tc <= 0 for tc in time_constants):
            raise ValueError("所有时间常数必须为正值")
        
        # 检查延迟时间非负
        delays = [self.T11, self.T12, self.T21, self.T22]
        if any(T < 0 for T in delays):
            raise ValueError("所有延迟时间必须非负")
        
        # 检查本地响应无延迟的约束
        if self.T11 != 0.0:
            warnings.warn("G11本地响应建议无延迟 (T11=0)")
        if self.T22 != 0.0:
            warnings.warn("G22本地响应建议无延迟 (T22=0)")
        
        # 检查传播延迟的合理性
        if self.T21 <= self.T12:
            warnings.warn("正向传播延迟T21通常应大于回水延迟T12")
    
    def to_dict(self) -> Dict[str, float]:
        """转换为字典格式"""
        return {
            'tau11': self.tau11, 'T11': self.T11, 'alpha11': self.alpha11,
            'tau12': self.tau12, 'T12': self.T12, 'alpha12': self.alpha12,
            'tau21': self.tau21, 'T21': self.T21, 'alpha21': self.alpha21,
            'tau22': self.tau22, 'T22': self.T22, 'alpha22': self.alpha22
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> 'IDZModelParameters':
        """从字典创建实例"""
        return cls(**data)
    
    def get_transfer_function_params(self, tf_name: str) -> Tuple[float, float, float]:
        """
        获取指定传递函数的参数
        
        Args:
            tf_name (str): 传递函数名称 ('G11', 'G12', 'G21', 'G22')
            
        Returns:
            Tuple[float, float, float]: (tau, T, alpha)
        """
        param_map = {
            'G11': (self.tau11, self.T11, self.alpha11),
            'G12': (self.tau12, self.T12, self.alpha12),
            'G21': (self.tau21, self.T21, self.alpha21),
            'G22': (self.tau22, self.T22, self.alpha22)
        }
        
        if tf_name not in param_map:
            raise ValueError(f"未知的传递函数名称: {tf_name}")
        
        return param_map[tf_name]


class IntervalDatabase:
    """
    区间数据库管理器
    
    负责区间的存储、检索、更新和持久化。
    支持空间索引和快速查询。
    """
    
    def __init__(self):
        self.intervals: Dict[str, FlowStageInterval] = {}
        self.spatial_index: Optional[Any] = None  # 可扩展为R-tree等空间索引
        self.logger = logging.getLogger("IntervalDatabase")
    
    def add_interval(self, interval: FlowStageInterval):
        """添加区间到数据库"""
        self.intervals[interval.interval_id] = interval
        self._update_spatial_index()
        self.logger.debug(f"添加区间: {interval.interval_id}")
    
    def get_interval(self, interval_id: str) -> Optional[FlowStageInterval]:
        """根据ID获取区间"""
        return self.intervals.get(interval_id)
    
    def remove_interval(self, interval_id: str) -> bool:
        """移除区间"""
        if interval_id in self.intervals:
            del self.intervals[interval_id]
            self._update_spatial_index()
            self.logger.debug(f"移除区间: {interval_id}")
            return True
        return False
    
    def find_containing_interval(self, Q: float, H: float) -> Optional[FlowStageInterval]:
        """查找包含给定(Q, H)点的区间"""
        for interval in self.intervals.values():
            if interval.contains_point(Q, H):
                return interval
        return None
    
    def find_neighboring_intervals(self, interval_id: str) -> List[FlowStageInterval]:
        """查找相邻区间"""
        target_interval = self.intervals.get(interval_id)
        if not target_interval:
            return []
        
        neighbors = []
        for interval in self.intervals.values():
            if interval.interval_id != interval_id and target_interval.is_neighbor(interval):
                neighbors.append(interval)
        
        return neighbors
    
    def get_all_intervals(self) -> List[FlowStageInterval]:
        """获取所有区间"""
        return list(self.intervals.values())
    
    def get_valid_intervals(self) -> List[FlowStageInterval]:
        """获取所有有效区间"""
        return [interval for interval in self.intervals.values() 
                if interval.validation_status == 'valid']
    
    def update_neighbors(self):
        """更新所有区间的邻居关系"""
        for interval in self.intervals.values():
            neighbors = self.find_neighboring_intervals(interval.interval_id)
            interval.neighboring_intervals = [n.interval_id for n in neighbors]
    
    def _update_spatial_index(self):
        """更新空间索引（预留接口）"""
        # 这里可以集成R-tree或其他空间索引结构
        pass
    
    def save_to_file(self, filepath: str):
        """保存数据库到文件"""
        data = {
            'intervals': {id: interval.to_dict() for id, interval in self.intervals.items()},
            'metadata': {
                'total_intervals': len(self.intervals),
                'creation_time': time.time()
            }
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"数据库已保存到: {filepath}")
    
    def load_from_file(self, filepath: str):
        """从文件加载数据库"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.intervals.clear()
            for interval_id, interval_data in data['intervals'].items():
                interval = FlowStageInterval.from_dict(interval_data)
                self.intervals[interval_id] = interval
            
            self._update_spatial_index()
            self.logger.info(f"从文件加载了 {len(self.intervals)} 个区间: {filepath}")
            
        except Exception as e:
            self.logger.error(f"加载数据库文件失败: {e}")
            raise
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        if not self.intervals:
            return {}
        
        intervals = list(self.intervals.values())
        quality_scores = [i.quality_score for i in intervals]
        
        # 计算边界范围
        Q_bounds = []
        H_bounds = []
        for interval in intervals:
            Q_bounds.extend(interval.Q_bounds)
            H_bounds.extend(interval.H_bounds)
        
        return {
            'total_intervals': len(intervals),
            'quality_stats': {
                'mean': np.mean(quality_scores),
                'std': np.std(quality_scores),
                'min': np.min(quality_scores),
                'max': np.max(quality_scores)
            },
            'spatial_coverage': {
                'Q_range': [np.min(Q_bounds), np.max(Q_bounds)],
                'H_range': [np.min(H_bounds), np.max(H_bounds)]
            },
            'validation_status': {
                'valid': len([i for i in intervals if i.validation_status == 'valid']),
                'invalid': len([i for i in intervals if i.validation_status == 'invalid']),
                'pending': len([i for i in intervals if i.validation_status == 'pending'])
            }
        }


# 导出主要类
__all__ = [
    'FlowStageInterval',
    'OptimizationResults', 
    'IDZModelParameters',
    'IntervalDatabase'
]