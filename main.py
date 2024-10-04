import os
import yfinance as yf
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta, date
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
import pandas as pd

# 设置中文字体，这里使用微软雅黑作为例子
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

# 修改配置
config = {
    'tickers': ['SPY', 'QQQ', 'XLG', 'IWM', 'DIA', 'VTI', 'KWEB'],
    'base_investment': 2000,  # 修改基础投资金额为2000美元
    'sma_window': 200,
    'std_window': 30,
    'min_weight': 0.5,
    'max_weight': 2,
    'macd_short_window': 12,
    'macd_long_window': 26,
    'macd_signal_window': 9,
}

# 修改投资计算函数
def calculate_investment(price, weight, base_investment):
    max_shares = base_investment * weight // price
    return max_shares * price, max_shares


def calculate_macd(data, short_window=12, long_window=26, signal_window=9):
    short_ema = data.ewm(span=short_window, adjust=False).mean()
    long_ema = data.ewm(span=long_window, adjust=False).mean()
    macd = short_ema - long_ema
    signal = macd.ewm(span=signal_window, adjust=False).mean()
    histogram = macd - signal
    return macd, signal, histogram

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


def calculate_weight(current_price, last_buy_price):
    if last_buy_price is None:
        return 1  # 第一次投资

    price_change = (current_price - last_buy_price) / last_buy_price

    if price_change < -0.2:
        return 2
    elif -0.2 <= price_change < -0.1:
        return 2
    elif -0.1 <= price_change < -0.05:
        return 1.5
    elif -0.05 <= price_change < 0.05:
        return 1
    elif 0.05 <= price_change < 0.1:
        return 0.7
    elif 0.1 <= price_change < 0.2:
        return 0.5
    else:
        return 0.5


# 修改 save_to_excel 函数
def save_to_excel(data, equal_investment, weighted_investment, shares_bought, ticker, start_date, end_date):
    investment_dates = equal_investment.index
    excel_data = pd.DataFrame(index=investment_dates)

    excel_data['日期'] = investment_dates
    excel_data['收盘价'] = data.loc[investment_dates, ticker].round(2)
    excel_data['等权投资金额'] = equal_investment[ticker].round(2)
    excel_data['加权投资金额'] = weighted_investment[ticker].round(2)
    excel_data['等权买入股数'] = (equal_investment[ticker] / excel_data['收盘价']).round(0).astype(int)
    excel_data['加权买入股数'] = shares_bought[ticker].round(0).astype(int)

    # 计算累计持股数和累计投资金额
    excel_data['等权累计持股数'] = excel_data['等权买入股数'].cumsum()
    excel_data['加权累计持股数'] = excel_data['加权买入股数'].cumsum()
    excel_data['等权累计投资'] = excel_data['等权投资金额'].cumsum().round(2)
    excel_data['加权累计投资'] = excel_data['加权投资金额'].cumsum().round(2)

    # 计算累计市值
    excel_data['等权累计市值'] = (excel_data['等权累计持股数'] * excel_data['收盘价']).round(2)
    excel_data['加权累计市值'] = (excel_data['加权累计持股数'] * excel_data['收盘价']).round(2)

    # 计算平均成本
    excel_data['等权平均成本'] = (excel_data['等权累计投资'] / excel_data['等权累计持股数']).round(2)
    excel_data['加权平均成本'] = (excel_data['加权累计投资'] / excel_data['加权累计持股数']).round(2)

    # 计算累计收益
    excel_data['等权累计收益'] = (excel_data['等权累计市值'] - excel_data['等权累计投资']).round(2)
    excel_data['加权累计收益'] = (excel_data['加权累计市值'] - excel_data['加权累计投资']).round(2)


    # 创建 output 目录（如果不存在）
    output_dir = 'output'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 修改文件保存路径
    filename = os.path.join(output_dir,
                            f"{ticker}_投资数据_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.xlsx")
    excel_data.to_excel(filename, index=False)
    print(f"数据已保存到文件: {filename}")


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

    # 计算MACD
    data[f'{ticker}_MACD'], data[f'{ticker}_MACD_SIGNAL'], _ = calculate_macd(
        data[ticker],
        short_window=config['macd_short_window'],
        long_window=config['macd_long_window'],
        signal_window=config['macd_signal_window']
    )

    # 将索引转换为日期类型
    data.index = pd.to_datetime(data.index).date

    # 创建投资日期列表
    investment_dates = get_investment_dates(start_date, end_date, data.index)

    if not investment_dates:
        raise ValueError("选定的日期范围内没有可用的投资日期")

    # 初始化结果DataFrame
    results = pd.DataFrame(index=investment_dates, columns=[ticker])
    investment_amounts = pd.DataFrame(index=investment_dates, columns=[ticker])
    last_buy_price = None

    # 模拟投资
    for d in investment_dates:
        price = data.loc[d, ticker]
        weight = calculate_weight(price, last_buy_price)
        investment_amount, shares_bought = calculate_investment(price, weight, config['base_investment'])

        results.loc[d, ticker] = shares_bought
        investment_amounts.loc[d, ticker] = investment_amount

        last_buy_price = price

    # 确保 investment_dates 中的日期都在 data 中存在
    valid_investment_dates = [date for date in investment_dates if date in data.index]


    # 计算等额定投策略
    equal_investment = pd.DataFrame(index=investment_dates, columns=[ticker])
    equal_shares = pd.DataFrame(index=investment_dates, columns=[ticker])
    for d in investment_dates:
        price = data.loc[d, ticker]
        equal_shares.loc[d, ticker] = config['base_investment'] // price
        equal_investment.loc[d, ticker] = equal_shares.loc[d, ticker] * price


    # 处理可能的零值
    price_data = data.loc[valid_investment_dates, ticker]
    price_data = price_data.replace(0, np.nan)  # 将零值替换为 NaN
    equal_shares = equal_investment.divide(price_data, axis=0)

    # 计算累积份额和策略价值
    equal_cumulative_shares = equal_shares.cumsum()
    weighted_cumulative_shares = results.cumsum()

    last_valid_date = data.index[-1]
    equal_portfolio_value = equal_cumulative_shares.multiply(data.loc[last_valid_date, ticker])
    weighted_portfolio_values = weighted_cumulative_shares.multiply(data.loc[last_valid_date, ticker])

    # 计算累计收益
    equal_cumulative_returns = equal_portfolio_value.subtract(equal_investment.cumsum(), axis=0)
    weighted_cumulative_returns = weighted_portfolio_values.subtract(investment_amounts.cumsum(), axis=0)

    # 清除旧图形
    plt.clf()
    # 修改绘图部分
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True, gridspec_kw={'height_ratios': [2, 1]})
    fig.subplots_adjust(hspace=0.1)

    # 在绘图部分
    ax1.plot(weighted_cumulative_returns.index, weighted_cumulative_returns[ticker], label=f'{ticker} 加权累计收益',
             color='blue')
    ax1.plot(equal_cumulative_returns.index, equal_cumulative_returns[ticker], label=f'{ticker} 等权累计收益', linestyle='--',
             color='orange')

    ax1.set_title(f'{ticker}: 加权累计收益 vs 等权累计收益 ({start_date.year}-{end_date.year})')
    ax1.set_ylabel('累计收益 ($)')
    ax1.legend()
    ax1.grid(True)

    # 添加零线
    ax1.axhline(y=0, color='red', linestyle=':', linewidth=1)

    # 绘制MACD
    ax2.plot(data.index, data[f'{ticker}_MACD'], label='MACD', color='blue')
    ax2.plot(data.index, data[f'{ticker}_MACD_SIGNAL'], label='Signal Line', color='red')
    ax2.bar(data.index, data[f'{ticker}_MACD'] - data[f'{ticker}_MACD_SIGNAL'], label='Histogram', color='gray', alpha=0.5)
    ax2.axhline(y=0, color='black', linestyle='--', linewidth=0.5)
    ax2.set_ylabel('MACD')
    ax2.legend(loc='upper left')
    ax2.grid(True)

    # 设置x轴标签
    ax2.set_xlabel('日期')

    # 设置 x 轴刻度
    years = mdates.YearLocator(2)  # 每两年
    months = mdates.MonthLocator()  # 每月
    years_fmt = mdates.DateFormatter('%Y')

    ax2.xaxis.set_major_locator(years)
    ax2.xaxis.set_major_formatter(years_fmt)
    ax2.xaxis.set_minor_locator(months)

    # 格式化 x 轴
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')

    # 自动调整日期范围
    ax2.set_xlim(data.index[0], data.index[-1])

    # 更新摘要统计
    total_weighted_investment = investment_amounts[ticker].sum()
    total_equal_investment = equal_investment[ticker].sum()
    weighted_final_value = weighted_portfolio_values[ticker].iloc[-1]
    equal_final_value = equal_portfolio_value[ticker].iloc[-1]

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

    # 更新摘要统计部分
    summary = f"\n{ticker} 的摘要统计：\n"
    summary += f"加权定投:\n"
    summary += f"  总投资: ${total_weighted_investment:.2f}\n"
    summary += f"  最终价值: ${weighted_final_value:.2f}\n"
    summary += f"  累计收益: ${weighted_cumulative_returns[ticker].iloc[-1]:.2f}\n"
    summary += f"  总回报率: {weighted_total_return:.2f}%\n"
    summary += f"  年化回报率: {weighted_annual_return:.2f}%\n"
    summary += f"等额定投:\n"
    summary += f"  总投资: ${total_equal_investment:.2f}\n"
    summary += f"  最终价值: ${equal_final_value:.2f}\n"
    summary += f"  累计收益: ${equal_cumulative_returns[ticker].iloc[-1]:.2f}\n"
    summary += f"  总回报率: {equal_total_return:.2f}%\n"
    summary += f"  年化回报率: {equal_annual_return:.2f}%\n"

    ax1.text(0.05, 0.05, summary, transform=ax1.transAxes, verticalalignment='bottom',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    # 调整布局
    plt.tight_layout()

    save_to_excel(data, equal_investment, investment_amounts, results, ticker, start_date, end_date)

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
start_date_entry.insert(0, "2022-01")  # 默认起始日期

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