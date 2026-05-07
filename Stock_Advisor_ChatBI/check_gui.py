import qwen_agent
import os

# 检查gui目录的__init__.py文件
gui_init_path = os.path.join(os.path.dirname(qwen_agent.__file__), 'gui', '__init__.py')
print('GUI __init__.py exists:', os.path.exists(gui_init_path))

if os.path.exists(gui_init_path):
    with open(gui_init_path, 'r', encoding='utf-8') as f:
        content = f.read()
    print('\nContent of gui/__init__.py:')
    print(content)

# 检查web_ui.py文件
web_ui_path = os.path.join(os.path.dirname(qwen_agent.__file__), 'gui', 'web_ui.py')
print('\nWeb UI file exists:', os.path.exists(web_ui_path))

if os.path.exists(web_ui_path):
    with open(web_ui_path, 'r', encoding='utf-8') as f:
        content = f.read()
    print('\nContent of gui/web_ui.py:')
    print(content[:1000])  # 只打印前1000个字符
