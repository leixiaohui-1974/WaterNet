"""
测试套件：SaintVenantModel测试

验证圣维南模型的实现正确性。

Author: WaterNet Development Team  
Date: 2024-10-03
"""

import pytest
import numpy as np
from waternet.models.saint_venant import SaintVenantModel


class TestSaintVenantModel:
    """圣维南模型测试类"""
    
    @pytest.fixture
    def simple_channel_sections(self):
        """创建简单明渠断面数据"""
        return [
            {
                'mileage': 0.0,
                'elevation': 100.0,
                'roughness': 0.025,
                'area_func': lambda h: max(0, h - 100) * 10,
                'top_width_func': lambda h: 10 if h > 100 else 0
            },
            {
                'mileage': 1000.0,
                'elevation': 99.0,  
                'roughness': 0.025,
                'area_func': lambda h: max(0, h - 99) * 10,
                'top_width_func': lambda h: 10 if h > 99 else 0
            }
        ]
    
    def test_saint_venant_initialization(self, simple_channel_sections):
        """测试圣维南模型初始化"""
        model = SaintVenantModel(
            "TestChannel", "upstream", "downstream", simple_channel_sections)
        
        assert model.name == "TestChannel"
        assert model.upstream_node == "upstream"
        assert model.downstream_node == "downstream"
        assert len(model.sections) == 2
        assert len(model.segments) == 1
        assert len(model.internal_nodes) == 0  # 只有2个断面，无内部节点
    
    def test_invalid_initialization(self):
        """测试无效初始化"""
        with pytest.raises(ValueError):
            SaintVenantModel("test", "up", "down", [])  # 断面不足
        
        incomplete_section = [{'mileage': 0.0}]  # 缺少必需字段
        with pytest.raises(ValueError):
            SaintVenantModel("test", "up", "down", incomplete_section)
    
    def test_steady_state_computation(self, simple_channel_sections):
        """测试恒定流计算"""
        model = SaintVenantModel(
            "TestChannel", "upstream", "downstream", simple_channel_sections)
        
        # 测试恒定流计算
        Q = 10.0  # m³/s
        H_down = 100.5  # m
        
        result = model.compute_steady_state(Q, H_down)
        
        # 验证结果格式
        assert 'total_volume' in result
        assert 'H_section_0' in result
        assert 'H_section_1' in result
        assert 'Q_seg_0' in result
        
        # 验证物理合理性
        assert result['total_volume'] > 0
        assert result['H_section_0'] >= result['H_section_1']  # 上游水位不低于下游
        assert result['Q_seg_0'] == Q  # 恒定流时流量相等
    
    def test_variable_names(self, simple_channel_sections):
        """测试变量名获取"""
        model = SaintVenantModel(
            "TestChannel", "upstream", "downstream", simple_channel_sections)
        
        var_names = model.get_variable_names()
        
        # 应该包含分段流量变量
        assert 'Q_TestChannel_seg_0' in var_names
        
        # 对于只有2个断面的情况，不应该有内部节点变量
        internal_vars = [name for name in var_names if 'internal' in name]
        assert len(internal_vars) == 0
    
    def test_segment_properties(self, simple_channel_sections):
        """测试分段属性计算"""
        model = SaintVenantModel(
            "TestChannel", "upstream", "downstream", simple_channel_sections)
        
        segment = model.segments[0]
        
        # 验证分段属性
        assert segment['length'] == 1000.0  # 里程差
        assert segment['slope'] == 0.001    # (100-99)/1000
        assert segment['roughness'] == 0.025  # 平均糙率
        
        # 验证分段连接
        assert segment['upstream_section'] == 0
        assert segment['downstream_section'] == 1


class TestSaintVenantEquations:
    """圣维南方程测试类"""
    
    @pytest.fixture
    def model_with_internal_nodes(self):
        """创建带内部节点的模型"""
        sections = [
            {
                'mileage': 0.0, 'elevation': 100.0, 'roughness': 0.025,
                'area_func': lambda h: max(0, h - 100) * 10,
                'top_width_func': lambda h: 10 if h > 100 else 0
            },
            {
                'mileage': 500.0, 'elevation': 99.5, 'roughness': 0.025,
                'area_func': lambda h: max(0, h - 99.5) * 10,
                'top_width_func': lambda h: 10 if h > 99.5 else 0
            },
            {
                'mileage': 1000.0, 'elevation': 99.0, 'roughness': 0.025,
                'area_func': lambda h: max(0, h - 99) * 10,
                'top_width_func': lambda h: 10 if h > 99 else 0
            }
        ]
        return SaintVenantModel("Channel3", "up", "down", sections)
    
    def test_equation_structure(self, model_with_internal_nodes):
        """测试方程结构"""
        model = model_with_internal_nodes
        
        # 准备测试变量
        variables = {
            'H_up': 100.5,
            'H_down': 99.2,
            'H_Channel3_internal_0': 99.8,
            'Q_Channel3_seg_0': 5.0,
            'Q_Channel3_seg_1': 5.0
        }
        
        prev_states = {
            'H_section_0': 100.4,
            'H_section_1': 99.7,
            'H_section_2': 99.1,
            'Q_Channel3_seg_0': 4.8,
            'Q_Channel3_seg_1': 4.8
        }
        
        equations = model.get_equations(variables, 60.0, prev_states)
        
        # 验证方程数量
        expected_equations = 2 * 2 + 1  # 2个分段的连续性和动量方程 + 1个内部节点平衡
        assert len(equations) == expected_equations
        
        # 验证方程名称
        assert 'continuity_seg_0' in equations
        assert 'continuity_seg_1' in equations
        assert 'momentum_seg_0' in equations
        assert 'momentum_seg_1' in equations
        assert 'balance_Channel3_internal_0' in equations
        
        # 验证方程残差是数值
        for eq_name, residual in equations.items():
            assert isinstance(residual, (int, float))
            assert np.isfinite(residual)