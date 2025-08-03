# RagoAlert 系统升级指南

## 🎉 升级概览

RagoAlert 已全面升级，主要改进：

- ✅ **多用户系统**: 每个用户独立配置和监控
- ✅ **YAML配置**: 从JSON改为YAML格式，支持注释和更好的可读性
- ✅ **股票池引用**: 支持@引用系统股票池，如`@china_tech`
- ✅ **环境变量配置**: 灵活的配置文件路径管理
- ✅ **简化部署**: 一键bash脚本部署，配置文件保护
- ✅ **目录重组**: 清晰的项目结构，生产和开发分离
- ✅ **Web管理界面**: 直观的用户配置管理页面
- ✅ **API接口**: RESTful API支持程序化配置管理

## 🚀 快速开始

### 开发环境

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 设置开发环境（自动创建 ~/.ragoalert-dev/ 配置）
python tests/dev_start.py --setup

# 3. 启动开发环境
python tests/dev_start.py --dev
```

### 生产环境

```bash
# 1. 创建配置目录和文件
sudo mkdir -p /etc/ragoalert
sudo vim /etc/ragoalert/system_config.yaml
sudo vim /etc/ragoalert/users_config.yaml

# 2. 一键部署
sudo ./scripts/deploy.sh deploy

# 3. 管理服务
./scripts/deploy.sh status
./scripts/deploy.sh logs -f
```

### Web管理界面

访问: http://localhost:8080

## 📁 项目结构变化

### 新增文件
- `config/config_manager.py` - YAML多用户配置管理系统
- `src/multi_user_monitor.py` - 多用户监控管理器
- `src/web_api.py` - Web API服务
- `scripts/deploy.sh` - 一键bash部署脚本
- `tests/dev_start.py` - 开发环境管理工具
- `tests/run_tests.py` - 测试运行器
- `docs/CONFIG_MIGRATION.md` - 配置迁移指南
- `docs/DEPLOY_SIMPLE.md` - 简化部署指南

### 目录重组
- `scripts/` - 只保留生产部署脚本
- `tests/` - 包含开发工具和测试套件
- `src/` - 核心业务代码
- `config/` - 配置管理模块

### 删除文件
- 复杂的Python部署脚本（deploy.py, service_manager.py）
- 详细的部署文档（DEPLOYMENT.md）
- 根目录配置文件（*.yaml）

## 🔧 架构变化

### 旧架构
```
main.py -> FluctuationMonitor (静态配置) -> 发送邮件给固定收件人
```

### 新架构
```
main.py -> MultiUserMonitorManager -> 为每个用户创建独立的Monitor -> 发送个性化邮件
```

## 📋 Web界面功能

### 用户管理
- 添加/删除用户
- 设置波动监控参数（阈值、通知间隔、监控股票）
- 设置趋势监控参数（盘前/盘后通知、监控股票）

### 系统配置
- SMTP邮箱设置
- Web服务端口
- 日志级别

### 统计信息
- 用户数量统计
- 监控股票总览

## 🔄 配置系统升级

### YAML配置格式
新系统使用YAML配置文件：

- `users_config.yaml` - 用户配置（支持注释和复杂结构）
- `system_config.yaml` - 系统配置（包含股票池定义）

### 股票池引用
支持@符号引用预定义股票池：
```yaml
users:
  user@example.com:
    fluctuation:
      symbols: "@china_tech"  # 引用系统股票池
```

### 环境变量配置
```bash
# 生产环境
RAGOALERT_CONFIG=/etc/ragoalert/users_config.yaml
RAGOALERT_SYSTEM_CONFIG=/etc/ragoalert/system_config.yaml

# 开发环境（自动设置）
RAGOALERT_CONFIG=~/.ragoalert-dev/users_config.yaml
RAGOALERT_SYSTEM_CONFIG=~/.ragoalert-dev/system_config.yaml
```

### 配置迁移
详见 [配置迁移指南](CONFIG_MIGRATION.md)，包含完整的配置对比和迁移步骤。

## 📧 邮件通知

每个用户现在收到个性化的邮件通知：
- 邮件主题包含用户名
- 只包含该用户监控的股票信息
- 根据用户设置的阈值触发

## 🛠️ API接口

系统提供RESTful API：

- `GET /api/users` - 获取所有用户
- `POST /api/users` - 创建用户
- `PUT /api/users/{email}` - 更新用户配置
- `DELETE /api/users/{email}` - 删除用户
- `GET /api/system` - 获取系统配置
- `PUT /api/system` - 更新系统配置
- `GET /api/stats` - 获取统计信息

## 🚀 部署系统升级

### 简化部署
- 一键bash脚本部署：`sudo ./scripts/deploy.sh deploy`
- 配置文件保护：部署时不会覆盖服务器配置
- 自动备份回滚：每次部署前自动备份，支持一键回滚
- systemd服务管理：标准的Linux服务管理

### 开发工具
- 开发环境管理：`python tests/dev_start.py --dev`
- 测试运行器：`python tests/run_tests.py --quick`
- 快速验证：`python tests/quick_test.py`

详见 [简化部署指南](DEPLOY_SIMPLE.md)

## 🧪 测试系统

### 测试工具重组
所有测试和开发工具移至`tests/`目录：
- `tests/run_tests.py` - 统一测试运行器
- `tests/dev_start.py` - 开发环境管理
- `tests/quick_test.py` - 快速验证脚本
- `tests/test_*.py` - 单元测试文件

### 测试命令
```bash
# 快速验证
python tests/run_tests.py --quick

# 完整测试
python tests/run_tests.py --all

# 特定测试
python tests/run_tests.py --deps --syntax --config
```

## 🔍 故障排除

### 1. 配置问题
```bash
# 检查配置文件语法
python -c "import yaml; yaml.safe_load(open('~/.ragoalert-dev/users_config.yaml'))"

# 验证环境变量
echo $RAGOALERT_CONFIG
echo $RAGOALERT_SYSTEM_CONFIG
```

### 2. 开发环境
```bash
# 重新设置开发环境
python tests/dev_start.py --setup

# 运行测试检查
python tests/run_tests.py --deps --syntax
```

### 3. 生产部署
```bash
# 检查服务状态
./scripts/deploy.sh status

# 查看日志
./scripts/deploy.sh logs -f

# 回滚版本
sudo ./scripts/deploy.sh rollback
```

### 4. 股票池引用
确保@引用的股票池在system_config.yaml中存在：
```yaml
stock_pools:
  china_tech: [BIDU, BABA, ...]
```

## 📞 技术支持

如有问题，请查看：
1. [配置迁移指南](CONFIG_MIGRATION.md) - 详细的配置对比和示例
2. [简化部署指南](DEPLOY_SIMPLE.md) - 部署和服务管理
3. [开发指南](README_DEV.md) - 开发环境和测试
4. 系统日志文件和服务状态