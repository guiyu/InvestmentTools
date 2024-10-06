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


class InvestmentApp:
    def __init__(self, master):
        self.master = master
        self.master.title("投资策略分析")
        self.master.geometry("1024x768")

        # Vanguard Dividend Appreciation ETF (VIG)
        # 特点：VIG专注于持有持续增加股息的大型公司。具有高质量、低波动的特性，在熊市中往往表现较好，因为这些公司通常具有较强的盈利能力和稳健的现金流。
        # 防御性：持有的公司在市场动荡时表现相对较稳定，特别是在经济下滑时能依赖于稳健的股息支撑。
        # 牛市表现：虽然不像科技类ETF那样快速增长，但依靠其稳定的资产配置，也能在牛市中获得稳健回报。

        # iShares Edge MSCI Minimum Volatility USA ETF (USMV)
        # 特点：USMV通过投资于波动性较小的股票来降低投资组合的整体波动率。它的目标是提供类似标普500的市场回报，但波动率更低，在熊市中回撤较小。
        # 防御性：由于其策略侧重于低波动性资产，USMV在熊市中往往比市场整体表现更好，减少了大幅回撤的风险。
        # 牛市表现：尽管增长速度可能不如高风险ETF，但它可以在市场上涨时保持温和的上行潜力，适合追求稳定收益的长期投资者。

        # Invesco S&P 500 Low Volatility ETF (SPLV)
        # 特点：SPLV专注于持有标普500指数中波动性最低的100只股票。与USMV类似，它旨在降低市场波动，并减少熊市中的下行风险。
        # 防御性：低波动性的股票在市场大幅下挫时通常表现较为抗跌，尤其是在经济衰退期和市场不确定性增加时。
        # 牛市表现：虽然牛市中的涨幅可能不会像高增长类股票那样显著，但凭借稳健的持仓，SPLV依然能提供有竞争力的回报。

        # iShares Select Dividend ETF (DVY)
        # 特点：DVY投资于美国市场中股息收益率较高的股票，持仓集中在金融、公共事业和能源等板块。高股息股票通常表现相对稳健。
        # 防御性：高股息股票通常具备稳定的现金流和稳健的资产负债表，在市场下跌时，股息收益可以起到一定的缓冲作用。
        # 牛市表现：虽然高股息股票的增长潜力不如科技类股，但它们仍能够在经济复苏时取得稳定增长，同时股息收益进一步提高整体回报。

        #  Vanguard Consumer Staples ETF (VDC)
        # 特点：VDC专注于消费必需品行业，包括食品、饮料和家庭用品等领域。这类公司由于提供日常生活必需品，在经济波动时需求保持稳定。
        # 防御性：消费必需品行业在熊市中表现相对抗跌，因为无论经济状况如何，消费者仍需购买这些产品。
        # 牛市表现：虽然消费必需品行业的增长速度较为稳定，但它可以在牛市中依然提供持续的回报，并且通过稳健的股息政策进一步增强收益。

        # 配置
        self.config = {
            'tickers': ['SPY', 'QQQ', 'XLG', 'VIG', 'USMV', 'SPLV', 'DVY', 'VDC', 'VGT', 'KWEB'],
            'base_investment': 2000,
            'sma_window': 200,
            'std_window': 30,
            'min_weight': 0.5,
            'max_weight': 2,
            'macd_short_window': 12,
            'macd_long_window': 26,
            'macd_signal_window': 9,
        }

        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']
        plt.rcParams['axes.unicode_minus'] = False

        self.create_widgets()

    def create_widgets(self):
        # 创建左侧框架
        self.left_frame = ttk.Frame(self.master, padding="10")
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y, expand=False)

        # 创建日期输入框和标签
        self.create_date_inputs()

        # 创建下拉菜单
        self.create_ticker_dropdown()

        # 创建基础投资金额输入框
        self.create_base_investment_input()

        # 创建更新按钮
        self.update_button = ttk.Button(self.left_frame, text="更新图表", command=self.update_plot)
        self.update_button.pack(pady=10)

        # 创建右侧框架
        self.right_frame = ttk.Frame(self.master, padding="10")
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # 创建画布
        self.fig = plt.Figure(figsize=(10, 6))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.right_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(fill=tk.BOTH, expand=True)

    def create_date_inputs(self):
        ttk.Label(self.left_frame, text="起始日期 (YYYY-MM):").pack(anchor=tk.W, pady=(0, 5))
        self.start_date_entry = ttk.Entry(self.left_frame, width=10)
        self.start_date_entry.pack(anchor=tk.W, pady=(0, 10))
        self.start_date_entry.insert(0, "2022-01")

        ttk.Label(self.left_frame, text="结束日期 (YYYY-MM):").pack(anchor=tk.W, pady=(0, 5))
        self.end_date_entry = ttk.Entry(self.left_frame, width=10)
        self.end_date_entry.pack(anchor=tk.W, pady=(0, 10))
        self.end_date_entry.insert(0, datetime.now().strftime("%Y-%m"))

    def create_ticker_dropdown(self):
        ttk.Label(self.left_frame, text="选择股票:").pack(anchor=tk.W, pady=(10, 5))
        self.ticker_var = tk.StringVar()
        self.ticker_dropdown = ttk.Combobox(self.left_frame, textvariable=self.ticker_var,
                                            values=self.config['tickers'], width=10)
        self.ticker_dropdown.set(self.config['tickers'][0])
        self.ticker_dropdown.pack(anchor=tk.W, pady=(0, 10))

    def create_base_investment_input(self):
        ttk.Label(self.left_frame, text="基础投资金额 ($):").pack(anchor=tk.W, pady=(10, 5))
        self.base_investment_entry = ttk.Entry(self.left_frame, width=10)
        self.base_investment_entry.pack(anchor=tk.W, pady=(0, 10))
        self.base_investment_entry.insert(0, str(self.config['base_investment']))

    def update_plot(self):
        ticker = self.ticker_var.get()
        try:
            start_date = datetime.strptime(self.start_date_entry.get(), "%Y-%m").date()
            end_date = datetime.strptime(self.end_date_entry.get(), "%Y-%m").date()
            end_date = (date(end_date.year, end_date.month, 1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)

            new_base_investment = float(self.base_investment_entry.get())
            if new_base_investment <= 0:
                raise ValueError("基础投资金额必须大于0")
            self.config['base_investment'] = new_base_investment
        except ValueError as e:
            messagebox.showerror("错误", f"请输入有效的日期格式 (YYYY-MM) 和基础投资金额: {str(e)}")
            return

        if ticker not in self.config['tickers']:
            messagebox.showerror("错误", "选择的标的不存在")
            return
        if start_date >= end_date:
            messagebox.showerror("错误", "起始日期必须早于结束日期")
            return

        try:
            fig = self.analyze_and_plot(ticker, start_date, end_date)

            for widget in self.right_frame.winfo_children():
                widget.destroy()

            canvas = FigureCanvasTkAgg(fig, master=self.right_frame)
            canvas_widget = canvas.get_tk_widget()
            canvas_widget.pack(fill=tk.BOTH, expand=True)
            canvas.draw()
        except Exception as e:
            messagebox.showerror("错误", f"分析过程中出现错误: {str(e)}")

    # 将所有之前的独立函数转换为类方法
    def calculate_macd(self, data, short_window=12, long_window=26, signal_window=9):
        short_ema = data.ewm(span=short_window, adjust=False).mean()
        long_ema = data.ewm(span=long_window, adjust=False).mean()
        macd = short_ema - long_ema
        signal = macd.ewm(span=signal_window, adjust=False).mean()
        histogram = macd - signal
        return macd, signal, histogram

    def get_second_wednesday(self, date):
        # 获取给定月份的第一天
        first_day = date.replace(day=1)
        # 找到第一个周三
        first_wednesday = first_day + timedelta(days=(2 - first_day.weekday() + 7) % 7)
        # 第二个周三
        second_wednesday = first_wednesday + timedelta(days=7)
        return second_wednesday

    def get_nearest_business_day(self, date, data_index):
        while date not in data_index:
            date += timedelta(days=1)
            if date > data_index[-1]:
                return data_index[-1]  # 如果超出数据范围，返回最后一个可用日期
        return date

    def get_investment_dates(self, start_date, end_date, data_index):
        investment_dates = []
        current_date = start_date.replace(day=1)  # 从起始日期的当月开始

        while current_date <= end_date:
            # 获取当月第二周的周三
            investment_date = self.get_second_wednesday(current_date)

            # 如果投资日期在数据范围内，则添加到列表
            if start_date <= investment_date <= end_date:
                # 获取最近的交易日（如果当天不是交易日，则向后顺延）
                actual_investment_date = self.get_nearest_business_day(investment_date, data_index)
                investment_dates.append(actual_investment_date)

            # 移动到下一个月
            current_date = (current_date.replace(day=1) + timedelta(days=32)).replace(day=1)

        return investment_dates

    def calculate_weight(self, current_price, last_buy_price):
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

    # 修改投资计算函数
    def calculate_investment(self, price, weight, base_investment):
        max_shares = base_investment * weight // price
        return max_shares * price, max_shares

    # 修改 save_to_excel 函数
    def save_to_excel(self, data, equal_investment, weighted_investment, shares_bought, ticker, start_date, end_date):
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

        # 添加基础投资金额到 Excel 文件
        excel_data['基础投资金额'] = self.config['base_investment']

        # 创建 output 目录（如果不存在）
        output_dir = 'output'
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 修改文件保存路径
        filename = os.path.join(output_dir,
                                f"{ticker}_投资数据_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.xlsx")
        excel_data.to_excel(filename, index=False)
        print(f"数据已保存到文件: {filename}")

        # 保存累计收益数值
        equal_cumulative_returns = excel_data['等权累计收益']
        weighted_cumulative_returns = excel_data['加权累计收益']

        # 打印累计收益数值到终端
        print("\n等权累计收益:")
        print(equal_cumulative_returns)
        print("\n加权累计收益:")
        print(weighted_cumulative_returns)

        # 返回累计收益数值
        return equal_cumulative_returns, weighted_cumulative_returns

    def analyze_and_plot(self, ticker, start_date, end_date):
        # 下载数据
        data = yf.download(ticker, start=start_date, end=end_date)['Adj Close']

        # 确保数据是浮点数类型
        data = data.astype(float)

        # 计算技术指标
        data = pd.DataFrame(data)
        data.columns = [ticker]
        data[f'{ticker}_SMA'] = data[ticker].rolling(window=self.config['sma_window']).mean()
        data[f'{ticker}_STD'] = data[ticker].rolling(window=self.config['std_window']).std()
        data[f'{ticker}_AVG_STD'] = data[f'{ticker}_STD'].expanding().mean()

        # 计算MACD
        data[f'{ticker}_MACD'], data[f'{ticker}_MACD_SIGNAL'], _ = self.calculate_macd(
            data[ticker],
            short_window=self.config['macd_short_window'],
            long_window=self.config['macd_long_window'],
            signal_window=self.config['macd_signal_window']
        )

        # 将索引转换为日期类型
        data.index = pd.to_datetime(data.index).date

        # 创建投资日期列表
        investment_dates = self.get_investment_dates(start_date, end_date, data.index)

        if not investment_dates:
            raise ValueError("选定的日期范围内没有可用的投资日期")

        # 初始化结果DataFrame
        results = pd.DataFrame(index=investment_dates, columns=[ticker])
        investment_amounts = pd.DataFrame(index=investment_dates, columns=[ticker])
        last_buy_price = None

        # 使用更新后的 base_investment 值
        base_investment = self.config['base_investment']

        # 模拟投资
        for d in investment_dates:
            price = data.loc[d, ticker]
            weight = self.calculate_weight(price, last_buy_price)
            investment_amount, shares_bought = self.calculate_investment(price, weight, base_investment)

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
            equal_shares.loc[d, ticker] = base_investment // price
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

        # 使用更新后的 save_to_excel 函数
        equal_returns, weighted_returns = self.save_to_excel(data, equal_investment, investment_amounts, results, ticker,
                                                        start_date, end_date)

        # 清除旧图形
        plt.clf()
        # 修改绘图部分
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True, gridspec_kw={'height_ratios': [2, 1]})
        fig.subplots_adjust(hspace=0.1)

        # 绘制累计收益
        ax1.plot(equal_returns.index, equal_returns, label=f'{ticker} 等权累计收益', linestyle='--', color='orange')
        ax1.plot(weighted_returns.index, weighted_returns, label=f'{ticker} 加权累计收益', color='blue')

        ax1.set_title(f'{ticker}: 加权累计收益 vs 等权累计收益 ({start_date.year}-{end_date.year})')
        ax1.set_ylabel('累计收益 ($)')
        ax1.legend()
        ax1.grid(True)

        # 添加零线
        ax1.axhline(y=0, color='red', linestyle=':', linewidth=1)

        # 确保 y 轴的范围包含所有数据点，包括负值
        y_min = min(equal_returns.min(), weighted_returns.min())
        y_max = max(equal_returns.max(), weighted_returns.max())
        # 给顶部和底部一些额外的空间
        y_range = y_max - y_min
        ax1.set_ylim(y_min - 0.1 * y_range, y_max + 0.1 * y_range)

        print(f"Final weighted cumulative return plotted: {weighted_cumulative_returns[ticker].iloc[-1]:.2f}")
        print(f"Final equal cumulative return plotted: {equal_cumulative_returns[ticker].iloc[-1]:.2f}")

        # 添加数据点标注
        ax1.scatter(weighted_returns.index[-1], weighted_returns.iloc[-1], color='blue')
        ax1.annotate(f'{weighted_returns.iloc[-1]:.2f}',
                     (weighted_returns.index[-1], weighted_returns.iloc[-1]),
                     textcoords="offset points", xytext=(0, 10), ha='center')

        ax1.scatter(equal_returns.index[-1], equal_returns.iloc[-1], color='orange')
        ax1.annotate(f'{equal_returns.iloc[-1]:.2f}',
                     (equal_returns.index[-1], equal_returns.iloc[-1]),
                     textcoords="offset points", xytext=(0, 10), ha='center')

        # 获取图表中的实际值
        weighted_line = ax1.get_lines()[0]
        equal_line = ax1.get_lines()[1]
        print(f"Final weighted cumulative return on chart: {weighted_line.get_ydata()[-1]:.2f}")
        print(f"Final equal cumulative return on chart: {equal_line.get_ydata()[-1]:.2f}")

        # 绘制MACD
        ax2.plot(data.index, data[f'{ticker}_MACD'], label='MACD', color='blue')
        ax2.plot(data.index, data[f'{ticker}_MACD_SIGNAL'], label='Signal Line', color='red')
        ax2.bar(data.index, data[f'{ticker}_MACD'] - data[f'{ticker}_MACD_SIGNAL'], label='Histogram', color='gray',
                alpha=0.5)
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
        total_equal_investment = equal_investment[ticker].sum()
        total_weighted_investment = investment_amounts[ticker].sum()

        equal_final_value = total_equal_investment + equal_returns.iloc[-1]
        weighted_final_value = total_weighted_investment + weighted_returns.iloc[-1]

        equal_total_return = (equal_final_value / total_equal_investment - 1) * 100
        weighted_total_return = (weighted_final_value / total_weighted_investment - 1) * 100

        # 计算实际的投资日期范围
        actual_start_date = equal_returns.index[0]
        actual_end_date = equal_returns.index[-1]
        investment_period_days = (actual_end_date - actual_start_date).days

        equal_annual_return = ((equal_final_value / total_equal_investment) ** (
                365.25 / investment_period_days) - 1) * 100
        weighted_annual_return = ((weighted_final_value / total_weighted_investment) ** (
                365.25 / investment_period_days) - 1) * 100

        # 更新摘要统计文本
        summary = f"\n{ticker} 的摘要统计：\n"
        summary += f"等额定投:\n"
        summary += f"  总投资: ${total_equal_investment:.2f}\n"
        summary += f"  最终价值: ${equal_final_value:.2f}\n"
        summary += f"  累计收益: ${equal_returns.iloc[-1]:.2f}\n"
        summary += f"  总回报率: {equal_total_return:.2f}%\n"
        summary += f"  年化回报率: {equal_annual_return:.2f}%\n"
        summary += f"加权定投:\n"
        summary += f"  总投资: ${total_weighted_investment:.2f}\n"
        summary += f"  最终价值: ${weighted_final_value:.2f}\n"
        summary += f"  累计收益: ${weighted_returns.iloc[-1]:.2f}\n"
        summary += f"  总回报率: {weighted_total_return:.2f}%\n"
        summary += f"  年化回报率: {weighted_annual_return:.2f}%\n"

        ax1.text(0.05, 0.05, summary, transform=ax1.transAxes, verticalalignment='bottom',
                 bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        # 调整布局
        plt.tight_layout()

        # save_to_excel(data, equal_investment, investment_amounts, results, ticker, start_date, end_date)

        return fig


if __name__ == "__main__":
    root = tk.Tk()
    app = InvestmentApp(root)
    root.mainloop()
