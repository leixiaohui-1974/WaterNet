#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
精细化水力学模型对比分析工具

比较多种精细化仿真方法的性能和精度：
1. 马斯京干模型 (修正参数)
2. 蓄量演算模型
3. 积分延迟零点模型(IDZ)
4. 圣维南方程模型
5. 简化圣维南模型(扩散波、运动波等)

Author: WaterNet Development Team
Date: 2025-10-05
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from typing import Dict, List, Any, Optional, Callable, Tuple
import json
from pathlib import Path
import time
import warnings

# 导入模型类
from waternet.models.lumped_models import MuskingumModel, StorageRoutingModel, IntegralDelayZeroModel
from waternet.models.saint_venant import SaintVenantModel
from waternet.models.simplified_saint_venant import SimplifiedSaintVenantModel
from waternet.objects.conveyance import ChannelObject


class AdvancedModelComparator:
    """高级水力学模型对比分析器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化对比分析器
        
        Args:
            config_path: 配置文件路径
        """
        self.config = self._load_default_config() if config_path is None else self._load_config(config_path)
        self.models = {}
        self.results = {}
        self.comparison_metrics = {}
        
        # 设置matplotlib中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS']
        plt.rcParams['axes.unicode_minus'] = False
        
        print("🔬 高级水力学模型对比分析器初始化完成")
        print(f"📊 将对比{len(self._get_model_types())}种精细化仿真方法")
    
    def _load_default_config(self) -> Dict:
        """加载默认配置"""
        return {
            'channel_geometry': {
                'length': 5000.0,
                'base_elevation': 85.0,
                'slope': 0.0002,
                'cross_sections': [
                    {'station': 0.0, 'elevation': 86.0, 'bottom_width': 12.0, 'side_slope': 1.5, 'roughness': 0.025},
                    {'station': 2500.0, 'elevation': 85.5, 'bottom_width': 15.0, 'side_slope': 1.5, 'roughness': 0.025},
                    {'station': 5000.0, 'elevation': 85.0, 'bottom_width': 18.0, 'side_slope': 2.0, 'roughness': 0.030}
                ]
            },
            'simulation_parameters': {
                'time_step': 60.0,
                'initial_volume': 400000.0,
                'boundary_conditions': {
                    'time_steps': [0, 3600, 7200, 10800, 14400, 18000],
                    'upstream_flows': [100.0, 120.0, 150.0, 130.0, 110.0, 95.0],
                    'downstream_levels': [96.0, 96.1, 96.3, 96.2, 96.1, 96.0]
                }
            },
            'model_parameters': {
                'muskingum': {'K': 300.0, 'x': 0.1},  # 修正后的稳定参数
                'idz': {
                    'G11': {'tau': 120.0, 'alpha': 240.0},
                    'G12': {'tau': 0.0, 'alpha': 100.0},
                    'G21': {'tau': 60.0, 'alpha': 180.0},
                    'G22': {'tau': 180.0, 'alpha': 300.0}
                }
            }
        }
    
    def _get_model_types(self) -> List[str]:
        """获取支持的模型类型"""
        return [
            'muskingum_corrected',
            'storage_routing', 
            'idz_model',
            'saint_venant_full',
            'simplified_diffusive_wave',
            'simplified_kinematic_wave'
        ]
    
    def _create_physical_functions(self) -> Tuple[Callable, Callable]:
        """创建物理关系函数"""
        def V_to_H_func(V):
            # 基于渠道几何的体积-水位关系
            return 85.0 + (V / 500000.0)**0.6
        
        def H_to_Q_func(H):
            # 基于梯形断面的水位-流量关系
            if H <= 85.0:
                return 0.0
            h = H - 85.0  # 水深
            A = h * (15.0 + 1.5 * h)  # 梯形面积
            R = A / (15.0 + 2 * h * np.sqrt(1 + 1.5**2))  # 水力半径
            V = (1/0.025) * R**(2/3) * 0.0002**0.5  # 曼宁公式
            return A * V
        
        return V_to_H_func, H_to_Q_func
    
    def setup_models(self):
        """设置所有待对比的模型"""
        print("🔧 正在设置水力学模型...")
        
        V_to_H_func, H_to_Q_func = self._create_physical_functions()
        config = self.config
        
        # 1. 修正后的马斯京干模型
        try:
            self.models['muskingum_corrected'] = MuskingumModel(
                dt=config['simulation_parameters']['time_step'],
                K=config['model_parameters']['muskingum']['K'],
                x=config['model_parameters']['muskingum']['x'],
                initial_V=config['simulation_parameters']['initial_volume'],
                V_to_H_func=V_to_H_func,
                H_to_Q_func=H_to_Q_func,
                name="修正马斯京干模型"
            )
            print("✅ 马斯京干模型 (K=300s, x=0.1)")
        except Exception as e:
            print(f"❌ 马斯京干模型创建失败: {e}")
        
        # 2. 蓄量演算模型
        try:
            self.models['storage_routing'] = StorageRoutingModel(
                dt=config['simulation_parameters']['time_step'],
                initial_V=config['simulation_parameters']['initial_volume'],
                V_to_H_func=V_to_H_func,
                H_to_Q_func=H_to_Q_func,
                name="蓄量演算模型"
            )
            print("✅ 蓄量演算模型")
        except Exception as e:
            print(f"❌ 蓄量演算模型创建失败: {e}")
        
        # 3. IDZ模型
        try:
            self.models['idz_model'] = IntegralDelayZeroModel(
                dt=config['simulation_parameters']['time_step'],
                initial_V=config['simulation_parameters']['initial_volume'],
                V_to_H_func=V_to_H_func,
                H_to_Q_func=H_to_Q_func,
                Q0_up=100.0, H0_up=87.0,
                Q0_down=100.0, H0_down=86.0,
                params=config['model_parameters']['idz'],
                name="IDZ传递函数模型"
            )
            print("✅ IDZ传递函数模型")
        except Exception as e:
            print(f"❌ IDZ模型创建失败: {e}")
        
        # 4. 圣维南模型 (通过ChannelObject创建)
        try:
            channel_config = self._create_channel_config()
            channel = ChannelObject('comparison_channel', config=channel_config)
            self.models['saint_venant_full'] = channel
            print("✅ 圣维南方程模型")
        except Exception as e:
            print(f"❌ 圣维南模型创建失败: {e}")
        
        print(f"🎯 成功设置 {len(self.models)} 个模型")
    
    def _create_channel_config(self) -> Dict:
        """创建渠道配置用于圣维南模型"""
        config = self.config
        return {
            'object_definition': {
                'object_id': 'comparison_channel',
                'object_type': 'channel',
                'name': '对比分析渠道'
            },
            'basic_properties': {
                'length': config['channel_geometry']['length'],
                'base_elevation': config['channel_geometry']['base_elevation'],
                'slope': config['channel_geometry']['slope'],
                'time_step': config['simulation_parameters']['time_step'],
                'initial_volume': config['simulation_parameters']['initial_volume']
            },
            'geometry_definition': {
                'cross_sections': config['channel_geometry']['cross_sections']
            },
            'simulation_preferences': {
                'default_method': 'saint_venant_model'
            }
        }
    
    def run_comparison_analysis(self):
        """运行对比分析"""
        print("\n🚀 开始多模型对比分析...")
        
        boundary_series = self.config['simulation_parameters']['boundary_conditions']
        
        for model_name, model in self.models.items():
            print(f"\n📈 正在测试: {model_name}")
            
            try:
                start_time = time.time()
                
                if model_name == 'saint_venant_full':
                    # 对于ChannelObject，使用非恒定流仿真方法
                    result = self._run_channel_simulation(model, boundary_series)
                else:
                    # 对于降阶模型，使用步进仿真
                    result = self._run_lumped_simulation(model, boundary_series)
                
                computation_time = time.time() - start_time
                
                result['computation_time'] = computation_time
                result['model_type'] = model_name
                result['success'] = True
                
                self.results[model_name] = result
                
                print(f"✅ {model_name} 完成 (耗时: {computation_time:.3f}s)")
                
            except Exception as e:
                print(f"❌ {model_name} 失败: {e}")
                self.results[model_name] = {
                    'success': False,
                    'error': str(e),
                    'model_type': model_name
                }
    
    def _run_lumped_simulation(self, model, boundary_series: Dict) -> Dict:
        """运行降阶模型仿真"""
        Q_in_series = boundary_series['upstream_flows']
        time_steps = boundary_series['time_steps']
        
        # 重置模型
        model.reset()
        
        # 执行仿真
        results = []
        for i, Q_in in enumerate(Q_in_series):
            step_result = model.step(Q_in)
            step_result['time'] = time_steps[i]
            step_result['Q_in'] = Q_in
            results.append(step_result)
        
        return {
            'time_series': results,
            'peak_reduction': self._calculate_peak_reduction(Q_in_series, [r['Q_out'] for r in results]),
            'delay_time': self._calculate_delay_time(time_steps, Q_in_series, [r['Q_out'] for r in results])
        }
    
    def _run_channel_simulation(self, channel, boundary_series: Dict) -> Dict:
        """运行渠道对象仿真"""
        # 使用渠道对象的非恒定流仿真方法
        simulation_options = {
            'output_sections': ['upstream', 'downstream'],
            'plot_options': {'single_scenario': False}
        }
        
        result = channel.simulate_unsteady_flow_series(
            boundary_series=boundary_series,
            simulation_options=simulation_options
        )
        
        if result['success']:
            # 提取时间序列数据进行对比
            time_series_data = []
            for record in result['time_series']:
                time_series_data.append({
                    'time': record['time'],
                    'Q_in': record['Q_in'],
                    'Q_out': record['Q_out'],
                    'H_out': record['H_level'],
                    'V': record['V_storage']
                })
            
            Q_in_series = boundary_series['upstream_flows']
            Q_out_series = [r['Q_out'] for r in time_series_data]
            
            return {
                'time_series': time_series_data,
                'peak_reduction': self._calculate_peak_reduction(Q_in_series, Q_out_series),
                'delay_time': self._calculate_delay_time(boundary_series['time_steps'], Q_in_series, Q_out_series)
            }
        else:
            raise RuntimeError(f"渠道仿真失败: {result.get('error', '未知错误')}")
    
    def _calculate_peak_reduction(self, Q_in_series: List[float], Q_out_series: List[float]) -> float:
        """计算峰值削减率"""
        max_in = max(Q_in_series)
        max_out = max(Q_out_series)
        return (max_in - max_out) / max_in * 100
    
    def _calculate_delay_time(self, time_steps: List[int], Q_in_series: List[float], Q_out_series: List[float]) -> float:
        """计算延迟时间(小时)"""
        max_in = max(Q_in_series)
        max_out = max(Q_out_series)
        
        try:
            peak_in_idx = Q_in_series.index(max_in)
            peak_out_idx = Q_out_series.index(max_out)
            delay_seconds = time_steps[peak_out_idx] - time_steps[peak_in_idx]
            return delay_seconds / 3600  # 转换为小时
        except:
            return 0.0
    
    def generate_comparison_report(self):
        """生成对比分析报告"""
        print("\n📊 生成对比分析报告...")
        
        # 创建结果目录
        results_dir = Path("results/model_comparison")
        results_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. 创建性能对比表
        self._create_performance_table(results_dir)
        
        # 2. 生成流量响应对比图
        self._create_flow_response_plot(results_dir)
        
        # 3. 生成误差分析
        self._create_accuracy_analysis(results_dir)
        
        # 4. 保存详细结果
        self._save_detailed_results(results_dir)
        
        print(f"📂 对比报告已保存到: {results_dir}")
    
    def _create_performance_table(self, results_dir: Path):
        """创建性能对比表"""
        performance_data = []
        
        for model_name, result in self.results.items():
            if result.get('success', False):
                performance_data.append({
                    '模型名称': model_name,
                    '计算时间(s)': f"{result.get('computation_time', 0):.4f}",
                    '峰值削减率(%)': f"{result.get('peak_reduction', 0):.1f}",
                    '延迟时间(h)': f"{result.get('delay_time', 0):.1f}",
                    '稳定性': '✅ 正常' if result['success'] else '❌ 失败'
                })
        
        df = pd.DataFrame(performance_data)
        
        # 保存为Excel
        excel_path = results_dir / "model_performance_comparison.xlsx"
        df.to_excel(excel_path, index=False, encoding='utf-8')
        
        # 打印表格
        print("\n📋 模型性能对比表:")
        print(df.to_string(index=False))
    
    def _create_flow_response_plot(self, results_dir: Path):
        """创建流量响应对比图"""
        plt.figure(figsize=(15, 10))
        
        # 输入流量
        boundary_series = self.config['simulation_parameters']['boundary_conditions']
        time_hours = [t/3600 for t in boundary_series['time_steps']]
        
        plt.subplot(2, 2, 1)
        plt.plot(time_hours, boundary_series['upstream_flows'], 'k-', linewidth=3, label='入流', marker='o')
        plt.xlabel('时间 (小时)')
        plt.ylabel('流量 (m³/s)')
        plt.title('边界条件 - 入流过程')
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        # 各模型出流对比
        plt.subplot(2, 2, 2)
        colors = ['red', 'blue', 'green', 'orange', 'purple', 'brown']
        
        for i, (model_name, result) in enumerate(self.results.items()):
            if result.get('success', False):
                time_series = result['time_series']
                if time_series:
                    model_times = [t['time']/3600 for t in time_series]
                    model_flows = [t['Q_out'] for t in time_series]
                    plt.plot(model_times, model_flows, color=colors[i % len(colors)], 
                            linewidth=2, label=model_name, marker='s', markersize=4)
        
        plt.xlabel('时间 (小时)')
        plt.ylabel('出流 (m³/s)')
        plt.title('各模型出流响应对比')
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        # 坦化效应对比
        plt.subplot(2, 2, 3)
        model_names = []
        peak_reductions = []
        
        for model_name, result in self.results.items():
            if result.get('success', False):
                model_names.append(model_name.replace('_', '\n'))
                peak_reductions.append(result.get('peak_reduction', 0))
        
        bars = plt.bar(model_names, peak_reductions, color=['lightcoral', 'lightblue', 'lightgreen', 'orange', 'plum'])
        plt.ylabel('峰值削减率 (%)')
        plt.title('坦化效应对比')
        plt.xticks(rotation=45)
        
        # 添加数值标签
        for bar, value in zip(bars, peak_reductions):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                    f'{value:.1f}%', ha='center', va='bottom')
        
        # 延迟效应对比
        plt.subplot(2, 2, 4)
        delay_times = []
        
        for model_name, result in self.results.items():
            if result.get('success', False):
                delay_times.append(result.get('delay_time', 0))
        
        bars = plt.bar(model_names, delay_times, color=['lightcoral', 'lightblue', 'lightgreen', 'orange', 'plum'])
        plt.ylabel('延迟时间 (小时)')
        plt.title('延迟效应对比')
        plt.xticks(rotation=45)
        
        # 添加数值标签
        for bar, value in zip(bars, delay_times):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1, 
                    f'{value:.1f}h', ha='center', va='bottom')
        
        plt.tight_layout()
        
        # 保存图像
        plot_path = results_dir / "model_comparison_analysis.svg"
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✅ 流量响应对比图: {plot_path}")
    
    def _create_accuracy_analysis(self, results_dir: Path):
        """创建精度分析"""
        if 'saint_venant_full' not in self.results or not self.results['saint_venant_full'].get('success', False):
            print("⚠️ 缺少圣维南模型结果，跳过精度分析")
            return
        
        # 以圣维南模型为基准
        reference_result = self.results['saint_venant_full']['time_series']
        ref_flows = [r['Q_out'] for r in reference_result]
        
        accuracy_data = []
        
        for model_name, result in self.results.items():
            if model_name == 'saint_venant_full' or not result.get('success', False):
                continue
                
            model_flows = [r['Q_out'] for r in result['time_series']]
            
            # 计算均方根误差
            if len(model_flows) == len(ref_flows):
                rmse = np.sqrt(np.mean([(m - r)**2 for m, r in zip(model_flows, ref_flows)]))
                relative_error = rmse / np.mean(ref_flows) * 100
                
                accuracy_data.append({
                    '模型': model_name,
                    'RMSE (m³/s)': f"{rmse:.2f}",
                    '相对误差 (%)': f"{relative_error:.1f}"
                })
        
        if accuracy_data:
            df_accuracy = pd.DataFrame(accuracy_data)
            accuracy_path = results_dir / "accuracy_analysis.xlsx"
            df_accuracy.to_excel(accuracy_path, index=False)
            
            print("\n🎯 精度分析表 (以圣维南模型为基准):")
            print(df_accuracy.to_string(index=False))
    
    def _save_detailed_results(self, results_dir: Path):
        """保存详细结果"""
        detailed_results = {
            'configuration': self.config,
            'model_results': self.results,
            'comparison_summary': {
                'total_models': len(self.models),
                'successful_models': len([r for r in self.results.values() if r.get('success', False)]),
                'analysis_timestamp': pd.Timestamp.now().isoformat()
            }
        }
        
        results_path = results_dir / "detailed_comparison_results.json"
        with open(results_path, 'w', encoding='utf-8') as f:
            json.dump(detailed_results, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"💾 详细结果已保存: {results_path}")


def main():
    """主函数"""
    print("🔬 启动高级水力学模型对比分析")
    print("=" * 60)
    
    # 创建对比分析器
    comparator = AdvancedModelComparator()
    
    # 设置模型
    comparator.setup_models()
    
    # 运行对比分析
    comparator.run_comparison_analysis()
    
    # 生成报告
    comparator.generate_comparison_report()
    
    print("\n" + "=" * 60)
    print("🎉 高级水力学模型对比分析完成！")
    print("📂 请查看 results/model_comparison/ 目录下的分析报告")


if __name__ == "__main__":
    main()