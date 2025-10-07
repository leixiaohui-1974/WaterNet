#!/usr/bin/env python3
"""
修复所有缩进问题的脚本
"""

def fix_all_indentation():
    file_path = 'E:/OneDrive/Documents/GitHub/WaterNet/waternet/core/unsteady_flow_analyzer.py'
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修复第247行的缩进问题
    content = content.replace(
        '            else:\n                # 其他模型使用通用参数传递方式\n            params.update({',
        '            else:\n                # 其他模型使用通用参数传递方式\n                params.update({'
    )
    
    # 修复第444行的缩进问题
    content = content.replace(
        '                if method_results:\n                for method_id, method_data in method_results.items():',
        '                if method_results:\n                    for method_id, method_data in method_results.items():'
    )
    
    # 修复其他缩进问题
    content = content.replace(
        '                all_water_levels = []\n                \n                for method_id, method_data in method_results.items():',
        '                all_water_levels = []\n                \n                    for method_id, method_data in method_results.items():'
    )
    
    content = content.replace(
        '                if method_results:\n                    outflows = []\n                for method_id, method_data in method_results.items():',
        '                if method_results:\n                    outflows = []\n                        for method_id, method_data in method_results.items():'
    )
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("所有缩进问题修复完成")

if __name__ == "__main__":
    fix_all_indentation()
