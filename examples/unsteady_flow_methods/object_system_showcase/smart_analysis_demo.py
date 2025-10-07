from __future__ import annotations

"""
智能非恒定流综合分析示例脚本。

步骤概述：
1. 设定边界流量、渠道几何参数以及对比方法；
2. 调用 `UnsteadyFlowAnalyzer` 生成标准化的分析结果；
3. 借助通用工具绘制断面时间序列、纵剖面图，并输出补充报告；
4. 对生成的数据、图表和报告执行结构化校验。
"""

import json
import math
from pathlib import Path
from typing import Dict

import numpy as np

from waternet.core.unsteady_flow_analyzer import (
    ChannelConfig,
    MethodConfig,
    UnsteadyFlowAnalyzer,
)
from waternet.utils.demo_reporting import (
    plot_cross_section_profiles,
    plot_method_time_series,
    write_analysis_detail_report,
)
from waternet.utils.output_manager import ensure_output_tree
from waternet.utils.validation import validate_analysis_bundle


def run_demo() -> None:
    """执行综合分析并生成附加成果。"""
    base_dir = Path(__file__).resolve().parent
    output_dir = base_dir / "outputs" / "smart_analysis"
    ensure_output_tree(output_dir, ("data", "plots", "reports"))

    analyzer = UnsteadyFlowAnalyzer(output_dir)

    # 构造边界流量序列：单峰洪水过程，带有一定的缓升陡降特征
    boundary_flows = [
        105.0 + 24.0 * math.sin(idx / 9.0 * math.pi) ** 1.4
        for idx in range(10)
    ]

    channel_cfg = ChannelConfig(
        length=4_200.0,
        slope=2.4e-4,
        roughness=0.028,
        bottom_width=14.0,
        side_slope=1.1,
        base_elevation=93.5,
        max_depth=7.5,
    )

    analyzer.configure(
        boundary_flows=boundary_flows,
        channel=channel_cfg,
        methods=[
            MethodConfig(
                identifier="muskingum_balanced",
                name="Muskingum 平衡参数方案",
                kind="lumped",
                parameters={"K": 3_400.0, "x": 0.17},
                color="#2563eb",
                linestyle="-",
            ),
            MethodConfig(
                identifier="muskingum_fast",
                name="Muskingum 快速响应方案",
                kind="lumped",
                parameters={"K": 2_200.0, "x": 0.09},
                color="#f97316",
                linestyle="--",
            ),
            MethodConfig(
                identifier="storage_smooth",
                name="蓄量演算平滑方案",
                kind="routing",
                parameters={"storage_coefficient": 0.42},
                color="#10b981",
                linestyle="-.",
            ),
        ],
    )

    result = analyzer.run_comparison()

    outputs = result["outputs"]
    data_path = Path(outputs["data"])
    plot_path = Path(outputs["plot"])
    report_path = Path(outputs["report"])

    validation = validate_analysis_bundle(
        data_path,
        plot_path,
        report_path,
    )
    if not validation.ok:
        raise RuntimeError("生成的数据或报告结构存在问题：" + "; ".join(validation.errors))

    payload = json.loads(data_path.read_text(encoding="utf-8"))
    timestamp = data_path.stem.split("_")[-1]
    time_axis = np.array(payload["time"]) / 3600.0

    methods: Dict[str, Dict[str, object]] = {}
    for method_id, method_payload in payload["methods"].items():
        methods[method_id] = {
            "config": method_payload["config"],
            "time_series": method_payload["time_series"],
            "metrics": method_payload["metrics"],
        }

    extra_plot_dir = output_dir / "plots"
    extra_report_dir = output_dir / "reports"

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
        result,
        methods,
        extra_plots,
        time_series_plot,
        extra_report_dir,
        timestamp,
    )

    rec = result["recommendations"]
    print("非恒定流综合分析已完成。")
    print(f"- 数据文件：{data_path}")
    print(f"- 综合图表：{plot_path}")
    print(f"- 基础报告：{report_path}")
    print(f"- 断面时间序列图：{extra_plots['cross_section']}")
    print(f"- 纵剖面图：{extra_plots['longitudinal']}")
    print(f"- 补充详细报告：{detailed_report}")
    print(f"- 综合推荐方法：{rec['best_overall']}")


if __name__ == "__main__":
    run_demo()