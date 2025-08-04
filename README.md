# 🚀 RagoAlert

多用户股票监控系统，支持实时波动监控、趋势分析和Web配置管理。

## ✨ 特性

- 🔄 **实时监控** - 多用户股票价格波动和趋势监控
- 🌐 **Web管理** - 直观的Web界面进行用户和配置管理
- 📧 **智能通知** - 邮件通知系统，支持自定义阈值和间隔
- 📊 **技术分析** - 集成EMA、MACD、RSI、ADX等技术指标
- ⚙️ **实时配置** - 配置修改即时生效，无需重启服务
- 🚀 **一键部署** - 自动化部署流程，配置文件受保护
- 🧪 **完整测试** - 单元测试、集成测试和性能测试

## 📁 项目结构

```
RagoAlert/
├── 📚 docs/                    # 📖 文档
│   ├── README.md              # 原始README
│   ├── README_DEV.md          # 开发指南
│   ├── DEPLOY_SIMPLE.md       # 简化部署指南
│   ├── CONFIG_MIGRATION.md    # 配置迁移指南
│   └── UPGRADE_GUIDE.md       # 升级指南
├── ⚙️ config/                  # 🔧 配置管理
│   ├── config_manager.py      # 配置管理核心
│   ├── config_template.yaml   # 配置模板
│   └── config_dev.yaml        # 开发配置
├── 🛠️ scripts/                 # 📜 生产部署脚本
│   └── deploy.sh              # 一键部署脚本
├── 💻 src/                     # 📦 核心代码
│   ├── data/                  # 数据获取
│   │   └── yahoo.py           # Yahoo Finance接口
│   ├── indicators/            # 技术指标
│   │   ├── fluctuation.py     # 波动分析
│   │   └── trend.py           # 趋势分析
│   ├── monitors/              # 监控器
│   │   ├── fluctuation_monitor.py # 波动监控
│   │   └── trend_monitor.py    # 趋势监控
│   ├── notifiers/             # 通知系统
│   │   └── email.py           # 邮件通知
│   ├── multi_user_monitor.py  # 多用户监控管理
│   └── web_api.py             # Web API服务
├── 🧪 tests/                   # ✅ 测试套件与开发工具
│   ├── dev_start.py           # 开发环境管理
│   ├── run_tests.py           # 测试运行器
│   ├── quick_test.py          # 快速验证
│   ├── test_data_generator.py # 测试数据生成
│   └── test_*.py              # 单元测试文件
├── main.py                    # 🚀 主程序入口
└── requirements.txt           # 📋 依赖清单
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置系统

```bash
# 配置文件会在首次运行时自动创建
# 可选：预先创建配置目录和文件
mkdir -p ~/.ragoalert
cp config/config_template.yaml ~/.ragoalert/users_config.yaml
cp config/config_template.yaml ~/.ragoalert/system_config.yaml

# 编辑配置文件，设置SMTP邮箱等信息
# vim ~/.ragoalert/system_config.yaml
```

### 3. 启动系统

```bash
# 启动完整系统（监控 + Web管理）
python main.py

# 或使用开发脚本
python tests/dev_start.py --dev
```

### 4. 访问Web管理界面

打开浏览器访问: http://localhost:8080

## 🧪 开发和测试

详细的开发指南请参阅 [开发文档](docs/DEV.md)

```bash
# 验证环境
python tests/run_tests.py --deps --syntax

# 快速验证（推荐用于日常开发）
python tests/run_tests.py --quick

# 完整测试（代码提交前运行）
python tests/run_tests.py --all

# 开发模式启动
python tests/dev_start.py --dev
```

> **💡 开发者提示**: 使用 `--quick` 进行快速验证，用 `--all` 进行完整测试。详细说明请查看 [开发指南](docs/DEV.md)。

## 📊 监控功能

### 波动监控
- 自定义波动阈值百分比
- 多股票并行监控
- 通知频率控制
- 历史价格追踪

### 趋势分析
- EMA短期/长期趋势判断
- MACD动量分析
- RSI超买超卖检测
- ADX趋势强度评估
- 买入/卖出信号生成

## ⚙️ 配置管理

### 用户配置
- 个人监控股票列表
- 自定义技术分析参数
- 通知偏好设置
- 股票池引用支持

### 系统配置
- SMTP邮件服务器设置
- Web服务端口配置
- 全局技术分析参数
- 股票池定义

## 📧 通知系统

支持Gmail SMTP邮件通知，包含：
- 波动监控：价格变化通知
- 趋势分析：技术指标和交易信号
- 系统状态：服务启动/停止通知

## 🛠️ API接口

RESTful API支持完整的CRUD操作：

- `GET /api/users` - 获取所有用户
- `POST /api/users` - 创建用户
- `PUT /api/users/{email}` - 更新用户
- `DELETE /api/users/{email}` - 删除用户
- `GET /api/stats` - 获取系统统计

## 📈 技术架构

- **多用户架构**: 每个用户独立的监控实例
- **实时配置**: YAML配置文件，支持热重载
- **并发处理**: ThreadPoolExecutor多线程处理
- **模块化设计**: 清晰的模块分离和依赖管理
- **完整测试**: 单元测试、集成测试、性能测试

## 🔧 环境变量

```bash
# 生产环境
RAGOALERT_CONFIG=~/.ragoalert/users_config.yaml      # 用户配置文件路径
RAGOALERT_SYSTEM_CONFIG=~/.ragoalert/system_config.yaml # 系统配置文件路径

# 开发环境（自动设置）
RAGOALERT_CONFIG=~/.ragoalert-dev/users_config.yaml    # 开发用户配置
RAGOALERT_SYSTEM_CONFIG=~/.ragoalert-dev/system_config.yaml # 开发系统配置

# 通用
RAGOALERT_LOG_LEVEL=INFO                        # 日志级别
```

## 📝 许可证

本项目采用 MIT 许可证。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 🚀 生产部署

### 快速部署到远程服务器

```bash
# 一键部署到生产环境
sudo ./scripts/deploy.sh deploy

# 服务管理
./scripts/deploy.sh status
./scripts/deploy.sh logs -f
./scripts/deploy.sh restart
```

### 配置文件保护

部署系统确保服务器配置文件**不会被部署替换**：
- ✅ `users_config.yaml` - 用户监控配置
- ✅ `system_config.yaml` - 系统配置(SMTP等)

配置存储在用户根目录下 `~/.ragoalert/`，可通过以下方式修改：
1. **Web API接口** - `http://your-server:8080`
2. **直接编辑** - 用户可直接编辑配置文件，无需管理员权限
3. **服务权限统一** - 服务运行在部署用户下，避免权限问题

详细部署指南请参阅 [简化部署文档](docs/DEPLOYMENT.md)

---

📚 更多信息请查看 [开发文档](docs/DEV.md)、[简化部署指南](docs/DEPLOYMENT.md)、[配置迁移指南](docs/CONFIG_MIGRATION.md) 和 [升级指南](docs/UPGRADE_GUIDE.md)