#!/usr/bin/env python3
"""
快速验证所有生成文件的状态
"""

import sys
from pathlib import Path
import json

# 添加项目路径
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

def check_file_status():
    """检查所有文件状态"""
    print("🔍 检查文件生成状态")
    print("=" * 60)
    
    output_base = current_dir / 'outputs'
    
    # 检查目录结构
    key_dirs = [
        'refactored_reports/comprehensive/data',
        'refactored_reports/comprehensive/plots/steady_flow_profiles',
        'refactored_reports/comprehensive/reports',
        'refactored_reports/hydraulic',
        'smart_analysis/reports',
        'simplified_demo/profiles'
    ]
    
    print("📁 目录检查:")
    for dir_path in key_dirs:
        full_path = output_base / dir_path
        if full_path.exists():
            file_count = len(list(full_path.glob('*')))
            print(f"   ✅ {dir_path}: {file_count} 个文件")
        else:
            print(f"   ❌ {dir_path}: 不存在")
    
    # 检查关键文件
    print(f"\n📄 关键文件检查:")
    
    # 1. 综合报告
    report_files = list((output_base / 'refactored_reports' / 'comprehensive' / 'reports').glob('*.md'))
    if report_files:
        for report_file in report_files:
            size = report_file.stat().st_size
            print(f"   ✅ 综合报告: {report_file.name} ({size:,} bytes)")
    else:
        print(f"   ❌ 综合报告: 未找到")
    
    # 2. 纵剖面图
    profile_files = list((output_base / 'refactored_reports' / 'comprehensive' / 'plots' / 'steady_flow_profiles').glob('*.svg'))
    if profile_files:
        for profile_file in profile_files:
            size = profile_file.stat().st_size
            print(f"   ✅ 纵剖面图: {profile_file.name} ({size:,} bytes)")
    else:
        print(f"   ❌ 纵剖面图: 未找到")
    
    # 3. 数据文件
    data_files = list((output_base / 'refactored_reports' / 'comprehensive' / 'data').glob('*.json'))
    if data_files:
        for data_file in data_files:
            size = data_file.stat().st_size
            print(f"   ✅ 数据文件: {data_file.name} ({size:,} bytes)")
            
            # 检查数据内容
            try:
                with open(data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if 'water_levels_fixed' in data:
                        print(f"     → 水位修复状态: {data['water_levels_fixed']}")
            except:
                pass
    else:
        print(f"   ❌ 数据文件: 未找到")
    
    # 4. 检查任何包含异常高水位的文件
    print(f"\n🔍 异常数据检查:")
    all_json_files = list(output_base.rglob('*.json'))
    found_anomaly = False
    
    for json_file in all_json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if '64321' in content or '308796' in content:
                    print(f"   ⚠️ 发现异常数据: {json_file}")
                    found_anomaly = True
        except:
            continue
    
    if not found_anomaly:
        print(f"   ✅ 未发现异常高水位数据")
    
    # 5. 总结
    print(f"\n📊 文件生成总结:")
    total_files = len(list(output_base.rglob('*.*')))
    total_size = sum(f.stat().st_size for f in output_base.rglob('*.*') if f.is_file())
    
    print(f"   总文件数: {total_files}")
    print(f"   总大小: {total_size:,} bytes ({total_size/1024/1024:.1f} MB)")
    
    return total_files > 0

if __name__ == "__main__":
    check_file_status()