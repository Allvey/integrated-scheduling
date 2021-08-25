#!E:\Pycharm Projects\Waytous
# -*- coding: utf-8 -*-
# @Time : 2021/7/21 16:45
# @Author : Opfer
# @Site :
# @File : realtime_dispatch.py
# @Software: PyCharm

# 实时调度模块

from traffic_flow.traffic_flow_planner import *
from static_data_process import *
from para_config import *
from settings import *
from equipment.truck import TruckInfo
from equipment.excavator import ExcavatorInfo
from equipment.dump import DumpInfo

# 调度类
class Dispatcher(WalkManage):
    def __init__(self):
        # object fields
        self.dump = DumpInfo()
        self.excavator = ExcavatorInfo()
        self.truck = TruckInfo()
        # self.walker = WalkManage()

        # 模拟挖机/卸载设备产量(防止调度修改真实产量)
        self.sim_dump_real_mass = np.zeros(self.dump.get_dump_num())
        self.sim_excavator_real_mass = np.zeros(self.excavator.get_excavator_num())
        # 真实设备可用时间
        self.cur_truck_reach_dump = np.zeros(self.truck.get_truck_num())
        self.cur_truck_reach_excavator = np.zeros(self.truck.get_truck_num())
        self.cur_excavator_ava_time = np.zeros(self.excavator.get_excavator_num())
        self.cur_dump_ava_time = np.zeros(self.dump.get_dump_num())
        # 卡车完成装载及卸载时间(矿卡可用时间)
        self.cur_truck_ava_time = np.zeros(self.truck.get_truck_num())
        # 模拟矿卡可用时间
        self.sim_truck_ava_time = np.zeros(self.truck.get_truck_num())
        # 模拟各设备可用时间(防止调度修改真实产量)
        self.sim_excavator_ava_time = np.zeros(self.excavator.get_excavator_num())
        self.sim_dump_ava_time = np.zeros(self.dump.get_dump_num())
        # 挖机/卸载设备预计产量(包含正在驶往挖机/卸载设备那部分矿卡的载重)
        self.pre_dump_real_mass = np.zeros(self.dump.get_dump_num())
        self.pre_excavator_real_mass = np.zeros(self.excavator.get_excavator_num())

        # 维护一个矿卡调度表
        self.Seq = [[] for _ in range(self.truck.get_truck_num())]
        # 调度开始时间
        self.start_time = datetime.now()
        # self.relative_now_time = datetime.now() - self.start_time

        # 下面是交通流调度部分
        # 驶往挖机的实际车流
        self.actual_goto_excavator_traffic_flow = np.zeros(
            (self.dump.get_dump_num(), self.excavator.get_excavator_num())
        )
        # 驶往卸载设备的实际车流
        self.actual_goto_dump_traffic_flow = np.zeros(
            (self.dump.get_dump_num(), self.excavator.get_excavator_num())
        )

        # 驶往挖机的实际车次
        self.goto_dump_truck_num = np.zeros(
            (self.dump.get_dump_num(), self.excavator.get_excavator_num())
        )
        # 驶往卸载设备的实际车次
        self.goto_excavator_truck_num = np.zeros(
            (self.dump.get_dump_num(), self.excavator.get_excavator_num())
        )

        # 驶往挖机的理想车流
        self.opt_goto_dump_traffic_flow = np.zeros(
            (self.dump.get_dump_num(), self.excavator.get_excavator_num())
        )
        # 驶往卸载设备的实际车流
        self.opt_goto_excavator_traffic_flow = np.zeros(
            (self.dump.get_dump_num(), self.excavator.get_excavator_num())
        )

    # 更新矿卡预计抵达目的地时间
    def update_truck_reach_time(self):
        try:
            dynamic_excavator_num = self.excavator.get_excavator_num()
            dumps = self.dump.get_dump_num()
            trucks = self.truck.get_truck_num()

            truck_current_task = self.truck.get_truck_current_task()

            truck_current_trip = self.truck.get_truck_current_trip()

            cur_truck_reach_excavator = self.truck.get_truck_reach_excavator()

            cur_truck_reach_dump = self.truck.get_truck_reach_dump()

            excavator_ava_ls = [[] for _ in range(dynamic_excavator_num)]
            dump_ava_ls = [[] for _ in range(dumps)]
            for i in range(trucks):
                task = truck_current_task[self.truck_index_to_uuid_dict[i]]
                end_area_index = truck_current_trip[i][1]
                if task in [0, 1]:
                    reach_time = cur_truck_reach_excavator[i]
                    excavator_ava_ls[end_area_index].append(
                        [reach_time, i, end_area_index]
                    )
                elif task in [3, 4]:
                    reach_time = cur_truck_reach_dump[i]
                    dump_ava_ls[end_area_index].append([reach_time, i, end_area_index])
                elif task == -2:
                    self.cur_truck_ava_time[i] = (
                        datetime.now() - self.start_time
                    ) / timedelta(hours=0, minutes=1, seconds=0)

            print(self.truck_index_to_uuid_dict)
            print(excavator_ava_ls)
            print(dump_ava_ls)
        except Exception as es:
            logger.error("矿卡预计抵达时间计算异常")
            logger.error(es)

        return excavator_ava_ls, dump_ava_ls

    # 更新挖机预计可用时间
    def update_excavator_ava_time(self, excavator_ava_ls):

        # 初始化挖机可用时间
        self.cur_excavator_ava_time = np.full(
            dynamic_excavator_num,
            (datetime.now() - self.start_time)
            / timedelta(hours=0, minutes=1, seconds=0),
        )

        loading_time = self.excavator.get_loading_time()

        loading_task_time = self.excavator.get_loading_task_time()

        try:

            now = float(
                (datetime.now() - self.start_time)
                / timedelta(hours=0, minutes=1, seconds=0)
            )

            for reach_ls in excavator_ava_ls:
                if len(reach_ls) != 0:
                    reach_ls = np.array(reach_ls)
                    tmp = reach_ls[np.lexsort(reach_ls[:, ::-1].T)]
                    for i in range(len(tmp)):
                        excavator_index = int(tmp[i][2])
                        self.cur_excavator_ava_time[excavator_index] = (
                            max(tmp[i][0], self.cur_excavator_ava_time[excavator_index])
                            + loading_task_time[excavator_index]
                        )
                        self.cur_truck_ava_time[
                            int(tmp[i][1])
                        ] = self.cur_excavator_ava_time[excavator_index]

                        # # 若挖机可用时间严重偏离，进行修正
                        # if abs(self.cur_excavator_ava_time[excavator_index] - now) > 60:
                        #     self.cur_truck_ava_time[int(tmp[i][1])] = now
                        # if abs(self.cur_excavator_ava_time[excavator_index] - now) > 60:
                        #     self.cur_excavator_ava_time[excavator_index] = now
        except Exception as es:
            logger.error("挖机可用时间计算异常")
            logger.error(es)

    # 更新卸载设备预计可用时间
    def update_dump_ava_time(self, dump_ava_ls):

        dynamic_dump_num = self.dump.get_dump_num()

        # 初始化卸载设备可用时间
        self.cur_dump_ava_time = np.full(
            dynamic_dump_num,
            (datetime.now() - self.start_time)
            / timedelta(hours=0, minutes=1, seconds=0),
        )

        unloading_time = self.dump.get_unloading_time()

        unloading_task_time = self.dump.get_unloading_task_time()

        try:

            now = float(
                (datetime.now() - self.start_time)
                / timedelta(hours=0, minutes=1, seconds=0)
            )

            for reach_ls in dump_ava_ls:
                if len(reach_ls) != 0:
                    reach_ls = np.array(reach_ls)
                    tmp = reach_ls[np.lexsort(reach_ls[:, ::-1].T)]
                    for i in range(len(tmp)):
                        dump_index = int(tmp[i][2])
                        self.cur_dump_ava_time[dump_index] = (
                            max(tmp[i][0], self.cur_dump_ava_time[dump_index])
                            + unloading_task_time[dump_index]
                        )
                        self.cur_truck_ava_time[
                            int(tmp[i][1])
                        ] = self.cur_dump_ava_time[dump_index]

                        # # 若卸载设备可用时间严重偏离，进行修正
                        # if abs(self.cur_dump_ava_time[dump_index] - now) > 60:
                        #     self.cur_dump_ava_time[dump_index] = now
                        # if abs(self.cur_truck_ava_time[int(tmp[i][1])] - now) > 60:
                        #     self.cur_truck_ava_time[int(tmp[i][1])] = now
        except Exception as es:
            logger.error("卸载设备可用时间计算异常")
            logger.error(es)

    # 更新实际交通流
    def update_actual_traffic_flow(self):

        loading_time = self.excavator.get_loading_time()

        unloading_time = self.dump.get_unloading_time()

        loading_task_time = self.excavator.get_loading_task_time()

        unloading_task_time = self.dump.get_unloading_task_time()

        truck_current_task = self.truck.get_truck_current_task()
        truck_current_trip = self.truck.get_truck_current_trip()
        payload = self.truck.get_payload()

        dynamic_dump_num = self.dump.get_dump_num()
        dynamic_excavator_num = self.excavator.get_excavator_num()

        # for item in session_mysql.query(EquipmentPair).filter(EquipmentPair.createtime >= self.start_time).all():
        #     dump_index = self.dump_uuid_to_index_dict[item.dump_id]
        #     excavator_index = self.excavator_uuid_to_index_dict[item.exactor_id]
        #     task = truck_current_task[item.truck_id]
        #     if task in heavy_task_set:
        #         self.goto_dump_truck_num[dump_index][excavator_index] = \
        #             self.goto_dump_truck_num[dump_index][excavator_index] + 1
        #         self.actual_goto_dump_traffic_flow[dump_index][excavator_index] = \
        #             self.actual_goto_dump_traffic_flow[dump_index][excavator_index] + float(
        #                 payload[self.truck_uuid_to_index_dict[item.truck_id]])
        #     if task in empty_task_set or task == -2:
        #         self.goto_excavator_truck_num[dump_index][excavator_index] = \
        #             self.goto_excavator_truck_num[dump_index][excavator_index] + 1
        #         print(item.truck_id)
        #         self.actual_goto_excavator_traffic_flow[dump_index][excavator_index] = \
        #             self.actual_goto_excavator_traffic_flow[dump_index][excavator_index] + float(
        #                 payload[self.truck_uuid_to_index_dict[item.truck_id]])

        self.goto_dump_truck_num = np.zeros((dynamic_excavator_num, dynamic_dump_num))
        self.actual_goto_dump_traffic_flow = np.zeros(
            (dynamic_excavator_num, dynamic_dump_num)
        )
        self.goto_excavator_truck_num = np.zeros(
            (dynamic_dump_num, dynamic_excavator_num)
        )
        self.actual_goto_excavator_traffic_flow = np.zeros(
            (dynamic_dump_num, dynamic_excavator_num)
        )

        try:
            for i in range(dynamic_truck_num):
                task = truck_current_task[self.truck_index_to_uuid_dict[i]]
                end_area_index = truck_current_trip[i][1]
                start_area_index = truck_current_trip[i][0]

                # 若矿卡正常行驶，需要将该部分载重计入实时产量
                if task in heavy_task_set:
                    self.goto_dump_truck_num[end_area_index][start_area_index] = (
                        self.goto_dump_truck_num[end_area_index][start_area_index] + 1
                    )
                    self.actual_goto_dump_traffic_flow[end_area_index][
                        start_area_index
                    ] = self.actual_goto_dump_traffic_flow[end_area_index][
                        start_area_index
                    ] + float(
                        payload[i]
                    )
                if task in empty_task_set:
                    self.goto_excavator_truck_num[start_area_index][end_area_index] = (
                        self.goto_excavator_truck_num[start_area_index][end_area_index]
                        + 1
                    )
                    self.actual_goto_excavator_traffic_flow[start_area_index][
                        end_area_index
                    ] = self.actual_goto_excavator_traffic_flow[start_area_index][
                        end_area_index
                    ] + float(
                        payload[i]
                    )

            # print(np.expand_dims(unloading_time,axis=0).repeat(dynamic_excavator_num, axis=0))

            self.actual_goto_dump_traffic_flow = self.actual_goto_dump_traffic_flow / (
                self.distance_to_dump.reshape(dynamic_excavator_num, dynamic_dump_num)
                / (1000 * empty_speed)
                + np.expand_dims(unloading_task_time, axis=0).repeat(
                    dynamic_excavator_num, axis=0
                )
            )

        except Exception as es:
            logger.error("更新不及时")
            logger.error(es)

        # print("驶往卸点实际载重")
        # print(self.actual_goto_dump_traffic_flow)
        # print("卸点路段行驶时间(h)")
        # print((self.distance_to_dump.reshape(dynamic_excavator_num, dynamic_dump_num) / (1000 * empty_speed)))
        # print("驶往卸点实际车流")
        # print(self.actual_goto_dump_traffic_flow)

        logger.info("驶往卸点实际载重")
        logger.info(self.actual_goto_dump_traffic_flow)
        logger.info("卸点路段行驶时间(h)")
        logger.info(
            (
                self.distance_to_dump.reshape(dynamic_excavator_num, dynamic_dump_num)
                / (1000 * empty_speed)
            )
        )
        logger.info("驶往卸点实际车流")
        logger.info(self.actual_goto_dump_traffic_flow)

        self.actual_goto_excavator_traffic_flow = (
            self.actual_goto_excavator_traffic_flow
            / (
                self.distance_to_excavator.reshape(
                    dynamic_excavator_num, dynamic_dump_num
                )
                / (1000 * heavy_speed)
                + np.expand_dims(loading_task_time, axis=0).repeat(
                    dynamic_dump_num, axis=0
                )
            )
        )

        # print("驶往挖机实际载重")
        # print(self.actual_goto_excavator_traffic_flow)
        # print("挖机路段行驶时间(h)")
        # print((self.distance_to_excavator.reshape(dynamic_excavator_num, dynamic_dump_num) / (1000 * heavy_speed)))
        # print("驶往挖机实际车流")
        # print(self.actual_goto_excavator_traffic_flow)

        logger.info("驶往挖机实际载重")
        logger.info(self.actual_goto_excavator_traffic_flow)
        logger.info("挖机路段行驶时间(h)")
        logger.info(
            (
                self.distance_to_excavator.reshape(
                    dynamic_excavator_num, dynamic_dump_num
                )
                / (1000 * heavy_speed)
            )
        )
        logger.info("驶往挖机实际车流")
        logger.info(self.actual_goto_excavator_traffic_flow)

    # 更新卸载设备预计产量
    def update_pre_unload_throughout(self):

        truck_current_task = self.truck.get_truck_current_task()
        payload = self.truck.get_payload()

        try:
            self.pre_dump_real_mass = copy.deepcopy(self.dump.get_dump_actual_mass())
            for i in range(self.truck.get_truck_num()):
                # task = self.truck_current_stage[i][0]
                task = truck_current_task[self.truck_index_to_uuid_dict[i]]
                end_area_index = self.truck.get_truck_current_trip()[i][1]
                # 若矿卡正常行驶，需要将该部分载重计入实时产量
                if task in heavy_task_set:
                    self.pre_dump_real_mass[end_area_index] = (
                        self.pre_dump_real_mass[end_area_index] + payload[i]
                    )
                else:
                    pass
        except Exception as es:
            logger.error("卸载设备预计装载量计算异常")
            logger.error(es)

    # 更新挖机预计产量
    def update_pre_load_throughout(self):

        truck_current_task = self.truck.get_truck_current_task()
        payload = self.truck.get_payload()

        try:
            self.pre_excavator_real_mass = copy.deepcopy(
                self.excavator.get_excavator_actual_mass()
            )
            for i in range(self.truck.get_truck_num()):
                # task = self.truck_current_stage[i][0]
                task = truck_current_task[self.truck_index_to_uuid_dict[i]]
                end_area_index = self.truck.get_truck_current_trip()[i][1]
                # 若矿卡正常行驶，需要将该部分载重计入实时产量
                if task in empty_task_set:
                    self.pre_excavator_real_mass[end_area_index] = (
                        self.pre_excavator_real_mass[end_area_index] + payload[i]
                    )
                else:
                    pass
        except Exception as es:
            logger.error("挖机/卸载设备预计装载量计算异常")
            logger.error(es)

    def period_update(self):

        logger.info(
            "#####################################周期更新开始#####################################"
        )

        # 装载周期参数
        self.period_map_para_load()

        self.period_walk_para_load()

        # 更新卸载设备对象
        self.dump.period_update()

        # 更新挖机对象
        self.excavator.period_update()

        # 更新矿卡对象
        self.truck.period_update()

        # # 更新距离参量
        # self.walker.update_walk_time()

        # # 更新设备距离（不同于工作区距离）
        # self.update_walk_time()

        # 更新实时车流
        self.update_actual_traffic_flow()

        # 计算理想车流
        (
            self.opt_goto_dump_traffic_flow,
            self.opt_goto_excavator_traffic_flow,
        ) = traffic_flow_plan()

        # 矿卡抵达时间
        excavator_reach_list, dump_reach_list = self.update_truck_reach_time()

        # 挖机可用时间
        self.update_excavator_ava_time(excavator_reach_list)

        # 卸载设备可用时间
        self.update_dump_ava_time(dump_reach_list)

        # 挖机预计装载量
        self.update_pre_load_throughout()

        # 卸载设备预计卸载量
        self.update_pre_unload_throughout()

    def sim_para_reset(self):

        # 设备可用时间重置
        self.sim_truck_ava_time = copy.deepcopy(self.cur_truck_ava_time)
        self.sim_excavator_ava_time = copy.deepcopy(self.cur_excavator_ava_time)
        self.sim_dump_ava_time = copy.deepcopy(self.cur_dump_ava_time)

        # 挖机\卸载设备产量重置
        self.sim_dump_real_mass = copy.deepcopy(self.pre_dump_real_mass)
        self.sim_excavator_real_mass = copy.deepcopy(self.pre_excavator_real_mass)

    def truck_schedule(self, truck_id):

        # 矿卡对应序号
        truck_index = self.truck_uuid_to_index_dict[truck_id]
        # 矿卡行程
        trip = self.truck.get_truck_current_trip()[truck_index]
        # 矿卡当前任务
        task = self.truck.get_truck_current_task()[
            self.truck_index_to_uuid_dict[truck_index]
        ]
        # 挖机目标产量
        excavator_target_mass = self.excavator.get_excavator_target_mass()
        # 挖机装载时间
        loading_time = self.excavator.get_loading_time()
        # 卸载设备目标产量
        dump_target_mass = self.dump.get_dump_target_mass()
        # 卸载设备卸载时间
        unloading_time = self.dump.get_unloading_time()
        # 路网信息
        walk_time_park_to_excavator = walk_manage.get_walk_time_park_to_excavator()
        walk_time_to_dump = walk_manage.get_walk_time_to_dump()
        walk_time_to_excavator = walk_manage.get_walk_time_to_excavator()

        # 出入场时间
        loading_task_time = self.excavator.get_loading_task_time()
        unloading_task_time = self.dump.get_unloading_task_time()

        dynamic_dump_num = self.dump.get_dump_num()
        dynamic_excavator_num = self.excavator.get_excavator_num()

        now = float(
            (datetime.now() - self.start_time)
            / timedelta(hours=0, minutes=1, seconds=0)
        )

        # print()
        # print("调度矿卡：", truck_id, truck_uuid_to_name_dict[truck_id])
        logger.info(" ")
        logger.info(f"调度矿卡 {truck_id}  {truck_uuid_to_name_dict[truck_id]}")

        target = 0

        if task == -2:
            try:
                logger.info("矿卡状态：矿卡启动或故障恢复")
                logger.info("矿卡行程：无")
                logger.info(f"涉及挖机：{list(self.excavator_uuid_to_index_dict.keys())}")
                logger.info(
                    f"挖机饱和度：{(1 - self.sim_excavator_real_mass / excavator_target_mass)}"
                )
                logger.info(
                    f"行程时间：{(np.maximum(self.sim_excavator_ava_time, now + walk_time_park_to_excavator[0, :]) + loading_time - now)}"
                )
                logger.info(f"行驶时间：{walk_time_park_to_excavator[0, :] + loading_time}")
            except Exception as es:
                logger.error(f"矿卡{truck_id}状态不匹配")
                logger.error(es)

            if truck_id in self.truck.truck_excavator_bind:
                target = self.excavator_uuid_to_index_dict[
                    self.truck.truck_excavator_bind[truck_id]
                ]
            else:
                target = np.argmax(
                    (
                        10
                        * (1 - self.sim_excavator_real_mass / excavator_target_mass)
                        / (
                            np.maximum(
                                self.sim_excavator_ava_time,
                                now + walk_time_park_to_excavator[0, :],
                            )
                            + loading_task_time
                            - now
                        )
                    )
                    + self.truck.excavator_exclude_modify[
                        self.truck_uuid_to_index_dict[truck_id]
                    ]
                )

            # target = np.argmin((walk_time_park_to_excavator[0, :] + loading_time))
            logger.info(f"目的地：{self.excavator_index_to_uuid_dict[target]}")
            # print("目的地: ", self.excavator_index_to_uuid_dict[target])

        if task in [0, 1, 2]:
            try:
                logger.info("矿卡状态：矿卡空载")
                # logger.info(f'矿卡行程：{self.dump_index_to_uuid_dict[trip[0]]}-{self.excavator_index_to_uuid_dict[trip[1]]}')
                logger.info(f"涉及卸载设备：{list(self.dump_uuid_to_index_dict.keys())}")
                # logger.info(f'卸载设备饱和度：{(1 - self.sim_dump_real_mass / dump_target_mass)}')
                # logger.info(
                #     f'行程时间：{(np.maximum(self.sim_dump_ava_time, self.sim_truck_ava_time[truck_index] + walk_time_to_dump[:, trip[1]]) + unloading_time - self.sim_truck_ava_time[truck_index])}')
                # logger.info(f'行驶时间：{walk_time_to_dump[:, trip[1]] + unloading_time}')
            except Exception as es:
                logger.error(f"矿卡{truck_id}状态不匹配")
                logger.error(es)

            # # 卡车空载，计算下一次卸载设备
            # target = np.argmax(10 * (1 - self.sim_dump_real_mass / dump_target_mass) /
            #                    (np.maximum(self.sim_dump_ava_time,
            #                                # self.sim_truck_reach_excavator[truck_index] + self.loading_time[trip[1]]
            #                                self.sim_truck_ava_time[truck_index]
            #                                + walk_time_to_dump[:, trip[1]]) + unloading_time
            #                     - self.sim_truck_ava_time[truck_index]))

            try:
                assert np.array(self.actual_goto_dump_traffic_flow).shape == (
                    dynamic_excavator_num,
                    dynamic_dump_num,
                )
                assert np.array(self.opt_goto_dump_traffic_flow).shape == (
                    dynamic_excavator_num,
                    dynamic_dump_num,
                )
            except Exception as es:
                logger.warning(es)
                self.actual_goto_dump_traffic_flow = np.array(
                    self.actual_goto_dump_traffic_flow
                ).reshape((dynamic_excavator_num, dynamic_dump_num))
                self.opt_goto_dump_traffic_flow = np.array(
                    self.opt_goto_dump_traffic_flow
                ).reshape((dynamic_excavator_num, dynamic_dump_num))

            self.actual_goto_dump_traffic_flow = np.array(
                self.actual_goto_dump_traffic_flow
            )
            self.opt_goto_dump_traffic_flow = np.array(self.opt_goto_dump_traffic_flow)

            logger.info("挖机id:")
            logger.info(self.excavator_uuid_to_index_dict)
            logger.info("卸点id:")
            logger.info(self.dump_uuid_to_index_dict)
            logger.info(f"卸载点实际车流:")
            logger.info(self.actual_goto_dump_traffic_flow)
            logger.info(f"卸载点理想车流:")
            logger.info(self.opt_goto_dump_traffic_flow)

            logger.info("卸载点实际车流")
            logger.info(self.actual_goto_dump_traffic_flow[int(trip[1]), :])
            logger.info("卸载点理想车流")
            logger.info(self.opt_goto_dump_traffic_flow[int(trip[1]), :])

            if truck_id in self.truck.truck_dump_bind:
                bind_unload_area_id = self.truck.truck_dump_bind[truck_id]
                for key, value in self.dump_index_to_unload_area_index_dict.items():
                    if value == unload_area_uuid_to_index_dict[bind_unload_area_id]:
                        target = key
                        break
            else:
                target = np.argmin(
                    (self.actual_goto_dump_traffic_flow[int(trip[1]), :] + 0.001)
                    / (self.opt_goto_dump_traffic_flow[int(trip[1]), :] + 0.001)
                    - self.truck.excavator_exclude_modify[
                        self.truck_uuid_to_index_dict[truck_id]
                    ]
                )

            logger.info("车流比:")
            logger.info(
                (self.actual_goto_dump_traffic_flow[int(trip[1]), :] + 0.001)
                / (self.opt_goto_dump_traffic_flow[int(trip[1]), :] + 0.001)
            )

            logger.info(f"目的地：{self.dump_index_to_uuid_dict[target]}")

        elif task in [3, 4, 5]:

            try:

                logger.info("矿卡状态：矿卡重载")
                # logger.info(f'矿卡行程：{self.excavator_index_to_uuid_dict[trip[0]]}-{self.dump_index_to_uuid_dict[trip[1]]}')
                logger.info(f"涉及挖机设备：{list(self.excavator_uuid_to_index_dict.keys())}")
                # logger.info(f'卸载设备饱和度：{(1 - self.sim_excavator_real_mass / excavator_target_mass)}')
                # logger.info(
                #     f'行程时间：{(np.maximum(self.sim_excavator_ava_time, self.sim_truck_ava_time[truck_index] + walk_time_to_excavator[trip[1], :]) + loading_time - self.sim_truck_ava_time[truck_index])}')
                # logger.info(f'行驶时间：{walk_time_to_excavator[trip[1], :] + loading_time}')
            except Exception as es:
                logger.error(f"矿卡{truck_id}状态不匹配")
                logger.error(es)

            # # 卡车重载，计算下一次装载点
            # target = np.argmax(10 * (1 - self.sim_excavator_real_mass / excavator_target_mass) /
            #                    (np.maximum(self.sim_excavator_ava_time,
            #                                self.sim_truck_ava_time[truck_index]
            #                                + walk_time_to_excavator[trip[1], :]) + loading_time
            #                     - self.sim_truck_ava_time[truck_index]))

            try:
                assert np.array(self.actual_goto_excavator_traffic_flow).shape == (
                    dynamic_excavator_num,
                    dynamic_dump_num,
                )
                assert np.array(self.opt_goto_excavator_traffic_flow).shape == (
                    dynamic_excavator_num,
                    dynamic_dump_num,
                )
            except Exception as es:
                logger.warning(es)
                self.actual_goto_excavator_traffic_flow = np.array(
                    self.actual_goto_excavator_traffic_flow
                ).reshape((dynamic_dump_num, dynamic_excavator_num))
                self.opt_goto_excavator_traffic_flow = np.array(
                    self.opt_goto_excavator_traffic_flow
                ).reshape((dynamic_dump_num, dynamic_excavator_num))

            # 不知道为什么，偶尔变成了list
            self.actual_goto_excavator_traffic_flow = np.array(
                self.actual_goto_excavator_traffic_flow
            )
            self.opt_goto_excavator_traffic_flow = np.array(
                self.opt_goto_excavator_traffic_flow
            )

            logger.info("挖机id:")
            logger.info(self.excavator_uuid_to_index_dict)
            logger.info("卸点id:")
            logger.info(self.dump_uuid_to_index_dict)
            logger.info(f"挖机实际车流:")
            logger.info(self.actual_goto_excavator_traffic_flow)
            logger.info(f"挖机理想车流:")
            logger.info(self.opt_goto_excavator_traffic_flow)

            logger.info("挖机实际车流")
            logger.info(self.actual_goto_excavator_traffic_flow[trip[1], :])
            logger.info("挖机理想车流")
            logger.info(self.opt_goto_excavator_traffic_flow[trip[1], :])


            # check 矿卡是否有绑定的挖机，若有则执行派往绑定的挖机，若无则进行调度
            if truck_id in self.truck.truck_excavator_bind:
                target = self.excavator_uuid_to_index_dict[
                    self.truck.truck_excavator_bind[truck_id]
                ]
            else:
                target = np.argmin(
                    (self.actual_goto_excavator_traffic_flow[trip[1], :] + 0.001)
                    / (self.opt_goto_excavator_traffic_flow[trip[1], :] + 0.001)
                    - self.truck.excavator_exclude_modify[
                        self.truck_uuid_to_index_dict[truck_id]
                    ]
                )

            logger.info("车流比:")
            logger.info(
                (self.actual_goto_excavator_traffic_flow[trip[1], :] + 0.001)
                / (self.opt_goto_excavator_traffic_flow[trip[1], :] + 0.001)
            )

            logger.info(f"目的地：{self.excavator_index_to_uuid_dict[target]}")

        return target

    def schedule_construct(self):

        # try:

        # 读取所需信息
        trucks = self.truck.get_truck_num()
        truck_current_trip = self.truck.get_truck_current_trip()
        truck_current_task = self.truck.get_truck_current_task()
        payload = self.truck.get_payload()
        unloading_time = self.dump.get_unloading_time()
        loading_time = self.excavator.get_loading_time()

        # 出入场时间
        loading_task_time = self.excavator.get_loading_task_time()
        unloading_task_time = self.dump.get_unloading_task_time()

        walk_time_to_unload_area = walk_manage.get_walk_time_to_unload_area()
        walk_time_to_load_area = walk_manage.get_walk_time_to_load_area()

        # Seq初始化
        Seq = [[truck_current_trip[i][1], -1] for i in range(trucks)]

        # 根据矿卡最早可用时间顺序进行规划
        temp = copy.deepcopy(self.cur_truck_ava_time)

        # 没有启动的矿卡加上一个很大的值，降低其优先级
        for i in range(trucks):
            task = truck_current_task[self.truck_index_to_uuid_dict[i]]
            if task == -2:
                temp[i] = temp[i] + M

        index = np.argsort(temp.reshape(1, -1))
        index = index.flatten()

        # 对于在线矿卡已经赋予新的派车计划，更新其最早可用时间，及相关设备时间参数
        for truck in index:
            if len(Seq[truck]) > 0:

                # try:
                task = truck_current_task[self.truck_index_to_uuid_dict[truck]]

                # 矿卡结束当前派车计划后的目的地
                end_eq_index = truck_current_trip[truck][1]

                # 调用调度函数，得到最优目的地序号
                target_eq_index = self.truck_schedule(
                    self.truck_index_to_uuid_dict[truck]
                )

                # 写入Seq序列
                Seq[truck][1] = target_eq_index

                # except Exception as es:
                #     logger.error(f'矿卡 {truck_uuid_to_name_dict[self.truck_index_to_uuid_dict[truck]]} 派车计划计算异常')
                #     logger.error(es)

                try:

                    if task in empty_task_set:
                        target_area_index = self.dump_index_to_unload_area_index_dict[
                            target_eq_index
                        ]
                        end_area_index = self.excavator_index_to_load_area_index_dict[
                            end_eq_index
                        ]
                        # 更新变量，预计产量更新
                        self.sim_dump_real_mass[target_eq_index] = (
                            self.sim_dump_real_mass[target_eq_index] + payload[truck]
                        )
                        # 预计卸载设备可用时间更新
                        self.sim_dump_ava_time[target_eq_index] = (
                            max(
                                self.sim_dump_ava_time[target_eq_index],
                                self.sim_truck_ava_time[truck]
                                + walk_time_to_unload_area[target_area_index][
                                    end_area_index
                                ],
                            )
                            + unloading_task_time[target_eq_index]
                        )
                    elif task in heavy_task_set:
                        target_area_index = (
                            self.excavator_index_to_load_area_index_dict[
                                target_eq_index
                            ]
                        )
                        end_area_index = self.dump_index_to_unload_area_index_dict[
                            end_eq_index
                        ]
                        # 更新变量，预计产量更新
                        self.sim_excavator_real_mass[target_eq_index] = (
                            self.sim_excavator_real_mass[target_eq_index]
                            + payload[truck]
                        )
                        # 预计装载点可用时间更新
                        self.sim_excavator_ava_time[target_eq_index] = (
                            max(
                                self.sim_excavator_ava_time[target_eq_index],
                                self.sim_truck_ava_time[truck]
                                + walk_time_to_unload_area[end_area_index][
                                    target_area_index
                                ],
                            )
                            + loading_task_time[target_eq_index]
                        )
                    else:
                        pass
                except Exception as es:
                    logger.error(
                        f"矿卡 {truck_uuid_to_name_dict[self.truck_index_to_uuid_dict[truck]]} 调度状态更新异常"
                    )
                    logger.error(es)

        for i in range(len(Seq)):
            try:

                record = {"truckId": self.truck_index_to_uuid_dict[i]}
                task = self.truck.get_truck_current_task()[
                    self.truck_index_to_uuid_dict[i]
                ]
                if task in empty_task_set:
                    item = (
                        session_mysql.query(Dispatch)
                        .filter_by(
                            dump_id=self.dump_index_to_uuid_dict[Seq[i][1]],
                            isauto=1,
                            isdeleted=0,
                        )
                        .first()
                    )
                    record["exactorId"] = item.exactor_id
                    record["dumpId"] = item.dump_id
                    record["loadAreaId"] = item.load_area_id
                    record["unloadAreaId"] = item.unload_area_id
                    record["dispatchId"] = item.id
                    record["isdeleted"] = False
                    record["creator"] = item.creator
                    record["createtime"] = item.createtime.strftime(
                        "%b %d, %Y %#I:%#M:%#S %p"
                    )
                elif task in heavy_task_set:
                    item = (
                        session_mysql.query(Dispatch)
                        .filter_by(
                            exactor_id=self.excavator_index_to_uuid_dict[Seq[i][1]],
                            isauto=1,
                            isdeleted=0,
                        )
                        .first()
                    )
                    record["exactorId"] = self.excavator_index_to_uuid_dict[Seq[i][1]]
                    record["dumpId"] = item.dump_id
                    record["loadAreaId"] = item.load_area_id
                    record["unloadAreaId"] = item.unload_area_id
                    record["dispatchId"] = item.id
                    record["isdeleted"] = False
                    record["creator"] = item.creator
                    record["createtime"] = item.createtime.strftime(
                        "%b %d, %Y %#I:%#M:%#S %p"
                    )
                elif task == -2:
                    item = (
                        session_mysql.query(Dispatch)
                        .filter_by(
                            exactor_id=self.excavator_index_to_uuid_dict[Seq[i][1]],
                            isauto=1,
                            isdeleted=0,
                        )
                        .first()
                    )
                    record["exactorId"] = item.exactor_id
                    record["dumpId"] = item.dump_id
                    record["loadAreaId"] = item.load_area_id
                    record["unloadAreaId"] = item.unload_area_id
                    record["dispatchId"] = item.id
                    record["isdeleted"] = False
                    record["creator"] = item.creator
                    record["createtime"] = item.createtime.strftime(
                        "%b %d, %Y %#I:%#M:%#S %p"
                    )
                else:
                    pass

                redis5.set(self.truck_index_to_uuid_dict[i], str(json.dumps(record)))
            except Exception as es:
                logger.error("调度结果写入异常-redis写入异常")
                logger.error(f"调度结果:{Seq}")
                logger.error(es)

        for i in range(trucks):
            print("dispatch_setting:")
            print(redis5.get(self.truck_index_to_uuid_dict[i]))
        # except Exception as es:
        #     logger.error("更新不及时")
        #     logger.error(es)

        logger.info(
            "#####################################周期更新结束#####################################"
        )

        return Seq

    # material_type = True

    #
    # # 根据物料优先级生成新的影响调度的coast矩阵
    # def arrange_material_type (self, material_type):
    #     # 首先判断物料的种
    #     if material_type:
    #         cost =
    #         if :
    #                 logger.info(f'物料类型是土方')
    #         else：
    #                 logger.info(f'物料类型是煤方')













# 下面三个函数保证程序定期执行，不用管他
def process(dispatcher):

    # 更新周期参数
    period_para_update()

    # 清空数据库缓存
    session_mysql.commit()
    session_mysql.flush()

    # 周期更新
    dispatcher.period_update()

    # 参数重置
    dispatcher.sim_para_reset()

    # try:

    # 调度计算
    dispatcher.schedule_construct()

    # except Exception as es:
    #     logger.error("更新不及时")
    #     logger.error(es)


scheduler = sched.scheduler(time.time, time.sleep)


def perform(inc, dispatcher):
    scheduler.enter(inc, 0, perform, (inc, dispatcher))
    process(dispatcher)


def main(inc, dispatcher):
    scheduler.enter(0, 0, perform, (inc, dispatcher))
    scheduler.run()


if __name__ == "__main__":
    logger.info(" ")
    logger.info("调度系统启动")

    dispatcher = Dispatcher()
    main(10, dispatcher)
