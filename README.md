# 投资策略分析工具
## 项目概述

这是一个用Python开发的投资策略分析工具，旨在帮助投资者比较不同的定投策略效果。该工具支持分析美国市场的多种ETF和指数，提供图形化界面，便于用户交互和结果可视化。

![SPY累计收益](example1.png)

## 主要功能

- 支持多种ETF和指数的分析，包括SPY, QQQ, XLG, IWM, DIA, VTI等，可自定义配置
- 比较等额定投和加权定投策略
- 可视化累计收益和MACD指标
- 支持自定义初始持仓和成本
- 生成详细的Excel报告
- 灵活的日期范围选择

## 安装说明

1. 确保您的系统已安装Python 3.7+
2. 克隆此仓库到本地：
   ```
   git clone https://github.com/yourusername/InvestmentTools.git
   ```
3. 进入项目目录：
   ```
   cd InvestmentTools
   ```
4. 安装所需依赖：
   ```
   pip install -r requirements.txt
   ```

## 使用方法

1. 运行主程序：
   ```
   python main.py
   ```
2. 在图形界面中：
   - 选择要分析的股票/ETF
   - 设置起始和结束日期
   - 输入初始持仓（如果有）
   - 点击"更新图表"按钮生成分析结果

## 依赖项

- yfinance
- pandas
- numpy
- matplotlib
- tkinter

详细的依赖列表请参见 `requirements.txt` 文件。

## MileStones

以下是我们计划在未来版本中实现的功能和改进：

### 短期目标

- [ ] 优化数据加载速度，提高大量历史数据的处理效率
- [ ] 增加更多技术指标选项，如RSI、布林带等
- [ ] 实现自动保存和加载用户偏好设置
- [ ] 添加批量分析功能，允许同时对多个股票或者指数进行分析
- [ ] 改进图表交互性，支持缩放和数据点悬停显示详情
- [ ] 允许用户进行初始资金定义，以便满足精确的收益计算
- [ ] 支持周/月/季度定投模式，并支持比较相关收益数据
- [ ] 结合汇率影响定投数据

### 中期目标

- [ ] 集成机器学习模型，提供基于历史数据的简单预测
- [ ] 添加投资组合分析功能，支持多股票组合的收益率计算
- [ ] 实现自定义投资策略的导入和使用
- [ ] 增加对股息再投资的模拟
- [ ] 开发网页版应用，提供在线使用功能
- [ ] 支持当天盘中的自定义数据的输入
- [ ] 支持服务器后台运行，在指定定投日期进行微信或邮件推送能力

### 长期目标

- [ ] 集成实时数据流，支持近实时的市场数据分析
- [ ] 开发移动应用版本，提供随时随地的分析能力
- [ ] 实现与主流券商API的集成，支持实盘交易数据导入
- [ ] 添加社区功能，允许用户分享和讨论投资策略
- [ ] 开发高级回测系统，支持更复杂的交易策略和市场情景模拟

### 持续改进

- [ ] 定期更新数据源和API，确保数据的准确性和可靠性
- [ ] 优化用户界面，提高用户体验
- [ ] 扩展对更多国际市场和金融产品的支持
- [ ] 加强代码测试覆盖率，提高软件稳定性
- [ ] 编写详细的用户手册和开发文档

我们欢迎社区成员参与到这些目标的实现中来。如果您对某个特定的功能特别感兴趣或有好的建议，请在Issues中提出或直接贡献代码。

## 注意事项

- 本工具使用yfinance获取历史数据，请确保您有稳定的网络连接。
- 对于中国市场的数据，可能会受到市场和数据源的限制，accuracy可能有所不同。
- 本工具仅供教育和研究目的使用，不构成投资建议。

## 贡献

欢迎提交问题报告和功能建议。如果您想为项目做出贡献，请遵循以下步骤：

1. Fork 本仓库
2. 创建您的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交您的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启一个 Pull Request

## 许可证

本项目采用 MIT 许可证 - 详情请见 [LICENSE](LICENSE) 文件。
 
