"""
WaterNet 快速开始指南 - 简化版

展示如何使用简化API快速创建和运行降阶模型，
大大减少了学习和使用的复杂度。

Author: WaterNet Development Team
Date: 2024-10-04
"""

import numpy as np
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 导入简化API
from waternet.utils.model_factory import (
    create_simple_muskingum,
    create_simple_storage_routing,
    create_model_by_scenario,
    quick_muskingum
)


def quick_start_simplified():
    """简化版快速开始示例"""
    print("🌊 WaterNet 快速开始 - 简化版")
    print("=" * 50)
    
    print("🎯 对比：传统方式 vs 简化方式")
    print("-" * 30)
    
    # === 1. 传统方式（复杂） ===
    print("❌ 传统方式（需要20+行代码）:")
    print('''
    # 需要手动定义物理关系函数
    def V_to_H(V):
        return 99 + V / 10000
    
    def H_to_Q(H):
        return max(0, (H - 99) * 20)
    
    # 需要明确指定所有参数
    model = MuskingumModel(
        dt=60.0, K=3600.0, x=0.2, initial_V=10000.0,
        V_to_H_func=V_to_H, H_to_Q_func=H_to_Q
    )
    ''')
    
    # === 2. 简化方式（一行代码） ===
    print("✅ 简化方式（一行代码）:")
    print("    model = create_simple_muskingum()")
    
    print("\\n" + "="*50)
    print("🚀 开始实际演示")
    print("="*50)


def demo_three_approaches():
    """演示三种不同的简化方法"""
    
    print("\\n1. 📦 最简单方式：一行代码创建")
    print("-" * 40)
    
    # 方法1：默认参数
    model1 = create_simple_muskingum()
    print(f"✅ 创建成功: {model1.name}")
    print(f"   默认参数: K={model1.K}s, x={model1.x}")
    
    
    print("\\n2. ⚙️ 部分自定义：只改需要的参数")
    print("-" * 40)
    
    # 方法2：部分自定义
    model2 = create_simple_muskingum(K=1800.0, x=0.3)
    print(f"✅ 创建成功: {model2.name}")
    print(f"   自定义参数: K={model2.K}s, x={model2.x}")
    
    
    print("\\n3. 🎬 场景驱动：根据应用自动选择")
    print("-" * 40)
    
    # 方法3：场景驱动
    scenarios = [
        ("reservoir", "水库调洪"),
        ("river_forecast", "河道预报"),
        ("precise_control", "精细控制")
    ]
    
    for scenario, description in scenarios:
        model = create_model_by_scenario(scenario)
        print(f"✅ {description}: {model.__class__.__name__}")
    
    return model1, model2


def demo_model_usage(model):
    """演示模型使用"""
    print("\\n" + "="*50)
    print("🔧 模型使用演示")
    print("="*50)
    
    print("\\n1. 📊 创建测试输入")
    # 简单的阶跃输入
    Q_in_series = np.array([
        5.0, 5.0, 5.0,      # 初始阶段
        15.0, 15.0, 15.0,   # 增加流量
        10.0, 10.0, 10.0,   # 中等流量
        5.0, 5.0, 5.0       # 回到初始
    ])
    
    print(f"输入序列: {Q_in_series}")
    print(f"时间步数: {len(Q_in_series)}")
    
    print("\\n2. 🏃‍♂️ 运行仿真")
    results = model.run_simulation(Q_in_series)
    
    print(f"✅ 仿真完成")
    print(f"   结果行数: {len(results)}")
    print(f"   结果列数: {len(results.columns)}")
    
    print("\\n3. 📈 结果分析")
    final_Q_out = results['Q_out'].iloc[-1]
    max_Q_out = results['Q_out'].max()
    min_Q_out = results['Q_out'].min()
    
    print(f"   最终出流: {final_Q_out:.2f} m³/s")
    print(f"   最大出流: {max_Q_out:.2f} m³/s")
    print(f"   最小出流: {min_Q_out:.2f} m³/s")
    
    return results


def demo_multiple_models():
    """演示多模型对比"""
    print("\\n" + "="*50)
    print("🏆 多模型性能对比")
    print("="*50)
    
    # 创建三种模型
    models = {
        "马斯京干（默认）": create_simple_muskingum(),
        "马斯京干（快速）": create_simple_muskingum(K=1200.0, x=0.1),
        "蓄量演算": create_simple_storage_routing()
    }
    
    # 统一输入
    Q_in = np.array([10.0, 20.0, 15.0, 10.0, 5.0])
    
    print("\\n对比结果:")
    print("模型类型            最终出流    最大出流    响应速度")
    print("-" * 55)
    
    for name, model in models.items():
        try:
            results = model.run_simulation(Q_in)
            final_Q = results['Q_out'].iloc[-1]
            max_Q = results['Q_out'].max()
            
            # 简单的响应速度评估
            if max_Q > 18.0:
                speed = "快"
            elif max_Q > 15.0:
                speed = "中"
            else:
                speed = "慢"
            
            print(f"{name:15s}   {final_Q:8.2f}   {max_Q:8.2f}     {speed}")
            
            # 重置模型
            model.reset()
            
        except Exception as e:
            print(f"{name:15s}   ERROR: {str(e)[:20]}...")


def demo_convenience_functions():
    """演示便捷函数"""
    print("\\n" + "="*50)
    print("⚡ 便捷函数演示")
    print("="*50)
    
    print("\\n1. 🏃‍♂️ 极简调用")
    quick_model = quick_muskingum()
    print(f"✅ quick_muskingum() -> {quick_model.name}")
    
    print("\\n2. 🎯 智能选择")
    smart_models = {
        "river": "河道洪水预报",
        "reservoir": "水库调洪", 
        "control": "精细控制"
    }
    
    for key, desc in smart_models.items():
        model = create_model_by_scenario(key)
        print(f"✅ auto_model('{key}') -> {desc}")


def show_comparison_summary():
    """显示对比总结"""
    print("\\n" + "="*50)
    print("📊 简化API优势总结")
    print("="*50)
    
    comparison = [
        ("代码量", "传统API: 20+ 行", "简化API: 1 行", "减少95%"),
        ("学习成本", "需要理解所有参数", "零配置即用", "大幅降低"),
        ("错误率", "参数配置易出错", "预设最佳实践", "显著减少"),
        ("开发效率", "需要查阅文档", "立即可用", "10倍提升"),
        ("维护性", "参数分散难管理", "统一配置管理", "大幅改善")
    ]
    
    print("\\n对比项目      传统API           简化API          改善程度")
    print("-" * 65)
    
    for item, traditional, simplified, improvement in comparison:
        print(f"{item:8s}  {traditional:15s}  {simplified:15s}  {improvement}")
    
    print("\\n💡 使用建议:")
    recommendations = [
        "🚀 快速原型：使用简化API验证想法",
        "📚 学习研究：从简化API开始，逐步深入",
        "🏭 生产环境：根据需求在简化API基础上微调",
        "🔧 复杂场景：简化API + 自定义参数组合使用"
    ]
    
    for rec in recommendations:
        print(f"   {rec}")


def main():
    """主函数"""
    try:
        # 开始演示
        quick_start_simplified()
        
        # 三种方法演示
        model1, model2 = demo_three_approaches()
        
        # 模型使用演示
        results = demo_model_usage(model1)
        
        # 多模型对比
        demo_multiple_models()
        
        # 便捷函数
        demo_convenience_functions()
        
        # 总结对比
        show_comparison_summary()
        
        print("\\n" + "🎉" * 20)
        print("🎉 简化版快速开始演示完成！")
        print("🎉" * 20)
        
        print("\\n📚 下一步建议:")
        print("1. 尝试运行本脚本体验简化API")
        print("2. 查看 examples/reduced_order_models_theory/ 了解理论")
        print("3. 根据具体需求调整参数")
        print("4. 集成到你的项目中")
        
        return results
        
    except Exception as e:
        print(f"❌ 演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()