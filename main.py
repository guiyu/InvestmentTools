import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from datetime import datetime, timedelta

# 设置中文字体，这里使用微软雅黑作为例子
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

# 设置回测的开始和结束日期
start_date = (datetime.now() - timedelta(days=365 * 20)).date()
end_date = datetime.now().date()

# 定义我们要回测的股票代码
tickers = ['QQQ', 'SPY', 'XLG']


# 获取每月第三个周五的函数
def get_third_friday(date):
    first = date.replace(day=1)
    first_friday = first + timedelta(days=(4 - first.weekday() + 7) % 7)
    third_friday = first_friday + timedelta(days=14)
    return third_friday


# 获取最近的交易日
def get_nearest_business_day(date, data_index):
    while date not in data_index:
        date += timedelta(days=1)
    return date


# 下载数据
data = yf.download(tickers, start=start_date, end=end_date)['Adj Close']

# 将索引转换为仅包含日期
data.index = data.index.date

# 创建投资日期列表（每月第三个周五）
investment_dates = []
current_date = start_date
while current_date <= end_date:
    third_friday = get_third_friday(current_date)
    if third_friday <= end_date:
        nearest_business_day = get_nearest_business_day(third_friday, data.index)
        investment_dates.append(nearest_business_day)
    current_date = (current_date.replace(day=1) + timedelta(days=32)).replace(day=1)

# 过滤数据以仅包括投资日期
investment_data = data.loc[investment_dates]

# 计算回报
returns = investment_data.pct_change()

# 计算累积回报
cumulative_returns = (1 + returns).cumprod()

# 绘制结果
plt.figure(figsize=(12, 6))
for ticker in tickers:
    plt.plot(cumulative_returns.index, cumulative_returns[ticker], label=ticker)

plt.title('QQQ, SPY, 和 XLG 的累积回报 (2003-2023)')
plt.xlabel('日期')
plt.ylabel('累积回报')
plt.legend()
plt.grid(True)
plt.show()

# 计算并打印摘要统计
for ticker in tickers:
    print(f"\n{ticker} 的摘要统计：")
    print(f"总回报: {cumulative_returns[ticker].iloc[-1]:.2f}")
    print(f"年化回报: {(cumulative_returns[ticker].iloc[-1] ** (1 / 20) - 1):.4f}")
    print(f"夏普比率: {returns[ticker].mean() / returns[ticker].std() * (252 ** 0.5):.4f}")  # 假设252个交易日
