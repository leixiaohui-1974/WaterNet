from __future__ import annotations

"""
非恒定流综合分析工具。

本模块提供体量精简但功能完备的分析器，可针对给定的入流过程线
和多种水力演算方法生成标准化的数据/图表/报告组合，便于示例脚本
进行自动校验与复用。
"""

from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path
from typing import Dict, Iterable, List, MutableMapping, Optional, Sequence, Tuple, Union

import matplotlib

matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from ..utils.output_manager import ensure_output_tree, timestamped_path

PathLike = Union[str, Path]


@dataclass
class MethodConfig:
    """用于描述参与对比的水力演算方法。"""

    identifier: str
    name: str
    kind: str
    parameters: Dict[str, float]
    color: str = "#1f77b4"
    linestyle: str = "-"


@dataclass
class ChannelConfig:
    """用于后处理的渠道水力简化描述。"""

    length: float = 5_000.0
    slope: float = 2.0e-4
    roughness: float = 0.025
    bottom_width: float = 15.0
    side_slope: float = 1.0
    base_elevation: float = 95.0
    max_depth: float = 8.0


@dataclass
class AnalysisConfig:
    """与外部接口一致的配置容器。"""

    duration: float = 8 * 3_600.0
    time_step: float = 1_800.0
    boundary_flows: Optional[Sequence[float]] = None
    channel: ChannelConfig = field(default_factory=ChannelConfig)
    methods: Optional[List[MethodConfig]] = None


@dataclass
class MethodSummary:
    """用于存储某一方法的时间序列结果与统计指标。"""

    config: MethodConfig
    outflow: np.ndarray
    water_level: np.ndarray
    velocity: np.ndarray
    metrics: Dict[str, float]

    def to_dict(self) -> Dict[str, object]:
        return {
            "config": {
                "identifier": self.config.identifier,
                "name": self.config.name,
                "kind": self.config.kind,
                "parameters": self.config.parameters,
            },
            "metrics": self.metrics,
            "time_series": {
                "outflow": self.outflow.tolist(),
                "water_level": self.water_level.tolist(),
                "velocity": self.velocity.tolist(),
            },
        }


class UnsteadyFlowAnalyzer:
    """在统一的入流条件下比较多种水力演算方法的表现。"""

    def __init__(self, output_dir: Optional[PathLike] = None) -> None:
        self.output_dir = Path(output_dir) if output_dir else Path.cwd() / "unsteady_flow_outputs"
        subdirs = ensure_output_tree(self.output_dir, ("data", "plots", "reports"))
        self.data_dir = subdirs["data"]
        self.plots_dir = subdirs["plots"]
        self.reports_dir = subdirs["reports"]
        self.config = self._default_config()
        self._rating_curve = self._build_rating_curve(self.config.channel)
        self.latest_result: Optional[Dict[str, object]] = None

    # ------------------------------------------------------------------ 公共接口
    def configure(self, **kwargs: object) -> None:
        """
        更新分析器的配置参数。

        支持的关键字包括：``duration``、``time_step``、``boundary_flows``、
        ``channel``、``methods``。
        """
        for key, value in kwargs.items():
            if not hasattr(self.config, key):
                raise AttributeError(f"Unknown configuration key: {key}")
            setattr(self.config, key, value)

        if isinstance(self.config.channel, ChannelConfig):
            self._rating_curve = self._build_rating_curve(self.config.channel)

    def run_comparison(self, override: Optional[MutableMapping[str, object]] = None) -> Dict[str, object]:
        """执行对比分析并落地数据、图表与报告等成果。"""
        config = self._merge_config(override or {})
        time_axis, inflow = self._build_time_series(config)
        summaries = self._simulate_methods(config, inflow)

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        data_path = timestamped_path(self.data_dir, "analysis_data", ".json", timestamp)
        plot_path = timestamped_path(self.plots_dir, "analysis_plot", ".png", timestamp)
        report_path = timestamped_path(self.reports_dir, "analysis_report", ".md", timestamp)

        self._write_data_bundle(time_axis, inflow, summaries, data_path, config)
        self._create_plot(time_axis, inflow, summaries, plot_path)
        self._write_markdown_report(summaries, report_path, config, data_path, plot_path)

        recommendations = self._derive_recommendations(summaries)
        self.latest_result = {
            "success": True,
            "timestamp": timestamp,
            "methods_analyzed": len(summaries),
            "outputs": {
                "data": str(data_path),
                "plot": str(plot_path),
                "report": str(report_path),
            },
            "recommendations": recommendations,
            "method_summaries": {summary.config.identifier: summary.metrics for summary in summaries},
        }
        return self.latest_result

    def get_method_recommendation(self, application_type: str = "general") -> str:
        """基于最新分析结果返回方法推荐。"""
        if not self.latest_result:
            raise RuntimeError("No analysis has been executed yet.")

        rec = self.latest_result["recommendations"]
        if application_type == "flood_forecasting":
            return rec.get("best_for_speed", rec.get("best_overall", ""))
        if application_type == "engineering_design":
            return rec.get("best_for_accuracy", rec.get("best_overall", ""))
        if application_type == "research":
            return rec.get("best_for_stability", rec.get("best_overall", ""))
        return rec.get("best_overall", "")

    # ------------------------------------------------------------------ 配置辅助函数
    def _default_config(self) -> AnalysisConfig:
        methods = [
            MethodConfig(
                identifier="muskingum_balanced",
                name="Muskingum (K=3600 s, x=0.15)",
                kind="lumped",
                parameters={"K": 3_600.0, "x": 0.15},
                color="#2563eb",
                linestyle="-",
            ),
            MethodConfig(
                identifier="muskingum_fast",
                name="Muskingum (K=2400 s, x=0.10)",
                kind="lumped",
                parameters={"K": 2_400.0, "x": 0.10},
                color="#f97316",
                linestyle="--",
            ),
            MethodConfig(
                identifier="storage_routing",
                name="Storage Routing",
                kind="routing",
                parameters={"storage_coefficient": 0.35},
                color="#10b981",
                linestyle="-.",
            ),
        ]

        default_flows = self._default_inflow_hydrograph(self.config.duration, self.config.time_step) if hasattr(self, "config") else self._default_inflow_hydrograph()

        return AnalysisConfig(
            boundary_flows=default_flows,
            methods=methods,
        )

    def _merge_config(self, override: MutableMapping[str, object]) -> AnalysisConfig:
        cfg = AnalysisConfig(
            duration=self.config.duration,
            time_step=self.config.time_step,
            boundary_flows=self.config.boundary_flows,
            channel=self.config.channel,
            methods=list(self.config.methods or []),
        )
        for key, value in override.items():
            if hasattr(cfg, key):
                setattr(cfg, key, value)

        if cfg.boundary_flows is None:
            cfg.boundary_flows = self._default_inflow_hydrograph(cfg.duration, cfg.time_step)
        cfg.boundary_flows = list(cfg.boundary_flows)

        if cfg.methods:
            cfg.methods = list(cfg.methods)
        else:
            raise ValueError("At least one routing method must be defined.")
        return cfg

    def _default_inflow_hydrograph(
        self,
        duration: Optional[float] = None,
        time_step: Optional[float] = None,
    ) -> np.ndarray:
        base_cfg = getattr(self, "config", None)
        if duration is None:
            duration = base_cfg.duration if base_cfg else 8 * 3_600.0
        if time_step is None:
            time_step = base_cfg.time_step if base_cfg else 1_800.0

        step_count = int(duration / time_step) if time_step else 9
        step_count = max(step_count, 9)
        t = np.linspace(0.0, np.pi, step_count)
        base = 95.0
        perturbation = 25.0 * np.sin(t) ** 1.5
        return base + perturbation

    def _build_time_series(self, config: AnalysisConfig) -> Tuple[np.ndarray, np.ndarray]:
        inflow = np.asarray(config.boundary_flows, dtype=float)
        if inflow.ndim != 1 or inflow.size < 3:
            raise ValueError("Boundary flow series must contain at least three values.")

        dt = config.time_step
        time_axis = np.arange(inflow.size) * dt
        return time_axis, inflow

    # ------------------------------------------------------------------ 数值模拟流程
    def _simulate_methods(self, config: AnalysisConfig, inflow: np.ndarray) -> List[MethodSummary]:
        dt = config.time_step
        summaries: List[MethodSummary] = []

        for method in config.methods or []:
            if method.identifier.startswith("muskingum"):
                outflow = self._simulate_muskingum(inflow, dt, method.parameters)
            else:
                outflow = self._simulate_linear_reservoir(inflow, dt, method.parameters)

            water_level, velocity = self._estimate_hydraulics(outflow)
            metrics = self._compute_metrics(inflow, outflow, water_level, dt)
            summaries.append(MethodSummary(method, outflow, water_level, velocity, metrics))
        return summaries

    @staticmethod
    def _simulate_muskingum(inflow: np.ndarray, dt: float, params: Dict[str, float]) -> np.ndarray:
        K = float(params.get("K", 3_600.0))
        x = float(params.get("x", 0.15))
        if K <= 0.0:
            raise ValueError("Muskingum parameter K must be positive.")
        if not (0.0 <= x <= 0.5):
            raise ValueError("Muskingum parameter x must be between 0 and 0.5.")

        denom = K - K * x + dt / 2.0
        if denom == 0.0:
            raise ValueError("Invalid Muskingum coefficients – denominator is zero.")

        c0 = (-K * x + dt / 2.0) / denom
        c1 = (K * x + dt / 2.0) / denom
        c2 = (K - dt / 2.0) / denom

        outflow = np.zeros_like(inflow)
        outflow[0] = inflow[0]
        for i in range(1, inflow.size):
            outflow[i] = c0 * inflow[i] + c1 * inflow[i - 1] + c2 * outflow[i - 1]
        return outflow

    @staticmethod
    def _simulate_linear_reservoir(inflow: np.ndarray, dt: float, params: Dict[str, float]) -> np.ndarray:
        coeff = float(params.get("storage_coefficient", 0.3))
        coeff = np.clip(coeff, 0.05, 0.95)

        outflow = np.zeros_like(inflow)
        storage = inflow[0] * dt
        outflow[0] = inflow[0]

        for i in range(1, inflow.size):
            storage = storage + (inflow[i] - outflow[i - 1]) * dt
            release = coeff * storage / dt
            outflow[i] = max(0.0, release)
            storage = max(0.0, storage - outflow[i] * dt)
        return outflow

    # ------------------------------------------------------------------ 水力学后处理
    def _build_rating_curve(self, channel: ChannelConfig) -> Tuple[np.ndarray, np.ndarray]:
        h_vals = np.linspace(0.05, channel.max_depth, 600)
        q_vals = np.zeros_like(h_vals)
        n = max(channel.roughness, 1e-4)
        slope = max(channel.slope, 1e-6)
        side = max(channel.side_slope, 0.0)
        beta = np.sqrt(1.0 + side**2)

        for idx, h in enumerate(h_vals):
            area = channel.bottom_width * h + side * h**2
            wetted_perimeter = channel.bottom_width + 2.0 * h * beta
            wetted_perimeter = max(wetted_perimeter, 1e-6)
            hydraulic_radius = area / wetted_perimeter
            q_vals[idx] = (1.0 / n) * area * hydraulic_radius ** (2.0 / 3.0) * slope ** 0.5

        return h_vals, q_vals

    def _estimate_hydraulics(self, discharge: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        h_vals, q_vals = self._rating_curve
        depth = np.interp(discharge, q_vals, h_vals, left=h_vals[0], right=h_vals[-1])
        channel = self.config.channel

        area = channel.bottom_width * depth + channel.side_slope * depth**2
        area = np.maximum(area, 1e-6)
        velocity = discharge / area
        water_level = channel.base_elevation + depth
        return water_level, velocity

    @staticmethod
    def _compute_metrics(inflow: np.ndarray, outflow: np.ndarray, water_level: np.ndarray, dt: float) -> Dict[str, float]:
        volume_in = np.trapz(inflow, dx=dt)
        volume_out = np.trapz(outflow, dx=dt)
        peak_in_idx = int(np.argmax(inflow))
        peak_out_idx = int(np.argmax(outflow))

        if volume_in > 1e-6:
            continuity_error = abs(volume_in - volume_out) / volume_in * 100.0
        else:
            continuity_error = 0.0

        lag_seconds = max(0, peak_out_idx - peak_in_idx) * dt
        damping = (np.max(inflow) - np.max(outflow)) / max(np.max(inflow), 1e-6) * 100.0
        damping = max(damping, 0.0)

        gradient = np.abs(np.diff(outflow, prepend=outflow[0]))
        stability_score = 100.0 - np.percentile(gradient, 95)
        stability_score = max(min(stability_score, 100.0), 0.0)

        return {
            "continuity_error_percent": float(continuity_error),
            "lag_seconds": float(lag_seconds),
            "peak_outflow": float(np.max(outflow)),
            "peak_water_level": float(np.max(water_level)),
            "mean_water_level": float(np.mean(water_level)),
            "damping_percent": float(damping),
            "stability_score": float(stability_score),
            "volume_out": float(volume_out),
        }

    # ------------------------------------------------------------------ 结果持久化工具
    def _write_data_bundle(
        self,
        time_axis: np.ndarray,
        inflow: np.ndarray,
        summaries: Iterable[MethodSummary],
        path: Path,
        config: AnalysisConfig,
    ) -> None:
        summaries_list = list(summaries)
        payload = {
            "metadata": {
                "created_at": datetime.utcnow().isoformat(timespec="seconds"),
                "time_step_seconds": config.time_step,
                "method_count": len(summaries_list),
            },
            "time": time_axis.tolist(),
            "inflow": inflow.tolist(),
            "methods": {},
        }

        for summary in summaries_list:
            payload["methods"][summary.config.identifier] = summary.to_dict()

        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)

    def _create_plot(
        self,
        time_axis: np.ndarray,
        inflow: np.ndarray,
        summaries: Iterable[MethodSummary],
        path: Path,
    ) -> None:
        summaries_list = list(summaries)
        hours = time_axis / 3600.0

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(hours, inflow, label="Inflow", color="#111827", linewidth=2.4)

        for summary in summaries_list:
            ax.plot(
                hours,
                summary.outflow,
                label=summary.config.name,
                color=summary.config.color,
                linestyle=summary.config.linestyle,
                linewidth=1.8,
            )

        ax.set_xlabel("时间（小时）")
        ax.set_ylabel("流量（m3/s）")
        ax.grid(True, linestyle="--", linewidth=0.6, alpha=0.5)
        ax.legend(loc="upper right")
        ax.set_title("非恒定流方法对比")

        fig.tight_layout()
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=200)
        plt.close(fig)

    def _write_markdown_report(
        self,
        summaries: Iterable[MethodSummary],
        report_path: Path,
        config: AnalysisConfig,
        data_path: Path,
        plot_path: Path,
    ) -> None:
        """生成中文 Markdown 报告，便于快速浏览关键指标。"""
        summaries_list = list(summaries)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        duration_str = self._format_duration(config.duration)
        recommendations = self._derive_recommendations(summaries_list)

        lines = [
            "# 非恒定流综合分析报告",
            "",
            f"- 生成时间：{datetime.utcnow().isoformat(timespec='seconds')} UTC",
            f"- 模拟时长：{duration_str}",
            f"- 时间步长：{config.time_step:.0f} s",
            f"- 数据文件：`{data_path.name}`",
            f"- 对比图件：`{plot_path.name}`",
            "",
            "## 方法指标总览",
            "",
            "| 方法 | 峰值流量 (m3/s) | 峰值水位 (m) | 连续性误差 (%) | 滞后时间 (h) | 稳定性评分 |",
            "| --- | --- | --- | --- | --- | --- |",
        ]

        for summary in summaries_list:
            metrics = summary.metrics
            lines.append(
                f"| {summary.config.name} | "
                f"{metrics['peak_outflow']:.1f} | "
                f"{metrics['peak_water_level']:.2f} | "
                f"{metrics['continuity_error_percent']:.2f} | "
                f"{metrics['lag_seconds'] / 3600.0:.2f} | "
                f"{metrics['stability_score']:.1f} |"
            )

        lines.extend(
            [
                "",
                "## 方法推荐",
                "",
                f"- 综合最优：**{recommendations['best_overall']}**",
                f"- 精度优选：**{recommendations['best_for_accuracy']}**",
                f"- 速度优选：**{recommendations['best_for_speed']}**",
                f"- 稳定性优选：**{recommendations['best_for_stability']}**",
            ]
        )

        report_path.write_text("\n".join(lines), encoding="utf-8")


    # ------------------------------------------------------------------ 方法推荐逻辑
    @staticmethod
    def _derive_recommendations(summaries: Iterable[MethodSummary]) -> Dict[str, str]:
        summaries_list = list(summaries)
        if not summaries_list:
            return {
                "best_overall": "",
                "best_for_accuracy": "",
                "best_for_speed": "",
                "best_for_stability": "",
            }

        def pick(metric: str, reverse: bool = False) -> str:
            key = (
                lambda s: s.metrics.get(metric, float("inf"))
                if not reverse
                else -s.metrics.get(metric, 0.0)
            )
            selected = min(summaries_list, key=key)
            return selected.config.name

        best_accuracy = pick("continuity_error_percent")
        best_speed = pick("lag_seconds")
        best_stability = pick("stability_score", reverse=True)

        overall = min(
            summaries_list,
            key=lambda s: s.metrics.get("continuity_error_percent", 0.0)
            + (100.0 - s.metrics.get("stability_score", 0.0)),
        )

        return {
            "best_overall": overall.config.name,
            "best_for_accuracy": best_accuracy,
            "best_for_speed": best_speed,
            "best_for_stability": best_stability,
        }

    @staticmethod
    def _format_duration(duration_seconds: float) -> str:
        hours = duration_seconds / 3600.0
        if hours < 24.0:
            return f"{hours:.1f} h"
        days = hours / 24.0
        return f"{days:.1f} d"
