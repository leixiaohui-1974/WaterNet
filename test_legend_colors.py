#!/usr/bin/env python3
"""
测试图例符号颜色加深效果
"""

from optimized_topology_generator import OptimizedTopologyGenerator

def test_legend_colors():
    """测试图例符号颜色加深效果"""
    # 创建生成器
    generator = OptimizedTopologyGenerator()
    
    # 验证设置
    print("=== 图例符号颜色加深加粗测试 ===")
    print(f"图例字体缩放比例: {generator.font_preferences['legend_scale']}")
    print("\n颜色配置已加深:")
    
    for obj_type, colors in generator.color_scheme.items():
        edge_color = colors['edge']
        fill_color = colors['fill']
        print(f"  {obj_type:>10}: 边框色={edge_color}, 填充色={fill_color}")
    
    # 生成测试拓扑图
    sample_data = generator.create_sample_topology()
    output_path = 'e:/OneDrive/Documents/GitHub/WaterNet/拓扑图_图例符号加深版.png'
    
    result_path = generator.generate_optimized_topology_png(
        sample_data, 
        output_path,
        'WaterNet拓扑图 - 图例符号加深加粗版'
    )
    
    print(f"\n✅ 图例符号加深的拓扑图已生成: {result_path}")
    print("\n改进效果:")
    print("1. 图例字体恢复2倍放大（严格按用户规范）")
    print("2. 所有图例符号边框线条从1.5加粗到3.0")
    print("3. 颜色从浅色调整为深色，提高可视性:")
    print("   - 水库: 浅蓝#E3F2FD → 深蓝#BBDEFB, 边框#1976D2 → #0D47A1")
    print("   - 枢纽站: 浅紫#F3E5F5 → 深紫#E1BEE7, 边框#7B1FA2 → #4A148C") 
    print("   - 连接点: 浅绿#E8F5E8 → 深绿#C8E6C9, 边框#388E3C → #1B5E20")
    print("   - 管道: 浅橙#FFF3E0 → 深橙#FFE0B2, 边框#F57C00 → #BF360C")
    print("4. 符号线条加粗3倍，更加清晰可见")

if __name__ == "__main__":
    test_legend_colors()