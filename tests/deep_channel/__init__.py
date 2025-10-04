"""
明渠模型深度测试案例框架

本模块提供全面的明渠模型验证测试框架，包括：
- 5断面非恒定流基础验证
- 降阶模型参数辨识验证  
- 同步孪生功能验证
- 糙率在线辨识验证
- 多模型在线辨识对比

框架组件：
- test_framework: 测试框架控制器
- geometry_config: 5断面河道几何配置
- numerical_solvers: 数值求解器增强
- model_identification: 参数辨识算法
- twin_coordination: 孪生协调器
- validation_tools: 验证分析工具
- visualization: 可视化和报告
"""

__version__ = "1.0.0"
__author__ = "WaterNet Development Team"

from .test_framework import DeepChannelTestFramework
from .geometry_config import FiveSectionChannelConfig
from .validation_tools import ValidationAnalyzer, PerformanceEvaluator
from .visualization import TestResultsVisualizer

__all__ = [
    'DeepChannelTestFramework',
    'FiveSectionChannelConfig', 
    'ValidationAnalyzer',
    'PerformanceEvaluator',
    'TestResultsVisualizer'
]