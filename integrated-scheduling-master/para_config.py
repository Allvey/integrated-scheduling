#!E:\Pycharm Projects\Waytous
# -*- coding: utf-8 -*-
# @Time : 2021/8/4 15:50
# @Author : Opfer
# @Site :
# @File : para_config.py
# @Software: PyCharm

from static_data_process import *
from settings import *
import numpy as np

# 全局参数设定

# 空载任务集合
empty_task_set = [0, 1, 5]

# 重载任务集合
heavy_task_set = [2, 3, 4]

# 空载矿卡速度，单位（km/h）
global empty_speed

empty_speed = 25

# 重载矿卡速度，单位（km/h）
global heavy_speed

heavy_speed = 22

# 卸载设备目标卸载量
dump_target_mass = 5000

# 挖机目标装载量
excavator_target_mass = 5000

# 任务集合
task_set = [-2, 0, 1, 2, 3, 4, 5]

# Big integer
M = 100000000

# 装载区、卸载区、备停区在调度算法运行器件默认不发生改变，提前计算部分参量
# (uuid,index(id)映射关系, 装载区数量, 卸载区数量, 备停区数量, 以及初次统计动态调度矿卡)
(
    load_area_uuid_to_index_dict,
    unload_area_uuid_to_index_dict,
    load_area_index_to_uuid_dict,
    unload_area_index_to_uuid_dict,
) = build_work_area_uuid_index_map()

load_area_num, unload_area_num = len(load_area_uuid_to_index_dict), len(
    unload_area_uuid_to_index_dict
)

park_uuid_to_index_dict, park_index_to_uuid_dict = build_park_uuid_index_map()

park_num = len(park_uuid_to_index_dict)

truck_uuid_to_name_dict, truck_name_to_uuid_dict = build_truck_uuid_name_map()

# 矿卡集合
truck_set = set(update_total_truck())

# 固定派车矿卡集合
fixed_truck_set = set(update_fixdisp_truck())

# 动态派车矿卡集合
dynamic_truck_set = truck_set.difference(fixed_truck_set)

dynamic_truck_num = len(dynamic_truck_set)

logger.info("可用于动态派车的矿卡：")
logger.info(dynamic_truck_set)

# 用于动态调度的挖机及卸载设备
dynamic_excavator_set = set(update_autodisp_excavator())
dynamic_excavator_num = len(dynamic_excavator_set)

dynamic_dump_set = set(update_autodisp_dump())
dynamic_dump_num = len(dynamic_dump_set)

# 设备映射类, 存储除工作区以外的映射关系
# 其余设备类继承该类
class DeviceMap:
    def __init__(self):
        self.excavator_uuid_to_index_dict = {}
        self.dump_uuid_to_index_dict = {}
        self.excavator_index_to_uuid_dict = {}
        self.dump_index_to_uuid_dict = {}

        self.dump_uuid_to_unload_area_uuid_dict = {}
        self.excavator_uuid_to_load_area_uuid_dict = {}
        self.excavator_index_to_load_area_index_dict = {}
        self.dump_index_to_unload_area_index_dict = {}

        self.truck_uuid_to_index_dict = {}
        self.truck_index_to_uuid_dict = {}

    def get_excavator_uuid_to_index_dict(self):
        return self.excavator_uuid_to_index_dict

    def get_dump_uuid_to_index_dict(self):
        return self.dump_uuid_to_index_dict

    def get_excavator_index_to_uuid_dict(self):
        return self.excavator_index_to_uuid_dict

    def get_dump_index_to_uuid_dict(self):
        return self.dump_index_to_uuid_dict

    def get_dump_uuid_to_unload_area_uuid_dict(self):
        return self.dump_uuid_to_unload_area_uuid_dict

    def get_excavator_uuid_to_load_area_uuid_dict(self):
        return self.excavator_uuid_to_load_area_uuid_dict

    def get_excavator_index_to_load_area_index_dict(self):
        return self.excavator_index_to_load_area_index_dict

    def get_dump_index_to_unload_area_index_dict(self):
        return self.dump_index_to_unload_area_index_dict

    def get_truck_uuid_to_index_dict(self):
        return self.truck_uuid_to_index_dict

    def get_truck_index_to_uuid_dict(self):
        return self.truck_index_to_uuid_dict

    def period_map_para_update(self):
        device_map_dict = update_deveices_map(
            unload_area_uuid_to_index_dict, load_area_uuid_to_index_dict
        )

        self.excavator_uuid_to_index_dict = device_map_dict[
            "excavator_uuid_to_index_dict"
        ]
        self.dump_uuid_to_index_dict = device_map_dict["dump_uuid_to_index_dict"]
        self.excavator_index_to_uuid_dict = device_map_dict[
            "excavator_index_to_uuid_dict"
        ]
        self.dump_index_to_uuid_dict = device_map_dict["dump_index_to_uuid_dict"]

        self.dump_uuid_to_unload_area_uuid_dict = device_map_dict[
            "dump_uuid_to_unload_area_uuid_dict"
        ]
        self.excavator_uuid_to_load_area_uuid_dict = device_map_dict[
            "excavator_uuid_to_load_area_uuid_dict"
        ]
        self.excavator_index_to_load_area_index_dict = device_map_dict[
            "excavator_index_to_load_area_index_dict"
        ]
        self.dump_index_to_unload_area_index_dict = device_map_dict[
            "dump_index_to_unload_area_index_dict"
        ]

        truck_map_dict = update_truck_uuid_index_map(dynamic_truck_set)

        self.truck_uuid_to_index_dict = truck_map_dict["truck_uuid_to_index_dict"]
        self.truck_index_to_uuid_dict = truck_map_dict["truck_index_to_uuid_dict"]

    def period_map_para_load(self):
        # 装载关系映射
        self.excavator_uuid_to_index_dict = device_map.excavator_uuid_to_index_dict
        self.dump_uuid_to_index_dict = device_map.dump_uuid_to_index_dict
        self.excavator_index_to_uuid_dict = device_map.excavator_index_to_uuid_dict
        self.dump_index_to_uuid_dict = device_map.dump_index_to_uuid_dict

        self.dump_uuid_to_unload_area_uuid_dict = (
            device_map.dump_uuid_to_unload_area_uuid_dict
        )
        self.excavator_uuid_to_load_area_uuid_dict = (
            device_map.excavator_uuid_to_load_area_uuid_dict
        )
        self.excavator_index_to_load_area_index_dict = (
            device_map.excavator_index_to_load_area_index_dict
        )
        self.dump_index_to_unload_area_index_dict = (
            device_map.dump_index_to_unload_area_index_dict
        )

        self.truck_uuid_to_index_dict = device_map.truck_uuid_to_index_dict
        self.truck_index_to_uuid_dict = device_map.truck_index_to_uuid_dict


# 路网信息类
class WalkManage(DeviceMap):
    def __init__(self):
        # # 工作区和设备不具备一一对应关系, 为方便就计算, 算法维护两套路网: 面向路网和面向设备

        # 路网真实距离
        self.walk_time_to_excavator = np.full(
            (dynamic_dump_num, dynamic_excavator_num), M
        )
        self.walk_time_to_dump = np.full((dynamic_dump_num, dynamic_excavator_num), M)
        self.walk_time_park_to_excavator = np.full((park_num, dynamic_excavator_num), M)
        self.walk_time_park_to_load_area = np.full((park_num, load_area_num), M)
        self.walk_time_to_load_area = np.full((unload_area_num, load_area_num), M)
        self.walk_time_to_unload_area = np.full((unload_area_num, load_area_num), M)

        # 路网行驶时间
        self.distance_to_excavator = np.full(
            (dynamic_dump_num, dynamic_excavator_num), M
        )
        self.distance_to_dump = np.full((dynamic_dump_num, dynamic_excavator_num), M)
        self.distance_park_to_excavator = np.full((park_num, dynamic_excavator_num), M)
        self.distance_park_to_load_area = np.full((park_num, load_area_num), M)
        self.distance_to_load_area = np.full((unload_area_num, load_area_num), M)
        self.distance_to_unload_area = np.full((unload_area_num, load_area_num), M)

    def get_walk_time_to_load_area(self):
        return self.walk_time_to_load_area

    def get_walk_time_to_unload_area(self):
        return self.walk_time_to_unload_area

    def get_walk_time_to_excavator(self):
        return self.walk_time_to_excavator

    def get_walk_time_to_dump(self):
        return self.walk_time_to_dump

    def get_walk_time_park_to_load_area(self):
        return self.walk_time_park_to_load_area

    def get_walk_time_park_to_excavator(self):
        return self.walk_time_park_to_excavator

    def get_distance_to_load_area(self):
        return self.distance_to_load_area

    def get_distance_to_unload_area(self):
        return self.distance_to_unload_area

    def get_distance_to_excavator(self):
        return self.distance_to_excavator

    def get_distance_to_dump(self):
        return self.distance_to_dump

    def get_distance_park_to_load_area(self):
        return self.distance_park_to_load_area

    def get_distance_park_to_excavator(self):
        return self.distance_park_to_excavator

    def period_walk_para_update(self):

        self.period_map_para_load()

        # 计算路网距离及行走时间
        try:
            # 处理距离
            for item in session_postgre.query(WalkTime).all():
                load_area = str(item.load_area_id)
                unload_area = str(item.unload_area_id)
                load_area_index = load_area_uuid_to_index_dict[load_area]
                unload_area_index = unload_area_uuid_to_index_dict[unload_area]
                self.distance_to_load_area[unload_area_index][load_area_index] = float(
                    item.to_load_distance
                )
                self.walk_time_to_load_area[unload_area_index][load_area_index] = float(
                    60 / 1000 * item.to_load_distance / empty_speed
                )
                self.distance_to_unload_area[unload_area_index][
                    load_area_index
                ] = float(item.to_unload_distance)
                self.walk_time_to_unload_area[unload_area_index][
                    load_area_index
                ] = float(60 / 1000 * item.to_unload_distance / heavy_speed)
        except Exception as es:
            logger.error("路网信息异常")
            logger.error(es)

        # 计算设备路网距离及行走时间
        try:
            for i in range(dynamic_dump_num):
                for j in range(dynamic_excavator_num):
                    self.distance_to_excavator[i][j] = self.distance_to_load_area[
                        self.dump_index_to_unload_area_index_dict[i]
                    ][self.excavator_index_to_load_area_index_dict[j]]
                    self.walk_time_to_excavator[i][j] = self.walk_time_to_load_area[
                        self.dump_index_to_unload_area_index_dict[i]
                    ][self.excavator_index_to_load_area_index_dict[j]]
                    self.distance_to_dump[i][j] = self.distance_to_unload_area[
                        self.dump_index_to_unload_area_index_dict[i]
                    ][self.excavator_index_to_load_area_index_dict[j]]
                    self.walk_time_to_dump[i][j] = self.walk_time_to_unload_area[
                        self.dump_index_to_unload_area_index_dict[i]
                    ][self.excavator_index_to_load_area_index_dict[j]]
        except Exception as es:
            logger.error("设备路网信息异常异常")
            logger.error(es)

        # try:
        for item in session_postgre.query(WalkTimePark).all():
            load_area = str(item.load_area_id)
            park_area = str(item.park_area_id)
            load_area_index = load_area_uuid_to_index_dict[load_area]
            park_index = park_uuid_to_index_dict[park_area]
            self.distance_park_to_load_area[park_index][load_area_index] = float(
                item.park_load_distance
            )
            self.walk_time_park_to_load_area[park_index][load_area_index] = float(
                60 / 1000 * item.park_load_distance / empty_speed
            )
        # except Exception as es:
        #     logger.error("备停区路网信息异常")
        #     logger.error(es)
        # try:
        for i in range(park_num):
            for j in range(dynamic_excavator_num):
                self.distance_park_to_excavator[i][j] = self.distance_park_to_load_area[
                    i
                ][self.excavator_index_to_load_area_index_dict[j]]
                self.walk_time_park_to_excavator[i][
                    j
                ] = self.walk_time_park_to_load_area[i][
                    self.excavator_index_to_load_area_index_dict[j]
                ]
        # except Exception as es:
        #     logger.error("备停区设备路网信息异常")
        #     logger.error(es)

    def period_walk_para_load(self):
        # 装载路网信息
        self.distance_to_load_area = walk_manage.distance_to_load_area
        self.distance_to_unload_area = walk_manage.distance_to_unload_area
        self.distance_park_to_load_area = walk_manage.distance_park_to_load_area

        self.distance_to_excavator = walk_manage.distance_to_excavator
        self.distance_to_dump = walk_manage.distance_to_dump
        self.distance_park_to_excavator = walk_manage.distance_park_to_excavator

        self.walk_time_to_excavator = walk_manage.walk_time_to_excavator
        self.walk_time_to_dump = walk_manage.walk_time_to_dump
        self.walk_time_park_to_excavator = walk_manage.walk_time_park_to_excavator

        self.walk_time_to_load_area = walk_manage.walk_time_to_load_area
        self.walk_time_to_unload_area = walk_manage.walk_time_to_unload_area
        self.walk_time_park_to_load_area = walk_manage.walk_time_park_to_load_area


device_map = DeviceMap()

walk_manage = WalkManage()

device_map.period_map_para_update()

walk_manage.period_walk_para_update()


def period_para_update():
    global load_area_uuid_to_index_dict, load_area_index_to_uuid_dict
    global unload_area_uuid_to_index_dict, unload_area_index_to_uuid_dict
    global load_area_num, unload_area_num, park_num
    global park_uuid_to_index_dict, park_index_to_uuid_dict
    global truck_uuid_to_name_dict, truck_name_to_uuid_dict
    global dynamic_truck_num, dynamic_excavator_num, dynamic_dump_num
    # 装载区、卸载区、备停区在调度算法运行器件默认不发生改变，提前计算部分参量
    # (uuid,index(id)映射关系, 装载区数量, 卸载区数量, 备停区数量, 以及初次统计动态调度矿卡)
    (
        load_area_uuid_to_index_dict,
        unload_area_uuid_to_index_dict,
        load_area_index_to_uuid_dict,
        unload_area_index_to_uuid_dict,
    ) = build_work_area_uuid_index_map()

    load_area_num, unload_area_num = len(load_area_uuid_to_index_dict), len(
        unload_area_uuid_to_index_dict
    )

    park_uuid_to_index_dict, park_index_to_uuid_dict = build_park_uuid_index_map()

    park_num = len(park_uuid_to_index_dict)

    truck_uuid_to_name_dict, truck_name_to_uuid_dict = build_truck_uuid_name_map()

    # 矿卡集合
    truck_set = set(update_total_truck())

    # 固定派车矿卡集合
    fixed_truck_set = set(update_fixdisp_truck())

    # 动态派车矿卡集合
    dynamic_truck_set = truck_set.difference(fixed_truck_set)

    dynamic_truck_num = len(dynamic_truck_set)

    logger.info("可用于动态派车的矿卡：")
    logger.info(dynamic_truck_set)

    # 用于动态调度的挖机及卸载设备
    dynamic_excavator_set = set(update_autodisp_excavator())
    dynamic_excavator_num = len(dynamic_excavator_set)

    dynamic_dump_set = set(update_autodisp_dump())
    dynamic_dump_num = len(dynamic_dump_set)

    device_map.period_map_para_update()

    walk_manage.period_walk_para_update()
