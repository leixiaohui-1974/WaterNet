# 单一渠道水力学测试目录

## 目录概述

本目录专门用于管理单一渠道的水力学分析、测试和示例，提供清晰的代码组织结构，避免与其他复杂系统示例混淆。

## 目录结构

```
single_channel_hydraulics/
├── README.md                    # 本说明文档
├── configs/                     # 渠道配置文件
│   ├── simple_channel.yaml     # 简单矩形渠道配置
│   ├── trapezoidal_channel.yaml # 梯形断面渠道配置
│   ├── complex_channel.yaml    # 复杂变断面渠道配置
│   └── test_channels/          # 测试用渠道配置
├── tests/                       # 测试脚本
│   ├── steady_flow_tests.py    # 恒定流测试
│   ├── unsteady_flow_tests.py  # 非恒定流测试
│   ├── geometry_tests.py       # 几何参数测试
│   └── validation_tests.py     # 验证测试
├── outputs/                     # 输出结果
│   ├── reports/                # 分析报告
│   ├── data/                   # 数据文件(CSV等)
│   └── plots/                  # 图表文件
├── docs/                        # 文档资料
│   ├── theory.md               # 理论基础
│   ├── examples.md             # 示例说明
│   └── troubleshooting.md      # 问题排查
├── steady_flow_analysis.py            # 恒定流分析主程序
├── head_loss_calculator.py            # 水头损失计算器
├── channel_geometry_tool.py           # 渠道几何工具
├── parameter_comparison_analysis.py   # 参数对比分析器
└── visualization_tools.py             # 可视化工具
```

## 主要功能模块

### 1. 恒定流分析 (steady_flow_analysis.py)
- 多工况恒定流计算
- 水面线分析
- 水头损失计算
- 结果导出和报告生成

### 2. 水头损失计算器 (head_loss_calculator.py)
- 摩擦损失计算
- 局部损失计算
- 损失分布分析
- 不同糙率条件对比

### 3. 渠道几何工具 (channel_geometry_tool.py)  
- 断面几何参数计算
- 水力几何函数生成
- 断面形状优化分析
- 几何参数敏感性分析

### 4. 参数对比分析器 (parameter_comparison_analysis.py) ⭐新增
- 坡度变化对比分析
- 流量范围对比分析  
- 断面参数对比分析
- 综合敏感性分析
- 参数优化建议

### 5. 水面线绘制工具 (water_surface_profile_plotter.py) 🆕最新功能
**参考 `config_driven_reservoir_gate_system.py` 的水面线绘制逻辑实现**
- ✅ 多工况水面线纵剖面对比（如：25, 50, 75, 100 m³/s）
- ✅ 流速和弗劳德数分布分析
- ✅ 水力几何参数全面计算
- ✅ 恒定流水面线精确计算（支持WaterNet基础库和简化算法）
- ✅ 高质量可视化图表输出（中文字体支持）
- ✅ 详细水力学分析报告生成
- ✅ 配置文件兼容性（支持现有trapezoidal_channel.yaml格式）
- ✅ 流态自动识别（亚临界流、混合流态）

**主要特色：**
- 基于参考文件的成熟水面线计算算法
- 双图表布局：水面线纵剖面 + 流速弗劳德数分布
- 专业水位数字标注和工程制图样式
- 参数敏感性定量分析（水深、流速、水头损失）

### 6. 可视化工具 (visualization_tools.py)
- 水面线绘制
- 损失分布图
- 断面形状显示
- 参数对比图表

## 配置文件说明

### simple_channel.yaml
- 标准矩形断面渠道
- 用于基础测试和教学演示
- 参数简单，计算稳定

### trapezoidal_channel.yaml  
- 标准梯形断面渠道
- 符合工程实际的断面形式
- 适合大多数工程应用

### complex_channel.yaml
- 变断面复杂渠道
- 用于高级分析和验证
- 测试算法鲁棒性

## 使用指南

### 快速开始
```bash
# 运行恒定流分析
python steady_flow_analysis.py

# 计算水头损失
python head_loss_calculator.py

# 运行参数对比分析
python parameter_comparison_analysis.py

# 新增：水面线绘制工具 🆕
python water_surface_profile_plotter.py

# 水面线绘制示例集
python water_surface_profile_examples.py
```

### 自定义配置
1. 复制合适的配置文件模板
2. 修改断面参数和边界条件
3. 运行相应的分析程序
4. 查看outputs目录中的结果

### 结果查看
- **CSV数据**: `outputs/data/` 目录
- **分析报告**: `outputs/reports/` 目录
- **图表文件**: `outputs/plots/` 目录

## 测试用例

### 基础测试
- 矩形断面恒定流计算
- 梯形断面水力参数验证
- 糙率系数敏感性分析

### 高级测试
- 复杂变断面流动分析
- 多工况对比验证
- 极端条件下的数值稳定性

### 验证测试
- 与解析解对比
- 与其他软件结果对比
- 物理模型试验对比

## 扩展功能

### 1. 参数优化
- 断面形状优化
- 糙率参数校准
- 边界条件优化

### 2. 不确定性分析
- 参数敏感性分析
- 蒙特卡洛模拟
- 误差传播分析

### 3. 实时分析
- 在线参数调整
- 实时结果更新
- 交互式可视化

## 注意事项

1. **配置文件格式**: 严格遵循YAML格式规范
2. **单位制**: 统一使用国际单位制(SI)
3. **数值精度**: 注意浮点数精度问题
4. **边界条件**: 确保边界条件物理合理

## 相关参考

- [WaterNet核心库文档](../../docs/api/)
- [圣维南方程理论](docs/theory.md)
- [使用示例](docs/examples.md)
- [问题排查指南](docs/troubleshooting.md)

## 维护说明

本目录由WaterNet项目团队维护，如有问题请：
1. 查看文档资料
2. 运行验证测试
3. 提交问题报告

---
*最后更新: 2024-10-05*
*版本: v1.0.0*