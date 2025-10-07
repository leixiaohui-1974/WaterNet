"""
ParameterOptimizer - 参数自动调优核心模块

实现多种非恒定流方法的参数自动优化，避免反复试错寻找最佳参数。
支持马斯京干法、蓄量演算法等方法的智能参数调优。

主要功能:
1. 马斯京干法参数(K, x)的自动优化
2. 基于物理约束的参数搜索
3. 多目标优化（精度、稳定性、物理合理性）
4. 参数敏感性分析
5. 自适应参数推荐

Author: WaterNet Development Team
Date: 2025-10-06
"""

import json
from datetime import datetime
from pathlib import Path

import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Callable, Union
from scipy.optimize import minimize, differential_evolution
import warnings
from dataclasses import dataclass
from enum import Enum

# 导入WaterNet核心组件
from ..models.lumped_models import MuskingumModel, StorageRoutingModel
from ..utils.model_factory import create_default_physical_relations
from ..utils.output_manager import ensure_output_tree, timestamped_path

PathLike = Union[str, Path]


class OptimizationObjective(Enum):
    """优化目标类型"""
    ACCURACY = "accuracy"                # 精度优先
    ACCURACY_FIRST = "accuracy_first"    # 精度优先（兼容性别名）
    STABILITY = "stability"              # 稳定性优先
    STABILITY_FIRST = "stability_first"  # 稳定性优先（兼容性别名）
    PHYSICAL = "physical"                # 物理合理性优先
    BALANCED = "balanced"                # 平衡优化


@dataclass
class OptimizationResult:
    """优化结果数据类"""
    success: bool
    optimal_params: Dict[str, float]
    objective_value: float
    iterations: int
    convergence_info: Dict[str, Any]
    parameter_sensitivity: Dict[str, float]
    physical_constraints_satisfied: bool
    stability_analysis: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """将优化结果序列化为易于存储的 JSON 结构。"""

        def convert(value):
            try:
                import numpy as np  # local import to avoid mandatory dependency at module import
            except Exception:  # pragma: no cover - numpy always available in project
                np = None  # type: ignore

            if np is not None and isinstance(value, np.generic):
                return value.item()
            if isinstance(value, dict):
                return {k: convert(v) for k, v in value.items()}
            if isinstance(value, (list, tuple)):
                return [convert(v) for v in value]
            return value

        return {
            "success": bool(self.success),
            "optimal_params": {k: float(v) for k, v in self.optimal_params.items()},
            "objective_value": float(self.objective_value),
            "iterations": int(self.iterations),
            "convergence_info": convert(self.convergence_info),
            "parameter_sensitivity": {k: float(v) for k, v in self.parameter_sensitivity.items()},
            "physical_constraints_satisfied": bool(self.physical_constraints_satisfied),
            "stability_analysis": convert(self.stability_analysis),
        }


class ParameterOptimizer:
    """
    参数自动优化器
    
    提供多种非恒定流模型的参数自动优化功能：
    - 马斯京干法参数 K, x 的优化
    - 蓄量演算法参数优化
    - 基于观测数据的参数率定
    - 参数敏感性分析
    - 物理约束验证
    """
    
    def __init__(self, 
                 objective_type: OptimizationObjective = OptimizationObjective.BALANCED,
                 max_iterations: int = 100,
                 tolerance: float = 1e-6):
        """
        初始化参数优化器
        
        Args:
            objective_type: 优化目标类型
            max_iterations: 最大迭代次数
            tolerance: 收敛容差
        """
        self.objective_type = objective_type
        self.max_iterations = max_iterations
        self.tolerance = tolerance
        
        # 物理约束条件
        self.physical_constraints = {
            'muskingum': {
                'K_min': 300.0,      # 最小滞时常数（秒）
                'K_max': 7200.0,     # 最大滞时常数（秒） 
                'x_min': 0.05,       # 最小权重系数
                'x_max': 0.4,        # 最大权重系数
                'stability_2Kx_dt': True  # 稳定性条件 2Kx ≤ dt
            }
        }
        
        # 优化历史
        self.optimization_history = []
        
    def optimize_muskingum_parameters(self, 
                                    observed_inflows: List[float],
                                    observed_outflows: List[float],
                                    time_step: float = 1800.0,
                                    initial_params: Optional[Dict[str, float]] = None) -> OptimizationResult:
        """
        优化马斯京干法参数
        
        Args:
            observed_inflows: 观测入流序列
            observed_outflows: 观测出流序列  
            time_step: 时间步长（秒）
            initial_params: 初始参数估计
            
        Returns:
            优化结果
        """
        print("[目标] 开始马斯京干法参数自动优化...")
        
        # 验证输入数据
        if len(observed_inflows) != len(observed_outflows):
            raise ValueError("入流和出流序列长度不一致")
        
        if len(observed_inflows) < 3:
            raise ValueError("观测数据点太少，至少需要3个数据点")
        
        # 设置参数边界
        constraints = self.physical_constraints['muskingum']
        bounds = [
            (constraints['K_min'], constraints['K_max']),  # K 边界
            (constraints['x_min'], constraints['x_max'])   # x 边界
        ]
        
        # 初始参数
        if initial_params is None:
            # 使用经验公式估算初始值
            K_init = self._estimate_initial_K(observed_inflows, observed_outflows, time_step)
            x_init = 0.15  # 经验值
        else:
            K_init = initial_params.get('K', 3600.0)
            x_init = initial_params.get('x', 0.15)
        
        initial_guess = [K_init, x_init]
        
        # 定义目标函数
        def objective_function(params):
            K, x = params
            
            # 稳定性约束检查
            if constraints['stability_2Kx_dt'] and 2 * K * x > time_step:
                return 1e6  # 违反稳定性条件，返回大值
            
            try:
                # 创建模型
                V_to_H_func, H_to_Q_func = create_default_physical_relations()
                model = MuskingumModel(
                    dt=time_step,
                    K=K,
                    x=x,
                    initial_V=15000.0,
                    V_to_H_func=V_to_H_func,
                    H_to_Q_func=H_to_Q_func
                )
                
                # 运行仿真
                simulated_outflows = []
                for Q_in in observed_inflows:
                    result = model.step(Q_in)
                    simulated_outflows.append(result['Q_out'])
                
                # 计算目标函数值
                return self._calculate_objective_value(
                    observed_outflows, simulated_outflows, [K, x], time_step
                )
                
            except Exception as e:
                warnings.warn(f"参数评估失败: K={K:.1f}, x={x:.3f}, 错误: {e}")
                return 1e6
        
        # 执行优化
        print(f"  [扫描] 搜索范围: K∈[{constraints['K_min']:.0f}, {constraints['K_max']:.0f}]s, "
              f"x∈[{constraints['x_min']:.3f}, {constraints['x_max']:.3f}]")
        
        try:
            # 使用差分进化算法，对非线性问题效果好
            result = differential_evolution(
                objective_function,
                bounds,
                seed=42,
                maxiter=self.max_iterations,
                tol=self.tolerance,
                popsize=15,
                atol=1e-8
            )
            
            if result.success:
                K_opt, x_opt = result.x
                
                print(f"  [完成] 优化成功!")
                print(f"    最优参数: K={K_opt:.1f}s, x={x_opt:.3f}")
                print(f"    目标函数值: {result.fun:.6f}")
                print(f"    迭代次数: {result.nit}")
                
                # 进行参数敏感性分析
                sensitivity = self._analyze_parameter_sensitivity(
                    objective_function, [K_opt, x_opt], bounds
                )
                
                # 稳定性分析
                stability_analysis = self._analyze_muskingum_stability(K_opt, x_opt, time_step)
                
                # 物理约束验证
                physical_ok = self._verify_physical_constraints(
                    'muskingum', {'K': K_opt, 'x': x_opt}, time_step
                )
                
                return OptimizationResult(
                    success=True,
                    optimal_params={'K': K_opt, 'x': x_opt},
                    objective_value=result.fun,
                    iterations=result.nit,
                    convergence_info={'message': result.message, 'status': result.success},
                    parameter_sensitivity=sensitivity,
                    physical_constraints_satisfied=physical_ok,
                    stability_analysis=stability_analysis
                )
                
            else:
                print(f"  [ERROR] 优化失败: {result.message}")
                return OptimizationResult(
                    success=False,
                    optimal_params={'K': K_init, 'x': x_init},
                    objective_value=result.fun,
                    iterations=result.nit,
                    convergence_info={'message': result.message, 'status': result.success},
                    parameter_sensitivity={},
                    physical_constraints_satisfied=False,
                    stability_analysis={}
                )
                
        except Exception as e:
            print(f"  [ERROR] 优化过程异常: {e}")
            return OptimizationResult(
                success=False,
                optimal_params={'K': K_init, 'x': x_init},
                objective_value=1e6,
                iterations=0,
                convergence_info={'message': str(e), 'status': False},
                parameter_sensitivity={},
                physical_constraints_satisfied=False,
                stability_analysis={}
            )
    
    def _estimate_initial_K(self, inflows: List[float], outflows: List[float], dt: float) -> float:
        """估算马斯京干法初始K值"""
        try:
            # 使用峰值延迟估算
            peak_in_idx = np.argmax(inflows)
            peak_out_idx = np.argmax(outflows)
            
            delay_steps = abs(peak_out_idx - peak_in_idx)
            delay_time = delay_steps * dt
            
            # K大致等于延迟时间
            K_estimate = max(delay_time, 1800.0)  # 至少30分钟
            
            # 限制在合理范围内
            constraints = self.physical_constraints['muskingum']
            K_estimate = np.clip(K_estimate, constraints['K_min'], constraints['K_max'])
            
            return K_estimate
            
        except Exception:
            return 3600.0  # 默认1小时
    
    def _calculate_objective_value(self, observed: List[float], simulated: List[float], 
                                 params: List[float], dt: float) -> float:
        """计算目标函数值"""
        observed = np.array(observed)
        simulated = np.array(simulated)
        
        if self.objective_type == OptimizationObjective.ACCURACY:
            # 精度优先：最小化均方根误差
            rmse = np.sqrt(np.mean((observed - simulated) ** 2))
            return rmse
            
        elif self.objective_type == OptimizationObjective.STABILITY:
            # 稳定性优先：最小化振荡
            oscillation = np.mean(np.abs(np.diff(simulated)))
            rmse = np.sqrt(np.mean((observed - simulated) ** 2))
            return 0.3 * rmse + 0.7 * oscillation
            
        elif self.objective_type == OptimizationObjective.PHYSICAL:
            # 物理合理性优先：考虑参数的物理意义
            K, x = params
            rmse = np.sqrt(np.mean((observed - simulated) ** 2))
            
            # 物理合理性惩罚
            physical_penalty = 0.0
            if K < 1800:  # K太小
                physical_penalty += (1800 - K) / 1800 * 10
            if x < 0.1 or x > 0.3:  # x不在常见范围
                physical_penalty += abs(x - 0.2) * 50
            
            return rmse + physical_penalty
            
        else:  # BALANCED
            # 平衡优化：多目标综合
            rmse = np.sqrt(np.mean((observed - simulated) ** 2))
            
            # 流量守恒检查
            mass_conservation = abs(np.sum(observed) - np.sum(simulated)) / np.sum(observed)
            
            # 峰值匹配
            peak_error = abs(np.max(observed) - np.max(simulated)) / np.max(observed)
            
            # 综合评分
            return 0.5 * rmse + 0.3 * mass_conservation * 100 + 0.2 * peak_error * 100
    
    def _analyze_parameter_sensitivity(self, objective_func: Callable, 
                                     optimal_params: List[float], 
                                     bounds: List[Tuple[float, float]]) -> Dict[str, float]:
        """分析参数敏感性"""
        try:
            sensitivity = {}
            base_value = objective_func(optimal_params)
            
            # 对每个参数进行扰动分析
            param_names = ['K', 'x']
            delta = 0.01  # 1% 扰动
            
            for i, (param_name, (lower, upper)) in enumerate(zip(param_names, bounds)):
                # 正向扰动
                params_plus = optimal_params.copy()
                perturbation = optimal_params[i] * delta
                params_plus[i] = min(optimal_params[i] + perturbation, upper)
                value_plus = objective_func(params_plus)
                
                # 负向扰动
                params_minus = optimal_params.copy()
                params_minus[i] = max(optimal_params[i] - perturbation, lower)
                value_minus = objective_func(params_minus)
                
                # 计算敏感性（相对变化率）
                sensitivity[param_name] = abs((value_plus - value_minus) / (2 * perturbation))
            
            return sensitivity
            
        except Exception as e:
            warnings.warn(f"敏感性分析失败: {e}")
            return {'K': 0.0, 'x': 0.0}
    
    def _analyze_muskingum_stability(self, K: float, x: float, dt: float) -> Dict[str, Any]:
        """分析马斯京干法稳定性"""
        stability_condition = 2 * K * x
        stability_margin = dt - stability_condition
        
        analysis = {
            'stability_condition_value': stability_condition,
            'time_step': dt,
            'stability_margin': stability_margin,
            'is_stable': stability_margin >= 0,
            'stability_ratio': stability_condition / dt,
            'recommended_dt_min': stability_condition,
            'recommendations': []
        }
        
        if stability_margin < 0:
            analysis['recommendations'].append(f"违反稳定性条件！建议时间步长≥{stability_condition:.0f}s")
        elif stability_margin < dt * 0.1:
            analysis['recommendations'].append("稳定性裕度较小，建议增大时间步长或调整参数")
        else:
            analysis['recommendations'].append("满足稳定性条件")
        
        # K值合理性分析
        if K < 1800:
            analysis['recommendations'].append("K值偏小，可能导致响应过于灵敏")
        elif K > 7200:
            analysis['recommendations'].append("K值偏大，可能导致响应过于迟缓")
        
        # x值合理性分析
        if x < 0.1:
            analysis['recommendations'].append("x值偏小，调节作用较弱")
        elif x > 0.3:
            analysis['recommendations'].append("x值偏大，可能导致数值不稳定")
        
        return analysis
    
    def _verify_physical_constraints(self, model_type: str, params: Dict[str, float], 
                                   dt: float) -> bool:
        """验证物理约束条件"""
        if model_type == 'muskingum':
            constraints = self.physical_constraints['muskingum']
            K = params['K']
            x = params['x']
            
            # 检查参数范围
            if not (constraints['K_min'] <= K <= constraints['K_max']):
                return False
            
            if not (constraints['x_min'] <= x <= constraints['x_max']):
                return False
            
            # 检查稳定性条件
            if constraints['stability_2Kx_dt'] and 2 * K * x > dt:
                return False
            
            return True
        
        return False
    
    def recommend_parameters(self, channel_properties: Dict[str, float], 
                           application_type: str = 'general') -> Dict[str, float]:
        """
        基于渠道特性推荐参数
        
        Args:
            channel_properties: 渠道特性字典，包含length, slope, roughness等
            application_type: 应用类型 ('flood_forecasting', 'engineering_design', 'research')
            
        Returns:
            推荐的参数字典
        """
        print('[信息] 正在生成马斯京干法参数推荐...')
        
        length = channel_properties.get('length', 5000.0)
        slope = channel_properties.get('slope', 0.0002)
        roughness = channel_properties.get('roughness', 0.025)
        
        # 基于渠道特性估算传播时间
        # 使用简化的洪波传播速度公式
        average_depth = 2.0  # 假设平均水深
        wave_speed = np.sqrt(9.81 * average_depth)  # 重力波速度
        
        # 考虑曼宁阻力的修正
        friction_factor = 1.0 + roughness * 10  # 经验修正
        effective_speed = wave_speed / friction_factor
        
        # 估算K值（传播时间）
        K_recommended = length / effective_speed
        
        # 根据应用类型调整参数
        if application_type == 'flood_forecasting':
            # 洪水预报：偏向快速响应
            K_recommended *= 0.8
            x_recommended = 0.1
        elif application_type == 'engineering_design':
            # 工程设计：偏向稳定性
            K_recommended *= 1.2
            x_recommended = 0.2
        else:  # general, research
            # 通用/科研：中等设置
            x_recommended = 0.15
        
        # 限制在物理约束范围内
        constraints = self.physical_constraints['muskingum']
        K_recommended = np.clip(K_recommended, constraints['K_min'], constraints['K_max'])
        x_recommended = np.clip(x_recommended, constraints['x_min'], constraints['x_max'])
        
        recommended_params = {
            'K': float(K_recommended),
            'x': float(x_recommended)
        }
        
        print(f"   推荐参数: K={K_recommended:.0f}s, x={x_recommended:.3f}")
        print(f"  [目标] 应用场景: {application_type}")
        print(f"   基于渠道长度: {length:.0f}m, 坡度: {slope:.6f}, 糙率: {roughness:.3f}")
        
        return recommended_params
    
    def batch_optimize_parameters(self, datasets: List[Dict[str, Any]]) -> List[OptimizationResult]:
        """
        批量参数优化
        
        Args:
            datasets: 包含多组观测数据的列表
            
        Returns:
            优化结果列表
        """
        print(f" 开始批量参数优化，共{len(datasets)}组数据...")
        
        results = []
        for i, dataset in enumerate(datasets):
            print(f"\n  [DATA] 处理第{i+1}组数据...")
            
            try:
                result = self.optimize_muskingum_parameters(
                    observed_inflows=dataset['inflows'],
                    observed_outflows=dataset['outflows'],
                    time_step=dataset.get('time_step', 1800.0),
                    initial_params=dataset.get('initial_params')
                )
                results.append(result)
                
                if result.success:
                    print(f"    [完成] 第{i+1}组优化成功")
                else:
                    print(f"    [ERROR] 第{i+1}组优化失败")
                    
            except Exception as e:
                print(f"    [ERROR] 第{i+1}组处理异常: {e}")
                results.append(OptimizationResult(
                    success=False,
                    optimal_params={},
                    objective_value=1e6,
                    iterations=0,
                    convergence_info={'message': str(e), 'status': False},
                    parameter_sensitivity={},
                    physical_constraints_satisfied=False,
                    stability_analysis={}
                ))
        
        # 统计结果
        successful_count = sum(1 for r in results if r.success)
        print(f"\n[PLOT] 批量优化完成: {successful_count}/{len(datasets)} 成功")
        
        return results
    
    def create_optimization_report(self, result: OptimizationResult, 
                                 output_path: Optional[str] = None) -> str:
        """
        创建优化报告
        
        Args:
            result: 优化结果
            output_path: 输出路径
            
        Returns:
            报告文件路径
        """
        if output_path is None:
            from pathlib import Path
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"parameter_optimization_report_{timestamp}.md"
        
        try:
            from datetime import datetime
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("# 参数优化报告\n\n")
                f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"**优化状态**: {'成功' if result.success else '失败'}\n\n")
                
                if result.success:
                    f.write("## 优化结果\n\n")
                    f.write("### 最优参数\n\n")
                    for param, value in result.optimal_params.items():
                        f.write(f"- **{param}**: {value:.3f}\n")
                    
                    f.write(f"\n- **目标函数值**: {result.objective_value:.6f}\n")
                    f.write(f"- **迭代次数**: {result.iterations}\n")
                    f.write(f"- **物理约束满足**: {'是' if result.physical_constraints_satisfied else '否'}\n\n")
                    
                    f.write("### 参数敏感性分析\n\n")
                    for param, sensitivity in result.parameter_sensitivity.items():
                        f.write(f"- **{param}敏感性**: {sensitivity:.6f}\n")
                    
                    f.write("\n### 稳定性分析\n\n")
                    stability = result.stability_analysis
                    if stability:
                        f.write(f"- **稳定性条件**: {'满足' if stability.get('is_stable', False) else '不满足'}\n")
                        f.write(f"- **稳定性裕度**: {stability.get('stability_margin', 0):.1f}s\n")
                        
                        if stability.get('recommendations'):
                            f.write("\n### 建议\n\n")
                            for rec in stability['recommendations']:
                                f.write(f"- {rec}\n")
                    
                else:
                    f.write("## 优化失败\n\n")
                    f.write(f"**失败原因**: {result.convergence_info.get('message', '未知')}\n\n")
                
                f.write("\n---\n")
                f.write("*本报告由WaterNet.ParameterOptimizer自动生成*\n")
            
            print(f"  [报告] 优化报告已生成: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"  [ERROR] 报告生成失败: {e}")
            return ""

    def export_result_bundle(
        self,
        result: OptimizationResult,
        output_dir: PathLike,
        report_name: Optional[str] = None,
    ) -> Dict[str, Path]:
        """
        将优化结果保存为标准的数据与报告组合。

        Args:
            result: 优化结果对象。
            output_dir: 输出目录，函数会自动创建。
            report_name: 报告文件名前缀，可选。

        Returns:
            包含 ``data`` 和 ``report`` （若生成）的路径映射。
        """
        base_dir = Path(output_dir)
        ensure_output_tree(base_dir, ())

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        data_path = timestamped_path(base_dir, "parameter_optimization", ".json", timestamp)
        with data_path.open("w", encoding="utf-8") as f:
            json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)

        report_prefix = report_name or "parameter_optimization_report"
        report_path = timestamped_path(base_dir, report_prefix, ".md", timestamp)
        generated = self.create_optimization_report(result, str(report_path))

        artefacts: Dict[str, Path] = {"data": data_path}
        if generated:
            artefacts["report"] = Path(generated)
        return artefacts
