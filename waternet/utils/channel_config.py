#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
渠道配置管理工具 - WaterNet核心库

提供通用的渠道配置加载、转换和验证功能。

核心功能：
1. 配置文件加载和解析
2. 配置格式转换和适配
3. 配置验证和默认值处理
4. SaintVenant模型创建

Author: WaterNet Development Team
Date: 2025-01-05
"""

import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
from .channel_geometry import ChannelGeometry


class ChannelConfigManager:
    """渠道配置管理器"""
    
    @staticmethod
    def load_channel_config(config_path: str) -> Dict[str, Any]:
        """
        加载渠道配置文件
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            Dict: 标准化的渠道配置
        """
        config_file = Path(config_path)
        
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                raw_config = yaml.safe_load(f)
                
                # 转换为标准格式
                return ChannelConfigManager._convert_to_standard_format(raw_config)
        else:
            # 使用默认配置
            return ChannelConfigManager._get_default_channel_config()
    
    @staticmethod
    def _convert_to_standard_format(raw_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        将现有配置格式转换为标准格式
        
        Args:
            raw_config: 原始配置
            
        Returns:
            Dict: 标准化配置
        """
        # 如果是sections格式（如trapezoidal_channel.yaml）
        if 'sections' in raw_config:
            sections = raw_config['sections']
            first_section = sections[0]
            last_section = sections[-1]
            
            total_length = last_section['mileage'] - first_section['mileage']
            
            # 获取断面几何参数
            cross_section = first_section.get('cross_section', {})
            
            converted_config = {
                'channel': {
                    'name': raw_config.get('name', '标准梯形渠道'),
                    'length': total_length if total_length > 0 else 10000.0,
                    'sections': len(sections),
                    'geometry': {
                        'type': cross_section.get('type', 'trapezoidal'),
                        'bottom_width': cross_section.get('bottom_width', 8.0),
                        'side_slope': cross_section.get('side_slope', 1.5),
                        'roughness': first_section.get('roughness', 0.025)
                    },
                    'profile': {
                        'upstream_elevation': first_section['elevation'],
                        'downstream_elevation': last_section['elevation']
                    },
                    'raw_sections': sections  # 保存原始断面数据
                }
            }
            
            return converted_config
        
        # 如果已经是标准格式
        if 'channel' in raw_config:
            return raw_config
            
        # 否则当作原始格式处理
        return {'channel': raw_config}
    
    @staticmethod
    def _get_default_channel_config() -> Dict[str, Any]:
        """获取默认渠道配置"""
        return {
            'channel': {
                'name': '标准梯形渠道',
                'length': 10000.0,  # 总长度 10km
                'sections': 11,     # 断面数量
                'geometry': {
                    'type': 'trapezoidal',
                    'bottom_width': 8.0,
                    'side_slope': 1.5,
                    'roughness': 0.025
                },
                'profile': {
                    'upstream_elevation': 110.0,
                    'downstream_elevation': 100.0
                }
            }
        }
    
    @staticmethod
    def create_saint_venant_sections(channel_config: Dict[str, Any]) -> List[Dict]:
        """
        根据渠道配置创建SaintVenant模型所需的断面数据
        
        Args:
            channel_config: 渠道配置
            
        Returns:
            List[Dict]: 断面数据列表
        """
        # 如果有原始断面数据，直接使用
        if 'raw_sections' in channel_config:
            raw_sections = channel_config['raw_sections']
            sections = []
            
            for section_data in raw_sections:
                cross_section = section_data['cross_section']
                bottom_width = cross_section['bottom_width']
                side_slope = cross_section['side_slope']
                elevation = section_data['elevation']
                roughness = section_data['roughness']
                mileage = section_data['mileage']
                
                # 创建几何函数
                geometry_funcs = ChannelGeometry.create_geometry_functions(
                    bottom_width, side_slope, elevation, roughness)
                
                section = {
                    'mileage': mileage,
                    'elevation': elevation,
                    'roughness': roughness,
                    'bottom_width': bottom_width,
                    'side_slope': side_slope,
                    **geometry_funcs
                }
                
                sections.append(section)
            
            return sections
        
        # 否则基于基本参数生成断面
        length = channel_config['length']
        n_sections = channel_config.get('sections', 11)
        geometry = channel_config['geometry']
        profile = channel_config['profile']
        
        bottom_width = geometry['bottom_width']
        side_slope = geometry['side_slope']
        roughness = geometry['roughness']
        
        upstream_elevation = profile['upstream_elevation']
        downstream_elevation = profile['downstream_elevation']
        
        sections = []
        
        for i in range(n_sections):
            ratio = i / (n_sections - 1)
            mileage = ratio * length
            elevation = upstream_elevation + ratio * (downstream_elevation - upstream_elevation)
            
            # 创建几何函数
            geometry_funcs = ChannelGeometry.create_geometry_functions(
                bottom_width, side_slope, elevation, roughness)
            
            section = {
                'mileage': mileage,
                'elevation': elevation,
                'roughness': roughness,
                'bottom_width': bottom_width,
                'side_slope': side_slope,
                **geometry_funcs
            }
            
            sections.append(section)
        
        return sections
    
    @staticmethod
    def validate_config(config: Dict[str, Any]) -> bool:
        """
        验证配置的有效性
        
        Args:
            config: 渠道配置
            
        Returns:
            bool: 配置是否有效
        """
        try:
            channel = config.get('channel', {})
            
            # 检查必需字段
            required_fields = ['name', 'length', 'geometry', 'profile']
            for field in required_fields:
                if field not in channel:
                    return False
            
            # 检查几何参数
            geometry = channel['geometry']
            if geometry.get('bottom_width', 0) <= 0:
                return False
            if geometry.get('side_slope', 0) < 0:
                return False
            if geometry.get('roughness', 0) <= 0:
                return False
            
            # 检查纵断面
            profile = channel['profile']
            if 'upstream_elevation' not in profile or 'downstream_elevation' not in profile:
                return False
            
            return True
            
        except Exception:
            return False