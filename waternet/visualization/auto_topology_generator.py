#!/usr/bin/env python3
"""
自动拓扑图生成器

集成IntuitiveTopologyGenerator，支持从配置文件自动生成多种样式的拓扑图。
基于COMPLEX_HUB_IMPLEMENTATION_REPORT.md的分层架构算法。
"""

import os
import sys
import yaml
import json
from typing import Dict, List, Optional, Any
from pathlib import Path

# 添加当前目录到路径
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

try:
    from intuitive_topology_generator import IntuitiveTopologyGenerator
except ImportError:
    print("Warning: Could not import IntuitiveTopologyGenerator")
    IntuitiveTopologyGenerator = None


class AutoTopologyGenerator:
    """自动拓扑图生成器"""
    
    def __init__(self, output_dir: str = "topology_outputs"):
        """
        初始化自动生成器
        
        Args:
            output_dir: 输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # 支持的拓扑图样式
        self.topology_styles = {
            'intuitive_system': {
                'name': '直观系统拓扑图',
                'description': '基于分层架构的直观可视化',
                'generator_class': IntuitiveTopologyGenerator
            },
            'text_ascii': {
                'name': '文本ASCII图',
                'description': '纯文本格式拓扑图',
                'generator_class': None  # 特殊处理
            }
        }
        
    def load_config_file(self, config_path: str) -> Dict:
        """加载配置文件"""
        config_path = Path(config_path)
        
        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
            
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                if config_path.suffix.lower() in ['.yaml', '.yml']:
                    return yaml.safe_load(f)
                elif config_path.suffix.lower() == '.json':
                    return json.load(f)
                else:
                    raise ValueError(f"不支持的配置文件格式: {config_path.suffix}")
        except Exception as e:
            raise RuntimeError(f"加载配置文件失败: {e}")
            
    def _convert_config_to_topology(self, config_data: Dict) -> Dict:
        """将配置数据转换为拓扑数据格式"""
        topology_data = {}
        
        # 处理不同的配置格式
        for key in ['reservoirs', 'stations', 'junctions', 'pipes']:
            if key in config_data:
                items = config_data[key]
                
                # 处理列表格式
                if isinstance(items, list):
                    topology_data[key] = []
                    for item in items:
                        if isinstance(item, dict):
                            topology_data[key].append(item)
                        else:
                            topology_data[key].append({'name': str(item), 'type': key[:-1]})
                            
                # 处理字典格式
                elif isinstance(items, dict):
                    topology_data[key] = []
                    for name, info in items.items():
                        if isinstance(info, dict):
                            item_data = info.copy()
                            item_data['name'] = name
                            if 'type' not in item_data:
                                item_data['type'] = key[:-1]
                            topology_data[key].append(item_data)
                        else:
                            topology_data[key].append({'name': name, 'type': key[:-1]})
                            
        # 处理连接关系
        if 'connections' in config_data:
            topology_data['connections'] = config_data['connections']
            
        return topology_data
    
    def generate_topology(self, config_data: Dict, style: str = 'intuitive_system') -> Optional[str]:
        """
        生成拓扑图
        
        Args:
            config_data: 配置数据
            style: 拓扑图样式
        
        Returns:
            生成的拓扑图路径或文本
        """
        if style not in self.topology_styles:
            raise ValueError(f"不支持的拓扑图样式: {style}")
            
        topology_data = self._convert_config_to_topology(config_data)
        
        if style == 'text_ascii':
            return self._generate_text_ascii_topology(topology_data)
        else:
            generator_class = self.topology_styles[style]['generator_class']
            if generator_class is None:
                raise ValueError(f"无法生成样式: {style}")
                
            generator = generator_class()
            output_path = self.output_dir / f"{self.topology_styles[style]['name']}.png"
            generator.generate_topology_image(topology_data, output_path=output_path)
            return str(output_path)
            
    def _generate_text_ascii_topology(self, topology_data: Dict) -> str:
        """生成文本ASCII格式拓扑图"""
        lines = []
        lines.append("水力建模系统架构")
        lines.append("├── 水力建模层")
        
        # 水库模型
        if 'reservoirs' in topology_data:
            for res in topology_data['reservoirs']:
                name = res.get('name', res.get('id', ''))
                lines.append(f"│   ├── ReservoirModel ({name})")
        
        # 枢纽站模型
        if 'stations' in topology_data:
            for station in topology_data['stations']:
                name = station.get('name', station.get('id', ''))
                lines.append(f"│   ├── ComplexStationModel ({name})")
        
        # 连接点模型
        if 'junctions' in topology_data:
            for junction in topology_data['junctions']:
                name = junction.get('name', junction.get('id', ''))
                lines.append(f"│   ├── JunctionModel ({name})")
        
        # 管道模型
        if 'pipes' in topology_data:
            for pipe in topology_data['pipes']:
                name = pipe.get('name', pipe.get('id', ''))
                lines.append(f"│   └── PressurizedPipeModel ({name})")
        
        lines.append("├── 求解层")
        lines.append("│   ├── ImplicitSolverAgent (联合求解器)")
        lines.append("│   └── SolverConfig (求解器配置)")
        lines.append("├── 网络构建层")
        lines.append("│   ├── NetworkBuilder (网络构建器)")
        lines.append("│   ├── TopologyValidator (拓扑验证器)")
        lines.append("│   └── ModelFactory系列 (模型工厂)")
        lines.append("└── 配置管理层")
        lines.append("    ├── ConfigManager (配置管理器)")
        lines.append("    ├── ConfigValidator (配置验证器)")
        lines.append("    └── NetworkConfiguration (网络配置)")
        
        return "\n".join(lines)

def demo_auto_generation():
    """演示自动拓扑图生成"""
    print("🎨 复杂水力枢纽系统拓扑图自动生成演示")
    print("="*60)
    
    # 创建自动生成器
    auto_gen = AutoTopologyGenerator()
    
    # 检查示例配置文件
    config_path = "../../examples/configs/complex_hub_network.yaml"
    if not os.path.exists(config_path):
        print("⚠️ 示例配置文件不存在，创建简化演示配置")
        
        # 创建演示配置
        demo_config = {
            'system': {
                'name': '复杂水力枢纽系统',
                'description': '包含上下游水库和中间控制结构的综合系统'
            },
            'reservoirs': {
                'upstream_reservoir': {
                    'name': '上游水库',
                    'initial_level': 110.0,
                    'capacity_function': 'rectangular'
                },
                'downstream_reservoir': {
                    'name': '下游调节池', 
                    'initial_level': 92.0,
                    'capacity_function': 'rectangular'
                }
            },
            'stations': {
                'main_control': {
                    'name': '主控闸站',
                    'station_type': 'gate_station',
                    'devices': ['main_gate']
                }
            },
            'junctions': {
                'flow_splitter': {
                    'name': '分流枢纽',
                    'junction_type': 'splitter'
                }
            },
            'pipes': {
                'main_pipe': {
                    'name': '输水主管',
                    'length': 2000,
                    'diameter': 2.5,
                    'upstream_node': 'upstream_reservoir',
                    'downstream_node': 'main_control'
                },
                'outlet_pipe': {
                    'name': '泄洪渠',
                    'length': 1500,
                    'diameter': 2.0,
                    'upstream_node': 'flow_splitter',
                    'downstream_node': 'downstream_reservoir'
                }
            },
            'connections': [
                {'from': 'main_control', 'to': 'flow_splitter', 'label': '20.3m³/s'},
                {'from': 'flow_splitter', 'to': 'downstream_reservoir', 'label': '7.6m³/s'}
            ]
        }
        
        # 保存演示配置
        os.makedirs("../../examples/configs", exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(demo_config, f, default_flow_style=False, allow_unicode=True)
        
        print(f"✅ 演示配置已创建: {config_path}")
    
    # 生成拓扑图
    try:
        output_paths = auto_gen.from_config_file(config_path, "./topology_outputs")
        
        print("\n📊 生成的拓扑图:")
        for style, path in output_paths.items():
            print(f"  {style}: {path}")
        
        # 生成文本版本
        text_topology = auto_gen.generate_text_topology(config_path)
        print(f"\n📝 文本版拓扑图:")
        print(text_topology)
        
        # 保存文本版本
        os.makedirs("./topology_outputs", exist_ok=True)
        with open("./topology_outputs/文本版拓扑图.txt", 'w', encoding='utf-8') as f:
            f.write(text_topology)
        
        print(f"\n🎉 自动拓扑图生成完成！")
        print(f"   支持的样式: 直观系统图、分层架构图、流程示意图、文本ASCII图")
        
    except Exception as e:
        print(f"❌ 生成失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    demo_auto_generation()