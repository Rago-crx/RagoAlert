#!/bin/bash

# RagoAlert 简化部署脚本
# 功能：一键部署，配置文件保护，基本服务管理

set -e

# 配置
SERVICE_NAME="ragoalert"
CURRENT_USER=$(whoami)
DEPLOY_DIR="/opt/ragoalert"
APP_DIR="$DEPLOY_DIR/app"
CONFIG_DIR="$HOME/.ragoalert"
BACKUP_DIR="$DEPLOY_DIR/backups"
VENV_DIR="$DEPLOY_DIR/venv"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        echo "请使用sudo运行此脚本"
        exit 1
    fi
}

deploy() {
    local source_dir=${1:-.}
    
    log "开始部署RagoAlert..."
    
    # 创建目录结构
    mkdir -p "$DEPLOY_DIR" "$CONFIG_DIR" "$BACKUP_DIR"
    
    # 停止服务
    systemctl stop "$SERVICE_NAME" 2>/dev/null || true
    
    # 备份当前版本
    if [[ -d "$APP_DIR" ]]; then
        local backup_name="backup_$(date +%Y%m%d_%H%M%S)"
        log "备份当前版本: $backup_name"
        cp -r "$APP_DIR" "$BACKUP_DIR/$backup_name"
    fi
    
    # 部署新代码
    log "部署应用代码..."
    rm -rf "$APP_DIR"
    cp -r "$source_dir" "$APP_DIR"
    
    # 检查配置文件
    check_config
    
    # 安装依赖
    setup_venv
    
    # 创建systemd服务
    create_service
    
    # 设置权限
    chown -R "$CURRENT_USER:$CURRENT_USER" "$DEPLOY_DIR"
    chown -R "$CURRENT_USER:$CURRENT_USER" "$CONFIG_DIR"
    
    # 启动服务
    systemctl daemon-reload
    systemctl enable "$SERVICE_NAME"
    systemctl start "$SERVICE_NAME"
    
    log "部署完成！"
    systemctl status "$SERVICE_NAME"
}

check_config() {
    log "检查配置文件..."
    
    # 检查必要的配置文件是否存在
    if [[ ! -f "$CONFIG_DIR/users_config.yaml" ]]; then
        log "错误: 配置文件不存在: $CONFIG_DIR/users_config.yaml"
        log "请先创建配置文件，参考: $APP_DIR/config/config_template.yaml"
        exit 1
    fi
    
    if [[ ! -f "$CONFIG_DIR/system_config.yaml" ]]; then
        log "错误: 配置文件不存在: $CONFIG_DIR/system_config.yaml"
        log "请先创建配置文件，参考: $APP_DIR/config/config_template.yaml"
        exit 1
    fi
    
    log "配置文件检查通过"
}

setup_venv() {
    log "设置Python虚拟环境..."
    
    if [[ ! -d "$VENV_DIR" ]]; then
        python3 -m venv "$VENV_DIR"
    fi
    
    if [[ -f "$APP_DIR/requirements.txt" ]]; then
        "$VENV_DIR/bin/pip" install --upgrade pip
        "$VENV_DIR/bin/pip" install -r "$APP_DIR/requirements.txt"
    fi
}

create_service() {
    log "创建systemd服务..."
    
    # 获取当前用户的配置目录绝对路径
    local config_abs_path=$(readlink -f "$CONFIG_DIR")
    
    cat > "/etc/systemd/system/$SERVICE_NAME.service" << EOF
[Unit]
Description=RagoAlert Stock Monitoring Service
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
Group=$CURRENT_USER
WorkingDirectory=$APP_DIR
Environment=PATH=$VENV_DIR/bin:/usr/local/bin:/usr/bin:/bin
Environment=PYTHONPATH=$APP_DIR
Environment=RAGOALERT_CONFIG=$config_abs_path/users_config.yaml
Environment=RAGOALERT_SYSTEM_CONFIG=$config_abs_path/system_config.yaml
ExecStart=$VENV_DIR/bin/python $APP_DIR/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
}

# 服务管理函数
start_service() {
    log "启动服务..."
    systemctl start "$SERVICE_NAME"
    systemctl status "$SERVICE_NAME"
}

stop_service() {
    log "停止服务..."
    systemctl stop "$SERVICE_NAME"
}

restart_service() {
    log "重启服务..."
    systemctl restart "$SERVICE_NAME"
    systemctl status "$SERVICE_NAME"
}

status_service() {
    systemctl status "$SERVICE_NAME"
}

show_logs() {
    journalctl -u "$SERVICE_NAME" -n 50 --no-pager
}

follow_logs() {
    journalctl -u "$SERVICE_NAME" -f
}

list_backups() {
    log "可用备份:"
    ls -la "$BACKUP_DIR" 2>/dev/null || echo "无备份"
}

rollback() {
    local backup_name=${1:-$(ls -t "$BACKUP_DIR" | head -1)}
    
    if [[ -z "$backup_name" ]]; then
        log "没有可用备份"
        exit 1
    fi
    
    local backup_path="$BACKUP_DIR/$backup_name"
    if [[ ! -d "$backup_path" ]]; then
        log "备份不存在: $backup_name"
        exit 1
    fi
    
    log "回滚到备份: $backup_name"
    
    systemctl stop "$SERVICE_NAME"
    rm -rf "$APP_DIR"
    cp -r "$backup_path" "$APP_DIR"
    chown -R "$SERVICE_NAME:$SERVICE_NAME" "$DEPLOY_DIR"
    systemctl start "$SERVICE_NAME"
    
    log "回滚完成"
}

# 使用说明
usage() {
    cat << EOF
RagoAlert 部署脚本

用法:
    $0 deploy [源码目录]     # 部署应用
    $0 start                # 启动服务
    $0 stop                 # 停止服务  
    $0 restart              # 重启服务
    $0 status               # 查看状态
    $0 logs                 # 查看日志
    $0 logs -f              # 跟踪日志
    $0 backups              # 列出备份
    $0 rollback [备份名]     # 回滚版本

示例:
    sudo $0 deploy          # 部署当前目录
    sudo $0 deploy /path/to/source  # 部署指定目录
    $0 status               # 查看服务状态
    $0 logs -f              # 实时查看日志
    sudo $0 rollback        # 回滚到最新备份
EOF
}

# 主逻辑
main() {
    case "${1:-}" in
        deploy)
            check_root
            deploy "${2:-}"
            ;;
        start)
            check_root
            start_service
            ;;
        stop)
            check_root
            stop_service
            ;;
        restart)
            check_root
            restart_service
            ;;
        status)
            status_service
            ;;
        logs)
            if [[ "${2:-}" == "-f" ]]; then
                follow_logs
            else
                show_logs
            fi
            ;;
        backups)
            list_backups
            ;;
        rollback)
            check_root
            rollback "${2:-}"
            ;;
        *)
            usage
            exit 1
            ;;
    esac
}

main "$@"