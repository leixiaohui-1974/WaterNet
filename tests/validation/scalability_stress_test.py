"""
大规模系统扩展性压力测试

测试边界条件框架在不同规模下的性能表现
评估内存使用效率和计算扩展性

Author: WaterNet Development Team
Date: 2024-10-04
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import time
import logging
import psutil
import tracemalloc
import gc
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from pathlib import Path

# 导入边界条件框架模块
from waternet.models.boundary_conditions import *
from waternet.models.control_signals import *
from waternet.models.implicit_solver import *
from waternet.models.sparse_matrix import *
from waternet.interfaces.hydro_model import DummyModel

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

logger = logging.getLogger(__name__)


@dataclass
class ScalabilityTestConfig:
    """扩展性测试配置"""
    scales: List[int]  # 测试规模
    time_steps: int    # 时间步数
    dt: float         # 时间步长
    iterations: int   # 重复测试次数


class ScalabilityTester:
    """扩展性压力测试器"""
    
    def __init__(self, config: ScalabilityTestConfig):
        self.config = config
        self.results = []
        self.performance_data = {}
        
    def create_large_scale_system(self, n_nodes: int) -> Tuple[List, BoundaryConditionManager, ControlSignalManager]:
        """创建大规模系统"""
        logger.info(f"创建 {n_nodes} 节点的大规模系统")
        
        # 创建网络拓扑 - 树状网络
        models = []
        for i in range(n_nodes - 1):
            upstream = f"node_{i}"
            downstream = f"node_{i+1}"
            model = DummyModel(f"pipe_{i}", upstream, downstream, 
                             k=1.0 + 0.1 * np.random.randn(), 
                             b=0.01 * np.random.randn())
            models.append(model)
        
        # 创建边界条件 - 约20%的节点有边界条件
        boundary_manager = BoundaryConditionManager()
        n_boundaries = max(1, n_nodes // 5)
        
        for i in range(n_boundaries):
            node_idx = i * (n_nodes // n_boundaries)
            
            if i % 3 == 0:  # 流量边界
                config = BoundaryConditionConfig(f"flow_bc_{i}", f"流量边界{i}")
                flow_value = 20.0 + 10.0 * np.random.rand()
                bc = FlowBoundary(f"flow_bc_{i}", f"node_{node_idx}", flow_value, config)
                
            elif i % 3 == 1:  # 水位边界
                config = BoundaryConditionConfig(f"stage_bc_{i}", f"水位边界{i}")
                stage_value = 100.0 + 2.0 * np.random.rand()
                bc = StageBoundary(f"stage_bc_{i}", f"node_{node_idx}", stage_value, config)
                
            else:  # 堰流关系边界
                config = BoundaryConditionConfig(f"rating_bc_{i}", f"堰流边界{i}")
                params = {'discharge_coefficient': 2.0 + 0.5 * np.random.rand(),
                         'reference_level': 99.0, 'exponent': 1.5}
                bc = RatingCurveBoundary(f"rating_bc_{i}", f"node_{node_idx}_flow", 
                                       f"node_{node_idx}_stage", "weir", params, config)
            
            boundary_manager.add_boundary_condition(bc)
        
        # 创建控制设备 - 约10%的节点有控制设备
        control_manager = ControlSignalManager()
        n_controls = max(1, n_nodes // 10)
        
        for i in range(n_controls):
            if i % 2 == 0:
                device = create_gate_device(f"gate_{i}", 0.0, 1.0, 0.5 + 0.3 * np.random.rand())
            else:
                device = create_pump_device(f"pump_{i}", 0.0, 1.0, 0.2 * np.random.rand())
            
            control_manager.add_device(device)
        
        logger.info(f"系统创建完成: {len(models)} 模型, {n_boundaries} 边界条件, {n_controls} 控制设备")
        return models, boundary_manager, control_manager
    
    def measure_performance(self, n_nodes: int) -> Dict[str, Any]:
        """测量指定规模的性能"""
        logger.info(f"测试规模: {n_nodes} 节点")
        
        # 性能指标初始化
        metrics = {
            'n_nodes': n_nodes,
            'creation_time': 0.0,
            'creation_memory': 0.0,
            'solve_time': 0.0,
            'solve_memory': 0.0,
            'peak_memory': 0.0,
            'convergence_rate': 0.0,
            'variables_count': 0,
            'equations_count': 0,
            'sparsity_ratio': 0.0
        }
        
        # 测试系统创建性能
        tracemalloc.start()
        gc.collect()
        process = psutil.Process()
        memory_before = process.memory_info().rss / 1024 / 1024
        
        start_time = time.time()
        try:
            models, boundary_manager, control_manager = self.create_large_scale_system(n_nodes)
            creation_time = time.time() - start_time
            
            memory_after_creation = process.memory_info().rss / 1024 / 1024
            creation_memory = memory_after_creation - memory_before
            
            # 分析系统特性
            all_variables = []
            for model in models:
                all_variables.extend(model.get_variable_names())
            all_variables.extend(boundary_manager.get_all_required_variables())
            
            metrics['variables_count'] = len(set(all_variables))
            metrics['equations_count'] = len(models) + boundary_manager.get_boundary_condition_count()
            
            # 稀疏性分析
            try:
                sparsity_info = analyze_system_sparsity(models, list(set(all_variables)), boundary_manager)
                metrics['sparsity_ratio'] = sparsity_info['sparsity_ratio']
            except:
                metrics['sparsity_ratio'] = 0.5  # 默认值
            
            # 求解器性能测试
            solver = create_boundary_solver(
                models=models,
                boundary_conditions=list(boundary_manager.boundary_conditions.values()),
                control_devices=list(control_manager.devices.values())
            )
            
            # 初始条件
            initial_conditions = {}
            for var in set(all_variables):
                if var.startswith('H_'):
                    initial_conditions[var] = 100.0 + np.random.rand()
                elif var.startswith('Q_'):
                    initial_conditions[var] = 20.0 + 10.0 * np.random.rand()
            
            # 稳态求解测试
            solve_start = time.time()
            result = solver.solve_steady_state(initial_conditions)
            solve_time = time.time() - solve_start
            
            memory_after_solve = process.memory_info().rss / 1024 / 1024
            solve_memory = memory_after_solve - memory_after_creation
            
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            
            # 更新指标
            metrics.update({
                'creation_time': creation_time,
                'creation_memory': creation_memory,
                'solve_time': solve_time,
                'solve_memory': solve_memory,
                'peak_memory': peak / 1024 / 1024,
                'convergence_rate': 1.0 if result['converged'] else 0.0,
                'iterations': result['statistics'].total_iterations if result['converged'] else -1
            })
            
            logger.info(f"  创建时间: {creation_time:.3f}s, 求解时间: {solve_time:.3f}s")
            logger.info(f"  内存使用: 创建 {creation_memory:.1f}MB, 求解 {solve_memory:.1f}MB")
            logger.info(f"  收敛状态: {result['converged']}, 变量数: {metrics['variables_count']}")
            
        except Exception as e:
            logger.error(f"规模 {n_nodes} 测试失败: {e}")
            metrics['error'] = str(e)
            tracemalloc.stop()
        
        return metrics
    
    def run_scalability_tests(self) -> Dict[str, Any]:
        """运行扩展性测试"""
        logger.info("开始大规模系统扩展性压力测试")
        logger.info(f"测试规模: {self.config.scales}")
        
        all_results = []
        
        for scale in self.config.scales:
            scale_results = []
            
            # 多次重复测试
            for iteration in range(self.config.iterations):
                logger.info(f"规模 {scale}, 第 {iteration + 1}/{self.config.iterations} 次测试")
                
                result = self.measure_performance(scale)
                result['iteration'] = iteration
                scale_results.append(result)
                
                # 强制垃圾回收
                gc.collect()
                time.sleep(0.5)  # 短暂休息
            
            # 计算平均值
            successful_results = [r for r in scale_results if 'error' not in r]
            if successful_results:
                avg_result = self._calculate_average_metrics(successful_results)
                avg_result['success_rate'] = len(successful_results) / len(scale_results)
                all_results.append(avg_result)
            else:
                logger.error(f"规模 {scale} 所有测试都失败了")
                all_results.append({
                    'n_nodes': scale,
                    'success_rate': 0.0,
                    'all_failed': True
                })
        
        # 生成分析报告
        analysis = self._analyze_scalability(all_results)
        
        self.results = all_results
        self.performance_data = analysis
        
        return {
            'test_config': self.config,
            'detailed_results': all_results,
            'analysis': analysis
        }
    
    def _calculate_average_metrics(self, results: List[Dict]) -> Dict[str, float]:
        """计算平均指标"""
        if not results:
            return {}
        
        avg_metrics = {}
        numeric_keys = ['n_nodes', 'creation_time', 'creation_memory', 'solve_time', 
                       'solve_memory', 'peak_memory', 'convergence_rate', 'variables_count',
                       'equations_count', 'sparsity_ratio', 'iterations']
        
        for key in numeric_keys:
            values = [r[key] for r in results if key in r and isinstance(r[key], (int, float))]
            if values:
                avg_metrics[key] = np.mean(values)
                avg_metrics[f'{key}_std'] = np.std(values)
        
        return avg_metrics
    
    def _analyze_scalability(self, results: List[Dict]) -> Dict[str, Any]:
        """分析扩展性"""
        successful_results = [r for r in results if not r.get('all_failed', False)]
        
        if len(successful_results) < 2:
            return {'status': 'insufficient_data'}
        
        # 提取数据
        scales = [r['n_nodes'] for r in successful_results]
        creation_times = [r['creation_time'] for r in successful_results]
        solve_times = [r['solve_time'] for r in successful_results]
        memories = [r['peak_memory'] for r in successful_results]
        
        # 计算扩展性指标
        analysis = {
            'scale_range': (min(scales), max(scales)),
            'time_complexity': self._estimate_complexity(scales, solve_times),
            'memory_complexity': self._estimate_complexity(scales, memories),
            'performance_degradation': self._calculate_degradation(scales, solve_times),
            'memory_efficiency': self._calculate_memory_efficiency(successful_results),
            'recommended_max_scale': self._estimate_max_scale(successful_results)
        }
        
        return analysis
    
    def _estimate_complexity(self, scales: List[float], metrics: List[float]) -> str:
        """估算复杂度"""
        if len(scales) < 2:
            return "unknown"
        
        # 简单的对数回归分析
        log_scales = np.log(scales)
        log_metrics = np.log(metrics)
        
        slope = np.polyfit(log_scales, log_metrics, 1)[0]
        
        if slope < 1.2:
            return "linear"
        elif slope < 1.8:
            return "superlinear"
        elif slope < 2.5:
            return "quadratic"
        else:
            return "exponential"
    
    def _calculate_degradation(self, scales: List[float], times: List[float]) -> float:
        """计算性能退化率"""
        if len(scales) < 2:
            return 0.0
        
        # 计算相对于最小规模的性能退化
        min_idx = scales.index(min(scales))
        max_idx = scales.index(max(scales))
        
        scale_ratio = scales[max_idx] / scales[min_idx]
        time_ratio = times[max_idx] / times[min_idx]
        
        return time_ratio / scale_ratio  # 期望为1.0（线性扩展）
    
    def _calculate_memory_efficiency(self, results: List[Dict]) -> float:
        """计算内存效率"""
        efficiencies = []
        for r in results:
            variables = r.get('variables_count', 1)
            memory = r.get('peak_memory', 1)
            efficiency = variables / memory  # 每MB内存处理的变量数
            efficiencies.append(efficiency)
        
        return np.mean(efficiencies)
    
    def _estimate_max_scale(self, results: List[Dict]) -> int:
        """估算推荐的最大规模"""
        # 基于内存使用和求解时间的简单启发式
        for r in results:
            if r.get('solve_time', 0) > 60:  # 超过1分钟
                return int(r['n_nodes'] * 0.8)
            if r.get('peak_memory', 0) > 1000:  # 超过1GB
                return int(r['n_nodes'] * 0.9)
        
        # 如果都在合理范围内，推断最大值
        max_tested = max(r['n_nodes'] for r in results)
        return int(max_tested * 2)
    
    def generate_performance_plots(self, output_dir: Path = None):
        """生成性能图表"""
        if not self.results:
            logger.warning("没有测试结果，无法生成图表")
            return
        
        if output_dir is None:
            output_dir = Path(".")
        
        successful_results = [r for r in self.results if not r.get('all_failed', False)]
        
        if len(successful_results) < 2:
            logger.warning("成功结果太少，无法生成有意义的图表")
            return
        
        scales = [r['n_nodes'] for r in successful_results]
        creation_times = [r['creation_time'] for r in successful_results]
        solve_times = [r['solve_time'] for r in successful_results]
        memories = [r['peak_memory'] for r in successful_results]
        variables = [r['variables_count'] for r in successful_results]
        
        # 创建多子图
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('边界条件框架扩展性性能分析', fontsize=16, fontweight='bold')
        
        # 时间性能
        axes[0, 0].loglog(scales, solve_times, 'bo-', linewidth=2, markersize=8, label='求解时间')
        axes[0, 0].loglog(scales, creation_times, 'ro-', linewidth=2, markersize=8, label='创建时间')
        axes[0, 0].set_xlabel('系统规模（节点数）', fontsize=12)
        axes[0, 0].set_ylabel('时间 (秒)', fontsize=12)
        axes[0, 0].set_title('计算时间扩展性', fontsize=14, fontweight='bold')
        axes[0, 0].grid(True, alpha=0.3)
        axes[0, 0].legend(fontsize=11)
        
        # 内存使用
        axes[0, 1].loglog(scales, memories, 'go-', linewidth=2, markersize=8)
        axes[0, 1].set_xlabel('系统规模（节点数）', fontsize=12)
        axes[0, 1].set_ylabel('峰值内存 (MB)', fontsize=12)
        axes[0, 1].set_title('内存使用扩展性', fontsize=14, fontweight='bold')
        axes[0, 1].grid(True, alpha=0.3)
        
        # 变量规模
        axes[1, 0].loglog(scales, variables, 'mo-', linewidth=2, markersize=8)
        axes[1, 0].set_xlabel('系统规模（节点数）', fontsize=12)
        axes[1, 0].set_ylabel('变量数量', fontsize=12)
        axes[1, 0].set_title('系统复杂度增长', fontsize=14, fontweight='bold')
        axes[1, 0].grid(True, alpha=0.3)
        
        # 效率指标
        memory_per_var = [m/v for m, v in zip(memories, variables)]
        time_per_var = [t/v*1000 for t, v in zip(solve_times, variables)]  # ms per variable
        
        axes[1, 1].semilogx(scales, memory_per_var, 'co-', linewidth=2, markersize=8, label='内存/变量 (MB)')
        ax2 = axes[1, 1].twinx()
        ax2.semilogx(scales, time_per_var, 'yo-', linewidth=2, markersize=8, label='时间/变量 (ms)')
        
        axes[1, 1].set_xlabel('系统规模（节点数）', fontsize=12)
        axes[1, 1].set_ylabel('内存效率 (MB/变量)', fontsize=12, color='c')
        ax2.set_ylabel('时间效率 (ms/变量)', fontsize=12, color='y')
        axes[1, 1].set_title('计算效率分析', fontsize=14, fontweight='bold')
        axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # 保存图表
        plot_file = output_dir / "scalability_performance.png"
        plt.savefig(plot_file, dpi=300, bbox_inches='tight')
        plt.show()
        
        logger.info(f"性能图表已保存到: {plot_file}")


def main():
    """主测试程序"""
    logger.info("🚀 WaterNet边界条件框架扩展性压力测试开始")
    
    # 测试配置
    config = ScalabilityTestConfig(
        scales=[10, 25, 50, 100, 200, 500],  # 测试规模
        time_steps=100,
        dt=60.0,
        iterations=3  # 每个规模重复3次
    )
    
    # 运行测试
    tester = ScalabilityTester(config)
    results = tester.run_scalability_tests()
    
    # 输出结果
    logger.info("=" * 60)
    logger.info("扩展性测试结果:")
    
    analysis = results['analysis']
    if analysis.get('status') != 'insufficient_data':
        logger.info(f"测试规模范围: {analysis['scale_range'][0]} - {analysis['scale_range'][1]} 节点")
        logger.info(f"时间复杂度: {analysis['time_complexity']}")
        logger.info(f"内存复杂度: {analysis['memory_complexity']}")
        logger.info(f"性能退化率: {analysis['performance_degradation']:.2f}")
        logger.info(f"内存效率: {analysis['memory_efficiency']:.2f} 变量/MB")
        logger.info(f"推荐最大规模: {analysis['recommended_max_scale']} 节点")
    
    # 生成图表
    tester.generate_performance_plots()
    
    logger.info("✅ 扩展性压力测试完成")
    return results


if __name__ == "__main__":
    main()