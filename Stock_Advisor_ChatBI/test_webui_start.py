
import os
import sys

print(f"Python version: {sys.version}")
print(f"Current directory: {os.getcwd()}")

from qwen_agent.agents import Assistant
from qwen_agent.gui import WebUI

print("WebUI imported successfully")

# 创建一个简单的助手
llm_cfg = {
    'model': 'qwen-turbo',
    'timeout': 30,
}

bot = Assistant(
    llm=llm_cfg,
    name='Test Bot',
    description='Test bot',
    system_message='You are a test assistant',
    function_list=[],
)

print("Assistant created successfully")

# 启动WebUI
print("Starting WebUI...")
webui = WebUI(bot)
print("WebUI instance created, running...")

# 这里会阻塞
webui.run()
