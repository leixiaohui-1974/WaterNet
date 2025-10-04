"""
边界条件框架综合测试套件

测试边界条件框架的所有核心功能，包括单元测试、集成测试和性能测试。
确保边界条件、控制信号、求解器增强和配置解析的正确性。

测试分类:
1. 单元测试: 测试各个组件的独立功能
2. 集成测试: 测试组件之间的协作
3. 性能测试: 测试大规模系统的性能
4. 配置测试: 测试配置解析和验证

Author: WaterNet Development Team
Date: 2024-10-04
"""

import unittest
import numpy as np
import tempfile
import os
from pathlib import Path
from typing import Dict, List
import yaml
import logging

# 禁用测试期间的日志输出
logging.getLogger().setLevel(logging.ERROR)

# 导入被测试的模块
from waternet.models.boundary_conditions import (
    BoundaryCondition, FlowBoundary, StageBoundary, RatingCurveBoundary,
    BoundaryConditionManager, BoundaryConditionConfig,
    create_time_series_function, create_periodic_function
)
from waternet.models.control_signals import (
    ControlDevice, GateDevice, PumpDevice, ValveDevice,
    ControlSignals, ControlSchedule, ControlSignalManager,
    create_gate_device, create_pump_device
)
from waternet.models.boundary_config import (
    ConfigValidator, BoundaryConfigParser, ControlConfigParser,
    ConfigFactory, load_boundary_config
)
from waternet.models.sparse_matrix import (
    SparsePattern, SparseJacobianBuilder, SparseSolver,
    analyze_system_sparsity
)
from waternet.models.adaptive_timestep import (
    TimeStepController, AdaptiveTimeStepConfig, ConvergenceMonitor,
    TimeStepStrategy, ConvergenceStatus
)


class TestBoundaryConditions(unittest.TestCase):
    """边界条件基础功能测试"""
    
    def setUp(self):
        """测试前置设置"""
        self.variables = {
            'H_upstream': 101.0,
            'H_downstream': 99.5,
            'Q_main': 50.0,
            'Q_branch': 20.0
        }
    
    def test_flow_boundary_constant(self):
        """测试恒定流量边界条件"""
        config = BoundaryConditionConfig("test_flow", "测试流量边界")
        flow_boundary = FlowBoundary("test_flow", "upstream", 45.0, config)
        
        # 测试基本功能
        self.assertEqual(flow_boundary.get_required_variables(), ['Q_upstream'])
        self.assertTrue(flow_boundary.is_enabled())
        
        # 测试方程生成
        variables = {'Q_upstream': 50.0}
        eq_name, residual = flow_boundary.get_equation(variables, 0.0)
        
        self.assertEqual(eq_name, "boundary_flow_upstream")
        self.assertAlmostEqual(residual, 5.0, places=6)  # 50.0 - 45.0
    
    def test_flow_boundary_time_varying(self):
        """测试时变流量边界条件"""
        # 创建时变函数
        time_func = create_time_series_function([0, 100, 200], [10, 20, 15])
        
        config = BoundaryConditionConfig("test_time_flow", "测试时变流量边界")
        flow_boundary = FlowBoundary("test_time_flow", "upstream", time_func, config)
        
        variables = {'Q_upstream': 18.0}
        
        # 测试不同时间点
        eq_name, residual = flow_boundary.get_equation(variables, 50.0)
        expected_flow = 15.0  # 在t=50时的插值结果
        self.assertAlmostEqual(residual, 3.0, places=1)  # 18.0 - 15.0
    
    def test_stage_boundary(self):
        """测试水位边界条件"""
        config = BoundaryConditionConfig("test_stage", "测试水位边界")
        stage_boundary = StageBoundary("test_stage", "downstream", 100.0, config)
        
        self.assertEqual(stage_boundary.get_required_variables(), ['H_downstream'])
        
        variables = {'H_downstream': 99.8}
        eq_name, residual = stage_boundary.get_equation(variables, 0.0)
        
        self.assertEqual(eq_name, "boundary_stage_downstream")
        self.assertAlmostEqual(residual, -0.2, places=6)  # 99.8 - 100.0
    
    def test_rating_curve_boundary(self):
        """测试水位流量关系边界条件"""
        config = BoundaryConditionConfig("test_rating", "测试水位流量关系")
        
        # 测试堰流公式
        curve_params = {
            'discharge_coefficient': 2.0,
            'reference_level': 99.0,
            'exponent': 1.5
        }
        rating_boundary = RatingCurveBoundary(
            "test_rating", "outlet", "outlet_stage", "weir", curve_params, config
        )
        
        variables = {'Q_outlet': 5.0, 'H_outlet_stage': 100.0}
        eq_name, residual = rating_boundary.get_equation(variables, 0.0)
        
        # 验证堰流公式: Q = C * (H - H0)^n = 2.0 * (100.0 - 99.0)^1.5 = 2.0
        expected_q = 2.0
        expected_residual = 5.0 - expected_q
        self.assertAlmostEqual(residual, expected_residual, places=3)
    
    def test_boundary_condition_manager(self):
        """测试边界条件管理器"""
        manager = BoundaryConditionManager()
        
        # 添加多个边界条件
        config1 = BoundaryConditionConfig("flow1", "流量边界1")
        flow_bc = FlowBoundary("flow1", "node1", 30.0, config1)
        
        config2 = BoundaryConditionConfig("stage1", "水位边界1")
        stage_bc = StageBoundary("stage1", "node2", 100.5, config2)
        
        manager.add_boundary_condition(flow_bc)
        manager.add_boundary_condition(stage_bc)
        
        self.assertEqual(len(manager), 2)
        self.assertEqual(manager.get_boundary_condition_count(), 2)
        
        # 测试批量方程生成
        variables = {'Q_node1': 35.0, 'H_node2': 100.2}
        equations = manager.get_all_equations(variables, 0.0)
        
        self.assertEqual(len(equations), 2)
        self.assertIn('boundary_flow_node1', equations)
        self.assertIn('boundary_stage_node2', equations)
        
        # 验证残差值
        self.assertAlmostEqual(equations['boundary_flow_node1'], 5.0, places=6)
        self.assertAlmostEqual(equations['boundary_stage_node2'], -0.3, places=6)


class TestControlSignals(unittest.TestCase):
    """控制信号功能测试"""
    
    def test_control_devices(self):
        """测试控制设备"""
        # 测试闸门设备
        gate = create_gate_device("gate1", 0.0, 1.0, 0.5)
        self.assertTrue(gate.validate_signal(0.8))
        self.assertFalse(gate.validate_signal(1.5))
        self.assertEqual(gate.apply_constraints(1.2), 1.0)
        self.assertEqual(gate.apply_constraints(-0.1), 0.0)
        
        # 测试泵站设备
        pump = create_pump_device("pump1", 0.0, 1.0, 0.0)
        self.assertEqual(pump.get_default_value(), 0.0)
        self.assertTrue(pump.is_enabled())
    
    def test_control_signals(self):
        """测试控制信号类"""
        signals = ControlSignals()
        
        # 测试信号设置和获取
        signals.set_signal("device1", 0.7)
        signals.set_signal("device2", 0.3)
        
        self.assertEqual(signals.get_signal("device1"), 0.7)
        self.assertEqual(signals.get_signal("device3", 0.5), 0.5)  # 默认值
        self.assertTrue(signals.has_signal("device1"))
        self.assertFalse(signals.has_signal("device3"))
        
        # 测试批量更新
        new_signals = {"device1": 0.9, "device3": 0.4}
        signals.update_signals(new_signals)
        self.assertEqual(signals.get_signal("device1"), 0.9)
        self.assertEqual(signals.get_signal("device3"), 0.4)
    
    def test_control_schedule(self):
        """测试控制调度表"""
        # 创建简单的时间序列调度
        data = {
            'time': [0, 60, 120],
            'device1': [0.0, 0.5, 1.0],
            'device2': [1.0, 0.8, 0.6]
        }
        schedule = ControlSchedule(data)
        
        # 测试时间插值
        signals_30 = schedule.get_signals_at_time(30.0)
        self.assertAlmostEqual(signals_30.get_signal("device1"), 0.25, places=2)
        self.assertAlmostEqual(signals_30.get_signal("device2"), 0.9, places=2)
        
        # 测试边界时间
        signals_0 = schedule.get_signals_at_time(0.0)
        self.assertEqual(signals_0.get_signal("device1"), 0.0)
        
        signals_150 = schedule.get_signals_at_time(150.0)
        self.assertEqual(signals_150.get_signal("device1"), 1.0)  # 超出范围，使用最后值
    
    def test_control_signal_manager(self):
        """测试控制信号管理器"""
        manager = ControlSignalManager()
        
        # 添加设备
        gate = create_gate_device("gate1", 0.0, 1.0, 0.5)
        pump = create_pump_device("pump1", 0.0, 1.0, 0.0)
        
        manager.add_device(gate)
        manager.add_device(pump)
        
        self.assertEqual(manager.get_device_count(), 2)
        self.assertEqual(manager.get_enabled_device_count(), 2)
        
        # 创建调度表
        data = {
            'time': [0, 100],
            'gate1': [0.3, 0.8],
            'pump1': [0.0, 0.6]
        }
        schedule = ControlSchedule(data)
        manager.set_schedule(schedule)
        
        # 测试信号获取
        signals = manager.get_signals_at_time(50.0)
        self.assertAlmostEqual(signals.get_signal("gate1"), 0.55, places=2)
        self.assertAlmostEqual(signals.get_signal("pump1"), 0.3, places=2)


class TestConfigurationParsing(unittest.TestCase):
    """配置解析功能测试"""
    
    def setUp(self):
        """测试前置设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / "test_config.yaml"
    
    def tearDown(self):
        """测试后清理"""
        if self.config_file.exists():
            self.config_file.unlink()
        os.rmdir(self.temp_dir)
    
    def test_config_validation(self):
        """测试配置验证"""
        validator = ConfigValidator()
        
        # 测试有效配置
        valid_config = {
            'boundary_conditions': [
                {
                    'name': 'test_flow',
                    'type': 'flow_boundary',
                    'node_name': 'upstream',
                    'flow_value': 50.0
                }
            ]
        }
        self.assertTrue(validator.validate_boundary_config(valid_config))
        
        # 测试无效配置
        invalid_config = {
            'boundary_conditions': [
                {
                    'name': 'test_flow',
                    'type': 'invalid_type',  # 无效类型
                    'node_name': 'upstream'
                }
            ]
        }
        self.assertFalse(validator.validate_boundary_config(invalid_config))
    
    def test_boundary_config_parsing(self):
        """测试边界条件配置解析"""
        config_data = {
            'boundary_conditions': [
                {
                    'name': 'upstream_flow',
                    'type': 'flow_boundary',
                    'node_name': 'upstream',
                    'flow_function': {
                        'type': 'constant',
                        'value': 45.0
                    }
                },
                {
                    'name': 'downstream_stage',
                    'type': 'stage_boundary',
                    'node_name': 'downstream',
                    'stage_value': 100.0
                }
            ]
        }
        
        # 保存配置到文件
        with open(self.config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f)
        
        # 解析配置
        parser = BoundaryConfigParser()
        manager = parser.parse_from_file(self.config_file)
        
        self.assertEqual(manager.get_boundary_condition_count(), 2)
        
        # 测试解析结果
        variables = {'Q_upstream': 50.0, 'H_downstream': 99.8}
        equations = manager.get_all_equations(variables, 0.0)
        
        self.assertEqual(len(equations), 2)
        self.assertAlmostEqual(equations['boundary_flow_upstream'], 5.0, places=6)
        self.assertAlmostEqual(equations['boundary_stage_downstream'], -0.2, places=6)
    
    def test_control_config_parsing(self):
        """测试控制配置解析"""
        control_config = {
            'devices': [
                {
                    'device_id': 'gate1',
                    'device_type': 'gate',
                    'min_value': 0.0,
                    'max_value': 1.0,
                    'default_value': 0.5
                }
            ],
            'schedule': {
                'type': 'step_schedule',
                'devices': ['gate1'],
                'step_times': [0, 100],
                'step_values': [
                    {'gate1': 0.3},
                    {'gate1': 0.8}
                ]
            }
        }
        
        parser = ControlConfigParser()
        manager = parser.parse_control_config(control_config)
        
        self.assertEqual(manager.get_device_count(), 1)
        
        # 测试调度执行
        signals = manager.get_signals_at_time(50.0)
        self.assertAlmostEqual(signals.get_signal("gate1"), 0.55, places=2)


class TestSparseMatrix(unittest.TestCase):
    """稀疏矩阵优化测试"""
    
    def test_sparse_pattern_analysis(self):
        """测试稀疏模式分析"""
        # 模拟简单的模型变量依赖
        class MockModel:
            def __init__(self, name, variables):
                self.name = name
                self._variables = variables
            
            def get_variable_names(self):
                return self._variables
            
            def get_equations(self, variables, dt, prev_states):
                return {f"eq_{var}": 0.0 for var in self._variables}
        
        models = [
            MockModel("model1", ["H_1", "Q_1"]),
            MockModel("model2", ["H_2", "Q_2", "Q_1"])  # Q_1 被共享
        ]
        
        variable_names = ["H_1", "Q_1", "H_2", "Q_2"]
        
        pattern_analyzer = SparsePattern()
        pattern, info = pattern_analyzer.analyze_pattern(models, variable_names)
        
        self.assertGreater(len(pattern), 0)
        self.assertEqual(info['n_variables'], 4)
        self.assertLessEqual(info['sparsity'], 1.0)
    
    def test_sparse_jacobian_builder(self):
        """测试稀疏雅可比构建器"""
        # 创建简单的稀疏模式
        pattern = {(0, 0), (0, 1), (1, 1), (1, 2)}
        matrix_shape = (3, 3)
        
        builder = SparseJacobianBuilder()
        builder.initialize_structure(pattern, matrix_shape)
        
        self.assertIsNotNone(builder.matrix_structure)
        self.assertEqual(builder.matrix_structure.shape, matrix_shape)


class TestAdaptiveTimeStep(unittest.TestCase):
    """自适应时间步测试"""
    
    def test_convergence_monitor(self):
        """测试收敛性监控"""
        config = AdaptiveTimeStepConfig()
        monitor = ConvergenceMonitor(config)
        
        # 测试收敛成功
        success_result = {
            'converged': True,
            'statistics': {
                'total_iterations': 5,
                'final_residual_norm': 1e-7
            }
        }
        status = monitor.assess_convergence(success_result)
        self.assertEqual(status, ConvergenceStatus.CONVERGED)
        
        # 测试收敛失败
        fail_result = {
            'converged': False,
            'statistics': {
                'total_iterations': 50,
                'convergence_history': [1.0, 0.8, 0.9, 1.2, 1.5]  # 发散趋势
            }
        }
        status = monitor.assess_convergence(fail_result)
        self.assertEqual(status, ConvergenceStatus.DIVERGED)
    
    def test_timestep_controller(self):
        """测试时间步长控制器"""
        config = AdaptiveTimeStepConfig(
            initial_dt=1.0,
            min_dt=0.1,
            max_dt=10.0,
            strategy=TimeStepStrategy.BALANCED
        )
        controller = TimeStepController(config)
        
        self.assertEqual(controller.get_current_timestep(), 1.0)
        
        # 测试收敛失败时的调整
        fail_result = {
            'converged': False,
            'statistics': {'total_iterations': 50, 'convergence_history': [1.0, 1.2]}
        }
        new_dt, info = controller.adjust_timestep(fail_result)
        
        self.assertLess(new_dt, 1.0)  # 时间步应该减小
        self.assertEqual(info['action'], 'reduce')
        
        # 测试连续成功后的调整
        success_result = {
            'converged': True,
            'statistics': {'total_iterations': 3, 'final_residual_norm': 1e-8}
        }
        
        # 模拟连续成功
        for _ in range(5):
            new_dt, info = controller.adjust_timestep(success_result, {})
        
        # 经过足够的成功步数后，时间步应该有增长的机会
        self.assertGreaterEqual(controller.consecutive_successes, 3)


class TestIntegration(unittest.TestCase):
    """集成测试"""
    
    def test_complete_boundary_system(self):
        """测试完整的边界条件系统"""
        # 创建边界条件管理器
        boundary_manager = BoundaryConditionManager()
        
        # 添加边界条件
        config1 = BoundaryConditionConfig("flow_bc", "测试流量边界")
        flow_bc = FlowBoundary("flow_bc", "upstream", 50.0, config1)
        boundary_manager.add_boundary_condition(flow_bc)
        
        config2 = BoundaryConditionConfig("stage_bc", "测试水位边界")
        stage_bc = StageBoundary("stage_bc", "downstream", 100.0, config2)
        boundary_manager.add_boundary_condition(stage_bc)
        
        # 创建控制信号管理器
        control_manager = ControlSignalManager()
        gate = create_gate_device("gate1", 0.0, 1.0, 0.5)
        control_manager.add_device(gate)
        
        # 测试系统协作
        variables = {
            'Q_upstream': 48.0,
            'H_downstream': 100.5
        }
        
        # 获取边界条件方程
        boundary_equations = boundary_manager.get_all_equations(variables, 0.0)
        self.assertEqual(len(boundary_equations), 2)
        
        # 获取控制信号
        control_signals = control_manager.get_signals_at_time(0.0)
        self.assertEqual(control_signals.get_signal("gate1"), 0.5)
        
        # 验证边界条件残差
        self.assertAlmostEqual(boundary_equations['boundary_flow_upstream'], -2.0, places=6)
        self.assertAlmostEqual(boundary_equations['boundary_stage_downstream'], 0.5, places=6)
    
    def test_config_to_system_integration(self):
        """测试配置到系统的完整集成"""
        # 创建临时配置文件
        config_data = {
            'boundary_conditions': [
                {
                    'name': 'test_flow',
                    'type': 'flow_boundary',
                    'node_name': 'inlet',
                    'flow_value': 30.0
                }
            ],
            'control_signals': {
                'devices': [
                    {
                        'device_id': 'valve1',
                        'device_type': 'valve',
                        'default_value': 0.8
                    }
                ]
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_file = f.name
        
        try:
            # 使用配置工厂创建系统
            factory = ConfigFactory()
            boundary_manager, control_manager = factory.create_from_config_file(temp_file)
            
            # 验证创建结果
            self.assertEqual(boundary_manager.get_boundary_condition_count(), 1)
            self.assertEqual(control_manager.get_device_count(), 1)
            
            # 验证功能
            variables = {'Q_inlet': 35.0}
            equations = boundary_manager.get_all_equations(variables, 0.0)
            self.assertAlmostEqual(equations['boundary_flow_inlet'], 5.0, places=6)
            
            signals = control_manager.get_signals_at_time(0.0)
            self.assertEqual(signals.get_signal("valve1"), 0.8)
            
        finally:
            os.unlink(temp_file)


class TestPerformance(unittest.TestCase):
    """性能测试"""
    
    def test_large_boundary_system_performance(self):
        """测试大规模边界条件系统性能"""
        import time
        
        # 创建大量边界条件
        boundary_manager = BoundaryConditionManager()
        n_boundaries = 100
        
        start_time = time.time()
        
        for i in range(n_boundaries):
            config = BoundaryConditionConfig(f"bc_{i}", f"边界条件{i}")
            flow_bc = FlowBoundary(f"bc_{i}", f"node_{i}", float(i), config)
            boundary_manager.add_boundary_condition(flow_bc)
        
        creation_time = time.time() - start_time
        
        # 创建大量变量
        variables = {f'Q_node_{i}': float(i + 10) for i in range(n_boundaries)}
        
        # 测试方程生成性能
        start_time = time.time()
        equations = boundary_manager.get_all_equations(variables, 0.0)
        equation_time = time.time() - start_time
        
        # 验证结果
        self.assertEqual(len(equations), n_boundaries)
        
        # 性能断言（这些阈值可以根据实际需要调整）
        self.assertLess(creation_time, 1.0, "边界条件创建时间过长")
        self.assertLess(equation_time, 0.5, "方程生成时间过长")
        
        print(f"性能测试结果:")
        print(f"  创建{n_boundaries}个边界条件: {creation_time:.3f}s")
        print(f"  生成{n_boundaries}个方程: {equation_time:.3f}s")


def run_all_tests():
    """运行所有测试"""
    # 创建测试套件
    test_classes = [
        TestBoundaryConditions,
        TestControlSignals,
        TestConfigurationParsing,
        TestSparseMatrix,
        TestAdaptiveTimeStep,
        TestIntegration,
        TestPerformance
    ]
    
    suite = unittest.TestSuite()
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 返回测试结果
    return result.wasSuccessful()


if __name__ == '__main__':
    # 设置日志级别
    logging.basicConfig(level=logging.INFO)
    
    print("开始运行边界条件框架综合测试...")
    print("=" * 60)
    
    success = run_all_tests()
    
    print("=" * 60)
    if success:
        print("✅ 所有测试通过！")
    else:
        print("❌ 部分测试失败，请检查日志。")
    
    print(f"测试完成。")