#!/usr/bin/env python3
"""
单一渠道水面线绘制工具 (简化版)

基于WaterNet核心库的水面线绘制工具，简化示例代码。

功能特点:
1. 多工况水面线对比
2. 专业可视化报告生成
3. 水力学性质分析

运行示例:
    python water_surface_profile_plotter.py

Author: WaterNet Development Team  
Date: 2025-01-05
"""

import sys
import os
from pathlib import Path

# 添加WaterNet路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from waternet.utils import ChannelConfigManager, WaterSurfaceProfileAnalyzer

try:
    import matplotlib.pyplot as plt
    import matplotlib
    import matplotlib.font_manager as fm
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("⚠️ matplotlib未安装，无法生成图表")


class WaterSurfaceProfilePlotter:
    """
    单一渠道水面线绘制器
    
    参考config_driven_reservoir_gate_system.py中_calculate_water_surface_profile和
    _create_water_surface_profile_plot方法的实现逻辑
    """
    
    def __init__(self, config_path: str | None = None):
        """
        初始化水面线绘制器
        
        Args:
            config_path: 渠道配置文件路径
        """
        self.config_path = config_path or "configs/trapezoidal_channel.yaml"
        
        # 加载渠道配置
        self.channel_config = self._load_channel_config()
        
        # 输出目录
        self.output_dir = Path(__file__).parent / "outputs" / "water_surface_profiles"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 仿真结果存储
        self.profile_results = []
        
        print(f"✓ 水面线绘制器初始化完成")
        print(f"  - 配置文件: {self.config_path}")
        print(f"  - 输出目录: {self.output_dir}")
    
    def _load_channel_config(self) -> Dict[str, Any]:
        """加载渠道配置"""
        config_file = Path(__file__).parent / self.config_path
        
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                raw_config = yaml.safe_load(f)
                print(f"✓ 成功加载配置文件: {config_file}")
                
                # 将现有配置格式转换为期望的格式
                if 'sections' in raw_config:
                    # 从sections中提取信息
                    sections = raw_config['sections']
                    first_section = sections[0]
                    last_section = sections[-1]
                    
                    total_length = last_section['mileage'] - first_section['mileage']
                    
                    # 获取断面几何参数
                    cross_section = first_section.get('cross_section', {})
                    
                    converted_config = {
                        'channel': {
                            'name': raw_config.get('name', '标准梯形渠道'),
                            'length': total_length if total_length > 0 else 10000.0,
                            'sections': len(sections),
                            'geometry': {
                                'type': cross_section.get('type', 'trapezoidal'),
                                'bottom_width': cross_section.get('bottom_width', 8.0),
                                'side_slope': cross_section.get('side_slope', 1.5),
                                'roughness': first_section.get('roughness', 0.025)
                            },
                            'profile': {
                                'upstream_elevation': first_section['elevation'],
                                'downstream_elevation': last_section['elevation']
                            },
                            'raw_sections': sections  # 保存原始断面数据
                        }
                    }
                    
                    return converted_config
                
                # 如果已经是期望格式，直接返回
                if 'channel' in raw_config:
                    return raw_config
                    
                # 否则当作原始格式处理
                return {'channel': raw_config}
        else:
            # 使用默认配置
            print(f"⚠️ 配置文件不存在，使用默认配置")
            return self._get_default_channel_config()
    
    def _get_default_channel_config(self) -> Dict[str, Any]:
        """获取默认渠道配置"""
        return {
            'channel': {
                'name': '标准梯形渠道',
                'length': 10000.0,  # 总长度 10km
                'sections': 11,     # 断面数量
                'geometry': {
                    'type': 'trapezoidal',
                    'bottom_width': 8.0,
                    'side_slope': 1.5,
                    'roughness': 0.025
                },
                'profile': {
                    'upstream_elevation': 110.0,
                    'downstream_elevation': 100.0
                }
            }
        }
    
    def compute_multiple_flow_conditions(self, flow_conditions: List[float] | None = None) -> List[Dict[str, Any]]:
        """
        计算多个流量工况的水面线
        
        参考config_driven_reservoir_gate_system.py中的多工况计算逻辑
        
        Args:
            flow_conditions: 流量工况列表 (m³/s)
            
        Returns:
            List[Dict]: 各工况的水面线结果
        """
        if flow_conditions is None:
            flow_conditions = [20.0, 40.0, 60.0, 80.0]  # 默认四个工况
        
        print(f"\n开始计算多工况水面线...")
        print(f"流量工况: {flow_conditions} m³/s")
        
        self.profile_results = []
        
        for i, flow in enumerate(flow_conditions):
            print(f"\n计算工况 {i+1}: Q = {flow:.1f} m³/s")
            
            # 计算单个工况的水面线
            profile_result = self._compute_single_flow_profile(flow, f"工况{i+1}")
            
            if profile_result:
                self.profile_results.append(profile_result)
                print(f"  ✓ 工况 {i+1} 计算完成")
            else:
                print(f"  ✗ 工况 {i+1} 计算失败")
        
        print(f"\n✓ 多工况计算完成，共 {len(self.profile_results)} 个工况")
        return self.profile_results
    
    def _compute_single_flow_profile(self, flow: float, case_name: str) -> Dict[str, Any]:
        """
        计算单个流量工况的水面线
        
        参考config_driven_reservoir_gate_system.py中_calculate_water_surface_profile方法
        """
        try:
            # 使用WaterNet基础库计算
            profile_data = self._compute_profile_using_base_library(flow)
            
            if not profile_data:
                # 使用简化计算方法
                profile_data = self._compute_profile_simplified(flow)
            
            # 构建完整结果
            result = {
                'case_name': case_name,
                'flow': flow,
                'profile_data': profile_data,
                'hydraulic_analysis': self._analyze_hydraulic_properties(profile_data, flow),
                'computation_time': time.time()
            }
            
            return result
            
        except Exception as e:
            print(f"    计算失败: {e}")
            return {}
    
    def _compute_profile_using_base_library(self, flow: float) -> Dict[str, Any] | None:
        """使用WaterNet基础库计算水面线"""
        try:
            from waternet.models.saint_venant import SaintVenantModel
            
            channel_config = self.channel_config['channel']
            sections = self._create_channel_sections(channel_config)
            
            model = SaintVenantModel(
                name=channel_config['name'],
                upstream_node="upstream",
                downstream_node="downstream",
                sections=sections
            )
            
            downstream_H = channel_config['profile']['downstream_elevation'] + 2.0
            result = model.compute_steady_state(Q=flow, downstream_H=downstream_H)
            
            distances, water_levels, bottom_elevations = [], [], []
            velocities, depths = [], []
            
            for i, section in enumerate(sections):
                distances.append(section['mileage'])
                bottom_elevations.append(section['elevation'])
                
                water_level = result.get(f'H_section_{i}', downstream_H)
                water_levels.append(water_level)
                
                depth = water_level - section['elevation']
                depths.append(depth)
                
                if depth > 0:
                    area = section['area_func'](water_level)
                    velocity = flow / area if area > 0 else 0
                    velocities.append(velocity)
                else:
                    velocities.append(0)
            
            return {
                'distances': distances,
                'water_levels': water_levels,
                'bottom_elevations': bottom_elevations,
                'depths': depths,
                'velocities': velocities,
                'method': 'waternet_base_library'
            }
        except Exception as e:
            print(f"    基础库计算失败: {e}")
            return None
    
    def _compute_profile_simplified(self, flow: float) -> Dict[str, Any]:
        """简化水面线计算方法"""
        channel_config = self.channel_config['channel']
        length = channel_config['length']
        n_sections = channel_config.get('sections', 11)
        geometry = channel_config['geometry']
        profile = channel_config['profile']
        
        bottom_width = geometry['bottom_width']
        side_slope = geometry['side_slope']
        roughness = geometry['roughness']
        
        upstream_elevation = profile['upstream_elevation']
        downstream_elevation = profile['downstream_elevation']
        bottom_slope = (upstream_elevation - downstream_elevation) / length
        
        normal_depth = self._solve_normal_depth(flow, bottom_width, side_slope, bottom_slope, roughness)
        downstream_H = downstream_elevation + normal_depth * 1.1
        
        distances, water_levels, bottom_elevations = [], [], []
        depths, velocities = [], []
        
        dx = length / (n_sections - 1)
        current_H = downstream_H
        
        for i in range(n_sections):
            x = i * dx
            ratio = x / length
            elevation = downstream_elevation + ratio * (upstream_elevation - downstream_elevation)
            
            distances.append(x)
            water_levels.append(current_H)
            bottom_elevations.append(elevation)
            
            depth = current_H - elevation
            depths.append(depth)
            
            if depth > 0:
                area = bottom_width * depth + side_slope * depth * depth
                velocity = flow / area if area > 0 else 0
                velocities.append(velocity)
                
                if i < n_sections - 1:
                    wetted_perimeter = bottom_width + 2 * depth * math.sqrt(1 + side_slope * side_slope)
                    hydraulic_radius = area / wetted_perimeter if wetted_perimeter > 0 else 0
                    friction_slope = (roughness * velocity) ** 2 / (hydraulic_radius ** (4/3)) if hydraulic_radius > 0 else 0.001
                    water_surface_slope = bottom_slope - friction_slope
                    current_H = current_H + water_surface_slope * dx
            else:
                velocities.append(0)
                current_H = elevation + normal_depth
        
        return {
            'distances': distances,
            'water_levels': water_levels,
            'bottom_elevations': bottom_elevations,
            'depths': depths,
            'velocities': velocities,
            'normal_depth': normal_depth,
            'method': 'simplified_calculation'
        }
    
    def _create_channel_sections(self, channel_config: Dict) -> List[Dict]:
        """创建渠道断面几何数据"""
        length = channel_config['length']
        n_sections = channel_config.get('sections', 11)
        geometry = channel_config['geometry']
        profile = channel_config['profile']
        
        bottom_width = geometry['bottom_width']
        side_slope = geometry['side_slope']
        roughness = geometry['roughness']
        
        upstream_elevation = profile['upstream_elevation']
        downstream_elevation = profile['downstream_elevation']
        
        sections = []
        
        for i in range(n_sections):
            ratio = i / (n_sections - 1)
            mileage = ratio * length
            elevation = upstream_elevation + ratio * (downstream_elevation - upstream_elevation)
            
            def create_area_func(elev, b_width, s_slope):
                def area_func(H):
                    if H <= elev:
                        return 0.01
                    h = H - elev
                    return b_width * h + s_slope * h * h
                return area_func
            
            def create_top_width_func(elev, b_width, s_slope):
                def top_width_func(H):
                    if H <= elev:
                        return b_width
                    h = H - elev
                    return b_width + 2 * s_slope * h
                return top_width_func
            
            def create_conveyance_func(area_f, top_width_f, n):
                def conveyance_func(H):
                    A = area_f(H)
                    if A <= 0:
                        return 0
                    
                    h = H - elevation
                    if h <= 0:
                        return 0
                    
                    P = bottom_width + 2 * h * math.sqrt(1 + side_slope * side_slope)
                    R = A / P if P > 0 else 0
                    
                    return A * (R ** (2/3)) / n if R > 0 else 0
                return conveyance_func
            
            area_f = create_area_func(elevation, bottom_width, side_slope)
            top_width_f = create_top_width_func(elevation, bottom_width, side_slope)
            conveyance_f = create_conveyance_func(area_f, top_width_f, roughness)
            
            sections.append({
                'mileage': mileage,
                'elevation': elevation,
                'roughness': roughness,
                'area_func': area_f,
                'top_width_func': top_width_f,
                'conveyance_func': conveyance_f
            })
        
        return sections
    
    def _solve_normal_depth(self, Q: float, b: float, m: float, S: float, n: float) -> float:
        """求解正常水深"""
        h = max(1.0, Q / (b * 3.0))
        
        for i in range(25):
            A = b * h + m * h ** 2
            P = b + 2 * h * math.sqrt(1 + m ** 2)
            R = A / P if P > 0 else 0
            
            Q_calc = (1.0 / n) * A * (R ** (2.0/3.0)) * (S ** 0.5) if R > 0 else 0
            error = Q_calc - Q
            
            if abs(error) < 0.001:
                break
            
            dA_dh = b + 2 * m * h
            dP_dh = 2 * math.sqrt(1 + m ** 2)
            dR_dh = (dA_dh * P - A * dP_dh) / (P ** 2) if P > 0 else 0
            
            if R > 0:
                dQ_dh = (1.0 / n) * (S ** 0.5) * (
                    dA_dh * (R ** (2.0/3.0)) + 
                    A * (2.0/3.0) * (R ** (-1.0/3.0)) * dR_dh
                )
            else:
                dQ_dh = 1.0
            
            if abs(dQ_dh) > 1e-10:
                h_new = h - error / dQ_dh
                h = max(0.1, min(10.0, h_new))
            else:
                break
        
        return h
    
    def _analyze_hydraulic_properties(self, profile_data: Dict, flow: float) -> Dict[str, Any]:
        """分析水力学性质"""
        if not profile_data:
            return {}
        
        depths = profile_data['depths']
        velocities = profile_data['velocities']
        
        froude_numbers = []
        specific_energies = []
        
        for depth, velocity in zip(depths, velocities):
            if depth > 0 and velocity > 0:
                froude = velocity / math.sqrt(9.81 * depth)
                froude_numbers.append(froude)
                specific_energy = depth + velocity ** 2 / (2 * 9.81)
                specific_energies.append(specific_energy)
            else:
                froude_numbers.append(0.0)
                specific_energies.append(0.0)
        
        flow_regime = 'subcritical' if all(fr < 1.0 for fr in froude_numbers if fr > 0) else 'mixed'
        
        water_levels = profile_data['water_levels']
        distances = profile_data['distances']
        
        total_head_loss = water_levels[0] - water_levels[-1] if len(water_levels) > 1 else 0
        channel_length = distances[-1] - distances[0] if len(distances) > 1 else 0
        average_slope = total_head_loss / channel_length if channel_length > 0 else 0
        
        return {
            'froude_numbers': froude_numbers,
            'specific_energies': specific_energies,
            'flow_regime': flow_regime,
            'total_head_loss': total_head_loss,
            'channel_length': channel_length,
            'average_slope': average_slope,
            'max_depth': max(depths) if depths else 0,
            'min_depth': min(depths) if depths else 0,
            'max_velocity': max(velocities) if velocities else 0,
            'min_velocity': min(velocities) if velocities else 0,
            'max_froude': max(froude_numbers) if froude_numbers else 0
        }
    
    def create_water_surface_profile_plot(self) -> str:
        """创建水面线纵剖面对比图"""
        if not self.profile_results:
            raise ValueError("无水面线计算结果，请先执行compute_multiple_flow_conditions()")
        
        try:
            import matplotlib.pyplot as plt
            import matplotlib
            
            # 设置中文字体
            self._setup_matplotlib_fonts()
            
            # 创建图形
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 12))
            
            # 颜色和样式设置
            colors = ['blue', 'red', 'green', 'orange', 'purple', 'brown', 'pink']
            markers = ['o', 's', '^', 'D', 'v', '<', '>']
            linestyles = ['-', '--', '-.', ':', (0, (3, 1, 1, 1)), (0, (5, 2)), (0, (3, 2, 1, 2))]
            
            # 绘制水面线对比
            self._plot_water_surface_profiles(ax1, colors, markers, linestyles)
            
            # 绘制流速和弗劳德数分布
            self._plot_velocity_and_froude(ax2, colors, markers, linestyles)
            
            # 调整布局
            plt.tight_layout(pad=3.0)
            
            # 保存图像
            output_path = self.output_dir / 'water_surface_profiles_comparison.png'
            plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
            plt.close()
            
            print(f"✅ 水面线对比图已保存: {output_path}")
            return str(output_path)
            
        except ImportError:
            print("⚠️ matplotlib未安装，无法生成图表")
            return ""
        except Exception as e:
            print(f"✗ 图表生成失败: {e}")
            return ""
    
    def _setup_matplotlib_fonts(self):
        """设置matplotlib中文字体"""
        import matplotlib
        import matplotlib.font_manager as fm
        
        preferred_fonts = ['Arial Unicode MS', 'Microsoft YaHei', 'SimHei', 'DejaVu Sans']
        available_font = None
        
        for font_name in preferred_fonts:
            try:
                font_prop = fm.FontProperties(family=font_name)
                font_path = fm.findfont(font_prop)
                if font_path and font_name.lower() in font_path.lower():
                    available_font = font_name
                    break
            except:
                continue
        
        if available_font:
            matplotlib.rcParams['font.sans-serif'] = [available_font, 'DejaVu Sans']
            print(f"✅ 使用字体: {available_font}")
        else:
            matplotlib.rcParams['font.sans-serif'] = ['DejaVu Sans']
            print("⚠️ 使用默认字体")
            
        matplotlib.rcParams['axes.unicode_minus'] = False
        matplotlib.rcParams['mathtext.default'] = 'regular'
        matplotlib.rcParams['font.family'] = 'sans-serif'
    
    def _plot_water_surface_profiles(self, ax, colors, markers, linestyles):
        """绘制水面线纵剖面"""
        for i, result in enumerate(self.profile_results):
            profile = result['profile_data']
            case_name = result['case_name']
            flow = result['flow']
            
            distances = profile['distances']
            water_levels = profile['water_levels']
            bottom_elevations = profile['bottom_elevations']
            
            color = colors[i % len(colors)]
            marker = markers[i % len(markers)]
            linestyle = linestyles[i % len(linestyles)]
            
            # 绘制水面线
            ax.plot(distances, water_levels, 
                   color=color, 
                   marker=marker,
                   linestyle=linestyle,
                   linewidth=3, markersize=8,
                   label=f'{case_name} (Q={flow:.1f}m³/s)',
                   markerfacecolor='white', markeredgewidth=2)
            
            # 绘制河底线（只绘制一次）
            if i == 0:
                ax.plot(distances, bottom_elevations, 
                       'k-', linewidth=2, alpha=0.8, label='渠底高程')
                ax.fill_between(distances, bottom_elevations, 
                               [min(bottom_elevations) - 1] * len(bottom_elevations), 
                               color='saddlebrown', alpha=0.4, label='渠底')
        
        # 设置上图属性
        ax.set_title('渠道水面线纵剖面对比 - 多工况分析', 
                    fontsize=21, fontweight='bold', color='black')
        ax.set_xlabel('纵向距离 (m)', fontsize=16)
        ax.set_ylabel('高程 (m)', fontsize=16)
        ax.legend(fontsize=14, loc='upper right')
        ax.grid(True, alpha=0.3, linestyle=':', linewidth=1)
        
        # 设置坐标范围
        self._set_plot_limits(ax)
        
        # 添加水位标注
        self._add_water_level_annotations(ax, colors)
    
    def _plot_velocity_and_froude(self, ax, colors, markers, linestyles):
        """绘制流速和弗劳德数分布"""
        ax_twin = ax.twinx()
        
        for i, result in enumerate(self.profile_results):
            profile = result['profile_data']
            hydraulic = result['hydraulic_analysis']
            case_name = result['case_name']
            
            distances = profile['distances']
            velocities = profile['velocities']
            froude_numbers = hydraulic.get('froude_numbers', [])
            
            color = colors[i % len(colors)]
            marker = markers[i % len(markers)]
            linestyle = linestyles[i % len(linestyles)]
            
            # 绘制流速分布
            ax.plot(distances, velocities, 
                   color=color,
                   linestyle=linestyle,
                   marker=marker,
                   linewidth=3, markersize=6,
                   label=f'{case_name} 流速')
            
            # 绘制弗劳德数分布
            if froude_numbers:
                ax_twin.plot(distances, froude_numbers, 
                           color=color, 
                           linestyle=':', alpha=0.7, linewidth=2,
                           label=f'{case_name} Fr数')
        
        # 设置下图属性
        ax.set_title('渠道流速和弗劳德数分布', 
                    fontsize=21, fontweight='bold', color='black')
        ax.set_xlabel('纵向距离 (m)', fontsize=16)
        ax.set_ylabel('流速 (m/s)', fontsize=16, color='blue')
        ax_twin.set_ylabel('弗劳德数', fontsize=16, color='red')
        ax.grid(True, alpha=0.3, linestyle=':', linewidth=1)
        
        # 添加临界流界限线
        ax_twin.axhline(y=1.0, color='red', linestyle='--', alpha=0.8, linewidth=2,
                        label='亚临界流界限 (Fr=1)')
        
        # 结合图例
        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax_twin.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2, 
                  fontsize=14, loc='upper right')
    
    def _set_plot_limits(self, ax):
        """设置绘图范围"""
        all_water_levels = []
        all_bottom_levels = []
        
        for result in self.profile_results:
            profile = result['profile_data']
            all_water_levels.extend(profile['water_levels'])
            all_bottom_levels.extend(profile['bottom_elevations'])
        
        if all_water_levels and all_bottom_levels:
            min_bottom = min(all_bottom_levels)
            max_water = max(all_water_levels)
            margin = (max_water - min_bottom) * 0.1
            ax.set_ylim(min_bottom - margin, max_water + margin)
    
    def _add_water_level_annotations(self, ax, colors):
        """添加水位数字标注"""
        for i, result in enumerate(self.profile_results):
            profile = result['profile_data']
            distances = profile['distances']
            water_levels = profile['water_levels']
            color = colors[i % len(colors)]
            
            # 在关键点添加水位数字
            for j in range(0, len(distances), max(1, len(distances)//4)):
                if j < len(water_levels):
                    ax.annotate(f'{water_levels[j]:.1f}', 
                               xy=(distances[j], water_levels[j]),
                               xytext=(0, -25), textcoords='offset points',
                               fontsize=12, color='red', fontweight='bold',
                               ha='center', va='top',
                               bbox=dict(boxstyle='round,pad=0.3', 
                                       facecolor='white', alpha=0.9, edgecolor=color))
    
    def generate_analysis_report(self, plot_path: str = "") -> str:
        """
        生成分析报告（含水面线绘制结果图）
        
        根据用户记忆中的"恒定流水面线可视化强制要求"，
        恒定流计算结果必须包含沿程水面线纵剖面图
        
        Args:
            plot_path: 水面线图片路径
        """
        if not self.profile_results:
            return "无计算结果"
        
        report_lines = [
            "# 渠道水面线分析报告",
            f"\n生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"渠道配置: {self.channel_config['channel']['name']}",
            f"渠道长度: {self.channel_config['channel']['length']:.0f}m",
            f"计算工况数量: {len(self.profile_results)}个"
        ]
        
        # 添加水面线纵剖面图（根据用户记忆要求）
        if plot_path:
            plot_filename = Path(plot_path).name
            report_lines.extend([
                "\n## 水面线纵剖面对比图 📊",
                f"\n**恒定流水面线可视化结果**：",
                f"\n![水面线纵剖面对比图]({plot_filename})",
                "\n*图表说明：*",
                "- 上图：各工况水面线纵剖面对比，包含渠底高程线",
                "- 下图：流速分布和弗劳德数分布分析",
                "- 水位数字标注：红色数字显示关键断面水位（单位：m）",
                "- 流态分析：Fr<1为亚临界流，Fr≥1为临界或超临界流"
            ])
        
        report_lines.extend([
            "\n## 各工况结果汇总",
            "\n| 工况 | 流量(m³/s) | 最大水深(m) | 最大流速(m/s) | 最大Fr数 | 水头损失(m) | 流态 |",
            "| --- | --- | --- | --- | --- | --- | --- |"
        ])
        
        # 工况数据表格
        for result in self.profile_results:
            case_name = result['case_name']
            flow = result['flow']
            hydraulic = result['hydraulic_analysis']
            
            max_depth = hydraulic.get('max_depth', 0)
            max_velocity = hydraulic.get('max_velocity', 0)
            max_froude = hydraulic.get('max_froude', 0)
            head_loss = hydraulic.get('total_head_loss', 0)
            flow_regime = hydraulic.get('flow_regime', 'unknown')
            
            report_lines.append(
                f"| {case_name} | {flow:.1f} | {max_depth:.2f} | {max_velocity:.2f} | "
                f"{max_froude:.3f} | {head_loss:.2f} | {flow_regime} |"
            )
        
        # 添加详细水力学分析
        report_lines.extend([
            "\n## 水力学特性分析",
            "\n### 流态特征"
        ])
        
        # 流态分析
        subcritical_count = sum(1 for r in self.profile_results 
                               if r['hydraulic_analysis'].get('flow_regime') == 'subcritical')
        if subcritical_count == len(self.profile_results):
            report_lines.append("✅ **全部工况均为亚临界流**：流动稳定，水面平缓")
        else:
            report_lines.append("⚠️ **存在临界或超临界流工况**：需注意流态转换")
        
        # 参数敏感性分析
        if len(self.profile_results) > 1:
            flows = [r['flow'] for r in self.profile_results]
            head_losses = [r['hydraulic_analysis'].get('total_head_loss', 0) for r in self.profile_results]
            
            flow_range = max(flows) - min(flows)
            loss_range = max(head_losses) - min(head_losses)
            
            if flow_range > 0:
                sensitivity = loss_range / flow_range  # m/(m³/s)
                report_lines.extend([
                    "\n### 参数敏感性",
                    f"- 流量变化范围: {min(flows):.1f} - {max(flows):.1f} m³/s",
                    f"- 水头损失变化范围: {min(head_losses):.2f} - {max(head_losses):.2f} m",
                    f"- 敏感性系数: {sensitivity:.3f} m/(m³/s)",
                    f"- **结论**: 流量每增加1 m³/s，水头损失约增加{sensitivity:.3f} m"
                ])
        
        # 工程建议
        max_flow_result = max(self.profile_results, key=lambda x: x['flow'])
        max_froude = max_flow_result['hydraulic_analysis'].get('max_froude', 0)
        
        report_lines.extend([
            "\n## 工程建议",
            "\n### 设计参考"
        ])
        
        if max_froude < 0.5:
            report_lines.append("✅ **推荐设计流量**: 当前最大流量工况下流态良好，可作为设计流量")
        elif max_froude < 0.8:
            report_lines.append("⚠️ **注意设计流量**: 接近临界流态，建议适当降低设计流量")
        else:
            report_lines.append("❌ **超出推荐范围**: 弗劳德数过高，强烈建议降低设计流量")
        
        # 添加计算方法说明
        report_lines.extend([
            "\n### 计算方法",
            "- **水面线计算**: 基于WaterNet基础库SaintVenantModel.compute_steady_state()",
            "- **备用算法**: 牛顿迭代法求解正常水深，逐步推算水面线",
            "- **弗劳德数**: Fr = V/√(gD)，其中V为流速，D为水深",
            "- **流态判断**: Fr<1亚临界流，Fr=1临界流，Fr>1超临界流"
        ])
        
        # 保存报告
        report_path = self.output_dir / 'analysis_report.md'
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))
        
        print(f"✅ 分析报告已保存: {report_path}")
        return str(report_path)


def main():
    """主函数"""
    print("单一渠道水面线绘制工具")
    print("=" * 50)
    
    try:
        # 创建水面线绘制器
        plotter = WaterSurfaceProfilePlotter()
        
        # 计算多个流量工况
        flow_conditions = [25.0, 50.0, 75.0, 100.0]  # 四个流量工况
        results = plotter.compute_multiple_flow_conditions(flow_conditions)
        
        if results:
            # 创建水面线对比图
            plot_path = plotter.create_water_surface_profile_plot()
            
            # 生成分析报告（包含图片引用）
            report_path = plotter.generate_analysis_report(plot_path)
            
            print(f"\n✅ 水面线绘制完成！")
            print(f"  - 计算工况: {len(results)} 个")
            print(f"  - 输出目录: {plotter.output_dir}")
            if plot_path:
                print(f"  - 水面线图: {plot_path}")
            if report_path:
                print(f"  - 分析报告: {report_path}")
        else:
            print("✗ 水面线计算失败")
    
    except Exception as e:
        print(f"✗ 程序执行失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()