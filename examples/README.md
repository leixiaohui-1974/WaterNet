# WaterNet 项目重构指南

## 概述

WaterNet项目已经完成了代码结构的重大重构和优化，建立了更清晰、更维护友好的项目组织结构。

## 新的项目结构

```
WaterNet/
├── waternet/                     # 核心代码库
│   ├── models/                   # 水力模型
│   ├── config/                   # 配置管理
│   ├── parameter_estimation/     # 参数估计
│   ├── coordination/             # 数字孪生协调
│   ├── interfaces/               # 模型接口
│   └── utils/                    # 工具函数
├── tests/                        # 统一测试目录 ⭐ 新统一结构
│   ├── unit/                     # 单元测试
│   ├── integration/              # 集成测试
│   ├── deep_channel/             # 深度测试案例 ⭐ 从 waternet/tests 迁移
│   ├── fixtures/                 # 测试数据
│   └── conftest.py               # pytest配置
├── examples/                     # 示例和演示 ⭐ 重新组织
│   ├── basic/                    # 基础使用示例 ⭐ 新增
│   ├── advanced/                 # 高级功能演示 ⭐ 新增
│   └── configs/                  # 示例配置文件
├── scripts/                      # 工具脚本
│   ├── test_runner.py           # 统一测试入口 ⭐ 新增
│   ├── benchmark.py             # 性能基准测试
│   └── validation.py            # 安装验证
├── docs/                         # 文档目录 ⭐ 新增
│   └── reports/                  # 测试报告 ⭐ 新增
├── configs/                      # 项目配置文件 ⭐ 新增
│   ├── test_configs/             # 测试配置
│   └── example_configs/          # 示例配置
└── pytest.ini                   # pytest统一配置 ⭐ 新增
```

## 主要变更

### 1. 测试系统重构 ⭐

**变更前:**
- `tests/` 和 `waternet/tests/` 双重测试目录
- 深度测试混杂在 `waternet/tests/deep_channel_testing/`

**变更后:**
- 统一测试目录 `tests/`
- 深度测试迁移到 `tests/deep_channel/`
- 标准化的单元测试和集成测试分离
- 统一的pytest配置

### 2. 示例代码重组 ⭐

**新增目录:**
- `examples/basic/` - 基础功能示例
- `examples/advanced/` - 高级功能演示

**迁移的文件:**
- `analyze_steady_profiles.py` → `examples/advanced/profile_analysis.py`
- `ascii_profile_viewer.py` → `examples/advanced/ascii_visualization.py`
- `demo_deep_channel_features.py` → `examples/advanced/deep_channel_demo.py`
- `unsteady_step_response.py` → `examples/advanced/unsteady_analysis.py`
- `visualize_steady_state_profile.py` → `examples/basic/profile_visualization.py`

### 3. 根目录清理 ⭐

**已删除的文件:**
- `comprehensive_core_test.py` (重构为 `tests/integration/test_comprehensive.py`)
- `test_deep_channel_implementation.py` (功能已整合)
- `test_fixes.py` (临时文件)
- 各种分析和可视化脚本 (已迁移到examples/)

### 4. 配置文件整合 ⭐

**新的配置结构:**
- `configs/example_configs/` - 示例配置文件
- `configs/test_configs/` - 测试配置文件
- `pytest.ini` - 统一pytest配置

### 5. 文档系统建立 ⭐

**新的文档结构:**
- `docs/reports/` - 测试报告和基准测试结果
- 整合了原有的各种报告文件

## 使用新的测试系统

### 统一测试入口

```bash
# 运行所有测试
python scripts/test_runner.py --all

# 只运行单元测试
python scripts/test_runner.py --unit

# 运行集成测试
python scripts/test_runner.py --integration

# 运行深度通道测试
python scripts/test_runner.py --deep-channel

# 运行测试并生成覆盖率报告
python scripts/test_runner.py --unit --coverage

# 列出可用测试
python scripts/test_runner.py --list
```

### 直接使用pytest

```bash
# 运行所有测试
pytest

# 运行特定测试目录
pytest tests/unit/
pytest tests/integration/
pytest tests/deep_channel/

# 运行特定测试文件
pytest tests/integration/test_comprehensive.py

# 生成覆盖率报告
pytest --cov=waternet --cov-report=html
```

## 导入路径更新

深度测试模块的导入路径已经更新以适应新的结构：

**变更前:**
```python
from waternet.tests.deep_channel_testing.test_framework import DeepChannelTestFramework
```

**变更后:**
```python
from test_framework import DeepChannelTestFramework
```

## 向后兼容性

- 核心 `waternet/` 模块的API保持不变
- 现有的基本示例仍然可用
- 重构的综合测试保持相同的功能

## 下一步建议

1. **测试验证**: 运行完整测试套件确保功能正常
2. **文档更新**: 更新README和用户指南
3. **CI/CD适配**: 更新持续集成配置以使用新的测试结构
4. **代码审查**: 检查导入路径和依赖关系

## 获取帮助

如果在使用新结构时遇到问题：

1. 查看 `pytest.ini` 了解测试配置
2. 运行 `python scripts/test_runner.py --list` 查看可用测试
3. 检查 `tests/` 目录下的示例测试文件
4. 参考 `examples/` 目录下的使用示例

---

*本重构于2024年10月完成，旨在提高代码质量和项目可维护性。*