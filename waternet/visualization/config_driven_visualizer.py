"""
配置驱动的水系统可视化引擎

基于YAML配置文件实现水系统对象的多模式可视化，支持：
1. 多种展示方式（简洁流程图、流向示意图、表格模式、工程图形化）
2. 智能模式选择
3. 各类水利对象的标准化模板
4. 输入输出配置化管理

Author: WaterNet Development Team
Date: 2024-10-05
"""

import yaml
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class ObjectTemplate:
    """对象模板数据类"""
    name: str
    category: str
    symbol: Dict[str, Any]
    display_properties: List[Dict[str, Any]]
    engineering_symbol: str
    ascii_art: str


class ConfigurableVisualizationEngine:
    """配置驱动的可视化引擎"""
    
    def __init__(self, config_file: str):
        """初始化可视化引擎"""
        self.config_file = config_file
        self.config = self._load_config()
        self.templates = self._load_templates()
        self.current_mode = "flow_diagram"
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"配置文件未找到: {self.config_file}")
        except yaml.YAMLError as e:
            raise ValueError(f"配置文件格式错误: {e}")
    
    def _load_templates(self) -> Dict[str, ObjectTemplate]:
        """加载对象模板"""
        templates = {}
        template_config = self.config.get('object_templates', {})
        
        for obj_type, template_data in template_config.items():
            templates[obj_type] = ObjectTemplate(
                name=template_data['name'],
                category=template_data['category'],
                symbol=template_data['symbol'],
                display_properties=template_data['display_properties'],
                engineering_symbol=template_data['engineering_symbol'],
                ascii_art=template_data['ascii_art']
            )
        
        return templates
    
    def select_display_mode(self, system_data: Dict[str, Any]) -> str:
        """智能选择显示模式"""
        auto_rules = self.config['visualization']['auto_mode_selection']['rules']
        
        node_count = len(system_data.get('topology', {}).get('nodes', []))
        has_complex_structures = self._check_complex_structures(system_data)
        
        # 按规则优先级检查
        for rule in auto_rules:
            condition = rule['condition']
            if self._evaluate_condition(condition, node_count, has_complex_structures):
                return rule['recommended_mode']
        
        return 'flow_diagram'
    
    def _check_complex_structures(self, system_data: Dict[str, Any]) -> bool:
        """检查是否包含复杂结构"""
        components = system_data.get('components', {})
        complex_types = ['gate_stations', 'pump_stations']
        
        for comp_type in complex_types:
            if comp_type in components and components[comp_type]:
                return True
        return False
    
    def _evaluate_condition(self, condition: str, node_count: int, has_complex_structures: bool) -> bool:
        """评估条件表达式"""
        condition = condition.replace('node_count', str(node_count))
        condition = condition.replace('has_complex_structures', str(has_complex_structures))
        
        try:
            return eval(condition)
        except:
            return False
    
    def generate_ascii_topology(self, system_data: Dict[str, Any]) -> str:
        """生成ASCII艺术拓扑图"""
        ascii_config = self.config['output_formats']['ascii_art']
        line_width = ascii_config.get('line_width', 80)
        
        lines = []
        lines.append("═" * line_width)
        lines.append(f"{'水库-闸门-明渠系统拓扑图'.center(line_width - 6)}")
        lines.append("═" * line_width)
        lines.append("")
        
        components = system_data.get('components', {})
        
        # 绘制水库
        if 'reservoirs' in components:
            lines.append("【水库系统】")
            for reservoir_name, reservoir_data in components['reservoirs'].items():
                template = self.templates.get('reservoir')
                if template:
                    lines.append(f"  {template.engineering_symbol} {reservoir_name}")
                    lines.append(f"     水位: {reservoir_data.get('level', '未知')}m")
                    lines.append(f"     类型: {reservoir_data.get('reservoir_type', '未知')}")
                lines.append("")
        
        # 绘制流程
        lines.append("【系统流程】")
        flow_line = self._build_flow_line(components)
        lines.extend(flow_line)
        lines.append("")
        
        # 绘制闸门
        if 'gates' in components:
            lines.append("【闸门控制】")
            for gate_name, gate_data in components['gates'].items():
                template = self.templates.get('gate')
                if template:
                    lines.append(f"  {template.engineering_symbol} {gate_name}")
                    control = gate_data.get('control', {})
                    geometry = gate_data.get('geometry', {})
                    lines.append(f"     开度: {control.get('initial_opening', '未知')}m")
                    lines.append(f"     宽度: {geometry.get('width', '未知')}m")
                lines.append("")
        
        # 绘制渠道
        if 'channels' in components:
            lines.append("【渠道参数】")
            for channel_name, channel_data in components['channels'].items():
                template = self.templates.get('channel')
                if template:
                    geometry = channel_data.get('geometry', {})
                    lines.append(f"  {template.engineering_symbol} {channel_name}")
                    lines.append(f"     长度: {geometry.get('length', '未知')}m")
                    lines.append(f"     底宽: {geometry.get('bottom_width', '未知')}m")
                    lines.append(f"     边坡: 1:{geometry.get('side_slope', '未知')}")
                lines.append("")
        
        # 图例
        if ascii_config.get('include_legend', True):
            lines.append("【图例说明】")
            lines.append("  ◊ = 水库    ┣┫ = 闸门    ┌─┐ = 渠道")
            lines.append("  ⟲ = 泵站    ◊ = 阀门     ⚹ = 水轮机")
        
        lines.append("═" * line_width)
        return "\n".join(lines)
    
    def _build_flow_line(self, components: Dict[str, Any]) -> List[str]:
        """构建流程连接线"""
        flow_lines = []
        
        reservoirs = components.get('reservoirs', {})
        gates = components.get('gates', {})
        channels = components.get('channels', {})
        
        # 查找上下游水库
        upstream_reservoir = None
        downstream_reservoir = None
        
        for res_name, res_data in reservoirs.items():
            if res_data.get('reservoir_type') == 'upstream':
                upstream_reservoir = res_name
            elif res_data.get('reservoir_type') == 'downstream':
                downstream_reservoir = res_name
        
        # 构建流程
        flow_components = []
        
        if upstream_reservoir:
            flow_components.append(f"◊{upstream_reservoir}")
        
        gate_names = list(gates.keys())
        if gate_names:
            flow_components.extend([f"┣┫{name}" for name in gate_names])
        
        channel_names = sorted(channels.keys())
        if channel_names:
            flow_components.extend([f"┌─┐{name}" for name in channel_names])
        
        if downstream_reservoir:
            flow_components.append(f"◊{downstream_reservoir}")
        
        # 生成连接线
        if len(flow_components) >= 2:
            connection_line = " ═══> ".join(flow_components)
            max_width = 76
            if len(connection_line) > max_width:
                words = connection_line.split(" ═══> ")
                current_line = ""
                for word in words:
                    if len(current_line + " ═══> " + word) <= max_width:
                        if current_line:
                            current_line += " ═══> " + word
                        else:
                            current_line = word
                    else:
                        if current_line:
                            flow_lines.append("  " + current_line)
                        current_line = "      └─> " + word
                if current_line:
                    flow_lines.append("  " + current_line)
            else:
                flow_lines.append("  " + connection_line)
        
        return flow_lines
    
    def generate_table_view(self, system_data: Dict[str, Any]) -> str:
        """生成表格视图"""
        table_config = self.config['output_formats']['table']
        col_sep = table_config.get('column_separator', ' | ')
        row_sep = table_config.get('row_separator', '-')
        max_width = table_config.get('max_column_width', 20)
        
        lines = []
        components = system_data.get('components', {})
        
        lines.append("系统组件总览")
        lines.append("=" * 60)
        
        header = ["类型", "名称", "关键参数", "状态"]
        lines.append(col_sep.join([h.ljust(max_width) for h in header]))
        lines.append(row_sep * 60)
        
        # 水库信息
        for res_name, res_data in components.get('reservoirs', {}).items():
            row = [
                "水库",
                res_name[:max_width],
                f"水位:{res_data.get('level', 'N/A')}m",
                res_data.get('reservoir_type', 'N/A')
            ]
            lines.append(col_sep.join([cell.ljust(max_width) for cell in row]))
        
        # 闸门信息
        for gate_name, gate_data in components.get('gates', {}).items():
            control = gate_data.get('control', {})
            geometry = gate_data.get('geometry', {})
            row = [
                "闸门",
                gate_name[:max_width],
                f"开度:{control.get('initial_opening', 'N/A')}m",
                f"宽度:{geometry.get('width', 'N/A')}m"
            ]
            lines.append(col_sep.join([cell.ljust(max_width) for cell in row]))
        
        # 渠道信息
        for ch_name, ch_data in components.get('channels', {}).items():
            geometry = ch_data.get('geometry', {})
            row = [
                "渠道",
                ch_name[:max_width],
                f"长度:{geometry.get('length', 'N/A')}m",
                f"底宽:{geometry.get('bottom_width', 'N/A')}m"
            ]
            lines.append(col_sep.join([cell.ljust(max_width) for cell in row]))
        
        lines.append("=" * 60)
        return "\n".join(lines)
    
    def generate_output(self, system_data: Dict[str, Any], output_dir: str = "output") -> Dict[str, str]:
        """生成所有配置的输出格式"""
        os.makedirs(output_dir, exist_ok=True)
        
        # 创建子目录
        dir_config = self.config['file_output']['directory_structure']
        for subdir in dir_config['subdirs']:
            os.makedirs(os.path.join(output_dir, subdir), exist_ok=True)
        
        results = {}
        output_formats = self.config['output_formats']
        
        # ASCII艺术图
        if output_formats['ascii_art']['enabled']:
            ascii_content = self.generate_ascii_topology(system_data)
            ascii_file = os.path.join(output_dir, "topology_diagrams", "system_topology.txt")
            with open(ascii_file, 'w', encoding='utf-8') as f:
                f.write(ascii_content)
            results['ascii_art'] = ascii_file
        
        # 表格视图
        if output_formats['table']['enabled']:
            table_content = self.generate_table_view(system_data)
            table_file = os.path.join(output_dir, "topology_diagrams", "system_table.txt")
            with open(table_file, 'w', encoding='utf-8') as f:
                f.write(table_content)
            results['table'] = table_file
        
        # 综合报告
        report_file = self._generate_comprehensive_report(system_data, output_dir)
        results['report'] = report_file
        
        return results
    
    def _generate_comprehensive_report(self, system_data: Dict[str, Any], output_dir: str) -> str:
        """生成综合报告"""
        report_config = self.config['report_templates']['engineering_report']
        
        report_content = []
        report_content.append(f"# {report_config['title']}")
        report_content.append(f"生成时间: {self._get_timestamp()}")
        report_content.append("")
        
        # 系统概述
        report_content.append("## 系统概述")
        system_info = system_data.get('system', {})
        report_content.append(f"系统名称: {system_info.get('name', '未命名系统')}")
        report_content.append(f"系统描述: {system_info.get('description', '无描述')}")
        report_content.append("")
        
        # 拓扑结构
        report_content.append("## 拓扑结构")
        report_content.append("```")
        report_content.append(self.generate_ascii_topology(system_data))
        report_content.append("```")
        report_content.append("")
        
        # 详细参数表
        report_content.append("## 详细参数")
        report_content.append(self.generate_table_view(system_data))
        report_content.append("")
        
        # 保存报告
        report_file = os.path.join(output_dir, "monitoring_reports", "system_report.md")
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(report_content))
        
        return report_file
    
    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        timestamp_format = self.config['file_output']['naming_convention']['timestamp_format']
        return datetime.now().strftime(timestamp_format)


def create_visualization_engine(config_file: str = None) -> ConfigurableVisualizationEngine:
    """创建可视化引擎实例"""
    if config_file is None:
        current_dir = os.path.dirname(__file__)
        config_file = os.path.join(current_dir, "..", "..", "configs", "visualization_templates.yaml")
    
    return ConfigurableVisualizationEngine(config_file)