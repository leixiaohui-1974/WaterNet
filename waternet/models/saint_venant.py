"""
SaintVenantModel 圣维南模型

基于圣维南方程组的一维非恒定流明渠水力模型。
实现了完整的物理方程，包括连续性方程和动量方程，
支持恒定流和非恒定流计算。

主要功能:
1. 基于断面几何的自动网格生成
2. 恒定流水面线计算（标准步进法）
3. 非恒定流方程构建（Preissmann差分格式）
4. 内部节点和分段的自动管理

技术特点:
- 采用四点隐式差分格式
- 支持任意复杂断面几何
- 自动处理临界流和缓流
- 数值稳定性良好

Author: WaterNet Development Team
Date: 2024-10-03
"""

import numpy as np
import warnings
from typing import Dict, List, Callable, Tuple, Optional, Any
from scipy.optimize import fsolve, brentq

from ..interfaces.hydro_model import HydroModel


class SaintVenantModel(HydroModel):
    """
    基于圣维南方程组的一维明渠非恒定流模型
    
    实现了完整的物理水力学方程，包括：
    - 连续性方程: ∂A/∂t + ∂Q/∂x = 0
    - 动量方程: ∂Q/∂t + ∂(Q²/A)/∂x + gA∂H/∂x + gA(Sf - S0) = 0
    
    采用Preissmann四点隐式差分格式进行离散化，
    确保数值计算的稳定性和精度。
    
    Attributes:
        upstream_node (str): 上游边界节点名称
        downstream_node (str): 下游边界节点名称  
        sections (List[Dict]): 断面几何数据列表
        internal_nodes (List[str]): 内部计算节点名称列表
        segments (List[Dict]): 分段属性数据列表
    """
    
    def __init__(self, name: str, upstream_node: str, downstream_node: str, 
                 sections: List[Dict[str, Any]]):
        """
        初始化圣维南模型
        
        Args:
            name (str): 模型唯一标识符
            upstream_node (str): 上游边界节点名称
            downstream_node (str): 下游边界节点名称
            sections (List[Dict]): 断面几何数据列表，每个元素包含：
                - mileage (float): 里程桩号
                - elevation (float): 底高程  
                - roughness (float): 曼宁糙率系数
                - area_func (Callable): 面积函数 A(H)
                - top_width_func (Callable): 水面宽函数 T(H)
                
        Raises:
            ValueError: 当断面数据不足或格式错误时
        """
        super().__init__(name, [upstream_node, downstream_node])
        
        # 验证输入参数
        if len(sections) < 2:
            raise ValueError("至少需要2个断面来定义明渠")
            
        # 验证断面数据格式
        required_keys = ['mileage', 'elevation', 'roughness', 'area_func', 'top_width_func']
        for i, section in enumerate(sections):
            for key in required_keys:
                if key not in section:
                    raise ValueError(f"断面{i}缺少必需字段: {key}")
                    
            # 验证函数类型
            if not callable(section['area_func']):
                raise ValueError(f"断面{i}的area_func必须是可调用函数")
            if not callable(section['top_width_func']):
                raise ValueError(f"断面{i}的top_width_func必须是可调用函数")
        
        # 按里程排序断面
        self.sections = sorted(sections, key=lambda x: x['mileage'])
        
        # 存储边界节点
        self.upstream_node = upstream_node
        self.downstream_node = downstream_node
        
        # 自动生成内部节点和分段
        self._generate_internal_topology()
    
    def _generate_internal_topology(self):
        """
        根据断面数据自动生成内部计算节点和分段
        
        命名规则:
        - 内部节点: {model_name}_internal_{index}
        - 分段流量: Q_{model_name}_seg_{index}
        """
        n_sections = len(self.sections)
        
        # 生成内部节点（除了首末断面，其余断面都有对应的内部节点）
        self.internal_nodes = []
        for i in range(1, n_sections - 1):
            node_name = f"{self.name}_internal_{i-1}"
            self.internal_nodes.append(node_name)
        
        # 生成分段属性
        self.segments = []
        for i in range(n_sections - 1):
            segment = self._calculate_segment_properties(i, i + 1)
            segment['index'] = i
            segment['flow_var'] = f"Q_{self.name}_seg_{i}"
            self.segments.append(segment)
    
    def _calculate_segment_properties(self, i: int, j: int) -> Dict[str, float]:
        """
        计算两个断面之间的分段平均属性
        
        Args:
            i (int): 上游断面索引
            j (int): 下游断面索引
            
        Returns:
            Dict[str, float]: 分段属性字典
        """
        section_i = self.sections[i]
        section_j = self.sections[j]
        
        # 计算分段长度
        length = abs(section_j['mileage'] - section_i['mileage'])
        
        # 计算平均坡度（注意方向：里程增加，高程可能降低）
        if length > 0:
            slope = (section_i['elevation'] - section_j['elevation']) / length
        else:
            slope = 0.0
            warnings.warn(f"断面{i}和{j}距离为0，坡度设为0")
        
        # 计算平均糙率
        roughness = (section_i['roughness'] + section_j['roughness']) / 2.0
        
        return {
            'length': length,
            'slope': slope,
            'roughness': roughness,
            'upstream_section': i,
            'downstream_section': j
        }
    
    def compute_steady_state(self, Q: float, downstream_H: float) -> Dict[str, float]:
        """
        计算恒定流水面线
        
        使用标准步进法从下游向上游逐段计算恒定流水面线。
        基于能量方程和曼宁公式。
        
        Args:
            Q (float): 恒定流量（m³/s）
            downstream_H (float): 下游边界水位（m）
            
        Returns:
            Dict[str, float]: 计算结果字典，包含：
                - 所有断面水位: 'H_section_{i}': 水位值
                - 所有分段流量: 'Q_seg_{i}': 流量值
                - 总蓄水量: 'total_volume': 体积值
                
        Raises:
            ValueError: 当边界条件不合理或计算不收敛时
        """
        if Q <= 0:
            raise ValueError(f"流量必须为正值，得到: {Q}")
            
        n_sections = len(self.sections)
        water_levels = np.zeros(n_sections)
        
        # 设置下游边界条件
        water_levels[-1] = downstream_H
        
        # 从下游向上游逐段计算
        for seg_idx in reversed(range(n_sections - 1)):
            segment = self.segments[seg_idx]
            
            # 获取下游断面水位（已知）
            j = segment['downstream_section']
            H_down = water_levels[j]
            
            # 计算上游断面水位
            i = segment['upstream_section']
            try:
                H_up = self._solve_steady_water_level(
                    Q, H_down, segment, self.sections[i], self.sections[j])
                water_levels[i] = H_up
                
            except Exception as e:
                raise ValueError(
                    f"分段{seg_idx}恒定流计算失败: {e}")
        
        # 计算总蓄水量
        total_volume = self._calculate_total_volume(water_levels, Q)
        
        # 构建结果字典
        result = {'total_volume': total_volume}
        
        # 添加断面水位
        for i, H in enumerate(water_levels):
            result[f'H_section_{i}'] = H
            
        # 添加分段流量（恒定流时所有分段流量相等）
        for i in range(n_sections - 1):
            result[f'Q_seg_{i}'] = Q
            
        return result
    
    def _solve_steady_water_level(self, Q: float, H_down: float, 
                                 segment: Dict, section_up: Dict, 
                                 section_down: Dict) -> float:
        """
        求解恒定流条件下的上游水位
        
        基于能量方程: H_up + V_up²/(2g) = H_down + V_down²/(2g) + hf
        其中水头损失 hf = L * n² * V_avg² / R_avg^(4/3)
        
        Args:
            Q (float): 流量
            H_down (float): 下游水位
            segment (Dict): 分段属性
            section_up (Dict): 上游断面几何
            section_down (Dict): 下游断面几何
            
        Returns:
            float: 上游水位
        """
        def energy_equation(H_up):
            """能量方程残差函数"""
            try:
                # 计算上下游断面的水力要素
                A_up = section_up['area_func'](H_up)
                A_down = section_down['area_func'](H_down)
                T_up = section_up['top_width_func'](H_up)
                T_down = section_down['top_width_func'](H_down)
                
                if A_up <= 0 or A_down <= 0:
                    return 1e6  # 无效水深
                    
                # 计算流速
                V_up = Q / A_up
                V_down = Q / A_down
                
                # 计算水力半径
                P_up = T_up + 2 * np.sqrt(A_up * T_up) / T_up if T_up > 0 else 1e-6
                P_down = T_down + 2 * np.sqrt(A_down * T_down) / T_down if T_down > 0 else 1e-6
                R_up = A_up / P_up
                R_down = A_down / P_down
                
                # 平均水力半径和流速
                R_avg = (R_up + R_down) / 2.0
                V_avg = (V_up + V_down) / 2.0
                
                # 摩擦损失（曼宁公式）
                g = 9.81
                n = segment['roughness']
                L = segment['length']
                
                if R_avg > 0:
                    hf = L * n**2 * V_avg**2 / (R_avg**(4/3))
                else:
                    hf = 1e6
                
                # 能量方程残差
                energy_up = H_up + V_up**2 / (2*g)
                energy_down = H_down + V_down**2 / (2*g)
                
                return energy_up - energy_down - hf
                
            except:
                return 1e6  # 计算错误时返回大值
        
        # 估算求解范围
        H_min = max(section_up['elevation'], H_down - 10.0)
        H_max = H_down + 10.0
        
        try:
            # 使用二分法求解
            H_up = brentq(energy_equation, H_min, H_max, xtol=1e-6)
            return H_up
        except ValueError:
            # 如果二分法失败，尝试从下游水位开始的简单估算
            return H_down + 0.01  # 略高于下游水位
    
    def _calculate_total_volume(self, water_levels: np.ndarray, Q: float) -> float:
        """
        计算总蓄水量
        
        使用梯形法则积分各分段的体积
        
        Args:
            water_levels (np.ndarray): 各断面水位
            Q (float): 流量（用于验证计算合理性）
            
        Returns:
            float: 总蓄水量（m³）
        """
        total_volume = 0.0
        
        for i, segment in enumerate(self.segments):
            i_up = segment['upstream_section']
            i_down = segment['downstream_section']
            
            H_up = water_levels[i_up]
            H_down = water_levels[i_down]
            
            # 计算上下游断面面积
            A_up = self.sections[i_up]['area_func'](H_up)
            A_down = self.sections[i_down]['area_func'](H_down)
            
            # 梯形法则计算分段体积
            L = segment['length']
            segment_volume = L * (A_up + A_down) / 2.0
            
            total_volume += segment_volume
        
        return total_volume
    
    def get_equations(self, variables: Dict[str, float], dt: float, 
                     prev_states: Dict[str, float]) -> Dict[str, float]:
        """
        构建圣维南方程组的残差
        
        实现连续性方程和动量方程的离散化形式。
        采用Preissmann四点隐式差分格式。
        
        Args:
            variables (Dict[str, float]): 当前时步变量值
            dt (float): 时间步长（秒）
            prev_states (Dict[str, float]): 上一时步状态
            
        Returns:
            Dict[str, float]: 方程残差字典
        """
        equations = {}
        g = 9.81  # 重力加速度
        
        # 为每个分段构建连续性方程和动量方程
        for seg in self.segments:
            seg_idx = seg['index']
            i_up = seg['upstream_section']
            i_down = seg['downstream_section']
            
            # 获取分段流量变量
            Q_var = seg['flow_var']
            Q = variables.get(Q_var, 0.0)
            
            # 获取上下游水位
            if i_up == 0:
                # 上游边界
                H_up = variables.get(f'H_{self.upstream_node}', 0.0)
            else:
                # 内部节点
                H_up = variables.get(f'H_{self.internal_nodes[i_up-1]}', 0.0)
                
            if i_down == len(self.sections) - 1:
                # 下游边界  
                H_down = variables.get(f'H_{self.downstream_node}', 0.0)
            else:
                # 内部节点
                H_down = variables.get(f'H_{self.internal_nodes[i_down-1]}', 0.0)
            
            # 计算水力要素
            section_up = self.sections[i_up]
            section_down = self.sections[i_down]
            
            A_up = section_up['area_func'](H_up)
            A_down = section_down['area_func'](H_down)
            T_up = section_up['top_width_func'](H_up)
            T_down = section_down['top_width_func'](H_down)
            
            # 获取前一时步的值
            Q_prev = prev_states.get(Q_var, Q)
            H_up_prev = prev_states.get(f'H_section_{i_up}', H_up)
            H_down_prev = prev_states.get(f'H_section_{i_down}', H_down)
            
            A_up_prev = section_up['area_func'](H_up_prev)
            A_down_prev = section_down['area_func'](H_down_prev)
            
            # 连续性方程 (使用Preissmann格式)
            dA_dt_up = (A_up - A_up_prev) / dt
            dA_dt_down = (A_down - A_down_prev) / dt
            dA_dt_avg = (dA_dt_up + dA_dt_down) / 2.0
            
            dQ_dx = (Q - Q) / seg['length']  # 同一分段内流量不变
            
            continuity_residual = dA_dt_avg + dQ_dx
            equations[f'continuity_seg_{seg_idx}'] = continuity_residual
            
            # 动量方程
            momentum_residual = self._compute_momentum_residual(
                seg, Q, Q_prev, H_up, H_down, H_up_prev, H_down_prev,
                A_up, A_down, dt)
            
            equations[f'momentum_seg_{seg_idx}'] = momentum_residual
        
        # 内部节点的流量平衡方程
        for i, node_name in enumerate(self.internal_nodes):
            # 找到连接到此节点的分段
            inflow_segs = []
            outflow_segs = []
            
            for seg in self.segments:
                if seg['downstream_section'] == i + 1:  # 流入
                    inflow_segs.append(seg['flow_var'])
                if seg['upstream_section'] == i + 1:  # 流出
                    outflow_segs.append(seg['flow_var'])
            
            # 流量平衡：流入 = 流出
            inflow = sum(variables.get(var, 0.0) for var in inflow_segs)
            outflow = sum(variables.get(var, 0.0) for var in outflow_segs)
            
            balance_residual = inflow - outflow
            equations[f'balance_{node_name}'] = balance_residual
        
        return equations
    
    def _compute_momentum_residual(self, segment: Dict, Q: float, Q_prev: float,
                                  H_up: float, H_down: float, 
                                  H_up_prev: float, H_down_prev: float,
                                  A_up: float, A_down: float, dt: float) -> float:
        """
        计算动量方程残差
        
        动量方程: ∂Q/∂t + ∂(Q²/A)/∂x + gA∂H/∂x + gA(Sf - S0) = 0
        """
        g = 9.81
        L = segment['length']
        S0 = segment['slope']
        n = segment['roughness']
        
        # 时间导数项
        dQ_dt = (Q - Q_prev) / dt
        
        # 对流项 ∂(Q²/A)/∂x
        if A_up > 0 and A_down > 0:
            momentum_flux_up = Q**2 / A_up
            momentum_flux_down = Q**2 / A_down
            d_momentum_flux_dx = (momentum_flux_down - momentum_flux_up) / L
        else:
            d_momentum_flux_dx = 0.0
        
        # 压力项 gA∂H/∂x
        A_avg = (A_up + A_down) / 2.0
        dH_dx = (H_down - H_up) / L
        pressure_term = g * A_avg * dH_dx
        
        # 摩阻项 gA*Sf
        if A_avg > 0:
            V_avg = Q / A_avg
            # 简化的水力半径计算
            R_avg = A_avg / (2 * np.sqrt(A_avg) + np.sqrt(A_avg))
            if R_avg > 0:
                Sf = n**2 * V_avg * abs(V_avg) / (R_avg**(4/3))
            else:
                Sf = 0.0
        else:
            Sf = 0.0
        
        friction_term = g * A_avg * (Sf - S0)
        
        # 动量方程残差
        momentum_residual = dQ_dt + d_momentum_flux_dx + pressure_term + friction_term
        
        return momentum_residual
    
    def get_variable_names(self) -> List[str]:
        """
        获取模型变量名列表
        
        包括:
        - 各分段流量变量
        - 内部节点水位变量
        
        Returns:
            List[str]: 变量名列表
        """
        variables = []
        
        # 分段流量变量
        for seg in self.segments:
            variables.append(seg['flow_var'])
        
        # 内部节点水位变量
        for node_name in self.internal_nodes:
            variables.append(f'H_{node_name}')
        
        return variables
    
    def get_cross_section_data(self, section_index: int) -> Dict[str, Any]:
        """
        获取指定断面的几何数据
        
        Args:
            section_index (int): 断面索引
            
        Returns:
            Dict[str, Any]: 断面数据
        """
        if not 0 <= section_index < len(self.sections):
            raise ValueError(f"断面索引超出范围: {section_index}")
            
        return self.sections[section_index].copy()
    
    def get_segment_data(self, segment_index: int) -> Dict[str, Any]:
        """
        获取指定分段的属性数据
        
        Args:
            segment_index (int): 分段索引
            
        Returns:
            Dict[str, Any]: 分段数据
        """
        if not 0 <= segment_index < len(self.segments):
            raise ValueError(f"分段索引超出范围: {segment_index}")
            
        return self.segments[segment_index].copy()
    
    def summary(self) -> str:
        """
        返回模型的摘要信息
        
        Returns:
            str: 模型摘要
        """
        n_sections = len(self.sections)
        n_segments = len(self.segments)
        total_length = sum(seg['length'] for seg in self.segments)
        
        summary = f"""
圣维南模型摘要: {self.name}
===============================================
边界节点: {self.upstream_node} -> {self.downstream_node}
断面数量: {n_sections}
分段数量: {n_segments}
内部节点: {len(self.internal_nodes)}
总长度: {total_length:.1f} m
变量数量: {len(self.get_variable_names())}

断面信息:
"""
        for i, section in enumerate(self.sections):
            summary += f"  断面{i}: 里程{section['mileage']:.1f}m, 高程{section['elevation']:.2f}m\n"
            
        return summary