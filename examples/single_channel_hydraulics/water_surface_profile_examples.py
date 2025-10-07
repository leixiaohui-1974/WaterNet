#!/usr/bin/env python3
"""
单一渠道水面线绘制示例

演示如何使用WaterSurfaceProfilePlotter进行水面线分析：
1. 基本水面线绘制
2. 多工况对比分析
3. 不同参数影响评估
4. 水力学性质分析

Author: WaterNet Development Team
Date: 2025-01-05
"""

from water_surface_profile_plotter import WaterSurfaceProfilePlotter
import time


def example_basic_profile_plotting():
    """示例1：基本水面线绘制"""
    print("\n" + "="*60)
    print("示例1：基本水面线绘制")
    print("="*60)
    
    # 创建绘制器
    plotter = WaterSurfaceProfilePlotter()
    
    # 计算单一工况
    flow_conditions = [50.0]  # 单一流量工况
    results = plotter.compute_multiple_flow_conditions(flow_conditions)
    
    if results:
        result = results[0]
        profile = result['profile_data']
        hydraulic = result['hydraulic_analysis']
        
        print(f"计算结果:")
        print(f"  流量: {result['flow']:.1f} m³/s")
        print(f"  最大水深: {hydraulic['max_depth']:.2f} m")
        print(f"  最大流速: {hydraulic['max_velocity']:.2f} m/s")
        print(f"  流态: {hydraulic['flow_regime']}")
        print(f"  水头损失: {hydraulic['total_head_loss']:.2f} m")


def example_multi_flow_comparison():
    """示例2：多工况水面线对比"""
    print("\n" + "="*60)
    print("示例2：多工况水面线对比")
    print("="*60)
    
    # 创建绘制器
    plotter = WaterSurfaceProfilePlotter()
    
    # 计算多个流量工况
    flow_conditions = [20.0, 40.0, 60.0, 80.0, 100.0]
    results = plotter.compute_multiple_flow_conditions(flow_conditions)
    
    if results:
        # 生成对比图
        plot_path = plotter.create_water_surface_profile_plot()
        
        # 生成分析报告（包含图片引用）
        report_path = plotter.generate_analysis_report(plot_path)
        
        print(f"多工况对比分析完成:")
        print(f"  工况数量: {len(results)} 个")
        print(f"  流量范围: {min(flow_conditions):.0f} - {max(flow_conditions):.0f} m³/s")
        if plot_path:
            print(f"  水面线图: {plot_path}")
        if report_path:
            print(f"  分析报告: {report_path}")


def example_parameter_sensitivity():
    """示例3：参数敏感性分析"""
    print("\n" + "="*60)
    print("示例3：参数敏感性分析（流量影响）")
    print("="*60)
    
    # 创建绘制器
    plotter = WaterSurfaceProfilePlotter()
    
    # 测试不同流量的影响
    test_flows = [10.0, 30.0, 50.0, 70.0, 90.0, 110.0]
    results = plotter.compute_multiple_flow_conditions(test_flows)
    
    if results:
        print("流量对水力参数的影响:")
        print("| 流量(m³/s) | 最大水深(m) | 最大流速(m/s) | 最大Fr数 | 水头损失(m) |")
        print("| --- | --- | --- | --- | --- |")
        
        for result in results:
            flow = result['flow']
            hydraulic = result['hydraulic_analysis']
            
            max_depth = hydraulic.get('max_depth', 0)
            max_velocity = hydraulic.get('max_velocity', 0)
            max_froude = hydraulic.get('max_froude', 0)
            head_loss = hydraulic.get('total_head_loss', 0)
            
            print(f"| {flow:.0f} | {max_depth:.2f} | {max_velocity:.2f} | {max_froude:.3f} | {head_loss:.2f} |")


def example_hydraulic_analysis():
    """示例4：详细水力学分析"""
    print("\n" + "="*60)
    print("示例4：详细水力学分析")
    print("="*60)
    
    # 创建绘制器
    plotter = WaterSurfaceProfilePlotter()
    
    # 计算中等流量工况
    results = plotter.compute_multiple_flow_conditions([50.0])
    
    if results:
        result = results[0]
        profile = result['profile_data']
        hydraulic = result['hydraulic_analysis']
        
        print("详细水力学分析结果:")
        print(f"  渠道长度: {hydraulic['channel_length']:.0f} m")
        print(f"  平均坡度: {hydraulic['average_slope']:.6f}")
        print(f"  水深范围: {hydraulic['min_depth']:.2f} - {hydraulic['max_depth']:.2f} m")
        print(f"  流速范围: {hydraulic['min_velocity']:.2f} - {hydraulic['max_velocity']:.2f} m/s")
        print(f"  弗劳德数范围: 0 - {hydraulic['max_froude']:.3f}")
        print(f"  流态: {hydraulic['flow_regime']}")
        
        # 计算沿程变化
        distances = profile['distances']
        depths = profile['depths']
        velocities = profile['velocities']
        froude_numbers = hydraulic['froude_numbers']
        
        print("\n沿程变化（每100m）:")
        print("| 里程(m) | 水深(m) | 流速(m/s) | Fr数 |")
        print("| --- | --- | --- | --- |")
        
        step = max(1, len(distances) // 10)  # 取10个点
        for i in range(0, len(distances), step):
            if i < len(distances):
                distance = distances[i]
                depth = depths[i]
                velocity = velocities[i] 
                froude = froude_numbers[i] if i < len(froude_numbers) else 0
                
                print(f"| {distance:.0f} | {depth:.2f} | {velocity:.2f} | {froude:.3f} |")


def main():
    """主函数 - 运行所有示例"""
    print("单一渠道水面线绘制示例集")
    print("参考 config_driven_reservoir_gate_system.py 的水面线绘制逻辑")
    print("专门为单一渠道设计的分析工具")
    
    try:
        # 运行所有示例
        example_basic_profile_plotting()
        example_multi_flow_comparison()
        example_parameter_sensitivity()
        example_hydraulic_analysis()
        
        print("\n" + "="*60)
        print("✅ 所有示例运行完成！")
        print("✅ 参考原始文件的水面线绘制逻辑已成功移植到单一渠道工具")
        print("="*60)
        
    except Exception as e:
        print(f"\n✗ 示例运行失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()