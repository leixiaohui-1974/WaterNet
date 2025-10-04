"""
StandardFiveSectionConfig 标准五断面配置管理器

统一管理WaterNet项目中的标准五断面配置，消除现有的重复实现，
提供权威的配置源和一致的API接口。

主要功能：
1. 标准五断面几何配置
2. 水力计算函数生成
3. 配置验证和完整性检查
4. 多种配置变体支持
5. 与现有系统的兼容适配

基于项目中现有的三处重复实现进行整合：
- examples/advanced/unsteady_analysis.py 中的 FiveSectionChannelConfig
- tests/deep_channel/geometry_config.py 中的 FiveSectionChannelConfig  
- waternet/models/integration_interface.py 中的相关配置

Author: WaterNet Development Team
Date: 2024-11-05
"""

import numpy as np
import warnings
from typing import Dict, List, Callable, Optional, Any, Union, Tuple
from dataclasses import dataclass
from pathlib import Path
import yaml


@dataclass
class SectionGeometry:
    """断面几何数据类"""
    mileage: float                 # 里程桩号 (m)
    elevation: float               # 底高程 (m)
    bottom_width: float            # 底宽 (m)
    side_slope: float              # 边坡系数
    roughness: float               # 曼宁糙率系数
    description: str = ""          # 断面描述
    
    def __post_init__(self):
        """数据验证"""
        if self.bottom_width <= 0:
            raise ValueError(f"底宽必须为正值: {self.bottom_width}")
        if self.side_slope < 0:
            raise ValueError(f"边坡系数不能为负值: {self.side_slope}")
        if self.roughness <= 0:
            raise ValueError(f"糙率系数必须为正值: {self.roughness}")
    
    def create_area_function(self) -> Callable[[float], float]:
        """创建面积函数 A(H)"""
        def area_func(H: float) -> float:
            h = max(0.0, H - self.elevation)
            if h <= 0:
                return 0.0
            return h * (self.bottom_width + self.side_slope * h)
        return area_func
    
    def create_top_width_function(self) -> Callable[[float], float]:
        """创建水面宽度函数 T(H)"""
        def top_width_func(H: float) -> float:
            h = max(0.0, H - self.elevation)
            if h <= 0:
                return 0.0
            return self.bottom_width + 2.0 * self.side_slope * h
        return top_width_func
    
    def create_hydraulic_radius_function(self) -> Callable[[float], float]:
        """创建水力半径函数 R(H)"""
        def hydraulic_radius_func(H: float) -> float:
            h = max(0.0, H - self.elevation)
            if h <= 0:
                return 0.0
            
            # 梯形断面的水力半径计算
            area = h * (self.bottom_width + self.side_slope * h)
            if area <= 0:
                return 0.0
                
            # 湿周计算
            side_length = h * np.sqrt(1 + self.side_slope**2)
            perimeter = self.bottom_width + 2.0 * side_length
            
            if perimeter <= 0:
                return 0.0
                
            return area / perimeter
        return hydraulic_radius_func
    
    def create_conveyance_function(self) -> Callable[[float], float]:
        """创建输水能力函数 K(H)"""
        def conveyance_func(H: float) -> float:
            h = max(0.0, H - self.elevation)
            if h <= 0:
                return 0.0
            
            area = h * (self.bottom_width + self.side_slope * h)
            if area <= 0:
                return 0.0
                
            # 水力半径计算
            side_length = h * np.sqrt(1 + self.side_slope**2)
            perimeter = self.bottom_width + 2.0 * side_length
            hydraulic_radius = area / perimeter if perimeter > 0 else 0.0
            
            if hydraulic_radius <= 0:
                return 0.0
            
            # 输水能力 K = (1/n) * A * R^(2/3)
            return (1.0 / self.roughness) * area * (hydraulic_radius ** (2.0/3.0))
        return conveyance_func


@dataclass
class ChannelConfiguration:
    """渠道配置数据类"""
    name: str                      # 配置名称
    description: str               # 配置描述
    sections: List[SectionGeometry] # 断面几何列表
    boundary_conditions: Dict[str, Any] = None  # 边界条件
    initial_conditions: Dict[str, Any] = None   # 初始条件
    
    def __post_init__(self):
        """配置验证"""
        if len(self.sections) < 2:
            raise ValueError("至少需要2个断面定义渠道")
        
        # 检查里程排序
        mileages = [sec.mileage for sec in self.sections]
        if mileages != sorted(mileages):
            warnings.warn("断面里程未按顺序排列，将自动排序")
            self.sections.sort(key=lambda x: x.mileage)
        
        # 设置默认边界和初始条件
        if self.boundary_conditions is None:
            self.boundary_conditions = {
                'upstream_type': 'flow',
                'downstream_type': 'level',
                'default_upstream_Q': 50.0,  # m³/s
                'default_downstream_H': 101.0  # m
            }
        
        if self.initial_conditions is None:
            self.initial_conditions = {
                'initial_flow': 50.0,  # m³/s
                'steady_state': True
            }


class StandardFiveSectionConfig:
    """
    标准五断面配置管理器
    
    提供统一的标准五断面配置，替代项目中的重复实现。
    基于梯形断面几何，涵盖典型的明渠水力特征。
    """
    
    def __init__(self, variant: str = "standard"):
        """
        初始化配置管理器
        
        Args:
            variant (str): 配置变体 ("standard", "steep", "mild", "complex")
        """
        self.variant = variant
        self.config = self._create_configuration(variant)
        
        print(f"✅ StandardFiveSectionConfig 初始化完成")
        print(f"   配置变体: {variant}")
        print(f"   断面数量: {len(self.config.sections)}")
        print(f"   渠道长度: {self._get_total_length():.1f} m")
    
    def _create_configuration(self, variant: str) -> ChannelConfiguration:
        """创建指定变体的配置"""
        
        if variant == "standard":
            return self._create_standard_configuration()
        elif variant == "steep":
            return self._create_steep_configuration()
        elif variant == "mild":
            return self._create_mild_configuration()
        elif variant == "complex":
            return self._create_complex_configuration()
        else:
            raise ValueError(f"不支持的配置变体: {variant}")
    
    def _create_standard_configuration(self) -> ChannelConfiguration:
        """创建标准配置（基于项目中使用最多的参数）"""
        sections = [
            SectionGeometry(
                mileage=0.0,
                elevation=100.00,
                bottom_width=10.0,
                side_slope=1.5,
                roughness=0.025,
                description="上游断面"
            ),
            SectionGeometry(
                mileage=500.0,
                elevation=99.50,
                bottom_width=12.0,
                side_slope=1.5,
                roughness=0.025,
                description="上游过渡断面"
            ),
            SectionGeometry(
                mileage=1000.0,
                elevation=99.00,
                bottom_width=10.0,
                side_slope=2.0,
                roughness=0.030,
                description="中间断面"
            ),
            SectionGeometry(
                mileage=1500.0,
                elevation=98.50,
                bottom_width=15.0,
                side_slope=1.5,
                roughness=0.025,
                description="下游过渡断面"
            ),
            SectionGeometry(
                mileage=2000.0,
                elevation=98.00,
                bottom_width=12.0,
                side_slope=2.0,
                roughness=0.030,
                description="下游断面"
            )
        ]
        
        return ChannelConfiguration(
            name="标准五断面梯形明渠",
            description="基于WaterNet项目标准参数的五断面配置",
            sections=sections,
            boundary_conditions={
                'upstream_type': 'flow',
                'downstream_type': 'level',
                'default_upstream_Q': 50.0,
                'default_downstream_H': 101.0
            },
            initial_conditions={
                'initial_flow': 50.0,
                'steady_state': True
            }
        )
    
    def _create_steep_configuration(self) -> ChannelConfiguration:
        """创建陡坡配置（适用于运动波测试）"""
        sections = [
            SectionGeometry(0.0, 100.00, 8.0, 1.0, 0.020, "陡坡上游"),
            SectionGeometry(400.0, 98.00, 8.0, 1.0, 0.020, "陡坡过渡1"),
            SectionGeometry(800.0, 96.00, 8.0, 1.0, 0.020, "陡坡中间"),
            SectionGeometry(1200.0, 94.00, 8.0, 1.0, 0.020, "陡坡过渡2"),
            SectionGeometry(1600.0, 92.00, 8.0, 1.0, 0.020, "陡坡下游")
        ]
        
        return ChannelConfiguration(
            name="陡坡五断面明渠",
            description="坡度较大的五断面配置，适用于运动波模式测试",
            sections=sections
        )
    
    def _create_mild_configuration(self) -> ChannelConfiguration:
        """创建缓坡配置（适用于扩散波测试）"""
        sections = [
            SectionGeometry(0.0, 100.00, 15.0, 2.0, 0.035, "缓坡上游"),
            SectionGeometry(1000.0, 99.80, 15.0, 2.0, 0.035, "缓坡过渡1"),
            SectionGeometry(2000.0, 99.60, 15.0, 2.0, 0.035, "缓坡中间"),
            SectionGeometry(3000.0, 99.40, 15.0, 2.0, 0.035, "缓坡过渡2"),
            SectionGeometry(4000.0, 99.20, 15.0, 2.0, 0.035, "缓坡下游")
        ]
        
        return ChannelConfiguration(
            name="缓坡五断面明渠",
            description="坡度很小的五断面配置，适用于扩散波模式测试",
            sections=sections
        )
    
    def _create_complex_configuration(self) -> ChannelConfiguration:
        """创建复杂配置（适用于完整方程测试）"""
        sections = [
            SectionGeometry(0.0, 100.00, 6.0, 1.0, 0.020, "复杂几何上游"),
            SectionGeometry(800.0, 99.20, 12.0, 2.5, 0.030, "急扩断面"),
            SectionGeometry(1200.0, 98.80, 8.0, 1.5, 0.040, "糙率变化断面"),
            SectionGeometry(1800.0, 98.30, 20.0, 3.0, 0.025, "宽断面"),
            SectionGeometry(2500.0, 97.50, 10.0, 1.8, 0.028, "复杂几何下游")
        ]
        
        return ChannelConfiguration(
            name="复杂五断面明渠",
            description="几何和糙率变化复杂的五断面配置，需要完整方程求解",
            sections=sections
        )
    
    def get_five_section_geometry(self) -> List[Dict[str, Any]]:
        """
        获取五断面几何数据（兼容现有接口）
        
        Returns:
            List[Dict]: 包含所有水力函数的断面数据列表
        """
        geometry_data = []
        
        for section in self.config.sections:
            section_data = {
                'mileage': section.mileage,
                'elevation': section.elevation,
                'bottom_width': section.bottom_width,
                'side_slope': section.side_slope,
                'roughness': section.roughness,
                'description': section.description,
                
                # 水力计算函数
                'area_func': section.create_area_function(),
                'top_width_func': section.create_top_width_function(),
                'hydraulic_radius_func': section.create_hydraulic_radius_function(),
                'conveyance_func': section.create_conveyance_function()
            }
            geometry_data.append(section_data)
        
        return geometry_data
    
    def compute_steady_state_profile(self, Q: float = None, 
                                   H_downstream: float = None) -> Dict[str, Any]:
        """
        计算恒定流水面线（兼容现有接口）
        
        Args:
            Q (float): 流量，None则使用默认值
            H_downstream (float): 下游水位，None则使用默认值
            
        Returns:
            Dict: 包含水面线计算结果
        """
        # 使用默认值或输入值
        if Q is None:
            Q = self.config.boundary_conditions['default_upstream_Q']
        if H_downstream is None:
            H_downstream = self.config.boundary_conditions['default_downstream_H']
        
        print(f"计算恒定流水面线: Q={Q} m³/s, H_down={H_downstream} m")
        
        # 简化的水面线计算（基于标准步进法）
        sections_results = []
        water_levels = np.zeros(len(self.config.sections))
        
        # 设置下游边界
        water_levels[-1] = H_downstream
        
        # 从下游向上游计算
        for i in reversed(range(len(self.config.sections) - 1)):
            section_down = self.config.sections[i + 1]
            section_up = self.config.sections[i]
            
            H_down = water_levels[i + 1]
            
            # 使用能量方程估算上游水位
            try:
                H_up = self._estimate_upstream_level(
                    Q, H_down, section_up, section_down)
                water_levels[i] = H_up
            except:
                # 简单估算
                length = section_up.mileage - section_down.mileage
                slope = (section_up.elevation - section_down.elevation) / abs(length)
                H_up = H_down + slope * abs(length) + 0.1  # 增加0.1m的流动水头
                water_levels[i] = H_up
        
        # 构建结果
        for i, section in enumerate(self.config.sections):
            H = water_levels[i]
            area = section.create_area_function()(H)
            velocity = Q / area if area > 0 else 0.0
            
            section_result = {
                'mileage': section.mileage,
                'elevation': section.elevation,
                'water_level': H,
                'water_depth': max(0.0, H - section.elevation),
                'area': area,
                'velocity': velocity,
                'flow_rate': Q
            }
            sections_results.append(section_result)
        
        # 计算总蓄水量
        total_volume = self._calculate_channel_volume(water_levels, Q)
        
        return {
            'success': True,
            'input_parameters': {'Q': Q, 'H_downstream': H_downstream},
            'sections': sections_results,
            'total_volume': total_volume,
            'water_levels': water_levels.tolist(),
            'configuration': self.variant
        }
    
    def _estimate_upstream_level(self, Q: float, H_down: float,
                               section_up: SectionGeometry,
                               section_down: SectionGeometry) -> float:
        """估算上游水位（简化能量方程）"""
        
        # 计算下游断面水力要素
        area_down = section_down.create_area_function()(H_down)
        if area_down <= 0:
            raise ValueError("下游断面面积为零")
        
        velocity_down = Q / area_down
        
        # 计算分段长度和坡度
        length = abs(section_up.mileage - section_down.mileage)
        elevation_diff = section_up.elevation - section_down.elevation
        slope = elevation_diff / length if length > 0 else 0.001
        
        # 简化的能量方程估算
        # H_up + V_up²/(2g) = H_down + V_down²/(2g) + hf
        g = 9.81
        
        # 假设上游流速与下游相近（迭代改进）
        H_up_estimate = H_down + slope * length + velocity_down**2 / (2*g) * 0.1
        
        # 检查合理性
        if H_up_estimate < section_up.elevation:
            H_up_estimate = section_up.elevation + 0.5
        
        return H_up_estimate
    
    def _calculate_channel_volume(self, water_levels: np.ndarray, Q: float) -> float:
        """计算渠道总蓄水量"""
        total_volume = 0.0
        
        for i in range(len(self.config.sections) - 1):
            section_up = self.config.sections[i]
            section_down = self.config.sections[i + 1]
            
            H_up = water_levels[i]
            H_down = water_levels[i + 1]
            
            area_up = section_up.create_area_function()(H_up)
            area_down = section_down.create_area_function()(H_down)
            
            length = abs(section_down.mileage - section_up.mileage)
            
            # 梯形法则计算分段体积
            segment_volume = length * (area_up + area_down) / 2.0
            total_volume += segment_volume
        
        return total_volume
    
    def _get_total_length(self) -> float:
        """获取渠道总长度"""
        if len(self.config.sections) < 2:
            return 0.0
        return abs(self.config.sections[-1].mileage - self.config.sections[0].mileage)
    
    def create_saint_venant_sections(self) -> List[Dict[str, Any]]:
        """
        创建适用于SaintVenantModel的断面数据
        
        Returns:
            List[Dict]: 圣维南模型所需的断面数据格式
        """
        sv_sections = []
        
        for section in self.config.sections:
            sv_section = {
                'mileage': section.mileage,
                'elevation': section.elevation,
                'roughness': section.roughness,
                'area_func': section.create_area_function(),
                'top_width_func': section.create_top_width_function()
            }
            sv_sections.append(sv_section)
        
        return sv_sections
    
    def export_to_yaml(self, file_path: str) -> bool:
        """导出配置到YAML文件"""
        try:
            # 准备导出数据（不包含函数）
            export_data = {
                'name': self.config.name,
                'description': self.config.description,
                'variant': self.variant,
                'sections': [
                    {
                        'mileage': sec.mileage,
                        'elevation': sec.elevation,
                        'bottom_width': sec.bottom_width,
                        'side_slope': sec.side_slope,
                        'roughness': sec.roughness,
                        'description': sec.description
                    }
                    for sec in self.config.sections
                ],
                'boundary_conditions': self.config.boundary_conditions,
                'initial_conditions': self.config.initial_conditions
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(export_data, f, default_flow_style=False, 
                         allow_unicode=True, indent=2)
            
            print(f"✅ 配置已导出到: {file_path}")
            return True
            
        except Exception as e:
            print(f"❌ 配置导出失败: {e}")
            return False
    
    @classmethod
    def load_from_yaml(cls, file_path: str) -> 'StandardFiveSectionConfig':
        """从YAML文件加载配置"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            # 重建SectionGeometry对象
            sections = []
            for sec_data in data['sections']:
                section = SectionGeometry(
                    mileage=sec_data['mileage'],
                    elevation=sec_data['elevation'],
                    bottom_width=sec_data['bottom_width'],
                    side_slope=sec_data['side_slope'],
                    roughness=sec_data['roughness'],
                    description=sec_data.get('description', '')
                )
                sections.append(section)
            
            # 创建配置对象
            config = ChannelConfiguration(
                name=data['name'],
                description=data['description'],
                sections=sections,
                boundary_conditions=data.get('boundary_conditions'),
                initial_conditions=data.get('initial_conditions')
            )
            
            # 创建配置管理器实例
            instance = cls.__new__(cls)
            instance.variant = data.get('variant', 'custom')
            instance.config = config
            
            print(f"✅ 配置已从文件加载: {file_path}")
            return instance
            
        except Exception as e:
            print(f"❌ 配置加载失败: {e}")
            raise
    
    def validate_configuration(self) -> Dict[str, Any]:
        """验证配置的完整性和合理性"""
        validation_result = {
            'is_valid': True,
            'warnings': [],
            'errors': [],
            'statistics': {}
        }
        
        try:
            # 基本几何检查
            mileages = [sec.mileage for sec in self.config.sections]
            elevations = [sec.elevation for sec in self.config.sections]
            roughnesses = [sec.roughness for sec in self.config.sections]
            
            # 检查里程单调性
            if mileages != sorted(mileages):
                validation_result['warnings'].append("断面里程未按升序排列")
            
            # 检查高程变化合理性
            elevation_changes = np.diff(elevations)
            if any(change > 5.0 for change in elevation_changes):
                validation_result['warnings'].append("存在异常大的高程跳跃")
            
            # 检查糙率系数范围
            if any(n < 0.01 or n > 0.1 for n in roughnesses):
                validation_result['warnings'].append("糙率系数可能超出合理范围")
            
            # 计算统计信息
            total_length = abs(mileages[-1] - mileages[0])
            average_slope = abs(elevations[0] - elevations[-1]) / total_length if total_length > 0 else 0
            
            validation_result['statistics'] = {
                'total_length': total_length,
                'average_slope': average_slope,
                'elevation_range': max(elevations) - min(elevations),
                'roughness_range': [min(roughnesses), max(roughnesses)]
            }
            
            # 测试水力函数
            test_H = 101.0  # 测试水位
            for i, section in enumerate(self.config.sections):
                try:
                    area = section.create_area_function()(test_H)
                    top_width = section.create_top_width_function()(test_H)
                    hydraulic_radius = section.create_hydraulic_radius_function()(test_H)
                    conveyance = section.create_conveyance_function()(test_H)
                    
                    if not all(np.isfinite([area, top_width, hydraulic_radius, conveyance])):
                        validation_result['errors'].append(f"断面{i}水力函数返回非有限值")
                    
                except Exception as e:
                    validation_result['errors'].append(f"断面{i}水力函数计算失败: {e}")
            
        except Exception as e:
            validation_result['errors'].append(f"配置验证过程发生错误: {e}")
            validation_result['is_valid'] = False
        
        # 最终判定
        if validation_result['errors']:
            validation_result['is_valid'] = False
        
        return validation_result
    
    def get_configuration_summary(self) -> str:
        """获取配置摘要信息"""
        validation = self.validate_configuration()
        stats = validation['statistics']
        
        summary = f"""
📋 标准五断面配置摘要
{'='*50}
配置名称: {self.config.name}
配置变体: {self.variant}
描述: {self.config.description}

🏞️ 几何特征:
  断面数量: {len(self.config.sections)}
  渠道长度: {stats.get('total_length', 0):.1f} m
  平均坡度: {stats.get('average_slope', 0):.6f}
  高程变化: {stats.get('elevation_range', 0):.2f} m
  糙率范围: {stats.get('roughness_range', [0, 0])}

🔧 边界条件:
  上游类型: {self.config.boundary_conditions.get('upstream_type', 'N/A')}
  下游类型: {self.config.boundary_conditions.get('downstream_type', 'N/A')}
  默认流量: {self.config.boundary_conditions.get('default_upstream_Q', 0)} m³/s
  默认下游水位: {self.config.boundary_conditions.get('default_downstream_H', 0)} m

✅ 验证状态:
  配置有效: {'是' if validation['is_valid'] else '否'}
  警告数量: {len(validation['warnings'])}
  错误数量: {len(validation['errors'])}
"""
        
        # 添加警告和错误详情
        if validation['warnings']:
            summary += "\n⚠️ 警告信息:\n"
            for warning in validation['warnings']:
                summary += f"  - {warning}\n"
        
        if validation['errors']:
            summary += "\n❌ 错误信息:\n"
            for error in validation['errors']:
                summary += f"  - {error}\n"
        
        return summary