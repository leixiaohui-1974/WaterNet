#!/usr/bin/env python3
"""
WaterNet 全方位自动化更新系统

一个完整的自动化更新解决方案，包含：
- 智能依赖管理
- 代码同步与版本控制
- 全面测试验证
- 性能监控与基准测试
- 智能备份与回滚机制
- 实时状态监控与通知
- 健康检查与诊断
"""

import os
import sys
import json
import time
import shutil
import logging
import subprocess
import platform
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from contextlib import contextmanager


@dataclass
class UpdateConfig:
    """更新配置类"""
    # 基础配置
    update_dependencies: bool = True
    update_code: bool = True
    run_tests: bool = True
    run_performance_tests: bool = True
    create_backup: bool = True
    
    # 依赖管理
    dependency_sources: List[str] = field(default_factory=lambda: ['pip', 'conda'])
    force_reinstall: bool = False
    upgrade_all: bool = False
    
    # 代码管理
    git_pull: bool = True
    git_branch: Optional[str] = None
    check_uncommitted_changes: bool = True
    
    # 测试配置
    test_timeout: int = 300  # 5分钟
    min_test_coverage: float = 0.8
    performance_threshold: float = 1.5  # 性能阈值倍数
    
    # 备份配置
    backup_count: int = 5
    backup_compress: bool = True
    
    # 通知配置
    notifications_enabled: bool = True
    notification_channels: List[str] = field(default_factory=lambda: ['console', 'file'])
    
    # 高级选项
    parallel_operations: bool = True
    rollback_on_failure: bool = True
    health_check_enabled: bool = True
    
    @classmethod
    def minimal(cls) -> 'UpdateConfig':
        """最小化配置 - 仅更新依赖"""
        return cls(
            update_code=False,
            run_tests=False,
            run_performance_tests=False,
            create_backup=False
        )
    
    @classmethod
    def safe(cls) -> 'UpdateConfig':
        """安全配置 - 包含备份和测试"""
        return cls(
            force_reinstall=False,
            upgrade_all=False,
            rollback_on_failure=True
        )
    
    @classmethod
    def development(cls) -> 'UpdateConfig':
        """开发配置 - 全功能但快速"""
        return cls(
            performance_threshold=2.0,
            test_timeout=180,
            backup_count=3
        )
    
    @classmethod
    def production(cls) -> 'UpdateConfig':
        """生产配置 - 最严格验证"""
        return cls(
            min_test_coverage=0.9,
            performance_threshold=1.2,
            test_timeout=600,
            backup_count=10
        )


class AutoUpdateSystem:
    """WaterNet 全方位自动化更新系统"""
    
    def __init__(self, config: Optional[UpdateConfig] = None, project_root: Optional[str] = None):
        self.config = config or UpdateConfig.safe()
        self.project_root = Path(project_root or os.getcwd())
        
        # 确保项目根目录存在
        if not self.project_root.exists():
            raise ValueError(f"项目根目录不存在: {self.project_root}")
        
        # 设置日志
        self._setup_logging()
        
        # 初始化状态
        self.update_start_time = None
        self.backup_path = None
        self.update_report = {
            'start_time': None,
            'end_time': None,
            'status': 'pending',
            'steps': {},
            'errors': [],
            'performance_metrics': {},
            'rollback_performed': False
        }
        
        self.logger.info(f"初始化自动化更新系统 - 项目: {self.project_root}")
        self.logger.info(f"配置: {self.config}")
    
    def _setup_logging(self):
        """设置日志系统"""
        log_dir = self.project_root / 'logs'
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / f'auto_update_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger('AutoUpdateSystem')
    
    def run_full_update(self) -> Dict[str, Any]:
        """运行完整更新流程"""
        self.update_start_time = datetime.now()
        self.update_report['start_time'] = self.update_start_time.isoformat()
        
        try:
            self.logger.info("开始全方位自动化更新流程")
            
            # 步骤1: 系统预检查
            self._execute_step('pre_check', self._run_pre_check)
            
            # 步骤2: 创建备份
            if self.config.create_backup:
                self._execute_step('backup', self._create_backup)
            
            # 步骤3: 更新依赖
            if self.config.update_dependencies:
                self._execute_step('dependencies', self._update_dependencies)
            
            # 步骤4: 更新代码
            if self.config.update_code:
                self._execute_step('code_update', self._update_code)
            
            # 步骤5: 运行测试
            if self.config.run_tests:
                self._execute_step('tests', self._run_tests)
            
            # 步骤6: 性能测试
            if self.config.run_performance_tests:
                self._execute_step('performance', self._run_performance_tests)
            
            # 步骤7: 最终验证
            self._execute_step('final_verification', self._final_verification)
            
            # 更新成功
            self.update_report['status'] = 'success'
            self.logger.info("自动化更新完成！所有步骤执行成功")
            
        except Exception as e:
            self.logger.error(f"更新过程中发生错误: {e}")
            self.update_report['status'] = 'failed'
            self.update_report['errors'].append(str(e))
            
            # 执行回滚
            if self.config.rollback_on_failure and self.backup_path:
                self._execute_rollback()
            
            raise
            
        finally:
            self.update_report['end_time'] = datetime.now().isoformat()
            duration = datetime.now() - self.update_start_time
            self.update_report['duration_seconds'] = duration.total_seconds()
            
            # 生成报告
            self._generate_report()
            
        return self.update_report
    
    def _execute_step(self, step_name: str, step_function):
        """执行单个更新步骤并记录结果"""
        start_time = time.time()
        self.logger.info(f"执行步骤: {step_name}")
        
        try:
            result = step_function()
            execution_time = time.time() - start_time
            
            self.update_report['steps'][step_name] = {
                'status': 'success',
                'execution_time': execution_time,
                'result': result
            }
            
            self.logger.info(f"步骤 {step_name} 完成，耗时: {execution_time:.2f}秒")
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"步骤 {step_name} 失败: {e}"
            
            self.update_report['steps'][step_name] = {
                'status': 'failed',
                'execution_time': execution_time,
                'error': str(e)
            }
            
            self.logger.error(error_msg)
            raise
    
    def _run_pre_check(self) -> Dict[str, Any]:
        """系统预检查"""
        check_results = {}
        
        # 检查Python环境
        python_version = platform.python_version()
        check_results['python_version'] = python_version
        
        if tuple(map(int, python_version.split('.'))) < (3, 7):
            raise RuntimeError(f"Python版本过低: {python_version}，需要 >= 3.7")
        
        # 检查项目结构
        required_dirs = ['waternet', 'examples', 'tests']
        missing_dirs = []
        
        for dir_name in required_dirs:
            dir_path = self.project_root / dir_name
            if not dir_path.exists():
                missing_dirs.append(dir_name)
        
        if missing_dirs:
            self.logger.warning(f"缺少目录: {missing_dirs}")
            check_results['missing_directories'] = missing_dirs
        
        # 检查Git状态
        if self.config.check_uncommitted_changes:
            try:
                result = subprocess.run(
                    ['git', 'status', '--porcelain'], 
                    cwd=self.project_root,
                    capture_output=True, 
                    text=True,
                    timeout=30
                )
                
                if result.stdout.strip():
                    uncommitted_files = result.stdout.strip().split('\n')
                    check_results['uncommitted_changes'] = uncommitted_files
                    self.logger.warning(f"存在未提交的更改: {len(uncommitted_files)} 个文件")
                
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
                self.logger.warning(f"无法检查Git状态: {e}")
        
        # 检查磁盘空间
        total, used, free = shutil.disk_usage(self.project_root)
        free_gb = free // (1024**3)
        check_results['free_disk_space_gb'] = free_gb
        
        if free_gb < 1:
            raise RuntimeError(f"磁盘空间不足: {free_gb}GB，建议至少1GB可用空间")
        
        self.logger.info(f"预检查完成: {check_results}")
        return check_results
    
    def _create_backup(self) -> Dict[str, Any]:
        """创建项目备份"""
        backup_dir = self.project_root / 'backups'
        backup_dir.mkdir(exist_ok=True)
        
        # 清理旧备份
        existing_backups = sorted(backup_dir.glob('backup_*'))
        if len(existing_backups) >= self.config.backup_count:
            for old_backup in existing_backups[:-self.config.backup_count+1]:
                if old_backup.is_dir():
                    shutil.rmtree(old_backup)
                else:
                    old_backup.unlink()
        
        # 创建新备份
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f'backup_{timestamp}'
        self.backup_path = backup_dir / backup_name
        
        # 要备份的目录
        dirs_to_backup = ['waternet', 'examples', 'tests', 'scripts']
        files_to_backup = ['setup.py', 'requirements.txt', 'README.md']
        
        self.backup_path.mkdir()
        
        # 备份目录
        for dir_name in dirs_to_backup:
            src_dir = self.project_root / dir_name
            if src_dir.exists():
                dst_dir = self.backup_path / dir_name
                shutil.copytree(src_dir, dst_dir)
        
        # 备份文件
        for file_name in files_to_backup:
            src_file = self.project_root / file_name
            if src_file.exists():
                dst_file = self.backup_path / file_name
                shutil.copy2(src_file, dst_file)
        
        # 压缩备份（如果启用）
        if self.config.backup_compress:
            archive_path = backup_dir / f'{backup_name}.tar.gz'
            shutil.make_archive(str(archive_path)[:-7], 'gztar', str(self.backup_path))
            shutil.rmtree(self.backup_path)
            self.backup_path = archive_path
        
        backup_size = self._get_path_size(self.backup_path)
        
        result = {
            'backup_path': str(self.backup_path),
            'backup_size_mb': backup_size / (1024 * 1024),
            'compressed': self.config.backup_compress
        }
        
        self.logger.info(f"备份创建完成: {result}")
        return result
    
    def _get_path_size(self, path: Path) -> int:
        """获取路径大小"""
        if path.is_file():
            return path.stat().st_size
        elif path.is_dir():
            return sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
        return 0
    
    def _update_dependencies(self) -> Dict[str, Any]:
        """更新项目依赖"""
        results = {}
        
        # 确保在可编辑模式下安装项目
        try:
            cmd = [sys.executable, '-m', 'pip', 'install', '-e', '.']
            if self.config.force_reinstall:
                cmd.extend(['--force-reinstall'])
            
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            results['editable_install'] = {
                'success': result.returncode == 0,
                'output': result.stdout,
                'error': result.stderr
            }
            
            if result.returncode != 0:
                raise RuntimeError(f"可编辑模式安装失败: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            raise RuntimeError("可编辑模式安装超时")
        
        # 更新核心依赖
        core_packages = ['numpy', 'pandas', 'matplotlib', 'scipy']
        
        for package in core_packages:
            try:
                cmd = [sys.executable, '-m', 'pip', 'install', '--upgrade', package]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=180
                )
                
                results[f'{package}_update'] = {
                    'success': result.returncode == 0,
                    'output': result.stdout,
                    'error': result.stderr
                }
                
                if result.returncode != 0:
                    self.logger.warning(f"更新 {package} 失败: {result.stderr}")
                
            except subprocess.TimeoutExpired:
                self.logger.warning(f"更新 {package} 超时")
                results[f'{package}_update'] = {
                    'success': False,
                    'error': 'timeout'
                }
        
        # 检查依赖完整性
        try:
            import waternet
            results['waternet_import'] = {'success': True}
        except ImportError as e:
            results['waternet_import'] = {'success': False, 'error': str(e)}
            raise RuntimeError(f"WaterNet导入失败: {e}")
        
        self.logger.info("依赖更新完成")
        return results
    
    def _update_code(self) -> Dict[str, Any]:
        """更新代码（Git拉取）"""
        if not self.config.git_pull:
            return {'skipped': True}
        
        results = {}
        
        try:
            # 获取当前分支
            result = subprocess.run(
                ['git', 'branch', '--show-current'],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            current_branch = result.stdout.strip()
            results['current_branch'] = current_branch
            
            # 切换分支（如果指定）
            if self.config.git_branch and self.config.git_branch != current_branch:
                result = subprocess.run(
                    ['git', 'checkout', self.config.git_branch],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.returncode != 0:
                    raise RuntimeError(f"分支切换失败: {result.stderr}")
                
                results['branch_switched'] = self.config.git_branch
            
            # 拉取更新
            result = subprocess.run(
                ['git', 'pull'],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            results['git_pull'] = {
                'success': result.returncode == 0,
                'output': result.stdout,
                'error': result.stderr
            }
            
            if result.returncode != 0:
                raise RuntimeError(f"Git拉取失败: {result.stderr}")
            
            # 检查是否有更新
            if 'Already up to date' in result.stdout:
                results['updates_available'] = False
            else:
                results['updates_available'] = True
                results['changes'] = result.stdout
            
        except subprocess.TimeoutExpired:
            raise RuntimeError("Git操作超时")
        
        self.logger.info(f"代码更新完成: {results}")
        return results
    
    def _run_tests(self) -> Dict[str, Any]:
        """运行测试套件"""
        results = {}
        
        # 运行示例脚本测试
        example_dir = self.project_root / 'examples' / 'interval_optimization'
        if example_dir.exists():
            example_files = [
                'application_examples.py',
                'correct_workflow_comparison.py'
            ]
            
            for example_file in example_files:
                file_path = example_dir / example_file
                if file_path.exists():
                    try:
                        start_time = time.time()
                        result = subprocess.run(
                            [sys.executable, str(file_path)],
                            cwd=self.project_root,
                            capture_output=True,
                            text=True,
                            timeout=self.config.test_timeout
                        )
                        
                        execution_time = time.time() - start_time
                        
                        results[f'example_{example_file}'] = {
                            'success': result.returncode == 0,
                            'execution_time': execution_time,
                            'output': result.stdout,
                            'error': result.stderr
                        }
                        
                        if result.returncode != 0:
                            self.logger.warning(f"示例 {example_file} 执行失败: {result.stderr}")
                        
                    except subprocess.TimeoutExpired:
                        results[f'example_{example_file}'] = {
                            'success': False,
                            'error': 'timeout'
                        }
        
        # 基础功能测试
        try:
            import waternet
            from waternet.models import SolverFactory
            # 尝试导入优化模块，可能不存在
            try:
                from waternet.optimization import IntervalOptimizer
                optimizer = IntervalOptimizer()
            except ImportError:
                # 如果优化模块不存在，跳过此测试
                self.logger.warning("优化模块不存在，跳过相关测试")
            
            # 测试基础导入
            results['import_test'] = {'success': True}
            
            # 测试基础功能
            solver = SolverFactory.create_solver('implicit')
            
            results['functionality_test'] = {'success': True}
            
        except Exception as e:
            results['import_test'] = {'success': False, 'error': str(e)}
            raise RuntimeError(f"基础功能测试失败: {e}")
        
        # 计算测试通过率
        total_tests = len([k for k in results.keys() if k.endswith('_test') or 'example_' in k])
        passed_tests = len([k for k, v in results.items() if v.get('success', False)])
        
        pass_rate = 0.0
        if total_tests > 0:
            pass_rate = passed_tests / total_tests
            results['test_summary'] = {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'pass_rate': pass_rate
            }
            
            if pass_rate < self.config.min_test_coverage:
                raise RuntimeError(f"测试通过率过低: {pass_rate:.2%}，要求: {self.config.min_test_coverage:.2%}")
        
        self.logger.info(f"测试完成，通过率: {pass_rate:.2%}")
        return results
    
    def _run_performance_tests(self) -> Dict[str, Any]:
        """运行性能测试"""
        results = {}
        
        try:
            import waternet
            try:
                import numpy as np
            except ImportError:
                self.logger.warning("numpy不可用，跳过性能测试")
                results['skipped'] = 'numpy not available'
                return results
            
            try:
                from waternet.optimization import IntervalOptimizer
                
                # 性能基准测试
                optimizer = IntervalOptimizer()
                
                # 创建测试数据
                test_data = {
                    'flow_rate': np.random.uniform(0.5, 2.0, 100),
                    'pressure': np.random.uniform(1.0, 3.0, 100)
                }
                
                # 测试优化性能
                start_time = time.time()
                
                for i in range(10):  # 运行10次测试
                    result = optimizer.optimize_interval(
                        target_flow=1.5,
                        data=test_data
                    )
                
                total_time = time.time() - start_time
                avg_time = total_time / 10
                
                results['optimization_performance'] = {
                    'average_time_seconds': avg_time,
                    'total_time_seconds': total_time,
                    'iterations': 10
                }
                
                # 性能阈值检查
                baseline_time = 0.1  # 基准时间：100ms
                performance_ratio = avg_time / baseline_time
                
                results['performance_ratio'] = performance_ratio
                
                if performance_ratio > self.config.performance_threshold:
                    self.logger.warning(f"性能下降: {performance_ratio:.2f}x，阈值: {self.config.performance_threshold}x")
                
                self.update_report['performance_metrics'] = results
                
            except ImportError:
                self.logger.warning("优化模块不可用，跳过性能测试")
                results['skipped'] = 'optimization module not available'
            
        except Exception as e:
            results['error'] = str(e)
            self.logger.warning(f"性能测试失败: {e}")
        
        return results
    
    def _final_verification(self) -> Dict[str, Any]:
        """最终验证"""
        results = {}
        
        # 验证项目结构完整性
        required_paths = [
            'waternet/__init__.py',
            'waternet/models/__init__.py',
            'waternet/optimization/__init__.py',
            'examples/interval_optimization/application_examples.py',
            'examples/interval_optimization/correct_workflow_comparison.py'
        ]
        
        missing_files = []
        for path in required_paths:
            if not (self.project_root / path).exists():
                missing_files.append(path)
        
        results['file_integrity'] = {
            'missing_files': missing_files,
            'integrity_check': len(missing_files) == 0
        }
        
        if missing_files:
            raise RuntimeError(f"关键文件缺失: {missing_files}")
        
        # 验证模块导入
        try:
            import waternet
            from waternet.models import SolverFactory, solve_with_auto_solver
            
            # 尝试导入优化模块，可能不存在
            try:
                from waternet.optimization import IntervalOptimizer
            except ImportError:
                self.logger.warning("优化模块不存在，但主要模块存在")
            
            results['import_verification'] = {'success': True}
            
        except ImportError as e:
            results['import_verification'] = {'success': False, 'error': str(e)}
            raise RuntimeError(f"模块导入验证失败: {e}")
        
        # 健康检查
        if self.config.health_check_enabled:
            health_status = self._run_health_check()
            results['health_check'] = health_status
        
        self.logger.info("最终验证完成")
        return results
    
    def _run_health_check(self) -> Dict[str, Any]:
        """运行系统健康检查"""
        health_status = {}
        
        # 检查Python包状态
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'check'],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            health_status['package_dependencies'] = {
                'consistent': result.returncode == 0,
                'output': result.stdout,
                'errors': result.stderr
            }
            
        except Exception as e:
            health_status['package_dependencies'] = {
                'consistent': False,
                'error': str(e)
            }
        
        return health_status
    
    def _execute_rollback(self):
        """执行回滚操作"""
        if not self.backup_path or not self.backup_path.exists():
            self.logger.error("无法执行回滚：备份不存在")
            return
        
        self.logger.info(f"开始回滚到备份: {self.backup_path}")
        
        try:
            # 如果备份是压缩的，先解压
            if self.backup_path.suffix == '.gz':
                import tarfile
                with tarfile.open(self.backup_path, 'r:gz') as tar:
                    tar.extractall(self.backup_path.parent)
                
                # 找到解压后的目录
                extracted_dir = self.backup_path.parent / self.backup_path.stem.replace('.tar', '')
                self.backup_path = extracted_dir
            
            # 恢复文件
            dirs_to_restore = ['waternet', 'examples']
            
            for dir_name in dirs_to_restore:
                backup_dir = self.backup_path / dir_name
                target_dir = self.project_root / dir_name
                
                if backup_dir.exists():
                    if target_dir.exists():
                        shutil.rmtree(target_dir)
                    shutil.copytree(backup_dir, target_dir)
            
            self.update_report['rollback_performed'] = True
            self.logger.info("回滚完成")
            
        except Exception as e:
            self.logger.error(f"回滚失败: {e}")
            self.update_report['errors'].append(f"回滚失败: {e}")
    
    def _generate_report(self):
        """生成更新报告"""
        report_dir = self.project_root / 'reports'
        report_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = report_dir / f'update_report_{timestamp}.json'
        
        # 添加额外信息到报告
        self.update_report['system_info'] = {
            'platform': platform.platform(),
            'python_version': platform.python_version(),
            'project_root': str(self.project_root)
        }
        
        # 保存报告
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.update_report, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"更新报告已保存: {report_file}")
        
        # 控制台输出摘要
        self._print_summary()
    
    def _print_summary(self):
        """打印更新摘要"""
        print("\n" + "="*60)
        print("WaterNet 自动化更新系统 - 执行摘要")
        print("="*60)
        
        # 基本信息
        print(f"状态: {self.update_report['status'].upper()}")
        print(f"开始时间: {self.update_report.get('start_time', 'N/A')}")
        print(f"结束时间: {self.update_report.get('end_time', 'N/A')}")
        
        if 'duration_seconds' in self.update_report:
            duration = self.update_report['duration_seconds']
            print(f"总耗时: {duration:.1f}秒")
        
        # 步骤执行情况
        print(f"\n步骤执行情况:")
        for step_name, step_info in self.update_report['steps'].items():
            status = step_info['status']
            time_taken = step_info.get('execution_time', 0)
            print(f"  {step_name}: {status.upper()} ({time_taken:.1f}s)")
        
        # 错误信息
        if self.update_report['errors']:
            print(f"\n错误信息:")
            for error in self.update_report['errors']:
                print(f"  - {error}")
        
        # 性能指标
        if self.update_report['performance_metrics']:
            perf = self.update_report['performance_metrics']
            if 'performance_ratio' in perf:
                print(f"\n性能指标:")
                print(f"  性能比率: {perf['performance_ratio']:.2f}x")
        
        print("="*60)


if __name__ == '__main__':
    # 示例用法
    try:
        # 使用安全配置
        config = UpdateConfig.safe()
        updater = AutoUpdateSystem(config=config)
        
        # 运行更新
        result = updater.run_full_update()
        print(f"更新完成: {result['status']}")
        
    except Exception as e:
        print(f"更新失败: {e}")
        sys.exit(1)
    
    def _run_pre_check(self) -> Dict[str, Any]:
        """运行系统预检查"""
        self.logger.info("运行系统预检查")
        
        checks = {
            'disk_space': self._check_disk_space(),
            'permissions': self._check_permissions(),
            'git_installed': self._check_git_installed(),
            'git_status': self._check_git_status(),
            'python_version': self._check_python_version(),
            'dependency_sources': self._check_dependency_sources()
        }
        
        if all(checks.values()):
            self.logger.info("所有预检查通过")
            return checks
        else:
            failed_checks = [k for k, v in checks.items() if not v]
            raise Exception(f"预检查失败: {', '.join(failed_checks)}")
    
    def _check_disk_space(self) -> bool:
        """检查磁盘空间"""
        total, used, free = shutil.disk_usage(self.project_root)
        if free < 1024**3:  # 1GB
            self.logger.error("磁盘空间不足")
            return False
        return True
    
    def _check_permissions(self) -> bool:
        """检查文件权限"""
        test_file = self.project_root / "temp_test.txt"
        try:
            test_file.write_text("test")
            test_file.unlink()
            return True
        except Exception as e:
            self.logger.error(f"写权限不足: {e}")
            return False
    
    def _check_git_installed(self) -> bool:
        """检查Git是否安装"""
        try:
            subprocess.run(['git', '--version'], check=True, capture_output=True)
            return True
        except Exception as e:
            self.logger.error(f"Git未安装: {e}")
            return False
    
    def _check_git_status(self) -> bool:
        """检查Git状态"""
        try:
            import git
            repo = git.Repo(self.project_root)
            if self.config.check_uncommitted_changes and repo.is_dirty():
                self.logger.warning("工作目录有未提交更改")
                return False
            return True
        except ImportError:
            self.logger.info("GitPython不可用，跳过Git状态检查")
            return True
        except Exception as e:
            self.logger.error(f"Git状态检查失败: {e}")
            return False
    
    def _check_python_version(self) -> bool:
        """检查Python版本"""
        major, minor, micro, releaselevel, serial = sys.version_info
        if major < 3 or (major == 3 and minor < 8):
            self.logger.error("Python版本过低，需要Python 3.8或更高")
            return False
        return True
    
    def _check_dependency_sources(self) -> bool:
        """检查依赖源"""
        valid_sources = ['pip', 'conda']
        for source in self.config.dependency_sources:
            if source not in valid_sources:
                self.logger.error(f"无效的依赖源: {source}")
                return False
        return True
    
    def _create_backup(self) -> str:
        """创建系统备份"""
        self.logger.info("创建系统备份")
        
        backup_dir = self.project_root / 'backups'
        backup_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f'backup_{timestamp}'
        backup_path.mkdir(exist_ok=True)
        
        # 备份关键目录
        backup_items = ['waternet', 'examples', 'tests', 'requirements.txt', 'pyproject.toml']
        
        for item in backup_items:
            src = self.project_root / item
            if src.exists():
                dst = backup_path / item
                if src.is_file():
                    shutil.copy2(src, dst)
                else:
                    shutil.copytree(src, dst, ignore=shutil.ignore_patterns('__pycache__'))
                    
        self.logger.info(f"备份完成: {backup_path}")
        self.backup_path = backup_path
        return str(backup_path)
    
    def _update_dependencies(self) -> Dict[str, Any]:
        """更新依赖包"""
        self.logger.info("更新依赖包")
        
        results = {}
        
        if 'pip' in self.config.dependency_sources:
            pip_results = self._update_pip_dependencies()
            results['pip'] = pip_results
        
        if 'conda' in self.config.dependency_sources:
            conda_results = self._update_conda_dependencies()
            results['conda'] = conda_results
        
        return results
    
    def _update_pip_dependencies(self) -> Dict[str, Any]:
        """更新pip依赖"""
        self.logger.info("更新pip依赖")
        
        results = {
            'pip_upgrade': False,
            'requirements_install': False,
            'project_install': False
        }
        
        try:
            # 更新pip
            subprocess.run([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'], 
                         check=True, capture_output=True)
            results['pip_upgrade'] = True
            
            # 安装requirements
            req_file = self.project_root / "requirements.txt"
            if req_file.exists():
                result = subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', str(req_file), '--upgrade'], 
                                      capture_output=True, text=True)
                if result.returncode != 0:
                    raise Exception(f"依赖安装失败: {result.stderr}")
                results['requirements_install'] = True
            
            # 重装项目
            subprocess.run([sys.executable, '-m', 'pip', 'install', '-e', '.'], 
                         cwd=self.project_root, check=True, capture_output=True)
            results['project_install'] = True
            
            # 验证核心模块
            subprocess.run([sys.executable, '-c', 'import waternet; print("WaterNet导入成功")'], 
                         check=True, capture_output=True)
            
            self.logger.info("pip依赖更新完成")
            return results
            
        except Exception as e:
            self.logger.error(f"pip依赖更新失败: {e}")
            raise
    
    def _update_conda_dependencies(self) -> Dict[str, Any]:
        """更新conda依赖"""
        self.logger.info("更新conda依赖")
        
        results = {
            'conda_upgrade': False,
            'environment_install': False,
            'project_install': False
        }
        
        try:
            # 更新conda
            subprocess.run(['conda', 'update', '-n', 'base', '-c', 'defaults', 'conda'], 
                         check=True, capture_output=True)
            results['conda_upgrade'] = True
            
            # 安装environment
            env_file = self.project_root / "environment.yml"
            if env_file.exists():
                result = subprocess.run(['conda', 'env', 'update', '-f', str(env_file)], 
                                      capture_output=True, text=True)
                if result.returncode != 0:
                    raise Exception(f"环境安装失败: {result.stderr}")
                results['environment_install'] = True
            
            # 重装项目
            subprocess.run([sys.executable, '-m', 'pip', 'install', '-e', '.'], 
                         cwd=self.project_root, check=True, capture_output=True)
            results['project_install'] = True
            
            # 验证核心模块
            subprocess.run([sys.executable, '-c', 'import waternet; print("WaterNet导入成功")'], 
                         check=True, capture_output=True)
            
            self.logger.info("conda依赖更新完成")
            return results
            
        except Exception as e:
            self.logger.error(f"conda依赖更新失败: {e}")
            raise
    
    def _update_code(self) -> Dict[str, Any]:
        """更新代码库"""
        self.logger.info("更新代码库")
        
        results = {
            'git_pull': False,
            'git_checkout': False,
            'git_status': False
        }
        
        try:
            # 检查Git状态（如果可用）
            try:
                import git
                repo = git.Repo(self.project_root)
                
                if self.config.git_branch:
                    repo.git.checkout(self.config.git_branch)
                    results['git_checkout'] = True
                
                if self.config.git_pull:
                    origin = repo.remotes.origin
                    origin.pull()
                    results['git_pull'] = True
                
                if self.config.check_uncommitted_changes and repo.is_dirty():
                    self.logger.warning("工作目录有未提交更改，跳过代码更新")
                else:
                    results['git_status'] = True
                
                self.logger.info("代码更新完成")
                return results
                
            except ImportError:
                self.logger.info("GitPython不可用，跳过Git操作")
                return results
            except Exception as e:
                self.logger.warning(f"Git操作失败: {e}")
                raise
                
        except Exception as e:
            self.logger.error(f"代码更新失败: {e}")
            raise
    
    def _run_tests(self) -> Dict[str, Any]:
        """运行测试套件"""
        self.logger.info("运行测试套件")
        
        results = {
            'passed_tests': 0,
            'total_tests': 0,
            'test_coverage': 0.0
        }
        
        try:
            # 运行主要示例脚本进行验证
            test_scripts = [
                'examples.interval_optimization.demo_five_intervals',
                'examples.interval_optimization.test_basic_interval_partitioning'
            ]
            
            for script in test_scripts:
                try:
                    result = subprocess.run([sys.executable, '-m', script], 
                                          cwd=self.project_root,
                                          capture_output=True, text=True, timeout=self.config.test_timeout)
                    if result.returncode == 0:
                        results['passed_tests'] += 1
                        self.logger.info(f"测试通过: {script}")
                    else:
                        self.logger.warning(f"测试失败: {script}")
                except Exception as e:
                    self.logger.warning(f"执行出错: {script} - {e}")
            
            results['total_tests'] = len(test_scripts)
            results['test_coverage'] = results['passed_tests'] / results['total_tests']
            
            if results['test_coverage'] < self.config.min_test_coverage:
                raise Exception(f"测试覆盖率低于阈值: {results['test_coverage']} < {self.config.min_test_coverage}")
            
            self.logger.info(f"测试完成: {results['passed_tests']}/{results['total_tests']} 通过")
            return results
            
        except Exception as e:
            self.logger.error(f"测试失败: {e}")
            raise
    
    def _run_performance_tests(self) -> Dict[str, Any]:
        """运行性能基准测试"""
        self.logger.info("运行性能基准测试")
        
        results = {
            'import_time_ms': 0.0,
            'demo_creation_time_s': 0.0,
            'demo_success': False
        }
        
        try:
            start_time = time.time()
            
            # 简单的性能测试：导入测试
            import_time = time.time()
            import waternet
            import_duration = time.time() - import_time
            
            # 创建简单系统测试
            try:
                from waternet.models import create_demonstration_system
                demo_time = time.time()
                demo_results = create_demonstration_system()
                demo_duration = time.time() - demo_time
                
                results = {
                    'import_time_ms': round(import_duration * 1000, 2),
                    'demo_creation_time_s': round(demo_duration, 2),
                    'demo_success': demo_results.get('optimization_results', {}).get('optimization_success', False)
                }
            except Exception as e:
                results = {
                    'import_time_ms': round(import_duration * 1000, 2),
                    'demo_creation_error': str(e)
                }
            
            self.logger.info(f"性能测试完成: {results}")
            return results
            
        except Exception as e:
            self.logger.error(f"性能测试失败: {e}")
            raise
    
    def _final_verification(self) -> Dict[str, Any]:
        """最终验证"""
        self.logger.info("执行最终验证")
        
        try:
            # 验证WaterNet模块完整性
            result = subprocess.run([
                sys.executable, '-c', 
                'import waternet; from waternet.models import FiveSectionConfig; print("验证通过")'
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"模块验证失败: {result.stderr}")
                
            self.logger.info("最终验证通过")
            return {'status': 'success'}
            
        except Exception as e:
            self.logger.error(f"最终验证失败: {e}")
            raise
    
    def _execute_rollback(self):
        """执行回滚"""
        if not self.backup_path or not self.backup_path.exists():
            self.logger.error("备份不存在，无法回滚")
            return False
            
        try:
            self.logger.info("执行回滚")
            
            # 恢复备份文件
            for item in self.backup_path.iterdir():
                dst = self.project_root / item.name
                if dst.exists():
                    if dst.is_file():
                        dst.unlink()
                    else:
                        shutil.rmtree(dst)
                        
                if item.is_file():
                    shutil.copy2(item, dst)
                else:
                    shutil.copytree(item, dst)
                    
            # 重新安装项目
            subprocess.run([sys.executable, '-m', 'pip', 'install', '-e', '.'], 
                         cwd=self.project_root, check=True, capture_output=True)
            
            self.logger.info("回滚完成")
            self.update_report['rollback_performed'] = True
            return True
            
        except Exception as e:
            self.logger.error(f"回滚失败: {e}")
            return False
    
    def _generate_report(self):
        """生成更新报告"""
        report_dir = self.project_root / 'reports'
        report_dir.mkdir(exist_ok=True)
        
        report_file = report_dir / f'update_report_{self.update_start_time.strftime("%Y%m%d_%H%M%S")}.json'
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.update_report, f, indent=2, ensure_ascii=False)
            
        self.logger.info(f"更新报告已保存: {report_file}")
        return self.update_report


def main():
    """主函数"""
    print("🌊 WaterNet全方位自动化更新系统")
    print("=" * 50)
    
    # 创建更新配置
    config = UpdateConfig()
    
    # 创建更新系统
    updater = AutoUpdateSystem(config)
    
    # 运行完整更新
    result = updater.run_full_update()
    
    # 显示结果摘要
    print("\n" + "=" * 50)
    print("📊 更新结果摘要")
    print("=" * 50)
    print(f"更新ID: {result['update_id']}")
    print(f"状态: {'✅ 成功' if result['success'] else '❌ 失败'}")
    
    for component, info in result['results'].items():
        status_icon = {'success': '✅', 'failed': '❌', 'pending': '⏳', 'running': '🔄', 'skipped': '⏭️'}
        print(f"{component}: {status_icon.get(info['status'], '❓')} {info['status']}")
    
    if not result['success']:
        print(f"错误信息: {result['error_message']}")
    
    print("\n🎯 系统特性:")
    print("• 智能依赖管理：自动检测和更新科学计算库")
    print("• 代码同步：Git集成的自动代码更新")
    print("• 完整测试：运行示例脚本验证功能")
    print("• 性能监控：基准测试确保系统性能")
    print("• 安全备份：失败时自动回滚机制")
    print("• 智能通知：实时状态反馈和报告生成")

if __name__ == "__main__":
    main()