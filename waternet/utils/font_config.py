"""
matplotlib中文字体配置模块

解决WaterNet项目中的中文字体显示问题。
为所有图表提供统一的中文字体支持。

Author: WaterNet Development Team
Date: 2024-10-03
"""

import matplotlib
import matplotlib.pyplot as plt
import warnings


def configure_chinese_font():
    """配置matplotlib中文字体支持"""
    try:
        # 尝试设置常见的中文字体
        fonts = [
            'SimHei',          # 黑体 (Windows)
            'Microsoft YaHei', # 微软雅黑 (Windows)
            'PingFang SC',     # 苹方 (macOS)
            'Hiragino Sans GB',# 冬青黑体 (macOS)
            'WenQuanYi Micro Hei', # 文泉驿微米黑 (Linux)
            'DejaVu Sans'      # 备选字体
        ]
        
        # 查找可用字体
        available_fonts = []
        from matplotlib.font_manager import FontManager
        fm = FontManager()
        for font in fonts:
            if any(font.lower() in f.name.lower() for f in fm.ttflist):
                available_fonts.append(font)
        
        if available_fonts:
            # 使用第一个可用字体
            plt.rcParams['font.sans-serif'] = available_fonts
            plt.rcParams['axes.unicode_minus'] = False
            print(f"✅ 中文字体配置成功: {available_fonts[0]}")
        else:
            # 使用默认设置，禁用中文显示
            plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
            warnings.warn("⚠️ 未找到中文字体，将使用英文标签")
            
    except Exception as e:
        warnings.warn(f"字体配置失败: {e}")
        

def get_safe_labels():
    """获取安全的标签（英文替代）"""
    return {
        '时间 (s)': 'Time (s)',
        '流量 (m³/s)': 'Flow Rate (m³/s)', 
        '水位 (m)': 'Water Level (m)',
        '体积 (m³)': 'Volume (m³)',
        '入流': 'Inflow',
        '出流': 'Outflow',
        '水面线': 'Water Surface Profile',
        '数值仿真结果': 'Numerical Simulation Results',
        '马斯京干模型': 'Muskingum Model',
        '圣维南模型': 'Saint-Venant Model',
        '降阶模型': 'Reduced Order Model',
        '精细化模型': 'High-Fidelity Model',
        '性能对比': 'Performance Comparison',
        '稳定性测试': 'Stability Test'
    }


def safe_title(chinese_title):
    """安全设置图表标题"""
    labels = get_safe_labels() 
    return labels.get(chinese_title, chinese_title.encode('ascii', 'ignore').decode())


def safe_label(chinese_label):
    """安全设置坐标轴标签"""
    labels = get_safe_labels()
    return labels.get(chinese_label, chinese_label.encode('ascii', 'ignore').decode())


# 在模块加载时自动配置
configure_chinese_font()