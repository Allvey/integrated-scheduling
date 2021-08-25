#!E:\Pycharm Projects\Waytous
# -*- coding: utf-8 -*-
# @Time : 2021/8/24 11:28
# @Author : Opfer
# @Site :
# @File : truck.py    
# @Software: PyCharm

from traffic_flow.traffic_flow_planner import *
from static_data_process import *
from para_config import *
from settings import *

# 矿卡设备类
class TruckInfo(WalkManage):
    def __init__(self):
        # object fileds
        # self.walker = WalkManage()
        # 矿卡数量
        self.dynamic_truck_num = len(dynamic_truck_set)
        # 矿卡抵达卸载设备时间
        self.cur_truck_reach_dump = np.zeros(self.dynamic_truck_num)
        # 矿卡抵达挖机时间
        self.cur_truck_reach_excavator = np.zeros(self.dynamic_truck_num)
        # 用于动态派车的矿卡集合
        self.dynamic_truck_set = []
        # 矿卡最后装载/卸载时间
        self.last_load_time = {}
        self.last_unload_time = {}
        # 相对矿卡最后装载/卸载时间
        self.relative_last_load_time = {}
        self.relative_last_unload_time = {}
        # 矿卡当前任务
        self.truck_current_task = {}
        # 调度开始时间
        self.start_time = datetime.now()
        # # 卡车完成装载及卸载时间
        # self.cur_truck_ava_time = np.zeros(self.dynamic_truck_num)
        # self.sim_truck_ava_time = np.zeros(self.dynamic_truck_num)
        # 矿卡有效载重
        self.payload = np.zeros(self.dynamic_truck_num)
        # 矿卡当前行程(第一列为出发地序号, 第二列为目的地序号)
        self.truck_current_trip = np.full((self.dynamic_truck_num, 2), -1)
        # 矿卡挖机绑定关系
        self.truck_excavator_bind = {}
        # 矿卡卸点绑定关系
        self.truck_dump_bind = {}
        # 矿卡挖机排斥关系
        self.truck_excavator_exclude = {}
        # 矿卡卸点排斥关系
        self.truck_dump_exclude = {}
        # 排斥关系modify
        self.excavator_exclude_modify = None
        # 矿卡优先级

    # def period_map_para_load(self):
    #     # 关系映射
    #     self.excavator_uuid_to_index_dict = device_map.excavator_uuid_to_index_dict
    #     self.dump_uuid_to_index_dict = device_map.dump_uuid_to_index_dict
    #     self.excavator_index_to_uuid_dict = device_map.excavator_index_to_uuid_dict
    #     self.dump_index_to_uuid_dict = device_map.dump_index_to_uuid_dict
    #
    #     self.dump_uuid_to_unload_area_uuid_dict = device_map.dump_uuid_to_unload_area_uuid_dict
    #     self.excavator_uuid_to_load_area_uuid_dict = device_map.excavator_uuid_to_load_area_uuid_dict
    #     self.excavator_index_to_load_area_index_dict = device_map.excavator_index_to_load_area_index_dict
    #     self.dump_index_to_unload_area_index_dict = device_map.dump_index_to_unload_area_index_dict
    #
    #     self.truck_uuid_to_index_dict = device_map.truck_uuid_to_index_dict
    #     self.truck_index_to_uuid_dict = device_map.truck_index_to_uuid_dict

    # def period_walk_para_load(self):
    #
    #     self.walk_time_to_excavator = walk_manage.walk_time_to_excavator
    #     self.walk_time_to_dump = walk_manage.walk_time_to_dump
    #     self.walk_time_park_to_excavator = walk_manage.walk_time_park_to_excavator
    #     self.walk_time_to_load_area = walk_manage.walk_time_to_load_area
    #     self.walk_time_to_unload_area = walk_manage.walk_time_to_unload_area

    def get_truck_current_trip(self):
        return self.truck_current_trip

    def get_truck_current_task(self):
        return self.truck_current_task

    def get_truck_num(self):
        return self.dynamic_truck_num

    def get_truck_reach_dump(self):
        return self.cur_truck_reach_dump

    def get_truck_reach_excavator(self):
        return self.cur_truck_reach_excavator

    def get_dynamic_truck_set(self):
        return self.dynamic_truck_set

    def get_realative_last_load_time(self):
        return self.relative_last_load_time

    def get_realative_last_unload_time(self):
        return self.relative_unlast_load_time

    def get_payload(self):
        return self.payload

    # 更新矿卡当前任务
    def update_truck_current_task(self):
        self.truck_current_task = {}
        device_name_set = redis2.keys()

        # try:
        for item in device_name_set:
            try:
                item = item.decode(encoding="utf-8")
                json_value = json.loads(redis2.get(item))
                device_type = json_value.get("type")
                if device_type == 1:
                    if truck_name_to_uuid_dict[item] in self.dynamic_truck_set:
                        currentTask = json_value.get("currentTask")
                        self.truck_current_task[
                            truck_name_to_uuid_dict[item]
                        ] = currentTask
            except Exception as es:
                logger.error("读取矿卡任务异常-reids读取异常")
                logger.error(es)

        # except Exception as es:
        #     logger.error("读取矿卡任务异常-reids读取异常")
        #     logger.error(es)

        logger.info("矿卡当前任务：")
        logger.info(self.truck_current_task)

    # 更新矿卡实际容量
    def update_truck_payload(self):
        try:
            self.payload = np.zeros(self.dynamic_truck_num)
            for truck_id in self.dynamic_truck_set:
                trcuk_index = self.truck_uuid_to_index_dict[truck_id]
                truck_spec = (
                    session_mysql.query(Equipment)
                    .filter_by(id=truck_id)
                    .first()
                    .equipment_spec
                )
                # truck_spec = query.equipment_spec
                self.payload[trcuk_index] = (
                    session_mysql.query(EquipmentSpec)
                    .filter_by(id=truck_spec)
                    .first()
                    .capacity
                )
        except Exception as es:
            logger.error("读取矿卡有效载重异常-矿卡型号信息缺失")
            logger.error(es)

    # 更新矿卡最后装载/卸载时间
    def update_truck_last_leave_time(self):
        self.last_load_time = {}
        self.last_unload_time = {}

        self.relative_last_load_time = {}
        self.relative_last_unload_time = {}

        try:

            for item in self.dynamic_truck_set:
                json_value = json.loads(redis2.get(truck_uuid_to_name_dict[item]))
                device_type = json_value.get("type")
                # 判断是否为矿卡
                if device_type == 1:
                    task = self.truck_current_task[item]
                    if task in heavy_task_set:
                        last_load_time_tmp = json_value.get("lastLoadTime")
                        if last_load_time_tmp is not None:
                            self.last_load_time[item] = datetime.strptime(
                                last_load_time_tmp, "%b %d, %Y %I:%M:%S %p"
                            )
                        else:
                            self.last_load_time[item] = datetime.now()
                        self.relative_last_load_time[item] = float(
                            (self.last_load_time[item] - self.start_time)
                            / timedelta(hours=0, minutes=1, seconds=0)
                        )
                        # print("相对last_load_time", self.relative_last_load_time[item])
                        logger.info("相对last_load_time")
                        logger.info(self.relative_last_load_time[item])
                    if task in empty_task_set:
                        last_unload_time_tmp = json_value.get("lastUnloadTime")
                        if last_unload_time_tmp is not None:
                            self.last_unload_time[item] = datetime.strptime(
                                last_unload_time_tmp, "%b %d, %Y %I:%M:%S %p"
                            )
                        else:
                            self.last_unload_time[item] = datetime.now()
                            json_value["lastUnloadTime"] = datetime.now().strftime(
                                "%b %d, %Y %I:%M:%S %p"
                            )
                            redis2.set(
                                truck_uuid_to_name_dict[item],
                                str(json.dumps(json_value)),
                            )
                            logger.info("lastUnlaodTime is None")
                        self.relative_last_unload_time[item] = float(
                            (self.last_unload_time[item] - self.start_time)
                            / timedelta(hours=0, minutes=1, seconds=0)
                        )
                        # print("相对last_unload_time", self.relative_last_unload_time[item])
                        logger.info("相对last_unload_time")
                        logger.info(self.relative_last_unload_time[item])
                    elif task == -2:
                        self.last_unload_time[item] = datetime.now()
                        json_value["lastUnloadTime"] = datetime.now().strftime(
                            "%b %d, %Y %I:%M:%S %p"
                        )
                        redis2.set(
                            truck_uuid_to_name_dict[item], str(json.dumps(json_value))
                        )
        except Exception as es:
            logger.error("读取矿卡可用时间异常-redis读取异常")
            logger.error(es)

    # 更新矿卡行程
    def update_truck_trip(self):

        walk_time_to_load_area = walk_manage.get_walk_time_to_load_area()
        walk_time_to_unload_area = walk_manage.get_walk_time_to_unload_area()

        # 初始化矿卡行程, -1代表备停区
        self.truck_current_trip = np.full((self.dynamic_truck_num, 2), -1)
        for i in range(self.dynamic_truck_num):
            try:
                session_mysql.commit()
                truck_id = self.truck_index_to_uuid_dict[i]
                task = self.truck_current_task[self.truck_index_to_uuid_dict[i]]
                # print("truck_task:", truck_id, task)
                item = (
                    session_mysql.query(EquipmentPair)
                    .filter_by(truck_id=truck_id, isdeleted=0)
                    .first()
                )
                if task in empty_task_set + heavy_task_set and item is None:
                    raise Exception(f"矿卡 {truck_id} 配对关系异常")
            except Exception as es:
                logger.warning(es)

            try:
                # 若矿卡状态为空运
                if task in empty_task_set:
                    last_unload_time = self.relative_last_unload_time[
                        self.truck_index_to_uuid_dict[i]
                    ]
                    # 开始区域id
                    start_area_id = self.dump_uuid_to_unload_area_uuid_dict[
                        item.dump_id
                    ]
                    # 开始区域序号
                    start_area_index = unload_area_uuid_to_index_dict[start_area_id]
                    end_area_id = self.excavator_uuid_to_load_area_uuid_dict[
                        item.exactor_id
                    ]
                    end_area_index = load_area_uuid_to_index_dict[end_area_id]
                    self.truck_current_trip[i] = [
                        self.dump_uuid_to_index_dict[item.dump_id],
                        self.excavator_uuid_to_index_dict[item.exactor_id],
                    ]
                    # if truck_uuid_to_name_dict[self.truck_index_to_uuid_dict[i]] in tmp_set:
                    #     print("here")
                    #     self.cur_truck_reach_excavator[i] = last_unload_time + 10 * self.walk_time_to_load_area[start_area_index][
                    #         end_area_index]
                    # else:
                    self.cur_truck_reach_excavator[i] = (
                        last_unload_time
                        + walk_time_to_load_area[start_area_index][end_area_index]
                    )
                # 若矿卡状态为重载
                elif task in heavy_task_set:
                    # print("读取重载行程")
                    # print(item.exactor_id, item.dump_id)
                    last_load_time = self.relative_last_load_time[
                        self.truck_index_to_uuid_dict[i]
                    ]
                    # 开始区域id
                    start_area_id = self.excavator_uuid_to_load_area_uuid_dict[
                        item.exactor_id
                    ]
                    # 开始区域序号
                    start_area_index = load_area_uuid_to_index_dict[start_area_id]
                    # 结束区域id
                    end_area_id = self.dump_uuid_to_unload_area_uuid_dict[item.dump_id]
                    # 结束区域序号
                    end_area_index = unload_area_uuid_to_index_dict[end_area_id]
                    self.truck_current_trip[i] = [
                        self.excavator_uuid_to_index_dict[item.exactor_id],
                        self.dump_uuid_to_index_dict[item.dump_id],
                    ]
                    self.cur_truck_reach_dump[i] = (
                        last_load_time
                        + walk_time_to_unload_area[end_area_index][start_area_index]
                    )
                # 其他状态，矿卡状态为-2，equipment_pair表不存在该矿卡
                else:
                    pass
            except Exception as es:
                logger.error("矿卡行程读取异常")
                logger.error(es)

        self.truck_current_trip.flatten()
        # print("当前矿卡行程：")
        # print(self.truck_current_trip)

    def update_truck_dump_area_bind(self):
        try:

            self.truck_dump_bind = {}
            for dump_area in session_postgre.query(DumpArea).all():
                if dump_area.BindList is not None:
                    for truck_name in dump_area.BindList:
                        self.truck_dump_bind[truck_name_to_uuid_dict[truck_name]] = str(
                            dump_area.Id
                        )
        except Exception as es:
            logger.error("矿卡-卸载区域绑定关系读取异常")
            logger.error(es)

    def update_truck_excavator_bind(self):
        try:
            self.truck_excavator_bind = {}
            for excavator_id in dynamic_excavator_set:
                item = session_mysql.query(Equipment).filter_by(id=excavator_id).first()
                if item.bind_list is not None:
                    for truck_name in json.loads(item.bind_list):
                        self.truck_excavator_bind[
                            truck_name_to_uuid_dict[truck_name]
                        ] = excavator_id
        except Exception as es:
            logger.error("矿卡-挖机绑定关系读取异常")
            logger.error(es)

    def update_truck_excavator_exclude(self):

        self.truck_excavator_exclude = {}

        self.excavator_exclude_modify = np.full(
            (dynamic_truck_num, dynamic_excavator_num), 0
        )

        try:
            for excavator_id in dynamic_excavator_set:
                item = (
                    session_mysql.query(Equipment)
                    .filter_by(id=excavator_id, only_allowed=1)
                    .first()
                )
                if item is not None:
                    for truck_id in dynamic_truck_set:
                        if truck_uuid_to_name_dict[truck_id] not in item.bind_list:
                            self.truck_excavator_exclude[truck_id] = excavator_id
                            self.excavator_exclude_modify[
                                self.truck_uuid_to_index_dict[truck_id]
                            ][
                                self.excavator_uuid_to_index_dict[excavator_id]
                            ] = -1000000
        except Exception as es:
            logger.error("矿卡-挖机禁止关系读取异常")
            logger.error(es)

    def update_truck_dump_exclude(self):

        pass

    def period_update(self):

        print("Truck update!")

        # # 更新行走队形
        # self.walker.update_walk_time()

        # 装载周期参数
        self.period_map_para_load()

        self.period_walk_para_load()

        # 更新全部矿卡设备集合
        truck_set = set(update_total_truck())

        # 更新固定派车矿卡集合
        fixed_truck_set = set(update_fixdisp_truck())

        # 更新动态派车矿卡集合
        self.dynamic_truck_set = truck_set.difference(fixed_truck_set)

        # 更新矿卡数量
        self.dynamic_truck_num = len(self.dynamic_truck_set)

        # 更新卡车当前任务
        self.update_truck_current_task()

        # 更新有效载重
        self.update_truck_payload()

        # 更新卡车最后一次装载/卸载时间
        self.update_truck_last_leave_time()

        # 更新卡车当前行程
        self.update_truck_trip()

        # 更新绑定关系
        self.update_truck_dump_area_bind()

        self.update_truck_excavator_bind()

        self.update_truck_excavator_exclude()
