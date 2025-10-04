"""
实际水力网络仿真验证框架

基于真实工程案例验证边界条件框架性能和适用性
包括多种典型水利工程场景的完整仿真验证

Author: WaterNet Development Team
Date: 2024-10-04
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Tuple
import psutil
import tracemalloc

# 导入WaterNet核心模块和边界条件框架
from waternet.models.boundary_conditions import *
from waternet.models.control_signals import *
from waternet.models.boundary_config import *
from waternet.models.implicit_solver import *
from waternet.models.adaptive_timestep import *
from waternet.models.sparse_matrix import *
from waternet.interfaces.hydro_model import DummyModel

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RealNetworkValidator:
    """实际水力网络验证器"""
    
    def __init__(self):
        self.results = {}
        self.performance_metrics = {}
        
    def create_urban_drainage_network(self) -> Tuple[List, BoundaryConditionManager, ControlSignalManager]:
        """创建城市排水网络案例"""
        logger.info("构建城市排水网络仿真案例")
        
        # 创建网络模型 - 简化的管网系统
        models = [
            DummyModel("main_pipe", "inlet", "junction1", k=0.9, b=0.0),
            DummyModel("branch1", "junction1", "outlet1", k=1.2, b=-0.1),
            DummyModel("branch2", "junction1", "outlet2", k=0.8, b=0.05),
            DummyModel("pump_line", "junction1", "reservoir", k=2.0, b=0.0)
        ]
        
        # 边界条件 - 模拟降雨径流入流
        boundary_manager = BoundaryConditionManager()
        
        # 时变入流边界
        rainfall_pattern = create_time_series_function(
            [0, 900, 1800, 2700, 3600, 4500, 5400, 7200],
            [5, 15, 35, 50, 40, 25, 15, 8],
            "linear"
        )
        
        config1 = BoundaryConditionConfig("rainfall_inflow", "降雨径流入流")
        inflow_bc = FlowBoundary("rainfall_inflow", "inlet", rainfall_pattern, config1)
        boundary_manager.add_boundary_condition(inflow_bc)
        
        # 出口水位边界
        config2 = BoundaryConditionConfig("downstream_level", "下游河道水位")
        level_bc = StageBoundary("downstream_level", "outlet1", 98.5, config2)
        boundary_manager.add_boundary_condition(level_bc)
        
        # 控制信号管理
        control_manager = ControlSignalManager()
        
        # 排水泵站控制
        pump = create_pump_device("drainage_pump", 0.0, 1.0, 0.0)
        control_manager.add_device(pump)
        
        # 闸门控制
        gate = create_gate_device("regulating_gate", 0.0, 1.0, 0.8)
        control_manager.add_device(gate)
        
        # 控制调度 - 防洪调度方案
        control_schedule = ControlSchedule.create_step_schedule(
            devices=['drainage_pump', 'regulating_gate'],
            step_times=[0, 1800, 3600, 5400],
            step_values=[
                {'drainage_pump': 0.0, 'regulating_gate': 0.8},
                {'drainage_pump': 0.3, 'regulating_gate': 0.6},
                {'drainage_pump': 0.8, 'regulating_gate': 0.4},
                {'drainage_pump': 0.5, 'regulating_gate': 0.6}
            ]
        )
        control_manager.set_schedule(control_schedule)
        
        return models, boundary_manager, control_manager
    
    def create_irrigation_canal_system(self) -> Tuple[List, BoundaryConditionManager, ControlSignalManager]:
        """创建灌溉渠系案例"""
        logger.info("构建灌溉渠系仿真案例")
        
        # 渠系网络
        models = [
            DummyModel("main_canal", "source", "diversion1", k=1.0, b=0.0),
            DummyModel("secondary1", "diversion1", "field1", k=0.7, b=0.02),
            DummyModel("secondary2", "diversion1", "field2", k=0.8, b=0.01),
            DummyModel("tertiary1", "diversion1", "field3", k=0.6, b=0.03)
        ]
        
        # 边界条件
        boundary_manager = BoundaryConditionManager()
        
        # 水源供水边界
        supply_func = create_periodic_function(
            amplitude=10.0, period=43200.0, offset=40.0, phase=0.0  # 12小时周期
        )
        config1 = BoundaryConditionConfig("water_supply", "水源供水")
        supply_bc = FlowBoundary("water_supply", "source", supply_func, config1)
        boundary_manager.add_boundary_condition(supply_bc)
        
        # 农田需水边界 - 蒸散发损失
        evap_pattern = create_time_series_function(
            [0, 21600, 43200, 64800, 86400],  # 24小时
            [2, 8, 12, 6, 2],
            "cubic"
        )
        config2 = BoundaryConditionConfig("field_demand", "农田需水")
        demand_bc = FlowBoundary("field_demand", "field1", evap_pattern, config2)
        boundary_manager.add_boundary_condition(demand_bc)
        
        # 控制设备
        control_manager = ControlSignalManager()
        
        # 分水闸控制
        diversion_gate = create_gate_device("diversion_gate", 0.0, 1.0, 0.5)
        control_manager.add_device(diversion_gate)
        
        # 田间闸门
        field_gates = [
            create_gate_device(f"field_gate_{i}", 0.0, 1.0, 0.6) 
            for i in range(1, 4)
        ]
        for gate in field_gates:
            control_manager.add_device(gate)
        
        return models, boundary_manager, control_manager
    
    def run_validation_scenario(self, scenario_name: str, models: List, 
                              boundary_manager: BoundaryConditionManager,
                              control_manager: ControlSignalManager) -> Dict[str, Any]:
        """运行验证场景"""
        logger.info(f"开始验证场景: {scenario_name}")
        
        # 性能监控
        tracemalloc.start()
        start_time = time.time()
        process = psutil.Process()
        memory_before = process.memory_info().rss / 1024 / 1024  # MB
        
        try:
            # 创建求解器
            solver = create_boundary_solver(
                models=models,
                boundary_conditions=list(boundary_manager.boundary_conditions.values()),
                control_devices=list(control_manager.devices.values())
            )
            
            # 初始条件
            initial_conditions = {}
            for i, model in enumerate(models):
                for var in model.get_variable_names():
                    if var.startswith('H_'):
                        initial_conditions[var] = 100.0 + i * 0.1
                    elif var.startswith('Q_'):
                        initial_conditions[var] = 20.0 + i * 2.0
            
            # 稳态求解
            steady_result = solver.solve_steady_state(initial_conditions)
            
            # 瞬态求解
            time_steps = np.arange(0, 7200, 300)  # 2小时，步长5分钟
            dt = 300.0
            
            transient_results = solver.solve_time_series(
                time_steps=time_steps,
                dt=dt,
                initial_conditions=steady_result['variables']
            )
            
            # 性能统计
            end_time = time.time()
            memory_after = process.memory_info().rss / 1024 / 1024  # MB
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            
            # 收集结果
            result = {
                'scenario': scenario_name,
                'steady_converged': steady_result['converged'],
                'steady_iterations': steady_result['statistics'].total_iterations,
                'transient_steps': len(transient_results),
                'transient_success_rate': sum(1 for r in transient_results if r['converged']) / len(transient_results),
                'total_time': end_time - start_time,
                'memory_usage': memory_after - memory_before,
                'peak_memory': peak / 1024 / 1024,  # MB
                'boundary_conditions': boundary_manager.get_boundary_condition_count(),
                'control_devices': control_manager.get_device_count(),
                'variables_count': len(initial_conditions)
            }
            
            logger.info(f"场景 {scenario_name} 验证完成:")
            logger.info(f"  稳态收敛: {result['steady_converged']}")
            logger.info(f"  瞬态成功率: {result['transient_success_rate']:.1%}")
            logger.info(f"  计算时间: {result['total_time']:.2f}s")
            logger.info(f"  内存使用: {result['memory_usage']:.1f}MB")
            
            return result
            
        except Exception as e:
            logger.error(f"场景 {scenario_name} 验证失败: {e}")
            return {
                'scenario': scenario_name,
                'error': str(e),
                'total_time': time.time() - start_time
            }
    
    def run_all_validations(self) -> Dict[str, Any]:
        """运行所有验证场景"""
        logger.info("开始实际水力网络仿真验证")
        
        scenarios = [
            ("城市排水网络", self.create_urban_drainage_network),
            ("灌溉渠系", self.create_irrigation_canal_system)
        ]
        
        results = []
        
        for scenario_name, create_func in scenarios:
            try:
                models, boundary_manager, control_manager = create_func()
                result = self.run_validation_scenario(
                    scenario_name, models, boundary_manager, control_manager
                )
                results.append(result)
                
            except Exception as e:
                logger.error(f"创建场景 {scenario_name} 失败: {e}")
                results.append({
                    'scenario': scenario_name,
                    'creation_error': str(e)
                })
        
        # 汇总统计
        summary = {
            'total_scenarios': len(scenarios),
            'successful_scenarios': sum(1 for r in results if 'error' not in r),
            'results': results,
            'overall_performance': self._calculate_overall_performance(results)
        }
        
        self.results['real_network_validation'] = summary
        return summary
    
    def _calculate_overall_performance(self, results: List[Dict]) -> Dict[str, float]:
        """计算整体性能指标"""
        successful_results = [r for r in results if 'error' not in r and 'creation_error' not in r]
        
        if not successful_results:
            return {'status': 'all_failed'}
        
        return {
            'avg_computation_time': np.mean([r['total_time'] for r in successful_results]),
            'avg_memory_usage': np.mean([r['memory_usage'] for r in successful_results]),
            'avg_success_rate': np.mean([r['transient_success_rate'] for r in successful_results]),
            'total_boundary_conditions': sum(r['boundary_conditions'] for r in successful_results),
            'total_control_devices': sum(r['control_devices'] for r in successful_results)
        }


def main():
    """主验证程序"""
    logger.info("🌊 WaterNet边界条件框架实际网络验证开始")
    
    validator = RealNetworkValidator()
    
    # 运行验证
    validation_results = validator.run_all_validations()
    
    # 输出结果
    logger.info("=" * 60)
    logger.info("验证结果汇总:")
    logger.info(f"总场景数: {validation_results['total_scenarios']}")
    logger.info(f"成功场景数: {validation_results['successful_scenarios']}")
    
    if validation_results['successful_scenarios'] > 0:
        perf = validation_results['overall_performance']
        logger.info(f"平均计算时间: {perf['avg_computation_time']:.2f}s")
        logger.info(f"平均内存使用: {perf['avg_memory_usage']:.1f}MB")
        logger.info(f"平均成功率: {perf['avg_success_rate']:.1%}")
        logger.info(f"总边界条件数: {perf['total_boundary_conditions']}")
        logger.info(f"总控制设备数: {perf['total_control_devices']}")
    
    logger.info("✅ 实际网络验证完成")
    return validation_results


if __name__ == "__main__":
    main()