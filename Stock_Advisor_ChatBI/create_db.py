import pandas as pd
from sqlalchemy import create_engine

df = pd.read_excel('stock_history.xlsx')

engine = create_engine('sqlite:///stock_data.db')

df.to_sql('stock_price', engine, if_exists='replace', index=False)

print(f"数据已导入到 stock_data.db")
print(f"共 {len(df)} 条记录")
print(f"\n表结构:")
print(df.dtypes)
