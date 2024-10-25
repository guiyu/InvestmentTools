# 投资策略分析系统技术文档

## 系统架构

### 核心组件
1. InvestmentApp 类
   - GUI/CLI双模式支持
   - PushPlus消息推送集成
   - 自动化定投提醒
   - 投资策略分析与可视化

2. 数据管理模块
   - yfinance数据获取接口
   - 本地数据缓存
   - JSON格式配置存储
   - Excel导出功能

3. 分析引擎
   - 技术指标计算（MACD、RSI、SMA）
   - 投资权重动态调整
   - 投资组合管理
   - 收益率分析

### 数据流
```
市场数据(yfinance) -> 数据处理(pandas) -> 策略分析 -> 可视化展示(matplotlib)
    ↑                    ↓                   ↓            ↓
    └──← 本地缓存 ←── JSON配置 ←── 用户交互(tkinter) ←── 消息推送(PushPlus)
```

## 核心功能实现

### 1. 初始化与配置
```python
def __init__(self, master=None):
    self.config = {
        'tickers': ['VOO', 'QQQ', 'SPLG', 'RSP', 'VTI', ...],
        'base_investment': 4000,
        'sma_window': 200,
        'std_window': 30,
        'min_weight': 0.5,
        'max_weight': 2,
        'macd_short_window': 12,
        'macd_long_window': 26,
        'macd_signal_window': 9,
    }
```

### 2. 投资策略实现
```python
def calculate_weight(self, price, sma, std, avg_std):
    n = 1 + (std / avg_std)
    weight = (sma / price) ** n
    return max(min(weight, config['max_weight']), config['min_weight'])
```

### 3. 自动化定投提醒
```python
def send_investment_reminder(self):
    # 定投日判断
    if self.get_second_wednesday(now.date()) == now.date():
        for ticker in self.config['tickers']:
            # 获取市场数据
            # 计算投资建议
            # 发送推送消息
```

## 用户界面

### GUI模式
1. 主窗口布局
   - 左侧控制面板
   - 右侧图表显示
   - 参数配置区域

2. 交互功能
   - 股票选择下拉框
   - 日期范围选择
   - 投资金额设置
   - 更新图表按钮

### CLI模式
```python
def run_cli(app, args):
    if args.login:
        app.pushplus_login(args.login)
    if args.estimate:
        app.estimate_today_investment()
    if args.start_reminder:
        app.start_reminder()
```

## 数据分析与可视化

### 技术指标计算
1. MACD指标
```python
def calculate_macd(self, data, short_window=12, long_window=26, signal_window=9):
    short_ema = data.ewm(span=short_window, adjust=False).mean()
    long_ema = data.ewm(span=long_window, adjust=False).mean()
    macd = short_ema - long_ema
    signal = macd.ewm(span=signal_window, adjust=False).mean()
    return macd, signal, macd - signal
```

2. RSI指标
```python
def calculate_rsi(self, prices, period=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))
```

### 可视化展示
1. 图表布局
   - 上方面板：收益曲线
   - 下方面板：MACD指标
   - 动态注释和统计信息

2. 数据导出
   - Excel格式导出
   - 投资明细记录
   - 收益率统计

## 集成功能

### PushPlus消息推送
```python
def pushplus_login(self, cli_token=None):
    # Token验证
    # 测试消息发送
    # 保存配置
```

### 自动化任务
```python
def run_reminder(self):
    schedule.every().day.at("08:00").do(self.send_investment_reminder)
    while not self.stop_flag.is_set():
        schedule.run_pending()
        time.sleep(60)
```

## 部署要求

### 环境依赖
- Python 3.7+
- 主要依赖包：
  - yfinance
  - pandas
  - numpy
  - matplotlib
  - tkinter
  - schedule
  - requests

### 安装步骤
1. 环境准备
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

2. 依赖安装
```bash
pip install -r requirements.txt
```

## 使用说明

### GUI模式启动
```bash
python investment_app.py
```

### CLI模式使用
```bash
python investment_app.py --cli --login YOUR_PUSHPLUS_TOKEN
python investment_app.py --cli --estimate
python investment_app.py --cli --start-reminder
```

## 注意事项

1. 数据安全
   - Token信息本地加密存储
   - 投资记录定期备份
   - 异常监控和日志记录

2. 性能优化
   - 数据缓存机制
   - 异步任务处理
   - 资源释放管理

3. 错误处理
   - 网络连接异常
   - 数据获取失败
   - 推送服务异常

## 维护指南

### 日常维护
1. 日志检查
2. 数据备份
3. 配置更新

### 问题排查
1. 网络连接检查
2. 数据一致性验证
3. 服务状态监控