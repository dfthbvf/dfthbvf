# -*- coding: utf-8 -*-
"""
Coze API 配置文件
"""
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# Coze API 配置
COZE_API_TOKEN = "pat_3eCJB0NRHZX7N7dOmt26o5f5Oq5JVmxgC948bTJjDBafn0v2Nou7o4Tre7T7sTGH"
COZE_BOT_ID = "7627838550604267574"

# Coze API 基础URL (中国区)
COZE_CN_BASE_URL = "https://api.coze.cn"

# 用户ID (可以是任意字符串，用于标识用户)
DEFAULT_USER_ID = "user_12345" 