"""
集成接口 - 与现有WaterNet组件的集成

提供与现有WaterNet组件的集成接口，包括5断面配置、圣维南模型等的无缝集成。

Author: WaterNet Development Team
Date: 2024-10-04
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Union
import logging
from dataclasses import dataclass
import warnings

from .flow_stage_interval_optimizer import FlowStageIntervalOptimizer, OptimizerConfig
from .flow_stage_interval_system import FlowStageInterval
from .saint_venant import SaintVenantModel


@dataclass
class FiveSectionConfig:
    """五断面明渠配置"""
    channel_length: float = 2000.0          # 渠道总长度 (m)
    channel_width: float = 80.0             # 渠道宽度 (m)
    channel_slope: float = 0.0008           # 渠道坡度
    manning_roughness: float = 0.025        # 曼宁糙率系数
    section_spacing: float = 500.0          # 断面间距 (m)
    
    # 运行范围
    Q_range: Tuple[float, float] = (20.0, 120.0)    # 流量范围 (m³/s)
    H_range: Tuple[float, float] = (100.0, 102.5)   # 水位范围 (m)
    
    # 几何参数
    bottom_elevation: float = 100.0         # 底高程 (m)
    side_slope: float = 0.0                 # 边坡（0表示矩形）


class FlowStageSystemIntegrator:
    """
    流量水位系统集成器
    
    负责将流量水位区间优化系统与现有WaterNet组件集成。
    """
    
    def __init__(self):
        self.logger = logging.getLogger("FlowStageSystemIntegrator")
        self.five_section_config: Optional[FiveSectionConfig] = None
        self.saint_venant_model: Optional[SaintVenantModel] = None
        self.interval_optimizer: Optional[FlowStageIntervalOptimizer] = None
    
    def setup_five_section_channel(self, config: FiveSectionConfig) -> SaintVenantModel:
        """
        设置五断面明渠模型
        
        Args:
            config: 五断面配置
            
        Returns:
            SaintVenantModel: 配置好的圣维南模型
        """
        self.five_section_config = config
        
        # 创建断面几何数据
        sections = self._create_five_section_geometry(config)
        
        # 创建圣维南模型
        self.saint_venant_model = SaintVenantModel(
            name="FiveSectionChannel",
            upstream_node="inlet",
            downstream_node="outlet", 
            sections=sections
        )
        
        self.logger.info(f"五断面明渠模型已设置，长度: {config.channel_length}m")
        
        return self.saint_venant_model
    
    def _create_five_section_geometry(self, config: FiveSectionConfig) -> List[Dict[str, Any]]:
        """创建五断面几何数据"""
        sections = []
        
        for i in range(5):
            # 计算里程
            mileage = i * config.section_spacing
            
            # 计算底高程（考虑坡度）
            elevation = config.bottom_elevation - mileage * config.channel_slope
            
            # 创建断面几何函数
            def create_area_func(width=config.channel_width, elev=elevation):
                def area_func(H):
                    if H <= elev:
                        return 0.0
                    depth = H - elev
                    return width * depth
                return area_func
            
            def create_top_width_func(width=config.channel_width):
                def top_width_func(H):
                    return width
                return top_width_func
            
            section = {
                'mileage': mileage,
                'elevation': elevation,
                'roughness': config.manning_roughness,
                'area_func': create_area_func(),
                'top_width_func': create_top_width_func()
            }
            
            sections.append(section)
        
        return sections
    
    def create_interval_optimizer(self, optimizer_config: Optional[OptimizerConfig] = None) -> FlowStageIntervalOptimizer:
        """
        创建区间优化器
        
        Args:
            optimizer_config: 优化器配置
            
        Returns:
            FlowStageIntervalOptimizer: 优化器实例
        """
        if optimizer_config is None:
            optimizer_config = OptimizerConfig()
        
        self.interval_optimizer = FlowStageIntervalOptimizer(optimizer_config)
        
        self.logger.info("区间优化器已创建")
        
        return self.interval_optimizer
    
    def setup_integrated_system(self, channel_config: FiveSectionConfig,
                               optimizer_config: Optional[OptimizerConfig] = None) -> Tuple[SaintVenantModel, FlowStageIntervalOptimizer]:
        """
        设置集成系统
        
        Args:
            channel_config: 渠道配置
            optimizer_config: 优化器配置
            
        Returns:
            Tuple: (圣维南模型, 区间优化器)
        """
        # 设置圣维南模型
        saint_venant = self.setup_five_section_channel(channel_config)
        
        # 创建区间优化器
        optimizer = self.create_interval_optimizer(optimizer_config)
        
        # 初始化区间
        Q_range = channel_config.Q_range
        H_range = channel_config.H_range
        
        optimizer.initialize_intervals(Q_range, H_range)
        
        self.logger.info("集成系统设置完成")
        
        return saint_venant, optimizer
    
    def run_optimization_workflow(self, max_error_threshold: float = 0.20) -> Dict[str, Any]:
        """
        运行完整的优化工作流
        
        Args:
            max_error_threshold: 最大误差阈值
            
        Returns:
            Dict: 优化结果摘要
        """
        if not self.saint_venant_model or not self.interval_optimizer:
            raise ValueError("系统未完全设置，请先调用setup_integrated_system")
        
        self.logger.info("开始运行优化工作流")
        
        # 执行优化
        optimization_results = self.interval_optimizer.optimize_intervals(
            self.saint_venant_model, max_error_threshold)
        
        # 生成结果摘要
        results_summary = {
            'optimization_success': optimization_results.success_rate > 0.8,
            'total_intervals': optimization_results.total_intervals,
            'optimization_time': optimization_results.optimization_time,
            'max_error': optimization_results.accuracy_statistics.get('max_error', 1.0),
            'success_rate': optimization_results.success_rate,
            'quality_distribution': optimization_results.quality_distribution,
            'performance_benchmarks': optimization_results.performance_benchmarks
        }
        
        self.logger.info(f"优化工作流完成，成功率: {results_summary['success_rate']:.1%}")
        
        return results_summary
    
    def demonstrate_system_capabilities(self) -> Dict[str, Any]:
        """
        演示系统功能
        
        Returns:
            Dict: 演示结果
        """
        # 使用默认配置设置系统
        default_config = FiveSectionConfig()
        saint_venant, optimizer = self.setup_integrated_system(default_config)
        
        # 运行优化
        optimization_summary = self.run_optimization_workflow()
        
        # 测试区间管理功能
        manager = optimizer.manager
        test_points = [
            (50.0, 101.0), (75.0, 101.5), (100.0, 102.0)
        ]
        
        interval_selections = []
        for Q, H in test_points:
            interval = manager.select_active_interval(Q, H)
            interval_selections.append({
                'point': (Q, H),
                'interval_id': interval.interval_id if interval else None
            })
        
        # 生成演示报告
        demonstration_results = {
            'channel_configuration': {
                'length': default_config.channel_length,
                'width': default_config.channel_width,
                'sections': 5,
                'Q_range': default_config.Q_range,
                'H_range': default_config.H_range
            },
            'optimization_results': optimization_summary,
            'interval_management': {
                'test_points': len(test_points),
                'successful_selections': len([s for s in interval_selections if s['interval_id']]),
                'selection_details': interval_selections
            },
            'system_performance': {
                'memory_usage_mb': optimization_summary['performance_benchmarks']['memory_usage_mb'],
                'processing_speed': optimization_summary['performance_benchmarks']['intervals_per_second']
            }
        }
        
        return demonstration_results


def create_five_section_interval_system(channel_length: float = 2000.0,
                                       channel_width: float = 80.0,
                                       Q_range: Tuple[float, float] = (20.0, 120.0),
                                       H_range: Tuple[float, float] = (100.0, 102.5)) -> FlowStageSystemIntegrator:
    """
    便捷函数：创建五断面区间系统
    
    Args:
        channel_length: 渠道长度
        channel_width: 渠道宽度
        Q_range: 流量范围
        H_range: 水位范围
        
    Returns:
        FlowStageSystemIntegrator: 配置好的集成器
    """
    config = FiveSectionConfig(
        channel_length=channel_length,
        channel_width=channel_width,
        Q_range=Q_range,
        H_range=H_range
    )
    
    integrator = FlowStageSystemIntegrator()
    integrator.setup_integrated_system(config)
    
    return integrator


def integrate_with_saint_venant(saint_venant_model: SaintVenantModel,
                              Q_range: Tuple[float, float],
                              H_range: Tuple[float, float],
                              optimizer_config: Optional[OptimizerConfig] = None) -> FlowStageIntervalOptimizer:
    """
    便捷函数：与现有圣维南模型集成
    
    Args:
        saint_venant_model: 现有的圣维南模型
        Q_range: 流量范围
        H_range: 水位范围
        optimizer_config: 优化器配置
        
    Returns:
        FlowStageIntervalOptimizer: 配置好的优化器
    """
    optimizer = FlowStageIntervalOptimizer(optimizer_config)
    optimizer.initialize_intervals(Q_range, H_range)
    
    return optimizer


def create_demonstration_system() -> Dict[str, Any]:
    """
    便捷函数：创建演示系统
    
    Returns:
        Dict: 演示结果
    """
    integrator = FlowStageSystemIntegrator()
    return integrator.demonstrate_system_capabilities()


# 导出主要接口
__all__ = [
    'FlowStageSystemIntegrator',
    'FiveSectionConfig',
    'create_five_section_interval_system',
    'integrate_with_saint_venant',
    'create_demonstration_system'
]