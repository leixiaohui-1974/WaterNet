#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诊断恒定流初始值估计的正确性
"""

import sys
import os
import numpy as np
import logging

# 添加项目路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from enhanced_solver import EnhancedSaintVenantSolver, NumericalSchemeConfig
from waternet.models.saint_venant import SaintVenantModel

# 设置日志
logging.basicConfig(level=logging.DEBUG)

def diagnose_initial_conditions():
    """诊断初始条件设置是否合理"""
    
    print("=== 诊断恒定流初始值估计 ===\n")
    
    # 创建简单的断面模型，符合SaintVenantModel的接口
    def area_func(h, elevation, bottom_width=10.0, side_slope=1.0):
        depth = max(0.1, h - elevation)
        return bottom_width * depth + side_slope * depth**2
    
    def top_width_func(h, elevation, bottom_width=10.0, side_slope=1.0):
        depth = max(0.1, h - elevation)
        return bottom_width + 2 * side_slope * depth
    
    sections = [
        {
            'mileage': 0.0,
            'elevation': 100.0,
            'roughness': 0.03,
            'area_func': lambda h: area_func(h, 100.0),
            'top_width_func': lambda h: top_width_func(h, 100.0)
        },
        {
            'mileage': 100.0,
            'elevation': 99.5,
            'roughness': 0.03,
            'area_func': lambda h: area_func(h, 99.5),
            'top_width_func': lambda h: top_width_func(h, 99.5)
        },
        {
            'mileage': 200.0,
            'elevation': 99.0,
            'roughness': 0.03,
            'area_func': lambda h: area_func(h, 99.0),
            'top_width_func': lambda h: top_width_func(h, 99.0)
        }
    ]

    try:
        # 创建模型
        model = SaintVenantModel('test_channel', 'upstream_node', 'downstream_node', sections)
        print(f"模型创建成功:")
        print(f"  断面数: {len(model.sections)}")
        print(f"  分段数: {len(model.segments)}")
        print(f"  内部节点数: {len(model.internal_nodes)}")
        
        # 1. 直接验证恒定流计算
        print("\n=== 1. 恒定流计算验证 ===")
        initial_flow = 100.0  # m³/s
        downstream_level = 99.0  # m
        
        try:
            steady_result = model.compute_steady_state(initial_flow, downstream_level)
            print(f"恒定流计算成功!")
            print(f"结果包含的键: {list(steady_result.keys())}")
            
            # 分析水面线
            for key, value in steady_result.items():
                if key.startswith('H_section_'):
                    print(f"  {key}: {value:.3f}m")
                elif key.startswith('Q_seg_'):
                    print(f"  {key}: {value:.2f}m³/s")
                else:
                    print(f"  {key}: {value:.3f}")
                    
        except Exception as e:
            print(f"恒定流计算失败: {e}")
            return False
        
        # 2. 验证增强求解器的初始化
        print("\n=== 2. 增强求解器初始化验证 ===")
        config = NumericalSchemeConfig(max_iterations=5, convergence_tolerance=1e-4)
        solver = EnhancedSaintVenantSolver(model, config)
        
        print(f"求解器网格信息:")
        print(f"  断面数: {solver.n_sections}")
        print(f"  分段数: {solver.n_segments}")
        print(f"  内部节点数: {solver.n_internal_nodes}")
        print(f"  流量变量数: {solver.n_flow_vars}")
        print(f"  水位变量数: {solver.n_head_vars}")
        print(f"  总变量数: {solver.n_total_vars}")
        
        # 设置初始条件
        solver.set_initial_conditions(initial_flow, downstream_level)
        
        print(f"\n初始状态验证:")
        print(f"  流量变量: {solver.current_state[:solver.n_flow_vars]}")
        print(f"  水位变量: {solver.current_state[solver.n_flow_vars:]}")
        
        # 3. 验证初始条件的物理合理性
        print("\n=== 3. 物理合理性检查 ===")
        
        # 检查流量是否合理
        flow_vars = solver.current_state[:solver.n_flow_vars]
        print(f"流量检查:")
        print(f"  流量范围: {np.min(flow_vars):.2f} ~ {np.max(flow_vars):.2f} m³/s")
        print(f"  目标流量: {initial_flow:.2f} m³/s")
        flow_error = np.abs(flow_vars - initial_flow).max()
        print(f"  最大流量偏差: {flow_error:.2f} m³/s")
        
        # 检查水位是否合理
        head_vars = solver.current_state[solver.n_flow_vars:]
        print(f"\n水位检查:")
        if len(head_vars) > 0:
            print(f"  内部节点水位范围: {np.min(head_vars):.3f} ~ {np.max(head_vars):.3f} m")
            print(f"  下游边界水位: {downstream_level:.3f} m")
            
            # 检查水位梯度是否合理（应该是向下游递减的）
            all_heads = [solver._get_upstream_water_level()] + list(head_vars) + [downstream_level]
            gradients = np.diff(all_heads)
            print(f"  水位梯度: {gradients}")
            
            if all(g <= 0 for g in gradients):
                print("  ✓ 水位梯度合理（向下游递减）")
            else:
                print("  ✗ 水位梯度异常！")
                return False
        
        # 4. 验证初始残差
        print("\n=== 4. 初始残差检查 ===")
        
        # 构建初始Preissmann系统
        jacobian, residual = solver._build_preissmann_system(
            solver.current_state, 1.0, 0.6, 0.5)
        
        residual_norm = np.linalg.norm(residual)
        max_residual = np.max(np.abs(residual))
        
        print(f"  Jacobian矩阵维度: {jacobian.shape}")
        print(f"  残差向量维度: {residual.shape}")
        print(f"  初始残差L2范数: {residual_norm:.2e}")
        print(f"  初始残差最大值: {max_residual:.2e}")
        
        # 分析残差分布
        print(f"  残差分布:")
        n_eq_per_segment = 2  # 每段两个方程：连续性+动量
        for i in range(solver.n_segments):
            start_idx = i * n_eq_per_segment
            end_idx = min(start_idx + n_eq_per_segment, len(residual))
            if end_idx > start_idx:
                segment_residuals = residual[start_idx:end_idx]
                print(f"    分段{i}: {segment_residuals}")
        
        # 5. 检查初始条件的数值合理性
        print("\n=== 5. 数值稳定性预检查 ===")
        
        # 检查Jacobian矩阵条件数
        if jacobian.shape[0] > 0:
            try:
                cond_num = np.linalg.cond(jacobian)
                print(f"  Jacobian条件数: {cond_num:.2e}")
                
                if cond_num > 1e12:
                    print("  ✗ 矩阵条件数过大，可能数值不稳定")
                    return False
                elif cond_num > 1e6:
                    print("  ⚠ 矩阵条件数较大，需要谨慎处理")
                else:
                    print("  ✓ 矩阵条件数正常")
                    
            except Exception as e:
                print(f"  ✗ 无法计算条件数: {e}")
                return False
        
        # 总结
        print(f"\n=== 诊断总结 ===")
        
        if flow_error < 1.0 and residual_norm < 1e2:
            print("✓ 恒定流初始值估计基本正确")
            print("✓ 初始残差在可接受范围内")
            
            if residual_norm > 1e-3:
                print("⚠ 初始残差较大，可能需要优化初始值或放宽收敛容差")
                
            return True
        else:
            print("✗ 恒定流初始值估计存在问题")
            print(f"  流量偏差过大: {flow_error:.2f}")
            print(f"  初始残差过大: {residual_norm:.2e}")
            return False
            
    except Exception as e:
        print(f"诊断过程出错: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = diagnose_initial_conditions()
    if success:
        print("\n✓ 恒定流初始值估计验证通过")
    else:
        print("\n✗ 恒定流初始值估计存在问题，需要修复")