#!E:\Pycharm Projects\Waytous
# -*- coding: utf-8 -*-
# @Time : 2021/8/24 11:28
# @Author : Opfer
# @Site :
# @File : dump.py    
# @Software: PyCharm

from traffic_flow.traffic_flow_planner import *
from static_data_process import *
from para_config import *
from settings import *

# 卸载设备类
class DumpInfo(WalkManage):
    def __init__(self):
        # 卸载设备数量
        self.dynamic_dump_num = len(dynamic_dump_set)
        # 目标产量
        self.dump_target_mass = np.zeros(self.dynamic_dump_num)
        # 实际真实产量
        self.cur_dump_real_mass = np.zeros(self.dynamic_dump_num)
        # # 预计产量（包含正在驶往目的地的矿卡载重）
        # self.pre_dump_real_mass = copy.deepcopy(self.cur_dump_real_mass)
        # # 模拟实际产量（防止调度修改真实产量）
        # self.sim_dump_real_mass = np.zeros(self.dynamic_dump_num)
        # # 真实设备可用时间
        # self.cur_dump_ava_time = np.zeros(self.dynamic_dump_num)
        # # 模拟各设备可用时间（防止调度修改真实产量）
        # self.sim_dump_ava_time = np.zeros(self.dynamic_dump_num)
        # 用于动态调度的卸载设备集合
        self.dynamic_dump_set = []
        # 开始时间
        self.start_time = datetime.now()
        # 卸载时间
        self.unloading_time = np.zeros(self.dynamic_dump_num)
        # 入场时间
        self.entrance_time = np.zeros(self.dynamic_dump_num)
        # 出场时间
        self.exit_time = np.zeros(self.dynamic_dump_num)

    def get_unloading_time(self):
        return self.unloading_time

    def get_dump_num(self):
        return self.dynamic_dump_num

    def get_dump_target_mass(self):
        return self.dump_target_mass

    def get_dump_actual_mass(self):
        return self.cur_dump_real_mass

    def get_dynamic_dump_set(self):
        return self.dynamic_dump_set

    # 更新卸载设备卸载时间
    def update_dump_unloadtime(self):
        self.unloading_time = np.zeros(self.dynamic_dump_num)

        for dump_id in self.dump_uuid_to_index_dict.keys():
            ave_unload_time = 0
            unload_count = 0
            try:
                for query in (
                    session_mysql.query(JobRecord.start_time, JobRecord.end_time)
                    .join(Equipment, JobRecord.equipment_id == Equipment.equipment_id)
                    .filter(Equipment.id == dump_id, JobRecord.end_time != None)
                    .order_by(JobRecord.start_time.desc())
                    .limit(10)
                ):
                    ave_unload_time = ave_unload_time + float(
                        (query.end_time - query.start_time)
                        / timedelta(hours=0, minutes=1, seconds=0)
                    )
                    unload_count = unload_count + 1
                self.unloading_time[self.dump_uuid_to_index_dict[dump_id]] = (
                    ave_unload_time / unload_count
                )
            except Exception as es:
                logger.error(f"卸载设备 {dump_id} 卸载时间信息缺失, 已设为默认值(1min)")
                logger.error(es)
                self.unloading_time[self.dump_uuid_to_index_dict[dump_id]] = 5.00
        # print("average_unload_time: ", self.unloading_time[self.dump_uuid_to_index_dict[dump_id]])

    # 更新卸载设备出入时间
    def update_dump_entrance_exit_time(self):
        self.entrance_time = np.zeros(self.dynamic_dump_num)
        self.exit_time = np.zeros(self.dynamic_dump_num)
        now = datetime.now().strftime("%Y-%m-%d")

        for dump_id in self.dump_uuid_to_index_dict.keys():
            try:
                for query in (
                    session_mysql.query(WorkRecord)
                    .filter(
                        WorkRecord.equipment_id == dump_id, WorkRecord.work_day > now
                    )
                    .first()
                ):
                    self.entrance_time[self.dump_uuid_to_index_dict[dump_id]] = float(
                        query.load_entrance_time / query.load_entrance_count
                    )
                    self.exit_time[self.dump_uuid_to_index_dict[dump_id]] = float(
                        query.exit_entrance_time / query.exit_entrance_count
                    )
            except Exception as es:
                logger.error(f"卸载设备 {dump_id} 出入场时间信息缺失, 已设为默认值(1min)")
                logger.error(es)
                self.entrance_time[self.dump_uuid_to_index_dict[dump_id]] = 0.50
                self.exit_time[self.dump_uuid_to_index_dict[dump_id]] = 0.50

    # 读取出入场时间
    def get_unloading_task_time(self):
        unloading_time = self.unloading_time

        dump_entrance_time = self.entrance_time

        dump_exit_time = self.exit_time

        unloading_task_time = unloading_time + dump_entrance_time + dump_exit_time

        return unloading_task_time

    # 更新卸载设备实际卸载量
    def update_actual_unload_thoughout(self):
        self.cur_dump_real_mass = np.zeros(self.dynamic_dump_num)
        now = datetime.now().strftime("%Y-%m-%d")
        for dump_id in self.dump_uuid_to_index_dict.keys():
            for query in (
                session_mysql.query(LoadInfo)
                .join(Equipment, LoadInfo.dump_id == Equipment.equipment_id)
                .filter(Equipment.id == dump_id, LoadInfo.time > now)
                .order_by(LoadInfo.time.desc())
                .all()
            ):
                # print("time:", query.time)
                # print("load_weight:", )
                self.cur_dump_real_mass[self.dump_uuid_to_index_dict[dump_id]] = (
                    self.cur_dump_real_mass[self.dump_uuid_to_index_dict[dump_id]]
                    + query.load_weight
                )

    def period_update(self):

        print("Dump update!")

        # 装载周期参数
        self.period_map_para_load()

        self.period_walk_para_load()

        # # 初始化卸载设备可用时间
        # self.cur_dump_ava_time = np.full(self.dynamic_dump_num,
        #                                    (datetime.now() - self.start_time) / timedelta(hours=0, minutes=1,
        #                                                                                   seconds=0))

        # 用于动态调度的卸载设备
        self.dynamic_dump_set = set(update_autodisp_dump())

        self.dynamic_dump_num = len(self.dynamic_dump_set)

        # 计算平均卸载时间
        self.update_dump_unloadtime()

        # 计算实时卸载量
        self.update_actual_unload_thoughout()

        # 卸载目标产量
        self.dump_target_mass = np.full(self.dynamic_dump_num, dump_target_mass)

        # # 同步虚拟卸载量
        # self.sim_dump_real_mass = copy.deepcopy(self.cur_dump_real_mass)

        # # 计算卸载设备预估产量
        # self.update_pre_unload_throughout()