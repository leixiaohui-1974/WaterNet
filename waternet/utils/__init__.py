"""
Utility helpers exposed to example scripts and other modules.
"""

from .channel_geometry import ChannelGeometry, HeadLossCalculator
from .channel_config import ChannelConfigManager
from .output_manager import ensure_output_tree, timestamped_path
from .validation import ValidationResult, validate_analysis_bundle, validate_optimizer_bundle
from .demo_reporting import (
    plot_method_time_series,
    plot_cross_section_profiles,
    write_analysis_detail_report,
    simulate_muskingum_series,
    plot_optimization_comparison,
    plot_parameter_sensitivity,
    write_optimization_summary,
)
from .water_surface_profile import WaterSurfaceProfileAnalyzer

__all__ = [
    "ChannelGeometry",
    "HeadLossCalculator",
    "WaterSurfaceProfileAnalyzer",
    "ChannelConfigManager",
    "ensure_output_tree",
    "timestamped_path",
    "ValidationResult",
    "validate_analysis_bundle",
    "validate_optimizer_bundle",
    "plot_method_time_series",
    "plot_cross_section_profiles",
    "write_analysis_detail_report",
    "simulate_muskingum_series",
    "plot_optimization_comparison",
    "plot_parameter_sensitivity",
    "write_optimization_summary",
]
