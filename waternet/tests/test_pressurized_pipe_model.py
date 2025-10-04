"""
PressurizedPipeModel 测试

测试有压管道精细化模型的基本功能，包括几何管理、变量命名、
恒定流计算等核心功能。

Author: WaterNet Development Team
Date: 2024-10-04
"""

import pytest
import numpy as np
import sys
import os

# 添加路径以导入模块
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from physical_objects.pressurized_pipe_model import PressurizedPipeModel


class TestPressurizedPipeModel:
    """PressurizedPipeModel 测试类"""
    
    def setup_method(self):
        """设置测试数据"""
        # 创建简单的三节点管道（两个分段）
        self.nodes = [
            {'mileage': 0.0, 'elevation': 100.0, 'diameter': 1.0, 'friction_coeff': 0.02},
            {'mileage': 500.0, 'elevation': 95.0, 'diameter': 1.0, 'friction_coeff': 0.02},
            {'mileage': 1000.0, 'elevation': 90.0, 'diameter': 0.8, 'friction_coeff': 0.025}
        ]
        
        self.pipe_model = PressurizedPipeModel(
            name="TestPipe",
            upstream_node="Node1",
            downstream_node="Node3", 
            nodes=self.nodes,
            wave_speed=1200.0
        )
    
    def test_initialization(self):
        """测试模型初始化"""
        assert self.pipe_model.name == "TestPipe"
        assert self.pipe_model.upstream_node == "Node1"
        assert self.pipe_model.downstream_node == "Node3"
        assert self.pipe_model.wave_speed == 1200.0
        assert len(self.pipe_model.segments) == 2
        assert len(self.pipe_model.internal_nodes) == 1
    
    def test_variable_names(self):
        """测试变量命名规范"""
        variable_names = self.pipe_model.get_variable_names()
        
        # 验证变量数量
        expected_count = len(self.pipe_model.internal_nodes) + len(self.pipe_model.segments)
        assert len(variable_names) == expected_count == 3
        
        # 验证变量命名格式
        assert 'H_TestPipe_internal_0' in variable_names
        assert 'Q_TestPipe_seg_0' in variable_names
        assert 'Q_TestPipe_seg_1' in variable_names
    
    def test_segment_properties(self):
        """测试分段属性计算"""
        segments = self.pipe_model.get_segment_properties()
        
        # 检查分段数量
        assert len(segments) == 2
        
        # 检查第一段属性
        seg0 = segments[0]
        assert abs(seg0['length'] - 500.0) < 1e-6
        assert abs(seg0['diameter'] - 1.0) < 1e-6
        assert abs(seg0['area'] - np.pi * 0.25) < 1e-6
        assert abs(seg0['friction_coeff'] - 0.02) < 1e-6
        
        # 检查第二段属性
        seg1 = segments[1]
        assert abs(seg1['length'] - 500.0) < 1e-6
        assert abs(seg1['diameter'] - 0.9) < 1e-6  # 平均直径
        assert abs(seg1['friction_coeff'] - 0.0225) < 1e-6  # 平均摩擦系数
    
    def test_steady_state_computation(self):
        """测试恒定流计算"""
        Q = 1.5  # m³/s
        downstream_H = 50.0  # m
        
        steady_states = self.pipe_model.compute_steady_state(Q, downstream_H)
        
        # 验证返回结果包含必要字段
        assert 'H_TestPipe_internal_0' in steady_states
        assert 'Q_TestPipe_seg_0' in steady_states
        assert 'Q_TestPipe_seg_1' in steady_states
        assert 'total_volume' in steady_states
        assert 'upstream_H' in steady_states
        
        # 验证流量守恒（恒定流条件下）
        assert abs(steady_states['Q_TestPipe_seg_0'] - Q) < 1e-6
        assert abs(steady_states['Q_TestPipe_seg_1'] - Q) < 1e-6
        
        # 验证水头计算合理性
        internal_H = steady_states['H_TestPipe_internal_0']
        upstream_H = steady_states['upstream_H']
        
        # 上游水头应高于内部节点水头，内部节点应高于下游水头
        assert upstream_H > internal_H > downstream_H
        
        # 手动验证第一段的水头损失计算
        seg0 = self.pipe_model.segments[0]
        velocity = Q / seg0['area']
        friction_loss = (seg0['friction_coeff'] * seg0['length'] / 
                        seg0['diameter'] * velocity**2 / (2 * 9.81))
        elevation_change = seg0['upstream_elevation'] - seg0['downstream_elevation']
        
        expected_internal_H = downstream_H + friction_loss + elevation_change
        assert abs(internal_H - expected_internal_H) < 1e-3
    
    def test_zero_flow_steady_state(self):
        """测试零流量恒定流"""
        Q = 0.0
        downstream_H = 50.0
        
        steady_states = self.pipe_model.compute_steady_state(Q, downstream_H)
        
        # 零流量时，水头差仅由高程差决定
        internal_H = steady_states['H_TestPipe_internal_0']
        upstream_H = steady_states['upstream_H']
        
        # 验证高程差
        seg0_elevation_diff = self.nodes[1]['elevation'] - self.nodes[2]['elevation']  # 5.0m
        seg1_elevation_diff = self.nodes[0]['elevation'] - self.nodes[1]['elevation']  # 5.0m
        
        assert abs(internal_H - (downstream_H + seg0_elevation_diff)) < 1e-3
        assert abs(upstream_H - (internal_H + seg1_elevation_diff)) < 1e-3
    
    def test_equations_structure(self):
        """测试方程结构正确性"""
        # 创建测试变量字典
        variables = {
            'H_Node1': 105.0,
            'H_TestPipe_internal_0': 102.0,
            'H_Node3': 100.0,
            'Q_TestPipe_seg_0': 1.0,
            'Q_TestPipe_seg_1': 1.0
        }
        
        # 创建前一步状态
        prev_states = {
            'H_TestPipe_internal_0': 101.8,
            'Q_TestPipe_seg_0': 0.95,
            'Q_TestPipe_seg_1': 0.95
        }
        
        dt = 0.1
        residuals = self.pipe_model.get_equations(variables, dt, prev_states)
        
        # 验证方程数量
        expected_eq_count = 2 * len(self.pipe_model.segments) + len(self.pipe_model.internal_nodes)
        assert len(residuals) == expected_eq_count == 5
        
        # 验证方程名称
        assert 'continuity_seg_0' in residuals
        assert 'continuity_seg_1' in residuals
        assert 'momentum_seg_0' in residuals
        assert 'momentum_seg_1' in residuals
        assert 'balance_H_TestPipe_internal_0' in residuals
        
        # 验证残差为数值类型
        for eq_name, residual in residuals.items():
            assert isinstance(residual, (int, float))
            assert np.isfinite(residual)
    
    def test_steady_state_equations_consistency(self):
        """测试恒定流状态下方程残差接近零"""
        # 首先计算恒定流状态
        Q = 1.0
        downstream_H = 50.0
        steady_states = self.pipe_model.compute_steady_state(Q, downstream_H)
        
        # 构建完整的变量字典
        variables = {
            'H_Node1': steady_states['upstream_H'],
            'H_TestPipe_internal_0': steady_states['H_TestPipe_internal_0'],
            'H_Node3': downstream_H,
            'Q_TestPipe_seg_0': steady_states['Q_TestPipe_seg_0'],
            'Q_TestPipe_seg_1': steady_states['Q_TestPipe_seg_1']
        }
        
        # 使用相同状态作为前一步状态（完美恒定流）
        prev_states = variables.copy()
        
        dt = 0.1
        residuals = self.pipe_model.get_equations(variables, dt, prev_states)
        
        # 在恒定流状态下，所有残差都应接近零
        for eq_name, residual in residuals.items():
            assert abs(residual) < 1e-6, f"方程 {eq_name} 的残差过大: {residual}"
    
    def test_validation(self):
        """测试计算设置验证"""
        assert self.pipe_model.validate_computational_setup() == True
    
    def test_error_handling(self):
        """测试错误处理"""
        # 测试节点数量不足
        with pytest.raises(ValueError):
            PressurizedPipeModel("Test", "A", "B", [{'mileage': 0}], 1200.0)
        
        # 测试波速非正值
        with pytest.raises(ValueError):
            PressurizedPipeModel("Test", "A", "B", self.nodes, -100.0)
        
        # 测试缺少必需字段
        invalid_nodes = [
            {'mileage': 0.0, 'elevation': 100.0},  # 缺少 diameter 和 friction_coeff
            {'mileage': 500.0, 'elevation': 95.0, 'diameter': 1.0, 'friction_coeff': 0.02}
        ]
        
        with pytest.raises(ValueError):
            PressurizedPipeModel("Test", "A", "B", invalid_nodes, 1200.0)


def run_basic_tests():
    """运行基本测试（不依赖pytest框架）"""
    print("开始 PressurizedPipeModel 基本测试...")
    
    try:
        # 创建测试实例
        nodes = [
            {'mileage': 0.0, 'elevation': 100.0, 'diameter': 1.0, 'friction_coeff': 0.02},
            {'mileage': 500.0, 'elevation': 95.0, 'diameter': 1.0, 'friction_coeff': 0.02},
            {'mileage': 1000.0, 'elevation': 90.0, 'diameter': 0.8, 'friction_coeff': 0.025}
        ]
        
        pipe_model = PressurizedPipeModel(
            name="TestPipe",
            upstream_node="Node1", 
            downstream_node="Node3",
            nodes=nodes,
            wave_speed=1200.0
        )
        
        print("✓ 模型初始化成功")
        
        # 测试变量命名
        variable_names = pipe_model.get_variable_names()
        expected_vars = ['H_TestPipe_internal_0', 'Q_TestPipe_seg_0', 'Q_TestPipe_seg_1']
        
        assert len(variable_names) == 3
        for var in expected_vars:
            assert var in variable_names
        
        print("✓ 变量命名规范正确")
        
        # 测试分段属性
        segments = pipe_model.get_segment_properties()
        assert len(segments) == 2
        assert abs(segments[0]['length'] - 500.0) < 1e-6
        
        print("✓ 分段属性计算正确")
        
        # 测试恒定流计算
        steady_states = pipe_model.compute_steady_state(1.5, 50.0)
        
        # 验证基本合理性
        assert 'H_TestPipe_internal_0' in steady_states
        assert steady_states['Q_TestPipe_seg_0'] == 1.5
        assert steady_states['upstream_H'] > steady_states['H_TestPipe_internal_0'] > 50.0
        
        print("✓ 恒定流计算正确")
        
        # 测试方程构建
        variables = {
            'H_Node1': steady_states['upstream_H'],
            'H_TestPipe_internal_0': steady_states['H_TestPipe_internal_0'],
            'H_Node3': 50.0,
            'Q_TestPipe_seg_0': 1.5,
            'Q_TestPipe_seg_1': 1.5
        }
        
        residuals = pipe_model.get_equations(variables, 0.1, variables)
        
        assert len(residuals) == 5
        for residual in residuals.values():
            assert isinstance(residual, (int, float))
            assert np.isfinite(residual)
        
        print("✓ 方程构建正确")
        
        # 显示模型摘要
        print("\n" + "="*50)
        print(pipe_model.get_pipe_summary())
        print("="*50)
        
        print("\n✅ 所有基本测试通过！")
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_basic_tests()
    exit(0 if success else 1)