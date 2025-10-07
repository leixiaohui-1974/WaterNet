"""
水网求解策略实现

实现各种求解策略的具体算法，包括：
1. 精细化联立求解（圣维南方程组的全耦合求解）
2. 简化联立求解（降阶模型的选择性联立求解）
3. 串行求解（按拓扑顺序的逐步求解）
4. 并行求解（独立对象的并发计算）
5. 自适应求解（根据耦合强度动态选择策略）

每种策略针对不同的耦合特性和计算需求进行优化。

Author: WaterNet Development Team  
Date: 2024-10-05
"""

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
from typing import Dict, List, Any, Optional, Tuple
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from .water_network_system import (
    WaterNetworkTopology, SolutionConfig, SolutionStrategy, 
    ModelCouplingStrength
)


class CoupledSystemSolver:
    """联立系统求解器 - 处理强耦合对象的联立方程组"""
    
    def __init__(self, config: SolutionConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
    def solve_coupled_system(self, 
                           objects: Dict[str, Any],
                           dt: float,
                           boundary_conditions: Dict[str, Any]) -> Dict[str, Any]:
        """
        求解联立系统
        
        对于强耦合对象（如IDZ模型、圣维南方程），构建联立方程组：
        [A]{x} = {b}
        
        其中：
        - A: 系数矩阵，体现对象间的耦合关系
        - x: 状态向量（流量、水位等）
        - b: 右端项（边界条件、源汇项等）
        """
        n_objects = len(objects)
        n_vars_per_object = 3  # Q, H, V
        n_total = n_objects * n_vars_per_object
        
        # 构建联立方程组
        A_matrix, b_vector = self._build_coupled_system(
            objects, dt, boundary_conditions, n_total
        )
        
        # 求解线性系统
        try:
            solution = self._solve_linear_system(A_matrix, b_vector)
            
            # 解析结果
            results = self._parse_solution(solution, objects, n_vars_per_object)
            
            return results
            
        except Exception as e:
            self.logger.error(f"联立系统求解失败: {e}")
            return self._fallback_solution(objects, dt, boundary_conditions)
    
    def _build_coupled_system(self, 
                            objects: Dict[str, Any],
                            dt: float,
                            boundary_conditions: Dict[str, Any],
                            n_total: int) -> Tuple[sp.csr_matrix, np.ndarray]:
        """构建联立方程组的系数矩阵和右端项"""
        
        # 初始化系数矩阵（稀疏矩阵）
        A_data, A_row, A_col = [], [], []
        b_vector = np.zeros(n_total)
        
        obj_ids = list(objects.keys())
        
        for i, obj_id in enumerate(obj_ids):
            obj = objects[obj_id]
            base_idx = i * 3  # 每个对象3个变量：Q, H, V
            
            # 获取对象的线性化系数
            jacobian = self._get_object_jacobian(obj, dt)
            residual = self._get_object_residual(obj, dt, boundary_conditions.get(obj_id, {}))
            
            # 添加对象内部的耦合关系
            for j in range(3):
                for k in range(3):
                    if abs(jacobian[j, k]) > 1e-12:
                        A_data.append(jacobian[j, k])
                        A_row.append(base_idx + j)
                        A_col.append(base_idx + k)
            
            # 添加对象间的耦合关系
            self._add_inter_object_coupling(
                A_data, A_row, A_col, obj_ids, i, obj, objects
            )
            
            # 设置右端项
            b_vector[base_idx:base_idx+3] = residual
        
        # 构建稀疏矩阵
        A_matrix = sp.csr_matrix((A_data, (A_row, A_col)), shape=(n_total, n_total))
        
        return A_matrix, b_vector
    
    def _get_object_jacobian(self, obj: Any, dt: float) -> np.ndarray:
        """获取对象的雅可比矩阵（线性化系数）"""
        # 对于不同类型的对象，线性化方法不同
        simulation_method = getattr(obj, 'simulation_method', 'unknown')
        
        if simulation_method == 'idz':
            return self._get_idz_jacobian(obj, dt)
        elif simulation_method == 'saint_venant':
            return self._get_saint_venant_jacobian(obj, dt)
        elif simulation_method == 'storage_routing':
            return self._get_storage_routing_jacobian(obj, dt)
        else:
            # 默认简化雅可比矩阵
            return self._get_default_jacobian(obj, dt)
    
    def _get_idz_jacobian(self, obj: Any, dt: float) -> np.ndarray:
        """IDZ模型的雅可比矩阵"""
        # IDZ模型的传递函数矩阵线性化
        # 简化实现：基于当前状态的线性化
        
        J = np.eye(3)  # 3x3单位矩阵作为基础
        
        # 根据IDZ模型特性调整系数
        # 流量方程：dQ/dt = f(Q, H)
        J[0, 0] = -1.0/dt  # dQ/dQ项
        J[0, 1] = 0.1      # dQ/dH项（回水效应）
        
        # 水位方程：dH/dt = g(Q, V)  
        J[1, 0] = 0.05     # dH/dQ项
        J[1, 2] = 0.02     # dH/dV项
        
        # 蓄量方程：dV/dt = Q_in - Q_out
        J[2, 0] = -1.0     # dV/dQ项
        
        return J
    
    def _get_saint_venant_jacobian(self, obj: Any, dt: float) -> np.ndarray:
        """圣维南方程的雅可比矩阵"""
        # 圣维南方程组的线性化
        J = np.zeros((3, 3))
        
        # 获取对象的几何参数
        width = getattr(obj, 'bottom_width', 10.0)
        slope = getattr(obj, 'bottom_slope', 0.001)
        manning = getattr(obj, 'manning_coefficient', 0.03)
        
        # 当前状态
        Q = getattr(obj, 'current_Q_out', 1.0)
        H = getattr(obj, 'current_H', 1.0)
        A = width * H  # 简化为矩形断面
        
        # 连续性方程的线性化
        J[2, 0] = -1.0  # dV/dQ
        J[2, 1] = width  # dV/dH
        
        # 动量方程的线性化（简化）
        if A > 0:
            V = Q / A
            J[0, 0] = V / A  # dQ/dQ项
            J[0, 1] = -Q / (A * H)  # dQ/dH项
        
        return J
    
    def _get_storage_routing_jacobian(self, obj: Any, dt: float) -> np.ndarray:
        """蓄量演算模型的雅可比矩阵"""
        J = np.eye(3)
        
        # 蓄量演算的特征：基于连续性方程和释放关系
        J[0, 1] = 0.1   # 水位影响出流
        J[1, 2] = 0.01  # 蓄量影响水位
        J[2, 0] = -dt   # 出流影响蓄量变化
        
        return J
    
    def _get_default_jacobian(self, obj: Any, dt: float) -> np.ndarray:
        """默认雅可比矩阵（弱耦合情况）"""
        J = np.eye(3)
        J[2, 0] = -dt  # 基本的连续性方程
        return J
    
    def _get_object_residual(self, obj: Any, dt: float, bc: Dict[str, Any]) -> np.ndarray:
        """获取对象的残差向量"""
        residual = np.zeros(3)
        
        # 基本的残差计算
        Q_in = bc.get('Q_in', 0.0)
        Q_out = getattr(obj, 'current_Q_out', 0.0)
        V_old = getattr(obj, 'current_V', 0.0)
        
        # 连续性方程残差
        residual[2] = (Q_in - Q_out) * dt
        
        return residual
    
    def _add_inter_object_coupling(self, 
                                 A_data: List[float],
                                 A_row: List[int], 
                                 A_col: List[int],
                                 obj_ids: List[str],
                                 current_idx: int,
                                 current_obj: Any,
                                 all_objects: Dict[str, Any]):
        """添加对象间的耦合关系"""
        # 这里需要根据水网拓扑添加对象间的连接关系
        # 简化实现：假设相邻对象间有流量连续性约束
        
        if current_idx > 0:
            # 与上游对象的流量连续性
            upstream_base = (current_idx - 1) * 3
            current_base = current_idx * 3
            
            # 上游出流 = 当前入流
            A_data.append(1.0)   # 上游Q系数
            A_row.append(current_base)
            A_col.append(upstream_base)
            
            A_data.append(-1.0)  # 当前Q系数
            A_row.append(current_base)
            A_col.append(current_base)
    
    def _solve_linear_system(self, A: sp.csr_matrix, b: np.ndarray) -> np.ndarray:
        """求解线性系统"""
        solver_type = self.config.solver_options.get('matrix_solver', 'sparse_lu')
        
        if solver_type == 'sparse_lu':
            # 稀疏LU分解
            return spla.spsolve(A, b)
        elif solver_type == 'gmres':
            # GMRES迭代求解
            solution, info = spla.gmres(A, b, 
                                      maxiter=self.config.max_iterations,
                                      tol=self.config.convergence_tolerance)
            if info != 0:
                self.logger.warning(f"GMRES求解器收敛性警告: info={info}")
            return solution
        else:
            # 默认直接求解
            return np.linalg.solve(A.toarray(), b)
    
    def _parse_solution(self, 
                       solution: np.ndarray, 
                       objects: Dict[str, Any],
                       n_vars: int) -> Dict[str, Any]:
        """解析求解结果"""
        results = {}
        obj_ids = list(objects.keys())
        
        for i, obj_id in enumerate(obj_ids):
            base_idx = i * n_vars
            results[obj_id] = {
                'flow_out': solution[base_idx],
                'water_level': solution[base_idx + 1], 
                'volume': solution[base_idx + 2]
            }
        
        return results
    
    def _fallback_solution(self, 
                          objects: Dict[str, Any],
                          dt: float,
                          boundary_conditions: Dict[str, Any]) -> Dict[str, Any]:
        """失败时的回退求解方案"""
        self.logger.info("使用串行求解作为回退方案")
        
        results = {}
        for obj_id, obj in objects.items():
            bc = boundary_conditions.get(obj_id, {})
            try:
                result = obj.step(dt, **bc)
                results[obj_id] = result
            except Exception as e:
                self.logger.error(f"回退求解失败于对象 {obj_id}: {e}")
                results[obj_id] = {
                    'flow_out': 0.0,
                    'water_level': 0.0,
                    'volume': 0.0
                }
        
        return results


class ParallelSolver:
    """并行求解器 - 处理独立对象的并发计算"""
    
    def __init__(self, config: SolutionConfig):
        self.config = config
        self.max_workers = config.solver_options.get('max_workers', 4)
        self.logger = logging.getLogger(__name__)
    
    def solve_parallel(self, 
                      objects: Dict[str, Any],
                      dt: float,
                      boundary_conditions: Dict[str, Any]) -> Dict[str, Any]:
        """并行求解独立对象"""
        
        if not self.config.enable_parallel or len(objects) <= 1:
            return self._sequential_solve(objects, dt, boundary_conditions)
        
        results = {}
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_obj = {
                executor.submit(self._solve_single_object, obj_id, obj, dt, 
                              boundary_conditions.get(obj_id, {})): obj_id
                for obj_id, obj in objects.items()
            }
            
            # 收集结果
            for future in as_completed(future_to_obj):
                obj_id = future_to_obj[future]
                try:
                    result = future.result(timeout=30.0)  # 30秒超时
                    results[obj_id] = result
                except Exception as e:
                    self.logger.error(f"并行求解失败于对象 {obj_id}: {e}")
                    results[obj_id] = self._get_default_result()
        
        return results
    
    def _solve_single_object(self, obj_id: str, obj: Any, dt: float, bc: Dict[str, Any]) -> Dict[str, Any]:
        """求解单个对象"""
        try:
            return obj.step(dt, **bc)
        except Exception as e:
            self.logger.error(f"对象 {obj_id} 求解失败: {e}")
            return self._get_default_result()
    
    def _sequential_solve(self, objects: Dict[str, Any], dt: float, bc: Dict[str, Any]) -> Dict[str, Any]:
        """顺序求解（作为并行求解的备选）"""
        results = {}
        for obj_id, obj in objects.items():
            results[obj_id] = self._solve_single_object(obj_id, obj, dt, bc.get(obj_id, {}))
        return results
    
    def _get_default_result(self) -> Dict[str, Any]:
        """获取默认结果（用于失败情况）"""
        return {
            'flow_out': 0.0,
            'water_level': 0.0,
            'volume': 0.0
        }


class AdaptiveSolver:
    """自适应求解器 - 根据系统特性动态选择最优求解策略"""
    
    def __init__(self, topology: WaterNetworkTopology, config: SolutionConfig):
        self.topology = topology
        self.config = config
        self.coupled_solver = CoupledSystemSolver(config)
        self.parallel_solver = ParallelSolver(config)
        self.logger = logging.getLogger(__name__)
        
        # 性能统计
        self.performance_stats = {
            'coupled_time': [],
            'parallel_time': [],
            'sequential_time': []
        }
    
    def solve_adaptive(self, 
                      dt: float,
                      boundary_conditions: Dict[str, Any]) -> Dict[str, Any]:
        """自适应求解"""
        
        # 分析当前系统状态
        coupling_analysis = self._analyze_current_coupling()
        
        # 选择最优策略
        optimal_strategy = self._select_optimal_strategy(coupling_analysis)
        
        # 执行求解
        start_time = time.time()
        
        if optimal_strategy == SolutionStrategy.COUPLED_SIMPLIFIED:
            results = self._solve_with_selective_coupling(dt, boundary_conditions, coupling_analysis)
        elif optimal_strategy == SolutionStrategy.PARALLEL:
            results = self.parallel_solver.solve_parallel(
                self.topology.objects, dt, boundary_conditions
            )
        else:  # SEQUENTIAL
            results = self._solve_sequential(dt, boundary_conditions)
        
        # 记录性能
        solve_time = time.time() - start_time
        self._record_performance(optimal_strategy, solve_time)
        
        return results
    
    def _analyze_current_coupling(self) -> Dict[str, Any]:
        """分析当前系统的耦合状态"""
        coupling_strengths = self.topology.analyze_coupling_strength()
        
        # 统计各耦合强度的数量
        strength_counts = {
            ModelCouplingStrength.DECOUPLED: 0,
            ModelCouplingStrength.WEAK: 0,
            ModelCouplingStrength.MODERATE: 0,
            ModelCouplingStrength.STRONG: 0
        }
        
        for strength in coupling_strengths.values():
            strength_counts[strength] += 1
        
        total_objects = len(self.topology.objects)
        
        return {
            'strength_counts': strength_counts,
            'total_objects': total_objects,
            'strong_coupling_ratio': strength_counts[ModelCouplingStrength.STRONG] / total_objects,
            'coupling_complexity': self._calculate_coupling_complexity(coupling_strengths)
        }
    
    def _calculate_coupling_complexity(self, coupling_strengths: Dict[str, ModelCouplingStrength]) -> float:
        """计算耦合复杂度指标"""
        weights = {
            ModelCouplingStrength.DECOUPLED: 0.0,
            ModelCouplingStrength.WEAK: 0.2,
            ModelCouplingStrength.MODERATE: 0.5,
            ModelCouplingStrength.STRONG: 1.0
        }
        
        total_weight = sum(weights[strength] for strength in coupling_strengths.values())
        return total_weight / len(coupling_strengths) if coupling_strengths else 0.0
    
    def _select_optimal_strategy(self, coupling_analysis: Dict[str, Any]) -> SolutionStrategy:
        """选择最优求解策略"""
        strong_ratio = coupling_analysis['strong_coupling_ratio']
        complexity = coupling_analysis['coupling_complexity']
        total_objects = coupling_analysis['total_objects']
        
        # 决策树逻辑
        if strong_ratio > 0.6:
            # 大量强耦合对象，使用联立求解
            return SolutionStrategy.COUPLED_SIMPLIFIED
        elif strong_ratio > 0.3 or complexity > 0.5:
            # 中等耦合，使用串行求解
            return SolutionStrategy.SEQUENTIAL
        elif total_objects > 10 and strong_ratio < 0.1:
            # 大量弱耦合对象，使用并行求解
            return SolutionStrategy.PARALLEL
        else:
            # 默认串行求解
            return SolutionStrategy.SEQUENTIAL
    
    def _solve_with_selective_coupling(self, 
                                     dt: float,
                                     boundary_conditions: Dict[str, Any],
                                     coupling_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """选择性联立求解 - 只对强耦合对象联立求解"""
        
        # 分离强耦合和弱耦合对象
        coupling_strengths = self.topology.analyze_coupling_strength()
        
        strong_coupled_objects = {
            obj_id: obj for obj_id, obj in self.topology.objects.items()
            if coupling_strengths[obj_id] == ModelCouplingStrength.STRONG
        }
        
        weak_coupled_objects = {
            obj_id: obj for obj_id, obj in self.topology.objects.items()
            if coupling_strengths[obj_id] != ModelCouplingStrength.STRONG
        }
        
        results = {}
        
        # 强耦合对象联立求解
        if strong_coupled_objects:
            coupled_results = self.coupled_solver.solve_coupled_system(
                strong_coupled_objects, dt, boundary_conditions
            )
            results.update(coupled_results)
        
        # 弱耦合对象并行求解
        if weak_coupled_objects:
            parallel_results = self.parallel_solver.solve_parallel(
                weak_coupled_objects, dt, boundary_conditions
            )
            results.update(parallel_results)
        
        return results
    
    def _solve_sequential(self, dt: float, boundary_conditions: Dict[str, Any]) -> Dict[str, Any]:
        """串行求解"""
        results = {}
        
        # 按拓扑顺序求解
        try:
            topo_order = list(self.topology.graph.topological_sort())
        except:
            # 存在环路，使用对象ID顺序
            topo_order = list(self.topology.objects.keys())
        
        for obj_id in topo_order:
            obj = self.topology.objects[obj_id]
            bc = boundary_conditions.get(obj_id, {})
            
            # 获取上游流量
            upstream_flow = self._get_upstream_flow(obj_id, results)
            if upstream_flow is not None:
                bc['Q_in'] = upstream_flow
            
            try:
                result = obj.step(dt, **bc)
                results[obj_id] = result
            except Exception as e:
                self.logger.error(f"串行求解失败于对象 {obj_id}: {e}")
                results[obj_id] = {
                    'flow_out': 0.0,
                    'water_level': 0.0,
                    'volume': 0.0
                }
        
        return results
    
    def _get_upstream_flow(self, obj_id: str, current_results: Dict[str, Any]) -> Optional[float]:
        """获取上游总流量"""
        predecessors = list(self.topology.graph.predecessors(obj_id))
        if not predecessors:
            return None
        
        total_flow = 0.0
        for pred_id in predecessors:
            if pred_id in current_results:
                total_flow += current_results[pred_id].get('flow_out', 0.0)
        
        return total_flow
    
    def _record_performance(self, strategy: SolutionStrategy, solve_time: float):
        """记录性能统计"""
        if strategy == SolutionStrategy.COUPLED_SIMPLIFIED:
            self.performance_stats['coupled_time'].append(solve_time)
        elif strategy == SolutionStrategy.PARALLEL:
            self.performance_stats['parallel_time'].append(solve_time)
        else:
            self.performance_stats['sequential_time'].append(solve_time)
        
        # 保持统计数据在合理范围内
        for key in self.performance_stats:
            if len(self.performance_stats[key]) > 100:
                self.performance_stats[key] = self.performance_stats[key][-100:]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能统计摘要"""
        summary = {}
        
        for strategy, times in self.performance_stats.items():
            if times:
                summary[strategy] = {
                    'mean_time': np.mean(times),
                    'max_time': np.max(times),
                    'min_time': np.min(times),
                    'total_calls': len(times)
                }
            else:
                summary[strategy] = {
                    'mean_time': 0.0,
                    'max_time': 0.0,
                    'min_time': 0.0,
                    'total_calls': 0
                }
        
        return summary