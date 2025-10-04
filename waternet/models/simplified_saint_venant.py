"""
SimplifiedSaintVenantModel 圣维南方程简化模式模型

基于现有SaintVenantModel的扩展，实现多种简化计算模式：
- 动力波模式（完整圣维南方程）
- 扩散波模式（忽略惯性项）
- 运动波模式（忽略惯性项和扩散项）
- 准静态波模式（忽略局部惯性项）

设计特点：
1. 继承现有SaintVenantModel，保持API向后兼容
2. 新增简化模式选择和切换机制
3. 智能模式选择器
4. 精度对比和性能监控
5. 统一的简化模式计算接口

Author: WaterNet Development Team  
Date: 2024-11-05
"""

import numpy as np
import warnings
from typing import Dict, List, Callable, Tuple, Optional, Any, Union
from scipy.optimize import fsolve, brentq
from enum import Enum

from .saint_venant import SaintVenantModel


class ApproximationMode(Enum):
    """简化模式类型枚举"""
    DYNAMIC_WAVE = "dynamic_wave"        # 动力波（完整方程）
    DIFFUSIVE_WAVE = "diffusive_wave"    # 扩散波（忽略惯性项）
    KINEMATIC_WAVE = "kinematic_wave"    # 运动波（忽略惯性+扩散项）
    QUASI_STATIC = "quasi_static"        # 准静态波（忽略局部惯性项）


class SimplifiedSaintVenantModel(SaintVenantModel):
    """
    圣维南方程简化模式模型
    
    在现有SaintVenantModel基础上扩展简化模式功能，实现：
    - 动力波、扩散波、运动波、准静态波四种计算模式
    - 自动模式选择器
    - 模式精度对比
    - 性能监控和统计
    
    继承所有原有功能，同时新增简化模式专用方法。
    """
    
    def __init__(self, name: str, upstream_node: str, downstream_node: str,
                 sections: List[Dict[str, Any]], 
                 approximation_mode: str = "dynamic_wave",
                 solver_type: str = "standard",
                 enable_performance_monitoring: bool = True):
        """
        初始化简化圣维南模型
        
        Args:
            name (str): 模型唯一标识符
            upstream_node (str): 上游边界节点名称
            downstream_node (str): 下游边界节点名称
            sections (List[Dict]): 断面几何数据列表
            approximation_mode (str): 简化模式类型
            solver_type (str): 求解器类型
            enable_performance_monitoring (bool): 是否启用性能监控
        """
        # 初始化基类
        super().__init__(name, upstream_node, downstream_node, sections, 
                        solver_type, enable_performance_monitoring)
        
        # 简化模式配置
        self.approximation_mode = ApproximationMode(approximation_mode)
        
        # 模式选择器和评估器（延迟初始化）
        self._mode_selector = None
        self._accuracy_comparator = None
        
        # 性能监控扩展
        if enable_performance_monitoring:
            self.simplification_metrics = {
                'mode_selection_history': [],
                'approximation_accuracy': {},
                'computational_speedup': {},
                'stability_analysis': {}
            }
        
        # 模式特定参数
        self._mode_parameters = self._initialize_mode_parameters()
        
        print(f"✅ SimplifiedSaintVenantModel 初始化完成")
        print(f"   当前模式: {self.approximation_mode.value}")
        print(f"   断面数量: {len(self.sections)}")
        print(f"   性能监控: {'开启' if enable_performance_monitoring else '关闭'}")
    
    def _initialize_mode_parameters(self) -> Dict[str, Dict]:
        """初始化各模式的特定参数"""
        return {
            'dynamic_wave': {
                'use_inertia_terms': True,
                'use_convection_terms': True,
                'use_pressure_terms': True,
                'use_friction_terms': True,
                'description': '完整圣维南方程（动力波）'
            },
            'diffusive_wave': {
                'use_inertia_terms': False,
                'use_convection_terms': False,
                'use_pressure_terms': True,
                'use_friction_terms': True,
                'description': '扩散波（忽略惯性项）'
            },
            'kinematic_wave': {
                'use_inertia_terms': False,
                'use_convection_terms': False,
                'use_pressure_terms': False,
                'use_friction_terms': True,
                'description': '运动波（仅保留摩阻项）'
            },
            'quasi_static': {
                'use_inertia_terms': False,
                'use_convection_terms': True,
                'use_pressure_terms': True,
                'use_friction_terms': True,
                'description': '准静态波（忽略局部惯性项）'
            }
        }
    
    def set_approximation_mode(self, mode: Union[str, ApproximationMode], 
                             auto_validate: bool = True) -> bool:
        """
        设置简化模式
        
        Args:
            mode (Union[str, ApproximationMode]): 新的简化模式
            auto_validate (bool): 是否自动验证模式适用性
            
        Returns:
            bool: 设置是否成功
        """
        if isinstance(mode, str):
            try:
                mode = ApproximationMode(mode)
            except ValueError:
                available_modes = [m.value for m in ApproximationMode]
                print(f"❌ 无效的简化模式: {mode}")
                print(f"   可用模式: {available_modes}")
                return False
        
        old_mode = self.approximation_mode
        self.approximation_mode = mode
        
        # 记录模式切换
        if self.enable_performance_monitoring:
            self.simplification_metrics['mode_selection_history'].append({
                'timestamp': np.datetime64('now'),
                'old_mode': old_mode.value,
                'new_mode': mode.value,
                'auto_validate': auto_validate
            })
        
        print(f"🔄 简化模式切换: {old_mode.value} → {mode.value}")
        print(f"   描述: {self._mode_parameters[mode.value]['description']}")
        
        # 自动验证适用性
        if auto_validate:
            validation_result = self._validate_mode_applicability()
            if not validation_result['is_suitable']:
                print(f"⚠️  模式适用性警告: {validation_result['warning']}")
                if validation_result['recommended_mode']:
                    print(f"   推荐模式: {validation_result['recommended_mode']}")
        
        return True
    
    def _validate_mode_applicability(self) -> Dict[str, Any]:
        """验证当前模式的适用性"""
        # 获取河道特征参数
        channel_params = self._analyze_channel_characteristics()
        
        # 基于简化的适用性判据
        slope = channel_params['average_slope']
        froude_number = channel_params.get('estimated_froude', 0.5)
        geometry_complexity = channel_params['geometry_complexity']
        
        current_mode = self.approximation_mode.value
        
        # 适用性检查逻辑
        warnings_list = []
        recommended_mode = None
        
        if current_mode == 'kinematic_wave':
            if slope < 0.002:
                warnings_list.append(f"坡度过小({slope:.4f} < 0.002)，扩散效应不可忽略")
                recommended_mode = 'diffusive_wave'
            if froude_number < 0.3:
                warnings_list.append(f"弗劳德数过小({froude_number:.2f} < 0.3)")
        
        elif current_mode == 'diffusive_wave':
            if slope > 0.005:
                warnings_list.append(f"坡度较大({slope:.4f} > 0.005)，运动波可能更适用")
                recommended_mode = 'kinematic_wave'
            if froude_number > 1.0:
                warnings_list.append(f"弗劳德数较大({froude_number:.2f} > 1.0)")
        
        elif current_mode == 'quasi_static':
            if froude_number > 0.3:
                warnings_list.append(f"弗劳德数过大({froude_number:.2f} > 0.3)")
                recommended_mode = 'diffusive_wave'
        
        return {
            'is_suitable': len(warnings_list) == 0,
            'warning': '; '.join(warnings_list) if warnings_list else None,
            'recommended_mode': recommended_mode,
            'channel_parameters': channel_params
        }
    
    def _analyze_channel_characteristics(self) -> Dict[str, float]:
        """分析河道特征参数"""
        # 计算平均坡度
        total_length = sum(seg['length'] for seg in self.segments)
        if total_length > 0:
            total_elevation_drop = (self.sections[0]['elevation'] - 
                                  self.sections[-1]['elevation'])
            average_slope = total_elevation_drop / total_length
        else:
            average_slope = 0.001  # 默认值
        
        # 评估几何复杂度
        elevation_variance = np.var([sec['elevation'] for sec in self.sections])
        roughness_variance = np.var([sec['roughness'] for sec in self.sections])
        geometry_complexity = elevation_variance + roughness_variance * 100
        
        # 估算弗劳德数（基于典型流量）
        typical_Q = 50.0  # 假设典型流量
        try:
            # 使用中间断面估算
            mid_section = self.sections[len(self.sections)//2]
            # 假设水深为1米估算面积
            estimated_area = mid_section['area_func'](mid_section['elevation'] + 1.0)
            if estimated_area > 0:
                velocity = typical_Q / estimated_area
                estimated_froude = velocity / np.sqrt(9.81 * 1.0)  # 假设水深1m
            else:
                estimated_froude = 0.5
        except:
            estimated_froude = 0.5
        
        return {
            'average_slope': abs(average_slope),
            'geometry_complexity': geometry_complexity,
            'estimated_froude': estimated_froude,
            'total_length': total_length,
            'section_count': len(self.sections)
        }
    
    def compute_with_approximation(self, Q: float, downstream_H: float, 
                                 mode: Optional[Union[str, ApproximationMode]] = None,
                                 compare_with_full: bool = False) -> Dict[str, Any]:
        """
        使用指定简化模式计算恒定流
        
        Args:
            Q (float): 恒定流量（m³/s）
            downstream_H (float): 下游边界水位（m）
            mode (Optional): 指定模式，None则使用当前模式
            compare_with_full (bool): 是否与完整模式对比
            
        Returns:
            Dict[str, Any]: 计算结果和性能统计
        """
        # 设置计算模式
        original_mode = self.approximation_mode
        if mode is not None:
            if not self.set_approximation_mode(mode, auto_validate=False):
                return {'success': False, 'error': 'Invalid mode'}
        
        # 记录计算开始时间
        import time
        start_time = time.time()
        
        try:
            # 根据当前模式选择计算方法
            if self.approximation_mode == ApproximationMode.DYNAMIC_WAVE:
                result = self._compute_dynamic_wave(Q, downstream_H)
            elif self.approximation_mode == ApproximationMode.DIFFUSIVE_WAVE:
                result = self._compute_diffusive_wave(Q, downstream_H)
            elif self.approximation_mode == ApproximationMode.KINEMATIC_WAVE:
                result = self._compute_kinematic_wave(Q, downstream_H)
            elif self.approximation_mode == ApproximationMode.QUASI_STATIC:
                result = self._compute_quasi_static_wave(Q, downstream_H)
            else:
                raise ValueError(f"未实现的简化模式: {self.approximation_mode}")
            
            # 计算耗时
            computation_time = time.time() - start_time
            
            # 构建返回结果
            output = {
                'success': True,
                'mode': self.approximation_mode.value,
                'computation_time': computation_time,
                'hydraulic_results': result,
                'input_parameters': {
                    'Q': Q,
                    'downstream_H': downstream_H
                }
            }
            
            # 与完整模式对比
            if compare_with_full and self.approximation_mode != ApproximationMode.DYNAMIC_WAVE:
                comparison_result = self._compare_with_full_model(Q, downstream_H, result)
                output['accuracy_comparison'] = comparison_result
            
            # 记录性能指标
            if self.enable_performance_monitoring:
                self._record_performance_metrics(self.approximation_mode.value, 
                                               computation_time, result)
            
            return output
            
        except Exception as e:
            print(f"❌ 简化模式计算失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'mode': self.approximation_mode.value
            }
        finally:
            # 恢复原始模式
            if mode is not None:
                self.approximation_mode = original_mode
    
    def _compute_dynamic_wave(self, Q: float, downstream_H: float) -> Dict[str, float]:
        """动力波模式计算（完整圣维南方程）"""
        # 直接使用基类的完整方法
        return super().compute_steady_state(Q, downstream_H)
    
    def _compute_diffusive_wave(self, Q: float, downstream_H: float) -> Dict[str, float]:
        """
        扩散波模式计算（忽略惯性项）
        
        扩散波方程：
        连续性方程: ∂A/∂t + ∂Q/∂x = 0
        动量方程: gA∂H/∂x + gA(Sf - S0) = 0
        
        对于恒定流: ∂H/∂x = S0 - Sf
        结合曼宁公式: Sf = n²Q|Q|/(A²R^(4/3))
        """
        n_sections = len(self.sections)
        water_levels = np.zeros(n_sections)
        
        # 设置下游边界条件
        water_levels[-1] = downstream_H
        
        # 从下游向上游逐段计算
        for seg_idx in reversed(range(n_sections - 1)):
            segment = self.segments[seg_idx]
            
            # 获取断面索引
            i = segment['upstream_section']
            j = segment['downstream_section']
            H_down = water_levels[j]
            
            # 使用扩散波方程求解上游水位
            try:
                H_up = self._solve_diffusive_wave_level_improved(
                    Q, H_down, segment, self.sections[i], self.sections[j])
                water_levels[i] = H_up
                
            except Exception as e:
                # 如果数值求解失败，使用能量方程估算
                try:
                    H_up = self._estimate_upstream_level_energy(
                        Q, H_down, segment, self.sections[i], self.sections[j])
                    water_levels[i] = H_up
                except:
                    # 最简单的估算
                    H_up = H_down + segment['slope'] * segment['length'] + 0.1
                    water_levels[i] = H_up
        
        # 计算总蓄水量
        total_volume = self._calculate_total_volume(water_levels, Q)
        
        # 构建结果字典
        result = {'total_volume': total_volume}
        
        # 添加断面水位
        for i, H in enumerate(water_levels):
            result[f'H_section_{i}'] = H
            
        # 添加分段流量
        for i in range(n_sections - 1):
            result[f'Q_seg_{i}'] = Q
            
        return result
    
    def _solve_diffusive_wave_level_improved(self, Q: float, H_down: float,
                                   segment: Dict, section_up: Dict, 
                                   section_down: Dict) -> float:
        """
        改进的扩散波水位求解
        
        扩散波方程: dH/dx = S0 - Sf
        其中 Sf = n²Q|Q|/(A²R^(4/3))
        
        使用迭代方法求解，提高数值稳定性
        """
        def diffusive_residual(H_up):
            try:
                # 计算上下游水力要素
                A_up = section_up['area_func'](H_up)
                A_down = section_down['area_func'](H_down)
                
                if A_up <= 0 or A_down <= 0:
                    return 1e6
                
                # 计算水面宽度
                T_up = section_up['top_width_func'](H_up)
                T_down = section_down['top_width_func'](H_down)
                
                # 计算湿周（梯形断面）
                h_up = H_up - section_up['elevation']
                h_down = H_down - section_down['elevation']
                
                # 估算边坡系数（从面积和底宽推算）
                if h_up > 0 and T_up > 0:
                    # A = h*(b + m*h), T = b + 2*m*h
                    # 简化估算湿周
                    P_up = T_up + 2 * h_up * 1.2  # 假设边坡系数约1.2
                else:
                    P_up = T_up
                    
                if h_down > 0 and T_down > 0:
                    P_down = T_down + 2 * h_down * 1.2
                else:
                    P_down = T_down
                
                # 计算水力半径
                R_up = A_up / P_up if P_up > 0 else 0
                R_down = A_down / P_down if P_down > 0 else 0
                
                # 平均水力半径和面积
                R_avg = (R_up + R_down) / 2.0
                A_avg = (A_up + A_down) / 2.0
                
                # 计算摩阻坡度
                n = segment['roughness']
                if R_avg > 0 and A_avg > 0:
                    V_avg = Q / A_avg
                    Sf = n**2 * V_avg * abs(V_avg) / (R_avg**(4.0/3.0))
                else:
                    Sf = 0.0
                
                # 扩散波方程残差
                dH_dx_actual = (H_up - H_down) / segment['length']
                dH_dx_theory = segment['slope'] - Sf
                
                return dH_dx_actual - dH_dx_theory
                
            except Exception as e:
                return 1e6
        
        # 迭代求解
        H_up_guess = H_down + segment['slope'] * segment['length']  # 初始估算
        
        # 使用牛顿法迭代
        for iteration in range(10):
            residual = diffusive_residual(H_up_guess)
            
            if abs(residual) < 1e-6:
                break
                
            # 数值微分计算梯度
            dh = 0.001
            residual_plus = diffusive_residual(H_up_guess + dh)
            gradient = (residual_plus - residual) / dh
            
            if abs(gradient) > 1e-10:
                # 牛顿法更新
                delta_H = -residual / gradient
                # 限制步长防止发散
                delta_H = np.clip(delta_H, -0.5, 0.5)
                H_up_guess += delta_H
            else:
                break
        
        # 检查结果合理性
        if H_up_guess < section_up['elevation']:
            H_up_guess = section_up['elevation'] + 0.1
        
        return H_up_guess
    
    def _estimate_upstream_level_energy(self, Q: float, H_down: float,
                                      segment: Dict, section_up: Dict,
                                      section_down: Dict) -> float:
        """
        基于能量方程的上游水位估算
        
        能量方程: H1 + V1²/(2g) = H2 + V2²/(2g) + hf
        其中 hf = L * n² * V_avg² / R_avg^(4/3)
        """
        g = 9.81
        
        # 计算下游断面水力要素
        A_down = section_down['area_func'](H_down)
        if A_down <= 0:
            raise ValueError("下游断面面积为零")
        
        V_down = Q / A_down
        
        # 使用迭代求解上游水位
        H_up_guess = H_down + segment['slope'] * segment['length'] + V_down**2 / (4*g)
        
        for _ in range(5):  # 简单迭代
            A_up = section_up['area_func'](H_up_guess)
            if A_up <= 0:
                H_up_guess += 0.1
                continue
                
            V_up = Q / A_up
            
            # 计算平均水力半径（简化）
            T_up = section_up['top_width_func'](H_up_guess)
            T_down = section_down['top_width_func'](H_down)
            
            R_up = A_up / (T_up + 2 * A_up / T_up) if T_up > 0 else A_up / 10
            R_down = A_down / (T_down + 2 * A_down / T_down) if T_down > 0 else A_down / 10
            R_avg = (R_up + R_down) / 2.0
            
            # 计算水头损失
            V_avg = (V_up + V_down) / 2.0
            n = segment['roughness']
            L = segment['length']
            
            if R_avg > 0:
                hf = L * n**2 * V_avg**2 / (R_avg**(4.0/3.0))
            else:
                hf = 0.1  # 默认损失
            
            # 能量方程求解
            H_up_new = H_down + V_down**2 / (2*g) - V_up**2 / (2*g) + hf
            
            # 检查收敛
            if abs(H_up_new - H_up_guess) < 0.001:
                break
                
            H_up_guess = 0.5 * H_up_guess + 0.5 * H_up_new  # 阻尼更新
        
        return max(H_up_guess, section_up['elevation'] + 0.05)
    
    def _compute_kinematic_wave(self, Q: float, downstream_H: float) -> Dict[str, float]:
        """运动波模式计算（改进版）
        
        运动波理论:
        - 忽略惯性项和压力项
        - 假设局部坡度等于摩阻坡度：S0 = Sf
        - 基于曼宁公式的正常水深计算
        - 考虑实际河道坡度变化
        """
        n_sections = len(self.sections)
        water_levels = np.zeros(n_sections)
        
        # 计算河道总坡度用于坡度分配
        total_slope = self._calculate_channel_slope()
        
        # 从下游开始逐断面计算
        water_levels[-1] = downstream_H
        
        for i in range(n_sections-2, -1, -1):  # 从倒数第二个断面开始向上游计算
            try:
                # 获取当前段的局部坡度
                if i < len(self.segments):
                    local_slope = self.segments[i]['slope']
                else:
                    local_slope = total_slope
                
                # 运动波条件下计算正常水深
                H_normal = self._solve_normal_depth_improved(Q, self.sections[i], local_slope)
                
                # 考虑下游水位约束（避免不合理的水位跳跃）
                H_downstream = water_levels[i+1]
                elevation_diff = self.sections[i]['elevation'] - self.sections[i+1]['elevation']
                
                # 确保水位合理性
                min_reasonable_H = H_downstream + elevation_diff - 0.5  # 允许小幅壅水
                max_reasonable_H = H_downstream + elevation_diff + 2.0  # 限制过大水位差
                
                water_levels[i] = np.clip(H_normal, min_reasonable_H, max_reasonable_H)
                
            except Exception as e:
                # 备用估算方法
                water_levels[i] = self._estimate_kinematic_level(i, Q, water_levels, total_slope)
        
        # 计算总蓄水量
        total_volume = self._calculate_total_volume(water_levels, Q)
        
        # 构建结果字典
        result = {'total_volume': total_volume}
        
        for i, H in enumerate(water_levels):
            result[f'H_section_{i}'] = H
            
        for i in range(n_sections - 1):
            result[f'Q_seg_{i}'] = Q
            
        return result
    
    def _solve_normal_depth_improved(self, Q: float, section: Dict, local_slope: float) -> float:
        """求解正常水深（运动波条件，改进版）
        
        基于曼宁公式: Q = (1/n) * A * R^(2/3) * sqrt(S)
        其中 S 为局部坡度
        """
        
        def manning_equation_residual(H):
            """曼宁方程残差"""
            try:
                A = section['area_func'](H)
                if A <= 0:
                    return 1e6
                    
                T = section['top_width_func'](H)
                if T <= 0:
                    return 1e6
                
                # 改进的水力半径计算
                # 对于矩形或梯形断面，使用更精确的湿周计算
                depth = H - section['elevation']
                if depth <= 0:
                    return 1e6
                
                # 计算湿周（简化为底宽 + 2*水深）
                # 假设断面近似为矩形
                bottom_width = T * 0.8  # 估算底宽（经验值）
                P = bottom_width + 2 * depth
                
                if P <= 0:
                    return 1e6
                    
                R = A / P
                
                # 曼宁公式计算
                n = section['roughness']
                
                # 使用传入的局部坡度
                slope = max(local_slope, 1e-6)  # 防止均坡度为零
                
                Q_calculated = (1.0/n) * A * (R**(2.0/3.0)) * np.sqrt(slope)
                
                return Q_calculated - Q
                
            except Exception:
                return 1e6
        
        # 求解范围
        H_min = section['elevation'] + 0.01
        H_max = section['elevation'] + 20.0  # 扩大范围
        
        try:
            # 使用Brent方法求解
            H_normal = brentq(manning_equation_residual, H_min, H_max, xtol=1e-6)
            return H_normal
        except ValueError:
            # 如果求解失败，使用迭代方法
            return self._iterative_normal_depth_solve(Q, section, local_slope)
    
    def _iterative_normal_depth_solve(self, Q: float, section: Dict, local_slope: float) -> float:
        """迭代求解正常水深（备用方法）"""
        H_guess = section['elevation'] + 1.0  # 初始估计
        
        for iteration in range(20):
            try:
                A = section['area_func'](H_guess)
                if A <= 0:
                    H_guess += 0.1
                    continue
                
                T = section['top_width_func'](H_guess)
                if T <= 0:
                    H_guess += 0.1
                    continue
                
                depth = H_guess - section['elevation']
                bottom_width = T * 0.8
                P = bottom_width + 2 * depth
                R = A / P if P > 0 else A / 10
                
                n = section['roughness']
                slope = max(local_slope, 1e-6)
                
                Q_calculated = (1.0/n) * A * (R**(2.0/3.0)) * np.sqrt(slope)
                
                # 计算残差
                residual = Q_calculated - Q
                
                if abs(residual) < Q * 0.01:  # 1%精度
                    break
                
                # 简单的梯度更新
                delta_H = 0.001
                A_plus = section['area_func'](H_guess + delta_H)
                if A_plus > 0:
                    T_plus = section['top_width_func'](H_guess + delta_H)
                    depth_plus = (H_guess + delta_H) - section['elevation']
                    P_plus = bottom_width + 2 * depth_plus
                    R_plus = A_plus / P_plus if P_plus > 0 else A_plus / 10
                    Q_plus = (1.0/n) * A_plus * (R_plus**(2.0/3.0)) * np.sqrt(slope)
                    
                    gradient = (Q_plus - Q_calculated) / delta_H
                    
                    if abs(gradient) > 1e-10:
                        delta_H_update = -residual / gradient
                        # 限制步长
                        delta_H_update = np.clip(delta_H_update, -0.5, 0.5)
                        H_guess += delta_H_update
                    else:
                        H_guess += 0.1 if residual > 0 else -0.1
                else:
                    H_guess += 0.1
                
                # 确保合理范围
                H_guess = max(H_guess, section['elevation'] + 0.01)
                H_guess = min(H_guess, section['elevation'] + 15.0)
                
            except Exception:
                H_guess += 0.1
        
        return max(H_guess, section['elevation'] + 0.1)
    
    def _calculate_channel_slope(self) -> float:
        """计算河道总体坡度"""
        if len(self.sections) < 2:
            return 0.001  # 默认坡度
        
        first_elevation = self.sections[0]['elevation']
        last_elevation = self.sections[-1]['elevation']
        
        # 计算总长度
        total_length = sum(seg['length'] for seg in self.segments) if self.segments else 1000.0
        
        slope = abs(first_elevation - last_elevation) / total_length
        return max(slope, 1e-6)  # 防止零坡度
    
    def _estimate_kinematic_level(self, section_index: int, Q: float, 
                                water_levels: np.ndarray, total_slope: float) -> float:
        """备用的运动波水位估算方法"""
        n_sections = len(self.sections)
        
        if section_index == n_sections - 1:
            # 最下游断面，已知水位
            return water_levels[section_index]
        
        # 基于均匈坡度估算
        downstream_H = water_levels[section_index + 1]
        
        if section_index < len(self.segments):
            segment_length = self.segments[section_index]['length']
        else:
            # 假设平均段长
            total_length = sum(seg['length'] for seg in self.segments) if self.segments else 1000.0
            segment_length = total_length / max(len(self.segments), 1)
        
        # 考虑水深和坑底高程变化
        elevation_current = self.sections[section_index]['elevation']
        elevation_downstream = self.sections[section_index + 1]['elevation']
        
        # 水面坡度近似等于坑底坡度（运动波假设）
        elevation_diff = elevation_current - elevation_downstream
        water_surface_diff = elevation_diff  # 简化假设
        
        estimated_H = downstream_H + water_surface_diff
        
        # 确保水位在合理范围内
        min_H = elevation_current + 0.1
        max_H = elevation_current + 10.0
        
        return np.clip(estimated_H, min_H, max_H)
    
    def _compute_quasi_static_wave(self, Q: float, downstream_H: float) -> Dict[str, float]:
        """准静态波模式计算（改进版）
        
        准静态波理论:
        - 保留对流项，忽略局部惯性项 ∂Q/∂t
        - 方程: ∂(Q²/A)/∂x + gA∂H/∂x + gA(Sf - S0) = 0
        - 在恒定流条件下，简化为保留动量校正的扩散波
        """
        n_sections = len(self.sections)
        water_levels = np.zeros(n_sections)
        
        # 从下游开始逐段计算
        water_levels[-1] = downstream_H
        
        for i in range(n_sections-2, -1, -1):
            try:
                if i < len(self.segments):
                    segment = self.segments[i]
                    section_up = self.sections[i]
                    section_down = self.sections[i+1]
                    H_down = water_levels[i+1]
                    
                    # 准静态波求解（包含动量校正）
                    H_up = self._solve_quasi_static_level(Q, H_down, segment, section_up, section_down)
                    water_levels[i] = H_up
                else:
                    # 备用估算
                    water_levels[i] = self._estimate_upstream_level_simple(i, water_levels)
                    
            except Exception as e:
                # 备用估算
                water_levels[i] = self._estimate_upstream_level_simple(i, water_levels)
        
        # 计算总蓄水量
        total_volume = self._calculate_total_volume(water_levels, Q)
        
        # 构建结果字典
        result = {'total_volume': total_volume}
        
        for i, H in enumerate(water_levels):
            result[f'H_section_{i}'] = H
            
        for i in range(n_sections - 1):
            result[f'Q_seg_{i}'] = Q
            
        return result
    
    def _solve_quasi_static_level(self, Q: float, H_down: float,
                                segment: Dict, section_up: Dict, 
                                section_down: Dict) -> float:
        """
        准静态波水位求解
        
        准静态方程: ∂(Q²/A)/∂x + gA∂H/∂x + gA(Sf - S0) = 0
        重新整理: dH/dx = S0 - Sf - (1/gA) * d(Q²/A)/dx
        
        对于恒定流: dH/dx = S0 - Sf - (Q²/gA²) * dA/dx
        """
        g = 9.81
        
        def quasi_static_residual(H_up):
            """准静态波方程残差"""
            try:
                # 计算上游断面水力要素
                A_up = section_up['area_func'](H_up)
                if A_up <= 0:
                    return 1e6
                
                T_up = section_up['top_width_func'](H_up)
                if T_up <= 0:
                    return 1e6
                
                # 计算下游断面水力要素
                A_down = section_down['area_func'](H_down)
                if A_down <= 0:
                    return 1e6
                
                T_down = section_down['top_width_func'](H_down)
                if T_down <= 0:
                    return 1e6
                
                # 计算摩阻坡度（上游）
                depth_up = H_up - section_up['elevation']
                P_up = T_up + 2 * depth_up  # 简化湿周
                R_up = A_up / P_up if P_up > 0 else A_up / 10
                n = segment['roughness']
                V_up = Q / A_up
                
                if R_up > 0 and V_up != 0:
                    Sf_up = n**2 * V_up * abs(V_up) / (R_up**(4.0/3.0))
                else:
                    Sf_up = 0.0
                
                # 计算动量校正项
                momentum_term = (Q**2 / (g * A_up**2)) - (Q**2 / (g * A_down**2))
                momentum_gradient = momentum_term / segment['length']
                
                # 准静态波方程
                dH_dx_actual = (H_up - H_down) / segment['length']
                dH_dx_theory = segment['slope'] - Sf_up + momentum_gradient
                
                return dH_dx_actual - dH_dx_theory
                
            except Exception:
                return 1e6
        
        # 初始估计（基于扩散波结果）
        H_up_guess = H_down + segment['slope'] * segment['length']
        
        # 使用牛顿法迭代
        for iteration in range(15):
            residual = quasi_static_residual(H_up_guess)
            
            if abs(residual) < 1e-6:
                break
            
            # 数值微分计算梯度
            dh = 0.001
            residual_plus = quasi_static_residual(H_up_guess + dh)
            gradient = (residual_plus - residual) / dh
            
            if abs(gradient) > 1e-10:
                # 牛顿法更新
                delta_H = -residual / gradient
                # 限制步长防止发散
                delta_H = np.clip(delta_H, -0.3, 0.3)
                H_up_guess += delta_H
            else:
                break
        
        # 检查结果合理性
        if H_up_guess < section_up['elevation']:
            H_up_guess = section_up['elevation'] + 0.05
        
        return H_up_guess
    
    def _estimate_upstream_level_simple(self, section_index: int, water_levels: np.ndarray) -> float:
        """简单的上游水位估算（备用方法）"""
        n_sections = len(self.sections)
        
        if section_index == n_sections - 1:
            return water_levels[section_index]
        
        # 基于相邻断面估算
        downstream_H = water_levels[section_index + 1]
        elevation_current = self.sections[section_index]['elevation']
        elevation_downstream = self.sections[section_index + 1]['elevation']
        
        # 简单的坑底坡度估算
        elevation_diff = elevation_current - elevation_downstream
        estimated_H = downstream_H + elevation_diff * 0.8  # 稍微减少坡度影响
        
        # 确保水位在合理范围内
        min_H = elevation_current + 0.05
        max_H = elevation_current + 8.0
        
        return np.clip(estimated_H, min_H, max_H)
    
    def _compare_with_full_model(self, Q: float, downstream_H: float, 
                               approx_result: Dict[str, float]) -> Dict[str, Any]:
        """与完整模型对比分析"""
        try:
            # 使用完整模式计算参考解
            full_result = self._compute_dynamic_wave(Q, downstream_H)
            
            # 计算误差指标
            errors = {}
            
            # 水位误差分析
            water_level_errors = []
            for i in range(len(self.sections)):
                key = f'H_section_{i}'
                if key in approx_result and key in full_result:
                    approx_H = approx_result[key]
                    full_H = full_result[key]
                    error = abs(approx_H - full_H)
                    relative_error = error / full_H if full_H != 0 else 0
                    water_level_errors.append({
                        'section': i,
                        'absolute_error': error,
                        'relative_error': relative_error
                    })
            
            # 总体积误差
            volume_error = abs(approx_result['total_volume'] - full_result['total_volume'])
            volume_relative_error = (volume_error / full_result['total_volume'] 
                                   if full_result['total_volume'] != 0 else 0)
            
            # 统计指标
            abs_errors = [e['absolute_error'] for e in water_level_errors]
            rel_errors = [e['relative_error'] for e in water_level_errors]
            
            comparison = {
                'volume_error': {
                    'absolute': volume_error,
                    'relative': volume_relative_error
                },
                'water_level_errors': {
                    'max_absolute': max(abs_errors) if abs_errors else 0,
                    'mean_absolute': np.mean(abs_errors) if abs_errors else 0,
                    'max_relative': max(rel_errors) if rel_errors else 0,
                    'mean_relative': np.mean(rel_errors) if rel_errors else 0,
                    'rmse': np.sqrt(np.mean([e**2 for e in abs_errors])) if abs_errors else 0
                },
                'detailed_errors': water_level_errors,
                'reference_result': full_result
            }
            
            return comparison
            
        except Exception as e:
            return {'error': f"对比分析失败: {e}"}
    
    def _record_performance_metrics(self, mode: str, computation_time: float, 
                                  result: Dict[str, float]):
        """记录性能指标"""
        if not self.enable_performance_monitoring:
            return
            
        metrics = self.simplification_metrics
        
        # 记录计算时间
        if mode not in metrics['computational_speedup']:
            metrics['computational_speedup'][mode] = []
        metrics['computational_speedup'][mode].append(computation_time)
        
        # 计算相对于动力波的加速比
        if 'dynamic_wave' in metrics['computational_speedup']:
            dynamic_times = metrics['computational_speedup']['dynamic_wave']
            if dynamic_times:
                avg_dynamic_time = np.mean(dynamic_times)
                speedup = avg_dynamic_time / computation_time if computation_time > 0 else 0
                print(f"📊 性能监控: {mode} 相对加速比 = {speedup:.2f}x")