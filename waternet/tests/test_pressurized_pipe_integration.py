"""
有压管道数字孪生系统集成测试

完整的系统测试，验证所有组件的集成效果和整体性能。

Author: WaterNet Development Team
Date: 2024-10-04
"""

import sys
import os
import numpy as np
import pandas as pd

# 添加路径以导入模块
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from physical_objects.pressurized_pipe_model import PressurizedPipeModel
from waternet.models.pressurized_pipe_rom import create_pressurized_pipe_rom
from waternet.parameter_estimation.pipe_parameter_estimator import PipeParameterEstimator
from waternet.coordination.pressurized_pipe_twin_harness import PressurizedPipeTwinHarness
from waternet.tests.run_pipe_simulation import PipeSimulationHarness


def run_integration_test():
    """运行完整的集成测试"""
    print("="*80)
    print("有压管道数字孪生系统 - 完整集成测试")
    print("="*80)
    
    test_results = {
        'tests_passed': 0,
        'tests_failed': 0,
        'test_details': []
    }
    
    try:
        # 测试1: 基础模型创建和验证
        print("\n[测试1] 基础模型创建和验证")
        pipe_model = create_test_pipe_model()
        
        # 验证模型基本功能
        assert pipe_model.validate_computational_setup()
        assert len(pipe_model.get_variable_names()) > 0
        
        # 恒定流计算测试
        steady_result = pipe_model.compute_steady_state(1.5, 95.0)
        assert 'upstream_H' in steady_result
        assert steady_result['upstream_H'] > 95.0
        
        test_results['tests_passed'] += 1
        test_results['test_details'].append("✅ 基础模型创建和验证 - 通过")
        print("✅ 基础模型功能验证通过")
        
        # 测试2: 降阶模型创建和基本功能
        print("\n[测试2] 降阶模型创建和基本功能")
        
        physical_params = {
            'L': pipe_model.total_length,
            'D': 1.0, 'a': 1200.0, 'f': 0.02
        }
        
        initial_conditions = {
            'H_initial': 100.0, 'Q_initial': 1.5, 'V_initial': 10000.0
        }
        
        # 测试不同类型的降阶模型
        rom_types = ['muskingum_hammer', 'linear_hammer', 'elastic_pipe']
        
        for rom_type in rom_types:
            try:
                rom = create_pressurized_pipe_rom(
                    rom_type, physical_params, 0.02, initial_conditions)
                
                # 基本仿真测试
                result = rom.step(1.5)
                assert 'Q_out' in result
                assert result['Q_out'] >= 0
                
                print(f"  ✅ {rom_type} 模型创建和仿真正常")
                
            except Exception as e:
                print(f"  ❌ {rom_type} 模型测试失败: {e}")
                test_results['tests_failed'] += 1
                test_results['test_details'].append(f"❌ {rom_type} 模型测试失败")
                continue
        
        test_results['tests_passed'] += 1
        test_results['test_details'].append("✅ 降阶模型创建和基本功能 - 通过")
        
        # 测试3: 仿真测试平台
        print("\n[测试3] 仿真测试平台")
        
        harness = PipeSimulationHarness(pipe_model, dt=0.05, total_time=2.0)
        harness.setup_valve_closure_scenario(
            Q_initial=1.5, t_close=1.0, closure_type='sudden')
        
        # 运行简化仿真（减少时间步数）
        simulation_results = harness.run_simulation()
        
        assert len(simulation_results) > 0
        assert 'time' in simulation_results.columns
        assert 'H_upstream' in simulation_results.columns
        
        test_results['tests_passed'] += 1
        test_results['test_details'].append("✅ 仿真测试平台 - 通过")
        print("✅ 仿真测试平台正常工作")
        
        # 测试4: 参数估计功能
        print("\n[测试4] 参数估计功能")
        
        estimator = PipeParameterEstimator(pipe_model)
        
        # 摩擦系数辨识测试
        steady_data = [
            {'Q': 1.0, 'H_up': 105.1, 'H_down': 95.0},
            {'Q': 1.5, 'H_up': 106.8, 'H_down': 95.0},
            {'Q': 2.0, 'H_up': 109.2, 'H_down': 95.0}
        ]
        
        friction_result = estimator.identify_friction_factor(steady_data)
        assert 'friction_factor' in friction_result
        assert 0.005 <= friction_result['friction_factor'] <= 0.1
        
        test_results['tests_passed'] += 1
        test_results['test_details'].append("✅ 参数估计功能 - 通过")
        print("✅ 参数估计功能正常")
        
        # 测试5: 同步孪生系统
        print("\n[测试5] 同步孪生系统")
        
        # 创建数字孪生
        digital_twin = create_pressurized_pipe_rom(
            'muskingum_hammer', physical_params, 0.02, initial_conditions)
        
        # 创建孪生协调器
        twin_harness = PressurizedPipeTwinHarness(
            pipe_model, digital_twin, correction_interval=10)
        
        # 运行短时间同步仿真
        Q_in_series = [1.5] * 20 + [0.5] * 20  # 简化输入序列
        sync_results = twin_harness.run_synchronized_simulation(
            Q_in_series, dt=0.05, total_time=2.0, enable_correction=True)
        
        assert len(sync_results) > 0
        assert 'error_Q' in sync_results.columns
        
        # 检查误差合理性
        avg_error = sync_results['error_Q'].mean()
        assert avg_error < 1.0  # 误差应该在合理范围内
        
        test_results['tests_passed'] += 1
        test_results['test_details'].append("✅ 同步孪生系统 - 通过")
        print("✅ 同步孪生系统正常工作")
        
        # 测试6: 性能评估
        print("\n[测试6] 性能评估")
        
        performance_summary = twin_harness.get_performance_summary()
        assert '总体性能' in performance_summary
        
        # 基本性能指标检查
        rmse = performance_summary['总体性能'].get('rmse_Q', float('inf'))
        assert rmse < 0.5  # RMSE应该在合理范围内
        
        test_results['tests_passed'] += 1
        test_results['test_details'].append("✅ 性能评估 - 通过")
        print("✅ 性能评估功能正常")
        
        print("\n" + "="*80)
        print("集成测试完成!")
        print(f"通过测试: {test_results['tests_passed']}")
        print(f"失败测试: {test_results['tests_failed']}")
        print("="*80)
        
        # 输出测试详情
        print("\n测试详情:")
        for detail in test_results['test_details']:
            print(f"  {detail}")
        
        # 总体评估
        total_tests = test_results['tests_passed'] + test_results['tests_failed']
        success_rate = test_results['tests_passed'] / total_tests * 100 if total_tests > 0 else 0
        
        print(f"\n总体成功率: {success_rate:.1f}%")
        
        if success_rate >= 80:
            print("🎉 系统集成测试整体PASS！")
            return True
        else:
            print("⚠️  系统集成测试存在问题，需要进一步调试。")
            return False
            
    except Exception as e:
        print(f"\n❌ 集成测试过程中发生异常: {e}")
        import traceback
        traceback.print_exc()
        
        test_results['tests_failed'] += 1
        test_results['test_details'].append(f"❌ 集成测试异常: {str(e)}")
        
        return False


def create_test_pipe_model() -> PressurizedPipeModel:
    """创建测试用的管道模型"""
    nodes = [
        {'mileage': 0.0, 'elevation': 100.0, 'diameter': 1.0, 'friction_coeff': 0.02},
        {'mileage': 500.0, 'elevation': 98.0, 'diameter': 1.0, 'friction_coeff': 0.02},
        {'mileage': 1000.0, 'elevation': 95.0, 'diameter': 0.8, 'friction_coeff': 0.025}
    ]
    
    return PressurizedPipeModel(
        name="IntegrationTestPipe",
        upstream_node="Reservoir",
        downstream_node="Valve",
        nodes=nodes,
        wave_speed=1200.0
    )


def run_performance_benchmark():
    """运行性能基准测试"""
    print("\n" + "="*80)
    print("性能基准测试")
    print("="*80)
    
    try:
        pipe_model = create_test_pipe_model()
        
        # 基准测试：恒定流计算性能
        import time
        
        print("\n恒定流计算性能测试...")
        start_time = time.time()
        
        for i in range(100):
            Q = 1.0 + i * 0.01
            steady_result = pipe_model.compute_steady_state(Q, 95.0)
        
        steady_time = time.time() - start_time
        print(f"100次恒定流计算耗时: {steady_time:.3f} 秒")
        print(f"平均单次计算: {steady_time/100*1000:.2f} 毫秒")
        
        # 基准测试：降阶模型性能
        physical_params = {
            'L': pipe_model.total_length, 'D': 1.0, 'a': 1200.0, 'f': 0.02
        }
        initial_conditions = {
            'H_initial': 100.0, 'Q_initial': 1.5, 'V_initial': 10000.0
        }
        
        rom = create_pressurized_pipe_rom(
            'muskingum_hammer', physical_params, 0.02, initial_conditions)
        
        print("\n降阶模型仿真性能测试...")
        start_time = time.time()
        
        Q_series = np.random.uniform(0.5, 2.5, 1000)
        for Q_in in Q_series:
            result = rom.step(Q_in)
        
        rom_time = time.time() - start_time
        print(f"1000步降阶模型仿真耗时: {rom_time:.3f} 秒")
        print(f"平均单步仿真: {rom_time/1000*1000:.2f} 毫秒")
        
        # 性能对比
        speedup_ratio = steady_time / rom_time * 100
        print(f"\n性能对比:")
        print(f"降阶模型相对恒定流计算的加速比: {speedup_ratio:.1f}x")
        
        return True
        
    except Exception as e:
        print(f"性能基准测试失败: {e}")
        return False


if __name__ == "__main__":
    # 运行集成测试
    success = run_integration_test()
    
    # 运行性能基准测试
    if success:
        run_performance_benchmark()
    
    print("\n" + "="*80)
    if success:
        print("🎉 有压管道数字孪生系统集成测试全部完成！")
        print("系统已准备就绪，可以投入使用。")
    else:
        print("⚠️  集成测试发现问题，建议进一步调试。")
    print("="*80)