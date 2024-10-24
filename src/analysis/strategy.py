import json
import os

from src.data.processor import calculate_rsi


def calculate_weight(config, current_price, sma=None, current_shares=0, equal_shares=0, base_investment=None,
                     historical_data=None, total_investment=0, equal_weight_investment=0, month=1):
    # 使用配置中的值或提供的值
    base_investment = float(base_investment or config['base_investment'])

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
        rsi = calculate_rsi(historical_data).iloc[-1]

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
    if shares_difference > 0.2 and historical_data is not None and calculate_rsi(historical_data).iloc[
        -1] > 70:  # 如果持股显著多于等权且RSI高
        sell_proportion = min(shares_difference - 0.1, 0.1)  # 最多卖出到比等权多10%
        return -sell_proportion  # 返回负值表示卖出

    # 确保权重在合理范围内
    return max(min(weight, 2), min_weight)


def calculate_investment(price, weight, base_investment):
    investment_amount = float(base_investment * weight)
    shares_bought = int(investment_amount / price)  # 向下取整
    actual_investment = float(shares_bought * price)
    return actual_investment, shares_bought


def save_investment_info(ticker, date, price, shares, amount):
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