"""
水力控制结构单元测试

本测试模块验证所有水力控制结构模型的功能正确性和数值稳定性。
测试涵盖正常工况、边界条件、异常处理等多个方面。
"""

import unittest
import math
from typing import List

# 导入被测试的模块
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from physical_objects.control_structure import (
    ControlStructure,
    GateModel,
    PumpModel,
    ValveModel,
    TurbineModel
)


class DummyControlStructure(ControlStructure):
    """用于测试抽象基类的虚拟实现"""
    
    def get_flow(self, H_up: float, H_down: float, setting: float) -> float:
        return max(0.0, setting)


class TestControlStructures(unittest.TestCase):
    """测试抽象基类ControlStructure"""
    
    def test_abstract_interface(self):
        """测试抽象接口不能直接实例化"""
        with self.assertRaises(TypeError):
            ControlStructure("test")
    
    def test_dummy_structure(self):
        """测试虚拟控制结构实现"""
        dummy = DummyControlStructure("test_dummy")
        self.assertEqual(dummy.name, "test_dummy")
        self.assertEqual(dummy.get_flow(10.0, 5.0, 2.5), 2.5)
        self.assertEqual(dummy.get_flow(10.0, 5.0, -1.0), 0.0)
    
    def test_invalid_name(self):
        """测试无效名称参数"""
        with self.assertRaises(ValueError):
            DummyControlStructure("")
        with self.assertRaises(ValueError):
            DummyControlStructure("   ")
        with self.assertRaises(ValueError):
            DummyControlStructure(123)  # type: ignore


class TestGateModel(unittest.TestCase):
    """测试闸门模型GateModel"""
    
    def setUp(self):
        """设置测试用例"""
        self.gate = GateModel("test_gate", discharge_coeff=0.8, width=5.0)
    
    def test_gate_normal_flow(self):
        """测试闸门正常流量计算"""
        # 验证案例：宽度5m，开度1.5m，流量系数0.8，水头差2m
        # Q = 0.8 × (5.0 × 1.5) × √(2 × 9.81 × 2.0) ≈ 37.6 m³/s
        flow = self.gate.get_flow(H_up=22.0, H_down=20.0, setting=1.5)
        expected_flow = 0.8 * (5.0 * 1.5) * math.sqrt(2 * 9.81 * 2.0)
        self.assertAlmostEqual(flow, expected_flow, places=2)
        self.assertAlmostEqual(flow, 37.6, places=1)
    
    def test_gate_zero_head_diff(self):
        """测试零水头差情况"""
        flow = self.gate.get_flow(H_up=20.0, H_down=20.0, setting=1.5)
        self.assertEqual(flow, 0.0)
        
        flow = self.gate.get_flow(H_up=19.0, H_down=20.0, setting=1.5)
        self.assertEqual(flow, 0.0)
    
    def test_gate_zero_opening(self):
        """测试闸门关闭情况"""
        flow = self.gate.get_flow(H_up=22.0, H_down=20.0, setting=0.0)
        self.assertEqual(flow, 0.0)
        
        flow = self.gate.get_flow(H_up=22.0, H_down=20.0, setting=-1.0)
        self.assertEqual(flow, 0.0)
    
    def test_gate_parameters(self):
        """测试闸门参数验证"""
        # 测试正常参数
        gate = GateModel("normal_gate", 0.75, 3.0)
        self.assertEqual(gate.name, "normal_gate")
        self.assertEqual(gate.discharge_coeff, 0.75)
        self.assertEqual(gate.width, 3.0)
        
        # 测试无效参数
        with self.assertRaises(ValueError):
            GateModel("invalid", 0.0, 5.0)  # 流量系数为0
        with self.assertRaises(ValueError):
            GateModel("invalid", 1.5, 5.0)  # 流量系数>1
        with self.assertRaises(ValueError):
            GateModel("invalid", 0.8, 0.0)  # 宽度为0
        with self.assertRaises(ValueError):
            GateModel("invalid", 0.8, -1.0)  # 宽度为负


class TestPumpModel(unittest.TestCase):
    """测试水泵模型PumpModel"""
    
    def setUp(self):
        """设置测试用例"""
        # 特性曲线：H = 100 - 0.1Q²
        self.pump = PumpModel("test_pump", pump_curve_coeffs=[100.0, 0.0, -0.1])
    
    def test_pump_working_point(self):
        """测试水泵工作点求解"""
        # 验证案例：H_up=20m，H_down=110m，需求扬程=90m
        # 工作点：100 - 0.1Q² = 90，解得Q = 10 m³/s
        flow = self.pump.get_flow(H_up=20.0, H_down=110.0, setting=1.0)
        self.assertAlmostEqual(flow, 10.0, places=1)
    
    def test_pump_off_condition(self):
        """测试水泵停机条件"""
        flow = self.pump.get_flow(H_up=20.0, H_down=110.0, setting=0.0)
        self.assertEqual(flow, 0.0)
    
    def test_pump_over_head(self):
        """测试超过零流量扬程的情况"""
        # 当需求扬程≥零流量扬程时，流量应为0
        flow = self.pump.get_flow(H_up=20.0, H_down=130.0, setting=1.0)  # 需求扬程=110m > 100m
        self.assertEqual(flow, 0.0)
    
    def test_pump_linear_curve(self):
        """测试线性特性曲线"""
        # H = 50 - 2Q
        linear_pump = PumpModel("linear_pump", [50.0, -2.0])
        flow = linear_pump.get_flow(H_up=10.0, H_down=40.0, setting=1.0)  # 需求扬程=30m
        # 50 - 2Q = 30，解得Q = 10
        self.assertAlmostEqual(flow, 10.0, places=1)
    
    def test_pump_parameters(self):
        """测试水泵参数验证"""
        # 测试正常参数
        pump = PumpModel("normal_pump", [80.0, -0.05])
        self.assertEqual(pump.name, "normal_pump")
        self.assertEqual(pump.pump_curve_coeffs, [80.0, -0.05])
        
        # 测试无效参数
        with self.assertRaises(ValueError):
            PumpModel("invalid", [])  # 空系数列表
        with self.assertRaises(ValueError):
            PumpModel("invalid", ["a", "b"])  # 非数值系数


class TestValveModel(unittest.TestCase):
    """测试阀门模型ValveModel"""
    
    def setUp(self):
        """设置测试用例"""
        self.valve = ValveModel("test_valve", valve_coeff=25.0)
    
    def test_valve_flow_calculation(self):
        """测试阀门流量计算"""
        # 验证案例：K_v=25.0，开度0.25，水头差4m
        # Q = (25.0 × √0.25) × √4.0 = 25.0 m³/s
        flow = self.valve.get_flow(H_up=24.0, H_down=20.0, setting=0.25)
        expected_flow = 25.0 * math.sqrt(0.25) * math.sqrt(4.0)
        self.assertAlmostEqual(flow, expected_flow, places=2)
        self.assertAlmostEqual(flow, 25.0, places=1)
    
    def test_valve_opening_effect(self):
        """测试阀门开度影响"""
        # 全开 vs 半开
        flow_full = self.valve.get_flow(H_up=21.0, H_down=20.0, setting=1.0)
        flow_half = self.valve.get_flow(H_up=21.0, H_down=20.0, setting=0.25)
        
        # 流量应该随开度的平方根变化
        ratio = flow_full / flow_half
        expected_ratio = math.sqrt(1.0) / math.sqrt(0.25)  # = 2.0
        self.assertAlmostEqual(ratio, expected_ratio, places=2)
    
    def test_valve_closed(self):
        """测试阀门关闭情况"""
        flow = self.valve.get_flow(H_up=21.0, H_down=20.0, setting=0.0)
        self.assertEqual(flow, 0.0)
        
        flow = self.valve.get_flow(H_up=21.0, H_down=20.0, setting=-0.5)
        self.assertEqual(flow, 0.0)
    
    def test_valve_zero_head_diff(self):
        """测试零水头差情况"""
        flow = self.valve.get_flow(H_up=20.0, H_down=20.0, setting=0.5)
        self.assertEqual(flow, 0.0)
        
        flow = self.valve.get_flow(H_up=19.0, H_down=20.0, setting=0.5)
        self.assertEqual(flow, 0.0)
    
    def test_valve_opening_limits(self):
        """测试开度限制"""
        # 测试超过1.0的开度被限制
        flow_over = self.valve.get_flow(H_up=21.0, H_down=20.0, setting=1.5)
        flow_max = self.valve.get_flow(H_up=21.0, H_down=20.0, setting=1.0)
        self.assertAlmostEqual(flow_over, flow_max, places=5)
    
    def test_valve_parameters(self):
        """测试阀门参数验证"""
        # 测试正常参数
        valve = ValveModel("normal_valve", 15.0)
        self.assertEqual(valve.name, "normal_valve")
        self.assertEqual(valve.valve_coeff, 15.0)
        
        # 测试无效参数
        with self.assertRaises(ValueError):
            ValveModel("invalid", 0.0)  # 系数为0
        with self.assertRaises(ValueError):
            ValveModel("invalid", -5.0)  # 系数为负


class TestTurbineModel(unittest.TestCase):
    """测试水轮机模型TurbineModel"""
    
    def setUp(self):
        """设置测试用例"""
        self.turbine = TurbineModel("test_turbine")
    
    def test_turbine_flow_control(self):
        """测试水轮机流量控制"""
        # 流量控制模式下，输出应等于设定值
        flow = self.turbine.get_flow(H_up=120.0, H_down=20.0, setting=85.0)
        self.assertEqual(flow, 85.0)
        
        flow = self.turbine.get_flow(H_up=120.0, H_down=20.0, setting=50.0)
        self.assertEqual(flow, 50.0)
    
    def test_turbine_negative_setting(self):
        """测试负流量设定"""
        flow = self.turbine.get_flow(H_up=120.0, H_down=20.0, setting=-10.0)
        self.assertEqual(flow, 0.0)
        
        flow = self.turbine.get_flow(H_up=120.0, H_down=20.0, setting=0.0)
        self.assertEqual(flow, 0.0)
    
    def test_turbine_power_calculation(self):
        """测试水轮机功率计算"""
        # 验证案例：水头100m，流量85 m³/s，效率90%
        # P = 9.81 × 85.0 × 100 × 0.9 = 75046.5 kW
        power = self.turbine.get_power(H_up=120.0, H_down=20.0, Q=85.0, efficiency=0.9)
        expected_power = 9.81 * 85.0 * 100.0 * 0.9
        self.assertAlmostEqual(power, expected_power, places=1)
        self.assertAlmostEqual(power, 75046.5, places=0)
    
    def test_turbine_power_edge_cases(self):
        """测试功率计算的边界情况"""
        # 零流量
        power = self.turbine.get_power(H_up=120.0, H_down=20.0, Q=0.0, efficiency=0.9)
        self.assertEqual(power, 0.0)
        
        # 零效率
        power = self.turbine.get_power(H_up=120.0, H_down=20.0, Q=85.0, efficiency=0.0)
        self.assertEqual(power, 0.0)
        
        # 零水头差
        power = self.turbine.get_power(H_up=20.0, H_down=20.0, Q=85.0, efficiency=0.9)
        self.assertEqual(power, 0.0)
        
        # 负水头差
        power = self.turbine.get_power(H_up=19.0, H_down=20.0, Q=85.0, efficiency=0.9)
        self.assertEqual(power, 0.0)
    
    def test_turbine_efficiency_limits(self):
        """测试效率限制"""
        # 测试超过1.0的效率被限制
        power_over = self.turbine.get_power(H_up=120.0, H_down=20.0, Q=85.0, efficiency=1.5)
        power_max = self.turbine.get_power(H_up=120.0, H_down=20.0, Q=85.0, efficiency=1.0)
        self.assertAlmostEqual(power_over, power_max, places=5)


class TestIntegration(unittest.TestCase):
    """集成测试：验证不同模型之间的兼容性"""
    
    def test_polymorphism(self):
        """测试多态性：所有模型都遵循统一接口"""
        structures: List[ControlStructure] = [
            GateModel("gate", 0.8, 5.0),
            PumpModel("pump", [100.0, 0.0, -0.1]),
            ValveModel("valve", 25.0),
            TurbineModel("turbine")
        ]
        
        # 所有结构都应该有name属性和get_flow方法
        for structure in structures:
            self.assertIsInstance(structure.name, str)
            self.assertTrue(hasattr(structure, 'get_flow'))
            
            # 调用get_flow方法应该返回数值
            flow = structure.get_flow(H_up=21.0, H_down=20.0, setting=1.0)
            self.assertIsInstance(flow, (int, float))
            self.assertGreaterEqual(flow, 0.0)
    
    def test_system_scenario(self):
        """测试系统级应用场景"""
        # 模拟一个简单的水力系统：上游水库 -> 闸门 -> 渠道 -> 水轮机
        
        # 上游水库水位
        H_reservoir = 150.0
        
        # 闸门控制
        gate = GateModel("intake_gate", 0.8, 3.0)
        gate_flow = gate.get_flow(H_up=H_reservoir, H_down=148.0, setting=1.2)
        
        # 渠道末端（水轮机前）水位
        H_turbine_inlet = 100.0
        
        # 水轮机发电
        turbine = TurbineModel("generator")
        turbine_flow = turbine.get_flow(H_up=H_turbine_inlet, H_down=50.0, setting=gate_flow)
        power = turbine.get_power(H_up=H_turbine_inlet, H_down=50.0, Q=turbine_flow, efficiency=0.88)
        
        # 验证结果合理性
        self.assertGreater(gate_flow, 0.0)
        self.assertEqual(turbine_flow, gate_flow)  # 流量守恒
        self.assertGreater(power, 0.0)
        
        print(f"系统测试结果：")
        print(f"  闸门流量: {gate_flow:.2f} m³/s")
        print(f"  水轮机流量: {turbine_flow:.2f} m³/s")
        print(f"  发电功率: {power:.0f} kW")


if __name__ == '__main__':
    # 配置测试运行
    unittest.main(verbosity=2)