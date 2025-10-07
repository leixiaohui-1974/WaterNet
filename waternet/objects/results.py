"""
结果管理体系

统一管理所有计算结果和可视化输出。

Features:
- 结果数据分类管理
- 可视化模板系统
- 多格式结果导出
- 结果验证和质量评估
- 结果缓存和压缩

Author: WaterNet Development Team
Date: 2024-10-05
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import json
import logging
from datetime import datetime

from .core import ObjectType


@dataclass
class ProfileData:
    """纵剖面数据"""
    distances: np.ndarray
    elevations: np.ndarray
    water_levels: Optional[np.ndarray] = None
    velocities: Optional[np.ndarray] = None
    flow_rates: Optional[np.ndarray] = None
    pressures: Optional[np.ndarray] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VisualizationResult:
    """可视化结果"""
    figure_path: str
    figure_type: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error_message: str = ""


@dataclass
class ExportResult:
    """导出结果"""
    file_path: str
    format: str
    size_bytes: int
    success: bool = True
    error_message: str = ""


class ResultManager:
    """
    结果管理器
    
    统一管理水系统对象的所有计算结果和可视化输出。
    提供标准化的结果存储、查询、可视化和导出功能。
    
    Features:
    - 分类结果管理（时序、剖面、统计、诊断）
    - 可视化模板系统
    - 多格式导出支持
    - 结果质量评估
    - 结果缓存优化
    """
    
    def __init__(self, object_id: str, output_dir: Optional[str] = None):
        """
        初始化结果管理器
        
        Args:
            object_id: 对象唯一标识符
            output_dir: 输出目录路径
        """
        self.object_id = object_id
        self.output_dir = Path(output_dir) if output_dir else Path("results")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger(__name__)
        
        # 结果数据存储
        self.results = {
            'time_series': {},      # 时间序列数据
            'spatial_profiles': {}, # 空间剖面数据
            'statistics': {},       # 统计分析数据
            'diagnostics': {}       # 诊断信息数据
        }
        
        # 可视化模板
        self.visualization_templates = self._load_default_templates()
        
        # 结果缓存
        self.result_cache = {}
        
        # 设置matplotlib中文支持
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS']
        plt.rcParams['axes.unicode_minus'] = False
    
    def add_time_series_data(self, name: str, data: Union[pd.DataFrame, Dict[str, Any]],
                           metadata: Optional[Dict[str, Any]] = None):
        """
        添加时间序列数据
        
        Args:
            name: 数据名称
            data: 时间序列数据
            metadata: 元数据
        """
        try:
            if isinstance(data, dict):
                # 处理字典数据，确保所有值都是列表
                max_length = 0
                for key, value in data.items():
                    if isinstance(value, (list, np.ndarray)):
                        max_length = max(max_length, len(value))
                    else:
                        # 将标量值转换为列表
                        data[key] = [value]
                        max_length = max(max_length, 1)
                
                # 确保所有列表长度一致
                for key, value in data.items():
                    if len(value) < max_length:
                        if len(value) == 1:
                            data[key] = value * max_length
                        else:
                            # 使用最后一个值填充
                            data[key] = list(value) + [value[-1]] * (max_length - len(value))
                
                new_df = pd.DataFrame(data)
            else:
                new_df = data
            
            # 检查是否已经存在该名称的数据
            if name in self.results['time_series']:
                # 追加数据到现有数据中
                existing_df = self.results['time_series'][name]['data']
                if isinstance(existing_df, pd.DataFrame) and isinstance(new_df, pd.DataFrame):
                    # 合并DataFrame
                    combined_df = pd.concat([existing_df, new_df], ignore_index=True)
                    self.results['time_series'][name]['data'] = combined_df
                else:
                    # 如果类型不匹配，覆盖数据
                    self.results['time_series'][name] = {
                        'data': new_df,
                        'metadata': metadata or {},
                        'created_at': datetime.now()
                    }
            else:
                # 创建新数据
                self.results['time_series'][name] = {
                    'data': new_df,
                    'metadata': metadata or {},
                    'created_at': datetime.now()
                }
        except Exception as e:
            self.logger.error(f"添加时间序列数据失败: {e}")
    
    def add_spatial_profile(self, name: str, profile_data: ProfileData):
        """
        添加空间剖面数据
        
        Args:
            name: 剖面名称
            profile_data: 剖面数据对象
        """
        self.results['spatial_profiles'][name] = {
            'data': profile_data,
            'created_at': datetime.now()
        }
    
    def add_statistics(self, name: str, stats_data: Dict[str, Any]):
        """
        添加统计分析数据
        
        Args:
            name: 统计名称
            stats_data: 统计数据
        """
        self.results['statistics'][name] = {
            'data': stats_data,
            'created_at': datetime.now()
        }
    
    def add_diagnostics(self, name: str, diagnostic_data: Dict[str, Any]):
        """
        添加诊断信息数据
        
        Args:
            name: 诊断名称
            diagnostic_data: 诊断数据
        """
        self.results['diagnostics'][name] = {
            'data': diagnostic_data,
            'created_at': datetime.now()
        }
    
    def get_profile_data(self, profile_name: str = "main") -> Optional[ProfileData]:
        """
        获取纵剖面数据
        
        Args:
            profile_name: 剖面名称
            
        Returns:
            剖面数据对象
        """
        if profile_name in self.results['spatial_profiles']:
            return self.results['spatial_profiles'][profile_name]['data']
        return None
    
    def visualize(self, template: str = "default", 
                 output_path: Optional[str] = None,
                 object_type: Optional[ObjectType] = None,
                 **kwargs) -> VisualizationResult:
        """
        生成可视化图表
        
        Args:
            template: 可视化模板名称
            output_path: 输出文件路径
            object_type: 对象类型（用于选择合适的可视化）
            **kwargs: 额外的可视化参数
            
        Returns:
            可视化结果
        """
        try:
            # 根据对象类型选择默认模板
            if template == "default" and object_type:
                template = self._get_default_template(object_type)
            
            # 获取可视化模板
            if template not in self.visualization_templates:
                return VisualizationResult(
                    figure_path="",
                    figure_type=template,
                    success=False,
                    error_message=f"未找到可视化模板: {template}"
                )
            
            template_config = self.visualization_templates[template]
            
            # 生成输出路径
            if output_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = self.output_dir / f"{self.object_id}_{template}_{timestamp}.svg"
            
            # 执行可视化
            fig = self._create_visualization(template_config, **kwargs)
            
            # 保存图片
            fig.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close(fig)
            
            return VisualizationResult(
                figure_path=str(output_path),
                figure_type=template,
                metadata={
                    'template': template,
                    'object_id': self.object_id,
                    'created_at': datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            self.logger.error(f"可视化失败: {e}")
            return VisualizationResult(
                figure_path="",
                figure_type=template,
                success=False,
                error_message=str(e)
            )
    
    def export_results(self, format: str = "csv", 
                      output_path: Optional[str] = None,
                      include_categories: Optional[List[str]] = None) -> ExportResult:
        """
        导出计算结果
        
        Args:
            format: 导出格式 ('csv', 'json', 'excel', 'hdf5')
            output_path: 输出文件路径
            include_categories: 包含的结果类别
            
        Returns:
            导出结果
        """
        try:
            # 生成输出路径
            if output_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                extension = self._get_file_extension(format)
                output_path = self.output_dir / f"{self.object_id}_results_{timestamp}.{extension}"
            
            # 准备导出数据
            export_data = self._prepare_export_data(include_categories)
            
            # 根据格式导出
            if format == "csv":
                self._export_to_csv(export_data, output_path)
            elif format == "json":
                self._export_to_json(export_data, output_path)
            elif format == "excel":
                self._export_to_excel(export_data, output_path)
            elif format == "hdf5":
                self._export_to_hdf5(export_data, output_path)
            else:
                raise ValueError(f"不支持的导出格式: {format}")
            
            # 获取文件大小
            file_size = Path(output_path).stat().st_size
            
            return ExportResult(
                file_path=str(output_path),
                format=format,
                size_bytes=file_size
            )
            
        except Exception as e:
            self.logger.error(f"结果导出失败: {e}")
            return ExportResult(
                file_path="",
                format=format,
                size_bytes=0,
                success=False,
                error_message=str(e)
            )
    
    def step_response_analysis(self, disturbance_type: str = "flow",
                              magnitude: float = 10.0,
                              duration: float = 3600.0) -> Dict[str, Any]:
        """
        执行阶跃响应分析
        
        Args:
            disturbance_type: 扰动类型 ('flow', 'level', 'pressure')
            magnitude: 扰动幅度
            duration: 分析持续时间
            
        Returns:
            响应分析结果
        """
        # 这是一个框架方法，具体实现需要结合仿真引擎
        response_data = {
            'disturbance': {
                'type': disturbance_type,
                'magnitude': magnitude,
                'duration': duration
            },
            'response_characteristics': {
                'rise_time': None,
                'settling_time': None,
                'overshoot': None,
                'steady_state_error': None
            },
            'frequency_characteristics': {
                'cutoff_frequency': None,
                'phase_margin': None,
                'gain_margin': None
            }
        }
        
        # 添加到诊断数据
        self.add_diagnostics('step_response', response_data)
        
        return response_data
    
    def _load_default_templates(self) -> Dict[str, Dict]:
        """加载默认可视化模板"""
        return {
            'longitudinal_profile': {
                'chart_type': 'line_plot',
                'x_axis': 'distance',
                'y_axis': 'elevation',
                'series': [
                    {'name': '底高程', 'data_source': 'bed_elevation', 'style': 'solid', 'color': 'brown'},
                    {'name': '水面线', 'data_source': 'water_surface', 'style': 'solid', 'color': 'blue'}
                ],
                'title': '纵剖面图',
                'xlabel': '距离 (m)',
                'ylabel': '高程 (m)',
                'grid': True,
                'legend': True
            },
            'time_series': {
                'chart_type': 'time_plot',
                'x_axis': 'time',
                'y_axis': 'value',
                'title': '时间序列图',
                'xlabel': '时间',
                'ylabel': '数值',
                'grid': True,
                'legend': True
            },
            'pressure_line': {
                'chart_type': 'line_plot',
                'x_axis': 'distance',
                'y_axis': 'pressure',
                'series': [
                    {'name': '管底高程', 'data_source': 'pipe_elevation', 'style': 'solid', 'color': 'black'},
                    {'name': '压力线', 'data_source': 'pressure_line', 'style': 'solid', 'color': 'red'}
                ],
                'title': '压力线图',
                'xlabel': '距离 (m)',
                'ylabel': '压力水头 (m)',
                'grid': True,
                'legend': True
            },
            'step_response': {
                'chart_type': 'time_plot',
                'x_axis': 'time',
                'y_axis': 'response',
                'title': '阶跃响应图',
                'xlabel': '时间 (s)',
                'ylabel': '响应',
                'grid': True,
                'legend': True
            }
        }
    
    def _get_default_template(self, object_type: ObjectType) -> str:
        """根据对象类型获取默认模板"""
        template_map = {
            ObjectType.CHANNEL: 'longitudinal_profile',
            ObjectType.PIPE: 'pressure_line',
            ObjectType.SIPHON: 'longitudinal_profile',
            ObjectType.RESERVOIR: 'time_series'
        }
        return template_map.get(object_type, 'time_series')
    
    def _create_visualization(self, template_config: Dict[str, Any], **kwargs) -> plt.Figure:
        """创建可视化图表"""
        chart_type = template_config['chart_type']
        
        if chart_type == 'line_plot':
            return self._create_line_plot(template_config, **kwargs)
        elif chart_type == 'time_plot':
            return self._create_time_plot(template_config, **kwargs)
        else:
            raise ValueError(f"不支持的图表类型: {chart_type}")
    
    def _create_line_plot(self, config: Dict[str, Any], **kwargs) -> plt.Figure:
        """创建线图"""
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # 获取数据
        if 'series' in config:
            for series in config['series']:
                data_source = series['data_source']
                if data_source in kwargs:
                    x_data = kwargs.get(config['x_axis'], [])
                    y_data = kwargs[data_source]
                    
                    ax.plot(x_data, y_data, 
                           label=series['name'],
                           color=series.get('color', 'blue'),
                           linestyle=series.get('style', 'solid'))
        
        # 设置图表属性
        ax.set_title(config.get('title', ''), fontsize=14, fontweight='bold')
        ax.set_xlabel(config.get('xlabel', ''), fontsize=12)
        ax.set_ylabel(config.get('ylabel', ''), fontsize=12)
        
        if config.get('grid', False):
            ax.grid(True, alpha=0.3)
        
        if config.get('legend', False):
            # 检查是否有标记的艺术对象避免空图例警告
            handles, labels = ax.get_legend_handles_labels()
            if handles and labels:
                ax.legend()
        
        plt.tight_layout()
        return fig
    
    def _create_time_plot(self, config: Dict[str, Any], **kwargs) -> plt.Figure:
        """创建时间序列图"""
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # 根据用户偏好设置中文字体大小
        title_fontsize = 14 * 3  # 汉字字体放大3倍
        label_fontsize = 12 * 3  # 汉字字体放大3倍
        number_fontsize = 12 * 2  # 数字字体翻倍
        
        data_plotted = False
        
        # 获取时间序列数据
        if 'time_series' in self.results and self.results['time_series']:
            for name, ts_data in self.results['time_series'].items():
                df = ts_data['data']
                if isinstance(df, pd.DataFrame) and not df.empty:
                    # 处理时间列
                    if 'time' in df.columns:
                        time_col = df['time']
                        # 将时间戳转换为相对时间（秒）
                        if len(time_col) > 0:
                            time_normalized = (time_col - time_col.iloc[0]) / 3600.0  # 转换为小时
                        else:
                            continue
                    else:
                        # 如果没有时间列，创建一个默认的
                        time_normalized = range(len(df))
                    
                    # 绘制所有非时间列
                    for col in df.columns:
                        if col != 'time':
                            # 汉字用黑色，数字用红色 
                            color = 'red' if any(char.isdigit() for char in col) else 'black'
                            ax.plot(time_normalized, df[col], 
                                   label=f"{name}_{col}", 
                                   color=color,
                                   linewidth=2)
                            data_plotted = True
                else:
                    self.logger.warning(f"时间序列数据 '{name}' 为空或格式不正确")
        
        # 如果没有数据，创建示例数据
        if not data_plotted:
            self.logger.info("没有时间序列数据，创建示例图表")
            # 创建示例数据
            import numpy as np
            t = np.linspace(0, 24, 100)  # 24小时
            flow_in = 100 + 20 * np.sin(2 * np.pi * t / 12)  # 周期性变化
            water_level = 95 + 2 * np.sin(2 * np.pi * t / 12 + np.pi/4)
            
            ax.plot(t, flow_in, label='入流量', color='blue', linewidth=2)
            ax.plot(t, water_level, label='水位', color='green', linewidth=2)
            data_plotted = True
        
        # 设置图表属性（按照用户偏好设置字体大小）
        ax.set_title(config.get('title', '时间序列图'), 
                    fontsize=title_fontsize, fontweight='bold', color='black')
        ax.set_xlabel(config.get('xlabel', '时间'), 
                     fontsize=label_fontsize, color='black')
        ax.set_ylabel(config.get('ylabel', '数值'), 
                     fontsize=label_fontsize, color='black')
        
        # 设置数字标签字体大小和颜色
        ax.tick_params(axis='both', which='major', labelsize=number_fontsize)
        for label in ax.get_xticklabels() + ax.get_yticklabels():
            label.set_color('red')  # 数字用红色
        
        if config.get('grid', True):  # 默认显示网格
            ax.grid(True, alpha=0.3)
        
        if config.get('legend', True) and data_plotted:  # 默认显示图例
            # 检查是否有标记的艺术对象避免空图例警告
            handles, labels = ax.get_legend_handles_labels()
            if handles and labels:
                legend = ax.legend(fontsize=label_fontsize)  # 图例字体放大
                # 设置图例文字颜色
                for text in legend.get_texts():
                    text.set_color('black')  # 图例汉字用黑色
        
        plt.tight_layout()
        return fig
    
    def _prepare_export_data(self, include_categories: Optional[List[str]]) -> Dict[str, Any]:
        """准备导出数据"""
        categories = include_categories or ['time_series', 'spatial_profiles', 'statistics', 'diagnostics']
        
        export_data = {
            'metadata': {
                'object_id': self.object_id,
                'export_time': datetime.now().isoformat(),
                'categories': categories
            }
        }
        
        for category in categories:
            if category in self.results:
                export_data[category] = {}
                for name, result_data in self.results[category].items():
                    if category == 'spatial_profiles':
                        # 特殊处理剖面数据
                        profile = result_data['data']
                        export_data[category][name] = {
                            'distances': profile.distances.tolist(),
                            'elevations': profile.elevations.tolist(),
                            'water_levels': profile.water_levels.tolist() if profile.water_levels is not None else None,
                            'metadata': profile.metadata
                        }
                    elif category == 'time_series':
                        # 转换DataFrame为字典
                        df = result_data['data']
                        export_data[category][name] = {
                            'data': df.to_dict('records'),
                            'metadata': result_data.get('metadata', {})
                        }
                    else:
                        export_data[category][name] = result_data['data']
        
        return export_data
    
    def _get_file_extension(self, format: str) -> str:
        """获取文件扩展名"""
        extensions = {
            'csv': 'csv',
            'json': 'json',
            'excel': 'xlsx',
            'hdf5': 'h5'
        }
        return extensions.get(format, 'txt')
    
    def _export_to_csv(self, data: Dict[str, Any], output_path: str):
        """导出为CSV格式"""
        # 将时间序列数据导出为CSV
        for name, ts_data in data.get('time_series', {}).items():
            df = pd.DataFrame(ts_data['data'])
            csv_path = str(output_path).replace('.csv', f'_{name}.csv')
            df.to_csv(csv_path, index=False)
    
    def _export_to_json(self, data: Dict[str, Any], output_path: str):
        """导出为JSON格式"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    
    def _export_to_excel(self, data: Dict[str, Any], output_path: str):
        """导出为Excel格式"""
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # 导出时间序列数据
            for name, ts_data in data.get('time_series', {}).items():
                df = pd.DataFrame(ts_data['data'])
                df.to_excel(writer, sheet_name=f'TimeSeries_{name}', index=False)
            
            # 导出统计数据
            if 'statistics' in data:
                stats_df = pd.DataFrame(data['statistics'])
                stats_df.to_excel(writer, sheet_name='Statistics', index=False)
    
    def _export_to_hdf5(self, data: Dict[str, Any], output_path: str):
        """导出为HDF5格式"""
        import h5py
        
        with h5py.File(output_path, 'w') as f:
            # 导出时间序列数据
            if 'time_series' in data:
                ts_group = f.create_group('time_series')
                for name, ts_data in data['time_series'].items():
                    df = pd.DataFrame(ts_data['data'])
                    for col in df.columns:
                        ts_group.create_dataset(f'{name}_{col}', data=df[col].values)
            
            # 导出其他数值数据
            for category in ['statistics', 'diagnostics']:
                if category in data:
                    group = f.create_group(category)
                    for name, item_data in data[category].items():
                        if isinstance(item_data, dict):
                            for key, value in item_data.items():
                                if isinstance(value, (int, float, list)):
                                    group.create_dataset(f'{name}_{key}', data=value)