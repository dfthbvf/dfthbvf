import os
import sys
import json
from flask import Flask, request, render_template, jsonify
import pandas as pd
from sqlalchemy import create_engine, text
import matplotlib.pyplot as plt
import base64
import io
import time
import numpy as np
import dashscope

# 解决中文显示问题
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'SimSun', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

# 配置DashScope API
dashscope.api_key = 'sk-da44331e91c04018af6dd0daecb39bdc'

app = Flask(__name__)

# AI分析函数
def analyze_with_ai(user_query, df, desc_df):
    """使用通义千问分析股票数据并给出建议"""
    try:
        # 检查是否有多个股票
        stock_codes = df['股票代码'].unique() if '股票代码' in df.columns else []
        is_comparison = len(stock_codes) > 1
        
        # 构建提示词
        if is_comparison:
            prompt = f"""你是一位专业的股票分析师。请根据以下数据对比分析两只股票，并给出专业的投资建议。

用户问题：{user_query}

数据表格（按股票分组显示）：
{df.to_string()}

数据统计描述：
{desc_df.to_string() if desc_df is not None else '无'}

请进行分析并给出：
1. 两只股票的走势对比分析
2. 关键指标对比（如涨跌幅、波动性等）
3. 两支股票的优劣势分析
4. 投资建议（仅供参考，不构成投资建议）

请用简洁专业的语言回答，重点突出对比分析。"""
        else:
            prompt = f"""你是一位专业的股票分析师。请根据以下数据和用户问题，给出专业的分析和投资建议。

用户问题：{user_query}

数据表格（前10行）：
{df.head(10).to_string()}

数据统计描述：
{desc_df.to_string() if desc_df is not None else '无'}

请进行分析并给出：
1. 数据趋势分析
2. 关键指标解读
3. 投资建议（仅供参考，不构成投资建议）

请用简洁专业的语言回答。"""
        
        # 调用通义千问API
        response = dashscope.Generation.call(
            model='qwen-turbo',
            prompt=prompt,
            max_tokens=600,
            temperature=0.7
        )
        
        if response.status_code == 200:
            return response.output['text']
        else:
            return None
    except Exception as e:
        print(f"AI分析错误: {e}")
        return None

# 数据库连接
def get_db_engine():
    return create_engine('sqlite:///stock_data.db')

# 生成图表
def generate_chart(df):
    columns = df.columns
    
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
            ax.plot(df[date_col], df[col], marker='o', linewidth=2, label=col)
        
        ax.set_title('股票数据趋势', fontsize=14, fontweight='bold')
        ax.set_xlabel(date_col, fontsize=11)
        ax.set_ylabel('数值', fontsize=11)
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3, linestyle='--')
        
        if len(df) > 10:
            plt.xticks(rotation=45, ha='right')
        
        plt.tight_layout()
    else:
        fig, ax = plt.subplots(figsize=(10, 6))
        
        if len(columns) > 1:
            x = np.arange(len(df))
            bottom = np.zeros(len(df))
            
            for col in columns[1:]:
                if pd.api.types.is_numeric_dtype(df[col]):
                    ax.bar(x, df[col], bottom=bottom, label=col)
                    bottom += df[col]
            
            ax.set_title('股票数据统计', fontsize=14, fontweight='bold')
            ax.set_xlabel(columns[0], fontsize=11)
            ax.set_ylabel('数值', fontsize=11)
            ax.legend(loc='best')
            
            if len(df) <= 20:
                ax.set_xticks(x)
                ax.set_xticklabels(df[columns[0]].astype(str), rotation=45, ha='right')
            
            plt.tight_layout()
    
    # 转换为base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
    plt.close()
    
    return f'data:image/png;base64,{image_base64}'

# 执行SQL查询
def execute_sql(sql):
    engine = get_db_engine()
    df = pd.read_sql(text(sql), engine)
    return df

# 生成SQL查询
def generate_sql(query):
    import datetime
    query = query.lower()
    
    # 获取当前日期
    current_date = datetime.datetime.now()
    current_year = current_date.year
    current_month = current_date.month
    current_date_str = current_date.strftime('%Y%m%d')
    
    # 检查是否包含股票名称 - 支持多支股票
    stocks = {
        '源杰科技': '688498.SH',
        '中际旭创': '300308.SZ',
        '隆基绿能': '601012.SH',
        '药明康德': '603259.SH'
    }
    
    # 查找所有匹配的股票
    stock_codes = []
    stock_names = []
    for name, code in stocks.items():
        if name in query:
            stock_codes.append(code)
            stock_names.append(name)
    
    # 如果没有匹配到任何股票，使用默认股票
    if not stock_codes:
        stock_codes = ['688498.SH']
        stock_names = ['源杰科技']
    
    # 检查时间范围 - 按优先级判断(年份+月份)
    start_date = None
    end_date = None
    
    # 优先检查年份+月份的组合
    if '2026年4月' in query or '2026年04月' in query:
        start_date = '20260401'
        end_date = '20260430'
    elif '2026年3月' in query or '2026年03月' in query:
        start_date = '20260301'
        end_date = '20260331'
    elif '2026年2月' in query or '2026年02月' in query or '2026年正月' in query:
        start_date = '20260201'
        end_date = '20260228'
    elif '2026年1月' in query or '2026年01月' in query:
        start_date = '20260101'
        end_date = '20260131'
    elif '2025年12月' in query or '2025年12月份' in query:
        start_date = '20251201'
        end_date = '20251231'
    elif '2025年11月' in query or '2025年11月份' in query:
        start_date = '20251101'
        end_date = '20251130'
    elif '2025年10月' in query or '2025年10月份' in query:
        start_date = '20251001'
        end_date = '20251031'
    elif '2025年9月' in query or '2025年09月' in query or '2025年9月份' in query:
        start_date = '20250901'
        end_date = '20250930'
    elif '2025年8月' in query or '2025年08月' in query:
        start_date = '20250801'
        end_date = '20250831'
    elif '2025年7月' in query or '2025年07月' in query:
        start_date = '20250701'
        end_date = '20250731'
    elif '2025年6月' in query or '2025年06月' in query:
        start_date = '20250601'
        end_date = '20250630'
    elif '2025年5月' in query or '2025年05月' in query:
        start_date = '20250501'
        end_date = '20250531'
    elif '2025年4月' in query or '2025年04月' in query:
        start_date = '20250401'
        end_date = '20250430'
    elif '2025年3月' in query or '2025年03月' in query:
        start_date = '20250301'
        end_date = '20250331'
    elif '2025年2月' in query or '2025年02月' in query:
        start_date = '20250201'
        end_date = '20250228'
    elif '2025年1月' in query or '2025年01月' in query:
        start_date = '20250101'
        end_date = '20250131'
    # 检查年份
    elif '2026' in query:
        start_date = '20260101'
        end_date = current_date_str
    elif '2025' in query:
        start_date = '20250101'
        end_date = '20251231'
    elif '2024' in query:
        start_date = '20240101'
        end_date = '20241231'
    elif '2023' in query:
        start_date = '20230101'
        end_date = '20231231'
    elif '2022' in query:
        start_date = '20220101'
        end_date = '20221231'
    else:
        # 默认查询最近一年的数据
        start_date = f'{(current_year - 1)}0101'
        end_date = current_date_str
    
    # 构建SQL - 支持多支股票
    codes_str = "', '".join(stock_codes)
    
    if '收盘价' in query:
        sql = f"""
        SELECT 交易日期, 股票代码, 股票名称, 收盘价 
        FROM stock_price 
        WHERE 股票代码 IN ('{codes_str}') 
        AND 交易日期 BETWEEN '{start_date}' AND '{end_date}' 
        ORDER BY 股票代码, 交易日期
        """
    elif '成交量' in query:
        sql = f"""
        SELECT 交易日期, 股票代码, 股票名称, 成交量 
        FROM stock_price 
        WHERE 股票代码 IN ('{codes_str}') 
        AND 交易日期 BETWEEN '{start_date}' AND '{end_date}' 
        ORDER BY 股票代码, 交易日期
        """
    elif '涨跌幅' in query:
        sql = f"""
        SELECT 交易日期, 股票代码, 股票名称, 涨跌幅 
        FROM stock_price 
        WHERE 股票代码 IN ('{codes_str}') 
        AND 交易日期 BETWEEN '{start_date}' AND '{end_date}' 
        ORDER BY 股票代码, 交易日期
        """
    else:
        sql = f"""
        SELECT 交易日期, 股票代码, 股票名称, 开盘价, 最高价, 最低价, 收盘价 
        FROM stock_price 
        WHERE 股票代码 IN ('{codes_str}') 
        AND 交易日期 BETWEEN '{start_date}' AND '{end_date}' 
        ORDER BY 股票代码, 交易日期
        """
    
    return sql

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/query', methods=['POST'])
def query():
    data = request.json
    user_query = data.get('query', '')
    
    try:
        # 生成SQL
        sql = generate_sql(user_query)
        print(f"Generated SQL: {sql}")
        
        # 执行查询
        df = execute_sql(sql)
        
        if df.empty:
            return jsonify({
                'success': False,
                'message': '未找到数据'
            })
        
        # 生成图表
        chart = generate_chart(df)
        
        # 转换为markdown表格
        table = df.head(20).to_markdown(index=False)
        
        # 生成数据描述统计
        numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
        if len(numeric_cols) > 0:
            desc_df = df[numeric_cols].describe()
            # 保留2位小数，使输出更美观
            desc_df = desc_df.round(2)
            describe = desc_df.to_markdown()
        else:
            desc_df = None
            describe = None
        
        # 调用AI进行分析和建议
        ai_analysis = analyze_with_ai(user_query, df, desc_df)
        
        return jsonify({
            'success': True,
            'table': table,
            'chart': chart,
            'sql': sql,
            'describe': describe,
            'ai_analysis': ai_analysis
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

# 创建模板目录
if not os.path.exists('templates'):
    os.makedirs('templates')

# 创建HTML模板
html_template = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>股票查询助手</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'Helvetica Neue', Helvetica, Arial, sans-serif;
            background-color: #f5f5f5;
            min-height: 100vh;
            color: #333;
        }
        .container-fluid {
            height: 100vh;
            display: flex;
            padding: 0;
        }
        /* 左侧聊天区域 */
        .chat-area {
            flex: 1;
            display: flex;
            flex-direction: column;
            background-color: #fff;
            box-shadow: 2px 0 8px rgba(0,0,0,0.05);
            z-index: 1;
        }
        .chat-header {
            padding: 16px 24px;
            border-bottom: 1px solid #e8e8e8;
            background-color: #fff;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .chat-header h2 {
            margin: 0;
            font-size: 18px;
            font-weight: 600;
            color: #262626;
        }
        .chat-header .subtitle {
            font-size: 12px;
            color: #8c8c8c;
        }
        .chat-messages {
            flex: 1;
            padding: 20px 24px;
            overflow-y: auto;
            background-color: #fafafa;
        }
        .message {
            margin-bottom: 24px;
            display: flex;
            align-items: flex-start;
            animation: fadeIn 0.3s ease;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .message-avatar {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-right: 12px;
            flex-shrink: 0;
            font-size: 18px;
        }
        .user-avatar {
            background: linear-gradient(135deg, #1890ff 0%, #36cfc9 100%);
            color: white;
        }
        .bot-avatar {
            background: linear-gradient(135deg, #722ed1 0%, #eb2f96 100%);
            color: white;
        }
        .message-content {
            flex: 1;
            max-width: 85%;
        }
        .message-bubble {
            padding: 12px 16px;
            border-radius: 8px;
            font-size: 14px;
            line-height: 1.6;
            word-wrap: break-word;
        }
        .user-message .message-bubble {
            background-color: #e6f7ff;
            border: 1px solid #91d5ff;
            color: #262626;
        }
        .bot-message .message-bubble {
            background-color: #fff;
            border: 1px solid #e8e8e8;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        }
        .message-time {
            font-size: 11px;
            color: #bfbfbf;
            margin-top: 4px;
            margin-left: 52px;
        }
        .chat-input-area {
            padding: 16px 24px;
            background-color: #fff;
            border-top: 1px solid #e8e8e8;
        }
        .input-wrapper {
            display: flex;
            gap: 12px;
            align-items: center;
        }
        .input-wrapper input {
            flex: 1;
            padding: 12px 16px;
            border: 1px solid #d9d9d9;
            border-radius: 8px;
            font-size: 14px;
            transition: all 0.3s;
            outline: none;
        }
        .input-wrapper input:focus {
            border-color: #1890ff;
            box-shadow: 0 0 0 2px rgba(24,144,255,0.2);
        }
        .input-wrapper input::placeholder {
            color: #bfbfbf;
        }
        .send-btn {
            padding: 12px 24px;
            background: linear-gradient(135deg, #722ed1 0%, #eb2f96 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .send-btn:hover {
            opacity: 0.9;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(114,46,209,0.3);
        }
        .send-btn:active {
            transform: translateY(0);
        }
        /* 右侧信息面板 */
        .info-panel {
            flex: 0 0 360px;
            background-color: #fff;
            border-left: 1px solid #e8e8e8;
            overflow-y: auto;
        }
        .assistant-card {
            padding: 32px 24px;
            text-align: center;
            border-bottom: 1px solid #f0f0f0;
        }
        .assistant-logo {
            width: 80px;
            height: 80px;
            margin: 0 auto 16px;
            background: linear-gradient(135deg, #722ed1 0%, #eb2f96 100%);
            border-radius: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 8px 24px rgba(114,46,209,0.25);
        }
        .assistant-logo i {
            font-size: 36px;
            color: white;
        }
        .assistant-card h3 {
            margin: 0 0 8px 0;
            font-size: 18px;
            font-weight: 600;
            color: #262626;
        }
        .assistant-card p {
            margin: 0;
            font-size: 13px;
            color: #8c8c8c;
            line-height: 1.6;
        }
        .section {
            padding: 20px 24px;
            border-bottom: 1px solid #f0f0f0;
        }
        .section-title {
            font-size: 14px;
            font-weight: 600;
            color: #262626;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .section-title i {
            color: #722ed1;
        }
        .plugin-list {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }
        .plugin-tag {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 12px;
            background-color: #f6ffed;
            border: 1px solid #b7eb8f;
            border-radius: 4px;
            font-size: 12px;
            color: #52c41a;
        }
        .plugin-tag i {
            font-size: 10px;
        }
        .example-list {
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        .example-item {
            padding: 12px 16px;
            background-color: #fafafa;
            border: 1px solid #f0f0f0;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .example-item:hover {
            background-color: #f0f5ff;
            border-color: #adc6ff;
            transform: translateX(4px);
        }
        .example-item i {
            color: #722ed1;
            font-size: 12px;
        }
        .example-item span {
            font-size: 13px;
            color: #595959;
            line-height: 1.5;
        }
        /* 图表和表格 */
        .chart-container {
            margin: 16px 0;
            text-align: center;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }
        .chart-container img {
            width: 100%;
            height: auto;
            display: block;
        }
        .table-container {
            margin: 16px 0;
            overflow-x: auto;
            background-color: #fff;
            border-radius: 8px;
            border: 1px solid #f0f0f0;
        }
        .table-container pre {
            padding: 16px;
            margin: 0;
            font-size: 12px;
            line-height: 1.6;
            background-color: #fafafa;
            border: none;
        }
        .sql-block {
            margin-top: 12px;
            padding: 12px;
            background-color: #f6ffed;
            border: 1px solid #b7eb8f;
            border-radius: 6px;
        }
        .sql-block small {
            display: block;
            color: #52c41a;
            font-weight: 500;
            font-size: 11px;
            margin-bottom: 6px;
        }
        .sql-block pre {
            padding: 0;
            margin: 0;
            font-size: 11px;
            color: #595959;
            background: transparent;
            border: none;
        }
        .describe-block {
            margin-top: 12px;
            padding: 12px;
            background-color: #e6f7ff;
            border: 1px solid #91d5ff;
            border-radius: 6px;
        }
        .describe-block small {
            display: block;
            color: #1890ff;
            font-weight: 500;
            font-size: 11px;
            margin-bottom: 6px;
        }
        .describe-block pre {
            padding: 0;
            margin: 0;
            font-size: 11px;
            color: #595959;
            background: transparent;
            border: none;
        }
        .ai-analysis-block {
            margin-top: 12px;
            padding: 16px;
            background: linear-gradient(135deg, #f5f7fa 0%, #e4e8f0 100%);
            border: 1px solid #d0d7de;
            border-radius: 8px;
        }
        .ai-analysis-block small {
            display: flex;
            align-items: center;
            gap: 6px;
            color: #722ed1;
            font-weight: 600;
            font-size: 12px;
            margin-bottom: 10px;
        }
        .ai-analysis-block .ai-content {
            font-size: 13px;
            color: #262626;
            line-height: 1.7;
            white-space: pre-wrap;
            word-wrap: break-word;
        }
        /* 加载和错误 */
        .loading {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 16px;
            color: #8c8c8c;
            font-size: 13px;
        }
        .loading-spinner {
            width: 20px;
            height: 20px;
            border: 2px solid #f0f0f0;
            border-top-color: #722ed1;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        .error-message {
            color: #cf1322;
            background-color: #fff1f0;
            border: 1px solid #ffa39e;
            border-radius: 6px;
            padding: 12px 16px;
            font-size: 13px;
        }
        /* 欢迎消息 */
        .welcome-content {
            padding: 8px 0;
        }
        .welcome-content h5 {
            font-size: 15px;
            font-weight: 600;
            color: #262626;
            margin-bottom: 12px;
        }
        .welcome-content p {
            color: #595959;
            margin-bottom: 12px;
            font-size: 13px;
        }
        .welcome-content ul {
            margin: 0;
            padding-left: 20px;
            color: #595959;
            font-size: 13px;
        }
        .welcome-content li {
            margin-bottom: 6px;
        }
        /* 滚动条样式 */
        .chat-messages::-webkit-scrollbar,
        .info-panel::-webkit-scrollbar {
            width: 6px;
        }
        .chat-messages::-webkit-scrollbar-track,
        .info-panel::-webkit-scrollbar-track {
            background: transparent;
        }
        .chat-messages::-webkit-scrollbar-thumb,
        .info-panel::-webkit-scrollbar-thumb {
            background: #d9d9d9;
            border-radius: 3px;
        }
        .chat-messages::-webkit-scrollbar-thumb:hover,
        .info-panel::-webkit-scrollbar-thumb:hover {
            background: #bfbfbf;
        }
        /* 响应式设计 */
        @media (max-width: 992px) {
            .container-fluid {
                flex-direction: column;
            }
            .info-panel {
                flex: none;
                height: 300px;
                border-left: none;
                border-top: 1px solid #e8e8e8;
            }
        }
    </style>
</head>
<body>
    <div class="container-fluid">
        <!-- 左侧聊天区域 -->
        <div class="chat-area">
            <div class="chat-header">
                <div>
                    <h2>股票查询助手</h2>
                    <span class="subtitle">基于SQLite的智能股票分析</span>
                </div>
            </div>
            <div id="chat-messages" class="chat-messages">
                <!-- 消息将在这里显示 -->
            </div>
            <div class="chat-input-area">
                <form id="query-form" class="input-wrapper">
                    <input type="text" id="user-query" placeholder="请输入您的问题，例如：查询源杰科技的收盘价...">
                    <button type="submit" class="send-btn">
                        <i class="fas fa-paper-plane"></i>
                        发送
                    </button>
                </form>
            </div>
        </div>
        
        <!-- 右侧信息面板 -->
        <div class="info-panel">
            <div class="assistant-card">
                <div class="assistant-logo">
                    <i class="fas fa-chart-line"></i>
                </div>
                <h3>股票查询助手</h3>
                <p>基于SQLite日线数据的股票查询与可视化<br>支持大行情折线图展示</p>
            </div>
            
            <div class="section">
                <div class="section-title">
                    <i class="fas fa-plug"></i>
                    可用插件
                </div>
                <div class="plugin-list">
                    <span class="plugin-tag">
                        <i class="fas fa-check-circle"></i>
                        enc_sql
                    </span>
                    <span class="plugin-tag">
                        <i class="fas fa-check-circle"></i>
                        tavily-search
                    </span>
                    <span class="plugin-tag">
                        <i class="fas fa-check-circle"></i>
                        tavily-extract
                    </span>
                </div>
            </div>
            
            <div class="section">
                <div class="section-title">
                    <i class="fas fa-lightbulb"></i>
                    推荐对话
                </div>
                <div class="example-list">
                    <div class="example-item" onclick="setQuery('查询源杰科技最近10天的收盘价')">
                        <i class="fas fa-chevron-right"></i>
                        <span>查询源杰科技最近10天的收盘价</span>
                    </div>
                    <div class="example-item" onclick="setQuery('查询中际旭创2024年的最高价和最低价')">
                        <i class="fas fa-chevron-right"></i>
                        <span>查询中际旭创2024年的最高价和最低价</span>
                    </div>
                    <div class="example-item" onclick="setQuery('帮我统计隆基绿能每月平均成交量')">
                        <i class="fas fa-chevron-right"></i>
                        <span>帮我统计隆基绿能每月平均成交量</span>
                    </div>
                    <div class="example-item" onclick="setQuery('查询药明康德最近一年的涨跌幅情况')">
                        <i class="fas fa-chevron-right"></i>
                        <span>查询药明康德最近一年的涨跌幅情况</span>
                    </div>
                    <div class="example-item" onclick="setQuery('对比源杰科技和中际旭创的涨跌幅')">
                        <i class="fas fa-chevron-right"></i>
                        <span>对比源杰科技和中际旭创的涨跌幅</span>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        function setQuery(text) {
            document.getElementById('user-query').value = text;
            document.getElementById('user-query').focus();
        }
        
        document.getElementById('query-form').addEventListener('submit', function(e) {
            e.preventDefault();
            
            const query = document.getElementById('user-query').value.trim();
            if (!query) return;
            
            // 添加用户消息
            addMessage('user', query);
            document.getElementById('user-query').value = '';
            
            // 显示加载中
            addMessage('bot', '<div class="loading"><div class="loading-spinner"></div><span>正在分析数据...</span></div>');
            
            // 发送请求
            fetch('/query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ query: query })
            })
            .then(response => response.json())
            .then(data => {
                // 移除加载中消息
                const messages = document.getElementById('chat-messages');
                messages.removeChild(messages.lastChild);
                
                if (data.success) {
                    let content = '';
                    
                    // 添加表格
                    content += '<div class="table-container"><pre>' + data.table + '</pre></div>';
                    
                    // 添加图表
                    content += '<div class="chart-container"><img src="' + data.chart + '" alt="股票图表"></div>';
                    
                    // 添加数据描述统计
                    if (data.describe) {
                        content += '<div class="describe-block"><small>数据统计描述</small><pre>' + data.describe + '</pre></div>';
                    }
                    
                    // 添加AI分析和建议
                    if (data.ai_analysis) {
                        content += '<div class="ai-analysis-block"><small><i class="fas fa-robot"></i> AI分析建议</small><div class="ai-content">' + data.ai_analysis + '</div></div>';
                    }
                    
                    // 添加SQL
                    content += '<div class="sql-block"><small>执行的SQL</small><pre>' + data.sql + '</pre></div>';
                    
                    addMessage('bot', content);
                } else {
                    addMessage('bot', '<div class="error-message">' + data.message + '</div>');
                }
            })
            .catch(error => {
                // 移除加载中消息
                const messages = document.getElementById('chat-messages');
                messages.removeChild(messages.lastChild);
                
                addMessage('bot', '<div class="error-message">网络错误，请重试</div>');
                console.error('Error:', error);
            });
        });
        
        function addMessage(type, content) {
            const messages = document.getElementById('chat-messages');
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message ' + type + '-message';
            
            const now = new Date();
            const time = now.getHours().toString().padStart(2, '0') + ':' + 
                        now.getMinutes().toString().padStart(2, '0');
            
            let avatarIcon = type === 'user' ? 'user' : 'robot';
            let avatarClass = type === 'user' ? 'user-avatar' : 'bot-avatar';
            
            messageDiv.innerHTML = `
                <div class="message-avatar ${avatarClass}">
                    <i class="fas fa-${avatarIcon}"></i>
                </div>
                <div class="message-content">
                    <div class="message-bubble">${content}</div>
                    <div class="message-time">${time}</div>
                </div>
            `;
            
            messages.appendChild(messageDiv);
            messages.scrollTop = messages.scrollHeight;
        }
        
        // 页面加载完成后添加欢迎消息
        window.onload = function() {
            addMessage('bot', `
                <div class="welcome-content">
                    <h5>欢迎使用股票查询助手！</h5>
                    <p>我可以帮您分析股票数据，支持以下功能：</p>
                    <ul>
                        <li>查询股票历史价格走势</li>
                        <li>统计成交量和涨跌幅</li>
                        <li>对比不同股票的表现</li>
                        <li>生成数据可视化图表</li>
                    </ul>
                    <p>请输入您的问题开始查询，或点击右侧推荐对话快速开始。</p>
                </div>
            `);
        };
    </script>
</body>
</html>
'''

# 写入HTML模板
with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html_template)

if __name__ == '__main__':
    print("股票查询助手 Web 界面启动中...")
    print("Web 服务器将在 http://localhost:8080 上运行")
    print("请在浏览器中打开上述地址进行访问")
    app.run(debug=True, host='127.0.0.1', port=8080)
