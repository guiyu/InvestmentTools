import os
from datetime import datetime, timedelta, date
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# 设置中文字体，这里使用微软雅黑作为例子
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

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

# 修改配置
config = {
    'ticker': 'SPY',
    'vix_ticker': '^VIX',
    'start_date': '2000-01-01',
    'end_date': datetime.now().strftime('%Y-%m-%d'),
    'base_investment': 2000,
    'grid_levels': 10,
    'grid_range': 0.2,  # 20% range for grid
    'rsi_window': 14,
    'rsi_overbought': 70,
    'rsi_oversold': 30,
    'macd_fast': 12,
    'macd_slow': 26,
    'macd_signal': 9,
    'vix_threshold': 30,
    'max_drawdown_threshold': 0.05,  # 5% maximum drawdown
}


def download_data(ticker, start_date, end_date):
    data = yf.download(ticker, start=start_date, end=end_date)
    return data['Adj Close']


def calculate_indicators(data):
    # Calculate RSI
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=config['rsi_window']).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=config['rsi_window']).mean()
    rs = gain / loss
    data['RSI'] = 100 - (100 / (1 + rs))

    # Calculate MACD
    exp1 = data.ewm(span=config['macd_fast'], adjust=False).mean()
    exp2 = data.ewm(span=config['macd_slow'], adjust=False).mean()
    data['MACD'] = exp1 - exp2
    data['Signal_Line'] = data['MACD'].ewm(span=config['macd_signal'], adjust=False).mean()

    return data


def calculate_grid_levels(current_price):
    grid_step = (config['grid_range'] * current_price) / config['grid_levels']
    return [current_price * (1 - config['grid_range'] / 2 + i * grid_step / current_price) for i in
            range(config['grid_levels'])]


def execute_trade(price, cash, shares, grid_levels):
    for i, level in enumerate(grid_levels):
        if price <= level:
            buy_amount = config['base_investment'] * (i + 1) / config['grid_levels']
            if cash >= buy_amount:
                shares_to_buy = buy_amount / price
                cash -= buy_amount
                shares += shares_to_buy
            break
        elif price > level and i == len(grid_levels) - 1:
            if shares > 0:
                sell_amount = config['base_investment'] / config['grid_levels']
                shares_to_sell = min(sell_amount / price, shares)
                cash += shares_to_sell * price
                shares -= shares_to_sell
    return cash, shares


def calculate_drawdown(equity_curve):
    rolling_max = equity_curve.cummax()
    drawdown = (equity_curve - rolling_max) / rolling_max
    return drawdown


def run_strategy():
    # Download data
    spy_data = download_data(config['ticker'], config['start_date'], config['end_date'])
    vix_data = download_data(config['vix_ticker'], config['start_date'], config['end_date'])

    # Combine data and calculate indicators
    data = pd.DataFrame({'SPY': spy_data, 'VIX': vix_data})
    data = data.dropna()
    data = calculate_indicators(data['SPY'])
    data['VIX'] = vix_data

    # Initialize variables
    cash = config['base_investment']
    shares = 0
    equity = []
    grid_levels = calculate_grid_levels(data['SPY'].iloc[0])

    # Run strategy
    for date, row in data.iterrows():
        price = row['SPY']

        # Check for bear market conditions
        if row['VIX'] > config['vix_threshold'] or row['RSI'] < config['rsi_oversold']:
            # In potential bear market, reduce position
            if shares > 0:
                cash += shares * price * 0.5
                shares *= 0.5
        elif row['RSI'] > config['rsi_overbought'] and row['MACD'] < row['Signal_Line']:
            # Overbought condition, sell some shares
            if shares > 0:
                cash += shares * price * 0.2
                shares *= 0.8
        else:
            # Normal market conditions, execute grid strategy
            cash, shares = execute_trade(price, cash, shares, grid_levels)

        # Recalculate grid levels monthly
        if date.month != data.index[data.index.get_loc(date) - 1].month:
            grid_levels = calculate_grid_levels(price)

        equity.append(cash + shares * price)

    equity_curve = pd.Series(equity, index=data.index)
    drawdown = calculate_drawdown(equity_curve)

    # Calculate performance metrics
    total_return = (equity[-1] - config['base_investment']) / config['base_investment']
    annual_return = (1 + total_return) ** (365.25 / (data.index[-1] - data.index[0]).days) - 1
    max_drawdown = drawdown.min()

    print(f"Total Return: {total_return:.2%}")
    print(f"Annual Return: {annual_return:.2%}")
    print(f"Max Drawdown: {max_drawdown:.2%}")

    # Plot results
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)
    ax1.plot(data.index, data['SPY'], label='SPY Price')
    ax1.plot(equity_curve.index, equity_curve, label='Portfolio Value')
    ax1.set_title('SPY Price and Portfolio Value')
    ax1.legend()

    ax2.plot(drawdown.index, drawdown, label='Drawdown')
    ax2.axhline(y=-config['max_drawdown_threshold'], color='r', linestyle='--', label='Max Drawdown Threshold')
    ax2.set_title('Portfolio Drawdown')
    ax2.legend()

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    run_strategy()