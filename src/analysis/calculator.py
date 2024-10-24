

def create_summary_statistics(portfolio_allocations, ticker, equal_investment, weighted_investment,
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
        allocations = [f"{asset}({weight * 100:.0f}%)" for asset, weight in portfolio_allocations.items() if
                       weight > 0]
        summary += f"  投资标的: {', '.join(allocations)}\n"
        # 继续添加其他统计信息
        summary += f"  实际总投资额: ${total_actual_investment:.2f}\n"
        summary += f"  最终价值: ${portfolio_final_value:.2f}\n"
        summary += f"  累计收益: ${portfolio_cumulative_return:.2f}\n"
        summary += f"  总回报率: {portfolio_total_return:.2f}%\n"
        summary += f"  年化回报率: {portfolio_annual_return:.2f}%\n"

    return summary


def add_endpoint_annotations(ax, equal_returns, weighted_returns, equal_column_name, portfolio_returns=None):
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