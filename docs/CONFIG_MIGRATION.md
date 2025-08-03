# 📄 配置文件迁移指南

从老版本Python配置迁移到新的YAML配置格式。

## 🔄 配置对比

### 老版本 → 新版本映射

| 老配置项 | 新配置位置 | 说明 |
|---------|------------|------|
| `gmail_password` | `system_config.yaml` → `smtp.sender_password` | SMTP密码 |
| `gmail_address` | `system_config.yaml` → `smtp.sender_email` | 发送邮箱 |
| `recipients` | `users_config.yaml` → `users` | 每个用户一个配置段 |
| `CHINA_TECH` | `system_config.yaml` → `stock_pools.china_tech` | 中概股股票池 |
| `NASDAQ_SYMBOLS` | `system_config.yaml` → `stock_pools.nasdaq_core/nasdaq_extended` | 拆分为核心和扩展 |
| `FLUCTUATION_THRESHOLD_PERCENT` | `users_config.yaml` → `users.*.fluctuation.threshold_percent` | 每用户独立设置 |
| `FLUCTUATION_MONITOR_SYMBOLS` | `system_config.yaml` → `stock_pools.fluctuation_focus` | 专门的波动监控池 |
| `UP_TREND_THRESHOLD` | `system_config.yaml` → `trend_analysis.up_trend_threshold` | 全局默认值 |
| `DOWN_TREND_THRESHOLD` | `system_config.yaml` → `trend_analysis.down_trend_threshold` | 全局默认值 |
| `SIGNAL_WEIGHTS` | `system_config.yaml` → `trend_analysis.signal_weights` | 信号权重配置 |
| `BUY_SIGNAL_THRESHOLD` | `system_config.yaml` → `trend_analysis.buy_signal_threshold` | 买入信号阈值 |
| `SELL_SIGNAL_THRESHOLD` | `system_config.yaml` → `trend_analysis.sell_signal_threshold` | 卖出信号阈值 |

## 📋 配置示例

### 系统配置 (`system_config.yaml`)
```yaml
# SMTP邮件配置
smtp:
  server: "smtp.gmail.com"
  port: 587
  sender_email: "your-email@gmail.com"
  sender_password: "your-app-password"

# Web服务配置
web:
  host: "0.0.0.0"
  port: 8080

# 股票池定义（重新组织你的原股票列表）
stock_pools:
  china_tech:
    - "BIDU"
    - "BABA"
    - "JD"
    - "PDD"
    # ... 其他中概股
  
  nasdaq_core:
    - "AAPL"
    - "MSFT"
    - "GOOGL"
    - "NVDA"
    # ... 其他核心股票
  
  fluctuation_focus:
    - "AAPL"
    - "MSFT"
    - "TSLA"
    # ... 重点监控的股票

# 趋势分析配置（你的原参数）
trend_analysis:
  up_trend_threshold: 3      # 原 UP_TREND_THRESHOLD
  down_trend_threshold: 3    # 原 DOWN_TREND_THRESHOLD
  signal_weights:            # 原 SIGNAL_WEIGHTS
    ema_cross: 0.3
    macd_cross: 0.2
    adx_strength: 0.2
    bb_position: 0.15
    rsi_level: 0.15
  buy_signal_threshold: 0.8  # 原 BUY_SIGNAL_THRESHOLD
  sell_signal_threshold: 0.8 # 原 SELL_SIGNAL_THRESHOLD
```

### 用户配置 (`users_config.yaml`)
```yaml
users:
  # 第一个接收者（你的主邮箱）
  caoruixu15@gmail.com:
    name: "主用户"
    fluctuation:
      enabled: true
      threshold_percent: 1.0    # 原 FLUCTUATION_THRESHOLD_PERCENT
      symbols: "@fluctuation_focus"  # 引用股票池
      notification_interval_minutes: 30
    trend:
      enabled: true
      symbols: "@nasdaq_core"
      notification_interval_minutes: 60
    notifications:
      email_enabled: true
  
  # 第二个接收者
  smilence7@outlook.com:
    name: "备用用户"
    fluctuation:
      enabled: true
      threshold_percent: 1.0
      symbols:  # 直接列表
        - "AAPL"
        - "MSFT"
        - "GOOGL"
        - "NVDA"
        - "TSLA"
      notification_interval_minutes: 30
    trend:
      enabled: true
      symbols:
        - "AAPL"
        - "TSLA"
        - "NVDA"
      notification_interval_minutes: 60
    notifications:
      email_enabled: true
```

## 🎯 核心改进

### 1. **多用户支持**
- 老版本：单一 `recipients` 列表
- 新版本：每个用户独立配置，支持不同监控需求

### 2. **股票池引用**
- 老版本：硬编码股票列表
- 新版本：可重用的股票池，用 `@pool_name` 引用

### 3. **配置层级**
- 老版本：全局配置
- 新版本：系统默认 + 用户覆盖

### 4. **灵活监控**
- 老版本：所有用户相同监控
- 新版本：每用户独立监控频率、股票列表、阈值

## 🚀 迁移步骤

### 1. 创建配置文件
```bash
# 基于模板创建配置文件
sudo cp config/config_template.yaml /etc/ragoalert/system_config.yaml
sudo cp config/config_template.yaml /etc/ragoalert/users_config.yaml
```

### 2. 根据老配置调整新配置
```bash
# 编辑系统配置（SMTP、股票池等）
sudo vim /etc/ragoalert/system_config.yaml

# 编辑用户配置（监控设置）
sudo vim /etc/ragoalert/users_config.yaml
```

根据本文档的配置对比表，将你的老配置项逐一迁移到新的YAML格式。

### 3. 验证配置
```bash
# 部署并验证
sudo ./scripts/deploy.sh deploy
./scripts/deploy.sh status
```

## 💡 配置技巧

### 股票池引用
```yaml
# 在 system_config.yaml 定义
stock_pools:
  my_favorites: [AAPL, TSLA, NVDA]

# 在 users_config.yaml 引用
users:
  user@example.com:
    fluctuation:
      symbols: "@my_favorites"  # 引用股票池
```

### 覆盖默认参数
```yaml
users:
  user@example.com:
    trend:
      # 使用系统默认参数，除了这些覆盖
      trend_analysis:
        up_trend_threshold: 5    # 覆盖系统默认的3
        buy_signal_threshold: 0.9 # 覆盖系统默认的0.8
```

### 多种监控组合
```yaml
users:
  conservative_user@example.com:
    fluctuation:
      threshold_percent: 2.0     # 保守用户，更高阈值
      notification_interval_minutes: 60  # 更长间隔
  
  active_trader@example.com:
    fluctuation:
      threshold_percent: 0.5     # 活跃交易者，更敏感
      notification_interval_minutes: 15  # 更频繁通知
```

你的配置已经完全迁移到新格式，可以直接使用！