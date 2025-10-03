"""
WaterNet 快速开始示例

最简单的使用示例，展示核心功能。

Author: WaterNet Development Team
Date: 2024-10-03
"""

import numpy as np
from waternet import (
    SaintVenantModel, MuskingumModel, 
    ParameterEstimator, SynchronizedTwinningHarness
)


def quick_start_example():
    """快速开始示例"""
    print("WaterNet 快速开始示例")
    print("=" * 40)
    
    # 1. 创建简单明渠模型
    print("1. 创建明渠模型...")
    
    sections = [
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
    
    # 圣维南模型
    sv_model = SaintVenantModel("TestChannel", "upstream", "downstream", sections)
    print(f"✅ 圣维南模型: {sv_model.name}")
    
    # 2. 创建降阶模型
    print("2. 创建降阶模型...")
    
    def V_to_H(V):
        return 99 + V / 10000
    
    def H_to_Q(H):
        return max(0, (H - 99) * 20)
    
    rom_model = MuskingumModel(
        dt=60.0, K=3600.0, x=0.2, initial_V=10000.0,
        V_to_H_func=V_to_H, H_to_Q_func=H_to_Q
    )
    print(f"✅ 降阶模型: {rom_model.name}")
    
    # 3. 参数估计
    print("3. 参数估计...")
    
    estimator = ParameterEstimator(sv_model)
    
    # 静态曲线辨识
    Q_range = np.linspace(5, 20, 4)
    H_range = np.linspace(99.2, 100.0, 3)
    
    curves = estimator.identify_static_curves(Q_range, H_range)
    print(f"✅ 静态曲线辨识完成，{len(curves['raw_data'])}个测试点")
    
    # 4. 同步孪生仿真
    print("4. 同步孪生仿真...")
    
    harness = SynchronizedTwinningHarness(sv_model, rom_model)
    
    # 创建测试输入
    n_steps = 30
    Q_in = np.concatenate([
        np.ones(10) * 8,   # 初始流量
        np.ones(10) * 16,  # 增加流量
        np.ones(10) * 10   # 中等流量
    ])
    H_down = np.ones(n_steps) * 99.3
    
    # 运行仿真
    results = harness.run_synchronized_simulation(
        Q_in, H_down, dt=60.0, enable_correction=True
    )
    
    print(f"✅ 仿真完成，{len(results)}个时间步")
    
    # 5. 结果分析
    print("5. 结果分析...")
    
    summary = harness.get_performance_summary()
    metrics = summary['总体性能']
    
    print(f"流量RMSE: {metrics['rmse_Q']:.3f} m³/s")
    print(f"相关系数: {metrics['correlation_Q']:.3f}")
    print(f"校正次数: {metrics['correction_count']}")
    
    print("\n✅ 快速开始示例完成!")
    return results


if __name__ == "__main__":
    results = quick_start_example()