#!_*_coding:utf-8 _*_
# __author__:"lurkerzhang"
import hashlib
import os

_FILE_SLIM = (100 * 1024 * 1024)  # 100MB


def get_file_md5(filename):
    hmd5 = hashlib.md5()
    fp = open(filename, "rb")
    f_size = os.stat(filename).st_size
    if f_size > _FILE_SLIM:
        while f_size > _FILE_SLIM:
            hmd5.update(fp.read(_FILE_SLIM))
            f_size /= _FILE_SLIM
        if (f_size > 0) and (f_size <= _FILE_SLIM):
            hmd5.update(fp.read())
    else:
        hmd5.update(fp.read())
    return hmd5.hexdigest()