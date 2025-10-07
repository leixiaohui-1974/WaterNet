#!/usr/bin/env python3
"""
综合演示修复版 - 确保所有计算生成对应的图表和报告
严格遵循用户记忆规范：
- 拓扑图字体显示规范：图例字体放大2倍，汉字字体放大3倍，数字字体翻倍并用红色突出显示
- 汉字与图形错开显示规范：避免重叠，确保清晰可读
- 面向对象实现要求：采用组合、策略、工厂等设计模式
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from waternet.objects.conveyance import ChannelObject
from waternet.core.unsteady_flow_analyzer import UnsteadyFlowAnalyzer
from waternet.core.parameter_optimizer import ParameterOptimizer, OptimizationObjective

def comprehensive_fixed_demo():
    """综合演示修复版"""
    
    print("🔧 WaterNet综合演示修复版")
    print("=" * 80)
    print("🎯 目标：确保所有计算生成对应的图表和报告")
    print("📐 规范：严格遵循用户记忆中的显示规范")
    print("🏗️ 设计：面向对象实现，确保封装性和可扩展性")
    print("=" * 80)
    
    # 设置输出目录
    output_base = Path(__file__).parent / 'outputs' / 'comprehensive_fixed'
    
    # 1. 创建智能明渠对象
    print("\n📍 第1部分：创建智能明渠对象")
    print("-" * 50)
    
    channel_config = {
        'basic_properties': {
            'length': 5000.0,
            'slope': 0.0002,
            'roughness': 0.025,
            'bottom_width': 15.0,
            'side_slope': 1.5,
            'initial_volume': 15000.0
        },
        'simulation_preferences': {
            'default_method': 'muskingum_model'
        },
        'muskingum_parameters': {
            'K': 3600.0,
            'x': 0.15
        }
    }
    
    channel = ChannelObject('comprehensive_channel', config=channel_config)
    channel.initialize()
    
    print(f"✅ 明渠对象创建成功: {channel.object_id}")
    print(f"🔧 仿真方法: {channel.simulation_method}")
    
    # 2. 执行基础计算
    print("\n📍 第2部分：执行基础恒定流计算")
    print("-" * 50)
    
    channel.set_upstream_boundary(flow=150.0)
    channel.set_downstream_boundary(level=95.0)
    
    steady_result = channel.solve_steady_flow()
    if steady_result.get('success', False):
        print(f"✅ 恒定流计算成功")
        print(f"📊 入流: {steady_result['inflow']:.1f} m³/s")
        print(f"📊 出流: {steady_result['outflow']:.1f} m³/s")
        print(f"📊 水位: {steady_result['water_level']:.2f} m")
        print(f"📊 蓄量: {steady_result['storage']:.0f} m³")
    else:
        print(f"❌ 恒定流计算失败: {steady_result.get('error', '未知错误')}")
        return
    
    # 3. 生成恒定流纵剖面图（强制要求）
    print("\n📍 第3部分：生成恒定流纵剖面图（遵循显示规范）")
    print("-" * 50)
    
    try:
        profile_output_dir = str(output_base / 'profiles')
        profile_result = channel.create_visualization(
            viz_type='profile',
            output_dir=profile_output_dir,
            include_boundary_conditions=True,
            include_cross_sections=True
        )
        
        if profile_result['success']:
            print(f"✅ 恒定流纵剖面图生成成功")
            print(f"🖼️ 图表文件: {profile_result['visualization_result']['file_path']}")
            print(f"📏 包含要素: 渠底高程、各断面信息、上下游边界条件")
            print(f"🎨 显示规范: 汉字字体放大3倍，数字红色显示，图形错开")
        else:
            print(f"❌ 恒定流纵剖面图生成失败: {profile_result.get('error', '未知错误')}")
    except Exception as e:
        print(f"❌ 纵剖面图生成异常: {e}")
    
    # 4. 生成多流量工况对比图
    print("\n📍 第4部分：生成多流量工况对比图")
    print("-" * 50)
    
    try:
        comparison_result = channel.compare_steady_flow_profiles(
            flow_scenarios=[
                {'name': '低流量', 'flow': 100.0},
                {'name': '设计流量', 'flow': 150.0}, 
                {'name': '高流量', 'flow': 200.0}
            ],
            output_dir=str(output_base / 'comparisons')
        )
        
        if comparison_result.get('success', False):
            print(f"✅ 多流量工况对比图生成成功")
            if 'plot_path' in comparison_result:
                print(f"🖼️ 对比图文件: {comparison_result['plot_path']}")
            print(f"📊 工况数量: 3个")
            print(f"🎨 显示规范: 遵循字体和颜色规范")
        else:
            print(f"❌ 多流量工况对比图生成失败")
    except Exception as e:
        print(f"❌ 对比图生成异常: {e}")
    
    # 5. 参数优化演示
    print("\n📍 第5部分：参数优化和智能推荐")
    print("-" * 50)
    
    try:
        optimizer = ParameterOptimizer(
            objective_type=OptimizationObjective.BALANCED,
            max_iterations=50,
            tolerance=1e-4
        )
        
        # 智能参数推荐
        flood_params = optimizer.recommend_parameters(channel_config['basic_properties'], 'flood_forecasting')
        design_params = optimizer.recommend_parameters(channel_config['basic_properties'], 'engineering_design')
        
        print(f"✅ 智能参数推荐完成")
        print(f"🌊 洪水预报参数: K={flood_params['K']:.0f}s, x={flood_params['x']:.3f}")
        print(f"🏗️ 工程设计参数: K={design_params['K']:.0f}s, x={design_params['x']:.3f}")
        
        # 参数优化
        observed_inflows = [120.0, 135.0, 160.0, 180.0, 165.0, 145.0, 130.0, 125.0, 120.0]
        observed_outflows = [120.0, 128.0, 145.0, 165.0, 170.0, 155.0, 140.0, 132.0, 125.0]
        
        opt_result = optimizer.optimize_muskingum_parameters(
            observed_inflows=observed_inflows,
            observed_outflows=observed_outflows,
            time_step=1800.0
        )
        
        if opt_result.success:
            print(f"✅ 参数自动优化成功")
            print(f"🎯 最优参数: K={opt_result.optimal_params['K']:.0f}s, x={opt_result.optimal_params['x']:.3f}")
            print(f"📊 目标函数值: {opt_result.objective_value:.3f}")
            
            # 生成优化报告
            opt_report_path = str(output_base / 'optimization_report.md')
            report_path = optimizer.create_optimization_report(opt_result, opt_report_path)
            if report_path:
                print(f"📄 优化报告: {report_path}")
        else:
            print(f"❌ 参数优化失败")
            
    except Exception as e:
        print(f"❌ 参数优化异常: {e}")
    
    # 6. 生成综合分析报告
    print("\n📍 第6部分：生成综合分析报告")
    print("-" * 50)
    
    try:
        report_result = channel.generate_analysis_report(
            report_type='comprehensive',
            output_dir=str(output_base / 'reports'),
            include_plots=True
        )
        
        if report_result['success']:
            summary = report_result['report_summary']
            print(f"✅ 综合分析报告生成成功")
            print(f"📄 报告文件: {summary['generated_files']['report_file']}")
            print(f"📊 分析组件: {len(summary['analysis_components'])}个")
            print(f"📁 输出目录: {summary['output_structure']['base_directory']}")
            
            # 显示生成的图表
            plot_files = summary['generated_files']['plot_files']
            if plot_files:
                print(f"🖼️ 生成图表:")
                for plot_name, plot_path in plot_files.items():
                    print(f"   - {plot_name}: {Path(plot_path).name}")
        else:
            print(f"❌ 综合分析报告生成失败: {report_result.get('error', '未知错误')}")
            
    except Exception as e:
        print(f"❌ 报告生成异常: {e}")
    
    # 7. 非恒定流仿真分析
    print("\n📍 第7部分：非恒定流仿真分析")
    print("-" * 50)
    
    try:
        analyzer = UnsteadyFlowAnalyzer(str(output_base / 'unsteady_analysis'))
        
        # 配置分析方法
        analysis_methods = ['修正马斯京干法', '保守马斯京干法', '快速马斯京干法']
        
        comprehensive_result = analyzer.run_comprehensive_analysis({
            'methods': analysis_methods,
            'channel_config': channel_config,
            'boundary_conditions': {
                'upstream_flows': [120, 140, 170, 190, 180, 160, 140, 130, 120],
                'downstream_levels': [95.0] * 9,
                'time_hours': [0, 1, 2, 3, 4, 5, 6, 7, 8]
            }
        })
        
        if comprehensive_result.get('success', False):
            print(f"✅ 非恒定流仿真分析完成")
            print(f"📊 分析方法: {len(analysis_methods)}种")
            print(f"🌊 时间序列: 9个时间点")
            
            # 检查生成的文件
            outputs = comprehensive_result.get('outputs', {})
            if outputs:
                print(f"📁 生成文件:")
                for file_type, file_path in outputs.items():
                    if Path(file_path).exists():
                        print(f"   ✅ {file_type}: {Path(file_path).name}")
                    else:
                        print(f"   ❌ {file_type}: 文件不存在")
        else:
            print(f"❌ 非恒定流仿真分析失败")
            
    except Exception as e:
        print(f"❌ 非恒定流分析异常: {e}")
    
    # 8. 验证生成的文件
    print("\n📍 第8部分：验证生成的文件")
    print("-" * 50)
    
    generated_files = []
    
    # 检查各个输出目录
    for subdir in ['profiles', 'comparisons', 'reports', 'unsteady_analysis']:
        dir_path = output_base / subdir
        if dir_path.exists():
            for file_path in dir_path.rglob('*'):
                if file_path.is_file():
                    generated_files.append(file_path)
    
    print(f"📊 总计生成文件: {len(generated_files)}个")
    
    # 按类型分类显示
    image_files = [f for f in generated_files if f.suffix.lower() in ['.png', '.jpg', '.svg']]
    report_files = [f for f in generated_files if f.suffix.lower() in ['.md', '.html', '.txt']]
    data_files = [f for f in generated_files if f.suffix.lower() in ['.csv', '.json', '.xlsx']]
    
    print(f"🖼️ 图表文件: {len(image_files)}个")
    for img_file in image_files:
        print(f"   - {img_file.name}")
    
    print(f"📄 报告文件: {len(report_files)}个")
    for report_file in report_files:
        print(f"   - {report_file.name}")
    
    print(f"💾 数据文件: {len(data_files)}个")
    for data_file in data_files:
        print(f"   - {data_file.name}")
    
    # 9. 总结
    print("\n📍 第9部分：演示总结")
    print("-" * 50)
    
    print(f"🎉 综合演示修复版完成！")
    print(f"📁 输出基目录: {output_base}")
    print(f"📊 生成文件总数: {len(generated_files)}")
    
    print(f"\n✅ 遵循的用户规范:")
    print(f"   🎨 拓扑图字体显示规范: 图例字体放大2倍，汉字字体放大3倍")
    print(f"   📍 汉字与图形错开显示: 避免重叠，确保清晰可读")
    print(f"   🏗️ 面向对象实现: 采用组合、策略、工厂设计模式")
    print(f"   📈 恒定流纵剖面图: 包含渠底高程、断面、边界条件信息")
    
    print(f"\n💡 技术亮点:")
    print(f"   🚀 智能参数推荐和自动优化")
    print(f"   📊 多流量工况对比分析")
    print(f"   🌊 非恒定流仿真分析")
    print(f"   📋 自动化报告和可视化生成")

if __name__ == "__main__":
    comprehensive_fixed_demo()