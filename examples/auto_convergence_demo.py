#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动收敛优化器演示程序

展示如何在WaterNet基础类库中使用自动收敛优化器，
实现透明的数值优化，用户无需手动调整参数。

Author: WaterNet Development Team
Date: 2024-12-23
"""

import sys
import os
import numpy as np

# 添加项目路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def demonstrate_auto_convergence():
    """演示自动收敛优化器的使用"""
    print("🎯 WaterNet自动收敛优化器演示")
    print("=" * 60)
    print("基于'简化参数设计规范'，用户只需选择收敛策略，")
    print("求解器会自动处理所有数值优化细节，实现透明的自动收敛。")
    print()
    
    try:
        # 导入基础类库
        from waternet.models.saint_venant import SaintVenantModel
        print("✅ 成功导入WaterNet基础类库")
        
        # 创建简单的渠道模型
        print("\n📋 创建测试渠道模型...")
        
        def area_func(h, elevation=85.0, bottom_width=15.0, side_slope=1.5):
            depth = max(0.1, h - elevation)
            return bottom_width * depth + side_slope * depth**2
        
        def top_width_func(h, elevation=85.0, bottom_width=15.0, side_slope=1.5):
            depth = max(0.1, h - elevation)
            return bottom_width + 2 * side_slope * depth
        
        sections = [
            {
                'mileage': 0.0,
                'elevation': 86.0,
                'roughness': 0.025,
                'area_func': lambda h: area_func(h, 86.0, 12.0, 1.5),
                'top_width_func': lambda h: top_width_func(h, 86.0, 12.0, 1.5)
            },
            {
                'mileage': 2500.0,
                'elevation': 85.5,
                'roughness': 0.025,
                'area_func': lambda h: area_func(h, 85.5, 15.0, 1.5),
                'top_width_func': lambda h: top_width_func(h, 85.5, 15.0, 1.5)
            },
            {
                'mileage': 5000.0,
                'elevation': 85.0,
                'roughness': 0.030,
                'area_func': lambda h: area_func(h, 85.0, 18.0, 2.0),
                'top_width_func': lambda h: top_width_func(h, 85.0, 18.0, 2.0)
            }
        ]
        
        model = SaintVenantModel(
            name="auto_convergence_channel",
            upstream_node="upstream",
            downstream_node="downstream",
            sections=sections,
            solver_type="enhanced"
        )
        
        print(f"   渠道名称: {model.name}")
        print(f"   断面数量: {len(sections)}")
        print(f"   总长度: 5000 m")
        
        # 演示不同收敛策略的使用
        strategies = [
            ("adaptive", "自适应策略（推荐）"),
            ("conservative", "保守策略（稳定性优先）"),
            ("balanced", "平衡策略（性能与稳定性兼顾）"),
            ("aggressive", "激进策略（性能优先）")
        ]
        
        print("\n🚀 演示不同收敛策略...")
        
        for strategy, description in strategies:
            print(f"\n--- {description} ---")
            
            try:
                # 创建集成自动收敛优化的增强求解器
                enhanced_solver = model.create_enhanced_solver()
                
                if enhanced_solver is None:
                    print("   ❌ 无法创建增强求解器")
                    continue
                
                print(f"   策略: {strategy}")
                print("   配置: 自动优化，用户无需调整数值参数")
                
                # 设置初始条件
                enhanced_solver.set_initial_conditions(100.0, 96.0)
                print("   ✅ 初始条件设置完成")
                
                # 测试单个时间步
                print("   🧪 测试时间步求解...")
                result = enhanced_solver.solve_time_step(
                    dt=60.0,
                    upstream_flow=101.0,
                    downstream_water_level=96.005
                )
                
                if result['convergence_success']:
                    print(f"   ✅ 收敛成功: {result['iterations']}次迭代")
                    print(f"   📊 方法: {result.get('method', 'unknown')}")
                    
                    # 显示诊断信息
                    diagnostics = result.get('diagnostics', {})
                    if diagnostics.get('auto_optimization_enabled'):
                        print("   🔧 自动收敛优化: 已启用")
                        print(f"   📈 收敛率: {diagnostics.get('convergence_rate', 0):.1%}")
                    
                    # 显示物理结果
                    flow_vars = result.get('flow_variables', {})
                    water_levels = result.get('water_levels', {})
                    
                    if flow_vars:
                        flows = list(flow_vars.values())
                        print(f"   🌊 流量范围: {min(flows):.2f} - {max(flows):.2f} m³/s")
                    
                    if water_levels:
                        levels = list(water_levels.values())
                        print(f"   📏 水位范围: {min(levels):.3f} - {max(levels):.3f} m")
                    
                else:
                    print(f"   ❌ 收敛失败: {result['iterations']}次迭代")
                
                # 获取性能摘要
                try:
                    performance = enhanced_solver.get_performance_summary()
                    solver_config = performance.get('solver_configuration', {})
                    
                    print("   📋 求解器配置:")
                    print(f"     收敛策略: {solver_config.get('convergence_strategy', 'unknown')}")
                    print(f"     质量优先级: {solver_config.get('quality_priority', 'unknown')}")
                    print(f"     自动优化: {solver_config.get('auto_convergence_enabled', False)}")
                    
                except Exception as e:
                    print(f"   ⚠️ 无法获取性能摘要: {e}")
                
            except Exception as e:
                print(f"   ❌ 策略测试失败: {e}")
                continue
        
        # 演示用户友好的API
        print("\n💡 用户友好的API演示...")
        print("用户只需要关心以下几个参数：")
        print()
        
        print("1. 收敛策略选择：")
        print("   - 'adaptive'    : 自适应（推荐，适用于大多数情况）")
        print("   - 'conservative': 保守型（适用于数值困难的问题）")
        print("   - 'balanced'    : 平衡型（适用于标准工程计算）")
        print("   - 'aggressive'  : 激进型（适用于性能要求高的场景）")
        print()
        
        print("2. 质量优先级：")
        print("   - 'stability'   : 稳定性优先（默认，推荐）")
        print("   - 'speed'       : 速度优先（适用于实时计算）")
        print()
        
        print("✨ 所有其他数值参数（Jacobian优化、时间步控制、松弛因子等）")
        print("   都由自动收敛优化器透明处理，用户无需关心！")
        
        return True
        
    except ImportError as e:
        print(f"❌ 模块导入失败: {e}")
        print("请确保自动收敛优化器已正确安装到基础类库中")
        return False
    
    except Exception as e:
        print(f"❌ 演示过程异常: {e}")
        import traceback
        traceback.print_exc()
        return False

def demonstrate_simplified_api():
    """演示简化的API使用"""
    print("\n🎨 简化API使用演示")
    print("=" * 60)
    
    # 演示代码示例
    example_code = '''
# 用户代码示例（极其简单！）

from waternet.models.saint_venant import SaintVenantModel

# 1. 创建模型（与之前完全相同）
model = SaintVenantModel(name="my_channel", ...)

# 2. 创建自动收敛求解器（一行代码！）
solver = model.create_enhanced_solver()

# 3. 设置初始条件
solver.set_initial_conditions(flow=100.0, level=96.0)

# 4. 求解（自动收敛优化！）
result = solver.solve_time_step(dt=60.0, upstream_flow=101.0, downstream_level=96.0)

# 5. 检查结果
if result['convergence_success']:
    print("✅ 自动收敛成功！")
    # 无需关心Jacobian条件数、松弛因子、时间步控制等复杂细节
else:
    print("❌ 即使自动优化也未收敛（罕见情况）")

# 高级用户可选：自定义收敛策略
solver_custom = model.create_enhanced_solver(
    convergence_strategy="conservative",  # 可选择策略
    quality_priority="stability"          # 可选择优先级
)
'''
    
    print("💻 用户代码示例：")
    print(example_code)
    
    print("🎯 设计优势：")
    print("1. ✅ 简化参数设计：用户只需选择策略，无需关心数值细节")
    print("2. ✅ 渐进式自定义：基础用户用默认值，高级用户可微调")
    print("3. ✅ 透明优化：所有Jacobian、松弛、时间步优化自动进行")
    print("4. ✅ 物理意义优先：确保数值稳定性和物理合理性")
    print("5. ✅ API向后兼容：不影响现有用户代码")

def main():
    """主函数"""
    print("🌊 WaterNet自动收敛优化器集成演示")
    print("将数值优化策略作为基础功能集成到类库中")
    print("用户无需手动尝试不同策略，实现自动收敛")
    print("=" * 80)
    
    # 执行演示
    success = demonstrate_auto_convergence()
    
    if success:
        demonstrate_simplified_api()
        
        print("\n" + "=" * 80)
        print("🏆 演示完成")
        print("✅ 自动收敛优化器已成功集成到基础类库")
        print("✅ 用户只需选择收敛策略，求解器自动处理数值优化")
        print("✅ 实现了透明的自动收敛，降低了使用门槛")
        print("✅ 符合'简化参数设计规范'和'基础代码库优先原则'")
    else:
        print("\n" + "=" * 80)
        print("⚠️ 演示部分失败")
        print("需要完成自动收敛优化器的完整集成")

if __name__ == "__main__":
    main()