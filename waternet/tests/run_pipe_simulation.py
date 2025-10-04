"""
PipeSimulationHarness 管道仿真测试平台

实现阀门关闭等水锤场景的完整仿真，为有压管道系统提供动态测试平台。
基于PressurizedPipeModel进行完整的水锤过程仿真。

功能特点:
- 阀门突然关闭场景仿真
- 完整的非恒定流求解
- 结果记录和分析
- CSV数据输出和可视化

Author: WaterNet Development Team
Date: 2024-10-04
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import warnings
import sys
import os
from typing import Dict, List, Optional, Tuple
from scipy.optimize import root

# 添加路径以导入模块
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from physical_objects.pressurized_pipe_model import PressurizedPipeModel
from waternet.models.pressurized_pipe_rom import create_pressurized_pipe_rom


class PipeSimulationHarness:
    """
    管道仿真测试平台
    
    提供完整的有压管道水锤仿真功能，支持多种边界条件和扰动场景。
    
    Attributes:
        pipe_model (PressurizedPipeModel): 有压管道精细化模型
        dt (float): 时间步长 (s)
        total_time (float): 总仿真时间 (s)
        scenario_config (Dict): 仿真场景配置
        results (pd.DataFrame): 仿真结果数据
    """
    
    def __init__(self, pipe_model: PressurizedPipeModel, dt: float = 0.01, 
                 total_time: float = 10.0):
        """
        初始化管道仿真测试平台
        
        Args:
            pipe_model (PressurizedPipeModel): 有压管道模型
            dt (float): 时间步长 (s)
            total_time (float): 总仿真时间 (s)
        """
        self.pipe_model = pipe_model
        self.dt = dt
        self.total_time = total_time
        self.n_steps = int(total_time / dt)
        
        self.scenario_config = {}
        self.results = None
        self.boundary_conditions = None
        
        print(f"管道仿真测试平台初始化完成:")
        print(f"  管道: {pipe_model.name}")
        print(f"  时间步长: {dt} s")
        print(f"  总时间: {total_time} s")
        print(f"  仿真步数: {self.n_steps}")
    
    def setup_valve_closure_scenario(self, Q_initial: float = 2.0, 
                                   H_upstream_initial: float = 105.0,
                                   H_downstream_initial: float = 100.0,
                                   t_close: float = 2.0,
                                   closure_type: str = 'sudden') -> Dict:
        """
        设置阀门关闭场景
        
        Args:
            Q_initial (float): 初始流量 (m³/s)
            H_upstream_initial (float): 初始上游水头 (m)
            H_downstream_initial (float): 初始下游水头 (m)
            t_close (float): 阀门开始关闭时间 (s)
            closure_type (str): 关闭类型 ('sudden', 'linear', 'exponential')
            
        Returns:
            Dict: 场景配置信息
        """
        self.scenario_config = {
            'type': 'valve_closure',
            'Q_initial': Q_initial,
            'H_upstream_initial': H_upstream_initial,
            'H_downstream_initial': H_downstream_initial,
            't_close': t_close,
            'closure_type': closure_type
        }
        
        # 生成边界条件时间序列
        self.boundary_conditions = self._generate_valve_closure_boundary_conditions()
        
        print(f"阀门关闭场景设置完成:")
        print(f"  初始流量: {Q_initial} m³/s")
        print(f"  关闭时间: {t_close} s")
        print(f"  关闭类型: {closure_type}")
        
        return self.scenario_config
    
    def _generate_valve_closure_boundary_conditions(self) -> Dict[str, np.ndarray]:
        """生成阀门关闭的边界条件时间序列"""
        time_array = np.linspace(0, self.total_time, self.n_steps + 1)
        
        Q_initial = self.scenario_config['Q_initial']
        H_upstream_initial = self.scenario_config['H_upstream_initial']
        H_downstream_initial = self.scenario_config['H_downstream_initial']
        t_close = self.scenario_config['t_close']
        closure_type = self.scenario_config['closure_type']
        
        # 上游边界条件（流量控制）
        Q_upstream = np.full_like(time_array, Q_initial)
        
        # 下游边界条件（阀门控制）
        Q_downstream = np.zeros_like(time_array)
        H_downstream = np.full_like(time_array, H_downstream_initial)
        
        if closure_type == 'sudden':
            # 突然关闭：在t_close时刻流量立即变为0
            Q_downstream[time_array < t_close] = Q_initial
            Q_downstream[time_array >= t_close] = 0.0
            
        elif closure_type == 'linear':
            # 线性关闭：在t_close到t_close+1秒内线性下降
            close_duration = 1.0
            for i, t in enumerate(time_array):
                if t < t_close:
                    Q_downstream[i] = Q_initial
                elif t < t_close + close_duration:
                    ratio = 1.0 - (t - t_close) / close_duration
                    Q_downstream[i] = Q_initial * ratio
                else:
                    Q_downstream[i] = 0.0
                    
        elif closure_type == 'exponential':
            # 指数关闭
            tau = 0.5  # 时间常数
            for i, t in enumerate(time_array):
                if t < t_close:
                    Q_downstream[i] = Q_initial
                else:
                    Q_downstream[i] = Q_initial * np.exp(-(t - t_close) / tau)
        
        return {
            'time': time_array,
            'Q_upstream': Q_upstream,
            'Q_downstream': Q_downstream,
            'H_upstream': np.full_like(time_array, H_upstream_initial),
            'H_downstream': H_downstream
        }
    
    def run_simulation(self) -> pd.DataFrame:
        """
        执行完整的仿真循环
        
        Returns:
            pd.DataFrame: 仿真结果数据框
        """
        if self.boundary_conditions is None:
            raise ValueError("请先设置仿真场景")
        
        print("开始水锤仿真...")
        
        # 初始化稳态
        Q_initial = self.scenario_config['Q_initial']
        H_downstream_initial = self.scenario_config['H_downstream_initial']
        
        print("计算初始稳态...")
        steady_state = self.pipe_model.compute_steady_state(Q_initial, H_downstream_initial)
        
        # 初始化仿真结果存储
        results_data = []
        
        # 当前状态
        current_variables = self._initialize_variables_from_steady_state(steady_state)
        prev_states = current_variables.copy()
        
        # 仿真主循环
        print(f"开始时步循环 (共{self.n_steps}步)...")
        
        for step in range(self.n_steps):
            t = step * self.dt
            
            # 更新边界条件
            current_variables = self._update_boundary_conditions(current_variables, step)
            
            # 求解当前时步
            try:
                solution = self._solve_current_timestep(current_variables, prev_states)
                
                if solution.success:
                    current_variables = self._extract_solution(solution.x, current_variables)
                else:
                    warnings.warn(f"时步{step}求解失败，使用前一步结果")
                
            except Exception as e:
                warnings.warn(f"时步{step}出现异常: {e}")
            
            # 记录结果
            step_result = self._record_timestep_result(t, step, current_variables)
            results_data.append(step_result)
            
            # 更新前一步状态
            prev_states = current_variables.copy()
            
            # 进度显示
            if (step + 1) % max(1, self.n_steps // 10) == 0:
                progress = (step + 1) / self.n_steps * 100
                print(f"仿真进度: {progress:.1f}%")
        
        # 转换为DataFrame
        self.results = pd.DataFrame(results_data)
        
        print("仿真完成!")
        print(f"结果包含 {len(self.results)} 个时间步的数据")
        
        return self.results
    
    def _initialize_variables_from_steady_state(self, steady_state: Dict[str, float]) -> Dict[str, float]:
        """从稳态结果初始化变量"""
        variables = {}
        
        # 边界节点
        variables[f'H_{self.pipe_model.upstream_node}'] = steady_state['upstream_H']
        variables[f'H_{self.pipe_model.downstream_node}'] = self.scenario_config['H_downstream_initial']
        variables[f'Q_{self.pipe_model.upstream_node}'] = self.scenario_config['Q_initial']
        
        # 内部节点和分段
        for var_name in self.pipe_model.get_variable_names():
            if var_name in steady_state:
                variables[var_name] = steady_state[var_name]
        
        return variables
    
    def _update_boundary_conditions(self, variables: Dict[str, float], step: int) -> Dict[str, float]:
        """更新边界条件"""
        # 上游流量边界
        variables[f'Q_{self.pipe_model.upstream_node}'] = self.boundary_conditions['Q_upstream'][step]
        
        # 上游水头边界（如果有）
        variables[f'H_{self.pipe_model.upstream_node}'] = self.boundary_conditions['H_upstream'][step]
        
        # 下游边界（水头或流量）
        variables[f'H_{self.pipe_model.downstream_node}'] = self.boundary_conditions['H_downstream'][step]
        
        return variables
    
    def _solve_current_timestep(self, current_variables: Dict[str, float], 
                              prev_states: Dict[str, float]):
        """求解当前时步的方程组"""
        # 提取未知变量
        var_names = self.pipe_model.get_variable_names()
        x0 = np.array([current_variables.get(name, 0.0) for name in var_names])
        
        # 定义目标函数
        def equations(x):
            # 构建完整变量字典
            variables = current_variables.copy()
            for i, name in enumerate(var_names):
                variables[name] = x[i]
            
            # 获取方程残差
            residuals = self.pipe_model.get_equations(variables, self.dt, prev_states)
            
            # 按变量顺序返回残差
            return np.array([residuals.get(f'continuity_seg_{i}', 0.0) 
                           for i in range(len(self.pipe_model.segments))] +
                          [residuals.get(f'momentum_seg_{i}', 0.0) 
                           for i in range(len(self.pipe_model.segments))] +
                          [residuals.get(f'balance_{node}', 0.0) 
                           for node in self.pipe_model.internal_nodes])
        
        # 使用scipy求解器
        try:
            solution = root(equations, x0, method='hybr', tol=1e-6)
            return solution
        except Exception as e:
            warnings.warn(f"数值求解失败: {e}")
            # 返回假的成功结果以继续仿真
            class FakeSolution:
                def __init__(self):
                    self.success = False
                    self.x = x0
            return FakeSolution()
    
    def _extract_solution(self, x: np.ndarray, variables: Dict[str, float]) -> Dict[str, float]:
        """从求解结果提取变量值"""
        var_names = self.pipe_model.get_variable_names()
        
        for i, name in enumerate(var_names):
            if i < len(x):
                variables[name] = x[i]
        
        return variables
    
    def _record_timestep_result(self, t: float, step: int, 
                               variables: Dict[str, float]) -> Dict[str, float]:
        """记录时步结果"""
        result = {
            'time': t,
            'step': step,
            'Q_in': variables.get(f'Q_{self.pipe_model.upstream_node}', 0.0),
            'H_upstream': variables.get(f'H_{self.pipe_model.upstream_node}', 0.0),
            'H_downstream': variables.get(f'H_{self.pipe_model.downstream_node}', 0.0)
        }
        
        # 添加内部节点水头
        for i, node_name in enumerate(self.pipe_model.internal_nodes):
            result[f'H_internal_{i}'] = variables.get(node_name, 0.0)
        
        # 添加分段流量
        for i in range(len(self.pipe_model.segments)):
            flow_var_name = f'Q_{self.pipe_model.name}_seg_{i}'
            result[f'Q_seg_{i}'] = variables.get(flow_var_name, 0.0)
        
        return result
    
    def save_results(self, filename: str = 'pipe_hammer_response.csv'):
        """保存仿真结果到CSV文件"""
        if self.results is None:
            raise ValueError("没有仿真结果可保存")
        
        filepath = os.path.join(os.path.dirname(__file__), filename)
        self.results.to_csv(filepath, index=False)
        print(f"仿真结果已保存到: {filepath}")
        
        return filepath
    
    def plot_results(self, save_plot: bool = True, show_plot: bool = False):
        """绘制仿真结果图表"""
        if self.results is None:
            raise ValueError("没有仿真结果可绘制")
        
        # 创建图表
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle(f'有压管道水锤仿真结果 - {self.pipe_model.name}', fontsize=16)
        
        time = self.results['time']
        
        # 子图1: 压力分布
        ax1 = axes[0, 0]
        ax1.plot(time, self.results['H_upstream'], 'b-', label='上游水头', linewidth=2)
        if 'H_internal_0' in self.results.columns:
            ax1.plot(time, self.results['H_internal_0'], 'g-', label='中点水头', linewidth=2)
        ax1.plot(time, self.results['H_downstream'], 'r-', label='下游水头', linewidth=2)
        ax1.set_xlabel('时间 (s)')
        ax1.set_ylabel('测压管水头 (m)')
        ax1.set_title('管道沿线压力变化')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 子图2: 流量变化
        ax2 = axes[0, 1]
        ax2.plot(time, self.results['Q_in'], 'b-', label='入流量', linewidth=2)
        if 'Q_seg_0' in self.results.columns:
            ax2.plot(time, self.results['Q_seg_0'], 'g--', label='分段0流量', linewidth=2)
        ax2.set_xlabel('时间 (s)')
        ax2.set_ylabel('流量 (m³/s)')
        ax2.set_title('管道流量变化')
        ax2.legend() 
        ax2.grid(True, alpha=0.3)
        
        # 子图3: 压力梯度
        ax3 = axes[1, 0]
        pressure_gradient = (self.results['H_upstream'] - self.results['H_downstream']) / self.pipe_model.total_length
        ax3.plot(time, pressure_gradient, 'purple', linewidth=2)
        ax3.set_xlabel('时间 (s)')
        ax3.set_ylabel('压力梯度 (m/m)')
        ax3.set_title('沿程压力梯度')
        ax3.grid(True, alpha=0.3)
        
        # 子图4: 水锤振荡分析
        ax4 = axes[1, 1]
        if 'H_internal_0' in self.results.columns:
            # 计算相对于初始值的振荡
            H_initial = self.results['H_internal_0'].iloc[0]
            H_oscillation = self.results['H_internal_0'] - H_initial
            ax4.plot(time, H_oscillation, 'orange', linewidth=2)
            ax4.set_xlabel('时间 (s)')
            ax4.set_ylabel('水头振荡 (m)')
            ax4.set_title('中点水头振荡')
            ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_plot:
            plot_filename = 'pipe_hammer_simulation.png'
            plot_path = os.path.join(os.path.dirname(__file__), plot_filename)
            plt.savefig(plot_path, dpi=300, bbox_inches='tight')
            print(f"仿真图表已保存到: {plot_path}")
        
        if show_plot:
            plt.show()
        else:
            plt.close()
        
        return fig
    
    def analyze_water_hammer_characteristics(self) -> Dict[str, float]:
        """分析水锤特性"""
        if self.results is None:
            raise ValueError("没有仿真结果可分析")
        
        analysis = {}
        
        # 基本统计
        H_upstream = self.results['H_upstream']
        H_initial = H_upstream.iloc[0]
        
        analysis['initial_head'] = H_initial
        analysis['max_head'] = H_upstream.max()
        analysis['min_head'] = H_upstream.min()
        analysis['head_rise'] = analysis['max_head'] - H_initial
        analysis['pressure_drop'] = H_initial - analysis['min_head']
        
        # 振荡分析
        if len(H_upstream) > 100:  # 确保有足够数据
            # 简单的峰值检测
            time = self.results['time'].values
            dt = time[1] - time[0]
            
            # 寻找第一个显著峰值的时间
            t_close = self.scenario_config.get('t_close', 0.0)
            after_closure = self.results[self.results['time'] > t_close]
            
            if len(after_closure) > 10:
                H_after = after_closure['H_upstream']
                max_idx = H_after.idxmax()
                analysis['first_peak_time'] = self.results.loc[max_idx, 'time'] - t_close
                
                # 估算振荡周期
                if analysis['first_peak_time'] > 0:
                    estimated_period = 4 * self.pipe_model.total_length / self.pipe_model.wave_speed
                    analysis['theoretical_period'] = estimated_period
                    analysis['observed_period'] = analysis['first_peak_time'] * 2  # 简化估算
        
        # Joukowsky公式验证
        Q_initial = self.scenario_config['Q_initial']
        if Q_initial > 0 and self.pipe_model.segments:
            area = self.pipe_model.segments[0]['area']
            velocity_change = Q_initial / area
            joukowsky_pressure = 1000 * 9.81 * self.pipe_model.wave_speed * velocity_change / 1000  # kPa
            analysis['joukowsky_pressure_rise'] = joukowsky_pressure / (1000 * 9.81)  # 转换为水头(m)
        
        print("水锤特性分析结果:")
        for key, value in analysis.items():
            print(f"  {key}: {value:.3f}")
        
        return analysis


def create_demo_pipe_model() -> PressurizedPipeModel:
    """创建演示用的管道模型"""
    nodes = [
        {'mileage': 0.0, 'elevation': 100.0, 'diameter': 1.0, 'friction_coeff': 0.02},
        {'mileage': 500.0, 'elevation': 98.0, 'diameter': 1.0, 'friction_coeff': 0.02},
        {'mileage': 1000.0, 'elevation': 95.0, 'diameter': 0.8, 'friction_coeff': 0.025}
    ]
    
    return PressurizedPipeModel(
        name="DemoPipe",
        upstream_node="Reservoir",
        downstream_node="Valve",
        nodes=nodes,
        wave_speed=1200.0
    )


def run_demo_simulation():
    """运行演示仿真"""
    print("="*60)
    print("有压管道水锤仿真演示")
    print("="*60)
    
    try:
        # 创建管道模型
        print("\n1. 创建管道模型...")
        pipe_model = create_demo_pipe_model()
        print(pipe_model.get_pipe_summary())
        
        # 创建仿真平台
        print("\n2. 创建仿真平台...")
        harness = PipeSimulationHarness(pipe_model, dt=0.02, total_time=8.0)
        
        # 设置阀门关闭场景
        print("\n3. 设置阀门关闭场景...")
        scenario = harness.setup_valve_closure_scenario(
            Q_initial=1.5,
            H_upstream_initial=110.0,
            H_downstream_initial=95.0,
            t_close=2.0,
            closure_type='sudden'
        )
        
        # 运行仿真
        print("\n4. 运行仿真...")
        results = harness.run_simulation()
        
        # 保存结果
        print("\n5. 保存结果...")
        csv_path = harness.save_results()
        
        # 绘制图表
        print("\n6. 绘制图表...")
        harness.plot_results(save_plot=True, show_plot=False)
        
        # 分析水锤特性
        print("\n7. 分析水锤特性...")
        analysis = harness.analyze_water_hammer_characteristics()
        
        print("\n演示仿真完成!")
        print(f"结果文件: {csv_path}")
        
        return harness, results, analysis
        
    except Exception as e:
        print(f"演示仿真失败: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None


if __name__ == "__main__":
    # 运行演示
    harness, results, analysis = run_demo_simulation()
    
    if harness is not None:
        print("\n✅ 管道水锤仿真演示成功完成!")
    else:
        print("\n❌ 管道水锤仿真演示失败!")
        exit(1)