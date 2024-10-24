import json
import os
import tkinter as tk
from datetime import datetime, timedelta
from tkinter import ttk, messagebox

import pandas as pd
import yfinance as yf


class InvestmentTracker:
    def __init__(self, pushplus_token):
        self.pushplus_token = pushplus_token
        self.investment_file = f'investment_history_{self.pushplus_token}.json'

    def save_investment_info(self, ticker, date, price, shares, amount):
        history = self.load_investment_info()
        investment_info = {
            'date': date.strftime('%Y-%m-%d %H:%M:%S'),
            'ticker': ticker,
            'price': price,
            'shares': shares,
            'amount': amount
        }
        history.append(investment_info)
        with open(self.investment_file, 'w') as f:
            json.dump(history, f, indent=4)

    def load_investment_info(self):
        if os.path.exists(self.investment_file):
            with open(self.investment_file, 'r') as f:
                return json.load(f)
        return []

    def find_closest_date(self, ticker, price):
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)  # 获取最近30天的数据
        data = yf.download(ticker, start=start_date, end=end_date)['Adj Close']
        closest_date = min(data.index, key=lambda x: abs(data[x] - price))
        return closest_date.to_pydatetime()

    def calculate_actual_returns(self, ticker):
        history = self.load_investment_info()
        ticker_history = [record for record in history if record['ticker'] == ticker]

        if not ticker_history:
            return None

        total_investment = sum(record['amount'] for record in ticker_history)
        total_shares = sum(record['shares'] for record in ticker_history)

        # 获取最新价格
        latest_data = yf.download(ticker, start=datetime.now() - timedelta(days=5), end=datetime.now())
        if latest_data.empty:
            return None
        current_price = latest_data['Adj Close'].iloc[-1]

        current_value = total_shares * current_price
        actual_return = current_value - total_investment

        return actual_return

    def get_actual_returns_series(self, ticker, start_date, end_date):
        history = self.load_investment_info()
        ticker_history = [record for record in history if record['ticker'] == ticker]

        if not ticker_history:
            return pd.Series(), 0, 0

        data = yf.download(ticker, start=start_date, end=end_date)['Adj Close']
        returns_series = pd.Series(index=data.index, dtype=float)

        cumulative_shares = 0
        cumulative_investment = 0

        for record in ticker_history:
            date = datetime.strptime(record['date'], '%Y-%m-%d %H:%M:%S').date()
            if date < start_date:
                cumulative_shares += record['shares']
                cumulative_investment += record['amount']
            elif start_date <= date <= end_date:
                cumulative_shares += record['shares']
                cumulative_investment += record['amount']
                returns_series[date:] = (data[date:] * cumulative_shares - cumulative_investment)

        final_value = data.iloc[-1] * cumulative_shares if not data.empty else 0

        return returns_series, cumulative_investment, final_value

    def calculate_investment_metrics(self, ticker, start_date, end_date):
        returns_series, cumulative_investment, final_value = self.get_actual_returns_series(ticker, start_date,
                                                                                            end_date)

        if returns_series.empty:
            return None

        investment_period_days = (end_date - start_date).days

        actual_return = final_value - cumulative_investment
        total_return = (final_value / cumulative_investment - 1) * 100 if cumulative_investment > 0 else 0
        annual_return = ((final_value / cumulative_investment) ** (
                365.25 / investment_period_days) - 1) * 100 if cumulative_investment > 0 and investment_period_days > 0 else 0

        return {
            'cumulative_investment': cumulative_investment,
            'final_value': final_value,
            'actual_return': actual_return,
            'total_return': total_return,
            'annual_return': annual_return
        }


class AssetAllocationDialog:
    def __init__(self, parent, tickers):
        self.parent = parent
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("资产配置")
        self.tickers = tickers
        self.allocations = {}
        self.result = None
        self.create_widgets()

    def create_widgets(self):
        for i, ticker in enumerate(self.tickers):
            ttk.Label(self.dialog, text=f"{ticker}:").grid(row=i, column=0, padx=5, pady=5)
            entry = ttk.Entry(self.dialog, width=10)
            entry.grid(row=i, column=1, padx=5, pady=5)
            entry.insert(0, "0")
            self.allocations[ticker] = entry

        ttk.Button(self.dialog, text="确认", command=self.validate_and_close).grid(row=len(self.tickers), column=0,
                                                                                 columnspan=2, pady=10)

    def validate_and_close(self):
        try:
            total = sum(float(entry.get()) for entry in self.allocations.values())
            if abs(total - 100) > 0.01:  # Allow for small floating point errors
                messagebox.showerror("错误", "所有占比之和必须为100%")
                return
            self.result = {ticker: float(entry.get()) / 100 for ticker, entry in self.allocations.items()}
            self.dialog.destroy()
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")

    def show(self):
        self.dialog.grab_set()  # 模态对话框
        self.parent.wait_window(self.dialog)
        return self.result
