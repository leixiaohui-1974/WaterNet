#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
运行横断面图功能演示的快捷脚本

使用方法:
python run_cross_section_demo.py
"""

import sys
from pathlib import Path
import subprocess

def main():
    """运行横断面图功能演示"""
    project_root = Path(__file__).parent
    demo_dir = project_root / 'examples' / 'cross_section_demo'
    demo_script = demo_dir / 'cross_section_demo.py'
    
    print("🌊 启动横断面图功能演示")
    print("=" * 60)
    print(f"📍 项目根目录: {project_root}")
    print(f"📂 演示目录: {demo_dir}")
    print(f"🐍 演示脚本: {demo_script}")
    
    if not demo_script.exists():
        print(f"❌ 演示脚本不存在: {demo_script}")
        return
    
    print("\n🚀 开始运行演示...")
    try:
        # 切换到演示目录并运行脚本
        import os
        original_cwd = os.getcwd()
        os.chdir(demo_dir)
        
        # 运行演示脚本
        result = subprocess.run([sys.executable, 'cross_section_demo.py'], 
                              capture_output=True, text=True, encoding='utf-8')
        
        print(result.stdout)
        if result.stderr:
            print("警告信息:")
            print(result.stderr)
        
        # 运行结果展示脚本
        if (demo_dir / 'show_results.py').exists():
            print("\n" + "="*60)
            print("📊 展示详细结果...")
            show_result = subprocess.run([sys.executable, 'show_results.py'], 
                                       capture_output=True, text=True, encoding='utf-8')
            print(show_result.stdout)
        
        # 恢复工作目录
        os.chdir(original_cwd)
        
        print("\n✅ 演示运行完成！")
        print(f"🔍 请查看结果目录: {demo_dir / 'outputs'}")
        
    except Exception as e:
        print(f"❌ 运行演示时出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()