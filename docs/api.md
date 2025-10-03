# WaterNet API 文档

## 概述

WaterNet是一个基于圣维南方程组的明渠水力模型接口系统，提供高精度物理模型与多种降阶模型的统一建模框架。

## 核心组件

### 1. HydroModel 抽象基类

所有水力模型的基础接口。

```python
from waternet.interfaces.hydro_model import HydroModel

class CustomModel(HydroModel):
    def __init__(self, name, node_names):
        super().__init__(name, node_names)
    
    def get_equations(self, variables, dt, prev_states):
        # 实现模型方程
        return {"equation_1": residual_value}
    
    def get_variable_names(self):
        # 返回变量名列表
        return ["Q_pipe_1", "H_node_1"]
```

### 2. SaintVenantModel 圣维南模型

高精度物理模型，基于圣维南方程组。

```python
from waternet.models.saint_venant import SaintVenantModel

# 定义断面几何
sections = [
    {
        'mileage': 0.0,
        'elevation': 100.0,
        'roughness': 0.025,
        'area_func': lambda h: max(0, h - 100) * 10,
        'top_width_func': lambda h: 10 if h > 100 else 0
    },
    # 更多断面...
]

# 创建模型
model = SaintVenantModel("Channel1", "upstream", "downstream", sections)

# 恒定流计算
result = model.compute_steady_state(Q=10.0, downstream_H=99.5)
```

### 3. 降阶模型库

#### BaseLumpedModel 基类

所有降阶模型的统一框架。

```python
from waternet.models.lumped_models import BaseLumpedModel

# 定义物理关系函数
def V_to_H(volume):
    return base_level + volume / storage_coefficient

def H_to_Q(water_level):
    return flow_coefficient * (water_level - threshold) ** 1.5
```

#### MuskingumModel 马斯京干模型

经典河道洪水演进模型。

```python
from waternet.models.lumped_models import MuskingumModel

model = MuskingumModel(
    dt=60.0,                    # 时间步长
    K=3600.0,                   # 滞时常数
    x=0.2,                      # 权重系数
    initial_V=10000.0,          # 初始蓄水量
    V_to_H_func=V_to_H,         # 蓄量-水位关系
    H_to_Q_func=H_to_Q          # 水位-流量关系
)

# 单步仿真
result = model.step(Q_in=15.0)

# 批量仿真
Q_in_series = [10, 15, 20, 15, 10]
results_df = model.run_simulation(Q_in_series)
```

#### StorageRoutingModel 蓄量演算模型

基于蓄量连续性方程的模型。

```python
from waternet.models.lumped_models import StorageRoutingModel

model = StorageRoutingModel(
    dt=60.0,
    initial_V=10000.0,
    V_to_H_func=V_to_H,
    H_to_Q_func=H_to_Q
)
```

#### IntegralDelayZeroModel IDZ模型

基于传递函数的系统响应模型。

```python
from waternet.models.lumped_models import IntegralDelayZeroModel

model = IntegralDelayZeroModel(
    dt=60.0,
    tau=600.0,      # 零点时间常数
    T_delay=300.0,  # 延迟时间
    alpha=1800.0,   # 极点时间常数
    initial_V=10000.0,
    V_to_H_func=V_to_H,
    H_to_Q_func=H_to_Q
)
```

### 4. ParameterEstimator 参数估计器

参数辨识和模型标定工具。

```python
from waternet.parameter_estimation.estimator import ParameterEstimator

# 创建估计器
estimator = ParameterEstimator(saint_venant_model)

# 静态特征曲线辨识
Q_range = np.linspace(5, 25, 10)
H_range = np.linspace(99, 101, 8)
curves = estimator.identify_static_curves(Q_range, H_range)

# 动态参数辨识
unsteady_data = {
    'Q_in': Q_in_series,
    'H_down': H_down_series,
    'dt': 60.0
}
params = estimator.identify_dynamic_parameters(unsteady_data, MuskingumModel)
```

### 5. SynchronizedTwinningHarness 同步孪生协调器

精细化模型与降阶模型的同步运行管理。

```python
from waternet.coordination.twinning_harness import SynchronizedTwinningHarness

# 创建协调器
harness = SynchronizedTwinningHarness(
    saint_venant_model=sv_model,
    reduced_order_model=rom_model,
    correction_interval=10,     # 校正间隔
    correction_threshold=0.1    # 误差阈值
)

# 运行同步仿真
results = harness.run_synchronized_simulation(
    Q_in_series=Q_in_data,
    H_down_series=H_down_data,
    dt=60.0,
    enable_correction=True
)

# 获取性能摘要
summary = harness.get_performance_summary()
```

## 使用模式

### 模式1：独立降阶模型仿真

```python
# 创建降阶模型
model = MuskingumModel(...)

# 运行仿真
results = model.run_simulation(Q_in_series)

# 分析结果
print(f"最终出流: {results['Q_out'].iloc[-1]}")
```

### 模式2：参数标定

```python
# 基于物理模型标定降阶模型参数
estimator = ParameterEstimator(physical_model)
best_params = estimator.identify_dynamic_parameters(data, ModelClass)

# 使用标定后的参数创建模型
calibrated_model = ModelClass(**best_params['best_parameters'])
```

### 模式3：同步孪生仿真

```python
# 双模型同步运行，自动校正
harness = SynchronizedTwinningHarness(physical_model, reduced_model)
results = harness.run_synchronized_simulation(inputs, enable_correction=True)

# 实时监控模型性能
performance = harness.get_performance_summary()
```

## 数据结构

### 断面几何数据

```python
section = {
    'mileage': float,           # 里程桩号
    'elevation': float,         # 底高程
    'roughness': float,         # 曼宁糙率
    'area_func': callable,      # 面积函数 A(H)
    'top_width_func': callable  # 水面宽函数 T(H)
}
```

### 仿真结果数据

```python
# 降阶模型结果
step_result = {
    'Q_out': float,    # 出流量
    'H_out': float,    # 出口水位
    'V': float,        # 蓄水量
    'time': float      # 当前时间
}

# 同步孪生结果
sync_result = {
    'time': float,
    'Q_in': float,
    'Q_out_sv': float,     # 圣维南模型出流
    'Q_out_rom': float,    # 降阶模型出流
    'H_up_sv': float,      # 圣维南模型上游水位
    'H_up_rom': float,     # 降阶模型上游水位
    'error_Q': float,      # 流量误差
    'error_H': float       # 水位误差
}
```

## 配置参数

### 优化算法配置

```python
estimator.optimization_config = {
    'method': 'differential_evolution',
    'maxiter': 100,
    'tol': 1e-6,
    'polish': True,
    'seed': 42
}
```

### 校正策略配置

```python
harness.correction_interval = 10      # 校正间隔
harness.correction_threshold = 0.1    # 误差阈值
harness.monitoring_window = 20        # 监控窗口大小
```

## 异常处理

WaterNet使用标准Python异常处理机制：

```python
try:
    result = model.compute_steady_state(Q, H_down)
except ValueError as e:
    print(f"参数错误: {e}")
except RuntimeError as e:
    print(f"计算错误: {e}")
```

常见异常类型：
- `ValueError`: 参数超出合理范围
- `RuntimeError`: 数值计算不收敛
- `TypeError`: 输入类型错误

## 最佳实践

1. **断面几何定义**: 确保面积和水面宽函数的单调性和连续性
2. **参数边界**: 为参数辨识设置合理的搜索边界
3. **数值稳定性**: 避免极端的几何参数和边界条件
4. **计算效率**: 根据精度需求选择合适的时间步长
5. **结果验证**: 始终检查计算结果的物理合理性