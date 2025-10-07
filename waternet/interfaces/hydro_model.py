"""
HydroModel抽象基类

定义了WaterNet系统中所有水力模型的统一接口规范。
所有具体的水力模型（包括物理模型和降阶模型的紧耦合版本）都必须继承此抽象基类。

设计原则:
1. 统一的接口规范：所有模型都使用相同的方法签名
2. 灵活的变量管理：支持任意复杂度的模型变量组织
3. 标准化的方程描述：通过残差字典描述模型方程
4. 拓扑连接支持：明确定义模型的输入输出节点

接口契约:
- variables: 包含所有变量当前值的字典 {变量名: 数值}
- prev_states: 包含上一时步状态的字典 {状态名: 数值}  
- 返回值: 方程残差字典 {方程名: 残差值}

Author: WaterNet Development Team
Date: 2024-10-03
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Union


class HydroModel(ABC):
    """
    水力模型抽象基类
    
    所有紧耦合水力模型的基础接口，定义了统一的模型交互规范。
    适用于需要与其他模型联合求解的复杂水力系统。
    
    Attributes:
        name (str): 模型唯一标识符
        _node_names (List[str]): 模型连接的边界节点名称列表
    
    Note:
        此接口主要用于联合求解场景，如果只需要独立仿真，
        可考虑使用更简单的降阶模型接口。
    """
    
    def __init__(self, name: str, node_names: List[str]):
        """
        初始化水力模型
        
        Args:
            name (str): 模型唯一标识符，在系统中必须唯一
            node_names (List[str]): 模型连接的边界节点名称列表
                                  通常包含上游节点和下游节点
        
        Raises:
            ValueError: 当name为空或node_names为空时
        """
        if not name or not isinstance(name, str):
            raise ValueError("模型名称name必须是非空字符串")
            
        if not node_names or not isinstance(node_names, list):
            raise ValueError("节点名称列表node_names必须是非空列表")
            
        for node_name in node_names:
            if not isinstance(node_name, str) or not node_name:
                raise ValueError(f"节点名称必须是非空字符串，得到: {node_name}")
        
        self.name = name
        self._node_names = node_names.copy()  # 防止外部修改
        
        # 初始化logger
        import logging
        self.logger = logging.getLogger(f"HydroModel.{name}")
    
    @property
    def node_names(self) -> List[str]:
        """
        获取模型连接的节点名称列表
        
        Returns:
            List[str]: 节点名称列表的副本（只读）
        """
        return self._node_names.copy()
    
    @abstractmethod
    def get_equations(self, variables: Dict[str, float], dt: float, 
                     prev_states: Dict[str, float]) -> Dict[str, float]:
        """
        获取模型方程的残差
        
        这是核心接口方法，用于计算模型在当前变量值下的方程残差。
        残差为0表示方程得到满足。求解器会调整variables中的值，
        使得所有方程的残差都趋向于0。
        
        Args:
            variables (Dict[str, float]): 当前时步的所有变量值
                格式: {'H_Node1': 100.5, 'Q_Pipe1': 1.0, ...}
                包含：
                - 节点水位: 'H_节点名'
                - 管段流量: 'Q_管段名'  
                - 内部变量: 模型自定义的内部变量
                
            dt (float): 时间步长（秒）
                
            prev_states (Dict[str, float]): 上一时步的状态值
                格式: {'V_Reservoir1': 50000, 'H_Node1': 99.8, ...}
                包含：
                - 蓄水量: 'V_存储体名'
                - 历史水位/流量等状态变量
        
        Returns:
            Dict[str, float]: 方程残差字典
                格式: {'方程名': 残差值, ...}
                例如: {
                    'continuity_seg_0': 0.01,    # 连续性方程残差
                    'momentum_seg_0': -0.05,     # 动量方程残差  
                    'balance_Node1': 0.002       # 节点平衡残差
                }
        
        Note:
            - 残差的数量应等于模型引入的未知变量数量
            - 残差的单位应与对应的物理量一致
            - 建议残差的绝对值在合理的数值范围内（避免过大或过小）
        """
        pass
    
    @abstractmethod  
    def get_variable_names(self) -> List[str]:
        """
        获取模型引入的变量名列表
        
        返回此模型在系统中新增的变量名称。这些变量将成为
        联合求解系统的未知数。变量命名应遵循标准约定：
        - 节点水位: 'H_节点名'
        - 管段流量: 'Q_管段名'
        - 内部节点: 'H_模型名_internal_索引'
        - 其他变量: 根据物理含义命名
        
        Returns:
            List[str]: 变量名称列表
                例如: ['Q_TestChannel_seg_0', 'H_TestChannel_internal_0']
        
        Note:
            - 变量数量应与get_equations()返回的方程数量相等
            - 变量名在整个系统中应唯一
            - 建议按照物理意义和计算顺序排列
        """
        pass
    
    def validate_interface(self, variables: Dict[str, float], dt: float,
                          prev_states: Dict[str, float]) -> bool:
        """
        验证接口实现的正确性
        
        检查get_equations()和get_variable_names()的实现是否匹配，
        以及返回值格式是否正确。用于开发阶段的接口验证。
        
        Args:
            variables (Dict[str, float]): 测试用的变量字典
            dt (float): 测试用的时间步长
            prev_states (Dict[str, float]): 测试用的状态字典
            
        Returns:
            bool: True表示接口实现正确，False表示存在问题
            
        Raises:
            ValueError: 当检测到接口实现错误时
        """
        try:
            # 检查变量名列表
            var_names = self.get_variable_names()
            if not isinstance(var_names, list):
                raise ValueError("get_variable_names()必须返回列表")
                
            for var_name in var_names:
                if not isinstance(var_name, str) or not var_name:
                    raise ValueError(f"变量名必须是非空字符串: {var_name}")
            
            # 检查方程残差
            equations = self.get_equations(variables, dt, prev_states)
            if not isinstance(equations, dict):
                raise ValueError("get_equations()必须返回字典")
                
            for eq_name, residual in equations.items():
                if not isinstance(eq_name, str) or not eq_name:
                    raise ValueError(f"方程名必须是非空字符串: {eq_name}")
                if not isinstance(residual, (int, float)):
                    raise ValueError(f"残差必须是数值: {eq_name}={residual}")
            
            # 检查变量和方程数量匹配
            if len(var_names) != len(equations):
                raise ValueError(
                    f"变量数量({len(var_names)})与方程数量({len(equations)})不匹配")
            
            return True
            
        except Exception as e:
            print(f"接口验证失败: {e}")
            return False
    
    def __repr__(self) -> str:
        """模型的字符串表示"""
        return f"{self.__class__.__name__}(name='{self.name}', nodes={self.node_names})"
    
    def __str__(self) -> str:
        """模型的可读字符串表示"""
        return f"水力模型 '{self.name}' (连接节点: {', '.join(self.node_names)})"


class DummyModel(HydroModel):
    """
    测试用的虚拟模型实现
    
    用于演示HydroModel接口的使用方法，以及进行单元测试。
    实现了一个简单的线性关系：Q_out = k * H_in + b
    """
    
    def __init__(self, name: str, upstream_node: str, downstream_node: str,
                 k: float = 1.0, b: float = 0.0):
        """
        初始化虚拟模型
        
        Args:
            name (str): 模型名称
            upstream_node (str): 上游节点名
            downstream_node (str): 下游节点名  
            k (float): 线性系数
            b (float): 常数项
        """
        super().__init__(name, [upstream_node, downstream_node])
        self.upstream_node = upstream_node
        self.downstream_node = downstream_node
        self.k = k
        self.b = b
    
    def get_equations(self, variables: Dict[str, float], dt: float,
                     prev_states: Dict[str, float]) -> Dict[str, float]:
        """
        实现简单的线性关系方程
        
        方程: Q_out = k * H_upstream + b
        """
        H_up = variables.get(f'H_{self.upstream_node}', 0.0)
        Q_out = variables.get(f'Q_{self.name}', 0.0)
        
        # 线性关系方程的残差
        residual = Q_out - (self.k * H_up + self.b)
        
        return {f'linear_relation_{self.name}': residual}
    
    def get_variable_names(self) -> List[str]:
        """返回模型引入的流量变量"""
        return [f'Q_{self.name}']


# 工具函数
def validate_variables_format(variables: Dict[str, float]) -> bool:
    """
    验证variables字典的格式是否正确
    
    Args:
        variables (Dict[str, float]): 待验证的变量字典
        
    Returns:
        bool: True表示格式正确
    """
    if not isinstance(variables, dict):
        return False
        
    for name, value in variables.items():
        if not isinstance(name, str) or not name:
            return False
        if not isinstance(value, (int, float)):
            return False
            
    return True


def validate_states_format(prev_states: Dict[str, float]) -> bool:
    """
    验证prev_states字典的格式是否正确
    
    Args:
        prev_states (Dict[str, float]): 待验证的状态字典
        
    Returns:
        bool: True表示格式正确
    """
    return validate_variables_format(prev_states)  # 格式要求相同