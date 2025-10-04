"""
WaterNet 安装验证脚本

验证WaterNet是否正确安装并可以正常工作。

Author: WaterNet Development Team
Date: 2024-10-03
"""

import sys
import os
import importlib
import subprocess
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
        try:
            print(simple_text)
        except UnicodeEncodeError:
            # 如果还是有问题，使用ASCII
            ascii_text = simple_text.encode('ascii', 'replace').decode('ascii')
            print(ascii_text)


def check_python_version():
    """检查Python版本"""
    safe_print("检查Python版本...")
    
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        safe_print(f"❌ Python版本太低: {version.major}.{version.minor}")
        safe_print("   WaterNet需要Python 3.8或更高版本")
        return False
    else:
        safe_print(f"✅ Python版本: {version.major}.{version.minor}.{version.micro}")
        return True


def check_dependencies():
    """检查依赖包"""
    safe_print("\n检查依赖包...")
    
    required_packages = {
        'numpy': '1.19.0',
        'scipy': '1.7.0',
        'pandas': '1.3.0',
        'matplotlib': '3.3.0',
        'yaml': '5.4.0'
    }
    
    missing_packages = []
    
    for package, min_version in required_packages.items():
        try:
            if package == 'yaml':
                import yaml
                module = yaml
                package_name = 'PyYAML'
            else:
                module = importlib.import_module(package)
                package_name = package
            
            # 检查版本
            if hasattr(module, '__version__'):
                version = module.__version__
                safe_print(f"✅ {package_name}: {version}")
            else:
                safe_print(f"✅ {package_name}: 已安装")
                
        except ImportError:
            safe_print(f"❌ {package_name}: 未安装")
            missing_packages.append(package_name)
    
    if missing_packages:
        safe_print(f"\n缺少以下依赖包: {', '.join(missing_packages)}")
        safe_print("请运行: pip install -r requirements.txt")
        return False
    
    return True


def check_waternet_import():
    """检查WaterNet导入"""
    safe_print("\n检查WaterNet核心模块...")
    
    try:
        # 添加项目路径
        project_root = Path(__file__).parent.parent
        sys.path.insert(0, str(project_root))
        
        # 测试核心导入
        from waternet.models import SaintVenantModel, MuskingumModel
        from waternet.config import ConfigManager
        safe_print("✅ 核心模块导入成功")
        
        # 测试可选模块
        try:
            from waternet.parameter_estimation.estimator import ParameterEstimator
            safe_print("✅ 参数估计模块可用")
        except ImportError:
            safe_print("⚠️  参数估计模块不可用（可选）")
        
        try:
            from waternet.coordination.twinning_harness import SynchronizedTwinningHarness
            safe_print("✅ 数字孪生模块可用")
        except ImportError:
            safe_print("⚠️  数字孪生模块不可用（可选）")
        
        return True
        
    except ImportError as e:
        safe_print(f"❌ WaterNet导入失败: {e}")
        return False


def test_basic_functionality():
    """测试基本功能"""
    safe_print("\n测试基本功能...")
    
    try:
        from waternet.models import SaintVenantModel, MuskingumModel
        from waternet.config import ConfigManager
        
        # 1. 测试圣维南模型
        safe_print("  测试圣维南模型...")
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
        
        sv_model = SaintVenantModel("TestModel", "up", "down", sections)
        result = sv_model.compute_steady_state(10.0, 99.5)
        
        if 'total_volume' in result and result['total_volume'] > 0:
            safe_print("  ✅ 圣维南模型恒定流计算正常")
        else:
            safe_print("  ❌ 圣维南模型计算结果异常")
            return False
        
        # 2. 测试马斯京干模型
        safe_print("  测试马斯京干模型...")
        V_to_H = lambda V: 99.0 + V * 1e-4
        H_to_Q = lambda H: 25.0 * max(0, H - 99.0) ** 1.5
        
        musk_model = MuskingumModel(
            dt=60.0, K=3600.0, x=0.2, initial_V=10000.0,
            V_to_H_func=V_to_H, H_to_Q_func=H_to_Q
        )
        
        Q_series = [8.0, 10.0, 12.0, 10.0, 8.0]
        results = musk_model.run_simulation(Q_series)
        
        if len(results) == len(Q_series) + 1 and all(results['Q_out'] >= 0):
            safe_print("  ✅ 马斯京干模型仿真正常")
        else:
            safe_print("  ❌ 马斯京干模型仿真异常")
            return False
        
        # 3. 测试配置管理器
        safe_print("  测试配置管理器...")
        config_manager = ConfigManager()
        
        # 创建临时配置
        test_config = {
            'name': 'test_channel',
            'sections': [
                {
                    'mileage': 0.0,
                    'elevation': 100.0,
                    'roughness': 0.025,
                    'cross_section': {'type': 'rectangular', 'width': 10.0}
                },
                {
                    'mileage': 1000.0,
                    'elevation': 99.0,
                    'roughness': 0.025,
                    'cross_section': {'type': 'rectangular', 'width': 10.0}
                }
            ]
        }
        
        # 验证配置
        if config_manager.validate_config(test_config, 'channel'):
            safe_print("  ✅ 配置管理器验证正常")
        else:
            safe_print("  ❌ 配置管理器验证失败")
            return False
        
        safe_print("✅ 所有基本功能测试通过")
        return True
        
    except Exception as e:
        safe_print(f"❌ 功能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_example_scripts():
    """测试示例脚本"""
    safe_print("\n检查示例脚本...")
    
    project_root = Path(__file__).parent.parent
    examples_dir = project_root / 'examples'
    
    if not examples_dir.exists():
        safe_print("⚠️  examples目录不存在")
        return True
    
    # 检查示例文件
    example_files = [
        'basic_usage.py',
        'parameter_estimation.py'
    ]
    
    for example_file in example_files:
        example_path = examples_dir / example_file
        if example_path.exists():
            safe_print(f"✅ 发现示例: {example_file}")
        else:
            safe_print(f"⚠️  缺少示例: {example_file}")
    
    return True


def test_configuration_files():
    """测试配置文件"""
    safe_print("\n检查配置文件...")
    
    project_root = Path(__file__).parent.parent
    configs_dir = project_root / 'examples' / 'configs'
    
    if not configs_dir.exists():
        safe_print("⚠️  配置目录不存在")
        return True
    
    config_files = [
        'simple_channel.yaml',
        'muskingum_model.yaml',
        'simulation_config.yaml'
    ]
    
    for config_file in config_files:
        config_path = configs_dir / config_file
        if config_path.exists():
            safe_print(f"✅ 发现配置: {config_file}")
            
            # 尝试加载配置
            try:
                import yaml
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                safe_print(f"  ✅ {config_file} 格式正确")
            except Exception as e:
                safe_print(f"  ❌ {config_file} 格式错误: {e}")
        else:
            safe_print(f"⚠️  缺少配置: {config_file}")
    
    return True


def run_quick_test():
    """运行快速测试"""
    safe_print("\n运行快速集成测试...")
    
    try:
        # 运行测试脚本
        project_root = Path(__file__).parent.parent
        test_script = project_root / 'scripts' / 'run_tests.py'
        
        if test_script.exists():
            result = subprocess.run([
                sys.executable, str(test_script), 'validate'
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                safe_print("✅ 快速测试通过")
                return True
            else:
                safe_print("❌ 快速测试失败")
                safe_print(f"错误信息: {result.stderr}")
                return False
        else:
            safe_print("⚠️  未找到测试脚本")
            return True
            
    except subprocess.TimeoutExpired:
        safe_print("❌ 测试超时")
        return False
    except Exception as e:
        safe_print(f"❌ 测试执行失败: {e}")
        return False


def main():
    """主函数"""
    safe_print("🚀 WaterNet 安装验证开始")
    safe_print("=" * 60)
    
    # 执行各项检查
    checks = [
        ("Python版本", check_python_version),
        ("依赖包", check_dependencies),
        ("模块导入", check_waternet_import),
        ("基本功能", test_basic_functionality),
        ("示例脚本", test_example_scripts),
        ("配置文件", test_configuration_files),
        ("快速测试", run_quick_test),
    ]
    
    results = {}
    for check_name, check_func in checks:
        try:
            results[check_name] = check_func()
        except Exception as e:
            safe_print(f"❌ {check_name}检查出现异常: {e}")
            results[check_name] = False
    
    # 输出总结
    safe_print("\n" + "=" * 60)
    safe_print("🔍 WaterNet 安装验证摘要")
    safe_print("=" * 60)
    
    all_passed = True
    for check_name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        safe_print(f"{check_name}: {status}")
        if not passed:
            all_passed = False
    
    safe_print("=" * 60)
    
    if all_passed:
        safe_print("🎉 所有验证通过，WaterNet安装成功！")
        safe_print("\n🚀 现在您可以:")
        safe_print("   - 运行示例程序: python examples/basic_usage.py")
        safe_print("   - 阅读文档了解更多功能")
        safe_print("   - 开始您的建模工作")
    else:
        safe_print("⚠️  存在一些问题，但核心功能可能仍然可用")
        safe_print("\n🔧 建议:")
        safe_print("   - 检查失败的项目并按提示解决")
        safe_print("   - 确保所有依赖包正确安装")
        safe_print("   - 查看错误信息并联系开发团队")
    
    safe_print("=" * 60)
    
    # 返回适当的退出码
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())