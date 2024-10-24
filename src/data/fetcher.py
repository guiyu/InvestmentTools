from datetime import timedelta

import requests


def check_internet_connection():
    try:
        # 尝试连接到 Yahoo Finance 的网站
        response = requests.get("https://finance.yahoo.com", timeout=5)
        return response.status_code == 200
    except requests.ConnectionError:
        return False


def get_nearest_business_day(date, data_index):
    while date not in data_index:
        date += timedelta(days=1)
        if date > data_index[-1]:
            return data_index[-1]  # 如果超出数据范围，返回最后一个可用日期
    return date


def get_second_wednesday(date):
    # 获取给定月份的第一天
    first_day = date.replace(day=1)
    # 找到第一个周三
    first_wednesday = first_day + timedelta(days=(2 - first_day.weekday() + 7) % 7)
    # 第二个周三
    second_wednesday = first_wednesday + timedelta(days=7)
    return second_wednesday


def get_next_investment_date(current_date):
    next_date = current_date.replace(day=1) + timedelta(days=32)
    next_date = next_date.replace(day=1)  # 下个月的第一天
    while next_date.weekday() != 2:  # 2 表示周三
        next_date += timedelta(days=1)
    return next_date + timedelta(days=7)  # 第二个周三


def get_investment_dates(start_date, end_date, data_index):
    investment_dates = []
    current_date = start_date.replace(day=1)  # 从起始日期的当月开始

    while current_date <= end_date:
        # 获取当月第二周的周三
        investment_date = get_second_wednesday(current_date)

        # 如果投资日期在数据范围内，则添加到列表
        if start_date <= investment_date <= end_date:
            # 获取最近的交易日（如果当天不是交易日，则向后顺延）
            actual_investment_date = get_nearest_business_day(investment_date, data_index)
            investment_dates.append(actual_investment_date)

        # 移动到下一个月
        current_date = (current_date.replace(day=1) + timedelta(days=32)).replace(day=1)

    return investment_dates