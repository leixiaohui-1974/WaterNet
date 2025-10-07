from __future__ import annotations

"""
马斯京干法参数自动优化示例。

流程说明：
1. 根据渠道特征给出不同应用场景的初始参数；
2. 输入观测入、出流过程，执行带约束的优化搜索；
3. 生成 JSON 数据、Markdown 报告，并补充比对图与敏感性分析图；
4. 校验输出结构，保证数据可复用。
"""

from pathlib import Path

import numpy as np

from waternet.core.parameter_optimizer import OptimizationObjective, ParameterOptimizer
from waternet.utils.demo_reporting import (
    plot_optimization_comparison,
    plot_parameter_sensitivity,
    simulate_muskingum_series,
    write_optimization_summary,
)
from waternet.utils.output_manager import ensure_output_tree
from waternet.utils.validation import validate_optimizer_bundle


def run_demo() -> None:
    """执行参数推荐、优化与成果整理。"""
    base_dir = Path(__file__).resolve().parent
    output_dir = base_dir / "outputs" / "parameter_optimization"
    ensure_output_tree(output_dir, ())

    optimizer = ParameterOptimizer(
        objective_type=OptimizationObjective.BALANCED,
        max_iterations=60,
        tolerance=1e-6,
    )

    channel_properties = {
        "length": 4_500.0,
        "slope": 2.2e-4,
        "roughness": 0.026,
    }

    flood_hint = optimizer.recommend_parameters(channel_properties, "flood_forecasting")
    design_hint = optimizer.recommend_parameters(channel_properties, "engineering_design")

    observed_inflows = [98, 112, 138, 162, 158, 140, 118, 104, 96]
    observed_outflows = [98, 106, 122, 147, 154, 146, 128, 110, 101]
    dt = 1_800.0

    initial_simulation = simulate_muskingum_series(observed_inflows, flood_hint, dt)

    result = optimizer.optimize_muskingum_parameters(
        observed_inflows=observed_inflows,
        observed_outflows=observed_outflows,
        time_step=dt,
        initial_params={"K": flood_hint["K"], "x": flood_hint["x"]},
    )

    artefacts = optimizer.export_result_bundle(result, output_dir)
    validation = validate_optimizer_bundle(
        artefacts["data"],
        artefacts.get("report"),
    )
    if not validation.ok:
        raise RuntimeError("参数优化输出校验失败：" + "; ".join(validation.errors))

    timestamp = artefacts["data"].stem.split("_")[-1]
    optimized_simulation = simulate_muskingum_series(
        observed_inflows,
        result.optimal_params,
        dt,
    )
    time_axis = np.arange(len(observed_inflows)) * dt / 3600.0

    comparison_plot = plot_optimization_comparison(
        time_axis,
        observed_outflows,
        initial_simulation,
        optimized_simulation,
        output_dir,
        timestamp,
    )
    sensitivity_plot = plot_parameter_sensitivity(
        result.parameter_sensitivity,
        output_dir,
        timestamp,
    )

    summary_report = write_optimization_summary(
        artefacts,
        flood_hint,
        design_hint,
        result.optimal_params,
        result.objective_value,
        comparison_plot,
        sensitivity_plot,
    )

    print("马斯京干法参数优化已完成。")
    print(f"- 参数数据：{artefacts['data']}")
    if artefacts.get("report"):
        print(f"- 自动报告：{artefacts['report']}")
    print(f"- 对比图：{comparison_plot}")
    print(f"- 敏感性图：{sensitivity_plot}")
    print(f"- 补充汇总报告：{summary_report}")
    print(
        "推荐参数概览："
        f"洪水预报 K={flood_hint['K']:.0f}s, x={flood_hint['x']:.3f}；"
        f"工程设计 K={design_hint['K']:.0f}s, x={design_hint['x']:.3f}；"
        f"优化结果 K={result.optimal_params['K']:.1f}s, x={result.optimal_params['x']:.3f}。"
    )


if __name__ == "__main__":
    run_demo()