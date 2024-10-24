import logging
import threading
import time
import tkinter as tk
from datetime import datetime, time as datetime_time, timedelta, date
from tkinter import ttk, messagebox

import pandas as pd
import pytz
import schedule
import yfinance as yf
from matplotlib import pyplot as plt, dates as mdates
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from src.analysis.strategy import calculate_weight, calculate_investment, save_investment_info
from src.core.app import save_token, load_token
from src.core.investment import InvestmentTracker, AssetAllocationDialog
from src.utils.pushplus_sender import PushPlusSender
from src.analysis.calculator import add_endpoint_annotations, create_summary_statistics
from src.data.fetcher import get_next_investment_date, get_second_wednesday, check_internet_connection, \
    get_investment_dates
from src.data.processor import calculate_rsi, calculate_macd, create_portfolio_data


# 在文件顶部添加这个打印语句，以确认导入成功
from src.ui.cli import parse_arguments, run_cli
from src.utils.notifications import run_reminder

print("All modules imported successfully, including time module")


def test_schedule():
    print("Schedule test function executed at", datetime.now())


# 测试 schedule 的基本功能
schedule.every(5).seconds.do(test_schedule)

class InvestmentApp:
    def __init__(self, master=None):
        self.master = master
        self.token_file = '../pushplus_token.json'
        self.pushplus_token = load_token(self.token_file)
        self.pushplus_sender = None
        self.investment_tracker = None
        self.is_logged_in = False
        self.setup_logger()
        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']
        plt.rcParams['axes.unicode_minus'] = False

        # 配置
        self.config = {
            'tickers': ['VOO', 'QQQ', 'SPLG', 'RSP', 'VTI', 'VTV', 'SCHD', 'VGT', 'TLT', 'IEI','BND','DBC','GLD'],
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
        if self.pushplus_login(self.pushplus_token):
            print("已使用保存的 token 自动登录")
        else:
            print("自动登录失败，请手动登录")

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

        # 创建更新按钮
        self.update_button = ttk.Button(self.left_frame, text="更新图表", command=self.update_plot)
        self.update_button.pack(pady=10)

        # 添加"当天定投估值"按钮
        self.estimate_button = ttk.Button(self.left_frame, text="当天定投估值", command=self.estimate_today_investment)
        self.estimate_button.pack(pady=10)

        # 创建登录按钮
        self.login_button = ttk.Button(self.left_frame, text="PushPlus登录", command=self.pushplus_login)
        self.login_button.pack(pady=10)

        # 添加"输入投资信息"按钮
        self.input_investment_button = ttk.Button(self.left_frame, text="输入投资信息",
                                                  command=self.show_investment_input_dialog)
        self.input_investment_button.pack(pady=10)

        # 添加资产配置按钮
        self.portfolio_button = ttk.Button(self.left_frame, text="设置资产组合", command=self.open_asset_allocation_dialog)
        self.portfolio_button.pack(pady=10)

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
        if not self.is_logged_in:
            return "请先登录PushPlus"

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
            weight = calculate_weight(self.config, current_price)
            investment_amount, shares_to_buy = calculate_investment(current_price, weight,
                                                                    self.config['base_investment'])

            # 确保计算结果是正确的类型
            if not isinstance(investment_amount, (int, float)):
                raise TypeError(f"投资金额必须是数字，而不是 {type(investment_amount)}")
            if not isinstance(shares_to_buy, int):
                raise TypeError(f"购买股数必须是整数，而不是 {type(shares_to_buy)}")

            investment_amount = float(investment_amount)
            shares_to_buy = int(shares_to_buy)

            # 计算下一次定投时间
            next_investment_date = get_next_investment_date(now)

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
            save_investment_info(ticker, now, current_price, shares_to_buy, investment_amount)

            return message

        except Exception as e:
            error_message = f"估值过程中出现错误: {str(e)}"
            print(f"详细错误信息: {error_message}")
            print(f"错误类型: {type(e)}")
            print(f"错误发生位置: {e.__traceback__.tb_frame.f_code.co_filename}, 行 {e.__traceback__.tb_lineno}")
            return error_message

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
            save_investment_info(ticker, date, price, shares, amount)
            dialog.destroy()
            messagebox.showinfo("成功", "投资信息已保存")

        ttk.Button(dialog, text="保存", command=save_investment).grid(row=3, column=0, columnspan=2, pady=10)

    def pushplus_login(self, cli_token=None):
        token = cli_token or self.pushplus_token
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
                self.is_logged_in = True  # 确保设置登录状态
                save_token(self.token_file, token)
                if self.master:
                    self.login_button.config(text="退出登录")
                    messagebox.showinfo("登录成功", f"PushPlus登录成功！\n\n测试消息发送时间：{time_str}")
                else:
                    print(f"PushPlus登录成功！\n测试消息发送时间：{time_str}")
                return True
            else:
                self.pushplus_sender = None
                self.pushplus_token = None
                self.is_logged_in = False
                self.investment_tracker = None
                if self.master:
                    self.login_button.config(text="PushPlus登录")
                    messagebox.showerror("登录失败", "PushPlus登录失败，请检查您的Token。")
                else:
                    print("PushPlus登录失败，请检查您的Token。")
                return False
        return False

    def destroy(self):
        if self.pushplus_token:
            save_token(self.token_file, self.pushplus_token)
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

            print("图形已更新")
        except Exception as e:
            messagebox.showerror("错误", f"分析过程中出现错误: {str(e)}")
            print(f"错误详情: {str(e)}")
            import traceback
            traceback.print_exc()

    def toggle_reminder(self):
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
        self.reminder_thread = threading.Thread(target=run_reminder, daemon=True)
        self.reminder_thread.start()
        if self.master:
            self.reminder_button.config(text="停止提醒")
            messagebox.showinfo("提醒已启动", "定投提醒功能已启动")
        else:
            print("定投提醒功能已启动")
        return True

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

        if get_second_wednesday(now.date()) == now.date():
            for ticker in self.config['tickers']:
                try:
                    stock = yf.Ticker(ticker)
                    current_price = stock.info['regularMarketPrice']

                    weight = calculate_weight(self.config, current_price)
                    investment_amount, shares_to_buy = calculate_investment(current_price, weight,
                                                                            self.config['base_investment'])

                    next_investment_date = get_next_investment_date(now)

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

    # 修改投资计算函数

    # 修改 save_to_excel 函数

    def setup_logger(self):
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            self.logger.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            ch = logging.StreamHandler()
            ch.setFormatter(formatter)
            self.logger.addHandler(ch)

    def analyze_and_plot(self, ticker, start_date, end_date):
        if not self.check_login():
            return None

        # 检查网络连接
        if not check_internet_connection():
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
        data['RSI'] = calculate_rsi(data[ticker])

        # 计算MACD
        data[f'{ticker}_MACD'], data[f'{ticker}_MACD_SIGNAL'], _ = calculate_macd(
            data[ticker],
            short_window=self.config['macd_short_window'],
            long_window=self.config['macd_long_window'],
            signal_window=self.config['macd_signal_window']
        )

        # 将索引转换为日期类型
        data.index = pd.to_datetime(data.index).date

        # 创建投资日期列表
        investment_dates = get_investment_dates(start_date, end_date, data.index)

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
            weight = calculate_weight(self.config, price,
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

        # 在 analyze_and_plot 方法中，修改这部分代码
        portfolio_returns = None
        if self.portfolio_allocations:
            portfolio_data = create_portfolio_data(self.portfolio_allocations, self.logger, self.config, data,
                                                   start_date, end_date)
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
        add_endpoint_annotations(
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
        summary = create_summary_statistics(self.portfolio_allocations,
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