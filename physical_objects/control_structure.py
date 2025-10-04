"""
水力控制结构模型

本模块定义了水力控制结构的抽象基类和具体实现，包括闸门、水泵、阀门、水轮机等不同类型的
水力控制设备。通过统一的接口设计，实现对不同水力设备的规范化建模。

Classes:
    ControlStructure: 抽象基类，定义水力控制结构的统一接口
    GateModel: 闸门模型，基于孔口出流理论
    PumpModel: 水泵模型，基于特性曲线的工作点求解
    ValveModel: 阀门模型，基于流量特性的简化模型
    TurbineModel: 水轮机模型，支持流量控制和功率计算
"""

from abc import ABC, abstractmethod
from typing import List
import math
try:
    from scipy.optimize import newton, brentq
except ImportError:
    # 如果scipy不可用，提供简化的回退实现
    newton = None
    brentq = None


class ControlStructure(ABC):
    """
    水力控制结构抽象基类
    
    定义了所有水力控制设备的统一接口，所有具体的控制结构都必须继承此基类
    并实现get_flow抽象方法。
    
    Attributes:
        _name (str): 设备名称
    """
    
    def __init__(self, name: str):
        """
        初始化控制结构
        
        Args:
            name (str): 设备名称
        """
        if not isinstance(name, str) or not name.strip():
            raise ValueError("设备名称必须是非空字符串")
        self._name = name.strip()
    
    @property
    def name(self) -> str:
        """
        获取设备名称
        
        Returns:
            str: 设备名称
        """
        return self._name
    
    @abstractmethod
    def get_flow(self, H_up: float, H_down: float, setting: float) -> float:
        """
        计算通过控制结构的流量
        
        Args:
            H_up (float): 上游水头 (m)
            H_down (float): 下游水头 (m)
            setting (float): 控制设置（单位和含义依具体设备而定）
        
        Returns:
            float: 流量 (m³/s)
        """
        pass


class GateModel(ControlStructure):
    """
    闸门模型
    
    基于淹没孔口出流理论实现的闸门水力计算模型。
    流量计算公式：Q = C_d × A × √(2g × ΔH)
    其中：A = width × opening，opening由setting参数控制
    
    Attributes:
        discharge_coeff (float): 流量系数 C_d（无量纲）
        width (float): 闸门宽度 (m)
    """
    
    def __init__(self, name: str, discharge_coeff: float, width: float):
        """
        初始化闸门模型
        
        Args:
            name (str): 闸门名称
            discharge_coeff (float): 流量系数 C_d，通常在0.6-0.8范围内
            width (float): 闸门宽度 (m)，必须大于0
        
        Raises:
            ValueError: 当参数值不合理时抛出异常
        """
        super().__init__(name)
        
        if discharge_coeff <= 0 or discharge_coeff > 1.0:
            raise ValueError("流量系数必须在(0, 1.0]范围内")
        if width <= 0:
            raise ValueError("闸门宽度必须大于0")
            
        self.discharge_coeff = discharge_coeff
        self.width = width
    
    def get_flow(self, H_up: float, H_down: float, setting: float) -> float:
        """
        计算闸门流量
        
        Args:
            H_up (float): 上游水头 (m)
            H_down (float): 下游水头 (m)
            setting (float): 闸门开度 (m)，必须非负
        
        Returns:
            float: 流量 (m³/s)
        """
        # 参数验证
        if setting < 0:
            return 0.0
        
        # 计算水头差
        head_diff = H_up - H_down
        if head_diff <= 0:
            return 0.0
        
        # 计算过水面积
        area = self.width * setting
        
        # 计算流量：Q = C_d × A × √(2g × ΔH)
        g = 9.81  # 重力加速度 (m/s²)
        flow = self.discharge_coeff * area * math.sqrt(2 * g * head_diff)
        
        return flow


class PumpModel(ControlStructure):
    """
    水泵模型
    
    基于水泵特性曲线的工作点求解模型。
    水泵特性曲线表示为多项式：H = c₀ + c₁Q + c₂Q² + ...
    通过求解水泵曲线与管路特性的交点确定工作流量。
    
    Attributes:
        pump_curve_coeffs (List[float]): 特性曲线系数 [c₀, c₁, c₂, ...]
    """
    
    def __init__(self, name: str, pump_curve_coeffs: List[float]):
        """
        初始化水泵模型
        
        Args:
            name (str): 水泵名称
            pump_curve_coeffs (List[float]): 特性曲线多项式系数
                                           [c₀, c₁, c₂, ...]，其中H = c₀ + c₁Q + c₂Q² + ...
        
        Raises:
            ValueError: 当参数不合理时抛出异常
        """
        super().__init__(name)
        
        if not pump_curve_coeffs or len(pump_curve_coeffs) == 0:
            raise ValueError("水泵特性曲线系数不能为空")
        if not all(isinstance(c, (int, float)) for c in pump_curve_coeffs):
            raise ValueError("特性曲线系数必须是数值类型")
            
        self.pump_curve_coeffs = list(pump_curve_coeffs)
    
    def _pump_head(self, flow: float) -> float:
        """
        根据流量计算水泵扬程
        
        Args:
            flow (float): 流量 (m³/s)
        
        Returns:
            float: 扬程 (m)
        """
        head = 0.0
        for i, coeff in enumerate(self.pump_curve_coeffs):
            head += coeff * (flow ** i)
        return head
    
    def _solve_pump_equation(self, H_sys: float) -> float:
        """
        求解水泵工作点方程：pump_head(Q) - H_sys = 0
        
        Args:
            H_sys (float): 系统所需扬程 (m)
        
        Returns:
            float: 工作流量 (m³/s)，求解失败时返回0
        """
        if newton is None or brentq is None:
            # 简化求解：假设线性特性曲线
            if len(self.pump_curve_coeffs) >= 2:
                c0, c1 = self.pump_curve_coeffs[0], self.pump_curve_coeffs[1]
                if abs(c1) > 1e-10:  # 避免除零
                    flow = (H_sys - c0) / c1
                    return max(0.0, flow)
            return 0.0
        
        def equation(Q):
            return self._pump_head(Q) - H_sys
        
        try:
            # 首先检查零流量点的扬程
            H_zero = self._pump_head(0.0)
            if H_sys >= H_zero:
                return 0.0
            
            # 使用牛顿法求解
            Q_solution = newton(equation, x0=1.0, maxiter=50)
            return max(0.0, Q_solution)
        
        except:
            try:
                # 牛顿法失败时使用区间求解法
                Q_solution = brentq(equation, 0.0, 100.0, maxiter=50)
                return max(0.0, Q_solution)
            except:
                return 0.0
    
    def get_flow(self, H_up: float, H_down: float, setting: float) -> float:
        """
        计算水泵流量
        
        Args:
            H_up (float): 吸水池水位 (m)
            H_down (float): 出水池水位 (m)
            setting (float): 水泵运行状态（0=停机，1=运行）
        
        Returns:
            float: 流量 (m³/s)
        """
        # 水泵停机
        if setting == 0:
            return 0.0
        
        # 计算系统所需扬程
        H_sys = H_down - H_up
        
        # 求解工作点
        return self._solve_pump_equation(H_sys)


class ValveModel(ControlStructure):
    """
    阀门模型
    
    基于阀门流量特性的简化模型。
    流量计算公式：Q = C_v × √(ΔH)
    其中：C_v = K_v × √(setting)，K_v为阀门全开流量系数
    
    Attributes:
        valve_coeff (float): 阀门全开流量系数 K_v (m²·⁵/s)
    """
    
    def __init__(self, name: str, valve_coeff: float):
        """
        初始化阀门模型
        
        Args:
            name (str): 阀门名称
            valve_coeff (float): 阀门全开流量系数 K_v (m²·⁵/s)，必须大于0
        
        Raises:
            ValueError: 当参数不合理时抛出异常
        """
        super().__init__(name)
        
        if valve_coeff <= 0:
            raise ValueError("阀门流量系数必须大于0")
            
        self.valve_coeff = valve_coeff
    
    def get_flow(self, H_up: float, H_down: float, setting: float) -> float:
        """
        计算阀门流量
        
        Args:
            H_up (float): 上游水头 (m)
            H_down (float): 下游水头 (m)
            setting (float): 阀门开度（0-1），0为关闭，1为全开
        
        Returns:
            float: 流量 (m³/s)
        """
        # 参数验证
        if setting <= 0:
            return 0.0
        
        # 限制开度范围
        opening = max(0.0, min(1.0, setting))
        
        # 计算水头差
        head_diff = H_up - H_down
        if head_diff <= 0:
            return 0.0
        
        # 计算流量：Q = K_v × √(opening) × √(ΔH)
        flow = self.valve_coeff * math.sqrt(opening) * math.sqrt(head_diff)
        
        return flow


class TurbineModel(ControlStructure):
    """
    水轮机模型
    
    简化的水轮机流量控制模型，支持功率计算。
    在流量控制模式下，setting直接表示目标流量。
    
    Attributes:
        无特殊属性
    """
    
    def __init__(self, name: str):
        """
        初始化水轮机模型
        
        Args:
            name (str): 水轮机名称
        """
        super().__init__(name)
    
    def get_flow(self, H_up: float, H_down: float, setting: float) -> float:
        """
        计算水轮机流量
        
        在流量控制模式下，直接返回设定的目标流量。
        
        Args:
            H_up (float): 上游水头 (m)
            H_down (float): 下游水头 (m)
            setting (float): 目标流量 (m³/s)
        
        Returns:
            float: 流量 (m³/s)
        """
        # 流量不能为负
        return max(0.0, setting)
    
    def get_power(self, H_up: float, H_down: float, Q: float, efficiency: float) -> float:
        """
        计算水轮机发电功率
        
        功率计算公式：P = ρ × g × Q × H × η
        其中：ρ = 1000 kg/m³（水密度），g = 9.81 m/s²（重力加速度）
        
        Args:
            H_up (float): 上游水头 (m)
            H_down (float): 下游水头 (m)
            Q (float): 流量 (m³/s)
            efficiency (float): 水轮机效率（0-1）
        
        Returns:
            float: 发电功率 (kW)
        """
        # 参数验证
        if Q <= 0 or efficiency <= 0:
            return 0.0
        
        # 计算有效水头
        head = H_up - H_down
        if head <= 0:
            return 0.0
        
        # 限制效率范围
        eff = max(0.0, min(1.0, efficiency))
        
        # 计算功率：P = ρ × g × Q × H × η (W)，转换为kW
        rho = 1000.0  # 水密度 (kg/m³)
        g = 9.81      # 重力加速度 (m/s²)
        power_kw = (rho * g * Q * head * eff) / 1000.0
        
        return power_kw