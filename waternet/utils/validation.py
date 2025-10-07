from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Union

PathLike = Union[str, Path]


@dataclass
class ValidationResult:
    """用于存储生成成果的校验结果。"""

    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Union[int, float, str]] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_analysis_bundle(
    data_path: PathLike,
    plot_path: PathLike,
    report_path: PathLike,
) -> ValidationResult:
    """
    校验分析器生成的标准数据/图表/报告组合。

    主要检查 JSON 结构是否完整，图件是否存在且非空，以及报告是否包含核心段落。
    """
    result = ValidationResult()

    # --- JSON 数据检查 ---------------------------------------------------------
    data_file = Path(data_path)
    if not data_file.exists():
        result.errors.append(f"数据文件缺失: {data_file}")
    else:
        try:
            payload = json.loads(data_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            result.errors.append(f"数据文件不是有效的 JSON: {exc}")
        else:
            required_keys = {"metadata", "time", "inflow", "methods"}
            missing = required_keys - set(payload.keys())
            if missing:
                result.errors.append(f"数据文件缺失 keys: {sorted(missing)}")
            else:
                time_length = len(payload["time"])
                inflow_length = len(payload["inflow"])
                if time_length < 3:
                    result.errors.append("时间序列长度不足三个步长")
                if time_length != inflow_length:
                    result.errors.append("时间序列与入流序列长度不一致")

                methods = payload.get("methods", {})
                if not methods:
                    result.errors.append("数据文件中未记录任何方法结果")
                else:
                    for method_id, entry in methods.items():
                        ts = entry.get("time_series", {})
                        outflow = ts.get("outflow", [])
                        if len(outflow) != time_length:
                            result.errors.append(
                                f"method {method_id} 出流序列长度不匹配: {len(outflow)} != {time_length}"
                            )
                        wl = ts.get("water_level", [])
                        if len(wl) != time_length:
                            result.errors.append(
                                f"method {method_id} 水位序列长度不匹配: {len(wl)} != {time_length}"
                            )
                        vel = ts.get("velocity", [])
                        if len(vel) != time_length:
                            result.errors.append(
                                f"method {method_id} 流速序列长度不匹配: {len(vel)} != {time_length}"
                            )

                    result.details["method_count"] = len(methods)
                    result.details["time_steps"] = time_length

    # --- 图件检查 --------------------------------------------------------------
    plot_file = Path(plot_path)
    if not plot_file.exists():
        result.errors.append(f"图件不存在: {plot_file}")
    else:
        if plot_file.stat().st_size < 2_000:
            result.warnings.append(f"图件文件体积过小，可能为空: {plot_file}")

    # --- 报告检查 ------------------------------------------------------------
    report_file = Path(report_path)
    if not report_file.exists():
        result.errors.append(f"报告文件不存在: {report_file}")
    else:
        text = report_file.read_text(encoding="utf-8").strip()
        if not text:
            result.errors.append(f"报告内容为空: {report_file}")
        else:
            required_sections = ['# 非恒定流综合分析报告', '## 方法指标总览', '## 方法推荐']
            for section in required_sections:
                if section not in text:
                    result.errors.append(f"报告缺少段落: {section}")

    return result


def validate_optimizer_bundle(
    data_path: PathLike,
    report_path: Optional[PathLike] = None,
) -> ValidationResult:
    """
    校验参数优化器输出的数据/报告组合。
    """
    result = ValidationResult()

    data_file = Path(data_path)
    if not data_file.exists():
        result.errors.append(f"数据文件缺失: {data_file}")
    else:
        try:
            payload = json.loads(data_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            result.errors.append(f"数据文件不是有效的 JSON: {exc}")
        else:
            required = {
                "success",
                "optimal_params",
                "objective_value",
                "iterations",
                "convergence_info",
                "parameter_sensitivity",
                "physical_constraints_satisfied",
                "stability_analysis",
            }
            missing = required - set(payload.keys())
            if missing:
                result.errors.append(f"数据文件缺失 keys: {sorted(missing)}")
            else:
                if not isinstance(payload["optimal_params"], dict) or not payload["optimal_params"]:
                    result.errors.append("最优参数字段缺失或为空")
                if payload.get("iterations", 0) <= 0:
                    result.warnings.append("迭代次数小于等于零")
                result.details["objective_value"] = payload.get("objective_value", 0.0)

    if report_path:
        report_file = Path(report_path)
        if not report_file.exists():
            result.errors.append(f"报告文件不存在: {report_file}")
        else:
            text = report_file.read_text(encoding="utf-8").strip()
            if not text:
                result.errors.append(f"报告内容为空: {report_file}")
            elif "# 参数优化报告" not in text:
                result.warnings.append("报告缺少预期的标题")

    return result
