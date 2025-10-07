"""
重构后对象系统演示脚本的兼容入口。

原先的单体示例已拆分为三个独立脚本，位于
``examples/unsteady_flow_methods/object_system_showcase`` 目录。
本脚本依次调用拆分后的脚本，保证旧的自动化流程仍可直接运行。
"""

from __future__ import annotations

import runpy
from pathlib import Path


def main() -> None:
    base_dir = Path(__file__).resolve().parent / "object_system_showcase"
    scripts = [
        "smart_analysis_demo.py",
        "parameter_optimization_demo.py",
        "simulation_manager_demo.py",
    ]

    for script in scripts:
        script_path = base_dir / script
        print(f"正在运行示例脚本：{script_path.name}")
        runpy.run_path(str(script_path), run_name="__main__")


if __name__ == "__main__":
    main()
