#!/usr/bin/env python3
"""
调试拓扑图展示问题的专用脚本
"""

from pathlib import Path
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from waternet.utils.config_driven_system import ConfigurationManager, SystemBuilder, PlotManager
from waternet.visualization.enhanced_topology_generator import EnhancedTopologyGenerator
try:
    import matplotlib
    matplotlib.use('Agg')  # 使用非交互式后端
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    print("matplotlib not available, skipping matplotlib tests")
    MATPLOTLIB_AVAILABLE = False

def test_topology_generation():
    """测试拓扑图生成"""
    print("🔍 开始调试拓扑图展示问题...")
    
    # 1. 加载配置
    config_path = "configs/reservoir_gate_channel_system.yaml"
    config_manager = ConfigurationManager(config_path)
    
    # 2. 构建系统
    system_builder = SystemBuilder(config_manager)
    system_builder.build_system()
    
    # 3. 创建图表管理器（需要可视化配置）
    visualization_config = config_manager.get_output_config().get('visualization', {})
    plot_manager = PlotManager(Path("plots"), visualization_config)
    
    # 4. 构建拓扑数据
    topology_data = plot_manager._build_topology_data(system_builder)
    
    print("📊 拓扑数据结构:")
    for key, value in topology_data.items():
        if isinstance(value, list):
            print(f"  {key}: {len(value)} 个项目")
            for item in value[:3]:  # 只显示前3个
                print(f"    - {item}")
            if len(value) > 3:
                print(f"    ... 还有 {len(value)-3} 个")
        else:
            print(f"  {key}: {value}")
    
    # 5. 测试增强版拓扑图生成器
    print("\n🎨 测试增强版拓扑图生成器...")
    generator = EnhancedTopologyGenerator()
    
    # 检查字体偏好设置
    print("📝 字体偏好设置:")
    for key, value in generator.font_preferences.items():
        print(f"  {key}: {value}")
    
    # 检查错开显示配置
    print("\n📐 错开显示配置:")
    for key, value in generator.offset_config.items():
        print(f"  {key}: {value}")
    
    # 6. 智能选择展示方式
    selected_mode = generator.intelligent_layout_selection(topology_data)
    print(f"\n🧠 智能选择的展示方式: {selected_mode}")
    mode_info = generator.display_modes[selected_mode]
    print(f"   描述: {mode_info['description']}")
    print(f"   布局: {mode_info['layout']}")
    print(f"   显示数值: {mode_info['show_values']}")
    
    # 7. 测试字体应用
    print("\n🔤 测试字体应用:")
    test_texts = [
        "上游水库",      # 纯汉字
        "1.5",          # 纯数字  
        "水库-1",       # 混合文本
        "Reservoir"     # 英文
    ]
    
    for text in test_texts:
        font_style = generator.apply_font_preferences(text)
        print(f"  {text:10} -> 字体大小: {font_style['fontsize']:4.1f}, 颜色: {font_style['color']:6}, 加粗: {font_style['fontweight']}")
    
    # 8. 生成拓扑图并捕获详细错误
    try:
        print("\n🖼️ 生成拓扑图...")
        result_path = generator.generate_enhanced_topology(
            topology_data,
            "plots/debug_topology.png",
            mode='auto',
            title="调试用拓扑图"
        )
        
        if result_path and os.path.exists(result_path):
            file_size = os.path.getsize(result_path)
            print(f"✅ 拓扑图生成成功: {result_path}")
            print(f"   文件大小: {file_size} 字节")
            
            # 检查图像是否为空白或占位符
            if file_size < 1000:
                print("⚠️ 文件大小异常小，可能是空白图像")
            
        else:
            print("❌ 拓扑图生成失败")
            
    except Exception as e:
        print(f"❌ 拓扑图生成异常: {e}")
        import traceback
        traceback.print_exc()
    
    # 9. 测试matplotlib中文字体支持
    print("\n🀄 测试matplotlib中文字体支持...")
    try:
        plt.figure(figsize=(8, 6))
        plt.text(0.5, 0.7, "上游水库", fontsize=24, ha='center', color='black', fontweight='normal')
        plt.text(0.5, 0.5, "1.5", fontsize=16, ha='center', color='red', fontweight='bold') 
        plt.text(0.5, 0.3, "水库-1", fontsize=24, ha='center', color='black', fontweight='normal')
        plt.title("中文字体测试", fontsize=16)
        plt.xlim(0, 1)
        plt.ylim(0, 1)
        plt.axis('off')
        plt.savefig("plots/font_test.png", dpi=300, bbox_inches='tight')
        plt.close()
        print("✅ 中文字体测试图保存完成")
    except Exception as e:
        print(f"❌ 中文字体测试失败: {e}")

if __name__ == "__main__":
    test_topology_generation()