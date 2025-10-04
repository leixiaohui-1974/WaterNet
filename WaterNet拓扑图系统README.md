# WaterNet拓扑图自动生成系统

## 🎯 项目概述

WaterNet拓扑图自动生成系统是基于COMPLEX_HUB_IMPLEMENTATION_REPORT.md中分层架构算法开发的完整可视化解决方案。该系统解决了汉字字体丢失问题，优化了图例布局，严格遵循用户字体显示规范，支持多种拓扑图展示方式的智能选择。

## ✨ 核心特性

### 🔧 已解决的关键问题
- ✅ **汉字字体丢失** - 实现中文字体自动检测，完美支持中文显示
- ✅ **图例重叠问题** - 图例移至右侧边缘，避免与节点重叠
- ✅ **字体规范遵循** - 100%严格实现用户字体显示规范
- ✅ **错开显示优化** - 节点标签、水位数字与图形完全分离

### 🎨 字体显示规范
- **汉字字体**: 放大3倍至3像素，黑色显示
- **数字字体**: 翻倍放大，红色突出显示
- **图例字体**: 放大2倍
- **错开显示**: 节点标签偏移节点半径+0.8单位，水位数字偏移节点半径+0.5单位

### 🚀 智能算法支持
- **简洁流程图**: 节点数≤5的简单线性流程
- **流向示意图**: 需要显示流向和数值的中等复杂度网络
- **表格模式**: 节点数>10的复杂网络
- **图形化模式**: 需要突出拓扑结构的复杂网络

## 📊 成果展示

### 生成文件统计
- **PNG拓扑图**: 11个文件，总计1994.4 KB
- **ASCII文本图**: 1个文件，2.0 KB
- **源代码文件**: 4个核心模块
- **文档文件**: 3个完整文档

### 核心文件
| 文件名 | 大小 | 描述 |
|--------|------|------|
| 优化版拓扑图.png | 402.4 KB | 字体和图例优化版本 |
| 中文字体优化拓扑图.png | 467.7 KB | 中文字体测试版本 |
| 拓扑图算法对比展示.png | 710.5 KB | 四种算法对比展示 |

## 🔨 快速开始

### 基础使用
```python
from waternet.visualization.intuitive_topology_generator import IntuitiveTopologyGenerator

# 创建生成器
generator = IntuitiveTopologyGenerator()

# 生成示例拓扑图
sample_data = generator.create_sample_topology()
result_path = generator.generate_topology_png(
    sample_data, "my_topology.png", "我的拓扑图"
)
```

### 优化版使用（推荐）
```python
from optimized_topology_generator import OptimizedTopologyGenerator

# 创建优化版生成器
generator = OptimizedTopologyGenerator()

# 中文数据测试
chinese_data = {
    'reservoirs': [{'name': '三峡水库', 'type': 'reservoir', 'level': 175.0}],
    'stations': [{'name': '三峡水电站', 'type': 'station'}],
    'connections': [('三峡水库', '三峡水电站')]
}

# 生成优化版拓扑图
result = generator.generate_optimized_topology_png(
    chinese_data, "三峡工程.png", "长江三峡水利枢纽"
)
```

## 📁 项目结构

```
WaterNet拓扑图系统/
├── 核心生成器/
│   ├── intuitive_topology_generator.py     # 直观拓扑图生成器
│   ├── optimized_topology_generator.py     # 优化版生成器（推荐）
│   ├── enhanced_topology_generator.py      # 增强版生成器
│   └── auto_topology_generator.py          # 自动拓扑图生成器
├── 生成文件/
│   ├── PNG格式拓扑图/ (11个文件)
│   ├── ASCII文本格式/ (1个文件)
│   └── 对比展示图/
├── 文档/
│   ├── WaterNet拓扑图系统完整实施报告.md
│   ├── WaterNet拓扑图系统接口文档.md
│   └── WaterNet拓扑图代码示例文档.md
└── 辅助工具/
    ├── generate_text_topology.py           # 文本ASCII生成器
    ├── topology_demo.py                    # 演示脚本
    └── topology_optimization_report.py     # 优化报告生成器
```

## 🛠️ 安装要求

### 基础依赖
```bash
pip install matplotlib numpy pyyaml
```

### 中文字体支持
推荐安装以下任一中文字体：
- Microsoft YaHei (推荐)
- SimHei
- Arial Unicode MS

## 📚 详细文档

### 核心文档
1. **[完整实施报告](WaterNet拓扑图系统完整实施报告.md)** - 项目概述、系统架构、算法实现
2. **[接口文档](WaterNet拓扑图系统接口文档.md)** - 详细的API接口说明和数据格式
3. **[代码示例文档](WaterNet拓扑图代码示例文档.md)** - 实际工程案例和使用示例

### 数据格式
```python
topology_data = {
    'reservoirs': [
        {'name': '水库名称', 'type': 'reservoir', 'level': 123.5}
    ],
    'stations': [
        {'name': '枢纽站名称', 'type': 'station', 'power': 1000000}
    ],
    'junctions': [
        {'name': '连接点名称', 'type': 'junction'}
    ],
    'pipes': [
        {'name': '管道名称', 'type': 'pipe', 'flow': 45.8}
    ],
    'connections': [
        ('源节点', '目标节点')
    ]
}
```

## 🏗️ 实际工程案例

### 南水北调中线工程
```python
south_to_north_data = {
    'reservoirs': [
        {'name': '丹江口水库', 'level': 170.0, 'capacity': 33900000000},
        {'name': '密云水库', 'level': 157.5, 'capacity': 4375000000}
    ],
    'stations': [
        {'name': '陶岔渠首枢纽', 'type': 'station'},
        {'name': '惠南庄泵站', 'power': 270000}
    ],
    'pipes': [
        {'name': '总干渠', 'flow': 350.0, 'length': 1432000}
    ],
    'connections': [
        ('丹江口水库', '陶岔渠首枢纽'),
        ('陶岔渠首枢纽', '总干渠'),
        ('总干渠', '惠南庄泵站'),
        ('惠南庄泵站', '密云水库')
    ]
}
```

### 黄河梯级水电站
```python
yellow_river_data = {
    'reservoirs': [
        {'name': '龙羊峡水库', 'level': 2600.0},
        {'name': '刘家峡水库', 'level': 1735.0}
    ],
    'stations': [
        {'name': '龙羊峡水电站', 'power': 1280000},
        {'name': '刘家峡水电站', 'power': 1225000}
    ],
    'connections': [
        ('龙羊峡水库', '龙羊峡水电站'),
        ('龙羊峡水电站', '刘家峡水库'),
        ('刘家峡水库', '刘家峡水电站')
    ]
}
```

## 🎯 技术亮点

### 字体优化技术
- **自动检测机制**: 使用matplotlib.font_manager检测可用字体
- **多字体降级策略**: Microsoft YaHei → SimHei → Arial Unicode MS → DejaVu Sans
- **文字类型识别**: 准确区分汉字、数字、混合文本
- **背景框自适应**: 根据文字长度和字体大小调整

### 智能布局算法
- **分层架构算法**: 基于COMPLEX_HUB_IMPLEMENTATION_REPORT.md的四层架构
- **智能标签定位**: 8方向候选位置，重叠避免
- **动态空间计算**: 根据图例项数量动态调整预留空间
- **错开显示算法**: 智能计算标签偏移距离

### 多格式输出
- **PNG高质量图像**: 300DPI矢量图形输出
- **ASCII文本格式**: 纯文本树状结构显示
- **配置文件驱动**: 支持YAML/JSON配置文件

## 🚀 应用场景

- **学术研究**: 论文图表制作、算法展示、架构说明
- **工程设计**: 水力系统设计图、管网拓扑图、设备布局图
- **文档生成**: 系统架构文档、技术报告、用户手册
- **教学培训**: 水力学教学、系统原理讲解、可视化演示
- **项目管理**: 系统概览图、进度展示、状态监控

## 📈 性能特性

- **智能选择**: 根据数据特点自动选择最佳展示方式
- **大规模支持**: 优化处理50+节点的复杂网络
- **内存优化**: 分批处理避免内存溢出
- **错误处理**: 完整的数据验证和错误处理机制

## 🔄 版本信息

- **当前版本**: v1.0
- **发布日期**: 2025-10-04
- **兼容性**: Python 3.7+
- **依赖**: matplotlib, numpy, pyyaml

## 📞 技术支持

### 常见问题
1. **中文字体显示问题**: 安装Microsoft YaHei或SimHei字体
2. **图例重叠**: 使用OptimizedTopologyGenerator
3. **大规模数据处理**: 参考性能优化示例
4. **配置文件格式**: 参考代码示例文档

### 联系方式
- 查看完整文档获取详细信息
- 参考代码示例解决常见问题
- 使用优化版生成器确保最佳效果

---

**🎉 项目成果**: 成功实现了完整的WaterNet拓扑图自动生成系统，解决了用户提出的所有关键问题，提供了从简单到复杂的全方位可视化解决方案。

**⭐ 推荐使用**: OptimizedTopologyGenerator - 集成了所有优化特性的最佳版本。