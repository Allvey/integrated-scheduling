#!E:\Pycharm Projects\Waytous
# -*- coding: utf-8 -*-
# @Time : 2021/7/23 11:25
# @Author : Opfer
# @Site :
# @File : settings.py
# @Software: PyCharm


# 数据库设备, redis设置, 日志设置
from tables import *
from urllib.parse import quote
import logging.handlers
from redis import StrictRedis, ConnectionPool
import numpy as np
from redis import StrictRedis, ConnectionPool
import redis
from datetime import datetime, timedelta
import copy
import json
import sched
import time

# 创建日志
########################################################################################################################
# 日志存储地址
log_path = "/usr/local/fleet-log/dispatch"

# # 创建日志目录
# if not os.path.exists(log_path):
#     os.mkdir(log_path)

# logging初始化工作
logging.basicConfig()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# timefilehandler = logging.handlers.TimedRotatingFileHandler(log_path + "/dispatch.log", when='M', interval=1, backupCount=60)
# filehandler = logging.handlers.RotatingFileHandler(log_path + "/dispatch.log", maxBytes=3*1024*1024, backupCount=10)
filehandler = logging.handlers.RotatingFileHandler(
    "./Logs/dispatch.log", maxBytes=3 * 1024 * 1024, backupCount=10
)
# 设置后缀名称，跟strftime的格式一样
filehandler.suffix = "%Y-%m-%d_%H-%M.log"

formatter = logging.Formatter("%(asctime)s - %(name)s: %(levelname)s %(message)s")
filehandler.setFormatter(formatter)
logger.addHandler(filehandler)


# 连接reids
########################################################################################################################
# redis 5 存储设备状态
pool5 = ConnectionPool(host="192.168.28.111", db=5, port=6379, password="Huituo@123")

redis5 = StrictRedis(connection_pool=pool5)

# redis 2 存储派车计划
pool2 = ConnectionPool(host="192.168.28.111", db=2, port=6379, password="Huituo@123")

redis2 = StrictRedis(connection_pool=pool2)

# 数据库连接设置
########################################################################################################################
# 创建对象的基类:
Base = declarative_base()

try:
    engine_mysql = create_engine(
        "mysql+mysqlconnector://root:%s@192.168.28.111:3306/waytous"
        % quote("Huituo@123")
    )

    engine_postgre = create_engine(
        "postgresql://postgres:%s@192.168.28.111:5432/shenbao_2021520"
        % quote("Huituo@123")
    )

    # 创建DBsession_mysql类型:
    DBsession_mysql = sessionmaker(bind=engine_mysql)

    DBsession_postgre = sessionmaker(bind=engine_postgre)

    # 创建session_mysql对象:
    session_mysql = DBsession_mysql()

    session_postgre = DBsession_postgre()
except Exception as es:
    logger.error("数据库连接失败")
    logger.error(es)
