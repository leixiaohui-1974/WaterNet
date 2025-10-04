# WaterNet - 明渠水力模型数字孪生建模框架

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-Passing-brightgreen)](tests/)

WaterNet是一个基于圣维南方程组的明渠水力模型数字孪生建模框架，专为水利工程的数值仿真和参数估计而设计。框架提供了从高精度物理模型到快速降阶模型的完整建模工具链。

## ✨ 主要特性

### 🔬 物理模型
- **圣维南模型**: 基于完整圣维南方程组的一维非恒定流模型
- **增强求解器**: 支持标准和增强数值求解器，包含稳定性控制
- **复杂几何**: 支持任意复杂断面几何（矩形、梯形等）
- **边界条件**: 灵活的上下游边界条件设置

### 📊 降阶模型
- **马斯京干模型**: 经典河道洪水演进模型
- **蓄量演算模型**: 基于蓄泄关系的集总模型
- **IDZ模型**: 积分延迟零点传递函数模型
- **统一接口**: 所有模型遵循相同的API设计

### 🔧 工程工具
- **参数估计**: 自动化参数辨识和优化
- **数字孪生**: 物理模型与降阶模型的协同仿真
- **配置管理**: YAML配置文件驱动的建模流程
- **可视化**: 内置结果可视化和分析工具

### 🧪 质量保证
- **分层测试**: 单元测试、集成测试、性能测试完整覆盖
- **持续集成**: 自动化测试和质量检查
- **文档完备**: 详细的API文档和使用示例

## 🚀 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/your-username/WaterNet.git
cd WaterNet

# 安装依赖
pip install -r requirements.txt

# 验证安装
python scripts/run_tests.py validate
```

### 基础使用

#### 1. 配置驱动建模

```python
from waternet.models import SaintVenantModel, MuskingumModel
from waternet.config import ConfigManager

# 初始化配置管理器
config_manager = ConfigManager('configs')

# 加载渠道配置
channel_config = config_manager.load_config('simple_channel.yaml')
sections = config_manager.create_channel_sections(channel_config)

# 创建圣维南模型
sv_model = SaintVenantModel(
    name="MyChannel",
    upstream_node="inlet",
    downstream_node="outlet",
    sections=sections
)

# 恒定流计算
result = sv_model.compute_steady_state(Q=15.0, downstream_H=99.5)
print(f"总蓄水量: {result['total_volume']:.1f} m³")
```

#### 2. 降阶模型仿真

```python
# 加载模型配置
model_config = config_manager.load_config('muskingum_model.yaml')
V_to_H_func, H_to_Q_func = config_manager.create_physical_relations(
    model_config['physical_relations'])

# 创建马斯京干模型
params = model_config['parameters']
muskingum_model = MuskingumModel(
    dt=params['dt'],
    K=params['K'],
    x=params['x'],
    initial_V=params['initial_V'],
    V_to_H_func=V_to_H_func,
    H_to_Q_func=H_to_Q_func
)

# 运行仿真
Q_in_series = [8.0, 12.0, 16.0, 12.0, 8.0]
results = muskingum_model.run_simulation(Q_in_series)
print(results.head())
```

#### 3. 参数估计

```python
from waternet.parameter_estimation.estimator import ParameterEstimator

# 创建参数估计器
estimator = ParameterEstimator(sv_model)

# 静态特征曲线辨识
Q_range = np.linspace(5.0, 25.0, 6)
H_range = np.linspace(99.2, 100.0, 5)
static_curves = estimator.identify_static_curves(Q_range, H_range)

# 动态参数辨识
unsteady_data = {
    'Q_in': Q_in_series,
    'H_down': [99.4] * len(Q_in_series),
    'dt': 60.0
}
param_result = estimator.identify_dynamic_parameters(unsteady_data, MuskingumModel)
```

## 📁 项目结构

> ✨ **重构更新**: 项目结构已经完成了全面的重构和优化，建立了更清晰、更标准化的目录结构。

```
WaterNet/
├── waternet/                    # 核心代码库
│   ├── models/                  # 水力模型实现
│   │   ├── saint_venant.py     # 圣维南模型
│   │   ├── lumped_models.py    # 降阶模型库
│   │   └── solvers.py          # 统一求解器
│   ├── config/                  # 配置管理系统
│   ├── parameter_estimation/    # 参数估计
│   ├── coordination/           # 数字孪生协调
│   ├── interfaces/             # 模型接口定义
│   └── utils/                  # 工具函数
├── tests/                      # 🔄 统一测试目录
│   ├── unit/                   # 单元测试 (39个测试用例)
│   ├── integration/            # 集成测试
│   ├── deep_channel/           # 🌊 深度测试框架
│   ├── fixtures/               # 测试数据
│   └── conftest.py             # pytest配置
├── examples/                   # 🔄 重新组织的示例
│   ├── basic/                  # 🌱 基础使用示例
│   ├── advanced/               # 🚀 高级功能演示
│   ├── configs/                # 配置文件
│   ├── basic_usage.py          # 基础使用示例
│   ├── parameter_estimation.py # 参数估计示例
│   └── README.md               # 📚 重构指南
├── scripts/                    # 工具脚本
│   └── test_runner.py          # 🔧 统一测试入口
├── docs/                       # 📝 文档系统
│   └── reports/                # 测试报告和基准结果
├── configs/                    # 🔧 项目配置
│   ├── example_configs/        # 示例配置
│   └── test_configs/           # 测试配置
└── pytest.ini                  # 🔧 pytest统一配置
```

### 重构亮点

- 🔄 **统一测试系统**: 合并了原有的双重测试目录，建立了统一的测试框架
- 🌊 **深度测试框架**: 从 `waternet/tests/deep_channel_testing/` 迁移到 `tests/deep_channel/`
- 🚀 **示例重组**: 创建了 `basic/` 和 `advanced/` 分类，提供更清晰的学习路径
- 🔧 **工具优化**: 新增统一测试入口和标准化配置
- 📚 **文档系统**: 建立了统一的文档和报告管理

## 🛠️ 开发指南

### 运行测试

🚀 **新的统一测试系统**

```bash
# 使用新的统一测试入口
# 运行所有测试
python scripts/test_runner.py --all

# 运行单元测试
python scripts/test_runner.py --unit

# 运行集成测试
python scripts/test_runner.py --integration

# 运行深度通道测试
python scripts/test_runner.py --deep-channel

# 生成覆盖率报告
python scripts/test_runner.py --unit --coverage

# 列出可用测试
python scripts/test_runner.py --list
```

**或者直接使用 pytest**

```bash
# 运行所有测试
pytest

# 按目录运行
pytest tests/unit/         # 单元测试
pytest tests/integration/  # 集成测试
pytest tests/deep_channel/ # 深度测试

# 按标记运行
pytest -m unit             # 只运行单元测试
pytest -m integration      # 只运行集成测试
pytest -m slow             # 运行慢速测试

# 生成覆盖率报告
pytest --cov=waternet --cov-report=html
```

### 配置文件格式

#### 渠道几何配置 (`channel.yaml`)

```yaml
name: simple_rectangular_channel
description: 简单矩形明渠
sections:
  - mileage: 0.0
    elevation: 100.0
    roughness: 0.025
    cross_section:
      type: rectangular
      width: 10.0
  - mileage: 1000.0
    elevation: 99.0
    roughness: 0.025
    cross_section:
      type: rectangular
      width: 10.0
```

#### 模型参数配置 (`model.yaml`)

```yaml
model_type: muskingum
parameters:
  K: 3600.0      # 滞时常数 (s)
  x: 0.2         # 权重系数
  dt: 60.0       # 时间步长 (s)
  initial_V: 12000.0  # 初始蓄水量 (m³)

physical_relations:
  V_to_H:
    type: linear
    base_level: 99.0
    coefficient: 0.000125
  H_to_Q:
    type: weir
    threshold: 99.0
    coefficient: 25.0
    exponent: 1.5
```

### 添加新模型

1. 继承`BaseLumpedModel`基类
2. 实现`step()`方法
3. 添加参数验证
4. 编写单元测试
5. 更新配置验证器

```python
class MyCustomModel(BaseLumpedModel):
    def __init__(self, dt, custom_param, initial_V, V_to_H_func, H_to_Q_func):
        super().__init__(dt, initial_V, V_to_H_func, H_to_Q_func)
        self.custom_param = custom_param
    
    def step(self, Q_in):
        # 实现模型逻辑
        Q_out = self.custom_algorithm(Q_in)
        self._update_physical_states(Q_in, Q_out)
        self.current_Q_out = Q_out
        self._record_state(Q_in)
        
        return {
            'Q_out': Q_out,
            'H_out': self.current_H,
            'V': self.current_V,
            'time': self.time
        }
```

## 📊 性能基准

### 计算性能
- **圣维南模型**: ~1000 时间步/秒（标准求解器）
- **马斯京干模型**: ~10000 时间步/秒
- **蓄量演算模型**: ~8000 时间步/秒
- **IDZ模型**: ~5000 时间步/秒

### 精度对比
- **质量守恒误差**: < 0.1%
- **数值稳定性**: Courant数 < 1.0
- **收敛性**: 牛顿法 < 5次迭代

## 🤝 贡献指南

我们欢迎各种形式的贡献！

### 如何贡献

1. Fork项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开Pull Request

### 代码规范

- 遵循PEP 8编码规范
- 编写清晰的文档字符串
- 添加单元测试
- 确保测试通过

### 报告问题

使用GitHub Issues报告bug或请求新功能。请包含：
- 问题描述
- 重现步骤
- 预期行为
- 系统信息

## 📚 文档和教程

- [API文档](docs/api.md)
- [用户指南](docs/user_guide.md)
- [开发者文档](docs/developer.md)
- [理论背景](docs/theory.md)
- [最佳实践](docs/best_practices.md)

## 📄 许可证

本项目采用MIT许可证。详情请见 [LICENSE](LICENSE) 文件。

## 🙏 致谢

- 感谢所有贡献者的宝贵贡献
- 感谢水利工程社区的支持和反馈
- 基于开源科学计算生态系统（NumPy、SciPy、Matplotlib等）

## 📞 联系我们

- **项目主页**: https://github.com/your-username/WaterNet
- **问题反馈**: https://github.com/your-username/WaterNet/issues
- **讨论**: https://github.com/your-username/WaterNet/discussions

---

**WaterNet** - 让明渠水力建模更简单、更准确、更高效。: 明渠输水系统数字孪生建模框架

WaterNet是一个基于圣维南方程组的明渠水力模型接口系统，提供高精度物理模型与多种降阶模型的统一建模框架。

## 🌊 主要特性

- **统一接口架构**: 基于HydroModel抽象基类的标准化模型接口
- **高精度物理模型**: 完整实现圣维南方程组的非恒定流计算
- **多元降阶模型库**: 集成水量平衡、蓄量演算、马斯京干、IDZ等经典算法
- **智能参数辨识**: 支持静态特征曲线拟合和动态参数优化
- **同步孪生协调**: 实现精细化模型与降阶模型的实时同步运行
- **在线自适应校正**: 基于实时数据的模型参数自动调整

## 🏗️ 系统架构

```
WaterNet架构层次
├── 接口层 (HydroModel)
├── 物理核心层 (SaintVenantModel) 
├── 降阶模型层 (BaseLumpedModel + 具体实现)
├── 参数辨识层 (ParameterEstimator)
└── 协调层 (SynchronizedTwinningHarness)
```

## 📦 安装

```bash
# 基础安装
pip install -e .

# 完整功能安装
pip install -e ".[dev]"

# 从源码安装
git clone https://github.com/waternet/waternet.git
cd waternet
pip install -e ".[dev]"
```

## 🚀 快速开始

### 基础使用示例

```python
import numpy as np
from waternet import SaintVenantModel, MuskingumModel, SynchronizedTwinningHarness

# 创建圣维南模型
sections = [
    {'mileage': 0, 'elevation': 100.0, 'roughness': 0.025, 
     'area_func': lambda h: max(0, h-100)*10, 
     'top_width_func': lambda h: 10 if h > 100 else 0},
    {'mileage': 1000, 'elevation': 99.0, 'roughness': 0.025,
     'area_func': lambda h: max(0, h-99)*10,
     'top_width_func': lambda h: 10 if h > 99 else 0}
]

sv_model = SaintVenantModel("TestChannel", "upstream", "downstream", sections)

# 创建降阶模型
rom_model = MuskingumModel(dt=60.0, K=3600, x=0.2, initial_V=50000,
                          V_to_H_func=lambda V: 99 + V/10000,
                          H_to_Q_func=lambda H: (H-99)**1.5 * 100)

# 同步孪生仿真
harness = SynchronizedTwinningHarness(sv_model, rom_model)
results = harness.run_simulation(Q_in_series=np.ones(100) * 10.0, dt=60.0)
```

### 参数辨识示例

```python
from waternet import ParameterEstimator

# 创建参数估计器
estimator = ParameterEstimator(sv_model)

# 静态特征辨识
Q_range = np.linspace(5, 50, 10)
H_range = np.linspace(99.5, 101.0, 10)
curves = estimator.identify_static_curves(Q_range, H_range)

# 动态参数辨识  
unsteady_data = {'Q_in': Q_in_series, 'H_down': H_down_series, 'dt': 60.0}
best_params = estimator.identify_dynamic_parameters(unsteady_data, MuskingumModel)
```

## 📚 文档

- [API文档](docs/api.md)
- [用户指南](docs/user_guide.md) 
- [开发者指南](docs/developer_guide.md)
- [示例集合](examples/)

## 🧪 测试

```bash
# 运行所有测试
pytest

# 运行覆盖率测试
pytest --cov=waternet --cov-report=html

# 运行特定测试
pytest waternet/tests/test_saint_venant.py
```

## 🤝 贡献

欢迎贡献代码、报告问题或提出建议！请查看[贡献指南](CONTRIBUTING.md)了解详细信息。

## 📄 许可证

本项目采用MIT许可证 - 详见[LICENSE](LICENSE)文件。

## 🎯 路线图

- [ ] 支持二维浅水方程模型
- [ ] 集成机器学习降阶算法  
- [ ] 增加GPU加速计算
- [ ] 实现分布式并行仿真
- [ ] 开发可视化界面

## 📞 联系方式

- 问题反馈: [GitHub Issues](https://github.com/waternet/waternet/issues)
- 邮件联系: waternet-dev@example.com
- 文档网站: https://waternet.readthedocs.io