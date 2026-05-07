import os
import pandas as pd
import tushare as ts
from datetime import datetime

ts.set_token('eebd801443d696508e292555391608771f2bce83fbc3ebb0c1669d57')
pro = ts.pro_api()

stocks = {
    '600519.SH': '贵州茅台',
    '000858.SZ': '五粮液',
    '601211.SH': '国泰君安',
    '688981.SH': '中芯国际'
}

end_date = datetime.now().strftime('%Y%m%d')

all_data = []

for code, name in stocks.items():
    df = pro.daily(
        ts_code=code,
        start_date='20200101',
        end_date=end_date
    )
    
    if df is not None and len(df) > 0:
        df['stock_name'] = name
        df['stock_code'] = code
        all_data.append(df)
        print(f"获取 {name} ({code}) 数据: {len(df)} 条")

if all_data:
    result = pd.concat(all_data, ignore_index=True)
    
    result = result.sort_values('trade_date', ascending=True)
    
    result = result[['trade_date', 'stock_code', 'stock_name', 'open', 'high', 'low', 'close', 'pre_close', 'change', 'pct_chg', 'vol', 'amount']]
    
    result.columns = ['交易日期', '股票代码', '股票名称', '开盘价', '最高价', '最低价', '收盘价', '前收价', '涨跌额', '涨跌幅', '成交量', '成交额']
    
    result.to_excel('stock_history_new.xlsx', sheet_name='历史价格', index=False)
    
    print(f"\n数据已保存到 stock_history_new.xlsx")
    print(f"总记录数: {len(result)}")
else:
    print("未获取到任何数据")
