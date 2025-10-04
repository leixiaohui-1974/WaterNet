"""
复杂水力枢纽模型系统演示脚本

展示复杂水力枢纽模型系统的完整功能，包括：
1. 网络配置加载和验证
2. 模型构建和拓扑检查
3. 稳态和瞬态求解
4. 结果分析和可视化

使用方法:
python complex_hub_demo.py [--config CONFIG_FILE] [--output OUTPUT_DIR] [--mode MODE]

Author: WaterNet Development Team
Date: 2024-10-04
"""

import sys
import os
import argparse
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import logging
from datetime import datetime
import json

# 添加WaterNet到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from waternet.models import (
    NetworkBuilder, ImplicitSolverAgent, SolverConfig,
    solve_hydraulic_network, solve_hydraulic_transient
)
from waternet.config.complex_hub_config import ConfigManager


def setup_logging(output_dir: Path, verbose: bool = False):
    """设置日志系统"""
    log_level = logging.DEBUG if verbose else logging.INFO
    
    # 创建日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    
    # 文件处理器
    log_file = output_dir / f"demo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # 配置根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    return logging.getLogger(__name__)


def load_and_validate_config(config_file: str, logger) -> dict:
    """加载和验证配置文件"""
    logger.info(f"加载配置文件: {config_file}")
    
    # 创建配置管理器
    config_manager = ConfigManager()
    
    try:
        # 加载配置
        network_config = config_manager.load_config(config_file)
        logger.info(f"成功加载网络配置: {network_config.system.name}")
        
        # 验证配置
        validation_result = config_manager.validator.validate_network_config(network_config)
        
        if validation_result['is_valid']:
            logger.info("配置验证通过")
        else:
            logger.error("配置验证失败:")
            for error in validation_result['errors']:
                logger.error(f"  - {error}")
            return None
        
        if validation_result['warnings']:
            logger.warning("配置验证警告:")
            for warning in validation_result['warnings']:
                logger.warning(f"  - {warning}")
        
        # 打印统计信息
        stats = validation_result['statistics']
        logger.info(f"网络统计: 水库{stats['total_reservoirs']}个, "
                   f"管道{stats['total_pipes']}个, "
                   f"枢纽站{stats['total_stations']}个, "
                   f"连接点{stats['total_junctions']}个")
        
        return network_config
        
    except Exception as e:
        logger.error(f"配置加载失败: {e}")
        return None


def convert_config_for_builder(network_config) -> dict:
    """将NetworkConfiguration转换为NetworkBuilder可用的格式"""
    builder_config = {
        'name': network_config.system.name,
        'models': []
    }
    
    # 水库
    for reservoir in network_config.reservoirs:
        model_config = {
            'name': reservoir.name,
            'type': reservoir.type,
            'initial_level': reservoir.initial_level,
            'surface_area': reservoir.surface_area,
            'bottom_level': reservoir.bottom_level,
            'nodes': reservoir.nodes or [f"{reservoir.name}_up", f"{reservoir.name}_down"]
        }
        if reservoir.min_level is not None:
            model_config['min_level'] = reservoir.min_level
        if reservoir.max_level is not None:
            model_config['max_level'] = reservoir.max_level
        
        builder_config['models'].append(model_config)
    
    # 管道
    for pipe in network_config.pipes:
        model_config = {
            'name': pipe.name,
            'type': pipe.type,
            'upstream_node': pipe.upstream_node,
            'downstream_node': pipe.downstream_node,
            'length': pipe.length,
            'diameter': pipe.diameter,
            'roughness': pipe.roughness,
            'minor_loss_coeff': pipe.minor_loss_coeff,
            'elevation_change': pipe.elevation_change
        }
        if pipe.fittings:
            model_config['fittings'] = pipe.fittings
        
        builder_config['models'].append(model_config)
    
    # 枢纽站
    for station in network_config.stations:
        model_config = {
            'name': station.name,
            'type': station.type,
            'upstream_node': station.upstream_node,
            'downstream_node': station.downstream_node,
            'station_type': station.station_type
        }
        if station.gates:
            model_config['gates'] = station.gates
        if station.pumps:
            model_config['pumps'] = station.pumps
        if station.structures:
            model_config['structures'] = station.structures
        
        builder_config['models'].append(model_config)
    
    # 连接点
    for junction in network_config.junctions:
        model_config = {
            'name': junction.name,
            'type': junction.type,
            'connected_objects': junction.connected_objects,
            'junction_type': junction.junction_type,
            'elevation': junction.elevation
        }
        if junction.flow_directions:
            model_config['flow_directions'] = junction.flow_directions
        if junction.loss_coefficients:
            model_config['loss_coefficients'] = junction.loss_coefficients
        if junction.inlet_object:
            model_config['inlet_object'] = junction.inlet_object
        if junction.split_ratios:
            model_config['split_ratios'] = junction.split_ratios
        
        builder_config['models'].append(model_config)
    
    return builder_config


def build_network(config_dict: dict, logger) -> list:
    """构建水力网络模型"""
    logger.info("开始构建水力网络模型...")
    
    try:
        builder = NetworkBuilder()
        models = builder.build_from_config(config_dict)
        
        logger.info(f"成功构建 {len(models)} 个模型")
        
        # 打印模型信息
        for model in models:
            logger.info(f"  - {model.__class__.__name__}: {model.name}")
        
        return models
        
    except Exception as e:
        logger.error(f"网络构建失败: {e}")
        return None


def demonstrate_steady_state_solution(models: list, initial_conditions: dict, 
                                    output_dir: Path, logger):
    """演示稳态求解"""
    logger.info("开始稳态求解演示...")
    
    try:
        # 配置求解器
        solver_config = SolverConfig(
            max_iterations=30,
            tolerance=1e-4,
            relaxation_factor=0.7,
            enable_diagnostics=True
        )
        
        # 求解稳态
        result = solve_hydraulic_network(models, initial_conditions, solver_config)
        
        if result['converged']:
            logger.info(f"稳态求解收敛，迭代 {result['statistics'].total_iterations} 次")
            logger.info(f"最终残差: {result['statistics'].final_residual_norm:.2e}")
            
            # 保存结果
            steady_results = {
                'converged': result['converged'],
                'iterations': result['statistics'].total_iterations,
                'final_residual': float(result['statistics'].final_residual_norm),
                'variables': {k: float(v) for k, v in result['variables'].items()},
                'convergence_history': [float(x) for x in result['statistics'].convergence_history]
            }
            
            result_file = output_dir / "steady_state_results.json"
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(steady_results, f, indent=2, ensure_ascii=False)
            
            logger.info(f"稳态结果已保存到: {result_file}")
            
            # 分析结果
            analyze_steady_state_results(result['variables'], output_dir, logger)
            
            return result['variables']
        else:
            logger.error("稳态求解未收敛")
            logger.error(f"失败原因: {result['statistics'].failure_reason}")
            return None
            
    except Exception as e:
        logger.error(f"稳态求解失败: {e}")
        return None


def analyze_steady_state_results(variables: dict, output_dir: Path, logger):
    """分析稳态结果"""
    logger.info("分析稳态求解结果...")
    
    # 分类变量
    water_levels = {k: v for k, v in variables.items() if k.startswith('H_')}
    flow_rates = {k: v for k, v in variables.items() if k.startswith('Q_')}
    
    logger.info("水位分布:")
    for name, level in sorted(water_levels.items()):
        logger.info(f"  {name}: {level:.3f} m")
    
    logger.info("流量分布:")
    for name, flow in sorted(flow_rates.items()):
        logger.info(f"  {name}: {flow:.3f} m³/s")
    
    # 创建结果图表
    try:
        create_steady_state_plots(water_levels, flow_rates, output_dir, logger)
    except Exception as e:
        logger.warning(f"图表生成失败: {e}")


def create_steady_state_plots(water_levels: dict, flow_rates: dict, 
                             output_dir: Path, logger):
    """创建稳态结果图表"""
    plt.style.use('default')
    
    # 水位分布图
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # 水位条形图
    names = [name.replace('H_', '') for name in water_levels.keys()]
    levels = list(water_levels.values())
    
    ax1.bar(range(len(names)), levels, color='skyblue', alpha=0.7)
    ax1.set_xlabel('位置')
    ax1.set_ylabel('水位 (m)')
    ax1.set_title('稳态水位分布')
    ax1.set_xticks(range(len(names)))
    ax1.set_xticklabels(names, rotation=45, ha='right')
    ax1.grid(True, alpha=0.3)
    
    # 流量分布图
    flow_names = [name.replace('Q_', '') for name in flow_rates.keys()]
    flows = list(flow_rates.values())
    
    colors = ['lightgreen' if f >= 0 else 'lightcoral' for f in flows]
    ax2.bar(range(len(flow_names)), flows, color=colors, alpha=0.7)
    ax2.set_xlabel('设备/管道')
    ax2.set_ylabel('流量 (m³/s)')
    ax2.set_title('稳态流量分布')
    ax2.set_xticks(range(len(flow_names)))
    ax2.set_xticklabels(flow_names, rotation=45, ha='right')
    ax2.grid(True, alpha=0.3)
    ax2.axhline(y=0, color='black', linestyle='-', alpha=0.5)
    
    plt.tight_layout()
    
    plot_file = output_dir / "steady_state_analysis.png"
    plt.savefig(plot_file, dpi=300, bbox_inches='tight')
    plt.close()
    
    logger.info(f"稳态分析图表已保存到: {plot_file}")


def demonstrate_transient_solution(models: list, initial_conditions: dict,
                                 network_config, output_dir: Path, logger):
    """演示瞬态求解"""
    logger.info("开始瞬态求解演示...")
    
    try:
        # 设置时间参数
        simulation_settings = network_config.simulation_settings or {}
        time_settings = simulation_settings.get('time_stepping', {})
        
        start_time = time_settings.get('start_time', 0.0)
        end_time = time_settings.get('end_time', 1800.0)  # 默认30分钟
        dt = time_settings.get('time_step', 60.0)  # 默认1分钟
        
        time_steps = np.arange(start_time, end_time + dt, dt)
        
        logger.info(f"瞬态求解时间范围: {start_time:.0f}s - {end_time:.0f}s, 步长: {dt:.0f}s")
        logger.info(f"总时间步数: {len(time_steps)}")
        
        # 边界条件函数
        def create_boundary_conditions():
            bc = {}
            # 简化的边界条件：上游入流和下游出流
            bc['Q_in_上游水库'] = lambda t: 50.0 + 10.0 * np.sin(2 * np.pi * t / 3600.0)  # 正弦变化
            bc['Q_out_调节水库'] = lambda t: 35.0 if t < 900 else 40.0  # 阶跃变化
            return bc
        
        boundary_conditions = create_boundary_conditions()
        
        # 配置求解器
        solver_config = SolverConfig(
            max_iterations=20,
            tolerance=1e-4,
            relaxation_factor=0.8
        )
        
        # 执行瞬态求解
        logger.info("执行瞬态求解...")
        results = solve_hydraulic_transient(
            models, time_steps, dt, initial_conditions, 
            boundary_conditions, solver_config
        )
        
        if results and len(results) > 0:
            logger.info(f"瞬态求解完成，成功求解 {len(results)} 个时间步")
            
            # 保存结果
            save_transient_results(results, output_dir, logger)
            
            # 分析和可视化
            analyze_transient_results(results, output_dir, logger)
            
            return results
        else:
            logger.error("瞬态求解失败")
            return None
            
    except Exception as e:
        logger.error(f"瞬态求解失败: {e}")
        return None


def save_transient_results(results: list, output_dir: Path, logger):
    """保存瞬态结果"""
    logger.info("保存瞬态求解结果...")
    
    # 转换结果格式
    transient_data = {
        'time_series': [],
        'summary': {
            'total_timesteps': len(results),
            'successful_timesteps': sum(1 for r in results if r.get('converged', False)),
            'average_iterations': np.mean([r.get('statistics', {}).get('total_iterations', 0) for r in results])
        }
    }
    
    for result in results:
        step_data = {
            'time': result.get('time', 0.0),
            'timestep': result.get('timestep', 0),
            'converged': result.get('converged', False),
            'iterations': result.get('statistics', {}).get('total_iterations', 0),
            'variables': {k: float(v) for k, v in result.get('variables', {}).items()}
        }
        transient_data['time_series'].append(step_data)
    
    result_file = output_dir / "transient_results.json"
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(transient_data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"瞬态结果已保存到: {result_file}")


def analyze_transient_results(results: list, output_dir: Path, logger):
    """分析瞬态结果"""
    logger.info("分析瞬态求解结果...")
    
    # 提取时间序列数据
    times = [r.get('time', 0.0) for r in results]
    
    # 提取关键变量的时间序列
    key_variables = [
        'H_上游水库', 'H_调节水库', 'Q_输水主管', 'Q_泄洪渠'
    ]
    
    variable_series = {}
    for var in key_variables:
        series = []
        for result in results:
            variables = result.get('variables', {})
            series.append(variables.get(var, 0.0))
        variable_series[var] = series
    
    # 创建时间序列图表
    create_transient_plots(times, variable_series, output_dir, logger)


def create_transient_plots(times: list, variable_series: dict, 
                          output_dir: Path, logger):
    """创建瞬态结果图表"""
    try:
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        axes = axes.flatten()
        
        colors = ['blue', 'red', 'green', 'orange']
        
        for i, (var_name, series) in enumerate(variable_series.items()):
            if i < len(axes):
                ax = axes[i]
                ax.plot(np.array(times) / 60, series, color=colors[i % len(colors)], 
                       linewidth=2, label=var_name)
                
                ax.set_xlabel('时间 (分钟)')
                if var_name.startswith('H_'):
                    ax.set_ylabel('水位 (m)')
                    ax.set_title(f'{var_name.replace("H_", "")} 水位变化')
                elif var_name.startswith('Q_'):
                    ax.set_ylabel('流量 (m³/s)')
                    ax.set_title(f'{var_name.replace("Q_", "")} 流量变化')
                
                ax.grid(True, alpha=0.3)
                ax.legend()
        
        # 如果有剩余的子图，隐藏它们
        for i in range(len(variable_series), len(axes)):
            axes[i].set_visible(False)
        
        plt.tight_layout()
        
        plot_file = output_dir / "transient_analysis.png"
        plt.savefig(plot_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"瞬态分析图表已保存到: {plot_file}")
        
    except Exception as e:
        logger.warning(f"瞬态图表生成失败: {e}")


def generate_demo_report(config_file: str, output_dir: Path, 
                        steady_results: dict, transient_results: list, logger):
    """生成演示报告"""
    logger.info("生成演示报告...")
    
    report = {
        'demo_info': {
            'timestamp': datetime.now().isoformat(),
            'config_file': str(config_file),
            'output_directory': str(output_dir)
        },
        'network_summary': {
            'config_loaded': config_file is not None,
            'steady_state_solved': steady_results is not None,
            'transient_solved': transient_results is not None and len(transient_results) > 0
        }
    }
    
    if steady_results:
        report['steady_state'] = {
            'converged': True,
            'key_results': {
                'water_levels': {k: v for k, v in steady_results.items() if k.startswith('H_')},
                'flow_rates': {k: v for k, v in steady_results.items() if k.startswith('Q_')}
            }
        }
    
    if transient_results:
        report['transient'] = {
            'total_timesteps': len(transient_results),
            'successful_timesteps': sum(1 for r in transient_results if r.get('converged', False)),
            'simulation_duration': transient_results[-1].get('time', 0.0) if transient_results else 0.0
        }
    
    report_file = output_dir / "demo_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    logger.info(f"演示报告已保存到: {report_file}")
    
    # 打印摘要
    print("\n" + "="*60)
    print("复杂水力枢纽模型系统演示完成")
    print("="*60)
    print(f"配置文件: {config_file}")
    print(f"输出目录: {output_dir}")
    print(f"稳态求解: {'成功' if steady_results else '失败'}")
    print(f"瞬态求解: {'成功' if transient_results else '失败'}")
    if transient_results:
        print(f"仿真时长: {transient_results[-1].get('time', 0.0)/60:.1f} 分钟")
    print(f"详细日志: {output_dir}/demo_*.log")
    print("="*60)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="复杂水力枢纽模型系统演示")
    parser.add_argument('--config', type=str, 
                       default='examples/configs/complex_hub_network.yaml',
                       help='配置文件路径')
    parser.add_argument('--output', type=str, 
                       default='demo_output',
                       help='输出目录')
    parser.add_argument('--mode', type=str, choices=['all', 'steady', 'transient'],
                       default='all', help='运行模式')
    parser.add_argument('--verbose', action='store_true',
                       help='详细输出')
    
    args = parser.parse_args()
    
    # 创建输出目录
    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True)
    
    # 设置日志
    logger = setup_logging(output_dir, args.verbose)
    
    logger.info("="*60)
    logger.info("复杂水力枢纽模型系统演示开始")
    logger.info("="*60)
    
    try:
        # 1. 加载和验证配置
        network_config = load_and_validate_config(args.config, logger)
        if network_config is None:
            logger.error("配置加载失败，演示终止")
            return 1
        
        # 2. 构建网络模型
        builder_config = convert_config_for_builder(network_config)
        models = build_network(builder_config, logger)
        if models is None:
            logger.error("网络构建失败，演示终止")
            return 1
        
        # 3. 准备初始条件
        initial_conditions = network_config.initial_conditions or {}
        
        steady_results = None
        transient_results = None
        
        # 4. 稳态求解演示
        if args.mode in ['all', 'steady']:
            steady_results = demonstrate_steady_state_solution(
                models, initial_conditions, output_dir, logger)
        
        # 5. 瞬态求解演示
        if args.mode in ['all', 'transient']:
            transient_results = demonstrate_transient_solution(
                models, initial_conditions, network_config, output_dir, logger)
        
        # 6. 生成报告
        generate_demo_report(args.config, output_dir, 
                           steady_results, transient_results, logger)
        
        logger.info("演示成功完成")
        return 0
        
    except Exception as e:
        logger.error(f"演示过程中发生错误: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())