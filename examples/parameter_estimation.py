"""
参数估计示例

演示如何使用配置文件进行参数估计工作流。

Author: WaterNet Development Team
Date: 2024-10-03
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

from waternet.models import SaintVenantModel, MuskingumModel
from waternet.config import ConfigManager
from waternet.parameter_estimation.estimator import ParameterEstimator


def main():
    """参数估计主函数"""
    print("="*60)
    print("WaterNet 参数估计示例（配置驱动版）")
    print("="*60)
    
    # 1. 初始化配置管理器
    config_dir = Path(__file__).parent / 'configs'
    config_manager = ConfigManager(config_dir)
    
    # 2. 加载渠道配置
    print("\n1. 加载渠道配置")
    channel_config = config_manager.load_config('simple_channel.yaml')
    sections = config_manager.create_channel_sections(channel_config)
    
    # 创建圣维南模型作为"真实"系统
    reference_model = SaintVenantModel(
        name="ReferenceSystem",
        upstream_node="upstream", 
        downstream_node="downstream",
        sections=sections
    )
    
    print(f"✅ 参考模型创建完成: {reference_model.name}")
    
    # 3. 生成参考数据
    print("\n2. 生成参考数据")
    Q_test_range = np.linspace(8.0, 20.0, 5)
    H_test_range = np.linspace(99.3, 99.7, 4)
    
    reference_data = []
    
    for Q in Q_test_range:
        for H_down in H_test_range:
            try:
                result = reference_model.compute_steady_state(Q, H_down)
                if 'total_volume' in result:
                    reference_data.append({
                        'Q_in': Q,
                        'H_down': H_down,
                        'total_volume': result['total_volume'],
                        'H_up': result.get('H_section_0', H_down + 0.1)
                    })
            except:
                continue
    
    print(f"✅ 生成了 {len(reference_data)} 个参考数据点")
    
    # 4. 加载初始模型配置
    print("\n3. 加载初始模型配置")
    model_config = config_manager.load_config('muskingum_model.yaml')
    
    # 创建物理关系函数
    V_to_H_func, H_to_Q_func = config_manager.create_physical_relations(
        model_config['physical_relations'])
    
    # 创建初始马斯京干模型
    params = model_config['parameters']
    initial_model = MuskingumModel(
        dt=params['dt'],
        K=params['K'],
        x=params['x'],
        initial_V=params['initial_V'],
        V_to_H_func=V_to_H_func,
        H_to_Q_func=H_to_Q_func,
        name="InitialMuskingum"
    )
    
    print(f"   初始参数: K={params['K']:.0f}s, x={params['x']:.3f}")
    
    # 5. 执行参数优化
    print("\n4. 执行参数优化")
    
    def objective_function(trial_params):
        """目标函数：最小化与参考数据的误差"""
        K_trial, x_trial = trial_params
        
        # 参数合理性检查
        if K_trial <= 0 or not (0 <= x_trial <= 0.5):
            return 1e6
        
        # 创建试验模型
        trial_model = MuskingumModel(
            dt=params['dt'],
            K=K_trial,
            x=x_trial,
            initial_V=params['initial_V'],
            V_to_H_func=V_to_H_func,
            H_to_Q_func=H_to_Q_func,
            name="TrialModel"
        )
        
        # 计算误差
        total_error = 0.0
        valid_points = 0
        
        for ref_point in reference_data:
            Q_in = ref_point['Q_in']
            
            # 运行简短仿真
            Q_series = np.ones(5) * Q_in
            try:
                results = trial_model.run_simulation(Q_series)
                
                # 比较最终状态
                final_Q_out = results['Q_out'].iloc[-1]
                final_V = results['V'].iloc[-1]
                
                # 计算误差（简化）
                Q_error = abs(final_Q_out - Q_in) / Q_in
                V_error = abs(final_V - ref_point['total_volume']) / ref_point['total_volume']
                
                total_error += Q_error + V_error * 0.1  # 加权
                valid_points += 1
                
            except:
                total_error += 10.0  # 惩罚项
        
        if valid_points == 0:
            return 1e6
        
        return total_error / valid_points
    
    # 简化的网格搜索优化
    print("   执行网格搜索优化...")
    
    K_range = np.linspace(1800.0, 7200.0, 6)
    x_range = np.linspace(0.1, 0.4, 4)
    
    best_score = float('inf')
    best_params = (params['K'], params['x'])
    
    optimization_results = []
    
    for K_test in K_range:
        for x_test in x_range:
            score = objective_function([K_test, x_test])
            optimization_results.append({
                'K': K_test,
                'x': x_test,
                'score': score
            })
            
            if score < best_score:
                best_score = score
                best_params = (K_test, x_test)
    
    print(f"✅ 优化完成")
    print(f"   最佳参数: K={best_params[0]:.0f}s, x={best_params[1]:.3f}")
    print(f"   目标函数值: {best_score:.4f}")
    print(f"   改进程度: {((objective_function([params['K'], params['x']]) - best_score) / objective_function([params['K'], params['x']]) * 100):.1f}%")
    
    # 6. 验证优化结果
    print("\n5. 验证优化结果")
    
    # 创建优化后的模型
    optimized_model = MuskingumModel(
        dt=params['dt'],
        K=best_params[0],
        x=best_params[1],
        initial_V=params['initial_V'],
        V_to_H_func=V_to_H_func,
        H_to_Q_func=H_to_Q_func,
        name="OptimizedMuskingum"
    )
    
    # 比较测试
    test_Q_series = np.array([8.0, 12.0, 16.0, 12.0, 8.0])
    
    initial_results = initial_model.run_simulation(test_Q_series)
    optimized_results = optimized_model.run_simulation(test_Q_series)
    
    print(f"   测试流量序列: {test_Q_series}")
    print(f"   初始模型最终出流: {initial_results['Q_out'].iloc[-1]:.2f} m³/s")
    print(f"   优化模型最终出流: {optimized_results['Q_out'].iloc[-1]:.2f} m³/s")
    
    # 7. 保存优化结果
    print("\n6. 保存优化结果")
    
    # 更新配置文件
    optimized_config = model_config.copy()
    optimized_config['parameters']['K'] = float(best_params[0])
    optimized_config['parameters']['x'] = float(best_params[1])
    optimized_config['optimization_info'] = {
        'original_K': float(params['K']),
        'original_x': float(params['x']),
        'optimization_method': 'grid_search',
        'objective_score': float(best_score),
        'improvement_percent': float((objective_function([params['K'], params['x']]) - best_score) / objective_function([params['K'], params['x']]) * 100)
    }
    
    config_manager.save_config(optimized_config, 'muskingum_optimized.yaml')
    print(f"✅ 优化配置已保存: muskingum_optimized.yaml")
    
    # 保存优化历史
    optimization_df = pd.DataFrame(optimization_results)
    
    output_dir = Path(__file__).parent / 'outputs'
    output_dir.mkdir(exist_ok=True)
    
    optimization_df.to_csv(output_dir / 'parameter_optimization_history.csv', index=False)
    print(f"✅ 优化历史已保存: parameter_optimization_history.csv")
    
    # 8. 可视化结果
    if len(optimization_results) > 0:
        plot_optimization_results(optimization_results, initial_results, 
                                 optimized_results, test_Q_series, output_dir)
    
    print("\n" + "="*60)
    print("✅ 参数估计示例完成！")
    print("="*60)


def plot_optimization_results(optimization_results, initial_results, 
                             optimized_results, test_Q_series, output_dir):
    """绘制优化结果"""
    print("\n7. 生成优化结果图表")
    
    try:
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        fig.suptitle('参数优化结果', fontsize=14)
        
        # 1. 参数空间搜索结果
        opt_df = pd.DataFrame(optimization_results)
        
        # 创建参数网格用于等高线图
        K_unique = sorted(opt_df['K'].unique())
        x_unique = sorted(opt_df['x'].unique())
        
        if len(K_unique) > 1 and len(x_unique) > 1:
            K_grid, x_grid = np.meshgrid(K_unique, x_unique)
            score_grid = np.zeros_like(K_grid)
            
            for i, K_val in enumerate(K_unique):
                for j, x_val in enumerate(x_unique):
                    score_val = opt_df[(opt_df['K'] == K_val) & (opt_df['x'] == x_val)]['score'].iloc[0]
                    score_grid[j, i] = score_val
            
            contour = axes[0, 0].contour(K_grid, x_grid, score_grid, levels=10)
            axes[0, 0].clabel(contour, inline=True, fontsize=8)
            axes[0, 0].set_xlabel('K (s)')
            axes[0, 0].set_ylabel('x')
            axes[0, 0].set_title('目标函数等高线')
            axes[0, 0].grid(True, alpha=0.3)
            
            # 标记最优点
            best_idx = opt_df['score'].idxmin()
            best_K = opt_df.loc[best_idx, 'K']
            best_x = opt_df.loc[best_idx, 'x']
            axes[0, 0].plot(best_K, best_x, 'ro', markersize=8, label='最优点')
            axes[0, 0].legend()
        
        # 2. 模型对比 - 流量
        time_hours = initial_results['time'] / 3600.0
        
        axes[0, 1].plot(time_hours[1:], test_Q_series, 'b-', label='输入流量', linewidth=2)
        axes[0, 1].plot(time_hours, initial_results['Q_out'], 'r--', label='初始模型', linewidth=2)
        axes[0, 1].plot(time_hours, optimized_results['Q_out'], 'g-', label='优化模型', linewidth=2)
        axes[0, 1].set_xlabel('时间 (小时)')
        axes[0, 1].set_ylabel('流量 (m³/s)')
        axes[0, 1].set_title('流量对比')
        axes[0, 1].legend()
        axes[0, 1].grid(True, alpha=0.3)
        
        # 3. 模型对比 - 蓄水量
        axes[1, 0].plot(time_hours, initial_results['V'], 'r--', label='初始模型', linewidth=2)
        axes[1, 0].plot(time_hours, optimized_results['V'], 'g-', label='优化模型', linewidth=2)
        axes[1, 0].set_xlabel('时间 (小时)')
        axes[1, 0].set_ylabel('蓄水量 (m³)')
        axes[1, 0].set_title('蓄水量对比')
        axes[1, 0].legend()
        axes[1, 0].grid(True, alpha=0.3)
        
        # 4. 误差分析
        error_initial = np.abs(initial_results['Q_out'].values[1:] - test_Q_series)
        error_optimized = np.abs(optimized_results['Q_out'].values[1:] - test_Q_series)
        
        x_pos = np.arange(len(test_Q_series))
        width = 0.35
        
        axes[1, 1].bar(x_pos - width/2, error_initial, width, label='初始模型', alpha=0.7)
        axes[1, 1].bar(x_pos + width/2, error_optimized, width, label='优化模型', alpha=0.7)
        axes[1, 1].set_xlabel('时间步')
        axes[1, 1].set_ylabel('绝对误差 (m³/s)')
        axes[1, 1].set_title('流量误差对比')
        axes[1, 1].legend()
        axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        plot_file = output_dir / 'parameter_optimization.svg'
        plt.savefig(plot_file, format='svg', bbox_inches='tight')
        print(f"✅ 优化结果图表已保存 (SVG): {plot_file}")
        
        plt.close()
        
    except Exception as e:
        print(f"❌ 绘图失败: {e}")


if __name__ == "__main__":
    # 设置matplotlib支持中文显示
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    
    # 运行示例
    main()