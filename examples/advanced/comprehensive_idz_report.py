#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IDZ模型辨识综合分析报告
整合所有分析结果，提供完整的系统辨识总结

基于非恒定流阶跃响应数据的IDZ模型辨识项目总结
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

def create_comprehensive_report():
    """创建综合分析报告"""
    
    report_content = f"""
# IDZ模型辨识综合分析报告
## 基于非恒定流阶跃响应的水力系统动态特性辨识

**分析日期**: {datetime.now().strftime('%Y年%m月%d日')}
**项目**: 五断面明渠非恒定流IDZ模型辨识
**方法**: 阶跃响应系统辨识技术

---

## 1. 项目概述

本项目基于非恒定流阶跃响应分析，对五断面明渠水力系统进行了系统的IDZ（输入-扰动-零点）模型辨识。
通过多种辨识算法和改进方法，成功建立了分布参数传递函数模型。

### 1.1 系统配置
- **断面数量**: 5个梯形断面
- **空间范围**: 0-2.0公里河道
- **输入类型**: 上游流量阶跃、下游水位阶跃
- **响应变量**: 水位、流量时间序列

### 1.2 分析场景
1. **上游正阶跃**: 流量从30 m³/s突增至50 m³/s
2. **上游负阶跃**: 流量从50 m³/s突减至30 m³/s  
3. **下游水位阶跃**: 水位从101.0m突增至101.5m

---

## 2. 主要发现

### 2.1 系统动态特性
经过详细的系统辨识分析，发现该水力系统具有以下主要特征：

#### **传递函数形式**
辨识出的传递函数为典型的**积分环节+一阶滞后**形式：

```
G(s) = K / [s·(τs + 1)] · exp(-td·s)
```

其中：
- **K**: 稳态增益 ≈ 1.0000
- **τ**: 时间常数 ≈ 25分钟
- **td**: 传播延迟 = 16.67 × 距离(km) 分钟

#### **空间传播特性**
1. **传播延迟**: 与距离呈严格线性关系
   - 延迟梯度: 16.67分钟/公里
   - 等效波速: 1.0 m/s
   
2. **响应衰减**: 沿程响应强度轻微衰减
   - 衰减系数: -0.0099 /km
   - 响应强度变化: 0.039068 → 0.039851

### 2.2 模型拟合质量
不同断面的拟合效果表现出明显的**空间梯度**：

| 断面 | 距离(km) | R² | 传播延迟(分钟) | 时间常数(分钟) |
|------|----------|----|--------------|--------------| 
| 断面0 | 0.0 | 0.6381 | 0.0 | 25.596 |
| 断面1 | 0.5 | 0.6786 | 8.3 | 25.361 |
| 断面2 | 1.0 | 0.7158 | 16.7 | 25.183 |
| 断面3 | 1.5 | 0.7470 | 25.0 | 25.112 |
| 断面4 | 2.0 | 0.7745 | 33.3 | 25.093 |

**关键观察**: 
- 下游断面拟合精度更高（R²从0.64提升至0.77）
- 上游直接扰动区域响应更复杂，线性化误差较大
- 中下游区域响应更接近理论传递函数形式

---

## 3. 技术方法与创新

### 3.1 多层次辨识策略
本项目采用了**渐进式改进**的辨识方法：

1. **基础IDZ辨识** (`idz_model_identification.py`)
   - 标准一阶/二阶系统辨识
   - 发现了传统方法的局限性
   
2. **改进水力辨识** (`improved_idz_identification.py`)
   - 专门针对水力系统特性优化
   - 引入波浪传播分析
   - 处理线性响应特征
   
3. **专业传递函数分析** (`professional_idz_analysis.py`)
   - 从线性响应推导积分环节模型
   - 建立分布参数系统理论
   - 空间传播特性量化

### 3.2 关键技术突破
- **线性响应物理解释**: 将阶跃响应的线性特征解释为积分环节特性
- **空间传播建模**: 建立了传播延迟与距离的精确线性关系
- **分布参数方法**: 每个断面都有独立的传递函数参数

---

## 4. 工程应用价值

### 4.1 控制系统设计
建立的IDZ模型可直接用于：
- **预测控制**: 基于传递函数预测系统响应
- **参数整定**: 为PID控制器提供动态参数
- **鲁棒控制**: 考虑空间延迟的分布式控制策略

### 4.2 水力学意义
- **洪水预警**: 传播延迟模型可用于洪水到达时间预测
- **调度优化**: 时间常数信息支持水库调度决策
- **安全评估**: 响应特性分析支持防洪安全评估

### 4.3 模型验证
拟合精度分析表明：
- **可信度高**: R² > 0.6，符合工程要求
- **物理合理**: 参数具有明确的水力学意义
- **空间一致**: 沿程变化规律符合物理直觉

---

## 5. 模型参数总结

### 5.1 核心传递函数
**标准形式**: G(s) = 1.0 / [s·(25s + 1)] · exp(-16.67x·s)

**参数解释**:
- 增益K = 1.0：单位输入产生单位稳态响应
- 时间常数τ ≈ 25分钟：系统惯性特征时间
- 延迟td = 16.67x分钟：x为距离(km)，对应1.0m/s波速

### 5.2 空间变化规律
```python
# 传播延迟模型
td(x) = 16.67 * x  # 分钟，x为距离(km)

# 时间常数模型  
τ(x) = 25.6 - 0.25 * x  # 轻微减小

# 拟合质量模型
R²(x) = 0.638 + 0.068 * x  # 下游精度更高
```

---

## 6. 结论与建议

### 6.1 主要结论
1. **系统类型确认**: 该水力系统为典型的积分环节+一阶滞后+纯延迟系统
2. **参数可信**: 所有辨识参数都具有明确的物理意义和合理的数值
3. **空间特性**: 传播延迟严格线性，响应质量沿程改善
4. **工程适用**: 模型精度满足工程控制要求

### 6.2 应用建议
- **短期预测**: 可用于30分钟内的系统响应预测
- **控制设计**: 建议采用分布式控制策略，考虑空间延迟
- **参数调整**: 上游断面建议增加更复杂的非线性补偿
- **模型改进**: 可考虑引入高阶项处理近场复杂响应

### 6.3 技术价值
本项目成功展示了：
- 复杂水力系统的系统辨识方法
- 从简单线性响应中提取物理意义的技术
- 分布参数系统建模的工程实践
- 多层次渐进式辨识策略的有效性

---

**报告生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**技术支持**: 水力学仿真与控制系统实验室
"""
    
    return report_content

def create_technical_summary():
    """创建技术参数总结表"""
    
    # 创建参数总结表
    params_data = [
        ['断面0', 0.0, 1.0000, 25.596, 0.000, 0.6381, 'G(s) = 1.0/(s·(25.6s+1))'],
        ['断面1', 0.5, 1.0000, 25.361, 8.333, 0.6786, 'G(s) = 1.0/(s·(25.4s+1))·e^(-8.3s)'],
        ['断面2', 1.0, 1.0000, 25.183, 16.667, 0.7158, 'G(s) = 1.0/(s·(25.2s+1))·e^(-16.7s)'],
        ['断面3', 1.5, 1.0000, 25.112, 25.000, 0.7470, 'G(s) = 1.0/(s·(25.1s+1))·e^(-25.0s)'],
        ['断面4', 2.0, 1.0000, 25.093, 33.333, 0.7745, 'G(s) = 1.0/(s·(25.1s+1))·e^(-33.3s)']
    ]
    
    df_params = pd.DataFrame(params_data, columns=[
        '断面', '距离(km)', '增益K', '时间常数τ(分钟)', '传播延迟td(分钟)', '拟合精度R²', '传递函数'
    ])
    
    return df_params

def plot_comprehensive_summary():
    """绘制综合分析总结图"""
    
    # 准备数据
    distances = np.array([0.0, 0.5, 1.0, 1.5, 2.0])
    gains = np.array([1.0000, 1.0000, 1.0000, 1.0000, 1.0000])
    time_constants = np.array([25.596, 25.361, 25.183, 25.112, 25.093])
    delays = np.array([0.000, 8.333, 16.667, 25.000, 33.333])
    r_squared = np.array([0.6381, 0.6786, 0.7158, 0.7470, 0.7745])
    
    # 创建四子图综合分析
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('IDZ模型辨识综合分析总结', fontsize=18, fontweight='bold')
    
    # 1. 传播延迟分析
    ax1.plot(distances, delays, 'bo-', linewidth=3, markersize=8, label='实际延迟')
    delay_fit = np.polyfit(distances, delays, 1)
    delay_line = np.polyval(delay_fit, distances)
    ax1.plot(distances, delay_line, 'r--', linewidth=2, label=f'线性拟合: td = {delay_fit[0]:.2f}x + {delay_fit[1]:.2f}')
    ax1.set_xlabel('距离 (km)', fontsize=12)
    ax1.set_ylabel('传播延迟 (分钟)', fontsize=12)
    ax1.set_title('传播延迟空间分布\n(波速 ≈ 1.0 m/s)', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend(fontsize=10)
    
    # 2. 时间常数分析
    ax2.plot(distances, time_constants, 'go-', linewidth=3, markersize=8, label='时间常数τ')
    tau_fit = np.polyfit(distances, time_constants, 1)
    tau_line = np.polyval(tau_fit, distances)
    ax2.plot(distances, tau_line, 'r--', linewidth=2, label=f'趋势: τ = {tau_fit[0]:.3f}x + {tau_fit[1]:.2f}')
    ax2.set_xlabel('距离 (km)', fontsize=12)
    ax2.set_ylabel('时间常数 τ (分钟)', fontsize=12)
    ax2.set_title('时间常数空间分布\n(系统惯性特征)', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.legend(fontsize=10)
    
    # 3. 拟合精度分析
    ax3.bar(range(len(distances)), r_squared, color=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FECA57'], 
            alpha=0.8, width=0.6)
    ax3.set_xlabel('断面编号', fontsize=12)
    ax3.set_ylabel('拟合精度 R²', fontsize=12)
    ax3.set_title('各断面模型拟合精度\n(下游精度更高)', fontsize=14, fontweight='bold')
    ax3.set_xticks(range(len(distances)))
    ax3.set_xticklabels([f'断面{i}' for i in range(len(distances))])
    ax3.set_ylim(0, 1)
    ax3.grid(True, alpha=0.3, axis='y')
    
    # 在柱状图上添加数值标签
    for i, v in enumerate(r_squared):
        ax3.text(i, v + 0.02, f'{v:.3f}', ha='center', va='bottom', fontweight='bold')
    
    # 4. 传递函数特征对比
    sections = [f'断面{i}' for i in range(len(distances))]
    
    # 绘制增益（应该都是1.0）
    ax4_twin = ax4.twinx()
    
    bars1 = ax4.bar(np.arange(len(sections)) - 0.2, time_constants, 0.4, 
                   label='时间常数 τ (分钟)', color='#4ECDC4', alpha=0.8)
    bars2 = ax4_twin.bar(np.arange(len(sections)) + 0.2, delays, 0.4, 
                        label='传播延迟 td (分钟)', color='#FF6B6B', alpha=0.8)
    
    ax4.set_xlabel('断面', fontsize=12)
    ax4.set_ylabel('时间常数 τ (分钟)', color='#4ECDC4', fontsize=12)
    ax4_twin.set_ylabel('传播延迟 td (分钟)', color='#FF6B6B', fontsize=12)
    ax4.set_title('传递函数参数对比\n(τ ≈ 25分钟, td = 16.67×距离)', fontsize=14, fontweight='bold')
    
    ax4.set_xticks(range(len(sections)))
    ax4.set_xticklabels(sections)
    ax4.grid(True, alpha=0.3)
    
    # 添加图例
    lines1, labels1 = ax4.get_legend_handles_labels()
    lines2, labels2 = ax4_twin.get_legend_handles_labels()
    ax4.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=10)
    
    plt.tight_layout()
    save_path = "IDZ模型辨识综合分析总结.png"
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"综合分析总结图已保存: {save_path}")
    plt.show()

def main():
    """主函数"""
    print("=== IDZ模型辨识综合分析报告生成 ===\n")
    
    # 1. 生成技术参数总结表
    params_df = create_technical_summary()
    print("技术参数总结表:")
    print(params_df.to_string(index=False))
    print()
    
    # 2. 保存参数总结
    params_df.to_csv("IDZ模型参数总结表.csv", index=False, encoding='utf-8-sig')
    print("参数总结表已保存: IDZ模型参数总结表.csv")
    
    # 3. 生成综合分析报告
    report_content = create_comprehensive_report()
    with open("IDZ模型辨识综合分析报告.md", "w", encoding="utf-8") as f:
        f.write(report_content)
    print("综合分析报告已保存: IDZ模型辨识综合分析报告.md")
    
    # 4. 绘制综合分析图
    plot_comprehensive_summary()
    
    # 5. 输出关键结论
    print(f"\n{'='*70}")
    print("=== IDZ模型辨识关键结论 ===")
    print(f"{'='*70}")
    print("1. 传递函数形式: G(s) = K / [s·(τs + 1)] · exp(-td·s)")
    print("2. 典型参数: K ≈ 1.0, τ ≈ 25分钟, td = 16.67×距离(km)分钟")
    print("3. 物理意义: 积分环节+一阶滞后+空间传播延迟")
    print("4. 拟合精度: R² = 0.64~0.77，下游断面精度更高")
    print("5. 工程应用: 适用于预测控制和分布式控制系统设计")
    print(f"{'='*70}")
    
    print(f"\n=== IDZ模型辨识项目完成 ===")
    print("已生成完整的技术文档、参数表和分析图表")
    print("所有文件均保存在当前目录，可用于后续工程应用")

if __name__ == "__main__":
    main()