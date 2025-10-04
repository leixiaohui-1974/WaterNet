# WaterNet边界条件框架使用指南

本指南介绍如何使用WaterNet边界条件框架来构建和求解复杂的水力网络系统。

## 🚀 快速开始

### 基础边界条件设置

```python
from waternet.models.boundary_conditions import *
from waternet.models.control_signals import *

# 1. 创建边界条件管理器
boundary_manager = BoundaryConditionManager()

# 2. 添加流量边界条件
config = BoundaryConditionConfig("upstream_flow", "上游入流边界")
flow_bc = FlowBoundary("upstream_flow", "upstream_node", 50.0, config)
boundary_manager.add_boundary_condition(flow_bc)

# 3. 添加水位边界条件
stage_config = BoundaryConditionConfig("downstream_stage", "下游水位边界")
stage_bc = StageBoundary("downstream_stage", "downstream_node", 100.0, stage_config)
boundary_manager.add_boundary_condition(stage_bc)

# 4. 计算边界条件方程
variables = {'Q_upstream_node': 52.0, 'H_downstream_node': 99.8}
equations = boundary_manager.get_all_equations(variables, time=0.0)
print(equations)
# 输出: {'boundary_flow_upstream_node': 2.0, 'boundary_stage_downstream_node': -0.2}
```

### 时变边界条件

```python
# 创建时变函数
time_func = create_time_series_function(
    times=[0, 1800, 3600],
    values=[20, 50, 30],
    interpolation="linear"
)

# 使用时变函数创建边界条件
flow_bc = FlowBoundary("variable_flow", "node1", time_func)

# 在不同时间点计算
variables = {'Q_node1': 35.0}
eq_name, residual = flow_bc.get_equation(variables, time=900)  # t=900s时
```

## 🎛️ 控制信号管理

### 基础控制设备

```python
# 创建控制信号管理器
control_manager = ControlSignalManager()

# 添加不同类型的控制设备
gate = create_gate_device("main_gate", min_opening=0.0, max_opening=1.0, default_opening=0.5)
pump = create_pump_device("drainage_pump", min_power=0.0, max_power=1.0, default_power=0.0)
valve = create_valve_device("branch_valve", min_opening=0.0, max_opening=1.0, default_opening=0.8)

control_manager.add_device(gate)
control_manager.add_device(pump)
control_manager.add_device(valve)

# 获取默认控制信号
signals = control_manager.get_signals_at_time(0.0)
print(f"主闸门开度: {signals.get_signal('main_gate')}")
```

### 控制调度表

```python
# 方法1: 直接创建调度表
schedule_data = {
    'time': [0, 1800, 3600],
    'main_gate': [0.5, 0.3, 0.8],
    'drainage_pump': [0.0, 0.8, 0.2]
}
schedule = ControlSchedule(schedule_data, interpolation_method="linear")
control_manager.set_schedule(schedule)

# 方法2: 阶跃调度表
step_schedule = ControlSchedule.create_step_schedule(
    devices=['main_gate', 'drainage_pump'],
    step_times=[0, 1800, 3600],
    step_values=[
        {'main_gate': 0.5, 'drainage_pump': 0.0},
        {'main_gate': 0.3, 'drainage_pump': 0.8},
        {'main_gate': 0.8, 'drainage_pump': 0.2}
    ]
)
```

## 📋 配置文件驱动

### YAML配置格式

```yaml
# boundary_config.yaml
boundary_conditions:
  - name: "上游流量边界"
    type: "flow_boundary"
    node_name: "upstream"
    flow_function:
      type: "time_series"
      times: [0, 1800, 3600]
      values: [30.0, 50.0, 35.0]
      interpolation: "linear"

  - name: "下游水位边界"
    type: "stage_boundary"
    node_name: "downstream"
    stage_value: 100.0

  - name: "堰流关系"
    type: "rating_curve_boundary"
    flow_node: "outlet_flow"
    stage_node: "outlet_stage"
    curve_type: "weir"
    curve_params:
      discharge_coefficient: 2.2
      reference_level: 99.0
      exponent: 1.5

control_signals:
  devices:
    - device_id: "主闸门"
      device_type: "gate"
      min_value: 0.0
      max_value: 1.0
      default_value: 0.5

  schedule:
    type: "step_schedule"
    devices: ["主闸门"]
    step_times: [0, 1800, 3600]
    step_values:
      - {"主闸门": 0.5}
      - {"主闸门": 0.3}
      - {"主闸门": 0.8}
```

### 从配置文件创建系统

```python
from waternet.models.boundary_config import create_complete_system

# 从配置文件创建完整系统
boundary_manager, control_manager = create_complete_system("boundary_config.yaml")

print(f"边界条件数量: {boundary_manager.get_boundary_condition_count()}")
print(f"控制设备数量: {control_manager.get_device_count()}")
```

## 🔧 求解器集成

### 创建边界条件求解器

```python
from waternet.models.implicit_solver import create_boundary_solver
from waternet.interfaces.hydro_model import DummyModel

# 1. 创建水力模型
models = [
    DummyModel("pipe1", "node1", "node2", k=0.8, b=0.1),
    DummyModel("pipe2", "node2", "node3", k=1.2, b=-0.05)
]

# 2. 创建边界条件
boundary_conditions = [
    FlowBoundary("upstream_bc", "node1", 50.0),
    StageBoundary("downstream_bc", "node3", 100.0)
]

# 3. 创建控制设备
control_devices = [
    create_gate_device("gate1", 0.0, 1.0, 0.6)
]

# 4. 创建集成求解器
solver = create_boundary_solver(
    models=models,
    boundary_conditions=boundary_conditions,
    control_devices=control_devices
)

# 5. 求解稳态问题
initial_conditions = {
    'H_node1': 101.0,
    'H_node2': 100.5,
    'H_node3': 100.0,
    'Q_pipe1': 40.0,
    'Q_pipe2': 38.0
}

result = solver.solve_steady_state(initial_conditions)
if result['converged']:
    print("求解成功!")
    print(f"解: {result['variables']}")
```

### 瞬态求解

```python
# 设置时间参数
time_steps = np.arange(0, 3600, 60)  # 0-1小时，步长1分钟
dt = 60.0

# 瞬态求解
results = solver.solve_time_series(
    time_steps=time_steps,
    dt=dt,
    initial_conditions=initial_conditions
)

# 分析结果
for i, result in enumerate(results[:5]):  # 显示前5个时间步
    print(f"时间 {result['time']:4.0f}s: 收敛={result['converged']}, "
          f"迭代={result['statistics'].total_iterations}")
```

## ⚡ 性能优化

### 稀疏矩阵优化

```python
from waternet.models.sparse_matrix import analyze_system_sparsity

# 分析系统稀疏性
sparsity_info = analyze_system_sparsity(models, variable_names)
print(f"稀疏度: {sparsity_info['sparsity_ratio']:.2%}")
print(f"推荐格式: {sparsity_info['recommended_format']}")

# 如果系统稀疏度高，可以启用稀疏矩阵优化
if sparsity_info['sparsity_ratio'] > 0.3:
    solver_config = SolverConfig(enable_sparse_matrix=True)
    solver = ImplicitSolverAgent(models, solver_config, boundary_manager, control_manager)
```

### 自适应时间步

```python
from waternet.models.adaptive_timestep import create_adaptive_controller, TimeStepStrategy

# 创建自适应时间步控制器
adaptive_controller = create_adaptive_controller(
    strategy=TimeStepStrategy.BALANCED,
    initial_dt=60.0,
    min_dt=1.0,
    max_dt=300.0
)

# 在求解循环中使用
current_time = 0.0
current_variables = initial_conditions.copy()

while current_time < 3600.0:
    dt = adaptive_controller.get_current_timestep()
    
    # 求解当前时间步
    result = solver.solve_step_with_boundaries(current_variables, dt, {}, current_time)
    
    # 调整时间步长
    new_dt, adjustment_info = adaptive_controller.adjust_timestep(result, current_variables)
    
    if result['converged']:
        current_time += dt
        current_variables = result['variables']
        print(f"时间 {current_time:6.1f}s: dt={dt:5.1f}s, {adjustment_info['reason']}")
    else:
        print(f"求解失败，减小时间步: {dt:.1f} -> {new_dt:.1f}")
```

## 🧪 高级功能

### 自定义边界条件

```python
class CustomBoundary(BoundaryCondition):
    def __init__(self, name, node_name, custom_func):
        config = BoundaryConditionConfig(name, "自定义边界条件")
        super().__init__(name, config)
        self.node_name = node_name
        self.custom_func = custom_func
    
    def get_equation(self, variables, time=0.0):
        var_name = f"Q_{self.node_name}"
        target_value = self.custom_func(time, variables)
        residual = variables[var_name] - target_value
        return f"boundary_custom_{self.node_name}", residual
    
    def get_required_variables(self):
        return [f"Q_{self.node_name}"]

# 使用自定义边界条件
def custom_flow_function(time, variables):
    # 复杂的流量计算逻辑
    base_flow = 30.0
    seasonal_factor = 1.0 + 0.3 * np.sin(2 * np.pi * time / 86400)  # 日周期
    return base_flow * seasonal_factor

custom_bc = CustomBoundary("complex_inflow", "inlet", custom_flow_function)
boundary_manager.add_boundary_condition(custom_bc)
```

### 复杂水位流量关系

```python
# 多项式水位流量关系
polynomial_params = {
    'coefficients': [0.0, 1.5, 0.02, -0.001]  # Q = 1.5*H + 0.02*H² - 0.001*H³
}
poly_bc = RatingCurveBoundary(
    "complex_outlet", "outlet_flow", "outlet_stage",
    "polynomial", polynomial_params
)

# 自定义水位流量关系
def custom_rating_curve(H):
    # 分段式水位流量关系
    if H < 99.0:
        return 0.0
    elif H < 100.0:
        return 2.0 * (H - 99.0) ** 1.5  # 堰流
    else:
        return 2.0 + 5.0 * (H - 100.0)  # 线性增长

custom_params = {'function': custom_rating_curve}
custom_rating_bc = RatingCurveBoundary(
    "custom_outlet", "outlet_flow", "outlet_stage",
    "custom", custom_params
)
```

## 📊 结果分析和可视化

### 边界条件性能分析

```python
import matplotlib.pyplot as plt

# 测试边界条件性能
test_times = np.linspace(0, 7200, 100)
residuals = []

for t in test_times:
    equations = boundary_manager.get_all_equations(test_variables, t)
    max_residual = max(abs(r) for r in equations.values())
    residuals.append(max_residual)

# 绘制残差演化
plt.figure(figsize=(10, 6))
plt.plot(test_times, residuals, linewidth=2)
plt.xlabel('时间 (s)')
plt.ylabel('最大残差')
plt.title('边界条件残差时间演化')
plt.grid(True, alpha=0.3)
plt.show()
```

### 控制信号可视化

```python
# 可视化控制信号演化
times = np.linspace(0, 7200, 100)
gate_signals = []
pump_signals = []

for t in times:
    signals = control_manager.get_signals_at_time(t)
    gate_signals.append(signals.get_signal('main_gate'))
    pump_signals.append(signals.get_signal('drainage_pump'))

plt.figure(figsize=(12, 6))
plt.plot(times, gate_signals, label='主闸门开度', linewidth=2)
plt.plot(times, pump_signals, label='排水泵功率', linewidth=2)
plt.xlabel('时间 (s)')
plt.ylabel('控制信号值')
plt.title('控制信号时间演化')
plt.legend()
plt.grid(True, alpha=0.3)
plt.show()
```

## 🐛 故障排除

### 常见问题

1. **边界条件变量不存在**
   ```python
   # 检查变量名是否正确
   required_vars = boundary_manager.get_all_required_variables()
   missing_vars = [var for var in required_vars if var not in variables]
   if missing_vars:
       print(f"缺少变量: {missing_vars}")
   ```

2. **控制信号超出范围**
   ```python
   # 检查控制信号约束
   signals = control_manager.get_signals_at_time(t)
   if not signals.validate_signals(control_manager.devices):
       print("控制信号验证失败")
   ```

3. **求解器收敛问题**
   ```python
   # 使用更宽松的收敛条件
   solver_config = SolverConfig(
       tolerance=1e-4,  # 放宽容差
       max_iterations=100,  # 增加最大迭代次数
       relaxation_factor=0.8  # 使用松弛因子
   )
   ```

### 调试技巧

```python
# 开启详细日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 验证边界条件配置
validator = ConfigValidator()
is_valid = validator.validate_boundary_config(config_data)
if not is_valid:
    print("配置验证错误:")
    for error in validator.errors:
        print(f"  - {error}")

# 检查求解器状态
result = solver.solve_steady_state(initial_conditions)
if not result['converged']:
    print(f"求解失败原因: {result['statistics'].failure_reason}")
    print(f"最终残差: {result['statistics'].final_residual_norm}")
```

## 📚 更多示例

完整的演示案例请参考：
- `examples/boundary_framework_demo.py` - 综合演示脚本
- `tests/test_boundary_framework.py` - 单元测试用例
- `configs/boundary_conditions_example.yaml` - 配置文件示例

通过这些示例，您可以快速上手WaterNet边界条件框架，构建复杂的水力网络仿真系统。