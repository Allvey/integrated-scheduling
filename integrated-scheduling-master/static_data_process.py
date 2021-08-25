#!E:\Pycharm Projects\Waytous
# -*- coding: utf-8 -*-
# @Time : 2021/7/23 11:23
# @Author : Opfer
# @Site :
# @File : static_data_process.py
# @Software: PyCharm


# 静态数据处理(函数名即为注释)

from settings import *


def build_work_area_uuid_index_map():
    # load_area_id <-> load_area_index
    # unload_area_id <-> unload_area_index
    load_area_uuid_to_index_dict = {}
    unload_area_uuid_to_index_dict = {}
    load_area_index_to_uuid_dict = {}
    unload_area_index_to_uuid_dict = {}

    unload_area_num = 0
    load_area_num = 0

    try:
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
        if unload_area_num < 1 or load_area_num < 1:
            raise Exception("无路网信息")
    except Exception as es:
        logger.error(es)
    return (
        load_area_uuid_to_index_dict,
        unload_area_uuid_to_index_dict,
        load_area_index_to_uuid_dict,
        unload_area_index_to_uuid_dict,
    )


def build_park_uuid_index_map():
    # park_id <-> park_index
    park_uuid_to_index_dict = {}
    park_index_to_uuid_dict = {}

    park_num = 0

    try:
        for item in session_postgre.query(WalkTimePark).all():
            park = str(item.park_area_id)
            if park not in park_uuid_to_index_dict:
                park_uuid_to_index_dict[park] = park_num
                park_index_to_uuid_dict[park_num] = park
                park_num = park_num + 1
        if park_num < 1:
            raise Exception("无备停区路网信息")
    except Exception as es:
        logger.error(es)

    return park_uuid_to_index_dict, park_index_to_uuid_dict


def build_truck_uuid_name_map():
    # truck_id <-> truck_name
    truck_uuid_to_name_dict = {}
    truck_name_to_uuid_dict = {}

    try:
        for item in session_mysql.query(Equipment).filter_by(device_type=1).all():
            truck_id = item.id
            truck_name = item.equipment_id

            truck_name_to_uuid_dict[truck_name] = truck_id
            truck_uuid_to_name_dict[truck_id] = truck_name
        if len(truck_uuid_to_name_dict) < 1 or len(truck_name_to_uuid_dict) < 1:
            raise Exception("无矿卡设备可用-矿卡设备映射异常")
    except Exception as es:
        logger.warning(es)
    return truck_uuid_to_name_dict, truck_name_to_uuid_dict


def update_deveices_map(unload_area_uuid_to_index_dict, load_area_uuid_to_index_dict):
    excavator_uuid_to_index_dict = {}  # 用于将Excavator表中的area_id映射到index
    dump_uuid_to_index_dict = {}  # 用于将Dump表中的area_id映射到index
    excavator_index_to_uuid_dict = {}  # 用于将index映射到Excavator表中的area_id
    dump_index_to_uuid_dict = {}  # 用于将index映射到Dump表中的area_id

    dump_uuid_to_unload_area_uuid_dict = {}
    excavator_uuid_to_load_area_uuid_dict = {}
    excavator_index_to_load_area_index_dict = {}
    dump_index_to_unload_area_index_dict = {}

    try:
        excavator_num = 0
        dump_num = 0
        for item in (
            session_mysql.query(Dispatch).filter_by(isdeleted=0, isauto=1).all()
        ):
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
            if dump_id not in dump_uuid_to_unload_area_uuid_dict:
                dump_uuid_to_index_dict[dump_id] = dump_num
                dump_index_to_uuid_dict[dump_num] = dump_id
                dump_uuid_to_unload_area_uuid_dict[dump_id] = unload_area_id
                dump_index_to_unload_area_index_dict[
                    dump_uuid_to_index_dict[dump_id]
                ] = unload_area_uuid_to_index_dict[unload_area_id]
                dump_num = dump_num + 1
            if excavator_id not in excavator_uuid_to_index_dict:
                excavator_uuid_to_index_dict[excavator_id] = excavator_num
                excavator_index_to_uuid_dict[excavator_num] = excavator_id
                excavator_uuid_to_load_area_uuid_dict[excavator_id] = load_area_id
                excavator_index_to_load_area_index_dict[
                    excavator_uuid_to_index_dict[excavator_id]
                ] = load_area_uuid_to_index_dict[load_area_id]
                excavator_num = excavator_num + 1
        if excavator_num < 1 or dump_num < 1:
            raise Exception("无动态派车计划可用-动态派车挖机/卸载设备映射失败")
    except Exception as es:
        logger.warning(es)

    return {
        "excavator_uuid_to_index_dict": excavator_uuid_to_index_dict,
        "dump_uuid_to_index_dict": dump_uuid_to_index_dict,
        "excavator_index_to_uuid_dict": excavator_index_to_uuid_dict,
        "dump_index_to_uuid_dict": dump_index_to_uuid_dict,
        "dump_uuid_to_unload_area_uuid_dict": dump_uuid_to_unload_area_uuid_dict,
        "excavator_uuid_to_load_area_uuid_dict": excavator_uuid_to_load_area_uuid_dict,
        "excavator_index_to_load_area_index_dict": excavator_index_to_load_area_index_dict,
        "dump_index_to_unload_area_index_dict": dump_index_to_unload_area_index_dict,
    }


def update_truck_uuid_index_map(dynamic_truck_set):
    truck_uuid_to_index_dict = {}
    truck_index_to_uuid_dict = {}

    # truck_id <-> truck_index
    truck_num = 0
    for truck_id in dynamic_truck_set:
        truck_uuid_to_index_dict[truck_id] = truck_num
        truck_index_to_uuid_dict[truck_num] = truck_id
        truck_num = truck_num + 1

    return {
        "truck_uuid_to_index_dict": truck_uuid_to_index_dict,
        "truck_index_to_uuid_dict": truck_index_to_uuid_dict,
    }


def update_total_truck():
    # 矿卡集合
    truck_list = []

    try:
        query = np.array(
            session_mysql.query(Equipment)
            .filter_by(device_type=1, isdeleted=0, disabled=0)
            .all()
        )

        # for item in query:
        #     json_value = json.loads(redis2.get(item.equipment_id))
        #     is_online = json_value.get('isOnline')
        #     if is_online:
        #         truck_list.append(item.id)

        for item in query:
            truck_list.append(item.id)

        if len(truck_list) < 1:
            raise Exception("无矿卡设备可用-矿卡集合读取异常")
    except Exception as es:
        logger.error(es)

    return truck_list


def update_fixdisp_truck():
    # 固定派车矿卡集合
    fixed_truck_list = []

    try:
        query = np.array(
            session_mysql.query(Dispatch).filter_by(isauto=0, isdeleted=0).all()
        )

        for item in query:
            fixed_truck_list.append(item.truck_id)
        if len(fixed_truck_list) < 1:
            raise Exception("无固定派车计划可用-固定派车矿卡集合读取异常")
    except Exception as es:
        logger.error(es)
    return fixed_truck_list


def update_autodisp_excavator():
    # 用于动态派车的挖机集合
    dynamic_excavator_list = []
    try:
        for item in (
            session_mysql.query(Dispatch).filter_by(isdeleted=0, isauto=1).all()
        ):
            dynamic_excavator_list.append(item.exactor_id)
        if len(dynamic_excavator_list) < 1:
            raise Exception("无动态派车计划可用-动态派车挖机/卸载设备集合读取异常")
    except Exception as es:
        logger.warning(es)

    return dynamic_excavator_list


def update_autodisp_dump():
    # 用于动态调度的卸载点集合
    dynamic_dump_list = []
    try:
        for item in (
            session_mysql.query(Dispatch).filter_by(isdeleted=0, isauto=1).all()
        ):
            dynamic_dump_list.append(item.dump_id)
        if len(dynamic_dump_list) < 1:
            raise Exception("无动态派车计划可用-动态派车挖机/卸载设备集合读取异常")
    except Exception as es:
        logger.warning(es)
    return dynamic_dump_list


def update_load_area():
    load_area_list = []
    for walk_time in session_postgre.query(WalkTime).all():
        load_area_list.append(walk_time.load_area_id)

    return load_area_list


def update_unload_area():
    unload_area_list = []
    for walk_time in session_postgre.query(WalkTime).all():
        unload_area_list.append(walk_time.unload_area_id)
    return unload_area_list


def update_park_area():
    park_area_list = []
    for walk_time_park in session_postgre.query(WalkTimePark).all():
        park_area_list.append(walk_time_park.park_area_id)
    return park_area_list
