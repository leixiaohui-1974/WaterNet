# API参考

<cite>
**本文档中引用的文件**   
- [hydro_model.py](file://waternet/interfaces/hydro_model.py)
- [saint_venant.py](file://waternet/models/saint_venant.py)
- [lumped_models.py](file://waternet/models/lumped_models.py)
- [estimator.py](file://waternet/parameter_estimation/estimator.py)
- [twinning_harness.py](file://waternet/coordination/twinning_harness.py)
- [standard_five_section.py](file://waternet/config/standard_five_section.py)
</cite>

## 目录
1. [HydroModel接口](#hydroModel接口)
2. [SaintVenantModel实现](#saintVenantModel实现)
3. [BaseLumpedModel继承体系](#baseLumpedModel继承体系)
4. [ParameterEstimator参数估计器](#parameterEstimator参数估计器)
5. [SynchronizedTwinningHarness协调器](#synchronizedTwinningHarness协调器)
6. [StandardFiveSectionConfig配置类](#standardFiveSectionConfig配置类)

## HydroModel接口

`HydroModel` 是所有紧耦合水力模型的基础抽象接口，定义了统一的模型交互规范。

### HydroModel.__init__
初始化水力模型。

**方法签名**
```python
def __init__(self, name: str, node_names: List[str])
```

**参数说明**
- `name` (str): 模型唯一标识符，在系统中必须唯一
- `node_names` (List[str]): 模型连接的边界节点名称列表，通常包含上游节点和下游节点

**异常抛出**
- `ValueError`: 当name为空或node_names为空时

**使用示例**
```python
# 创建一个水力模型实例
model = HydroModel(name="Channel1", node_names=["UpstreamNode", "DownstreamNode"])
```

**Section sources**
- [hydro_model.py](file://waternet/interfaces/hydro_model.py#L41-L64)

### HydroModel.node_names
获取模型连接的节点名称列表。

**方法签名**
```python
@property
def node_names(self) -> List[str]
```

**返回值类型**
- `List[str]`: 节点名称列表的副本（只读）

**使用示例**
```python
# 获取模型的节点名称
nodes = model.node_names
print(f"模型连接的节点: {nodes}")
```

**Section sources**
- [hydro_model.py](file://waternet/interfaces/hydro_model.py#L67-L74)

### HydroModel.get_equations
获取模型方程的残差。这是核心接口方法，用于计算模型在当前变量值下的方程残差。

**方法签名**
```python
@abstractmethod
def get_equations(self, variables: Dict[str, float], dt: float, prev_states: Dict[str, float]) -> Dict[str, float]
```

**参数说明**
- `variables` (Dict[str, float]): 当前时步的所有变量值，格式: {'H_Node1': 100.5, 'Q_Pipe1': 1.0, ...}
- `dt` (float): 时间步长（秒）
- `prev_states` (Dict[str, float]): 上一时步的状态值，格式: {'V_Reservoir1': 50000, 'H_Node1': 99.8, ...}

**返回值类型**
- `Dict[str, float]`: 方程残差字典，格式: {'方程名': 残差值, ...}

**使用示例**
```python
# 计算模型方程残差
equations = model.get_equations(variables, dt, prev_states)
for eq_name, residual in equations.items():
    print(f"{eq_name}: {residual}")
```

**Section sources**
- [hydro_model.py](file://waternet/interfaces/hydro_model.py#L77-L116)

### HydroModel.get_variable_names
获取模型引入的变量名列表。

**方法签名**
```python
@abstractmethod  
def get_variable_names(self) -> List[str]
```

**返回值类型**
- `List[str]`: 变量名称列表，例如: ['Q_TestChannel_seg_0', 'H_TestChannel_internal_0']

**使用示例**
```python
# 获取模型变量名
var_names = model.get_variable_names()
print(f"模型变量: {var_names}")
```

**Section sources**
- [hydro_model.py](file://waternet/interfaces/hydro_model.py#L119-L139)

### HydroModel.validate_interface
验证接口实现的正确性。

**方法签名**
```python
def validate_interface(self, variables: Dict[str, float], dt: float, prev_states: Dict[str, float]) -> bool
```

**参数说明**
- `variables` (Dict[str, float]): 测试用的变量字典
- `dt` (float): 测试用的时间步长
- `prev_states` (Dict[str, float]): 测试用的状态字典

**返回值类型**
- `bool`: True表示接口实现正确，False表示存在问题

**异常抛出**
- `ValueError`: 当检测到接口实现错误时

**使用示例**
```python
# 验证模型接口实现
is_valid = model.validate_interface(test_variables, test_dt, test_states)
if is_valid:
    print("模型接口实现正确")
else:
    print("模型接口存在问题")
```

**Section sources**
- [hydro_model.py](file://waternet/interfaces/hydro_model.py#L141-L190)

### HydroModel.__repr__
获取模型的字符串表示。

**方法签名**
```python
def __repr__(self) -> str
```

**返回值类型**
- `str`: 模型的字符串表示

**使用示例**
```python
# 获取模型的字符串表示
print(repr(model))
```

**Section sources**
- [hydro_model.py](file://waternet/interfaces/hydro_model.py#L192-L194)

### HydroModel.__str__
获取模型的可读字符串表示。

**方法签名**
```python
def __str__(self) -> str
```

**返回值类型**
- `str`: 模型的可读字符串表示

**使用示例**
```python
# 打印模型信息
print(model)
```

**Section sources**
- [hydro_model.py](file://waternet/interfaces/hydro_model.py#L196-L198)

## SaintVenantModel实现

`SaintVenantModel` 是基于圣维南方程组的一维明渠非恒定流模型，实现了完整的物理水力学方程。

### SaintVenantModel.__init__
初始化圣维南模型。

**方法签名**
```python
def __init__(self, name: str, upstream_node: str, downstream_node: str, sections: List[Dict[str, Any]], solver_type: str = "standard", enable_performance_monitoring: bool = False)
```

**参数说明**
- `name` (str): 模型唯一标识符
- `upstream_node` (str): 上游边界节点名称
- `downstream_node` (str): 下游边界节点名称
- `sections` (List[Dict]): 断面几何数据列表，每个元素包含：mileage, elevation, roughness, area_func, top_width_func
- `solver_type` (str): 求解器类型 ('standard' 或 'enhanced')
- `enable_performance_monitoring` (bool): 是否启用性能监控

**异常抛出**
- `ValueError`: 当断面数据不足或格式错误时

**使用示例**
```python
# 定义断面几何数据
sections = [
    {
        'mileage': 0.0,
        'elevation': 100.0,
        'roughness': 0.025,
        'area_func': lambda H: (H - 100.0) * 10.0,
        'top_width_func': lambda H: 10.0
    },
    {
        'mileage': 1000.0,
        'elevation': 99.0,
        'roughness': 0.025,
        'area_func': lambda H: (H - 99.0) * 12.0,
        'top_width_func': lambda H: 12.0
    }
]

# 创建圣维南模型
model = SaintVenantModel(
    name="Channel1",
    upstream_node="UpNode",
    downstream_node="DownNode",
    sections=sections,
    solver_type="standard"
)
```

**Section sources**
- [saint_venant.py](file://waternet/models/saint_venant.py#L60-L122)

### SaintVenantModel.compute_steady_state
计算恒定流水面线。

**方法签名**
```python
def compute_steady_state(self, Q: float, downstream_H: float) -> Dict[str, float]
```

**参数说明**
- `Q` (float): 恒定流量（m³/s）
- `downstream_H` (float): 下游边界水位（m）

**返回值类型**
- `Dict[str, float]`: 计算结果字典，包含所有断面水位、分段流量和总蓄水量

**异常抛出**
- `ValueError`: 当边界条件不合理或计算不收敛时

**使用示例**
```python
# 计算恒定流水面线
result = model.compute_steady_state(Q=50.0, downstream_H=101.0)
print(f"总蓄水量: {result['total_volume']} m³")
for i in range(len(model.sections)):
    print(f"断面{i}水位: {result[f'H_section_{i}']} m")
```

**Section sources**
- [saint_venant.py](file://waternet/models/saint_venant.py#L183-L245)

### SaintVenantModel.get_equations
构建圣维南方程组的残差。

**方法签名**
```python
def get_equations(self, variables: Dict[str, float], dt: float, prev_states: Dict[str, float]) -> Dict[str, float]
```

**参数说明**
- `variables` (Dict[str, float]): 当前时步变量值
- `dt` (float): 时间步长（秒）
- `prev_states` (Dict[str, float]): 上一时步状态

**返回值类型**
- `Dict[str, float]`: 方程残差字典

**使用示例**
```python
# 构建方程残差
equations = model.get_equations(current_vars, dt, prev_states)
print(f"连续性方程残差: {equations['continuity_seg_0']}")
print(f"动量方程残差: {equations['momentum_seg_0']}")
```

**Section sources**
- [saint_venant.py](file://waternet/models/saint_venant.py#L357-L454)

### SaintVenantModel.get_variable_names
获取模型变量名列表。

**方法签名**
```python
def get_variable_names(self) -> List[str]
```

**返回值类型**
- `List[str]`: 变量名列表，包括分段流量变量和内部节点水位变量

**使用示例**
```python
# 获取模型变量名
var_names = model.get_variable_names()
print(f"模型变量: {var_names}")
```

**Section sources**
- [saint_venant.py](file://waternet/models/saint_venant.py#L505-L526)

### SaintVenantModel.summary
返回模型的摘要信息。

**方法签名**
```python
def summary(self) -> str
```

**返回值类型**
- `str`: 模型摘要信息

**使用示例**
```python
# 打印模型摘要
print(model.summary())
```

**Section sources**
- [saint_venant.py](file://waternet/models/saint_venant.py#L558-L584)

### SaintVenantModel.create_enhanced_solver
创建增强型求解器。

**方法签名**
```python
def create_enhanced_solver(self, numerical_config=None, stability_config=None)
```

**参数说明**
- `numerical_config`: 数值格式配置
- `stability_config`: 稳定性控制配置

**返回值类型**
- `EnhancedSaintVenantSolver`: 增强型求解器实例，如果不可用则返回None

**使用示例**
```python
# 创建增强型求解器
solver = model.create_enhanced_solver()
if solver:
    print("增强型求解器创建成功")
else:
    print("增强型求解器不可用")
```

**Section sources**
- [saint_venant.py](file://waternet/models/saint_venant.py#L586-L607)

### SaintVenantModel.solve_with_enhanced_solver
使用增强型求解器进行非恒定流计算。

**方法签名**
```python
def solve_with_enhanced_solver(self, initial_flow: float, downstream_H: float, Q_in_series: List[float], H_down_series: List[float], dt: float = 60.0) -> Dict[str, Any]
```

**参数说明**
- `initial_flow` (float): 初始流量
- `downstream_H` (float): 初始下游水位
- `Q_in_series` (List[float]): 上游入流序列
- `H_down_series` (List[float]): 下游水位序列
- `dt` (float): 时间步长

**返回值类型**
- `Dict[str, Any]`: 求解结果

**使用示例**
```python
# 使用增强型求解器进行计算
results = model.solve_with_enhanced_solver(
    initial_flow=50.0,
    downstream_H=101.0,
    Q_in_series=[50.0, 60.0, 70.0, 60.0, 50.0],
    H_down_series=[101.0, 101.0, 101.0, 101.0, 101.0],
    dt=60.0
)
print(f"计算成功: {results['success']}")
```

**Section sources**
- [saint_venant.py](file://waternet/models/saint_venant.py#L609-L646)

## BaseLumpedModel继承体系

`BaseLumpedModel` 是所有集总参数降阶模型的抽象基类，为所有降阶模型提供统一的接口和通用功能。

### BaseLumpedModel.__init__
初始化降阶模型基类。

**方法签名**
```python
def __init__(self, dt: float, initial_V: float, V_to_H_func: Callable[[float], float], H_to_Q_func: Callable[[float], float], name: str = "LumpedModel", QH_to_V_func: Optional[Callable[[float, float], float]] = None)
```

**参数说明**
- `dt` (float): 时间步长（秒），必须为正值
- `initial_V` (float): 初始蓄水量（m³），必须为非负值
- `V_to_H_func` (Callable): 蓄量转换为水位的函数 H = f(V)
- `H_to_Q_func` (Callable): 水位转换为出流的函数 Q = f(H)
- `name` (str): 模型名称，用于标识和调试
- `QH_to_V_func` (Optional[Callable]): 流量水位耦合的蓄量函数 V = f(Q, H)

**异常抛出**
- `ValueError`: 当参数不合理时

**使用示例**
```python
# 定义物理关系函数
def V_to_H(V):
    return 100.0 + V / 10000.0

def H_to_Q(H):
    return max(0.0, (H - 100.0) * 10.0)

# 创建降阶模型
model = BaseLumpedModel(
    dt=60.0,
    initial_V=10000.0,
    V_to_H_func=V_to_H,
    H_to_Q_func=H_to_Q,
    name="StorageModel"
)
```

**Section sources**
- [lumped_models.py](file://waternet/models/lumped_models.py#L61-L124)

### BaseLumpedModel.step
执行一个时间步的仿真。

**方法签名**
```python
@abstractmethod
def step(self, Q_in: float) -> Dict[str, float]
```

**参数说明**
- `Q_in` (float): 当前时步的入流量（m³/s）

**返回值类型**
- `Dict[str, float]`: 仿真结果字典，至少包含 'Q_out', 'H_out', 'V', 'time'

**使用示例**
```python
# 执行一步仿真
result = model.step(Q_in=50.0)
print(f"出流量: {result['Q_out']} m³/s")
print(f"水位: {result['H_out']} m")
```

**Section sources**
- [lumped_models.py](file://waternet/models/lumped_models.py#L211-L234)

### BaseLumpedModel.run_simulation
运行完整的仿真序列。

**方法签名**
```python
def run_simulation(self, Q_in_series: Union[List[float], np.ndarray], record_interval: int = 1) -> pd.DataFrame
```

**参数说明**
- `Q_in_series` (Union[List, np.ndarray]): 入流时间序列
- `record_interval` (int): 记录间隔（每多少步记录一次）

**返回值类型**
- `pd.DataFrame`: 仿真结果数据框

**使用示例**
```python
# 运行完整仿真
Q_in_series = [50.0, 60.0, 70.0, 60.0, 50.0]
results_df = model.run_simulation(Q_in_series, record_interval=1)
print(results_df[['time', 'Q_in', 'Q_out', 'H_out']])
```

**Section sources**
- [lumped_models.py](file://waternet/models/lumped_models.py#L300-L358)

### BaseLumpedModel.reset
重置模型到初始状态。

**方法签名**
```python
def reset(self, new_initial_V: Optional[float] = None)
```

**参数说明**
- `new_initial_V` (Optional[float]): 新的初始蓄水量，如果为None则使用原初始值

**使用示例**
```python
# 重置模型状态
model.reset(new_initial_V=15000.0)
print("模型已重置")
```

**Section sources**
- [lumped_models.py](file://waternet/models/lumped_models.py#L360-L386)

### BaseLumpedModel.summary
返回模型摘要信息。

**方法签名**
```python
def summary(self) -> str
```

**返回值类型**
- `str`: 模型摘要

**使用示例**
```python
# 打印模型摘要
print(model.summary())
```

**Section sources**
- [lumped_models.py](file://waternet/models/lumped_models.py#L492-L511)

### BaseLumpedModel.get_current_state
获取当前状态。

**方法签名**
```python
def get_current_state(self) -> Dict[str, float]
```

**返回值类型**
- `Dict[str, float]`: 当前状态字典

**使用示例**
```python
# 获取当前状态
current_state = model.get_current_state()
print(f"当前时间: {current_state['time']} s")
print(f"当前蓄水量: {current_state['V']} m³")
```

**Section sources**
- [lumped_models.py](file://waternet/models/lumped_models.py#L388-L400)

### BaseLumpedModel.create_enhanced_version
创建当前模型的增强版本。

**方法签名**
```python
def create_enhanced_version(self, **kwargs)
```

**参数说明**
- `**kwargs`: 增强功能参数

**返回值类型**
- `Enhanced model instance`: 增强模型实例，如果不可用则返回None

**使用示例**
```python
# 创建增强版本
enhanced_model = model.create_enhanced_version()
if enhanced_model:
    print("增强版本创建成功")
else:
    print("增强版本不可用")
```

**Section sources**
- [lumped_models.py](file://waternet/models/lumped_models.py#L411-L448)

## ParameterEstimator参数估计器

`ParameterEstimator` 是基于高精度圣维南模型的参数辨识算法，为降阶模型提供精确的参数标定和在线校正功能。

### ParameterEstimator.__init__
初始化参数估计器。

**方法签名**
```python
def __init__(self, saint_venant_model: SaintVenantModel)
```

**参数说明**
- `saint_venant_model` (SaintVenantModel): 作为基准的圣维南模型

**异常抛出**
- `TypeError`: 当需要SaintVenantModel类型的基准模型时

**使用示例**
```python
# 创建参数估计器
estimator = ParameterEstimator(saint_venant_model=model)
```

**Section sources**
- [estimator.py](file://waternet/parameter_estimation/estimator.py#L32-L53)

### ParameterEstimator.identify_static_curves
辨识静态特征曲线。

**方法签名**
```python
def identify_static_curves(self, Q_range: np.ndarray, H_down_range: np.ndarray, curve_types: List[str] = ['V_H', 'Q_H'], poly_orders: List[int] = [2, 3, 4]) -> Dict[str, Any]
```

**参数说明**
- `Q_range` (np.ndarray): 流量测试范围 [m³/s]
- `H_down_range` (np.ndarray): 下游水位测试范围 [m]
- `curve_types` (List[str]): 需要拟合的曲线类型
- `poly_orders` (List[int]): 多项式拟合阶数范围

**返回值类型**
- `Dict[str, Any]`: 静态曲线拟合结果

**异常抛出**
- `ValueError`: 当测试点数量不足或流量范围非正值时

**使用示例**
```python
# 辨识静态特征曲线
Q_range = np.linspace(10.0, 100.0, 10)
H_down_range = np.linspace(100.0, 102.0, 5)
static_curves = estimator.identify_static_curves(Q_range, H_down_range)
print(f"最佳V-H关系阶数: {static_curves['best_orders']['V_H']}")
```

**Section sources**
- [estimator.py](file://waternet/parameter_estimation/estimator.py#L55-L107)

### ParameterEstimator.identify_dynamic_parameters
辨识动态模型参数。

**方法签名**
```python
def identify_dynamic_parameters(self, unsteady_data: Dict[str, Any], model_class: Type[BaseLumpedModel], parameter_bounds: Optional[Dict[str, Tuple[float, float]]] = None) -> Dict[str, Any]
```

**参数说明**
- `unsteady_data` (Dict[str, Any]): 非恒定流数据
- `model_class` (Type[BaseLumpedModel]): 待标定的降阶模型类型
- `parameter_bounds` (Optional[Dict]): 参数搜索边界

**返回值类型**
- `Dict[str, Any]`: 参数辨识结果

**异常抛出**
- `ValueError`: 当缺少必需的数据字段时

**使用示例**
```python
# 辨识动态参数
unsteady_data = {
    'Q_in': [50.0, 60.0, 70.0, 60.0, 50.0],
    'H_down': [101.0, 101.0, 101.0, 101.0, 101.0],
    'dt': 60.0
}
result = estimator.identify_dynamic_parameters(
    unsteady_data, 
    MuskingumModel,
    parameter_bounds={'K': (500.0, 2000.0), 'x': (0.1, 0.4)}
)
print(f"最佳参数: {result['best_parameters']}")
```

**Section sources**
- [estimator.py](file://waternet/parameter_estimation/estimator.py#L262-L296)

## SynchronizedTwinningHarness协调器

`SynchronizedTwinningHarness` 是同步孪生协调器，管理精细化模型与降阶模型的同步运行，实现数字孪生系统的核心协调功能。

### SynchronizedTwinningHarness.__init__
初始化同步孪生协调器。

**方法签名**
```python
def __init__(self, saint_venant_model: SaintVenantModel, reduced_order_model: BaseLumpedModel, correction_interval: int = 10, correction_threshold: float = 0.1)
```

**参数说明**
- `saint_venant_model` (SaintVenantModel): 精细化物理模型
- `reduced_order_model` (BaseLumpedModel): 降阶模型
- `correction_interval` (int): 校正间隔（时间步数）
- `correction_threshold` (float): 触发校正的误差阈值

**异常抛出**
- `TypeError`: 当模型类型不正确时

**使用示例**
```python
# 创建同步孪生协调器
harness = SynchronizedTwinningHarness(
    saint_venant_model=sv_model,
    reduced_order_model=lumped_model,
    correction_interval=20,
    correction_threshold=0.15
)
```

**Section sources**
- [twinning_harness.py](file://waternet/coordination/twinning_harness.py#L49-L96)

### SynchronizedTwinningHarness.run_synchronized_simulation
运行同步孪生仿真。

**方法签名**
```python
def run_synchronized_simulation(self, Q_in_series: Union[List[float], np.ndarray], H_down_series: Union[List[float], np.ndarray], dt: float, enable_correction: bool = True) -> pd.DataFrame
```

**参数说明**
- `Q_in_series` (Union[List, np.ndarray]): 入流时间序列
- `H_down_series` (Union[List, np.ndarray]): 下游水位序列
- `dt` (float): 时间步长（秒）
- `enable_correction` (bool): 是否启用在线校正

**返回值类型**
- `pd.DataFrame`: 同步仿真结果数据框

**异常抛出**
- `ValueError`: 当输入序列长度不匹配或为空时

**使用示例**
```python
# 运行同步孪生仿真
Q_in_series = [50.0, 60.0, 70.0, 60.0, 50.0]
H_down_series = [101.0, 101.0, 101.0, 101.0, 101.0]
results = harness.run_synchronized_simulation(
    Q_in_series=Q_in_series,
    H_down_series=H_down_series,
    dt=60.0,
    enable_correction=True
)
print(f"仿真完成，性能指标: {harness.get_performance_summary()}")
```

**Section sources**
- [twinning_harness.py](file://waternet/coordination/twinning_harness.py#L98-L161)

### SynchronizedTwinningHarness.run_simulation
运行孪生仿真（为兼容性提供的简化接口）。

**方法签名**
```python
def run_simulation(self, Q_in_series: Union[List[float], np.ndarray], dt: float, H_down_series: Optional[Union[List[float], np.ndarray]] = None, enable_correction: bool = True) -> List[Dict[str, Any]]
```

**参数说明**
- `Q_in_series` (Union[List, np.ndarray]): 入流时间序列
- `dt` (float): 时间步长（秒）
- `H_down_series` (Optional[Union[List, np.ndarray]]): 下游水位序列
- `enable_correction` (bool): 是否启用在线校正

**返回值类型**
- `List[Dict[str, Any]]`: 仿真结果列表

**使用示例**
```python
# 运行简化接口的仿真
results = harness.run_simulation(
    Q_in_series=[50.0, 60.0, 70.0],
    dt=60.0,
    enable_correction=True
)
for result in results:
    print(f"时间: {result['time']}, HF出流: {result['hf_Q_out']}, ROM出流: {result['rom_Q_out']}")
```

**Section sources**
- [twinning_harness.py](file://waternet/coordination/twinning_harness.py#L163-L207)

### SynchronizedTwinningHarness.get_performance_summary
获取性能摘要。

**方法签名**
```python
def get_performance_summary(self) -> Dict[str, Any]
```

**返回值类型**
- `Dict[str, Any]`: 性能摘要

**使用示例**
```python
# 获取性能摘要
summary = harness.get_performance_summary()
print(f"流量RMSE: {summary['总体性能']['rmse_Q']:.4f} m³/s")
print(f"相关系数: {summary['总体性能']['correlation_Q']:.3f}")
```

**Section sources**
- [twinning_harness.py](file://waternet/coordination/twinning_harness.py#L459-L476)

### SynchronizedTwinningHarness.reset
重置协调器状态。

**方法签名**
```python
def reset(self)
```

**使用示例**
```python
# 重置协调器
harness.reset()
print("协调器状态已重置")
```

**Section sources**
- [twinning_harness.py](file://waternet/coordination/twinning_harness.py#L478-L488)

## StandardFiveSectionConfig配置类

`StandardFiveSectionConfig` 是标准五断面配置管理器，提供统一的标准五断面配置，替代项目中的重复实现。

### StandardFiveSectionConfig.__init__
初始化配置管理器。

**方法签名**
```python
def __init__(self, variant: str = "standard")
```

**参数说明**
- `variant` (str): 配置变体 ("standard", "steep", "mild", "complex")

**异常抛出**
- `ValueError`: 当不支持的配置变体时

**使用示例**
```python
# 创建标准配置
config = StandardFiveSectionConfig(variant="standard")

# 创建陡坡配置
steep_config = StandardFiveSectionConfig(variant="steep")

# 创建缓坡配置
mild_config = StandardFiveSectionConfig(variant="mild")
```

**Section sources**
- [standard_five_section.py](file://waternet/config/standard_five_section.py#L157-L170)

### StandardFiveSectionConfig.get_five_section_geometry
获取五断面几何数据（兼容现有接口）。

**方法签名**
```python
def get_five_section_geometry(self) -> List[Dict[str, Any]]
```

**返回值类型**
- `List[Dict]`: 包含所有水力函数的断面数据列表

**使用示例**
```python
# 获取五断面几何数据
geometry = config.get_five_section_geometry()
for i, section in enumerate(geometry):
    print(f"断面{i}里程: {section['mileage']} m")
    print(f"断面{i}底高程: {section['elevation']} m")
    # 可以直接使用水力函数
    area = section['area_func'](101.0)
    print(f"水位101.0m时面积: {area} m²")
```

**Section sources**
- [standard_five_section.py](file://waternet/config/standard_five_section.py#L295-L321)

### StandardFiveSectionConfig.compute_steady_state_profile
计算恒定流水面线（兼容现有接口）。

**方法签名**
```python
def compute_steady_state_profile(self, Q: float = None, H_downstream: float = None) -> Dict[str, Any]
```

**参数说明**
- `Q` (float): 流量，None则使用默认值
- `H_downstream` (float): 下游水位，None则使用默认值

**返回值类型**
- `Dict`: 包含水面线计算结果

**使用示例**
```python
# 计算恒定流水面线
profile = config.compute_steady_state_profile(Q=50.0, H_downstream=101.0)
print(f"总蓄水量: {profile['total_volume']} m³")
for section in profile['sections']:
    print(f"里程{section['mileage']}m: 水位{section['water_level']}m, 流速{section['velocity']:.2f}m/s")
```

**Section sources**
- [standard_five_section.py](file://waternet/config/standard_five_section.py#L323-L396)

### StandardFiveSectionConfig.create_saint_venant_sections
创建适用于SaintVenantModel的断面数据。

**方法签名**
```python
def create_saint_venant_sections(self) -> List[Dict[str, Any]]
```

**返回值类型**
- `List[Dict]`: 圣维南模型所需的断面数据格式

**使用示例**
```python
# 创建圣维南模型可用的断面数据
sv_sections = config.create_saint_venant_sections()
# 可以直接用于创建SaintVenantModel
sv_model = SaintVenantModel(
    name="Channel",
    upstream_node="UpNode",
    downstream_node="DownNode",
    sections=sv_sections
)
```

**Section sources**
- [standard_five_section.py](file://waternet/config/standard_five_section.py#L456-L475)

### StandardFiveSectionConfig.export_to_yaml
导出配置到YAML文件。

**方法签名**
```python
def export_to_yaml(self, file_path: str) -> bool
```

**参数说明**
- `file_path` (str): 输出文件路径

**返回值类型**
- `bool`: True表示导出成功

**使用示例**
```python
# 导出配置到文件
success = config.export_to_yaml("channel_config.yaml")
if success:
    print("配置已成功导出")
else:
    print("配置导出失败")
```

**Section sources**
- [standard_five_section.py](file://waternet/config/standard_five_section.py#L477-L509)

### StandardFiveSectionConfig.load_from_yaml
从YAML文件加载配置。

**方法签名**
```python
@classmethod
def load_from_yaml(cls, file_path: str) -> 'StandardFiveSectionConfig'
```

**参数说明**
- `file_path` (str): 输入文件路径

**返回值类型**
- `StandardFiveSectionConfig`: 配置管理器实例

**异常抛出**
- `Exception`: 当配置加载失败时

**使用示例**
```python
# 从文件加载配置
loaded_config = StandardFiveSectionConfig.load_from_yaml("channel_config.yaml")
print("配置已从文件加载")
```

**Section sources**
- [standard_five_section.py](file://waternet/config/standard_five_section.py#L512-L550)

### StandardFiveSectionConfig.validate_configuration
验证配置的完整性和合理性。

**方法签名**
```python
def validate_configuration(self) -> Dict[str, Any]
```

**返回值类型**
- `Dict[str, Any]`: 验证结果，包含是否有效、警告、错误和统计信息

**使用示例**
```python
# 验证配置
validation = config.validate_configuration()
if validation['is_valid']:
    print("配置有效")
else:
    print("配置存在问题:")
    for error in validation['errors']:
        print(f"  - {error}")
```

**Section sources**
- [standard_five_section.py](file://waternet/config/standard_five_section.py#L552-L614)

### StandardFiveSectionConfig.get_configuration_summary
获取配置摘要信息。

**方法签名**
```python
def get_configuration_summary(self) -> str
```

**返回值类型**
- `str`: 配置摘要信息

**使用示例**
```python
# 打印配置摘要
print(config.get_configuration_summary())
```

**Section sources**
- [standard_five_section.py](file://waternet/config/standard_five_section.py#L616-L658)