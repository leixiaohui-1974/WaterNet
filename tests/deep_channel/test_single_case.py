#!/usr/bin/env python
"""
单独运行测试案例验证
"""

from test_case_1 import TestCase1_UnsteadyFlowValidation

if __name__ == "__main__":
    print("="*50)
    print("运行Case1单独测试")
    print("="*50)
    
    test = TestCase1_UnsteadyFlowValidation()
    result = test.execute_test_case()
    
    print("Case1 执行结果:")
    print(f"测试成功: {result['execution_summary']['test_success']}")
    print(f"执行时间: {result['execution_summary']['total_execution_time']:.3f}秒")
    
    if 'sv_validation' in result:
        sv_val = result['sv_validation']
        print(f"SV模型验证成功: {sv_val['validation_success']}")
        if 'performance_metrics' in sv_val:
            metrics = sv_val['performance_metrics']
            print(f"质量守恒误差: {metrics.get('mass_conservation_error', 'N/A')}")
            print(f"数值稳定性: {metrics.get('numerical_stability', 'N/A')}")
    
    print("="*50)