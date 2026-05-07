import os
import asyncio
from typing import Optional
import dashscope
from qwen_agent.agents import Assistant
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

dashscope.api_key = 'sk-da44331e91c04018af6dd0daecb39bdc'
dashscope.timeout = 30

system_prompt = """我是股票查询助手，以下是关于股票价格表相关的字段，我可能会编写对应的SQL，对数据进行查询
-- 股票价格表
CREATE TABLE stock_price (
    交易日期 VARCHAR(10),     -- 交易日期，格式：YYYYMMDD
    股票代码 VARCHAR(20),     -- 股票代码，如：600519.SH
    股票名称 VARCHAR(50),     -- 股票名称
    开盘价 DECIMAL(10,2),    -- 开盘价
    最高价 DECIMAL(10,2),    -- 最高价
    最低价 DECIMAL(10,2),    -- 最低价
    收盘价 DECIMAL(10,2),    -- 收盘价
    前收价 DECIMAL(10,2),    -- 前一天收盘价
    涨跌额 DECIMAL(10,2),    -- 涨跌额
    涨跌幅 DECIMAL(10,4),    -- 涨跌幅
    成交量 BIGINT,           -- 成交量
    成交额 DECIMAL(20,2)    -- 成交额
);

支持的股票：
- 贵州茅台 (600519.SH)
- 五粮液 (000858.SZ)
- 广发证券 (000776.SZ)
- 中芯国际 (688981.SH)

数据时间范围：2020-01-01 至今

示例查询：
1. 查询某只股票在某时间段的收盘价
2. 计算某只股票的最高价/最低价
3. 查询某股票某天的涨跌幅
4. 按日期统计某股票的成交量

我将回答用户关于股票相关的问题

每当 exc_sql 工具返回 markdown 表格和图片时，你必须原样输出工具返回的全部内容（包括图片），不要只总结表格，也不要省略图片。这样用户才能直接看到表格和图片。
"""

_last_df_dict = {}

def get_session_id(kwargs):
    messages = kwargs.get('messages')
    if messages is not None:
        return id(messages)
    return None


def sample_data(df, max_points=10):
    if len(df) <= max_points:
        return df
    indices = np.linspace(0, len(df) - 1, max_points, dtype=int)
    return df.iloc[indices].reset_index(drop=True)


def generate_chart_png(df_sql, save_path, max_points=10):
    if len(df_sql) == 0:
        return None
    
    df = sample_data(df_sql.copy(), max_points)
    
    columns = df.columns.tolist()
    
    object_columns = df.select_dtypes(include=['object', 'string']).columns.tolist()
    num_columns = df.select_dtypes(include=[np.number]).columns.tolist()
    
    fig, ax = plt.subplots(figsize=(14, 7))
    
    if '交易日期' in object_columns:
        x_col = '交易日期'
    elif object_columns:
        x_col = object_columns[0]
    else:
        x_col = columns[0]
    
    x_labels = df[x_col].astype(str).tolist()
    x = np.arange(len(df))
    
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
    
    if len(num_columns) > 0:
        plot_num = min(len(num_columns), 3)
        
        for i in range(plot_num):
            col = num_columns[i]
            label = str(col)
            ax.plot(x, df[col], marker='o', linewidth=2.5, markersize=8, 
                   label=label, color=colors[i % len(colors)])
        
        ax.set_xticks(x)
        ax.set_xticklabels(x_labels, rotation=45, ha='right', fontsize=9)
        ax.legend(loc='best', fontsize=10)
        ax.set_ylabel('数值', fontsize=11)
    else:
        if len(object_columns) >= 2 and len(num_columns) > 0:
            pivot_df = df.pivot_table(index=x_col, values=num_columns[0], aggfunc='sum', dropna=False)
            pivot_df = pivot_df.reset_index()
            
            ax.plot(range(len(pivot_df)), pivot_df[num_columns[0]], 
                   marker='o', linewidth=2.5, markersize=8, color=colors[0])
            
            ax.set_xticks(range(len(pivot_df)))
            ax.set_xticklabels(pivot_df[x_col].astype(str), rotation=45, ha='right', fontsize=9)
    
    ax.set_xlabel(str(x_col), fontsize=11)
    ax.set_title('股票数据统计', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, linestyle='--')
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=100, bbox_inches='tight')
    plt.close()
    
    return save_path


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
        
        if len(df) > 0:
            save_dir = os.path.join(os.path.dirname(__file__), 'image_show')
            os.makedirs(save_dir, exist_ok=True)
            filename = f'stock_chart_{int(time.time() * 1000)}.png'
            save_path = os.path.join(save_dir, filename)
            
            chart_path = generate_chart_png(df, save_path, max_points=10)
            
            if chart_path:
                img_path = os.path.join('image_show', filename)
                img_md = f'\n\n![股票图表]({img_path})\n'
                return f"{md}{img_md}"
        
        return md


def init_agent_service():
    llm_cfg = {
        'model': 'qwen-turbo',
        'timeout': 30,
        'retry_count': 3,
    }
    try:
        faq_file = os.path.join(os.path.dirname(__file__), 'faq.txt')
        bot = Assistant(
            llm=llm_cfg,
            name='股票查询助手',
            description='基于 SQLite 日线数据的股票查询与可视化（大行数折线图）',
            system_message=system_prompt,
            function_list=['exc_sql'],
            files=[faq_file]
        )
        print("股票助手初始化成功！")
        return bot
    except Exception as e:
        print(f"助手初始化失败: {str(e)}")
        raise


def main():
    try:
        bot = init_agent_service()
        messages = []
        
        print("\n" + "="*50)
        print("股票查询助手已启动！")
        print("="*50)
        print("支持查询以下股票：")
        print("  - 贵州茅台 (600519.SH)")
        print("  - 五粮液 (000858.SZ)")
        print("  - 广发证券 (000776.SZ)")
        print("  - 中芯国际 (688981.SH)")
        print("="*50)
        print("\n输入问题进行查询，输入 'quit' 或 'exit' 退出")
        print("-"*50 + "\n")
        
        while True:
            try:
                query = input('请输入问题: ').strip()
                
                if not query:
                    print("问题不能为空！")
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
                
                print("\n" + "-"*50 + "\n")
                
            except KeyboardInterrupt:
                print("\n\n感谢使用，再见！")
                break
            except Exception as e:
                print(f"处理请求时出错: {str(e)}")
                print("请重试或输入新的问题\n")
                
    except Exception as e:
        print(f"启动失败: {str(e)}")


if __name__ == '__main__':
    main()
