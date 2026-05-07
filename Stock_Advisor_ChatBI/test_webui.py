import os
import sys
import traceback

print(f"Python version: {sys.version}")
print(f"Current directory: {os.getcwd()}")
print(f"sys.path: {sys.path}")

# 测试qwen_agent模块是否存在
print("\n=== 检查qwen_agent模块 ===")
try:
    import qwen_agent
    print(f"qwen_agent imported, version: {getattr(qwen_agent, '__version__', 'unknown')}")
    print(f"qwen_agent modules: {dir(qwen_agent)}")
except Exception as e:
    print(f"qwen_agent import failed: {e}")
    traceback.print_exc()

# 测试WebUI导入
print("\n=== 检查WebUI导入 ===")
try:
    from qwen_agent.gui import WebUI
    print("WebUI imported successfully")
    print(f"WebUI class: {WebUI}")
except Exception as e:
    print(f"WebUI import failed: {e}")
    traceback.print_exc()

# 测试Assistant导入
print("\n=== 检查Assistant导入 ===")
try:
    from qwen_agent.agents import Assistant
    print("Assistant imported successfully")
    print(f"Assistant class: {Assistant}")
except Exception as e:
    print(f"Assistant import failed: {e}")
    traceback.print_exc()

# 测试dashscope
print("\n=== 检查dashscope ===")
try:
    import dashscope
    print(f"dashscope imported, version: {getattr(dashscope, '__version__', 'unknown')}")
except Exception as e:
    print(f"dashscope import failed: {e}")
    traceback.print_exc()

print("\n=== 测试完成 ===")
