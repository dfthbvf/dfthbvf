import os
import sys
import traceback

print(f"Python version: {sys.version}")
print(f"Current directory: {os.getcwd()}")

# 测试WebUI导入和初始化
try:
    print("\n=== 测试WebUI导入 ===")
    from qwen_agent.gui import WebUI
    print("✓ WebUI导入成功")
    
    print("\n=== 测试Assistant导入 ===")
    from qwen_agent.agents import Assistant
    print("✓ Assistant导入成功")
    
    print("\n=== 测试创建Assistant ===")
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
    print("✓ Assistant创建成功")
    
    print("\n=== 测试创建WebUI实例 ===")
    webui = WebUI(bot)
    print("✓ WebUI实例创建成功")
    
    print("\n=== 所有测试通过！ ===")
    print("WebUI模块正常工作")
    
except Exception as e:
    print(f"✗ 测试失败: {e}")
    traceback.print_exc()
