"""
测试套件：降阶模型测试

验证各种降阶模型的实现正确性。

Author: WaterNet Development Team
Date: 2024-10-03
"""

import pytest
import numpy as np
import pandas as pd
from waternet.models.lumped_models import (
    BaseLumpedModel, WaterBalanceModel, StorageRoutingModel,
    MuskingumModel, IntegralDelayZeroModel
)


class TestBaseLumpedModel:
    """降阶模型基类测试"""
    
    @pytest.fixture
    def simple_functions(self):
        """创建简单的物理关系函数"""
        def V_to_H(V):
            return 100.0 + V / 10000.0
        
        def H_to_Q(H):
            return max(0.0, (H - 100.0) * 10.0)
        
        return V_to_H, H_to_Q
    
    def test_water_balance_model(self, simple_functions):
        """测试水量平衡模型"""
        V_to_H, H_to_Q = simple_functions
        
        model = WaterBalanceModel(
            dt=60.0, initial_V=10000.0, 
            V_to_H_func=V_to_H, H_to_Q_func=H_to_Q)
        
        # 测试单步仿真
        result = model.step(5.0)
        
        assert 'Q_out' in result
        assert 'H_out' in result
        assert 'V' in result
        assert result['Q_out'] == 5.0  # 水量平衡：出流=入流
    
    def test_storage_routing_model(self, simple_functions):
        """测试蓄量演算模型"""
        V_to_H, H_to_Q = simple_functions
        
        model = StorageRoutingModel(
            dt=60.0, initial_V=10000.0,
            V_to_H_func=V_to_H, H_to_Q_func=H_to_Q)
        
        # 测试阶跃响应
        Q_in_series = [0.0] * 10 + [10.0] * 20 + [0.0] * 10
        results = model.run_simulation(Q_in_series)
        
        # 验证结果格式
        assert isinstance(results, pd.DataFrame)
        assert len(results) == len(Q_in_series) + 1  # 包含初始状态
        assert 'Q_out' in results.columns
        assert 'V' in results.columns
        
        # 验证物理合理性
        assert all(results['V'] >= 0)  # 蓄水量非负
        assert all(results['Q_out'] >= 0)  # 出流非负
    
    def test_muskingum_model(self, simple_functions):
        """测试马斯京干模型"""
        V_to_H, H_to_Q = simple_functions
        
        model = MuskingumModel(
            dt=60.0, K=3600.0, x=0.2, initial_V=10000.0,
            V_to_H_func=V_to_H, H_to_Q_func=H_to_Q)
        
        # 验证系数计算
        assert hasattr(model, 'C0')
        assert hasattr(model, 'C1') 
        assert hasattr(model, 'C2')
        
        # 验证系数和为1（数值稳定性）
        coeff_sum = model.C0 + model.C1 + model.C2
        assert abs(coeff_sum - 1.0) < 1e-6
        
        # 测试脉冲响应
        Q_in_series = [0.0] * 5 + [20.0] + [0.0] * 20
        results = model.run_simulation(Q_in_series)
        
        # 马斯京干模型应该有滞后效应
        peak_idx = np.argmax(results['Q_out'])
        assert peak_idx > 5  # 峰值出现在输入峰值之后
    
    def test_idz_model(self, simple_functions):
        """测试IDZ模型"""
        V_to_H, H_to_Q = simple_functions
        
        model = IntegralDelayZeroModel(
            dt=60.0, tau=600.0, T_delay=300.0, alpha=1800.0,
            initial_V=10000.0, V_to_H_func=V_to_H, H_to_Q_func=H_to_Q)
        
        # 验证延迟缓冲区
        assert len(model.delay_buffer) == model.delay_steps
        
        # 测试阶跃响应
        Q_in_series = [0.0] * 10 + [15.0] * 30
        results = model.run_simulation(Q_in_series)
        
        # IDZ模型应该有延迟和动态特性
        Q_out = results['Q_out'].values
        
        # 初期应该基本为0（延迟效应）
        assert np.mean(Q_out[:5]) < 1.0
        
        # 最终应该趋向稳态值（但不一定等于输入）
        final_value = np.mean(Q_out[-5:])
        assert final_value > 0


class TestModelParameters:
    """模型参数测试"""
    
    def test_invalid_parameters(self):
        """测试无效参数处理"""
        def dummy_func(x):
            return x
        
        # 马斯京干模型参数边界测试
        with pytest.raises(ValueError):
            MuskingumModel(60.0, -100.0, 0.2, 1000.0, dummy_func, dummy_func)  # K < 0
        
        with pytest.raises(ValueError):  
            MuskingumModel(60.0, 3600.0, 0.6, 1000.0, dummy_func, dummy_func)  # x > 0.5
        
        # IDZ模型参数边界测试
        with pytest.raises(ValueError):
            IntegralDelayZeroModel(60.0, -100.0, 300.0, 1800.0, 1000.0, dummy_func, dummy_func)  # tau < 0
        
        with pytest.raises(ValueError):
            IntegralDelayZeroModel(60.0, 600.0, -100.0, 1800.0, 1000.0, dummy_func, dummy_func)  # T_delay < 0
    
    def test_model_reset(self):
        """测试模型重置功能"""
        def V_to_H(V):
            return 100.0 + V / 10000.0
        
        def H_to_Q(H):
            return max(0.0, (H - 100.0) * 10.0)
        
        model = MuskingumModel(
            dt=60.0, K=3600.0, x=0.2, initial_V=10000.0,
            V_to_H_func=V_to_H, H_to_Q_func=H_to_Q)
        
        # 运行一些步骤
        for i in range(5):
            model.step(float(i + 1))
        
        # 记录状态
        state_before_reset = model.get_current_state()
        
        # 重置模型
        model.reset()
        
        # 验证重置效果
        state_after_reset = model.get_current_state()
        assert state_after_reset['time'] == 0.0
        assert state_after_reset['V'] == 10000.0
        assert len(model.history['time']) == 1  # 只有初始状态
    
    def test_physical_bounds(self):
        """测试物理边界约束"""
        def V_to_H(V):
            return 100.0 + V / 10000.0
        
        def H_to_Q(H):
            return max(0.0, (H - 100.0) * 10.0)
        
        model = StorageRoutingModel(
            dt=60.0, initial_V=10000.0,
            V_to_H_func=V_to_H, H_to_Q_func=H_to_Q)
        
        # 设置物理边界
        model.set_physical_bounds(min_volume=5000.0, max_volume=50000.0)
        
        # 测试大入流时是否受到最大蓄量限制
        for i in range(10):
            result = model.step(1000.0)  # 大入流
        
        assert model.current_V <= 50000.0  # 不超过最大值