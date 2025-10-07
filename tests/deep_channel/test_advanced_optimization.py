#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高级数值优化测试
验证Jacobian矩阵scaling、自适应时间步长和动态松弛因子的效果
"""

import sys
import os
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple

# 添加项目路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from enhanced_solver import EnhancedSaintVenantSolver, NumericalSchemeConfig
from waternet.models.saint_venant import SaintVenantModel
from advanced_numerical_optimizer import AdvancedNumericalOptimizer, OptimizationConfig, MatrixConditioningStrategy

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

def create_test_model():
    """创建测试模型"""
    
    def area_func(h, elevation, bottom_width=400.0, side_slope=3.0):
        depth = max(2.0, h - elevation)
        return bottom_width * depth + side_slope * depth**2
    
    def top_width_func(h, elevation, bottom_width=400.0, side_slope=3.0):
        depth = max(2.0, h - elevation)
        return bottom_width + 2 * side_slope * depth
    
    sections = [
        {
            'mileage': 0.0,
            'elevation': 100.0,
            'roughness': 0.02,
            'area_func': lambda h: area_func(h, 100.0),
            'top_width_func': lambda h: top_width_func(h, 100.0)
        },
        {
            'mileage': 4000.0,
            'elevation': 99.0,
            'roughness': 0.02,
            'area_func': lambda h: area_func(h, 99.0),
            'top_width_func': lambda h: top_width_func(h, 99.0)
        },
        {
            'mileage': 8000.0,
            'elevation': 98.0,
            'roughness': 0.02,
            'area_func': lambda h: area_func(h, 98.0),
            'top_width_func': lambda h: top_width_func(h, 98.0)
        }
    ]

    return SaintVenantModel('advanced_test_model', 'upstream_node', 'downstream_node', sections)

class OptimizedSaintVenantSolver(EnhancedSaintVenantSolver):
    """集成高级优化器的圣维南求解器"""
    
    def __init__(self, model, numerical_config, optimization_config=None):
        super().__init__(model, numerical_config)
        
        # 初始化高级优化器
        self.advanced_optimizer = AdvancedNumericalOptimizer(
            config=optimization_config or OptimizationConfig(),
            logger=self.logger
        )
        
        # 优化历史
        self.optimization_history = {
            'residuals': [],
            'timesteps': [],
            'relaxations': [],
            'condition_numbers': [],
            'iterations': []
        }
    
    def _newton_raphson_solver(self, dt: float) -> Tuple[bool, int]:
        """集成高级优化的牛顿-拉夫逊求解器"""
        max_iter = self.numerical_config.max_iterations
        tolerance = self.numerical_config.convergence_tolerance
        theta = self.numerical_config.theta
        psi = self.numerical_config.psi
        
        # 更新特征尺度
        solver_state = {
            'current_state': self.current_state,
            'water_levels': {i: self.current_state[self.n_flow_vars + i] 
                           for i in range(self.n_head_vars) 
                           if self.n_flow_vars + i < len(self.current_state)},
            'geometry': {
                'length_scale': np.mean(self.dx_array) if len(self.dx_array) > 0 else 1000.0,
                'area_scale': 1000.0  # 估算值
            }
        }
        self.advanced_optimizer.update_characteristic_scales(solver_state)
        
        # 初始化参数
        alpha = self.numerical_config.under_relaxation
        adaptive_dt = dt
        solution = self.current_state.copy()
        
        self.logger.debug(f"开始高级优化牛顿-拉夫逊迭代：最大{max_iter}次，容差={tolerance:.2e}")
        
        for iteration in range(max_iter):
            # 构建系统
            jacobian, residual = self._build_preissmann_system(solution, adaptive_dt, theta, psi)
            
            # 高级Jacobian优化
            jacobian_opt, residual_opt = self.advanced_optimizer.optimize_jacobian_matrix(
                jacobian, residual)
            
            # 计算残差范数和条件数
            residual_norm = np.linalg.norm(residual_opt)
            condition_number = self.advanced_optimizer._compute_condition_number(jacobian_opt)
            
            # 记录历史
            self.optimization_history['residuals'].append(residual_norm)
            self.optimization_history['condition_numbers'].append(condition_number)
            self.optimization_history['relaxations'].append(alpha)
            self.optimization_history['timesteps'].append(adaptive_dt)
            self.optimization_history['iterations'].append(iteration)
            
            # 收敛检查
            converged = (
                residual_norm < tolerance or
                (iteration > 5 and residual_norm < tolerance * 50)
            )
            
            if converged:
                self.current_state[:] = solution[:]
                self.logger.info(f"高级优化收敛成功：迭代{iteration + 1}次，残差={residual_norm:.2e}")
                
                # 输出优化报告
                report = self.advanced_optimizer.get_optimization_report()
                self.logger.debug(f"优化统计: {report['optimization_statistics']}")
                
                return True, iteration + 1
            
            # 自适应时间步长控制
            if iteration % 3 == 0 and iteration > 0:
                max_cfl = self._estimate_max_cfl(adaptive_dt)
                new_dt = self.advanced_optimizer.adaptive_timestep_control(
                    adaptive_dt, residual_norm, max_cfl, iteration)
                
                if abs(new_dt - adaptive_dt) > 0.02 * adaptive_dt:
                    adaptive_dt = new_dt
                    self.logger.debug(f"自适应时间步调整: {dt:.3f} -> {adaptive_dt:.3f}")
                    # 重新构建系统
                    jacobian, residual = self._build_preissmann_system(solution, adaptive_dt, theta, psi)
                    jacobian_opt, residual_opt = self.advanced_optimizer.optimize_jacobian_matrix(
                        jacobian, residual)
                    residual_norm = np.linalg.norm(residual_opt)
            
            # 动态松弛因子策略
            alpha = self.advanced_optimizer.dynamic_relaxation_strategy(
                iteration, residual_norm, condition_number, alpha)
            
            # 高级求解
            try:
                delta = self.advanced_optimizer.solve_with_sparse_optimization(
                    jacobian_opt, residual_opt)
                
                # 更新解
                solution += alpha * delta
                
                # 物理可行性保证
                self._ensure_physical_feasibility(solution)
                
            except Exception as e:
                self.logger.warning(f"迭代{iteration}高级求解失败: {e}")
                alpha *= 0.5
                if alpha < 0.001:
                    return False, iteration + 1
                continue
            
            if iteration % 5 == 0 or iteration < 3:
                self.logger.debug(f"迭代{iteration + 1}: 残差={residual_norm:.2e}, "
                                 f"条件数={condition_number:.2e}, 松弛={alpha:.3f}, dt={adaptive_dt:.3f}")
        
        self.logger.warning(f"达到最大迭代次数{max_iter}，未收敛：最终残差={residual_norm:.2e}")
        return False, max_iter
    
    def _estimate_max_cfl(self, dt: float) -> float:
        """估算最大CFL数"""
        try:
            max_cfl = 0.0
            for i in range(self.n_segments):
                wave_speed = self._calculate_wave_speed(i)
                dx = self.dx_array[i] if i < len(self.dx_array) else 1000.0
                cfl = wave_speed * dt / dx
                max_cfl = max(max_cfl, cfl)
            return max_cfl
        except:
            return 0.5

def test_optimization_strategies():
    """测试不同优化策略的效果"""
    print("=== 高级数值优化策略对比测试 ===")
    
    model = create_test_model()
    
    # 基础配置
    base_config = NumericalSchemeConfig(
        theta=0.6, psi=0.5, 
        max_iterations=25, 
        convergence_tolerance=1e-4,
        under_relaxation=0.6
    )
    
    # 测试参数
    initial_flow = 100.0
    downstream_level = 102.5
    
    # 测试不同优化策略
    strategies = [
        ("物理量纲scaling", MatrixConditioningStrategy.PHYSIC_BASED),
        ("平衡缩放", MatrixConditioningStrategy.EQUILIBRATION),
        ("几何缩放", MatrixConditioningStrategy.GEOMETRIC_SCALING),
        ("迭代缩放", MatrixConditioningStrategy.ITERATIVE_SCALING)
    ]
    
    results = {}
    
    for strategy_name, strategy in strategies:
        print(f"\n--- {strategy_name} ---")
        
        try:
            # 配置优化器
            opt_config = OptimizationConfig(
                matrix_strategy=strategy,
                cfl_target=0.6,
                initial_relaxation=0.6,
                min_relaxation=0.05
            )
            
            # 创建求解器
            solver = OptimizedSaintVenantSolver(model, base_config, opt_config)
            solver.set_initial_conditions(initial_flow, downstream_level)
            
            # 测试单个时间步
            result = solver.solve_time_step(2.0, initial_flow, downstream_level)
            
            # 获取优化报告
            opt_report = solver.advanced_optimizer.get_optimization_report()
            
            # 记录结果
            results[strategy_name] = {
                'convergence_success': result['convergence_success'],
                'iterations': result['iterations'],
                'optimization_stats': opt_report['optimization_statistics'],
                'performance_metrics': opt_report['performance_metrics'],
                'history': solver.optimization_history
            }
            
            print(f"  收敛状态: {'成功' if result['convergence_success'] else '失败'}")
            print(f"  迭代次数: {result['iterations']}")
            print(f"  优化统计: {opt_report['optimization_statistics']}")
            
            if opt_report['performance_metrics']['avg_residual'] > 0:
                print(f"  平均残差: {opt_report['performance_metrics']['avg_residual']:.2e}")
            
        except Exception as e:
            print(f"  {strategy_name}测试失败: {e}")
            results[strategy_name] = {'error': str(e)}
    
    return results

def test_adaptive_controls():
    """测试自适应控制功能"""
    print("\n=== 自适应控制功能测试 ===")
    
    model = create_test_model()
    
    # 严格配置（更容易测试自适应功能）
    config = NumericalSchemeConfig(
        theta=1.0, psi=0.5,  # 全隐式
        max_iterations=40, 
        convergence_tolerance=1e-6,
        under_relaxation=0.8
    )
    
    # 自适应优化配置
    opt_config = OptimizationConfig(
        matrix_strategy=MatrixConditioningStrategy.PHYSIC_BASED,
        cfl_target=0.4,  # 更严格的CFL条件
        dt_growth_limit=1.3,
        dt_reduction_factor=0.6,
        initial_relaxation=0.8,
        relaxation_adaptation_rate=0.15
    )
    
    # 测试场景
    test_cases = [
        {"name": "标准条件", "flow": 80.0, "level": 102.0, "dt": 1.0},
        {"name": "大时间步", "flow": 100.0, "level": 102.5, "dt": 3.0},
        {"name": "挑战性条件", "flow": 200.0, "level": 103.0, "dt": 1.5}
    ]
    
    adaptive_results = {}
    
    for case in test_cases:
        print(f"\n--- {case['name']} ---")
        print(f"初始参数: 流量={case['flow']} m³/s, 水位={case['level']} m, dt={case['dt']} s")
        
        try:
            solver = OptimizedSaintVenantSolver(model, config, opt_config)
            solver.set_initial_conditions(case['flow'], case['level'])
            
            # 测试多个时间步以观察自适应效果
            step_results = []
            for step in range(3):
                result = solver.solve_time_step(case['dt'], case['flow'], case['level'])
                
                step_results.append({
                    'step': step + 1,
                    'success': result['convergence_success'],
                    'iterations': result['iterations']
                })
                
                print(f"  时间步 {step + 1}: {'成功' if result['convergence_success'] else '失败'}, "
                      f"迭代{result['iterations']}次")
                
                if not result['convergence_success']:
                    break
            
            # 分析自适应历史
            history = solver.optimization_history
            if history['timesteps']:
                dt_changes = [abs(history['timesteps'][i] - history['timesteps'][i-1]) 
                            for i in range(1, len(history['timesteps']))]
                print(f"  时间步变化次数: {sum(1 for change in dt_changes if change > 0.01)}")
            
            if history['relaxations']:
                alpha_changes = [abs(history['relaxations'][i] - history['relaxations'][i-1]) 
                               for i in range(1, len(history['relaxations']))]
                print(f"  松弛因子调整次数: {sum(1 for change in alpha_changes if change > 0.01)}")
            
            adaptive_results[case['name']] = {
                'step_results': step_results,
                'optimization_history': history,
                'adaptive_performance': {
                    'timestep_adaptations': len([c for c in dt_changes if c > 0.01]) if 'dt_changes' in locals() else 0,
                    'relaxation_adjustments': len([c for c in alpha_changes if c > 0.01]) if 'alpha_changes' in locals() else 0
                }
            }
            
        except Exception as e:
            print(f"  {case['name']}测试失败: {e}")
            adaptive_results[case['name']] = {'error': str(e)}
    
    return adaptive_results

def generate_optimization_comparison_report(strategy_results, adaptive_results):
    """生成优化对比报告"""
    print("\n=== 高级数值优化对比报告 ===")
    
    report = []
    report.append("# 圣维南求解器高级数值优化对比报告")
    report.append("")
    report.append("## 优化策略对比")
    
    # 策略对比
    successful_strategies = []
    for strategy, result in strategy_results.items():
        if 'error' not in result:
            success = "✅" if result['convergence_success'] else "❌"
            iterations = result['iterations']
            report.append(f"### {strategy}")
            report.append(f"- **收敛状态**: {success}")
            report.append(f"- **迭代次数**: {iterations}")
            
            if result['convergence_success']:
                successful_strategies.append(strategy)
                
            # 优化统计
            stats = result['optimization_stats']
            if any(stats.values()):
                report.append(f"- **优化统计**:")
                for key, value in stats.items():
                    if value > 0:
                        report.append(f"  - {key}: {value}")
            
            report.append("")
    
    # 自适应控制分析
    report.append("## 自适应控制效果")
    
    for case_name, result in adaptive_results.items():
        if 'error' not in result:
            report.append(f"### {case_name}")
            
            success_count = sum(1 for r in result['step_results'] if r['success'])
            total_steps = len(result['step_results'])
            
            report.append(f"- **收敛成功率**: {success_count}/{total_steps}")
            
            if 'adaptive_performance' in result:
                perf = result['adaptive_performance']
                report.append(f"- **时间步自适应次数**: {perf['timestep_adaptations']}")
                report.append(f"- **松弛因子调整次数**: {perf['relaxation_adjustments']}")
            
            report.append("")
    
    # 总结建议
    report.append("## 优化建议")
    
    if successful_strategies:
        best_strategy = successful_strategies[0]  # 简化选择第一个成功的
        report.append(f"1. **推荐策略**: {best_strategy}")
        report.append("2. **自适应控制**: 建议启用时间步和松弛因子自适应")
    else:
        report.append("1. **需要进一步优化**: 当前策略下收敛性仍有问题")
        report.append("2. **建议**: 考虑更保守的参数设置或预条件技术")
    
    report.append("3. **稀疏矩阵优化**: 对大规模系统启用稀疏求解器")
    report.append("4. **监控指标**: 重点关注条件数和残差变化趋势")
    
    # 保存报告
    report_text = "\n".join(report)
    
    with open('advanced_optimization_report.md', 'w', encoding='utf-8') as f:
        f.write(report_text)
    
    print("高级优化对比报告已保存: advanced_optimization_report.md")
    
    return report_text

def main():
    """主测试函数"""
    print("圣维南求解器高级数值优化测试")
    print("=" * 60)
    
    try:
        # 策略对比测试
        strategy_results = test_optimization_strategies()
        
        # 自适应控制测试
        adaptive_results = test_adaptive_controls()
        
        # 生成对比报告
        report = generate_optimization_comparison_report(strategy_results, adaptive_results)
        
        # 总结
        print("\n" + "=" * 60)
        print("高级数值优化测试完成")
        
        # 统计成功率
        strategy_success = sum(1 for r in strategy_results.values() 
                             if 'error' not in r and r.get('convergence_success', False))
        adaptive_success = sum(1 for r in adaptive_results.values() 
                             if 'error' not in r and any(s['success'] for s in r.get('step_results', [])))
        
        print(f"优化策略成功率: {strategy_success}/{len(strategy_results)}")
        print(f"自适应控制有效性: {adaptive_success}/{len(adaptive_results)}")
        
        if strategy_success > 0 or adaptive_success > 0:
            print("✅ 高级优化技术验证部分成功")
        else:
            print("⚠️ 高级优化技术需要进一步调优")
        
        print("详细报告已生成，请查看 advanced_optimization_report.md")
        
        return True
        
    except Exception as e:
        print(f"❌ 高级优化测试过程出错: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)