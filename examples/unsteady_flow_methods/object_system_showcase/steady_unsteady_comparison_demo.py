"""
综合恒定-非恒定流示例脚本

恒定流部分：
- 构建 20 km 渠道（2 km 一个断面），覆盖多种断面形式与坡度组合；
- 针对多组流量/下游水位边界条件执行恒定流计算；
- 基于圣维南恒定流解生成水面线、断面形态与多指标诊断图；
- 输出包含水系统拓扑信息、断面详细数据及图件路径的结果文件。

非恒定流部分将在后续步骤填充。
"""

import importlib.util
import json
import math
import sys
from dataclasses import dataclass
from itertools import product
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import gridspec
from waternet.objects.conveyance import ChannelObject
from waternet.models.simplified_saint_venant import SimplifiedSaintVenantModel
from waternet.utils.output_manager import ensure_output_tree
from waternet.utils.demo_reporting import plot_method_time_series


for stream in (sys.stdout, sys.stderr):
    try:
        if stream and getattr(stream, "encoding", "").lower() != "utf-8":
            stream.reconfigure(encoding="utf-8")
    except AttributeError:
        continue


def _load_cross_section_plotter():
    """按需加载断面时间序列绘图函数，避免修改原示例目录结构。"""
    module_path = Path(__file__).resolve().parents[2] / "water_network_cross_sections_validation.py"
    spec = importlib.util.spec_from_file_location("cross_section_plotter", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载断面时间序列绘图模块。")
    module = importlib.util.module_from_spec(spec)
    return module.create_cross_section_time_series_plots


create_cross_section_time_series_plots = _load_cross_section_plotter()



@dataclass(frozen=True)
class CrossSectionPattern:
    """用于描述断面形态参数的简单数据类。"""

    name: str
    shape_type: str
    bottom_width: float
    side_slope: float
    roughness: float


@dataclass(frozen=True)
class ChannelVariant:
    """渠道变体配置，体现坡度与断面组合差异。"""

    key: str
    display_name: str
    slope: float
    downstream_bed_elevation: float
    base_roughness: float
    patterns: Sequence[CrossSectionPattern]



CHANNEL_VARIANTS: Tuple[ChannelVariant, ...] = (
    ChannelVariant(
        key="gentle_mixed",
        display_name="缓坡复合断面渠道",
        slope=2.0e-4,
        downstream_bed_elevation=88.0,
        base_roughness=0.028,
        patterns=(
            CrossSectionPattern("梯形窄底", "trapezoidal", bottom_width=20.0, side_slope=1.5, roughness=0.027),
            CrossSectionPattern("矩形堤槽", "rectangular", bottom_width=18.0, side_slope=0.0, roughness=0.025),
            CrossSectionPattern("梯形宽底", "trapezoidal", bottom_width=24.0, side_slope=2.0, roughness=0.029),
        ),
    ),
    ChannelVariant(
        key="transition_rect",
        display_name="中坡矩形-梯形复合渠道",
        slope=3.5e-4,
        downstream_bed_elevation=88.0,
        base_roughness=0.027,
        patterns=(
            CrossSectionPattern("矩形加固", "rectangular", bottom_width=16.0, side_slope=0.0, roughness=0.024),
            CrossSectionPattern("梯形缓坡", "trapezoidal", bottom_width=22.0, side_slope=1.2, roughness=0.027),
        ),
    ),
    ChannelVariant(
        key="steep_wide",
        display_name="陡坡大断面渠道",
        slope=5.0e-4,
        downstream_bed_elevation=88.0,
        base_roughness=0.029,
        patterns=(
            CrossSectionPattern("梯形深槽", "trapezoidal", bottom_width=26.0, side_slope=1.8, roughness=0.030),
            CrossSectionPattern("矩形超宽", "rectangular", bottom_width=24.0, side_slope=0.0, roughness=0.027),
            CrossSectionPattern("梯形护底", "trapezoidal", bottom_width=22.0, side_slope=2.4, roughness=0.031),
        ),
    ),
)



def build_cross_sections(variant: ChannelVariant) -> List[Dict[str, float]]:
    """根据变体配置生成 2 km 间隔的断面列表。"""
    sections: List[Dict[str, float]] = []
    stations = [idx * SECTION_SPACING for idx in range(int(CHANNEL_LENGTH // SECTION_SPACING) + 1)]
    upstream_bed = variant.downstream_bed_elevation + variant.slope * CHANNEL_LENGTH

    for idx, station in enumerate(stations):
        pattern = variant.patterns[idx % len(variant.patterns)]
        ratio = station / CHANNEL_LENGTH
        elevation = upstream_bed - ratio * (upstream_bed - variant.downstream_bed_elevation)
        sections.append(
            {
                "station": float(station),
                "elevation": float(elevation),
                "shape_type": pattern.shape_type,
                "bottom_width": pattern.bottom_width,
                "side_slope": pattern.side_slope,
                "roughness": pattern.roughness,
                "label": pattern.name,
            }

    return sections


def build_channel_config(variant: ChannelVariant, cross_sections: Sequence[Dict[str, float]]) -> Dict[str, object]:
    """构建 ChannelObject 所需的完整配置。"""
    avg_width = sum(section["bottom_width"] for section in cross_sections) / len(cross_sections)
    config = {
        "object_definition": {
            "object_id": f"demo_{variant.key}",
            "object_type": "channel",
            "name": variant.display_name,
            "description": "用于恒定/非恒定流对比分析的示例渠道",
        },
        "basic_properties": {
            "length": CHANNEL_LENGTH,
            "average_width": avg_width,
            "base_elevation": variant.downstream_bed_elevation,
            "slope": variant.slope,
            "roughness": variant.base_roughness,
            "time_step": 900.0,
            "initial_volume": 6.5e5,
            "initial_flow": STEADY_FLOWS[0],
        },
        "geometry_definition": {
            "cross_sections": list(cross_sections),
        },
        "simulation_preferences": {
            "default_method": "saint_venant_simplified",
            "enable_twin": False,
        },
            "K": 2_400.0,
            "x": 0.10,
        },
    }
    return config


def compute_section_geometry(section: Dict[str, float], water_level: float) -> Tuple[float, float, float]:
    """计算断面水深、面积及水面宽。"""
    depth = max(0.0, water_level - section["elevation"])
    bottom_width = section["bottom_width"]
    side_slope = section["side_slope"]

    if section["shape_type"] == "rectangular" or abs(side_slope) < 1e-6:
        area = bottom_width * depth
        top_width = bottom_width
    else:
        area = depth * (bottom_width + side_slope * depth)
        top_width = bottom_width + 2 * side_slope * depth

    area = max(area, 1e-6)
    return depth, area, top_width


def plot_key_cross_section_shapes(
    cross_sections: Sequence[Dict[str, float]],
    water_levels: Sequence[float],
    case_name: str,
    output_dir: Path,
) -> Path:
    """绘制具有代表性的断面形状（展示断面形式变化）。"""
    output_dir.mkdir(parents=True, exist_ok=True)

    representative_indices: List[int] = []
    seen_patterns: set = set()
    for idx, section in enumerate(cross_sections):
        pattern_key = (
            section["shape_type"],
            round(section["bottom_width"], 3),
            round(section["side_slope"], 3),
        if pattern_key not in seen_patterns:
            seen_patterns.add(pattern_key)
            representative_indices.append(idx)

    if representative_indices[-1] != len(cross_sections) - 1:
        representative_indices.append(len(cross_sections) - 1)

    cols = len(representative_indices)
    fig, axes = plt.subplots(1, cols, figsize=(4.2 * cols, 4.2), sharey=True)
    if cols == 1:
        axes = [axes]

    for ax, idx in zip(axes, representative_indices):
        section = cross_sections[idx]
        water_level = float(water_levels[idx])
        bottom_elev = section["elevation"]
        depth = max(0.0, water_level - bottom_elev)

        bottom_width = section["bottom_width"]
        side_slope = section["side_slope"]
        half_bottom = bottom_width / 2.0

        if section["shape_type"] == "rectangular" or abs(side_slope) < 1e-6:
            left_top = -half_bottom
            right_top = half_bottom
        else:
            side_extension = side_slope * depth
            left_top = -half_bottom - side_extension
            right_top = half_bottom + side_extension

        channel_x = [left_top, -half_bottom, half_bottom, right_top]
        channel_y = [water_level, bottom_elev, bottom_elev, water_level]
        ax.plot(channel_x, channel_y, color="#444", linewidth=2.0)
        ax.fill_between(channel_x, channel_y, bottom_elev - 0.5, color="#d1d5db", alpha=0.6)

        water_x = [left_top, right_top]
        water_y = [water_level, water_level]
        ax.fill_between([left_top, right_top], [bottom_elev, bottom_elev], water_y, color="#93c5fd", alpha=0.7)
        ax.plot(water_x, water_y, color="#1d4ed8", linewidth=2.0)

        ax.set_title(
            f"{section.get('label', '断面')} (x={section.get('station', 0)/1000:.1f} km)",
            fontsize=11,
        ax.set_xlabel("横向距离 (m)")
        ax.grid(alpha=0.3, linestyle="--", linewidth=0.6)

        ax.set_xlim(min(left_top * 1.1, -half_bottom * 1.5), max(right_top * 1.1, half_bottom * 1.5))
        ax.set_ylim(bottom_elev - depth * 0.2 - 0.5, water_level + depth * 0.3 + 0.5)

    axes[0].set_ylabel("高程 (m)")
    fig.suptitle(f"{case_name} 关键断面形状", fontsize=14)
    fig.tight_layout()

    save_path = output_dir / f"{case_name}_shape_variations.svg"
    fig.savefig(save_path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return save_path


def plot_cross_section_grid(
    cross_sections: Sequence[Dict[str, float]],
    water_levels: Sequence[float],
    velocities: Sequence[float],
    case_name: str,
    output_dir: Path,
) -> Path:
    """绘制所有断面的小 multiples，方便比较不同形状。"""
    output_dir.mkdir(parents=True, exist_ok=True)

    depths = [max(0.0, wl - sec["elevation"]) for wl, sec in zip(water_levels, cross_sections)]
    max_depth = max(depths) if depths else 1.0
    max_half_span = max(
        sec["bottom_width"] / 2.0 + max_depth * max(sec["side_slope"], 0.0) for sec in cross_sections
    )

    cols = min(4, max(1, int(math.ceil(math.sqrt(len(cross_sections))))))
    rows = int(math.ceil(len(cross_sections) / cols))

    fig, axes = plt.subplots(rows, cols, figsize=(4.0 * cols, 3.5 * rows), sharey=True)
    axes = axes.flatten() if isinstance(axes, np.ndarray) else [axes]

    for ax in axes[len(cross_sections) :]:
        ax.axis("off")

    for ax, section, water_level, depth, velocity in zip(axes, cross_sections, water_levels, depths, velocities):
        bottom_elev = section["elevation"]
        bottom_width = section["bottom_width"]
        side_slope = section["side_slope"]
        half_bottom = bottom_width / 2.0

        if section["shape_type"] == "rectangular" or abs(side_slope) < 1e-6:
            left_top = -half_bottom
            right_top = half_bottom
        else:
            side_extension = side_slope * depth
            left_top = -half_bottom - side_extension
            right_top = half_bottom + side_extension

        channel_x = [left_top, -half_bottom, half_bottom, right_top]
        channel_y = [water_level, bottom_elev, bottom_elev, water_level]
        ax.plot(channel_x, channel_y, color="#374151", linewidth=1.8)
        ax.fill_between(channel_x, channel_y, bottom_elev - max_depth * 0.1, color="#d1d5db", alpha=0.6)

        ax.axhline(water_level, color="#1d4ed8", linewidth=1.6)
        ax.fill_between([left_top, right_top], [bottom_elev, bottom_elev], [water_level, water_level], color="#93c5fd", alpha=0.6)

        ax.set_xlim(-max_half_span * 1.1, max_half_span * 1.1)
        ax.set_ylim(bottom_elev - max_depth * 0.3, bottom_elev + max_depth * 1.3)

        label = section.get("label", "")
        station_km = section.get("station", 0.0) / 1000.0
        ax.set_title(f"{label} (x={station_km:.1f} km)", fontsize=10, color="#111827")
        ax.grid(alpha=0.25, linestyle="--")

        ax.text(
            0.0,
            water_level + max_depth * 0.05,
            f"H={water_level:.2f} m\nv={velocity:.2f} m/s",
            ha="center",
            va="bottom",
            fontsize=9,
            color="#111827",
            bbox=dict(boxstyle="round,pad=0.25", facecolor="white", alpha=0.85),

        ax.set_xlabel("横向距离 (m)", fontsize=9)

    axes[0].set_ylabel("高程 (m)", fontsize=9)
    fig.suptitle(f"{case_name} 全断面水位/流速对比", fontsize=14, color="#111827")
    fig.tight_layout()

    save_path = output_dir / f"{case_name}_cross_sections.svg"
    fig.savefig(save_path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return save_path


def plot_longitudinal_diagnostics(
    distances: Sequence[float],
    bed_elevations: Sequence[float],
    water_levels: Sequence[float],
    velocities: Sequence[float],
    depths: Sequence[float],
    froude: Sequence[float],
    case_name: str,
    output_dir: Path,
) -> Path:
    """绘制纵向水位/流速/水深/弗劳德数诊断图。"""
    output_dir.mkdir(parents=True, exist_ok=True)

    x_km = np.array(distances) / 1000.0
    bed = np.array(bed_elevations)
    water = np.array(water_levels)
    vel = np.array(velocities)
    dep = np.array(depths)
    fr = np.array(froude)

    fig, axes = plt.subplots(4, 1, figsize=(10, 12), sharex=True)

    axes[0].plot(x_km, bed, color="#6b7280", linewidth=1.5, label="渠底")
    axes[0].plot(x_km, water, color="#2563eb", linewidth=1.8, label="水面")
    axes[0].fill_between(x_km, bed, water, color="#93c5fd", alpha=0.5)
    axes[0].set_ylabel("高程 (m)")
    axes[0].set_title(f"{case_name} 水面线与渠底")
    axes[0].grid(alpha=0.3, linestyle="--")
    axes[0].legend(loc="best")

    axes[1].plot(x_km, vel, color="#f97316", linewidth=1.8)
    axes[1].set_ylabel("流速 (m/s)")
    axes[1].set_title("流速分布")
    axes[1].grid(alpha=0.3, linestyle="--")

    axes[2].plot(x_km, dep, color="#10b981", linewidth=1.8)
    axes[2].set_ylabel("水深 (m)")
    axes[2].set_title("水深分布")
    axes[2].grid(alpha=0.3, linestyle="--")

    axes[3].plot(x_km, fr, color="#8b5cf6", linewidth=1.8)
    axes[3].axhline(1.0, color="#ef4444", linestyle="--", linewidth=1.2, label="Fr=1")
    axes[3].set_ylabel("弗劳德数 (-)")
    axes[3].set_xlabel("距离 (km)")
    axes[3].set_title("弗劳德数分布")
    axes[3].grid(alpha=0.3, linestyle="--")
    axes[3].legend(loc="best")

    fig.suptitle(f"{case_name} 纵向水力诊断", fontsize=15)
    fig.tight_layout(rect=[0, 0.02, 1, 0.98])

    save_path = output_dir / f"{case_name}_longitudinal_diagnostics.svg"
    fig.savefig(save_path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return save_path


def plot_multi_scenario_overview(
    variant: ChannelVariant,
    cross_sections: Sequence[Dict[str, float]],
    scenario_entries: Sequence[Dict[str, object]],
    output_dir: Path,
) -> Path:
    """绘制多工况纵向指标对比图。"""
    output_dir.mkdir(parents=True, exist_ok=True)
    distances = np.array([section["station"] for section in cross_sections]) / 1000.0
    bed = np.array([section["elevation"] for section in cross_sections])

    fig = plt.figure(figsize=(11, 10))
    gs = gridspec.GridSpec(3, 1, figure=fig, hspace=0.25)

    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[1, 0], sharex=ax1)
    ax3 = fig.add_subplot(gs[2, 0], sharex=ax1)

    ax1.plot(distances, bed, color="#6b7280", linewidth=1.4, label="渠底")
    colors = plt.cm.viridis(np.linspace(0.1, 0.9, len(scenario_entries)))

    for color, scenario in zip(colors, scenario_entries):
        water = np.array(scenario["profile_data"]["water_levels"])
        vel = np.array(scenario["profile_data"]["velocities"])
        fr = np.array(scenario["profile_data"]["froude_numbers"])
        ax1.plot(distances, water, color=color, linewidth=1.6, label=scenario["name"])
        ax2.plot(distances, vel, color=color, linewidth=1.6)
        ax3.plot(distances, fr, color=color, linewidth=1.6)

    ax1.fill_between(distances, bed, np.min([s["profile_data"]["water_levels"] for s in scenario_entries], axis=0), color="#e5e7eb", alpha=0.4)
    ax1.set_ylabel("高程 (m)")
    ax1.set_title(f"{variant.display_name} 水面线对比")
    ax1.grid(alpha=0.3, linestyle="--")
    ax1.legend(loc="best", fontsize=9)

    ax2.set_ylabel("流速 (m/s)")
    ax2.set_title("流速分布对比")
    ax2.grid(alpha=0.3, linestyle="--")

    ax3.set_ylabel("弗劳德数 (-)")
    ax3.set_xlabel("距离 (km)")
    ax3.set_title("弗劳德数分布对比")
    ax3.axhline(1.0, color="#ef4444", linestyle="--", linewidth=1.0)
    ax3.grid(alpha=0.3, linestyle="--")

    fig.suptitle(f"{variant.display_name} 多工况纵向指标对比", fontsize=15)
    fig.tight_layout(rect=[0, 0.02, 1, 0.97])

    path = output_dir / f"{variant.key}_scenario_overview.svg"
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return path


def write_steady_report(
    variant: ChannelVariant,
    scenario_entries: Sequence[Dict[str, object]],
    overview_plot: Path,
    output_dir: Path,
) -> Path:
    """基于计算结果生成 Markdown 报告。"""
    output_dir.mkdir(parents=True, exist_ok=True)

    lines = [
        "",
        f"- 渠道长度：{CHANNEL_LENGTH/1000:.1f} km",
        f"- 断面数量：{len(scenario_entries[0]['profile_data']['distances']) if scenario_entries else 0}",
        f"- 概览图：`{overview_plot.name}`",
        "",
        "| 工况 | 流量 (m³/s) | 下游水位 (m) | 水头降 (m) | 最大水深 (m) | 最大流速 (m/s) | 最大 Fr |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]

    for scenario in scenario_entries:
        metrics = scenario["hydraulic_analysis"]
        lines.append(
            f"| {scenario['name']} | {scenario['flow']:.1f} | {scenario['downstream_level']:.2f} | "
            f"{metrics['total_head_loss']:.2f} | {metrics['max_depth']:.2f} | {metrics['max_velocity']:.2f} | "
            f"{metrics['max_froude']:.2f} |"

    lines.extend(
        [
            "",
            f"- 多工况纵向对比：`{overview_plot.name}`",
            "- 各工况的纵向诊断图与断面图详见 `plots/<variant>/...` 目录。",
        ]
    )

    report_path = output_dir / f"{variant.key}_steady_report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def enumerate_flow_level_cases() -> List[Dict[str, float]]:
    """组合流量与下游水位，形成恒定流工况。"""
    cases: List[Dict[str, float]] = []
    for idx, (flow, level) in enumerate(product(STEADY_FLOWS, TAIL_LEVELS), start=1):
        cases.append(
            {
                "name": f"工况{idx}_Q{int(flow)}_Hd{level:.2f}",
                "flow": flow,
                "downstream_level": level,
            }
    return cases



def run_steady_analysis(output_root: Path) -> List[Dict[str, object]]:
    """执行恒定流多情景分析，返回结果摘要。"""
    steady_root = output_root / "steady_flow"
    dirs = ensure_output_tree(steady_root, ("data", "plots", "reports"))

    flow_level_cases = enumerate_flow_level_cases()
    variant_summaries: List[Dict[str, object]] = []

    for variant in CHANNEL_VARIANTS:
        cross_sections = build_cross_sections(variant)
        channel_config = build_channel_config(variant, cross_sections)

        variant_plot_dir = dirs["plots"] / variant.key
        variant_report_dir = dirs["reports"] / variant.key
        variant_data_dir = dirs["data"] / variant.key
        for folder in (variant_plot_dir, variant_report_dir, variant_data_dir):
            folder.mkdir(parents=True, exist_ok=True)

        channel = ChannelObject(f"channel_{variant.key}", config=channel_config)

        scenario_entries: List[Dict[str, object]] = []

        distances = [section["station"] for section in cross_sections]
        bottom_elevations = [section["elevation"] for section in cross_sections]

        for case in flow_level_cases:
            channel.set_upstream_boundary(flow=case["flow"])
            channel.set_downstream_boundary(level=case["downstream_level"])
            steady_result = channel.solve_steady_flow()

            detailed = steady_result.get("detailed_results", {})
            if not detailed:
                continue

            water_levels = [
                float(detailed.get(f"H_section_{idx}", steady_result.get("water_level", bottom_elevations[idx] + 1.0)))
                for idx in range(len(cross_sections))
            ]

            segment_flows = [
                float(detailed.get(f"Q_seg_{idx}", steady_result.get("outflow", case["flow"])))
                for idx in range(max(len(cross_sections) - 1, 1))
            ]
            section_flows: List[float] = []
            for idx in range(len(cross_sections)):
                if idx < len(segment_flows):
                    section_flows.append(segment_flows[idx])
                else:
                    section_flows.append(segment_flows[-1] if segment_flows else steady_result.get("outflow", case["flow"]))

            depths: List[float] = []
            velocities: List[float] = []
            froude_numbers: List[float] = []
            top_widths: List[float] = []
            section_records: List[Dict[str, float]] = []

            for idx, section in enumerate(cross_sections):
                water_level = water_levels[idx]
                depth, area, top_width = compute_section_geometry(section, water_level)
                depth = max(depth, 0.0)
                flow = section_flows[idx]
                velocity = flow / area if area > 1e-6 else 0.0
                froude = velocity / math.sqrt(9.81 * max(depth, 1e-6)) if depth > 1e-6 else 0.0

                depths.append(depth)
                velocities.append(velocity)
                froude_numbers.append(froude)
                top_widths.append(top_width)

                section_records.append(
                    {
                        "station": distances[idx],
                        "bed_elevation": bottom_elevations[idx],
                        "water_level": water_level,
                        "depth": depth,
                        "flow": flow,
                        "velocity": velocity,
                        "froude": froude,
                    }
        
            profile_data = {
                "distances": distances,
                "water_levels": water_levels,
                "bottom_elevations": bottom_elevations,
                "depths": depths,
                "velocities": velocities,
                "froude_numbers": froude_numbers,
                "flows": section_flows,
                "top_widths": top_widths,
                "method": "saint_venant_section_results",
                "downstream_boundary": case["downstream_level"],
            }

            total_head_loss = water_levels[0] - water_levels[-1]
            max_froude = max(froude_numbers) if froude_numbers else 0.0
            min_froude = min(froude_numbers) if froude_numbers else 0.0
            avg_froude = float(sum(froude_numbers) / len(froude_numbers)) if froude_numbers else 0.0

            if all(fr < 1.0 for fr in froude_numbers):
                flow_regime = "subcritical"
            elif all(fr > 1.0 for fr in froude_numbers if fr > 0):
                flow_regime = "supercritical"
            else:
                flow_regime = "mixed"

            hydraulic_analysis = {
                "flow_regime": flow_regime,
                "total_head_loss": total_head_loss,
                "channel_length": CHANNEL_LENGTH,
                "max_depth": max(depths) if depths else 0.0,
                "min_depth": min(depths) if depths else 0.0,
                "max_velocity": max(velocities) if velocities else 0.0,
                "min_velocity": min(velocities) if velocities else 0.0,
                "max_froude": max_froude,
                "min_froude": min_froude,
                "avg_froude": avg_froude,
            }

            longitudinal_plot = plot_longitudinal_diagnostics(
                distances,
                bottom_elevations,
                water_levels,
                velocities,
                depths,
                froude_numbers,
                case["name"],
                variant_plot_dir / "longitudinal",
            )
            cross_plot = plot_cross_section_grid(
                cross_sections,
                water_levels,
                velocities,
                case["name"],
                variant_plot_dir / "cross_section_grid",
            )
            shape_plot = plot_key_cross_section_shapes(
                cross_sections,
                water_levels,
                case["name"],
                variant_plot_dir / "section_shapes",
            )

            scenario_entries.append(
                {
                    "name": case["name"],
                    "flow": case["flow"],
                    "downstream_level": case["downstream_level"],
                    "steady_result": steady_result,
                    "section_details": section_records,
                    "profile_data": profile_data,
                    "hydraulic_analysis": hydraulic_analysis,
                    "cross_section_plot": str(cross_plot),
                    "longitudinal_plot": str(longitudinal_plot),
                    "shape_plot": str(shape_plot),
                }
            )
    
        if not scenario_entries:
            continue

        overview_plot = plot_multi_scenario_overview(
            variant,
            cross_sections,
            scenario_entries,
            variant_plot_dir,
        )
        report_path = write_steady_report(
            variant,
            scenario_entries,
            overview_plot,
            variant_report_dir,
        )

        


        variant_summary = {
            "variant": {
                "key": variant.key,
                "name": variant.display_name,
                "slope": variant.slope,
                "section_count": len(cross_sections),
                "nodes": len(cross_sections),
                "base_roughness": variant.base_roughness,
            },
            "topology": {
                "stations_m": [section["station"] for section in cross_sections],
                "bed_elevations_m": [section["elevation"] for section in cross_sections],
                "section_labels": [section["label"] for section in cross_sections],
                "bottom_widths_m": [section["bottom_width"] for section in cross_sections],
                "side_slopes": [section["side_slope"] for section in cross_sections],
                "roughness": [section["roughness"] for section in cross_sections],
                "shape_types": [section["shape_type"] for section in cross_sections],
            },
            "artefacts": {
                "scenario_overview_plot": str(overview_plot),
                "report": str(report_path),
                "shape_directory": str((variant_plot_dir / "section_shapes").resolve()),
            },
            "scenarios": scenario_entries,
        }

        summary_path = variant_data_dir / f"{variant.key}_steady_summary.json"
        summary_path.write_text(json.dumps(variant_summary, indent=2, ensure_ascii=False), encoding="utf-8")

        variant_summary["summary_path"] = str(summary_path)
        variant_summaries.append(variant_summary)

        print(f"[稳态] {variant.display_name} 结果已导出：{summary_path}")

    return variant_summaries



def run_unsteady_analysis(
    output_root: Path,
    steady_summaries: Iterable[Dict[str, object]],
) -> Dict[str, object]:
    """
    基于恒定流结果执行多种分布式方法的非恒定流对比分析。

    采用 SimplifiedSaintVenantModel 的不同近似模式（准静态波、扩散波、运动波）模拟
    上游流量涨落过程，输出各断面时间序列图、方法对比图与数据包。
    """

    unsteady_root = output_root / "unsteady_flow"
    dirs = ensure_output_tree(unsteady_root, ("data", "plots", "reports"))

    summaries = list(steady_summaries)
    if not summaries:
        return {"success": False, "message": "缺少恒定流结果，无法执行非恒定流分析。"}

    variant_lookup = {variant.key: variant for variant in CHANNEL_VARIANTS}
    selected_variants: List[Tuple[Dict[str, object], ChannelVariant]] = []
    for summary in summaries:
        variant_key = summary.get("variant", {}).get("key")
        variant_obj = variant_lookup.get(variant_key)
        if variant_obj is not None:
            selected_variants.append((summary, variant_obj))

    if not selected_variants:
        return {"success": False, "message": "未匹配到可用的渠道变体配置。"}

    boundary_series = {
        "upstream_flows": [120.0, 150.0, 210.0, 250.0, 220.0, 180.0, 150.0, 130.0, 120.0],
        "downstream_levels": [92.6, 92.8, 93.1, 93.4, 93.2, 93.0, 92.85, 92.75, 92.6],
    }
    time_steps = boundary_series["time_steps"]
    time_hours = [t / 3600.0 for t in time_steps]

    method_modes = [
        {"mode": "quasi_static", "name": "准静态波模式"},
        {"mode": "diffusive_wave", "name": "扩散波模式"},
        {"mode": "kinematic_wave", "name": "运动波模式"},
    ]

    overall_payload: Dict[str, object] = {"success": True, "variants": []}

    for summary, variant in selected_variants:
        cross_sections = build_cross_sections(variant)
        channel_config = build_channel_config(variant, cross_sections)
        channel = ChannelObject(f"unsteady_{variant.key}", config=channel_config)
        sections_for_model = channel._prepare_sections_data()

        variant_plot_dir = dirs["plots"] / variant.key
        variant_report_dir = dirs["reports"] / variant.key
        variant_data_dir = dirs["data"] / variant.key
        for folder in (variant_plot_dir, variant_report_dir, variant_data_dir):
            folder.mkdir(parents=True, exist_ok=True)

        comparison_methods: Dict[str, Dict[str, object]] = {}
        method_summaries: List[Dict[str, object]] = []

        for method in method_modes:
            model = SimplifiedSaintVenantModel(
                name=f"{variant.key}_{method['mode']}",
                upstream_node="upstream",
                downstream_node="downstream",
                sections=sections_for_model,
                approximation_mode=method["mode"],
                enable_performance_monitoring=False,
    
            initial_flow = boundary_series["upstream_flows"][0]
            initial_level = boundary_series["downstream_levels"][0]
            model.compute_with_approximation(initial_flow, initial_level, mode=method["mode"])

            cross_section_series = {
                f"断面{idx + 1}": {
                    "time": [],
                    "water_level": [],
                    "flow_rate": [],
                    "velocity": [],
                    "froude_number": [],
                }
                for idx in range(len(cross_sections))
            }

            time_records: List[Dict[str, float]] = []
            upstream_levels: List[float] = []
            outflows: List[float] = []
            storage_series: List[float] = []
            characteristic_velocity: List[float] = []

            for idx, (t, q_up) in enumerate(zip(time_steps, boundary_series["upstream_flows"])):
                if idx == 0 and len(time_steps) > 1:
                    dt = max(60.0, time_steps[1] - time_steps[0])
                elif idx == 0:
                    dt = 900.0
                else:
                    dt = max(60.0, time_steps[idx] - time_steps[idx - 1])

                downstream_level = (
                    boundary_series["downstream_levels"][idx]
                    if idx < len(boundary_series["downstream_levels"])
                    else boundary_series["downstream_levels"][-1]
        
                step_result = model.step(Q_in=q_up, downstream_level=downstream_level, dt=dt)
                q_out = float(step_result.get("Q_out", q_up))
                upstream_level = float(step_result.get("H_out", cross_sections[0]["elevation"] + 1.0))
                storage = float(step_result.get("V", 0.0))

                storage_series.append(storage)
                upstream_levels.append(upstream_level)
                outflows.append(q_out)
                time_records.append(
                    {
                        "time": time_hours[idx],
                        "Q_in": q_up,
                        "Q_out": q_out,
                        "storage": storage,
                    }
        
                hydraulic = model.compute_with_approximation(q_up, downstream_level, mode=method["mode"])
                hydro = hydraulic.get("hydraulic_results", {})
                segment_count = len(cross_sections) - 1

                for sec_idx, section in enumerate(cross_sections):
                    section_name = f"断面{sec_idx + 1}"
                    level = float(hydro.get(f"H_section_{sec_idx}", section["elevation"] + 1.0))
                    depth, area, _ = compute_section_geometry(section, level)

                    if segment_count <= 0:
                        flow_val = q_out
                    elif sec_idx == 0:
                        flow_val = float(hydro.get("Q_seg_0", q_up))
                    elif sec_idx >= segment_count:
                        flow_val = float(hydro.get(f"Q_seg_{segment_count - 1}", q_out))
                    else:
                        left = float(hydro.get(f"Q_seg_{sec_idx - 1}", q_up))
                        right = float(hydro.get(f"Q_seg_{sec_idx}", q_out))
                        flow_val = 0.5 * (left + right)

                    velocity_val = flow_val / area if area > 0 else 0.0
                    froude_val = velocity_val / math.sqrt(9.81 * max(depth, 1e-3))

                    series = cross_section_series[section_name]
                    series["time"].append(time_hours[idx])
                    series["water_level"].append(level)
                    series["flow_rate"].append(flow_val)
                    series["velocity"].append(velocity_val)
                    series["froude_number"].append(froude_val)

                characteristic_velocity.append(cross_section_series["断面1"]["velocity"][-1])

            method_output_dir = (variant_plot_dir / method["mode"])
            section_plot_dir = method_output_dir / "sections"
            method_output_dir.mkdir(parents=True, exist_ok=True)
            create_cross_section_time_series_plots(cross_section_series, section_plot_dir)

            inflow_peak_values = boundary_series["upstream_flows"]
            inflow_peak_idx = int(np.argmax(inflow_peak_values))
            outflow_peak_idx = int(np.argmax(outflows)) if outflows else 0
            lag_hours = time_hours[outflow_peak_idx] - time_hours[inflow_peak_idx]
            inflow_peak = max(inflow_peak_values) if inflow_peak_values else 1.0
            peak_outflow = max(outflows) if outflows else 0.0
            damping = ((inflow_peak - peak_outflow) / max(inflow_peak, 1e-6)) * 100.0

            method_summary = {
                "mode": method["mode"],
                "name": method["name"],
                "time_series": time_records,
                "upstream_levels": upstream_levels,
                "outflows": outflows,
                "storage": storage_series,
                "cross_sections": cross_section_series,
                "plots": {
                    "section_directory": str(section_plot_dir),
                },
                "metrics": {
                    "peak_outflow": peak_outflow,
                    "lag_hours": lag_hours,
                    "damping_percent": damping,
                    "final_storage": storage_series[-1] if storage_series else 0.0,
                },
            }
            method_summaries.append(method_summary)

            comparison_methods[method["mode"]] = {
                "config": {"name": method["name"]},
                "time_series": {
                    "water_level": upstream_levels,
                    "outflow": outflows,
                    "velocity": characteristic_velocity,
                },
                "metrics": method_summary["metrics"],
            }

        time_axis = np.array(time_hours)
        combined_plot = plot_method_time_series(
            time_axis,
            comparison_methods,
            variant_plot_dir,
            f"{variant.key}_unsteady",

        variant_summary = {
            "variant": summary["variant"],
            "boundary_series": boundary_series,
            "methods": method_summaries,
            "plots": {
                "method_time_series": str(combined_plot),
            },
        }

        summary_path = variant_data_dir / f"{variant.key}_unsteady_summary.json"
        summary_path.write_text(json.dumps(variant_summary, indent=2, ensure_ascii=False), encoding="utf-8")

        report_lines = [
            "",
            f"- 输入流量峰值: {max(boundary_series['upstream_flows']):.1f} m³/s",
            f"- 分析方法: {', '.join(m['name'] for m in method_modes)}",
            "",
            "| 方法 | 峰值流量 (m³/s) | 滞后时间 (h) | 坦化率 (%) | 末端蓄量 (m³) |",
            "| --- | --- | --- | --- | --- |",
        ]
        for method_summary in method_summaries:
            metrics = method_summary["metrics"]
            report_lines.append(
                f"| {method_summary['name']} | {metrics['peak_outflow']:.1f} | "
                f"{metrics['lag_hours']:.2f} | {metrics['damping_percent']:.1f} | "
                f"{metrics['final_storage']:.0f} |"
    
        report_lines.extend(
            [
                "",
                f"- 综合时间序列: `{Path(combined_plot).name}`",
                "- 各方法断面过程图：见 `sections` 子目录",
            ]

        report_path = variant_report_dir / f"{variant.key}_unsteady_report.md"
        report_path.write_text("\n".join(report_lines), encoding="utf-8")

        variant_summary["report"] = str(report_path)
        overall_payload["variants"].append(
            {
                "summary_path": str(summary_path),
                "report": str(report_path),
                "plots": variant_summary["plots"],
            }

    return overall_payload



def run_demo() -> None:
    base_dir = Path(__file__).resolve().parent
    output_root = base_dir / "outputs" / "steady_unsteady_comparison"
    ensure_output_tree(output_root, ("data", "plots", "reports"))

    print("=== 恒定流多工况对比分析 ===")
    steady_payload = run_steady_analysis(output_root)

    print("\n=== 非恒定流多方法对比（待实现） ===")
    unsteady_payload = None

    summary_path = output_root / "data" / "comparison_overview.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(
            {
                "steady_flow": [
                    {
                        "variant": item["variant"],
                        "summary_path": item.get("summary_path", ""),
                        "artefacts": item.get("artefacts", {}),
                    }
                    for item in steady_payload
                ],
                "unsteady_flow": unsteady_payload,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(f"\n整体概览文件：{summary_path}")


if __name__ == "__main__":
    run_demo()
