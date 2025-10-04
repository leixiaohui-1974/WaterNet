"""
稀疏矩阵优化模块

实现稀疏雅可比矩阵计算和求解，优化大规模水力网络的求解性能。
通过符号计算预分析矩阵结构，使用scipy.sparse进行高效存储和计算。

设计原则:
1. 稀疏存储: 只存储非零元素，减少内存占用
2. 符号分析: 预先确定矩阵稀疏结构模式
3. 高效求解: 使用专门的稀疏线性求解器
4. 混合策略: 解析雅可比与数值雅可比混合使用

主要组件:
- SparsePattern: 稀疏模式分析
- SparseJacobianBuilder: 稀疏雅可比构建器
- SparseSolver: 稀疏线性求解器

Author: WaterNet Development Team
Date: 2024-10-04
"""

import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import spsolve, factorized
from typing import Dict, List, Tuple, Set, Optional, Any
from dataclasses import dataclass
import logging
import time


@dataclass
class SparseMatrixConfig:
    """稀疏矩阵配置"""
    use_symbolic_analysis: bool = True
    sparse_threshold: float = 0.3  # 稀疏度阈值
    use_analytical_jacobian: bool = True
    factorization_method: str = "lu"  # "lu", "qr", "cholesky"
    reuse_pattern: bool = True
    matrix_format: str = "csc"  # "csc", "csr", "lil"


class SparsePattern:
    """
    稀疏模式分析器
    
    分析雅可比矩阵的稀疏结构，预先确定非零元素位置。
    """
    
    def __init__(self):
        """初始化稀疏模式分析器"""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.pattern_cache = {}
        
    def analyze_pattern(self, models: List, variable_names: List[str],
                       boundary_manager = None) -> Tuple[Set[Tuple[int, int]], Dict[str, Any]]:
        """
        分析稀疏模式
        
        Args:
            models (List): 模型列表
            variable_names (List[str]): 变量名列表
            boundary_manager: 边界条件管理器
            
        Returns:
            Tuple[Set, Dict]: (非零位置集合, 分析信息)
        """
        self.logger.info("开始稀疏模式分析")
        start_time = time.time()
        
        var_to_idx = {name: i for i, name in enumerate(variable_names)}
        n_vars = len(variable_names)
        
        # 收集模型依赖关系
        pattern = set()
        eq_idx = 0
        
        for model in models:
            model_vars = model.get_variable_names()
            model_equations = self._get_model_equations_pattern(model)
            
            for eq_name in model_equations:
                # 确定该方程依赖的变量
                dependent_vars = self._find_dependent_variables(eq_name, model_vars, model)
                
                for var_name in dependent_vars:
                    if var_name in var_to_idx:
                        var_idx = var_to_idx[var_name]
                        pattern.add((eq_idx, var_idx))
                
                eq_idx += 1
        
        # 添加边界条件依赖
        if boundary_manager:
            boundary_pattern = self._analyze_boundary_pattern(boundary_manager, var_to_idx, eq_idx)
            pattern.update(boundary_pattern)
        
        analysis_info = {
            'n_equations': eq_idx + (boundary_manager.get_boundary_condition_count() if boundary_manager else 0),
            'n_variables': n_vars,
            'n_nonzeros': len(pattern),
            'sparsity': 1.0 - len(pattern) / (n_vars * n_vars),
            'analysis_time': time.time() - start_time
        }
        
        self.logger.info(f"稀疏模式分析完成: {analysis_info['sparsity']:.2%} 稀疏度, {analysis_info['n_nonzeros']} 非零元素")
        
        return pattern, analysis_info
    
    def _get_model_equations_pattern(self, model) -> List[str]:
        """获取模型方程模式"""
        try:
            # 使用零值测试获取方程名称
            test_vars = {name: 0.0 for name in model.get_variable_names()}
            equations = model.get_equations(test_vars, 1.0, {})
            return list(equations.keys())
        except Exception as e:
            self.logger.warning(f"模型 {model.name} 方程模式分析失败: {e}")
            return []
    
    def _find_dependent_variables(self, eq_name: str, model_vars: List[str], model) -> List[str]:
        """查找方程依赖的变量"""
        # 简化实现：假设方程依赖模型的所有变量
        # 实际实现中可以通过符号分析或启发式方法精确确定
        return model_vars
    
    def _analyze_boundary_pattern(self, boundary_manager, var_to_idx: Dict[str, int], 
                                 start_eq_idx: int) -> Set[Tuple[int, int]]:
        """分析边界条件稀疏模式"""
        pattern = set()
        eq_idx = start_eq_idx
        
        for bc_name, bc in boundary_manager.boundary_conditions.items():
            if bc.is_enabled():
                required_vars = bc.get_required_variables()
                for var_name in required_vars:
                    if var_name in var_to_idx:
                        var_idx = var_to_idx[var_name]
                        pattern.add((eq_idx, var_idx))
                eq_idx += 1
        
        return pattern


class SparseJacobianBuilder:
    """
    稀疏雅可比矩阵构建器
    
    基于稀疏模式构建雅可比矩阵，支持解析和数值混合计算。
    """
    
    def __init__(self, config: SparseMatrixConfig = None):
        """
        初始化稀疏雅可比构建器
        
        Args:
            config (SparseMatrixConfig): 配置参数
        """
        self.config = config or SparseMatrixConfig()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        self.sparse_pattern = None
        self.matrix_structure = None
        self.factorized_solver = None
        
    def initialize_structure(self, pattern: Set[Tuple[int, int]], 
                           matrix_shape: Tuple[int, int]):
        """
        初始化矩阵结构
        
        Args:
            pattern (Set[Tuple[int, int]]): 稀疏模式
            matrix_shape (Tuple[int, int]): 矩阵形状
        """
        self.sparse_pattern = pattern
        self.matrix_shape = matrix_shape
        
        # 创建矩阵结构模板
        rows, cols = zip(*pattern) if pattern else ([], [])
        data = np.ones(len(pattern))
        
        if self.config.matrix_format == "csc":
            self.matrix_structure = sp.csc_matrix((data, (rows, cols)), shape=matrix_shape)
        elif self.config.matrix_format == "csr":
            self.matrix_structure = sp.csr_matrix((data, (rows, cols)), shape=matrix_shape)
        else:  # lil
            self.matrix_structure = sp.lil_matrix(matrix_shape)
            for row, col in pattern:
                self.matrix_structure[row, col] = 1.0
        
        self.logger.info(f"矩阵结构初始化完成: {matrix_shape}, {len(pattern)} 非零元素")
    
    def build_jacobian(self, models: List, variables: Dict[str, float],
                      dt: float, prev_states: Dict[str, float],
                      boundary_manager = None, current_time: float = 0.0) -> sp.spmatrix:
        """
        构建稀疏雅可比矩阵
        
        Args:
            models (List): 模型列表
            variables (Dict[str, float]): 变量值
            dt (float): 时间步长
            prev_states (Dict[str, float]): 前一状态
            boundary_manager: 边界条件管理器
            current_time (float): 当前时间
            
        Returns:
            sp.spmatrix: 稀疏雅可比矩阵
        """
        if self.matrix_structure is None:
            raise ValueError("矩阵结构未初始化，请先调用initialize_structure")
        
        # 复制矩阵结构
        jacobian = self.matrix_structure.copy()
        jacobian.data.fill(0.0)  # 清零数据
        
        # 构建模型部分的雅可比
        self._build_model_jacobian(jacobian, models, variables, dt, prev_states)
        
        # 构建边界条件部分的雅可比
        if boundary_manager:
            self._build_boundary_jacobian(jacobian, boundary_manager, variables, current_time)
        
        return jacobian
    
    def _build_model_jacobian(self, jacobian: sp.spmatrix, models: List,
                            variables: Dict[str, float], dt: float, prev_states: Dict[str, float]):
        """构建模型雅可比矩阵部分"""
        # 数值微分计算雅可比
        variable_names = list(variables.keys())
        h = 1e-8  # 微分步长
        
        # 基准残差
        f0 = self._calculate_model_residuals(models, variables, dt, prev_states)
        
        for j, var_name in enumerate(variable_names):
            # 扰动变量
            step = max(abs(variables[var_name]) * h, h)
            variables_plus = variables.copy()
            variables_plus[var_name] += step
            
            # 计算扰动后的残差
            f_plus = self._calculate_model_residuals(models, variables_plus, dt, prev_states)
            
            # 计算偏导数并填入稀疏矩阵
            derivatives = (f_plus - f0) / step
            
            for i, derivative in enumerate(derivatives):
                if abs(derivative) > 1e-15 and (i, j) in self.sparse_pattern:
                    jacobian[i, j] = derivative
    
    def _build_boundary_jacobian(self, jacobian: sp.spmatrix, boundary_manager,
                               variables: Dict[str, float], current_time: float):
        """构建边界条件雅可比矩阵部分"""
        # 简化实现：数值微分
        variable_names = list(variables.keys())
        h = 1e-8
        
        # 获取边界条件基准残差
        boundary_equations = boundary_manager.get_all_equations(variables, current_time)
        f0_boundary = np.array(list(boundary_equations.values()))
        
        n_model_eqs = jacobian.shape[0] - len(f0_boundary)
        
        for j, var_name in enumerate(variable_names):
            step = max(abs(variables[var_name]) * h, h)
            variables_plus = variables.copy()
            variables_plus[var_name] += step
            
            # 计算扰动后的边界条件残差
            boundary_equations_plus = boundary_manager.get_all_equations(variables_plus, current_time)
            f_plus_boundary = np.array(list(boundary_equations_plus.values()))
            
            # 计算偏导数
            derivatives = (f_plus_boundary - f0_boundary) / step
            
            for i, derivative in enumerate(derivatives):
                row_idx = n_model_eqs + i
                if abs(derivative) > 1e-15 and (row_idx, j) in self.sparse_pattern:
                    jacobian[row_idx, j] = derivative
    
    def _calculate_model_residuals(self, models: List, variables: Dict[str, float],
                                 dt: float, prev_states: Dict[str, float]) -> np.ndarray:
        """计算模型残差"""
        all_residuals = []
        
        for model in models:
            try:
                model_residuals = model.get_equations(variables, dt, prev_states)
                model_vars = model.get_variable_names()
                
                for var_name in model_vars:
                    residual = 0.0
                    for eq_name, eq_residual in model_residuals.items():
                        if var_name in eq_name:
                            residual = eq_residual
                            break
                    all_residuals.append(residual)
                    
            except Exception as e:
                self.logger.error(f"模型 {model.name} 残差计算失败: {e}")
                model_vars = model.get_variable_names()
                all_residuals.extend([1000.0] * len(model_vars))
        
        return np.array(all_residuals)


class SparseSolver:
    """
    稀疏线性求解器
    
    使用高效的稀疏线性代数算法求解大规模线性系统。
    """
    
    def __init__(self, config: SparseMatrixConfig = None):
        """
        初始化稀疏求解器
        
        Args:
            config (SparseMatrixConfig): 配置参数
        """
        self.config = config or SparseMatrixConfig()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        self.factorized_solver = None
        self.last_matrix_structure = None
        
    def solve(self, jacobian: sp.spmatrix, residuals: np.ndarray) -> np.ndarray:
        """
        求解稀疏线性系统
        
        Args:
            jacobian (sp.spmatrix): 稀疏雅可比矩阵
            residuals (np.ndarray): 残差向量
            
        Returns:
            np.ndarray: 解向量
        """
        try:
            # 检查矩阵格式
            if not sp.isspmatrix_csc(jacobian):
                jacobian = jacobian.tocsc()
            
            # 检查条件数
            if hasattr(jacobian, 'nnz') and jacobian.nnz > 0:
                cond_estimate = self._estimate_condition_number(jacobian)
                if cond_estimate > 1e12:
                    self.logger.warning(f"矩阵条件数估计过大: {cond_estimate:.2e}")
            
            # 使用预分解求解器
            if (self.config.factorization_method == "lu" and 
                self.config.reuse_pattern and
                self._can_reuse_factorization(jacobian)):
                
                if self.factorized_solver is None:
                    self.factorized_solver = factorized(jacobian)
                    self.last_matrix_structure = jacobian.copy()
                    self.last_matrix_structure.data.fill(1.0)
                
                solution = self.factorized_solver(-residuals)
            else:
                # 直接求解
                solution = spsolve(jacobian, -residuals)
                
                # 更新预分解求解器
                if self.config.reuse_pattern and self.config.factorization_method == "lu":
                    self.factorized_solver = factorized(jacobian)
                    self.last_matrix_structure = jacobian.copy()
                    self.last_matrix_structure.data.fill(1.0)
            
            return solution
            
        except Exception as e:
            self.logger.error(f"稀疏线性系统求解失败: {e}")
            # 回退到稠密求解
            return self._fallback_dense_solve(jacobian, residuals)
    
    def _can_reuse_factorization(self, jacobian: sp.spmatrix) -> bool:
        """检查是否可以重用矩阵分解"""
        if self.last_matrix_structure is None:
            return False
        
        # 检查稀疏结构是否相同
        current_structure = jacobian.copy()
        current_structure.data.fill(1.0)
        
        return (current_structure - self.last_matrix_structure).nnz == 0
    
    def _estimate_condition_number(self, matrix: sp.spmatrix) -> float:
        """估计矩阵条件数"""
        try:
            # 简化的条件数估计
            if matrix.shape[0] != matrix.shape[1]:
                return float('inf')
            
            # 使用对角元素的比值作为粗略估计
            diag = matrix.diagonal()
            if np.any(np.abs(diag) < 1e-15):
                return float('inf')
            
            return np.max(np.abs(diag)) / np.min(np.abs(diag))
            
        except Exception:
            return 1.0  # 默认值
    
    def _fallback_dense_solve(self, jacobian: sp.spmatrix, residuals: np.ndarray) -> np.ndarray:
        """回退到稠密矩阵求解"""
        self.logger.warning("回退到稠密矩阵求解")
        
        try:
            dense_jacobian = jacobian.toarray()
            solution = np.linalg.solve(dense_jacobian, -residuals)
            return solution
        except Exception as e:
            self.logger.error(f"稠密矩阵求解也失败: {e}")
            # 最后的回退：伪逆
            dense_jacobian = jacobian.toarray()
            solution = np.linalg.pinv(dense_jacobian) @ (-residuals)
            return solution
    
    def clear_factorization(self):
        """清除预分解缓存"""
        self.factorized_solver = None
        self.last_matrix_structure = None
        self.logger.debug("清除矩阵预分解缓存")


# 便捷函数
def analyze_system_sparsity(models: List, variable_names: List[str],
                          boundary_manager = None) -> Dict[str, Any]:
    """
    分析系统稀疏性
    
    Args:
        models (List): 模型列表
        variable_names (List[str]): 变量名列表
        boundary_manager: 边界条件管理器
        
    Returns:
        Dict[str, Any]: 稀疏性分析结果
    """
    pattern_analyzer = SparsePattern()
    pattern, info = pattern_analyzer.analyze_pattern(models, variable_names, boundary_manager)
    
    return {
        'sparsity_ratio': info['sparsity'],
        'nonzero_count': info['n_nonzeros'],
        'matrix_size': (info['n_equations'], info['n_variables']),
        'is_sparse': info['sparsity'] > 0.3,
        'recommended_format': 'sparse' if info['sparsity'] > 0.3 else 'dense',
        'pattern': pattern,
        'analysis_info': info
    }


def create_sparse_jacobian_builder(config: SparseMatrixConfig = None) -> SparseJacobianBuilder:
    """创建稀疏雅可比构建器的便捷函数"""
    return SparseJacobianBuilder(config)


def create_sparse_solver(config: SparseMatrixConfig = None) -> SparseSolver:
    """创建稀疏求解器的便捷函数"""
    return SparseSolver(config)