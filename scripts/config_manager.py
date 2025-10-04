#!/usr/bin/env python3
"""
WaterNet 更新配置文件系统

支持多环境配置管理，包括：
- 开发环境配置
- 测试环境配置  
- 生产环境配置
- 用户自定义配置
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field


@dataclass
class NotificationConfig:
    """通知配置"""
    enabled: bool = True
    channels: List[str] = field(default_factory=lambda: ['console', 'file'])
    email_recipients: List[str] = field(default_factory=list)
    webhook_url: Optional[str] = None
    slack_token: Optional[str] = None
    discord_webhook: Optional[str] = None


@dataclass
class PerformanceConfig:
    """性能配置"""
    threshold_multiplier: float = 1.5
    baseline_time_ms: float = 100.0
    memory_limit_mb: int = 512
    cpu_timeout_seconds: int = 60
    parallel_processes: int = 1


@dataclass
class TestingConfig:
    """测试配置"""
    enabled: bool = True
    timeout_seconds: int = 300
    min_coverage: float = 0.8
    run_examples: bool = True
    run_performance_tests: bool = True
    example_files: List[str] = field(default_factory=lambda: [
        'application_examples.py',
        'correct_workflow_comparison.py'
    ])


@dataclass
class BackupConfig:
    """备份配置"""
    enabled: bool = True
    max_backups: int = 5
    compress: bool = True
    include_logs: bool = False
    exclude_patterns: List[str] = field(default_factory=lambda: [
        '__pycache__',
        '*.pyc',
        '.git',
        'node_modules',
        '.venv'
    ])


@dataclass
class DependencyConfig:
    """依赖管理配置"""
    sources: List[str] = field(default_factory=lambda: ['pip'])
    force_reinstall: bool = False
    upgrade_all: bool = False
    pip_extra_args: List[str] = field(default_factory=list)
    conda_channels: List[str] = field(default_factory=lambda: ['conda-forge'])
    core_packages: List[str] = field(default_factory=lambda: [
        'numpy', 'pandas', 'matplotlib', 'scipy'
    ])


@dataclass
class GitConfig:
    """Git配置"""
    pull_enabled: bool = True
    target_branch: Optional[str] = None
    check_uncommitted: bool = True
    auto_stash: bool = False
    remote_name: str = 'origin'


@dataclass
class EnvironmentConfig:
    """环境配置"""
    name: str
    description: str
    
    # 核心配置
    update_dependencies: bool = True
    update_code: bool = True
    create_backup: bool = True
    rollback_on_failure: bool = True
    
    # 子配置
    notifications: NotificationConfig = field(default_factory=NotificationConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    testing: TestingConfig = field(default_factory=TestingConfig)
    backup: BackupConfig = field(default_factory=BackupConfig)
    dependencies: DependencyConfig = field(default_factory=DependencyConfig)
    git: GitConfig = field(default_factory=GitConfig)
    
    # 高级选项
    parallel_operations: bool = True
    health_check_enabled: bool = True
    debug_mode: bool = False
    
    @classmethod
    def development(cls) -> 'EnvironmentConfig':
        """开发环境配置"""
        config = cls(
            name="development",
            description="开发环境 - 快速迭代，较少验证"
        )
        
        # 调整为开发友好的设置
        config.testing.timeout_seconds = 180
        config.testing.min_coverage = 0.7
        config.performance.threshold_multiplier = 2.0
        config.backup.max_backups = 3
        config.dependencies.upgrade_all = True
        config.git.check_uncommitted = False
        config.debug_mode = True
        
        return config
    
    @classmethod
    def testing(cls) -> 'EnvironmentConfig':
        """测试环境配置"""
        config = cls(
            name="testing",
            description="测试环境 - 严格测试验证"
        )
        
        # 强化测试设置
        config.testing.timeout_seconds = 600
        config.testing.min_coverage = 0.9
        config.testing.run_performance_tests = True
        config.performance.threshold_multiplier = 1.3
        config.backup.enabled = True
        config.rollback_on_failure = True
        
        return config
    
    @classmethod
    def production(cls) -> 'EnvironmentConfig':
        """生产环境配置"""
        config = cls(
            name="production", 
            description="生产环境 - 最高安全性和稳定性"
        )
        
        # 最严格的设置
        config.testing.timeout_seconds = 900
        config.testing.min_coverage = 0.95
        config.performance.threshold_multiplier = 1.1
        config.backup.max_backups = 10
        config.backup.compress = True
        config.backup.include_logs = True
        config.dependencies.force_reinstall = False
        config.git.check_uncommitted = True
        config.git.auto_stash = False
        
        return config
    
    @classmethod
    def minimal(cls) -> 'EnvironmentConfig':
        """最小配置 - 仅核心功能"""
        config = cls(
            name="minimal",
            description="最小配置 - 仅更新依赖"
        )
        
        # 最小化设置
        config.update_code = False
        config.create_backup = False
        config.testing.enabled = False
        config.testing.run_performance_tests = False
        config.backup.enabled = False
        config.health_check_enabled = False
        
        return config


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()
        self.config_dir = self.project_root / 'config'
        self.config_dir.mkdir(exist_ok=True)
        
        # 预定义环境配置
        self.predefined_configs = {
            'development': EnvironmentConfig.development(),
            'testing': EnvironmentConfig.testing(),
            'production': EnvironmentConfig.production(),
            'minimal': EnvironmentConfig.minimal()
        }
    
    def get_config(self, name: str) -> EnvironmentConfig:
        """获取配置"""
        # 首先检查预定义配置
        if name in self.predefined_configs:
            return self.predefined_configs[name]
        
        # 然后检查用户自定义配置文件
        config_file = self.config_dir / f'{name}.yaml'
        if config_file.exists():
            return self.load_config_from_file(config_file)
        
        config_file = self.config_dir / f'{name}.json'
        if config_file.exists():
            return self.load_config_from_file(config_file)
        
        raise ValueError(f"配置 '{name}' 不存在")
    
    def load_config_from_file(self, file_path: Path) -> EnvironmentConfig:
        """从文件加载配置"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_path.suffix == '.yaml' or file_path.suffix == '.yml':
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)
            
            return self._dict_to_config(data)
            
        except Exception as e:
            raise ValueError(f"无法加载配置文件 {file_path}: {e}")
    
    def save_config(self, config: EnvironmentConfig, format: str = 'yaml'):
        """保存配置到文件"""
        filename = f"{config.name}.{format}"
        file_path = self.config_dir / filename
        
        data = asdict(config)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                if format == 'yaml':
                    yaml.safe_dump(data, f, default_flow_style=False, 
                                 allow_unicode=True, indent=2)
                else:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"配置已保存到: {file_path}")
            
        except Exception as e:
            raise ValueError(f"无法保存配置文件: {e}")
    
    def list_configs(self) -> Dict[str, str]:
        """列出所有可用配置"""
        configs = {}
        
        # 添加预定义配置
        for name, config in self.predefined_configs.items():
            configs[name] = f"[预定义] {config.description}"
        
        # 添加用户自定义配置
        for config_file in self.config_dir.glob('*.yaml'):
            name = config_file.stem
            if name not in configs:
                configs[name] = f"[自定义] {config_file}"
        
        for config_file in self.config_dir.glob('*.json'):
            name = config_file.stem
            if name not in configs:
                configs[name] = f"[自定义] {config_file}"
        
        return configs
    
    def create_custom_config(self, name: str, base_config: str = 'development') -> EnvironmentConfig:
        """创建自定义配置"""
        # 基于现有配置创建
        base = self.get_config(base_config)
        
        # 创建新配置
        config = EnvironmentConfig(
            name=name,
            description=f"基于 {base_config} 的自定义配置",
            
            # 复制基础配置的所有设置
            update_dependencies=base.update_dependencies,
            update_code=base.update_code,
            create_backup=base.create_backup,
            rollback_on_failure=base.rollback_on_failure,
            
            notifications=base.notifications,
            performance=base.performance,
            testing=base.testing,
            backup=base.backup,
            dependencies=base.dependencies,
            git=base.git,
            
            parallel_operations=base.parallel_operations,
            health_check_enabled=base.health_check_enabled,
            debug_mode=base.debug_mode
        )
        
        return config
    
    def _dict_to_config(self, data: Dict[str, Any]) -> EnvironmentConfig:
        """将字典转换为配置对象"""
        # 处理嵌套配置对象
        if 'notifications' in data:
            data['notifications'] = NotificationConfig(**data['notifications'])
        
        if 'performance' in data:
            data['performance'] = PerformanceConfig(**data['performance'])
        
        if 'testing' in data:
            data['testing'] = TestingConfig(**data['testing'])
        
        if 'backup' in data:
            data['backup'] = BackupConfig(**data['backup'])
        
        if 'dependencies' in data:
            data['dependencies'] = DependencyConfig(**data['dependencies'])
        
        if 'git' in data:
            data['git'] = GitConfig(**data['git'])
        
        return EnvironmentConfig(**data)
    
    def validate_config(self, config: EnvironmentConfig) -> List[str]:
        """验证配置"""
        warnings = []
        
        # 验证基本设置
        if config.testing.min_coverage > 1.0:
            warnings.append("测试覆盖率不能超过100%")
        
        if config.testing.timeout_seconds < 60:
            warnings.append("测试超时时间过短，建议至少60秒")
        
        if config.backup.max_backups < 1:
            warnings.append("至少应保留1个备份")
        
        if config.performance.threshold_multiplier < 1.0:
            warnings.append("性能阈值倍数应大于等于1.0")
        
        # 验证依赖源
        valid_sources = ['pip', 'conda']
        for source in config.dependencies.sources:
            if source not in valid_sources:
                warnings.append(f"无效的依赖源: {source}")
        
        return warnings
    
    def export_all_configs(self, output_dir: Optional[Path] = None):
        """导出所有配置"""
        output_dir = output_dir or (self.project_root / 'exported_configs')
        output_dir.mkdir(exist_ok=True)
        
        for name, config in self.predefined_configs.items():
            config_file = output_dir / f'{name}.yaml'
            
            data = asdict(config)
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.safe_dump(data, f, default_flow_style=False, 
                             allow_unicode=True, indent=2)
        
        print(f"所有配置已导出到: {output_dir}")


def main():
    """演示配置管理器的使用"""
    import argparse
    
    parser = argparse.ArgumentParser(description='WaterNet 配置管理器')
    parser.add_argument('--list', action='store_true', help='列出所有配置')
    parser.add_argument('--show', type=str, help='显示指定配置')
    parser.add_argument('--export', action='store_true', help='导出所有预定义配置')
    parser.add_argument('--create', type=str, help='创建自定义配置')
    parser.add_argument('--base', type=str, default='development', help='创建时的基础配置')
    
    args = parser.parse_args()
    
    manager = ConfigManager()
    
    if args.list:
        print("📋 可用配置:")
        configs = manager.list_configs()
        for name, desc in configs.items():
            print(f"  {name}: {desc}")
    
    elif args.show:
        try:
            config = manager.get_config(args.show)
            print(f"📄 配置 '{args.show}':")
            print(f"  名称: {config.name}")
            print(f"  描述: {config.description}")
            print(f"  更新依赖: {config.update_dependencies}")
            print(f"  更新代码: {config.update_code}")
            print(f"  创建备份: {config.create_backup}")
            print(f"  测试覆盖率: {config.testing.min_coverage}")
            print(f"  性能阈值: {config.performance.threshold_multiplier}x")
        except ValueError as e:
            print(f"❌ {e}")
    
    elif args.export:
        manager.export_all_configs()
    
    elif args.create:
        try:
            config = manager.create_custom_config(args.create, args.base)
            manager.save_config(config)
            print(f"✅ 自定义配置 '{args.create}' 创建成功")
        except Exception as e:
            print(f"❌ 创建配置失败: {e}")
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()