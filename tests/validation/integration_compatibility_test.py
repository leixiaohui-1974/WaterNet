"""
WaterNet模块集成兼容性测试

验证边界条件框架与现有WaterNet模块的无缝集成
确保向后兼容性和功能完整性

Author: WaterNet Development Team
Date: 2024-10-04
"""

import numpy as np
import logging
import time
import traceback
from typing import Dict, List, Any, Tuple
from pathlib import Path

# 导入WaterNet核心模块
from waternet.models.boundary_conditions import *
from waternet.models.control_signals import *
from waternet.models.implicit_solver import *
from waternet.models.saint_venant import SaintVenantModel
from waternet.models.lumped_models import *
from waternet.coordination.twinning_harness import *
from waternet.interfaces.hydro_model import HydroModel

logger = logging.getLogger(__name__)


class IntegrationCompatibilityTester:
    """集成兼容性测试器"""
    
    def __init__(self):
        self.test_results = []
        self.compatibility_matrix = {}
        
    def test_saint_venant_integration(self) -> Dict[str, Any]:
        """测试与圣维南模型的集成"""
        logger.info("测试与圣维南模型的集成兼容性")
        
        result = {
            'test_name': 'saint_venant_integration',
            'status': 'unknown',
            'details': {},
            'errors': []
        }
        
        try:
            # 创建简化的圣维南模型
            sections = [
                {
                    'mileage': 0.0,
                    'elevation': 100.0,
                    'roughness': 0.025,
                    'area_func': lambda h: max(0, 10 * (h - 100.0)),
                    'top_width_func': lambda h: 10.0 if h > 100.0 else 0.0
                },
                {
                    'mileage': 1000.0,
                    'elevation': 99.5,
                    'roughness': 0.025,
                    'area_func': lambda h: max(0, 10 * (h - 99.5)),
                    'top_width_func': lambda h: 10.0 if h > 99.5 else 0.0
                }
            ]
            
            # 创建圣维南模型
            sv_model = SaintVenantModel("test_channel", "upstream", "downstream", sections)
            
            # 创建边界条件
            boundary_manager = BoundaryConditionManager()
            
            # 上游流量边界
            config1 = BoundaryConditionConfig("upstream_flow", "上游流量边界")
            flow_bc = FlowBoundary("upstream_flow", "upstream", 50.0, config1)
            boundary_manager.add_boundary_condition(flow_bc)
            
            # 下游水位边界
            config2 = BoundaryConditionConfig("downstream_stage", "下游水位边界")
            stage_bc = StageBoundary("downstream_stage", "downstream", 100.0, config2)
            boundary_manager.add_boundary_condition(stage_bc)
            
            # 测试与隐式求解器的集成
            solver = ImplicitSolverAgent([sv_model], None, boundary_manager)
            
            # 初始条件
            initial_conditions = {
                'H_upstream': 101.0,
                'H_downstream': 100.0,
                'Q_test_channel_seg_0': 45.0
            }
            
            # 尝试求解
            solve_result = solver.solve_steady_state(initial_conditions)
            
            result['details'].update({
                'model_created': True,
                'boundary_conditions_added': boundary_manager.get_boundary_condition_count(),
                'solver_created': True,
                'solve_converged': solve_result['converged'],
                'solve_iterations': solve_result['statistics'].total_iterations
            })
            
            if solve_result['converged']:
                result['status'] = 'success'
                logger.info("✅ 圣维南模型集成测试成功")
            else:
                result['status'] = 'partial'
                result['errors'].append("求解未收敛")
                logger.warning("⚠️ 圣维南模型求解未收敛")
                
        except Exception as e:
            result['status'] = 'failed'
            result['errors'].append(str(e))
            logger.error(f"❌ 圣维南模型集成测试失败: {e}")
            traceback.print_exc()
        
        return result
    
    def test_lumped_models_integration(self) -> Dict[str, Any]:
        """测试与降阶模型的集成"""
        logger.info("测试与降阶模型的集成兼容性")
        
        result = {
            'test_name': 'lumped_models_integration',
            'status': 'unknown',
            'details': {},
            'errors': []
        }
        
        try:
            # 测试不同类型的降阶模型
            models_tested = []
            
            # 水量平衡模型
            try:
                wb_model = WaterBalanceModel("wb_test", ["inlet"], ["outlet"])
                models_tested.append("WaterBalanceModel")
            except Exception as e:
                result['errors'].append(f"WaterBalanceModel创建失败: {e}")
            
            # 蓄量演算模型
            try:
                sr_model = StorageRoutingModel("sr_test", ["inlet"], ["outlet"], K=3600, X=0.2)
                models_tested.append("StorageRoutingModel")
            except Exception as e:
                result['errors'].append(f"StorageRoutingModel创建失败: {e}")
            
            # 马斯京干模型
            try:
                mk_model = MuskingumModel("mk_test", ["inlet"], ["outlet"], K=3600, X=0.2)
                models_tested.append("MuskingumModel")
            except Exception as e:
                result['errors'].append(f"MuskingumModel创建失败: {e}")
            
            # IDZ模型
            try:
                idz_model = IntegralDelayZeroModel("idz_test", ["inlet"], ["outlet"], T=1800, K=3600)
                models_tested.append("IntegralDelayZeroModel")
            except Exception as e:
                result['errors'].append(f"IntegralDelayZeroModel创建失败: {e}")
            
            result['details']['models_tested'] = models_tested
            result['details']['models_count'] = len(models_tested)
            
            # 如果有模型成功创建，测试边界条件集成
            if models_tested:
                # 使用第一个成功创建的模型进行边界条件测试
                test_model_name = models_tested[0]
                
                if test_model_name == "WaterBalanceModel":
                    test_model = wb_model
                elif test_model_name == "StorageRoutingModel":
                    test_model = sr_model
                elif test_model_name == "MuskingumModel":
                    test_model = mk_model
                else:  # IDZ
                    test_model = idz_model
                
                # 创建边界条件
                boundary_manager = BoundaryConditionManager()
                config = BoundaryConditionConfig("inlet_flow", "入流边界")
                flow_bc = FlowBoundary("inlet_flow", "inlet", 30.0, config)
                boundary_manager.add_boundary_condition(flow_bc)
                
                # 测试step方法集成（降阶模型特有）
                if hasattr(test_model, 'step'):
                    step_result = test_model.step(Q_in=30.0, dt=300.0)
                    result['details']['step_method_works'] = True
                    result['details']['step_result'] = step_result is not None
                
                result['status'] = 'success'
                logger.info(f"✅ 降阶模型集成测试成功，测试了 {len(models_tested)} 个模型")
            else:
                result['status'] = 'failed'
                result['errors'].append("所有降阶模型创建都失败了")
                logger.error("❌ 所有降阶模型创建都失败了")
                
        except Exception as e:
            result['status'] = 'failed'
            result['errors'].append(str(e))
            logger.error(f"❌ 降阶模型集成测试失败: {e}")
            traceback.print_exc()
        
        return result
    
    def test_configuration_backward_compatibility(self) -> Dict[str, Any]:
        """测试配置文件向后兼容性"""
        logger.info("测试配置文件向后兼容性")
        
        result = {
            'test_name': 'configuration_backward_compatibility',
            'status': 'unknown',
            'details': {},
            'errors': []
        }
        
        try:
            # 测试传统配置格式
            traditional_config = {
                'boundary_conditions': [
                    {
                        'name': 'test_flow',
                        'type': 'flow_boundary',
                        'node_name': 'upstream',
                        'flow_value': 50.0
                    }
                ]
            }
            
            # 验证新解析器能处理传统格式
            from waternet.models.boundary_config import BoundaryConfigParser
            parser = BoundaryConfigParser()
            
            boundary_manager = parser.parse_from_dict(traditional_config)
            result['details']['traditional_config_parsed'] = True
            result['details']['boundary_count'] = boundary_manager.get_boundary_condition_count()
            
            # 测试传统求解器接口
            from waternet.models.implicit_solver import solve_hydraulic_network
            
            # 创建简单模型用于测试
            from waternet.interfaces.hydro_model import DummyModel
            models = [DummyModel("test", "upstream", "downstream")]
            
            # 测试传统接口（不包含边界条件参数）
            initial_conditions = {'H_upstream': 101.0, 'H_downstream': 100.0, 'Q_test': 45.0}
            
            try:
                traditional_result = solve_hydraulic_network(models, initial_conditions)
                result['details']['traditional_solver_works'] = traditional_result['converged']
            except Exception as e:
                result['errors'].append(f"传统求解器接口失败: {e}")
            
            # 测试新接口（包含边界条件参数）
            try:
                enhanced_result = solve_hydraulic_network(
                    models, initial_conditions, None, boundary_manager, None
                )
                result['details']['enhanced_solver_works'] = enhanced_result['converged']
            except Exception as e:
                result['errors'].append(f"增强求解器接口失败: {e}")
            
            if not result['errors']:
                result['status'] = 'success'
                logger.info("✅ 配置文件向后兼容性测试成功")
            else:
                result['status'] = 'partial'
                logger.warning("⚠️ 配置文件兼容性存在部分问题")
                
        except Exception as e:
            result['status'] = 'failed'
            result['errors'].append(str(e))
            logger.error(f"❌ 配置文件兼容性测试失败: {e}")
            traceback.print_exc()
        
        return result
    
    def test_api_compatibility(self) -> Dict[str, Any]:
        """测试API向后兼容性"""
        logger.info("测试API向后兼容性")
        
        result = {
            'test_name': 'api_compatibility',
            'status': 'unknown',
            'details': {},
            'errors': []
        }
        
        try:
            compatibility_checks = []
            
            # 检查核心接口是否保持
            api_checks = [
                ('BoundaryCondition', 'waternet.models.boundary_conditions'),
                ('FlowBoundary', 'waternet.models.boundary_conditions'),
                ('StageBoundary', 'waternet.models.boundary_conditions'),
                ('ImplicitSolverAgent', 'waternet.models.implicit_solver'),
                ('solve_hydraulic_network', 'waternet.models.implicit_solver'),
                ('ControlSignalManager', 'waternet.models.control_signals'),
                ('create_gate_device', 'waternet.models.control_signals')
            ]
            
            for api_name, module_name in api_checks:
                try:
                    module = __import__(module_name, fromlist=[api_name])
                    api_obj = getattr(module, api_name)
                    compatibility_checks.append(f"{api_name}: ✅")
                except (ImportError, AttributeError) as e:
                    compatibility_checks.append(f"{api_name}: ❌ {e}")
                    result['errors'].append(f"API {api_name} 不可用: {e}")
            
            result['details']['api_checks'] = compatibility_checks
            
            # 测试方法签名兼容性
            try:
                from waternet.models.boundary_conditions import FlowBoundary
                
                # 测试传统构造方法
                config = BoundaryConditionConfig("test", "测试")
                fb = FlowBoundary("test", "node1", 50.0, config)
                
                # 测试核心方法存在
                methods_exist = [
                    hasattr(fb, 'get_equation'),
                    hasattr(fb, 'get_required_variables'),
                    hasattr(fb, 'validate_variables')
                ]
                
                result['details']['method_compatibility'] = all(methods_exist)
                
            except Exception as e:
                result['errors'].append(f"方法签名兼容性检查失败: {e}")
            
            if not result['errors']:
                result['status'] = 'success'
                logger.info("✅ API向后兼容性测试成功")
            else:
                result['status'] = 'partial'
                logger.warning("⚠️ API兼容性存在部分问题")
                
        except Exception as e:
            result['status'] = 'failed'
            result['errors'].append(str(e))
            logger.error(f"❌ API兼容性测试失败: {e}")
            traceback.print_exc()
        
        return result
    
    def test_performance_regression(self) -> Dict[str, Any]:
        """测试性能回归"""
        logger.info("测试性能回归")
        
        result = {
            'test_name': 'performance_regression',
            'status': 'unknown',
            'details': {},
            'errors': []
        }
        
        try:
            # 创建基准测试系统
            from waternet.interfaces.hydro_model import DummyModel
            
            # 传统求解器性能
            models = [DummyModel(f"model_{i}", f"node_{i}", f"node_{i+1}") for i in range(10)]
            initial_conditions = {}
            
            for i, model in enumerate(models):
                for var in model.get_variable_names():
                    if var.startswith('H_'):
                        initial_conditions[var] = 100.0
                    elif var.startswith('Q_'):
                        initial_conditions[var] = 20.0
            
            # 测试传统求解器
            start_time = time.time()
            traditional_solver = ImplicitSolverAgent(models)
            traditional_result = traditional_solver.solve_steady_state(initial_conditions)
            traditional_time = time.time() - start_time
            
            # 测试增强求解器（带边界条件）
            boundary_manager = BoundaryConditionManager()
            config = BoundaryConditionConfig("test_bc", "测试边界条件")
            bc = FlowBoundary("test_bc", "node_0", 20.0, config)
            boundary_manager.add_boundary_condition(bc)
            
            start_time = time.time()
            enhanced_solver = ImplicitSolverAgent(models, None, boundary_manager)
            enhanced_result = enhanced_solver.solve_steady_state(initial_conditions)
            enhanced_time = time.time() - start_time
            
            # 性能对比
            performance_ratio = enhanced_time / traditional_time if traditional_time > 0 else float('inf')
            
            result['details'].update({
                'traditional_time': traditional_time,
                'enhanced_time': enhanced_time,
                'performance_ratio': performance_ratio,
                'traditional_converged': traditional_result['converged'],
                'enhanced_converged': enhanced_result['converged']
            })
            
            # 判断性能回归
            if performance_ratio < 2.0:  # 性能下降不超过100%
                result['status'] = 'success'
                logger.info(f"✅ 性能回归测试通过，性能比率: {performance_ratio:.2f}")
            else:
                result['status'] = 'partial'
                result['errors'].append(f"性能显著下降，比率: {performance_ratio:.2f}")
                logger.warning(f"⚠️ 性能下降明显，比率: {performance_ratio:.2f}")
                
        except Exception as e:
            result['status'] = 'failed'
            result['errors'].append(str(e))
            logger.error(f"❌ 性能回归测试失败: {e}")
            traceback.print_exc()
        
        return result
    
    def run_all_integration_tests(self) -> Dict[str, Any]:
        """运行所有集成兼容性测试"""
        logger.info("开始WaterNet模块集成兼容性测试")
        
        test_functions = [
            self.test_saint_venant_integration,
            self.test_lumped_models_integration,
            self.test_configuration_backward_compatibility,
            self.test_api_compatibility,
            self.test_performance_regression
        ]
        
        results = []
        
        for test_func in test_functions:
            try:
                result = test_func()
                results.append(result)
                self.test_results.append(result)
                
            except Exception as e:
                logger.error(f"测试函数 {test_func.__name__} 执行失败: {e}")
                results.append({
                    'test_name': test_func.__name__,
                    'status': 'failed',
                    'errors': [str(e)]
                })
        
        # 汇总结果
        total_tests = len(results)
        successful_tests = sum(1 for r in results if r['status'] == 'success')
        partial_tests = sum(1 for r in results if r['status'] == 'partial')
        failed_tests = sum(1 for r in results if r['status'] == 'failed')
        
        summary = {
            'total_tests': total_tests,
            'successful_tests': successful_tests,
            'partial_tests': partial_tests,
            'failed_tests': failed_tests,
            'success_rate': successful_tests / total_tests,
            'results': results,
            'overall_status': self._determine_overall_status(successful_tests, partial_tests, failed_tests)
        }
        
        return summary
    
    def _determine_overall_status(self, success: int, partial: int, failed: int) -> str:
        """确定整体状态"""
        total = success + partial + failed
        
        if failed == 0 and partial == 0:
            return 'excellent'
        elif failed == 0:
            return 'good'
        elif failed < total // 2:
            return 'acceptable'
        else:
            return 'poor'
    
    def generate_compatibility_report(self) -> str:
        """生成兼容性报告"""
        if not self.test_results:
            return "没有测试结果可用于生成报告"
        
        report_lines = [
            "# WaterNet边界条件框架集成兼容性报告",
            "",
            "## 测试概览",
            ""
        ]
        
        summary = self.run_all_integration_tests()
        
        report_lines.extend([
            f"- 总测试数: {summary['total_tests']}",
            f"- 成功测试: {summary['successful_tests']} ✅",
            f"- 部分成功: {summary['partial_tests']} ⚠️",
            f"- 失败测试: {summary['failed_tests']} ❌",
            f"- 成功率: {summary['success_rate']:.1%}",
            f"- 整体状态: {summary['overall_status']}",
            "",
            "## 详细测试结果",
            ""
        ])
        
        for result in summary['results']:
            status_icon = {'success': '✅', 'partial': '⚠️', 'failed': '❌', 'unknown': '❓'}.get(result['status'], '❓')
            
            report_lines.extend([
                f"### {result['test_name']} {status_icon}",
                f"**状态**: {result['status']}",
                ""
            ])
            
            if result.get('details'):
                report_lines.append("**详细信息**:")
                for key, value in result['details'].items():
                    report_lines.append(f"- {key}: {value}")
                report_lines.append("")
            
            if result.get('errors'):
                report_lines.append("**错误信息**:")
                for error in result['errors']:
                    report_lines.append(f"- {error}")
                report_lines.append("")
        
        return "\n".join(report_lines)


def main():
    """主测试程序"""
    logger.info("🔗 WaterNet模块集成兼容性测试开始")
    
    tester = IntegrationCompatibilityTester()
    
    # 运行测试
    summary = tester.run_all_integration_tests()
    
    # 输出结果
    logger.info("=" * 60)
    logger.info("集成兼容性测试结果:")
    logger.info(f"总测试数: {summary['total_tests']}")
    logger.info(f"成功: {summary['successful_tests']}, 部分成功: {summary['partial_tests']}, 失败: {summary['failed_tests']}")
    logger.info(f"成功率: {summary['success_rate']:.1%}")
    logger.info(f"整体评价: {summary['overall_status']}")
    
    # 生成报告
    report = tester.generate_compatibility_report()
    
    # 保存报告
    report_file = Path("integration_compatibility_report.md")
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    logger.info(f"📋 兼容性报告已保存到: {report_file}")
    logger.info("✅ 集成兼容性测试完成")
    
    return summary


if __name__ == "__main__":
    main()