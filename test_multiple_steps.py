#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from waternet.models.saint_venant import SaintVenantModel
import time

def test_multiple_steps():
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

    print('=== SAINT VENANT UNSTEADY FLOW TEST ===')
    sv_model = SaintVenantModel('test_channel', 'upstream', 'downstream', sections)

    print('Testing multiple time steps...')
    success_count = 0
    total_tests = 5

    for i in range(total_tests):
        try:
            Q_in = 80.0 + i * 10.0
            H_down = 95.5 + i * 0.1
            
            start_time = time.time()
            result = sv_model.step(Q_in=Q_in, downstream_level=H_down, dt=60.0)
            calc_time = time.time() - start_time
            
            print(f'Step {i+1}: Q_in={Q_in}, H_down={H_down}')
            print(f'  Result: Q_out={result.get("Q_out"):.2f}, H_out={result.get("H_out"):.2f}, V={result.get("V"):.0f}')
            print(f'  Time: {calc_time:.3f}s')
            success_count += 1
            
        except Exception as e:
            print(f'Step {i+1} FAILED: {e}')

    print(f'\n=== SUMMARY ===')
    print(f'Successful steps: {success_count}/{total_tests}')
    print(f'Success rate: {success_count/total_tests*100:.1f}%')

    if success_count == total_tests:
        print('SUCCESS: ALL UNSTEADY FLOW TESTS PASSED!')
    else:
        print('WARNING: Some tests failed')
        
    return success_count == total_tests

if __name__ == "__main__":
    test_multiple_steps()