#!/usr/bin/env python3
"""
配置驱动的水库-闸门-明渠系统仿真

基于配置文件实现完整的水库-闸门-明渠系统建模和仿真。
演示配置驱动的系统构建、仿真执行和结果输出。

运行示例:
    python config_driven_reservoir_gate_system.py

配置文件:
    configs/reservoir_gate_channel_system.yaml

Author: WaterNet Development Team
Date: 2024-10-05
"""

import sys
import os
import time
import numpy as np
from pathlib import Path
from typing import Dict, List, Any

# 添加WaterNet路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from waternet.utils.config_driven_system import (
        ConfigurationManager, SystemBuilder, InputOutputManager,
        create_system_from_config
    )
    from waternet.models.configurable_gate_model import ConfigurableGateModel
    from waternet.models.constant_level_reservoir import ConstantLevelReservoir
    from waternet.models.saint_venant import SaintVenantModel
    print("✓ WaterNet模块导入成功")
except ImportError as e:
    print(f"✗ WaterNet模块导入失败: {e}")
    print("请确保已通过 'pip install -e .' 安装项目")
    sys.exit(1)


class ConfigDrivenSimulation:
    """
    配置驱动的仿真控制器
    
    基于配置文件执行完整的仿真流程，包括：
    1. 系统初始化
    2. 恒定流计算
    3. 非恒定流仿真
    4. 结果分析和输出
    """
    
    def __init__(self, config_path: str):
        """
        初始化仿真控制器
        
        Args:
            config_path (str): 配置文件路径
        """
        self.config_path = config_path
        
        # 创建系统组件
        self.system_builder, self.io_manager = create_system_from_config(config_path)
        self.config_manager = self.system_builder.config_manager
        
        # 获取配置
        self.simulation_config = self.config_manager.get_simulation_config()
        self.test_cases_config = self.config_manager.get_test_cases_config()
        
        # 仿真状态
        self.models = self.system_builder.get_all_models()
        self.current_time = 0.0
        self.time_step = self.simulation_config.get('time', {}).get('initial_time_step', 10.0)
        self.simulation_data = []
        
        print(f"✓ 配置驱动仿真系统初始化完成")
        print(f"  - 配置文件: {config_path}")
        print(f"  - 模型数量: {len(self.models)}")
        print(f"  - 输出目录: {self.io_manager.get_session_directory()}")
    
    def run_complete_simulation(self):
        """运行完整仿真流程"""
        print("\n" + "="*60)
        print("开始配置驱动的水库-闸门-明渠系统仿真")
        print("="*60)
        
        try:
            # 1. 系统初始化和验证
            self._initialize_system()
            
            # 2. 运行恒定流测试
            self._run_steady_flow_tests()
            
            # 3. 运行非恒定流测试
            self._run_unsteady_flow_tests()
            
            # 4. 生成报告和可视化
            self._generate_outputs()
            
            print("\n✓ 仿真完成！所有测试用例已执行")
            print(f"✓ 结果已保存到: {self.io_manager.get_session_directory()}")
            
        except Exception as e:
            print(f"\n✗ 仿真失败: {e}")
            raise
    
    def _initialize_system(self):
        """初始化系统"""
        print("\n1. 系统初始化...")
        
        # 显示系统摘要
        summary = self.system_builder.get_system_summary()
        print(f"   系统包含 {summary['total_models']} 个模型:")
        
        for model_name, model_info in summary['models'].items():
            print(f"   - {model_name}: {model_info['type']}")
        
        # 验证配置
        self._validate_system_configuration()
        
        print("   ✓ 系统初始化完成")
    
    def _validate_system_configuration(self):
        """验证系统配置"""
        # 检查模型完整性
        required_components = ['上游水库', '下游水库']
        for component in required_components:
            if component not in self.models:
                raise ValueError(f"缺少必需组件: {component}")
        
        # 检查闸门配置
        gates = [name for name, model in self.models.items() 
                if isinstance(model, ConfigurableGateModel)]
        if not gates:
            print("   警告: 未发现闸门模型，将使用简化配置")
        
        print(f"   ✓ 发现 {len(gates)} 个闸门模型")
    
    def _run_steady_flow_tests(self):
        """运行恒定流测试"""
        print("\n2. 恒定流测试...")
        
        steady_tests = self.test_cases_config.get('steady_flow_tests', {})
        
        if not steady_tests:
            print("   跳过恒定流测试（未配置测试用例）")
            return
        
        # 创建结果写入器
        results_writer = self.io_manager.create_results_writer(
            'steady_flow_results', 'csv')
        
        steady_results = []
        
        for test_name, test_config in steady_tests.items():
            print(f"   执行测试: {test_name}")
            
            # 设置闸门开度
            gate_settings = test_config.get('gate_settings', {})
            self._apply_gate_settings(gate_settings)
            
            # 执行恒定流计算
            result = self._calculate_steady_flow(test_name, test_config)
            steady_results.append(result)
            
            # 写入结果
            results_writer.write_row(result)
            
            print(f"     ✓ {test_name} 完成")
        
        results_writer.finalize()
        print(f"   ✓ 恒定流测试完成，共 {len(steady_results)} 个工况")
    
    def _apply_gate_settings(self, gate_settings: Dict[str, float]):
        """应用闸门设置"""
        for gate_name, opening in gate_settings.items():
            if gate_name in self.models:
                model = self.models[gate_name]
                if isinstance(model, ConfigurableGateModel):
                    model.set_opening(opening)
                    print(f"     设置 {gate_name} 开度: {opening:.2f}m")
    
    def _calculate_steady_flow(self, test_name: str, 
                             test_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        计算恒定流工况
        
        Args:
            test_name (str): 测试名称
            test_config (Dict): 测试配置
        
        Returns:
            Dict[str, Any]: 计算结果
        """
        # 获取水库水位
        upstream_reservoir = self.models.get('上游水库')
        downstream_reservoir = self.models.get('下游水库')
        
        if not upstream_reservoir or not downstream_reservoir:
            raise ValueError("缺少上游或下游水库")
        
        H_upstream = upstream_reservoir.get_water_level()
        H_downstream = downstream_reservoir.get_water_level()
        
        # 计算闸门流量
        total_flow = 0.0
        gate_flows = {}
        
        for model_name, model in self.models.items():
            if isinstance(model, ConfigurableGateModel):
                opening = model.get_current_opening()
                flow = model.calculate_discharge(H_upstream, H_downstream, opening)
                gate_flows[model_name] = flow
                total_flow += flow
        
        # 计算水力指标
        head_difference = H_upstream - H_downstream
        
        result = {
            'test_name': test_name,
            'upstream_level': H_upstream,
            'downstream_level': H_downstream,
            'head_difference': head_difference,
            'total_flow': total_flow,
            **gate_flows,
            'calculation_time': time.time()
        }
        
        return result
    
    def _run_unsteady_flow_tests(self):
        """运行非恒定流测试"""
        print("\n3. 非恒定流测试...")
        
        unsteady_tests = self.test_cases_config.get('unsteady_flow_tests', {})
        
        if not unsteady_tests:
            print("   跳过非恒定流测试（未配置测试用例）")
            return
        
        # 创建时间序列结果写入器
        time_series_writer = self.io_manager.create_results_writer(
            'unsteady_flow_time_series', 'csv')
        
        for test_name, test_config in unsteady_tests.items():
            print(f"   执行测试: {test_name}")
            
            # 执行非恒定流仿真
            time_series_data = self._simulate_unsteady_flow(test_name, test_config)
            
            # 写入时间序列数据
            for data_point in time_series_data:
                time_series_writer.write_row(data_point)
            
            print(f"     ✓ {test_name} 完成，{len(time_series_data)} 个时间步")
        
        time_series_writer.finalize()
        print("   ✓ 非恒定流测试完成")
    
    def _simulate_unsteady_flow(self, test_name: str, 
                              test_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        模拟非恒定流过程
        
        Args:
            test_name (str): 测试名称
            test_config (Dict): 测试配置
        
        Returns:
            List[Dict[str, Any]]: 时间序列数据
        """
        # 设置初始条件
        initial_conditions = test_config.get('initial_conditions', {})
        self._apply_gate_settings(initial_conditions)
        
        # 获取控制序列
        control_sequence = test_config.get('control_sequence', [])
        
        # 仿真参数
        time_config = self.simulation_config.get('time', {})
        start_time = time_config.get('start_time', 0.0)
        end_time = time_config.get('end_time', 3600.0)  # 默认1小时
        dt = time_config.get('initial_time_step', 10.0)
        
        time_series_data = []
        current_time = start_time
        control_index = 0
        
        print(f"     仿真时间: {start_time:.0f}s 到 {end_time:.0f}s，步长: {dt:.0f}s")
        
        while current_time <= end_time:
            # 检查是否需要执行控制动作
            while (control_index < len(control_sequence) and 
                   control_sequence[control_index]['time'] <= current_time):
                
                action = control_sequence[control_index]
                self._execute_control_action(action)
                control_index += 1
                print(f"       t={current_time:.0f}s: 执行控制动作")
            
            # 计算当前时步的系统状态
            system_state = self._calculate_system_state(current_time)
            system_state['test_name'] = test_name
            time_series_data.append(system_state)
            
            current_time += dt
        
        return time_series_data
    
    def _execute_control_action(self, action: Dict[str, Any]):
        """执行控制动作"""
        action_type = action.get('action')
        target = action.get('target')
        value = action.get('value')
        
        if action_type == 'set_gate_opening':
            if target in self.models:
                model = self.models[target]
                if isinstance(model, ConfigurableGateModel):
                    model.set_opening(value)
    
    def _calculate_system_state(self, current_time: float) -> Dict[str, Any]:
        """
        计算系统当前状态
        
        Args:
            current_time (float): 当前时间
        
        Returns:
            Dict[str, Any]: 系统状态
        """
        # 获取水库状态
        upstream_reservoir = self.models.get('上游水库')
        downstream_reservoir = self.models.get('下游水库')
        
        state = {
            'time': current_time,
            'upstream_level': upstream_reservoir.get_water_level() if upstream_reservoir else 0.0,
            'downstream_level': downstream_reservoir.get_water_level() if downstream_reservoir else 0.0
        }
        
        # 获取闸门状态
        total_flow = 0.0
        for model_name, model in self.models.items():
            if isinstance(model, ConfigurableGateModel):
                opening = model.get_current_opening()
                state[f'{model_name}_opening'] = opening
                
                # 计算流量（简化）
                H_up = state['upstream_level']
                H_down = state['downstream_level']
                flow = model.calculate_discharge(H_up, H_down, opening)
                state[f'{model_name}_flow'] = flow
                total_flow += flow
        
        state['total_flow'] = total_flow
        
        return state
    
    def _generate_outputs(self):
        """生成输出和报告"""
        print("\n4. 生成输出...")
        
        # 创建图表管理器
        plot_manager = self.io_manager.create_plot_manager()
        
        # 生成系统拓扑图
        try:
            topology_plot = plot_manager.create_topology_plot(self.system_builder)
            print(f"   ✓ 系统拓扑图: {topology_plot}")
        except Exception as e:
            print(f"   警告: 拓扑图生成失败: {e}")
        
        # 生成时间序列图
        try:
            time_series_plots = plot_manager.create_time_series_plots()
            for plot_name, plot_path in time_series_plots.items():
                print(f"   ✓ {plot_name}: {plot_path}")
        except Exception as e:
            print(f"   警告: 时间序列图生成失败: {e}")
        
        # 生成仿真报告
        report_generator = self.io_manager.create_report_generator()
        try:
            simulation_results = {'status': 'completed'}
            report_path = report_generator.generate_summary_report(
                self.system_builder, simulation_results)
            print(f"   ✓ 仿真报告: {report_path}")
        except Exception as e:
            print(f"   警告: 报告生成失败: {e}")
        
        print("   ✓ 输出生成完成")
    
    def get_simulation_summary(self) -> Dict[str, Any]:
        """获取仿真摘要"""
        return {
            'config_path': self.config_path,
            'models_count': len(self.models),
            'output_directory': str(self.io_manager.get_session_directory()),
            'simulation_completed': True
        }


def main():
    """主函数"""
    print("配置驱动的水库-闸门-明渠系统仿真")
    print("=" * 50)
    
    # 配置文件路径
    config_path = Path(__file__).parent.parent / "configs" / "reservoir_gate_channel_system.yaml"
    
    if not config_path.exists():
        print(f"✗ 配置文件不存在: {config_path}")
        print("请确保配置文件存在并且路径正确")
        return
    
    try:
        # 创建并运行仿真
        simulation = ConfigDrivenSimulation(str(config_path))
        simulation.run_complete_simulation()
        
        # 显示摘要
        summary = simulation.get_simulation_summary()
        print(f"\n仿真摘要:")
        print(f"  配置文件: {summary['config_path']}")
        print(f"  模型数量: {summary['models_count']}")
        print(f"  输出目录: {summary['output_directory']}")
        
        print(f"\n✓ 配置驱动仿真成功完成！")
        
    except Exception as e:
        print(f"\n✗ 仿真失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()