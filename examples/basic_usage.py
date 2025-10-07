"""
WaterNet 基础使用示例（简化配置版）

演示WaterNet框架的基本功能，使用配置文件驱动。

Author: WaterNet Development Team
Date: 2024-10-03
"""

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path

# 导入WaterNet组件
from waternet.models import SaintVenantModel, MuskingumModel
from waternet.config import ConfigManager


def main():
    """
    主演示函数
    """
    print("="*60)
    print("WaterNet 基础使用演示（配置驱动版）")
    print("="*60)
    
    # 1. 初始化配置管理器
    config_dir = Path(__file__).parent / 'configs'
    config_manager = ConfigManager(config_dir)
    
    print(f"配置目录: {config_dir}")
    
    # 如果配置文件不存在，创建默认配置
    if not (config_dir / 'simple_channel.yaml').exists():
        print("创建默认配置文件...")
        config_manager.create_default_configs()
    
    # 2. 加载渠道配置并创建模型
    print("\n1. 加载渠道配置并创建圣维南模型")
    channel_config = config_manager.load_config('simple_channel.yaml')
    print(f"渠道名称: {channel_config['name']}")
    print(f"断面数量: {len(channel_config['sections'])}")
    
    # 创建断面数据
    sections = config_manager.create_channel_sections(channel_config)
    
    # 创建圣维南模型
    sv_model = SaintVenantModel(
        name=channel_config['name'],
        upstream_node="upstream",
        downstream_node="downstream",
        sections=sections
    )
    
    print(f"✅ 圣维南模型创建成功，分段数: {len(sv_model.segments)}")
    
    # 3. 恒定流计算演示
    print("\n2. 恒定流计算演示")
    Q_steady = 15.0
    H_downstream = 99.5
    
    try:
        steady_result = sv_model.compute_steady_state(Q_steady, H_downstream)
        print(f"✅ 恒定流计算成功")
        print(f"   流量: {Q_steady} m³/s")
        print(f"   下游水位: {H_downstream} m")
        print(f"   总蓄水量: {steady_result['total_volume']:.1f} m³")
        
        # 显示各断面水位
        for i in range(len(sections)):
            H_key = f'H_section_{i}'
            if H_key in steady_result:
                print(f"   断面{i}水位: {steady_result[H_key]:.3f} m")
                
    except Exception as e:
        print(f"❌ 恒定流计算失败: {e}")
        return
    
    # 4. 加载模型配置并创建降阶模型
    print("\n3. 创建降阶模型")
    model_config = config_manager.load_config('muskingum_model.yaml')
    
    # 创建物理关系函数
    V_to_H_func, H_to_Q_func = config_manager.create_physical_relations(
        model_config['physical_relations'])
    
    # 创建马斯京干模型
    params = model_config['parameters']
    muskingum_model = MuskingumModel(
        dt=params['dt'],
        K=params['K'],
        x=params['x'],
        initial_V=params['initial_V'],
        V_to_H_func=V_to_H_func,
        H_to_Q_func=H_to_Q_func,
        name="ConfiguredMuskingum"
    )
    
    print(f"✅ 马斯京干模型创建成功")
    print(f"   参数: K={params['K']:.0f}s, x={params['x']:.2f}")
    print(f"   系数: C0={muskingum_model.C0:.4f}, C1={muskingum_model.C1:.4f}, C2={muskingum_model.C2:.4f}")
    
    # 5. 加载仿真配置并运行仿真
    print("\n4. 运行非恒定流仿真")
    sim_config = config_manager.load_config('simulation_config.yaml')
    
    # 获取边界条件
    bc = sim_config['boundary_conditions']
    Q_in_series = np.array(bc['upstream_values'])
    H_down = bc['downstream_values']
    
    print(f"   仿真类型: {sim_config['simulation_type']}")
    print(f"   时间步长: {sim_config['time_step']}s")
    print(f"   入流范围: {Q_in_series.min():.1f} - {Q_in_series.max():.1f} m³/s")
    
    try:
        # 运行降阶模型仿真
        results_df = muskingum_model.run_simulation(Q_in_series)
        
        print(f"✅ 仿真完成，时间步数: {len(results_df)}")
        
        # 6. 结果分析和可视化
        print("\n5. 结果分析")
        
        # 基本统计
        Q_out_mean = results_df['Q_out'].mean()
        Q_out_max = results_df['Q_out'].max()
        Q_in_mean = np.mean(Q_in_series)
        
        print(f"   平均入流: {Q_in_mean:.2f} m³/s")
        print(f"   平均出流: {Q_out_mean:.2f} m³/s")
        print(f"   最大出流: {Q_out_max:.2f} m³/s")
        print(f"   质量平衡误差: {abs(Q_in_mean - Q_out_mean)/Q_in_mean*100:.1f}%")
        
        # 绘制结果
        if sim_config.get('output', {}).get('plot_results', False):
            plot_results(results_df, Q_in_series, sim_config)
        
        # 保存结果
        if sim_config.get('output', {}).get('save_results', False):
            save_results(results_df, Q_in_series, sim_config)
            
    except Exception as e:
        print(f"❌ 仿真失败: {e}")
        return
    


def plot_results(results_df: pd.DataFrame, Q_in_series: np.ndarray, 
                 sim_config: dict):
    """
    绘制仿真结果
    """
    print("\n6. 生成结果图表")
    
    try:
        fig, axes = plt.subplots(2, 2, figsize=(12, 8))
        fig.suptitle('WaterNet 仿真结果', fontsize=14)
        
        time_minutes = results_df['time'].values / 60.0  # 转换为分钟
        
        # 1. 入流和出流对比
        axes[0, 0].plot(time_minutes[1:], Q_in_series, 'b-', label='入流', linewidth=2)
        axes[0, 0].plot(time_minutes, results_df['Q_out'], 'r--', label='出流', linewidth=2)
        axes[0, 0].set_xlabel('时间 (分钟)')
        axes[0, 0].set_ylabel('流量 (m³/s)')
        axes[0, 0].set_title('流量对比')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)
        
        # 2. 水位变化
        axes[0, 1].plot(time_minutes, results_df['H_out'], 'g-', linewidth=2)
        axes[0, 1].set_xlabel('时间 (分钟)')
        axes[0, 1].set_ylabel('水位 (m)')
        axes[0, 1].set_title('出口水位')
        axes[0, 1].grid(True, alpha=0.3)
        
        # 3. 蓄水量变化
        axes[1, 0].plot(time_minutes, results_df['V'], 'purple', linewidth=2)
        axes[1, 0].set_xlabel('时间 (分钟)')
        axes[1, 0].set_ylabel('蓄水量 (m³)')
        axes[1, 0].set_title('蓄水量变化')
        axes[1, 0].grid(True, alpha=0.3)
        
        # 4. 流量差值
        if len(Q_in_series) == len(results_df) - 1:
            Q_diff = Q_in_series - results_df['Q_out'].values[1:]
            axes[1, 1].plot(time_minutes[1:], Q_diff, 'orange', linewidth=2)
            axes[1, 1].set_xlabel('时间 (分钟)')
            axes[1, 1].set_ylabel('流量差 (m³/s)')
            axes[1, 1].set_title('入流-出流差值')
            axes[1, 1].grid(True, alpha=0.3)
            axes[1, 1].axhline(y=0, color='k', linestyle='-', alpha=0.5)
        
        plt.tight_layout()
        
        # 保存图表
        output_dir = Path(__file__).parent / 'outputs'
        output_dir.mkdir(exist_ok=True)
        
        plot_file = output_dir / 'simulation_results.svg'
        plt.savefig(plot_file, dpi=300, bbox_inches='tight')
        print(f"✅ 结果图表已保存: {plot_file}")
        
        plt.close()
        
    except Exception as e:
        print(f"❌ 绘图失败: {e}")


def save_results(results_df: pd.DataFrame, Q_in_series: np.ndarray, 
                 sim_config: dict):
    """
    保存仿真结果
    """
    print("\n7. 保存仿真结果")
    
    try:
        output_dir = Path(__file__).parent / 'outputs'
        output_dir.mkdir(exist_ok=True)
        
        # 添加入流数据到结果
        results_extended = results_df.copy()
        Q_in_extended = [0.0] + list(Q_in_series)  # 添加初始值
        results_extended['Q_in'] = Q_in_extended[:len(results_extended)]
        
        # 保存为CSV
        output_format = sim_config.get('output', {}).get('output_format', 'csv')
        
        if output_format == 'csv':
            csv_file = output_dir / 'simulation_results.csv'
            results_extended.to_csv(csv_file, index=False)
            print(f"✅ 结果已保存为CSV: {csv_file}")
        
        elif output_format == 'excel':
            excel_file = output_dir / 'simulation_results.xlsx'
            with pd.ExcelWriter(excel_file) as writer:
                results_extended.to_excel(writer, sheet_name='仿真结果', index=False)
            print(f"✅ 结果已保存为Excel: {excel_file}")
        
        # 保存摘要统计
        summary = {
            '仿真参数': {
                '模型类型': 'Muskingum',
                '时间步长(s)': sim_config['time_step'],
                '总时间(s)': sim_config['total_time'],
                '时间步数': len(results_df)
            },
            '流量统计': {
                '平均入流(m³/s)': float(np.mean(Q_in_series)),
                '最大入流(m³/s)': float(np.max(Q_in_series)),
                '平均出流(m³/s)': float(results_df['Q_out'].mean()),
                '最大出流(m³/s)': float(results_df['Q_out'].max())
            },
            '水位统计': {
                '平均水位(m)': float(results_df['H_out'].mean()),
                '最高水位(m)': float(results_df['H_out'].max()),
                '最低水位(m)': float(results_df['H_out'].min())
            }
        }
        
        import yaml
        summary_file = output_dir / 'simulation_summary.yaml'
        with open(summary_file, 'w', encoding='utf-8') as f:
            yaml.dump(summary, f, default_flow_style=False, allow_unicode=True)
        
        print(f"✅ 仿真摘要已保存: {summary_file}")
        
    except Exception as e:
        print(f"❌ 保存结果失败: {e}")


if __name__ == "__main__":
    # 设置matplotlib支持中文显示
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    
    # 运行演示
    main()


def demonstrate_steady_flow(sv_model):
    """演示恒定流计算"""
    print("\n" + "="*50)
    print("恒定流计算演示")
    print("="*50)
    
    # 设置计算条件
    Q_steady = 15.0      # 恒定流量 15 m³/s
    H_downstream = 99.5  # 下游水位 99.5 m
    
    print(f"流量: {Q_steady} m³/s")
    print(f"下游水位: {H_downstream} m")
    
    # 计算恒定流水面线
    try:
        result = sv_model.compute_steady_state(Q_steady, H_downstream)
        
        print("\n恒定流计算结果:")
        print(f"总蓄水量: {result['total_volume']:.2f} m³")
        
        # 提取各断面水位
        water_levels = []
        for i in range(len(sv_model.sections)):
            key = f'H_section_{i}'
            if key in result:
                water_levels.append(result[key])
                print(f"断面{i}水位: {result[key]:.3f} m")
        
        return result
        
    except Exception as e:
        print(f"恒定流计算失败: {e}")
        return None


def create_reduced_order_models(sv_model):
    """创建降阶模型"""
    print("\n" + "="*50)
    print("降阶模型创建演示")
    print("="*50)
    
    # 定义简化的物理关系函数
    def V_to_H_relation(V):
        """蓄量-水位关系：基于梯形断面近似"""
        base_level = 99.0
        storage_coefficient = 1.0 / 8000.0  # 经验系数
        return base_level + V * storage_coefficient
    
    def H_to_Q_relation(H):
        """水位-出流关系：基于堰流公式简化"""
        threshold_level = 99.0
        if H <= threshold_level:
            return 0.0
        else:
            # 简化的流量系数
            flow_coefficient = 25.0
            return flow_coefficient * (H - threshold_level) ** 1.5
    
    # 创建马斯京干模型
    muskingum_model = MuskingumModel(
        dt=60.0,              # 时间步长 60秒
        K=3600.0,             # 滞时常数 1小时
        x=0.2,                # 权重系数
        initial_V=12000.0,    # 初始蓄水量
        V_to_H_func=V_to_H_relation,
        H_to_Q_func=H_to_Q_relation,
        name="MuskingumROM"
    )
    
    # 创建蓄量演算模型
    storage_model = StorageRoutingModel(
        dt=60.0,
        initial_V=12000.0,
        V_to_H_func=V_to_H_relation,
        H_to_Q_func=H_to_Q_relation,
        name="StorageROM"
    )
    
    print("马斯京干模型参数:")
    print(f"  K = {muskingum_model.K} 秒")
    print(f"  x = {muskingum_model.x}")
    print(f"  C0 = {muskingum_model.C0:.4f}")
    print(f"  C1 = {muskingum_model.C1:.4f}")
    print(f"  C2 = {muskingum_model.C2:.4f}")
    
    return muskingum_model, storage_model


def demonstrate_parameter_estimation(sv_model, rom_model):
    """演示参数估计功能"""
    print("\n" + "="*50)
    print("参数估计演示")
    print("="*50)
    
    # 创建参数估计器
    estimator = ParameterEstimator(sv_model)
    
    # 静态特征曲线辨识
    print("1. 静态特征曲线辨识...")
    Q_range = np.linspace(5.0, 25.0, 6)
    H_range = np.linspace(99.2, 100.0, 5)
    
    try:
        static_curves = estimator.identify_static_curves(Q_range, H_range)
        
        print("✅ 静态曲线辨识完成")
        print(f"   测试点数量: {len(static_curves['raw_data'])}")
        print(f"   成功率: {static_curves['raw_data']['success'].mean():.1%}")
        
        for curve_type, stats in static_curves['statistics'].items():
            print(f"   {curve_type}曲线 R² = {stats['r2']:.3f}")
        
    except Exception as e:
        print(f"❌ 静态曲线辨识失败: {e}")
        return None
    
    # 动态参数辨识
    print("\n2. 动态参数辨识...")
    
    # 创建测试用的非恒定流数据
    time_steps = 24
    Q_in_test = np.concatenate([
        np.ones(6) * 8.0,    # 初始流量
        np.ones(6) * 20.0,   # 高流量
        np.ones(6) * 12.0,   # 中等流量
        np.ones(6) * 8.0     # 回到初始流量
    ])
    H_down_test = np.ones(time_steps) * 99.4
    
    unsteady_data = {
        'Q_in': Q_in_test,
        'H_down': H_down_test,
        'dt': 60.0
    }
    
    try:
        param_result = estimator.identify_dynamic_parameters(
            unsteady_data, MuskingumModel)
        
        if param_result['success']:
            print("✅ 动态参数辨识成功")
            best_params = param_result['best_parameters']
            print(f"   优化后参数: K = {best_params['K']:.0f}s, x = {best_params['x']:.3f}")
            print(f"   目标函数值: {param_result['best_score']:.4f}")
        else:
            print("❌ 动态参数辨识失败")
        
        return param_result
        
    except Exception as e:
        print(f"❌ 动态参数辨识过程出错: {e}")
        return None


def demonstrate_synchronized_twinning(sv_model, rom_model):
    """演示同步孪生仿真"""
    print("\n" + "="*50)
    print("同步孪生仿真演示")
    print("="*50)
    
    # 创建同步孪生协调器
    harness = SynchronizedTwinningHarness(
        saint_venant_model=sv_model,
        reduced_order_model=rom_model,
        correction_interval=8,     # 每8步校正一次
        correction_threshold=0.3   # 误差阈值
    )
    
    # 创建测试输入序列（模拟真实的入流过程）
    time_hours = 2.0  # 仿真2小时
    dt = 60.0         # 时间步长60秒
    n_steps = int(time_hours * 3600 / dt)
    
    # 创建变化的入流序列
    time_array = np.linspace(0, time_hours, n_steps)
    Q_in_series = 10.0 + 8.0 * np.sin(2 * np.pi * time_array / 1.5) + \
                  3.0 * np.random.normal(0, 1, n_steps)  # 基础流量 + 周期变化 + 噪声
    Q_in_series = np.maximum(Q_in_series, 2.0)  # 确保流量为正
    
    # 下游水位（略有变化）
    H_down_series = 99.4 + 0.1 * np.sin(2 * np.pi * time_array / 2.0)
    
    print(f"仿真时间: {time_hours} 小时")
    print(f"时间步数: {n_steps}")
    print(f"入流范围: {Q_in_series.min():.1f} - {Q_in_series.max():.1f} m³/s")
    
    # 运行同步仿真
    try:
        results = harness.run_synchronized_simulation(
            Q_in_series=Q_in_series,
            H_down_series=H_down_series,
            dt=dt,
            enable_correction=True
        )
        
        print("✅ 同步孪生仿真完成")
        
        # 分析结果
        summary = harness.get_performance_summary()
        metrics = summary['总体性能']
        
        print(f"\n性能指标:")
        print(f"  流量RMSE: {metrics['rmse_Q']:.3f} m³/s")
        print(f"  相关系数: {metrics['correlation_Q']:.3f}")
        print(f"  平均相对误差: {metrics['mean_relative_error']:.1f}%")
        print(f"  最大误差: {metrics['max_error']:.3f} m³/s")
        
        correction_info = summary['校正历史']
        print(f"\n校正统计:")
        print(f"  校正次数: {correction_info['校正次数']}")
        print(f"  成功次数: {correction_info['成功次数']}")
        
        return results
        
    except Exception as e:
        print(f"❌ 同步孪生仿真失败: {e}")
        return None


def plot_results(results):
    """绘制仿真结果"""
    if results is None:
        print("无法绘制结果：仿真数据为空")
        return
    
    print("\n生成结果图表...")
    
    try:
        fig, axes = plt.subplots(2, 2, figsize=(12, 8))
        fig.suptitle('WaterNet同步孪生仿真结果', fontsize=14)
        
        time_hours = results['time'] / 3600.0  # 转换为小时
        
        # 1. 入流和出流对比
        axes[0, 0].plot(time_hours, results['Q_in'], 'b-', label='入流', linewidth=1.5)
        axes[0, 0].plot(time_hours, results['Q_out_sv'], 'r-', label='圣维南模型', linewidth=1.5)
        axes[0, 0].plot(time_hours, results['Q_out_rom'], 'g--', label='降阶模型', linewidth=1.5)
        axes[0, 0].set_xlabel('时间 (小时)')
        axes[0, 0].set_ylabel('流量 (m³/s)')
        axes[0, 0].set_title('流量对比')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)
        
        # 2. 水位对比
        axes[0, 1].plot(time_hours, results['H_up_sv'], 'r-', label='圣维南模型', linewidth=1.5)
        axes[0, 1].plot(time_hours, results['H_up_rom'], 'g--', label='降阶模型', linewidth=1.5)
        axes[0, 1].set_xlabel('时间 (小时)')
        axes[0, 1].set_ylabel('水位 (m)')
        axes[0, 1].set_title('上游水位对比')
        axes[0, 1].legend()
        axes[0, 1].grid(True, alpha=0.3)
        
        # 3. 误差分析
        axes[1, 0].plot(time_hours, results['error_Q'], 'k-', linewidth=1)
        axes[1, 0].set_xlabel('时间 (小时)')
        axes[1, 0].set_ylabel('绝对误差 (m³/s)')
        axes[1, 0].set_title('流量绝对误差')
        axes[1, 0].grid(True, alpha=0.3)
        
        # 4. 相对误差
        axes[1, 1].plot(time_hours, results['relative_error_Q'], 'purple', linewidth=1)
        axes[1, 1].set_xlabel('时间 (小时)')
        axes[1, 1].set_ylabel('相对误差 (%)')
        axes[1, 1].set_title('流量相对误差')
        axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # 保存图表
        output_file = '/data/workspace/WaterNet/examples/simulation_results.svg'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"✅ 结果图表已保存: {output_file}")
        
        plt.close()
        
    except Exception as e:
        print(f"❌ 绘图失败: {e}")


def main():
    """主演示函数"""
    print("="*60)
    print("WaterNet 明渠模型接口系统演示")
    print("="*60)
    
    # 1. 创建物理模型
    configs_dir = os.path.join(os.path.dirname(__file__), 'configs')
    config_manager = ConfigManager(configs_dir)
    sv_model = create_saint_venant_model(config_manager)
    
    # 2. 演示恒定流计算
    steady_result = demonstrate_steady_flow(sv_model)
    
    # 3. 创建降阶模型
    muskingum_model, storage_model = create_reduced_order_models(sv_model)
    
    # 4. 演示参数估计
    param_result = demonstrate_parameter_estimation(sv_model, muskingum_model)
    
    # 5. 演示同步孪生仿真
    sync_results = demonstrate_synchronized_twinning(sv_model, muskingum_model)
    
    # 6. 绘制结果
    if sync_results is not None:
        plot_results(sync_results)
    
    print("\n" + "="*60)
    print("WaterNet演示完成！")
    print("="*60)
    
    return {
        'saint_venant_model': sv_model,
        'reduced_order_model': muskingum_model,
        'parameter_estimation': param_result,
        'synchronized_results': sync_results
    }


if __name__ == "__main__":
    # 设置matplotlib支持中文显示（如果需要）
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    
    # 运行演示
    demo_results = main()