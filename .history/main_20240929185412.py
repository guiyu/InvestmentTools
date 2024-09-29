import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# Set the start and end dates for our backtest
start_date = datetime.now() - timedelta(days=365*20)
end_date = datetime.now()

# Define the tickers we want to backtest
tickers = ['QQQ', 'SPY', 'XLG']

# Function to get the third Friday of each month
def get_third_friday(date):
    # Find the first day of the month
    first = date.replace(day=1)
    # Find the first Friday
    first_friday = first + timedelta(days=(4 - first.weekday() + 7) % 7)
    # Find the third Friday
    third_friday = first_friday + timedelta(days=14)
    return third_friday

# Download the data
data = yf.download(tickers, start=start_date, end=end_date)['Adj Close']

# Create a list of investment dates (third Fridays)
investment_dates = []
current_date = start_date
while current_date <= end_date:
    third_friday = get_third_friday(current_date)
    if third_friday <= end_date:
        investment_dates.append(third_friday)
    current_date = current_date.replace(day=1) + timedelta(days=32)
    current_date = current_date.replace(day=1)

# Filter the data to only include investment dates
investment_data = data.loc[investment_dates]

# Calculate returns
returns = investment_data.pct_change()

# Calculate cumulative returns
cumulative_returns = (1 + returns).cumprod()

# Plot the results
plt.figure(figsize=(12, 6))
for ticker in tickers:
    plt.plot(cumulative_returns.index, cumulative_returns[ticker], label=ticker)

plt.title('Cumulative Returns of QQQ, SPY, and XLG (2003-2023)')
plt.xlabel('Date')
plt.ylabel('Cumulative Return')
plt.legend()
plt.grid(True)
plt.show()

# Calculate and print summary statistics
for ticker in tickers:
    print(f"\nSummary Statistics for {ticker}:")
    print(f"Total Return: {cumulative_returns[ticker].iloc[-1]:.2f}")
    print(f"Annualized Return: {(cumulative_returns[ticker].iloc[-1]**(1/20) - 1):.4f}")
    print(f"Sharpe Ratio: {returns[ticker].mean() / returns[ticker].std():.4f}")