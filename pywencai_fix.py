#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pywencai 库的 bug 修复
在 get() 函数中添加 None 检查，避免 AttributeError
"""

import os
import sys
import subprocess

# 禁止 Node.js 弃用警告
os.environ['NODE_NO_WARNINGS'] = '1'

import pywencai as _pywencai
from pywencai import wencai as _wencai_module

# 保存原始的 get 函数
_original_get = _wencai_module.get

def get_with_none_check(loop=False, **kwargs):
    """
    包装后的 get 函数，处理 params 为 None 的情况
    """
    kwargs = {_wencai_module.replace_key(key): value for key, value in kwargs.items()}

    # 获取 robot data，处理 None 的情况
    params = _wencai_module.get_robot_data(**kwargs)

    if params is None:
        # 问财API无法响应或返回错误数据
        return None

    # 继续原有逻辑
    data = params.get('data')
    url_params = params.get('url_params')
    condition = _wencai_module._.get(data, 'condition')

    if condition is not None:
        kwargs = {**kwargs, **data}
        find = kwargs.get('find', None)
        if loop and find is None:
            row_count = params.get('row_count')
            return _wencai_module.loop_page(loop, row_count, url_params, **kwargs)
        else:
            return _wencai_module.get_page(url_params, **kwargs)
    else:
        no_detail = kwargs.get('no_detail')
        if no_detail != True:
            return data

# 替换原始的 get 函数
_wencai_module.get = get_with_none_check
_pywencai.get = get_with_none_check

print("✅ pywencai 库 bug 修复已应用")

