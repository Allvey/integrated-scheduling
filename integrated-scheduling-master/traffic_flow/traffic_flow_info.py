#!E:\Pycharm Projects\Waytous
# -*- coding: utf-8 -*-
# @Time : 2021/8/3 10:41
# @Author : Opfer
# @Site :
# @File : traffic_flow_info.py
# @Software: PyCharm

# import

from static_data_process import *
from settings import *
from path_plan.path_plannner import *
from para_config import *
from traffic_flow.traffic_flow_planner import *
from static_data_process import *
from para_config import *
from settings import *
from equipment.truck import TruckInfo
from equipment.excavator import ExcavatorInfo
from equipment.dump import DumpInfo

# 车流规划类
class Traffic_para(WalkManage):
    def __init__(self, num_of_load_area, num_of_unload_area, num_of_excavator, num_of_dump):
        # self.load_area_uuid_to_index_dict = {}  # 用于保存装载点uuid到id的映射
        # self.load_area_index_to_uuid_dict = {}  # 用于保存装载点id到uuid的映射
        # self.unload_area_uuid_to_index_dict = {}  # 用于保存卸载点uuid到id的映射
        # self.unload_area_index_to_uuid_dict = {}  # 用于保存卸载点id到uuid的映射
        #
        # self.excavator_uuid_to_index_dict = {}  # 用于保存挖机uuid到id的映射
        # self.excavator_index_to_uuid_dict = {}  # 用于保存挖机id到uuid的映射
        # self.dump_uuid_to_index_dict = {}  # 用于保存卸点uuid到id的映射
        # self.dump_index_to_uuid_dict = {}  # 用于保存卸点id到uuid的映射
        #
        # self.dump_uuid_to_unload_area_uuid_dict = {}  # 用于保存卸点与卸载区的绑定关系(uuid)
        # self.excavator_uuid_to_load_area_uuid_dict = {}  # 用于保存挖机与装载区的绑定关系(uuid)
        # self.dump_index_to_unload_area_index_dict = {}  # 用于保存卸点与卸载区的绑定关系(id)
        # self.excavator_index_to_load_area_index_dict = {}  # 用于保存挖机与装载区的绑定关系(id)


        self.empty_speed = 25  # 空载矿卡平均时速
        self.heavy_speed = 22  # 重载矿卡平均时速
        self.walk_time_to_load_area = np.zeros((num_of_unload_area, num_of_load_area))  # 空载运输路线距离
        self.walk_time_to_unload_area = np.zeros((num_of_load_area, num_of_unload_area))  # 重载运输路线距离

        # self.avg_goto_excavator_weight = np.zeros((num_of_load_area, num_of_unload_area))
        self.avg_goto_excavator_weight = np.full((num_of_unload_area, num_of_load_area), 1)

        # self.avg_goto_dump_weight = np.zeros((num_of_load_area, num_of_unload_area))
        self.avg_goto_dump_weight = np.full((num_of_load_area, num_of_unload_area), 1)
        self.walk_time_to_excavator = np.zeros((num_of_dump, num_of_excavator))  # 逻辑空载运输路线距离
        self.walk_time_to_dump = np.zeros((num_of_excavator, num_of_dump))  # 逻辑重载运输路线距离
        self.payload = 20  # 有效载重(不同型号矿卡载重不同，这里暂时认为车队是同质的)
        self.min_throughout = 200  # 最小产量约束
        self.truck_total_num = 0

        self.excavator_strength = np.zeros(num_of_excavator)  # 用于保存电铲的工作强度,单位是t/h
        self.dump_strength = np.zeros(num_of_dump)  # 卸载点的工作强度，单位是t/h

        self.path_planner = PathPlanner()
        self.path_planner.walk_cost()


        '''
        以下参数暂时没用到
        '''
        self.excavator_priority_coefficient = np.zeros(num_of_excavator)  # 每个电铲的优先级系数
        self.grade_loading_array = np.zeros(num_of_excavator)  # 用于保存电铲挖掘矿石的品位
        self.dump_priority_coefficient = np.zeros(num_of_dump)  # 每个卸载点的优先级系数
        # 卸载道路的运输系数：卸载道路上，每运输1吨货物需要一辆卡车运行时长,等于（该卸载道路上车辆平均运行时长/卡车平均实际装载量）
        self.goto_unload_area_factor = np.full((num_of_load_area, num_of_unload_area), 10, dtype=float)
        # 装载道路的运输系数，装载道路上，每提供1吨的装载能力需要一辆卡车运行时长,等于（该装载道路上车辆平均运行时长/卡车平均装载能力）
        self.goto_load_area_factor = np.full((num_of_unload_area, num_of_load_area), 10, dtype=float)
        self.goto_dump_factor = np.full((num_of_excavator, num_of_dump), 10, dtype=float) # 逻辑卸载道路的运输系数
        self.goto_excavator_factor = np.full((num_of_dump, num_of_excavator), 10, dtype=float)  # 逻辑装载道路的运输系数
        self.priority_coefficient = np.zeros((num_of_excavator, num_of_dump))  # 卸载道路的优先级系数
        self.grade_lower_dump_array = np.zeros(num_of_dump)  # 卸载点矿石品位下限
        self.grade_upper_dump_array = np.zeros(num_of_dump)  # 卸载点矿石品位上限

        # 装/卸区的物料类型
        self.load_area_material_type = {}
        self.unload_area_material_type = {}

    # # 提取卸载点信息并建立映射
    # def extract_dump_info(self):
    #     dump_index = 0
    #     for dispatch in session_mysql.query(Dispatch).filter_by(isdeleted=0, isauto=1).all():
    #         unload_area_id = dispatch.unload_area_id
    #         dump_id = dispatch.dump_id
    #         if dump_id not in self.dump_uuid_to_unload_area_uuid_dict:
    #             # dump_uuid <-> dump_id
    #             self.dump_uuid_to_index_dict[dump_id] = dump_index
    #             self.dump_index_to_uuid_dict[dump_index] = dump_id
    #             # dump_uuid -> unload_area_uuid
    #             self.dump_uuid_to_unload_area_uuid_dict[dump_id] = unload_area_id
    #             # dump_id -> unload_area_id
    #             self.dump_index_to_unload_area_index_dict[
    #                 self.dump_uuid_to_index_dict[dump_id]] = \
    #                 unload_area_uuid_to_index_dict[unload_area_id]
    #
    #             self.dump_strength[dump_index] = 300  # 卸载设备最大卸载能力，单位吨/小时
    #             self.grade_upper_dump_array[dump_index] = 100  # 卸点品位上限
    #             self.grade_lower_dump_array[dump_index] = 100  # 卸点品位下限
    #             self.dump_priority_coefficient[dump_index] = 1  # 卸载设备优先级
    #             dump_index += 1

    # 设置卸载点信息
    def extract_dump_info(self):
        try:
            for dump_index in range(dynamic_excavator_num):
                unload_area_id = unload_area_index_to_uuid_dict[self.dump_index_to_unload_area_index_dict[dump_index]]

                unload_ability = session_postgre.query(DumpArea).filter_by(Id=unload_area_id).first().UnloadAbililty
                self.dump_strength[dump_index] = unload_ability # 卸载设备最大卸载能力，单位吨/小时

                # self.dump_strength[dump_index] = 10000  # 卸载设备最大卸载能力，单位吨/小时
                self.grade_upper_dump_array[dump_index] = 100  # 卸点品位上限
                self.grade_lower_dump_array[dump_index] = 100  # 卸点品位下限
                self.dump_priority_coefficient[dump_index] = 1  # 卸载设备优先级
        except Exception as es:
            logger.error(es)
            logger.error("卸载点信息设置异常")

    # # 提取挖机信息并建立映射
    # def extract_excavator_info(self):
    #     try:
    #         excavator_index = 0
    #         for dispatch in session_mysql.query(Dispatch).filter_by(isdeleted=0, isauto=1).all():
    #             excavator_id = dispatch.exactor_id
    #             load_area_id = dispatch.load_area_id
    #             if excavator_id not in self.excavator_uuid_to_index_dict:
    #                 # excavator_uuid <-> excavator_uuid
    #                 self.excavator_uuid_to_index_dict[excavator_id] = excavator_index
    #                 self.excavator_index_to_uuid_dict[excavator_index] = excavator_id
    #                 # excavator_uuid -> load_area_uuid
    #                 self.excavator_uuid_to_load_area_uuid_dict[excavator_id] = load_area_id
    #                 # excavator_id -> load_area_id
    #                 self.excavator_index_to_load_area_index_dict[
    #                     self.excavator_uuid_to_index_dict[excavator_id]] = \
    #                     load_area_uuid_to_index_dict[load_area_id]
    #
    #                 self.excavator_strength[excavator_index] = 300  # 挖机最大装载能力，单位吨/小时
    #                 self.grade_loading_array[excavator_index] = 100  # 挖机装载物料品位
    #                 self.excavator_priority_coefficient[excavator_index] = 1  # 挖机优先级
    #                 excavator_index += 1
    #     except Exception as es:
    #         logger.error("车流规划读取挖机信息异常")

    # 设置挖信息
    def extract_excavator_info(self):
        try:
            for excavator_index in range(len(self.excavator_index_to_uuid_dict)):
                load_ability = session_mysql.query(EquipmentSpec.mining_abililty).\
                    join(Equipment, Equipment.equipment_spec == EquipmentSpec.id).\
                    filter(Equipment.id == self.excavator_index_to_uuid_dict[excavator_index]).first()
                self.excavator_strength[excavator_index] = load_ability.mining_abililty
                # self.excavator_strength[excavator_index] = 1000  # 挖机最大装载能力，单位吨/小时
                self.grade_loading_array[excavator_index] = 100  # 挖机装载物料品位
                self.excavator_priority_coefficient[excavator_index] = 1  # 挖机优先级
        except Exception as es:
            logger.error(es)
            logger.error("挖机信息设置异常")

    # def extract_walk_time_info(self):
    #     # load_area_uuid <-> load_area_id
    #     # unload_area_uuid <-> unload_area_id
    #     load_area_index = 0
    #     unload_area_index = 0
    #     for walk_time in session_postgre.query(WalkTime).all():
    #
    #         load_area_id = str(walk_time.load_area_id)
    #         unload_area_id = str(walk_time.unload_area_id)
    #
    #         if load_area_id not in load_area_uuid_to_index_dict:
    #             load_area_uuid_to_index_dict[load_area_id] = load_area_index
    #             load_area_index_to_uuid_dict[load_area_index] = load_area_id
    #             load_area_index += 1
    #         if unload_area_id not in unload_area_uuid_to_index_dict:
    #             unload_area_uuid_to_index_dict[unload_area_id] = unload_area_index
    #             unload_area_index_to_uuid_dict[unload_area_index] = unload_area_id
    #             unload_area_index += 1



    # 根据物料优先级生成新的影响调度的coast矩阵
    # def arrange_material_type (self, material_type):
    #
    #     # 首先判断物料的种
    #     # if material_type:
    #     #     logger.info(f'物料类型是土方')
    #     # else：
    #     #     logger.info(f'物料类型是煤方')

    include_material_type = True

    def extract_walk_time_info(self, include_material_type):

        try:
            # 车流规划部分矩阵格式与其余两个模块不同
            cost_to_load_area = self.path_planner.cost_to_load_area
            cost_to_unload_area = self.path_planner.cost_to_unload_area

            distance_to_load_area = self.path_planner.distance_to_load_area
            distance_to_unload_area = self.path_planner.distance_to_unload_area

            self.load_area_material_type = {}
            self.unload_area_material_type = {}
            for item in session_postgre.query(DiggingWorkArea).all():
                if item.Material is not None:
                    self.load_area_material_type[load_area_uuid_to_index_dict[item.Id]] = item.Material

            for item in session_postgre.query(DumpArea).all():
                if item.Material is not None:
                    self.unload_area_material_type[unload_area_uuid_to_index_dict[item.Id]] = item.Material

            # 路网信息读取
            for unload_area_index in range(unload_area_num):
                for load_area_index in range(load_area_num):
                    # 是否考虑cost
                    if include_material_type == True:
                        logger.info(f'考虑物料类型')
                        if self.unload_area_material_type[unload_area_index] == 'c481794b-6ced-45b9-a9c4-c4a388f44418' \
                                    and self.load_area_material_type[load_area_index] == 'c481794b-6ced-45b9-a9c4-c4a388f44418':

                                self.goto_load_area_factor[unload_area_index][load_area_index] = \
                                    0.75*(cost_to_load_area[unload_area_index][load_area_index] / (empty_speed * 1000)) / self.payload

                                self.goto_unload_area_factor[load_area_index][unload_area_index] = \
                                    0.75*(cost_to_unload_area[unload_area_index][load_area_index] / (heavy_speed * 1000)) /  self.payload
                        else:
                                self.goto_load_area_factor[unload_area_index][load_area_index] = \
                                    (cost_to_load_area[unload_area_index][load_area_index] / (empty_speed * 1000)) / self.payload

                                self.goto_unload_area_factor[load_area_index][unload_area_index] = \
                                    (cost_to_unload_area[unload_area_index][load_area_index] / (heavy_speed * 1000)) /  self.payload
                    # 不考虑物料类型的cost
                    else:
                        self.goto_load_area_factor[unload_area_index][load_area_index] = \
                            (cost_to_load_area[unload_area_index][load_area_index] / (empty_speed * 1000)) / self.payload

                        self.goto_unload_area_factor[load_area_index][unload_area_index] = \
                            (cost_to_unload_area[unload_area_index][load_area_index] / (heavy_speed * 1000)) /  self.payload


        except Exception as es:
            logger.error(es)
            logger.error("车流规划信息计算异常")


    # def extract_walk_time_info(self):
    #     try:
    #         # 车流规划部分矩阵格式与其余两个模块不同
    #         cost_to_load_area = self.path_planner.cost_to_load_area
    #         cost_to_unload_area = self.path_planner.cost_to_unload_area
    #
    #         distance_to_load_area = self.path_planner.distance_to_load_area
    #         distance_to_unload_area = self.path_planner.distance_to_unload_area
    #
    #         # 路网信息读取
    #         for unload_area_index in range(unload_area_num):
    #             for load_area_index in range(load_area_num):
    #                 self.goto_load_area_factor[unload_area_index][load_area_index] = \
    #                     (cost_to_load_area[unload_area_index][load_area_index] / (empty_speed * 1000)) / self.payload
    #
    #                 self.goto_unload_area_factor[load_area_index][unload_area_index] = \
    #                     (cost_to_unload_area[unload_area_index][load_area_index] / (heavy_speed * 1000)) /  self.payload
    #     except Exception as es:
    #         logger.error(es)
    #         logger.error("车流规划信息计算异常")
    #
    #     # for walk_time in session_postgre.query(WalkTime).all():
    #     #     load_area_id = str(walk_time.load_area_id)
    #     #     unload_area_id = str(walk_time.unload_area_id)
    #     #     # 将uuid转为id
    #     #     load_area_index = load_area_uuid_to_index_dict[load_area_id]
    #     #     unload_area_index = unload_area_uuid_to_index_dict[unload_area_id]
    #     #
    #     #     # # 运输路线距离
    #     #     # self.walk_time_to_load_area[unload_area_index][load_area_index] = walk_time.to_load_distance
    #     #     # self.walk_time_to_unload_area[load_area_index][unload_area_index] = walk_time.to_unload_distance
    #     #
    #     #     # 卸载道路上，每运输1吨货物需要一辆卡车运行时长,等于（该卸载道路上车辆平均运行时长/卡车平均实际装载量）
    #     #     # 单位为辆小时/吨
    #     #     # i代表第i个电铲,j代表第j个卸载点
    #     #     # walktime_goto_dump单位是秒，需要除以3600，转成小时
    #     #     self.goto_load_area_factor[unload_area_index][load_area_index] = \
    #     #         (60 / 1000 * walk_time.to_load_distance / self.empty_speed) / self.payload
    #     #     # / self.avg_goto_excavator_weight[load_area_index][unload_area_index]
    #     #
    #     #     # 装载道路上，每提供1吨的装载能力需要一辆卡车运行时长,等于（该装载道路上车辆平均运行时长/卡车平均装载能力）
    #     #     # 单位为辆小时/吨
    #     #     # i代表第i个卸载点,j代表第j个电铲
    #     #     # walktime_goto_excavator单位是秒，需要除以3600，转成小时
    #     #     self.goto_unload_area_factor[load_area_index][unload_area_index] = \
    #     #         (60 / 1000 * walk_time.to_unload_distance / self.heavy_speed) / self.payload
    #     #     # / self.avg_goto_excavator_weight[unload_area_index][load_area_index]


# 初始化车流规划类
def Traffic_para_init(num_of_load_area, num_of_unload_area, num_of_excavator, num_of_dump):

    try:

        tra_para = Traffic_para(num_of_load_area, num_of_unload_area, num_of_excavator, num_of_dump)

        tra_para.period_map_para_load()

        tra_para.period_walk_para_load()

        # Traffic_para.extract_walk_time_info(tra_para)

        Traffic_para.extract_excavator_info(tra_para)

        Traffic_para.extract_dump_info(tra_para)

        Traffic_para.extract_walk_time_info(tra_para)

        # 全部矿卡设备集合
        truck_set = set(update_total_truck())

        # 固定派车矿卡集合
        fixed_truck_set = set(update_fixdisp_truck())

        # 动态派车矿卡集合
        tra_para.truck_total_num = len(truck_set.difference(fixed_truck_set))

        # 计算逻辑道路因子
        for i in range(num_of_excavator):
            for j in range(num_of_dump):
                # 查找挖机绑定的装载区, 卸载设备绑定的卸载区
                load_area_index = tra_para.excavator_index_to_load_area_index_dict[i]
                unload_area_index = tra_para.dump_index_to_unload_area_index_dict[j]

                # 逻辑道路因子赋值, 来自实际道路因子
                tra_para.goto_excavator_factor[j][i] = \
                    tra_para.goto_load_area_factor[unload_area_index][load_area_index]

                tra_para.goto_dump_factor[i][j] = \
                    tra_para.goto_unload_area_factor[load_area_index][unload_area_index]

                # 每条卸载道路的优先级,等于电铲的优先级乘以卸载点的优先级
                tra_para.priority_coefficient[i][j] = tra_para.excavator_priority_coefficient[i] \
                                                                    * tra_para.dump_priority_coefficient[j]

                # # 逻辑距离赋值，来自实际道路距离
                # tra_para.walk_time_to_excavator[j][i] = \
                #     tra_para.walk_time_to_load_area[unload_area_index][load_area_index]
                #
                # tra_para.walk_time_to_dump[i][j] = \
                #     tra_para.walk_time_to_unload_area[load_area_index][unload_area_index]

    except Exception as es:
        logger.error(es)
        logger.error("车流规划类比初始化异常")
    return tra_para
