# 安装指南

## 系统要求

- Python 3.7+
- 稳定的网络连接（用于数据获取）
- 足够的磁盘空间用于数据存储

## 安装步骤

1. 克隆仓库到本地：
   ```bash
   git clone https://github.com/yourusername/InvestmentTools.git
   ```

2. 进入项目目录：
   ```bash
   cd InvestmentTools
   ```

3. 安装所需依赖：
   ```bash
   pip install -r requirements.txt
   ```

## 依赖项

主要依赖项包括：

- yfinance：用于获取市场数据
- pandas：数据处理和分析
- numpy：数值计算
- matplotlib：数据可视化
- tkinter：图形界面
- pytz：时区处理
- requests：网络请求
- schedule：定时任务

完整的依赖列表请参见 `requirements.txt` 文件。

## 常见问题

1. **依赖安装失败**
   - 检查Python版本是否符合要求
   - 确保pip已更新到最新版本
   - 尝试使用虚拟环境安装

2. **数据获取问题**
   - 检查网络连接
   - 确认API密钥配置正确
   - 验证代理设置（如适用）

## 故障排除

如果遇到安装问题，请尝试以下步骤：

1. 清理Python缓存：
   ```bash
   python -m pip cache purge
   ```

2. 更新pip和setuptools：
   ```bash
   python -m pip install --upgrade pip setuptools
   ```

3. 在虚拟环境中安装：
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   pip install -r requirements.txt
   ```

如果问题仍然存在，请查看项目Issues页面或提交新的Issue。
