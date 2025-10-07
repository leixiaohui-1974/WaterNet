#!/usr/bin/env python3
"""
WaterNet 性能基准测试

测试各种模型和求解器的计算性能、精度和稳定性。

Author: WaterNet Development Team  
Date: 2024-10-03
"""

import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import sys
import os
import gc
from typing import Dict, List, Any
import warnings

# 尝试导入可选依赖
try:
    import memory_profiler
    HAS_MEMORY_PROFILER = True
except ImportError:
    HAS_MEMORY_PROFILER = False
    warnings.warn("未安装memory_profiler，将跳过内存性能测试")

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    warnings.warn("未安装psutil，将使用简化系统监控")

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from waternet.models import SaintVenantModel, MuskingumModel, StorageRoutingModel
from waternet.models import SolverFactory
from waternet.config import ConfigManager


class PerformanceBenchmark:
    """性能基准测试类"""
    
    def __init__(self, output_dir=None):
        """
        初始化基准测试
        
        Args:
            output_dir: 输出目录
        """
        if output_dir is None:
            output_dir = Path(__file__).parent.parent / 'benchmark_results'
        
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.results = {
            'model_performance': [],
            'solver_performance': [],
            'memory_usage': [],
            'accuracy_tests': [],
            'stability_tests': []
        }
        
        # 创建测试模型
        self._setup_test_models()
    
    def _setup_test_models(self):
        """设置测试模型"""
        print("设置测试模型...")
        
        # 简单渠道
        self.simple_sections = [
            {
                'mileage': 0.0, 'elevation': 100.0, 'roughness': 0.025,
                'area_func': lambda h: max(0, h - 100) * 10,
                'top_width_func': lambda h: 10 if h > 100 else 0
            },
            {
                'mileage': 1000.0, 'elevation': 99.0, 'roughness': 0.025,
                'area_func': lambda h: max(0, h - 99) * 10,
                'top_width_func': lambda h: 10 if h > 99 else 0
            }
        ]
        
        # 复杂渠道
        self.complex_sections = []
        n_sections = 10
        for i in range(n_sections):
            mileage = i * 100.0
            elevation = 100.0 - i * 0.1
            roughness = 0.025 + i * 0.001
            width = 8.0 + i * 0.5
            
            self.complex_sections.append({
                'mileage': mileage,
                'elevation': elevation,
                'roughness': roughness,
                'area_func': lambda h, w=width, e=elevation: max(0, h - e) * w,
                'top_width_func': lambda h, w=width, e=elevation: w if h > e else 0
            })
        
        # 物理关系函数
        self.V_to_H_func = lambda V: 99.0 + V * 1e-4
        self.H_to_Q_func = lambda H: 25.0 * max(0, H - 99.0) ** 1.5
        
        print("✅ 测试模型设置完成")
    
    def benchmark_model_performance(self):
        """基准测试模型性能"""
        print("\n🚀 开始模型性能基准测试...")
        
        # 测试配置
        test_configs = [
            {
                'name': 'SaintVenant_Simple',
                'model_type': 'saint_venant',
                'sections': self.simple_sections,
                'test_type': 'steady'
            },
            {
                'name': 'SaintVenant_Complex', 
                'model_type': 'saint_venant',
                'sections': self.complex_sections,
                'test_type': 'steady'
            },
            {
                'name': 'Muskingum_Fast',
                'model_type': 'muskingum',
                'params': {'K': 1800.0, 'x': 0.2, 'dt': 60.0, 'initial_V': 10000.0},
                'test_type': 'unsteady'
            },
            {
                'name': 'StorageRouting_Standard',
                'model_type': 'storage_routing', 
                'params': {'dt': 60.0, 'initial_V': 10000.0},
                'test_type': 'unsteady'
            }
        ]
        
        for config in test_configs:
            print(f"\n测试配置: {config['name']}")
            
            # 创建模型
            start_time = time.time()
            model = self._create_test_model(config)
            creation_time = time.time() - start_time
            
            if model is None:
                continue
                
            # 性能测试
            if config['test_type'] == 'steady':
                perf_result = self._test_steady_performance(model, config['name'])
            else:
                perf_result = self._test_unsteady_performance(model, config['name'])
            
            perf_result['creation_time'] = creation_time
            perf_result['model_name'] = config['name']
            perf_result['model_type'] = config['model_type']
            
            self.results['model_performance'].append(perf_result)
            
            # 清理内存
            del model
            gc.collect()
        
        print("✅ 模型性能基准测试完成")
    
    def _create_test_model(self, config):
        """创建测试模型"""
        try:
            if config['model_type'] == 'saint_venant':
                return SaintVenantModel(
                    name=config['name'],
                    upstream_node="up",
                    downstream_node="down",
                    sections=config['sections']
                )
            elif config['model_type'] == 'muskingum':
                params = config['params']
                return MuskingumModel(
                    dt=params['dt'],
                    K=params['K'],
                    x=params['x'],
                    initial_V=params['initial_V'],
                    V_to_H_func=self.V_to_H_func,
                    H_to_Q_func=self.H_to_Q_func,
                    name=config['name']
                )
            elif config['model_type'] == 'storage_routing':
                params = config['params']
                return StorageRoutingModel(
                    dt=params['dt'],
                    initial_V=params['initial_V'],
                    V_to_H_func=self.V_to_H_func,
                    H_to_Q_func=self.H_to_Q_func,
                    name=config['name']
                )
        except Exception as e:
            print(f"❌ 创建模型失败: {e}")
            return None
    
    def _test_steady_performance(self, model, model_name):
        """测试恒定流性能"""
        n_tests = 50
        Q_values = np.linspace(8.0, 20.0, n_tests)
        H_down = 99.5
        
        times = []
        success_count = 0
        
        for Q in Q_values:
            start_time = time.time()
            try:
                result = model.compute_steady_state(Q, H_down)
                if 'total_volume' in result:
                    success_count += 1
            except:
                pass
            times.append(time.time() - start_time)
        
        return {
            'test_type': 'steady',
            'n_tests': n_tests,
            'total_time': sum(times),
            'avg_time': np.mean(times),
            'min_time': np.min(times),
            'max_time': np.max(times),
            'success_rate': success_count / n_tests,
            'throughput': n_tests / sum(times) if sum(times) > 0 else 0
        }
    
    def _test_unsteady_performance(self, model, model_name):
        """测试非恒定流性能"""
        n_steps = 100
        Q_series = 10.0 + 5.0 * np.sin(np.linspace(0, 4*np.pi, n_steps))
        Q_series = np.maximum(Q_series, 2.0)
        
        start_time = time.time()
        try:
            results = model.run_simulation(Q_series)
            success = len(results) == n_steps + 1
        except Exception as e:
            print(f"❌ 非恒定流测试失败: {e}")
            success = False
            results = None
        
        total_time = time.time() - start_time
        
        return {
            'test_type': 'unsteady',
            'n_steps': n_steps,
            'total_time': total_time,
            'avg_time_per_step': total_time / n_steps,
            'success': success,
            'throughput': n_steps / total_time if total_time > 0 else 0
        }
    
    def benchmark_memory_usage(self):
        """基准测试内存使用"""
        print("\n💾 开始内存使用基准测试...")
        
        if not HAS_MEMORY_PROFILER:
            print("⚠️  跳过内存测试（未安装memory_profiler）")
            return
        
        @memory_profiler.profile
        def memory_test_function():
            # 创建大规模模型
            large_sections = []
            n_sections = 50
            for i in range(n_sections):
                large_sections.append({
                    'mileage': i * 50.0,
                    'elevation': 100.0 - i * 0.05,
                    'roughness': 0.025,
                    'area_func': lambda h, e=100.0-i*0.05: max(0, h - e) * 10,
                    'top_width_func': lambda h, e=100.0-i*0.05: 10 if h > e else 0
                })
            
            # 创建圣维南模型
            large_model = SaintVenantModel(
                name="LargeModel",
                upstream_node="up",
                downstream_node="down", 
                sections=large_sections
            )
            
            # 运行大量计算
            for Q in np.linspace(5.0, 25.0, 20):
                try:
                    result = large_model.compute_steady_state(Q, 99.5)
                except:
                    continue
            
            return large_model
        
        # 捕获内存配置文件输出
        import io
        from contextlib import redirect_stdout
        
        f = io.StringIO()
        with redirect_stdout(f):
            try:
                model = memory_test_function()
                memory_output = f.getvalue()
                
                # 解析内存使用信息
                memory_lines = [line for line in memory_output.split('\n') if 'MiB' in line]
                if memory_lines:
                    memory_usage = memory_lines[-1]
                    self.results['memory_usage'].append({
                        'test': 'large_model',
                        'memory_info': memory_usage
                    })
                
                del model
                gc.collect()
                
            except Exception as e:
                print(f"❌ 内存测试失败: {e}")
        
        print("✅ 内存使用基准测试完成")
    
    def benchmark_accuracy(self):
        """基准测试计算精度"""
        print("\n🎯 开始精度基准测试...")
        
        # 创建参考模型
        ref_model = SaintVenantModel(
            name="Reference",
            upstream_node="up",
            downstream_node="down",
            sections=self.simple_sections
        )
        
        # 测试质量守恒
        Q_test = 12.0
        H_down = 99.4
        
        try:
            result = ref_model.compute_steady_state(Q_test, H_down)
            
            # 计算质量守恒误差
            total_volume = result.get('total_volume', 0)
            n_segments = len(ref_model.segments)
            
            # 简化的质量守恒检查
            expected_volume = Q_test * 100.0  # 简化估算
            volume_error = abs(total_volume - expected_volume) / expected_volume if expected_volume > 0 else 0
            
            self.results['accuracy_tests'].append({
                'test': 'mass_conservation',
                'reference_volume': expected_volume,
                'computed_volume': total_volume,
                'relative_error': volume_error,
                'passed': volume_error < 0.05  # 5%误差阈值
            })
            
        except Exception as e:
            print(f"❌ 精度测试失败: {e}")
        
        print("✅ 精度基准测试完成")
    
    def benchmark_stability(self):
        """基准测试数值稳定性"""
        print("\n⚖️ 开始稳定性基准测试...")
        
        # 创建马斯京干模型进行稳定性测试
        musk_model = MuskingumModel(
            dt=60.0,
            K=3600.0,
            x=0.2,
            initial_V=10000.0,
            V_to_H_func=self.V_to_H_func,
            H_to_Q_func=self.H_to_Q_func,
            name="StabilityTest"
        )
        
        # 测试极端输入
        extreme_inputs = [
            np.ones(100) * 0.1,  # 极小流量
            np.ones(100) * 100.0,  # 极大流量
            np.random.normal(10.0, 5.0, 100),  # 随机噪声
            np.concatenate([np.ones(50) * 5.0, np.ones(50) * 50.0])  # 突变
        ]
        
        for i, Q_series in enumerate(extreme_inputs):
            Q_series = np.maximum(Q_series, 0.1)  # 确保正值
            
            try:
                results = musk_model.run_simulation(Q_series)
                
                # 检查结果稳定性
                Q_out_values = results['Q_out'].values
                is_stable = (
                    np.all(np.isfinite(Q_out_values)) and
                    np.all(Q_out_values >= 0) and
                    np.all(Q_out_values < 1000)  # 合理上界
                )
                
                self.results['stability_tests'].append({
                    'test': f'extreme_input_{i}',
                    'input_type': ['minimal', 'maximal', 'noisy', 'step'][i],
                    'stable': is_stable,
                    'max_output': np.max(Q_out_values),
                    'min_output': np.min(Q_out_values),
                    'has_nan': np.any(np.isnan(Q_out_values)),
                    'has_inf': np.any(np.isinf(Q_out_values))
                })
                
                # 重置模型
                musk_model.reset()
                
            except Exception as e:
                self.results['stability_tests'].append({
                    'test': f'extreme_input_{i}',
                    'input_type': ['minimal', 'maximal', 'noisy', 'step'][i],
                    'stable': False,
                    'error': str(e)
                })
        
        print("✅ 稳定性基准测试完成")
    
    def generate_report(self):
        """生成基准测试报告"""
        print("\n📊 生成基准测试报告...")
        
        report = {
            'summary': self._generate_summary(),
            'detailed_results': self.results,
            'recommendations': self._generate_recommendations()
        }
        
        # 保存报告
        import json
        report_file = self.output_dir / 'benchmark_report.json'
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        
        # 生成可视化
        self._create_visualizations()
        
        # 打印摘要
        self._print_summary(report['summary'])
        
        print(f"✅ 基准测试报告已保存: {report_file}")
    
    def _generate_summary(self):
        """生成摘要统计"""
        summary = {}
        
        # 性能摘要
        if self.results['model_performance']:
            perf_data = self.results['model_performance']
            summary['performance'] = {
                'fastest_model': min(perf_data, key=lambda x: x.get('avg_time', float('inf')))['model_name'],
                'highest_throughput': max(perf_data, key=lambda x: x.get('throughput', 0))['model_name'],
                'average_success_rate': np.mean([p.get('success_rate', p.get('success', 0)) for p in perf_data])
            }
        
        # 精度摘要
        if self.results['accuracy_tests']:
            acc_data = self.results['accuracy_tests']
            summary['accuracy'] = {
                'tests_passed': sum(1 for test in acc_data if test.get('passed', False)),
                'total_tests': len(acc_data),
                'pass_rate': sum(1 for test in acc_data if test.get('passed', False)) / len(acc_data)
            }
        
        # 稳定性摘要
        if self.results['stability_tests']:
            stab_data = self.results['stability_tests']
            summary['stability'] = {
                'stable_tests': sum(1 for test in stab_data if test.get('stable', False)),
                'total_tests': len(stab_data),
                'stability_rate': sum(1 for test in stab_data if test.get('stable', False)) / len(stab_data)
            }
        
        return summary
    
    def _generate_recommendations(self):
        """生成优化建议"""
        recommendations = []
        
        # 基于性能结果的建议
        if self.results['model_performance']:
            perf_data = self.results['model_performance']
            
            # 找出慢速模型
            slow_models = [p for p in perf_data if p.get('avg_time', 0) > 0.1]
            if slow_models:
                recommendations.append(
                    f"考虑优化以下慢速模型: {[m['model_name'] for m in slow_models]}"
                )
            
            # 检查成功率
            low_success = [p for p in perf_data if p.get('success_rate', p.get('success', 1)) < 0.9]
            if low_success:
                recommendations.append(
                    f"以下模型成功率较低，需要改进: {[m['model_name'] for m in low_success]}"
                )
        
        # 基于稳定性结果的建议
        if self.results['stability_tests']:
            unstable_count = sum(1 for test in self.results['stability_tests'] if not test.get('stable', True))
            if unstable_count > 0:
                recommendations.append(
                    f"发现{unstable_count}个稳定性问题，建议加强输入验证和数值保护"
                )
        
        return recommendations
    
    def _create_visualizations(self):
        """创建可视化图表"""
        try:
            # 性能对比图
            if self.results['model_performance']:
                self._plot_performance_comparison()
            
            # 稳定性测试结果
            if self.results['stability_tests']:
                self._plot_stability_results()
                
        except Exception as e:
            print(f"❌ 生成可视化失败: {e}")
    
    def _plot_performance_comparison(self):
        """绘制性能对比图"""
        perf_data = self.results['model_performance']
        
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        fig.suptitle('WaterNet 性能基准测试结果', fontsize=14)
        
        model_names = [p['model_name'] for p in perf_data]
        avg_times = [p.get('avg_time', 0) for p in perf_data]
        throughputs = [p.get('throughput', 0) for p in perf_data]
        success_rates = [p.get('success_rate', p.get('success', 0)) for p in perf_data]
        
        # 平均计算时间
        axes[0, 0].bar(model_names, avg_times)
        axes[0, 0].set_title('平均计算时间')
        axes[0, 0].set_ylabel('时间 (秒)')
        axes[0, 0].tick_params(axis='x', rotation=45)
        
        # 吞吐量
        axes[0, 1].bar(model_names, throughputs)
        axes[0, 1].set_title('计算吞吐量')
        axes[0, 1].set_ylabel('计算/秒')
        axes[0, 1].tick_params(axis='x', rotation=45)
        
        # 成功率
        axes[1, 0].bar(model_names, [sr * 100 for sr in success_rates])
        axes[1, 0].set_title('成功率')
        axes[1, 0].set_ylabel('成功率 (%)')
        axes[1, 0].tick_params(axis='x', rotation=45)
        axes[1, 0].set_ylim(0, 105)
        
        # 综合评分（简化）
        scores = []
        for p in perf_data:
            # 简化评分：速度 + 成功率
            speed_score = 1.0 / (p.get('avg_time', 1) + 0.001)  # 避免除零
            success_score = p.get('success_rate', p.get('success', 0))
            scores.append((speed_score + success_score) / 2)
        
        axes[1, 1].bar(model_names, scores)
        axes[1, 1].set_title('综合性能评分')
        axes[1, 1].set_ylabel('评分')
        axes[1, 1].tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        plt.savefig(self.output_dir / 'performance_comparison.svg', dpi=300, bbox_inches='tight')
        plt.close()
    
    def _plot_stability_results(self):
        """绘制稳定性测试结果"""
        stab_data = self.results['stability_tests']
        
        # 统计稳定性结果
        input_types = [test['input_type'] for test in stab_data]
        stable_flags = [test.get('stable', False) for test in stab_data]
        
        # 创建稳定性统计图
        fig, ax = plt.subplots(1, 1, figsize=(10, 6))
        
        from collections import Counter
        type_counts = Counter(input_types)
        stable_counts = {}
        
        for input_type in type_counts:
            stable_count = sum(1 for test in stab_data 
                             if test['input_type'] == input_type and test.get('stable', False))
            stable_counts[input_type] = stable_count
        
        types = list(type_counts.keys())
        total_counts = [type_counts[t] for t in types]
        stable_counts_list = [stable_counts[t] for t in types]
        
        x = np.arange(len(types))
        width = 0.35
        
        ax.bar(x - width/2, total_counts, width, label='总测试数', alpha=0.7)
        ax.bar(x + width/2, stable_counts_list, width, label='稳定测试数', alpha=0.7)
        
        ax.set_xlabel('输入类型')
        ax.set_ylabel('测试数量')
        ax.set_title('稳定性测试结果')
        ax.set_xticks(x)
        ax.set_xticklabels(types)
        ax.legend()
        
        plt.tight_layout()
        plt.savefig(self.output_dir / 'stability_results.svg', dpi=300, bbox_inches='tight')
        plt.close()
    
    def _print_summary(self, summary):
        """打印摘要报告"""
        print("\n" + "="*60)
        print("📈 WaterNet 性能基准测试摘要")
        print("="*60)
        
        if 'performance' in summary:
            perf = summary['performance']
            print(f"⚡ 性能最佳模型: {perf['fastest_model']}")
            print(f"🚀 吞吐量最高模型: {perf['highest_throughput']}")
            print(f"📊 平均成功率: {perf['average_success_rate']:.1%}")
        
        if 'accuracy' in summary:
            acc = summary['accuracy']
            print(f"🎯 精度测试通过率: {acc['pass_rate']:.1%} ({acc['tests_passed']}/{acc['total_tests']})")
        
        if 'stability' in summary:
            stab = summary['stability']
            print(f"⚖️ 稳定性测试通过率: {stab['stability_rate']:.1%} ({stab['stable_tests']}/{stab['total_tests']})")
        
        print("="*60)


def main():
    """主函数"""
    print("🚀 WaterNet 性能基准测试开始")
    print("="*60)
    
    # 创建基准测试实例
    benchmark = PerformanceBenchmark()
    
    try:
        # 运行各项基准测试
        benchmark.benchmark_model_performance()
        benchmark.benchmark_memory_usage()
        benchmark.benchmark_accuracy()
        benchmark.benchmark_stability()
        
        # 生成报告
        benchmark.generate_report()
        
        print("\n🎉 所有基准测试完成！")
        
    except Exception as e:
        print(f"\n❌ 基准测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 忽略一些不重要的警告
    warnings.filterwarnings('ignore', category=RuntimeWarning)
    warnings.filterwarnings('ignore', category=FutureWarning)
    
    main()