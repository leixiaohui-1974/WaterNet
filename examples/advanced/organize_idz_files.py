#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IDZ辨识项目文件整理脚本
将所有相关文件按功能分类整理到不同目录
"""

import os
import shutil
from pathlib import Path

def organize_idz_files():
    """整理IDZ辨识项目文件"""
    
    # 当前目录
    current_dir = Path(".")
    
    # 创建分类目录
    directories = {
        "01_原始仿真": "非恒定流仿真与数据生成",
        "02_数据处理": "时间序列数据处理与可视化", 
        "03_IDZ辨识": "IDZ模型辨识程序（按演进顺序）",
        "04_最终成果": "最终成功版本与核心成果",
        "05_分析报告": "专业分析与报告生成",
        "06_数据文件": "所有CSV数据文件",
        "07_可视化": "图表与可视化文件",
        "08_文档": "技术文档与说明"
    }
    
    # 创建目录
    for dir_name, description in directories.items():
        dir_path = current_dir / dir_name
        dir_path.mkdir(exist_ok=True)
        print(f"创建目录: {dir_name} - {description}")
    
    # 文件分类规则
    file_categories = {
        "01_原始仿真": [
            "unsteady_analysis.py",
            "deep_channel_demo.py",
            "profile_analysis.py"
        ],
        
        "02_数据处理": [
            "create_time_data.py",
            "plot_time_series.py", 
            "supplement_visualization.py",
            "ascii_visualization.py"
        ],
        
        "03_IDZ辨识": [
            "idz_model_identification.py",          # 基础版本
            "improved_idz_identification.py",       # 改进版本
            "refined_idz_analysis.py",              # 精细化版本
            "correct_idz_analysis.py",              # 时间基准纠正
            "simple_idz_analysis.py"                # 简化版本
        ],
        
        "04_最终成果": [
            "exponential_idz_analysis.py",          # ⭐ 最终成功版本
            "final_idz_summary.py",                 # 最终总结
            "指数响应IDZ模型辨识结果.csv",            # 最终结果数据
            "指数响应IDZ模型参数分布总结.png",        # 最终图表
            "上游正阶跃_指数响应IDZ拟合结果.png",
            "上游负阶跃_指数响应IDZ拟合结果.png", 
            "下游水位阶跃_指数响应IDZ拟合结果.png"
        ],
        
        "05_分析报告": [
            "professional_idz_analysis.py",
            "model_comparison_analysis.py",
            "comprehensive_idz_report.py"
        ],
        
        "06_数据文件": [
            "各断面时间序列详细数据.csv",
            "阶跃响应对比数据.csv",
            "IDZ模型参数总结表.csv",
            "IDZ传递函数详细报告.csv",
            "正确IDZ模型辨识结果.csv",
            "3参数IDZ模型辨识结果.csv",
            "精确IDZ模型参数报告.csv",
            "改进IDZ模型辨识报告.csv",
            "IDZ模型辨识报告.csv",
            "原模型与IDZ模型对比报告.csv"
        ],
        
        "07_可视化": [
            "初始稳态水力学参数分布.png",
            "各断面水位流量时间序列响应.png",
            "断面响应详细分析.png",
            "非恒定流阶跃响应汇总分析.png",
            "IDZ模型辨识综合分析总结.png",
            "IDZ模型辨识精度汇总.png"
        ],
        
        "08_文档": [
            "IDZ模型辨识综合分析报告.md",
            "IDZ传递函数总结.txt",
            "IDZ模型辨识项目完整文档.md"
        ]
    }
    
    # 移动文件
    moved_files = []
    for category, files in file_categories.items():
        target_dir = current_dir / category
        for file_name in files:
            source_file = current_dir / file_name
            if source_file.exists():
                target_file = target_dir / file_name
                try:
                    shutil.copy2(source_file, target_file)
                    moved_files.append(f"{file_name} → {category}")
                    print(f"复制: {file_name} → {category}")
                except Exception as e:
                    print(f"错误: 无法复制 {file_name}: {e}")
    
    # 处理其他PNG文件（历史版本）
    png_files = list(current_dir.glob("*.png"))
    historical_png = []
    for png_file in png_files:
        if png_file.name not in [f for files in file_categories.values() for f in files]:
            historical_png.append(png_file.name)
    
    if historical_png:
        historical_dir = current_dir / "09_历史版本图表"
        historical_dir.mkdir(exist_ok=True)
        for png_file in historical_png:
            source = current_dir / png_file
            target = historical_dir / png_file
            try:
                shutil.copy2(source, target)
                moved_files.append(f"{png_file} → 09_历史版本图表")
                print(f"复制: {png_file} → 09_历史版本图表")
            except Exception as e:
                print(f"错误: 无法复制 {png_file}: {e}")
    
    # 生成整理报告
    create_organization_report(directories, moved_files)
    
    print(f"\n✅ 文件整理完成！")
    print(f"共移动 {len(moved_files)} 个文件")
    print(f"创建 {len(directories)} 个分类目录")

def create_organization_report(directories, moved_files):
    """生成整理报告"""
    
    report_content = f"""# IDZ辨识项目文件整理报告

## 整理概况
- 整理时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- 分类目录: {len(directories)} 个
- 整理文件: {len(moved_files)} 个

## 目录结构

"""
    
    for dir_name, description in directories.items():
        report_content += f"### {dir_name}\n**说明**: {description}\n\n"
    
    report_content += "## 文件分布\n\n"
    
    current_category = ""
    for file_movement in moved_files:
        file_name, category = file_movement.split(" → ")
        if category != current_category:
            report_content += f"\n### {category}\n"
            current_category = category
        report_content += f"- {file_name}\n"
    
    report_content += f"""

## 使用建议

### 新用户入门
1. 查看 `08_文档/IDZ模型辨识项目完整文档.md`
2. 运行 `04_最终成果/exponential_idz_analysis.py`
3. 查看 `04_最终成果/` 目录下的结果文件

### 深入研究
1. 了解演进过程: 查看 `03_IDZ辨识/` 目录下的程序
2. 分析数据: 查看 `06_数据文件/` 目录
3. 对比结果: 查看 `07_可视化/` 和 `09_历史版本图表/`

### 工程应用
1. 使用最终成果: `04_最终成果/指数响应IDZ模型辨识结果.csv`
2. 参考传递函数: `08_文档/IDZ传递函数总结.txt`
3. 了解应用价值: `08_文档/IDZ模型辨识综合分析报告.md`

---
*本报告由文件整理脚本自动生成*
"""
    
    with open("IDZ项目文件整理报告.md", "w", encoding="utf-8") as f:
        f.write(report_content)
    
    print("生成整理报告: IDZ项目文件整理报告.md")

if __name__ == "__main__":
    from datetime import datetime
    
    print("=== IDZ辨识项目文件整理 ===")
    print("将按功能分类整理所有相关文件...")
    
    organize_idz_files()