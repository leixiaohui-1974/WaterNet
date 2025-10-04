"""
ApproximationSelector 近似模式选择器

智能选择最适合的圣维南方程简化模式，基于水力条件、几何特征和精度要求
进行科学的模式推荐。

主要功能：
1. 水力条件分析（坡度、弗劳德数、几何复杂度）
2. 模式适用性评估
3. 自动模式选择和推荐
4. 模式切换决策支持
5. 适用性边界分析

Author: WaterNet Development Team
Date: 2024-11-05
"""

import numpy as np
import warnings
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum

# 导入简化模式枚举
from .simplified_saint_venant import ApproximationMode


@dataclass
class HydraulicConditions:
    """水力条件数据类"""
    slope: float                    # 河道坡度
    froude_number: float           # 弗劳德数
    reynolds_number: Optional[float] = None  # 雷诺数
    flow_depth: Optional[float] = None       # 流动深度
    channel_width: Optional[float] = None    # 河道宽度
    roughness: float = 0.025       # 糙率系数
    
    def __post_init__(self):
        """数据验证"""
        if self.slope < 0:
            raise ValueError("坡度不能为负值")
        if self.froude_number < 0:
            raise ValueError("弗劳德数不能为负值")
        if self.roughness <= 0:
            raise ValueError("糙率系数必须为正值")


@dataclass 
class GeometryComplexity:
    """几何复杂度数据类"""
    elevation_variance: float      # 高程变化方差
    roughness_variance: float     # 糙率变化方差
    cross_section_variation: float # 断面变化程度
    channel_length: float         # 河道长度
    section_count: int            # 断面数量
    
    @property
    def complexity_score(self) -> float:
        """计算几何复杂度评分"""
        # 归一化各指标并计算综合评分
        elevation_score = min(self.elevation_variance / 10.0, 1.0)
        roughness_score = min(self.roughness_variance / 0.01, 1.0)  
        variation_score = min(self.cross_section_variation / 0.5, 1.0)
        
        return (elevation_score + roughness_score + variation_score) / 3.0


@dataclass
class AccuracyRequirement:
    """精度要求数据类"""
    max_relative_error: float = 0.05    # 最大相对误差 (5%)
    max_absolute_error: float = 0.1     # 最大绝对误差 (m)
    conservation_tolerance: float = 0.01 # 质量守恒容差 (1%)
    priority: str = "balanced"          # 优先级: "speed", "accuracy", "balanced"
    
    def __post_init__(self):
        """验证优先级设置"""
        valid_priorities = ["speed", "accuracy", "balanced"]
        if self.priority not in valid_priorities:
            raise ValueError(f"无效的优先级设置: {self.priority}")


class ApproximationSelector:
    """
    近似模式智能选择器
    
    基于水力条件、几何特征和精度要求，智能推荐最适合的
    圣维南方程简化模式。实现科学的决策逻辑和适用性分析。
    """
    
    def __init__(self, enable_logging: bool = True):
        """
        初始化选择器
        
        Args:
            enable_logging (bool): 是否启用日志记录
        """
        self.enable_logging = enable_logging
        self.selection_history = []
        
        # 模式适用性规则表
        self._applicability_rules = self._initialize_applicability_rules()
        
        # 性能特征表
        self._performance_characteristics = self._initialize_performance_characteristics()
        
        if enable_logging:
            print("✅ ApproximationSelector 初始化完成")
    
    def _initialize_applicability_rules(self) -> Dict[str, Dict]:
        """初始化模式适用性规则"""
        return {
            'kinematic_wave': {
                'slope_min': 0.002,
                'froude_min': 0.3,
                'froude_max': 2.0,
                'complexity_max': 0.3,
                'description': '陡坡急流，重力主导',
                'physical_basis': '忽略惯性和扩散项，适用于陡坡河道'
            },
            'diffusive_wave': {
                'slope_min': 0.0001,
                'slope_max': 0.005,
                'froude_min': 0.1,
                'froude_max': 1.0,
                'complexity_max': 0.6,
                'description': '中等坡度，扩散效应显著',
                'physical_basis': '忽略惯性项，保留扩散项，适用于一般河道'
            },
            'quasi_static': {
                'slope_max': 0.002,
                'froude_max': 0.3,
                'complexity_max': 0.4,
                'description': '缓坡慢流，准静态条件',
                'physical_basis': '忽略局部惯性项，适用于缓变流'
            },
            'dynamic_wave': {
                'fallback': True,
                'description': '复杂条件，完整物理方程',
                'physical_basis': '完整圣维南方程，适用于所有条件'
            }
        }
    
    def _initialize_performance_characteristics(self) -> Dict[str, Dict]:
        """初始化性能特征表"""
        return {
            'kinematic_wave': {
                'computational_cost': 1.0,      # 相对计算成本
                'expected_accuracy': 0.85,      # 预期精度（相对于完整模式）
                'numerical_stability': 0.95,    # 数值稳定性
                'implementation_complexity': 1.0 # 实现复杂度
            },
            'diffusive_wave': {
                'computational_cost': 3.0,
                'expected_accuracy': 0.92,
                'numerical_stability': 0.88,
                'implementation_complexity': 2.0
            },
            'quasi_static': {
                'computational_cost': 2.0,
                'expected_accuracy': 0.90,
                'numerical_stability': 0.90,
                'implementation_complexity': 1.5
            },
            'dynamic_wave': {
                'computational_cost': 10.0,
                'expected_accuracy': 1.00,
                'numerical_stability': 0.80,
                'implementation_complexity': 5.0
            }
        }
    
    def select_optimal_mode(self, 
                          hydraulic_conditions: HydraulicConditions,
                          geometry_complexity: GeometryComplexity,
                          accuracy_requirement: AccuracyRequirement) -> Dict[str, Any]:
        """
        选择最优近似模式
        
        Args:
            hydraulic_conditions: 水力条件
            geometry_complexity: 几何复杂度  
            accuracy_requirement: 精度要求
            
        Returns:
            Dict[str, Any]: 选择结果和详细分析
        """
        if self.enable_logging:
            print("🤖 开始智能模式选择分析")
            print(f"   水力条件: 坡度={hydraulic_conditions.slope:.5f}, Fr={hydraulic_conditions.froude_number:.3f}")
            print(f"   几何复杂度: {geometry_complexity.complexity_score:.3f}")
            print(f"   精度要求: {accuracy_requirement.max_relative_error*100:.1f}%, 优先级={accuracy_requirement.priority}")
        
        # 评估每种模式的适用性
        mode_scores = {}
        for mode_name in ['kinematic_wave', 'diffusive_wave', 'quasi_static', 'dynamic_wave']:
            score = self._evaluate_mode_suitability(
                mode_name, hydraulic_conditions, geometry_complexity, accuracy_requirement)
            mode_scores[mode_name] = score
        
        # 选择得分最高的模式
        best_mode = max(mode_scores.keys(), key=lambda x: mode_scores[x]['total_score'])
        best_score = mode_scores[best_mode]
        
        # 构建选择结果
        selection_result = {
            'recommended_mode': ApproximationMode(best_mode),
            'confidence_score': best_score['total_score'],
            'selection_reason': self._generate_selection_reason(best_mode, best_score),
            'all_mode_scores': mode_scores,
            'alternative_modes': self._get_alternative_modes(mode_scores, best_mode),
            'warnings': self._generate_warnings(best_mode, hydraulic_conditions, geometry_complexity)
        }
        
        # 记录选择历史
        self._record_selection(selection_result, hydraulic_conditions, 
                             geometry_complexity, accuracy_requirement)
        
        if self.enable_logging:
            print(f"   推荐模式: {best_mode}")
            print(f"   置信度: {best_score['total_score']:.3f}")
            print(f"   选择原因: {selection_result['selection_reason']}")
        
        return selection_result
    
    def _evaluate_mode_suitability(self, 
                                 mode_name: str,
                                 hydraulic_conditions: HydraulicConditions,
                                 geometry_complexity: GeometryComplexity,
                                 accuracy_requirement: AccuracyRequirement) -> Dict[str, float]:
        """评估特定模式的适用性"""
        
        rules = self._applicability_rules[mode_name]
        performance = self._performance_characteristics[mode_name]
        
        # 初始化评分
        scores = {
            'hydraulic_suitability': 0.0,
            'geometric_suitability': 0.0,
            'accuracy_match': 0.0,
            'performance_score': 0.0,
            'total_score': 0.0
        }
        
        # 1. 水力适用性评分
        scores['hydraulic_suitability'] = self._score_hydraulic_suitability(
            mode_name, hydraulic_conditions, rules)
        
        # 2. 几何适用性评分  
        scores['geometric_suitability'] = self._score_geometric_suitability(
            mode_name, geometry_complexity, rules)
        
        # 3. 精度匹配评分
        scores['accuracy_match'] = self._score_accuracy_match(
            mode_name, accuracy_requirement, performance)
        
        # 4. 性能评分
        scores['performance_score'] = self._score_performance(
            mode_name, accuracy_requirement, performance)
        
        # 5. 计算总评分（加权平均）
        weights = self._get_scoring_weights(accuracy_requirement.priority)
        scores['total_score'] = (
            weights['hydraulic'] * scores['hydraulic_suitability'] +
            weights['geometric'] * scores['geometric_suitability'] +
            weights['accuracy'] * scores['accuracy_match'] +
            weights['performance'] * scores['performance_score']
        )
        
        return scores
    
    def _score_hydraulic_suitability(self, mode_name: str, 
                                   conditions: HydraulicConditions,
                                   rules: Dict) -> float:
        """评分水力适用性"""
        score = 1.0
        
        # 动力波模式总是适用
        if mode_name == 'dynamic_wave':
            return score
        
        # 检查坡度条件
        if 'slope_min' in rules:
            if conditions.slope < rules['slope_min']:
                penalty = (rules['slope_min'] - conditions.slope) / rules['slope_min']
                score *= max(0.0, 1.0 - penalty * 2.0)
        
        if 'slope_max' in rules:
            if conditions.slope > rules['slope_max']:
                penalty = (conditions.slope - rules['slope_max']) / rules['slope_max']
                score *= max(0.0, 1.0 - penalty * 2.0)
        
        # 检查弗劳德数条件
        if 'froude_min' in rules:
            if conditions.froude_number < rules['froude_min']:
                penalty = (rules['froude_min'] - conditions.froude_number) / rules['froude_min']
                score *= max(0.0, 1.0 - penalty * 1.5)
        
        if 'froude_max' in rules:
            if conditions.froude_number > rules['froude_max']:
                penalty = (conditions.froude_number - rules['froude_max']) / rules['froude_max']
                score *= max(0.0, 1.0 - penalty * 1.5)
        
        return max(0.0, score)
    
    def _score_geometric_suitability(self, mode_name: str,
                                   geometry: GeometryComplexity,
                                   rules: Dict) -> float:
        """评分几何适用性"""
        score = 1.0
        
        # 动力波模式对几何复杂度最不敏感
        if mode_name == 'dynamic_wave':
            return score
        
        # 检查复杂度限制
        if 'complexity_max' in rules:
            complexity_score = geometry.complexity_score
            if complexity_score > rules['complexity_max']:
                penalty = (complexity_score - rules['complexity_max']) / rules['complexity_max']
                score *= max(0.0, 1.0 - penalty)
        
        return max(0.0, score)
    
    def _score_accuracy_match(self, mode_name: str,
                            accuracy_req: AccuracyRequirement,
                            performance: Dict) -> float:
        """评分精度匹配度"""
        expected_accuracy = performance['expected_accuracy']
        required_accuracy = 1.0 - accuracy_req.max_relative_error
        
        if expected_accuracy >= required_accuracy:
            # 满足精度要求
            return 1.0
        else:
            # 不满足精度要求，计算缺口
            accuracy_gap = required_accuracy - expected_accuracy
            return max(0.0, 1.0 - accuracy_gap * 2.0)
    
    def _score_performance(self, mode_name: str,
                         accuracy_req: AccuracyRequirement,
                         performance: Dict) -> float:
        """评分性能表现"""
        # 根据优先级调整性能评分
        if accuracy_req.priority == "speed":
            # 速度优先：计算成本越低越好
            cost_score = 1.0 / performance['computational_cost']
            stability_score = performance['numerical_stability']
            return (cost_score * 0.7 + stability_score * 0.3)
        
        elif accuracy_req.priority == "accuracy":
            # 精度优先：预期精度越高越好
            accuracy_score = performance['expected_accuracy']
            stability_score = performance['numerical_stability']
            return (accuracy_score * 0.8 + stability_score * 0.2)
        
        else:  # balanced
            # 平衡模式：综合考虑
            cost_score = 1.0 / performance['computational_cost']
            accuracy_score = performance['expected_accuracy']
            stability_score = performance['numerical_stability']
            return (cost_score * 0.3 + accuracy_score * 0.4 + stability_score * 0.3)
    
    def _get_scoring_weights(self, priority: str) -> Dict[str, float]:
        """获取评分权重"""
        if priority == "speed":
            return {
                'hydraulic': 0.3,
                'geometric': 0.2,
                'accuracy': 0.2,
                'performance': 0.3
            }
        elif priority == "accuracy":
            return {
                'hydraulic': 0.4,
                'geometric': 0.3,
                'accuracy': 0.2,
                'performance': 0.1
            }
        else:  # balanced
            return {
                'hydraulic': 0.3,
                'geometric': 0.25,
                'accuracy': 0.25,
                'performance': 0.2
            }
    
    def _generate_selection_reason(self, mode_name: str, scores: Dict[str, float]) -> str:
        """生成选择原因说明"""
        reasons = []
        
        if scores['hydraulic_suitability'] > 0.8:
            reasons.append("水力条件高度适合")
        elif scores['hydraulic_suitability'] > 0.6:
            reasons.append("水力条件基本适合")
        else:
            reasons.append("水力条件需要注意")
        
        if scores['geometric_suitability'] > 0.8:
            reasons.append("几何条件优良")
        elif scores['geometric_suitability'] > 0.6:
            reasons.append("几何条件可接受")
        
        if scores['accuracy_match'] > 0.8:
            reasons.append("精度要求匹配")
        
        if scores['performance_score'] > 0.7:
            reasons.append("性能表现良好")
        
        # 添加模式特定说明
        mode_desc = self._applicability_rules[mode_name]['description']
        reasons.append(mode_desc)
        
        return "; ".join(reasons)
    
    def _get_alternative_modes(self, mode_scores: Dict, best_mode: str) -> List[Dict]:
        """获取备选模式"""
        # 排除最佳模式，按评分排序
        alternatives = [(mode, scores['total_score']) 
                       for mode, scores in mode_scores.items() 
                       if mode != best_mode]
        alternatives.sort(key=lambda x: x[1], reverse=True)
        
        # 返回前两个备选方案
        result = []
        for mode, score in alternatives[:2]:
            if score > 0.3:  # 只考虑评分合理的备选方案
                result.append({
                    'mode': ApproximationMode(mode),
                    'score': score,
                    'description': self._applicability_rules[mode]['description']
                })
        
        return result
    
    def _generate_warnings(self, mode_name: str,
                          hydraulic_conditions: HydraulicConditions,
                          geometry_complexity: GeometryComplexity) -> List[str]:
        """生成警告信息"""
        warnings = []
        
        # 检查边界条件
        if mode_name == 'kinematic_wave':
            if hydraulic_conditions.slope < 0.002:
                warnings.append("坡度较小，运动波假设可能不够准确")
            if hydraulic_conditions.froude_number < 0.3:
                warnings.append("弗劳德数较小，扩散效应可能重要")
        
        elif mode_name == 'diffusive_wave':
            if hydraulic_conditions.froude_number > 1.0:
                warnings.append("弗劳德数较大，惯性效应可能重要")
            if geometry_complexity.complexity_score > 0.6:
                warnings.append("几何复杂度较高，简化假设需要验证")
        
        elif mode_name == 'quasi_static':
            if hydraulic_conditions.froude_number > 0.3:
                warnings.append("弗劳德数不够小，准静态假设可能失效")
        
        # 通用警告
        if geometry_complexity.complexity_score > 0.8:
            warnings.append("几何复杂度很高，建议考虑使用完整方程")
        
        return warnings
    
    def _record_selection(self, selection_result: Dict,
                         hydraulic_conditions: HydraulicConditions,
                         geometry_complexity: GeometryComplexity,
                         accuracy_requirement: AccuracyRequirement):
        """记录选择历史"""
        record = {
            'timestamp': np.datetime64('now'),
            'recommended_mode': selection_result['recommended_mode'].value,
            'confidence_score': selection_result['confidence_score'],
            'hydraulic_conditions': {
                'slope': hydraulic_conditions.slope,
                'froude_number': hydraulic_conditions.froude_number,
                'roughness': hydraulic_conditions.roughness
            },
            'geometry_complexity': geometry_complexity.complexity_score,
            'accuracy_requirement': accuracy_requirement.priority
        }
        
        self.selection_history.append(record)
        
        # 限制历史记录长度
        if len(self.selection_history) > 100:
            self.selection_history = self.selection_history[-100:]
    
    def analyze_selection_patterns(self) -> Dict[str, Any]:
        """分析选择模式统计"""
        if not self.selection_history:
            return {'message': '暂无选择历史数据'}
        
        # 统计各模式的选择频率
        mode_frequency = {}
        confidence_scores = []
        
        for record in self.selection_history:
            mode = record['recommended_mode']
            mode_frequency[mode] = mode_frequency.get(mode, 0) + 1
            confidence_scores.append(record['confidence_score'])
        
        # 计算统计指标
        total_selections = len(self.selection_history)
        mode_percentages = {mode: count/total_selections * 100 
                          for mode, count in mode_frequency.items()}
        
        analysis = {
            'total_selections': total_selections,
            'mode_frequency': mode_frequency,
            'mode_percentages': mode_percentages,
            'average_confidence': np.mean(confidence_scores),
            'confidence_std': np.std(confidence_scores),
            'most_common_mode': max(mode_frequency.keys(), key=lambda x: mode_frequency[x])
        }
        
        return analysis
    
    def get_applicability_summary(self) -> str:
        """获取适用性规则摘要"""
        summary = "📋 简化模式适用性规则摘要\n"
        summary += "=" * 50 + "\n\n"
        
        for mode_name, rules in self._applicability_rules.items():
            summary += f"🌊 {mode_name.upper()}:\n"
            summary += f"   描述: {rules['description']}\n"
            
            if 'slope_min' in rules:
                summary += f"   最小坡度: {rules['slope_min']}\n"
            if 'slope_max' in rules:
                summary += f"   最大坡度: {rules['slope_max']}\n"
            if 'froude_min' in rules:
                summary += f"   最小弗劳德数: {rules['froude_min']}\n"
            if 'froude_max' in rules:
                summary += f"   最大弗劳德数: {rules['froude_max']}\n"
            if 'complexity_max' in rules:
                summary += f"   最大复杂度: {rules['complexity_max']}\n"
            
            summary += f"   物理基础: {rules['physical_basis']}\n\n"
        
        return summary