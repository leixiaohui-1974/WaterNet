"""
降阶模型简化API演示

展示如何使用简化的API快速创建和使用降阶模型，
大大减少了参数配置的复杂度。

基于降阶模型理论分析的最佳实践参数。

Author: WaterNet Development Team
Date: 2024-10-04
"""

import numpy as np
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# 导入简化API（目前直接从模块导入，最终会从waternet导入）
from waternet.utils.model_factory import (
    create_simple_muskingum,
    create_simple_storage_routing,
    create_simple_idz,
    create_model_by_scenario,
    quick_muskingum,
    auto_model
)


def demo_simplified_api():
    """演示简化API的使用"""
    print("=" * 80)
    print("🚀 降阶模型简化API演示")
    print("=" * 80)
    
    print("\\n✨ 传统方式 vs 简化方式对比")
    print("-" * 50)
    
    # 传统复杂方式的代码示例（仅显示，不运行）
    print("📝 传统方式（复杂）:")
    traditional_code = '''
# 需要手动定义物理关系函数
def V_to_H(V):
    return 100.0 + V / 10000.0

def H_to_Q(H):
    return max(0.0, (H - 100.0) * 25.0)

# 需要明确指定所有参数
model = MuskingumModel(
    dt=60.0,
    K=3600.0, 
    x=0.2,
    initial_V=15000.0,
    V_to_H_func=V_to_H,
    H_to_Q_func=H_to_Q,
    name="Traditional"
)
'''
    print(traditional_code)
    
    print("\\n🎯 简化方式（一行代码）:")
    simplified_code = '''
# 一行代码，使用最佳实践默认参数
model = create_simple_muskingum()
'''
    print(simplified_code)


def demo_simple_creation():
    """演示简单模型创建"""
    print("\\n\\n1. 🎯 最简单的模型创建")
    print("-" * 50)
    
    # 最简单的使用方式
    print("创建马斯京干模型（默认参数）:")
    muskingum = create_simple_muskingum()
    print(f"✅ 成功创建: {muskingum.name}")
    print(f"   参数: K={muskingum.K}s, x={muskingum.x}, dt={muskingum.dt}s")
    
    print("\\n创建蓄量演算模型（启用Q-H耦合）:")
    storage = create_simple_storage_routing()
    print(f"✅ 成功创建: {storage.name}")
    print(f"   Q-H耦合: {storage.use_QH_coupling}")
    
    print("\\n创建IDZ模型（默认参数）:")
    idz = create_simple_idz()
    print(f"✅ 成功创建: {idz.name}")
    print(f"   参数: τ={idz.tau}s, T={idz.T_delay}s, α={idz.alpha}s")


def demo_partial_customization():
    """演示部分参数自定义"""
    print("\\n\\n2. ⚙️ 部分参数自定义")
    print("-" * 50)
    
    # 只自定义需要的参数
    print("自定义马斯京干参数:")
    custom_musk = create_simple_muskingum(K=1800.0, x=0.3)
    print(f"✅ 自定义创建: K={custom_musk.K}s, x={custom_musk.x}")
    
    print("\\n自定义IDZ延迟特性:")
    custom_idz = create_simple_idz(T_delay=600.0, alpha=2000.0)
    print(f"✅ 自定义创建: T={custom_idz.T_delay}s, α={custom_idz.alpha}s")
    
    print("\\n禁用Q-H耦合的蓄量演算:")
    simple_storage = create_simple_storage_routing(enable_qh_coupling=False)
    print(f"✅ 传统模式: Q-H耦合={simple_storage.use_QH_coupling}")


def demo_scenario_based():
    """演示基于场景的模型选择"""
    print("\\n\\n3. 🎬 基于应用场景自动选择模型")
    print("-" * 50)
    
    scenarios = [
        ("reservoir", "水库调洪演算"),
        ("river_forecast", "河道洪水预报"),
        ("precise_control", "精细控制分析")
    ]
    
    for scenario_key, description in scenarios:
        model = create_model_by_scenario(scenario_key)
        print(f"📊 {description}: {model.__class__.__name__}")
        print(f"   场景代码: '{scenario_key}' -> {model.name}")


def demo_convenient_aliases():
    """演示便捷别名"""
    print("\\n\\n4. 🏃‍♂️ 便捷别名（更快捷）")
    print("-" * 50)
    
    # 使用便捷别名
    print("使用便捷别名:")
    quick_model = quick_muskingum()
    auto_selected = auto_model('river')
    
    print(f"✅ quick_muskingum() -> {quick_model.name}")
    print(f"✅ auto_model('river') -> {auto_selected.name}")


def demo_model_comparison():
    """演示模型性能对比"""
    print("\\n\\n5. 📈 简化API模型性能测试")
    print("-" * 50)
    
    # 创建三种模型进行对比
    models = {
        "马斯京干": create_simple_muskingum(),
        "蓄量演算": create_simple_storage_routing(),
        "IDZ模型": create_simple_idz()
    }
    
    # 创建测试输入
    Q_in_series = np.concatenate([
        np.ones(10) * 10.0,   # 初始流量
        np.ones(20) * 20.0,   # 增加流量  
        np.ones(10) * 10.0    # 恢复流量
    ])
    
    print("测试输入: 10→20→10 m³/s 阶跃过程")
    print("\\n模型响应对比:")
    print("模型类型      最终出流(m³/s)  响应特性")
    print("-" * 45)
    
    for name, model in models.items():
        try:
            results = model.run_simulation(Q_in_series)
            final_flow = results['Q_out'].iloc[-1]
            max_flow = results['Q_out'].max()
            
            # 简单的响应特性描述
            if abs(final_flow - 10.0) < 0.5:
                response = "稳定收敛"
            elif max_flow > 19.0:
                response = "快速响应"
            else:
                response = "平滑过渡"
            
            print(f"{name:10s}  {final_flow:13.2f}  {response}")
            
            # 重置模型
            model.reset()
            
        except Exception as e:
            print(f"{name:10s}  {'ERROR':>13}  计算失败: {e}")


def demo_best_practices():
    """演示最佳实践建议"""
    print("\\n\\n6. 💡 使用最佳实践建议")
    print("-" * 50)
    
    practices = [
        {
            "场景": "快速原型开发",
            "建议": "使用 create_simple_muskingum() 或 auto_model('river')",
            "优点": "零配置，立即可用"
        },
        {
            "场景": "精度要求高",
            "建议": "使用 create_simple_storage_routing() 启用Q-H耦合",
            "优点": "物理机理更准确"
        },
        {
            "场景": "控制系统设计",
            "建议": "使用 create_simple_idz() 获得系统响应特性",
            "优点": "动态特性描述精确"
        },
        {
            "场景": "参数敏感性分析",
            "建议": "先用默认参数验证，再逐步调整关键参数",
            "优点": "避免参数空间搜索"
        }
    ]
    
    for practice in practices:
        print(f"🎯 {practice['场景']}:")
        print(f"   建议: {practice['建议']}")
        print(f"   优点: {practice['优点']}")
        print()


def demo_migration_guide():
    """演示从传统API迁移指南"""
    print("\\n\\n7. 🔄 从传统API迁移指南")
    print("-" * 50)
    
    migration_examples = [
        {
            "before": "MuskingumModel(dt=60, K=3600, x=0.2, initial_V=15000, V_to_H_func=..., H_to_Q_func=...)",
            "after": "create_simple_muskingum()",
            "savings": "减少90%代码量"
        },
        {
            "before": "需要手动定义V_to_H和H_to_Q函数",
            "after": "自动使用工程最佳实践参数",
            "savings": "消除重复代码"
        },
        {
            "before": "需要查阅文档确定合理参数范围",
            "after": "基于理论分析的预设参数",
            "savings": "减少学习成本"
        }
    ]
    
    for i, example in enumerate(migration_examples, 1):
        print(f"{i}. 传统方式: {example['before']}")
        print(f"   简化方式: {example['after']}")
        print(f"   效果: {example['savings']}")
        print()


def main():
    """主演示函数"""
    try:
        # 展示简化API优势
        demo_simplified_api()
        
        # 基本使用演示
        demo_simple_creation()
        
        # 参数自定义
        demo_partial_customization()
        
        # 场景选择
        demo_scenario_based()
        
        # 便捷别名
        demo_convenient_aliases()
        
        # 性能对比
        demo_model_comparison()
        
        # 最佳实践
        demo_best_practices()
        
        # 迁移指南
        demo_migration_guide()
        
        print("\\n" + "=" * 80)
        print("🎉 简化API演示完成！")
        print("=" * 80)
        print("✅ 主要优势:")
        print("  • 零配置快速启动")
        print("  • 基于理论的最佳实践参数")
        print("  • 向后兼容传统API")
        print("  • 支持渐进式自定义")
        print("  • 应用场景自动匹配")
        
        print("\\n💡 使用建议:")
        print("  • 原型开发：使用简化API快速验证想法")
        print("  • 生产应用：根据具体需求微调参数")
        print("  • 学习研究：从简化API开始，逐步深入理论")
        
    except Exception as e:
        print(f"演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()