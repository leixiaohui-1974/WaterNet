"""
WaterNet 测试配置文件

为pytest提供全局配置、fixtures和测试辅助函数。
"""

import pytest
import numpy as np
import os
import sys
from typing import Dict, List, Callable, Any

# 添加源代码路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from waternet.models import SaintVenantModel, MuskingumModel, StorageRoutingModel
from waternet.models import SolverFactory


@pytest.fixture(scope="session")
def test_data_dir():
    """测试数据目录"""
    return os.path.join(os.path.dirname(__file__), 'fixtures')


@pytest.fixture
def simple_channel_sections():
    """简单矩形明渠断面数据"""
    return [
        {
            'mileage': 0.0,
            'elevation': 100.0,
            'roughness': 0.025,
            'area_func': lambda h: max(0, h - 100) * 10,
            'top_width_func': lambda h: 10 if h > 100 else 0
        },
        {
            'mileage': 500.0,
            'elevation': 99.5,
            'roughness': 0.025,
            'area_func': lambda h: max(0, h - 99.5) * 10,
            'top_width_func': lambda h: 10 if h > 99.5 else 0
        },
        {
            'mileage': 1000.0,
            'elevation': 99.0,
            'roughness': 0.025,
            'area_func': lambda h: max(0, h - 99) * 10,
            'top_width_func': lambda h: 10 if h > 99 else 0
        }
    ]


@pytest.fixture
def saint_venant_model(simple_channel_sections):
    """圣维南模型实例"""
    return SaintVenantModel(
        name="TestChannel",
        upstream_node="upstream",
        downstream_node="downstream",
        sections=simple_channel_sections
    )


@pytest.fixture
def physical_relations():
    """物理关系函数"""
    def V_to_H_relation(V):
        """蓄量-水位关系"""
        base_level = 99.0
        storage_coefficient = 1.0 / 8000.0
        return base_level + V * storage_coefficient
    
    def H_to_Q_relation(H):
        """水位-出流关系"""
        threshold_level = 99.0
        if H <= threshold_level:
            return 0.0
        else:
            flow_coefficient = 25.0
            return flow_coefficient * (H - threshold_level) ** 1.5
    
    return V_to_H_relation, H_to_Q_relation


@pytest.fixture
def muskingum_model(physical_relations):
    """马斯京干模型实例"""
    V_to_H_func, H_to_Q_func = physical_relations
    return MuskingumModel(
        dt=60.0,
        K=3600.0,
        x=0.2,
        initial_V=12000.0,
        V_to_H_func=V_to_H_func,
        H_to_Q_func=H_to_Q_func,
        name="TestMuskingum"
    )


@pytest.fixture
def storage_model(physical_relations):
    """蓄量演算模型实例"""
    V_to_H_func, H_to_Q_func = physical_relations
    return StorageRoutingModel(
        dt=60.0,
        initial_V=12000.0,
        V_to_H_func=V_to_H_func,
        H_to_Q_func=H_to_Q_func,
        name="TestStorage"
    )


@pytest.fixture
def test_flow_series():
    """测试用流量序列"""
    return np.array([
        8.0, 8.0, 12.0, 15.0, 20.0, 18.0, 
        15.0, 12.0, 10.0, 8.0, 8.0, 8.0
    ])


@pytest.fixture
def test_water_level_series():
    """测试用水位序列"""
    return np.array([
        99.4, 99.4, 99.45, 99.5, 99.55, 99.52,
        99.48, 99.45, 99.42, 99.4, 99.4, 99.4
    ])


@pytest.fixture
def standard_solver():
    """标准求解器"""
    return SolverFactory.create_solver("standard")


@pytest.fixture
def enhanced_solver():
    """增强求解器"""
    return SolverFactory.create_solver("enhanced")


# 测试辅助函数
def assert_valid_steady_result(result: Dict[str, float], n_sections: int):
    """验证恒定流计算结果的有效性"""
    # 检查必需的键
    assert 'total_volume' in result
    assert result['total_volume'] > 0
    
    # 检查断面水位
    for i in range(n_sections):
        key = f'H_section_{i}'
        assert key in result
        assert np.isfinite(result[key])
        assert result[key] > 0
    
    # 检查分段流量
    for i in range(n_sections - 1):
        key = f'Q_seg_{i}'
        assert key in result
        assert result[key] > 0


def assert_valid_unsteady_result(results: List[Dict[str, Any]]):
    """验证非恒定流计算结果的有效性"""
    assert len(results) > 0
    
    for result in results:
        assert 'time' in result
        assert np.isfinite(result['time'])
        assert result['time'] >= 0
        
        if 'Q_out' in result:
            assert np.isfinite(result['Q_out'])
            assert result['Q_out'] >= 0
        
        if 'H_out' in result:
            assert np.isfinite(result['H_out'])
            assert result['H_out'] > 0


def assert_mass_conservation(Q_in_series, Q_out_series, tolerance=0.1):
    """验证质量守恒"""
    total_inflow = np.sum(Q_in_series)
    total_outflow = np.sum(Q_out_series)
    
    if total_inflow > 0:
        relative_error = abs(total_outflow - total_inflow) / total_inflow
        assert relative_error < tolerance, f"质量不守恒，相对误差: {relative_error:.3f}"


def assert_model_consistency(model):
    """验证模型内部一致性"""
    # 检查基本属性
    assert hasattr(model, 'name')
    assert hasattr(model, 'sections')
    assert len(model.sections) >= 2
    
    # 检查断面数据完整性
    for i, section in enumerate(model.sections):
        assert 'mileage' in section
        assert 'elevation' in section
        assert 'roughness' in section
        assert callable(section['area_func'])
        assert callable(section['top_width_func'])
    
    # 检查内部拓扑
    if hasattr(model, 'segments'):
        assert len(model.segments) == len(model.sections) - 1


# pytest配置
def pytest_configure(config):
    """pytest配置"""
    # 添加自定义标记
    config.addinivalue_line(
        "markers", "unit: 单元测试标记"
    )
    config.addinivalue_line(
        "markers", "integration: 集成测试标记"
    )
    config.addinivalue_line(
        "markers", "performance: 性能测试标记"
    )
    config.addinivalue_line(
        "markers", "slow: 慢速测试标记"
    )