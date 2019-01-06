程序入口：
bin
    1、run_server.py   先运行
    2、client1.py client2.py client3.py  分别运行，模拟多个用户同时登陆在线
    3、登录用户名：alex, egon, zhang   密码都是123456

演示说明：
1、客户端用户配置文件:config/user.ini  空间配额quto 单位为MB, POOLSIZE 设置并发数
2、client_data_dir文件夹是客户端用户存放数据的地方，不同的账号登录后在该文件夹下生成一个以账号名命名的文件夹
3、server_data_dir文件夹是服务器端FTP存放数据的地方，该文件夹中share文件夹为各用户共享文件夹，可以下载上传文件；
   客户端登陆后，该文件夹下生成以用户名命名的用户家目录。
4、命令格式：
   默认登陆后，用户当前文件夹为服务器端的share目录
   进入文件夹 ：cd [当前目录中的文件夹名]
   返回上层文件夹：cd ..
   进入用户的家目录：cd .
   下载当前目录文件：get [文件名] 支持续传
   上传本地目录（client_data_dir/[username]/）的文件到服务器：put [文件名]
   创建文件夹：mkdir [文件夹名]

