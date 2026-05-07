import os
import sys
import traceback
import subprocess

print(f"Python version: {sys.version}")
print(f"Current directory: {os.getcwd()}")

# 检查端口是否被占用
def check_port(port):
    try:
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            result = s.connect_ex(('localhost', port))
            return result == 0
    except Exception as e:
        print(f"Error checking port: {e}")
        return False

# 测试WebUI启动
print("\n=== 测试WebUI启动 ===")

# 创建一个简单的测试脚本
test_script = """
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
"""

# 写入测试脚本
with open('test_webui_start.py', 'w', encoding='utf-8') as f:
    f.write(test_script)

# 检查8080端口是否已被占用
print(f"Port 8080 is in use: {check_port(8080)}")

# 运行测试脚本
print("\nRunning test script...")
process = subprocess.Popen(
    [sys.executable, 'test_webui_start.py'],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

# 等待一段时间
import time
time.sleep(5)

# 检查进程状态
if process.poll() is None:
    print("WebUI process is running")
    print(f"Port 8080 is now in use: {check_port(8080)}")
    
    # 读取输出
    stdout, stderr = process.communicate(timeout=2)
    print("\nSTDOUT:")
    print(stdout)
    print("\nSTDERR:")
    print(stderr)
    
    # 终止进程
    process.terminate()
else:
    print(f"WebUI process exited with code: {process.returncode}")
    stdout, stderr = process.communicate()
    print("\nSTDOUT:")
    print(stdout)
    print("\nSTDERR:")
    print(stderr)

print("\n=== 测试完成 ===")
