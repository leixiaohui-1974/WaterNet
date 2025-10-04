"""
AccuracyComparator 精度对比器

对不同简化模式的计算结果进行精度评估和对比分析，提供：
1. 多维度精度指标计算
2. 误差分布分析
3. 模式间对比评估
4. 可视化分析工具
5. 综合精度报告生成

Author: WaterNet Development Team
Date: 2024-11-05
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass
import warnings
from pathlib import Path


@dataclass
class AccuracyMetrics:
    """精度指标数据类"""
    rmse: float                    # 均方根误差
    mae: float                     # 平均绝对误差  
    mape: float                    # 平均绝对百分比误差
    nse: float                     # 纳什-萨特克利夫效率系数
    r_squared: float               # 决定系数
    bias: float                    # 偏差
    max_error: float               # 最大误差
    relative_rmse: float           # 相对均方根误差
    
    def to_dict(self) -> Dict[str, float]:
        """转换为字典格式"""
        return {
            'RMSE': self.rmse,
            'MAE': self.mae,
            'MAPE': self.mape,
            'NSE': self.nse,
            'R²': self.r_squared,
            'Bias': self.bias,
            'Max_Error': self.max_error,
            'Relative_RMSE': self.relative_rmse
        }


@dataclass
class ComparisonResult:
    """对比结果数据类"""
    reference_mode: str            # 参考模式
    test_mode: str                 # 测试模式
    variable_name: str             # 变量名称
    accuracy_metrics: AccuracyMetrics  # 精度指标
    performance_ratio: float       # 性能比值（计算时间比）
    conservation_error: float      # 守恒误差
    stability_score: float         # 稳定性评分
    recommendation: str            # 推荐结论


class AccuracyComparator:
    """
    精度对比器
    
    提供多种简化模式之间的精度对比和评估功能，
    支持多维度指标计算和综合分析。
    """
    
    def __init__(self, enable_logging: bool = True):
        """
        初始化精度对比器
        
        Args:
            enable_logging (bool): 是否启用日志输出
        """
        self.enable_logging = enable_logging
        self.comparison_history = []
        
        # 精度评估标准
        self.accuracy_standards = {
            'excellent': {'rmse_threshold': 0.02, 'nse_threshold': 0.90},
            'good': {'rmse_threshold': 0.05, 'nse_threshold': 0.75},
            'acceptable': {'rmse_threshold': 0.10, 'nse_threshold': 0.50},
            'poor': {'rmse_threshold': float('inf'), 'nse_threshold': -float('inf')}
        }
        
        if enable_logging:
            print("✅ AccuracyComparator 初始化完成")
    
    def compare_results(self, 
                       reference_results: Dict[str, Any],
                       test_results: Dict[str, Any],
                       reference_mode: str = "dynamic_wave",
                       test_mode: str = "unknown",
                       variables: Optional[List[str]] = None) -> Dict[str, ComparisonResult]:
        """
        对比两组计算结果
        
        Args:
            reference_results: 参考结果（通常是完整模式）
            test_results: 测试结果（简化模式）
            reference_mode: 参考模式名称
            test_mode: 测试模式名称
            variables: 要对比的变量列表，None则自动检测
            
        Returns:
            Dict[str, ComparisonResult]: 各变量的对比结果
        """
        if self.enable_logging:
            print(f"🔍 开始精度对比分析: {test_mode} vs {reference_mode}")
        
        # 自动检测要对比的变量
        if variables is None:
            variables = self._detect_common_variables(reference_results, test_results)
        
        comparison_results = {}
        
        for var_name in variables:
            if var_name in reference_results and var_name in test_results:
                try:
                    # 提取数据
                    ref_data = self._extract_variable_data(reference_results, var_name)
                    test_data = self._extract_variable_data(test_results, var_name)
                    
                    # 计算精度指标
                    accuracy_metrics = self._calculate_accuracy_metrics(ref_data, test_data)
                    
                    # 计算性能指标
                    performance_ratio = self._calculate_performance_ratio(
                        reference_results, test_results)
                    
                    # 计算守恒误差
                    conservation_error = self._calculate_conservation_error(
                        reference_results, test_results, var_name)
                    
                    # 评估稳定性
                    stability_score = self._evaluate_stability(test_data)
                    
                    # 生成推荐结论
                    recommendation = self._generate_recommendation(
                        accuracy_metrics, performance_ratio, test_mode)
                    
                    # 构建对比结果
                    comparison_result = ComparisonResult(
                        reference_mode=reference_mode,
                        test_mode=test_mode,
                        variable_name=var_name,
                        accuracy_metrics=accuracy_metrics,
                        performance_ratio=performance_ratio,
                        conservation_error=conservation_error,
                        stability_score=stability_score,
                        recommendation=recommendation
                    )
                    
                    comparison_results[var_name] = comparison_result
                    
                    if self.enable_logging:
                        print(f"   {var_name}: RMSE={accuracy_metrics.rmse:.4f}, "
                              f"R²={accuracy_metrics.r_squared:.3f}")
                    
                except Exception as e:
                    if self.enable_logging:
                        print(f"⚠️ 变量 {var_name} 对比失败: {e}")
                    continue
        
        # 记录对比历史
        self._record_comparison(comparison_results, reference_mode, test_mode)
        
        return comparison_results
    
    def _detect_common_variables(self, ref_results: Dict, test_results: Dict) -> List[str]:
        """检测两组结果中的共同变量"""
        ref_vars = set(ref_results.keys())
        test_vars = set(test_results.keys())
        common_vars = ref_vars.intersection(test_vars)
        
        # 排除非数值变量
        excluded_vars = {'success', 'mode', 'error', 'input_parameters', 
                        'computation_time', 'accuracy_comparison'}
        
        return [var for var in common_vars if var not in excluded_vars]
    
    def _extract_variable_data(self, results: Dict, var_name: str) -> np.ndarray:
        """提取变量数据"""
        data = results[var_name]
        
        if isinstance(data, (list, tuple, np.ndarray)):
            return np.array(data, dtype=float)
        elif isinstance(data, (int, float)):
            return np.array([data], dtype=float)
        else:
            raise ValueError(f"无法处理的数据类型: {type(data)}")
    
    def _calculate_accuracy_metrics(self, reference: np.ndarray, 
                                   predicted: np.ndarray) -> AccuracyMetrics:
        """计算精度指标"""
        # 确保数组长度一致
        min_length = min(len(reference), len(predicted))
        ref = reference[:min_length]
        pred = predicted[:min_length]
        
        # 基本误差计算
        errors = pred - ref
        abs_errors = np.abs(errors)
        
        # RMSE - 均方根误差
        rmse = np.sqrt(np.mean(errors**2))
        
        # MAE - 平均绝对误差
        mae = np.mean(abs_errors)
        
        # MAPE - 平均绝对百分比误差
        ref_nonzero = ref[ref != 0]
        pred_nonzero = pred[ref != 0]
        if len(ref_nonzero) > 0:
            mape = np.mean(np.abs((pred_nonzero - ref_nonzero) / ref_nonzero)) * 100
        else:
            mape = 0.0
        
        # NSE - 纳什-萨特克利夫效率系数
        if np.var(ref) > 0:
            nse = 1 - np.sum(errors**2) / np.sum((ref - np.mean(ref))**2)
        else:
            nse = 0.0
        
        # R² - 决定系数
        if np.var(ref) > 0 and np.var(pred) > 0:
            correlation_matrix = np.corrcoef(ref, pred)
            r_squared = correlation_matrix[0, 1]**2
        else:
            r_squared = 0.0
        
        # Bias - 偏差
        bias = np.mean(errors)
        
        # 最大误差
        max_error = np.max(abs_errors)
        
        # 相对RMSE
        ref_mean = np.mean(ref)
        relative_rmse = rmse / ref_mean if ref_mean != 0 else float('inf')
        
        return AccuracyMetrics(
            rmse=rmse,
            mae=mae,
            mape=mape,
            nse=nse,
            r_squared=r_squared,
            bias=bias,
            max_error=max_error,
            relative_rmse=relative_rmse
        )
    
    def _calculate_performance_ratio(self, ref_results: Dict, 
                                   test_results: Dict) -> float:
        """计算性能比值"""
        ref_time = ref_results.get('computation_time', 1.0)
        test_time = test_results.get('computation_time', 1.0)
        
        if test_time > 0:
            return ref_time / test_time  # 加速比
        else:
            return 1.0
    
    def _calculate_conservation_error(self, ref_results: Dict, 
                                    test_results: Dict, 
                                    var_name: str) -> float:
        """计算守恒误差"""
        # 对于体积变量，检查质量守恒
        if 'volume' in var_name.lower():
            ref_volume = ref_results.get('total_volume', 0.0)
            test_volume = test_results.get('total_volume', 0.0)
            
            if ref_volume != 0:
                conservation_error = abs(test_volume - ref_volume) / ref_volume
            else:
                conservation_error = 0.0
        else:
            # 对于其他变量，暂时返回0
            conservation_error = 0.0
        
        return conservation_error
    
    def _evaluate_stability(self, data: np.ndarray) -> float:
        """评估数值稳定性"""
        if len(data) < 2:
            return 1.0
        
        # 检查是否存在NaN或无穷大值
        if np.any(~np.isfinite(data)):
            return 0.0
        
        # 计算变异系数作为稳定性指标
        if np.mean(data) != 0:
            cv = np.std(data) / abs(np.mean(data))
            stability_score = max(0.0, 1.0 - cv)
        else:
            stability_score = 1.0 if np.std(data) == 0 else 0.0
        
        return stability_score
    
    def _generate_recommendation(self, metrics: AccuracyMetrics, 
                               performance_ratio: float,
                               test_mode: str) -> str:
        """生成推荐结论"""
        # 评估精度等级
        if metrics.rmse <= self.accuracy_standards['excellent']['rmse_threshold'] and \
           metrics.nse >= self.accuracy_standards['excellent']['nse_threshold']:
            accuracy_level = "优秀"
        elif metrics.rmse <= self.accuracy_standards['good']['rmse_threshold'] and \
             metrics.nse >= self.accuracy_standards['good']['nse_threshold']:
            accuracy_level = "良好"
        elif metrics.rmse <= self.accuracy_standards['acceptable']['rmse_threshold'] and \
             metrics.nse >= self.accuracy_standards['acceptable']['nse_threshold']:
            accuracy_level = "可接受"
        else:
            accuracy_level = "较差"
        
        # 评估性能提升
        if performance_ratio > 5:
            performance_level = "显著提升"
        elif performance_ratio > 2:
            performance_level = "中等提升"
        elif performance_ratio > 1.2:
            performance_level = "轻微提升"
        else:
            performance_level = "无明显提升"
        
        # 综合推荐
        if accuracy_level in ["优秀", "良好"] and performance_level != "无明显提升":
            recommendation = f"推荐使用{test_mode}模式：精度{accuracy_level}，性能{performance_level}"
        elif accuracy_level == "可接受" and performance_ratio > 3:
            recommendation = f"可考虑使用{test_mode}模式：精度{accuracy_level}，但性能{performance_level}"
        else:
            recommendation = f"不推荐使用{test_mode}模式：精度{accuracy_level}，性能提升有限"
        
        return recommendation
    
    def _record_comparison(self, comparison_results: Dict[str, ComparisonResult],
                          reference_mode: str, test_mode: str):
        """记录对比历史"""
        record = {
            'timestamp': np.datetime64('now'),
            'reference_mode': reference_mode,
            'test_mode': test_mode,
            'variables_compared': list(comparison_results.keys()),
            'summary_metrics': self._calculate_summary_metrics(comparison_results)
        }
        
        self.comparison_history.append(record)
        
        # 限制历史记录长度
        if len(self.comparison_history) > 50:
            self.comparison_history = self.comparison_history[-50:]
    
    def _calculate_summary_metrics(self, comparison_results: Dict[str, ComparisonResult]) -> Dict:
        """计算汇总指标"""
        if not comparison_results:
            return {}
        
        rmse_values = []
        nse_values = []
        r_squared_values = []
        performance_ratios = []
        
        for result in comparison_results.values():
            rmse_values.append(result.accuracy_metrics.rmse)
            nse_values.append(result.accuracy_metrics.nse)
            r_squared_values.append(result.accuracy_metrics.r_squared)
            performance_ratios.append(result.performance_ratio)
        
        return {
            'average_rmse': np.mean(rmse_values),
            'average_nse': np.mean(nse_values),
            'average_r_squared': np.mean(r_squared_values),
            'average_performance_ratio': np.mean(performance_ratios)
        }
    
    def generate_comparison_report(self, comparison_results: Dict[str, ComparisonResult],
                                 save_path: Optional[str] = None) -> str:
        """生成对比分析报告"""
        if not comparison_results:
            return "无对比数据可生成报告"
        
        # 获取基本信息
        sample_result = next(iter(comparison_results.values()))
        reference_mode = sample_result.reference_mode
        test_mode = sample_result.test_mode
        
        # 生成报告
        report = f"""
🔬 精度对比分析报告
{'='*60}
对比模式: {test_mode} vs {reference_mode} (参考)
生成时间: {np.datetime64('now')}
分析变量: {len(comparison_results)} 个

📊 详细分析结果
{'-'*30}
"""
        
        # 各变量详细结果
        for var_name, result in comparison_results.items():
            metrics = result.accuracy_metrics
            report += f"""
🌊 变量: {var_name}
   RMSE: {metrics.rmse:.6f}
   MAE:  {metrics.mae:.6f}
   NSE:  {metrics.nse:.3f}
   R²:   {metrics.r_squared:.3f}
   偏差: {metrics.bias:.6f}
   最大误差: {metrics.max_error:.6f}
   相对RMSE: {metrics.relative_rmse:.3f}
   性能比: {result.performance_ratio:.2f}x
   守恒误差: {result.conservation_error:.6f}
   稳定性评分: {result.stability_score:.3f}
   推荐结论: {result.recommendation}
"""
        
        # 汇总统计
        summary_metrics = self._calculate_summary_metrics(comparison_results)
        report += f"""
📈 汇总统计
{'-'*30}
平均RMSE: {summary_metrics.get('average_rmse', 0):.6f}
平均NSE:  {summary_metrics.get('average_nse', 0):.3f}
平均R²:   {summary_metrics.get('average_r_squared', 0):.3f}
平均性能比: {summary_metrics.get('average_performance_ratio', 0):.2f}x

🎯 总体结论
{'-'*30}
"""
        
        # 生成总体结论
        avg_rmse = summary_metrics.get('average_rmse', float('inf'))
        avg_nse = summary_metrics.get('average_nse', -float('inf'))
        avg_performance = summary_metrics.get('average_performance_ratio', 1.0)
        
        if avg_rmse < 0.05 and avg_nse > 0.75:
            overall_conclusion = f"{test_mode}模式表现优秀，精度高且计算效率提升{avg_performance:.1f}倍，强烈推荐使用"
        elif avg_rmse < 0.10 and avg_nse > 0.50:
            overall_conclusion = f"{test_mode}模式表现良好，在可接受的精度损失下获得{avg_performance:.1f}倍性能提升，推荐使用"
        else:
            overall_conclusion = f"{test_mode}模式精度损失较大，不建议在高精度要求的场景中使用"
        
        report += overall_conclusion + "\n"
        
        # 保存报告
        if save_path:
            try:
                with open(save_path, 'w', encoding='utf-8') as f:
                    f.write(report)
                if self.enable_logging:
                    print(f"📄 报告已保存至: {save_path}")
            except Exception as e:
                if self.enable_logging:
                    print(f"⚠️ 报告保存失败: {e}")
        
        return report
    
    def create_comparison_dataframe(self, comparison_results: Dict[str, ComparisonResult]) -> pd.DataFrame:
        """创建对比结果数据框"""
        if not comparison_results:
            return pd.DataFrame()
        
        data = []
        for var_name, result in comparison_results.items():
            metrics = result.accuracy_metrics.to_dict()
            row = {
                'Variable': var_name,
                'Test_Mode': result.test_mode,
                'Reference_Mode': result.reference_mode,
                **metrics,
                'Performance_Ratio': result.performance_ratio,
                'Conservation_Error': result.conservation_error,
                'Stability_Score': result.stability_score,
                'Recommendation': result.recommendation
            }
            data.append(row)
        
        return pd.DataFrame(data)
    
    def compare_multiple_modes(self, results_dict: Dict[str, Dict[str, Any]],
                             reference_mode: str = "dynamic_wave") -> Dict[str, Dict[str, ComparisonResult]]:
        """对比多种模式与参考模式"""
        if reference_mode not in results_dict:
            raise ValueError(f"参考模式 {reference_mode} 不在结果字典中")
        
        reference_results = results_dict[reference_mode]
        multi_comparison = {}
        
        for mode_name, test_results in results_dict.items():
            if mode_name != reference_mode:
                comparison = self.compare_results(
                    reference_results, test_results, reference_mode, mode_name)
                multi_comparison[mode_name] = comparison
        
        return multi_comparison
    
    def get_accuracy_ranking(self, multi_comparison: Dict[str, Dict[str, ComparisonResult]],
                           metric: str = 'rmse') -> List[Tuple[str, float]]:
        """获取模式精度排名"""
        mode_scores = {}
        
        for mode_name, comparison_results in multi_comparison.items():
            scores = []
            for var_name, result in comparison_results.items():
                if metric.lower() == 'rmse':
                    scores.append(result.accuracy_metrics.rmse)
                elif metric.lower() == 'nse':
                    scores.append(result.accuracy_metrics.nse)
                elif metric.lower() == 'r_squared':
                    scores.append(result.accuracy_metrics.r_squared)
                else:
                    raise ValueError(f"不支持的指标: {metric}")
            
            if scores:
                mode_scores[mode_name] = np.mean(scores)
        
        # 排序（RMSE越小越好，NSE和R²越大越好）
        reverse_order = metric.lower() in ['nse', 'r_squared']
        ranking = sorted(mode_scores.items(), key=lambda x: x[1], reverse=reverse_order)
        
        return ranking
    
    def analyze_convergence_patterns(self) -> Dict[str, Any]:
        """分析历史对比的收敛模式"""
        if len(self.comparison_history) < 3:
            return {'message': '历史数据不足，无法分析收敛模式'}
        
        # 提取历史RMSE趋势
        rmse_trends = {}
        for record in self.comparison_history:
            test_mode = record['test_mode']
            avg_rmse = record['summary_metrics'].get('average_rmse', None)
            
            if avg_rmse is not None:
                if test_mode not in rmse_trends:
                    rmse_trends[test_mode] = []
                rmse_trends[test_mode].append(avg_rmse)
        
        # 分析趋势
        convergence_analysis = {}
        for mode, rmse_values in rmse_trends.items():
            if len(rmse_values) >= 3:
                # 简单线性趋势分析
                x = np.arange(len(rmse_values))
                slope = np.polyfit(x, rmse_values, 1)[0]
                
                convergence_analysis[mode] = {
                    'trend_slope': slope,
                    'is_improving': slope < -0.001,
                    'stability': np.std(rmse_values[-3:]) / np.mean(rmse_values[-3:])
                }
        
        return convergence_analysis