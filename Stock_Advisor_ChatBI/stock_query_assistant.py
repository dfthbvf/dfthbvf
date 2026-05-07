import os
import sys
print(f"Python version: {sys.version}")
print(f"Current directory: {os.getcwd()}")

import asyncio
from typing import Optional
import dashscope

from qwen_agent.agents import Assistant
from qwen_agent.gui import WebUI
from qwen_agent import retrieve
import pandas as pd
from sqlalchemy import create_engine, text
from qwen_agent.tools.base import BaseTool, register_tool
import matplotlib.pyplot as plt
import io
import base64
import time
import numpy as np

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'SimSun', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

ROOT_RESOURCE = os.path.join(os.path.dirname(__file__), 'resource')
DOCUMENTS_DIR = os.path.join(os.path.dirname(__file__), 'documents')
FAQ_FILE = os.path.join(os.path.dirname(__file__), 'faq.txt')

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

注意事项：
1. 股票代码格式：上海证券交易所为 .SH 后缀，深圳证券交易所为 .SZ 后缀
2. 日期格式在数据库中为 YYYYMMDD 格式
3. 成交量单位为股，如果需要转换为手，需要除以 100
4. 可以使用股票名称进行查询，更加直观

示例查询：
1. 查询某只股票在某时间段的收盘价
2. 计算某只股票的最高价/最低价
3. 查询某股票某天的涨跌幅
4. 按日期统计某股票的成交量
5. 对比两支股票的涨跌幅

我将回答用户关于股票相关的问题。如果用户询问的知识在FAQ中有记录，请参考FAQ内容回答。

每当 exc_sql 工具返回 markdown 表格和图片时，你必须原样输出工具返回的全部内容（包括图片 markdown），不要只总结表格，也不要省略图片。这样用户才能直接看到表格和图片。
"""

# ====== 会话隔离 DataFrame 存储 ======
# 用于存储每个会话的 DataFrame，避免多用户数据串扰
_last_df_dict = {}

def get_session_id(kwargs):
    """根据 kwargs 获取当前会话的唯一 session_id，这里用 messages 的 id"""
    messages = kwargs.get('messages')
    if messages is not None:
        return id(messages)
    return None

# ====== exc_sql 工具类实现 ======
@register_tool('exc_sql')
class ExcSQLTool(BaseTool):
    """
    SQL查询工具，执行传入的SQL语句并返回结果，并自动进行可视化。
    """
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
        from sqlalchemy import text  # 导入text类型用于处理原生SQL
        
        # 获取session_id用于数据隔离
        session_id = get_session_id(kwargs)
        
        args = json.loads(params)
        sql_input = args['sql_input']
        print('sql_input=', sql_input)
        
        # 连接SQLite数据库
        engine = create_engine('sqlite:///stock_data.db')
        
        # 使用 SQLAlchemy 的 text() 包装 SQL 语句，避免格式化问题
        df = pd.read_sql(text(sql_input), engine)
        print('df=', df)
        
        # 将DataFrame存储到会话中
        if session_id:
            _last_df_dict[session_id] = df
        
        # 增加显示行数，避免截断重要数据
        display_rows = min(len(df), 100)
        md = df.head(display_rows).to_markdown(index=False)
        
        # 自动创建目录
        save_dir = os.path.join(os.path.dirname(__file__), 'image_show')
        os.makedirs(save_dir, exist_ok=True)
        filename = f'stock_{int(time.time() * 1000)}.png'
        save_path = os.path.join(save_dir, filename)
        
        # 生成图表
        generate_chart_png(df, save_path)
        img_path = os.path.join('image_show', filename)
        img_md = f'![股票图表]({img_path})'
        
        return f"{md}\n\n{img_md}"

# ========== 通用可视化函数 ========== 
def generate_chart_png(df_sql, save_path):
    columns = df_sql.columns.tolist()
    
    date_columns = ['交易日期', '日期']
    value_columns = ['收盘价', '开盘价', '最高价', '最低价', '成交量', '成交额', '涨跌幅']
    stock_columns = ['股票名称', '股票代码', '名称']
    
    date_col = None
    for col in columns:
        if col in date_columns:
            date_col = col
            break
    
    stock_col = None
    for col in columns:
        if col in stock_columns:
            stock_col = col
            break
    
    stock_value_cols = []
    for col in columns:
        if any(stock_name in col for stock_name in ['源杰科技', '中际旭创', '隆基绿能', '药明康德']):
            if '收盘价' in col or '开盘价' in col or '最高价' in col or '最低价' in col or '成交量' in col:
                stock_value_cols.append(col)
    
    value_cols = []
    for col in columns:
        if col in value_columns:
            value_cols.append(col)
    
    if date_col and (value_cols or stock_value_cols):
        fig, ax = plt.subplots(figsize=(14, 7))
        
        colors = ['#1890ff', '#52c41a', '#faad14', '#f5222d', '#722ed1', '#eb2f96']
        markers = ['o', 's', '^', 'D', 'v', 'p']
        
        if stock_value_cols:
            df_plot = df_sql.copy()
            df_plot[date_col] = pd.to_datetime(df_plot[date_col])
            df_plot = df_plot.sort_values(by=date_col)
            
            df_plot = df_plot.set_index(date_col)
            for col in stock_value_cols:
                df_plot[col] = pd.to_numeric(df_plot[col], errors='coerce')
            df_plot = df_plot[stock_value_cols]
            df_plot = df_plot.ffill().bfill()
            df_plot = df_plot.reset_index()
            
            for idx, col in enumerate(stock_value_cols):
                color = colors[idx % len(colors)]
                marker = markers[idx % len(markers)]
                valid_data = df_plot.dropna(subset=[col])
                ax.plot(valid_data[date_col], valid_data[col], 
                       marker=marker, linewidth=2, 
                       label=col, 
                       color=color,
                       markersize=4)
            
            ax.set_title('股票对比趋势', fontsize=14, fontweight='bold')
        elif stock_col:
            df_plot = df_sql.copy()
            df_plot[date_col] = pd.to_datetime(df_plot[date_col])
            df_plot = df_plot.sort_values(by=date_col)
            
            unique_stocks = df_plot[stock_col].unique()
            
            if len(unique_stocks) > 1:
                for idx, stock_name in enumerate(unique_stocks):
                    stock_data = df_plot[df_plot[stock_col] == stock_name].copy()
                    color = colors[idx % len(colors)]
                    marker = markers[idx % len(markers)]
                    
                    for col in value_cols[:2]:
                        valid_data = stock_data.dropna(subset=[col])
                        ax.plot(valid_data[date_col], valid_data[col], 
                               marker=marker, linewidth=2, 
                               label=f'{stock_name}-{col}', 
                               color=color,
                               markersize=4)
                
                ax.set_title('股票对比趋势', fontsize=14, fontweight='bold')
            else:
                for col in value_cols[:3]:
                    valid_data = df_plot.dropna(subset=[col])
                    ax.plot(valid_data[date_col], valid_data[col], marker='o', linewidth=2, label=col)
                ax.set_title('股票数据趋势', fontsize=14, fontweight='bold')
        else:
            df_plot = df_sql.copy()
            df_plot[date_col] = pd.to_datetime(df_plot[date_col])
            df_plot = df_plot.sort_values(by=date_col)
            
            for col in value_cols[:3]:
                valid_data = df_plot.dropna(subset=[col])
                ax.plot(valid_data[date_col], valid_data[col], marker='o', linewidth=2, label=col)
            ax.set_title('股票数据趋势', fontsize=14, fontweight='bold')
        
        ax.set_xlabel(date_col, fontsize=11)
        ax.set_ylabel('数值', fontsize=11)
        ax.legend(loc='best', fontsize=9)
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

# ====== 初始化知识库 ======
def init_knowledge_base():
    """初始化知识库索引"""
    try:
        if os.path.exists(FAQ_FILE):
            print(f"正在加载知识库文件: {FAQ_FILE}")
            retrieve.build_index(os.path.dirname(FAQ_FILE))
            print("知识库索引构建成功！")
        else:
            print(f"知识库文件不存在: {FAQ_FILE}")
    except Exception as e:
        print(f"知识库初始化失败: {str(e)}")

# ====== 自定义助手类 - 集成知识库检索 ======
class StockAssistant(Assistant):
    """股票查询助手 - 集成知识库检索"""
    
    def _preprocess(self, query: str, **kwargs):
        """预处理用户查询，检索知识库作为上下文"""
        try:
            contexts = retrieve.search(query, top_n=3)
            if contexts:
                context_text = "\n\n".join(contexts)
                enhanced_query = f"""基于以下知识库信息回答用户问题：

{context_text}

用户问题：{query}

请根据知识库中的信息来回答问题，如果知识库中没有相关信息，请基于你已有的知识回答。"""
                return enhanced_query
        except Exception as e:
            print(f"知识库检索失败: {str(e)}")
        return query

# ====== 初始化股票助手服务 ======
def init_agent_service():
    """初始化股票助手服务"""
    print("Initializing agent service...")
    
    init_knowledge_base()
    
    llm_cfg = {
        'model': 'qwen-turbo',
        'timeout': 30,
        'retry_count': 3,
    }
    try:
        print("Creating Assistant...")
        bot = StockAssistant(
            llm=llm_cfg,
            name='股票查询助手',
            description='基于SQLite的股票历史价格查询与分析',
            system_message=system_prompt,
            function_list=['exc_sql'],
        )
        print("股票助手初始化成功！")
        return bot
    except Exception as e:
        print(f"助手初始化失败: {str(e)}")
        raise

# ====== 启动 Web 界面 ======
def app_gui():
    """Web交互模式
    
    提供网页界面，支持：
    - 可视化交互
    - 历史记录
    - 示例问题
    """
    try:
        print("正在启动股票查询 Web 界面...")
        # 初始化助手
        bot = init_agent_service()
        
        # 配置聊天界面
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
        print("WebUI class loaded successfully")
        
        # 启动WebUI
        print("Creating WebUI instance...")
        webui = WebUI(
            bot,
            chatbot_config=chatbot_config
        )
        print("WebUI instance created successfully")
        
        print("Starting WebUI server...")
        print("Web server will be available at: http://localhost:8080")
        webui.run()
        print("WebUI server started")
    except Exception as e:
        print(f"启动 Web 界面失败: {str(e)}")
        import traceback
        traceback.print_exc()


def app_tui():
    """终端交互模式
    
    提供命令行交互界面，支持：
    - 连续对话
    - 实时响应
    """
    try:
        print("Starting TUI...")
        # 初始化助手
        bot = init_agent_service()

        # 对话历史
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
                # 获取用户输入
                query = input('\n> ').strip()
                
                # 输入验证
                if not query:
                    continue
                
                if query.lower() in ['quit', 'exit', 'q']:
                    print("感谢使用，再见！")
                    break
                    
                # 构建消息
                messages.append({'role': 'user', 'content': query})

                print("\n正在处理...\n")
                # 运行助手并处理响应
                response = []
                for response in bot.run(messages):
                    pass
                messages.extend(response)
                
                # 输出响应
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


if __name__ == '__main__':
    # 运行Web交互模式
    app_gui()
