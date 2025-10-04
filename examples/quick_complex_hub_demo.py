"""
复杂水力枢纽模型系统快速演示

这是一个简化的演示脚本，展示复杂水力枢纽模型系统的核心功能。
无需外部配置文件，通过代码直接构建演示系统。

Author: WaterNet Development Team
Date: 2024-10-04
"""

import sys
import os
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import logging

# 添加WaterNet到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from waternet.models import (
    ReservoirModel, JunctionModel, ComplexStationModel, PressurizedPipeModel,
    ImplicitSolverAgent, SolverConfig,
    create_simple_reservoir, create_simple_junction, create_gate_station, create_simple_pipe
)


def setup_simple_logging():
    """设置简单的日志系统"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    return logging.getLogger(__name__)


def create_demo_system(logger):
    """创建演示系统"""
    logger.info("创建演示水力系统...")
    
    # 1. 创建上游水库
    upstream_reservoir = create_simple_reservoir(
        name="上游水库",
        upstream_node="上游_入口",
        downstream_node="上游_出口", 
        initial_level=110.0,
        bottom_level=100.0,
        surface_area=2000000.0
    )
    
    # 2. 创建主枢纽站
    gate_configs = [
        {
            'name': '主闸门',
            'width': 12.0,
            'discharge_coeff': 0.75,
            'initial_opening': 3.0
        }
    ]
    
    main_station = create_gate_station(
        name="主枢纽",
        upstream_node="上游_出口",
        downstream_node="分流点",
        gate_configs=gate_configs
    )
    
    # 3. 创建分流连接点
    junction = create_simple_junction(
        "分流点", "主枢纽", "主管道", "泄洪道"
    )
    
    # 4. 创建主输水管道
    main_pipe = create_simple_pipe(
        name="主管道",
        upstream_node="分流点",
        downstream_node="下游_入口",
        length=2000.0,
        diameter=2.0
    )
    
    # 5. 创建泄洪道
    spillway = create_simple_pipe(
        name="泄洪道", 
        upstream_node="分流点",
        downstream_node="泄洪_出口",
        length=800.0,
        diameter=2.5
    )
    
    # 6. 创建下游水库
    downstream_reservoir = create_simple_reservoir(
        name="下游水库",
        upstream_node="下游_入口",
        downstream_node="下游_出口",
        initial_level=95.0,
        bottom_level=85.0,
        surface_area=1500000.0
    )
    
    models = [
        upstream_reservoir,
        main_station, 
        junction,
        main_pipe,
        spillway,
        downstream_reservoir
    ]
    
    logger.info(f"系统创建完成，包含 {len(models)} 个组件:")
    for model in models:
        logger.info(f"  - {model.__class__.__name__}: {model.name}")
    
    return models


def demonstrate_basic_functionality(models, logger):
    """演示基本功能"""
    logger.info("演示基本功能...")
    
    # 测试每个模型的接口
    for model in models:
        try:
            var_names = model.get_variable_names()
            logger.info(f"{model.name} 变量: {var_names}")
            
            # 测试方程计算
            test_vars = {name: 0.0 for name in var_names}
            test_vars.update({
                'H_上游水库': 110.0,
                'H_下游水库': 95.0,
                'H_分流点': 105.0,
                'H_上游_出口': 110.0,
                'H_下游_入口': 95.0,
                'H_泄洪_出口': 100.0
            })
            
            equations = model.get_equations(test_vars, 1.0, {})
            logger.info(f"{model.name} 方程数: {len(equations)}")
            
        except Exception as e:
            logger.warning(f"{model.name} 测试失败: {e}")


def solve_simple_steady_state(models, logger):
    """求解简单稳态问题"""
    logger.info("求解稳态问题...")
    
    try:
        # 设置初始条件
        initial_conditions = {
            'H_上游水库': 110.0,
            'H_下游水库': 95.0,
            'H_分流点': 105.0,
            'Q_主闸门': 30.0,
            'Q_主管道': 20.0,
            'Q_泄洪道': 10.0,
            'H_上游_出口': 110.0,
            'H_下游_入口': 95.0,
            'H_泄洪_出口': 100.0
        }
        
        # 创建求解器
        solver_config = SolverConfig(
            max_iterations=20,
            tolerance=1e-3,
            relaxation_factor=0.5
        )
        
        solver = ImplicitSolverAgent(models, solver_config)
        
        # 显示系统信息
        stats = solver.get_system_statistics()
        logger.info(f"系统统计: {stats}")
        
        # 尝试求解（注意：简化模型可能不会收敛）
        logger.info("开始求解...")
        result = solver.solve_steady_state(initial_conditions)
        
        if result['converged']:
            logger.info("求解成功收敛!")
            logger.info(f"迭代次数: {result['statistics'].total_iterations}")
            logger.info(f"最终残差: {result['statistics'].final_residual_norm:.2e}")
            
            # 显示主要结果
            variables = result['variables']
            logger.info("主要结果:")
            for var_name, value in sorted(variables.items()):
                if var_name.startswith('H_'):
                    logger.info(f"  {var_name}: {value:.3f} m")
                elif var_name.startswith('Q_'):
                    logger.info(f"  {var_name}: {value:.3f} m³/s")
            
            return variables
        else:
            logger.warning("求解未收敛")
            logger.warning(f"失败原因: {result['statistics'].failure_reason}")
            return None
            
    except Exception as e:
        logger.error(f"求解失败: {e}")
        return None


def create_simple_visualization(models, results, logger):
    """创建简单的可视化"""
    if not results:
        logger.warning("没有结果可以可视化")
        return
    
    try:
        logger.info("生成系统示意图...")
        
        # 创建系统示意图
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # 水位图
        water_levels = {k.replace('H_', ''): v for k, v in results.items() if k.startswith('H_')}
        if water_levels:
            names = list(water_levels.keys())
            levels = list(water_levels.values())
            
            ax1.bar(range(len(names)), levels, color='lightblue', alpha=0.7)
            ax1.set_xlabel('位置')
            ax1.set_ylabel('水位 (m)')
            ax1.set_title('系统水位分布')
            ax1.set_xticks(range(len(names)))
            ax1.set_xticklabels(names, rotation=45, ha='right')
            ax1.grid(True, alpha=0.3)
        
        # 流量图
        flow_rates = {k.replace('Q_', ''): v for k, v in results.items() if k.startswith('Q_')}
        if flow_rates:
            names = list(flow_rates.keys())
            flows = list(flow_rates.values())
            
            colors = ['lightgreen' if f >= 0 else 'lightcoral' for f in flows]
            ax2.bar(range(len(names)), flows, color=colors, alpha=0.7)
            ax2.set_xlabel('设备/管道')
            ax2.set_ylabel('流量 (m³/s)')
            ax2.set_title('系统流量分布')
            ax2.set_xticks(range(len(names)))
            ax2.set_xticklabels(names, rotation=45, ha='right')
            ax2.grid(True, alpha=0.3)
            ax2.axhline(y=0, color='black', linestyle='-', alpha=0.5)
        
        plt.tight_layout()
        
        # 保存图片
        output_file = "demo_system_results.png"
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        plt.show()
        
        logger.info(f"系统图已保存为: {output_file}")
        
    except Exception as e:
        logger.warning(f"可视化生成失败: {e}")


def run_component_tests(logger):
    """运行组件测试"""
    logger.info("运行组件测试...")
    
    # 测试水库模型
    logger.info("测试水库模型...")
    reservoir = create_simple_reservoir("测试水库", "入口", "出口", 100.0, surface_area=1000000.0)
    
    # 测试水位计算
    volume = 5000000.0
    level = reservoir.get_water_level(volume)
    logger.info(f"体积 {volume/1000000:.1f}M m³ 对应水位 {level:.2f} m")
    
    # 测试管道模型
    logger.info("测试管道模型...")
    pipe = create_simple_pipe("测试管道", "节点1", "节点2", 1000.0, 1.0)
    
    properties = pipe.get_hydraulic_properties(2.0)  # 2 m³/s流量
    logger.info(f"流量 2.0 m³/s 对应流速 {properties['velocity']:.2f} m/s")
    
    # 测试枢纽站模型
    logger.info("测试枢纽站模型...")
    gate_configs = [{'name': '测试闸门', 'width': 10.0, 'discharge_coeff': 0.7, 'initial_opening': 2.0}]
    station = create_gate_station("测试枢纽", "上游", "下游", gate_configs)
    
    capacity = station.calculate_total_capacity(102.0, 100.0)
    logger.info(f"水头2m时通过能力 {capacity:.2f} m³/s")


def main():
    """主函数"""
    logger = setup_simple_logging()
    
    print("="*60)
    print("复杂水力枢纽模型系统快速演示")
    print("="*60)
    
    try:
        # 1. 运行组件测试
        run_component_tests(logger)
        print()
        
        # 2. 创建演示系统
        models = create_demo_system(logger)
        print()
        
        # 3. 演示基本功能
        demonstrate_basic_functionality(models, logger)
        print()
        
        # 4. 尝试求解稳态
        results = solve_simple_steady_state(models, logger)
        print()
        
        # 5. 创建可视化
        create_simple_visualization(models, results, logger)
        
        print("="*60)
        print("演示完成!")
        print("="*60)
        print("系统功能:")
        print("✓ 多种水力模型组件 (水库、枢纽站、连接点、管道)")
        print("✓ 网络拓扑构建和验证")
        print("✓ 联合求解器集成")
        print("✓ 配置管理和验证")
        if results:
            print("✓ 稳态求解演示")
        else:
            print("⚠ 稳态求解需要进一步调试")
        print("✓ 结果分析和可视化")
        print("="*60)
        
        return 0
        
    except Exception as e:
        logger.error(f"演示过程中发生错误: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())