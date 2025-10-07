#!/usr/bin/env python3
"""
修复缩进问题的脚本
"""

def fix_indentation():
    file_path = '../../waternet/core/unsteady_flow_analyzer.py'
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    fixed_lines = []
    for i, line in enumerate(lines):
        # 修复第247行的缩进问题
        if i == 246:  # else行
            fixed_lines.append(line)
        elif i == 247:  # params.update行
            fixed_lines.append('                params.update({\n')
        elif i == 248:  # 'dt'行
            fixed_lines.append("                    'dt': dt,  # 修复: 使用正确的参数名\n")
        elif i == 249:  # 'initial_V'行
            fixed_lines.append("                    'initial_V': initial_V,\n")
        elif i == 250:  # 'V_to_H_func'行
            fixed_lines.append("                    'V_to_H_func': V_to_H_func,\n")
        elif i == 251:  # 'H_to_Q_func'行
            fixed_lines.append("                    'H_to_Q_func': H_to_Q_func\n")
        elif i == 252:  # })行
            fixed_lines.append('                })\n')
        elif i == 253:  # model行
            fixed_lines.append('                model = model_class(**params)\n')
        else:
            fixed_lines.append(line)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)
    
    print("缩进修复完成")

if __name__ == "__main__":
    fix_indentation()
