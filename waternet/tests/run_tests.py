"""
测试运行器和配置

提供便捷的测试运行和验证功能。

Author: WaterNet Development Team
Date: 2024-10-03
"""

import subprocess
import sys
import os


def run_all_tests():
    """运行所有测试"""
    print("开始运行WaterNet测试套件...")
    
    try:
        # 运行pytest
        result = subprocess.run([
            sys.executable, '-m', 'pytest', 
            'waternet/tests/', 
            '-v', '--tb=short'
        ], capture_output=True, text=True)
        
        print("测试输出:")
        print(result.stdout)
        
        if result.stderr:
            print("错误信息:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("✅ 所有测试通过!")
        else:
            print(f"❌ 测试失败，退出代码: {result.returncode}")
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"运行测试时发生错误: {e}")
        return False


def run_coverage_test():
    """运行覆盖率测试"""
    print("开始运行覆盖率测试...")
    
    try:
        result = subprocess.run([
            sys.executable, '-m', 'pytest',
            'waternet/tests/',
            '--cov=waternet',
            '--cov-report=term-missing',
            '--cov-report=html'
        ], capture_output=True, text=True)
        
        print(result.stdout)
        
        if result.returncode == 0:
            print("✅ 覆盖率测试完成!")
            print("📊 详细报告已生成到htmlcov/目录")
        else:
            print("❌ 覆盖率测试失败")
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"运行覆盖率测试时发生错误: {e}")
        return False


if __name__ == "__main__":
    # 设置工作目录
    os.chdir('/data/workspace/WaterNet')
    
    # 运行基础测试
    success = run_all_tests()
    
    if success:
        print("\n" + "="*50)
        # 运行覆盖率测试
        run_coverage_test()