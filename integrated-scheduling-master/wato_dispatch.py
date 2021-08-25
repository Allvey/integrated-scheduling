#!E:\Pycharm Projects\Waytous
# -*- coding: utf-8 -*-
# @Time : 2021/6/15 10:35
# @Author : Opfer
# @Site :
# @File : wato_dispatch.py
# @Software: PyCharm


# 独立的调度系统


from sqlalchemy import Column, create_engine
from sqlalchemy import VARCHAR, DateTime, Float, Integer, BOOLEAN
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import numpy as np
from redis import StrictRedis, ConnectionPool
import redis
from datetime import datetime, timedelta
import copy
import json
import sched
import time
from tables import *
from urllib.parse import quote
import logging
import logging.handlers

# 全局参数设定
########################################################################################################################

empty_task_set = [0, 1, 5]

heavy_task_set = [2, 3, 4]

# 空载矿卡速度，单位（km/h）
empty_speed = 25

# 重载矿卡速度，单位（km/h）
heavy_speed = 22

# 卸点目标卸载量
dump_target_mass = 5000

# 挖机目标装载量
shovel_target_mass = 5000

task_set = [-2, 0, 1, 2, 3, 4, 5]

M = 100000000

# 连接reids
########################################################################################################################

pool5 = ConnectionPool(host='192.168.28.111', db=5, port=6379, password='Huituo@123')

redis5 = StrictRedis(connection_pool=pool5)

pool2 = ConnectionPool(host='192.168.28.111', db=2, port=6379, password='Huituo@123')

redis2 = StrictRedis(connection_pool=pool2)

# 创建对象的基类:
Base = declarative_base()


# 初始化数据库连接:

engine_mysql = create_engine('mysql+mysqlconnector://root:%s@192.168.28.111:3306/waytous' % quote('Huituo@123'))

engine_postgre = create_engine('postgresql://postgres:%s@192.168.28.111:5432/shenbao_2021520' % quote('Huituo@123'))

# 创建DBsession_mysql类型:
DBsession_mysql = sessionmaker(bind=engine_mysql)

DBsession_postgre = sessionmaker(bind=engine_postgre)

# 创建session_mysql对象:
session_mysql = DBsession_mysql()

session_postgre = DBsession_postgre()


# 创建日志
########################################################################################################################
# logging初始化工作
logging.basicConfig()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

timefilehandler = logging.handlers.TimedRotatingFileHandler("RDlogs/dispatch.log", when='M', interval=1, backupCount=60)
# 设置后缀名称，跟strftime的格式一样
timefilehandler.suffix = "%Y-%m-%d_%H-%M.log"

formatter = logging.Formatter('%(asctime)s|%(name)-12s: %(levelname)-8s %(message)s')
timefilehandler.setFormatter(formatter)
logger.addHandler(timefilehandler)

########################################################################################################################
# load_area_id <-> load_area_index
# unload_area_id <-> unload_area_index
load_area_uuid_to_index_dict = {}
unload_area_uuid_to_index_dict = {}
load_area_index_to_uuid_dict = {}
unload_area_index_to_uuid_dict = {}

unload_area_num = 0
load_area_num = 0

for item in session_postgre.query(WalkTime).all():
    load_area = str(item.load_area_id)
    unload_area = str(item.unload_area_id)
    if load_area not in load_area_uuid_to_index_dict:
        load_area_uuid_to_index_dict[load_area] = load_area_num
        load_area_index_to_uuid_dict[load_area_num] = load_area
        load_area_num = load_area_num + 1
    if unload_area not in unload_area_uuid_to_index_dict:
        unload_area_uuid_to_index_dict[unload_area] = unload_area_num
        unload_area_index_to_uuid_dict[unload_area_num] = unload_area
        unload_area_num = unload_area_num + 1

########################################################################################################################
# park_id <-> park_index
park_uuid_to_index_dict = {}
park_index_to_uuid_dict = {}

park_num = 0

for item in session_postgre.query(WalkTimePark).all():
    park = str(item.park_area_id)
    if park not in park_uuid_to_index_dict:
        park_uuid_to_index_dict[park] = park_num
        park_index_to_uuid_dict[park_num] = park
        park_num = park_num + 1


########################################################################################################################
# truck_id <-> truck_name
truck_uuid_to_name_dict = {}
truck_name_to_uuid_dict = {}

for item in session_mysql.query(Equipment).filter_by(device_type=1).all():
    truck_id = item.id
    truck_name = item.equipment_id

    truck_name_to_uuid_dict[truck_name] = truck_id
    truck_uuid_to_name_dict[truck_id] = truck_name


########################################################################################################################

# 矿卡集合
truck_set = []

query = np.array(session_mysql.query(Equipment).filter_by(device_type=1, isdeleted=0).all())

for item in query:
    truck_set.append(item.id)

truck_set = set(truck_set)

# 固定派车矿卡集合
fixed_truck_set = []

query = np.array(session_mysql.query(Dispatch).filter_by(isauto=0, isdeleted=0).all())

for item in query:
    fixed_truck_set.append(item.truck_id)

fixed_truck_set = set(fixed_truck_set)

# 动态派车矿卡集合

dynamic_truck_set = truck_set.difference(fixed_truck_set)

# print("可用于动态派车的矿卡：")
# print(dynamic_truck_set)

logger.info("可用于动态派车的矿卡：")
logger.info(dynamic_truck_set)

########################################################################################################################
# 用于动态派车的挖机集合
dynamic_excavator_set = []
# 用于动态调度的卸载点集合
dynamic_dump_set = []
for item in session_mysql.query(Dispatch).filter_by(isdeleted=0, isauto=1).all():
    dynamic_excavator_set.append(item.exactor_id)
    dynamic_dump_set.append(item.dump_id)

# 用于动态调度的挖机及卸载设备数量
dynamic_excavator_set = set(dynamic_excavator_set)
dynamic_dump_set = set(dynamic_dump_set)


# for item in dynamic_truck_set:
#     now = datetime.now()
#     truck = Truck(truck_id=item, current_task=-1, last_load_time=now, last_unload_time=now, payload=220.0)
#
#     truck = truck.check_existing()
#     session_mysql.add(truck)
#
#     session_mysql.commit()



def seq_is_empty(sequence):
    # 判断sequence是否为空
    for i in range(len(sequence)):
        if len(sequence[i]) != 0:
            return False
    return True


def sequence_meet(sequence):
    # 判断构造解是否达标
    meet = True
    for i in range(len(sequence)):
        meet = meet and len(sequence[i]) > 2
    return meet


class Dispatcher:
    def __init__(self):
        # 设备数量
        self.dumps = len(dynamic_dump_set)
        self.shovels = len(dynamic_excavator_set)
        self.trucks = len(dynamic_truck_set)
        self.dis = np.full((self.dumps, self.shovels), M)
        # 目标产量
        self.dump_target_mass = np.zeros(self.dumps)
        self.shovel_target_mass = np.zeros(self.shovels)
        # 真实实际产量
        self.cur_dump_real_mass = np.zeros(self.dumps)
        self.cur_shovel_real_mass = np.zeros(self.shovels)
        # 预计产量
        self.pre_dump_real_mass = copy.deepcopy(self.cur_dump_real_mass)
        self.pre_shovel_real_mass = copy.deepcopy(self.cur_shovel_real_mass)
        # 模拟实际产量(防止修改真实产量)
        self.sim_dump_real_mass = np.zeros(self.dumps)
        self.sim_shovel_real_mass = np.zeros(self.shovels)
        # 真实设备可用时间
        self.cur_truck_reach_dump = np.zeros(self.trucks)
        self.cur_truck_reach_shovel = np.zeros(self.trucks)
        self.cur_shovel_ava_time = np.zeros(self.shovels)
        self.cur_dump_ava_time = np.zeros(self.dumps)
        # 模拟各设备可用时间
        self.sim_truck_reach_dump = np.zeros(self.trucks)
        self.sim_truck_reach_shovel = np.zeros(self.trucks)
        self.sim_shovel_ava_time = np.zeros(self.shovels)
        self.sim_dump_ava_time = np.zeros(self.dumps)

        # 矿卡阶段
        self.truck_current_task = {}

        # 维护一个矿卡调度表
        self.Seq = [[] for _ in range(self.trucks)]

        # 调度开始时间
        self.start_time = datetime.now()

        # self.relative_now_time = datetime.now() - self.start_time

        # 行走时间
        self.com_time_area = np.full((unload_area_num, load_area_num), M)
        self.go_time_area = np.full((unload_area_num, load_area_num), M)

        self.com_time_eq = np.full((self.dumps, self.shovels), M)
        self.go_time_eq = np.full((self.dumps, self.shovels), M)

        self.park_to_load_area = np.full((park_num, load_area_num), M)
        self.park_to_load_eq = np.full((park_num, self.shovels), M)

        # 卡车完成装载及卸载时间
        self.cur_truck_ava_time = np.zeros(self.trucks)
        self.sim_truck_ava_time = np.zeros(self.trucks)

        # 处理距离
        for item in session_postgre.query(WalkTime).all():
            load_area = str(item.load_area_id)
            unload_area = str(item.unload_area_id)
            load_area_index = load_area_uuid_to_index_dict[load_area]
            unload_area_index = unload_area_uuid_to_index_dict[unload_area]
            self.com_time_area[unload_area_index][load_area_index] = 60 / 1000 * item.to_load_distance / empty_speed
            self.go_time_area[unload_area_index][load_area_index] = 60 / 1000 * item.to_unload_distance / heavy_speed

    def update(self):

        print("#####################################周期更新#####################################")

        logger.info("周期更新开始")

        # 初始化挖机可用时间

        self.cur_shovel_ava_time = np.full(self.shovels,
                                           (datetime.now() - self.start_time) / timedelta(hours=0, minutes=1,
                                                                                          seconds=0))

        ################################################################################################################
        # 矿卡集合
        ################################################################################################################

        # 读取矿卡集合
        truck_set = []

        query = np.array(session_mysql.query(Equipment).filter_by(device_type=1, isdeleted=0).all())

        for item in query:
            truck_set.append(item.id)

        truck_set = set(truck_set)

        # 固定派车矿卡集合
        fixed_truck_set = []

        query = np.array(session_mysql.query(Dispatch).filter_by(isauto=0, isdeleted=0).all())

        for item in query:
            fixed_truck_set.append(item.truck_id)

        fixed_truck_set = set(fixed_truck_set)

        # 动态派车矿卡集合
        self.dynamic_truck_set = truck_set.difference(fixed_truck_set)

        # 更新矿卡数量
        self.trucks = len(self.dynamic_truck_set)


        ################################################################################################################
        # 更新矿卡参数
        ################################################################################################################

        # 卡车完成装载及卸载时间
        self.cur_truck_ava_time = np.zeros(self.trucks)
        self.sim_truck_ava_time = np.zeros(self.trucks)

        # 真实设备可用时间
        self.cur_truck_reach_dump = np.zeros(self.trucks)
        self.cur_truck_reach_shovel = np.zeros(self.trucks)
        # 模拟各设备可用时间
        self.sim_truck_reach_dump = np.zeros(self.trucks)
        self.sim_truck_reach_shovel = np.zeros(self.trucks)

        ################################################################################################################
        # 动态派车挖机、卸载设备集合
        ################################################################################################################

        # 用于动态派车的挖机集合
        self.dynamic_excavator_set = []
        # 用于动态调度的卸载点集合
        self.dynamic_dump_set = []
        for item in session_mysql.query(Dispatch).filter_by(isdeleted=0, isauto=1).all():
            self.dynamic_excavator_set.append(item.exactor_id)
            self.dynamic_dump_set.append(item.dump_id)

        # 用于动态调度的挖机及卸载设备数量
        self.dynamic_excavator_set = set(self.dynamic_excavator_set)
        self.dynamic_dump_set = set(self.dynamic_dump_set)

        # 更新挖机和卸载设备数量
        self.dumps = len(self.dynamic_dump_set)
        self.shovels = len(self.dynamic_excavator_set)

        # print("检测到挖机数量:", self.shovels)
        # print(self.dynamic_excavator_set)
        # print("检测到卸点数量：", self.dumps)

        # 初始化挖机可用时间

        self.cur_shovel_ava_time = np.full(self.shovels,
                                           (datetime.now() - self.start_time) / timedelta(hours=0, minutes=1,
                                                                                          seconds=0))

        ################################################################################################################
        # 挖机卸载点映射
        ################################################################################################################

        self.excavator_uuid_to_index_dict = {}  # 用于将Excavator表中的area_id映射到index
        self.dump_uuid_to_index_dict = {}  # 用于将Dump表中的area_id映射到index
        self.excavator_index_to_uuid_dict = {}  # 用于将index映射到Excavator表中的area_id
        self.dump_index_to_uuid_dict = {}  # 用于将index映射到Dump表中的area_id

        self.dump_uuid_to_unload_area_uuid_dict = {}
        self.excavator_uuid_to_load_area_uuid_dict = {}
        self.excavator_index_to_load_area_index_dict = {}
        self.dump_index_to_unload_area_index_dict = {}

        excavator_num = 0
        dump_num = 0
        for item in session_mysql.query(Dispatch).filter_by(isdeleted=0, isauto=1).all():
            # excavator_id <-> excavator_index
            # dump_id <-> dump_index
            # excavator_id <-> load_area_id
            # dump_id <-> unload_area_id
            # excavator_index <-> load_area_index
            # dump_index <-> unload_area_index
            excavator_id = item.exactor_id
            load_area_id = item.load_area_id
            unload_area_id = item.unload_area_id
            dump_id = item.dump_id
            if dump_id not in self.dump_uuid_to_unload_area_uuid_dict:
                self.dump_uuid_to_index_dict[dump_id] = dump_num
                self.dump_index_to_uuid_dict[dump_num] = dump_id
                self.dump_uuid_to_unload_area_uuid_dict[dump_id] = unload_area_id
                self.dump_index_to_unload_area_index_dict[self.dump_uuid_to_index_dict[dump_id]] = \
                    unload_area_uuid_to_index_dict[unload_area_id]
                dump_num = dump_num + 1
            if excavator_id not in self.excavator_uuid_to_index_dict:
                self.excavator_uuid_to_index_dict[excavator_id] = excavator_num
                self.excavator_index_to_uuid_dict[excavator_num] = excavator_id
                self.excavator_uuid_to_load_area_uuid_dict[excavator_id] = load_area_id
                self.excavator_index_to_load_area_index_dict[self.excavator_uuid_to_index_dict[excavator_id]] = \
                    load_area_uuid_to_index_dict[load_area_id]
                excavator_num = excavator_num + 1

        # print(self.excavator_index_to_load_area_index_dict)

        ################################################################################################################
        # 设备距离
        ################################################################################################################

        for i in range(self.dumps):
            for j in range(self.shovels):
                self.com_time_eq[i][j] = self.com_time_area[self.dump_index_to_unload_area_index_dict[i]] \
                    [self.excavator_index_to_load_area_index_dict[j]]
                self.go_time_eq[i][j] = self.go_time_area[self.dump_index_to_unload_area_index_dict[i]] \
                    [self.excavator_index_to_load_area_index_dict[j]]

        for item in session_postgre.query(WalkTimePort).all():
            load_area = str(item.load_area_id)
            park_area = str(item.park_area_id)
            load_area_index = load_area_uuid_to_index_dict[load_area]
            park_index = park_uuid_to_index_dict[park]
            self.park_to_load_area[park_index][load_area_index] = 60 / 1000 * item.park_load_distance / empty_speed

        for i in range(park_num):
            for j in range(self.shovels):
                self.park_to_load_eq[i][j] = self.park_to_load_area[i][self.excavator_index_to_load_area_index_dict[j]]

        ################################################################################################################
        # 矿卡映射
        ################################################################################################################
        self.truck_uuid_to_index_dict = {}
        self.truck_index_to_uuid_dict = {}

        # truck_id <-> truck_index
        truck_num = 0
        for truck_id in self.dynamic_truck_set:
            self.truck_uuid_to_index_dict[truck_id] = truck_num
            self.truck_index_to_uuid_dict[truck_num] = truck_id
            truck_num = truck_num + 1

        ################################################################################################################
        # 卡车当前任务
        ################################################################################################################
        # self.truck_current_stage = np.array(session_mysql.query(Truck.status).all())
        self.truck_current_task = {}
        device_name_set = redis2.keys()

        for item in device_name_set:
            item = item.decode(encoding='utf-8')
            json_value = json.loads(redis2.get(item))
            device_type = json_value.get('type')
            if device_type == 1:
                if truck_name_to_uuid_dict[item] in self.dynamic_truck_set:
                    currentTask = json_value.get('currentTask')
                    self.truck_current_task[truck_name_to_uuid_dict[item]] = currentTask
                    try:
                        if currentTask not in task_set:
                            raise Exception(f'车辆{item}出现未知状态{currentTask}')
                    except Exception as es:
                        logger.warning(es)
                        print(es)

        # print("矿卡当前任务：")
        # print(self.truck_current_task)

        logger.info("矿卡当前任务：")
        logger.info(self.truck_current_task)

        ################################################################################################################
        # 卡车当前状态
        ################################################################################################################

        self.truck_current_state = {}
        device_name_set = redis2.keys()

        for item in device_name_set:
            item = item.decode(encoding='utf-8')
            json_value = json.loads(redis2.get(item))
            device_type = json_value.get('type')
            if device_type == 1:
                if truck_name_to_uuid_dict[item] in self.dynamic_truck_set:
                    self.truck_current_state[truck_name_to_uuid_dict[item]] = json_value.get('state')

        # print("矿卡当前状态：")
        # print(self.truck_current_state)

        ################################################################################################################
        # 有效载重
        ################################################################################################################
        # self.payload = np.array(session_mysql.query(Truck.payload).all())
        self.payload = np.zeros(self.trucks)
        for truck_id in self.dynamic_truck_set:
            trcuk_index = self.truck_uuid_to_index_dict[truck_id]
            truck_spec = session_mysql.query(Equipment).filter_by(id=truck_id).first().equipment_spec
            # truck_spec = query.equipment_spec
            self.payload[trcuk_index] = session_mysql.query(EquipmentSpec).filter_by(id=truck_spec).first().capacity

        ################################################################################################################
        # 卡车最后一次装载/卸载时间
        ################################################################################################################

        self.last_load_time = {}
        self.last_unload_time = {}

        self.relative_last_load_time = {}
        self.relative_last_unload_time = {}

        # for x in redis2.keys():
        #     print(redis2.get(x))

        for item in self.dynamic_truck_set:
            json_value = json.loads(redis2.get(truck_uuid_to_name_dict[item]))
            device_type = json_value.get('type')
            # 判断是否为矿卡
            if device_type == 1:
                task = self.truck_current_task[item]
                state = self.truck_current_state[item]
                if task in heavy_task_set:
                    last_load_time_tmp = json_value.get('lastLoadTime')
                    if last_load_time_tmp is not None:
                        self.last_load_time[item] = datetime.strptime(last_load_time_tmp, \
                                                                        "%b %d, %Y %I:%M:%S %p")
                    else:
                        self.last_load_time[item] = datetime.now()
                    self.relative_last_load_time[item] = ((self.last_load_time[item] - self.start_time) /
                                                          timedelta(hours=0, minutes=1, seconds=0))
                    # print("相对last_load_time", self.relative_last_load_time[item])
                    logger.info("相对last_load_time")
                    logger.info(self.relative_last_load_time[item])
                if task in empty_task_set:
                    last_unload_time_tmp = json_value.get('lastUnloadTime')
                    if last_unload_time_tmp is not None:
                        self.last_unload_time[item] = datetime.strptime(last_unload_time_tmp, \
                                                                        "%b %d, %Y %I:%M:%S %p")
                    else:
                        self.last_unload_time[item] = datetime.now()
                    self.relative_last_unload_time[item] = ((self.last_unload_time[item] - self.start_time) /
                                                            timedelta(hours=0, minutes=1, seconds=0))
                    # print("相对last_unload_time", self.relative_last_unload_time[item])
                    logger.info("相对last_unload_time")
                    logger.info(self.relative_last_unload_time[item])

        ################################################################################################################
        # 计算平均装载时间
        ################################################################################################################
        self.loading_time = np.zeros(self.shovels)

        for excavator_id in self.excavator_uuid_to_index_dict.keys():
            ave_load_time = 0
            for query in session_mysql.query(JobRecord.start_time, JobRecord.end_time). \
                    join(Equipment, JobRecord.equipment_id == Equipment.equipment_id). \
                    filter(Equipment.id == excavator_id, JobRecord.end_time != None). \
                    order_by(JobRecord.start_time.desc()).limit(10):
                ave_load_time = ave_load_time + int(
                    (query.end_time - query.start_time) / timedelta(hours=0, minutes=1, seconds=0))
            self.loading_time[self.excavator_uuid_to_index_dict[excavator_id]] = ave_load_time / 10

        ################################################################################################################
        # 计算平均卸载时间
        ################################################################################################################
        self.unloading_time = np.zeros(dump_num)

        for dump_id in self.dump_uuid_to_index_dict.keys():
            ave_unload_time = 0
            for query in session_mysql.query(JobRecord.start_time, JobRecord.end_time). \
                    join(Equipment, JobRecord.equipment_id == Equipment.equipment_id). \
                    filter(Equipment.id == dump_id, JobRecord.end_time != None). \
                    order_by(JobRecord.start_time.desc()).limit(10):
                ave_unload_time = ave_unload_time + int(
                    (query.end_time - query.start_time) / timedelta(hours=0, minutes=1, seconds=0))
            self.unloading_time[self.dump_uuid_to_index_dict[dump_id]] = ave_unload_time / 10
            # print("average_unload_time: ", self.unloading_time[self.dump_uuid_to_index_dict[dump_id]])

        ################################################################################################################
        # 读取实时装载卸载量
        ################################################################################################################
        self.cur_shovel_real_mass = np.zeros(self.shovels)
        self.cur_dump_real_mass = np.zeros(self.dumps)

        now = datetime.now().strftime('%Y-%m-%d')

        for excavator_id in self.excavator_uuid_to_index_dict.keys():
            # print(excavator_id)
            for query in session_mysql.query(LoadInfo). \
                    join(Equipment, LoadInfo.dump_id == Equipment.equipment_id). \
                    filter(Equipment.id == excavator_id, LoadInfo.time > now). \
                    order_by(LoadInfo.time.desc()).all():
                # print("time:", query.time)
                # print("load_weight:", )
                self.cur_shovel_real_mass[self.excavator_uuid_to_index_dict[excavator_id]] = \
                    self.cur_shovel_real_mass[self.excavator_uuid_to_index_dict[excavator_id]] + query.load_weight

        for dump_id in self.dump_uuid_to_index_dict.keys():
            # print(excavator_id)
            for query in session_mysql.query(LoadInfo). \
                    join(Equipment, LoadInfo.dump_id == Equipment.equipment_id). \
                    filter(Equipment.id == dump_id, LoadInfo.time > now). \
                    order_by(LoadInfo.time.desc()).all():
                # print("time:", query.time)
                # print("load_weight:", )
                self.cur_dump_real_mass[self.dump_uuid_to_index_dict[dump_id]] = \
                    self.cur_dump_real_mass[self.dump_uuid_to_index_dict[dump_id]] + query.load_weight

        ################################################################################################################
        # 读取卡车当前行程
        ################################################################################################################
        self.truck_current_trip = np.full((self.trucks, 2), -1)

        for i in range(self.trucks):
            session_mysql.commit()
            truck_id = self.truck_index_to_uuid_dict[i]
            task = self.truck_current_task[self.truck_index_to_uuid_dict[i]]
            # print("truck_task:", truck_id, task)
            item = session_mysql.query(EquipmentPair).filter_by(truck_id=truck_id, isdeleted=0).first()

            # if task in heavy_task_set:
            #     print(item.id, item.truck_id, item.exactor_id, item.dump_id, item.isdeleted)
            try:
                if task in empty_task_set + heavy_task_set:
                    if item is None:
                        raise Exception("矿卡配对关系不存在")
            except Exception as es:
                print(es)
                logger.warning(es)
                return
            state = self.truck_current_state[self.truck_index_to_uuid_dict[i]]

            # 若矿卡状态为空运
            if task in empty_task_set:
                # print("读取空载行程")
                # print(item.exactor_id, item.dump_id)
                # 若矿卡从低停车场空运出发????????
                # if task == 0:
                #     last_unload_time = self.relative_last_unload_time[self.truck_index_to_uuid_dict[i]]
                #     # 开始区域id
                #     # 开始区域序号
                #     start_area_index = -1
                #     # 结束区域id
                #     end_area_id = self.excavator_uuid_to_load_area_uuid_dict[item.exactor_id]
                #     # 结束区域序号
                #     end_area_index = load_area_uuid_to_index_dict[end_area_id]
                #     self.truck_current_trip[i] = [-1, self.excavator_uuid_to_index_dict[item.exactor_id]]
                #     self.cur_truck_reach_shovel[i] = last_unload_time + self.com_time_area[start_area_index][
                #         end_area_index]
                # else:
                last_unload_time = self.relative_last_unload_time[self.truck_index_to_uuid_dict[i]]
                # 开始区域id
                start_area_id = self.dump_uuid_to_unload_area_uuid_dict[item.dump_id]
                # 开始区域序号
                start_area_index = unload_area_uuid_to_index_dict[start_area_id]
                end_area_id = self.excavator_uuid_to_load_area_uuid_dict[item.exactor_id]
                end_area_index = load_area_uuid_to_index_dict[end_area_id]
                self.truck_current_trip[i] = [self.dump_uuid_to_index_dict[item.dump_id],
                                              self.excavator_uuid_to_index_dict[item.exactor_id]]
                # if truck_uuid_to_name_dict[self.truck_index_to_uuid_dict[i]] in tmp_set:
                #     print("here")
                #     self.cur_truck_reach_shovel[i] = last_unload_time + 10 * self.com_time_area[start_area_index][
                #         end_area_index]
                # else:
                self.cur_truck_reach_shovel[i] = last_unload_time + self.com_time_area[start_area_index][
                        end_area_index]
            # 若矿卡状态为重载
            elif task in heavy_task_set:
                # print("读取重载行程")
                # print(item.exactor_id, item.dump_id)
                last_load_time = self.relative_last_load_time[self.truck_index_to_uuid_dict[i]]
                # 开始区域id
                start_area_id = self.excavator_uuid_to_load_area_uuid_dict[item.exactor_id]
                # 开始区域序号
                start_area_index = load_area_uuid_to_index_dict[start_area_id]
                # 结束区域id
                end_area_id = self.dump_uuid_to_unload_area_uuid_dict[item.dump_id]
                # 结束区域序号
                end_area_index = unload_area_uuid_to_index_dict[end_area_id]
                self.truck_current_trip[i] = [self.excavator_uuid_to_index_dict[item.exactor_id],
                                              self.dump_uuid_to_index_dict[item.dump_id]]
                self.cur_truck_reach_dump[i] = last_load_time + self.go_time_area[end_area_index][start_area_index]
            # 其他状态，矿卡状态为-2，equipment_pair表不存在该矿卡
            else:
                pass

        self.truck_current_trip.flatten()
        # print("当前矿卡行程：")
        # print(self.truck_current_trip)

        ################################################################################################################
        # 读取卸点产量
        ################################################################################################################

        # 卸载目标产量
        # self.dump_target_mass = (np.array(session_mysql.query(Dump.target_mass).all())).flatten()
        self.dump_target_mass = np.full(self.dumps, dump_target_mass)

        ################################################################################################################
        # 读取挖机产量
        ################################################################################################################

        # 电铲目标产量
        # self.shovel_target_mass = (np.array(session_mysql.query(Excavator.target_mass).all())).flatten()
        self.shovel_target_mass = np.full(self.shovels, shovel_target_mass)


        ################################################################################################################
        # 计算挖机与卸载点预估产量
        ################################################################################################################
        self.pre_dump_real_mass = copy.deepcopy(self.cur_dump_real_mass)
        self.pre_shovel_real_mass = copy.deepcopy(self.cur_shovel_real_mass)
        for i in range(self.trucks):
            # task = self.truck_current_stage[i][0]
            task = self.truck_current_task[self.truck_index_to_uuid_dict[i]]
            end_area_index = self.truck_current_trip[i][1]
            # 若矿卡正常行驶，需要将该部分载重计入实时产量
            if task in empty_task_set or (task == -1 and state == 4):
                self.pre_shovel_real_mass[end_area_index] = self.pre_shovel_real_mass[end_area_index] + self.payload[i]
            elif task in heavy_task_set or (task == -1 and state == 5):
                self.pre_dump_real_mass[end_area_index] = self.pre_dump_real_mass[end_area_index] + self.payload[i]
            else:
                pass

        ################################################################################################################
        # 矿卡抵达时间
        ################################################################################################################

        now = (datetime.now() - self.start_time) / timedelta(hours=0, minutes=1, seconds=0)

        shovel_ava_ls = [[] for _ in range(self.shovels)]
        dump_ava_ls = [[] for _ in range(self.dumps)]
        for i in range(self.trucks):
            task = self.truck_current_task[self.truck_index_to_uuid_dict[i]]
            end_area_index = self.truck_current_trip[i][1]
            if task in empty_task_set:
                reach_time = self.cur_truck_reach_shovel[i]
                shovel_ava_ls[end_area_index].append([reach_time, i, end_area_index])
            elif task in heavy_task_set:
                reach_time = self.cur_truck_reach_dump[i]
                dump_ava_ls[end_area_index].append([reach_time, i, end_area_index])
            elif task == -2:
                self.cur_truck_ava_time[i] = (datetime.now() - self.start_time) / timedelta(hours=0, minutes=1,
                                                                                            seconds=0)
        ################################################################################################################
        # 挖机可用时间
        ################################################################################################################

        for reach_ls in shovel_ava_ls:
            if len(reach_ls) != 0:
                reach_ls = np.array(reach_ls)
                tmp = reach_ls[np.lexsort(reach_ls[:, ::-1].T)]
                for i in range(len(tmp)):
                    shovel_index = int(tmp[i][2])
                    self.cur_shovel_ava_time[shovel_index] = max(tmp[i][0], self.cur_shovel_ava_time[shovel_index]) + \
                                                             self.loading_time[shovel_index]
                    self.cur_truck_ava_time[int(tmp[i][1])] = self.cur_shovel_ava_time[shovel_index]

                    # 若挖机可用时间严重偏离，进行修正
                    if abs(self.cur_shovel_ava_time[shovel_index] - now) > 60:
                        self.cur_truck_ava_time[int(tmp[i][1])] = now
                    if abs(self.cur_shovel_ava_time[shovel_index] - now) > 60:
                        self.cur_shovel_ava_time[shovel_index] = now

        ################################################################################################################
        # 卸点可用时间
        ################################################################################################################
        # dump_index = 0
        for reach_ls in dump_ava_ls:
            if len(reach_ls) != 0:
                reach_ls = np.array(reach_ls)
                tmp = reach_ls[np.lexsort(reach_ls[:, ::-1].T)]
                for i in range(len(tmp)):
                    dump_index = int(tmp[i][2])
                    self.cur_dump_ava_time[dump_index] = max(tmp[i][0], self.cur_dump_ava_time[dump_index]) + \
                                                         self.unloading_time[dump_index]
                    self.cur_truck_ava_time[int(tmp[i][1])] = self.cur_dump_ava_time[dump_index]

                    # 若卸点可用时间严重偏离，进行修正
                    if abs(self.cur_dump_ava_time[dump_index] - now) > 60:
                        self.cur_dump_ava_time[dump_index] = now
                    if abs(self.cur_truck_ava_time[int(tmp[i][1])] - now) > 60:
                        self.cur_truck_ava_time[int(tmp[i][1])] = now
                # dump_index = dump_index + 1


        logger.info('f{周期更新结束}')

    def reset(self):

        # 卡车抵达时间重置
        self.sim_truck_reach_dump = copy.deepcopy(self.cur_truck_reach_dump)
        self.sim_truck_reach_shovel = copy.deepcopy(self.cur_truck_reach_shovel)

        # 设备可用时间重置
        self.sim_truck_ava_time = copy.deepcopy(self.cur_truck_ava_time)
        self.sim_shovel_ava_time = copy.deepcopy(self.cur_shovel_ava_time)
        self.sim_dump_ava_time = copy.deepcopy(self.cur_dump_ava_time)

        # 电铲\卸载点产量重置
        self.sim_dump_real_mass = copy.deepcopy(self.pre_dump_real_mass)
        self.sim_shovel_real_mass = copy.deepcopy(self.pre_shovel_real_mass)

    def truck_schedule_send_post(self, truck_id):

        truck_index = self.truck_uuid_to_index_dict[truck_id]

        trip = self.truck_current_trip[truck_index]

        task = self.truck_current_task[self.truck_index_to_uuid_dict[truck_index]]
        # state = self.truck_current_state[self.truck_index_to_uuid_dict[truck_index]]

        now = (datetime.now() - self.start_time) / timedelta(hours=0, minutes=1, seconds=0)

        logger.info(" ")
        logger.info(f'调度矿卡{truck_id}  {truck_uuid_to_name_dict[truck_id]}')
        #
        # print(f'矿卡可用时间：{truck_uuid_to_name_dict[truck_id]}')
        # print(self.sim_truck_ava_time[self.truck_uuid_to_index_dict[truck_id]])
        #
        # print(f'挖机可用时间：')
        # print(self.sim_shovel_ava_time)
        #
        # print(f'卸点可用时间：')
        # print(self.sim_dump_ava_time)

        target = 0

        if task == -2:
            # print("矿卡状态：矿卡启动或故障恢复")
            # print("矿卡行程：无")
            # print("涉及电铲：")
            # print(list(self.excavator_uuid_to_index_dict.keys()))
            # print("电铲饱和度：")
            # print(10 * (1 - self.sim_shovel_real_mass / self.shovel_target_mass))
            # print("行程时间：")
            # print((np.maximum(self.sim_shovel_ava_time,
            #                   now + self.park_to_load_eq[0, :]) + self.loading_time
            #        - now))
            # print("行驶时间：")
            # print(self.park_to_load_eq[0, :] + self.loading_time)

            logger.info("矿卡状态：矿卡启动或故障恢复")
            logger.info("矿卡行程：无")
            logger.info(f'涉及电铲：{list(self.excavator_uuid_to_index_dict.keys())}')
            logger.info(f'电铲饱和度：{(1 - self.sim_shovel_real_mass / self.shovel_target_mass)}')
            logger.info(f'行程时间：{(np.maximum(self.sim_shovel_ava_time, now + self.park_to_load_eq[0, :]) + self.loading_time - now)}')
            logger.info(f'行驶时间：{self.park_to_load_eq[0, :] + self.loading_time}')

            target = np.argmax(10 * (1 - self.sim_shovel_real_mass / self.shovel_target_mass) /
                               (np.maximum(self.sim_shovel_ava_time,
                                           now + self.park_to_load_eq[0, :]) + self.loading_time
                                - now))
            # print("目的地: ", self.excavator_index_to_uuid_dict[target])

            logger.info(f'目的地：{self.excavator_index_to_uuid_dict[target]}')
        if task in empty_task_set:
            # print("矿卡状态：矿卡空载")
            # print("矿卡行程：", self.dump_index_to_uuid_dict[trip[0]], self.excavator_index_to_uuid_dict[trip[1]])
            # print("涉及卸点：")
            # print(list(self.dump_uuid_to_index_dict.keys()))
            # print("卸点饱和度：")
            # print(10 * (1 - self.sim_dump_real_mass / self.dump_target_mass))
            # print("行程时间：")
            # print((np.maximum(self.sim_dump_ava_time,
            #                   # self.sim_truck_reach_shovel[truck_index] + self.loading_time[trip[1]]
            #                   self.sim_truck_ava_time[truck_index]
            #                   + self.go_time_eq[:, trip[1]]) + self.unloading_time
            #        - self.sim_truck_ava_time[truck_index]))
            # # print("卸载时间：")
            # # print(self.unloading_time)
            # print("行驶时间：")
            # print(self.go_time_eq[:, trip[1]] + self.unloading_time)

            logger.info("矿卡状态：矿卡空载")
            logger.info(f'矿卡行程：{self.dump_index_to_uuid_dict[trip[0]]}-{self.excavator_index_to_uuid_dict[trip[1]]}')
            logger.info(f'涉及卸点：{list(self.dump_uuid_to_index_dict.keys())}')
            logger.info(f'卸点饱和度：{(1 - self.sim_dump_real_mass / self.dump_target_mass)}')
            logger.info(f'行程时间：{(np.maximum(self.sim_dump_ava_time,self.sim_truck_ava_time[truck_index] + self.go_time_eq[:, trip[1]]) + self.unloading_time - self.sim_truck_ava_time[truck_index])}')
            logger.info(f'行驶时间：{self.go_time_eq[:, trip[1]] + self.unloading_time}')


            # 卡车空载，计算下一次卸载点
            # start_area_index = self.excavator_index_to_load_area_index_dict[trip[1]]
            target = np.argmax(10 * (1 - self.sim_dump_real_mass / self.dump_target_mass) /
                               (np.maximum(self.sim_dump_ava_time,
                                           # self.sim_truck_reach_shovel[truck_index] + self.loading_time[trip[1]]
                                           self.sim_truck_ava_time[truck_index]
                                           + self.go_time_eq[:, trip[1]]) + self.unloading_time
                                - self.sim_truck_ava_time[truck_index]))
            # print("目的地: ", self.dump_index_to_uuid_dict[target])

            logger.info(f'目的地：{self.dump_index_to_uuid_dict[target]}')

        elif task in heavy_task_set:
            # print("矿卡状态：矿卡重载")
            # print("矿卡行程：", self.excavator_index_to_uuid_dict[trip[0]], self.dump_index_to_uuid_dict[trip[1]])
            # print("涉及电铲：")
            # print(list(self.excavator_uuid_to_index_dict.keys()))
            # print("电铲饱和度：")
            # print(10 * (1 - self.sim_shovel_real_mass / self.shovel_target_mass))
            # print("装载时间：")
            # print(self.loading_time)
            # print("行程时间：")
            # print((np.maximum(self.sim_shovel_ava_time,
            #                   self.sim_truck_ava_time[truck_index]
            #                   + self.com_time_eq[trip[1], :]) + self.loading_time
            #        - self.sim_truck_ava_time[truck_index]))
            # print("行驶时间：")
            # print(self.com_time_eq[trip[1], :])

            logger.info("矿卡状态：矿卡重载")
            logger.info(f'矿卡行程：{self.excavator_index_to_uuid_dict[trip[0]]}-{self.dump_index_to_uuid_dict[trip[1]]}')
            logger.info(f'涉及卸点：{list(self.excavator_uuid_to_index_dict.keys())}')
            logger.info(f'卸点饱和度：{(1 - self.sim_shovel_real_mass / self.shovel_target_mass)}')
            logger.info(f'行程时间：{(np.maximum(self.sim_shovel_ava_time,self.sim_truck_ava_time[truck_index] + self.com_time_eq[trip[1], :]) + self.loading_time - self.sim_truck_ava_time[truck_index])}')
            logger.info(f'行驶时间：{self.com_time_eq[trip[1], :] + self.loading_time}')

            # 卡车重载，计算下一次装载点
            # start_area_index = self.dump_index_to_unload_area_index_dict[trip[1]]
            target = np.argmax(10 * (1 - self.sim_shovel_real_mass / self.shovel_target_mass) /
                               (np.maximum(self.sim_shovel_ava_time,
                                           self.sim_truck_ava_time[truck_index]
                                           + self.com_time_eq[trip[1], :]) + self.loading_time
                                - self.sim_truck_ava_time[truck_index]))

            # print("目的地: ", self.excavator_index_to_uuid_dict[target])
            logger.info(f'目的地：{self.excavator_index_to_uuid_dict[target]}')

        return target

    def solution_construct(self):

        # Seq初始化
        Seq = [[self.truck_current_trip[i][1], -1] for i in range(self.trucks)]

        # 根据矿卡最早可用时间顺序进行规划

        temp = copy.deepcopy(self.cur_truck_ava_time)

        for i in range(self.trucks):
            task = self.truck_current_task[self.truck_index_to_uuid_dict[i]]
            if task == -2:
                temp[i] = temp[i] + M

        index = np.argsort(temp.reshape(1, -1))
        index = index.flatten()

        for truck in index:
            if len(Seq[truck]) > 0:
                task = self.truck_current_task[self.truck_index_to_uuid_dict[truck]]
                state = self.truck_current_state[self.truck_index_to_uuid_dict[truck]]

                end_eq_index = self.truck_current_trip[truck][1]

                target_eq_index = self.truck_schedule_send_post(self.truck_index_to_uuid_dict[truck])

                Seq[truck][1] = target_eq_index

                if task in empty_task_set:
                    target_area_index = self.dump_index_to_unload_area_index_dict[target_eq_index]
                    end_area_index = self.excavator_index_to_load_area_index_dict[end_eq_index]
                    # 更新变量，预计产量更新
                    self.sim_dump_real_mass[target_eq_index] = self.sim_dump_real_mass[target_eq_index] + self.payload[
                        truck]
                    # 预计卸点可用时间更新
                    self.sim_dump_ava_time[target_eq_index] = (
                            max(
                                self.sim_dump_ava_time[target_eq_index],
                                self.sim_truck_ava_time[truck]
                                + self.go_time_area[target_area_index][end_area_index],
                            )
                            + self.unloading_time[target_eq_index]
                    )
                elif task in heavy_task_set or (task == -1 and state == 5):
                    target_area_index = self.excavator_index_to_load_area_index_dict[target_eq_index]
                    end_area_index = self.dump_index_to_unload_area_index_dict[end_eq_index]
                    # 更新变量，预计产量更新
                    self.sim_shovel_real_mass[target_eq_index] = self.sim_shovel_real_mass[target_eq_index] + \
                                                                 self.payload[
                                                                     truck]
                    # 预计装载点可用时间更新
                    self.sim_shovel_ava_time[target_eq_index] = (
                            max(
                                self.sim_shovel_ava_time[target_eq_index],
                                self.sim_truck_ava_time[truck]
                                + self.go_time_area[end_area_index][target_area_index],
                            )
                            + self.loading_time[target_eq_index]
                    )
                # elif task == -2 or state == 7:
                #     target_area_index = self.excavator_index_to_load_area_index_dict[target_eq_index]
                #     # 更新变量，预计产量更新
                #     self.sim_shovel_real_mass[target_eq_index] = self.sim_shovel_real_mass[target_eq_index] + \
                #                                                  self.payload[
                #                                                      truck]
                #     # 预计装载点可用时间更新
                #     self.sim_shovel_ava_time[target_eq_index] = (
                #             max(
                #                 self.sim_shovel_ava_time[target_eq_index],
                #                 self.sim_truck_ava_time[truck]
                #                 + self.park_to_load_area[0][target_area_index],
                #             )
                #             + self.loading_time[target_eq_index]
                #     )
                else:
                    pass

        for i in range(len(Seq)):
            record = {"truckId": self.truck_index_to_uuid_dict[i]}
            task = self.truck_current_task[self.truck_index_to_uuid_dict[i]]
            state = self.truck_current_state[self.truck_index_to_uuid_dict[i]]
            if task in empty_task_set:
                item = session_mysql.query(Dispatch).filter_by(
                    dump_id=self.dump_index_to_uuid_dict[Seq[i][1]], isauto=1, isdeleted=0).first()
                record["exactorId"] = item.exactor_id
                record["dumpId"] = item.dump_id
                record["loadAreaId"] = item.load_area_id
                record["unloadAreaId"] = item.unload_area_id
                record["dispatchId"] = item.id
                record["isdeleted"] = False
                record["creator"] = item.creator
                record["createtime"] = item.createtime.strftime('%b %d, %Y %#I:%#M:%#S %p')
            elif task in heavy_task_set:
                item = session_mysql.query(Dispatch).filter_by(
                    exactor_id=self.excavator_index_to_uuid_dict[Seq[i][1]], isauto=1, isdeleted=0).first()
                record["exactorId"] = self.excavator_index_to_uuid_dict[Seq[i][1]]
                record["dumpId"] = item.dump_id
                record["loadAreaId"] = item.load_area_id
                record["unloadAreaId"] = item.unload_area_id
                record["dispatchId"] = item.id
                record["isdeleted"] = False
                record["creator"] = item.creator
                record["createtime"] = item.createtime.strftime('%b %d, %Y %#I:%#M:%#S %p')
            elif task == -2:
                item = session_mysql.query(Dispatch).filter_by(
                    exactor_id=self.excavator_index_to_uuid_dict[Seq[i][1]], isauto=1, isdeleted=0).first()
                record["exactorId"] = item.exactor_id
                record["dumpId"] = item.dump_id
                record["loadAreaId"] = item.load_area_id
                record["unloadAreaId"] = item.unload_area_id
                record["dispatchId"] = item.id
                record["isdeleted"] = False
                record["creator"] = item.creator
                record["createtime"] = item.createtime.strftime('%b %d, %Y %#I:%#M:%#S %p')
            else:
                pass
                # json_value = json.loads(redis5.get(self.truck_index_to_uuid_dict[i]))
                #
                # if json_value is not None:
                #
                #     record["exactorId"] = json_value.get('exactorId')
                #     record["dumpId"] = json_value.get('dumpId')
                #     record["loadAreaId"] = json_value.get('loadAreaId')
                #     record["unloadAreaId"] = json_value.get('unloadAreaId')
                #     record["dispatchId"] = json_value.get('dispatchId')
                #     record["isdeleted"] = json_value.get('isdeleted')
                #     record["creator"] = json_value.get('creator')
                #     record["createtime"] = json_value.get('createtime')
                # else:
                #     item = session_mysql.query(Dispatch).filter_by(
                #         exactor_id=self.excavator_index_to_uuid_dict[Seq[i][1]], isauto=1, isdeleted=0).first()
                #     record["exactorId"] = item.exactor_id
                #     record["dumpId"] = item.dump_id
                #     record["loadAreaId"] = item.load_area_id
                #     record["unloadAreaId"] = item.unload_area_id
                #     record["dispatchId"] = item.id
                #     record["isdeleted"] = False
                #     record["creator"] = item.creator
                #     record["createtime"] = item.createtime.strftime('%b %d, %Y %#I:%#M:%#S %p')

            redis5.set(self.truck_index_to_uuid_dict[i], str(json.dumps(record)))

        for i in range(self.trucks):
            print("dispatch_setting:")
            print(redis5.get(self.truck_index_to_uuid_dict[i]))

        return Seq


def process(obj):
    session_mysql.commit()
    session_mysql.flush()

    obj.update()

    obj.reset()

    obj.solution_construct()


scheduler = sched.scheduler(time.time, time.sleep)


def perform(inc, obj):
    scheduler.enter(inc, 0, perform, (inc, obj))
    process(obj)


def main(inc, obj):
    scheduler.enter(0, 0, perform, (inc, obj))
    scheduler.run()


if __name__ == "__main__":

    logger.info(" ")
    logger.info("调度系统启动")

    obj = Dispatcher()

    main(60, obj)
