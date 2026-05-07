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
from datetime import datetime, timedelta

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

ARIMA预测功能：
- 使用arima_stock工具可以对股票未来价格进行预测
- 参数ts_code是必填的股票代码
- 参数n是可选的预测天数，默认5天
- ARIMA模型参数为(5,1,5)
- 使用过去一年的历史数据进行建模

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


def generate_chart_png(df_sql, save_path, max_points=10, title='股票数据统计'):
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
    ax.set_title(title, fontsize=14, fontweight='bold')
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


def get_one_year_data(ts_code):
    engine = create_engine('sqlite:///stock_data.db')
    
    one_year_ago = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
    
    sql = f"""
    SELECT 交易日期, 收盘价 
    FROM stock_price 
    WHERE 股票代码 = '{ts_code}' 
    AND 交易日期 >= '{one_year_ago}'
    ORDER BY 交易日期 ASC
    """
    
    df = pd.read_sql(text(sql), engine)
    return df


def arima_predict(ts_code, n=5):
    try:
        from statsmodels.tsa.arima.model import ARIMA
    except ImportError:
        return None, "请安装 statsmodels 库: pip install statsmodels"
    
    df = get_one_year_data(ts_code)
    
    if df is None or len(df) == 0:
        return None, f"未找到股票 {ts_code} 的历史数据"
    
    if len(df) < 50:
        return None, f"数据量不足，需要至少50天的数据，当前只有 {len(df)} 天"
    
    close_prices = df['收盘价'].values
    
    try:
        model = ARIMA(close_prices, order=(5, 1, 5))
        model_fit = model.fit()
        
        forecast = model_fit.forecast(steps=n)
        
        last_date_str = df['交易日期'].iloc[-1]
        last_date = datetime.strptime(last_date_str, '%Y%m%d')
        
        future_dates = []
        current_date = last_date
        for i in range(n):
            current_date += timedelta(days=1)
            while current_date.weekday() >= 5:
                current_date += timedelta(days=1)
            future_dates.append(current_date.strftime('%Y%m%d'))
        
        result_df = pd.DataFrame({
            '预测日期': future_dates,
            '预测收盘价': np.round(forecast, 2)
        })
        
        return result_df, None
    except Exception as e:
        return None, f"ARIMA模型训练失败: {str(e)}"


@register_tool('arima_stock')
class ArimaStockTool(BaseTool):
    description = '使用ARIMA模型对股票未来价格进行预测'
    parameters = [{
        'name': 'ts_code',
        'type': 'string',
        'description': '股票代码，如 600519.SH（必填）',
        'required': True
    }, {
        'name': 'n',
        'type': 'integer',
        'description': '预测天数，默认为5天',
        'required': False
    }]

    def call(self, params: str, **kwargs) -> str:
        import json
        import os
        import time
        
        args = json.loads(params)
        ts_code = args.get('ts_code')
        n = args.get('n', 5)
        
        if not ts_code:
            return "错误：股票代码(ts_code)是必填参数"
        
        print(f"ARIMA预测: ts_code={ts_code}, n={n}")
        
        result_df, error = arima_predict(ts_code, n)
        
        if error:
            return f"预测失败: {error}"
        
        md = result_df.to_markdown(index=False)
        
        save_dir = os.path.join(os.path.dirname(__file__), 'image_show')
        os.makedirs(save_dir, exist_ok=True)
        filename = f'arima_forecast_{int(time.time() * 1000)}.png'
        save_path = os.path.join(save_dir, filename)
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        x = np.arange(len(result_df))
        ax.plot(x, result_df['预测收盘价'], marker='o', linewidth=2.5, 
               markersize=10, color='#ff7f0e', label='预测价格')
        
        ax.set_xticks(x)
        ax.set_xticklabels(result_df['预测日期'], rotation=45, ha='right', fontsize=10)
        ax.set_xlabel('预测日期', fontsize=11)
        ax.set_ylabel('预测收盘价 (元)', fontsize=11)
        ax.set_title(f'ARIMA预测 - {ts_code} 未来{n}天收盘价', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.legend(fontsize=10)
        
        for i, price in enumerate(result_df['预测收盘价']):
            ax.annotate(f'{price}', (i, price), textcoords="offset points", 
                       xytext=(0,10), ha='center', fontsize=9)
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=100, bbox_inches='tight')
        plt.close()
        
        img_path = os.path.join('image_show', filename)
        img_md = f'\n\n![ARIMA预测图表]({img_path})\n'
        
        return f"{md}{img_md}"


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
            description='基于 SQLite 日线数据的股票查询与可视化，支持ARIMA预测',
            system_message=system_prompt,
            function_list=['exc_sql', 'arima_stock'],
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
        print("功能：")
        print("  - SQL查询与可视化")
        print("  - ARIMA股票价格预测")
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
        print(f"启动失败: {str(e)}")


if __name__ == '__main__':
    main()
