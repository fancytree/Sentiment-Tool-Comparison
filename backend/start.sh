#!/bin/bash

# 设置环境变量
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1
 
# 启动应用
exec gunicorn -c gunicorn.conf.py main:app 