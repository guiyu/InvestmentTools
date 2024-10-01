import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# 设置中文字体，这里使用微软雅黑作为例子
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

# 配置
config = {
    'tickers': ['SPY', 'QQQ'],
    'start_date': (datetime.now() - timedelta(days=365 * 20)).date(),
    'end_date': datetime.now().date(),
    'base_investment': 100,  # 基础投资金额
    'sma_window': 200,  # SMA窗口
    'std_window': 30,  # 标准差窗口
    'min_weight': 0.5,
    'max_weight': 2,
}


def get_second_wednesday(date):
    first = date.replace(day=1)
    first_wednesday = first + timedelta(days=(2 - first.weekday() + 7) % 7)
    second_wednesday = first_wednesday + timedelta(days=7)
    return second_wednesday


def get_nearest_business_day(date, data_index):
    while date not in data_index:
        date += timedelta(days=1)
    return date


def get_investment_dates(start_date, end_date):
    dates = []
    current_date = start_date
    while current_date <= end_date:
        second_wednesday = get_second_wednesday(current_date)
        if second_wednesday <= end_date:
            dates.append(second_wednesday)
        current_date = (current_date.replace(day=1) + timedelta(days=32)).replace(day=1)
    return dates


def calculate_weight(price, sma, std, avg_std):
    n = 1 + (std / avg_std)
    weight = (sma / price) ** n
    return max(min(weight, config['max_weight']), config['min_weight'])


# 下载数据
data = yf.download(config['tickers'], start=config['start_date'], end=config['end_date'])['Adj Close']

# 计算技术指标
for ticker in config['tickers']:
    data[f'{ticker}_SMA'] = data[ticker].rolling(window=config['sma_window']).mean()
    data[f'{ticker}_STD'] = data[ticker].rolling(window=config['std_window']).std()
    data[f'{ticker}_AVG_STD'] = data[f'{ticker}_STD'].expanding().mean()

# 将索引转换为仅包含日期
data.index = data.index.date

# 创建投资日期列表
investment_dates = get_investment_dates(config['start_date'], config['end_date'])

# 初始化结果DataFrame
results = pd.DataFrame(index=investment_dates, columns=config['tickers'])
investment_amounts = pd.DataFrame(index=investment_dates, columns=config['tickers'])

# 模拟投资
for date in investment_dates:
    actual_date = get_nearest_business_day(date, data.index)
    for ticker in config['tickers']:
        price = data.loc[actual_date, ticker]
        sma = data.loc[actual_date, f'{ticker}_SMA']
        std = data.loc[actual_date, f'{ticker}_STD']
        avg_std = data.loc[actual_date, f'{ticker}_AVG_STD']

        weight = calculate_weight(price, sma, std, avg_std)
        investment_amount = config['base_investment'] * weight
        shares_bought = investment_amount / price

        results.loc[date, ticker] = shares_bought
        investment_amounts.loc[date, ticker] = investment_amount

# 计算累积份额和加权定投策略价值
cumulative_shares = results.cumsum()
weighted_portfolio_values = cumulative_shares.multiply(data.loc[data.index[-1], config['tickers']], axis=1)
cumulative_investment = investment_amounts.cumsum()

# 计算等额定投指数增长价值
equal_investment = pd.DataFrame(config['base_investment'], index=investment_dates, columns=config['tickers'])
equal_shares = equal_investment.divide(data.loc[investment_dates, config['tickers']])
equal_cumulative_shares = equal_shares.cumsum()
equal_portfolio_value = equal_cumulative_shares.multiply(data.loc[data.index[-1], config['tickers']], axis=1)

# 绘制结果
plt.figure(figsize=(12, 6))
for ticker in config['tickers']:
    plt.plot(weighted_portfolio_values.index, weighted_portfolio_values[ticker], label=f'{ticker} 加权定投')
    plt.plot(equal_portfolio_value.index, equal_portfolio_value[ticker], label=f'{ticker} 等额定投', linestyle='--')
plt.title(f'加权定投vs等额定投策略的投资组合价值 ({config["start_date"].year}-{config["end_date"].year})')
plt.xlabel('日期')
plt.ylabel('投资组合价值')
plt.legend()
plt.grid(True)
plt.show()

# 计算并打印摘要统计
for ticker in config['tickers']:
    weighted_final_value = weighted_portfolio_values[ticker].iloc[-1]
    equal_final_value = equal_portfolio_value[ticker].iloc[-1]
    total_weighted_investment = cumulative_investment[ticker].iloc[-1]
    total_equal_investment = config['base_investment'] * len(investment_dates)

    weighted_total_return = (weighted_final_value / total_weighted_investment - 1) * 100
    equal_total_return = (equal_final_value / total_equal_investment - 1) * 100

    weighted_annual_return = ((weighted_final_value / total_weighted_investment) ** (
                365.25 / (config['end_date'] - config['start_date']).days) - 1) * 100
    equal_annual_return = ((equal_final_value / total_equal_investment) ** (
                365.25 / (config['end_date'] - config['start_date']).days) - 1) * 100

    print(f"\n{ticker} 的摘要统计：")
    print(f"加权定投:")
    print(f"  总投资: ${total_weighted_investment:.2f}")
    print(f"  最终价值: ${weighted_final_value:.2f}")
    print(f"  总回报率: {weighted_total_return:.2f}%")
    print(f"  年化回报率: {weighted_annual_return:.2f}%")
    print(f"等额定投:")
    print(f"  总投资: ${total_equal_investment:.2f}")
    print(f"  最终价值: ${equal_final_value:.2f}")
    print(f"  总回报率: {equal_total_return:.2f}%")
    print(f"  年化回报率: {equal_annual_return:.2f}%")

# 计算调仓次数
rebalance_count = len(investment_dates)
total_years = (config['end_date'] - config['start_date']).days / 365.25
print(f"\n总调仓次数: {rebalance_count}")
print(f"平均每年调仓次数: {rebalance_count / total_years:.2f}")