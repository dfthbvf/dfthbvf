import pandas as pd

df = pd.read_excel('stock_history_tech_updated.xlsx')

df = df.sort_values('交易日期', ascending=True)

df.to_excel('stock_history_tech_sorted.xlsx', sheet_name='历史价格', index=False)

print(f"数据已按交易日期从小到大排序完成！")
print(f"总记录数: {len(df)}")
print(f"\n前5行数据:")
print(df.head())
print(f"\n后5行数据:")
print(df.tail())
