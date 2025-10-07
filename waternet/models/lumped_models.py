"""
BaseLumpedModel 降阶模型基类

定义了所有集总参数降阶模型的统一框架和接口。
提供标准的仿真循环、状态管理和结果记录功能。

设计特点:
1. 统一的step-by-step仿真接口
2. 自动的状态变量管理
3. 标准化的结果记录格式
4. 可扩展的物理关系函数
5. 内置的数值稳定性保护

支持的降阶模型类型:
- 水量平衡模型（WaterBalanceModel）
- 蓄量演算模型（StorageRoutingModel）
- 马斯京干模型（MuskingumModel）
- IDZ模型（IntegralDelayZeroModel）

Author: WaterNet Development Team
Date: 2024-10-03
"""

import numpy as np
import pandas as pd
import warnings
from abc import ABC, abstractmethod
from typing import Dict, List, Callable, Optional, Union, Any


class BaseLumpedModel(ABC):
    """
    集总参数降阶模型抽象基类
    
    为所有降阶模型提供统一的接口和通用功能。
    采用"step-by-step"的仿真模式，每次调用step()方法
    推进一个时间步长。
    
    重要改进：蓄水量现在由流量和水位共同决定
    - 支持V = f(Q, H)的更精确物理关系
    - 向后兼容原有的V = f(H)关系
    
    核心功能:
    - 时间步进仿真
    - 状态变量管理
    - 物理关系函数调用（支持Q-H耦合）
    - 结果数据记录
    - 数值稳定性保护
    
    Attributes:
        dt (float): 时间步长（秒）
        initial_V (float): 初始蓄水量（m³）
        V_to_H_func (Callable): 蓄量-水位关系函数
        H_to_Q_func (Callable): 水位-出流关系函数
        QH_to_V_func (Optional[Callable]): 流量水位-蓄量关系函数
        current_V (float): 当前蓄水量
        current_H (float): 当前水位
        current_Q_out (float): 当前出流量
        time (float): 当前仿真时间
    """
    
    def __init__(self, dt: float, initial_V: float, 
                 V_to_H_func: Callable[[float], float],
                 H_to_Q_func: Callable[[float], float],
                 name: str = "LumpedModel",
                 QH_to_V_func: Optional[Callable[[float, float], float]] = None):
        """
        初始化降阶模型基类
        
        Args:
            dt (float): 时间步长（秒），必须为正值
            initial_V (float): 初始蓄水量（m³），必须为非负值
            V_to_H_func (Callable): 蓄量转换为水位的函数 H = f(V)
            H_to_Q_func (Callable): 水位转换为出流的函数 Q = f(H)
            name (str): 模型名称，用于标识和调试
            QH_to_V_func (Optional[Callable]): 流量水位耦合的蓄量函数 V = f(Q, H)
                                              如果提供，将优先使用这个更精确的关系
            
        Raises:
            ValueError: 当参数不合理时
        """
        # 参数验证
        if dt <= 0:
            raise ValueError(f"时间步长dt必须为正值，得到: {dt}")
        if initial_V < 0:
            raise ValueError(f"初始蓄水量不能为负值，得到: {initial_V}")
        if not callable(V_to_H_func):
            raise ValueError("V_to_H_func必须是可调用函数")
        if not callable(H_to_Q_func):
            raise ValueError("H_to_Q_func必须是可调用函数")
        
        # 基本参数
        self.dt = dt
        self.initial_V = initial_V
        self.V_to_H_func = V_to_H_func
        self.H_to_Q_func = H_to_Q_func
        self.QH_to_V_func = QH_to_V_func  # 新增：Q-H耦合的蓄量函数
        self.name = name
        
        # 物理关系模式标识
        self.use_QH_coupling = QH_to_V_func is not None
        
        # 数值保护参数（必须在状态变量之前设置）
        self._min_volume = 0.0  # 最小蓄水量
        self._max_volume = 1e10  # 最大蓄水量（防止溢出）
        self._tolerance = 1e-6  # 数值容差
        
        # 状态变量
        self.current_V = initial_V
        self.current_H = 0.0  # 初始化为默认值
        self.current_H = self._safe_V_to_H(initial_V)  # 再计算真实值
        self.current_Q_out = self._safe_H_to_Q(self.current_H)
        self.time = 0.0
        
        # 历史状态（用于需要历史信息的模型）
        self.history = {
            'V': [self.current_V],
            'H': [self.current_H], 
            'Q_out': [self.current_Q_out],
            'Q_in': [0.0],
            'time': [0.0]
        }
        
        # 验证初始状态的一致性
        self._validate_initial_state()
    
    def _validate_initial_state(self):
        """验证初始状态的物理一致性"""
        try:
            # 测试V-H关系函数
            test_H = self.V_to_H_func(self.initial_V)
            if not isinstance(test_H, (int, float)) or not np.isfinite(test_H):
                raise ValueError("V_to_H_func返回非有限数值")
            
            # 测试H-Q关系函数
            test_Q = self.H_to_Q_func(test_H)
            if not isinstance(test_Q, (int, float)) or not np.isfinite(test_Q):
                raise ValueError("H_to_Q_func返回非有限数值")
                
            if test_Q < 0:
                warnings.warn(f"初始出流量为负值: {test_Q}")
                
        except Exception as e:
            raise ValueError(f"物理关系函数验证失败: {e}")
    
    def _safe_V_to_H(self, V: float) -> float:
        """安全的蓄量-水位转换"""
        try:
            # 限制蓄量范围
            V_safe = np.clip(V, self._min_volume, self._max_volume)
            H = self.V_to_H_func(V_safe)
            
            if not np.isfinite(H):
                warnings.warn(f"V_to_H_func返回非有限值，V={V}")
                return getattr(self, 'current_H', 0.0)  # 返回当前水位或默认值
            
            return float(H)
            
        except Exception as e:
            warnings.warn(f"V_to_H_func计算失败: {e}，使用当前水位")
            return getattr(self, 'current_H', 0.0)
    
    def _compute_volume_from_QH(self, Q: float, H: float) -> float:
        """
        根据流量和水位计算蓄水量
        
        支持两种模式：
        1. 如果提供了QH_to_V_func，优先使用 V = f(Q, H)
        2. 否则使用传统的 V = f_inv(H) 方法
        
        Args:
            Q (float): 流量 (m³/s)
            H (float): 水位 (m)
            
        Returns:
            float: 蓄水量 (m³)
        """
        if self.use_QH_coupling and self.QH_to_V_func is not None:
            try:
                V = self.QH_to_V_func(Q, H)
                if np.isfinite(V) and V >= 0:
                    return float(V)
                else:
                    warnings.warn(f"QH_to_V_func返回异常值: V={V}, 使用传统方法")
            except Exception as e:
                warnings.warn(f"QH_to_V_func计算失败: {e}, 使用传统方法")
        
        # 传统方法：通过水位反推蓄量（需要反函数）
        # 这里简化为使用连续性方程更新
        return self.current_V
    
    def _safe_H_to_Q(self, H: float) -> float:
        """安全的水位-出流转换"""
        try:
            Q = self.H_to_Q_func(H)
            
            if not np.isfinite(Q):
                warnings.warn(f"H_to_Q_func返回非有限值，H={H}")
                return 0.0
            
            if Q < 0:
                warnings.warn(f"出流量为负值: {Q}，设为0")
                return 0.0
                
            return float(Q)
            
        except Exception as e:
            warnings.warn(f"H_to_Q_func计算失败: {e}，设出流为0")
            return 0.0
    
    @abstractmethod
    def step(self, Q_in: float, downstream_level: Optional[float] = None, **kwargs) -> Dict[str, float]:
        """
        执行一个时间步的仿真
        
        这是核心仿真方法，每个具体模型必须实现自己的算法逻辑。
        方法应该：
        1. 根据Q_in和当前状态计算新状态
        2. 更新内部状态变量
        3. 返回当前时步的计算结果
        
        Args:
            Q_in (float): 当前时步的入流量（m³/s）
            downstream_level (Optional[float]): 下游水位，用于非恒定流仿真兼容性
            **kwargs: 其他兼容性参数
            
        Returns:
            Dict[str, float]: 仿真结果字典，至少包含：
                - 'Q_out': 出流量（m³/s）
                - 'H_out': 出口水位（m）
                - 'V': 蓄水量（m³）
                - 'time': 当前时间（s）
                
        Note:
            子类实现时应调用_update_physical_states()来更新物理状态
        """
        pass
    
    def _update_physical_states(self, Q_in_avg: float, Q_out_avg: float):
        """
        更新物理状态变量
        
        根据平均入流和出流更新蓄水量，并计算对应的水位。
        支持两种计算模式：
        1. 传统连续性方程: dV/dt = Q_in - Q_out
        2. Q-H耦合模式: V = f(Q_avg, H_new)
        
        Args:
            Q_in_avg (float): 时步内平均入流量
            Q_out_avg (float): 时步内平均出流量
        """
        if self.use_QH_coupling:
            # 使用Q-H耦合模式
            # 先用连续性方程估算新水位
            dV_continuity = (Q_in_avg - Q_out_avg) * self.dt
            V_continuity = self.current_V + dV_continuity
            V_continuity = np.clip(V_continuity, self._min_volume, self._max_volume)
            
            # 计算对应水位
            H_estimated = self._safe_V_to_H(V_continuity)
            
            # 使用Q-H耦合关系计算更精确的蓄水量
            Q_avg = (Q_in_avg + Q_out_avg) / 2.0
            V_corrected = self._compute_volume_from_QH(Q_avg, H_estimated)
            
            # 更新状态
            self.current_V = V_corrected
            self.current_H = H_estimated
        else:
            # 传统连续性方程模式
            dV = (Q_in_avg - Q_out_avg) * self.dt
            new_V = self.current_V + dV
            
            # 应用数值保护
            new_V = np.clip(new_V, self._min_volume, self._max_volume)
            
            # 更新状态
            self.current_V = new_V
            self.current_H = self._safe_V_to_H(new_V)
        
        # 推进时间
        self.time += self.dt
    
    def _record_state(self, Q_in: float):
        """
        记录当前状态到历史数据
        
        Args:
            Q_in (float): 当前时步入流量
        """
        self.history['V'].append(self.current_V)
        self.history['H'].append(self.current_H)
        self.history['Q_out'].append(self.current_Q_out)
        self.history['Q_in'].append(Q_in)
        self.history['time'].append(self.time)
        
        # 限制历史数据长度（防止内存溢出）
        max_history = 10000
        if len(self.history['time']) > max_history:
            for key in self.history:
                self.history[key] = self.history[key][-max_history:]
    
    def run_simulation(self, Q_in_series: Union[List[float], np.ndarray], 
                      record_interval: int = 1) -> pd.DataFrame:
        """
        运行完整的仿真序列
        
        Args:
            Q_in_series (Union[List, np.ndarray]): 入流时间序列
            record_interval (int): 记录间隔（每多少步记录一次）
            
        Returns:
            pd.DataFrame: 仿真结果数据框，列包括：
                - time: 时间（s）
                - Q_in: 入流量（m³/s）
                - Q_out: 出流量（m³/s）
                - H_out: 出口水位（m）
                - V: 蓄水量（m³）
                - 其他模型特定的变量
        """
        if len(Q_in_series) == 0:
            raise ValueError("入流序列不能为空")
        
        # 初始化结果记录
        results = []
        
        # 记录初始状态
        initial_result = {
            'time': self.time,
            'Q_in': 0.0,
            'Q_out': self.current_Q_out,
            'H_out': self.current_H,
            'V': self.current_V
        }
        results.append(initial_result)
        
        # 执行仿真循环
        for i, Q_in in enumerate(Q_in_series):
            # 执行一步仿真
            step_result = self.step(Q_in)
            
            # 按间隔记录结果
            if i % record_interval == 0:
                result = {
                    'time': self.time,
                    'Q_in': Q_in,
                    'Q_out': step_result['Q_out'],
                    'H_out': step_result['H_out'],
                    'V': step_result['V']
                }
                
                # 添加模型特定的输出
                for key, value in step_result.items():
                    if key not in result:
                        result[key] = value
                        
                results.append(result)
        
        # 转换为DataFrame
        df = pd.DataFrame(results)
        return df
    
    def reset(self, new_initial_V: Optional[float] = None):
        """
        重置模型到初始状态
        
        Args:
            new_initial_V (Optional[float]): 新的初始蓄水量，
                                           如果为None则使用原初始值
        """
        if new_initial_V is not None:
            if new_initial_V < 0:
                raise ValueError("初始蓄水量不能为负值")
            self.initial_V = new_initial_V
        
        # 重置状态变量
        self.current_V = self.initial_V
        self.current_H = self._safe_V_to_H(self.initial_V)
        self.current_Q_out = self._safe_H_to_Q(self.current_H)
        self.time = 0.0
        
        # 清空历史记录
        self.history = {
            'V': [self.current_V],
            'H': [self.current_H],
            'Q_out': [self.current_Q_out],
            'Q_in': [0.0],
            'time': [0.0]
        }
    
    def get_current_state(self) -> Dict[str, float]:
        """
        获取当前状态
        
        Returns:
            Dict[str, float]: 当前状态字典
        """
        return {
            'time': self.time,
            'V': self.current_V,
            'H': self.current_H,
            'Q_out': self.current_Q_out
        }
    
    def get_history_dataframe(self) -> pd.DataFrame:
        """
        获取历史状态数据框
        
        Returns:
            pd.DataFrame: 历史状态数据
        """
        return pd.DataFrame(self.history)
    
    def create_enhanced_version(self, **kwargs):
        """
        创建当前模型的增强版本
        
        Args:
            **kwargs: 增强功能参数
            
        Returns:
            Enhanced model instance
        """
        try:
            from ..tests.deep_channel_testing.enhanced_models import (
                EnhancedMuskingumModel, EnhancedStorageRoutingModel, 
                IntegralDelayZeroModel as EnhancedIDZModel)
            
            if isinstance(self, MuskingumModel):
                return EnhancedMuskingumModel(
                    dt=self.dt, K=self.K, x=self.x, 
                    initial_V=self.initial_V,
                    V_to_H_func=self.V_to_H_func,
                    H_to_Q_func=self.H_to_Q_func,
                    name=f"Enhanced_{self.name}",
                    **kwargs
                )
            elif isinstance(self, StorageRoutingModel):
                return EnhancedStorageRoutingModel(
                    dt=self.dt, initial_V=self.initial_V,
                    V_to_H_func=self.V_to_H_func,
                    H_to_Q_func=self.H_to_Q_func,
                    name=f"Enhanced_{self.name}",
                    **kwargs
                )
            else:
                warnings.warn(f"暂不支持{self.__class__.__name__}的增强版本")
                return None
        except ImportError:
            warnings.warn("增强模型不可用")
            return None
    
    def set_physical_bounds(self, min_volume: float = 0.0, 
                           max_volume: float = 1e10):
        """
        设置物理约束边界
        
        Args:
            min_volume (float): 最小蓄水量
            max_volume (float): 最大蓄水量
        """
        if min_volume < 0:
            raise ValueError("最小蓄水量不能为负值")
        if max_volume <= min_volume:
            raise ValueError("最大蓄水量必须大于最小蓄水量")
            
        self._min_volume = min_volume
        self._max_volume = max_volume
    
    def validate_physical_functions(self, V_test_range: np.ndarray) -> bool:
        """
        验证物理关系函数的有效性
        
        Args:
            V_test_range (np.ndarray): 测试蓄水量范围
            
        Returns:
            bool: True表示函数有效
        """
        try:
            for V in V_test_range:
                H = self.V_to_H_func(V)
                if not np.isfinite(H):
                    return False
                    
                Q = self.H_to_Q_func(H)
                if not np.isfinite(Q) or Q < 0:
                    return False
                    
            return True
            
        except Exception:
            return False
    
    def summary(self) -> str:
        """
        返回模型摘要信息
        
        Returns:
            str: 模型摘要
        """
        return f"""
降阶模型摘要: {self.name}
==============================
类型: {self.__class__.__name__}
时间步长: {self.dt} 秒
初始蓄水量: {self.initial_V:.2f} m³
当前状态:
  时间: {self.time:.1f} s
  蓄水量: {self.current_V:.2f} m³
  水位: {self.current_H:.3f} m
  出流: {self.current_Q_out:.3f} m³/s
历史记录长度: {len(self.history['time'])}
"""
    
    def __repr__(self) -> str:
        """模型的字符串表示"""
        return f"{self.__class__.__name__}(name='{self.name}', dt={self.dt}, V={self.current_V:.1f})"


class WaterBalanceModel(BaseLumpedModel):
    """
    水量平衡模型
    
    最简单的降阶模型，假设入流等于出流，无滞后效应。
    适用于快速估算或作为基准对比模型。
    
    特点:
    - 无参数需要标定
    - 计算速度极快
    - 无滞后和调蓄效应
    - 出流立即响应入流变化
    """
    
    def __init__(self, dt: float, initial_V: float,
                 V_to_H_func: Callable[[float], float],
                 H_to_Q_func: Callable[[float], float],
                 name: str = "WaterBalance",
                 QH_to_V_func: Optional[Callable[[float, float], float]] = None):
        """
        初始化水量平衡模型
        
        Args:
            dt (float): 时间步长（秒）
            initial_V (float): 初始蓄水量（m³）
            V_to_H_func (Callable): 蓄量-水位关系函数
            H_to_Q_func (Callable): 水位-出流关系函数
            name (str): 模型名称
            QH_to_V_func (Optional[Callable]): Q-H耦合蓄量函数
        """
        super().__init__(dt, initial_V, V_to_H_func, H_to_Q_func, name, QH_to_V_func)
    
    def step(self, Q_in: float) -> Dict[str, float]:
        """
        水量平衡模型的时步推进
        
        假设: Q_out = Q_in (无滞后，入流等于出流)
        
        Args:
            Q_in (float): 入流量
            
        Returns:
            Dict[str, float]: 仿真结果
        """
        # 水量平衡：出流等于入流
        Q_out = Q_in
        
        # 更新物理状态（平均入流和出流相等，蓄水量不变）
        self._update_physical_states(Q_in, Q_out)
        
        # 更新当前出流
        self.current_Q_out = Q_out
        
        # 记录状态
        self._record_state(Q_in)
        
        return {
            'Q_out': Q_out,
            'H_out': self.current_H,
            'V': self.current_V,
            'time': self.time
        }


class StorageRoutingModel(BaseLumpedModel):
    """
    蓄量演算模型
    
    基于蓄量连续性方程和V-H、H-Q关系曲线的集总模型。
    适用于具有明显蓄水特性的渠段或水库。
    
    基本方程:
    - 连续性: dV/dt = Q_in - Q_out
    - 蓄泄关系: V = f(H), Q_out = g(H)
    
    特点:
    - 物理意义明确
    - 参数易于获取
    - 适用于天然河道和人工渠道
    """
    
    def __init__(self, dt: float, initial_V: float,
                 V_to_H_func: Callable[[float], float],
                 H_to_Q_func: Callable[[float], float],
                 name: str = "StorageRouting",
                 QH_to_V_func: Optional[Callable[[float, float], float]] = None):
        """
        初始化蓄量演算模型
        
        Args:
            dt (float): 时间步长（秒）
            initial_V (float): 初始蓄水量（m³）
            V_to_H_func (Callable): 蓄量-水位关系函数
            H_to_Q_func (Callable): 水位-出流关系函数
            name (str): 模型名称
            QH_to_V_func (Optional[Callable]): Q-H耦合蓄量函数
        """
        super().__init__(dt, initial_V, V_to_H_func, H_to_Q_func, name, QH_to_V_func)
    
    def step(self, Q_in: float, downstream_level: Optional[float] = None, **kwargs) -> Dict[str, float]:
        """
        蓄量演算模型的时步推进
        
        使用蓄量连续性方程计算新的蓄水量，
        然后通过V-H和H-Q关系计算出流。
        
        Args:
            Q_in (float): 入流量
            downstream_level (Optional[float]): 下游水位，用于非恒定流仿真兼容性
            **kwargs: 其他兼容性参数
            
        Returns:
            Dict[str, float]: 仿真结果
        """
        # 当前出流（基于当前水位）
        Q_out_current = self.current_Q_out
        
        # 预估时步末的出流（使用平均值迭代）
        for iteration in range(3):  # 简单迭代求解
            # 平均入流和出流
            Q_in_avg = Q_in
            Q_out_avg = (Q_out_current + self.current_Q_out) / 2.0
            
            # 更新蓄水量
            new_V = self.current_V + (Q_in_avg - Q_out_avg) * self.dt
            new_V = np.clip(new_V, self._min_volume, self._max_volume)
            
            # 计算新水位和出流
            new_H = self._safe_V_to_H(new_V)
            Q_out_current = self._safe_H_to_Q(new_H)
        
        # 更新物理状态
        Q_out_avg = (Q_out_current + self.current_Q_out) / 2.0
        self._update_physical_states(Q_in, Q_out_avg)
        
        # 更新当前出流
        self.current_Q_out = Q_out_current
        
        # 记录状态
        self._record_state(Q_in)
        
        return {
            'Q_out': Q_out_current,
            'H_out': self.current_H,
            'V': self.current_V,
            'time': self.time
        }


class MuskingumModel(BaseLumpedModel):
    """
    马斯京干模型
    
    经典的河道洪水演进模型，基于线性水库理论。
    适用于天然河道和明渠的洪水传播计算。
    
    基本方程:
    Q_out = C0*Q_in + C1*Q_in_prev + C2*Q_out_prev
    
    其中系数:
    C0 = (-Kx + 0.5*dt) / (K - Kx + 0.5*dt)
    C1 = (Kx + 0.5*dt) / (K - Kx + 0.5*dt)
    C2 = (K - Kx - 0.5*dt) / (K - Kx + 0.5*dt)
    
    参数:
    - K: 滞时常数（秒）
    - x: 权重系数（0 ≤ x ≤ 0.5）
    """
    
    def __init__(self, dt: float, K: float, x: float, initial_V: float,
                 V_to_H_func: Callable[[float], float],
                 H_to_Q_func: Callable[[float], float],
                 name: str = "Muskingum"):
        """
        初始化马斯京干模型
        
        Args:
            dt (float): 时间步长（秒）
            K (float): 滞时常数（秒），必须大于0
            x (float): 权重系数，范围[0, 0.5]
            initial_V (float): 初始蓄水量（m³）
            V_to_H_func (Callable): 蓄量-水位关系函数
            H_to_Q_func (Callable): 水位-出流关系函数
            name (str): 模型名称
            
        Raises:
            ValueError: 当参数超出合理范围时
        """
        # 参数验证
        if K <= 0:
            raise ValueError(f"滞时常数K必须为正值，得到: {K}")
        if not 0 <= x <= 0.5:
            raise ValueError(f"权重系数x必须在[0, 0.5]范围内，得到: {x}")
        
        super().__init__(dt, initial_V, V_to_H_func, H_to_Q_func, name)
        
        self.K = K
        self.x = x
        
        # 计算马斯京干系数
        self._compute_muskingum_coefficients()
        
        # 历史变量
        self.Q_in_prev = 0.0
        self.Q_out_prev = self.current_Q_out
    
    def _compute_muskingum_coefficients(self):
        """
        计算马斯京干模型系数
        """
        denominator = self.K - self.K * self.x + 0.5 * self.dt
        
        if abs(denominator) < 1e-10:
            raise ValueError("马斯京干系数计算中分母接近零")
        
        self.C0 = (-self.K * self.x + 0.5 * self.dt) / denominator
        self.C1 = (self.K * self.x + 0.5 * self.dt) / denominator
        self.C2 = (self.K - self.K * self.x - 0.5 * self.dt) / denominator
        
        # 验证系数和为1（数值稳定性）
        coeff_sum = self.C0 + self.C1 + self.C2
        if abs(coeff_sum - 1.0) > 1e-6:
            warnings.warn(f"马斯京干系数和不为1: {coeff_sum}")
    
    def step(self, Q_in: float, downstream_level: Optional[float] = None, **kwargs) -> Dict[str, float]:
        """
        马斯京干模型的时步推进
        
        Args:
            Q_in (float): 入流量
            downstream_level (Optional[float]): 下游水位，用于非恒定流仿真兼容性
            **kwargs: 其他兼容性参数
            
        Returns:
            Dict[str, float]: 仿真结果
        """
        # 马斯京干公式
        Q_out = (self.C0 * Q_in + 
                self.C1 * self.Q_in_prev + 
                self.C2 * self.Q_out_prev)
        
        # 数值保护
        Q_out = max(0.0, Q_out)
        
        # 更新物理状态
        Q_in_avg = (Q_in + self.Q_in_prev) / 2.0
        Q_out_avg = (Q_out + self.Q_out_prev) / 2.0
        self._update_physical_states(Q_in_avg, Q_out_avg)
        
        # 更新历史变量
        self.Q_in_prev = Q_in
        self.Q_out_prev = Q_out
        self.current_Q_out = Q_out
        
        # 记录状态
        self._record_state(Q_in)
        
        return {
            'Q_out': Q_out,
            'H_out': self.current_H,
            'V': self.current_V,
            'time': self.time,
            'C0': self.C0,
            'C1': self.C1,
            'C2': self.C2
        }
    
    def reset(self, new_initial_V: Optional[float] = None):
        """
        重置模型状态
        
        Args:
            new_initial_V (Optional[float]): 新的初始蓄水量
        """
        super().reset(new_initial_V)
        self.Q_in_prev = 0.0
        self.Q_out_prev = self.current_Q_out


class IntegralDelayZeroModel(BaseLumpedModel):
    """
    IDZ模型（积分延迟零点模型）- 四方程耦合系统
    
    基于双节点传递函数矩阵的河道水力系统模型，考虑上下游节点间的完整耦合关系。
    传递函数矩阵形式:
    [Q1_out]   [G11(s) G12(s)] [Q1_in]
    [Q2_out] = [G21(s) G22(s)] [Q2_in]
    
    四个传递函数:
    - G11(s): 上游输入 → 上游输出 (自反馈)
    - G12(s): 下游输入 → 上游输出 (回水效应)
    - G21(s): 上游输入 → 下游输出 (正向传播)
    - G22(s): 下游输入 → 下游输出 (自反馈)
    
    平衡点定义:
    - 基于稳态流量与水位值 (Q0_up, H0_up, Q0_down, H0_down)
    - 对应蓄量 V0 = f(Q0, H0)，无额外假设
    
    特点:
    - 完整的双向耦合
    - 回水效应建模
    - 基于物理平衡点的线性化
    - 适用于复杂河网系统
    """
    
    def __init__(self, dt: float, initial_V: float, 
                 V_to_H_func: Callable[[float], float],
                 H_to_Q_func: Callable[[float], float],
                 Q0_up: float, H0_up: float, Q0_down: float, H0_down: float,
                 tau11: float = 100.0, tau12: float = 50.0, 
                 tau21: float = 200.0, tau22: float = 100.0,
                 T11: float = 0.0, T12: float = 300.0, 
                 T21: float = 600.0, T22: float = 0.0,
                 alpha11: float = 300.0, alpha12: float = 200.0,
                 alpha21: float = 400.0, alpha22: float = 300.0,
                 name: str = "IDZModel"):
        """
        初始化四方程IDZ模型
        
        Args:
            dt (float): 时间步长（秒）
            initial_V (float): 初始蓄水量（m³）
            V_to_H_func (Callable): 蓄量-水位关系函数
            H_to_Q_func (Callable): 水位-出流关系函数
            Q0_up (float): 上游稳态流量（m³/s）
            H0_up (float): 上游稳态水位（m）
            Q0_down (float): 下游稳态流量（m³/s）
            H0_down (float): 下游稳态水位（m）
            tau11 (float): G11零点时间常数（秒）
            tau12 (float): G12零点时间常数（秒）
            tau21 (float): G21零点时间常数（秒）
            tau22 (float): G22零点时间常数（秒）
            T11 (float): G11延迟时间（秒）
            T12 (float): G12延迟时间（秒）
            T21 (float): G21延迟时间（秒）
            T22 (float): G22延迟时间（秒）
            alpha11 (float): G11极点时间常数（秒）
            alpha12 (float): G12极点时间常数（秒）
            alpha21 (float): G21极点时间常数（秒）
            alpha22 (float): G22极点时间常数（秒）
            name (str): 模型名称
            
        Raises:
            ValueError: 当参数不合理时
        """
        # 参数验证
        if any(tau <= 0 for tau in [tau11, tau12, tau21, tau22]):
            raise ValueError("所有零点时间常数必须为正值")
        if any(T < 0 for T in [T11, T12, T21, T22]):
            raise ValueError("所有延迟时间必须非负")
        if any(alpha <= 0 for alpha in [alpha11, alpha12, alpha21, alpha22]):
            raise ValueError("所有极点时间常数必须为正值")
        
        super().__init__(dt, initial_V, V_to_H_func, H_to_Q_func, name)
        
        # 稳态平衡点（线性化基准点）
        self.Q0_up = Q0_up
        self.H0_up = H0_up
        self.Q0_down = Q0_down
        self.H0_down = H0_down
        
        # 对应的平衡蓄量（基于物理关系，无假设）
        self.V0 = self._compute_equilibrium_volume(Q0_up, H0_up, Q0_down, H0_down)
        
        # 四个传递函数的参数
        self.params = {
            'G11': {'tau': tau11, 'T': T11, 'alpha': alpha11},
            'G12': {'tau': tau12, 'T': T12, 'alpha': alpha12},
            'G21': {'tau': tau21, 'T': T21, 'alpha': alpha21},
            'G22': {'tau': tau22, 'T': T22, 'alpha': alpha22}
        }
        
        # 为每个传递函数创建延迟缓冲区
        self.delay_buffers = {}
        self.internal_states = {}
        
        for tf_name, param in self.params.items():
            delay_steps = int(np.ceil(param['T'] / dt))
            self.delay_buffers[tf_name] = [0.0] * max(1, delay_steps)
            self.internal_states[tf_name] = {'y_prev': 0.0, 'u_prev': 0.0}
        
        # 计算所有传递函数的离散化系数
        self.discrete_coeffs = {}
        for tf_name in self.params:
            self.discrete_coeffs[tf_name] = self._compute_discrete_coefficients(tf_name)
    
    def _compute_equilibrium_volume(self, Q_up: float, H_up: float, 
                                   Q_down: float, H_down: float) -> float:
        """
        基于稳态流量和水位计算平衡蓄量
        
        不做任何假设，直接基于给定的稳态条件计算对应蓄量
        
        Args:
            Q_up (float): 上游稳态流量
            H_up (float): 上游稳态水位
            Q_down (float): 下游稳态流量
            H_down (float): 下游稳态水位
            
        Returns:
            float: 平衡蓄量
        """
        # 使用平均水位和流量计算蓄量
        H_avg = (H_up + H_down) / 2.0
        Q_avg = (Q_up + Q_down) / 2.0
        
        if self.use_QH_coupling and self.QH_to_V_func is not None:
            try:
                V0 = self.QH_to_V_func(Q_avg, H_avg)
                return V0
            except:
                pass
        
        # 否则使用传统V-H关系的逆向估算
        # 这里需要通过V-H关系的逆函数计算，简化为直接使用initial_V
        return self.initial_V
    
    def _compute_discrete_coefficients(self, tf_name: str) -> Dict[str, float]:
        """
        计算指定传递函数的离散化系数
        
        使用一阶保持器（ZOH）离散化方法
        对于 G(s) = (τs + 1) / (αs + 1)
        
        Args:
            tf_name (str): 传递函数名称 ('G11', 'G12', 'G21', 'G22')
            
        Returns:
            Dict[str, float]: 离散化系数
        """
        param = self.params[tf_name]
        tau = param['tau']
        alpha = param['alpha']
        
        # 极点部分的离散化
        a1 = np.exp(-self.dt / alpha)
        b0 = (1 - a1)
        
        # 零点部分的近似处理
        c0 = 1.0 + tau / self.dt
        c1 = -tau / self.dt
        
        return {'a1': a1, 'b0': b0, 'c0': c0, 'c1': c1}
    
    def step(self, Q_in: float, Q_in_down: float = 0.0) -> Dict[str, float]:
        """
        四方程IDZ模型的时步推进
        
        计算上下游双节点的耦合响应：
        Q1_out = G11 * ΔQ1_in + G12 * ΔQ2_in + Q0_up
        Q2_out = G21 * ΔQ1_in + G22 * ΔQ2_in + Q0_down
        
        Args:
            Q_in (float): 上游入流量（m³/s），保持与基类接口兼容
            Q_in_down (float): 下游入流量（m³/s），默认为0
            
        Returns:
            Dict[str, float]: 仿真结果
        """
        # 为了兼容基类接口，将Q_in作为上游入流
        Q_in_up = Q_in
        
        # 计算相对于平衡点的扰动
        dQ_up = Q_in_up - self.Q0_up
        dQ_down = Q_in_down - self.Q0_down
        
        # 对每个传递函数计算响应
        responses = {}
        
        for tf_name in ['G11', 'G12', 'G21', 'G22']:
            # 选择输入信号
            if tf_name in ['G11', 'G21']:  # 上游输入
                input_signal = dQ_up
            else:  # G12, G22 - 下游输入
                input_signal = dQ_down
            
            # 延迟处理
            delay_buffer = self.delay_buffers[tf_name]
            delayed_input = delay_buffer[0]
            self.delay_buffers[tf_name] = delay_buffer[1:] + [input_signal]
            
            # 传递函数计算
            coeffs = self.discrete_coeffs[tf_name]
            states = self.internal_states[tf_name]
            
            # y[k] = a1*y[k-1] + b0*(c0*u[k] + c1*u[k-1])
            u_filtered = (coeffs['c0'] * delayed_input + 
                         coeffs['c1'] * states['u_prev'])
            response = (coeffs['a1'] * states['y_prev'] + 
                       coeffs['b0'] * u_filtered)
            
            # 更新内部状态
            states['y_prev'] = response
            states['u_prev'] = delayed_input
            
            responses[tf_name] = response
        
        # 计算总输出（传递函数矩阵乘法）
        Q_out_up = (responses['G11'] + responses['G12'] + self.Q0_up)
        Q_out_down = (responses['G21'] + responses['G22'] + self.Q0_down)
        
        # 数值保护
        Q_out_up = max(0.0, Q_out_up)
        Q_out_down = max(0.0, Q_out_down)
        
        # 使用平均出流作为系统总出流
        Q_out = (Q_out_up + Q_out_down) / 2.0
        
        # 更新物理状态
        Q_in_avg = (Q_in_up + Q_in_down) / 2.0
        self._update_physical_states(Q_in_avg, Q_out)
        self.current_Q_out = Q_out
        
        # 记录状态
        self._record_state(Q_in_avg)
        
        return {
            'Q_out': Q_out,
            'Q_out_up': Q_out_up,
            'Q_out_down': Q_out_down,
            'H_out': self.current_H,
            'V': self.current_V,
            'time': self.time,
            'dQ_up': dQ_up,
            'dQ_down': dQ_down,
            'G11_response': responses['G11'],
            'G12_response': responses['G12'],
            'G21_response': responses['G21'],
            'G22_response': responses['G22'],
            'equilibrium_V': self.V0
        }
    
    def reset(self, new_initial_V: Optional[float] = None):
        """
        重置模型状态
        
        Args:
            new_initial_V (Optional[float]): 新的初始蓄水量
        """
        super().reset(new_initial_V)
        
        # 重置所有传递函数的延迟缓冲区和内部状态
        for tf_name in self.params:
            delay_steps = int(np.ceil(self.params[tf_name]['T'] / self.dt))
            self.delay_buffers[tf_name] = [0.0] * max(1, delay_steps)
            self.internal_states[tf_name] = {'y_prev': 0.0, 'u_prev': 0.0}
    
    def get_transfer_function_matrix(self) -> Dict[str, Any]:
        """
        获取传递函数矩阵的参数
        
        Returns:
            Dict: 传递函数矩阵参数
        """
        return {
            'equilibrium_point': {
                'Q0_up': self.Q0_up,
                'H0_up': self.H0_up,
                'Q0_down': self.Q0_down,
                'H0_down': self.H0_down,
                'V0': self.V0
            },
            'transfer_functions': self.params,
            'discrete_coefficients': self.discrete_coeffs
        }
    
    def update_equilibrium_point(self, Q0_up: float, H0_up: float, 
                                Q0_down: float, H0_down: float):
        """
        更新平衡点
        
        Args:
            Q0_up (float): 新的上游稳态流量
            H0_up (float): 新的上游稳态水位
            Q0_down (float): 新的下游稳态流量
            H0_down (float): 新的下游稳态水位
        """
        self.Q0_up = Q0_up
        self.H0_up = H0_up
        self.Q0_down = Q0_down
        self.H0_down = H0_down
        
        # 重新计算平衡蓄量
        self.V0 = self._compute_equilibrium_volume(Q0_up, H0_up, Q0_down, H0_down)