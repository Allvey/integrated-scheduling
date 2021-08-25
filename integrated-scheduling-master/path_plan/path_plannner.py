#!E:\Pycharm Projects\Waytous
# -*- coding: utf-8 -*-
# @Time : 2021/7/26 14:35
# @Author : Opfer
# @Site :
# @File : path_plannner.py    
# @Software: PyCharm

import numpy
from settings import *
from static_data_process import *
from settings import *
from para_config import *

M = 1000000


class PathPlanner(WalkManage):
    def __init__(self):
        # 路线行驶成本
        self.rout_cost = np.array((unload_area_num, load_area_num))
        # 路段集合
        self.lane_set = {}
        # 车辆长度(暂)
        self.truck_length = 113
        # 装载区数量
        self.num_of_load_area = len(set(update_load_area()))
        # 卸载区数量
        self.num_of_unload_area = len(set(update_unload_area()))
        # 备停区数量
        self.num_of_park_area = len(set(update_park_area()))
        # 路网行驶成本信息信息
        self.cost_to_load_area = np.full((self.num_of_unload_area, self.num_of_load_area), M)
        self.cost_to_unload_area = np.full((self.num_of_unload_area, self.num_of_load_area), M)
        # 路网信息（备停区）
        self.cost_park_to_load_area = np.full((self.num_of_park_area, self.num_of_load_area), M)
        # 路段类
        self.lane = LaneInfo()
        self.lane.lane_speed_generate()

    def path_cost_generate(self, load_area_id, unload_area_id, is_park):

        # 卸载道路阻塞成本初始化
        cost_to_unload_blockage = 0
        # 装载道路阻塞成本初始化
        cost_to_load_blockage = 0
        # 卸载道路总成本初始化
        to_unload_cost = 0
        # 装载道路总成本初始化
        to_load_cost = 0
        # 阻塞成本权重
        alpha = 10000
        # 距离成本权重
        beta = 1

        try:
            # 备停区处理
            if is_park:
                # 提取指定道路记录
                path = session_postgre.query(WalkTimePark).filter_by(park_area_id=unload_area_id,
                                                                     load_area_id=load_area_id).first()

                # 读取道路路段信息
                for lane_id in path.park_load_lanes:
                    # 各路段阻塞成本累加
                    cost_to_load_blockage = cost_to_load_blockage + beta * self.lane_cost_generate(lane_id)

                # 道路总成本=道路距离成本+道路阻塞成本
                to_load_cost = alpha * cost_to_load_blockage + beta * path.park_load_distance
            else:
                path = session_postgre.query(WalkTime).filter_by(load_area_id=load_area_id,
                                                                 unload_area_id=unload_area_id).first()

                for lane_id in path.to_unload_lanes:
                    cost_to_unload_blockage = cost_to_unload_blockage + self.lane_cost_generate(lane_id)

                for lane_id in path.to_load_lanes:
                    cost_to_load_blockage = cost_to_load_blockage + self.lane_cost_generate(lane_id)

                to_unload_cost = alpha * cost_to_unload_blockage + beta * path.to_unload_distance
                to_load_cost = alpha * cost_to_load_blockage + beta * path.to_load_distance
        except Exception as es:
            logger.error(f'道路{load_area_id-unload_area_id}行驶成本计算异常')
            logger.error(es)

        return to_load_cost, to_unload_cost

    def lane_cost_generate(self, lane_id):
        try:

            # 读取路段记录
            lane_rec = session_postgre.query(Lane).filter_by(Id=lane_id).first()

            # 道路长度
            lane_length = lane_rec.Length
            # 车辆自由行驶时的速度
            clear_speed = lane_rec.MaxSpeed

            # 1. 计算阻塞时车辆密度=路段长度/车辆长度
            truck_density = lane_length / self.truck_length
            # 2. 读取实际车流速度
            actual_speed = self.lane.lane_speed_dict[lane_id]
            # 3. 计算路段阻塞程度=(1-实际路段速度)/路段最高速度
            lane_blockage = (1 - actual_speed / clear_speed) * truck_density
        except Exception as es:
            logger.error('路段拥堵成本计算异常')
            logger.error(es)

        return lane_blockage

    def walk_cost(self):

        self.period_walk_para_load()

        self.period_map_para_load()

        try:

            # 读取路网成本
            for walk_time in session_postgre.query(WalkTime).all():
                unload_area_index = unload_area_uuid_to_index_dict[str(walk_time.unload_area_id)]
                load_area_index = load_area_uuid_to_index_dict[str(walk_time.load_area_id)]
                self.cost_to_load_area[unload_area_index][load_area_index], \
                self.cost_to_unload_area[unload_area_index][load_area_index] = \
                    self.path_cost_generate(walk_time.load_area_id, walk_time.unload_area_id, False)

            # 读取备停区路网成本
            for walk_time_park in session_postgre.query(WalkTimePark).all():
                park_area_index = park_uuid_to_index_dict[str(walk_time_park.park_area_id)]
                load_area_index = load_area_uuid_to_index_dict[str(walk_time_park.load_area_id)]
                _, self.cost_park_to_load_area[park_area_index][load_area_index] = \
                    self.path_cost_generate(walk_time_park.load_area_id, walk_time_park.park_area_id, True)
        except Exception as es:
            logger.error('路网信息计成本计算异常')
            logger.error(es)

        cost_to_excavator = np.zeros_like(self.distance_to_excavator)
        cost_to_dump = np.zeros_like(self.distance_to_dump)


        dynamic_excavator_set



        for i in range(dynamic_dump_num):
            for j in range(dynamic_excavator_num):
                cost_to_excavator[i][j] = self.cost_to_load_area[self.dump_index_to_unload_area_index_dict[i]][self.excavator_index_to_load_area_index_dict[j]]
                cost_to_dump[i][j] = self.cost_to_unload_area[self.dump_index_to_unload_area_index_dict[i]][self.excavator_index_to_load_area_index_dict[j]]

        logger.info("真实路网距离-驶往挖机:")
        logger.info(self.distance_to_excavator)

        logger.info("真实路网距离-驶往卸点:")
        logger.info(self.distance_to_dump)

        logger.info("阻塞路网距离-驶往挖机:")
        logger.info(cost_to_excavator)

        logger.info("阻塞路网距离-驶往卸点:")
        logger.info(cost_to_dump)


class LaneInfo:
    def __init__(self):
        self.lane_speed_dict = {}

    def update_truck_speed(self):
        # 读取矿卡实时速度信息
        try:
            truck_speed_dict = {}
            device_name_set = redis2.keys()
            for item in device_name_set:
                item = item.decode(encoding='utf-8')
                json_value = json.loads(redis2.get(item))
                device_type = json_value.get('type')
                if device_type == 1:
                    truck_speed = json_value.get('speed')
                    truck_speed_dict[truck_name_to_uuid_dict[item]] = truck_speed
        except Exception as es:
            logger.error(f'矿卡{item}实时速度读取异常')
            logger.error(es)

        return truck_speed_dict

    def update_truck_loacate(self):
        # 读取矿卡所在路段信息
        try:
            truck_locate_dict = {}
            device_name_set = redis2.keys()
            for item in device_name_set:
                item = item.decode(encoding='utf-8')
                json_value = json.loads(redis2.get(item))
                device_type = json_value.get('type')
                is_online = json_value.get('isOnline')
                if device_type == 1 and is_online:
                    truck_locate = json_value.get('laneId')
                    truck_locate_dict[truck_name_to_uuid_dict[item]] = truck_locate
        except Exception as es:
            logger.error(f'矿卡{item}所在路段信息读取异常')

        return truck_locate_dict

    def lane_speed_generate(self):

        # truck -> lane
        truck_locate_dict = self.update_truck_loacate()

        # print("truck -> lane")
        # print(truck_locate_dict)

        logger.info("矿卡位于路段:")
        logger.info(truck_locate_dict)

        # truck -> speed
        truck_speed_dict = self.update_truck_speed()

        # print("truck -> speed")
        # print(truck_speed_dict)

        logger.info("矿卡当前速度:")
        logger.info(truck_speed_dict)

        try:
            # lane_set, 用到的路段集合
            lane_set = []
            for walk_time in session_postgre.query(WalkTime).all():
                for lane in walk_time.to_load_lanes:
                    lane_set.append(lane)
                for lane in walk_time.to_unload_lanes:
                    lane_set.append(lane)
            for walk_time_park in session_postgre.query(WalkTimePark).all():
                for lane in walk_time_park.park_load_lanes:
                    lane_set.append(lane)
            lane_set = set(lane_set)
        except Exception as es:
            logger.error('所用路网路段集合读取异常')
            logger.info(es)

        # lane -> speed, 各路段平均行驶速度
        self.lane_speed_dict = {}

        # lane -> num, 各路段行驶车辆
        lane_trucks_dict = {}

        # used lane, 存在行驶矿卡的路段
        tmp_lane_set = []

        try:

            # 初始化
            for lane_id in lane_set:
                self.lane_speed_dict[str(lane_id)] = 0
                lane_trucks_dict[str(lane_id)] = 0

            # 对于各路段信息
            for truck in truck_locate_dict.keys():
                lane_id = truck_locate_dict[truck]
                if lane_id in lane_set:
                    self.lane_speed_dict[truck_locate_dict[truck]] = self.lane_speed_dict[truck_locate_dict[truck]] + \
                                                                truck_speed_dict[truck]
                    # 该路段矿卡数量加一
                    lane_trucks_dict[truck_locate_dict[truck]] = lane_trucks_dict[truck_locate_dict[truck]] + 1
                    # 记录存在行驶矿卡的路段
                    tmp_lane_set.append(lane_id)

            # 存在矿卡的路段
            # print("存在矿卡的路段:")
            # print(tmp_lane_set)

            logger.info("存在矿卡的路段:")
            logger.info(tmp_lane_set)

            # 对不存在的矿卡路段，实时速度设置为最高
            for lane_id in lane_set:
                if lane_id not in tmp_lane_set:
                    self.lane_speed_dict[str(lane_id)] = session_postgre.query(Lane).filter_by(Id=lane_id).first().MaxSpeed
                    lane_trucks_dict[str(lane_id)] = 1

            # 各路段实时速度取平均
            for lane in lane_trucks_dict:
                self.lane_speed_dict[lane] = self.lane_speed_dict[lane] / lane_trucks_dict[lane]

        except Exception as es:
            logger.error("路段实时速度计算异常")
            logger.error(es)

        return self.lane_speed_dict

# path_planner = PathPlanner()
#
# path_planner.walk_cost()
