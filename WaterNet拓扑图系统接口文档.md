# WaterNet拓扑图系统接口文档

## 1. 核心类接口

### 1.1 IntuitiveTopologyGenerator

#### 类概述
```python
class IntuitiveTopologyGenerator:
    """
    直观拓扑图生成器
    
    基于COMPLEX_HUB_IMPLEMENTATION_REPORT.md的分层架构算法，
    实现水力建模系统的拓扑图自动生成。
    """
```

#### 构造函数
```python
def __init__(self, figsize=(14, 10)):
    """
    初始化生成器
    
    Args:
        figsize (tuple): 图形尺寸，默认(14, 10)
        
    Attributes:
        font_preferences (dict): 字体偏好配置
        layer_config (dict): 层级配置参数
        color_scheme (dict): 颜色方案配置
    """
```

#### 主要方法

##### generate_topology_png
```python
def generate_topology_png(self, topology_data: Dict, output_path: str,
                        title: str = "直观系统拓扑图") -> str:
    """
    生成拓扑图PNG文件
    
    Args:
        topology_data (Dict): 拓扑数据字典，包含以下键值：
            - reservoirs: 水库列表
            - stations: 枢纽站列表  
            - junctions: 连接点列表
            - pipes: 管道列表
            - connections: 连接关系列表
        output_path (str): 输出文件路径
        title (str): 图标题，默认"直观系统拓扑图"
        
    Returns:
        str: 生成的文件路径
        
    Raises:
        FileNotFoundError: 输出目录不存在
        ValueError: 数据格式错误
        
    Example:
        >>> generator = IntuitiveTopologyGenerator()
        >>> data = generator.create_sample_topology()
        >>> path = generator.generate_topology_png(data, "my_topology.png")
        >>> print(f"生成文件: {path}")
    """
```

##### create_sample_topology
```python
def create_sample_topology(self) -> Dict:
    """
    创建示例拓扑数据
    
    Returns:
        Dict: 标准格式的拓扑数据字典
        
    Example:
        >>> generator = IntuitiveTopologyGenerator()
        >>> sample_data = generator.create_sample_topology()
        >>> print(sample_data.keys())
        dict_keys(['reservoirs', 'stations', 'junctions', 'pipes', 'connections'])
    """
```

##### apply_font_preferences
```python
def apply_font_preferences(self, text: str, base_size: Optional[float] = None) -> dict:
    """
    应用用户字体偏好配置
    
    严格遵循用户规范：
    - 汉字字体放大3倍（黑色显示）
    - 数字字体翻倍（红色显示）
    - 自动检测文本类型
    
    Args:
        text (str): 待处理的文本
        base_size (float, optional): 基础字体大小，默认使用配置值
        
    Returns:
        dict: 字体样式配置字典，包含：
            - fontsize: 字体大小
            - color: 字体颜色
            - fontweight: 字体粗细
            - family: 字体族
            
    Example:
        >>> generator = IntuitiveTopologyGenerator()
        >>> style = generator.apply_font_preferences("上游水库")
        >>> print(style)
        {'fontsize': 24.0, 'color': 'black', 'fontweight': 'bold', 'family': 'SimHei'}
    """
```

### 1.2 OptimizedTopologyGenerator

#### 类概述
```python
class OptimizedTopologyGenerator:
    """
    优化版拓扑图生成器
    
    解决汉字字体丢失问题，图例布局优化，
    严格遵循用户字体显示规范和错开显示要求。
    """
```

#### 构造函数
```python
def __init__(self, figsize=(16, 12)):
    """
    初始化优化版生成器
    
    Args:
        figsize (tuple): 图形尺寸，默认(16, 12)，为图例预留更多空间
        
    Features:
        - 中文字体自动检测
        - 图例右侧布局
        - 错开显示规范
        - 文字背景框
    """
```

#### 主要方法

##### generate_optimized_topology_png
```python
def generate_optimized_topology_png(self, topology_data: Dict, output_path: str,
                                  title: str = "优化版拓扑图") -> str:
    """
    生成优化版拓扑图PNG文件
    
    优化特点：
    - 解决汉字字体丢失问题
    - 图例放置在右侧避免重叠
    - 严格遵循用户字体显示规范
    - 节点间距优化避免重叠
    - 文字背景框提升可读性
    
    Args:
        topology_data (Dict): 拓扑数据字典
        output_path (str): 输出文件路径
        title (str): 图标题
        
    Returns:
        str: 生成的文件路径
        
    Example:
        >>> generator = OptimizedTopologyGenerator()
        >>> data = create_chinese_topology_data()
        >>> path = generator.generate_optimized_topology_png(
        ...     data, "optimized.png", "优化版中文拓扑图"
        ... )
    """
```

##### create_legend
```python
def create_legend(self, layout: Dict) -> None:
    """
    创建图例，放置在右侧避免与其他对象重叠
    
    Args:
        layout (Dict): 布局信息字典
        
    Features:
        - 图例位置：右侧边缘
        - 图例背景：白色背景框
        - 图例样式：与实际节点一致
        - 字体规范：图例字体放大2倍
        
    Example:
        >>> generator = OptimizedTopologyGenerator()
        >>> layout = generator.create_layered_layout(topology_data)
        >>> generator.create_legend(layout)
    """
```

### 1.3 EnhancedTopologyGenerator

#### 类概述
```python
class EnhancedTopologyGenerator:
    """
    增强版拓扑图生成器
    
    支持多种拓扑图展示方式，智能选择最佳展示模式。
    """
```

#### 智能选择方法
```python
def intelligent_layout_selection(self, topology_data: Dict) -> str:
    """
    根据数据特点智能选择最佳展示方式
    
    选择逻辑：
    - 节点数 ≤ 5 → simple_flow (简洁流程图)
    - 节点数 ≤ 10 且有数值 → flow_direction (流向示意图)  
    - 节点数 > 10 → table_mode (表格模式)
    - 复杂拓扑 → graphical_mode (图形化模式)
    
    Args:
        topology_data (Dict): 拓扑数据字典
        
    Returns:
        str: 选择的展示模式
        
    Example:
        >>> generator = EnhancedTopologyGenerator()
        >>> mode = generator.intelligent_layout_selection(simple_data)
        >>> print(mode)  # 'simple_flow'
    """
```

---

## 2. 数据格式规范

### 2.1 拓扑数据格式

#### 完整数据结构
```python
topology_data = {
    'reservoirs': [
        {
            'name': str,           # 水库名称（必需）
            'type': 'reservoir',   # 类型标识（必需）
            'level': float,        # 水位（可选）
            'capacity': float,     # 库容（可选）
            'volume': float        # 蓄水量（可选）
        }
    ],
    'stations': [
        {
            'name': str,           # 枢纽站名称（必需）
            'type': 'station',     # 类型标识（必需）
            'equipment': list,     # 设备列表（可选）
            'power': float         # 装机功率（可选）
        }
    ],
    'junctions': [
        {
            'name': str,           # 连接点名称（必需）
            'type': 'junction',    # 类型标识（必需）
            'elevation': float     # 高程（可选）
        }
    ],
    'pipes': [
        {
            'name': str,           # 管道名称（必需）
            'type': 'pipe',        # 类型标识（必需）
            'flow': float,         # 流量（可选）
            'length': float,       # 长度（可选）
            'diameter': float      # 直径（可选）
        }
    ],
    'connections': [
        ('源节点名称', '目标节点名称'),  # 连接关系元组
        # ... 更多连接
    ]
}
```

#### 最小数据结构
```python
# 最简数据格式
minimal_data = {
    'reservoirs': ['水库A', '水库B'],
    'connections': [('水库A', '水库B')]
}
```

#### 字符串格式支持
```python
# 支持字符串格式的组件
string_format_data = {
    'reservoirs': ['上游水库', '下游水库'],
    'stations': ['枢纽站A'],
    'pipes': ['连接管道'],
    'connections': [
        ('上游水库', '枢纽站A'),
        ('枢纽站A', '下游水库')
    ]
}
```

### 2.2 配置格式

#### 字体配置
```python
font_preferences = {
    'chinese_scale': 3.0,      # 汉字放大倍数
    'number_scale': 2.0,       # 数字放大倍数
    'number_color': 'red',     # 数字颜色
    'chinese_color': 'black',  # 汉字颜色
    'legend_scale': 2.0,       # 图例放大倍数
    'base_fontsize': 8         # 基础字体大小
}
```

#### 布局配置
```python
layer_config = {
    'spacing': 2.5,           # 层间距
    'node_spacing': 2.0,      # 节点间距
    'min_width': 1.8,         # 最小节点宽度
    'min_height': 1.0         # 最小节点高度
}
```

#### 颜色配置
```python
color_scheme = {
    'reservoir': {'fill': '#E3F2FD', 'edge': '#1976D2', 'text': '#0D47A1'},
    'station': {'fill': '#F3E5F5', 'edge': '#7B1FA2', 'text': '#4A148C'}, 
    'junction': {'fill': '#E8F5E8', 'edge': '#388E3C', 'text': '#1B5E20'},
    'pipe': {'fill': '#FFF3E0', 'edge': '#F57C00', 'text': '#E65100'},
}
```

---

## 3. 使用示例

### 3.1 基础使用示例

#### 最简单的使用方式
```python
from waternet.visualization.intuitive_topology_generator import IntuitiveTopologyGenerator

# 创建生成器
generator = IntuitiveTopologyGenerator()

# 使用内置示例数据
sample_data = generator.create_sample_topology()

# 生成拓扑图
result_path = generator.generate_topology_png(
    sample_data,
    "example_topology.png",
    "示例拓扑图"
)

print(f"拓扑图已生成: {result_path}")
```

#### 自定义数据示例
```python
# 创建自定义拓扑数据
custom_data = {
    'reservoirs': [
        {'name': '龙羊峡水库', 'type': 'reservoir', 'level': 2600.0, 'capacity': 27400000},
        {'name': '刘家峡水库', 'type': 'reservoir', 'level': 1735.0, 'capacity': 5700000}
    ],
    'stations': [
        {'name': '龙羊峡水电站', 'type': 'station', 'power': 1280},
        {'name': '刘家峡水电站', 'type': 'station', 'power': 1225}
    ],
    'pipes': [
        {'name': '黄河干流', 'type': 'pipe', 'flow': 1200.0, 'length': 130000}
    ],
    'connections': [
        ('龙羊峡水库', '龙羊峡水电站'),
        ('龙羊峡水电站', '黄河干流'),
        ('黄河干流', '刘家峡水库'),
        ('刘家峡水库', '刘家峡水电站')
    ]
}

# 生成自定义拓扑图
result_path = generator.generate_topology_png(
    custom_data,
    "黄河梯级水电站拓扑图.png",
    "黄河上游梯级水电站系统"
)
```

### 3.2 优化版使用示例

#### 解决中文字体问题
```python
from optimized_topology_generator import OptimizedTopologyGenerator

# 创建优化版生成器
opt_generator = OptimizedTopologyGenerator()

# 包含大量中文的数据
chinese_data = {
    'reservoirs': [
        {'name': '三峡水库', 'type': 'reservoir', 'level': 175.0},
        {'name': '葛洲坝水库', 'type': 'reservoir', 'level': 66.0},
        {'name': '丹江口水库', 'type': 'reservoir', 'level': 170.0}
    ],
    'stations': [
        {'name': '三峡水电站', 'type': 'station'},
        {'name': '葛洲坝水电站', 'type': 'station'},
        {'name': '丹江口水电站', 'type': 'station'}
    ],
    'junctions': [
        {'name': '长江干流汇合点', 'type': 'junction'},
        {'name': '汉江入长江口', 'type': 'junction'}
    ],
    'connections': [
        ('三峡水库', '三峡水电站'),
        ('三峡水电站', '长江干流汇合点'),
        ('长江干流汇合点', '葛洲坝水库'),
        ('丹江口水库', '汉江入长江口'),
        ('汉江入长江口', '长江干流汇合点')
    ]
}

# 生成优化版拓扑图
result_path = opt_generator.generate_optimized_topology_png(
    chinese_data,
    "长江流域水电站拓扑图.png",
    "长江流域梯级水电站系统拓扑图"
)

print(f"优化版拓扑图已生成: {result_path}")
print("优化特点:")
print("- 中文字体完美显示")
print("- 图例位于右侧，不与节点重叠")
print("- 水位数字红色显示")
print("- 节点标签错开显示")
```

### 3.3 批量生成示例

#### 多种算法模式对比
```python
def generate_algorithm_comparison():
    """生成多种算法模式的对比图"""
    
    # 测试数据集
    test_datasets = {
        'simple': {
            'reservoirs': [{'name': '水库A', 'type': 'reservoir'}],
            'stations': [{'name': '泵站B', 'type': 'station'}],
            'connections': [('水库A', '泵站B')]
        },
        'medium': {
            'reservoirs': [
                {'name': '上游水库', 'type': 'reservoir', 'level': 120.5},
                {'name': '中游水库', 'type': 'reservoir', 'level': 115.2},
                {'name': '下游水库', 'type': 'reservoir', 'level': 110.8}
            ],
            'stations': [
                {'name': '控制枢纽', 'type': 'station'},
                {'name': '调节枢纽', 'type': 'station'}
            ],
            'junctions': [
                {'name': '分流点', 'type': 'junction'},
                {'name': '汇流点', 'type': 'junction'}
            ],
            'connections': [
                ('上游水库', '控制枢纽'),
                ('控制枢纽', '分流点'),
                ('分流点', '中游水库'),
                ('分流点', '汇流点'),
                ('汇流点', '下游水库')
            ]
        },
        'complex': {
            'reservoirs': [f'水库{i}' for i in range(1, 8)],
            'stations': [f'枢纽{i}' for i in range(1, 6)],
            'junctions': [f'节点{i}' for i in range(1, 5)],
            'pipes': [f'管道{i}' for i in range(1, 10)]
        }
    }
    
    generator = OptimizedTopologyGenerator()
    results = {}
    
    for dataset_name, dataset in test_datasets.items():
        output_path = f"算法对比_{dataset_name}.png"
        title = f"{dataset_name.upper()}算法模式演示"
        
        result_path = generator.generate_optimized_topology_png(
            dataset, output_path, title
        )
        
        results[dataset_name] = result_path
        print(f"{dataset_name}模式: {result_path}")
    
    return results

# 执行批量生成
comparison_results = generate_algorithm_comparison()
```

### 3.4 配置文件驱动示例

#### YAML配置文件使用
```python
import yaml

def generate_from_yaml_config(config_file: str):
    """从YAML配置文件生成拓扑图"""
    
    # 加载YAML配置
    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 转换为拓扑数据格式
    topology_data = {
        'reservoirs': config.get('reservoirs', []),
        'stations': config.get('stations', []),
        'junctions': config.get('junctions', []),
        'pipes': config.get('pipes', []),
        'connections': config.get('connections', [])
    }
    
    # 创建生成器
    generator = OptimizedTopologyGenerator()
    
    # 生成拓扑图
    output_path = config.get('output_path', 'config_topology.png')
    title = config.get('title', '配置驱动拓扑图')
    
    result_path = generator.generate_optimized_topology_png(
        topology_data, output_path, title
    )
    
    print(f"配置驱动拓扑图: {result_path}")
    return result_path

# 使用示例
result = generate_from_yaml_config("examples/configs/complex_hub_network.yaml")
```

#### 示例YAML配置文件
```yaml
# water_system_config.yaml
title: "南水北调中线工程拓扑图"
output_path: "南水北调拓扑图.png"

reservoirs:
  - name: "丹江口水库"
    type: "reservoir"
    level: 170.0
    capacity: 33900000
  - name: "北京密云水库"
    type: "reservoir" 
    level: 157.5
    capacity: 4375000

stations:
  - name: "陶岔渠首枢纽"
    type: "station"
    equipment: ["闸门", "泵站"]
  - name: "惠南庄泵站"
    type: "station"
    equipment: ["泵站"]

pipes:
  - name: "总干渠"
    type: "pipe"
    flow: 350.0
    length: 1432000
  - name: "北京段干渠"
    type: "pipe"
    flow: 100.0
    length: 80000

connections:
  - ["丹江口水库", "陶岔渠首枢纽"]
  - ["陶岔渠首枢纽", "总干渠"]
  - ["总干渠", "惠南庄泵站"]
  - ["惠南庄泵站", "北京段干渠"]
  - ["北京段干渠", "北京密云水库"]
```

---

## 4. 错误处理

### 4.1 常见错误类型

#### 数据格式错误
```python
try:
    result = generator.generate_topology_png(invalid_data, "output.png")
except ValueError as e:
    print(f"数据格式错误: {e}")
    # 处理: 检查数据格式，确保必需字段存在
```

#### 文件路径错误
```python
try:
    result = generator.generate_topology_png(data, "/invalid/path/output.png")
except FileNotFoundError as e:
    print(f"路径错误: {e}")
    # 处理: 创建目录或使用有效路径
```

#### 字体缺失警告
```python
# 字体缺失时的处理
if available_font is None:
    print("警告: 未找到中文字体，汉字可能显示为方框")
    print("建议安装: Microsoft YaHei 或 SimHei 字体")
```

### 4.2 数据验证

#### 数据完整性检查
```python
def validate_topology_data(topology_data: Dict) -> bool:
    """验证拓扑数据完整性"""
    
    # 检查必需的键
    required_keys = ['reservoirs', 'stations', 'junctions', 'pipes']
    has_data = any(key in topology_data and topology_data[key] 
                   for key in required_keys)
    
    if not has_data:
        raise ValueError("拓扑数据为空，至少需要一种组件类型")
    
    # 检查连接关系的有效性
    if 'connections' in topology_data:
        all_nodes = set()
        for key in required_keys:
            if key in topology_data:
                for item in topology_data[key]:
                    if isinstance(item, dict):
                        all_nodes.add(item.get('name', ''))
                    else:
                        all_nodes.add(str(item))
        
        for source, target in topology_data['connections']:
            if source not in all_nodes:
                print(f"警告: 连接源节点 '{source}' 不存在")
            if target not in all_nodes:
                print(f"警告: 连接目标节点 '{target}' 不存在")
    
    return True
```

---

## 5. 性能优化建议

### 5.1 大规模数据处理
```python
# 对于大规模数据（节点数>50），建议使用表格模式
def handle_large_topology(topology_data: Dict):
    """处理大规模拓扑数据"""
    
    total_nodes = sum(len(topology_data.get(key, [])) 
                     for key in ['reservoirs', 'stations', 'junctions', 'pipes'])
    
    if total_nodes > 50:
        print("检测到大规模数据，建议使用表格模式")
        # 调整配置参数
        generator = OptimizedTopologyGenerator(figsize=(20, 16))
        generator.layer_config['node_spacing'] = 1.5  # 减小间距
        generator.font_preferences['base_fontsize'] = 6  # 减小字体
    
    return generator
```

### 5.2 内存优化
```python
# 分批处理大量拓扑图
def batch_generate_topologies(data_list: List[Dict], batch_size: int = 10):
    """分批生成拓扑图，避免内存溢出"""
    
    results = []
    for i in range(0, len(data_list), batch_size):
        batch = data_list[i:i+batch_size]
        
        for j, data in enumerate(batch):
            generator = OptimizedTopologyGenerator()
            output_path = f"batch_{i//batch_size}_item_{j}.png"
            
            result = generator.generate_optimized_topology_png(
                data, output_path, f"批次{i//batch_size}项目{j}"
            )
            results.append(result)
            
            # 释放内存
            del generator
    
    return results
```

---

**文档版本**: 1.0  
**更新时间**: 2025-10-04  
**适用版本**: WaterNet拓扑图系统 v1.0