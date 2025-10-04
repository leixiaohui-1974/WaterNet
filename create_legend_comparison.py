#!/usr/bin/env python3
"""
生成图例符号优化前后对比图
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Rectangle, Circle, Polygon
import numpy as np

# 配置中文字体
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

def create_comparison_chart():
    """创建图例符号优化前后对比图"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
    
    # 原始颜色配置（浅色）
    original_colors = {
        'reservoir': {'fill': '#E3F2FD', 'edge': '#1976D2'},
        'station': {'fill': '#F3E5F5', 'edge': '#7B1FA2'}, 
        'junction': {'fill': '#E8F5E8', 'edge': '#388E3C'},
        'pipe': {'fill': '#FFF3E0', 'edge': '#F57C00'}
    }
    
    # 优化后颜色配置（深色）
    enhanced_colors = {
        'reservoir': {'fill': '#BBDEFB', 'edge': '#0D47A1'},
        'station': {'fill': '#E1BEE7', 'edge': '#4A148C'},
        'junction': {'fill': '#C8E6C9', 'edge': '#1B5E20'},
        'pipe': {'fill': '#FFE0B2', 'edge': '#BF360C'}
    }
    
    # 类型名称
    type_names = {
        'reservoir': '水库',
        'station': '枢纽站',
        'junction': '连接点',
        'pipe': '管道'
    }
    
    # 绘制原始版本（左侧）
    ax1.set_title('优化前 - 图例符号（浅色细线）', fontsize=16, fontweight='bold', pad=20)
    draw_legend_symbols(ax1, original_colors, type_names, linewidth=1.5)
    
    # 绘制优化版本（右侧）
    ax2.set_title('优化后 - 图例符号（深色粗线）', fontsize=16, fontweight='bold', pad=20)
    draw_legend_symbols(ax2, enhanced_colors, type_names, linewidth=3.0)
    
    # 设置坐标轴
    for ax in [ax1, ax2]:
        ax.set_xlim(0, 4)
        ax.set_ylim(0, 5)
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)
        ax.set_xticks([])
        ax.set_yticks([])
    
    plt.tight_layout()
    output_path = 'e:/OneDrive/Documents/GitHub/WaterNet/图例符号优化对比图.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    
    print(f"✅ 图例符号优化对比图已生成: {output_path}")
    return output_path

def draw_legend_symbols(ax, colors, type_names, linewidth=1.5):
    """绘制图例符号"""
    y_positions = [4, 3, 2, 1]
    symbol_types = ['reservoir', 'station', 'junction', 'pipe']
    
    for i, (symbol_type, y_pos) in enumerate(zip(symbol_types, y_positions)):
        color_config = colors[symbol_type]
        type_name = type_names[symbol_type]
        
        x_pos = 1
        
        # 根据类型绘制不同符号
        if symbol_type == 'reservoir':
            # 水库用圆角矩形
            symbol = FancyBboxPatch(
                (x_pos - 0.2, y_pos - 0.2), 0.4, 0.4,
                boxstyle="round,pad=0.05",
                facecolor=color_config['fill'],
                edgecolor=color_config['edge'],
                linewidth=linewidth
            )
            ax.add_patch(symbol)
            
        elif symbol_type == 'junction':
            # 连接点用圆形
            symbol = Circle((x_pos, y_pos), 0.2,
                          facecolor=color_config['fill'],
                          edgecolor=color_config['edge'],
                          linewidth=linewidth)
            ax.add_patch(symbol)
            
        elif symbol_type == 'station':
            # 枢纽站用六边形
            angles = np.linspace(0, 2*np.pi, 7)
            vertices = [(x_pos + 0.2 * np.cos(angle), y_pos + 0.2 * np.sin(angle)) 
                       for angle in angles[:-1]]
            symbol = Polygon(vertices,
                           facecolor=color_config['fill'],
                           edgecolor=color_config['edge'],
                           linewidth=linewidth)
            ax.add_patch(symbol)
            
        else:  # pipe
            # 管道用矩形
            symbol = Rectangle((x_pos - 0.2, y_pos - 0.2), 0.4, 0.4,
                             facecolor=color_config['fill'],
                             edgecolor=color_config['edge'],
                             linewidth=linewidth)
            ax.add_patch(symbol)
        
        # 添加标签
        ax.text(x_pos + 0.6, y_pos, f'{type_name}', 
               fontsize=14, fontweight='bold',
               ha='left', va='center')
        
        # 显示颜色值
        ax.text(x_pos + 0.6, y_pos - 0.3, 
               f'边框: {color_config["edge"]}', 
               fontsize=10, ha='left', va='center')
        ax.text(x_pos + 0.6, y_pos - 0.5, 
               f'填充: {color_config["fill"]}', 
               fontsize=10, ha='left', va='center')

if __name__ == "__main__":
    create_comparison_chart()
    print("\n优化说明:")
    print("1. 边框线条粗细: 1.5 → 3.0 (加粗2倍)")
    print("2. 颜色深度优化:")
    print("   - 所有边框颜色都选择了更深的色调")
    print("   - 填充色也相应加深，保持协调性") 
    print("3. 视觉效果显著提升，符号更加清晰可见")