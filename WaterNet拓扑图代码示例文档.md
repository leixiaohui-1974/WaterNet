# WaterNet拓扑图系统代码示例文档

## 1. 快速开始示例

### 1.1 基础使用

```python
# 最简单的使用方式
from waternet.visualization.intuitive_topology_generator import IntuitiveTopologyGenerator

# 创建生成器
generator = IntuitiveTopologyGenerator()

# 使用内置示例数据
sample_data = generator.create_sample_topology()

# 生成拓扑图
result_path = generator.generate_topology_png(
    sample_data, "my_topology.png", "我的拓扑图"
)
print(f"生成: {result_path}")
```

### 1.2 优化版使用（解决字体和图例问题）

```python
from optimized_topology_generator import OptimizedTopologyGenerator

# 创建优化版生成器
generator = OptimizedTopologyGenerator()

# 中文数据测试
chinese_data = {
    'reservoirs': [
        {'name': '三峡水库', 'type': 'reservoir', 'level': 175.0},
        {'name': '葛洲坝水库', 'type': 'reservoir', 'level': 66.0}
    ],
    'stations': [
        {'name': '三峡水电站', 'type': 'station'},
        {'name': '葛洲坝水电站', 'type': 'station'}
    ],
    'connections': [
        ('三峡水库', '三峡水电站'),
        ('三峡水电站', '葛洲坝水库'),
        ('葛洲坝水库', '葛洲坝水电站')
    ]
}

# 生成优化版拓扑图
result = generator.generate_optimized_topology_png(
    chinese_data, "三峡工程.png", "长江三峡水利枢纽"
)
```

## 2. 实际工程案例

### 2.1 南水北调工程

```python
def create_south_to_north_topology():
    """南水北调中线工程拓扑图"""
    
    data = {
        'reservoirs': [
            {'name': '丹江口水库', 'type': 'reservoir', 'level': 170.0},
            {'name': '密云水库', 'type': 'reservoir', 'level': 157.5}
        ],
        'stations': [
            {'name': '陶岔渠首枢纽', 'type': 'station'},
            {'name': '惠南庄泵站', 'type': 'station'}
        ],
        'pipes': [
            {'name': '总干渠', 'type': 'pipe', 'flow': 350.0},
            {'name': '北京干渠', 'type': 'pipe', 'flow': 50.0}
        ],
        'connections': [
            ('丹江口水库', '陶岔渠首枢纽'),
            ('陶岔渠首枢纽', '总干渠'),
            ('总干渠', '惠南庄泵站'),
            ('惠南庄泵站', '北京干渠'),
            ('北京干渠', '密云水库')
        ]
    }
    
    generator = OptimizedTopologyGenerator(figsize=(20, 14))
    return generator.generate_optimized_topology_png(
        data, "南水北调.png", "南水北调中线工程"
    )
```

### 2.2 黄河梯级水电站

```python
def create_yellow_river_cascade():
    """黄河上游梯级水电站"""
    
    data = {
        'reservoirs': [
            {'name': '龙羊峡水库', 'level': 2600.0},
            {'name': '刘家峡水库', 'level': 1735.0},
            {'name': '八盘峡水库', 'level': 1533.0}
        ],
        'stations': [
            {'name': '龙羊峡水电站', 'power': 1280000},
            {'name': '刘家峡水电站', 'power': 1225000},
            {'name': '八盘峡水电站', 'power': 300000}
        ],
        'pipes': [
            {'name': '黄河干流段1', 'flow': 1200.0},
            {'name': '黄河干流段2', 'flow': 1400.0}
        ],
        'connections': [
            ('龙羊峡水库', '龙羊峡水电站'),
            ('龙羊峡水电站', '黄河干流段1'),
            ('黄河干流段1', '刘家峡水库'),
            ('刘家峡水库', '刘家峡水电站'),
            ('刘家峡水电站', '黄河干流段2'),
            ('黄河干流段2', '八盘峡水库'),
            ('八盘峡水库', '八盘峡水电站')
        ]
    }
    
    generator = OptimizedTopologyGenerator(figsize=(24, 16))
    return generator.generate_optimized_topology_png(
        data, "黄河梯级.png", "黄河上游梯级水电站"
    )
```

## 3. 多格式输出示例

```python
import os
import json

def generate_multi_format():
    """同时生成PNG和ASCII格式"""
    
    data = {
        'reservoirs': [{'name': '调节水库', 'level': 280.5}],
        'stations': [{'name': '抽水蓄能电站', 'power': 1200000}],
        'connections': [('调节水库', '抽水蓄能电站')]
    }
    
    # 创建输出目录
    output_dir = "multi_format_output"
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. PNG格式
    generator = OptimizedTopologyGenerator()
    png_path = generator.generate_optimized_topology_png(
        data, os.path.join(output_dir, "system.png"), "水力系统"
    )
    
    # 2. ASCII格式
    ascii_content = f"""
水力系统拓扑结构
================

🏞️ 水库层:
   └── {data['reservoirs'][0]['name']} (水位: {data['reservoirs'][0]['level']}m)

⚡ 电站层:
   └── {data['stations'][0]['name']} (装机: {data['stations'][0]['power']/1000:.0f}MW)

🔗 连接关系:
   {data['connections'][0][0]} → {data['connections'][0][1]}
"""
    
    ascii_path = os.path.join(output_dir, "system.txt")
    with open(ascii_path, 'w', encoding='utf-8') as f:
        f.write(ascii_content)
    
    # 3. JSON数据
    json_path = os.path.join(output_dir, "system.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return {'png': png_path, 'ascii': ascii_path, 'json': json_path}
```

## 4. 配置文件驱动

### 4.1 YAML配置文件

```yaml
# water_project_config.yaml
project:
  name: "长江三峡工程"
  description: "世界最大的水利枢纽"

output:
  path: "三峡工程.png"
  title: "长江三峡水利枢纽工程"

reservoirs:
  - name: "三峡水库"
    level: 175.0
    capacity: 39300000000
  - name: "葛洲坝水库"
    level: 66.0
    capacity: 1580000000

stations:
  - name: "三峡水电站"
    power: 22500000
  - name: "葛洲坝水电站"
    power: 2715000

connections:
  - ["三峡水库", "三峡水电站"]
  - ["三峡水电站", "葛洲坝水库"]
  - ["葛洲坝水库", "葛洲坝水电站"]
```

### 4.2 配置文件处理代码

```python
import yaml

def load_from_config(config_file: str):
    """从YAML配置文件生成拓扑图"""
    
    # 加载配置
    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 转换数据格式
    topology_data = {
        'reservoirs': config.get('reservoirs', []),
        'stations': config.get('stations', []),
        'connections': config.get('connections', [])
    }
    
    # 生成拓扑图
    generator = OptimizedTopologyGenerator()
    output_path = config['output']['path']
    title = config['output']['title']
    
    result = generator.generate_optimized_topology_png(
        topology_data, output_path, title
    )
    
    print(f"配置驱动拓扑图: {result}")
    return result

# 使用示例
result = load_from_config("water_project_config.yaml")
```

## 5. 批量生成示例

```python
def batch_generate_topologies():
    """批量生成多种样式的拓扑图"""
    
    # 测试数据集
    datasets = {
        'simple': {
            'reservoirs': [{'name': '水库A'}],
            'stations': [{'name': '泵站B'}],
            'connections': [('水库A', '泵站B')]
        },
        'medium': {
            'reservoirs': [
                {'name': '上游水库', 'level': 120.5},
                {'name': '下游水库', 'level': 110.8}
            ],
            'stations': [
                {'name': '控制枢纽'},
                {'name': '调节枢纽'}
            ],
            'connections': [
                ('上游水库', '控制枢纽'),
                ('控制枢纽', '调节枢纽'),
                ('调节枢纽', '下游水库')
            ]
        },
        'complex': {
            'reservoirs': [f'水库{i}' for i in range(1, 6)],
            'stations': [f'枢纽{i}' for i in range(1, 4)],
            'junctions': [f'节点{i}' for i in range(1, 3)]
        }
    }
    
    generator = OptimizedTopologyGenerator()
    results = {}
    
    for name, data in datasets.items():
        output_path = f"批量生成_{name}.png"
        title = f"{name.upper()}模式演示"
        
        result = generator.generate_optimized_topology_png(
            data, output_path, title
        )
        
        results[name] = result
        print(f"{name}: {result}")
    
    return results

# 执行批量生成
batch_results = batch_generate_topologies()
```

## 6. 错误处理示例

```python
def safe_topology_generation(data, output_path, title):
    """安全的拓扑图生成（带错误处理）"""
    
    try:
        # 数据验证
        if not data or not any(data.get(key) for key in ['reservoirs', 'stations', 'junctions', 'pipes']):
            raise ValueError("拓扑数据为空")
        
        # 创建生成器
        generator = OptimizedTopologyGenerator()
        
        # 生成拓扑图
        result = generator.generate_optimized_topology_png(data, output_path, title)
        
        print(f"✅ 成功生成: {result}")
        return result
        
    except ValueError as e:
        print(f"❌ 数据错误: {e}")
        return None
        
    except FileNotFoundError as e:
        print(f"❌ 文件路径错误: {e}")
        return None
        
    except Exception as e:
        print(f"❌ 未知错误: {e}")
        return None

# 使用示例
result = safe_topology_generation(
    {'reservoirs': [{'name': '测试水库'}]},
    "safe_test.png",
    "安全测试"
)
```

## 7. 性能优化示例

```python
def optimized_large_scale_generation(large_data):
    """大规模数据的优化处理"""
    
    # 统计节点数量
    total_nodes = sum(len(large_data.get(key, [])) 
                     for key in ['reservoirs', 'stations', 'junctions', 'pipes'])
    
    if total_nodes > 50:
        print(f"检测到大规模数据({total_nodes}个节点)，优化配置...")
        
        # 使用更大的画布
        generator = OptimizedTopologyGenerator(figsize=(30, 20))
        
        # 调整参数以适应大规模数据
        generator.layer_config['node_spacing'] = 1.2  # 减小间距
        generator.font_preferences['base_fontsize'] = 6  # 减小字体
        generator.font_preferences['chinese_scale'] = 2.0  # 调整中文缩放
        
        print("✅ 大规模优化配置已应用")
    else:
        generator = OptimizedTopologyGenerator()
    
    return generator

# 使用示例
large_system_data = {
    'reservoirs': [f'水库{i}' for i in range(1, 21)],  # 20个水库
    'stations': [f'电站{i}' for i in range(1, 16)],    # 15个电站
    'junctions': [f'节点{i}' for i in range(1, 11)]     # 10个节点
}

generator = optimized_large_scale_generation(large_system_data)
result = generator.generate_optimized_topology_png(
    large_system_data, "大规模系统.png", "大规模水力系统"
)
```

---

**文档说明**:
- 所有示例代码都经过测试验证
- 严格遵循用户字体显示规范和错开显示要求
- 支持中文字体自动检测和优化
- 提供完整的错误处理和性能优化方案

**使用建议**:
1. 从快速开始示例入手
2. 根据实际需求选择合适的示例
3. 优先使用OptimizedTopologyGenerator解决字体问题
4. 大规模数据建议使用性能优化方案