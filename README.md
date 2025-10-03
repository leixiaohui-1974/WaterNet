# WaterNet: 明渠输水系统数字孪生建模框架

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