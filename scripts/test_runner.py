#!/usr/bin/env python3
"""
WaterNet 统一测试入口脚本

这个脚本提供了一个统一的测试执行入口，支持不同类型的测试运行。

使用方法:
    python scripts/test_runner.py --all                    # 运行所有测试
    python scripts/test_runner.py --unit                   # 只运行单元测试
    python scripts/test_runner.py --integration            # 只运行集成测试
    python scripts/test_runner.py --deep-channel           # 只运行深度测试
    python scripts/test_runner.py --coverage               # 运行测试并生成覆盖率报告
    python scripts/test_runner.py --performance            # 运行性能测试

Author: WaterNet Development Team
Date: 2024-10-03
"""

import os
import sys
import argparse
import subprocess
import time
from pathlib import Path
from typing import List, Optional

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class WaterNetTestRunner:
    """WaterNet测试运行器"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.tests_dir = self.project_root / "tests"
        
    def run_unit_tests(self, verbose: bool = True) -> int:
        """运行单元测试"""
        print("🧪 运行单元测试...")
        
        cmd = [
            sys.executable, "-m", "pytest",
            str(self.tests_dir / "unit"),
            "-v" if verbose else "-q",
            "--tb=short"
        ]
        
        return subprocess.call(cmd)
    
    def run_integration_tests(self, verbose: bool = True) -> int:
        """运行集成测试"""
        print("🔗 运行集成测试...")
        
        cmd = [
            sys.executable, "-m", "pytest", 
            str(self.tests_dir / "integration"),
            "-v" if verbose else "-q",
            "--tb=short"
        ]
        
        return subprocess.call(cmd)
    
    def run_deep_channel_tests(self, verbose: bool = True) -> int:
        """运行深度通道测试"""
        print("🌊 运行深度通道测试...")
        
        cmd = [
            sys.executable, "-m", "pytest",
            str(self.tests_dir / "deep_channel"),
            "-v" if verbose else "-q",
            "--tb=short",
            "-x"  # 遇到失败时停止
        ]
        
        return subprocess.call(cmd)
    
    def run_performance_tests(self, verbose: bool = True) -> int:
        """运行性能测试"""
        print("⚡ 运行性能测试...")
        
        cmd = [
            sys.executable, "-m", "pytest",
            str(self.tests_dir),
            "-v" if verbose else "-q",
            "-m", "slow",
            "--tb=short"
        ]
        
        return subprocess.call(cmd)
    
    def run_with_coverage(self, test_dirs: Optional[List[str]] = None) -> int:
        """运行测试并生成覆盖率报告"""
        print("📊 运行测试并生成覆盖率报告...")
        
        if test_dirs is None:
            test_dirs = [str(self.tests_dir)]
        
        cmd = [
            sys.executable, "-m", "pytest",
            *test_dirs,
            "--cov=waternet",
            "--cov-report=html",
            "--cov-report=term-missing",
            "--cov-report=xml",
            "-v"
        ]
        
        result = subprocess.call(cmd)
        
        if result == 0:
            print("✅ 覆盖率报告已生成在 htmlcov/ 目录")
        
        return result
    
    def run_all_tests(self, verbose: bool = True) -> int:
        """运行所有测试"""
        print("🚀 运行所有测试...")
        
        start_time = time.time()
        
        # 运行单元测试
        result = self.run_unit_tests(verbose)
        if result != 0:
            print("❌ 单元测试失败")
            return result
        
        # 运行集成测试
        result = self.run_integration_tests(verbose)
        if result != 0:
            print("❌ 集成测试失败")
            return result
        
        # 运行深度测试（可选，因为比较慢）
        print("\n🤔 是否运行深度通道测试？(这可能需要较长时间)")
        response = input("输入 'y' 运行深度测试，或按Enter跳过: ")
        if response.lower() == 'y':
            result = self.run_deep_channel_tests(verbose)
            if result != 0:
                print("❌ 深度通道测试失败")
                return result
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n✅ 所有测试完成！总耗时: {duration:.1f}秒")
        return 0
    
    def list_available_tests(self):
        """列出可用的测试"""
        print("📋 可用的测试套件:")
        print(f"  单元测试:     {self.tests_dir / 'unit'}")
        print(f"  集成测试:     {self.tests_dir / 'integration'}")
        print(f"  深度通道测试: {self.tests_dir / 'deep_channel'}")
        print(f"  测试固件:     {self.tests_dir / 'fixtures'}")
        
        # 统计测试文件数量
        unit_files = list((self.tests_dir / "unit").glob("test_*.py"))
        integration_files = list((self.tests_dir / "integration").glob("test_*.py"))
        deep_files = list((self.tests_dir / "deep_channel").glob("test_*.py"))
        
        print(f"\n📊 测试文件统计:")
        print(f"  单元测试文件: {len(unit_files)}")
        print(f"  集成测试文件: {len(integration_files)}")
        print(f"  深度测试文件: {len(deep_files)}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="WaterNet 统一测试运行器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --all                    运行所有测试
  %(prog)s --unit --coverage        运行单元测试并生成覆盖率报告
  %(prog)s --integration            运行集成测试
  %(prog)s --deep-channel           运行深度通道测试
  %(prog)s --list                   列出可用测试
        """
    )
    
    parser.add_argument("--all", action="store_true", help="运行所有测试")
    parser.add_argument("--unit", action="store_true", help="运行单元测试")
    parser.add_argument("--integration", action="store_true", help="运行集成测试")
    parser.add_argument("--deep-channel", action="store_true", help="运行深度通道测试")
    parser.add_argument("--performance", action="store_true", help="运行性能测试")
    parser.add_argument("--coverage", action="store_true", help="生成覆盖率报告")
    parser.add_argument("--list", action="store_true", help="列出可用测试")
    parser.add_argument("--quiet", "-q", action="store_true", help="减少输出信息")
    
    args = parser.parse_args()
    
    runner = WaterNetTestRunner()
    verbose = not args.quiet
    
    if args.list:
        runner.list_available_tests()
        return 0
    
    if args.all:
        if args.coverage:
            return runner.run_with_coverage()
        else:
            return runner.run_all_tests(verbose)
    
    result = 0
    
    if args.unit:
        if args.coverage:
            result = runner.run_with_coverage([str(runner.tests_dir / "unit")])
        else:
            result = runner.run_unit_tests(verbose)
    
    if args.integration and result == 0:
        if args.coverage:
            result = runner.run_with_coverage([str(runner.tests_dir / "integration")])
        else:
            result = runner.run_integration_tests(verbose)
    
    if args.deep_channel and result == 0:
        result = runner.run_deep_channel_tests(verbose)
    
    if args.performance and result == 0:
        result = runner.run_performance_tests(verbose)
    
    # 如果没有指定任何测试类型，显示帮助
    if not any([args.all, args.unit, args.integration, args.deep_channel, 
               args.performance, args.list]):
        parser.print_help()
        return 1
    
    return result


if __name__ == "__main__":
    sys.exit(main())