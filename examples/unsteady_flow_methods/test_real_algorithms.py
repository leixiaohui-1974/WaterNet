#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试WaterNet基础库中的真实算法对比

Author: WaterNet Development Team
Date: 2025-01-06
"""

import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path

def test_real_algorithms():
    """测试WaterNet基础库中的真实算法"""
    print("测试WaterNet基础库真实算法对比")
    print("=" * 60)
    
    try:
        # 导入真实的基础库算法
        from waternet.models.lumped_models import MuskingumModel, StorageRoutingModel
        from waternet.utils.model_factory import create_default_physical_relations
        
        print("✅ 成功导入基础库算法模块")
        
        # 创建物理关系函数
        V_to_H_func, H_to_Q_func = create_default_physical_relations()
        print("✅ 物理关系函数创建成功")
        
        # 测试数据
        input_flows = [100, 115, 140, 160, 150, 130, 110, 105, 100]
        time_hours = np.array([i * 0.5 for i in range(len(input_flows))])
        
        # 测试马斯京干法
        print("\n1. 测试马斯京干法...")
        muskingum_model = MuskingumModel(
            dt=1800.0,  # 30分钟
            K=3600.0,   # 1小时滞时常数
            x=0.15,     # 权重系数
            initial_V=15000.0,
            V_to_H_func=V_to_H_func,
            H_to_Q_func=H_to_Q_func
        )
        
        muskingum_results = []
        for Q_in in input_flows:
            result = muskingum_model.step(Q_in)
            muskingum_results.append(result['Q_out'])
        
        print(f"   马斯京干法计算完成，输出流量范围: {min(muskingum_results):.1f} - {max(muskingum_results):.1f} m³/s")
        
        # 测试蓄量演算法
        print("\n2. 测试蓄量演算法...")
        storage_model = StorageRoutingModel(
            dt=1800.0,
            initial_V=15000.0,
            V_to_H_func=V_to_H_func,
            H_to_Q_func=H_to_Q_func
        )
        
        storage_results = []
        for Q_in in input_flows:
            result = storage_model.step(Q_in)
            storage_results.append(result['Q_out'])
        
        print(f"   蓄量演算法计算完成，输出流量范围: {min(storage_results):.1f} - {max(storage_results):.1f} m³/s")
        
        # 创建对比图
        print("\n3. 生成对比图...")
        
        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
        
        # 流量对比图
        ax1.plot(time_hours, input_flows, 'k--', linewidth=3, label='输入流量', marker='o', markersize=8)
        ax1.plot(time_hours, muskingum_results, 'b-', linewidth=2, label='马斯京干法', marker='s', markersize=6)
        ax1.plot(time_hours, storage_results, 'r-', linewidth=2, label='蓄量演算法', marker='^', markersize=6)
        
        ax1.set_xlabel('时间 (小时)', fontsize=14)
        ax1.set_ylabel('流量 (m³/s)', fontsize=14)
        ax1.set_title('WaterNet基础库真实算法流量响应对比', fontsize=16, fontweight='bold')
        ax1.legend(fontsize=12)
        ax1.grid(True, alpha=0.3)
        
        # 坦化效应对比
        Q_in_max = max(input_flows)
        musk_damping = (Q_in_max - max(muskingum_results)) / Q_in_max * 100
        storage_damping = (Q_in_max - max(storage_results)) / Q_in_max * 100
        
        methods = ['马斯京干法', '蓄量演算法']
        dampings = [musk_damping, storage_damping]
        colors = ['blue', 'red']
        
        bars = ax2.bar(methods, dampings, color=colors, alpha=0.7, edgecolor='black', linewidth=2)
        
        # 添加数值标签
        for bar, value in zip(bars, dampings):
            ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                    f'{value:.1f}%', ha='center', va='bottom', 
                    fontsize=12, color='red', fontweight='bold')
        
        ax2.set_ylabel('坦化效应 (%)', fontsize=14)
        ax2.set_title('真实算法坦化效应对比', fontsize=16, fontweight='bold')
        ax2.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        
        # 保存图片
        script_dir = Path(__file__).parent
        output_dir = script_dir / 'outputs' / 'plots' / 'real_algorithm_test'
        output_dir.mkdir(parents=True, exist_ok=True)
        save_path = output_dir / 'waternet_real_algorithms_test.svg'
        print(f"✅ 图表已保存为: {save_path}")
        
        plt.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        if save_path.exists():
            file_size = save_path.stat().st_size
            print(f"✅ 真实算法对比图生成成功: {save_path}")
            print(f"   文件大小: {file_size} bytes")
            print(f"   马斯京干法坦化效应: {musk_damping:.1f}%")
            print(f"   蓄量演算法坦化效应: {storage_damping:.1f}%")
        else:
            print("❌ 图片生成失败")
        
        print("\n✅ WaterNet基础库真实算法测试完成!")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_real_algorithms()