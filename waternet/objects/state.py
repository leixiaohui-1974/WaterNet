"""
状态管理体系

负责水系统对象状态的存储、更新和历史记录管理。

Features:
- 瞬时状态和累积状态管理
- 状态历史记录
- 状态插值和查询
- 状态验证和一致性检查
- 状态快照和恢复

Author: WaterNet Development Team
Date: 2024-10-05
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging


@dataclass
class StateResult:
    """状态更新结果"""
    success: bool
    message: str = ""
    updated_variables: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class StateManager:
    """
    状态管理器
    
    负责水系统对象状态的完整生命周期管理，包括：
    - 瞬时状态（水位、流量、压力）
    - 累积状态（蓄水量、总流量）
    - 边界状态（边界条件、控制信号）
    - 系统状态（运行模式、故障信息）
    
    Features:
    - 多层次状态分类管理
    - 状态历史记录和查询
    - 状态插值和外推
    - 状态验证和一致性检查
    - 状态快照和恢复功能
    """
    
    def __init__(self, object_id: str, max_history_length: int = 10000):
        """
        初始化状态管理器
        
        Args:
            object_id: 对象唯一标识符
            max_history_length: 最大历史记录长度
        """
        self.object_id = object_id
        self.max_history_length = max_history_length
        self.logger = logging.getLogger(__name__)
        
        # 当前状态
        self.current_state = {
            'instantaneous': {},  # 瞬时状态
            'cumulative': {},     # 累积状态
            'boundary': {},       # 边界状态
            'system': {}          # 系统状态
        }
        
        # 状态历史
        self.state_history = {
            'times': [],
            'states': []
        }
        
        # 状态验证规则
        self.validation_rules = {}
        
        # 状态变化监听器
        self.state_listeners = []
        
        # 初始化系统状态
        self._initialize_system_state()
    
    def get_current_state(self, category: Optional[str] = None) -> Dict[str, Any]:
        """
        获取当前状态
        
        Args:
            category: 状态类别，可选值: 'instantaneous', 'cumulative', 'boundary', 'system'
                     如果为None，返回所有状态
        
        Returns:
            当前状态字典
        """
        if category is None:
            return self.current_state.copy()
        elif category in self.current_state:
            return self.current_state[category].copy()
        else:
            raise ValueError(f"无效的状态类别: {category}")
    
    def update_state(self, updates: Dict[str, Any], 
                    timestamp: Optional[datetime] = None,
                    validate: bool = True) -> StateResult:
        """
        更新对象状态
        
        Args:
            updates: 状态更新字典
            timestamp: 时间戳，如果为None则使用当前时间
            validate: 是否进行状态验证
        
        Returns:
            状态更新结果
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        result = StateResult(success=True)
        updated_vars = []
        
        try:
            # 分类处理状态更新
            for category in ['instantaneous', 'cumulative', 'boundary', 'system']:
                if category in updates:
                    category_updates = updates[category]
                    for var_name, value in category_updates.items():
                        # 状态验证
                        if validate:
                            validation_result = self._validate_state_value(
                                category, var_name, value
                            )
                            if not validation_result.success:
                                result.warnings.extend(validation_result.warnings)
                                continue
                        
                        # 更新状态
                        old_value = self.current_state[category].get(var_name)
                        self.current_state[category][var_name] = value
                        updated_vars.append(f"{category}.{var_name}")
                        
                        # 触发状态变化监听器
                        self._notify_state_change(category, var_name, old_value, value)
            
            # 处理直接状态更新（向后兼容）
            for var_name, value in updates.items():
                if var_name not in ['instantaneous', 'cumulative', 'boundary', 'system']:
                    # 根据变量名推断类别
                    category = self._infer_state_category(var_name)
                    
                    if validate:
                        validation_result = self._validate_state_value(category, var_name, value)
                        if not validation_result.success:
                            result.warnings.extend(validation_result.warnings)
                            continue
                    
                    old_value = self.current_state[category].get(var_name)
                    self.current_state[category][var_name] = value
                    updated_vars.append(f"{category}.{var_name}")
                    
                    self._notify_state_change(category, var_name, old_value, value)
            
            # 记录历史状态
            self._record_state_history(timestamp)
            
            result.updated_variables = updated_vars
            
        except Exception as e:
            result.success = False
            result.message = f"状态更新失败: {e}"
            self.logger.error(f"状态更新失败 {self.object_id}: {e}")
        
        return result
    
    def get_state_history(self, variable: str, 
                         start_time: Optional[datetime] = None,
                         end_time: Optional[datetime] = None) -> pd.DataFrame:
        """
        获取状态变量的历史记录
        
        Args:
            variable: 状态变量名（格式: category.variable_name）
            start_time: 开始时间
            end_time: 结束时间
        
        Returns:
            包含时间和数值的DataFrame
        """
        if not self.state_history['times']:
            return pd.DataFrame(columns=['timestamp', 'value'])
        
        # 解析变量名
        if '.' in variable:
            category, var_name = variable.split('.', 1)
        else:
            # 在所有类别中搜索变量
            category, var_name = self._find_variable_category(variable)
        
        # 提取历史数据
        times = []
        values = []
        
        for i, (timestamp, state) in enumerate(zip(self.state_history['times'], 
                                                  self.state_history['states'])):
            if start_time and timestamp < start_time:
                continue
            if end_time and timestamp > end_time:
                break
            
            if category in state and var_name in state[category]:
                times.append(timestamp)
                values.append(state[category][var_name])
        
        return pd.DataFrame({
            'timestamp': times,
            'value': values
        })
    
    def interpolate_state(self, timestamp: datetime, 
                         variables: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        插值获取指定时间的状态
        
        Args:
            timestamp: 目标时间
            variables: 需要插值的变量列表，如果为None则插值所有变量
        
        Returns:
            插值后的状态字典
        """
        if not self.state_history['times']:
            return {}
        
        times = np.array([t.timestamp() for t in self.state_history['times']])
        target_time = timestamp.timestamp()
        
        # 如果目标时间在历史范围内
        if times[0] <= target_time <= times[-1]:
            interpolated_state = {}
            
            # 对每个状态类别进行插值
            for category in ['instantaneous', 'cumulative', 'boundary', 'system']:
                interpolated_state[category] = {}
                
                # 获取该类别的所有变量
                all_variables = set()
                for state in self.state_history['states']:
                    if category in state:
                        all_variables.update(state[category].keys())
                
                # 对每个变量进行插值
                for var_name in all_variables:
                    if variables and f"{category}.{var_name}" not in variables:
                        continue
                    
                    # 提取变量的时间序列
                    var_values = []
                    var_times = []
                    
                    for i, state in enumerate(self.state_history['states']):
                        if category in state and var_name in state[category]:
                            var_values.append(state[category][var_name])
                            var_times.append(times[i])
                    
                    if len(var_values) >= 2:
                        # 线性插值
                        interpolated_value = np.interp(target_time, var_times, var_values)
                        interpolated_state[category][var_name] = interpolated_value
            
            return interpolated_state
        else:
            # 目标时间在历史范围外，返回最近的状态
            if target_time < times[0]:
                return self.state_history['states'][0]
            else:
                return self.state_history['states'][-1]
    
    def create_snapshot(self, name: str, description: str = "") -> str:
        """
        创建状态快照
        
        Args:
            name: 快照名称
            description: 快照描述
        
        Returns:
            快照ID
        """
        snapshot_id = f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        if not hasattr(self, 'snapshots'):
            self.snapshots = {}
        
        self.snapshots[snapshot_id] = {
            'name': name,
            'description': description,
            'timestamp': datetime.now(),
            'state': self.current_state.copy(),
            'history_length': len(self.state_history['times'])
        }
        
        return snapshot_id
    
    def restore_snapshot(self, snapshot_id: str) -> bool:
        """
        恢复状态快照
        
        Args:
            snapshot_id: 快照ID
        
        Returns:
            是否成功恢复
        """
        if not hasattr(self, 'snapshots') or snapshot_id not in self.snapshots:
            return False
        
        snapshot = self.snapshots[snapshot_id]
        self.current_state = snapshot['state'].copy()
        
        # 可选：截断历史记录到快照时的长度
        history_length = snapshot['history_length']
        if len(self.state_history['times']) > history_length:
            self.state_history['times'] = self.state_history['times'][:history_length]
            self.state_history['states'] = self.state_history['states'][:history_length]
        
        return True
    
    def add_validation_rule(self, category: str, variable: str, 
                           validator: callable):
        """
        添加状态验证规则
        
        Args:
            category: 状态类别
            variable: 变量名
            validator: 验证函数，接收value参数，返回(is_valid, message)
        """
        if category not in self.validation_rules:
            self.validation_rules[category] = {}
        
        self.validation_rules[category][variable] = validator
    
    def add_state_listener(self, listener: callable):
        """
        添加状态变化监听器
        
        Args:
            listener: 监听函数，接收(category, variable, old_value, new_value)参数
        """
        self.state_listeners.append(listener)
    
    def _initialize_system_state(self):
        """初始化系统状态"""
        self.current_state['system'].update({
            'initialized_at': datetime.now(),
            'operation_mode': 'normal',
            'error_count': 0,
            'last_update': datetime.now()
        })
    
    def _infer_state_category(self, variable_name: str) -> str:
        """根据变量名推断状态类别"""
        # 基于变量名前缀或模式推断类别
        if variable_name.startswith(('H_', 'Q_', 'P_', 'V_flow')):
            return 'instantaneous'
        elif variable_name.startswith(('V_', 'total_', 'cumulative_')):
            return 'cumulative'
        elif variable_name.startswith(('BC_', 'boundary_')):
            return 'boundary'
        else:
            return 'system'
    
    def _find_variable_category(self, variable_name: str) -> Tuple[str, str]:
        """在所有类别中查找变量"""
        for category in ['instantaneous', 'cumulative', 'boundary', 'system']:
            if variable_name in self.current_state[category]:
                return category, variable_name
        
        # 如果没找到，使用推断
        category = self._infer_state_category(variable_name)
        return category, variable_name
    
    def _validate_state_value(self, category: str, variable: str, 
                             value: Any) -> StateResult:
        """验证状态值"""
        result = StateResult(success=True)
        
        # 通用验证
        if not isinstance(value, (int, float, str, bool, type(None))):
            result.success = False
            result.warnings.append(f"状态值类型无效: {variable} = {type(value)}")
            return result
        
        # 数值范围验证
        if isinstance(value, (int, float)):
            if not np.isfinite(value):
                result.success = False
                result.warnings.append(f"状态值非有限数: {variable} = {value}")
                return result
        
        # 自定义验证规则
        if (category in self.validation_rules and 
            variable in self.validation_rules[category]):
            
            validator = self.validation_rules[category][variable]
            try:
                is_valid, message = validator(value)
                if not is_valid:
                    result.success = False
                    result.warnings.append(f"验证失败 {variable}: {message}")
            except Exception as e:
                result.warnings.append(f"验证器执行失败 {variable}: {e}")
        
        return result
    
    def _record_state_history(self, timestamp: datetime):
        """记录状态历史"""
        self.state_history['times'].append(timestamp)
        self.state_history['states'].append(self.current_state.copy())
        
        # 限制历史记录长度
        if len(self.state_history['times']) > self.max_history_length:
            self.state_history['times'].pop(0)
            self.state_history['states'].pop(0)
    
    def _notify_state_change(self, category: str, variable: str, 
                           old_value: Any, new_value: Any):
        """通知状态变化监听器"""
        for listener in self.state_listeners:
            try:
                listener(category, variable, old_value, new_value)
            except Exception as e:
                self.logger.warning(f"状态监听器执行失败: {e}")