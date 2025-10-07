from __future__ import annotations

"""
示例专用的报告与图表生成工具。

该模块集中封装示例脚本中复用的绘图与报告逻辑，
避免在示例内部重复编写通用函数，便于维护与扩展。
"""

from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import matplotlib.pyplot as plt
import numpy as np

from ..core.unsteady_flow_analyzer import ChannelConfig
from ..models.lumped_models import MuskingumModel
from ..utils.model_factory import create_default_physical_relations

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def plot_method_time_series(
    time_hours: np.ndarray,
    methods: Dict[str, Dict[str, object]],
    output_dir: Path,
    timestamp: str,
) -> Path:
    """绘制水位、流量、流速的时间序列对比图。"""
    fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
    titles = ["各方法水位时间序列对比", "各方法流量时间序列对比", "各方法流速时间序列对比"]
    ylabels = ["水位（m）", "流量（m3/s）", "流速（m/s）"]

    for axis, title, ylabel in zip(axes, titles, ylabels):
        axis.set_title(title)
        axis.set_ylabel(ylabel)
        axis.grid(alpha=0.3, linestyle="--", linewidth=0.6)

    axes[-1].set_xlabel("时间（小时）")

    for payload in methods.values():
        cfg = payload["config"]
        label = cfg["name"]
        series = payload["time_series"]
        axes[0].plot(time_hours, series["water_level"], label=label, linewidth=2)
        axes[1].plot(time_hours, series["outflow"], label=label, linewidth=2)
        axes[2].plot(time_hours, series["velocity"], label=label, linewidth=2)

    axes[0].legend(loc="best")
    fig.tight_layout()

    plot_path = output_dir / f"analysis_time_series_{timestamp}.png"
    fig.savefig(plot_path, dpi=220)
    plt.close(fig)
    return plot_path


def plot_cross_section_profiles(
    time_hours: np.ndarray,
    channel: ChannelConfig,
    methods: Dict[str, Dict[str, object]],
    output_dir: Path,
    timestamp: str,
) -> Dict[str, Path]:
    """生成断面时间序列与纵剖面图。"""
    positions = np.array([0.0, 0.25, 0.5, 0.75, 1.0]) * channel.length
    bed_profile = channel.base_elevation + channel.slope * (channel.length - positions)

    fig, axes = plt.subplots(2, len(positions), figsize=(16, 6), sharex=True, sharey="row")
    for col, pos in enumerate(positions):
        for axis in axes[:, col]:
            axis.grid(alpha=0.3, linestyle="--", linewidth=0.6)
        axes[0, col].set_title(f"断面{col + 1}\n距上游{pos:,.0f} m")
        axes[0, col].set_ylabel("水位（m）")
        axes[1, col].set_ylabel("流量（m3/s）")
        axes[1, col].set_xlabel("时间（小时）")

    for payload in methods.values():
        cfg = payload["config"]
        label = cfg["name"]
        ts = payload["time_series"]
        water_level = np.array(ts["water_level"])
        outflow = np.array(ts["outflow"])
        depth = water_level - channel.base_elevation

        for col, pos in enumerate(positions):
            local_bed = bed_profile[col]
            local_water = depth + local_bed
            axes[0, col].plot(time_hours, local_water, label=label, linewidth=1.8)
            axes[1, col].plot(time_hours, outflow, label=label, linewidth=1.8)

    axes[0, 0].legend(loc="best")
    fig.tight_layout()
    cs_path = output_dir / f"cross_section_time_series_{timestamp}.png"
    fig.savefig(cs_path, dpi=220)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.set_title("峰值时刻纵向水位剖面")
    ax.set_xlabel("距上游距离（m）")
    ax.set_ylabel("标高（m）")
    ax.grid(alpha=0.3, linestyle="--", linewidth=0.6)

    ax.plot(positions, bed_profile, color="#444", linestyle=":", linewidth=1.2, label="河床")

    for payload in methods.values():
        cfg = payload["config"]
        label = cfg["name"]
        outflow = np.array(payload["time_series"]["outflow"])
        water_level = np.array(payload["time_series"]["water_level"])
        peak_idx = int(np.argmax(outflow))
        depth_peak = water_level[peak_idx] - channel.base_elevation
        water_surface = bed_profile + depth_peak
        ax.plot(positions, water_surface, linewidth=2, label=label)

    ax.legend(loc="best")
    fig.tight_layout()
    longitudinal_path = output_dir / f"longitudinal_profile_{timestamp}.png"
    fig.savefig(longitudinal_path, dpi=220)
    plt.close(fig)

    return {"cross_section": cs_path, "longitudinal": longitudinal_path}


def write_analysis_detail_report(
    result: Dict[str, object],
    methods: Dict[str, Dict[str, object]],
    extra_plots: Dict[str, Path],
    time_series_plot: Path,
    report_dir: Path,
    timestamp: str,
) -> Path:
    """撰写分析详细报告，聚焦结论与工程建议。"""
    report_path = report_dir / f"analysis_detail_{timestamp}.md"
    rec = result["recommendations"]

    lines = [
        "# 非恒定流综合分析详细报告",
        "",
        f"- 生成时间：{timestamp}",
        f"- 断面时间序列图：`{extra_plots['cross_section'].name}`",
        f"- 纵剖面图：`{extra_plots['longitudinal'].name}`",
        f"- 综合时间序列图：`{time_series_plot.name}`",
        "",
        "## 方法结论与推荐",
        "",
        f"- 综合最优：**{rec.get('best_overall', '暂无数据')}**",
        f"- 精度优选：**{rec.get('best_for_accuracy', '暂无数据')}**",
        f"- 速度优选：**{rec.get('best_for_speed', '暂无数据')}**",
        f"- 稳定性优选：**{rec.get('best_for_stability', '暂无数据')}**",
        "",
        "## 关键指标对比",
        "",
        "| 方法 | 峰值流量 (m3/s) | 峰值水位 (m) | 连续性误差 (%) | 滞后时间 (h) | 稳定性评分 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]

    for payload in methods.values():
        cfg = payload["config"]
        metrics = payload["metrics"]
        lines.append(
            f"| {cfg['name']} | "
            f"{metrics['peak_outflow']:.1f} | "
            f"{metrics['peak_water_level']:.2f} | "
            f"{metrics['continuity_error_percent']:.2f} | "
            f"{metrics['lag_seconds'] / 3600.0:.2f} | "
            f"{metrics['stability_score']:.1f} |"
        )

    lines.extend(
        [
            "",
            "## 工程建议",
            "",
            "1. 对实时调度要求较高的场景，优先选择滞后时间短的方法；",
            "2. 若需要严格控制水量守恒，应结合断面序列选择连续性误差最低的方案；",
            "3. 对纵向梯度较大的渠道，可叠加更精细的模型进一步复核。",
        ]
    )

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def simulate_muskingum_series(
    inflows: Iterable[float],
    params: Dict[str, float],
    dt: float,
) -> List[float]:
    """根据给定参数计算马斯京干法的出流时间序列。"""
    V_to_H_func, H_to_Q_func = create_default_physical_relations()
    model = MuskingumModel(
        dt=dt,
        K=params["K"],
        x=params["x"],
        initial_V=15_000.0,
        V_to_H_func=V_to_H_func,
        H_to_Q_func=H_to_Q_func,
    )
    output = []
    for q_in in inflows:
        output.append(model.step(q_in)["Q_out"])
    return output


def plot_optimization_comparison(
    time_hours: np.ndarray,
    observed: Iterable[float],
    initial_guess: Iterable[float],
    optimized: Iterable[float],
    output_dir: Path,
    timestamp: str,
) -> Path:
    """绘制参数优化前后的出流对比图。"""
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(time_hours, observed, label="观测出流", linewidth=2.2, color="#111827")
    ax.plot(time_hours, initial_guess, label="初始参数模拟", linewidth=1.8, linestyle="--", color="#f97316")
    ax.plot(time_hours, optimized, label="优化参数模拟", linewidth=1.8, linestyle="-.", color="#2563eb")
    ax.set_xlabel("时间（小时）")
    ax.set_ylabel("流量（m3/s）")
    ax.set_title("马斯京干法参数优化前后出流对比")
    ax.grid(alpha=0.3, linestyle="--", linewidth=0.6)
    ax.legend(loc="best")
    fig.tight_layout()

    plot_path = output_dir / f"optimization_flow_comparison_{timestamp}.png"
    fig.savefig(plot_path, dpi=220)
    plt.close(fig)
    return plot_path


def plot_parameter_sensitivity(
    sensitivity: Dict[str, float],
    output_dir: Path,
    timestamp: str,
) -> Path:
    """绘制参数敏感性柱状图。"""
    fig, ax = plt.subplots(figsize=(6, 4))
    labels = list(sensitivity.keys())
    values = [sensitivity[label] for label in labels]
    ax.bar(labels, values, color=["#2563eb", "#f97316"])
    ax.set_ylabel("敏感度绝对值")
    ax.set_title("参数敏感性分析")
    ax.grid(alpha=0.2, linestyle="--", axis="y")
    fig.tight_layout()

    plot_path = output_dir / f"parameter_sensitivity_{timestamp}.png"
    fig.savefig(plot_path, dpi=220)
    plt.close(fig)
    return plot_path


def write_optimization_summary(
    artefacts: Dict[str, Path],
    flood_hint: Dict[str, float],
    design_hint: Dict[str, float],
    optimized_params: Dict[str, float],
    objective_value: float,
    comparison_plot: Path,
    sensitivity_plot: Path,
) -> Path:
    """根据参数优化结果生成中文补充说明。"""
    timestamp = artefacts["data"].stem.split("_")[-1]
    auto_report = artefacts.get("report")
    extra_report = artefacts["data"].parent / f"optimization_summary_{timestamp}.md"

    lines = [
        "# 马斯京干法参数优化补充说明",
        "",
        f"- 数据文件：`{artefacts['data'].name}`",
        f"- 自动生成报告：`{auto_report.name if auto_report else '（未提供）'}`",
        f"- 出流对比图：`{comparison_plot.name}`",
        f"- 参数敏感性图：`{sensitivity_plot.name}`",
        "",
        "## 参数推荐与优化结果",
        "",
        "| 场景 | K (s) | x | 说明 |",
        "| --- | --- | --- | --- |",
        f"| 洪水预报推荐 | {flood_hint['K']:.0f} | {flood_hint['x']:.3f} | 追求快速响应 |",
        f"| 工程设计推荐 | {design_hint['K']:.0f} | {design_hint['x']:.3f} | 更注重稳定性 |",
        f"| 优化结果 | {optimized_params['K']:.1f} | {optimized_params['x']:.3f} | 目标函数值 {objective_value:.6f} |",
        "",
        "## 建议",
        "",
        "1. 可将优化结果作为当前工况的默认参数，并结合后续实测进行滚动修正；",
        "2. 当来流过程发生显著变化时，可根据敏感性分析优先调整 K 值；",
        "3. 建议分别对设计洪水及非常规工况开展复核，确保安全裕度充足。",
    ]

    extra_report.write_text("\n".join(lines), encoding="utf-8")
    return extra_report