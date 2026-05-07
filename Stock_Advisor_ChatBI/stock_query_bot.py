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

每当 exc_sql 工具返回 markdown 表格时，你必须原样输出工具返回的全部内容，不要只总结表格。这样用户才能直接看到表格。
"""

_last_df_dict = {}

def get_session_id(kwargs):
    messages = kwargs.get('messages')
    if messages is not None:
        return id(messages)
    return None

@register_tool('exc_sql')
class ExcSQLTool(BaseTool):
    description = '对于生成的SQL，进行SQL查询'
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
        return md


def init_agent_service():
    llm_cfg = {
        'model': 'qwen-turbo',
        'timeout': 30,
        'retry_count': 3,
    }
    try:
        bot = Assistant(
            llm=llm_cfg,
            name='股票查询助手',
            description='股票历史价格查询与分析',
            system_message=system_prompt,
            function_list=['exc_sql'],
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
