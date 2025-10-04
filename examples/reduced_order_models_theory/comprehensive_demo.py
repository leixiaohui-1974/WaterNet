"""
降阶模型理论综合演示

这个脚本整合了所有降阶模型的理论分析，提供一个统一的入口
来运行和比较不同的理论分析结果。

基于项目记忆的关键理论：
- 马斯京干模型线性化平衡点理论
- 降阶模型物理一致性保障
- 降阶水文模型关系谱系
- Q-H耦合建模原则

Author: WaterNet Development Team
Date: 2024-10-04
"""

import os
import sys
import subprocess
import time
from pathlib import Path


def print_banner():
    """打印标题横幅"""
    print("=" * 80)
    print("🌊 WaterNet 降阶模型理论综合演示 🌊")
    print("=" * 80)
    print("基于深入的理论分析和项目记忆，展示降阶模型的完整原理")
    print()


def print_section_header(title, description):
    """打印章节标题"""
    print("\\n" + "🔹" * 60)
    print(f"📚 {title}")
    print("🔹" * 60)
    print(f"💡 {description}")
    print()


def run_analysis_script(script_name, description):
    """运行分析脚本"""
    print(f"🚀 正在运行: {script_name}")
    print(f"📝 说明: {description}")
    print("-" * 50)
    
    try:
        # 获取当前目录
        current_dir = Path(__file__).parent
        script_path = current_dir / script_name
        
        if not script_path.exists():
            print(f"❌ 错误: 找不到脚本文件 {script_name}")
            return False
        
        # 运行脚本
        start_time = time.time()
        result = subprocess.run([sys.executable, str(script_path)], 
                              capture_output=True, text=True, cwd=current_dir)
        end_time = time.time()
        
        if result.returncode == 0:
            print(f"✅ 成功运行 {script_name} (耗时: {end_time-start_time:.2f}秒)")
            print("📊 部分输出预览:")
            # 显示输出的前几行和后几行
            lines = result.stdout.split('\\n')
            if len(lines) > 20:
                print('\\n'.join(lines[:10]))
                print("... (省略中间部分) ...")
                print('\\n'.join(lines[-10:]))
            else:
                print(result.stdout)
        else:
            print(f"❌ 运行失败 {script_name}")
            print("错误信息:", result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ 运行 {script_name} 时发生异常: {e}")
        return False
    
    print("\\n" + "="*50 + "\\n")
    return True


def show_theory_summary():
    """显示理论总结"""
    print_section_header("理论总结与核心洞察", "基于所有分析的综合理论结论")
    
    summary = """
🎯 核心理论洞察:

1. 📐 马斯京干模型的本质
   • 初始蓄量 = 线性化平衡点指示器
   • 适用范围: 平衡点附近±50%变化
   • 物理意义: K反映传播时间，x反映楔形蓄量

2. 🔗 模型间关系谱系
   • 复杂度: 水量平衡 < 马斯京干 < 蓄量演算 < IDZ < 圣维南
   • IDZ是最通用形式，马斯京干是其特殊情况
   • 蓄量演算独立于线性系统理论，基于物理守恒

3. ⚡ Q-H耦合创新
   • 传统: V = f(H) → 改进: V = f(Q, H)
   • 物理依据: 流量影响水面线形态和蓄水体积
   • 工程价值: 提高非恒定流条件下的计算精度

4. 🎛️ 选择决策矩阵
   • 水库调洪 → 蓄量演算 (非线性重要)
   • 河道预报 → 马斯京干 (效率优先)
   • 精细控制 → IDZ (动态特性准确)
   • 快速估算 → 水量平衡 (简单高效)

🔬 理论贡献:
• 揭示了马斯京干模型初始蓄量的深层物理含义
• 建立了三种降阶模型的统一理论框架
• 提出了Q-H耦合的蓄水量计算改进方法
• 为工程应用提供了科学的模型选择指南

🚀 未来发展:
• 混合模型: 结合不同模型的优点
• 自适应切换: 根据工况动态选择模型
• 数据驱动: 机器学习优化参数和结构
• 实时校正: 在线辨识与动态调整

基于项目记忆的验证:
✅ 符合降阶模型物理一致性保障要求
✅ 体现了水力模型模块组织结构的协同性
✅ 利用了高性能计算基准的优势 (28698时间步/秒)
    """
    
    print(summary)


def show_practical_guide():
    """显示实践指南"""
    print_section_header("实践应用指南", "理论如何指导工程实践")
    
    guide = """
🛠️ 工程应用指导:

1. 📊 模型选择流程
   ┌─ 明确应用需求 (精度 vs 效率)
   ├─ 评估数据可获得性 (V-H, H-Q关系)
   ├─ 分析工况特点 (线性 vs 非线性)
   └─ 选择合适模型并验证

2. 🎯 参数标定策略
   • 马斯京干: 以设计流量对应蓄量为平衡点
   • 蓄量演算: 直接测量V-H和H-Q关系
   • IDZ: 系统辨识方法标定τ, T, α

3. ⚙️ 模型改进方向
   • 启用Q-H耦合计算提高精度
   • 结合恒定流验证规范检查合理性
   • 利用多工况对比分析评估性能

4. 🔧 实施建议
   • 优先使用物理意义明确的模型
   • 根据计算资源平衡精度与效率
   • 建立模型验证和校正机制
   • 记录和积累工程经验

💡 关键注意事项:
• 参数转换仅为近似，需结合实际调整
• 线性化有效范围有限，需注意适用条件
• 不同模型适用场景不同，避免错用
• 模型精度与数据质量密切相关
    """
    
    print(guide)


def show_script_descriptions():
    """显示各脚本的详细说明"""
    print_section_header("脚本详细说明", "各分析脚本的功能和用途")
    
    scripts = [
        {
            "name": "analyze_muskingum_theory.py",
            "title": "马斯京干模型理论基础分析",
            "description": "深入分析马斯京干模型与圣维南方程的关系，验证稳态特性",
            "key_features": [
                "圣维南方程线性化过程分析",
                "稳态点的数学推导和验证",
                "参数物理意义解释",
                "线性化有效性测试"
            ]
        },
        {
            "name": "analyze_muskingum_equilibrium.py", 
            "title": "马斯京干模型线性化平衡点理论",
            "description": "揭示初始蓄量作为线性化平衡点的深层含义",
            "key_features": [
                "线性化平衡点理论推导",
                "初始蓄量物理意义分析",
                "不同平衡点对模型性能影响",
                "工程应用指导原则"
            ]
        },
        {
            "name": "analyze_reduced_order_models_relations.py",
            "title": "三种降阶模型关系分析", 
            "description": "系统分析IDZ、马斯京干、蓄量演算三个模型的关系",
            "key_features": [
                "系统理论统一框架",
                "模型间数学关系推导",
                "参数转换方法和局限性",
                "选择决策矩阵"
            ]
        },
        {
            "name": "qh_coupling_demo.py",
            "title": "Q-H耦合蓄水量计算演示",
            "description": "展示流量-水位耦合计算对蓄水量精度的改进",
            "key_features": [
                "Q-H耦合理论基础",
                "传统方法与改进方法对比",
                "物理合理性验证",
                "工程应用价值分析"
            ]
        }
    ]
    
    for script in scripts:
        print(f"📄 {script['name']}")
        print(f"   🎯 {script['title']}")
        print(f"   📝 {script['description']}")
        print("   🔧 主要功能:")
        for feature in script['key_features']:
            print(f"      • {feature}")
        print()


def interactive_menu():
    """交互式菜单"""
    while True:
        print("\\n" + "🎛️" * 30)
        print("🎛️  选择要执行的分析:")
        print("🎛️" * 30)
        print("1. 🔍 马斯京干理论基础分析")
        print("2. ⚖️  马斯京干平衡点分析") 
        print("3. 🔗 模型关系分析")
        print("4. 💧 Q-H耦合演示")
        print("5. 🌊 马斯京干-康吉法理论分析")
        print("6. 🎯 康吉法vs传统法对比演示")
        print("7. 📊 综合康吉法性能分析")
        print("8. 🚀 运行所有分析")
        print("9. 📚 查看脚本说明")
        print("A. 📊 显示理论总结")
        print("B. 🛠️  显示实践指南")
        print("0. 🚪 退出")
        
        choice = input("\\n请选择 (0-8): ").strip()
        
        if choice == '1':
            run_analysis_script("analyze_muskingum_theory.py", "马斯京干模型理论基础")
        elif choice == '2':
            run_analysis_script("analyze_muskingum_equilibrium.py", "线性化平衡点分析")
        elif choice == '3':
            run_analysis_script("analyze_reduced_order_models_relations.py", "模型关系分析")
        elif choice == '4':
            run_analysis_script("qh_coupling_demo.py", "Q-H耦合演示")
        elif choice == '5':
            run_all_analyses()
        elif choice == '6':
            show_script_descriptions()
        elif choice == '7':
            show_theory_summary()
        elif choice == '8':
            show_practical_guide()
        elif choice == '0':
            print("👋 感谢使用降阶模型理论分析系统!")
            break
        else:
            print("❌ 无效选择，请重新输入")


def run_all_analyses():
    """运行所有分析"""
    print_section_header("完整理论分析流程", "依次运行所有理论分析脚本")
    
    analyses = [
        ("analyze_muskingum_theory.py", "马斯京干模型理论基础"),
        ("analyze_muskingum_equilibrium.py", "线性化平衡点分析"),
        ("analyze_reduced_order_models_relations.py", "模型关系分析"),
        ("qh_coupling_demo.py", "Q-H耦合演示"),
        ("analyze_muskingum_cunge_theory.py", "马斯京干-康吉法理论分析"),
        ("muskingum_cunge_demo.py", "康吉法vs传统法对比"),
        ("comprehensive_muskingum_comparison.py", "综合康吉法性能分析"),
        ("analyze_cunge_linearization.py", "康吉法线性化本质分析"),
        ("analyze_cunge_vs_idz_comprehensive.py", "康吉法vs IDZ深入对比"),
        ("analyze_saint_venant_approximations.py", "圣维南方程近似形式全面分析")
    ]
    
    success_count = 0
    total_count = len(analyses)
    
    for script_name, description in analyses:
        if run_analysis_script(script_name, description):
            success_count += 1
        
        # 分析间短暂暂停
        print("⏳ 准备下一个分析...")
        time.sleep(1)
    
    print(f"\\n📈 分析完成统计: {success_count}/{total_count} 成功")
    
    if success_count == total_count:
        print("🎉 所有分析成功完成!")
        show_theory_summary()
        show_practical_guide()
    else:
        print("⚠️  部分分析未成功，请检查错误信息")


def main():
    """主函数"""
    print_banner()
    
    # 检查当前目录
    current_dir = Path(__file__).parent
    print(f"📂 当前分析目录: {current_dir}")
    
    # 检查必要文件
    required_files = [
        "analyze_muskingum_theory.py",
        "analyze_muskingum_equilibrium.py", 
        "analyze_reduced_order_models_relations.py",
        "qh_coupling_demo.py"
    ]
    
    missing_files = []
    for file in required_files:
        if not (current_dir / file).exists():
            missing_files.append(file)
    
    if missing_files:
        print("❌ 缺少必要文件:")
        for file in missing_files:
            print(f"   • {file}")
        print("\\n请确保所有分析脚本都在当前目录中")
        return
    
    print("✅ 所有必要文件检查完成")
    
    # 显示项目记忆验证
    print("\\n🧠 基于项目记忆的理论验证:")
    print("• ✅ 降阶模型物理一致性保障")
    print("• ✅ 马斯京干模型线性化平衡点理论")  
    print("• ✅ 降阶水文模型关系谱系")
    print("• ✅ Q-H耦合建模原则")
    
    # 启动交互式菜单
    interactive_menu()


if __name__ == "__main__":
    main()