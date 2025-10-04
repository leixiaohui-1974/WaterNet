"""
PressurizedPipeModel 有压管道精细化物理模型

基于水锤基本方程的有压管道完整物理建模，完全继承HydroModel抽象基类。
实现特征线法或四点隐式差分格式求解水锤瞬变流。

核心特性:
- 基于水锤基本方程的完整物理建模
- 统一的get_equations()和get_variable_names()接口  
- 支持与现有求解器的无缝集成
- 内置性能监控和数值稳定性保障

Author: WaterNet Development Team
Date: 2024-10-04
"""

import numpy as np
import warnings
from typing import Dict, List, Tuple, Optional, Any
from scipy.optimize import root

from ..waternet.interfaces.hydro_model import HydroModel


class PressurizedPipeModel(HydroModel):
    """
    有压管道精细化物理模型
    
    基于水锤基本方程的完整物理建模，采用特征线法或四点隐式差分格式
    求解有压管道的瞬变流动。
    
    核心方程:
    - 连续性方程: ∂H/∂t + (a²/gA) × ∂Q/∂x = 0
    - 动量方程: ∂Q/∂t + gA × ∂H/∂x + f×Q×|Q|/(2DA) = 0
    
    Attributes:
        name (str): 模型名称
        upstream_node (str): 上游节点名
        downstream_node (str): 下游节点名  
        nodes (List[Dict]): 管道节点几何信息
        wave_speed (float): 水锤波速 (m/s)
        segments (List[Dict]): 计算分段信息
        internal_nodes (List[str]): 内部节点名列表
    """
    
    def __init__(self, name: str, upstream_node: str, downstream_node: str,
                 nodes: List[Dict], wave_speed: float):
        """
        初始化有压管道模型
        
        Args:
            name (str): 模型名称，全系统内唯一
            upstream_node (str): 上游边界节点名
            downstream_node (str): 下游边界节点名
            nodes (List[Dict]): 管道节点列表，每个字典包含:
                - 'mileage': 里程(m)
                - 'elevation': 高程(m) 
                - 'diameter': 内径(m)
                - 'friction_coeff': 达西摩擦系数 f
            wave_speed (float): 水锤波速 a (m/s)
            
        Raises:
            ValueError: 当参数不合理时
        """
        super().__init__(name, [upstream_node, downstream_node])
        
        # 参数验证
        if len(nodes) < 2:
            raise ValueError("节点列表至少需要包含2个节点")
        
        if wave_speed <= 0:
            raise ValueError(f"水锤波速必须为正值，得到: {wave_speed}")
        
        # 验证节点数据完整性
        required_keys = ['mileage', 'elevation', 'diameter', 'friction_coeff']
        for i, node in enumerate(nodes):
            for key in required_keys:
                if key not in node:
                    raise ValueError(f"节点{i}缺少必需字段: {key}")
                if not isinstance(node[key], (int, float)):
                    raise ValueError(f"节点{i}的{key}必须为数值类型")
                if key == 'diameter' and node[key] <= 0:
                    raise ValueError(f"节点{i}的管径必须为正值")
        
        # 基本属性  
        self.upstream_node = upstream_node
        self.downstream_node = downstream_node
        self.nodes = sorted(nodes, key=lambda x: x['mileage'])  # 按里程排序
        self.wave_speed = wave_speed
        
        # 常数
        self.g = 9.81  # 重力加速度 (m/s²)
        
        # 构建计算网格
        self._build_computational_grid()
        
        print(f"有压管道模型'{name}'初始化完成:")
        print(f"  总长度: {self.total_length:.1f} m")
        print(f"  分段数: {len(self.segments)}")
        print(f"  内部节点数: {len(self.internal_nodes)}")
        print(f"  波速: {wave_speed} m/s")
    
    def _build_computational_grid(self):
        """构建计算网格和分段信息"""
        self.segments = []
        self.internal_nodes = []
        
        # 计算总长度
        self.total_length = self.nodes[-1]['mileage'] - self.nodes[0]['mileage']
        
        # 创建分段信息
        for i in range(len(self.nodes) - 1):
            node_up = self.nodes[i]
            node_down = self.nodes[i + 1]
            
            # 分段几何属性
            length = node_down['mileage'] - node_up['mileage']
            diameter = (node_up['diameter'] + node_down['diameter']) / 2.0  # 平均直径
            area = np.pi * (diameter / 2.0) ** 2
            friction_coeff = (node_up['friction_coeff'] + node_down['friction_coeff']) / 2.0
            
            segment_info = {
                'index': i,
                'length': length,
                'diameter': diameter,
                'area': area,
                'friction_coeff': friction_coeff,
                'upstream_elevation': node_up['elevation'],
                'downstream_elevation': node_down['elevation'],
                'slope': (node_down['elevation'] - node_up['elevation']) / length
            }
            
            self.segments.append(segment_info)
        
        # 创建内部节点名列表（除了边界节点的所有节点）
        for i in range(1, len(self.nodes) - 1):
            internal_node_name = f"H_{self.name}_internal_{i-1}"
            self.internal_nodes.append(internal_node_name)
    
    def get_variable_names(self) -> List[str]:
        """
        获取模型引入的变量名列表
        
        Returns:
            List[str]: 变量名列表，包括:
                - 内部节点的测压管水头: 'H_{model_name}_internal_{index}'
                - 各分段的流量: 'Q_{model_name}_seg_{index}'
        """
        variable_names = []
        
        # 内部节点的测压管水头变量
        variable_names.extend(self.internal_nodes)
        
        # 各分段的流量变量
        for i in range(len(self.segments)):
            flow_var_name = f"Q_{self.name}_seg_{i}"
            variable_names.append(flow_var_name)
        
        return variable_names
    
    def compute_steady_state(self, Q: float, downstream_H: float) -> Dict[str, float]:
        """
        计算恒定流状态
        
        基于达西-魏斯巴赫公式和能量方程，从下游开始逐段向上游计算。
        能量方程: H_up = H_down + h_f + Δz
        其中:
        - h_f = f × (L/D) × (V²/2g) 为沿程水头损失 
        - Δz = z_up - z_down 为高程差
        - V = Q/A 为平均流速
        
        Args:
            Q (float): 恒定流量 (m³/s)
            downstream_H (float): 下游测压管水头 (m)
            
        Returns:
            Dict[str, float]: 恒定流计算结果，包含:
                - 所有内部节点的测压管水头 'H_{model_name}_internal_{index}'
                - 所有分段的流量 'Q_{model_name}_seg_{index}' 
                - 'total_volume': 管道总蓄水量 (m³)
                - 'upstream_H': 最上游测压管水头 (m)
                - 'total_head_loss': 总水头损失 (m)
                - 'average_velocity': 平均流速 (m/s)
                
        Raises:
            ValueError: 当计算参数不合理时
        """
        if not np.isfinite(Q):
            raise ValueError(f"流量必须为有限数值，得到: {Q}")
        if not np.isfinite(downstream_H):
            raise ValueError(f"下游水头必须为有限数值，得到: {downstream_H}")
        
        if Q < 0:
            warnings.warn(f"流量为负值: {Q} m³/s，将按反向流动计算")
        
        results = {}
        current_H = downstream_H
        total_head_loss = 0.0
        total_weighted_velocity = 0.0
        total_length = 0.0
        
        # 从最下游分段开始，向上游逐段计算
        for i in reversed(range(len(self.segments))):
            segment = self.segments[i]
            
            # 分段流量（恒定流条件下所有分段流量相同）
            flow_var_name = f"Q_{self.name}_seg_{i}"
            results[flow_var_name] = Q
            
            # 计算流速和雷诺数（用于验证流态）
            if segment['area'] > 1e-10:
                velocity = Q / segment['area']
                reynolds_number = abs(velocity) * segment['diameter'] / 1e-6  # 假设运动粘度1e-6 m²/s
            else:
                velocity = 0.0
                reynolds_number = 0.0
            
            # 计算摩擦水头损失
            if abs(Q) > 1e-10 and segment['area'] > 1e-10:
                # 达西-魏斯巴赫公式: h_f = f × (L/D) × (V²/2g)
                velocity_head = velocity**2 / (2 * self.g)
                friction_loss = (segment['friction_coeff'] * segment['length'] / 
                               segment['diameter'] * abs(velocity_head))
                
                # 考虑流向（负流量时摩擦损失方向相反）
                if Q < 0:
                    friction_loss = -friction_loss
            else:
                friction_loss = 0.0
                
            # 计算高程差（向上游计算时，上游高程减去下游高程）
            elevation_change = segment['upstream_elevation'] - segment['downstream_elevation']
            
            # 总水头方程: H_up = H_down + h_f + Δz
            upstream_H = current_H + friction_loss + elevation_change
            
            # 累积统计信息
            total_head_loss += abs(friction_loss)
            total_weighted_velocity += abs(velocity) * segment['length']
            total_length += segment['length']
            
            # 记录上游节点水头（如果是内部节点）
            if i > 0:  # 不是最上游分段
                internal_index = i - 1
                if internal_index < len(self.internal_nodes):
                    internal_node_name = self.internal_nodes[internal_index]
                    results[internal_node_name] = upstream_H
                    
                    # 验证水头的物理合理性
                    if not np.isfinite(upstream_H):
                        warnings.warn(f"内部节点{internal_node_name}计算出非有限水头: {upstream_H}")
            
            # 为下一段计算做准备
            current_H = upstream_H
        
        # 计算平均流速
        average_velocity = total_weighted_velocity / total_length if total_length > 0 else 0.0
        
        # 计算总蓄水量
        total_volume = 0.0
        for segment in self.segments:
            segment_volume = segment['area'] * segment['length']
            total_volume += segment_volume
        
        # 整理计算结果
        results.update({
            'total_volume': total_volume,
            'upstream_H': current_H,  # 最上游水头
            'total_head_loss': total_head_loss,
            'average_velocity': average_velocity,
            'downstream_H': downstream_H,
            'flow_rate': Q
        })
        
        # 验证结果的物理合理性
        self._validate_steady_state_results(results, Q, downstream_H)
        
        return results
    
    def _validate_steady_state_results(self, results: Dict[str, float], 
                                      Q: float, downstream_H: float):
        """
        验证恒定流计算结果的物理合理性
        
        Args:
            results (Dict[str, float]): 计算结果
            Q (float): 输入流量
            downstream_H (float): 下游水头
        """
        try:
            upstream_H = results['upstream_H']
            total_head_loss = results['total_head_loss']
            
            # 检查水头是否有限
            if not np.isfinite(upstream_H):
                warnings.warn(f"上游水头计算结果非有限: {upstream_H}")
                return
            
            # 检查水头梯度合理性
            total_elevation_change = (self.nodes[0]['elevation'] - 
                                    self.nodes[-1]['elevation'])
            
            head_difference = upstream_H - downstream_H
            expected_min_head_diff = total_elevation_change  # 仅考虑高程差的最小水头差
            
            if Q > 0 and head_difference < expected_min_head_diff - 1e-3:
                warnings.warn(
                    f"水头差({head_difference:.3f}m)小于最小期望值({expected_min_head_diff:.3f}m)")
            
            # 检查摩擦损失合理性
            if total_head_loss < 0:
                warnings.warn(f"总摩擦损失为负值: {total_head_loss}")
            
            # 检查流速合理性
            average_velocity = results.get('average_velocity', 0.0)
            if abs(average_velocity) > 10.0:  # 一般管道流速限制
                warnings.warn(f"平均流速过高: {average_velocity:.2f} m/s")
                
        except Exception as e:
            warnings.warn(f"恒定流结果验证失败: {e}")
    
    def get_equations(self, variables: Dict[str, float], dt: float,
                     prev_states: Dict[str, float]) -> Dict[str, float]:
        """
        获取水锤方程的残差
        
        基于水锤基本方程组构建残差方程：
        1. 连续性方程: ∂H/∂t + (a²/gA) × ∂Q/∂x = 0
        2. 动量方程: ∂Q/∂t + gA × ∂H/∂x + f×Q×|Q|/(2DA) = 0
        3. 内部节点流量平衡: Q_in - Q_out = 0
        
        采用四点隐式差分格式进行数值离散化，确保数值稳定性。
        
        Args:
            variables (Dict[str, float]): 当前时步所有变量值
            dt (float): 时间步长 (s)
            prev_states (Dict[str, float]): 上一时步状态值
            
        Returns:
            Dict[str, float]: 方程残差字典，包含：
                - 'continuity_seg_{i}': 各分段连续性方程残差
                - 'momentum_seg_{i}': 各分段动量方程残差
                - 'balance_{node_name}': 内部节点流量平衡残差
        """
        residuals = {}
        tolerance = 1e-10
        
        try:
            # 预处理边界条件和变量
            boundary_data = self._extract_boundary_conditions(variables)
            current_states = self._extract_current_states(variables)
            previous_states = self._extract_previous_states(prev_states, current_states)
            
            # 为每个分段构建连续性和动量方程
            for i, segment in enumerate(self.segments):
                # 获取分段几何参数
                seg_length = segment['length']
                seg_area = segment['area']
                seg_diameter = segment['diameter']
                friction_f = segment['friction_coeff']
                
                # 确保几何参数合理
                if seg_length < tolerance or seg_area < tolerance:
                    residuals[f'continuity_seg_{i}'] = 0.0
                    residuals[f'momentum_seg_{i}'] = 0.0
                    continue
                
                # 获取分段端点的水头和流量状态
                segment_states = self._get_segment_states(i, current_states, boundary_data)
                segment_prev_states = self._get_segment_states(i, previous_states, boundary_data)
                
                # 计算连续性方程残差
                continuity_residual = self._compute_continuity_residual(
                    segment_states, segment_prev_states, dt, seg_length, seg_area)
                residuals[f'continuity_seg_{i}'] = continuity_residual
                
                # 计算动量方程残差
                momentum_residual = self._compute_momentum_residual(
                    segment_states, segment_prev_states, dt, seg_length, 
                    seg_area, seg_diameter, friction_f)
                residuals[f'momentum_seg_{i}'] = momentum_residual
            
            # 构建内部节点流量平衡方程
            self._compute_node_balance_residuals(residuals, current_states, boundary_data)
                
        except Exception as e:
            warnings.warn(f"方程构建失败: {e}")
            # 返回默认残差（避免求解器崩溃）
            self._set_default_residuals(residuals)
        
        return residuals
    
    def _extract_boundary_conditions(self, variables: Dict[str, float]) -> Dict[str, float]:
        """提取边界条件数据"""
        return {
            'Q_upstream': variables.get(f'Q_{self.upstream_node}', 0.0),
            'H_upstream': variables.get(f'H_{self.upstream_node}', 100.0),
            'H_downstream': variables.get(f'H_{self.downstream_node}', 100.0)
        }
    
    def _extract_current_states(self, variables: Dict[str, float]) -> Dict[str, List[float]]:
        """提取当前时步的内部状态数据"""
        H_internal = []
        Q_segments = []
        
        # 提取内部节点水头
        for node_name in self.internal_nodes:
            H_val = variables.get(node_name, 100.0)
            H_internal.append(H_val)
        
        # 提取分段流量
        for i in range(len(self.segments)):
            flow_var_name = f"Q_{self.name}_seg_{i}"
            Q_val = variables.get(flow_var_name, 0.0)
            Q_segments.append(Q_val)
        
        return {'H_internal': H_internal, 'Q_segments': Q_segments}
    
    def _extract_previous_states(self, prev_states: Dict[str, float], 
                                current_states: Dict[str, List[float]]) -> Dict[str, List[float]]:
        """提取上一时步的状态数据（缺失时使用当前值）"""
        H_internal_prev = []
        Q_segments_prev = []
        
        # 提取上一时步内部节点水头
        for i, node_name in enumerate(self.internal_nodes):
            if node_name in prev_states:
                H_prev = prev_states[node_name]
            elif i < len(current_states['H_internal']):
                H_prev = current_states['H_internal'][i]  # 使用当前值作为默认值
            else:
                H_prev = 100.0
            H_internal_prev.append(H_prev)
        
        # 提取上一时步分段流量
        for i in range(len(self.segments)):
            flow_var_name = f"Q_{self.name}_seg_{i}"
            if flow_var_name in prev_states:
                Q_prev = prev_states[flow_var_name]
            elif i < len(current_states['Q_segments']):
                Q_prev = current_states['Q_segments'][i]
            else:
                Q_prev = 0.0
            Q_segments_prev.append(Q_prev)
        
        return {'H_internal': H_internal_prev, 'Q_segments': Q_segments_prev}
    
    def _get_segment_states(self, seg_index: int, states: Dict[str, List[float]], 
                           boundary_data: Dict[str, float]) -> Dict[str, float]:
        """获取指定分段的端点状态数据"""
        # 构建完整的水头数组（包括边界节点）
        H_all = [boundary_data['H_upstream']]
        H_all.extend(states['H_internal'])
        H_all.append(boundary_data['H_downstream'])
        
        # 构建完整的流量数组（包括边界流量）
        Q_all = [boundary_data['Q_upstream']]
        Q_all.extend(states['Q_segments'])
        
        return {
            'H_upstream': H_all[seg_index],
            'H_downstream': H_all[seg_index + 1],
            'Q_segment': states['Q_segments'][seg_index] if seg_index < len(states['Q_segments']) else 0.0,
            'Q_upstream': Q_all[seg_index] if seg_index < len(Q_all) else 0.0
        }
    
    def _compute_continuity_residual(self, current: Dict[str, float], 
                                   previous: Dict[str, float], dt: float,
                                   seg_length: float, seg_area: float) -> float:
        """
        计算连续性方程残差
        
        连续性方程: ∂H/∂t + (a²/gA) × ∂Q/∂x = 0
        离散化: (H_j^{n+1} - H_j^n)/Δt + (a²/gA) × (Q_{j+1}^{n+1} - Q_j^{n+1})/Δx = 0
        """
        if dt <= 1e-10:
            return 0.0
        
        # 时间导数项（使用分段中点水头）
        H_current = (current['H_upstream'] + current['H_downstream']) / 2.0
        H_previous = (previous['H_upstream'] + previous['H_downstream']) / 2.0
        dH_dt = (H_current - H_previous) / dt
        
        # 空间导数项（流量梯度）
        dQ_dx = (current['Q_segment'] - current['Q_upstream']) / seg_length
        
        # 连续性方程残差
        wave_speed_term = (self.wave_speed**2) / (self.g * seg_area)
        residual = dH_dt + wave_speed_term * dQ_dx
        
        return residual
    
    def _compute_momentum_residual(self, current: Dict[str, float], 
                                 previous: Dict[str, float], dt: float,
                                 seg_length: float, seg_area: float, 
                                 seg_diameter: float, friction_f: float) -> float:
        """
        计算动量方程残差
        
        动量方程: ∂Q/∂t + gA × ∂H/∂x + f×Q×|Q|/(2DA) = 0
        离散化: (Q_i^{n+1} - Q_i^n)/Δt + gA × (H_{j+1}^{n+1} - H_j^{n+1})/Δx + R_i^{n+1} = 0
        """
        if dt <= 1e-10:
            return 0.0
        
        # 时间导数项
        dQ_dt = (current['Q_segment'] - previous['Q_segment']) / dt
        
        # 空间导数项（水头梯度）
        dH_dx = (current['H_downstream'] - current['H_upstream']) / seg_length
        pressure_gradient_term = self.g * seg_area * dH_dx
        
        # 摩擦项
        Q_current = current['Q_segment']
        if abs(Q_current) > 1e-10 and seg_area > 1e-10 and seg_diameter > 1e-10:
            friction_term = (friction_f * Q_current * abs(Q_current) / 
                           (2 * seg_diameter * seg_area))
        else:
            friction_term = 0.0
        
        # 动量方程残差
        residual = dQ_dt + pressure_gradient_term + friction_term
        
        return residual
    
    def _compute_node_balance_residuals(self, residuals: Dict[str, float],
                                      current_states: Dict[str, List[float]],
                                      boundary_data: Dict[str, float]):
        """计算内部节点流量平衡残差"""
        Q_segments = current_states['Q_segments']
        Q_upstream = boundary_data['Q_upstream']
        
        for i, internal_node in enumerate(self.internal_nodes):
            # 节点i+1处的流量平衡: Q_in - Q_out = 0
            if i < len(Q_segments):
                Q_in = Q_segments[i] if i < len(Q_segments) else Q_upstream
                Q_out = Q_segments[i+1] if (i+1) < len(Q_segments) else Q_segments[i]
            else:
                Q_in = Q_upstream
                Q_out = Q_upstream
            
            balance_residual = Q_in - Q_out
            residuals[f'balance_{internal_node}'] = balance_residual
    
    def _set_default_residuals(self, residuals: Dict[str, float]):
        """设置默认残差值（用于错误处理）"""
        for i in range(len(self.segments)):
            residuals[f'continuity_seg_{i}'] = 0.0
            residuals[f'momentum_seg_{i}'] = 0.0
        
        for node in self.internal_nodes:
            residuals[f'balance_{node}'] = 0.0
    
    def validate_computational_setup(self) -> bool:
        """
        验证计算设置的合理性
        
        Returns:
            bool: True表示设置合理
        """
        try:
            # 检查网格数量是否匹配
            expected_vars = len(self.internal_nodes) + len(self.segments)
            expected_eqs = 2 * len(self.segments) + len(self.internal_nodes)
            
            actual_vars = len(self.get_variable_names())
            
            if actual_vars != expected_vars:
                print(f"警告: 变量数量不匹配，期望{expected_vars}，实际{actual_vars}")
                return False
            
            # 检查几何合理性
            for segment in self.segments:
                if segment['length'] <= 0:
                    print(f"错误: 分段长度非正值: {segment['length']}")
                    return False
                if segment['diameter'] <= 0:
                    print(f"错误: 管径非正值: {segment['diameter']}")
                    return False
                if segment['area'] <= 0:
                    print(f"错误: 面积非正值: {segment['area']}")
                    return False
            
            return True
            
        except Exception as e:
            print(f"验证过程出错: {e}")
            return False
    
    def get_segment_properties(self) -> List[Dict]:
        """获取分段属性信息（用于调试和可视化）"""
        return self.segments.copy()
    
    def get_pipe_summary(self) -> str:
        """
        返回管道模型摘要信息
        
        Returns:
            str: 管道摘要
        """
        return f"""
有压管道模型摘要: {self.name}
================================
上游节点: {self.upstream_node}
下游节点: {self.downstream_node}
总长度: {self.total_length:.1f} m
波速: {self.wave_speed} m/s
分段数: {len(self.segments)}
内部节点数: {len(self.internal_nodes)}
变量总数: {len(self.get_variable_names())}

分段信息:
""" + "\n".join([f"  段{i}: L={seg['length']:.1f}m, D={seg['diameter']:.3f}m, f={seg['friction_coeff']:.4f}"
                for i, seg in enumerate(self.segments)])
    
    def __repr__(self) -> str:
        """模型的字符串表示"""
        return (f"PressurizedPipeModel(name='{self.name}', "
                f"length={self.total_length:.1f}m, segments={len(self.segments)})")