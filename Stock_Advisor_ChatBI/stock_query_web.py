import os
import sys
import traceback

print(f"Python version: {sys.version}")
print(f"Current directory: {os.getcwd()}")

# 检查依赖
qwen_agent_available = False
webui_available = False
dashscope_available = False
pandas_available = False
sqlalchemy_available = False
matplotlib_available = False

# 检查 qwen_agent
try:
    from qwen_agent.agents import Assistant
    qwen_agent_available = True
    print("OK: Qwen agent Assistant imported successfully")
except Exception as e:
    print(f"ERROR: Qwen agent Assistant import failed: {e}")
    traceback.print_exc()

# 检查 WebUI
try:
    from qwen_agent.gui import WebUI
    webui_available = True
    print("OK: Qwen agent WebUI imported successfully")
except Exception as e:
    print(f"ERROR: Qwen agent WebUI import failed: {e}")
    traceback.print_exc()

# 检查 dashscope
try:
    import dashscope
    dashscope_available = True
    print("OK: Dashscope imported successfully")
except Exception as e:
    print(f"ERROR: Dashscope import failed: {e}")
    traceback.print_exc()

# 检查 pandas
try:
    import pandas as pd
    pandas_available = True
    print("OK: Pandas imported successfully")
except Exception as e:
    print(f"ERROR: Pandas import failed: {e}")

# 检查 SQLAlchemy
try:
    from sqlalchemy import create_engine, text
    sqlalchemy_available = True
    print("OK: SQLAlchemy imported successfully")
except Exception as e:
    print(f"ERROR: SQLAlchemy import failed: {e}")

# 检查 matplotlib
try:
    import matplotlib.pyplot as plt
    matplotlib_available = True
    print("OK: Matplotlib imported successfully")
except Exception as e:
    print(f"ERROR: Matplotlib import failed: {e}")

# 检查数据库文件
print(f"SQLite database exists: {os.path.exists('stock_data.db')}")
if os.path.exists('stock_data.db'):
    print(f"Database size: {os.path.getsize('stock_data.db')} bytes")

# 测试数据库连接
db_connected = False
try:
    from sqlalchemy import create_engine
    engine = create_engine('sqlite:///stock_data.db')
    import pandas as pd
    df = pd.read_sql('SELECT COUNT(*) FROM stock_price', engine)
    print(f"Database connection successful, total records: {df.iloc[0, 0]}")
    db_connected = True
except Exception as e:
    print(f"Database connection failed: {e}")

# 解决中文显示问题
if matplotlib_available:
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'SimSun', 'Arial Unicode MS']
    plt.rcParams['axes.unicode_minus'] = False

# 配置 DashScope
if dashscope_available:
    dashscope.api_key = 'sk-da44331e91c04018af6dd0daecb39bdc'
    dashscope.timeout = 30
    print("Dashscope configured successfully")

# ====== 股票查询助手 system prompt ======
system_prompt = """我是股票查询助手，以下是关于股票价格表相关的字段，我可能会编写对应的SQL，对数据进行查询
-- 股票价格表
CREATE TABLE stock_price (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    交易日期 TEXT NOT NULL,
    股票代码 TEXT NOT NULL,
    股票名称 TEXT NOT NULL,
    开盘价 REAL NOT NULL,
    最高价 REAL NOT NULL,
    最低价 REAL NOT NULL,
    收盘价 REAL NOT NULL,
    前收价 REAL NOT NULL,
    涨跌额 REAL NOT NULL,
    涨跌幅 REAL NOT NULL,
    成交量 REAL NOT NULL,
    成交额 REAL NOT NULL
);

支持的股票：
- 源杰科技 (688498.SH)
- 中际旭创 (300308.SZ)
- 隆基绿能 (601012.SH)
- 药明康德 (603259.SH)

数据时间范围：2022-01-01 至 2026-04-23

示例查询：
1. 查询某只股票在某时间段的收盘价
2. 计算某只股票的最高价/最低价
3. 查询某股票某天的涨跌幅
4. 按日期统计某股票的成交量

我将回答用户关于股票相关的问题

每当 exc_sql 工具返回 markdown 表格和图片时，你必须原样输出工具返回的全部内容（包括图片 markdown），不要只总结表格，也不要省略图片。这样用户才能直接看到表格和图片。
"""

# ====== 会话隔离 DataFrame 存储 ======
_last_df_dict = {}

def get_session_id(kwargs):
    messages = kwargs.get('messages')
    if messages is not None:
        return id(messages)
    return None

# ====== exc_sql 工具类实现 ======
if qwen_agent_available:
    from qwen_agent.tools.base import BaseTool, register_tool

    @register_tool('exc_sql')
    class ExcSQLTool(BaseTool):
        description = '对于生成的SQL，进行SQL查询，并自动可视化'
        parameters = [{
            'name': 'sql_input',
            'type': 'string',
            'description': '生成的SQL语句',
            'required': True
        }]

        def call(self, params: str, **kwargs) -> str:
            import json
            import matplotlib.pyplot as plt
            import io, os, time
            import numpy as np
            from sqlalchemy import text
            import pandas as pd
            from sqlalchemy import create_engine
            
            session_id = get_session_id(kwargs)
            args = json.loads(params)
            sql_input = args['sql_input']
            print('sql_input=', sql_input)
            
            engine = create_engine('sqlite:///stock_data.db')
            df = pd.read_sql(text(sql_input), engine)
            print('df=', df)
            
            if session_id:
                _last_df_dict[session_id] = df
            
            md = df.head(20).to_markdown(index=False)
            
            save_dir = os.path.join(os.path.dirname(__file__), 'image_show')
            os.makedirs(save_dir, exist_ok=True)
            filename = f'stock_{int(time.time() * 1000)}.png'
            save_path = os.path.join(save_dir, filename)
            
            generate_chart_png(df, save_path)
            img_path = os.path.join('image_show', filename)
            img_md = f'![股票图表]({img_path})'
            
            return f"{md}\n\n{img_md}"

# ========== 通用可视化函数 ========== 
def generate_chart_png(df_sql, save_path):
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd
    
    columns = df_sql.columns
    
    date_columns = ['交易日期', '日期']
    value_columns = ['收盘价', '开盘价', '最高价', '最低价', '成交量', '成交额', '涨跌幅']
    
    date_col = None
    for col in columns:
        if col in date_columns:
            date_col = col
            break
    
    value_cols = []
    for col in columns:
        if col in value_columns:
            value_cols.append(col)
    
    if date_col and value_cols:
        fig, ax = plt.subplots(figsize=(12, 6))
        
        for col in value_cols[:3]:
            ax.plot(df_sql[date_col], df_sql[col], marker='o', linewidth=2, label=col)
        
        ax.set_title('股票数据趋势', fontsize=14, fontweight='bold')
        ax.set_xlabel(date_col, fontsize=11)
        ax.set_ylabel('数值', fontsize=11)
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3, linestyle='--')
        
        if len(df_sql) > 10:
            plt.xticks(rotation=45, ha='right')
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=100, bbox_inches='tight')
        plt.close()
    else:
        fig, ax = plt.subplots(figsize=(10, 6))
        
        if len(columns) > 1:
            x = np.arange(len(df_sql))
            bottom = np.zeros(len(df_sql))
            
            for col in columns[1:]:
                if pd.api.types.is_numeric_dtype(df_sql[col]):
                    ax.bar(x, df_sql[col], bottom=bottom, label=col)
                    bottom += df_sql[col]
            
            ax.set_title('股票数据统计', fontsize=14, fontweight='bold')
            ax.set_xlabel(columns[0], fontsize=11)
            ax.set_ylabel('数值', fontsize=11)
            ax.legend(loc='best')
            
            if len(df_sql) <= 20:
                ax.set_xticks(x)
                ax.set_xticklabels(df_sql[columns[0]].astype(str), rotation=45, ha='right')
            
            plt.tight_layout()
            plt.savefig(save_path, dpi=100, bbox_inches='tight')
            plt.close()

# ====== 初始化股票助手服务 ======
def init_agent_service():
    print("Initializing agent service...")
    llm_cfg = {
        'model': 'qwen-turbo',
        'timeout': 30,
        'retry_count': 3,
    }
    try:
        print("Creating Assistant...")
        from qwen_agent.agents import Assistant
        bot = Assistant(
            llm=llm_cfg,
            name='股票查询助手',
            description='基于SQLite日线数据的股票查询与可视化（大行数折线图）',
            system_message=system_prompt,
            function_list=['exc_sql'],
        )
        print("股票助手初始化成功！")
        return bot
    except Exception as e:
        print(f"助手初始化失败: {str(e)}")
        traceback.print_exc()
        raise

# ====== 启动 Web 界面 ======
def app_gui():
    try:
        print("正在启动股票查询 Web 界面...")
        bot = init_agent_service()
        
        chatbot_config = {
            'prompt.suggestions': [
                '查询源杰科技最近10天的收盘价',
                '查询中际旭创2024年的最高价和最低价',
                '帮我统计隆基绿能每月平均成交量',
                '查询药明康德最近一年的涨跌幅情况',
                '对比源杰科技和中际旭创的涨跌幅',
                '查询隆基绿能最近20天的成交量',
                '统计药明康德2025年4月的日均成交额',
                '查询源杰科技2024年全年的收盘价走势'
            ]
        }
        
        print("Web 界面准备就绪，正在启动服务...")
        from qwen_agent.gui import WebUI
        print("WebUI imported successfully")
        print("Creating WebUI instance...")
        webui = WebUI(
            bot,
            chatbot_config=chatbot_config
        )
        print("WebUI instance created successfully")
        print("Running WebUI...")
        webui.run()
    except Exception as e:
        print(f"启动 Web 界面失败: {str(e)}")
        traceback.print_exc()

# ====== 终端交互模式 ======
def app_tui():
    try:
        print("Starting TUI...")
        bot = init_agent_service()

        messages = []
        
        print("\n" + "="*50)
        print("股票查询助手已启动！")
        print("="*50)
        print("支持查询以下股票：")
        print("  - 源杰科技 (688498.SH)")
        print("  - 中际旭创 (300308.SZ)")
        print("  - 隆基绿能 (601012.SH)")
        print("  - 药明康德 (603259.SH)")
        print("="*50)
        print("功能：")
        print("  - SQL查询与可视化")
        print("="*50)
        print("\n请在下方输入问题：")
        
        while True:
            try:
                query = input('\n> ').strip()
                
                if not query:
                    continue
                
                if query.lower() in ['quit', 'exit', 'q']:
                    print("感谢使用，再见！")
                    break
                    
                messages.append({'role': 'user', 'content': query})

                print("\n正在处理...\n")
                response = []
                for response in bot.run(messages):
                    pass
                messages.extend(response)
                
                for msg in response:
                    if msg.get('role') == 'assistant':
                        content = msg.get('content', '')
                        if isinstance(content, list):
                            for item in content:
                                if isinstance(item, dict):
                                    if item.get('text'):
                                        print(item['text'])
                                    elif item.get('image'):
                                        print(f"[图片: {item['image']}]")
                        else:
                            print(content)
                
            except KeyboardInterrupt:
                print("\n\n感谢使用，再见！")
                break
            except Exception as e:
                print(f"处理请求时出错: {str(e)}")
                print("请重试或输入新的问题\n")
    except Exception as e:
        print(f"启动终端模式失败: {str(e)}")
        traceback.print_exc()


if __name__ == '__main__':
    # 检查所有必要的依赖
    required_deps = [
        ('qwen_agent', qwen_agent_available),
        ('WebUI', webui_available),
        ('dashscope', dashscope_available),
        ('pandas', pandas_available),
        ('SQLAlchemy', sqlalchemy_available),
        ('matplotlib', matplotlib_available),
        ('database', db_connected)
    ]
    
    print("\n依赖检查结果:")
    for dep_name, available in required_deps:
        status = "OK" if available else "MISSING"
        print(f"{dep_name}: {status}")
    
    # 启动 Web 界面
    if all([qwen_agent_available, webui_available, dashscope_available, pandas_available, sqlalchemy_available, matplotlib_available, db_connected]):
        print("\n所有依赖检查通过，启动 Web 界面...")
        app_gui()
    else:
        print("\n缺少必要依赖，启动终端模式...")
        app_tui()
