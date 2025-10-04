"""
控制信号管理系统

实现时变控制信号和调度表管理，支持外部Agent或调度系统的动态控制。
通过统一的接口管理各种控制设备的信号，支持插值和时间调度。

设计原则:
1. 时变性: 支持基于时间的动态控制信号
2. 插值性: 支持线性和高级插值方法
3. 鲁棒性: 处理缺失控制信号和边界情况
4. 扩展性: 支持多种控制设备类型

主要组件:
- ControlSignals: 控制信号基类
- ControlSchedule: 时间调度表
- ControlDevice: 控制设备抽象
- ControlSignalManager: 控制信号管理器

Author: WaterNet Development Team  
Date: 2024-10-04
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union, Any, Callable, Tuple
from dataclasses import dataclass, field
import numpy as np
import pandas as pd
from scipy.interpolate import interp1d
import logging
from enum import Enum


class ControlDeviceType(Enum):
    """控制设备类型枚举"""
    GATE = "gate"           # 闸门
    PUMP = "pump"           # 泵站
    VALVE = "valve"         # 阀门
    WEIR = "weir"           # 堰
    SPILLWAY = "spillway"   # 溢洪道
    CUSTOM = "custom"       # 自定义设备


@dataclass
class ControlDeviceConfig:
    """控制设备配置"""
    device_id: str
    device_type: ControlDeviceType
    min_value: float = 0.0
    max_value: float = 1.0
    default_value: float = 0.0
    description: str = ""
    enabled: bool = True


class ControlDevice(ABC):
    """
    控制设备抽象基类
    
    定义控制设备的统一接口，包括信号验证、物理约束等功能。
    """
    
    def __init__(self, config: ControlDeviceConfig):
        """
        初始化控制设备
        
        Args:
            config (ControlDeviceConfig): 设备配置
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # 验证配置
        if config.min_value >= config.max_value:
            raise ValueError(f"设备 {config.device_id}: 最小值必须小于最大值")
        
        if not (config.min_value <= config.default_value <= config.max_value):
            raise ValueError(f"设备 {config.device_id}: 默认值必须在[min_value, max_value]范围内")
    
    @abstractmethod
    def validate_signal(self, signal_value: float) -> bool:
        """
        验证控制信号是否有效
        
        Args:
            signal_value (float): 控制信号值
            
        Returns:
            bool: True表示信号有效
        """
        pass
    
    @abstractmethod
    def apply_constraints(self, signal_value: float) -> float:
        """
        应用物理约束，确保信号在有效范围内
        
        Args:
            signal_value (float): 原始信号值
            
        Returns:
            float: 约束后的信号值
        """
        pass
    
    def get_default_value(self) -> float:
        """获取默认控制值"""
        return self.config.default_value
    
    def is_enabled(self) -> bool:
        """检查设备是否启用"""
        return self.config.enabled
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.config.device_id})"


class GateDevice(ControlDevice):
    """
    闸门控制设备
    
    控制信号范围: [0, 1] (0=关闭, 1=全开)
    """
    
    def __init__(self, device_id: str, min_opening: float = 0.0, 
                 max_opening: float = 1.0, default_opening: float = 0.5):
        """
        初始化闸门设备
        
        Args:
            device_id (str): 设备ID
            min_opening (float): 最小开度
            max_opening (float): 最大开度
            default_opening (float): 默认开度
        """
        config = ControlDeviceConfig(
            device_id=device_id,
            device_type=ControlDeviceType.GATE,
            min_value=min_opening,
            max_value=max_opening,
            default_value=default_opening,
            description=f"闸门控制设备 - {device_id}"
        )
        super().__init__(config)
    
    def validate_signal(self, signal_value: float) -> bool:
        """验证闸门开度是否在有效范围内"""
        return self.config.min_value <= signal_value <= self.config.max_value
    
    def apply_constraints(self, signal_value: float) -> float:
        """将闸门开度约束在[min_value, max_value]范围内"""
        return np.clip(signal_value, self.config.min_value, self.config.max_value)


class PumpDevice(ControlDevice):
    """
    泵站控制设备
    
    控制信号范围: [0, 1] (0=停止, 1=满负荷运行)
    """
    
    def __init__(self, device_id: str, min_power: float = 0.0, 
                 max_power: float = 1.0, default_power: float = 0.0):
        """
        初始化泵站设备
        
        Args:
            device_id (str): 设备ID
            min_power (float): 最小功率
            max_power (float): 最大功率
            default_power (float): 默认功率
        """
        config = ControlDeviceConfig(
            device_id=device_id,
            device_type=ControlDeviceType.PUMP,
            min_value=min_power,
            max_value=max_power,
            default_value=default_power,
            description=f"泵站控制设备 - {device_id}"
        )
        super().__init__(config)
    
    def validate_signal(self, signal_value: float) -> bool:
        """验证泵站功率是否在有效范围内"""
        return self.config.min_value <= signal_value <= self.config.max_value
    
    def apply_constraints(self, signal_value: float) -> float:
        """将泵站功率约束在[min_value, max_value]范围内"""
        return np.clip(signal_value, self.config.min_value, self.config.max_value)


class ValveDevice(ControlDevice):
    """
    阀门控制设备
    
    控制信号范围: [0, 1] (0=关闭, 1=全开)
    """
    
    def __init__(self, device_id: str, min_opening: float = 0.0, 
                 max_opening: float = 1.0, default_opening: float = 1.0):
        """
        初始化阀门设备
        
        Args:
            device_id (str): 设备ID
            min_opening (float): 最小开度
            max_opening (float): 最大开度
            default_opening (float): 默认开度
        """
        config = ControlDeviceConfig(
            device_id=device_id,
            device_type=ControlDeviceType.VALVE,
            min_value=min_opening,
            max_value=max_opening,
            default_value=default_opening,
            description=f"阀门控制设备 - {device_id}"
        )
        super().__init__(config)
    
    def validate_signal(self, signal_value: float) -> bool:
        """验证阀门开度是否在有效范围内"""
        return self.config.min_value <= signal_value <= self.config.max_value
    
    def apply_constraints(self, signal_value: float) -> float:
        """将阀门开度约束在[min_value, max_value]范围内"""
        return np.clip(signal_value, self.config.min_value, self.config.max_value)


class ControlSignals:
    """
    控制信号类
    
    管理单个时刻的所有控制设备信号值。
    提供信号验证、约束应用和缺失值处理功能。
    """
    
    def __init__(self, signals: Optional[Dict[str, float]] = None):
        """
        初始化控制信号
        
        Args:
            signals (Dict[str, float], optional): 信号字典 {设备ID: 信号值}
        """
        self._signals = signals or {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def set_signal(self, device_id: str, value: float):
        """
        设置控制信号
        
        Args:
            device_id (str): 设备ID
            value (float): 信号值
        """
        self._signals[device_id] = float(value)
    
    def get_signal(self, device_id: str, default_value: float = 0.0) -> float:
        """
        获取控制信号
        
        Args:
            device_id (str): 设备ID
            default_value (float): 默认值（当信号不存在时）
            
        Returns:
            float: 信号值
        """
        return self._signals.get(device_id, default_value)
    
    def has_signal(self, device_id: str) -> bool:
        """检查是否存在指定设备的信号"""
        return device_id in self._signals
    
    def get_all_signals(self) -> Dict[str, float]:
        """获取所有信号"""
        return self._signals.copy()
    
    def update_signals(self, new_signals: Dict[str, float]):
        """
        批量更新信号
        
        Args:
            new_signals (Dict[str, float]): 新信号字典
        """
        self._signals.update(new_signals)
    
    def apply_device_constraints(self, devices: Dict[str, ControlDevice]):
        """
        应用设备约束
        
        Args:
            devices (Dict[str, ControlDevice]): 设备字典
        """
        for device_id, value in self._signals.items():
            if device_id in devices:
                device = devices[device_id]
                if device.is_enabled():
                    constrained_value = device.apply_constraints(value)
                    if constrained_value != value:
                        self.logger.debug(f"设备 {device_id} 信号约束: {value:.3f} -> {constrained_value:.3f}")
                        self._signals[device_id] = constrained_value
    
    def validate_signals(self, devices: Dict[str, ControlDevice]) -> bool:
        """
        验证所有信号的有效性
        
        Args:
            devices (Dict[str, ControlDevice]): 设备字典
            
        Returns:
            bool: True表示所有信号有效
        """
        for device_id, value in self._signals.items():
            if device_id in devices:
                device = devices[device_id]
                if device.is_enabled() and not device.validate_signal(value):
                    self.logger.error(f"设备 {device_id} 信号无效: {value}")
                    return False
        return True
    
    def __len__(self) -> int:
        return len(self._signals)
    
    def __repr__(self) -> str:
        return f"ControlSignals({len(self._signals)} signals)"


class ControlSchedule:
    """
    控制调度表
    
    管理基于时间的控制信号调度，支持插值和时间窗口查询。
    可从DataFrame、CSV文件或字典创建调度表。
    """
    
    def __init__(self, data: Optional[Union[pd.DataFrame, Dict[str, Any]]] = None,
                 interpolation_method: str = "linear"):
        """
        初始化控制调度表
        
        Args:
            data (Union[DataFrame, Dict], optional): 调度数据
            interpolation_method (str): 插值方法 ('linear', 'nearest', 'cubic')
        """
        self.interpolation_method = interpolation_method
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        if data is None:
            self._schedule_df = pd.DataFrame()
        elif isinstance(data, pd.DataFrame):
            self._schedule_df = data.copy()
        elif isinstance(data, dict):
            self._schedule_df = pd.DataFrame(data)
        else:
            raise ValueError("调度数据必须是DataFrame或字典格式")
        
        # 确保时间索引
        if not self._schedule_df.empty and 'time' in self._schedule_df.columns:
            self._schedule_df.set_index('time', inplace=True)
        
        # 对时间索引排序
        if not self._schedule_df.empty:
            self._schedule_df.sort_index(inplace=True)
        
        self._interpolators = {}
        self._build_interpolators()
    
    def _build_interpolators(self):
        """构建插值器"""
        if self._schedule_df.empty:
            return
        
        time_values = self._schedule_df.index.values
        
        for device_id in self._schedule_df.columns:
            signal_values = self._schedule_df[device_id].values
            
            if len(time_values) > 1:
                # 多点数据，创建插值器
                interpolator = interp1d(
                    time_values, signal_values,
                    kind=self.interpolation_method,
                    bounds_error=False,
                    fill_value=(signal_values[0], signal_values[-1])
                )
                self._interpolators[device_id] = interpolator
            else:
                # 单点数据，创建常数函数
                value = signal_values[0]
                self._interpolators[device_id] = lambda t, v=value: v
    
    def get_signals_at_time(self, time: float) -> ControlSignals:
        """
        获取指定时刻的控制信号
        
        Args:
            time (float): 时间（秒）
            
        Returns:
            ControlSignals: 控制信号对象
        """
        signals = {}
        
        for device_id, interpolator in self._interpolators.items():
            try:
                signal_value = float(interpolator(time))
                signals[device_id] = signal_value
            except Exception as e:
                self.logger.warning(f"设备 {device_id} 在时间 {time:.1f}s 插值失败: {e}")
        
        return ControlSignals(signals)
    
    def add_time_point(self, time: float, signals: Dict[str, float]):
        """
        添加时间点
        
        Args:
            time (float): 时间点
            signals (Dict[str, float]): 信号字典
        """
        new_row = pd.Series(signals, name=time)
        self._schedule_df = pd.concat([self._schedule_df, new_row.to_frame().T])
        self._schedule_df.sort_index(inplace=True)
        
        # 重建插值器
        self._build_interpolators()
    
    def get_time_range(self) -> Tuple[float, float]:
        """
        获取调度表的时间范围
        
        Returns:
            Tuple[float, float]: (开始时间, 结束时间)
        """
        if self._schedule_df.empty:
            return (0.0, 0.0)
        
        return (self._schedule_df.index.min(), self._schedule_df.index.max())
    
    def get_device_list(self) -> List[str]:
        """获取设备列表"""
        return list(self._schedule_df.columns)
    
    def has_device(self, device_id: str) -> bool:
        """检查是否包含指定设备"""
        return device_id in self._schedule_df.columns
    
    def get_schedule_dataframe(self) -> pd.DataFrame:
        """获取调度表DataFrame"""
        return self._schedule_df.copy()
    
    def save_to_csv(self, filename: str):
        """
        保存调度表到CSV文件
        
        Args:
            filename (str): 文件名
        """
        self._schedule_df.to_csv(filename)
        self.logger.info(f"调度表已保存到: {filename}")
    
    @classmethod
    def from_csv(cls, filename: str, time_column: str = "time",
                 interpolation_method: str = "linear") -> "ControlSchedule":
        """
        从CSV文件创建调度表
        
        Args:
            filename (str): CSV文件名
            time_column (str): 时间列名
            interpolation_method (str): 插值方法
            
        Returns:
            ControlSchedule: 调度表实例
        """
        df = pd.read_csv(filename)
        
        if time_column in df.columns:
            df.set_index(time_column, inplace=True)
        
        return cls(df, interpolation_method)
    
    @classmethod
    def create_step_schedule(cls, devices: List[str], step_times: List[float],
                           step_values: List[Dict[str, float]],
                           interpolation_method: str = "nearest") -> "ControlSchedule":
        """
        创建阶跃调度表
        
        Args:
            devices (List[str]): 设备列表
            step_times (List[float]): 阶跃时间列表
            step_values (List[Dict[str, float]]): 阶跃值列表
            interpolation_method (str): 插值方法
            
        Returns:
            ControlSchedule: 调度表实例
        """
        if len(step_times) != len(step_values):
            raise ValueError("时间点数量与值数量不匹配")
        
        data = {}
        data['time'] = step_times
        
        for device in devices:
            device_values = []
            for step_value in step_values:
                device_values.append(step_value.get(device, 0.0))
            data[device] = device_values
        
        return cls(data, interpolation_method)
    
    def __len__(self) -> int:
        return len(self._schedule_df)
    
    def __repr__(self) -> str:
        n_times = len(self._schedule_df)
        n_devices = len(self._schedule_df.columns)
        return f"ControlSchedule({n_times} times, {n_devices} devices)"


class ControlSignalManager:
    """
    控制信号管理器
    
    统一管理控制设备、调度表和信号验证。
    提供集成的接口用于求解器和模型调用。
    """
    
    def __init__(self):
        """初始化控制信号管理器"""
        self.devices: Dict[str, ControlDevice] = {}
        self.schedule: Optional[ControlSchedule] = None
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        self.logger.info("控制信号管理器初始化完成")
    
    def add_device(self, device: ControlDevice):
        """
        添加控制设备
        
        Args:
            device (ControlDevice): 控制设备实例
        """
        device_id = device.config.device_id
        
        if device_id in self.devices:
            self.logger.warning(f"设备 {device_id} 已存在，将被覆盖")
        
        self.devices[device_id] = device
        self.logger.info(f"添加控制设备: {device_id} ({device.config.device_type.value})")
    
    def remove_device(self, device_id: str):
        """
        移除控制设备
        
        Args:
            device_id (str): 设备ID
        """
        if device_id in self.devices:
            del self.devices[device_id]
            self.logger.info(f"移除控制设备: {device_id}")
        else:
            self.logger.warning(f"设备 {device_id} 不存在")
    
    def set_schedule(self, schedule: ControlSchedule):
        """
        设置控制调度表
        
        Args:
            schedule (ControlSchedule): 调度表实例
        """
        self.schedule = schedule
        self.logger.info(f"设置控制调度表: {repr(schedule)}")
    
    def get_signals_at_time(self, time: float) -> ControlSignals:
        """
        获取指定时刻的控制信号
        
        Args:
            time (float): 时间（秒）
            
        Returns:
            ControlSignals: 控制信号对象
        """
        if self.schedule is not None:
            # 从调度表获取信号
            signals = self.schedule.get_signals_at_time(time)
        else:
            # 使用默认信号
            signals = self._get_default_signals()
        
        # 应用设备约束
        signals.apply_device_constraints(self.devices)
        
        # 验证信号
        if not signals.validate_signals(self.devices):
            self.logger.warning(f"时间 {time:.1f}s 的控制信号验证失败")
        
        return signals
    
    def _get_default_signals(self) -> ControlSignals:
        """获取默认控制信号"""
        default_signals = {}
        
        for device_id, device in self.devices.items():
            if device.is_enabled():
                default_signals[device_id] = device.get_default_value()
        
        return ControlSignals(default_signals)
    
    def validate_schedule_compatibility(self) -> bool:
        """
        验证调度表与设备的兼容性
        
        Returns:
            bool: True表示兼容
        """
        if self.schedule is None:
            return True
        
        schedule_devices = set(self.schedule.get_device_list())
        manager_devices = set(self.devices.keys())
        
        # 检查未定义的设备
        undefined_devices = schedule_devices - manager_devices
        if undefined_devices:
            self.logger.warning(f"调度表中包含未定义的设备: {undefined_devices}")
        
        # 检查缺失的调度
        missing_schedules = manager_devices - schedule_devices
        if missing_schedules:
            self.logger.info(f"设备缺少调度定义，将使用默认值: {missing_schedules}")
        
        return len(undefined_devices) == 0
    
    def get_device_count(self) -> int:
        """获取设备数量"""
        return len(self.devices)
    
    def get_enabled_device_count(self) -> int:
        """获取启用的设备数量"""
        return sum(1 for device in self.devices.values() if device.is_enabled())
    
    def get_device_list(self) -> List[str]:
        """获取设备列表"""
        return list(self.devices.keys())
    
    def get_enabled_device_list(self) -> List[str]:
        """获取启用的设备列表"""
        return [device_id for device_id, device in self.devices.items() 
                if device.is_enabled()]
    
    def __repr__(self) -> str:
        enabled_count = self.get_enabled_device_count()
        total_count = self.get_device_count()
        has_schedule = self.schedule is not None
        return f"ControlSignalManager({enabled_count}/{total_count} devices, schedule={has_schedule})"


# 便捷函数
def create_gate_device(device_id: str, min_opening: float = 0.0, 
                      max_opening: float = 1.0, default_opening: float = 0.5) -> GateDevice:
    """创建闸门设备的便捷函数"""
    return GateDevice(device_id, min_opening, max_opening, default_opening)


def create_pump_device(device_id: str, min_power: float = 0.0,
                      max_power: float = 1.0, default_power: float = 0.0) -> PumpDevice:
    """创建泵站设备的便捷函数"""
    return PumpDevice(device_id, min_power, max_power, default_power)


def create_valve_device(device_id: str, min_opening: float = 0.0,
                       max_opening: float = 1.0, default_opening: float = 1.0) -> ValveDevice:
    """创建阀门设备的便捷函数"""
    return ValveDevice(device_id, min_opening, max_opening, default_opening)


def create_simple_schedule(device_signals: Dict[str, List[Tuple[float, float]]],
                          interpolation_method: str = "linear") -> ControlSchedule:
    """
    创建简单调度表的便捷函数
    
    Args:
        device_signals (Dict[str, List[Tuple[float, float]]]): 
            设备信号字典 {设备ID: [(时间, 值), ...]}
        interpolation_method (str): 插值方法
        
    Returns:
        ControlSchedule: 调度表实例
    """
    # 收集所有时间点
    all_times = set()
    for device_id, time_value_pairs in device_signals.items():
        for time, value in time_value_pairs:
            all_times.add(time)
    
    all_times = sorted(all_times)
    
    # 构建DataFrame
    data = {'time': all_times}
    
    for device_id, time_value_pairs in device_signals.items():
        # 创建插值函数
        times = [t for t, v in time_value_pairs]
        values = [v for t, v in time_value_pairs]
        
        if len(times) > 1:
            interp_func = interp1d(times, values, kind='linear', 
                                 bounds_error=False, 
                                 fill_value=(values[0], values[-1]))
            device_values = [float(interp_func(t)) for t in all_times]
        else:
            device_values = [values[0]] * len(all_times)
        
        data[device_id] = device_values
    
    return ControlSchedule(data, interpolation_method)