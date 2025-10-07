#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最终测试ImplicitSolverAgent的非恒定流求解
"""

from waternet.models.saint_venant import SaintVenantModel

def test_unsteady_flow_final():
    # 创建测试模型
    sections = [
        {
            'name': 'upstream', 
            'mileage': 0, 
            'elevation': 100.0, 
            'roughness': 0.035,
            'area_func': lambda h: max(0.1, (h - 100.0) * 10.0) if h > 100.0 else 0.1,
            'top_width_func': lambda h: 10.0
        },
        {
            'name': 'middle', 
            'mileage': 0.5, 
            'elevation': 99.5, 
            'roughness': 0.035,
            'area_func': lambda h: max(0.1, (h - 99.5) * 10.0) if h > 99.5 else 0.1,
            'top_width_func': lambda h: 10.0
        },
        {
            'name': 'downstream', 
            'mileage': 1.0, 
            'elevation': 99.0, 
            'roughness': 0.035,
            'area_func': lambda h: max(0.1, (h - 99.0) * 10.0) if h > 99.0 else 0.1,
            'top_width_func': lambda h: 10.0
        }
    ]
    
    print('📋 创建圣维南模型...')
    sv_model = SaintVenantModel('test_channel', 'upstream', 'downstream', sections)
    
    print('🚀 测试非恒定流step方法...')
    try:
        # 调用step方法进行非恒定流计算
        result = sv_model.step(Q_in=100.0, downstream_level=96.0, dt=60.0)
        
        print('✅ 非恒定流step成功!')
        print(f'   Q_out: {result.get("Q_out", "N/A")}')
        print(f'   H_out: {result.get("H_out", "N/A")}')
        print(f'   V: {result.get("V", "N/A")}')
        
        return True
        
    except Exception as e:
        print(f'❌ 非恒定流step失败: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_unsteady_flow_final()
    if success:
        print("\n🎯 结论: 基础库的ImplicitSolverAgent非恒定流求解成功!")
    else:
        print("\n❌ 非恒定流求解仍有问题需要进一步调试")