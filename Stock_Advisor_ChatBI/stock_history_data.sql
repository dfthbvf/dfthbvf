CREATE TABLE stock_price (
    id INT AUTO_INCREMENT PRIMARY KEY,
    交易日期 VARCHAR(10) NOT NULL,
    股票代码 VARCHAR(20) NOT NULL,
    股票名称 VARCHAR(50) NOT NULL,
    开盘价 DECIMAL(10,2) NOT NULL,
    最高价 DECIMAL(10,2) NOT NULL,
    最低价 DECIMAL(10,2) NOT NULL,
    收盘价 DECIMAL(10,2) NOT NULL,
    前收价 DECIMAL(10,2) NOT NULL,
    涨跌额 DECIMAL(10,2) NOT NULL,
    涨跌幅 DECIMAL(10,4) NOT NULL,
    成交量 BIGINT NOT NULL,
    成交额 DECIMAL(20,2) NOT NULL,
    INDEX idx_trade_date (交易日期),
    INDEX idx_stock_code (股票代码),
    INDEX idx_stock_name (股票名称)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
