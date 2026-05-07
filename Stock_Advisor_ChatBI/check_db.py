import sqlite3

conn = sqlite3.connect('stock_data.db')
cursor = conn.cursor()

cursor.execute('PRAGMA table_info(stock_price)')
columns = [col[1] for col in cursor.fetchall()]
print('Columns:', columns)

cursor.execute('SELECT * FROM stock_price LIMIT 3')
rows = cursor.fetchall()
print('Sample rows:', rows)

cursor.execute("SELECT 股票名称, COUNT(*) FROM stock_price GROUP BY 股票名称")
stocks = cursor.fetchall()
print('Stocks in DB:', stocks)
