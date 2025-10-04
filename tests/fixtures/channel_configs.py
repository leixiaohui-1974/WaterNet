"""
渠道配置数据

提供各种测试用例的渠道几何配置。
"""

import numpy as np


def simple_rectangular_channel():
    """简单矩形明渠配置"""
    return [
        {
            'mileage': 0.0,
            'elevation': 100.0,
            'roughness': 0.025,
            'area_func': lambda h: max(0, h - 100) * 10,
            'top_width_func': lambda h: 10 if h > 100 else 0
        },
        {
            'mileage': 1000.0,
            'elevation': 99.0,
            'roughness': 0.025,
            'area_func': lambda h: max(0, h - 99) * 10,
            'top_width_func': lambda h: 10 if h > 99 else 0
        }
    ]


def trapezoidal_channel():
    """梯形断面明渠配置"""
    def trap_area(h, bottom_width=8.0, side_slope=2.0, bottom_elev=100.0):
        if h <= bottom_elev:
            return 0.0
        depth = h - bottom_elev
        return depth * (bottom_width + side_slope * depth)
    
    def trap_width(h, bottom_width=8.0, side_slope=2.0, bottom_elev=100.0):
        if h <= bottom_elev:
            return 0.0
        depth = h - bottom_elev
        return bottom_width + 2 * side_slope * depth
    
    return [
        {
            'mileage': 0.0,
            'elevation': 100.0,
            'roughness': 0.030,
            'area_func': lambda h: trap_area(h, 8.0, 2.0, 100.0),
            'top_width_func': lambda h: trap_width(h, 8.0, 2.0, 100.0)
        },
        {
            'mileage': 500.0,
            'elevation': 99.5,
            'roughness': 0.028,
            'area_func': lambda h: trap_area(h, 10.0, 1.5, 99.5),
            'top_width_func': lambda h: trap_width(h, 10.0, 1.5, 99.5)
        },
        {
            'mileage': 1000.0,
            'elevation': 99.0,
            'roughness': 0.025,
            'area_func': lambda h: trap_area(h, 12.0, 1.0, 99.0),
            'top_width_func': lambda h: trap_width(h, 12.0, 1.0, 99.0)
        }
    ]


def complex_channel():
    """复杂多断面明渠配置"""
    sections = []
    n_sections = 5
    
    for i in range(n_sections):
        mileage = i * 250.0
        elevation = 100.0 - i * 0.3
        roughness = 0.025 + i * 0.002
        
        # 变化的断面尺寸
        width = 8.0 + i * 1.0
        
        sections.append({
            'mileage': mileage,
            'elevation': elevation,
            'roughness': roughness,
            'area_func': lambda h, w=width, e=elevation: max(0, h - e) * w,
            'top_width_func': lambda h, w=width, e=elevation: w if h > e else 0
        })
    
    return sections


def get_test_flow_series(series_type="steady"):
    """获取测试流量序列"""
    if series_type == "steady":
        return np.ones(10) * 12.0
    
    elif series_type == "step":
        return np.concatenate([
            np.ones(5) * 8.0,
            np.ones(5) * 16.0
        ])
    
    elif series_type == "sinusoidal":
        t = np.linspace(0, 2*np.pi, 20)
        return 12.0 + 6.0 * np.sin(t)
    
    elif series_type == "flood":
        # 模拟洪水过程
        return np.array([
            5.0, 6.0, 8.0, 12.0, 18.0, 25.0, 30.0, 
            28.0, 24.0, 20.0, 15.0, 12.0, 10.0, 8.0, 6.0
        ])
    
    else:
        raise ValueError(f"未知的流量序列类型: {series_type}")


def get_test_boundary_conditions():
    """获取测试边界条件"""
    return {
        'steady_flow': {
            'Q_upstream': 12.0,
            'H_downstream': 99.5
        },
        'low_flow': {
            'Q_upstream': 5.0,
            'H_downstream': 99.2
        },
        'high_flow': {
            'Q_upstream': 25.0,
            'H_downstream': 100.0
        }
    }


def get_physical_relations(relation_type="simple"):
    """获取物理关系函数"""
    
    if relation_type == "simple":
        def V_to_H_simple(V):
            base_level = 99.0
            storage_coeff = 1.0 / 8000.0
            return base_level + V * storage_coeff
        
        def H_to_Q_simple(H):
            threshold = 99.0
            if H <= threshold:
                return 0.0
            return 25.0 * (H - threshold) ** 1.5
        
        return V_to_H_simple, H_to_Q_simple
    
    elif relation_type == "nonlinear":
        def V_to_H_nonlinear(V):
            base_level = 99.0
            if V <= 0:
                return base_level
            return base_level + 0.001 * V + 1e-8 * V**2
        
        def H_to_Q_nonlinear(H):
            threshold = 99.0
            if H <= threshold:
                return 0.0
            depth = H - threshold
            # 复合堰流公式
            if depth < 0.5:
                return 20.0 * depth ** 1.5
            else:
                return 20.0 * 0.5**1.5 + 30.0 * (depth - 0.5) ** 2.0
        
        return V_to_H_nonlinear, H_to_Q_nonlinear
    
    else:
        raise ValueError(f"未知的物理关系类型: {relation_type}")


def get_model_parameters(model_type="muskingum"):
    """获取模型参数配置"""
    
    if model_type == "muskingum":
        return {
            'standard': {'K': 3600.0, 'x': 0.2},
            'fast': {'K': 1800.0, 'x': 0.3},
            'slow': {'K': 7200.0, 'x': 0.1}
        }
    
    elif model_type == "idz":
        return {
            'standard': {'tau': 1800.0, 'T_delay': 600.0, 'alpha': 3600.0},
            'responsive': {'tau': 900.0, 'T_delay': 300.0, 'alpha': 1800.0},
            'damped': {'tau': 3600.0, 'T_delay': 1200.0, 'alpha': 7200.0}
        }
    
    else:
        raise ValueError(f"未知的模型类型: {model_type}")