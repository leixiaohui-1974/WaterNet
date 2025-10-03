"""
WaterNet 基础使用示例

演示WaterNet框架的基本功能和使用方法。

Author: WaterNet Development Team
Date: 2024-10-03
"""

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

# 导入WaterNet组件
from waternet.models.saint_venant import SaintVenantModel
from waternet.models.lumped_models import MuskingumModel, StorageRoutingModel
from waternet.parameter_estimation.estimator import ParameterEstimator
from waternet.coordination.twinning_harness import SynchronizedTwinningHarness


def create_simple_channel():
    """创建简单的矩形明渠"""
    print("创建简单矩形明渠...")
    
    # 定义断面几何
    sections = [
        {
            'mileage': 0.0,        # 上游断面，里程0m
            'elevation': 100.0,     # 底高程100m
            'roughness': 0.025,     # 曼宁糙率
            'area_func': lambda h: max(0, h - 100) * 10,      # 矩形断面：宽10m
            'top_width_func': lambda h: 10 if h > 100 else 0  # 水面宽度
        },
        {
            'mileage': 500.0,      # 中间断面，里程500m
            'elevation': 99.5,     # 底高程99.5m
            'roughness': 0.025,
            'area_func': lambda h: max(0, h - 99.5) * 10,
            'top_width_func': lambda h: 10 if h > 99.5 else 0
        },
        {
            'mileage': 1000.0,     # 下游断面，里程1000m
            'elevation': 99.0,     # 底高程99m
            'roughness': 0.025,
            'area_func': lambda h: max(0, h - 99) * 10,
            'top_width_func': lambda h: 10 if h > 99 else 0
        }
    ]
    
    # 创建圣维南模型
    sv_model = SaintVenantModel(
        name="SimpleChannel",
        upstream_node="upstream",
        downstream_node="downstream", 
        sections=sections
    )
    
    print(f"明渠模型创建完成: {sv_model.name}")
    print(f"断面数量: {len(sv_model.sections)}")
    print(f"分段数量: {len(sv_model.segments)}")
    print(f"内部节点数量: {len(sv_model.internal_nodes)}")
    
    return sv_model


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
        output_file = '/data/workspace/WaterNet/examples/simulation_results.png'
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
    sv_model = create_simple_channel()
    
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