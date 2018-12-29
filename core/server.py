#!_*_coding:utf-8 _*_
# __author__:"lurkerzhang"
import socket
from conf.settings import HOST_IP, HOST_PORT, SHARE_DIR, USER_DIR, USER_DATA
import threading
import struct
import json
import os
import configparser
import subprocess
from core.file_md5 import get_file_md5


# 用户类
class ClientUser:
    def __init__(self, name):
        self.name = name
        self.cur_dir = SHARE_DIR
        self.home_dir = os.path.join(USER_DIR, name)
        self.is_logined = False
        self.quto = 0  # MB


# TCP服务类
class FTPServer:
    def __init__(self, HOST):
        # 在线用户容器
        self.online = []
        # 创建套接字
        self.ftp_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # 防止端口占用
        self.ftp_server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # 绑定服务器地址
        self.ftp_server_socket.bind(HOST)
        # 最大监听10
        self.ftp_server_socket.listen(10)

    # 连接客户端（多用户）,无限循环服务
    def run(self):
        while True:
            # 等待连接客户端
            conn, addr = self.ftp_server_socket.accept()

            # 创建线程与请求连接的客户端通信
            t = threading.Thread(target=self.comm, args=(conn, addr))
            t.start()

    # 客户端通信
    def comm(self, conn, addr):
        try:
            user = login(conn, addr)
            if not user:
                return
            else:
                while True:
                    try:
                        # 1、收命令
                        res = conn.recv(8096)
                        if not res:
                            break
                        print('客户端发来的命令', res.decode('utf-8'))
                        # 2、解析命令，提取相应命令参数
                        cmds = res.decode('utf-8').split()
                        if cmds[0] == 'get':
                            get(cmds, conn, user)
                        elif cmds[0] == 'put':
                            put(cmds, conn, user)
                        elif cmds[0] == 'exit':
                            print('用户%s断开链接' % user.name)
                            conn.close()
                            break
                        else:
                            user = cmd_exe(res, conn, user)
                    except ConnectionResetError:
                        break
                return
        except ConnectionResetError:
            print('%s强制关闭了与服务器的连接' % str(addr))


# 处理客户端登陆
def login(conn, addr):
    user = None
    if not user:
        user_data = configparser.ConfigParser()
        user_data.read(USER_DATA)
        users_list = user_data.sections()
        while True:
            user_name = conn.recv(1024).decode('utf-8')
            if user_name == 'exit':
                print('%s尝试登陆失败' % str(addr))
                return user
            elif user_name not in users_list:
                print('来自客户端%s使用未知用户名%s登陆失败' % (str(addr), user_name))
                conn.send('false'.encode('utf-8'))
                continue
            else:
                conn.send('true'.encode('utf-8'))
                password = conn.recv(1024).decode('utf-8')
                if password == user_data.get(user_name, 'password'):
                    conn.send('true'.encode('utf-8'))
                    user = ClientUser(user_name)
                    user.is_logined = True
                    user.quto = user_data.get(user_name, 'quto')
                    print('来自客户端%s的用户%s成功登陆到服务器' % (str(addr), user_name))
                    return user
                else:
                    conn.send('false'.encode('utf-8'))
                    print('来自客户端%s的用户%s因密码错误登陆失败' % (str(addr), user_name))
                    continue


# 下载:get
def get(cmds, conn, user):
    filename = cmds[1]
    file_path = os.path.join(user.cur_dir, filename)
    if not os.path.exists(file_path):
        filename = ''
        file_md5 = 'none'
        file_size = 0
    else:
        file_md5 = get_file_md5(file_path)
        file_size = os.path.getsize(file_path)
    # 以读的方式打开文件，读取文件内容发送给客户端
    # 制作报头

    header_dic = {
        'filename': filename,
        'md5': file_md5,
        'file_size': file_size
    }
    header_json = json.dumps(header_dic)
    header_bytes = header_json.encode('utf-8')
    # 第二步：先发送报头的长度
    conn.send(struct.pack('i', len(header_bytes)))
    # 第三步：再发送报头
    conn.send(header_bytes)
    # 文件不存在发送报头后结束
    if not filename:
        return
    # 等待客户端反馈确认信息
    recv_confire = conn.recv(1024)
    if recv_confire.decode('utf-8') == '101':
        return
    elif recv_confire.decode('utf-8') == '100':
        # 第四步：再发送真实的数据
        if not filename:
            return
        with open(file_path, 'rb') as f:
            for line in f:
                conn.send(line)
        return
    else:
        seek_addr = int(recv_confire.decode('utf-8'))
        with open(file_path, 'rb') as f:
            f.seek(seek_addr, 0)
            for line in f:
                conn.send(line)
        return


# 上传
def put(cmds, conn, user):
    # 以写的方式打开一个新文件，接收服务器发来的文件内容写入客户端的新文件
    # 收报头长度
    obj = conn.recv(4)
    header_size = (struct.unpack('i', obj))[0]
    # 收报头
    header_bytes = conn.recv(header_size)
    # 从报头中解析出真实数据的描述信息
    header_json = header_bytes.decode('utf-8')
    header_dic = json.loads(header_json)
    total_size = header_dic['file_size']
    filename = header_dic['filename']
    user_quto = user.quto
    put_dir = os.path.join(user.home_dir, filename)
    cur_quto = get_dir_size(user.home_dir)
    if cur_quto + round(total_size/1024/1024, 2) > float(user_quto):
        conn.send('101'.encode('utf-8'))
        return
    else:
        conn.send('100'.encode('utf-8'))
    # 接收的数据
    with open(put_dir, 'wb') as f:
        recv_size = 0
        while recv_size < total_size:
            line = conn.recv(1024)
            f.write(line)
            recv_size += len(line)
        # 上传完成
        return 1


def cmd_exe(xcmd, conn, user):
    try:
        xcmd = xcmd.decode('utf-8')
        # 根据用户目录重建cmd命令
        cmd_list = xcmd.split()
        home_dir = user.home_dir
        cur_dir = user.cur_dir
        if len(cmd_list) < 2:
            cmd_list.append(cur_dir)
        else:
            if cmd_list[0] == 'cd':
                if cmd_list[1] == '.':
                    user.cur_dir = user.home_dir
                    cur_dir = user.cur_dir
                    cmd_list[1] = cur_dir
                elif cmd_list[1] == '..':
                    if cur_dir == home_dir or cur_dir == SHARE_DIR:
                        cmd_list[1] = cur_dir
                    else:
                        cur_dir_list = cur_dir.split('\\')
                        cur_dir_list.pop()
                        user.cur_dir = '\\'.join(cur_dir_list)
                        cur_dir = user.cur_dir
                        cmd_list[1] = cur_dir
                elif cmd_list[1] == 'share':
                    user.cur_dir = SHARE_DIR
                    cur_dir = user.cur_dir
                    cmd_list[1] = cur_dir
                else:
                    cmd_list[1] = os.path.join(cur_dir,cmd_list[1])
                    if os.path.exists(cmd_list[1]):
                        user.cur_dir = cmd_list[1]
            else:
                cmd_list[1] = os.path.join(cur_dir, cmd_list[1])
        cmd = ' '.join(cmd_list)
        print(cmd)

        # 执行命令，拿到结果
        obj = subprocess.Popen(cmd, shell=True,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
        stdout = obj.stdout.read()
        stderr = obj.stderr.read()

        # 把命令的结果返回给客户端
        # 制作固定长度的报头
        header_dic = {
            'filename': 'a.txt',
            'md5': '',
            'total_size': len(stdout) + len(stderr)
        }
        header_json = json.dumps(header_dic)
        header_bytes = header_json.encode('utf-8')
        # 发送报头的长度
        conn.send(struct.pack('i', len(header_bytes)))
        # 发送报头
        conn.send(header_bytes)
        # 发送数据
        conn.send(stdout)
        conn.send(stderr)
        return user
    except ConnectionResetError:
        return user


# 获取指定路径的文件夹大小（单位：GB）
def get_dir_size(p_doc):
    list1 = []

    def get_size(path):
        fileList = os.listdir(path)  # 获取path目录下所有文件
        for filename in fileList:
            pathTmp = os.path.join(path, filename)  # 获取path与filename组合后的路径
            if os.path.isdir(pathTmp):  # 判断是否为目录
                get_size(pathTmp)  # 是目录就继续递归查找
            elif os.path.isfile(pathTmp):  # 判断是否为文件
                filesize = os.path.getsize(pathTmp)  # 如果是文件，则获取相应文件的大小
                list1.append(filesize)  # 将文件的大小添加到列表
    get_size(p_doc)
    return round(sum(list1)/1024/1024, 2)  # MB


def main():
    HOST = (HOST_IP, HOST_PORT)
    myFTPServer = FTPServer(HOST)
    myFTPServer.run()
