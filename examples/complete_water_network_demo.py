"""
完整水网对象体系演示脚本

展示包含所有水系统对象类型的完整水网系统：
1. 输水对象：河道、管道、倒虹吸
2. 存储对象：水库、湖泊、调蓄池
3. 调控对象：闸、泵、阀、水轮机
4. 枢纽站：泵站、闸站、电站
5. 水网系统集成演示

Author: WaterNet Development Team
Date: 2024-10-05
"""

import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import numpy as np
from pathlib import Path

# 导入完整的对象系统
from waternet.objects import (
    # 输水对象
    ChannelObject, PipeObject, SiphonObject,
    # 存储对象  
    ReservoirObject, LakeObject,
    # 调控对象
    GateObject, PumpObject, ValveObject, TurbineObject,
    # 枢纽站
    HubStationObject, PumpStationObject, GateStationObject, PowerStationObject,
    # 工厂函数
    create_water_object
)


def demo_complete_water_network():
    """演示完整的水网对象体系"""
    print("=" * 80)
    print("完整水网对象体系演示")
    print("=" * 80)
    
    try:
        # 1. 创建存储对象 - 水库
        print("\n1. 创建水库...")
        reservoir = create_water_object('reservoir', 'main_reservoir')
        print(f"   ✓ {reservoir}")
        
        # 2. 创建输水对象 - 主渠道
        print("\n2. 创建主渠道...")
        main_channel = create_water_object('channel', 'main_channel')
        print(f"   ✓ {main_channel}")
        
        # 3. 创建调控对象 - 闸门
        print("\n3. 创建调控闸门...")
        control_gate = create_water_object('gate', 'control_gate_001')
        print(f"   ✓ {control_gate}")
        
        # 4. 创建枢纽站 - 泵站
        print("\n4. 创建提升泵站...")
        pump_station = create_water_object('pump_station', 'lift_pump_station')
        print(f"   ✓ {pump_station}")
        
        # 5. 创建管道系统
        print("\n5. 创建输水管道...")
        transfer_pipe = create_water_object('pipe', 'transfer_pipe')
        print(f"   ✓ {transfer_pipe}")
        
        # 6. 创建电站
        print("\n6. 创建水电站...")
        power_station = create_water_object('power_station', 'hydro_power_station')
        print(f"   ✓ {power_station}")
        
        # 7. 创建调蓄设施
        print("\n7. 创建调蓄池...")
        storage_tank = create_water_object('storage_tank', 'regulation_tank')
        print(f"   ✓ {storage_tank}")
        
        print(f"\n✅ 成功创建了包含7个对象的完整水网系统！")
        
        # 8. 演示系统运行
        print("\n" + "=" * 60)
        print("系统运行演示")
        print("=" * 60)
        
        # 水库放水
        print("\n🌊 水库开始放水...")
        reservoir_result = reservoir.update_state(outflow=150.0, time_step=3600)
        if reservoir_result.success:
            print("   ✓ 水库放水成功")
        
        # 闸门控制
        print("\n🚪 调节闸门开度...")
        gate_result = control_gate.set_control_signal(60.0)  # 60%开度
        if gate_result['success']:
            print(f"   ✓ 闸门开度调整至 {gate_result['new_opening']:.1f}%")
            print(f"   ✓ 通过流量 {gate_result['discharge']:.2f} m³/s")
        
        # 泵站运行
        print("\n⚡ 启动提升泵站...")
        pump_station_config = {
            'station_configuration': {
                'devices': [
                    {'type': 'pump', 'rated_flow': 100.0, 'rated_head': 30.0},
                    {'type': 'pump', 'rated_flow': 80.0, 'rated_head': 30.0}
                ],
                'complexity': 'compound'
            }
        }
        pump_station._object_config = pump_station_config
        pump_station.initialize()
        
        # 泵站优化运行
        pump_optimization = pump_station.optimize_pump_combination(target_flow=120.0)
        print(f"   ✓ 泵站优化完成，目标流量: {pump_optimization['target_flow']} m³/s")
        print(f"   ✓ 运行泵组: {len(pump_optimization['pumps_to_operate'])} 台")
        
        # 电站发电
        print("\n⚡ 水电站发电运行...")
        power_station_config = {
            'station_configuration': {
                'devices': [
                    {'type': 'turbine', 'rated_capacity': 50.0},
                    {'type': 'turbine', 'rated_capacity': 30.0}
                ],
                'complexity': 'compound'
            }
        }
        power_station._object_config = power_station_config
        power_station.initialize()
        
        power_optimization = power_station.optimize_power_generation(target_power=60.0)
        if power_optimization['success']:
            print(f"   ✓ 发电优化完成，目标功率: {power_optimization['target_power']} MW")
            print(f"   ✓ 实际分配功率: {power_optimization['allocated_power']:.1f} MW")
        
        # 管道输水
        print("\n🔧 管道系统输水...")
        pipe_result = transfer_pipe.solve_steady_flow()
        if pipe_result['success']:
            print(f"   ✓ 管道稳态计算完成")
        
        print("\n" + "=" * 60)
        print("系统状态总览")
        print("=" * 60)
        
        # 汇总系统状态
        system_objects = [
            ("水库", reservoir),
            ("主渠道", main_channel),
            ("调控闸门", control_gate),
            ("提升泵站", pump_station),
            ("输水管道", transfer_pipe),
            ("水电站", power_station),
            ("调蓄池", storage_tank)
        ]
        
        for name, obj in system_objects:
            obj_info = obj.get_object_info()
            print(f"📊 {name}:")
            print(f"   - ID: {obj_info['object_id']}")
            print(f"   - 类型: {obj_info['object_type']}")
            print(f"   - 数字孪生: {'✓' if obj_info['has_twin'] else '✗'}")
        
        print("\n🎯 水网对象体系特色功能演示:")
        print("   ✅ 统一对象接口：所有对象使用相同的创建和管理方式")
        print("   ✅ 配置驱动创建：通过工厂函数根据类型字符串创建对象") 
        print("   ✅ 多类型支持：覆盖输水、存储、调控、枢纽站等所有对象类型")
        print("   ✅ 系统级协调：支持多对象协同运行和优化控制")
        print("   ✅ 数字孪生能力：每个对象都支持创建数字孪生")
        
    except Exception as e:
        print(f"❌ 演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


def demo_control_objects():
    """演示调控对象功能"""
    print("\n" + "=" * 80)
    print("调控对象专项演示")
    print("=" * 80)
    
    try:
        # 创建各种调控对象
        print("\n🔧 创建调控设备...")
        
        # 1. 闸门
        gate = GateObject('demo_gate')
        gate.initialize()
        print(f"   ✓ 闸门: {gate.object_id}")
        
        # 2. 水泵
        pump = PumpObject('demo_pump')
        pump.initialize()
        print(f"   ✓ 水泵: {pump.object_id}")
        
        # 3. 阀门
        valve = ValveObject('demo_valve')
        valve.initialize()
        print(f"   ✓ 阀门: {valve.object_id}")
        
        # 4. 水轮机
        turbine = TurbineObject('demo_turbine')
        turbine.initialize()
        print(f"   ✓ 水轮机: {turbine.object_id}")
        
        print("\n⚙️  设备控制演示...")
        
        # 闸门控制
        print("\n🚪 闸门控制：")
        for opening in [0, 30, 60, 100]:
            result = gate.set_control_signal(opening)
            if result['success']:
                response = gate.get_output_response()
                print(f"   开度 {opening:3d}% → 流量 {response['discharge']:6.2f} m³/s")
        
        # 水泵控制
        print("\n⚡ 水泵控制：")
        for speed in [0, 40, 70, 100]:
            result = pump.set_control_signal(speed)
            if result['success']:
                response = pump.get_output_response()
                op = response['operating_point']
                print(f"   转速 {speed:3d}% → 流量 {op['flow']:6.2f} m³/s, 效率 {op['efficiency']:5.1%}")
        
        # 阀门控制
        print("\n🔧 阀门控制：")
        for opening in [0, 25, 50, 75, 100]:
            result = valve.set_control_signal(opening)
            if result['success']:
                response = valve.get_output_response()
                print(f"   开度 {opening:3d}% → 流量比 {response['flow_ratio']:5.1%}")
        
        # 水轮机控制
        print("\n🌊 水轮机控制：")
        for guide_vane in [0, 40, 80, 100]:
            result = turbine.set_control_signal(guide_vane)
            if result['success']:
                response = turbine.get_output_response()
                print(f"   导叶 {guide_vane:3d}% → 功率 {response['power_output']:6.2f} MW, 效率 {response['efficiency']:5.1%}")
        
        print("\n✅ 调控对象演示完成！")
        
    except Exception as e:
        print(f"❌ 调控对象演示失败: {e}")


def demo_station_objects():
    """演示枢纽站对象功能"""
    print("\n" + "=" * 80) 
    print("枢纽站对象专项演示")
    print("=" * 80)
    
    try:
        # 1. 泵站演示
        print("\n🏭 泵站运行演示...")
        pump_station = PumpStationObject('demo_pump_station')
        
        # 配置泵站
        pump_station_config = {
            'station_configuration': {
                'devices': [
                    {'type': 'pump', 'rated_flow': 200.0, 'rated_head': 50.0},
                    {'type': 'pump', 'rated_flow': 150.0, 'rated_head': 50.0},
                    {'type': 'pump', 'rated_flow': 100.0, 'rated_head': 50.0}
                ],
                'complexity': 'compound',
                'control_strategy': {
                    'coordination_mode': 'optimization',
                    'optimization_objective': 'efficiency'
                }
            }
        }
        pump_station._object_config = pump_station_config
        pump_station.initialize()
        
        print(f"   ✓ 创建泵站，包含 {len(pump_station.devices)} 台水泵")
        
        # 泵站优化运行
        optimization_targets = [180, 280, 400, 450]
        for target in optimization_targets:
            result = pump_station.optimize_pump_combination(target_flow=target)
            print(f"   目标流量 {target:3d} m³/s → 启动 {len(result['pumps_to_operate'])} 台泵")
        
        # 2. 闸站演示
        print("\n🚧 闸站运行演示...")
        gate_station = GateStationObject('demo_gate_station')
        
        gate_station_config = {
            'station_configuration': {
                'devices': [
                    {'type': 'gate', 'width': 15.0, 'height': 8.0},
                    {'type': 'gate', 'width': 12.0, 'height': 8.0},
                    {'type': 'gate', 'width': 10.0, 'height': 6.0}
                ],
                'complexity': 'compound'
            }
        }
        gate_station._object_config = gate_station_config
        gate_station.initialize()
        
        print(f"   ✓ 创建闸站，包含 {len(gate_station.devices)} 座闸门")
        
        # 流量分配
        flow_targets = [100, 200, 300]
        for target in flow_targets:
            result = gate_station.distribute_flow(target_flow=target)
            if result['success']:
                avg_opening = np.mean(list(result['gate_settings'].values()))
                print(f"   目标流量 {target:3d} m³/s → 平均开度 {avg_opening:5.1f}%")
        
        # 3. 电站演示
        print("\n⚡ 电站运行演示...")
        power_station = PowerStationObject('demo_power_station')
        
        power_station_config = {
            'station_configuration': {
                'devices': [
                    {'type': 'turbine', 'rated_capacity': 100.0},
                    {'type': 'turbine', 'rated_capacity': 80.0},
                    {'type': 'turbine', 'rated_capacity': 60.0}
                ],
                'complexity': 'compound'
            }
        }
        power_station._object_config = power_station_config
        power_station.initialize()
        
        print(f"   ✓ 创建电站，包含 {len(power_station.devices)} 台机组")
        
        # 发电优化
        power_targets = [50, 120, 180, 240]
        for target in power_targets:
            result = power_station.optimize_power_generation(target_power=target)
            if result['success']:
                efficiency = len([u for u in result['unit_settings'].values() if u['power_output'] > 0])
                print(f"   目标功率 {target:3d} MW → 运行 {efficiency} 台机组，实际 {result['allocated_power']:5.1f} MW")
        
        print("\n✅ 枢纽站演示完成！")
        
    except Exception as e:
        print(f"❌ 枢纽站演示失败: {e}")


def demo_water_network_topology():
    """演示水网拓扑结构"""
    print("\n" + "=" * 80)
    print("水网拓扑结构演示")
    print("=" * 80)
    
    try:
        # 构建一个典型的水网系统
        print("\n🌐 构建典型水网系统...")
        
        # 水源
        source_reservoir = create_water_object('reservoir', 'source_reservoir')
        print("   ✓ 水源水库")
        
        # 主输水系统
        main_channel = create_water_object('channel', 'main_channel')
        regulation_gate = create_water_object('gate', 'regulation_gate')
        print("   ✓ 主输水渠道 + 调节闸门")
        
        # 分水枢纽
        distribution_hub = create_water_object('hub_station', 'distribution_hub')
        print("   ✓ 分水枢纽站")
        
        # 分支系统1：灌溉系统
        irrigation_channel = create_water_object('channel', 'irrigation_channel')
        irrigation_gates = [
            create_water_object('gate', f'irrigation_gate_{i}') for i in range(1, 4)
        ]
        print("   ✓ 灌溉系统：1条渠道 + 3座分水闸")
        
        # 分支系统2：城市供水
        water_treatment = create_water_object('pump_station', 'water_treatment_station')
        supply_pipes = [
            create_water_object('pipe', f'supply_pipe_{i}') for i in range(1, 3)
        ]
        regulation_valves = [
            create_water_object('valve', f'regulation_valve_{i}') for i in range(1, 3)
        ]
        print("   ✓ 城市供水：水厂泵站 + 2条供水管道 + 2个调节阀")
        
        # 分支系统3：水电站
        power_channel = create_water_object('channel', 'power_channel')
        hydro_power = create_water_object('power_station', 'hydro_power_station')
        tailrace = create_water_object('channel', 'tailrace_channel')
        print("   ✓ 水电系统：引水渠道 + 电站 + 尾水渠道")
        
        # 调蓄设施
        storage_tanks = [
            create_water_object('storage_tank', f'storage_tank_{i}') for i in range(1, 3)
        ]
        print("   ✓ 调蓄设施：2座调蓄池")
        
        # 汇总系统组成
        all_objects = [
            source_reservoir, main_channel, regulation_gate, distribution_hub,
            irrigation_channel, *irrigation_gates,
            water_treatment, *supply_pipes, *regulation_valves,
            power_channel, hydro_power, tailrace,
            *storage_tanks
        ]
        
        print(f"\n📊 水网系统统计:")
        object_types = {}
        for obj in all_objects:
            obj_type = obj.object_type.value
            object_types[obj_type] = object_types.get(obj_type, 0) + 1
        
        for obj_type, count in object_types.items():
            print(f"   - {obj_type}: {count} 个")
        
        print(f"\n   总计: {len(all_objects)} 个水系统对象")
        
        # 展示拓扑连接关系（简化）
        print(f"\n🔗 主要连接关系:")
        connections = [
            ("水源水库", "主输水渠道"),
            ("主输水渠道", "调节闸门"),
            ("调节闸门", "分水枢纽站"),
            ("分水枢纽站", "灌溉渠道"),
            ("分水枢纽站", "水厂泵站"),
            ("分水枢纽站", "引水渠道"),
            ("引水渠道", "水电站"),
            ("水电站", "尾水渠道")
        ]
        
        for upstream, downstream in connections:
            print(f"   {upstream} → {downstream}")
        
        print("\n✅ 水网拓扑结构演示完成！")
        print("💡 该系统展示了WaterNet支持的完整水网对象体系")
        
    except Exception as e:
        print(f"❌ 拓扑演示失败: {e}")


def main():
    """主函数"""
    print("WaterNet 完整水网对象体系演示")
    print("=" * 100)
    print("本演示展示了基于用户需求扩展的完整水系统对象体系")
    print("包括输水、存储、调控、枢纽站等所有类型的水系统对象")
    print("=" * 100)
    
    try:
        # 主要演示模块
        demo_complete_water_network()      # 完整水网演示
        demo_control_objects()             # 调控对象演示  
        demo_station_objects()             # 枢纽站演示
        demo_water_network_topology()      # 拓扑结构演示
        
        print("\n" + "=" * 100)
        print("🎉 完整水网对象体系演示成功完成！")
        print("\n💎 核心成果总结:")
        print("   ✅ 输水对象: 河道、管道、倒虹吸")
        print("   ✅ 存储对象: 水库、湖泊、调蓄池") 
        print("   ✅ 调控对象: 闸、泵、阀、水轮机")
        print("   ✅ 枢纽站: 泵站、闸站、电站等复合对象")
        print("   ✅ 统一接口: 配置驱动的对象创建和管理")
        print("   ✅ 系统集成: 支持复杂水网系统建模")
        print("\n🚀 这个完整的对象体系为水网系统数字化建模提供了强大的基础！")
        print("=" * 100)
        
    except Exception as e:
        print(f"❌ 演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()