import os

import numpy as np
import pandas as pd
import yfinance as yf

from src.data.fetcher import get_investment_dates


def calculate_macd(data, short_window=12, long_window=26, signal_window=9):
    short_ema = data.ewm(span=short_window, adjust=False).mean()
    long_ema = data.ewm(span=long_window, adjust=False).mean()
    macd = short_ema - long_ema
    signal = macd.ewm(span=signal_window, adjust=False).mean()
    histogram = macd - signal
    return macd, signal, histogram


def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def calculate_target_value(initial_investment, months, annual_rate=0.12):
    monthly_rate = (1 + annual_rate) ** (1 / 12) - 1
    return initial_investment * (1 + monthly_rate) ** months


def create_portfolio_data(portfolio_allocations, logger, config, data, start_date, end_date):
    if not portfolio_allocations:
        return pd.DataFrame()

    logger.info(f"开始创建投资组合数据 - 起始日期: {start_date}, 结束日期: {end_date}")
    logger.info(f"投资组合配置: {portfolio_allocations}")

    portfolio_data = pd.DataFrame(index=data.index)
    portfolio_data['Portfolio_Value'] = 0.0
    portfolio_data['Portfolio_Cost'] = 0.0

    # 新增：创建一个 DataFrame 来存储每个投资日期的详细信息
    investment_details = []

    for ticker in portfolio_allocations.keys():
        portfolio_data[f'{ticker}_Shares'] = 0.0
        portfolio_data[f'{ticker}_Cost'] = 0.0

    investment_dates = get_investment_dates(start_date, end_date, data.index)
    logger.info(f"投资日期: {investment_dates}")

    cumulative_investment = 0.0

    for date in investment_dates:
        logger.info(f"\n--- 投资日期: {date} ---")
        total_investment = 0.0
        date_details = {'日期': date, '总投资金额': 0.0, '累计投资成本': 0.0}
        for ticker, weight in portfolio_allocations.items():
            if weight == 0:
                continue
            if ticker not in data.columns:
                ticker_data = yf.download(ticker, start=start_date, end=end_date)['Adj Close']
                data[ticker] = ticker_data

            price = data.loc[date, ticker]
            allocation = config['base_investment'] * weight
            shares = np.ceil(allocation / price)
            actual_investment = shares * price
            total_investment += actual_investment

            portfolio_data.loc[date:, f'{ticker}_Shares'] += shares
            portfolio_data.loc[date:, f'{ticker}_Cost'] += actual_investment

            logger.info(f"标的: {ticker}")
            logger.info(f"  价格: ${price:.2f}")
            logger.info(f"  分配金额: ${allocation:.2f}")
            logger.info(f"  购买股数: {shares}")
            logger.info(f"  实际投资金额: ${actual_investment:.2f}")

            date_details[f'{ticker}_价格'] = price
            date_details[f'{ticker}_分配金额'] = allocation
            date_details[f'{ticker}_购买股数'] = shares
            date_details[f'{ticker}_实际投资金额'] = actual_investment

        cumulative_investment += total_investment
        portfolio_data.loc[date:, 'Portfolio_Cost'] = cumulative_investment
        logger.info(f"本期总投资金额: ${total_investment:.2f}")
        logger.info(f"累计投资成本: ${cumulative_investment:.2f}")

        date_details['总投资金额'] = total_investment
        date_details['累计投资成本'] = cumulative_investment
        investment_details.append(date_details)

    logger.info("\n--- 投资组合累计数据 ---")
    for date in data.index:
        portfolio_value = 0.0
        for ticker, weight in portfolio_allocations.items():
            if weight == 0:
                continue
            shares = portfolio_data.loc[date, f'{ticker}_Shares']
            price = data.loc[date, ticker]
            portfolio_value += shares * price
        portfolio_data.loc[date, 'Portfolio_Value'] = portfolio_value

    portfolio_data['Portfolio_Return'] = portfolio_data['Portfolio_Value'] - portfolio_data['Portfolio_Cost']
    portfolio_data['Total_Return_Rate'] = portfolio_data['Portfolio_Return'] / portfolio_data['Portfolio_Cost']

    logger.info(f"最终投资组合价值: ${portfolio_data['Portfolio_Value'].iloc[-1]:.2f}")
    logger.info(f"累计投资成本: ${portfolio_data['Portfolio_Cost'].iloc[-1]:.2f}")
    logger.info(f"资产组合累计收益: ${portfolio_data['Portfolio_Return'].iloc[-1]:.2f}")
    logger.info(f"总回报率: {portfolio_data['Total_Return_Rate'].iloc[-1] * 100:.2f}%")

    # 将详细投资信息添加到 portfolio_data
    portfolio_data.loc[investment_dates, 'Investment_Details'] = pd.DataFrame(investment_details).to_dict('records')

    return portfolio_data


def save_to_excel(portfolio_allocations, logger, config, data, equal_investment, weighted_investment, shares_bought,
                  ticker, start_date, end_date):
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
    if portfolio_allocations:
        portfolio_data = create_portfolio_data(portfolio_allocations, logger, config, data,
                                               start_date, end_date)
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
                for ticker in portfolio_allocations.keys():
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
        if portfolio_allocations:
            portfolio_details = pd.DataFrame({
                '标的名称': portfolio_allocations.keys(),
                '配置比例': portfolio_allocations.values(),
                '最终持股数': [portfolio_data[f'{t}_Shares'].iloc[-1] for t in portfolio_allocations.keys()],
                '累计投资金额': [portfolio_data[f'{t}_Cost'].iloc[-1] for t in portfolio_allocations.keys()]
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