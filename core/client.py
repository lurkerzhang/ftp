#!_*_coding:utf-8 _*_
# __author__:"lurkerzhang"
import socket
import struct
import json
import hashlib
import os
import sys

from core.file_md5 import get_file_md5


# 登陆
def login(client):
    print('提示：用户名:zhang,alex,egon 密码都是123456')
    while True:
        name = input('用户名：').strip()
        if name == 'exit':
            client.send(name.encode('utf-8'))
            return False
        else:
            client.send(name.encode('utf-8'))
            name_exist = client.recv(1024).decode('utf-8')
            if name_exist == 'true':
                pwd = hashlib.md5(input('密码：').strip().encode('utf-8')).hexdigest()
                client.send(pwd.encode('utf-8'))
                login_res = client.recv(1024).decode('utf-8')
                if login_res == 'true':
                    return name
                elif login_res == 'logined':
                    print('%s 已登陆不能重复登陆'% name)
                    return ''
                else:
                    print('密码错误')
                    continue
            else:
                print('用户不存在')
                continue


def main():
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(('127.0.0.1', 8080))
    if client.recv(1024).decode('utf-8') == 'full':
        print('服务器并发数超限稍候再试')
        exit('bye')
    name = login(client)
    if not name:
        print('登陆失败')
        exit('bye')
    else:
        print('%s登陆成功' % name)
        print('''演示说明：
    进入文件夹 ：cd [当前目录中的文件夹名]
    查看目录内容：dir 、dir [文件夹名称]
    返回上层文件夹：cd ..
    进入用户的家目录：cd .
    进入用户共享目录：cd share
    下载当前目录文件：get [文件名] 支持续传
    上传本地目录（client_data_dir/[username]/）的文件到服务器：put [文件名]
    创建文件夹：mkdir [文件夹名]
    客户端用户配置文件:config/user.ini  空间配额quto 单位为MB
        ''')
        download_dir = os.path.join(os.path.dirname(os.path.dirname((os.path.abspath(__file__)))), 'client_data_dir', name)
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
        while True:
            # 1、发命令
            cmd = input('>>>: ').strip()
            if not cmd:
                continue
            elif cmd.split()[0] == 'get':
                get(cmd, client, download_dir)
            elif cmd.split()[0] == 'put':
                put(cmd, client, download_dir)
            elif cmd.split()[0] == 'exit':
                client.send(b'exit')
                exit('bye')
            else:
                cmd_exe(cmd, client)
    client.close()


def get(cmd, client, download_dir):
    client.send(cmd.encode('gbk'))
    # 以写的方式打开一个新文件，接收服务器发来的文件内容写入客户端的新文件

    # 第一步：先收报头长度
    obj = client.recv(4)
    header_size = (struct.unpack('i', obj))[0]
    # 第三步：再收报头
    header_bytes = client.recv(header_size)
    # 第三步：从报头中解析出真实数据的描述信息
    header_json = header_bytes.decode('utf-8')
    header_dic = json.loads(header_json)
    total_size = header_dic['file_size']
    filename = header_dic['filename']
    filemd5 = header_dic['md5']
    if not filename:
        print('文件不存在')
        return 0
    # 接收数据
    # 保存文件位置
    save_path = os.path.join(download_dir, filename)
    if os.path.exists(save_path):
        # 文件已存在，检测一致性
        if get_file_md5(save_path) == filemd5:
            print('文件已存在，与服务器文件一致，不需重新下载')
            client.send('101'.encode('utf-8'))
            return
        else:
            print('是否续传？y/n')
            s = input().strip()
            if s == 'y':
                # 获取本地文件大小
                local_size = os.path.getsize(save_path)
                client.send(str(local_size).encode('utf-8'))
                with open(save_path, 'ab+') as f:
                    recv_size = local_size
                    while recv_size < total_size:
                        line = client.recv(1024)
                        f.write(line)
                        recv_size += len(line)
                        done = int(50 * recv_size / total_size)
                        sys.stdout.write(
                            "\r[%s%s] %d%%" % ('█' * done, ' ' * (50 - done), 100 * recv_size / total_size))
                        sys.stdout.flush()
    else:
        client.send('100'.encode('utf-8'))
        with open(save_path, 'wb') as f:
            recv_size = 0
            while recv_size < total_size:
                line = client.recv(1024)
                f.write(line)
                recv_size += len(line)

                # 下载进度显示
                done = int(50 * recv_size / total_size)
                sys.stdout.write("\r[%s%s] %d%%" % ('█' * done, ' ' * (50 - done), 100 * recv_size / total_size))
                sys.stdout.flush()
    # 检查文件一致性
    local_file_md5 = get_file_md5(save_path)
    if local_file_md5 == filemd5:
        print('下载完成，通过文件一致性检测')
    else:
        print('下载完成，未通过文件一致性检测')
    return


def put(cmd, client, download_dir):
    filename = cmd.split()[1]
    # 文件不存在则返回
    if not os.path.exists(os.path.join(download_dir, filename)):
        print('文件%s不存在' % os.path.join(download_dir, filename))
        return
    client.send(cmd.encode('gbk'))
    cmd = cmd.split()
    # 制作的报头
    header_dic = {
        'filename': filename,
        'md5': '',
        'file_size': os.path.getsize('%s\%s' % (download_dir, filename))
    }
    header_json = json.dumps(header_dic)
    header_bytes = header_json.encode('utf-8')
    # 发送报头的长度
    client.send(struct.pack('i', len(header_bytes)))
    # 发送报头
    client.send(header_bytes)
    # 等待服务器响应
    res = client.recv(1024).decode('utf-8')
    if res == '101':
        print('配额超限')
        return
    elif res == '100':
        # 发送真实的数据
        with open('%s' % os.path.join(download_dir, filename), 'rb') as f:
            for line in f:
                client.send(line)


def cmd_exe(cmd, client):
    # 发命令
    client.send(cmd.encode('utf-8'))
    # 拿命令的结果，并打印
    # 先收报头长度
    obj = client.recv(4)
    header_size = struct.unpack('i', obj)[0]
    # 再收报头
    header_bytes = client.recv(header_size)
    # 从报头中解析出真实数据的描述信息
    header_json = header_bytes.decode('utf-8')
    header_dic = json.loads(header_json)
    total_size = header_dic['total_size']
    # 接收真实的数据
    recv_size = 0
    recv_data = b''
    while recv_size < total_size:
        res = client.recv(10)
        recv_data += res
        recv_size += len(res)
    temp = recv_data.decode('gbk').split('\n')
    new_recv_list = []
    for i in temp:
        if '驱动器' not in i and '中的卷是' not in i and '卷的序列号是' not in i and i and i != '\r':
            new_recv_list.append(i)
    new_recv_data = '\n'.join(new_recv_list)
    print(new_recv_data)