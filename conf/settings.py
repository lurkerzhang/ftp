#!_*_coding:utf-8 _*_
# __author__:"lurkerzhang"
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USER_DIR = os.path.join(BASE_DIR, 'server_data_dir', 'user')
SHARE_DIR = os.path.join(BASE_DIR, 'server_data_dir', 'share')
HOST_IP = '127.0.0.1'
HOST_PORT = 8080
USER_DATA = os.path.join(BASE_DIR,'conf','user.ini')
# 设置并发数
POOLSIZE = 10