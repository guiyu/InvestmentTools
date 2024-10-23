# 使用说明

## 启动程序

### GUI模式

1. 运行主程序：
   ```bash
   python main.py
   ```

2. 在图形界面中：
   - 选择要分析的股票/ETF
   - 设置起始和结束日期
   - 输入基础投资金额
   - 点击"更新图表"按钮生成分析结果

### CLI模式

1. 使用命令行参数运行：
   ```bash
   python main.py --cli [options]
   ```

   可用选项：
   - `--login TOKEN`: 使用PushPlus token登录
   - `--estimate`: 估算今日投资
   - `--start-reminder`: 启动投资提醒

   示例：
   ```bash
   python main.py --cli --login your_pushplus_token --estimate
   ```

## 基本功能

### 数据查看
- 在主界面上方选择股票代码
- 设置时间范围
- 选择要显示的指标
- 使用图表工具栏进行缩放和平移

### 投资分析
- 查看历史投资表现
- 比较不同策略的效果
- 导出分析报告
- 查看详细统计数据

### 定投提醒
1. 登录PushPlus：
   - 点击"PushPlus登录"按钮
   - 输入您的token
   
2. 设置提醒：
   - 点击"启动提醒"按钮
   - 选择提醒频率
   - 设置提醒时间

## 高级功能

### 自定义分析
- 创建自定义指标
- 设置个性化参数
- 保存和加载分析模板

### 数据导出
- 选择导出格式（Excel/CSV）
- 自定义导出字段
- 设置导出周期

### 投资组合管理
- 创建多个投资组合
- 设置资产配置比例
- 跟踪组合表现

## 快捷键

- `Ctrl+R`: 刷新数据
- `Ctrl+E`: 导出数据
- `Ctrl+S`: 保存设置
- `Ctrl+Q`: 退出程序

## 最佳实践

1. 数据管理
   - 定期备份配置
   - 及时更新数据
   - 定期清理缓存

2. 策略使用
   - 从小规模开始测试
   - 保持策略稳定性
   - 定期评估效果

3. 系统维护
   - 保持软件更新
   - 监控系统资源
   - 定期检查日志

## 常见问题解答

1. **数据不显示**
   - 检查网络连接
   - 验证股票代码
   - 确认时间范围有效

2. **分析结果异常**
   - 检查参数设置
   - 验证数据完整性
   - 确认计算方法

3. **提醒功能失效**
   - 检查token有效性
   - 确认网络连接
   - 验证时间设置