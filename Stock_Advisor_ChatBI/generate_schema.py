import pandas as pd

df = pd.read_excel('stock_history_tech_sorted.xlsx')

print("前5行数据:")
print(df.head())
print()

print("\n数据类型:")
print(df.dtypes)
print()

mysql_schema = """-- 股票历史价格表
CREATE TABLE stock_price (
    id INT AUTO_INCREMENT PRIMARY KEY,
    交易日期 VARCHAR(10) NOT NULL COMMENT '交易日期，格式：YYYYMMDD',
    股票代码 VARCHAR(20) NOT NULL COMMENT '股票代码',
    股票名称 VARCHAR(50) NOT NULL COMMENT '股票名称',
    开盘价 DECIMAL(10,2) NOT NULL COMMENT '开盘价',
    最高价 DECIMAL(10,2) NOT NULL COMMENT '最高价',
    最低价 DECIMAL(10,2) NOT NULL COMMENT '最低价',
    收盘价 DECIMAL(10,2) NOT NULL COMMENT '收盘价',
    前收价 DECIMAL(10,2) NOT NULL COMMENT '前收价',
    涨跌额 DECIMAL(10,2) NOT NULL COMMENT '涨跌额',
    涨跌幅 DECIMAL(10,4) NOT NULL COMMENT '涨跌幅',
    成交量 DECIMAL(20,2) NOT NULL COMMENT '成交量',
    成交额 DECIMAL(20,2) NOT NULL COMMENT '成交额',
    INDEX idx_trade_date (交易日期),
    INDEX idx_stock_code (股票代码),
    INDEX idx_stock_name (股票名称)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股票历史价格表';
"""

with open('stock_history_schema.sql', 'w', encoding='utf-8') as f:
    f.write(mysql_schema)

print("\nMySQL建表语句已生成到 stock_history_schema.sql")
print(mysql_schema)
