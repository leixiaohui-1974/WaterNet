from __future__ import annotations

"""
WaterSystemSimulationManager 综合示例。

展示内容：
1. 利用仿真管理器执行综合分析策略，并生成拓展图表与详细报告；
2. 切换到参数优化策略，获得优化结果及校验信息；
3. 汇总关键输出路径，便于进一步查阅。
"""

import json
import math
from pathlib import Path
from typing import Dict

import numpy as np

from waternet.core.simulation_manager import (
    SimulationConfiguration,
    SimulationStrategy,
    WaterSystemSimulationManager,
)
from waternet.core.unsteady_flow_analyzer import ChannelConfig
from waternet.utils.demo_reporting import (
    plot_cross_section_profiles,
    plot_method_time_series,
    write_analysis_detail_report,
)
from waternet.utils.output_manager import ensure_output_tree
from waternet.utils.validation import validate_analysis_bundle, validate_optimizer_bundle


def _sample_hydrograph(samples: int = 9) -> list[float]:
    """构造带有单峰洪水特征的边界流量序列。"""
    return [
        102.0 + 26.0 * math.sin(idx / (samples - 1) * math.pi) ** 1.3
        for idx in range(samples)
    ]


def _convert_methods(payload: Dict[str, Dict[str, object]]) -> Dict[str, Dict[str, object]]:
    """提取方法配置、时间序列与指标，方便后续绘图。"""
    methods: Dict[str, Dict[str, object]] = {}
    for method_id, method_payload in payload.items():
        methods[method_id] = {
            "config": method_payload["config"],
            "time_series": method_payload["time_series"],
            "metrics": method_payload["metrics"],
        }
    return methods


def run_demo() -> None:
    """执行综合分析与参数优化，并生成附加成果。"""
    base_dir = Path(__file__).resolve().parent
    output_dir = base_dir / "outputs" / "simulation_manager"
    ensure_output_tree(output_dir, ())

    config = SimulationConfiguration(
        project_name="WaterNet Object Showcase",
        strategy=SimulationStrategy.COMPREHENSIVE_ANALYSIS,
        output_directory=str(output_dir),
    )

    manager = WaterSystemSimulationManager(config)

    analysis_override = {
        "boundary_flows": _sample_hydrograph(10),
        "channel": ChannelConfig(
            length=4_600.0,
            slope=2.1e-4,
            roughness=0.027,
            bottom_width=13.5,
            side_slope=1.0,
            base_elevation=94.0,
            max_depth=7.8,
        ),
    }

    analysis_result = manager.run_simulation(analysis_override)
    if not analysis_result.analysis_results:
        raise RuntimeError("综合分析未返回任何结果。")

    outputs = analysis_result.analysis_results["outputs"]
    data_path = Path(outputs["data"])
    plot_path = Path(outputs["plot"])
    report_path = Path(outputs["report"])

    analysis_validation = validate_analysis_bundle(
        data_path,
        plot_path,
        report_path,
    )
    if not analysis_validation.ok:
        raise RuntimeError("综合分析输出校验失败：" + "; ".join(analysis_validation.errors))

    payload = json.loads(data_path.read_text(encoding="utf-8"))
    timestamp = data_path.stem.split("_")[-1]
    time_axis = np.array(payload["time"]) / 3600.0
    methods = _convert_methods(payload["methods"])
    channel_cfg: ChannelConfig = analysis_override["channel"]

    extra_plot_dir = output_dir / "plots"
    extra_report_dir = output_dir / "reports"
    extra_plot_dir.mkdir(parents=True, exist_ok=True)
    extra_report_dir.mkdir(parents=True, exist_ok=True)

    time_series_plot = plot_method_time_series(
        time_axis,
        methods,
        extra_plot_dir,
        timestamp,
    )
    extra_plots = plot_cross_section_profiles(
        time_axis,
        channel_cfg,
        methods,
        extra_plot_dir,
        timestamp,
    )
    detailed_report = write_analysis_detail_report(
        analysis_result.analysis_results,
        methods,
        extra_plots,
        time_series_plot,
        extra_report_dir,
        timestamp,
    )

    manager.config.strategy = SimulationStrategy.PARAMETER_OPTIMIZATION
    optimisation_result = manager.run_simulation()
    optimiser_files = optimisation_result.output_files

    data_file = optimiser_files.get("data")
    if not data_file:
        raise RuntimeError("参数优化输出缺少数据文件。")

    artefacts = {key: Path(value) for key, value in optimiser_files.items()}
    optimisation_validation = validate_optimizer_bundle(
        artefacts["data"],
        artefacts.get("report"),
    )
    if not optimisation_validation.ok:
        raise RuntimeError("参数优化输出校验失败：" + "; ".join(optimisation_validation.errors))

    print("仿真管理器演示已完成。")
    print("综合分析主要输出：")
    print(f"- 数据文件：{data_path}")
    print(f"- 综合图表：{plot_path}")
    print(f"- 基础报告：{report_path}")
    print(f"- 断面时间序列图：{extra_plots['cross_section']}")
    print(f"- 纵剖面图：{extra_plots['longitudinal']}")
    print(f"- 补充详细报告：{detailed_report}")
    print("参数优化输出：")
    for name, path in artefacts.items():
        print(f"- {name}：{path}")


if __name__ == "__main__":
    run_demo()