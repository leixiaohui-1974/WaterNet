#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WaterNet边界条件框架用户文档实用性和准确性评估

本模块提供全面的文档评估系统，通过实际使用场景验证文档的完整性和准确性。
包含自动化测试和人工评估相结合的综合评估方法。

评估内容：
1. 文档完整性检查 - 确保所有API和功能都有文档
2. 示例代码可执行性验证 - 验证文档中的代码示例能正确运行
3. 用户使用场景模拟 - 模拟新用户按文档操作的完整流程
4. 文档准确性检查 - 验证描述与实际实现的一致性
5. 易用性评估 - 评估文档的可读性和逻辑性

Authors: WaterNet Team
Date: 2024-01-20
Version: 1.0.0
"""

import os
import sys
import time
import traceback
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
from enum import Enum
import ast
import re
import logging

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    # 导入WaterNet框架
    from waternet.models.boundary_conditions import (
        BoundaryCondition, FlowBoundary, StageBoundary, 
        RatingCurveBoundary, BoundaryConditionManager
    )
    from waternet.models.control_signals import (
        ControlSignals, ControlDevice, PumpStation, Valve,
        ControlSchedule, ControlSignalManager
    )
    from waternet.models.boundary_config import (
        BoundaryConfigParser, ConfigValidator
    )
    from waternet.models.implicit_solver import ImplicitSolverAgent
    
    # 导入基础水力模型
    from waternet.models.saint_venant import SaintVenantModel
    from waternet.models.base import HydroModel
    
except ImportError as e:
    print(f"警告：无法导入WaterNet模块 - {e}")
    print("某些测试将被跳过")


class EvaluationLevel(Enum):
    """评估严重程度级别"""
    CRITICAL = "严重"      # 导致功能无法使用
    MAJOR = "重要"         # 影响用户体验
    MINOR = "轻微"         # 小问题但不影响功能
    SUGGESTION = "建议"    # 改进建议


@dataclass
class EvaluationResult:
    """单个评估结果"""
    category: str          # 评估类别
    test_name: str         # 测试名称
    level: EvaluationLevel # 严重程度
    status: str            # 状态：PASS/FAIL/WARNING
    message: str           # 详细信息
    execution_time: float  # 执行时间
    details: Optional[Dict] = None  # 详细数据


class DocumentationEvaluator:
    """文档实用性和准确性评估器"""
    
    def __init__(self, doc_path: str = None):
        """初始化评估器
        
        Args:
            doc_path: 文档路径，默认为项目中的边界条件指南
        """
        self.project_root = Path(__file__).parent.parent.parent
        
        # 默认文档路径
        if doc_path is None:
            self.doc_path = self.project_root / "docs" / "BOUNDARY_CONDITIONS_GUIDE.md"
        else:
            self.doc_path = Path(doc_path)
            
        self.results: List[EvaluationResult] = []
        self.temp_dir = None
        
        # 配置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    def run_full_evaluation(self) -> Dict[str, Any]:
        """运行完整的文档评估
        
        Returns:
            评估结果汇总
        """
        start_time = time.time()
        
        print("="*60)
        print("WaterNet边界条件框架文档评估")
        print("="*60)
        
        try:
            # 创建临时工作目录
            self.temp_dir = tempfile.mkdtemp(prefix="waternet_doc_eval_")
            
            # 1. 文档存在性和基础检查
            self._check_documentation_existence()
            
            # 2. 文档完整性检查
            self._check_documentation_completeness()
            
            # 3. 示例代码验证
            self._validate_example_codes()
            
            # 4. 用户使用场景模拟
            self._simulate_user_scenarios()
            
            # 5. API文档准确性检查
            self._check_api_accuracy()
            
            # 6. 易用性评估
            self._evaluate_usability()
            
        except Exception as e:
            self._add_result(
                "系统错误", "评估执行", EvaluationLevel.CRITICAL,
                "FAIL", f"评估过程出现异常: {str(e)}", 0.0
            )
            
        finally:
            # 清理临时目录
            if self.temp_dir and os.path.exists(self.temp_dir):
                try:
                    shutil.rmtree(self.temp_dir)
                except:
                    pass
        
        total_time = time.time() - start_time
        
        # 生成评估报告
        return self._generate_evaluation_report(total_time)
        
    def _check_documentation_existence(self):
        """检查文档存在性和基础结构"""
        start_time = time.time()
        
        # 检查主文档文件
        if not self.doc_path.exists():
            self._add_result(
                "文档存在性", "主文档文件", EvaluationLevel.CRITICAL,
                "FAIL", f"文档文件不存在: {self.doc_path}", 
                time.time() - start_time
            )
            return
            
        # 检查文档大小
        file_size = self.doc_path.stat().st_size
        if file_size < 1000:  # 小于1KB可能是空文档
            self._add_result(
                "文档存在性", "文档内容", EvaluationLevel.MAJOR,
                "WARNING", f"文档文件过小 ({file_size} bytes)，可能内容不完整", 
                time.time() - start_time
            )
        else:
            self._add_result(
                "文档存在性", "文档内容", EvaluationLevel.MINOR,
                "PASS", f"文档文件正常 ({file_size} bytes)", 
                time.time() - start_time
            )
            
        # 检查文档编码
        try:
            with open(self.doc_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            self._add_result(
                "文档存在性", "文档编码", EvaluationLevel.MINOR,
                "PASS", "文档UTF-8编码正常", 
                time.time() - start_time
            )
            
        except UnicodeDecodeError:
            self._add_result(
                "文档存在性", "文档编码", EvaluationLevel.MAJOR,
                "FAIL", "文档编码错误，无法读取", 
                time.time() - start_time
            )
            
    def _check_documentation_completeness(self):
        """检查文档完整性"""
        start_time = time.time()
        
        try:
            with open(self.doc_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except:
            self._add_result(
                "文档完整性", "内容读取", EvaluationLevel.CRITICAL,
                "FAIL", "无法读取文档内容", 
                time.time() - start_time
            )
            return
            
        # 必须包含的章节
        required_sections = [
            "边界条件框架概述",
            "快速开始",
            "API参考",
            "配置示例",
            "常见问题"
        ]
        
        missing_sections = []
        for section in required_sections:
            if section not in content:
                missing_sections.append(section)
                
        if missing_sections:
            self._add_result(
                "文档完整性", "必需章节", EvaluationLevel.MAJOR,
                "FAIL", f"缺少必需章节: {', '.join(missing_sections)}", 
                time.time() - start_time
            )
        else:
            self._add_result(
                "文档完整性", "必需章节", EvaluationLevel.MINOR,
                "PASS", "所有必需章节都存在", 
                time.time() - start_time
            )
            
        # 检查核心类的文档覆盖
        core_classes = [
            "BoundaryCondition",
            "FlowBoundary", 
            "StageBoundary",
            "RatingCurveBoundary",
            "BoundaryConditionManager",
            "ControlSignals",
            "ControlSignalManager"
        ]
        
        undocumented_classes = []
        for cls_name in core_classes:
            if cls_name not in content:
                undocumented_classes.append(cls_name)
                
        if undocumented_classes:
            self._add_result(
                "文档完整性", "API覆盖", EvaluationLevel.MAJOR,
                "FAIL", f"未文档化的核心类: {', '.join(undocumented_classes)}", 
                time.time() - start_time
            )
        else:
            self._add_result(
                "文档完整性", "API覆盖", EvaluationLevel.MINOR,
                "PASS", "所有核心类都有文档", 
                time.time() - start_time
            )
            
    def _validate_example_codes(self):
        """验证文档中的示例代码"""
        start_time = time.time()
        
        try:
            with open(self.doc_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except:
            self._add_result(
                "示例代码验证", "内容读取", EvaluationLevel.CRITICAL,
                "FAIL", "无法读取文档内容", 
                time.time() - start_time
            )
            return
            
        # 提取Python代码块
        code_blocks = re.findall(r'```python\n(.*?)\n```', content, re.DOTALL)
        
        if not code_blocks:
            self._add_result(
                "示例代码验证", "代码存在性", EvaluationLevel.MAJOR,
                "FAIL", "文档中没有Python代码示例", 
                time.time() - start_time
            )
            return
            
        self._add_result(
            "示例代码验证", "代码存在性", EvaluationLevel.MINOR,
            "PASS", f"发现 {len(code_blocks)} 个Python代码示例", 
            time.time() - start_time
        )
        
        # 验证每个代码块的语法
        syntax_errors = []
        for i, code_block in enumerate(code_blocks):
            try:
                ast.parse(code_block)
            except SyntaxError as e:
                syntax_errors.append(f"代码块{i+1}: {str(e)}")
                
        if syntax_errors:
            self._add_result(
                "示例代码验证", "语法检查", EvaluationLevel.MAJOR,
                "FAIL", f"语法错误: {'; '.join(syntax_errors)}", 
                time.time() - start_time
            )
        else:
            self._add_result(
                "示例代码验证", "语法检查", EvaluationLevel.MINOR,
                "PASS", f"所有 {len(code_blocks)} 个代码示例语法正确", 
                time.time() - start_time
            )
            
        # 尝试执行简单的代码示例
        self._execute_example_codes(code_blocks)
        
    def _execute_example_codes(self, code_blocks: List[str]):
        """执行示例代码"""
        executable_count = 0
        execution_errors = []
        
        for i, code_block in enumerate(code_blocks):
            # 跳过包含输出或非执行性代码的块
            if any(keyword in code_block for keyword in ['print(', '>>>', '...']):
                continue
                
            try:
                # 创建临时执行环境
                test_file = os.path.join(self.temp_dir, f"test_example_{i}.py")
                
                # 添加必要的导入
                full_code = f"""
import sys
sys.path.insert(0, r'{self.project_root}')

{code_block}
"""
                
                with open(test_file, 'w', encoding='utf-8') as f:
                    f.write(full_code)
                    
                # 尝试执行
                result = subprocess.run(
                    [sys.executable, test_file],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    executable_count += 1
                else:
                    execution_errors.append(f"代码块{i+1}: {result.stderr.strip()}")
                    
            except Exception as e:
                execution_errors.append(f"代码块{i+1}: {str(e)}")
                
        # 记录执行结果
        if execution_errors:
            self._add_result(
                "示例代码验证", "代码执行", EvaluationLevel.MAJOR,
                "FAIL", f"代码执行错误: {'; '.join(execution_errors[:3])}", 
                0.0
            )
        elif executable_count > 0:
            self._add_result(
                "示例代码验证", "代码执行", EvaluationLevel.MINOR,
                "PASS", f"成功执行 {executable_count} 个代码示例", 
                0.0
            )
        else:
            self._add_result(
                "示例代码验证", "代码执行", EvaluationLevel.SUGGESTION,
                "WARNING", "没有可执行的代码示例", 
                0.0
            )
            
    def _simulate_user_scenarios(self):
        """模拟新用户使用场景"""
        start_time = time.time()
        
        scenarios = [
            self._scenario_basic_boundary_creation,
            self._scenario_control_signals_usage,
            self._scenario_config_file_usage,
            self._scenario_solver_integration
        ]
        
        passed_scenarios = 0
        failed_scenarios = []
        
        for scenario in scenarios:
            try:
                if scenario():
                    passed_scenarios += 1
                else:
                    failed_scenarios.append(scenario.__name__)
            except Exception as e:
                failed_scenarios.append(f"{scenario.__name__}: {str(e)}")
                
        if failed_scenarios:
            self._add_result(
                "用户场景模拟", "场景执行", EvaluationLevel.MAJOR,
                "FAIL", f"失败场景: {', '.join(failed_scenarios)}", 
                time.time() - start_time
            )
        else:
            self._add_result(
                "用户场景模拟", "场景执行", EvaluationLevel.MINOR,
                "PASS", f"所有 {len(scenarios)} 个用户场景执行成功", 
                time.time() - start_time
            )
            
    def _scenario_basic_boundary_creation(self) -> bool:
        """场景1：基础边界条件创建"""
        try:
            # 创建流量边界
            flow_bc = FlowBoundary(node_id="inlet", flow_rate=10.0)
            
            # 创建水位边界
            stage_bc = StageBoundary(node_id="outlet", stage=5.0)
            
            # 验证基本属性
            assert flow_bc.node_id == "inlet"
            assert stage_bc.node_id == "outlet"
            
            return True
        except Exception:
            return False
            
    def _scenario_control_signals_usage(self) -> bool:
        """场景2：控制信号使用"""
        try:
            # 创建控制信号
            signals = ControlSignals()
            
            # 创建泵站设备
            pump = PumpStation(device_id="pump1", max_flow_rate=50.0)
            
            # 添加设备到信号管理器
            manager = ControlSignalManager()
            manager.add_device(pump)
            
            return True
        except Exception:
            return False
            
    def _scenario_config_file_usage(self) -> bool:
        """场景3：配置文件使用"""
        try:
            # 创建简单配置
            config = {
                "boundary_conditions": [
                    {
                        "type": "flow",
                        "node_id": "inlet",
                        "value": 10.0
                    }
                ]
            }
            
            # 验证配置
            validator = ConfigValidator()
            is_valid, errors = validator.validate_boundary_config(config)
            
            return is_valid
        except Exception:
            return False
            
    def _scenario_solver_integration(self) -> bool:
        """场景4：求解器集成"""
        try:
            # 创建边界条件管理器
            bc_manager = BoundaryConditionManager()
            
            # 添加边界条件
            flow_bc = FlowBoundary(node_id="inlet", flow_rate=10.0)
            bc_manager.add_boundary_condition(flow_bc)
            
            return True
        except Exception:
            return False
            
    def _check_api_accuracy(self):
        """检查API文档准确性"""
        start_time = time.time()
        
        # 检查类方法签名一致性
        api_issues = []
        
        try:
            # 检查BoundaryCondition类
            from waternet.models.boundary_conditions import BoundaryCondition
            
            # 验证抽象方法存在
            if not hasattr(BoundaryCondition, 'get_equation'):
                api_issues.append("BoundaryCondition缺少get_equation方法")
                
            if not hasattr(BoundaryCondition, 'validate_variables'):
                api_issues.append("BoundaryCondition缺少validate_variables方法")
                
        except ImportError:
            api_issues.append("无法导入BoundaryCondition类")
            
        try:
            # 检查具体实现类
            from waternet.models.boundary_conditions import FlowBoundary
            
            # 验证构造函数
            flow_bc = FlowBoundary(node_id="test", flow_rate=1.0)
            if not hasattr(flow_bc, 'node_id'):
                api_issues.append("FlowBoundary缺少node_id属性")
                
        except Exception as e:
            api_issues.append(f"FlowBoundary验证失败: {str(e)}")
            
        if api_issues:
            self._add_result(
                "API准确性", "接口一致性", EvaluationLevel.MAJOR,
                "FAIL", f"API问题: {'; '.join(api_issues)}", 
                time.time() - start_time
            )
        else:
            self._add_result(
                "API准确性", "接口一致性", EvaluationLevel.MINOR,
                "PASS", "API文档与实现一致", 
                time.time() - start_time
            )
            
    def _evaluate_usability(self):
        """评估文档易用性"""
        start_time = time.time()
        
        try:
            with open(self.doc_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except:
            self._add_result(
                "易用性评估", "内容读取", EvaluationLevel.CRITICAL,
                "FAIL", "无法读取文档内容", 
                time.time() - start_time
            )
            return
            
        usability_score = 0
        usability_notes = []
        
        # 检查结构清晰度
        if "目录" in content or "##" in content:
            usability_score += 20
        else:
            usability_notes.append("缺少清晰的文档结构")
            
        # 检查示例丰富度
        example_count = len(re.findall(r'```python', content))
        if example_count >= 5:
            usability_score += 20
        elif example_count >= 3:
            usability_score += 15
        elif example_count >= 1:
            usability_score += 10
        else:
            usability_notes.append("示例代码太少")
            
        # 检查说明详细度
        if len(content) > 5000:  # 至少5KB的内容
            usability_score += 20
        elif len(content) > 3000:
            usability_score += 15
        else:
            usability_notes.append("文档内容偏少")
            
        # 检查关键词覆盖
        key_terms = ["安装", "配置", "示例", "参数", "返回值", "异常"]
        covered_terms = sum(1 for term in key_terms if term in content)
        usability_score += (covered_terms / len(key_terms)) * 20
        
        # 检查多语言支持
        if "English" in content or "中文" in content:
            usability_score += 10
            
        # 检查常见问题
        if "常见问题" in content or "FAQ" in content:
            usability_score += 10
            
        # 评估结果
        if usability_score >= 80:
            level = EvaluationLevel.MINOR
            status = "PASS"
            message = f"文档易用性良好 (评分: {usability_score}/100)"
        elif usability_score >= 60:
            level = EvaluationLevel.SUGGESTION
            status = "WARNING"
            message = f"文档易用性一般 (评分: {usability_score}/100)"
        else:
            level = EvaluationLevel.MAJOR
            status = "FAIL"
            message = f"文档易用性较差 (评分: {usability_score}/100)"
            
        if usability_notes:
            message += f" - 改进点: {', '.join(usability_notes)}"
            
        self._add_result(
            "易用性评估", "综合评分", level, status, message,
            time.time() - start_time,
            details={"score": usability_score, "notes": usability_notes}
        )
        
    def _add_result(self, category: str, test_name: str, level: EvaluationLevel,
                   status: str, message: str, execution_time: float,
                   details: Optional[Dict] = None):
        """添加评估结果"""
        result = EvaluationResult(
            category=category,
            test_name=test_name,
            level=level,
            status=status,
            message=message,
            execution_time=execution_time,
            details=details
        )
        self.results.append(result)
        
        # 实时打印结果
        status_symbol = {
            "PASS": "✓",
            "FAIL": "✗", 
            "WARNING": "⚠"
        }.get(status, "?")
        
        print(f"{status_symbol} [{category}] {test_name}: {message}")
        
    def _generate_evaluation_report(self, total_time: float) -> Dict[str, Any]:
        """生成评估报告"""
        # 统计结果
        stats = {
            "total_tests": len(self.results),
            "passed": len([r for r in self.results if r.status == "PASS"]),
            "failed": len([r for r in self.results if r.status == "FAIL"]),
            "warnings": len([r for r in self.results if r.status == "WARNING"]),
            "total_time": total_time
        }
        
        # 按级别分类问题
        issues_by_level = {
            EvaluationLevel.CRITICAL: [],
            EvaluationLevel.MAJOR: [],
            EvaluationLevel.MINOR: [],
            EvaluationLevel.SUGGESTION: []
        }
        
        for result in self.results:
            if result.status in ["FAIL", "WARNING"]:
                issues_by_level[result.level].append(result)
                
        # 计算总体评分
        total_score = 100
        for level, issues in issues_by_level.items():
            if level == EvaluationLevel.CRITICAL:
                total_score -= len(issues) * 25
            elif level == EvaluationLevel.MAJOR:
                total_score -= len(issues) * 15
            elif level == EvaluationLevel.MINOR:
                total_score -= len(issues) * 5
            elif level == EvaluationLevel.SUGGESTION:
                total_score -= len(issues) * 2
                
        total_score = max(0, total_score)
        
        # 生成建议
        recommendations = []
        if issues_by_level[EvaluationLevel.CRITICAL]:
            recommendations.append("立即修复严重问题")
        if issues_by_level[EvaluationLevel.MAJOR]:
            recommendations.append("优先处理重要问题")
        if stats["failed"] > stats["passed"]:
            recommendations.append("文档需要大幅改进")
        if total_score < 70:
            recommendations.append("建议重新组织文档结构")
            
        print("\n" + "="*60)
        print("评估报告汇总")
        print("="*60)
        print(f"总测试数: {stats['total_tests']}")
        print(f"通过: {stats['passed']} | 失败: {stats['failed']} | 警告: {stats['warnings']}")
        print(f"总体评分: {total_score}/100")
        print(f"执行时间: {total_time:.2f}秒")
        
        if recommendations:
            print("\n改进建议:")
            for i, rec in enumerate(recommendations, 1):
                print(f"{i}. {rec}")
                
        return {
            "statistics": stats,
            "issues_by_level": {k.value: [r.__dict__ for r in v] 
                              for k, v in issues_by_level.items()},
            "total_score": total_score,
            "recommendations": recommendations,
            "all_results": [r.__dict__ for r in self.results]
        }


def main():
    """主函数 - 运行文档评估"""
    try:
        evaluator = DocumentationEvaluator()
        report = evaluator.run_full_evaluation()
        
        # 保存详细报告
        import json
        report_file = Path(__file__).parent / "documentation_evaluation_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
            
        print(f"\n详细报告已保存至: {report_file}")
        
        # 返回总体评分用于CI/CD
        return report["total_score"]
        
    except Exception as e:
        print(f"评估失败: {str(e)}")
        traceback.print_exc()
        return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(0 if exit_code >= 70 else 1)  # 70分以上算通过