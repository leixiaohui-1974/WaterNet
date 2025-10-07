#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
非恒定流方法对比分析系统测试脚本

测试所有主要功能的运行状态
"""

import sys
import os
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

def test_comprehensive_comparison():
    """测试全谱方法对比"""
    print("🔍 测试全谱方法对比...")
    try:
        from comprehensive_methods_comparison import generate_comprehensive_unsteady_flow_comparison
        result = generate_comprehensive_unsteady_flow_comparison()
        if result:
            print("✅ 全谱方法对比测试通过")
            return True
        else:
            print("❌ 全谱方法对比测试失败")
            return False
    except Exception as e:
        print(f"❌ 全谱方法对比测试异常: {e}")
        return False

def test_object_system():
    """测试对象系统（只测试导入）"""
    print("🔍 测试对象系统导入...")
    try:
        sys.path.append(str(project_root / 'waternet'))
        from waternet.objects.conveyance import ChannelObject
        print("✅ 对象系统导入测试通过")
        return True
    except Exception as e:
        print(f"❌ 对象系统导入测试失败: {e}")
        return False

def test_file_structure():
    """测试文件结构完整性"""
    print("🔍 测试文件结构...")
    
    required_files = [
        'comprehensive_methods_comparison.py',
        'object_system_demo.py',
        'muskingum_vs_saint_venant_comparison.py',
        'simplified_model_comparison.py',
        'advanced_model_comparison.py',
        'README.md'
    ]
    
    required_dirs = [
        'configs',
        'outputs',
        'outputs/plots',
        'outputs/data', 
        'outputs/reports',
        'docs'
    ]
    
    base_path = Path(__file__).parent
    
    # 检查文件
    missing_files = []
    for file_name in required_files:
        if not (base_path / file_name).exists():
            missing_files.append(file_name)
    
    # 检查目录
    missing_dirs = []
    for dir_name in required_dirs:
        if not (base_path / dir_name).exists():
            missing_dirs.append(dir_name)
    
    if missing_files or missing_dirs:
        print(f"❌ 文件结构不完整")
        if missing_files:
            print(f"   缺失文件: {missing_files}")
        if missing_dirs:
            print(f"   缺失目录: {missing_dirs}")
        return False
    else:
        print("✅ 文件结构完整")
        return True

def check_output_files():
    """检查输出文件"""
    print("🔍 检查输出文件...")
    
    output_paths = [
        'outputs/plots/multi_method_comparison',
        'outputs/plots/muskingum_vs_saint_venant',
        'outputs/plots/simplified_model_comparison',
        'outputs/data/main_channel_unsteady_flow',
        'outputs/data/test_modified_muskingum_unsteady_flow'
    ]
    
    base_path = Path(__file__).parent
    existing_outputs = []
    
    for output_path in output_paths:
        full_path = base_path / output_path
        if full_path.exists():
            if full_path.is_dir():
                file_count = len(list(full_path.iterdir()))
                existing_outputs.append(f"{output_path} ({file_count} 文件)")
            else:
                existing_outputs.append(output_path)
    
    print(f"✅ 现有输出文件/目录: {len(existing_outputs)}")
    for output in existing_outputs:
        print(f"   📁 {output}")
    
    return len(existing_outputs) > 0

def main():
    """主测试函数"""
    print("=" * 60)
    print("非恒定流方法对比分析系统 - 完整性测试")
    print("=" * 60)
    
    tests = [
        ("文件结构", test_file_structure),
        ("对象系统导入", test_object_system),
        ("输出文件检查", check_output_files),
        ("全谱方法对比", test_comprehensive_comparison)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        success = test_func()
        results.append((test_name, success))
    
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{test_name:20} {status}")
    
    print(f"\n总体结果: {passed}/{total} 测试通过")
    
    if passed == total:
        print("🎉 所有测试都通过！系统运行正常。")
        return 0
    else:
        print("⚠️ 部分测试失败，请检查相关问题。")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)