import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# 设置中文字体，这里使用微软雅黑作为例子
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

# 配置
config = {
    'tickers': ['SPY', 'QQQ', 'IWM', 'DIA', 'VTI'],  # 增加了一些常见的ETF
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


def analyze_and_plot(ticker):
    # 下载数据
    data = yf.download(ticker, start=config['start_date'], end=config['end_date'])['Adj Close']

    # 确保数据是浮点数类型
    data = data.astype(float)

    # 计算技术指标
    data = pd.DataFrame(data)  # 将Series转换为DataFrame
    data.columns = [ticker]  # 重命名列
    data[f'{ticker}_SMA'] = data[ticker].rolling(window=config['sma_window']).mean()
    data[f'{ticker}_STD'] = data[ticker].rolling(window=config['std_window']).std()
    data[f'{ticker}_AVG_STD'] = data[f'{ticker}_STD'].expanding().mean()

    # 将索引转换为仅包含日期
    data.index = pd.to_datetime(data.index).date

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

    # 计算累积份额和加权定投策略价值
    cumulative_shares = results.cumsum()
    weighted_portfolio_values = cumulative_shares.multiply(data.loc[data.index[-1], ticker], axis=1)
    cumulative_investment = investment_amounts.cumsum()

    # 计算等额定投指数增长价值
    equal_investment = pd.DataFrame(config['base_investment'], index=investment_dates, columns=[ticker])
    equal_shares = equal_investment.divide(data.loc[investment_dates, ticker])
    equal_cumulative_shares = equal_shares.cumsum()
    equal_portfolio_value = equal_cumulative_shares.multiply(data.loc[data.index[-1], ticker], axis=1)

    # 绘制结果
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(weighted_portfolio_values.index, weighted_portfolio_values[ticker], label=f'{ticker} 加权定投')
    ax.plot(equal_portfolio_value.index, equal_portfolio_value[ticker], label=f'{ticker} 等额定投', linestyle='--')
    ax.set_title(f'{ticker}: 加权定投vs等额定投策略的投资组合价值 ({config["start_date"].year}-{config["end_date"].year})')
    ax.set_xlabel('日期')
    ax.set_ylabel('投资组合价值')
    ax.legend()
    ax.grid(True)

    # 计算并显示摘要统计
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

    summary = f"\n{ticker} 的摘要统计：\n"
    summary += f"加权定投:\n"
    summary += f"  总投资: ${total_weighted_investment:.2f}\n"
    summary += f"  最终价值: ${weighted_final_value:.2f}\n"
    summary += f"  总回报率: {weighted_total_return:.2f}%\n"
    summary += f"  年化回报率: {weighted_annual_return:.2f}%\n"
    summary += f"等额定投:\n"
    summary += f"  总投资: ${total_equal_investment:.2f}\n"
    summary += f"  最终价值: ${equal_final_value:.2f}\n"
    summary += f"  总回报率: {equal_total_return:.2f}%\n"
    summary += f"  年化回报率: {equal_annual_return:.2f}%\n"

    ax.text(0.05, 0.05, summary, transform=ax.transAxes, verticalalignment='bottom',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    return fig

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

# 运行GUI主循环
root.mainloop()