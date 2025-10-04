"""
测试套件：HydroModel接口测试

验证HydroModel抽象基类的接口实现正确性。

Author: WaterNet Development Team
Date: 2024-10-03
"""

import pytest
import numpy as np
from waternet.interfaces.hydro_model import HydroModel, DummyModel


class TestHydroModel:
    """HydroModel接口测试类"""
    
    def test_hydro_model_initialization(self):
        """测试HydroModel初始化"""
        # 测试正常初始化
        model = DummyModel("test_model", "node1", "node2")
        assert model.name == "test_model"
        assert model.node_names == ["node1", "node2"]
        
        # 测试无效初始化
        with pytest.raises(ValueError):
            DummyModel("", "node1", "node2")  # 空名称
            
        with pytest.raises(ValueError):
            DummyModel("test", "", "node2")  # 空节点名
    
    def test_dummy_model_interface(self):
        """测试DummyModel接口实现"""
        model = DummyModel("test", "upstream", "downstream", k=2.0, b=1.0)
        
        # 测试变量名获取
        var_names = model.get_variable_names()
        assert var_names == ["Q_test"]
        
        # 测试方程计算
        variables = {"H_upstream": 10.0, "Q_test": 21.0}
        equations = model.get_equations(variables, 60.0, {})
        
        expected_residual = 21.0 - (2.0 * 10.0 + 1.0)  # Q - (k*H + b)
        assert abs(equations["linear_relation_test"] - expected_residual) < 1e-10
    
    def test_interface_validation(self):
        """测试接口验证功能"""
        model = DummyModel("test", "upstream", "downstream")
        
        variables = {"H_upstream": 5.0, "Q_test": 5.0}
        prev_states = {}
        
        # 接口验证应该通过
        assert model.validate_interface(variables, 60.0, prev_states)


class TestModelValidation:
    """模型验证测试类"""
    
    def test_variables_format_validation(self):
        """测试变量格式验证"""
        from waternet.interfaces.hydro_model import validate_variables_format
        
        # 有效格式
        valid_vars = {"H_node1": 100.0, "Q_pipe1": 1.5}
        assert validate_variables_format(valid_vars)
        
        # 无效格式
        invalid_vars = {"H_node1": "invalid", "Q_pipe1": 1.5}
        assert not validate_variables_format(invalid_vars)
        
        assert not validate_variables_format("not_dict")
        assert validate_variables_format({})  # 空字典是有效的
    
    def test_states_format_validation(self):
        """测试状态格式验证"""
        from waternet.interfaces.hydro_model import validate_states_format
        
        # 有效格式
        valid_states = {"V_reservoir": 5000.0, "H_prev": 99.5}
        assert validate_states_format(valid_states)
        
        # 无效格式
        invalid_states = {123: 456}  # 非字符串键
        assert not validate_states_format(invalid_states)