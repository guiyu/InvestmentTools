import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk, messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# 设置中文字体，这里使用微软雅黑作为例子
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题


# 配置
config = {
    'tickers': ['SPY', 'QQQ'],
    'start_date': (datetime.now() - timedelta(days=365 * 20)).date(),
    'end_date': datetime.now().date(),
    'base_investment': 1000,
    'sma_window': 200,
    'std_window': 30,
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
# for date in investment_dates:
#     actual_date = get_nearest_business_day(date, data.index)
#     for ticker in config['tickers']:
#         price = data.loc[actual_date, ticker]
#         sma = data.loc[actual_date, f'{ticker}_SMA']
#         std = data.loc[actual_date, f'{ticker}_STD']
#         avg_std = data.loc[actual_date, f'{ticker}_AVG_STD']
#
#         weight = calculate_weight(price, sma, std, avg_std)
#         investment_amount = config['base_investment'] * weight
#         shares_bought = investment_amount / price
#
#         results.loc[date, ticker] = shares_bought
#         investment_amounts.loc[date, ticker] = investment_amount

def analyze_and_plot(ticker):
    # 下载数据
    data = yf.download(ticker, start=config['start_date'], end=config['end_date'])['Adj Close']

    # 打印数据以进行调试
    print(f"Downloaded data for {ticker}:")
    print(data.head())

    # 确保数据是DataFrame格式
    data = pd.DataFrame(data)

    # 重命名列
    data.columns = [ticker]

    # 打印列名以进行调试
    print(f"Columns after renaming: {data.columns}")

    # 计算技术指标
    data[f'{ticker}_SMA'] = data[ticker].rolling(window=config['sma_window']).mean()
    data[f'{ticker}_STD'] = data[ticker].rolling(window=config['std_window']).std()
    data[f'{ticker}_AVG_STD'] = data[f'{ticker}_STD'].expanding().mean()

    # 将索引转换为仅包含日期
    data.index = data.index.date

    # 创建投资日期列表
    investment_dates = get_investment_dates(config['start_date'], config['end_date'])

    # 初始化结果DataFrame
    results = pd.DataFrame(index=investment_dates, columns=[ticker])
    investment_amounts = pd.DataFrame(index=investment_dates, columns=[ticker])

    # 模拟投资
    for date in investment_dates:
        actual_date = get_nearest_business_day(date, data.index)
        price = data.loc[actual_date, ticker]
        sma = data.loc[actual_date, f'{ticker}_SMA']
        std = data.loc[actual_date, f'{ticker}_STD']
        avg_std = data.loc[actual_date, f'{ticker}_AVG_STD']

        weight = calculate_weight(price, sma, std, avg_std)
        investment_amount = config['base_investment'] * weight
        shares_bought = investment_amount / price

        results.loc[date, ticker] = shares_bought
        investment_amounts.loc[date, ticker] = investment_amount

    # 计算累积份额和最终价值
    cumulative_shares = results.cumsum()
    portfolio_values = cumulative_shares.multiply(data[ticker], axis=0)
    cumulative_investment = investment_amounts.cumsum()

    # 计算等额定投指数增长价值
    equal_investment = pd.Series(config['base_investment'], index=investment_dates).cumsum()
    equal_shares = equal_investment / data[ticker].reindex(investment_dates)
    equal_portfolio_value = equal_shares.cumsum() * data[ticker]

    # 打印调试信息
    print(f"Portfolio values shape: {portfolio_values.shape}")
    print(f"Cumulative investment shape: {cumulative_investment.shape}")
    print(f"Index growth shape: {equal_portfolio_value.shape}")

    # 确保所有数据具有相同的索引
    common_index = portfolio_values.index.intersection(cumulative_investment.index).intersection(equal_portfolio_value.index)
    portfolio_values = portfolio_values.loc[common_index]
    cumulative_investment = cumulative_investment.loc[common_index]
    equal_portfolio_value = equal_portfolio_value.loc[common_index]

    # 绘制结果
    plt.figure(figsize=(12, 6))
    plt.plot(portfolio_values.index, portfolio_values[ticker], label='加权定投策略价值', color='blue')
    plt.plot(cumulative_investment.index, cumulative_investment[ticker], label='累计投资金额', color='green')
    plt.plot(equal_portfolio_value.index, equal_portfolio_value, label='等额定投指数增长价值', color='red')

    plt.title(f'{ticker} 加权定投策略vs等额定投 ({config["start_date"].year}-{config["end_date"].year})')
    plt.xlabel('日期')
    plt.ylabel('金额')
    plt.legend()
    plt.grid(True)

    # 设置y轴的范围，确保所有数据都在视图中
    plt.ylim(0, max(portfolio_values[ticker].max(), cumulative_investment[ticker].max(), equal_portfolio_value.max()) * 1.1)

    return plt.gcf()

# 计算累积份额和最终价值
cumulative_shares = results.cumsum()
final_prices = data.loc[data.index[-1], config['tickers']]
portfolio_values = cumulative_shares.multiply(final_prices, axis=1)

# 创建GUI
root = tk.Tk()
root.title("投资策略分析")

# 创建下拉菜单
ticker_var = tk.StringVar()
ticker_dropdown = ttk.Combobox(root, textvariable=ticker_var, values=config['tickers'])
ticker_dropdown.set(config['tickers'][0])  # 设置默认值
ticker_dropdown.pack(pady=10)

# 创建画布
canvas = FigureCanvasTkAgg(plt.Figure(figsize=(12, 6)), master=root)
canvas_widget = canvas.get_tk_widget()
canvas_widget.pack()

def update_plot():
    ticker = ticker_var.get()
    if ticker not in config['tickers']:
        messagebox.showerror("错误", "选择的标的不存在")
        return
    fig = analyze_and_plot(ticker)
    canvas.figure = fig
    canvas.draw()

# 创建更新按钮
update_button = ttk.Button(root, text="更新图表", command=update_plot)
update_button.pack(pady=10)

# 初始绘图
update_plot()

root.mainloop()


# 绘制结果
plt.figure(figsize=(12, 6))
for ticker in config['tickers']:
    plt.plot(portfolio_values.index, portfolio_values[ticker], label=ticker)

plt.title(f'加权定投策略的投资组合价值 ({config["start_date"].year}-{config["end_date"].year})')
plt.xlabel('日期')
plt.ylabel('投资组合价值')
plt.legend()
plt.grid(True)
plt.show()

# 计算并打印摘要统计
total_investment = investment_amounts.sum().sum()
for ticker in config['tickers']:
    final_value = portfolio_values[ticker].iloc[-1]
    total_return = (final_value / investment_amounts[ticker].sum() - 1) * 100
    annual_return = ((final_value / investment_amounts[ticker].sum()) ** (
                365.25 / (config['end_date'] - config['start_date']).days) - 1) * 100

    print(f"\n{ticker} 的摘要统计：")
    print(f"总投资: ${investment_amounts[ticker].sum():.2f}")
    print(f"最终价值: ${final_value:.2f}")
    print(f"总回报率: {total_return:.2f}%")
    print(f"年化回报率: {annual_return:.2f}%")

# 计算调仓次数
rebalance_count = len(investment_dates)
total_years = (config['end_date'] - config['start_date']).days / 365.25
print(f"\n总调仓次数: {rebalance_count}")
print(f"平均每年调仓次数: {rebalance_count / total_years:.2f}")

# 生成定投金额和时间点的表格
investment_table = investment_amounts.reset_index()
investment_table.columns = ['投资日期'] + [f'{ticker}定投金额' for ticker in config['tickers']]
print("\n定投金额和时间点表格：")
print(investment_table.to_string(index=False))

# 将表格保存到CSV文件
investment_table.to_csv('investment_table.csv', index=False)
print("\n定投金额和时间点表格已保存到 'investment_table.csv'")