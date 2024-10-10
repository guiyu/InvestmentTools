import json
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
import schedule as schedule_lib
import time
import threading
import pytz
from datetime import datetime, time
from pushplus_sender import PushPlusSender  # 导入新的 PushPlusSender 类
from investment_tracker import InvestmentTracker
import requests
import time


class InvestmentApp:
    def __init__(self, master):
        self.master = master
        self.master.title("投资策略分析")
        self.master.geometry("1024x768")
        self.token_file = 'pushplus_token.json'
        self.pushplus_token = self.load_token()
        self.investment_tracker = None
        self.is_logged_in = False


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

        # SPLG 标普500 ETF

        # 配置
        self.config = {
            'tickers': ['SPY', 'QQQ', 'XLG', 'SPLG', 'RSP', 'VTI', 'VTV', 'SCHD', 'VGT', 'KWEB'],
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

        self.pushplus_sender = None
        self.reminder_thread = None
        self.bot = None
        self.reminder_thread = None
        self.create_widgets()

    def load_token(self):
        if os.path.exists(self.token_file):
            with open(self.token_file, 'r') as f:
                data = json.load(f)
                return data.get('token')
        return None

    def save_token(self, token):
        with open(self.token_file, 'w') as f:
            json.dump({'token': token}, f)

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

        # 添加"当天定投估值"按钮
        self.estimate_button = ttk.Button(self.left_frame, text="当天定投估值", command=self.estimate_today_investment)
        self.estimate_button.pack(pady=10)

        # 创建微信登录按钮
        self.login_button = ttk.Button(self.left_frame, text="PushPlus登录", command=self.pushplus_login)
        self.login_button.pack(pady=10)

        # 添加"输入投资信息"按钮
        self.input_investment_button = ttk.Button(self.left_frame, text="输入投资信息", command=self.show_investment_input_dialog)
        self.input_investment_button.pack(pady=10)

        # 创建启动/停止提醒按钮
        self.reminder_button = ttk.Button(self.left_frame, text="启动提醒", command=self.toggle_reminder)
        self.reminder_button.pack(pady=10)

        # 创建右侧框架
        self.right_frame = ttk.Frame(self.master, padding="10")
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # 初始化图表
        self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True,
                                                      gridspec_kw={'height_ratios': [2, 1]})
        self.fig.subplots_adjust(hspace=0.1)

        # 设置初始坐标轴
        self.ax1.set_ylabel('累计收益 ($)')
        self.ax2.set_ylabel('MACD')
        self.ax2.set_xlabel('日期')

        # 创建画布
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.right_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(fill=tk.BOTH, expand=True)

    def estimate_today_investment(self):
        ticker = self.ticker_var.get()
        beijing_tz = pytz.timezone('Asia/Shanghai')
        now = datetime.now(beijing_tz)

        # 获取股票数据
        stock = yf.Ticker(ticker)

        # 检查是否在交易时间
        trading_start = time(9, 30)
        trading_end = time(16, 0)
        current_time = now.time()

        try:
            if trading_start <= current_time <= trading_end and now.weekday() < 5:
                # 交易时间，尝试获取当前价格
                try:
                    current_price = stock.info['regularMarketPrice']
                except KeyError:
                    # 如果无法获取regularMarketPrice，尝试使用最新的收盘价
                    hist = stock.history(period="1d")
                    if hist.empty:
                        raise ValueError("无法获取当前价格和历史数据")
                    current_price = hist['Close'].iloc[-1]
            else:
                # 非交易时间，获取最近的收盘价
                end_date = now.date()
                start_date = end_date - timedelta(days=5)  # 获取过去5天的数据
                hist = stock.history(start=start_date, end=end_date)
                if hist.empty:
                    raise ValueError("无法获取历史数据")
                current_price = hist['Close'].iloc[-1]

            # 计算建议购买的股票数和投资金额
            weight = self.calculate_weight(current_price, None)  # 假设这是首次购买
            investment_amount, shares_to_buy = self.calculate_investment(current_price, weight,
                                                                         self.config['base_investment'])
            # 计算下一次定投时间
            next_investment_date = self.get_next_investment_date(now)

            # 准备消息内容
            message = (
                f"定投估值报告\n\n"
                f"日期时间: {now.strftime('%Y-%m-%d %H:%M:%S')} (北京时间)\n"
                f"股票: {ticker}\n"
                f"当前价格: ${current_price:.2f}\n"
                f"建议购买股数: {shares_to_buy}\n"
                f"本次投资金额: ${investment_amount:.2f}\n"
                f"下一次预计定投时间: {next_investment_date.strftime('%Y-%m-%d')}"
            )

            # 在GUI中显示消息
            messagebox.showinfo("今日定投估值", message)

            # 保存投资信息
            self.save_investment_info(ticker, now, current_price, shares_to_buy, investment_amount)

        except Exception as e:
            error_message = f"估值过程中出现错误: {str(e)}"
            messagebox.showerror("错误", error_message)
            print(error_message)  # 打印错误信息到控制台以便调试

    def get_next_investment_date(self, current_date):
        next_date = current_date.replace(day=1) + timedelta(days=32)
        next_date = next_date.replace(day=1)  # 下个月的第一天
        while next_date.weekday() != 2:  # 2 表示周三
            next_date += timedelta(days=1)
        return next_date + timedelta(days=7)  # 第二个周三

    def save_investment_info(self, ticker, date, price, shares, amount):
        investment_file = 'investment_history.json'

        # 读取现有的投资历史
        if os.path.exists(investment_file):
            with open(investment_file, 'r') as f:
                history = json.load(f)
        else:
            history = []

        # 添加新的投资信息
        investment_info = {
            'date': date.strftime('%Y-%m-%d %H:%M:%S'),
            'ticker': ticker,
            'price': price,
            'shares': shares,
            'amount': amount
        }
        history.append(investment_info)

        # 保存更新后的历史
        with open(investment_file, 'w') as f:
            json.dump(history, f, indent=4)

    def show_investment_input_dialog(self):
        if not self.investment_tracker:
            messagebox.showerror("错误", "请先登录PushPlus")
            return

        dialog = tk.Toplevel(self.master)
        dialog.title("输入投资信息")

        tk.Label(dialog, text="标的名称:").grid(row=0, column=0, padx=5, pady=5)
        ticker_entry = ttk.Combobox(dialog, values=self.config['tickers'])
        ticker_entry.grid(row=0, column=1, padx=5, pady=5)
        ticker_entry.set(self.ticker_var.get())  # 默认选择当前选中的标的

        tk.Label(dialog, text="股票价格:").grid(row=1, column=0, padx=5, pady=5)
        price_entry = ttk.Entry(dialog)
        price_entry.grid(row=1, column=1, padx=5, pady=5)

        tk.Label(dialog, text="交易数量:").grid(row=2, column=0, padx=5, pady=5)
        shares_entry = ttk.Entry(dialog)
        shares_entry.grid(row=2, column=1, padx=5, pady=5)

        def save_investment():
            ticker = ticker_entry.get()
            try:
                price = float(price_entry.get())
                shares = int(shares_entry.get())
            except ValueError:
                messagebox.showerror("错误", "请输入有效的价格和数量")
                return

            amount = price * shares
            date = self.investment_tracker.find_closest_date(ticker, price)
            self.investment_tracker.save_investment_info(ticker, date, price, shares, amount)
            dialog.destroy()
            messagebox.showinfo("成功", "投资信息已保存")

        ttk.Button(dialog, text="保存", command=save_investment).grid(row=3, column=0, columnspan=2, pady=10)

    def pushplus_login(self):
        if self.pushplus_sender is None:
            token = self.pushplus_token
            if not token:
                token = tk.simpledialog.askstring(
                    "PushPlus Token",
                    "请输入您的PushPlus Token:\n\n"
                    "如果您还没有 Token，请访问 https://www.pushplus.plus/ 获取。\n"
                    "在该网站注册并登录后，您可以在个人中心找到您的 Token。"
                )
            if token:
                self.pushplus_sender = PushPlusSender(token)
                self.investment_tracker = InvestmentTracker(token)
                self.is_logged_in = True
                self.login_button.config(text="退出登录")

                # 获取当前北京时间
                beijing_time = datetime.now(pytz.timezone('Asia/Shanghai'))
                time_str = beijing_time.strftime("%Y-%m-%d %H:%M:%S")

                # 发送包含时间戳的测试消息
                test_result = self.pushplus_sender.send_message(
                    "登录测试",
                    f"PushPlus登录成功\n\n时间：{time_str} (北京时间)"
                )

                if test_result:
                    messagebox.showinfo("登录成功", f"PushPlus登录成功！\n\n测试消息发送时间：{time_str}")
                    self.login_button.config(text="退出登录")
                    self.pushplus_token = token
                    self.save_token(token)
                else:
                    messagebox.showerror("登录失败", "PushPlus登录失败，请检查您的Token。")
                    self.pushplus_sender = None
                    self.pushplus_token = None
                    self.is_logged_in = False
                    self.investment_tracker = None
                    self.login_button.config(text="PushPlus登录")

        else:
            self.pushplus_sender = None
            self.pushplus_token = None
            self.is_logged_in = False
            self.investment_tracker = None
            self.save_token(None)
            self.login_button.config(text="PushPlus登录")
            messagebox.showinfo("退出成功", "已退出PushPlus登录")

    def destroy(self):
        if self.pushplus_token:
            self.save_token(self.pushplus_token)
        self.master.destroy()

    def check_login(self):
        if not self.is_logged_in or self.investment_tracker is None:
            messagebox.showerror("错误", "请先登录PushPlus")
            return False
        return True

    def create_date_inputs(self):
        ttk.Label(self.left_frame, text="起始日期 (YYYY-MM):").pack(anchor=tk.W, pady=(0, 5))
        self.start_date_entry = ttk.Entry(self.left_frame, width=10)
        self.start_date_entry.pack(anchor=tk.W, pady=(0, 10))
        self.start_date_entry.insert(0, "2024-01")

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
        if not self.check_login():
            return
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

            # 清除旧的图形内容
            for widget in self.right_frame.winfo_children():
                widget.destroy()

            # 创建新的画布并显示更新后的图形
            self.canvas = FigureCanvasTkAgg(fig, master=self.right_frame)
            self.canvas_widget = self.canvas.get_tk_widget()
            self.canvas_widget.pack(fill=tk.BOTH, expand=True)
            self.canvas.draw()

            print("图形已更新")  # 添加这行来确认方法执行到此处
        except Exception as e:
            messagebox.showerror("错误", f"分析过程中出现错误: {str(e)}")
            print(f"错误详情: {str(e)}")  # 添加这行来打印详细错误信息

    # def wechat_login(self):
    #     if self.bot is None:
    #         try:
    #             self.bot = Bot(cache_path=True)
    #             qr = qrcode.QRCode(version=1, box_size=10, border=5)
    #             qr.add_data(self.bot.uuid)
    #             qr.make(fit=True)
    #             img = qr.make_image(fill_color="black", back_color="white")
    #
    #             # 将二维码图片显示在GUI上
    #             buffer = io.BytesIO()
    #             img.save(buffer, format="PNG")
    #             image = Image.open(buffer)
    #             photo = ImageTk.PhotoImage(image)
    #
    #             qr_window = tk.Toplevel(self.master)
    #             qr_window.title("微信登录")
    #             qr_label = ttk.Label(qr_window, image=photo)
    #             qr_label.image = photo
    #             qr_label.pack()
    #
    #             messagebox.showinfo("登录成功", "微信登录成功！")
    #             self.login_button.config(text="退出登录")
    #         except Exception as e:
    #             messagebox.showerror("登录失败", f"微信登录失败: {str(e)}")
    #     else:
    #         self.bot.logout()
    #         self.bot = None
    #         self.login_button.config(text="微信登录")
    #         messagebox.showinfo("退出成功", "已退出微信登录")

    def toggle_reminder(self):
        if self.reminder_thread is None:
            self.start_reminder()
        else:
            self.stop_reminder()

    def start_reminder(self):
        if self.pushplus_sender is None:
            messagebox.showerror("错误", "请先登录PushPlus")
            return

        self.reminder_thread = threading.Thread(target=self.run_reminder, daemon=True)
        self.reminder_thread.start()
        self.reminder_button.config(text="停止提醒")
        messagebox.showinfo("提醒已启动", "定投提醒功能已启动")

    def run_reminder(self):
        schedule_lib.every().day.at("08:00").do(self.send_investment_reminder)
        while self.reminder_thread:
            schedule_lib.run_pending()
            time.sleep(60)

    def stop_reminder(self):
        if self.reminder_thread:
            schedule_lib.clear()
            self.reminder_thread = None
            self.reminder_button.config(text="启动提醒")
            messagebox.showinfo("提醒已停止", "定投提醒功能已停止")

    def send_investment_reminder(self):
        if self.pushplus_sender is None:
            print("PushPlus未登录，无法发送提醒")
            return

        today = datetime.now().date()
        if self.get_second_wednesday(today) == today:
            for ticker in self.config['tickers']:
                data = yf.download(ticker, start=today - timedelta(days=365), end=today)['Adj Close']
                if not data.empty:
                    current_price = data.iloc[-1]
                    weight = self.calculate_weight(current_price, data.iloc[-2] if len(data) > 1 else None)
                    investment_amount, shares_to_buy = self.calculate_investment(current_price, weight,
                                                                                 self.config['base_investment'])

                    message = (f"今日是定投日，股票 {ticker} 的定投提醒：\n"
                               f"收盘价: ${current_price:.2f}\n"
                               f"建议购买股数: {shares_to_buy}\n"
                               f"加权投资金额: ${investment_amount:.2f}")

                    self.pushplus_sender.send_message(f"{ticker}定投提醒", message)
                    print(f"已发送 {ticker} 的定投提醒")
        else:
            print("今天不是定投日")

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

    def calculate_weight(self, ticker, current_price, current_shares, equal_shares, base_investment, historical_data,
                         total_investment, equal_weight_investment, month):
        # 确保最低投资额
        min_weight = 0.8

        # 计算当前持股差异百分比
        shares_difference = (current_shares - equal_shares) / equal_shares if equal_shares > 0 else 0

        # 基础权重
        if shares_difference < -0.1:  # 如果加权持股少于等权持股的90%
            weight = 1.5
        elif shares_difference > 0.1:  # 如果加权持股多于等权持股的110%
            weight = 0.5
        else:
            weight = 1.0

        # 计算市场趋势指标
        sma_50 = historical_data[ticker].rolling(window=50).mean().iloc[-1]
        sma_200 = historical_data[ticker].rolling(window=200).mean().iloc[-1]
        rsi = self.calculate_rsi(historical_data[ticker]).iloc[-1]

        # 根据市场趋势调整权重
        if current_price < sma_50 and current_price < sma_200:  # 强烈下跌趋势
            weight *= 1.5
        elif current_price < sma_50 or current_price < sma_200:  # 轻微下跌趋势
            weight *= 1.2
        elif current_price > sma_50 and current_price > sma_200:  # 上涨趋势
            if rsi > 70:  # 可能出现超买
                weight *= 0.8
            else:
                weight *= 1.0

        # 控制年度总投资额
        if month % 12 == 0:  # 每年年底
            investment_ratio = total_investment / equal_weight_investment
            if investment_ratio > 1.1:  # 如果总投资额超过等权投资10%
                weight = max(0.5, weight - 0.3)  # 减少投资但保持最低投资
            elif investment_ratio < 0.9:  # 如果总投资额低于等权投资10%
                weight += 0.3  # 增加投资

        # 考虑兑现部分收益
        if shares_difference > 0.2 and rsi > 70:  # 如果持股显著多于等权且RSI高
            sell_proportion = min(shares_difference - 0.1, 0.1)  # 最多卖出到比等权多10%
            return -sell_proportion  # 返回负值表示卖出

        # 确保权重在合理范围内
        return max(min(weight, 2), min_weight)

    def calculate_rsi(self, prices, period=14):
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def calculate_target_value(self, initial_investment, months, annual_rate=0.12):
        monthly_rate = (1 + annual_rate) ** (1 / 12) - 1
        return initial_investment * (1 + monthly_rate) ** months

    # 修改投资计算函数
    def calculate_investment(self, price, weight, base_investment):
        investment_amount = base_investment * weight
        shares_bought = (investment_amount / price).round(0).astype(int)
        actual_investment = shares_bought * price
        return actual_investment, shares_bought

    # 修改 save_to_excel 函数
    def save_to_excel(self, data, equal_investment, weighted_investment, shares_bought, ticker, start_date, end_date):
        investment_dates = equal_investment.index
        excel_data = pd.DataFrame(index=investment_dates)

        excel_data['日期'] = investment_dates
        excel_data['收盘价'] = data.loc[investment_dates, ticker].round(2)
        excel_data['等权投资金额'] = equal_investment[ticker].round(2)
        excel_data['加权投资金额'] = weighted_investment[ticker].round(2)

        # 1. 使用四舍五入计算买入股数
        excel_data['等权买入股数'] = np.round(excel_data['等权投资金额'] / excel_data['收盘价']).astype(int)
        excel_data['加权买入股数'] = np.round(excel_data['加权投资金额'] / excel_data['收盘价']).astype(int)

        # 2. 计算实际投资金额
        excel_data['等权实际投资金额'] = (excel_data['等权买入股数'] * excel_data['收盘价']).round(2)
        excel_data['加权实际投资金额'] = (excel_data['加权买入股数'] * excel_data['收盘价']).round(2)

        # 计算累计持股数和累计投资金额
        excel_data['等权累计持股数'] = excel_data['等权买入股数'].cumsum()
        excel_data['加权累计持股数'] = excel_data['加权买入股数'].cumsum()
        excel_data['等权累计投资'] = excel_data['等权实际投资金额'].cumsum().round(2)
        excel_data['加权累计投资'] = excel_data['加权实际投资金额'].cumsum().round(2)

        # 计算累计市值
        excel_data['等权累计市值'] = (excel_data['等权累计持股数'] * excel_data['收盘价']).round(2)
        excel_data['加权累计市值'] = (excel_data['加权累计持股数'] * excel_data['收盘价']).round(2)

        # 3. 更新平均成本的计算
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

    def check_internet_connection(self):
        try:
            # 尝试连接到 Yahoo Finance 的网站
            response = requests.get("https://finance.yahoo.com", timeout=5)
            return response.status_code == 200
        except requests.ConnectionError:
            return False

    def analyze_and_plot(self, ticker, start_date, end_date):
        if not self.check_login():
            return None

        # 检查网络连接
        if not self.check_internet_connection():
            messagebox.showerror("网络错误", "无法连接到互联网。请检查您的网络连接后重试。")
            return None

        # 下载数据
        data = yf.download(ticker, start=start_date, end=end_date)['Adj Close']

        # 确保数据是浮点数类型
        data = data.astype(float)

        # 计算技术指标
        data = pd.DataFrame(data)
        data.columns = [ticker]
        data[f'{ticker}_SMA50'] = data[ticker].rolling(window=50).mean()
        data[f'{ticker}_SMA200'] = data[ticker].rolling(window=200).mean()
        data['RSI'] = self.calculate_rsi(data[ticker])

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
        base_investment = self.config['base_investment']
        weighted_investment = pd.DataFrame(index=investment_dates, columns=[ticker])
        equal_investment = pd.DataFrame(index=investment_dates, columns=[ticker])
        weighted_shares = pd.DataFrame(index=investment_dates, columns=[ticker])
        equal_shares = pd.DataFrame(index=investment_dates, columns=[ticker])

        total_weighted_investment = 0
        total_equal_investment = 0
        weighted_shares_held = 0
        equal_shares_held = 0

        for i, d in enumerate(investment_dates):
            current_data = data.loc[:d]
            price = current_data[ticker].iloc[-1]

            # 等额定投策略
            equal_invest_amount = base_investment
            equal_shares_bought = equal_invest_amount / price
            equal_shares_held += equal_shares_bought
            total_equal_investment += equal_invest_amount

            # 加权定投策略
            weight = self.calculate_weight(ticker, price, weighted_shares_held, equal_shares_held,
                                           base_investment, current_data, total_weighted_investment,
                                           total_equal_investment, i + 1)

            if weight >= 0:  # 买入
                weighted_invest_amount = base_investment * weight
                weighted_shares_bought = weighted_invest_amount / price
                weighted_shares_held += weighted_shares_bought
                total_weighted_investment += weighted_invest_amount
            else:  # 卖出
                shares_to_sell = abs(weight) * weighted_shares_held
                weighted_shares_held -= shares_to_sell
                total_weighted_investment -= shares_to_sell * price
                weighted_invest_amount = -shares_to_sell * price
                weighted_shares_bought = -shares_to_sell

            weighted_investment.loc[d, ticker] = weighted_invest_amount
            equal_investment.loc[d, ticker] = equal_invest_amount
            weighted_shares.loc[d, ticker] = weighted_shares_bought
            equal_shares.loc[d, ticker] = equal_shares_bought

        # 计算累积份额和策略价值
        weighted_cumulative_shares = weighted_shares.cumsum()
        equal_cumulative_shares = equal_shares.cumsum()

        weighted_portfolio_values = weighted_cumulative_shares.multiply(data.loc[investment_dates, ticker], axis=0)
        equal_portfolio_values = equal_cumulative_shares.multiply(data.loc[investment_dates, ticker], axis=0)

        # 计算累计收益
        weighted_cumulative_returns = weighted_portfolio_values.subtract(weighted_investment.cumsum(), axis=0)
        equal_cumulative_returns = equal_portfolio_values.subtract(equal_investment.cumsum(), axis=0)

        # 保存到Excel
        self.save_to_excel(data, equal_investment, weighted_investment, weighted_shares, ticker, start_date, end_date)

        # 绘图
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True, gridspec_kw={'height_ratios': [2, 1]})
        fig.subplots_adjust(hspace=0.1)

        ax1.plot(equal_cumulative_returns.index, equal_cumulative_returns[ticker], label=f'{ticker} 等权累计收益',
                 linestyle='--', color='orange')
        ax1.plot(weighted_cumulative_returns.index, weighted_cumulative_returns[ticker], label=f'{ticker} 加权累计收益',
                 linestyle='--', color='blue')

        ax1.set_title(f'{ticker}: 加权累计收益 vs 等权累计收益 ({start_date.year}-{end_date.year})')
        ax1.set_ylabel('累计收益 ($)')
        ax1.legend()
        ax1.grid(True)

        # 添加零线
        ax1.axhline(y=0, color='red', linestyle=':', linewidth=1)

        # 确保 y 轴的范围包含所有数据点
        y_min = min(equal_cumulative_returns[ticker].min(), weighted_cumulative_returns[ticker].min())
        y_max = max(equal_cumulative_returns[ticker].max(), weighted_cumulative_returns[ticker].max())
        y_range = y_max - y_min
        ax1.set_ylim(y_min - 0.1 * y_range, y_max + 0.1 * y_range)

        # 添加终点标注
        ax1.scatter(weighted_cumulative_returns.index[-1], weighted_cumulative_returns[ticker].iloc[-1], color='blue')
        ax1.annotate(f'{weighted_cumulative_returns[ticker].iloc[-1]:.2f}',
                     (weighted_cumulative_returns.index[-1], weighted_cumulative_returns[ticker].iloc[-1]),
                     textcoords="offset points", xytext=(0, 10), ha='center')

        ax1.scatter(equal_cumulative_returns.index[-1], equal_cumulative_returns[ticker].iloc[-1], color='orange')
        ax1.annotate(f'{equal_cumulative_returns[ticker].iloc[-1]:.2f}',
                     (equal_cumulative_returns.index[-1], equal_cumulative_returns[ticker].iloc[-1]),
                     textcoords="offset points", xytext=(0, 10), ha='center')

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
        total_weighted_investment = weighted_investment[ticker].sum()

        equal_final_value = equal_portfolio_values[ticker].iloc[-1]
        weighted_final_value = weighted_portfolio_values[ticker].iloc[-1]

        equal_total_return = (equal_final_value / total_equal_investment - 1) * 100
        weighted_total_return = (weighted_final_value / total_weighted_investment - 1) * 100

        investment_period_days = (end_date - start_date).days

        equal_annual_return = ((equal_final_value / total_equal_investment) ** (
                    365.25 / investment_period_days) - 1) * 100
        weighted_annual_return = ((weighted_final_value / total_weighted_investment) ** (
                    365.25 / investment_period_days) - 1) * 100

        # 更新摘要统计文本
        summary = f"\n{ticker} 的摘要统计：\n"
        summary += f"等额定投:\n"
        summary += f"  总投资: ${total_equal_investment:.2f}\n"
        summary += f"  最终价值: ${equal_final_value:.2f}\n"
        summary += f"  累计收益: ${equal_cumulative_returns[ticker].iloc[-1]:.2f}\n"
        summary += f"  总回报率: {equal_total_return:.2f}%\n"
        summary += f"  年化回报率: {equal_annual_return:.2f}%\n"
        summary += f"加权定投:\n"
        summary += f"  总投资: ${total_weighted_investment:.2f}\n"
        summary += f"  最终价值: ${weighted_final_value:.2f}\n"
        summary += f"  累计收益: ${weighted_cumulative_returns[ticker].iloc[-1]:.2f}\n"
        summary += f"  总回报率: {weighted_total_return:.2f}%\n"
        summary += f"  年化回报率: {weighted_annual_return:.2f}%\n"

        ax1.text(0.05, 0.05, summary, transform=ax1.transAxes, verticalalignment='bottom',
                 bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        # 调整布局
        plt.tight_layout()
        return fig


if __name__ == "__main__":
    root = tk.Tk()
    app = InvestmentApp(root)
    root.protocol("WM_DELETE_WINDOW", app.destroy)
    root.mainloop()
