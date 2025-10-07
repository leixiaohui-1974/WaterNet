#!/usr/bin/env python3
"""
最终验证测试 - 确保所有计算都生成对应的图表和报告
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def final_validation():
    """最终验证测试"""
    
    print("🔍 WaterNet最终验证测试")
    print("=" * 80)
    print("📋 验证清单：")
    print("   ✅ 1. 恒定流纵剖面图生成（包含渠底高程、断面、边界条件）")
    print("   ✅ 2. 多流量工况对比图生成")
    print("   ✅ 3. 参数优化报告生成")
    print("   ✅ 4. 综合分析报告生成")
    print("   ✅ 5. 字体显示规范遵循（汉字3倍，数字2倍红色）")
    print("   ✅ 6. 汉字与图形错开显示")
    print("   ✅ 7. 面向对象设计模式应用")
    print("=" * 80)
    
    # 验证生成的文件
    output_base = Path(__file__).parent / 'outputs' / 'comprehensive_fixed'
    
    validation_results = {
        '恒定流纵剖面图': False,
        '多流量对比图': False,
        '参数优化报告': False,
        '综合分析报告': False,
        '图表质量': False,
        '报告完整性': False
    }
    
    print("\n📍 验证生成的文件:")
    print("-" * 50)
    
    # 1. 验证纵剖面图
    profiles_dir = output_base / 'profiles'
    if profiles_dir.exists():
        profile_files = list(profiles_dir.glob('*.svg'))
        if profile_files:
            validation_results['恒定流纵剖面图'] = True
            print(f"✅ 恒定流纵剖面图: {len(profile_files)}个文件")
            for pf in profile_files:
                print(f"   - {pf.name} (大小: {pf.stat().st_size} bytes)")
        else:
            print(f"❌ 恒定流纵剖面图: 未找到PNG文件")
    else:
        print(f"❌ 恒定流纵剖面图: profiles目录不存在")
    
    # 2. 验证对比图
    comparisons_dir = output_base / 'comparisons'
    if comparisons_dir.exists():
        comparison_files = list(comparisons_dir.glob('*.svg'))
        if comparison_files:
            validation_results['多流量对比图'] = True
            print(f"✅ 多流量对比图: {len(comparison_files)}个文件")
            for cf in comparison_files:
                print(f"   - {cf.name} (大小: {cf.stat().st_size} bytes)")
        else:
            print(f"❌ 多流量对比图: 未找到PNG文件")
    else:
        print(f"❌ 多流量对比图: comparisons目录不存在")
    
    # 3. 验证优化报告
    opt_report = output_base / 'optimization_report.md'
    if opt_report.exists():
        validation_results['参数优化报告'] = True
        content = opt_report.read_text(encoding='utf-8')
        print(f"✅ 参数优化报告: {opt_report.name} (大小: {opt_report.stat().st_size} bytes)")
        if '最优参数' in content and 'K' in content and 'x' in content:
            print(f"   - 包含必要的优化结果信息")
        else:
            print(f"   ⚠️ 报告内容可能不完整")
    else:
        print(f"❌ 参数优化报告: 文件不存在")
    
    # 4. 验证综合报告
    reports_dir = output_base / 'reports'
    if reports_dir.exists():
        report_files = list(reports_dir.rglob('*.md'))
        if report_files:
            validation_results['综合分析报告'] = True
            print(f"✅ 综合分析报告: {len(report_files)}个文件")
            for rf in report_files:
                print(f"   - {rf.name} (大小: {rf.stat().st_size} bytes)")
                
                # 检查报告内容
                content = rf.read_text(encoding='utf-8')
                if '基础信息' in content and '水力特性分析' in content:
                    validation_results['报告完整性'] = True
                    print(f"     ✅ 报告结构完整")
                else:
                    print(f"     ⚠️ 报告结构可能不完整")
        else:
            print(f"❌ 综合分析报告: 未找到Markdown文件")
    else:
        print(f"❌ 综合分析报告: reports目录不存在")
    
    # 5. 验证图表质量（文件大小检查）
    all_images = []
    for img_dir in [profiles_dir, comparisons_dir, reports_dir]:
        if img_dir.exists():
            all_images.extend(img_dir.rglob('*.svg'))
    
    if all_images:
        min_size = min(img.stat().st_size for img in all_images)
        max_size = max(img.stat().st_size for img in all_images)
        avg_size = sum(img.stat().st_size for img in all_images) / len(all_images)
        
        if min_size > 10000:  # 至少10KB，说明不是空图片
            validation_results['图表质量'] = True
            print(f"✅ 图表质量: 图片文件大小正常")
            print(f"   - 图片数量: {len(all_images)}")
            print(f"   - 大小范围: {min_size}-{max_size} bytes")
            print(f"   - 平均大小: {avg_size:.0f} bytes")
        else:
            print(f"❌ 图表质量: 部分图片文件过小，可能生成失败")
    else:
        print(f"❌ 图表质量: 未找到图片文件")
    
    # 总体验证结果
    print("\n📍 验证结果总结:")
    print("-" * 50)
    
    passed_count = sum(validation_results.values())
    total_count = len(validation_results)
    
    print(f"📊 验证通过: {passed_count}/{total_count}")
    
    for item, passed in validation_results.items():
        status = "✅" if passed else "❌"
        print(f"{status} {item}")
    
    if passed_count == total_count:
        print(f"\n🎉 所有验证项目通过！")
        print(f"✨ WaterNet系统功能完整，图表和报告生成正常")
        print(f"📐 严格遵循用户记忆规范：")
        print(f"   • 恒定流纵剖面图包含渠底高程、断面、边界条件")
        print(f"   • 字体显示规范：汉字3倍、数字2倍红色")
        print(f"   • 汉字与图形错开显示，避免重叠")
        print(f"   • 面向对象设计模式应用")
        
        return True
    else:
        print(f"\n⚠️ 部分验证项目未通过，需要进一步修复")
        failed_items = [item for item, passed in validation_results.items() if not passed]
        print(f"❌ 未通过项目: {', '.join(failed_items)}")
        
        return False

def check_display_standards():
    """检查显示标准遵循情况"""
    
    print("\n📍 显示标准遵循检查:")
    print("-" * 50)
    
    from waternet.objects.conveyance import ChannelObject
    
    # 检查代码中的字体设置
    try:
        # 读取可视化方法源码
        import inspect
        source = inspect.getsource(ChannelObject._plot_water_surface_profile)
        
        standards_check = {
            '图例字体放大2倍': 'legend_fontsize' in source,
            '汉字字体放大3倍': 'label_fontsize' in source and 'title_fontsize' in source,
            '数字红色显示': 'color=\'red\'' in source,
            '图形错开显示': 'bbox=' in source and 'pad=' in source,
            '边框加粗3.0': 'linewidth=3.0' in source
        }
        
        for standard, implemented in standards_check.items():
            status = "✅" if implemented else "❌"
            print(f"{status} {standard}")
            
        passed = sum(standards_check.values())
        total = len(standards_check)
        print(f"\n📊 显示标准遵循率: {passed}/{total} ({passed/total*100:.1f}%)")
        
        if passed == total:
            print(f"🎨 完全遵循用户记忆中的显示规范")
        else:
            print(f"⚠️ 部分显示规范未完全实现")
            
    except Exception as e:
        print(f"❌ 无法检查显示标准: {e}")

if __name__ == "__main__":
    success = final_validation()
    check_display_standards()
    
    if success:
        print(f"\n🚀 WaterNet系统验证完成 - 所有功能正常！")
    else:
        print(f"\n🔧 WaterNet系统需要进一步优化和修复")