# 面向对象系统拆解示例说明

本目录存放经过拆解后的三个独立示例脚本，用以替换原先臃肿的 `refactored_object_system_demo.py`。
每个示例都能够独立运行、输出数据/图形/报告，并在脚本内部完成结构校验，方便二次开发和比对校验。

## 示例脚本概览

| 脚本 | 主要功能 | 核心输出 |
| --- | --- | --- |
| `smart_analysis_demo.py` | 调用 `UnsteadyFlowAnalyzer` 对多种非恒定流算法进行对比分析，生成时间序列、综合图表与中文报告 | `outputs/smart_analysis/` 目录下的 JSON 数据、PNG 图表、Markdown 报告以及扩展的断面分析结果 |
| `parameter_optimization_demo.py` | 使用 `ParameterOptimizer` 自动推荐并优化马斯京干法参数，输出优化过程、敏感性分析及结论 | `outputs/parameter_optimization/` 目录下的参数数据、优化报告与附加分析图表 |
| `steady_unsteady_comparison_demo.py` | 构建 20 km 渠道的多流量/水位恒定流分析，并基于稳态结果对比准静态波、扩散波、运动波三种分布式方法的非恒定流响应 | `outputs/steady_unsteady_comparison/` 中的稳态/非稳态数据包、纵剖面图、断面时间序列图与综合报告 |
| `simulation_manager_demo.py` | 通过 `WaterSystemSimulationManager` 统一调度综合分析与参数优化流程，验证完整管线 | `outputs/simulation_manager/` 中的分析数据、纵剖面图、汇总报告及优化结果 |

最顶层的 `refactored_object_system_demo.py` 会依次调用上述三个脚本，以便兼容原有的调用入口。

## 输出内容

运行任意脚本后，会在 `outputs/` 子目录下生成如下内容：

1. **数据文件（JSON）**：包含时间序列、方法配置、统计指标等信息，可直接用于二次分析。
2. **图表（PNG/SVG）**：覆盖流量与水位的综合对比图、断面水位/流量时间序列图、纵剖面图等。
3. **报告（Markdown）**：提供中文的结论、建议、方法推荐、关键指标说明。
4. **验证报告（可选）**：对生成文件完成结构化校验，确保数据完整。

所有输出均为中文字段与注释，便于国内团队快速理解与汇报。

## 使用方法

在仓库根目录执行：

```bash
python examples/unsteady_flow_methods/refactored_object_system_demo.py
```

或单独运行某个拆分脚本，如：

```bash
python examples/unsteady_flow_methods/object_system_showcase/smart_analysis_demo.py
```

若需要完整的恒定流-非恒定流联合示例，可执行：

```bash
python examples/unsteady_flow_methods/object_system_showcase/steady_unsteady_comparison_demo.py
```

该脚本会生成较多数据与图件，首次运行耗时较长，请耐心等待。

脚本运行完毕后，可在对应 `outputs/` 文件夹中查看生成的详细成果。若需重复运行，建议先清理旧的输出目录，以免混淆新旧结果。
