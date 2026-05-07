import os
import sys
print(f"Python version: {sys.version}")
print(f"Current directory: {os.getcwd()}")

# 测试WebUI启动
try:
    print("\n=== 测试WebUI启动 ===")
    
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
    print("This will block until you stop the server")
    print("Web server should be available at: http://localhost:8080")
    
    webui = WebUI(bot)
    webui.run()
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
