import logging

import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta, date
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# 设置中文字体，这里使用微软雅黑作为例子
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

# 修改配置以使用可变的日期
config = {
    'tickers': ['SPY', 'QQQ', 'IWM', 'DIA', 'VTI'],
    'base_investment': 100,
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
    max_date = data_index[-1]
    while date not in data_index:
        date += timedelta(days=1)
        if date > max_date:
            return max_date
    return date


def get_investment_dates(start_date, end_date, data_index):
    # 确保只使用数据中存在的日期
    valid_dates = [d for d in data_index if start_date <= d <= end_date]
    # 按月选择日期
    monthly_dates = []
    current_month = None
    for d in valid_dates:
        if d.replace(day=1) != current_month:
            monthly_dates.append(d)
            current_month = d.replace(day=1)
    return monthly_dates


def calculate_weight(price, sma, std, avg_std):
    n = 1 + (std / avg_std)
    weight = (sma / price) ** n
    return max(min(weight, config['max_weight']), config['min_weight'])


def analyze_and_plot(ticker, start_date, end_date):
    # 下载数据
    data = yf.download(ticker, start=start_date, end=end_date)['Adj Close']

    # 确保数据是浮点数类型
    data = data.astype(float)

    # 计算技术指标
    data = pd.DataFrame(data)
    data.columns = [ticker]
    data[f'{ticker}_SMA'] = data[ticker].rolling(window=config['sma_window']).mean()
    data[f'{ticker}_STD'] = data[ticker].rolling(window=config['std_window']).std()
    data[f'{ticker}_AVG_STD'] = data[f'{ticker}_STD'].expanding().mean()

    # 将索引转换为日期类型
    data.index = pd.to_datetime(data.index).date

    # 创建投资日期列表
    investment_dates = get_investment_dates(start_date, end_date, data.index)

    if not investment_dates:
        raise ValueError("选定的日期范围内没有可用的投资日期")

    # 初始化结果DataFrame
    results = pd.DataFrame(index=investment_dates, columns=[ticker])
    investment_amounts = pd.DataFrame(index=investment_dates, columns=[ticker])

    # 模拟投资
    for d in investment_dates:
        price = data.loc[d, ticker]
        sma = data.loc[d, f'{ticker}_SMA']
        std = data.loc[d, f'{ticker}_STD']
        avg_std = data.loc[d, f'{ticker}_AVG_STD']

        weight = calculate_weight(price, sma, std, avg_std)
        investment_amount = config['base_investment'] * weight
        shares_bought = investment_amount / price

        results.loc[d, ticker] = shares_bought
        investment_amounts.loc[d, ticker] = investment_amount

    # 计算累积份额和加权定投策略价值
    cumulative_shares = results.cumsum()
    weighted_portfolio_values = cumulative_shares.multiply(data.loc[data.index[-1], ticker])
    cumulative_investment = investment_amounts.cumsum()


    # 计算等额定投指数增长价值
    equal_investment = pd.DataFrame(config['base_investment'], index=investment_dates, columns=[ticker])
    equal_shares = equal_investment.divide(data.loc[investment_dates, ticker])
    equal_cumulative_shares = equal_shares.cumsum()
    equal_portfolio_value = equal_cumulative_shares.multiply(data.loc[data.index[-1], ticker])

    # 清除旧图形
    plt.clf()
    fig, ax = plt.subplots(figsize=(12, 6))

    # 绘制结果时使用唯一的标签
    ax.plot(weighted_portfolio_values.index, weighted_portfolio_values, label=f'{ticker} 加权定投', color='blue')
    ax.plot(equal_portfolio_value.index, equal_portfolio_value, label=f'{ticker} 等额定投', linestyle='--', color='orange')

    ax.set_title(f'{ticker}: 加权定投vs等额定投策略的投资组合价值 ({start_date.year}-{end_date.year})')
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

    # 计算实际的投资日期范围
    actual_start_date = investment_dates[0]
    actual_end_date = investment_dates[-1]
    investment_period_days = (actual_end_date - actual_start_date).days

    weighted_annual_return = ((weighted_final_value / total_weighted_investment) ** (
            365.25 / investment_period_days) - 1) * 100
    equal_annual_return = ((equal_final_value / total_equal_investment) ** (
            365.25 / investment_period_days) - 1) * 100

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
root.geometry("1024x768")  # 设置窗口大小

# 创建左侧框架用于放置控件
left_frame = ttk.Frame(root, padding="10")
left_frame.pack(side=tk.LEFT, fill=tk.Y, expand=False)

# 创建日期输入框和标签
start_date_label = ttk.Label(left_frame, text="起始日期 (YYYY-MM):")
start_date_label.pack(anchor=tk.W, pady=(0, 5))
start_date_entry = ttk.Entry(left_frame, width=10)
start_date_entry.pack(anchor=tk.W, pady=(0, 10))
start_date_entry.insert(0, "2000-01")  # 默认起始日期

end_date_label = ttk.Label(left_frame, text="结束日期 (YYYY-MM):")
end_date_label.pack(anchor=tk.W, pady=(0, 5))
end_date_entry = ttk.Entry(left_frame, width=10)
end_date_entry.pack(anchor=tk.W, pady=(0, 10))
end_date_entry.insert(0, datetime.now().strftime("%Y-%m"))  # 默认结束日期为当前月份

# 创建下拉菜单
ticker_label = ttk.Label(left_frame, text="选择股票:")
ticker_label.pack(anchor=tk.W, pady=(10, 5))
ticker_var = tk.StringVar()
ticker_dropdown = ttk.Combobox(left_frame, textvariable=ticker_var, values=config['tickers'], width=10)
ticker_dropdown.set(config['tickers'][0])  # 设置默认值
ticker_dropdown.pack(anchor=tk.W, pady=(0, 10))

# 创建右侧框架用于放置图表
right_frame = ttk.Frame(root, padding="10")
right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

# 创建画布
canvas = FigureCanvasTkAgg(plt.Figure(figsize=(10, 6)), master=right_frame)
canvas_widget = canvas.get_tk_widget()
canvas_widget.pack(fill=tk.BOTH, expand=True)


def update_plot():
    ticker = ticker_var.get()
    try:
        start_date = datetime.strptime(start_date_entry.get(), "%Y-%m").date()
        end_date = datetime.strptime(end_date_entry.get(), "%Y-%m").date()
        # 将结束日期调整到月末
        end_date = (date(end_date.year, end_date.month, 1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    except ValueError:
        messagebox.showerror("错误", "请输入有效的日期格式 (YYYY-MM)")
        return

    if ticker not in config['tickers']:
        messagebox.showerror("错误", "选择的标的不存在")
        return
    if start_date >= end_date:
        messagebox.showerror("错误", "起始日期必须早于结束日期")
        return

    try:
        fig = analyze_and_plot(ticker, start_date, end_date)

        # 清除旧的图形内容
        for widget in right_frame.winfo_children():
            widget.destroy()

        # 创建新的画布并显示更新后的图形
        canvas = FigureCanvasTkAgg(fig, master=right_frame)
        canvas_widget = canvas.get_tk_widget()
        canvas_widget.pack(fill=tk.BOTH, expand=True)
        canvas.draw()
    except Exception as e:
        messagebox.showerror("错误", f"分析过程中出现错误: {str(e)}")


# 创建更新按钮
update_button = ttk.Button(left_frame, text="更新图表", command=update_plot)
update_button.pack(pady=10)

# 初始绘图
update_plot()

# 运行GUI主循环
root.mainloop()