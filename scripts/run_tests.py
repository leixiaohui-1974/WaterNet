"""
WaterNet 统一测试运行脚本

提供统一的测试入口，支持不同级别和类型的测试。
"""

import sys
import os
import argparse
import subprocess
import time
from pathlib import Path


# 解决Windows终端编码问题
try:
    # 设置UTF-8输出
    if sys.stdout.encoding != 'utf-8':
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
except Exception:
    # 如果无法设置，使用简单的输出
    pass


def safe_print(text):
    """安全打印函数，处理编码问题"""
    try:
        print(text)
    except UnicodeEncodeError:
        # 如果出现编码错误，替换为简单字符
        simple_text = text
        simple_text = simple_text.replace('✅', '[OK]')
        simple_text = simple_text.replace('❌', '[ERROR]')
        simple_text = simple_text.replace('⚠️', '[WARNING]')
        simple_text = simple_text.replace('🚀', '[START]')
        simple_text = simple_text.replace('🔍', '[SEARCH]')
        simple_text = simple_text.replace('🔧', '[TOOL]')
        simple_text = simple_text.replace('📊', '[INFO]')
        simple_text = simple_text.replace('🧪', '[TEST]')
        simple_text = simple_text.replace('🔗', '[LINK]')
        simple_text = simple_text.replace('⚡', '[SPEED]')
        simple_text = simple_text.replace('📊', '[CHART]')
        try:
            print(simple_text)
        except UnicodeEncodeError:
            # 如果还是有问题，使用ASCII
            ascii_text = simple_text.encode('ascii', 'replace').decode('ascii')
            print(ascii_text)


def get_project_root():
    """获取项目根目录"""
    current = Path(__file__).parent
    while current.parent != current:
        if (current / 'waternet').exists():
            return current
        current = current.parent
    return Path.cwd()


def run_command(cmd, capture_output=True):
    """运行命令并返回结果"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=capture_output, 
            text=True, cwd=get_project_root()
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)


def run_unit_tests(verbose=False, coverage=False):
    """运行单元测试"""
    safe_print("🧪 运行单元测试...")
    
    cmd = "python -m pytest tests/unit/ -m unit"
    
    if verbose:
        cmd += " -v"
    if coverage:
        cmd += " --cov=waternet --cov-report=html --cov-report=term"
    
    success, stdout, stderr = run_command(cmd)
    
    if success:
        safe_print("✅ 单元测试通过")
    else:
        safe_print("❌ 单元测试失败")
        if stdout:
            safe_print("STDOUT:", stdout)
        if stderr:
            safe_print("STDERR:", stderr)
    
    return success


def run_integration_tests(verbose=False):
    """运行集成测试"""
    safe_print("🔗 运行集成测试...")
    
    cmd = "python -m pytest tests/integration/ -m integration"
    
    if verbose:
        cmd += " -v"
    
    success, stdout, stderr = run_command(cmd)
    
    if success:
        safe_print("✅ 集成测试通过")
    else:
        safe_print("❌ 集成测试失败")
        if stdout:
            safe_print("STDOUT:", stdout)
        if stderr:
            safe_print("STDERR:", stderr)
    
    return success


def run_performance_tests(verbose=False):
    """运行性能测试"""
    safe_print("⚡ 运行性能测试...")
    
    cmd = "python -m pytest tests/ -m performance"
    
    if verbose:
        cmd += " -v"
    
    success, stdout, stderr = run_command(cmd)
    
    if success:
        safe_print("✅ 性能测试通过")
    else:
        safe_print("❌ 性能测试失败")
        if stdout:
            safe_print("STDOUT:", stdout)
        if stderr:
            safe_print("STDERR:", stderr)
    
    return success


def run_all_tests(verbose=False, coverage=False, include_slow=False):
    """运行所有测试"""
    safe_print("🚀 运行全部测试...")
    
    cmd = "python -m pytest tests/"
    
    if not include_slow:
        cmd += " -m 'not slow'"
    
    if verbose:
        cmd += " -v"
    if coverage:
        cmd += " --cov=waternet --cov-report=html --cov-report=term"
    
    success, stdout, stderr = run_command(cmd)
    
    if success:
        safe_print("✅ 全部测试通过")
    else:
        safe_print("❌ 部分测试失败")
        if stdout:
            safe_print("STDOUT:", stdout)
        if stderr:
            safe_print("STDERR:", stderr)
    
    return success


def check_dependencies():
    """检查测试依赖"""
    safe_print("🔍 检查测试依赖...")
    
    required_packages = ['pytest', 'numpy', 'pandas', 'scipy', 'matplotlib']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        safe_print(f"❌ 缺少依赖包: {', '.join(missing_packages)}")
        safe_print("请运行: pip install -r requirements.txt")
        return False
    else:
        safe_print("✅ 所有依赖包已安装")
        return True


def generate_test_report():
    """生成测试报告"""
    safe_print("📊 生成测试报告...")
    
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    report_file = f"test_report_{timestamp}.html"
    
    cmd = f"python -m pytest tests/ --html={report_file} --self-contained-html"
    
    success, stdout, stderr = run_command(cmd)
    
    if success:
        safe_print(f"✅ 测试报告已生成: {report_file}")
    else:
        safe_print("❌ 测试报告生成失败")
    
    return success


def validate_installation():
    """验证安装"""
    safe_print("🔧 验证WaterNet安装...")
    
    try:
        # 尝试导入核心模块
        from waternet.models import SaintVenantModel, MuskingumModel
        from waternet.models import SolverFactory
        safe_print("✅ 核心模块导入成功")
        
        # 简单功能测试
        sections = [
            {
                'mileage': 0.0, 'elevation': 100.0, 'roughness': 0.025,
                'area_func': lambda h: max(0, h - 100) * 10,
                'top_width_func': lambda h: 10 if h > 100 else 0
            },
            {
                'mileage': 1000.0, 'elevation': 99.0, 'roughness': 0.025,
                'area_func': lambda h: max(0, h - 99) * 10,
                'top_width_func': lambda h: 10 if h > 99 else 0
            }
        ]
        
        model = SaintVenantModel("TestModel", "up", "down", sections)
        result = model.compute_steady_state(10.0, 99.5)
        
        if 'total_volume' in result and result['total_volume'] > 0:
            safe_print("✅ 基本功能测试通过")
            return True
        else:
            safe_print("❌ 基本功能测试失败")
            return False
            
    except Exception as e:
        safe_print(f"❌ 安装验证失败: {e}")
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='WaterNet 测试运行器')
    parser.add_argument('test_type', nargs='?', default='all',
                        choices=['unit', 'integration', 'performance', 'all', 'validate'],
                        help='测试类型')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='详细输出')
    parser.add_argument('--coverage', action='store_true',
                        help='生成覆盖率报告')
    parser.add_argument('--include-slow', action='store_true',
                        help='包含慢速测试')
    parser.add_argument('--report', action='store_true',
                        help='生成HTML测试报告')
    parser.add_argument('--check-deps', action='store_true',
                        help='检查测试依赖')
    
    args = parser.parse_args()
    
    # 检查依赖
    if args.check_deps:
        if not check_dependencies():
            sys.exit(1)
        return
    
    success = True
    
    if args.test_type == 'unit':
        success = run_unit_tests(args.verbose, args.coverage)
    elif args.test_type == 'integration':
        success = run_integration_tests(args.verbose)
    elif args.test_type == 'performance':
        success = run_performance_tests(args.verbose)
    elif args.test_type == 'validate':
        success = validate_installation()
    elif args.test_type == 'all':
        success = run_all_tests(args.verbose, args.coverage, args.include_slow)
    
    if args.report:
        generate_test_report()
    
    if success:
        safe_print("🎉 测试完成!")
    else:
        safe_print("💥 部分测试失败")
        sys.exit(1)


if __name__ == "__main__":
    main()