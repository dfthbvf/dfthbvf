import matplotlib.pyplot as plt

dates = ['20250102', '20250103', '20250106', '20250107', '20250108',
         '20250109', '20250110', '20250113', '20250114', '20250115']
moutai_futures = [-2.3622, -0.8737, -2.3729, 0.0139, 0.1597,
                  0.104, -0.554, 0.5557, 1.9751, -0.0835]
smic_futures = [-4.925, -1.8341, -1.5514, 4.2098, -1.9647,
                2.8147, 2.0368, 1.9747, 3.9465, 0.7897]

plt.figure(figsize=(10, 6))
plt.plot(dates, moutai_futures, marker='o', label='贵州茅台 (600519.SH)')
plt.plot(dates, smic_futures, marker='s', label='中芯国际 (688981.SH)')

plt.xlabel('交易日期')
plt.ylabel('涨跌幅 (%)')
plt.title('2025年中芯国际与贵州茅台的涨跌幅对比')
plt.legend()
plt.grid(True)
plt.xticks(rotation=45)
plt.tight_layout()

plt.savefig('stock_comparison.png')
plt.show()
