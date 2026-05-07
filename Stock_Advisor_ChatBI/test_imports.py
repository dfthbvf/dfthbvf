import os
import sys

print(f"Python version: {sys.version}")
print(f"Current directory: {os.getcwd()}")

# 测试模块导入
try:
    print("\n1. Importing qwen_agent...")
    import qwen_agent
    print(f"   qwen_agent imported successfully, version: {getattr(qwen_agent, '__version__', 'unknown')}")
except Exception as e:
    print(f"   Error importing qwen_agent: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    print("\n2. Importing WebUI...")
    from qwen_agent.gui import WebUI
    print("   WebUI imported successfully")
except Exception as e:
    print(f"   Error importing WebUI: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\nAll imports successful!")
print("WebUI is ready to use")
