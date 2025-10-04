"""
降阶模型简化API工厂

提供简化的模型创建接口，使用预设的默认参数，
让用户能够快速创建和使用降阶模型。

基于降阶模型理论分析的最佳实践参数。

Author: WaterNet Development Team
Date: 2024-10-04
"""

import numpy as np
from typing import Optional, Callable, Tuple
from ..models.lumped_models import (
    MuskingumModel, StorageRoutingModel, IntegralDelayZeroModel
)

try:
    from ..models.muskingum_cunge import MuskingumCungeModel, create_cunge_model_from_geometry
except ImportError:
    MuskingumCungeModel = None
    create_cunge_model_from_geometry = None


def create_default_physical_relations(
    base_level: float = 100.0,
    storage_coefficient: float = 1e-4,
    flow_coefficient: float = 25.0,
    flow_exponent: float = 1.5
) -> Tuple[Callable[[float], float], Callable[[float], float]]:
    """
    创建默认的物理关系函数
    
    基于常见的工程经验参数，适用于大多数应用场景。
    
    Args:
        base_level (float): 基准水位 (m)，默认100.0
        storage_coefficient (float): 蓄量系数 (1/m²)，默认1e-4
        flow_coefficient (float): 流量系数，默认25.0
        flow_exponent (float): 流量公式指数，默认1.5
        
    Returns:
        Tuple[Callable, Callable]: (V_to_H_func, H_to_Q_func)
        
    Example:
        >>> V_to_H, H_to_Q = create_default_physical_relations()
        >>> # 使用默认参数创建物理关系函数
    """
    def V_to_H_func(V: float) -> float:
        """蓄量-水位关系: H = base_level + V * storage_coefficient"""
        return base_level + V * storage_coefficient
    
    def H_to_Q_func(H: float) -> float:
        """水位-出流关系: Q = flow_coefficient * (H - base_level)^flow_exponent"""
        if H <= base_level:
            return 0.0
        return flow_coefficient * (H - base_level) ** flow_exponent
    
    return V_to_H_func, H_to_Q_func


def create_simple_muskingum(
    K: Optional[float] = None,
    x: Optional[float] = None, 
    dt: Optional[float] = None,
    initial_V: Optional[float] = None,
    V_to_H_func: Optional[Callable[[float], float]] = None,
    H_to_Q_func: Optional[Callable[[float], float]] = None,
    name: str = "SimpleMuskingum"
) -> MuskingumModel:
    """
    创建简化的马斯京干模型
    
    使用基于理论分析的最佳实践默认参数。
    
    Args:
        K (Optional[float]): 滞时常数 (秒)，默认3600.0 (1小时)
        x (Optional[float]): 权重系数，默认0.2 
        dt (Optional[float]): 时间步长 (秒)，默认60.0 (1分钟)
        initial_V (Optional[float]): 初始蓄水量 (m³)，默认15000.0
        V_to_H_func (Optional[Callable]): 蓄量-水位函数，默认使用标准关系
        H_to_Q_func (Optional[Callable]): 水位-出流函数，默认使用标准关系
        name (str): 模型名称
        
    Returns:
        MuskingumModel: 配置好的马斯京干模型
        
    Example:
        >>> # 最简单的使用方式
        >>> model = create_simple_muskingum()
        >>> 
        >>> # 自定义部分参数
        >>> model = create_simple_muskingum(K=1800.0, x=0.3)
    """
    # 使用默认参数（基于理论分析的最佳实践）
    K = K if K is not None else 3600.0          # 1小时滞时常数
    x = x if x is not None else 0.2             # 标准权重系数
    dt = dt if dt is not None else 60.0         # 1分钟时间步长
    initial_V = initial_V if initial_V is not None else 15000.0  # 设计工况蓄量
    
    # 创建默认物理关系函数
    if V_to_H_func is None or H_to_Q_func is None:
        default_V_to_H, default_H_to_Q = create_default_physical_relations()
        V_to_H_func = V_to_H_func or default_V_to_H
        H_to_Q_func = H_to_Q_func or default_H_to_Q
    
    return MuskingumModel(
        dt=dt,
        K=K,
        x=x,
        initial_V=initial_V,
        V_to_H_func=V_to_H_func,
        H_to_Q_func=H_to_Q_func,
        name=name
    )


def create_simple_muskingum_cunge(
    length: float,
    width: float,
    slope: float,
    roughness: float,
    reference_discharge: Optional[float] = None,
    dt: Optional[float] = None,
    initial_V: Optional[float] = None,
    V_to_H_func: Optional[Callable[[float], float]] = None,
    H_to_Q_func: Optional[Callable[[float], float]] = None,
    enable_adaptive: bool = False,
    name: str = "SimpleMuskingumCunge"
) -> object:
    """
    创建简化的马斯京干-康吉模型
    
    基于河道物理特性自动计算马斯京干参数，无需经验率定。
    
    Args:
        length (float): 河段长度 (m)
        width (float): 河道宽度 (m) 
        slope (float): 河底坡度
        roughness (float): 曼宁粗糙系数
        reference_discharge (Optional[float]): 参考流量 (m³/s)，默认100.0
        dt (Optional[float]): 时间步长 (秒)，默认60.0
        initial_V (Optional[float]): 初始蓄水量 (m³)，默认15000.0
        V_to_H_func (Optional[Callable]): 蓄量-水位函数
        H_to_Q_func (Optional[Callable]): 水位-出流函数
        enable_adaptive (bool): 是否启用自适应参数，默认False
        name (str): 模型名称
        
    Returns:
        康吉模型实例 (如果模块可用) 或 马斯京干模型 (fallback)
        
    Example:
        >>> # 基于河道几何创建康吉模型
        >>> model = create_simple_muskingum_cunge(
        ...     length=1000.0, width=50.0, slope=0.001, roughness=0.025
        ... )
        >>> 
        >>> # 启用自适应参数
        >>> adaptive_model = create_simple_muskingum_cunge(
        ...     length=1000.0, width=50.0, slope=0.001, roughness=0.025,
        ...     enable_adaptive=True
        ... )
    """
    # 默认参数
    reference_discharge = reference_discharge if reference_discharge is not None else 100.0
    dt = dt if dt is not None else 60.0
    initial_V = initial_V if initial_V is not None else 15000.0
    
    # 创建默认物理关系函数
    if V_to_H_func is None or H_to_Q_func is None:
        default_V_to_H, default_H_to_Q = create_default_physical_relations()
        V_to_H_func = V_to_H_func or default_V_to_H
        H_to_Q_func = H_to_Q_func or default_H_to_Q
    
    # 尝试创建康吉模型
    if create_cunge_model_from_geometry is not None:
        try:
            return create_cunge_model_from_geometry(
                dt=dt,
                length=length,
                width=width,
                slope=slope,
                roughness=roughness,
                reference_discharge=reference_discharge,
                initial_V=initial_V,
                V_to_H_func=V_to_H_func,
                H_to_Q_func=H_to_Q_func,
                enable_adaptive_parameters=enable_adaptive,
                name=name
            )
        except Exception as e:
            print(f"Warning: 无法创建康吉模型 ({e})，使用传统马斯京干模型")
    
    # Fallback到传统马斯京干模型
    print("Warning: 康吉模型不可用，使用传统马斯京干模型")
    return create_simple_muskingum(
        K=3600.0, x=0.2, dt=dt, initial_V=initial_V,
        V_to_H_func=V_to_H_func, H_to_Q_func=H_to_Q_func, name=name
    )


def create_simple_storage_routing(
    dt: Optional[float] = None,
    initial_V: Optional[float] = None,
    V_to_H_func: Optional[Callable[[float], float]] = None,
    H_to_Q_func: Optional[Callable[[float], float]] = None,
    enable_qh_coupling: bool = True,
    name: str = "SimpleStorageRouting"
) -> StorageRoutingModel:
    """
    创建简化的蓄量演算模型
    
    默认启用Q-H耦合计算，提供更高精度。
    
    Args:
        dt (Optional[float]): 时间步长 (秒)，默认60.0
        initial_V (Optional[float]): 初始蓄水量 (m³)，默认15000.0
        V_to_H_func (Optional[Callable]): 蓄量-水位函数
        H_to_Q_func (Optional[Callable]): 水位-出流函数
        enable_qh_coupling (bool): 是否启用Q-H耦合，默认True
        name (str): 模型名称
        
    Returns:
        StorageRoutingModel: 配置好的蓄量演算模型
        
    Example:
        >>> # 使用默认参数创建
        >>> model = create_simple_storage_routing()
        >>> 
        >>> # 禁用Q-H耦合（使用传统方法）
        >>> model = create_simple_storage_routing(enable_qh_coupling=False)
    """
    # 默认参数
    dt = dt if dt is not None else 60.0
    initial_V = initial_V if initial_V is not None else 15000.0
    
    # 创建默认物理关系函数
    if V_to_H_func is None or H_to_Q_func is None:
        default_V_to_H, default_H_to_Q = create_default_physical_relations()
        V_to_H_func = V_to_H_func or default_V_to_H
        H_to_Q_func = H_to_Q_func or default_H_to_Q
    
    # Q-H耦合函数
    QH_to_V_func = None
    if enable_qh_coupling:
        def simple_qh_coupling(Q: float, H: float) -> float:
            """简化的Q-H耦合蓄量计算"""
            base_level = 100.0
            depth = max(0, H - base_level)
            
            # 基础体积（假设矩形断面）
            base_volume = depth * 1000.0 * 500.0  # 深度 × 长度 × 宽度
            
            # 流量修正（考虑弗劳德数效应）
            if Q > 0 and depth > 0.01:
                velocity = Q / (depth * 500.0)
                froude_number = velocity / np.sqrt(9.81 * depth)
                flow_correction = 1.0 - 0.05 * min(froude_number, 0.5)
            else:
                flow_correction = 1.0
            
            return base_volume * flow_correction
        
        QH_to_V_func = simple_qh_coupling
    
    return StorageRoutingModel(
        dt=dt,
        initial_V=initial_V,
        V_to_H_func=V_to_H_func,
        H_to_Q_func=H_to_Q_func,
        name=name,
        QH_to_V_func=QH_to_V_func
    )


def create_simple_idz(
    tau: Optional[float] = None,
    T_delay: Optional[float] = None,
    alpha: Optional[float] = None,
    dt: Optional[float] = None,
    initial_V: Optional[float] = None,
    V_to_H_func: Optional[Callable[[float], float]] = None,
    H_to_Q_func: Optional[Callable[[float], float]] = None,
    name: str = "SimpleIDZ"
) -> IntegralDelayZeroModel:
    """
    创建简化的IDZ模型
    
    使用基于系统辨识的经验参数。
    
    Args:
        tau (Optional[float]): 零点时间常数 (秒)，默认600.0
        T_delay (Optional[float]): 延迟时间 (秒)，默认300.0
        alpha (Optional[float]): 极点时间常数 (秒)，默认1500.0
        dt (Optional[float]): 时间步长 (秒)，默认60.0
        initial_V (Optional[float]): 初始蓄水量 (m³)，默认15000.0
        V_to_H_func (Optional[Callable]): 蓄量-水位函数
        H_to_Q_func (Optional[Callable]): 水位-出流函数
        name (str): 模型名称
        
    Returns:
        IntegralDelayZeroModel: 配置好的IDZ模型
        
    Example:
        >>> # 默认参数创建
        >>> model = create_simple_idz()
        >>> 
        >>> # 自定义延迟特性
        >>> model = create_simple_idz(T_delay=600.0, alpha=2000.0)
    """
    # 默认参数（基于系统辨识经验）
    tau = tau if tau is not None else 600.0         # 10分钟零点时间常数
    T_delay = T_delay if T_delay is not None else 300.0  # 5分钟延迟
    alpha = alpha if alpha is not None else 1500.0  # 25分钟极点时间常数
    dt = dt if dt is not None else 60.0
    initial_V = initial_V if initial_V is not None else 15000.0
    
    # 创建默认物理关系函数
    if V_to_H_func is None or H_to_Q_func is None:
        default_V_to_H, default_H_to_Q = create_default_physical_relations()
        V_to_H_func = V_to_H_func or default_V_to_H
        H_to_Q_func = H_to_Q_func or default_H_to_Q
    
    return IntegralDelayZeroModel(
        dt=dt,
        tau=tau,
        T_delay=T_delay,
        alpha=alpha,
        initial_V=initial_V,
        V_to_H_func=V_to_H_func,
        H_to_Q_func=H_to_Q_func,
        name=name
    )


def create_model_by_scenario(
    scenario: str,
    **kwargs
) -> object:
    """
    根据应用场景创建合适的模型
    
    基于降阶模型选择决策矩阵自动选择模型类型。
    
    Args:
        scenario (str): 应用场景，可选值：
            - 'reservoir': 水库调洪演算 -> 蓄量演算模型
            - 'river_forecast': 河道洪水预报 -> 马斯京干模型  
            - 'precise_control': 精细控制分析 -> IDZ模型
            - 'quick_estimate': 快速工程估算 -> 水量平衡模型
        **kwargs: 传递给对应模型的参数
        
    Returns:
        降阶模型实例
        
    Example:
        >>> # 水库调洪场景
        >>> model = create_model_by_scenario('reservoir')
        >>> 
        >>> # 河道预报场景，自定义参数
        >>> model = create_model_by_scenario('river_forecast', K=1800.0)
    """
    scenario_mapping = {
        'reservoir': create_simple_storage_routing,
        'water_reservoir': create_simple_storage_routing,
        'storage': create_simple_storage_routing,
        
        'river_forecast': create_simple_muskingum,
        'river': create_simple_muskingum,
        'flood_forecast': create_simple_muskingum,
        'muskingum': create_simple_muskingum,
        
        'precise_control': create_simple_idz,
        'control': create_simple_idz,
        'idz': create_simple_idz,
        
        'quick_estimate': lambda **kw: None,  # TODO: 实现水量平衡模型
        'balance': lambda **kw: None,
    }
    
    if scenario.lower() not in scenario_mapping:
        available_scenarios = list(scenario_mapping.keys())
        raise ValueError(f"未知场景 '{scenario}'。可用场景: {available_scenarios}")
    
    model_factory = scenario_mapping[scenario.lower()]
    
    if model_factory is None:
        raise NotImplementedError(f"场景 '{scenario}' 的模型尚未实现")
    
    return model_factory(**kwargs)


# 便捷别名
quick_muskingum = create_simple_muskingum
quick_storage = create_simple_storage_routing  
quick_idz = create_simple_idz
auto_model = create_model_by_scenario