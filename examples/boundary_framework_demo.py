"""
边界条件框架演示案例

演示边界条件框架在复杂水力网络中的应用，包括：
1. 基础边界条件设置
2. 时变控制信号管理
3. 配置文件驱动的系统构建
4. 与求解器的集成使用
5. 性能优化和自适应时间步

Author: WaterNet Development Team
Date: 2024-10-04
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import logging
import time
from typing import Dict, List, Any

# 导入WaterNet核心模块
from waternet.models.boundary_conditions import (
    FlowBoundary, StageBoundary, RatingCurveBoundary,
    BoundaryConditionManager, BoundaryConditionConfig,
    create_time_series_function, create_periodic_function
)
from waternet.models.control_signals import (
    ControlSignalManager, ControlSchedule,
    create_gate_device, create_pump_device, create_valve_device,
    create_simple_schedule
)
from waternet.models.implicit_solver import (
    ImplicitSolverAgent, SolverConfig,
    create_boundary_solver
)
from waternet.models.boundary_config import (
    ConfigFactory, generate_config_template
)
from waternet.models.adaptive_timestep import (
    create_adaptive_controller, TimeStepStrategy
)
from waternet.models.sparse_matrix import (
    analyze_system_sparsity
)
from waternet.interfaces.hydro_model import DummyModel

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def demo_basic_boundary_conditions():
    """演示基础边界条件功能"""
    logger.info("=== 基础边界条件演示 ===")
    
    # 1. 创建边界条件管理器
    boundary_manager = BoundaryConditionManager()
    
    # 2. 创建不同类型的边界条件
    
    # 恒定流量边界
    config1 = BoundaryConditionConfig("upstream_flow", "上游恒定入流")
    flow_boundary = FlowBoundary("upstream_flow", "upstream", 50.0, config1)
    boundary_manager.add_boundary_condition(flow_boundary)
    
    # 时变水位边界
    time_func = create_time_series_function(
        [0, 1800, 3600, 5400, 7200],
        [99.5, 100.0, 100.2, 99.8, 99.6],
        "linear"
    )
    config2 = BoundaryConditionConfig("downstream_stage", "下游时变水位")
    stage_boundary = StageBoundary("downstream_stage", "downstream", time_func, config2)
    boundary_manager.add_boundary_condition(stage_boundary)
    
    # 堰流关系边界
    weir_params = {
        'discharge_coefficient': 2.2,
        'reference_level': 99.0,
        'exponent': 1.5
    }
    config3 = BoundaryConditionConfig("weir_outlet", "堰流出口")
    rating_boundary = RatingCurveBoundary(
        "weir_outlet", "outlet_flow", "outlet_stage", 
        "weir", weir_params, config3
    )
    boundary_manager.add_boundary_condition(rating_boundary)
    
    logger.info(f"创建了 {boundary_manager.get_boundary_condition_count()} 个边界条件")
    
    # 3. 测试边界条件在不同时间的表现
    test_times = [0, 1800, 3600, 5400, 7200]
    test_variables = {
        'Q_upstream': 52.0,
        'H_downstream': 99.9,
        'Q_outlet_flow': 8.0,
        'H_outlet_stage': 100.1
    }
    
    results = []
    for t in test_times:
        equations = boundary_manager.get_all_equations(test_variables, t)
        results.append({
            'time': t,
            'equations': equations,
            'max_residual': max(abs(r) for r in equations.values())
        })
        
        logger.info(f"时间 {t:4.0f}s: 最大残差 = {results[-1]['max_residual']:.6f}")
    
    return results


def demo_control_signals():
    """演示控制信号管理"""
    logger.info("=== 控制信号管理演示 ===")
    
    # 1. 创建控制信号管理器
    control_manager = ControlSignalManager()
    
    # 2. 添加不同类型的控制设备
    gate1 = create_gate_device("main_gate", 0.0, 1.0, 0.5)
    pump1 = create_pump_device("drainage_pump", 0.0, 1.0, 0.0)
    valve1 = create_valve_device("branch_valve", 0.0, 1.0, 0.8)
    
    control_manager.add_device(gate1)
    control_manager.add_device(pump1)
    control_manager.add_device(valve1)
    
    logger.info(f"添加了 {control_manager.get_device_count()} 个控制设备")
    
    # 3. 创建控制调度表
    device_signals = {
        'main_gate': [(0, 0.5), (1800, 0.3), (3600, 0.2), (5400, 0.4), (7200, 0.6)],
        'drainage_pump': [(0, 0.0), (1800, 0.0), (3600, 0.8), (5400, 0.5), (7200, 0.0)],
        'branch_valve': [(0, 0.8), (1800, 0.6), (3600, 0.4), (5400, 0.5), (7200, 0.7)]
    }
    
    schedule = create_simple_schedule(device_signals, "linear")
    control_manager.set_schedule(schedule)
    
    # 4. 测试控制信号的时间演化
    test_times = np.linspace(0, 7200, 25)
    control_history = []
    
    for t in test_times:
        signals = control_manager.get_signals_at_time(t)
        control_history.append({
            'time': t,
            'main_gate': signals.get_signal('main_gate'),
            'drainage_pump': signals.get_signal('drainage_pump'),
            'branch_valve': signals.get_signal('branch_valve')
        })
    
    # 5. 可视化控制信号演化
    times = [item['time'] for item in control_history]
    gate_values = [item['main_gate'] for item in control_history]
    pump_values = [item['drainage_pump'] for item in control_history]
    valve_values = [item['branch_valve'] for item in control_history]
    
    plt.figure(figsize=(12, 8))
    plt.subplot(3, 1, 1)
    plt.plot(times, gate_values, 'b-', linewidth=2, label='主闸门开度')
    plt.ylabel('开度')
    plt.title('控制信号时间演化')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    plt.subplot(3, 1, 2)
    plt.plot(times, pump_values, 'r-', linewidth=2, label='排水泵功率')
    plt.ylabel('功率')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    plt.subplot(3, 1, 3)
    plt.plot(times, valve_values, 'g-', linewidth=2, label='分支阀门开度')
    plt.ylabel('开度')
    plt.xlabel('时间 (s)')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    plt.tight_layout()
    plt.savefig('control_signals_demo.svg', dpi=300, bbox_inches='tight')
    plt.show()
    
    logger.info("控制信号演化图已保存为 control_signals_demo.svg")
    
    return control_history


def demo_config_driven_system():
    """演示配置驱动的系统构建"""
    logger.info("=== 配置驱动系统演示 ===")
    
    # 1. 生成配置模板
    config_file = Path("demo_boundary_config.yaml")
    generate_config_template(config_file)
    logger.info(f"生成配置模板: {config_file}")
    
    # 2. 从配置文件创建系统
    factory = ConfigFactory()
    
    try:
        boundary_manager, control_manager = factory.create_from_config_file(config_file)
        
        logger.info(f"从配置文件创建系统:")
        logger.info(f"  - 边界条件数量: {boundary_manager.get_boundary_condition_count()}")
        logger.info(f"  - 控制设备数量: {control_manager.get_device_count()}")
        
        # 3. 测试配置系统的功能
        test_variables = {
            'Q_上游节点': 55.0,
            'H_下游节点': 100.1,
            'Q_出口流量': 6.0,
            'H_出口水位': 100.0
        }
        
        # 测试边界条件
        equations = boundary_manager.get_all_equations(test_variables, 1800.0)
        logger.info("边界条件方程残差:")
        for eq_name, residual in equations.items():
            logger.info(f"  {eq_name}: {residual:.6f}")
        
        # 测试控制信号
        signals = control_manager.get_signals_at_time(1800.0)
        logger.info("控制信号值:")
        for device_id in control_manager.get_device_list():
            value = signals.get_signal(device_id)
            logger.info(f"  {device_id}: {value:.3f}")
        
        return boundary_manager, control_manager
        
    except Exception as e:
        logger.error(f"配置驱动系统创建失败: {e}")
        return None, None


def demo_solver_integration():
    """演示与求解器的集成"""
    logger.info("=== 求解器集成演示 ===")
    
    # 1. 创建简单的水力模型
    models = [
        DummyModel("pipe1", "node1", "node2", k=0.8, b=0.1),
        DummyModel("pipe2", "node2", "node3", k=1.2, b=-0.05)
    ]
    
    # 2. 创建边界条件
    boundary_conditions = []
    
    # 上游流量边界
    config1 = BoundaryConditionConfig("upstream_bc", "上游流量边界")
    flow_bc = FlowBoundary("upstream_bc", "node1", 50.0, config1)
    boundary_conditions.append(flow_bc)
    
    # 下游水位边界
    config2 = BoundaryConditionConfig("downstream_bc", "下游水位边界")
    stage_bc = StageBoundary("downstream_bc", "node3", 100.0, config2)
    boundary_conditions.append(stage_bc)
    
    # 3. 创建控制设备
    control_devices = [
        create_gate_device("gate1", 0.0, 1.0, 0.6),
        create_valve_device("valve1", 0.0, 1.0, 0.8)
    ]
    
    # 4. 创建集成求解器
    solver = create_boundary_solver(
        models=models,
        boundary_conditions=boundary_conditions,
        control_devices=control_devices
    )
    
    logger.info("创建了集成边界条件求解器")
    
    # 5. 求解稳态问题
    initial_conditions = {
        'H_node1': 101.0,
        'H_node2': 100.5,
        'H_node3': 100.0,
        'Q_pipe1': 40.0,
        'Q_pipe2': 38.0
    }
    
    logger.info("开始稳态求解...")
    start_time = time.time()
    
    result = solver.solve_steady_state(initial_conditions)
    
    solve_time = time.time() - start_time
    
    if result['converged']:
        logger.info(f"稳态求解成功! 耗时: {solve_time:.3f}s")
        logger.info(f"迭代次数: {result['statistics'].total_iterations}")
        logger.info(f"最终残差: {result['statistics'].final_residual_norm:.2e}")
        
        # 显示求解结果
        variables = result['variables']
        logger.info("求解结果:")
        for var_name, value in variables.items():
            logger.info(f"  {var_name}: {value:.6f}")
    else:
        logger.error("稳态求解失败!")
        logger.error(f"失败原因: {result['statistics'].failure_reason}")
    
    return result


def demo_advanced_features():
    """演示高级功能"""
    logger.info("=== 高级功能演示 ===")
    
    # 1. 稀疏矩阵分析
    logger.info("1. 稀疏矩阵分析")
    
    # 创建模拟模型系统
    models = [DummyModel(f"model_{i}", f"node_{i}", f"node_{i+1}") for i in range(10)]
    variable_names = [f"H_node_{i}" for i in range(11)] + [f"Q_model_{i}" for i in range(10)]
    
    sparsity_info = analyze_system_sparsity(models, variable_names)
    
    logger.info(f"  系统规模: {sparsity_info['matrix_size']}")
    logger.info(f"  稀疏度: {sparsity_info['sparsity_ratio']:.2%}")
    logger.info(f"  非零元素数: {sparsity_info['nonzero_count']}")
    logger.info(f"  推荐格式: {sparsity_info['recommended_format']}")
    
    # 2. 自适应时间步控制
    logger.info("2. 自适应时间步控制")
    
    controller = create_adaptive_controller(
        strategy=TimeStepStrategy.BALANCED,
        initial_dt=60.0,
        min_dt=1.0,
        max_dt=300.0
    )
    
    # 模拟求解过程
    dt_history = []
    convergence_history = []
    
    for step in range(20):
        # 模拟不同的收敛情况
        if step < 5:
            # 初期收敛困难
            solver_result = {
                'converged': step % 2 == 0,
                'statistics': {
                    'total_iterations': 25 + np.random.randint(-5, 10),
                    'final_residual_norm': 1e-6 if step % 2 == 0 else 1e-3,
                    'convergence_history': [1.0, 0.5, 0.1] if step % 2 == 0 else [1.0, 1.2, 1.5]
                }
            }
        elif step < 15:
            # 中期稳定收敛
            solver_result = {
                'converged': True,
                'statistics': {
                    'total_iterations': 8 + np.random.randint(-2, 3),
                    'final_residual_norm': 1e-7,
                    'convergence_history': [1.0, 0.3, 0.05, 1e-7]
                }
            }
        else:
            # 后期快速收敛
            solver_result = {
                'converged': True,
                'statistics': {
                    'total_iterations': 4 + np.random.randint(-1, 2),
                    'final_residual_norm': 1e-8,
                    'convergence_history': [0.1, 0.01, 1e-8]
                }
            }
        
        dt, adjustment_info = controller.adjust_timestep(solver_result)
        
        dt_history.append(dt)
        convergence_history.append(solver_result['converged'])
        
        if step % 5 == 0:
            logger.info(f"  步骤 {step:2d}: dt = {dt:6.1f}s, {adjustment_info['reason']}")
    
    # 分析自适应性能
    stats = controller.get_statistics()
    success_rate = stats.successful_steps / stats.total_steps
    
    logger.info(f"  自适应时间步统计:")
    logger.info(f"    成功率: {success_rate:.1%}")
    logger.info(f"    平均时间步: {stats.avg_dt:.1f}s")
    logger.info(f"    时间步范围: [{stats.min_dt_used:.1f}, {stats.max_dt_used:.1f}]s")
    logger.info(f"    调整次数: 减少 {stats.dt_reductions}, 增加 {stats.dt_increases}")
    
    # 可视化时间步演化
    plt.figure(figsize=(12, 6))
    
    plt.subplot(2, 1, 1)
    steps = range(len(dt_history))
    plt.plot(steps, dt_history, 'b-o', linewidth=2, markersize=4)
    plt.ylabel('时间步长 (s)')
    plt.title('自适应时间步长演化')
    plt.grid(True, alpha=0.3)
    
    plt.subplot(2, 1, 2)
    convergence_colors = ['red' if not conv else 'green' for conv in convergence_history]
    plt.scatter(steps, [1]*len(steps), c=convergence_colors, s=50, alpha=0.7)
    plt.ylabel('收敛状态')
    plt.xlabel('求解步数')
    plt.ylim(0.5, 1.5)
    plt.yticks([1], ['收敛'])
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('adaptive_timestep_demo.svg', dpi=300, bbox_inches='tight')
    plt.show()
    
    logger.info("自适应时间步演化图已保存为 adaptive_timestep_demo.svg")


def demo_performance_comparison():
    """演示性能对比"""
    logger.info("=== 性能对比演示 ===")
    
    # 创建不同规模的边界条件系统
    scales = [10, 50, 100, 200]
    creation_times = []
    equation_times = []
    
    for scale in scales:
        logger.info(f"测试规模: {scale} 个边界条件")
        
        # 测试创建时间
        start_time = time.time()
        
        boundary_manager = BoundaryConditionManager()
        for i in range(scale):
            config = BoundaryConditionConfig(f"bc_{i}", f"边界条件{i}")
            flow_bc = FlowBoundary(f"bc_{i}", f"node_{i}", float(i), config)
            boundary_manager.add_boundary_condition(flow_bc)
        
        creation_time = time.time() - start_time
        creation_times.append(creation_time)
        
        # 测试方程生成时间
        variables = {f'Q_node_{i}': float(i + 10) for i in range(scale)}
        
        start_time = time.time()
        equations = boundary_manager.get_all_equations(variables, 0.0)
        equation_time = time.time() - start_time
        equation_times.append(equation_time)
        
        logger.info(f"  创建时间: {creation_time:.4f}s")
        logger.info(f"  方程生成时间: {equation_time:.4f}s")
        logger.info(f"  平均创建时间: {creation_time/scale*1000:.2f}ms/个")
        logger.info(f"  平均方程时间: {equation_time/scale*1000:.2f}ms/个")
    
    # 可视化性能结果
    plt.figure(figsize=(12, 5))
    
    plt.subplot(1, 2, 1)
    plt.loglog(scales, creation_times, 'bo-', linewidth=2, markersize=8, label='创建时间')
    plt.loglog(scales, equation_times, 'ro-', linewidth=2, markersize=8, label='方程生成时间')
    plt.xlabel('边界条件数量')
    plt.ylabel('时间 (s)')
    plt.title('性能扩展性测试')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    plt.subplot(1, 2, 2)
    avg_creation = [ct/sc*1000 for ct, sc in zip(creation_times, scales)]
    avg_equation = [et/sc*1000 for et, sc in zip(equation_times, scales)]
    
    plt.semilogx(scales, avg_creation, 'bo-', linewidth=2, markersize=8, label='平均创建时间')
    plt.semilogx(scales, avg_equation, 'ro-', linewidth=2, markersize=8, label='平均方程时间')
    plt.xlabel('边界条件数量')
    plt.ylabel('平均时间 (ms/个)')
    plt.title('平均性能分析')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    plt.tight_layout()
    plt.savefig('performance_comparison.svg', dpi=300, bbox_inches='tight')
    plt.show()
    
    logger.info("性能对比图已保存为 performance_comparison.svg")
    
    return {
        'scales': scales,
        'creation_times': creation_times,
        'equation_times': equation_times
    }


def main():
    """主演示函数"""
    logger.info("🌊 WaterNet边界条件框架综合演示开始")
    logger.info("=" * 60)
    
    try:
        # 1. 基础功能演示
        boundary_results = demo_basic_boundary_conditions()
        
        # 2. 控制信号演示
        control_results = demo_control_signals()
        
        # 3. 配置驱动演示
        boundary_manager, control_manager = demo_config_driven_system()
        
        # 4. 求解器集成演示
        if boundary_manager and control_manager:
            solver_result = demo_solver_integration()
        
        # 5. 高级功能演示
        demo_advanced_features()
        
        # 6. 性能对比演示
        performance_results = demo_performance_comparison()
        
        logger.info("=" * 60)
        logger.info("✅ 所有演示完成！")
        logger.info("📊 生成的文件:")
        logger.info("  - control_signals_demo.svg: 控制信号演化图")
        logger.info("  - adaptive_timestep_demo.svg: 自适应时间步演化图")
        logger.info("  - performance_comparison.svg: 性能对比图")
        logger.info("  - demo_boundary_config.yaml: 配置模板文件")
        
    except Exception as e:
        logger.error(f"演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()