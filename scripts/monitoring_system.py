#!/usr/bin/env python3
"""
WaterNet 智能通知和监控系统

提供实时状态反馈和多渠道通知功能：
- 控制台实时输出
- 文件日志记录
- 邮件通知
- Webhook集成
- 性能监控
- 状态仪表板
"""

import os
import sys
import json
import time
import smtplib
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging


@dataclass
class NotificationMessage:
    """通知消息"""
    title: str
    message: str
    level: str = 'info'  # info, warning, error, success
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MonitoringMetrics:
    """监控指标"""
    start_time: datetime
    current_step: str = ""
    progress_percentage: float = 0.0
    steps_completed: int = 0
    total_steps: int = 0
    errors_count: int = 0
    warnings_count: int = 0
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    resource_usage: Dict[str, float] = field(default_factory=dict)


class NotificationChannel:
    """通知渠道基类"""
    
    def __init__(self, name: str, config: Dict[str, Any] = None):
        self.name = name
        self.config = config or {}
        self.enabled = self.config.get('enabled', True)
    
    def send(self, message: NotificationMessage) -> bool:
        """发送通知"""
        raise NotImplementedError
    
    def format_message(self, message: NotificationMessage) -> str:
        """格式化消息"""
        timestamp = message.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        level_icon = {
            'info': 'ℹ️',
            'warning': '⚠️',
            'error': '❌',
            'success': '✅'
        }.get(message.level, 'ℹ️')
        
        return f"{level_icon} [{timestamp}] {message.title}\n{message.message}"


class ConsoleNotifier(NotificationChannel):
    """控制台通知器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__('console', config)
        self.use_colors = self.config.get('use_colors', True)
        
        # ANSI颜色代码
        self.colors = {
            'info': '\033[94m',      # 蓝色
            'warning': '\033[93m',   # 黄色  
            'error': '\033[91m',     # 红色
            'success': '\033[92m',   # 绿色
            'reset': '\033[0m'       # 重置
        }
    
    def send(self, message: NotificationMessage) -> bool:
        """发送控制台通知"""
        if not self.enabled:
            return False
        
        try:
            formatted_msg = self.format_message(message)
            
            if self.use_colors and message.level in self.colors:
                color_code = self.colors[message.level]
                reset_code = self.colors['reset']
                formatted_msg = f"{color_code}{formatted_msg}{reset_code}"
            
            print(formatted_msg)
            return True
            
        except Exception as e:
            print(f"控制台通知发送失败: {e}")
            return False


class FileNotifier(NotificationChannel):
    """文件日志通知器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__('file', config)
        self.log_file = Path(self.config.get('log_file', 'logs/notifications.log'))
        self.log_file.parent.mkdir(exist_ok=True)
        
        # 设置日志记录器
        self.logger = logging.getLogger(f'NotificationLogger_{id(self)}')
        self.logger.setLevel(logging.INFO)
        
        # 避免重复添加处理器
        if not self.logger.handlers:
            handler = logging.FileHandler(self.log_file, encoding='utf-8')
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def send(self, message: NotificationMessage) -> bool:
        """发送文件日志通知"""
        if not self.enabled:
            return False
        
        try:
            log_level = {
                'info': logging.INFO,
                'warning': logging.WARNING,
                'error': logging.ERROR,
                'success': logging.INFO
            }.get(message.level, logging.INFO)
            
            log_message = f"{message.title} - {message.message}"
            self.logger.log(log_level, log_message)
            
            return True
            
        except Exception as e:
            print(f"文件日志通知发送失败: {e}")
            return False


class EmailNotifier(NotificationChannel):
    """邮件通知器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__('email', config)
        self.smtp_server = self.config.get('smtp_server', 'smtp.gmail.com')
        self.smtp_port = self.config.get('smtp_port', 587)
        self.username = self.config.get('username')
        self.password = self.config.get('password')
        self.recipients = self.config.get('recipients', [])
        
        if not all([self.username, self.password, self.recipients]):
            self.enabled = False
    
    def send(self, message: NotificationMessage) -> bool:
        """发送邮件通知"""
        if not self.enabled:
            return False
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.username
            msg['To'] = ', '.join(self.recipients)
            msg['Subject'] = f"WaterNet更新通知: {message.title}"
            
            body = self.format_message(message)
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.username, self.password)
            
            text = msg.as_string()
            server.sendmail(self.username, self.recipients, text)
            server.quit()
            
            return True
            
        except Exception as e:
            print(f"邮件通知发送失败: {e}")
            return False


class WebhookNotifier(NotificationChannel):
    """Webhook通知器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__('webhook', config)
        self.webhook_url = self.config.get('webhook_url')
        self.headers = self.config.get('headers', {'Content-Type': 'application/json'})
        self.timeout = self.config.get('timeout', 10)
        
        if not self.webhook_url:
            self.enabled = False
    
    def send(self, message: NotificationMessage) -> bool:
        """发送Webhook通知"""
        if not self.enabled:
            return False
        
        try:
            payload = {
                'title': message.title,
                'message': message.message,
                'level': message.level,
                'timestamp': message.timestamp.isoformat(),
                'metadata': message.metadata
            }
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers=self.headers,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            return True
            
        except Exception as e:
            print(f"Webhook通知发送失败: {e}")
            return False


class SlackNotifier(NotificationChannel):
    """Slack通知器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__('slack', config)
        self.webhook_url = self.config.get('webhook_url')
        self.channel = self.config.get('channel', '#general')
        self.username = self.config.get('username', 'WaterNet Bot')
        
        if not self.webhook_url:
            self.enabled = False
    
    def send(self, message: NotificationMessage) -> bool:
        """发送Slack通知"""
        if not self.enabled:
            return False
        
        try:
            color_map = {
                'info': '#36a64f',
                'warning': '#ff9500', 
                'error': '#ff0000',
                'success': '#36a64f'
            }
            
            payload = {
                'channel': self.channel,
                'username': self.username,
                'attachments': [{
                    'color': color_map.get(message.level, '#36a64f'),
                    'title': message.title,
                    'text': message.message,
                    'ts': int(message.timestamp.timestamp())
                }]
            }
            
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            return True
            
        except Exception as e:
            print(f"Slack通知发送失败: {e}")
            return False


class MonitoringSystem:
    """监控系统"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.metrics = None
        self.notifiers: List[NotificationChannel] = []
        self.status_callbacks: List[Callable] = []
        
        # 初始化通知器
        self._setup_notifiers()
        
        # 监控状态
        self.is_monitoring = False
        self.last_update_time = None
    
    def _setup_notifiers(self):
        """设置通知器"""
        notifier_configs = self.config.get('notifiers', {})
        
        # 控制台通知器
        if notifier_configs.get('console', {}).get('enabled', True):
            self.notifiers.append(ConsoleNotifier(notifier_configs.get('console', {})))
        
        # 文件通知器
        if notifier_configs.get('file', {}).get('enabled', True):
            self.notifiers.append(FileNotifier(notifier_configs.get('file', {})))
        
        # 邮件通知器
        if notifier_configs.get('email', {}).get('enabled', False):
            self.notifiers.append(EmailNotifier(notifier_configs.get('email', {})))
        
        # Webhook通知器
        if notifier_configs.get('webhook', {}).get('enabled', False):
            self.notifiers.append(WebhookNotifier(notifier_configs.get('webhook', {})))
        
        # Slack通知器
        if notifier_configs.get('slack', {}).get('enabled', False):
            self.notifiers.append(SlackNotifier(notifier_configs.get('slack', {})))
    
    def start_monitoring(self, total_steps: int = 0):
        """开始监控"""
        self.metrics = MonitoringMetrics(
            start_time=datetime.now(),
            total_steps=total_steps
        )
        self.is_monitoring = True
        self.last_update_time = datetime.now()
        
        self.notify("监控开始", "WaterNet自动化更新系统监控已启动", "info")
    
    def stop_monitoring(self):
        """停止监控"""
        if self.metrics:
            duration = datetime.now() - self.metrics.start_time
            self.notify(
                "监控结束", 
                f"更新过程完成，总耗时: {duration.total_seconds():.1f}秒",
                "success"
            )
        
        self.is_monitoring = False
    
    def update_progress(self, step_name: str, progress: float = None):
        """更新进度"""
        if not self.is_monitoring or not self.metrics:
            return
        
        self.metrics.current_step = step_name
        
        if progress is not None:
            self.metrics.progress_percentage = min(100.0, max(0.0, progress))
        elif self.metrics.total_steps > 0:
            self.metrics.progress_percentage = (self.metrics.steps_completed / self.metrics.total_steps) * 100
        
        self.last_update_time = datetime.now()
        
        # 调用状态回调
        for callback in self.status_callbacks:
            try:
                callback(self.metrics)
            except Exception as e:
                print(f"状态回调执行失败: {e}")
    
    def complete_step(self, step_name: str, success: bool = True, details: str = ""):
        """完成步骤"""
        if not self.is_monitoring or not self.metrics:
            return
        
        self.metrics.steps_completed += 1
        
        if success:
            level = "success"
            message = f"步骤 '{step_name}' 完成"
        else:
            level = "error"
            message = f"步骤 '{step_name}' 失败"
            self.metrics.errors_count += 1
        
        if details:
            message += f": {details}"
        
        self.notify(f"步骤更新", message, level)
        self.update_progress(step_name)
    
    def add_warning(self, title: str, message: str):
        """添加警告"""
        if self.metrics:
            self.metrics.warnings_count += 1
        
        self.notify(title, message, "warning")
    
    def add_error(self, title: str, message: str):
        """添加错误"""
        if self.metrics:
            self.metrics.errors_count += 1
        
        self.notify(title, message, "error")
    
    def record_performance_metric(self, name: str, value: float):
        """记录性能指标"""
        if self.metrics:
            self.metrics.performance_metrics[name] = value
    
    def record_resource_usage(self):
        """记录资源使用情况"""
        if not self.metrics:
            return
        
        try:
            import psutil
            
            self.metrics.resource_usage.update({
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_usage_percent': psutil.disk_usage('/').percent
            })
            
        except ImportError:
            # psutil不可用时跳过
            pass
        except Exception as e:
            print(f"资源使用情况记录失败: {e}")
    
    def notify(self, title: str, message: str, level: str = "info", metadata: Dict[str, Any] = None):
        """发送通知"""
        notification = NotificationMessage(
            title=title,
            message=message,
            level=level,
            metadata=metadata or {}
        )
        
        # 发送到所有启用的通知器
        for notifier in self.notifiers:
            try:
                notifier.send(notification)
            except Exception as e:
                print(f"通知器 {notifier.name} 发送失败: {e}")
    
    def add_status_callback(self, callback: Callable[[MonitoringMetrics], None]):
        """添加状态回调函数"""
        self.status_callbacks.append(callback)
    
    def get_status_summary(self) -> Dict[str, Any]:
        """获取状态摘要"""
        if not self.metrics:
            return {'status': 'not_monitoring'}
        
        duration = datetime.now() - self.metrics.start_time
        
        return {
            'status': 'monitoring' if self.is_monitoring else 'completed',
            'current_step': self.metrics.current_step,
            'progress_percentage': self.metrics.progress_percentage,
            'steps_completed': self.metrics.steps_completed,
            'total_steps': self.metrics.total_steps,
            'duration_seconds': duration.total_seconds(),
            'errors_count': self.metrics.errors_count,
            'warnings_count': self.metrics.warnings_count,
            'performance_metrics': self.metrics.performance_metrics,
            'resource_usage': self.metrics.resource_usage
        }
    
    def generate_report(self) -> str:
        """生成监控报告"""
        if not self.metrics:
            return "没有监控数据"
        
        summary = self.get_status_summary()
        
        report = f"""
WaterNet 自动化更新 - 监控报告
==========================================

执行时间: {self.metrics.start_time.strftime('%Y-%m-%d %H:%M:%S')}
总耗时: {summary['duration_seconds']:.1f} 秒

进度统计:
- 当前步骤: {summary['current_step']}
- 完成进度: {summary['progress_percentage']:.1f}%
- 完成步骤: {summary['steps_completed']}/{summary['total_steps']}

问题统计:
- 错误数量: {summary['errors_count']}
- 警告数量: {summary['warnings_count']}

性能指标:
"""
        
        for name, value in summary['performance_metrics'].items():
            report += f"- {name}: {value:.2f}\n"
        
        if summary['resource_usage']:
            report += "\n资源使用:\n"
            for name, value in summary['resource_usage'].items():
                report += f"- {name}: {value:.1f}%\n"
        
        return report


def create_monitoring_system(config: Dict[str, Any] = None) -> MonitoringSystem:
    """创建监控系统实例"""
    default_config = {
        'notifiers': {
            'console': {'enabled': True, 'use_colors': True},
            'file': {'enabled': True, 'log_file': 'logs/update_notifications.log'},
            'email': {'enabled': False},
            'webhook': {'enabled': False},
            'slack': {'enabled': False}
        }
    }
    
    if config:
        # 合并配置
        for key, value in config.items():
            if key in default_config and isinstance(value, dict):
                default_config[key].update(value)
            else:
                default_config[key] = value
    
    return MonitoringSystem(default_config)


if __name__ == '__main__':
    # 演示监控系统的使用
    print("🔍 WaterNet 监控系统演示")
    
    # 创建监控系统
    monitor = create_monitoring_system()
    
    # 开始监控
    monitor.start_monitoring(total_steps=5)
    
    # 模拟更新过程
    steps = [
        "系统预检查",
        "创建备份", 
        "更新依赖",
        "运行测试",
        "最终验证"
    ]
    
    for i, step in enumerate(steps):
        monitor.update_progress(step, (i / len(steps)) * 100)
        time.sleep(1)  # 模拟处理时间
        
        if i == 2:  # 在第3步添加一个警告
            monitor.add_warning("依赖警告", "某些包版本可能不兼容")
        
        monitor.complete_step(step, success=True, details=f"步骤{i+1}执行成功")
    
    # 记录性能指标
    monitor.record_performance_metric("average_step_time", 1.2)
    monitor.record_resource_usage()
    
    # 停止监控
    monitor.stop_monitoring()
    
    # 生成报告
    print("\n" + monitor.generate_report())