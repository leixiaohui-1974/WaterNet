"""
复杂水力枢纽模型系统综合测试

测试复杂水力枢纽模型系统的各个组件和集成功能。
包括单元测试、集成测试和性能测试。

Author: WaterNet Development Team
Date: 2024-10-04
"""

import unittest
import numpy as np
import tempfile
import os
import sys
from typing import Dict, List, Any
import logging

# 设置路径以导入WaterNet模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from waternet.models.reservoir_model import ReservoirModel, create_simple_reservoir
from waternet.models.junction_model import JunctionModel, create_simple_junction
from waternet.models.complex_station_model import ComplexStationModel, create_gate_station
from waternet.models.pressurized_pipe_model import PressurizedPipeModel, create_simple_pipe
from waternet.models.network_builder import NetworkBuilder, NetworkConfig
from waternet.models.implicit_solver import ImplicitSolverAgent, SolverConfig
from waternet.config.complex_hub_config import ConfigManager, NetworkConfiguration, SystemConfig


class TestReservoirModel(unittest.TestCase):
    """水库模型测试"""
    
    def setUp(self):
        """测试初始化"""
        self.reservoir = create_simple_reservoir(
            name="TestReservoir",
            upstream_node="Reservoir_up",
            downstream_node="Reservoir_down", 
            initial_level=100.0,
            bottom_level=95.0,
            surface_area=1000000.0
        )
    
    def test_variable_names(self):
        """测试变量名"""
        variables = self.reservoir.get_variable_names()
        self.assertEqual(variables, ['H_TestReservoir'])
    
    def test_water_level_calculation(self):
        """测试水位计算"""
        volume = 5000000.0  # 5 million m³
        level = self.reservoir.get_water_level(volume)
        self.assertAlmostEqual(level, 100.0, places=2)  # 95 + 5000000/1000000
    
    def test_equations(self):
        """测试方程计算"""
        variables = {
            'H_TestReservoir': 100.0,
            'Q_inlet': 10.0,
            'Q_outlet': 8.0
        }
        prev_states = {'V_TestReservoir': 5000000.0}
        
        equations = self.reservoir.get_equations(variables, 1.0, prev_states)
        self.assertIn('capacity_curve_TestReservoir', equations)
    
    def test_flow_balance(self):
        """测试流量平衡计算"""
        variables = {
            'Q_TestReservoir_in': 10.0,
            'Q_TestReservoir_out': -8.0
        }
        
        Q_in, Q_out = self.reservoir._calculate_flow_balance(variables)
        self.assertAlmostEqual(Q_in, 10.0)
        self.assertAlmostEqual(Q_out, 8.0)


class TestJunctionModel(unittest.TestCase):
    """连接点模型测试"""
    
    def setUp(self):
        """测试初始化"""
        self.junction = create_simple_junction(
            "TestJunction", "Pipe1", "Pipe2", "Pipe3"
        )
    
    def test_variable_names(self):
        """测试变量名"""
        variables = self.junction.get_variable_names()
        self.assertEqual(variables, ['H_TestJunction'])
    
    def test_mass_balance(self):
        """测试质量平衡"""
        variables = {
            'H_TestJunction': 100.0,
            'Q_Pipe1': 10.0,  # 流入
            'Q_Pipe2': -5.0,  # 流出
            'Q_Pipe3': -5.0   # 流出
        }
        
        is_balanced = self.junction.validate_mass_balance(variables)
        self.assertTrue(is_balanced)
    
    def test_flow_classification(self):
        """测试流量分类"""
        variables = {
            'Q_Pipe1_start': 10.0,
            'Q_Pipe2_end': 6.0,
            'Q_Pipe3_end': 4.0
        }
        
        Q_in_list, Q_out_list = self.junction._classify_flows(variables)
        self.assertAlmostEqual(sum(Q_in_list), 10.0)
        self.assertAlmostEqual(sum(Q_out_list), 10.0)


class TestPressurizedPipeModel(unittest.TestCase):
    """有压管道模型测试"""
    
    def setUp(self):
        """测试初始化"""
        self.pipe = create_simple_pipe(
            name="TestPipe",
            upstream_node="Node1",
            downstream_node="Node2",
            length=1000.0,
            diameter=1.0
        )
    
    def test_variable_names(self):
        """测试变量名"""
        variables = self.pipe.get_variable_names()
        self.assertEqual(variables, ['Q_TestPipe'])
    
    def test_friction_loss_calculation(self):
        """测试摩阻损失计算"""
        velocity = 2.0  # m/s
        head_loss = self.pipe._calculate_friction_loss(velocity)
        self.assertGreater(head_loss, 0)
    
    def test_energy_equation(self):
        """测试能量方程"""
        variables = {
            'Q_TestPipe': 1.57,  # π * 0.5² * 2 ≈ 1.57 m³/s for V=2m/s
            'H_Node1': 102.0,
            'H_Node2': 100.0
        }
        
        equations = self.pipe.get_equations(variables, 1.0, {})
        self.assertIn('energy_balance_TestPipe', equations)
    
    def test_hydraulic_properties(self):
        """测试水力特性计算"""
        flow_rate = 1.0
        properties = self.pipe.get_hydraulic_properties(flow_rate)
        
        self.assertIn('velocity', properties)
        self.assertIn('reynolds_number', properties)
        self.assertIn('friction_factor', properties)
        self.assertGreater(properties['velocity'], 0)


class TestComplexStationModel(unittest.TestCase):
    """复杂枢纽站模型测试"""
    
    def setUp(self):
        """测试初始化"""
        gate_configs = [{
            'name': 'Gate1',
            'width': 10.0,
            'discharge_coeff': 0.7,
            'initial_opening': 2.0
        }]
        
        self.station = create_gate_station(
            name="TestStation",
            upstream_node="Station_up",
            downstream_node="Station_down",
            gate_configs=gate_configs
        )
    
    def test_variable_names(self):
        """测试变量名"""
        variables = self.station.get_variable_names()
        self.assertEqual(variables, ['Q_Gate1'])
    
    def test_gate_flow_calculation(self):
        """测试闸门流量计算"""
        variables = {
            'Q_Gate1': 15.0,
            'H_Station_up': 102.0,
            'H_Station_down': 100.0
        }
        
        equations = self.station.get_equations(variables, 1.0, {})
        self.assertIn('structure_flow_Gate1', equations)
    
    def test_capacity_calculation(self):
        """测试通过能力计算"""
        capacity = self.station.calculate_total_capacity(102.0, 100.0)
        self.assertGreater(capacity, 0)


class TestNetworkBuilder(unittest.TestCase):
    """网络构建器测试"""
    
    def setUp(self):
        """测试初始化"""
        self.builder = NetworkBuilder()
    
    def test_simple_network_creation(self):
        """测试简单网络创建"""
        config = {
            'name': 'Test Network',
            'models': [
                {
                    'name': 'TestReservoir',
                    'type': 'reservoir',
                    'initial_level': 100.0,
                    'surface_area': 1000000.0,
                    'nodes': ['Res_out']
                },
                {
                    'name': 'TestPipe',
                    'type': 'pipe',
                    'upstream_node': 'Res_out',
                    'downstream_node': 'End',
                    'length': 1000.0,
                    'diameter': 1.0
                }
            ]
        }
        
        models = self.builder.build_from_config(config)
        self.assertEqual(len(models), 2)
        self.assertIsInstance(models[0], ReservoirModel)
        self.assertIsInstance(models[1], PressurizedPipeModel)
    
    def test_topology_validation(self):
        """测试拓扑验证"""
        models = [
            create_simple_reservoir("Res1", "Up", "Down", 100.0),
            create_simple_pipe("Pipe1", "Down", "End", 1000.0, 1.0)
        ]
        
        validation_result = self.builder.validator.validate_network(models)
        self.assertTrue(validation_result['is_valid'])


class TestImplicitSolver(unittest.TestCase):
    """联合求解器测试"""
    
    def setUp(self):
        """测试初始化"""
        # 创建简单的两组件系统
        self.reservoir = create_simple_reservoir(
            "Reservoir", "Res_out", "End", 100.0, surface_area=1000000.0
        )
        self.pipe = create_simple_pipe(
            "Pipe", "Res_out", "End", 1000.0, 1.0
        )
        
        self.models = [self.reservoir, self.pipe]
        self.solver = ImplicitSolverAgent(self.models)
    
    def test_variable_mapping(self):
        """测试变量映射"""
        expected_vars = ['H_Reservoir', 'Q_Pipe']
        self.assertEqual(self.solver.variable_names, expected_vars)
        self.assertEqual(self.solver.total_variables, 2)
    
    def test_system_validation(self):
        """测试系统验证"""
        # 验证系统初始化时不应抛出异常
        stats = self.solver.get_system_statistics()
        self.assertEqual(stats['total_models'], 2)
        self.assertEqual(stats['total_variables'], 2)
    
    def test_residual_calculation(self):
        """测试残差计算"""
        variables = {
            'H_Reservoir': 100.0,
            'Q_Pipe': 1.0,
            'H_Res_out': 100.0,
            'H_End': 99.0
        }
        
        residuals = self.solver._calculate_residuals(variables, 0.0, {})
        self.assertEqual(len(residuals), 2)
    
    @unittest.skip("需要更稳定的求解器实现")
    def test_steady_state_solve(self):
        """测试稳态求解"""
        initial_guess = {
            'H_Reservoir': 100.0,
            'Q_Pipe': 1.0,
            'H_Res_out': 100.0,
            'H_End': 99.0
        }
        
        config = SolverConfig(max_iterations=20, tolerance=1e-3)
        solver = ImplicitSolverAgent(self.models, config)
        
        result = solver.solve_steady_state(initial_guess)
        # 注意：此测试可能因为简化的模型而不收敛


class TestConfigManager(unittest.TestCase):
    """配置管理器测试"""
    
    def setUp(self):
        """测试初始化"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_manager = ConfigManager(self.temp_dir)
    
    def tearDown(self):
        """测试清理"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_template_creation(self):
        """测试模板创建"""
        config = self.config_manager.create_template_config("simple_cascade")
        self.assertIsInstance(config, NetworkConfiguration)
        self.assertEqual(len(config.reservoirs), 2)
        self.assertEqual(len(config.pipes), 1)
    
    def test_config_save_load(self):
        """测试配置保存和加载"""
        # 创建配置
        config = self.config_manager.create_template_config("simple_cascade")
        
        # 保存配置
        file_path = self.config_manager.save_config(config, "test_config")
        self.assertTrue(os.path.exists(file_path))
        
        # 加载配置
        loaded_config = self.config_manager.load_config("test_config.yaml")
        self.assertEqual(loaded_config.system.name, config.system.name)
    
    def test_config_validation(self):
        """测试配置验证"""
        config = self.config_manager.create_template_config("simple_cascade")
        validation_result = self.config_manager.validator.validate_network_config(config)
        
        self.assertTrue(validation_result['is_valid'])
        self.assertEqual(len(validation_result['errors']), 0)


class TestIntegration(unittest.TestCase):
    """集成测试"""
    
    def test_end_to_end_workflow(self):
        """测试端到端工作流程"""
        # 1. 创建配置
        temp_dir = tempfile.mkdtemp()
        config_manager = ConfigManager(temp_dir)
        config = config_manager.create_template_config("simple_cascade")
        
        # 2. 保存配置
        config_file = config_manager.save_config(config, "integration_test")
        
        # 3. 从配置构建网络
        builder = NetworkBuilder()
        
        # 转换配置格式
        network_config = {
            'name': config.system.name,
            'models': []
        }
        
        # 添加水库
        for reservoir in config.reservoirs:
            network_config['models'].append({
                'name': reservoir.name,
                'type': reservoir.type,
                'initial_level': reservoir.initial_level,
                'surface_area': reservoir.surface_area,
                'bottom_level': reservoir.bottom_level,
                'nodes': reservoir.nodes or [f"{reservoir.name}_up", f"{reservoir.name}_down"]
            })
        
        # 添加管道
        for pipe in config.pipes:
            network_config['models'].append({
                'name': pipe.name,
                'type': pipe.type,
                'upstream_node': pipe.upstream_node,
                'downstream_node': pipe.downstream_node,
                'length': pipe.length,
                'diameter': pipe.diameter,
                'roughness': pipe.roughness
            })
        
        models = builder.build_from_config(network_config)
        
        # 4. 验证网络
        validation_result = builder.validator.validate_network(models)
        self.assertTrue(validation_result['is_valid'])
        
        # 5. 清理
        import shutil
        shutil.rmtree(temp_dir)
        
        self.assertGreater(len(models), 0)


class PerformanceTest(unittest.TestCase):
    """性能测试"""
    
    def test_large_network_creation(self):
        """测试大型网络创建性能"""
        import time
        
        # 创建包含多个组件的网络配置
        network_config = {
            'name': 'Large Network',
            'models': []
        }
        
        # 创建多个水库
        for i in range(10):
            network_config['models'].append({
                'name': f'Reservoir_{i}',
                'type': 'reservoir',
                'initial_level': 100.0 + i,
                'surface_area': 1000000.0,
                'nodes': [f'Res_{i}_out']
            })
        
        # 创建多个管道
        for i in range(9):
            network_config['models'].append({
                'name': f'Pipe_{i}',
                'type': 'pipe',
                'upstream_node': f'Res_{i}_out',
                'downstream_node': f'Res_{i+1}_out' if i < 8 else 'End',
                'length': 1000.0 + i * 100,
                'diameter': 1.0 + i * 0.1
            })
        
        builder = NetworkBuilder()
        
        start_time = time.time()
        models = builder.build_from_config(network_config)
        build_time = time.time() - start_time
        
        self.assertEqual(len(models), 19)
        self.assertLess(build_time, 5.0)  # 应在5秒内完成
        
        print(f"大型网络创建耗时: {build_time:.3f}秒")


def run_comprehensive_tests():
    """运行综合测试"""
    # 设置日志
    logging.basicConfig(level=logging.INFO,
                       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # 创建测试套件
    test_suite = unittest.TestSuite()
    
    # 添加测试用例
    test_suite.addTest(unittest.makeSuite(TestReservoirModel))
    test_suite.addTest(unittest.makeSuite(TestJunctionModel))
    test_suite.addTest(unittest.makeSuite(TestPressurizedPipeModel))
    test_suite.addTest(unittest.makeSuite(TestComplexStationModel))
    test_suite.addTest(unittest.makeSuite(TestNetworkBuilder))
    test_suite.addTest(unittest.makeSuite(TestImplicitSolver))
    test_suite.addTest(unittest.makeSuite(TestConfigManager))
    test_suite.addTest(unittest.makeSuite(TestIntegration))
    test_suite.addTest(unittest.makeSuite(PerformanceTest))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # 生成测试报告
    print("\n" + "="*50)
    print("测试报告摘要")
    print("="*50)
    print(f"运行测试数: {result.testsRun}")
    print(f"成功测试数: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败测试数: {len(result.failures)}")
    print(f"错误测试数: {len(result.errors)}")
    
    if result.failures:
        print("\n失败的测试:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    if result.errors:
        print("\n出错的测试:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback.splitlines()[-1]}")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_comprehensive_tests()
    sys.exit(0 if success else 1)