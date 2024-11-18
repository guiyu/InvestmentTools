"""
portfolio_rebalance_manager.py
投资组合再平衡管理器
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
from enum import Enum
import logging
from typing import Dict, Tuple, List, Optional, Any
import json


class RebalancePeriod(Enum):
    """再平衡周期枚举类"""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMIANNUAL = "semiannual"
    ANNUAL = "annual"

    @classmethod
    def get_days(cls, period: 'RebalancePeriod') -> int:
        """获取周期对应的大约天数"""
        days_mapping = {
            cls.MONTHLY: 30,
            cls.QUARTERLY: 90,
            cls.SEMIANNUAL: 180,
            cls.ANNUAL: 360
        }
        return days_mapping[period]


class RebalanceManager:
    """投资组合再平衡管理器"""

    def __init__(self, threshold: float = 0.05, min_trade_amount: float = 100):
        """
        初始化再平衡管理器

        Args:
            threshold (float): 再平衡触发阈值（默认5%）
            min_trade_amount (float): 最小交易金额（默认100美元）
        """
        # 设置日志
        self.logger = logging.getLogger(__name__)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

        # 基本配置
        self.threshold = threshold
        self.min_trade_amount = min_trade_amount
        self.rebalance_period = None
        self.last_rebalance_date = None

        # 投资组合配置
        self.target_allocations: Dict[str, float] = {}
        self.current_holdings: Dict[str, float] = {}

        # 历史记录
        self.rebalance_history: List[Dict[str, Any]] = []
        self.trades_history: List[Dict[str, Any]] = []

        # 性能指标
        self.performance_metrics = {
            'rebalance_count': 0,
            'total_trades': 0,
            'trading_costs': 0.0,
            'tracking_error': []
        }

    def initialize(self, initial_holdings: Dict[str, float],
                   initial_prices: Dict[str, float],
                   start_date: datetime) -> None:
        """
        初始化投资组合状态

        Args:
            initial_holdings: 初始持仓数量
            initial_prices: 初始价格
            start_date: 开始日期
        """
        self.current_holdings = initial_holdings.copy()
        self.last_rebalance_date = start_date
        self.validate_portfolio(initial_prices)
        self.logger.info("Portfolio initialized successfully")

    def validate_portfolio(self, prices: Dict[str, float]) -> None:
        """
        验证投资组合配置的有效性

        Args:
            prices: 当前市场价格

        Raises:
            ValueError: 如果配置无效
        """
        if not self.target_allocations:
            raise ValueError("Target allocations not set")

        if not set(self.target_allocations.keys()) <= set(prices.keys()):
            missing = set(self.target_allocations.keys()) - set(prices.keys())
            raise ValueError(f"Missing price data for: {missing}")

        if not np.isclose(sum(self.target_allocations.values()), 1.0, rtol=1e-5):
            raise ValueError("Target allocations must sum to 1.0")

        self.logger.debug("Portfolio validation passed")

    def set_rebalance_period(self, period: RebalancePeriod) -> None:
        """
        设置再平衡周期

        Args:
            period: 再平衡周期枚举值
        """
        if not isinstance(period, RebalancePeriod):
            raise ValueError(f"Invalid rebalance period: {period}")

        self.rebalance_period = period
        self.logger.info(f"Rebalance period set to {period.value}")

    def set_target_allocations(self, allocations: Dict[str, float]) -> None:
        """
        设置目标资产配置比例

        Args:
            allocations: 资产配置比例字典 {ticker: weight}
        """
        if not isinstance(allocations, dict):
            raise ValueError("Allocations must be a dictionary")

        if not np.isclose(sum(allocations.values()), 1.0, rtol=1e-5):
            raise ValueError("Allocation weights must sum to 1.0")

        self.target_allocations = allocations.copy()
        self.logger.info(f"Target allocations updated: {allocations}")

    def update_current_holdings(self, holdings: Dict[str, float]) -> None:
        """
        更新当前持仓信息

        Args:
            holdings: 当前持仓数量字典 {ticker: shares}
        """
        self.current_holdings = holdings.copy()
        self.logger.debug(f"Current holdings updated: {holdings}")

    def calculate_current_allocations(self, prices: Dict[str, float]) -> Dict[str, float]:
        """
        计算当前资产配置比例

        Args:
            prices: 当前价格信息 {ticker: price}

        Returns:
            当前资产配置比例 {ticker: weight}
        """
        # 计算总市值
        total_value = sum(self.current_holdings.get(ticker, 0) * prices[ticker]
                          for ticker in self.target_allocations.keys())

        if total_value == 0:
            return {ticker: 0.0 for ticker in self.target_allocations.keys()}

        # 计算每个资产的权重
        current_allocations = {
            ticker: (self.current_holdings.get(ticker, 0) * prices[ticker]) / total_value
            for ticker in self.target_allocations.keys()
        }

        return current_allocations

    def get_next_rebalance_date(self, current_date: datetime) -> Optional[datetime]:
        """
        获取下一个再平衡日期

        Args:
            current_date: 当前日期

        Returns:
            下一个再平衡日期，如果未设置再平衡周期则返回None
        """
        if not self.rebalance_period or not self.last_rebalance_date:
            return None

        days = RebalancePeriod.get_days(self.rebalance_period)
        next_date = self.last_rebalance_date + timedelta(days=days)

        # 确保下一个再平衡日期是交易日
        while self.is_trading_day(next_date) is False:
            next_date += timedelta(days=1)

        return next_date

    def is_trading_day(self, date: datetime) -> bool:
        """
        检查是否为交易日

        Args:
            date: 待检查日期

        Returns:
            是否为交易日
        """
        # 周末不是交易日
        if date.weekday() >= 5:
            return False

        # TODO: 可以添加节假日检查
        return True

    def check_rebalance_needed(self, current_date: datetime,
                               prices: Dict[str, float]) -> Tuple[bool, str]:
        """
        检查是否需要进行再平衡

        Args:
            current_date: 当前日期
            prices: 当前价格信息 {ticker: price}

        Returns:
            (需要再平衡, 原因说明)
        """
        # 检查是否到达再平衡时间
        next_rebalance_date = self.get_next_rebalance_date(current_date)
        if not next_rebalance_date or current_date < next_rebalance_date:
            return False, "未到再平衡时间"

        # 计算当前配置
        current_allocations = self.calculate_current_allocations(prices)

        # 检查是否有显著偏离
        max_deviation = 0.0
        deviated_asset = None

        for ticker in self.target_allocations:
            target = self.target_allocations[ticker]
            current = current_allocations.get(ticker, 0)
            deviation = abs(target - current)

            if deviation > max_deviation:
                max_deviation = deviation
                deviated_asset = ticker

        if max_deviation > self.threshold:
            return True, f"{deviated_asset} 偏离目标配置 {max_deviation:.2%}"

        return False, "资产配置在目标范围内"

    def calculate_rebalance_trades(self, prices: Dict[str, float]) -> Tuple[Dict[str, int], Dict[str, float]]:
        """
        计算再平衡所需的交易

        Args:
            prices: 当前价格信息 {ticker: price}

        Returns:
            (交易份额, 交易金额)
        """
        # 计算当前总市值
        current_value = sum(self.current_holdings.get(ticker, 0) * prices[ticker]
                            for ticker in self.target_allocations.keys())

        # 计算目标市值
        target_values = {ticker: current_value * weight
                         for ticker, weight in self.target_allocations.items()}

        # 计算当前市值
        current_values = {ticker: self.current_holdings.get(ticker, 0) * prices[ticker]
                          for ticker in self.target_allocations.keys()}

        # 计算需要调整的金额
        trades_amounts = {}
        trades_shares = {}

        for ticker in self.target_allocations:
            diff = target_values[ticker] - current_values[ticker]

            # 如果调整金额小于最小交易金额，跳过
            if abs(diff) < self.min_trade_amount:
                continue

            trades_amounts[ticker] = diff
            # 计算交易份额，买入向下取整，卖出向上取整
            if diff > 0:  # 买入
                shares = int(diff / prices[ticker])
            else:  # 卖出
                shares = -int(-diff / prices[ticker])

            if shares != 0:  # 只记录非零交易
                trades_shares[ticker] = shares

        return trades_shares, trades_amounts

    def execute_rebalance(self, current_date: datetime,
                          prices: Dict[str, float]) -> Dict[str, Any]:
        """
        执行再平衡操作

        Args:
            current_date: 当前日期
            prices: 当前价格信息 {ticker: price}

        Returns:
            再平衡执行结果
        """
        try:
            # 检查是否需要再平衡
            needed, reason = self.check_rebalance_needed(current_date, prices)
            if not needed:
                return {
                    "status": "not_needed",
                    "message": reason,
                    "date": current_date
                }

            # 记录再平衡前的状态
            pre_rebalance = self.calculate_current_allocations(prices)

            # 计算交易清单
            trades_shares, trades_amounts = self.calculate_rebalance_trades(prices)

            # 执行交易
            for ticker, shares in trades_shares.items():
                self.current_holdings[ticker] = self.current_holdings.get(ticker, 0) + shares

            # 记录再平衡后的状态
            post_rebalance = self.calculate_current_allocations(prices)

            # 更新最后再平衡日期
            self.last_rebalance_date = current_date

            # 记录交易历史
            trade_record = {
                "date": current_date,
                "trades_shares": trades_shares,
                "trades_amounts": trades_amounts,
                "prices": prices,
                "pre_allocations": pre_rebalance,
                "post_allocations": post_rebalance
            }
            self.trades_history.append(trade_record)

            # 更新性能指标
            self.performance_metrics['rebalance_count'] += 1
            self.performance_metrics['total_trades'] += len(trades_shares)

            # 生成结果报告
            result = {
                "status": "success",
                "date": current_date,
                "trades": {
                    "shares": trades_shares,
                    "amounts": trades_amounts
                },
                "allocations": {
                    "before": pre_rebalance,
                    "after": post_rebalance,
                    "target": self.target_allocations
                },
                "holdings": self.current_holdings.copy()
            }

            self.rebalance_history.append(result)
            self.logger.info(f"Rebalance executed successfully on {current_date}")

            return result

        except Exception as e:
            error_msg = f"Error during rebalance: {str(e)}"
            self.logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg,
                "date": current_date
            }

    def get_rebalance_history(self) -> List[Dict[str, Any]]:
        """获取再平衡历史记录"""
        return self.rebalance_history

    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        return self.performance_metrics

    def generate_rebalance_report(self, result: Dict[str, Any]) -> str:
        """
        生成再平衡报告

        Args:
            result: 再平衡执行结果

        Returns:
            格式化的报告文本
        """
        if result["status"] != "success":
            return f"再平衡未执行: {result.get('message', '未知原因')}"

        report_lines = []

        # 基本信息
        report_lines.extend([
            "再平衡执行报告",
            "=" * 30,
            f"\n执行日期: {result['date'].strftime('%Y-%m-%d %H:%M:%S')}",
            "-" * 30
        ])

        # 交易详情
        trades = result["trades"]["shares"]
        if trades:
            report_lines.append("\n交易详情:")
            buys = {t: s for t, s in trades.items() if s > 0}
            sells = {t: -s for t, s in trades.items() if s < 0}

            if buys:
                report_lines.append("\n买入:")
                for ticker, shares in buys.items():
                    amount = result["trades"]["amounts"][ticker]
                    report_lines.append(f"  {ticker}: {shares}股 (${amount:.2f})")

            if sells:
                report_lines.append("\n卖出:")
                for ticker, shares in sells.items():
                    amount = -result["trades"]["amounts"][ticker]
                    report_lines.append(f"  {ticker}: {shares}股 (${amount:.2f})")

        # 配置变化
        report_lines.extend([
            "\n配置变化:",
            "-" * 30
        ])

        for ticker in self.target_allocations:
            before = result["allocations"]["before"][ticker]
            after = result["allocations"]["after"][ticker]
            target = result["allocations"]["target"][ticker]

            report_lines.extend([
                f"\n{ticker}:",
                f"  目标配置: {target:.2%}",
                f"  调整前: {before:.2%}",
                f"  调整后: {after:.2%}",
                f"  偏差: {(after - target):.2%}"
            ])

        # 添加性能指标
        report_lines.extend([
            "\n性能指标:",
            "-" * 30,
            f"累计再平衡次数: {self.performance_metrics['rebalance_count']}",
            f"累计交易次数: {self.performance_metrics['total_trades']}"
        ])

        return "\n".join(report_lines)

    def save_state(self, filepath: str) -> None:
        """
        保存再平衡管理器状态

        Args:
            filepath: 保存文件路径
        """
        state = {
            "threshold": self.threshold,
            "min_trade_amount": self.min_trade_amount,
            "rebalance_period": self.rebalance_period.value if self.rebalance_period else None,
            "last_rebalance_date": self.last_rebalance_date.isoformat() if self.last_rebalance_date else None,
            "target_allocations": self.target_allocations,
            "current_holdings": self.current_holdings,
            "performance_metrics": self.performance_metrics
        }

        with open(filepath, 'w') as f:
            json.dump(state, f, indent=4)

        self.logger.info(f"State saved to {filepath}")

    def load_state(self, filepath: str) -> None:
        """
        加载再平衡管理器状态

        Args:
            filepath: 状态文件路径
        """
        with open(filepath, 'r') as f:
            state = json.load(f)

        self.threshold = state["threshold"]
        self.min_trade_amount = state["min_trade_amount"]
        self.rebalance_period = RebalancePeriod(state["rebalance_period"]) if state["rebalance_period"] else None
        self.last_rebalance_date = datetime.fromisoformat(state["last_rebalance_date"]) if state[
            "last_rebalance_date"] else None
        self.target_allocations = state["target_allocations"]
        self.current_holdings = state["current_holdings"]
        self.performance_metrics = state["performance_metrics"]

        self.logger.info(f"State loaded from {filepath}")