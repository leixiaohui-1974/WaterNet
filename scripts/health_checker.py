#!/usr/bin/env python3
"""
WaterNet 系统健康检查和诊断工具

全方位系统诊断功能：
- Python环境检查
- 依赖包完整性验证
- 项目结构检查
- 性能基准测试
- 系统资源监控
- 自动问题诊断和修复建议
"""

import os
import sys
import json
import time
import subprocess
import platform
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import importlib
import pkg_resources


@dataclass
class HealthCheckResult:
    """健康检查结果"""
    component: str
    status: str  # 'healthy', 'warning', 'error'
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    suggestions: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SystemDiagnostics:
    """系统诊断报告"""
    overall_status: str = 'unknown'
    health_score: float = 0.0
    total_checks: int = 0
    healthy_checks: int = 0
    warning_checks: int = 0
    error_checks: int = 0
    results: List[HealthCheckResult] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)


class HealthChecker:
    """健康检查器基类"""
    
    def __init__(self, name: str):
        self.name = name
    
    def check(self) -> HealthCheckResult:
        """执行健康检查"""
        raise NotImplementedError
    
    def _create_result(self, status: str, message: str, 
                      details: Dict[str, Any] = None,
                      suggestions: List[str] = None) -> HealthCheckResult:
        """创建检查结果"""
        return HealthCheckResult(
            component=self.name,
            status=status,
            message=message,
            details=details or {},
            suggestions=suggestions or []
        )


class PythonEnvironmentChecker(HealthChecker):
    """Python环境检查器"""
    
    def __init__(self):
        super().__init__("Python环境")
    
    def check(self) -> HealthCheckResult:
        """检查Python环境"""
        try:
            # 获取Python版本信息
            version_info = sys.version_info
            version_str = f"{version_info.major}.{version_info.minor}.{version_info.micro}"
            
            details = {
                'version': version_str,
                'executable': sys.executable,
                'platform': platform.platform(),
                'architecture': platform.architecture()[0]
            }
            
            # 检查版本兼容性
            if version_info < (3, 7):
                return self._create_result(
                    'error',
                    f"Python版本过低: {version_str}",
                    details,
                    ['请升级到Python 3.7或更高版本']
                )
            elif version_info < (3, 8):
                return self._create_result(
                    'warning',
                    f"Python版本较旧: {version_str}",
                    details,
                    ['建议升级到Python 3.8或更高版本以获得更好的性能']
                )
            else:
                return self._create_result(
                    'healthy',
                    f"Python环境正常: {version_str}",
                    details
                )
                
        except Exception as e:
            return self._create_result(
                'error',
                f"无法检查Python环境: {e}",
                suggestions=['检查Python安装是否正确']
            )


class DependencyChecker(HealthChecker):
    """依赖包检查器"""
    
    def __init__(self, project_root: Path):
        super().__init__("依赖包")
        self.project_root = project_root
        self.required_packages = [
            'numpy', 'pandas', 'matplotlib', 'scipy'
        ]
    
    def check(self) -> HealthCheckResult:
        """检查依赖包"""
        try:
            missing_packages = []
            outdated_packages = []
            installed_packages = {}
            
            # 检查核心包
            for package in self.required_packages:
                try:
                    module = importlib.import_module(package)
                    version = getattr(module, '__version__', 'unknown')
                    installed_packages[package] = version
                except ImportError:
                    missing_packages.append(package)
            
            # 检查包冲突
            try:
                subprocess.run([sys.executable, '-m', 'pip', 'check'], 
                             check=True, capture_output=True, text=True)
                conflicts = []
            except subprocess.CalledProcessError as e:
                conflicts = e.stdout.split('\n') if e.stdout else []
            
            details = {
                'installed_packages': installed_packages,
                'missing_packages': missing_packages,
                'conflicts': conflicts
            }
            
            suggestions = []
            
            if missing_packages:
                suggestions.append(f"安装缺失的包: pip install {' '.join(missing_packages)}")
            
            if conflicts:
                suggestions.append("解决包冲突: pip install --upgrade --force-reinstall <冲突的包>")
            
            # 判断状态
            if missing_packages:
                status = 'error'
                message = f"缺失关键依赖包: {', '.join(missing_packages)}"
            elif conflicts:
                status = 'warning'
                message = f"检测到包冲突: {len(conflicts)} 个冲突"
            else:
                status = 'healthy'
                message = f"所有依赖包正常: {len(installed_packages)} 个包已安装"
            
            return self._create_result(status, message, details, suggestions)
            
        except Exception as e:
            return self._create_result(
                'error',
                f"依赖检查失败: {e}",
                suggestions=['运行 pip check 手动检查依赖']
            )


class ProjectStructureChecker(HealthChecker):
    """项目结构检查器"""
    
    def __init__(self, project_root: Path):
        super().__init__("项目结构")
        self.project_root = project_root
        self.required_paths = [
            'waternet/__init__.py',
            'waternet/models/__init__.py',
            'examples/interval_optimization/',
            'setup.py',
            'README.md'
        ]
        self.important_files = [
            'examples/interval_optimization/application_examples.py',
            'examples/interval_optimization/correct_workflow_comparison.py'
        ]
    
    def check(self) -> HealthCheckResult:
        """检查项目结构"""
        try:
            missing_required = []
            missing_important = []
            existing_paths = []
            
            # 检查必需路径
            for path_str in self.required_paths:
                path = self.project_root / path_str
                if path.exists():
                    existing_paths.append(path_str)
                else:
                    missing_required.append(path_str)
            
            # 检查重要文件
            for file_str in self.important_files:
                file_path = self.project_root / file_str
                if not file_path.exists():
                    missing_important.append(file_str)
            
            details = {
                'existing_paths': existing_paths,
                'missing_required': missing_required,
                'missing_important': missing_important,
                'project_root': str(self.project_root)
            }
            
            suggestions = []
            
            if missing_required:
                suggestions.append("恢复缺失的核心文件和目录")
                suggestions.append("检查项目是否完整克隆或下载")
            
            if missing_important:
                suggestions.append("恢复重要的示例文件")
                suggestions.append("运行项目设置脚本重新生成文件")
            
            # 判断状态
            if missing_required:
                status = 'error'
                message = f"缺失核心项目文件: {len(missing_required)} 个文件/目录"
            elif missing_important:
                status = 'warning'
                message = f"缺失重要文件: {len(missing_important)} 个文件"
            else:
                status = 'healthy'
                message = "项目结构完整"
            
            return self._create_result(status, message, details, suggestions)
            
        except Exception as e:
            return self._create_result(
                'error',
                f"项目结构检查失败: {e}",
                suggestions=['检查项目目录访问权限']
            )


class WaterNetModuleChecker(HealthChecker):
    """WaterNet模块检查器"""
    
    def __init__(self, project_root: Path):
        super().__init__("WaterNet模块")
        self.project_root = project_root
    
    def check(self) -> HealthCheckResult:
        """检查WaterNet模块"""
        try:
            import_results = {}
            suggestions = []
            
            # 测试基础导入
            try:
                import waternet
                import_results['waternet'] = 'success'
                version = getattr(waternet, '__version__', 'unknown')
            except ImportError as e:
                import_results['waternet'] = f'failed: {e}'
                suggestions.append("重新安装WaterNet: pip install -e .")
            
            # 测试核心模块导入
            core_modules = [
                'waternet.models',
                'waternet.models.SolverFactory'
            ]
            
            for module_path in core_modules:
                try:
                    if '.' in module_path and module_path.count('.') > 1:
                        # 导入特定类或函数
                        module_name, attr_name = module_path.rsplit('.', 1)
                        module = importlib.import_module(module_name)
                        getattr(module, attr_name)
                    else:
                        importlib.import_module(module_path)
                    import_results[module_path] = 'success'
                except ImportError as e:
                    import_results[module_path] = f'failed: {e}'
                    suggestions.append(f"修复模块导入问题: {module_path}")
            
            # 测试可选模块
            optional_modules = [
                'waternet.optimization'
            ]
            
            for module_path in optional_modules:
                try:
                    importlib.import_module(module_path)
                    import_results[module_path] = 'success'
                except ImportError:
                    import_results[module_path] = 'optional_missing'
            
            details = {
                'import_results': import_results,
                'version': version if 'version' in locals() else 'unknown'
            }
            
            # 计算成功率
            total_core = len([m for m in import_results.keys() if not m.endswith('optimization')])
            successful_core = len([r for m, r in import_results.items() 
                                 if r == 'success' and not m.endswith('optimization')])
            
            if successful_core == 0:
                status = 'error'
                message = "WaterNet模块无法导入"
                suggestions.insert(0, "检查WaterNet是否正确安装")
            elif successful_core < total_core:
                status = 'warning'
                message = f"部分WaterNet模块导入失败: {successful_core}/{total_core}"
            else:
                status = 'healthy'
                message = "WaterNet模块导入正常"
            
            return self._create_result(status, message, details, suggestions)
            
        except Exception as e:
            return self._create_result(
                'error',
                f"模块检查失败: {e}",
                suggestions=['检查Python路径和模块安装']
            )


class PerformanceChecker(HealthChecker):
    """性能检查器"""
    
    def __init__(self, project_root: Path):
        super().__init__("系统性能")
        self.project_root = project_root
    
    def check(self) -> HealthCheckResult:
        """检查系统性能"""
        try:
            performance_metrics = {}
            suggestions = []
            
            # 测试导入时间
            start_time = time.time()
            try:
                import waternet
                import_time = (time.time() - start_time) * 1000
                performance_metrics['import_time_ms'] = round(import_time, 2)
            except ImportError:
                performance_metrics['import_time_ms'] = -1
                suggestions.append("修复模块导入问题以进行性能测试")
            
            # 测试系统资源
            try:
                import psutil
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage(str(self.project_root))
                
                performance_metrics.update({
                    'cpu_usage_percent': cpu_percent,
                    'memory_usage_percent': memory.percent,
                    'available_memory_gb': round(memory.available / (1024**3), 2),
                    'disk_free_gb': round(disk.free / (1024**3), 2)
                })
                
            except ImportError:
                suggestions.append("安装 psutil 以获得详细的系统资源信息")
            
            # 简单的计算性能测试
            start_time = time.time()
            result = sum(i**2 for i in range(10000))
            calc_time = (time.time() - start_time) * 1000
            performance_metrics['calc_benchmark_ms'] = round(calc_time, 2)
            
            details = {'metrics': performance_metrics}
            
            # 性能评估
            issues = []
            
            if performance_metrics.get('import_time_ms', 0) > 1000:
                issues.append("模块导入时间过长")
                suggestions.append("检查系统I/O性能和Python环境")
            
            if performance_metrics.get('memory_usage_percent', 0) > 80:
                issues.append("内存使用率过高")
                suggestions.append("关闭不必要的程序以释放内存")
            
            if performance_metrics.get('disk_free_gb', 1) < 0.5:
                issues.append("磁盘空间不足")
                suggestions.append("清理磁盘空间，至少保留1GB可用空间")
            
            if issues:
                status = 'warning'
                message = f"性能问题: {', '.join(issues)}"
            else:
                status = 'healthy'
                message = "系统性能正常"
            
            return self._create_result(status, message, details, suggestions)
            
        except Exception as e:
            return self._create_result(
                'error',
                f"性能检查失败: {e}",
                suggestions=['检查系统资源和权限']
            )


class SystemDiagnostician:
    """系统诊断专家"""
    
    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()
        
        # 初始化检查器
        self.checkers = [
            PythonEnvironmentChecker(),
            DependencyChecker(self.project_root),
            ProjectStructureChecker(self.project_root),
            WaterNetModuleChecker(self.project_root),
            PerformanceChecker(self.project_root)
        ]
    
    def run_full_diagnosis(self) -> SystemDiagnostics:
        """运行完整诊断"""
        print("🔍 开始WaterNet系统诊断...")
        print("-" * 50)
        
        results = []
        
        for checker in self.checkers:
            print(f"检查 {checker.name}...", end=' ')
            try:
                result = checker.check()
                results.append(result)
                
                # 显示结果
                status_icon = {
                    'healthy': '✅',
                    'warning': '⚠️',
                    'error': '❌'
                }.get(result.status, '❓')
                
                print(f"{status_icon} {result.message}")
                
            except Exception as e:
                error_result = HealthCheckResult(
                    component=checker.name,
                    status='error',
                    message=f"检查失败: {e}",
                    suggestions=[f"手动检查 {checker.name}"]
                )
                results.append(error_result)
                print(f"❌ 检查失败: {e}")
        
        # 生成诊断报告
        diagnosis = self._generate_diagnosis(results)
        
        print("-" * 50)
        print(f"🏥 诊断完成！健康评分: {diagnosis.health_score:.1f}/100")
        print(f"📊 总览: {diagnosis.healthy_checks}健康, {diagnosis.warning_checks}警告, {diagnosis.error_checks}错误")
        
        return diagnosis
    
    def _generate_diagnosis(self, results: List[HealthCheckResult]) -> SystemDiagnostics:
        """生成诊断报告"""
        total_checks = len(results)
        healthy_checks = len([r for r in results if r.status == 'healthy'])
        warning_checks = len([r for r in results if r.status == 'warning'])
        error_checks = len([r for r in results if r.status == 'error'])
        
        # 计算健康评分
        health_score = (healthy_checks * 100 + warning_checks * 60) / total_checks if total_checks > 0 else 0
        
        # 确定整体状态
        if error_checks > 0:
            overall_status = 'critical'
        elif warning_checks > 0:
            overall_status = 'warning'
        else:
            overall_status = 'healthy'
        
        # 生成推荐建议
        recommendations = self._generate_recommendations(results)
        
        return SystemDiagnostics(
            overall_status=overall_status,
            health_score=health_score,
            total_checks=total_checks,
            healthy_checks=healthy_checks,
            warning_checks=warning_checks,
            error_checks=error_checks,
            results=results,
            recommendations=recommendations
        )
    
    def _generate_recommendations(self, results: List[HealthCheckResult]) -> List[str]:
        """生成修复建议"""
        recommendations = []
        
        # 收集所有建议
        all_suggestions = []
        for result in results:
            all_suggestions.extend(result.suggestions)
        
        # 去重并排序
        unique_suggestions = list(set(all_suggestions))
        
        # 按优先级排序建议
        priority_keywords = [
            ('python', '升级Python环境'),
            ('pip install', '安装依赖包'),
            ('重新安装', '修复安装问题'),
            ('检查', '检查系统配置')
        ]
        
        for keyword, category in priority_keywords:
            category_suggestions = [s for s in unique_suggestions if keyword.lower() in s.lower()]
            if category_suggestions:
                recommendations.append(f"{category}:")
                recommendations.extend([f"  - {s}" for s in category_suggestions])
        
        # 添加剩余建议
        remaining = [s for s in unique_suggestions 
                    if not any(keyword in s.lower() for keyword, _ in priority_keywords)]
        if remaining:
            recommendations.append("其他建议:")
            recommendations.extend([f"  - {s}" for s in remaining])
        
        return recommendations
    
    def generate_report(self, diagnosis: SystemDiagnostics) -> str:
        """生成详细报告"""
        report = f"""
WaterNet 系统诊断报告
====================
生成时间: {diagnosis.generated_at.strftime('%Y-%m-%d %H:%M:%S')}
项目路径: {self.project_root}

总体评估
--------
健康评分: {diagnosis.health_score:.1f}/100
整体状态: {diagnosis.overall_status.upper()}
检查总数: {diagnosis.total_checks}
  - ✅ 健康: {diagnosis.healthy_checks}
  - ⚠️  警告: {diagnosis.warning_checks}
  - ❌ 错误: {diagnosis.error_checks}

详细结果
--------
"""
        
        for result in diagnosis.results:
            status_icon = {'healthy': '✅', 'warning': '⚠️', 'error': '❌'}.get(result.status, '❓')
            report += f"{status_icon} {result.component}: {result.message}\n"
            
            if result.suggestions:
                report += "  建议:\n"
                for suggestion in result.suggestions:
                    report += f"    - {suggestion}\n"
            report += "\n"
        
        if diagnosis.recommendations:
            report += "修复建议\n--------\n"
            for rec in diagnosis.recommendations:
                report += f"{rec}\n"
        
        return report
    
    def save_report(self, diagnosis: SystemDiagnostics, output_file: Optional[Path] = None):
        """保存诊断报告"""
        if output_file is None:
            reports_dir = self.project_root / 'reports'
            reports_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = reports_dir / f'health_check_{timestamp}.txt'
        
        report_content = self.generate_report(diagnosis)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        print(f"📄 诊断报告已保存到: {output_file}")
        return output_file


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='WaterNet 系统健康检查和诊断工具')
    parser.add_argument('--output', '-o', type=str, help='保存报告到指定文件')
    parser.add_argument('--json', action='store_true', help='输出JSON格式的结果')
    parser.add_argument('--quiet', '-q', action='store_true', help='静默模式，只输出结果')
    
    args = parser.parse_args()
    
    try:
        # 创建诊断器
        diagnostician = SystemDiagnostician()
        
        # 运行诊断
        if not args.quiet:
            diagnosis = diagnostician.run_full_diagnosis()
        else:
            # 静默模式
            diagnosis = SystemDiagnostics()
            for checker in diagnostician.checkers:
                result = checker.check()
                diagnosis.results.append(result)
            diagnosis = diagnostician._generate_diagnosis(diagnosis.results)
        
        # 输出结果
        if args.json:
            # JSON输出
            result_data = {
                'overall_status': diagnosis.overall_status,
                'health_score': diagnosis.health_score,
                'summary': {
                    'total': diagnosis.total_checks,
                    'healthy': diagnosis.healthy_checks,
                    'warning': diagnosis.warning_checks,
                    'error': diagnosis.error_checks
                },
                'results': [
                    {
                        'component': r.component,
                        'status': r.status,
                        'message': r.message,
                        'suggestions': r.suggestions
                    }
                    for r in diagnosis.results
                ],
                'recommendations': diagnosis.recommendations,
                'timestamp': diagnosis.generated_at.isoformat()
            }
            print(json.dumps(result_data, ensure_ascii=False, indent=2))
        
        # 保存报告
        if args.output:
            diagnostician.save_report(diagnosis, Path(args.output))
        elif not args.json:
            diagnostician.save_report(diagnosis)
        
        # 设置退出码
        if diagnosis.overall_status == 'critical':
            sys.exit(2)
        elif diagnosis.overall_status == 'warning':
            sys.exit(1)
        else:
            sys.exit(0)
            
    except KeyboardInterrupt:
        print("\n⚠️  诊断被用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"💥 诊断过程发生错误: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()