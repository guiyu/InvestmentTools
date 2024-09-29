import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# 设置中文字体，这里使用微软雅黑作为例子
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

# 配置
config = {
    'tickers': ['SPY', 'QQQ'],  # 可以根据需要添加或删除股票代码
    'start_date': (datetime.now() - timedelta(days=365*20)).date(),  # 回测开始日期（20年前）
    'end_date': datetime.now().date(),  # 回测结束日期（今天）
}

# 获取每月第二个星期三的函数
def get_second_wednesday(date):
    first = date.replace(day=1)  # 获取当月第一天
    first_wednesday = first + timedelta(days=(2 - first.weekday() + 7) % 7)  # 获取当月第一个星期三
    second_wednesday = first_wednesday + timedelta(days=7)  # 获取当月第二个星期三
    return second_wednesday

# 获取最近的交易日函数
def get_nearest_business_day(date, data_index):
    while date not in data_index:
        date += timedelta(days=1)  # 如果不是交易日，往后推一天
    return date

# 获取投资日期的函数
def get_investment_dates(start_date, end_date):
    dates = []
    current_date = start_date
    while current_date <= end_date:
        second_wednesday = get_second_wednesday(current_date)
        if second_wednesday <= end_date:
            dates.append(second_wednesday)
        current_date = (current_date.replace(day=1) + timedelta(days=32)).replace(day=1)  # 移到下个月
    return dates

# 下载数据
data = yf.download(config['tickers'], start=config['start_date'], end=config['end_date'])['Adj Close']

# 将索引转换为仅包含日期
data.index = data.index.date

# 创建投资日期列表
investment_dates = get_investment_dates(config['start_date'], config['end_date'])

# 过滤数据以仅包括投资日期
investment_data = data.loc[[get_nearest_business_day(date, data.index) for date in investment_dates]]

# 计算回报
returns = investment_data.pct_change()

# 计算累积回报
cumulative_returns = (1 + returns).cumprod()

# 绘制结果
plt.figure(figsize=(12, 6))
for ticker in config['tickers']:
    plt.plot(cumulative_returns.index, cumulative_returns[ticker], label=ticker)

plt.title(f'选定ETF的累积回报 ({config["start_date"].year}-{config["end_date"].year})\n每月第二个星期三投资')
plt.xlabel('日期')
plt.ylabel('累积回报')
plt.legend()
plt.grid(True)
plt.show()

# 计算并打印摘要统计
for ticker in config['tickers']:
    print(f"\n{ticker} 的摘要统计：")
    print(f"总回报: {cumulative_returns[ticker].iloc[-1]:.2f}")
    total_years = (config['end_date'] - config['start_date']).days / 365.25
    print(f"年化回报: {(cumulative_returns[ticker].iloc[-1]**(1/total_years) - 1):.4f}")
    print(f"夏普比率: {returns[ticker].mean() / returns[ticker].std() * (12**0.5):.4f}")  # 使用月度数据，所以是12的平方根

# 计算调仓次数
rebalance_count = len(investment_dates)
print(f"\n总调仓次数: {rebalance_count}")
print(f"平均每年调仓次数: {rebalance_count / total_years:.2f}")