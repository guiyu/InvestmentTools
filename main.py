import argparse
import json
import os
import yfinance as yf
import numpy as np
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
import pandas as pd
import threading
import pytz
import logging
from AssetAllocationDialog import AssetAllocationDialog
from pushplus_sender import PushPlusSender
from investment_tracker import InvestmentTracker
import requests
import time
from datetime import datetime, timedelta, date, time as datetime_time
import schedule

from matplotlib import font_manager

# 在文件顶部添加这个打印语句，以确认导入成功
print("All modules imported successfully, including time module")


def test_schedule():
    print("Schedule test function executed at", datetime.now())


# 测试 schedule 的基本功能
schedule.every(5).seconds.do(test_schedule)


class InvestmentApp:
    def __init__(self, master=None):
        self.master = master
        self.token_file = 'pushplus_token.json'
        self.pushplus_token = self.load_token()
        self.pushplus_sender = None
        self.investment_tracker = None
        self.is_logged_in = False
        self.setup_logger()
        self.setup_chinese_font()

        plt.rcParams['axes.unicode_minus'] = False

        # 配置
        self.config = {
            'tickers': ['VOO', 'QQQ', 'SPLG', 'RSP', 'VTI', 'VTV', 'SCHD', 'VGT', 'TLT', 'IEI','BND','DBC','GLD', 'XLV','NVDA'],
            'base_investment': 4000,
            'sma_window': 200,
            'std_window': 30,
            'min_weight': 0.5,
            'max_weight': 2,
            'macd_short_window': 12,
            'macd_long_window': 26,
            'macd_signal_window': 9,
        }

        self.portfolio_allocations = {}

        self.pushplus_sender = None
        self.reminder_thread = None
        self.stop_flag = threading.Event()
        self.bot = None

        # GUI 相关的属性初始化为 None
        self.left_frame = None
        self.right_frame = None
        self.start_date_entry = None
        self.end_date_entry = None
        self.ticker_var = None
        self.ticker_dropdown = None
        self.base_investment_entry = None
        self.update_button = None
        self.estimate_button = None
        self.login_button = None
        self.input_investment_button = None
        self.reminder_button = None
        self.fig = None
        self.ax1 = None
        self.ax2 = None
        self.canvas = None
        self.canvas_widget = None

        # 只在 GUI 模式下初始化窗口和组件
        if self.master is not None:
            self.init_gui()

        # 在 GUI 初始化之后尝试自动登录
        if self.pushplus_token:
            self.auto_login()

    def init_gui(self):
        self.master.title("投资策略分析")
        self.master.geometry("1024x768")
        self.create_widgets()

    def auto_login(self):
        """从本地文件自动登录"""
        if not self.is_logged_in and self.pushplus_token:
            if self.pushplus_login(self.pushplus_token):
                print("已使用保存的 token 自动登录")
            else:
                print("自动登录失败，请手动登录")
                # 自动登录失败时，确保清理状态
                self.logout()

    def load_token(self):
        if os.path.exists(self.token_file):
            with open(self.token_file, 'r') as f:
                data = json.load(f)
                return data.get('token')
        return None

    def save_token(self, token):
        with open(self.token_file, 'w') as f:
            json.dump({'token': token}, f)

    def open_asset_allocation_dialog(self):
        dialog = AssetAllocationDialog(self.master, self.config['tickers'])
        result = dialog.show()
        if result:
            self.portfolio_allocations = result
            print("资产组合配置:", self.portfolio_allocations)
            # 触发图表更新
            self.update_plot()
        else:
            print("用户取消了资产配置")

    def create_widgets(self):
        if self.master is None:
            return

            # 创建左侧框架
        self.left_frame = ttk.Frame(self.master, padding="10")
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y, expand=False)

        # 创建日期输入框和标签
        self.create_date_inputs()

        # 创建下拉菜单
        self.create_ticker_dropdown()

        # 创建基础投资金额输入框
        self.create_base_investment_input()

        # 创建主要功能按钮
        self.update_button = ttk.Button(self.left_frame, text="更新图表", command=self.update_plot)
        self.update_button.pack(pady=10)

        self.estimate_button = ttk.Button(self.left_frame, text="当天定投估值", command=self.estimate_today_investment)
        self.estimate_button.pack(pady=10)

        # self.input_investment_button = ttk.Button(self.left_frame, text="输入投资信息",
        #                                           command=self.show_investment_input_dialog)
        # self.input_investment_button.pack(pady=10)

        self.portfolio_button = ttk.Button(self.left_frame, text="设置资产组合", command=self.open_asset_allocation_dialog)
        self.portfolio_button.pack(pady=10)

        # 添加分割线
        ttk.Separator(self.left_frame, orient='horizontal').pack(fill='x', pady=15)

        # 创建PushPlus相关按钮（竖直排列）
        pushplus_frame = ttk.Frame(self.left_frame)
        pushplus_frame.pack(pady=10)

        # PushPlus登录按钮
        self.login_button = ttk.Button(pushplus_frame, text="PushPlus登录", command=self.pushplus_login)
        self.login_button.pack(pady=(0, 5))  # 上边距0，下边距5

        # 启动提醒按钮
        self.reminder_button = ttk.Button(pushplus_frame, text="启动提醒", command=self.toggle_reminder)
        self.reminder_button.pack(pady=(5, 0))  # 上边距5，下边距0

        # 创建右侧框架和图表（保持不变）
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
        # if not self.is_logged_in:
        #     return "请先登录PushPlus"

        try:
            # 在 CLI 模式下使用默认 ticker
            if hasattr(self, 'ticker_var') and self.ticker_var:
                ticker = self.ticker_var.get()
            else:
                ticker = self.config['tickers'][0]  # 使用配置中的第一个 ticker 作为默认值

            if not isinstance(ticker, str):
                raise TypeError(f"股票标识符必须是字符串，而不是 {type(ticker)}")

            beijing_tz = pytz.timezone('Asia/Shanghai')
            now = datetime.now(beijing_tz)

            # 获取股票数据
            stock = yf.Ticker(ticker)

            # 检查是否在交易时间
            trading_start = datetime_time(9, 30)
            trading_end = datetime_time(16, 0)
            current_time = now.time()

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

            # 确保 current_price 是浮点数
            if not isinstance(current_price, (int, float)):
                raise TypeError(f"当前价格必须是数字，而不是 {type(current_price)}")
            current_price = float(current_price)

            # 计算建议购买的股票数和投资金额
            weight = self.calculate_weight(current_price)
            investment_amount, shares_to_buy = self.calculate_investment(current_price, weight,
                                                                         self.config['base_investment'])

            # 确保计算结果是正确的类型
            if not isinstance(investment_amount, (int, float)):
                raise TypeError(f"投资金额必须是数字，而不是 {type(investment_amount)}")
            if not isinstance(shares_to_buy, int):
                raise TypeError(f"购买股数必须是整数，而不是 {type(shares_to_buy)}")

            investment_amount = float(investment_amount)
            shares_to_buy = int(shares_to_buy)

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
            if self.master:
                messagebox.showinfo("今日定投估值", message)
            else:
                print("今日定投估值", message)

            # 保存投资信息
            self.save_investment_info(ticker, now, current_price, shares_to_buy, investment_amount)

            return message

        except Exception as e:
            error_message = f"估值过程中出现错误: {str(e)}"
            print(f"详细错误信息: {error_message}")
            print(f"错误类型: {type(e)}")
            print(f"错误发生位置: {e.__traceback__.tb_frame.f_code.co_filename}, 行 {e.__traceback__.tb_lineno}")
            return error_message

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
            'price': float(price),  # 确保是 Python float
            'shares': int(shares),  # 确保是 Python int
            'amount': float(amount)  # 确保是 Python float
        }
        history.append(investment_info)

        # 保存更新后的历史
        with open(investment_file, 'w') as f:
            json.dump(history, f, indent=4)

    def show_investment_input_dialog(self):
        # if not self.investment_tracker:
        #     messagebox.showerror("错误", "请先登录PushPlus")
        #     return

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

    def pushplus_login(self, cli_token=None):
        token = cli_token or self.pushplus_token

        # GUI模式下才处理退出登录
        if self.master and self.is_logged_in:
            self.logout()
            return False

        # 未登录状态，处理登录操作
        if not token:
            if self.master:
                token = tk.simpledialog.askstring(
                    "PushPlus Token",
                    "请输入您的PushPlus Token:\n\n"
                    "如果您还没有 Token，请访问 https://www.pushplus.plus/ 获取。\n"
                    "在该网站注册并登录后，您可以在个人中心找到您的 Token。"
                )
            else:
                print("Error: No token provided for CLI mode")
                return False

        if token:
            self.pushplus_sender = PushPlusSender(token)
            self.investment_tracker = InvestmentTracker(token)

            # 获取当前北京时间
            beijing_time = datetime.now(pytz.timezone('Asia/Shanghai'))
            time_str = beijing_time.strftime("%Y-%m-%d %H:%M:%S")

            # 发送包含时间戳的测试消息
            test_result = self.pushplus_sender.send_message(
                "登录测试",
                f"PushPlus登录成功\n\n时间：{time_str} (北京时间)"
            )

            if test_result:
                self.pushplus_token = token
                self.is_logged_in = True
                self.save_token(token)
                if self.master:
                    self.login_button.config(text="退出登录")
                    messagebox.showinfo("登录成功", f"PushPlus登录成功！\n\n测试消息发送时间：{time_str}")
                else:
                    print(f"PushPlus登录成功！\n测试消息发送时间：{time_str}")
                return True
            else:
                self.logout()
                if self.master:
                    messagebox.showerror("登录失败", "PushPlus登录失败，请检查您的Token。")
                else:
                    print("PushPlus登录失败，请检查您的Token。")
                return False
        return False

    def logout(self):
        """退出登录并清理相关状态"""
        # 清理对象状态
        self.pushplus_sender = None
        self.pushplus_token = None
        self.is_logged_in = False
        self.investment_tracker = None

        # 停止提醒（如果正在运行）
        if self.reminder_thread and self.reminder_thread.is_alive():
            self.stop_reminder()

        # 删除token文件
        if os.path.exists(self.token_file):
            try:
                os.remove(self.token_file)
            except Exception as e:
                print(f"删除token文件时出错: {str(e)}")

        # 更新GUI状态
        if self.master:
            self.login_button.config(text="PushPlus登录")
            self.reminder_button.config(text="启动提醒")  # 重置提醒按钮状态
            messagebox.showinfo("退出登录", "已成功退出PushPlus登录")
        else:
            print("已退出PushPlus登录")

    def destroy(self):
        """关闭程序时的清理操作"""
        if self.is_logged_in:
            self.save_token(self.pushplus_token)  # 仅在登录状态下保存token
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
        # if not self.check_login():
        #     return
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

            print("图形已更新")
        except Exception as e:
            messagebox.showerror("错误", f"分析过程中出现错误: {str(e)}")
            print(f"错误详情: {str(e)}")
            import traceback
            traceback.print_exc()

    def toggle_reminder(self):
        if not self.is_logged_in:  # 保留 PushPlus 登录检查
            if self.master:
                messagebox.showerror("错误", "请先登录PushPlus")
            else:
                print("错误: 请先登录PushPlus")
            return

        if self.reminder_thread is None or not self.reminder_thread.is_alive():
            self.start_reminder()
        else:
            self.stop_reminder()

    def start_reminder(self):
        if not self.is_logged_in:
            if self.master:
                messagebox.showerror("错误", "请先登录PushPlus")
            else:
                print("错误: 请先登录PushPlus")
            return False

        self.stop_flag.clear()
        self.reminder_thread = threading.Thread(target=self.run_reminder, daemon=True)
        self.reminder_thread.start()
        if self.master:
            self.reminder_button.config(text="停止提醒")
            messagebox.showinfo("提醒已启动", "定投提醒功能已启动")
        else:
            print("定投提醒功能已启动")
        return True

    def run_reminder(self):
        schedule.clear()  # 清除之前的所有任务
        schedule.every().day.at("08:00").do(self.send_investment_reminder)
        print("Reminder scheduled for 08:00 every day")
        while not self.stop_flag.is_set():
            schedule.run_pending()
            time.sleep(60 * 1000 * 1000)  # 使用 time.sleep()
        print("Reminder thread stopped")

    def stop_reminder(self):
        if self.reminder_thread and self.reminder_thread.is_alive():
            self.stop_flag.set()
            self.reminder_thread.join()
        self.reminder_thread = None
        if self.master:
            self.reminder_button.config(text="启动提醒")
            messagebox.showinfo("提醒已停止", "定投提醒功能已停止")
        else:
            print("定投提醒功能已停止")

    def send_investment_reminder(self):
        if self.pushplus_sender is None:
            print("PushPlus未登录，无法发送提醒")
            return

        beijing_tz = pytz.timezone('Asia/Shanghai')
        now = datetime.now(beijing_tz)

        if self.get_second_wednesday(now.date()) == now.date():
            for ticker in self.config['tickers']:
                try:
                    stock = yf.Ticker(ticker)
                    current_price = stock.info['regularMarketPrice']

                    weight = self.calculate_weight(current_price)
                    investment_amount, shares_to_buy = self.calculate_investment(current_price, weight,
                                                                                 self.config['base_investment'])

                    next_investment_date = self.get_next_investment_date(now)

                    message = (
                        f"定投提醒\n\n"
                        f"日期时间: {now.strftime('%Y-%m-%d %H:%M:%S')} (北京时间)\n"
                        f"股票: {ticker}\n"
                        f"当前价格: ${current_price:.2f}\n"
                        f"建议购买股数: {shares_to_buy}\n"
                        f"本次投资金额: ${investment_amount:.2f}\n"
                        f"下一次预计定投时间: {next_investment_date.strftime('%Y-%m-%d')}"
                    )

                    self.pushplus_sender.send_message(f"{ticker}定投提醒", message)
                    print(f"已发送 {ticker} 的定投提醒")

                    if self.master:
                        messagebox.showinfo(f"{ticker}定投提醒", message)
                except Exception as e:
                    print(f"获取 {ticker} 数据时出错: {str(e)}")
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

    def calculate_weight(self, current_price, sma=None, current_shares=0, equal_shares=0, base_investment=None,
                         historical_data=None, total_investment=0, equal_weight_investment=0, month=1):
        # 使用配置中的值或提供的值
        base_investment = float(base_investment or self.config['base_investment'])

        # 确保最低投资额
        min_weight = 0.8

        # 计算当前持股差异百分比
        current_shares = float(current_shares)
        equal_shares = float(equal_shares)
        shares_difference = (current_shares - equal_shares) / equal_shares if equal_shares > 0 else 0

        # 基础权重
        if shares_difference < -0.1:  # 如果加权持股少于等权持股的90%
            weight = 1.5
        elif shares_difference > 0.1:  # 如果加权持股多于等权持股的110%
            weight = 0.5
        else:
            weight = 1.0

        # 如果没有提供历史数据，我们就不进行市场趋势调整
        if historical_data is not None:
            # 计算市场趋势指标
            sma_50 = historical_data.rolling(window=50).mean().iloc[-1]
            sma_200 = historical_data.rolling(window=200).mean().iloc[-1]
            rsi = self.calculate_rsi(historical_data).iloc[-1]

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
        month = int(month)
        if month % 12 == 0:  # 每年年底
            total_investment = float(total_investment)
            equal_weight_investment = float(equal_weight_investment)
            investment_ratio = total_investment / equal_weight_investment if equal_weight_investment > 0 else 1
            if investment_ratio > 1.1:  # 如果总投资额超过等权投资10%
                weight = max(0.5, weight - 0.3)  # 减少投资但保持最低投资
            elif investment_ratio < 0.9:  # 如果总投资额低于等权投资10%
                weight += 0.3  # 增加投资

        # 考虑兑现部分收益
        if shares_difference > 0.2 and historical_data is not None and self.calculate_rsi(historical_data).iloc[
            -1] > 70:  # 如果持股显著多于等权且RSI高
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
        investment_amount = float(base_investment * weight)
        shares_bought = int(investment_amount / price)  # 向下取整
        actual_investment = float(shares_bought * price)
        return actual_investment, shares_bought

    # 修改 save_to_excel 函数
    def save_to_excel(self, data, equal_investment, weighted_investment, shares_bought, ticker, start_date, end_date):
        investment_dates = equal_investment.index
        excel_data = pd.DataFrame(index=investment_dates)

        excel_data['日期'] = investment_dates
        excel_data['收盘价'] = data.loc[investment_dates, ticker].round(2)

        excel_data['等权买入股数'] = np.round(equal_investment[ticker] / excel_data['收盘价']).astype(int)
        excel_data['加权买入股数'] = np.round(weighted_investment[ticker] / excel_data['收盘价']).astype(int)

        excel_data['等权实际投资金额'] = (excel_data['等权买入股数'] * excel_data['收盘价']).round(2)
        excel_data['加权实际投资金额'] = (excel_data['加权买入股数'] * excel_data['收盘价']).round(2)

        excel_data['等权累计持股数'] = excel_data['等权买入股数'].cumsum()
        excel_data['加权累计持股数'] = excel_data['加权买入股数'].cumsum()
        excel_data['等权累计投资'] = excel_data['等权实际投资金额'].cumsum().round(2)
        excel_data['加权累计投资'] = excel_data['加权实际投资金额'].cumsum().round(2)

        excel_data['等权累计市值'] = (excel_data['等权累计持股数'] * excel_data['收盘价']).round(2)
        excel_data['加权累计市值'] = (excel_data['加权累计持股数'] * excel_data['收盘价']).round(2)

        excel_data['等权平均成本'] = (excel_data['等权累计投资'] / excel_data['等权累计持股数']).round(2)
        excel_data['加权平均成本'] = (excel_data['加权累计投资'] / excel_data['加权累计持股数']).round(2)

        excel_data['等权累计收益'] = (excel_data['等权累计市值'] - excel_data['等权累计投资']).round(2)
        excel_data['加权累计收益'] = (excel_data['加权累计市值'] - excel_data['加权累计投资']).round(2)

        portfolio_returns = None
        if self.portfolio_allocations:
            portfolio_data = self.create_portfolio_data(data, start_date, end_date)
            excel_data['投资组合价值'] = portfolio_data['Portfolio_Value'].round(2)
            excel_data['累计投资成本'] = portfolio_data['Portfolio_Cost'].round(2)
            excel_data['资产组合累计收益'] = portfolio_data['Portfolio_Return'].round(2)
            excel_data['总回报率'] = portfolio_data['Total_Return_Rate'].round(4)
            portfolio_returns = portfolio_data['Portfolio_Return']

            # 添加详细的投资信息
            excel_data['总投资金额'] = np.nan
            excel_data['累计投资成本'] = np.nan

            for date in investment_dates:
                if 'Investment_Details' in portfolio_data.columns and isinstance(
                        portfolio_data.loc[date, 'Investment_Details'], dict):
                    details = portfolio_data.loc[date, 'Investment_Details']
                    excel_data.loc[date, '总投资金额'] = details['总投资金额']
                    excel_data.loc[date, '累计投资成本'] = details['累计投资成本']

                    purchased_tickers = []
                    for ticker in self.portfolio_allocations.keys():
                        if f'{ticker}_购买股数' in details and details[f'{ticker}_购买股数'] > 0:
                            purchased_tickers.append(ticker)
                            for col in ['价格', '分配金额', '购买股数', '实际投资金额']:
                                key = f'{ticker}_{col}'
                                if key not in excel_data.columns:
                                    excel_data[key] = np.nan
                                excel_data.loc[date, key] = details[key]

                    # 创建购买详情列
                    purchase_details = '; '.join([f"{t}: {details[f'{t}_购买股数']:.2f}" for t in purchased_tickers])
                    excel_data.loc[date, '购买详情'] = purchase_details if purchase_details else '无购买'

        # 创建 output 目录（如果不存在）
        output_dir = 'output'
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 修改文件保存路径
        filename = os.path.join(output_dir,
                                f"{ticker}_投资数据_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.xlsx")

        # 创建 ExcelWriter 对象
        with pd.ExcelWriter(filename) as writer:
            excel_data.to_excel(writer, sheet_name='投资详情', index=False)
            if self.portfolio_allocations:
                portfolio_details = pd.DataFrame({
                    '标的名称': self.portfolio_allocations.keys(),
                    '配置比例': self.portfolio_allocations.values(),
                    '最终持股数': [portfolio_data[f'{t}_Shares'].iloc[-1] for t in self.portfolio_allocations.keys()],
                    '累计投资金额': [portfolio_data[f'{t}_Cost'].iloc[-1] for t in self.portfolio_allocations.keys()]
                })
                portfolio_details['实际投资比例'] = portfolio_details['累计投资金额'] / portfolio_details['累计投资金额'].sum()
                portfolio_details.to_excel(writer, sheet_name='资产组合详情', index=False)

        print(f"数据已保存到文件: {filename}")

        # 返回与 create_summary_statistics 方法兼容的数据
        equal_portfolio_values = excel_data['等权累计市值']
        weighted_portfolio_values = excel_data['加权累计市值']
        equal_cumulative_returns = excel_data['等权累计收益']
        weighted_cumulative_returns = excel_data['加权累计收益']

        return (equal_investment, weighted_investment,
                equal_portfolio_values, weighted_portfolio_values,
                equal_cumulative_returns, weighted_cumulative_returns,
                portfolio_returns)

    def setup_logger(self):
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            self.logger.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            ch = logging.StreamHandler()
            ch.setFormatter(formatter)
            self.logger.addHandler(ch)

    def create_portfolio_data(self, data, start_date, end_date):
        if not self.portfolio_allocations:
            return pd.DataFrame()

        self.logger.info(f"开始创建投资组合数据 - 起始日期: {start_date}, 结束日期: {end_date}")
        self.logger.info(f"投资组合配置: {self.portfolio_allocations}")

        portfolio_data = pd.DataFrame(index=data.index)
        portfolio_data['Portfolio_Value'] = 0.0
        portfolio_data['Portfolio_Cost'] = 0.0

        # 新增：创建一个 DataFrame 来存储每个投资日期的详细信息
        investment_details = []

        for ticker in self.portfolio_allocations.keys():
            portfolio_data[f'{ticker}_Shares'] = 0.0
            portfolio_data[f'{ticker}_Cost'] = 0.0

        investment_dates = self.get_investment_dates(start_date, end_date, data.index)
        self.logger.info(f"投资日期: {investment_dates}")

        cumulative_investment = 0.0

        for date in investment_dates:
            self.logger.info(f"\n--- 投资日期: {date} ---")
            total_investment = 0.0
            date_details = {'日期': date, '总投资金额': 0.0, '累计投资成本': 0.0}
            for ticker, weight in self.portfolio_allocations.items():
                if weight == 0:
                    continue
                if ticker not in data.columns:
                    ticker_data = yf.download(ticker, start=start_date, end=end_date)['Adj Close']
                    data[ticker] = ticker_data

                price = data.loc[date, ticker]
                allocation = self.config['base_investment'] * weight
                shares = np.ceil(allocation / price)
                actual_investment = shares * price
                total_investment += actual_investment

                portfolio_data.loc[date:, f'{ticker}_Shares'] += shares
                portfolio_data.loc[date:, f'{ticker}_Cost'] += actual_investment

                self.logger.info(f"标的: {ticker}")
                self.logger.info(f"  价格: ${price:.2f}")
                self.logger.info(f"  分配金额: ${allocation:.2f}")
                self.logger.info(f"  购买股数: {shares}")
                self.logger.info(f"  实际投资金额: ${actual_investment:.2f}")

                date_details[f'{ticker}_价格'] = price
                date_details[f'{ticker}_分配金额'] = allocation
                date_details[f'{ticker}_购买股数'] = shares
                date_details[f'{ticker}_实际投资金额'] = actual_investment

            cumulative_investment += total_investment
            portfolio_data.loc[date:, 'Portfolio_Cost'] = cumulative_investment
            self.logger.info(f"本期总投资金额: ${total_investment:.2f}")
            self.logger.info(f"累计投资成本: ${cumulative_investment:.2f}")

            date_details['总投资金额'] = total_investment
            date_details['累计投资成本'] = cumulative_investment
            investment_details.append(date_details)

        self.logger.info("\n--- 投资组合累计数据 ---")
        for date in data.index:
            portfolio_value = 0.0
            for ticker, weight in self.portfolio_allocations.items():
                if weight == 0:
                    continue
                shares = portfolio_data.loc[date, f'{ticker}_Shares']
                price = data.loc[date, ticker]
                portfolio_value += shares * price
            portfolio_data.loc[date, 'Portfolio_Value'] = portfolio_value

        portfolio_data['Portfolio_Return'] = portfolio_data['Portfolio_Value'] - portfolio_data['Portfolio_Cost']
        portfolio_data['Total_Return_Rate'] = portfolio_data['Portfolio_Return'] / portfolio_data['Portfolio_Cost']

        self.logger.info(f"最终投资组合价值: ${portfolio_data['Portfolio_Value'].iloc[-1]:.2f}")
        self.logger.info(f"累计投资成本: ${portfolio_data['Portfolio_Cost'].iloc[-1]:.2f}")
        self.logger.info(f"资产组合累计收益: ${portfolio_data['Portfolio_Return'].iloc[-1]:.2f}")
        self.logger.info(f"总回报率: {portfolio_data['Total_Return_Rate'].iloc[-1] * 100:.2f}%")

        # 将详细投资信息添加到 portfolio_data
        portfolio_data.loc[investment_dates, 'Investment_Details'] = pd.DataFrame(investment_details).to_dict('records')

        return portfolio_data

    def add_endpoint_annotations(self, ax, equal_returns, weighted_returns, equal_column_name, portfolio_returns=None):
        """
        添加终点注释

        Parameters:
        ax: matplotlib axis对象
        equal_returns: 等权收益DataFrame
        weighted_returns: 加权收益DataFrame
        equal_column_name: 等权收益列名
        portfolio_returns: 可选的组合收益Series
        """
        try:
            # 加权收益终点注释
            if 'weighted_cumulative_return' in weighted_returns.columns:
                weighted_value = weighted_returns['weighted_cumulative_return'].iloc[-1]
                ax.scatter(weighted_returns.index[-1], weighted_value, color='blue')
                ax.annotate(f'{weighted_value:.2f}',
                            (weighted_returns.index[-1], weighted_value),
                            textcoords="offset points", xytext=(0, 10), ha='center')

            # 等权收益终点注释
            if 'equal_cumulative_return' in equal_returns.columns:
                equal_value = equal_returns['equal_cumulative_return'].iloc[-1]
                ax.scatter(equal_returns.index[-1], equal_value, color='orange')
                ax.annotate(f'{equal_value:.2f}',
                            (equal_returns.index[-1], equal_value),
                            textcoords="offset points", xytext=(0, 10), ha='center')

            # 投资组合收益终点注释
            if portfolio_returns is not None and len(portfolio_returns) > 0:
                portfolio_value = portfolio_returns.iloc[-1]
                ax.scatter(portfolio_returns.index[-1], portfolio_value, color='green')
                ax.annotate(f'{portfolio_value:.2f}',
                            (portfolio_returns.index[-1], portfolio_value),
                            textcoords="offset points", xytext=(0, 10), ha='center')

        except Exception as e:
            print(f"添加终点注释时出现错误: {str(e)}")
            # 继续执行而不中断程序
            pass

    def create_summary_statistics(self, ticker, equal_investment, weighted_investment,
                                  equal_portfolio_values, weighted_portfolio_values,
                                  equal_cumulative_returns, weighted_cumulative_returns,
                                  start_date, end_date, portfolio_returns=None):
        """
        创建投资统计摘要

        Parameters:
        ticker: 股票代码
        equal_investment: DataFrame，包含等权投资数据
        weighted_investment: DataFrame，包含加权投资数据
        equal_portfolio_values: DataFrame，包含等权组合价值
        weighted_portfolio_values: DataFrame，包含加权组合价值
        equal_cumulative_returns: DataFrame，包含等权累计收益
        weighted_cumulative_returns: DataFrame，包含加权累计收益
        start_date: 开始日期
        end_date: 结束日期
        portfolio_returns: 可选，Series，包含投资组合收益
        """
        # 计算总投资额
        total_equal_investment = equal_investment['equal_investment'].sum()
        total_weighted_investment = weighted_investment['weighted_investment'].sum()

        equal_final_value = equal_portfolio_values['equal_market_value'].iloc[-1]
        weighted_final_value = weighted_portfolio_values['weighted_market_value'].iloc[-1]

        equal_total_return = (equal_final_value / total_equal_investment - 1) * 100 if total_equal_investment > 0 else 0
        weighted_total_return = (
                                            weighted_final_value / total_weighted_investment - 1) * 100 if total_weighted_investment > 0 else 0

        investment_period_days = (end_date - start_date).days

        equal_annual_return = ((equal_final_value / total_equal_investment) ** (
                365.25 / investment_period_days) - 1) * 100 if total_equal_investment > 0 else 0
        weighted_annual_return = ((weighted_final_value / total_weighted_investment) ** (
                365.25 / investment_period_days) - 1) * 100 if total_weighted_investment > 0 else 0

        # 创建摘要文本
        summary = f"\n{ticker} 的摘要统计：\n"
        summary += f"等额定投:\n"
        summary += f"  总投资: ${total_equal_investment:.2f}\n"
        summary += f"  最终价值: ${equal_final_value:.2f}\n"
        summary += f"  累计收益: ${equal_cumulative_returns['equal_cumulative_return'].iloc[-1]:.2f}\n"
        summary += f"  总回报率: {equal_total_return:.2f}%\n"
        summary += f"  年化回报率: {equal_annual_return:.2f}%\n"
        summary += f"加权定投:\n"
        summary += f"  总投资: ${total_weighted_investment:.2f}\n"
        summary += f"  最终价值: ${weighted_final_value:.2f}\n"
        summary += f"  累计收益: ${weighted_cumulative_returns['weighted_cumulative_return'].iloc[-1]:.2f}\n"
        summary += f"  总回报率: {weighted_total_return:.2f}%\n"
        summary += f"  年化回报率: {weighted_annual_return:.2f}%\n"

        # 如果有投资组合数据，添加投资组合统计
        if portfolio_returns is not None:
            # 使用附加到 portfolio_returns 的 portfolio_data
            total_actual_investment = portfolio_returns.portfolio_data['Portfolio_Cost'].iloc[-1]
            portfolio_final_value = portfolio_returns.portfolio_data['Portfolio_Value'].iloc[-1]
            portfolio_cumulative_return = portfolio_returns.iloc[-1]

            # 计算收益率
            portfolio_total_return = ((portfolio_final_value / total_actual_investment) - 1) * 100
            years = (end_date - start_date).days / 365.25
            portfolio_annual_return = ((portfolio_final_value / total_actual_investment) ** (1 / years) - 1) * 100

            # 生成摘要
            summary += f"资产组合:\n"
            # 添加投资标的和占比
            allocations = [f"{asset}({weight * 100:.0f}%)" for asset, weight in self.portfolio_allocations.items() if
                           weight > 0]
            summary += f"  投资标的: {', '.join(allocations)}\n"
            # 继续添加其他统计信息
            summary += f"  实际总投资额: ${total_actual_investment:.2f}\n"
            summary += f"  最终价值: ${portfolio_final_value:.2f}\n"
            summary += f"  累计收益: ${portfolio_cumulative_return:.2f}\n"
            summary += f"  总回报率: {portfolio_total_return:.2f}%\n"
            summary += f"  年化回报率: {portfolio_annual_return:.2f}%\n"

        return summary
    def check_internet_connection(self):
        try:
            # 尝试连接到 Yahoo Finance 的网站
            response = requests.get("https://finance.yahoo.com", timeout=5)
            return response.status_code == 200
        except requests.ConnectionError:
            return False

    def analyze_and_plot(self, ticker, start_date, end_date):
        # if not self.check_login():
        #     return None

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

        # 初始化每日数据DataFrame
        base_investment = self.config['base_investment']
        daily_data = pd.DataFrame(index=data.index)
        daily_data['price'] = data[ticker]

        # 初始化持仓和投资数据
        daily_data['equal_shares'] = 0.0
        daily_data['weighted_shares'] = 0.0
        daily_data['equal_investment'] = 0.0
        daily_data['weighted_investment'] = 0.0
        daily_data['equal_cumulative_shares'] = 0.0
        daily_data['weighted_cumulative_shares'] = 0.0
        daily_data['equal_cumulative_investment'] = 0.0
        daily_data['weighted_cumulative_investment'] = 0.0

        # 计算每个投资日的投资情况
        for d in investment_dates:
            price = data.loc[d, ticker]

            # 等额定投策略
            equal_invest_amount = base_investment
            equal_shares = equal_invest_amount / price

            # 加权定投策略
            weight = self.calculate_weight(price,
                                           data[ticker].rolling(window=self.config['sma_window']).mean().loc[d],
                                           data[ticker].rolling(window=self.config['std_window']).std().loc[d],
                                           data[ticker].rolling(
                                               window=self.config['std_window']).std().expanding().mean().loc[d])
            weighted_invest_amount = base_investment * weight
            weighted_shares = weighted_invest_amount / price

            # 记录投资日的数据
            daily_data.loc[d, 'equal_shares'] = equal_shares
            daily_data.loc[d, 'weighted_shares'] = weighted_shares
            daily_data.loc[d, 'equal_investment'] = equal_invest_amount
            daily_data.loc[d, 'weighted_investment'] = weighted_invest_amount

        # 计算累计持股数
        daily_data['equal_cumulative_shares'] = daily_data['equal_shares'].cumsum()
        daily_data['weighted_cumulative_shares'] = daily_data['weighted_shares'].cumsum()

        # 计算累计投资额
        daily_data['equal_cumulative_investment'] = daily_data['equal_investment'].cumsum()
        daily_data['weighted_cumulative_investment'] = daily_data['weighted_investment'].cumsum()

        # 计算每日市值
        daily_data['equal_market_value'] = daily_data['equal_cumulative_shares'] * daily_data['price']
        daily_data['weighted_market_value'] = daily_data['weighted_cumulative_shares'] * daily_data['price']

        # 计算每日累计收益
        daily_data['equal_cumulative_return'] = daily_data['equal_market_value'] - daily_data[
            'equal_cumulative_investment']
        daily_data['weighted_cumulative_return'] = daily_data['weighted_market_value'] - daily_data[
            'weighted_cumulative_investment']

        # 绘图
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True, gridspec_kw={'height_ratios': [2, 1]})
        fig.subplots_adjust(hspace=0.1)

        # 绘制每日累计收益
        ax1.plot(daily_data.index, daily_data['equal_cumulative_return'],
                 label=f'{ticker} 等权累计收益', color='orange')
        ax1.plot(daily_data.index, daily_data['weighted_cumulative_return'],
                 label=f'{ticker} 加权累计收益', color='blue')

        portfolio_returns = None
        if self.portfolio_allocations:
            portfolio_data = self.create_portfolio_data(data, start_date, end_date)
            portfolio_returns = portfolio_data['Portfolio_Return']
            # 将整个 portfolio_data 附加到 portfolio_returns
            portfolio_returns.portfolio_data = portfolio_data
            ax1.plot(portfolio_data.index, portfolio_returns, label='资产组合累计收益', color='green')

        # 设置图表属性
        ax1.set_title(f'{ticker}: 累计收益比较 ({start_date.year}-{end_date.year})')
        ax1.set_ylabel('累计收益 ($)')
        ax1.legend()
        ax1.grid(True)

        # 添加零线
        ax1.axhline(y=0, color='red', linestyle=':', linewidth=1)

        # 确保y轴范围包含所有数据点
        y_values = [daily_data['equal_cumulative_return'], daily_data['weighted_cumulative_return']]
        if portfolio_returns is not None:
            y_values.append(portfolio_returns)
        y_min = min(min(y) for y in y_values)
        y_max = max(max(y) for y in y_values)
        y_range = y_max - y_min
        ax1.set_ylim(y_min - 0.1 * y_range, y_max + 0.1 * y_range)

        # 添加终点注释部分的更新
        self.add_endpoint_annotations(
            ax1,
            daily_data[['equal_cumulative_return']],
            daily_data[['weighted_cumulative_return']],
            'equal_cumulative_return',
            portfolio_returns
        )

        # 绘制MACD（其余部分保持不变）
        ax2.plot(data.index, data[f'{ticker}_MACD'], label='MACD', color='blue')
        ax2.plot(data.index, data[f'{ticker}_MACD_SIGNAL'], label='Signal Line', color='red')
        ax2.bar(data.index, data[f'{ticker}_MACD'] - data[f'{ticker}_MACD_SIGNAL'],
                label='Histogram', color='gray', alpha=0.5)
        ax2.axhline(y=0, color='black', linestyle='--', linewidth=0.5)
        ax2.set_ylabel('MACD')
        ax2.legend(loc='upper left')
        ax2.grid(True)

        # 设置x轴属性
        ax2.set_xlabel('日期')
        years = mdates.YearLocator(2)
        months = mdates.MonthLocator()
        years_fmt = mdates.DateFormatter('%Y')
        ax2.xaxis.set_major_locator(years)
        ax2.xaxis.set_major_formatter(years_fmt)
        ax2.xaxis.set_minor_locator(months)
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
        ax2.set_xlim(data.index[0], data.index[-1])

        # 更新统计信息
        summary = self.create_summary_statistics(
            ticker,
            daily_data[['equal_investment']],
            daily_data[['weighted_investment']],
            daily_data[['equal_market_value']],
            daily_data[['weighted_market_value']],
            daily_data[['equal_cumulative_return']],
            daily_data[['weighted_cumulative_return']],
            start_date,
            end_date,
            portfolio_returns
        )

        ax1.text(0.05, 0.05, summary, transform=ax1.transAxes, verticalalignment='bottom',
                 bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        plt.tight_layout()
        return fig

    
    def setup_chinese_font(self):
        """
            根据操作系统设置合适的中文字体
        """
        import platform
        system = platform.system()

        # 根据操作系统选择字体
        if system == 'Windows':
            font = 'Microsoft YaHei'
            fonts = [font]
        elif system == 'Darwin':  # MacOS

            
            # 取消这段注释，可以打印出系统字体名称列表
            #debug_to_display_system_fonts = """
            print(f"---- 系统字体列表: ----- ")
            for font_path in font_manager.findSystemFonts(fontpaths=None, fontext='ttf'):
                try:
                    font_prop = font_manager.FontProperties(fname=font_path)
                    font_name = font_prop.get_name()
                    print(f"font_path: {font_path}, font_name: {font_name}")
                except RuntimeError:
                    print(f"无法加载字体: {font_path}")
                    #"""
                
            # Mac系统字体优先级
            fonts = [
                'PingFang HK',
                'PingFang SC',
                'Hiragino Sans GB',
                'STHeiti',
                'Heiti SC',
                'STSong',
                'Songti SC'
            ]
            # 选择第一个可用的字体
            #font = next((f for f in mac_fonts), 'Arial Unicode MS')
        elif system == 'Linux':
            font = 'WenQuanYi Micro Hei'
            fonts = [font]
        else:
            font = 'Arial Unicode MS'
            fonts = [font]

        # 设置matplotlib字体
        plt.rcParams['font.sans-serif'] = fonts
        plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

        print(f"当前操作系统: {system}")
        #print(f"使用字体: {font}")


def parse_arguments():
    parser = argparse.ArgumentParser(description="Investment App")
    parser.add_argument("--cli", action="store_true", help="Run in CLI mode")
    parser.add_argument("--login", help="Login to PushPlus with token", metavar="TOKEN")
    parser.add_argument("--estimate", action="store_true", help="Estimate today's investment")
    parser.add_argument("--start-reminder", action="store_true", help="Start investment reminder")
    return parser.parse_args()


def run_cli(app, args):
    if args.login:
        if app.pushplus_login(args.login):
            print("PushPlus登录成功")
        else:
            print("PushPlus登录失败")

    # 如果没有显式登录，尝试使用保存的 token 自动登录
    if not app.is_logged_in:
        app.auto_login()

    if args.estimate:
        if app.is_logged_in:
            result = app.estimate_today_investment()
            print(result)
        else:
            print("错误: 请先登录PushPlus")

    if args.start_reminder:
        if app.is_logged_in:
            result = app.start_reminder()
            if result:
                print("定投提醒功能已启动")
                # Keep the script running
                while True:
                    time.sleep(60)  # 使用 time.sleep()，每分钟检查一次
            else:
                print("定投提醒功能启动失败或已在运行中")
        else:
            print("错误: 请先登录PushPlus")


if __name__ == "__main__":
    print("Testing schedule functionality...")
    for _ in range(3):  # Run for 3 iterations to test schedule
        schedule.run_pending()
        time.sleep(1)
    print("Schedule test completed")

    # 清除测试用的任务
    schedule.clear()

    # 继续正常的应用程序初始化
    args = parse_arguments()

    if args.cli:
        app = InvestmentApp(None)  # 初始化无 GUI 的 InvestmentApp
        run_cli(app, args)
    else:
        root = tk.Tk()
        app = InvestmentApp(root)
        root.protocol("WM_DELETE_WINDOW", app.destroy)
        root.mainloop()
