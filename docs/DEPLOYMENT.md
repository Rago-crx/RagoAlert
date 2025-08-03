# 🚀 RagoAlert 简化部署指南

一键bash脚本部署，简单高效。

## 📋 快速部署

### 1. 服务器准备配置文件

```bash
# 登录服务器
ssh user@server

# 创建配置目录
sudo mkdir -p /etc/ragoalert

# 手动创建配置文件（管理员负责）
# 可参考 config/config_template.yaml 作为起点
sudo vim /etc/ragoalert/system_config.yaml
sudo vim /etc/ragoalert/users_config.yaml
```

### 2. 部署到服务器

```bash
# 在服务器上拉取代码
ssh user@server
cd /opt
sudo git clone https://github.com/your-repo/RagoAlert.git
cd RagoAlert

# 或更新现有代码
sudo git pull origin main

# 一键部署
sudo ./scripts/deploy.sh deploy
```

### 3. 服务管理

```bash
# 查看状态
./scripts/deploy.sh status

# 启动/停止/重启
sudo ./scripts/deploy.sh start
sudo ./scripts/deploy.sh stop  
sudo ./scripts/deploy.sh restart

# 查看日志
./scripts/deploy.sh logs
./scripts/deploy.sh logs -f  # 实时跟踪
```

### 4. 配置管理

配置文件位置：`/etc/ragoalert/`
- `users_config.yaml` - 用户配置
- `system_config.yaml` - 系统配置

```bash
# 编辑配置
sudo vim /etc/ragoalert/system_config.yaml

# 重启生效
sudo ./scripts/deploy.sh restart
```

### 5. 备份回滚

```bash
# 查看备份
./scripts/deploy.sh backups

# 回滚到最新备份
sudo ./scripts/deploy.sh rollback

# 回滚到指定备份
sudo ./scripts/deploy.sh rollback backup_20241201_120000
```

## 🏗️ 部署结构

```
/opt/ragoalert/
├── app/           # 应用代码
├── backups/       # 自动备份
└── venv/          # Python环境

/etc/ragoalert/    # 独立配置目录
├── users_config.yaml
└── system_config.yaml
```

## ⚙️ 配置保护

- ✅ 配置文件独立存储在 `/etc/ragoalert/`
- ✅ 通过环境变量指定配置路径
- ✅ 部署时不会影响现有配置
- ✅ 只能通过Web API或服务器直接编辑修改

## 🔧 常用命令

```bash
# 完整部署流程
sudo ./scripts/deploy.sh deploy

# 日常管理
./scripts/deploy.sh status
./scripts/deploy.sh logs -f
sudo ./scripts/deploy.sh restart

# 问题排查  
systemctl status ragoalert
journalctl -u ragoalert -f
```

简单高效，满足核心需求！