"""
集成测试：完整系统验证

Author: WaterNet Development Team
Date: 2024-10-03
"""

import pytest
import numpy as np
import pandas as pd
from waternet.models.saint_venant import SaintVenantModel
from waternet.models.lumped_models import MuskingumModel
from waternet.parameter_estimation.estimator import ParameterEstimator
from waternet.coordination.twinning_harness import SynchronizedTwinningHarness


class TestIntegration:
    """系统集成测试"""
    
    @pytest.fixture
    def test_channel_setup(self):
        """创建测试用的明渠配置"""
        sections = [
            {
                'mileage': 0.0, 'elevation': 100.0, 'roughness': 0.025,
                'area_func': lambda h: max(0, h - 100) * 10,
                'top_width_func': lambda h: 10 if h > 100 else 0
            },
            {
                'mileage': 1000.0, 'elevation': 99.0, 'roughness': 0.025,
                'area_func': lambda h: max(0, h - 99) * 10,
                'top_width_func': lambda h: 10 if h > 99 else 0
            }
        ]
        
        sv_model = SaintVenantModel("TestChannel", "upstream", "downstream", sections)
        
        def V_to_H(V):
            return 99.0 + V / 10000.0
        
        def H_to_Q(H):
            return max(0.0, (H - 99.0) * 20.0)
        
        rom_model = MuskingumModel(
            dt=60.0, K=3600.0, x=0.2, initial_V=10000.0,
            V_to_H_func=V_to_H, H_to_Q_func=H_to_Q)
        
        return sv_model, rom_model
    
    def test_parameter_estimation_workflow(self, test_channel_setup):
        """测试参数估计工作流程"""
        sv_model, _ = test_channel_setup
        
        estimator = ParameterEstimator(sv_model)
        
        # 测试静态特征曲线辨识
        Q_range = np.linspace(5.0, 25.0, 5)
        H_range = np.linspace(99.2, 100.5, 4)
        
        static_result = estimator.identify_static_curves(Q_range, H_range)
        
        # 验证结果
        assert 'fitted_curves' in static_result
        assert 'raw_data' in static_result
        assert 'V_H' in static_result['fitted_curves']
        assert 'Q_H' in static_result['fitted_curves']
    
    def test_synchronized_twinning(self, test_channel_setup):
        """测试同步孪生仿真"""
        sv_model, rom_model = test_channel_setup
        
        harness = SynchronizedTwinningHarness(
            sv_model, rom_model, 
            correction_interval=10, 
            correction_threshold=0.5)
        
        # 创建测试输入
        time_steps = 20
        Q_in = np.concatenate([
            np.ones(10) * 8.0,
            np.ones(10) * 18.0
        ])
        H_down = np.ones(time_steps) * 99.3
        
        # 运行仿真
        results = harness.run_synchronized_simulation(
            Q_in, H_down, dt=60.0, enable_correction=True)
        
        # 验证结果
        assert isinstance(results, pd.DataFrame)
        assert len(results) == time_steps
        
        required_columns = ['time', 'Q_in', 'Q_out_sv', 'Q_out_rom', 'error_Q']
        for col in required_columns:
            assert col in results.columns
        
        # 验证物理合理性
        assert all(results['Q_out_sv'] >= 0)
        assert all(results['Q_out_rom'] >= 0)
    
    def test_performance_metrics(self, test_channel_setup):
        """测试性能指标计算"""
        sv_model, rom_model = test_channel_setup
        
        harness = SynchronizedTwinningHarness(sv_model, rom_model)
        
        Q_in = np.ones(10) * 10.0
        H_down = np.ones(10) * 99.5
        
        results = harness.run_synchronized_simulation(
            Q_in, H_down, dt=60.0, enable_correction=False)
        
        metrics = harness.performance_metrics
        
        assert 'rmse_Q' in metrics
        assert 'correlation_Q' in metrics
        assert metrics['rmse_Q'] >= 0