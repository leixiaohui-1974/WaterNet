#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Muskingum模型接口修复
验证downstream_level参数兼容性
"""

import sys
import os
import numpy as np

# 添加项目路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from waternet.models.lumped_models import MuskingumModel, StorageRoutingModel, IntegralDelayZeroModel

def create_test_functions():
    """创建测试用的物理关系函数"""
    def V_to_H(V):
        """蓄量转水位：简单线性关系"""
        return 100.0 + V / 1000.0  # 基准水位100m，每1000m³提升1m
    
    def H_to_Q(H):
        """水位转出流：堰流公式"""
        if H > 100.0:
            return 10.0 * (H - 100.0) ** 1.5
        else:
            return 0.0
    
    return V_to_H, H_to_Q

def test_muskingum_interface():
    """测试Muskingum模型接口兼容性"""
    print("=== 测试Muskingum模型接口修复 ===")
    
    V_to_H, H_to_Q = create_test_functions()
    
    # 创建Muskingum模型
    model = MuskingumModel(
        dt=60.0,           # 1分钟时间步
        K=300.0,           # 5分钟滞时常数
        x=0.2,             # 权重系数
        initial_V=5000.0,  # 初始蓄水量
        V_to_H_func=V_to_H,
        H_to_Q_func=H_to_Q,
        name="TestMuskingum"
    )
    
    # 测试1：原有接口（向后兼容）
    try:
        result1 = model.step(Q_in=10.0)
        print(f"✓ 原有接口测试通过: Q_out={result1['Q_out']:.3f} m³/s")
    except Exception as e:
        print(f"✗ 原有接口测试失败: {e}")
        return False
    
    # 测试2：新接口带downstream_level参数
    try:
        result2 = model.step(Q_in=12.0, downstream_level=101.5)
        print(f"✓ 新接口测试通过: Q_out={result2['Q_out']:.3f} m³/s")
    except Exception as e:
        print(f"✗ 新接口测试失败: {e}")
        return False
    
    # 测试3：新接口带其他参数
    try:
        result3 = model.step(Q_in=8.0, downstream_level=101.0, upstream_stage=102.0)
        print(f"✓ 扩展参数测试通过: Q_out={result3['Q_out']:.3f} m³/s")
    except Exception as e:
        print(f"✗ 扩展参数测试失败: {e}")
        return False
    
    return True

def test_storage_routing_interface():
    """测试StorageRouting模型接口兼容性"""
    print("\n=== 测试StorageRouting模型接口修复 ===")
    
    V_to_H, H_to_Q = create_test_functions()
    
    # 创建StorageRouting模型
    model = StorageRoutingModel(
        dt=60.0,           # 1分钟时间步
        initial_V=5000.0,  # 初始蓄水量
        V_to_H_func=V_to_H,
        H_to_Q_func=H_to_Q,
        name="TestStorageRouting"
    )
    
    # 测试原有接口和新接口
    try:
        result1 = model.step(Q_in=15.0)
        print(f"✓ StorageRouting原有接口: Q_out={result1['Q_out']:.3f} m³/s")
        
        result2 = model.step(Q_in=18.0, downstream_level=102.0)
        print(f"✓ StorageRouting新接口: Q_out={result2['Q_out']:.3f} m³/s")
        
        return True
    except Exception as e:
        print(f"✗ StorageRouting接口测试失败: {e}")
        return False

def test_idz_interface():
    """测试IDZ模型接口兼容性"""
    print("\n=== 测试IDZ模型接口 ===")
    
    V_to_H, H_to_Q = create_test_functions()
    
    # 创建IDZ模型
    try:
        model = IntegralDelayZeroModel(
            dt=60.0,
            initial_V=5000.0,
            V_to_H_func=V_to_H,
            H_to_Q_func=H_to_Q,
            Q0_up=10.0, H0_up=101.0,
            Q0_down=10.0, H0_down=100.5,
            name="TestIDZ"
        )
        
        # IDZ模型已经有支持multiple参数的接口
        result1 = model.step(Q_in=12.0)
        print(f"✓ IDZ模型接口正常: Q_out上游={result1.get('Q_out_up', 'N/A')}")
        
        result2 = model.step(Q_in=15.0, Q_in_down=2.0)
        print(f"✓ IDZ双节点接口正常: Q_out下游={result2.get('Q_out_down', 'N/A')}")
        
        return True
    except Exception as e:
        print(f"✗ IDZ模型测试失败: {e}")
        return False

def test_nonsteady_simulation_compatibility():
    """测试非恒定流仿真兼容性"""
    print("\n=== 测试非恒定流仿真兼容性 ===")
    
    V_to_H, H_to_Q = create_test_functions()
    
    # 创建模型
    model = MuskingumModel(
        dt=60.0, K=300.0, x=0.2, initial_V=5000.0,
        V_to_H_func=V_to_H, H_to_Q_func=H_to_Q
    )
    
    # 模拟非恒定流仿真场景
    time_series = np.arange(0, 3600, 60)  # 1小时，1分钟步长
    Q_in_series = 10.0 + 5.0 * np.sin(time_series / 600.0)  # 正弦变化的入流
    downstream_levels = 101.0 + 0.5 * np.sin(time_series / 800.0)  # 变化的下游水位
    
    results = []
    
    try:
        for i, (Q_in, h_down) in enumerate(zip(Q_in_series, downstream_levels)):
            # 模拟非恒定流仿真中的调用方式
            result = model.step(Q_in=Q_in, downstream_level=h_down)
            results.append({
                'time': i * 60,
                'Q_in': Q_in,
                'Q_out': result['Q_out'],
                'H_out': result['H_out'],
                'downstream_level': h_down
            })
        
        print(f"✓ 非恒定流仿真测试通过，计算了{len(results)}个时间步")
        print(f"  最终出流: {results[-1]['Q_out']:.3f} m³/s")
        print(f"  最终水位: {results[-1]['H_out']:.3f} m")
        
        return True
        
    except Exception as e:
        print(f"✗ 非恒定流仿真测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("Muskingum模型接口兼容性测试")
    print("=" * 50)
    
    # 记录结果
    test_results = []
    
    # 执行各项测试
    test_results.append(("Muskingum接口", test_muskingum_interface()))
    test_results.append(("StorageRouting接口", test_storage_routing_interface()))
    test_results.append(("IDZ接口", test_idz_interface()))
    test_results.append(("非恒定流兼容性", test_nonsteady_simulation_compatibility()))
    
    # 汇总结果
    print("\n" + "=" * 50)
    print("测试结果汇总:")
    
    passed = 0
    for test_name, result in test_results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n总体结果: {passed}/{len(test_results)} 项测试通过")
    
    if passed == len(test_results):
        print("🎉 所有接口修复验证通过！")
        print("根据记忆中的要求，Muskingum模型现在支持downstream_level参数传递。")
        return True
    else:
        print("⚠️ 部分测试失败，需要进一步修复。")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)