#!E:\Pycharm Projects\Waytous
# -*- coding: utf-8 -*-
# @Time : 2021/7/19 15:05
# @Author : Opfer
# @Site :
# @File : traffic_flow_planner.py
# @Software: PyCharm

# import
import pulp
from traffic_flow.traffic_flow_info import *
# from backstore_traffic_flow_info import *
# import time
# start = time.time()
# much_job = [x**2 for x in range (1, 1000000, 3)]


# 从数据库中读取挖机和卸载设备相关参数，并将线性规划所用参数保存在TrafficProgPara类中


# 解决线性规划问题，生成每条道路的流量
def transportation_problem_slove(coefficient, w_ij, s_ij, b_excavator,
                                 b_dump, grade_loading_array,
                                 max_unload_weigh_alg_flag, truck_total_num,
                                 walk_time_to_excavator, walk_time_to_dump, min_throughout,
                                 grade_lower_array=None, grade_upper_array=None):
    row = len(coefficient)  # 代表挖机的个数,第i行代表第i台挖机
    col = len(coefficient[0])  # 代表卸载设备的个数,第j行代表第j个卸载设备

    # prob = pulp.LpProblem('Transportation Problem', sense=pulp.LpMaximize)
    # 卸载道路的流量,单位是吨/小时,i代表起点为第i个挖机,j代表终点为第j个卸载设备
    var_x = [[pulp.LpVariable('x{0}{1}'.format(i, j), lowBound=0) for j in range(col)] for i in range(row)]
    # 装载道路的流量,单位是吨/小时,i代表起点为第i个卸载设备,j代表终点为第j个挖机
    var_y = [[pulp.LpVariable('y{0}{1}'.format(i, j), lowBound=0) for j in range(row)] for i in range(col)]

    flatten = lambda x: [y for l in x for y in flatten(l)] if type(x) is list else [x]

    # 定义目标函数
    if max_unload_weigh_alg_flag == True:
        prob = pulp.LpProblem('Transportation Problem', sense=pulp.LpMaximize)
        # 得到目标函数，目标函数是使得系统的运输量最大
        prob += pulp.lpDot(flatten(var_x), coefficient.flatten())
    else:
        prob = pulp.LpProblem('Transportation Problem', sense=pulp.LpMinimize)
        goto_excavator_cost = var_x * walk_time_to_excavator
        goto_dump_cost = var_y * walk_time_to_dump
        prob += (pulp.lpSum(flatten(goto_excavator_cost)) + 1.5 * pulp.lpSum(flatten(goto_dump_cost)))

    # 定义约束条件
    # 最小产量约束，仅在最小化成本模式下成立
    if max_unload_weigh_alg_flag == False:
        prob += pulp.lpSum(var_x) >= min_throughout

    logger.info("road_factor")
    logger.info(w_ij)

    # 矿卡总数约束,在每条道路上的车辆总数要小于矿卡总个数
    # 通过矩阵按元素相乘得到每条卸载道路上的车辆个数
    unload_truck_total_num_array = w_ij * var_x
    # 通过矩阵按元素相乘得到每条装载道路上的车辆个数
    load_truck_totla_num_array = s_ij * var_y
    # 装载的矿卡数和卸载的矿卡数需要小于矿卡总数
    prob += (pulp.lpSum(unload_truck_total_num_array) +
             pulp.lpSum(load_truck_totla_num_array) <= 2)

    # 最大工作强度约束
    # 约束每个挖机的工作强度
    for i in range(row):
        prob += (pulp.lpSum(var_x[i]) <= b_excavator[i])
    # 约束每个卸载设备的工作强度
    for j in range(col):
        prob += (pulp.lpSum(var_y[j]) <= b_dump[j])

    '''
    # 车流基尔霍夫定理约束
    # 进入挖机和从挖机出去的车辆个数需要相同
    for i in range(row):
        prob += (pulp.lpSum(unload_truck_total_num_array[i]) == pulp.lpSum(load_truck_totla_num_array[:,i]))
    # 从装载点离开和进来的车辆个数需要相同
    for j in range(col):
        prob += (pulp.lpSum(load_truck_totla_num_array[j]) == pulp.lpSum(unload_truck_total_num_array[:,j]))
    '''

    # 从装载点去往卸载设备的流量之和要小于从卸载设备到装载点的流量之和
    for i in range(row):
        prob += (pulp.lpSum((np.array(var_x))[i]) <= pulp.lpSum((np.array(var_y))[:, i]))

    # 从卸载设备出发去往装载点的流量之和要小于从装载点到本卸载设备的流量之和
    for j in range(col):
        prob += (pulp.lpSum((np.array(var_y))[j]) <= pulp.lpSum((np.array(var_x))[:, j]))

    # 矿石品位约束卸载
    # 去往卸载设备的流量使用矩阵乘法乘以每个挖机处矿石的品位，得到每个卸载设备的矿石品位总和
    grade_array = np.dot(grade_loading_array, var_x)
    for j in range(col):
        sum_traffic_unload = pulp.lpSum((np.array(var_x))[:, j])
        prob += (grade_array[j] >= sum_traffic_unload * grade_lower_array[j])
        prob += (grade_array[j] <= sum_traffic_unload * grade_upper_array[j])

    # 非负约束
    for i in range(row):
        for j in range(col):
            prob += var_x[i][j] >= 0
            prob += var_y[j][i] >= 0

    prob.solve()

    try:
        if -1 == prob.status:
            raise Exception("Model infeasible or unbounded")
    except Exception as es:
        logger.warning(es)

    return {'objective': pulp.value(prob.objective),
            'var_x': [[pulp.value(var_x[i][j]) for j in range(col)] for i in range(row)],
            'var_y': [[pulp.value(var_y[i][j]) for j in range(row)] for i in range(col)]}


def traffic_flow_plan():
    excavator_list = update_autodisp_excavator()

    dump_list = update_autodisp_dump()

    excavator_set = set(excavator_list)

    dump_set = set(dump_list)

    load_area_list = update_load_area()

    unload_area_list = update_unload_area()

    load_area_set = set(load_area_list)

    unload_area_set = set(unload_area_list)

    excavator_num = len(excavator_set)

    dump_num = len(dump_set)

    unload_area_num = len(unload_area_set)

    load_area_num = len(load_area_set)

    print("装载区数量:", load_area_num, "卸载区数量:", unload_area_num, "挖机数量:", excavator_num, "卸载设备数量:", dump_num)

    # 初始化参量
    traffic_programme_para = Traffic_para_init(load_area_num, unload_area_num, excavator_num, dump_num)
    # traffic_programme_para = traffic_programme_para_init(load_area_num, unload_area_num, excavator_num, dump_num)
    # 系统是否以最大化产量为目标
    max_unload_weigh_alg_flag = True
    if max_unload_weigh_alg_flag:
        logger.info(f'最大产量调度模式')
    else:
        logger.info(f'最小成本调度模式')

    coefficient = traffic_programme_para.priority_coefficient
    w_ij = traffic_programme_para.goto_dump_factor
    s_ij = traffic_programme_para.goto_excavator_factor
    b_excavator = traffic_programme_para.excavator_strength
    b_dump = traffic_programme_para.dump_strength
    grade_loading_array = traffic_programme_para.grade_loading_array
    grade_lower_dump_array = traffic_programme_para.grade_lower_dump_array
    grade_upper_dump_array = traffic_programme_para.grade_upper_dump_array
    min_throughout = traffic_programme_para.min_throughout
    walk_time_to_excavator = traffic_programme_para.walk_time_to_excavator
    walk_time_to_dump = traffic_programme_para.walk_time_to_dump
    truck_total_num = traffic_programme_para.truck_total_num

    res = transportation_problem_slove(coefficient, w_ij, s_ij, b_excavator, b_dump,
                                       grade_loading_array, max_unload_weigh_alg_flag, truck_total_num,
                                       walk_time_to_excavator, walk_time_to_dump, min_throughout,
                                       grade_upper_dump_array, grade_lower_dump_array)

    if max_unload_weigh_alg_flag:
        print('最大化产量', res["objective"])
        logger.info(f'最大产量:{res["objective"]}')
    else:
        print('最小成本', res["objective"])
        logger.info(f'最小成本:{res["objective"]}')

    print('各变量的取值为：')
    logger.info('各变量取值:')
    print(np.array(res['var_x']).round(3))
    logger.info(f'重运车流:{res["var_x"]} 单位: 吨/时')
    print(np.array(res['var_y']).round(3))
    logger.info(f'空运车流:{res["var_y"]} 单位: 吨/时')

    # 通过矩阵按元素相乘得到每条卸载道路上的车辆个数
    print("卸载道路上的车辆个数")
    unload_traffic = res['var_x']
    print((traffic_programme_para.goto_dump_factor * unload_traffic).round(3))
    # 通过矩阵按元素相乘得到每条装载道路上的车辆个数
    print("装载道路上的车辆个数")
    load_traffic = res['var_y']
    print((traffic_programme_para.goto_excavator_factor * load_traffic).round(3))

    return res["var_x"], res["var_y"]

traffic_flow_plan()

# end = time.time()
# print("used {:.5}s".format(end-start))
