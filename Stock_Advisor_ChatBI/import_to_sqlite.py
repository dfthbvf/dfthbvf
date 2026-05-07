import sqlite3
import pandas as pd
from datetime import datetime

# 读取排序后的数据
df = pd.read_excel('stock_history_tech_sorted.xlsx')

# 连接SQLite数据库
conn = sqlite3.connect('stock_data.db')
cursor = conn.cursor()

# 创建表
create_table_sql = """
CREATE TABLE IF NOT EXISTS stock_price (
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
"""

cursor.execute(create_table_sql)

# 清空表（如果已存在数据）
cursor.execute("DELETE FROM stock_price;")

# 插入数据
insert_sql = """
INSERT INTO stock_price (
    交易日期, 股票代码, 股票名称, 开盘价, 最高价, 最低价, 收盘价, 
    前收价, 涨跌额, 涨跌幅, 成交量, 成交额
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

# 批量插入
data = []
for index, row in df.iterrows():
    data.append((
        str(int(row['交易日期'])),  # 确保交易日期为字符串格式
        row['股票代码'],
        row['股票名称'],
        row['开盘价'],
        row['最高价'],
        row['最低价'],
        row['收盘价'],
        row['前收价'],
        row['涨跌额'],
        row['涨跌幅'],
        row['成交量'],
        row['成交额']
    ))

cursor.executemany(insert_sql, data)

# 提交事务
conn.commit()

# 验证数据
total_records = cursor.execute("SELECT COUNT(*) FROM stock_price").fetchone()[0]
print(f"数据导入完成！")
print(f"导入记录数: {total_records}")
print(f"Excel文件记录数: {len(df)}")

# 查看前5条记录
print("\n前5条记录:")
cursor.execute("SELECT * FROM stock_price LIMIT 5")
for row in cursor.fetchall():
    print(row)

# 关闭连接
cursor.close()
conn.close()

print("\nSQLite数据库创建成功，数据已导入到 stock_data.db")
