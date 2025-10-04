#!/usr/bin/env python3
"""
WaterNet 快速更新启动器

提供简单易用的命令行接口来运行自动化更新系统
支持多种预设配置和自定义选项
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from scripts.auto_update_system import AutoUpdateSystem, UpdateConfig
except ImportError as e:
    print(f"错误：无法导入自动化更新系统模块: {e}")
    print("请确保您在正确的项目目录中")
    sys.exit(1)


class QuickUpdateLauncher:
    """快速更新启动器"""
    
    def __init__(self):
        self.project_root = project_root
        self.configs = {
            'minimal': UpdateConfig.minimal(),
            'safe': UpdateConfig.safe(),
            'development': UpdateConfig.development(),
            'production': UpdateConfig.production()
        }
    
    def run_update(self, config_name: str = 'safe', **kwargs) -> Dict[str, Any]:
        """运行更新"""
        print(f"🚀 启动WaterNet自动化更新系统")
        print(f"📋 使用配置: {config_name}")
        print(f"📁 项目路径: {self.project_root}")
        print("-" * 60)
        
        # 获取配置
        if config_name in self.configs:
            config = self.configs[config_name]
        else:
            print(f"❌ 未知配置: {config_name}")
            print(f"可用配置: {list(self.configs.keys())}")
            return {'status': 'failed', 'error': 'invalid_config'}
        
        # 应用自定义选项
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
                print(f"🔧 自定义选项: {key} = {value}")
        
        try:
            # 创建更新系统
            updater = AutoUpdateSystem(config=config, project_root=str(self.project_root))
            
            # 运行更新
            result = updater.run_full_update()
            
            print("-" * 60)
            print(f"✅ 更新完成: {result['status']}")
            
            return result
            
        except Exception as e:
            print(f"❌ 更新失败: {e}")
            return {'status': 'failed', 'error': str(e)}
    
    def run_deps_only_update(self) -> Dict[str, Any]:
        """仅更新依赖"""
        print("🔄 仅更新Python依赖包...")
        return self.run_update('minimal', create_backup=False)
    
    def run_test_only(self) -> Dict[str, Any]:
        """仅运行测试"""
        print("🧪 仅运行系统测试...")
        config = UpdateConfig(
            update_dependencies=False,
            update_code=False,
            run_tests=True,
            run_performance_tests=True,
            create_backup=False
        )
        updater = AutoUpdateSystem(config=config, project_root=str(self.project_root))
        return updater.run_full_update()
    
    def show_status(self) -> Dict[str, Any]:
        """显示系统状态"""
        print("📊 WaterNet 系统状态检查")
        print("-" * 40)
        
        status = {}
        
        # 检查Python环境
        try:
            import sys
            status['python_version'] = sys.version.split()[0]
            print(f"🐍 Python版本: {status['python_version']}")
        except Exception as e:
            status['python_error'] = str(e)
            print(f"❌ Python检查失败: {e}")
        
        # 检查WaterNet模块
        try:
            import waternet
            status['waternet_version'] = getattr(waternet, '__version__', 'unknown')
            print(f"💧 WaterNet版本: {status['waternet_version']}")
        except ImportError as e:
            status['waternet_error'] = str(e)
            print(f"❌ WaterNet模块不可用: {e}")
        
        # 检查核心依赖
        deps = ['numpy', 'pandas', 'matplotlib', 'scipy']
        status['dependencies'] = {}
        
        for dep in deps:
            try:
                module = __import__(dep)
                version = getattr(module, '__version__', 'unknown')
                status['dependencies'][dep] = version
                print(f"📦 {dep}: {version}")
            except ImportError:
                status['dependencies'][dep] = 'not_installed'
                print(f"❌ {dep}: 未安装")
        
        # 检查示例文件
        example_dir = self.project_root / 'examples' / 'interval_optimization'
        status['examples'] = {}
        
        example_files = [
            'application_examples.py',
            'correct_workflow_comparison.py'
        ]
        
        for file_name in example_files:
            file_path = example_dir / file_name
            status['examples'][file_name] = file_path.exists()
            status_icon = "✅" if file_path.exists() else "❌"
            print(f"{status_icon} 示例文件 {file_name}: {'存在' if file_path.exists() else '缺失'}")
        
        # 检查最近的更新报告
        reports_dir = self.project_root / 'reports'
        if reports_dir.exists():
            reports = list(reports_dir.glob('update_report_*.json'))
            if reports:
                latest_report = max(reports, key=lambda x: x.stat().st_mtime)
                try:
                    with open(latest_report, 'r', encoding='utf-8') as f:
                        report_data = json.load(f)
                    
                    status['last_update'] = {
                        'time': report_data.get('start_time', 'unknown'),
                        'status': report_data.get('status', 'unknown'),
                        'file': str(latest_report)
                    }
                    
                    print(f"📄 最近更新: {report_data.get('start_time', 'unknown')} - {report_data.get('status', 'unknown')}")
                except Exception as e:
                    print(f"⚠️  无法读取更新报告: {e}")
        
        print("-" * 40)
        status['status'] = 'success'  # 明确设置成功状态
        return status
    
    def rollback_to_latest(self) -> Dict[str, Any]:
        """回滚到最新备份"""
        print("🔄 回滚到最新备份...")
        
        backup_dir = self.project_root / 'backups'
        if not backup_dir.exists():
            print("❌ 没有找到备份目录")
            return {'status': 'failed', 'error': 'no_backups'}
        
        # 查找最新备份
        backups = list(backup_dir.glob('backup_*'))
        if not backups:
            print("❌ 没有找到任何备份")
            return {'status': 'failed', 'error': 'no_backups'}
        
        latest_backup = max(backups, key=lambda x: x.stat().st_mtime)
        print(f"📦 找到最新备份: {latest_backup.name}")
        
        try:
            # 创建临时配置用于回滚
            config = UpdateConfig(
                update_dependencies=False,
                update_code=False,
                run_tests=False,
                run_performance_tests=False,
                create_backup=False
            )
            
            updater = AutoUpdateSystem(config=config, project_root=str(self.project_root))
            updater.backup_path = latest_backup
            updater._execute_rollback()
            
            print("✅ 回滚完成")
            return {'status': 'success', 'backup_used': str(latest_backup)}
            
        except Exception as e:
            print(f"❌ 回滚失败: {e}")
            return {'status': 'failed', 'error': str(e)}


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='WaterNet 快速更新启动器')
    
    parser.add_argument('--config', '-c', 
                       choices=['minimal', 'safe', 'development', 'production'],
                       default='safe',
                       help='使用的更新配置 (默认: safe)')
    
    parser.add_argument('--status', '-s', action='store_true',
                       help='显示系统状态')
    
    parser.add_argument('--deps-only', action='store_true',
                       help='仅更新依赖包')
    
    parser.add_argument('--test-only', action='store_true',
                       help='仅运行测试')
    
    parser.add_argument('--rollback', action='store_true',
                       help='回滚到最新备份')
    
    parser.add_argument('--no-backup', action='store_true',
                       help='跳过备份创建')
    
    parser.add_argument('--no-tests', action='store_true',
                       help='跳过测试运行')
    
    parser.add_argument('--force', action='store_true',
                       help='强制重新安装依赖')
    
    args = parser.parse_args()
    
    launcher = QuickUpdateLauncher()
    
    try:
        if args.status:
            result = launcher.show_status()
        elif args.deps_only:
            result = launcher.run_deps_only_update()
        elif args.test_only:
            result = launcher.run_test_only()
        elif args.rollback:
            result = launcher.rollback_to_latest()
        else:
            # 构建自定义选项
            kwargs = {}
            if args.no_backup:
                kwargs['create_backup'] = False
            if args.no_tests:
                kwargs['run_tests'] = False
                kwargs['run_performance_tests'] = False
            if args.force:
                kwargs['force_reinstall'] = True
            
            result = launcher.run_update(args.config, **kwargs)
        
        # 输出结果摘要
        if result and result.get('status') == 'success':
            print("\n🎉 操作成功完成！")
            sys.exit(0)
        else:
            print(f"\n❌ 操作失败: {result.get('error', 'unknown')}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️  操作被用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 发生未预期的错误: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()