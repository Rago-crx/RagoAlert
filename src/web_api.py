"""
FastAPI Web服务
提供用户配置管理API接口和前端页面
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
import logging
from config.config_manager import config_manager, UserConfig, UserFluctuationConfig, UserTrendConfig
import os

app = FastAPI(title="RagoAlert Configuration API", version="1.0.0")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic模型定义
class FluctuationConfigModel(BaseModel):
    threshold_percent: float = 3.0
    symbols: List[str] = ["AAPL", "TSLA", "NVDA", "MSFT", "GOOGL"]
    notification_interval_minutes: int = 5
    enabled: bool = True

class TrendConfigModel(BaseModel):
    enabled: bool = True
    symbols: List[str] = ["AAPL", "TSLA", "NVDA", "MSFT", "GOOGL"]
    pre_market_notification: bool = True
    post_market_notification: bool = True

class UserConfigModel(BaseModel):
    email: EmailStr
    name: str = ""
    fluctuation: FluctuationConfigModel
    trend: TrendConfigModel

class UserConfigUpdateModel(BaseModel):
    name: Optional[str] = None
    fluctuation: Optional[FluctuationConfigModel] = None
    trend: Optional[TrendConfigModel] = None

class SystemConfigModel(BaseModel):
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 465
    sender_email: str = ""
    sender_password: str = ""
    web_port: int = 8080
    log_level: str = "INFO"

# API路由

@app.get("/")
async def root():
    """根路径，返回API信息"""
    return {"message": "RagoAlert Configuration API", "version": "1.0.0"}

@app.get("/api/users", response_model=Dict[str, Any])
async def get_all_users():
    """获取所有用户配置"""
    try:
        users = config_manager.get_all_users()
        result = {}
        for email, user_config in users.items():
            result[email] = {
                "email": user_config.email,
                "name": user_config.name,
                "fluctuation": {
                    "threshold_percent": user_config.fluctuation.threshold_percent,
                    "symbols": user_config.fluctuation.symbols,
                    "notification_interval_minutes": user_config.fluctuation.notification_interval_minutes,
                    "enabled": user_config.fluctuation.enabled
                },
                "trend": {
                    "enabled": user_config.trend.enabled,
                    "symbols": user_config.trend.symbols,
                    "pre_market_notification": user_config.trend.pre_market_notification,
                    "post_market_notification": user_config.trend.post_market_notification
                },
                "created_at": user_config.created_at,
                "updated_at": user_config.updated_at
            }
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/users/{email}", response_model=Dict[str, Any])
async def get_user_config(email: str):
    """获取指定用户配置"""
    try:
        user_config = config_manager.get_user_config(email)
        if not user_config:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        return {
            "email": user_config.email,
            "name": user_config.name,
            "fluctuation": {
                "threshold_percent": user_config.fluctuation.threshold_percent,
                "symbols": user_config.fluctuation.symbols,
                "notification_interval_minutes": user_config.fluctuation.notification_interval_minutes,
                "enabled": user_config.fluctuation.enabled
            },
            "trend": {
                "enabled": user_config.trend.enabled,
                "symbols": user_config.trend.symbols,
                "pre_market_notification": user_config.trend.pre_market_notification,
                "post_market_notification": user_config.trend.post_market_notification
            },
            "created_at": user_config.created_at,
            "updated_at": user_config.updated_at
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/users", response_model=Dict[str, str])
async def create_user(user_data: UserConfigModel):
    """创建新用户配置"""
    try:
        # 检查用户是否已存在
        existing_user = config_manager.get_user_config(user_data.email)
        if existing_user:
            raise HTTPException(status_code=400, detail="用户已存在")
        
        # 创建用户配置
        success = config_manager.create_or_update_user(
            email=user_data.email,
            name=user_data.name,
            fluctuation_threshold_percent=user_data.fluctuation.threshold_percent,
            fluctuation_symbols=user_data.fluctuation.symbols,
            fluctuation_notification_interval_minutes=user_data.fluctuation.notification_interval_minutes,
            fluctuation_enabled=user_data.fluctuation.enabled,
            trend_enabled=user_data.trend.enabled,
            trend_symbols=user_data.trend.symbols,
            trend_pre_market_notification=user_data.trend.pre_market_notification,
            trend_post_market_notification=user_data.trend.post_market_notification
        )
        
        if success:
            return {"message": "用户创建成功", "email": user_data.email}
        else:
            raise HTTPException(status_code=500, detail="用户创建失败")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/users/{email}", response_model=Dict[str, str])
async def update_user_config(email: str, user_data: UserConfigUpdateModel):
    """更新用户配置"""
    try:
        # 检查用户是否存在
        existing_user = config_manager.get_user_config(email)
        if not existing_user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 准备更新数据
        update_data = {}
        if user_data.name is not None:
            update_data["name"] = user_data.name
        
        if user_data.fluctuation is not None:
            update_data.update({
                "fluctuation_threshold_percent": user_data.fluctuation.threshold_percent,
                "fluctuation_symbols": user_data.fluctuation.symbols,
                "fluctuation_notification_interval_minutes": user_data.fluctuation.notification_interval_minutes,
                "fluctuation_enabled": user_data.fluctuation.enabled
            })
        
        if user_data.trend is not None:
            update_data.update({
                "trend_enabled": user_data.trend.enabled,
                "trend_symbols": user_data.trend.symbols,
                "trend_pre_market_notification": user_data.trend.pre_market_notification,
                "trend_post_market_notification": user_data.trend.post_market_notification
            })
        
        # 更新用户配置
        success = config_manager.create_or_update_user(email=email, **update_data)
        
        if success:
            return {"message": "用户配置更新成功", "email": email}
        else:
            raise HTTPException(status_code=500, detail="用户配置更新失败")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/users/{email}", response_model=Dict[str, str])
async def delete_user(email: str):
    """删除用户配置"""
    try:
        success = config_manager.delete_user(email)
        if success:
            return {"message": "用户删除成功", "email": email}
        else:
            raise HTTPException(status_code=404, detail="用户不存在")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/system", response_model=Dict[str, Any])
async def get_system_config():
    """获取系统配置"""
    try:
        sys_config = config_manager.system_config
        return {
            "smtp_server": sys_config.smtp_server,
            "smtp_port": sys_config.smtp_port,
            "sender_email": sys_config.sender_email,
            "sender_password": "***" if sys_config.sender_password else "",  # 隐藏密码
            "web_port": sys_config.web_port,
            "log_level": sys_config.log_level
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/system", response_model=Dict[str, str])
async def update_system_config(system_data: SystemConfigModel):
    """更新系统配置"""
    try:
        update_data = {}
        for field, value in system_data.dict().items():
            if field == "sender_password" and value == "***":
                continue  # 跳过密码占位符
            update_data[field] = value
        
        success = config_manager.update_system_config(**update_data)
        if success:
            return {"message": "系统配置更新成功"}
        else:
            raise HTTPException(status_code=500, detail="系统配置更新失败")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats", response_model=Dict[str, Any])
async def get_statistics():
    """获取统计信息"""
    try:
        all_users = config_manager.get_all_users()
        fluctuation_users = config_manager.get_fluctuation_enabled_users()
        trend_users = config_manager.get_trend_enabled_users()
        monitored_symbols = config_manager.get_all_monitored_symbols()
        
        return {
            "total_users": len(all_users),
            "fluctuation_enabled_users": len(fluctuation_users),
            "trend_enabled_users": len(trend_users),
            "total_monitored_symbols": len(monitored_symbols),
            "monitored_symbols": sorted(list(monitored_symbols))
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/reload", response_model=Dict[str, str])
async def reload_configs():
    """重新加载配置文件"""
    try:
        success = config_manager.reload_all_configs()
        if success:
            return {"message": "配置重新加载成功"}
        else:
            raise HTTPException(status_code=500, detail="配置重新加载失败")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 前端页面路由
@app.get("/admin", response_class=HTMLResponse)
async def admin_page():
    """管理页面"""
    return """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>RagoAlert 配置管理</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
            .header { background: #2c3e50; color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
            .card { background: white; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }
            .card-header { background: #3498db; color: white; padding: 15px; border-radius: 10px 10px 0 0; }
            .card-body { padding: 20px; }
            .form-group { margin-bottom: 15px; }
            .form-group label { display: block; margin-bottom: 5px; font-weight: bold; }
            .form-control { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; font-size: 14px; }
            .btn { padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; font-size: 14px; }
            .btn-primary { background: #3498db; color: white; }
            .btn-success { background: #27ae60; color: white; }
            .btn-danger { background: #e74c3c; color: white; }
            .btn-warning { background: #f39c12; color: white; }
            .btn:hover { opacity: 0.9; }
            .user-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(400px, 1fr)); gap: 20px; }
            .user-card { border: 1px solid #ddd; border-radius: 8px; padding: 15px; background: white; }
            .user-email { font-weight: bold; color: #2c3e50; margin-bottom: 10px; }
            .config-section { margin-bottom: 15px; padding: 10px; background: #f8f9fa; border-radius: 5px; }
            .config-title { font-weight: bold; margin-bottom: 5px; }
            .symbol-tags { display: flex; flex-wrap: wrap; gap: 5px; }
            .symbol-tag { background: #e9ecef; padding: 3px 8px; border-radius: 15px; font-size: 12px; }
            .status-enabled { color: #27ae60; }
            .status-disabled { color: #e74c3c; }
            .tabs { display: flex; border-bottom: 1px solid #ddd; margin-bottom: 20px; }
            .tab { padding: 10px 20px; cursor: pointer; border: none; background: none; }
            .tab.active { background: #3498db; color: white; }
            .tab-content { display: none; }
            .tab-content.active { display: block; }
            .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }
            .stat-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; text-align: center; }
            .stat-number { font-size: 2em; font-weight: bold; }
            .stat-label { font-size: 0.9em; opacity: 0.9; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 RagoAlert 配置管理系统</h1>
                <p>管理股票监控用户配置和系统设置</p>
            </div>
            
            <div class="tabs">
                <button class="tab active" onclick="showTab('users')">用户管理</button>
                <button class="tab" onclick="showTab('system')">系统配置</button>
                <button class="tab" onclick="showTab('stats')">统计信息</button>
            </div>
            
            <div id="users-tab" class="tab-content active">
                <div class="card">
                    <div class="card-header">
                        <h2>添加新用户</h2>
                    </div>
                    <div class="card-body">
                        <form id="userForm">
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                                <div>
                                    <div class="form-group">
                                        <label>邮箱地址</label>
                                        <input type="email" class="form-control" id="userEmail" required>
                                    </div>
                                    <div class="form-group">
                                        <label>用户名称</label>
                                        <input type="text" class="form-control" id="userName">
                                    </div>
                                    <div class="form-group">
                                        <label>波动阈值 (%)</label>
                                        <input type="number" class="form-control" id="fluctuationThreshold" value="3" step="0.1">
                                    </div>
                                    <div class="form-group">
                                        <label>通知间隔 (分钟)</label>
                                        <input type="number" class="form-control" id="notificationInterval" value="5">
                                    </div>
                                </div>
                                <div>
                                    <div class="form-group">
                                        <label>波动监控股票 (逗号分隔)</label>
                                        <textarea class="form-control" id="fluctuationSymbols" rows="3">AAPL,TSLA,NVDA,MSFT,GOOGL</textarea>
                                    </div>
                                    <div class="form-group">
                                        <label>趋势监控股票 (逗号分隔)</label>
                                        <textarea class="form-control" id="trendSymbols" rows="3">AAPL,TSLA,NVDA,MSFT,GOOGL</textarea>
                                    </div>
                                    <div class="form-group">
                                        <label>
                                            <input type="checkbox" id="fluctuationEnabled" checked> 启用波动监控
                                        </label>
                                    </div>
                                    <div class="form-group">
                                        <label>
                                            <input type="checkbox" id="trendEnabled" checked> 启用趋势监控
                                        </label>
                                    </div>
                                </div>
                            </div>
                            <button type="submit" class="btn btn-primary">添加用户</button>
                            <button type="button" class="btn btn-warning" onclick="refreshUsers()">刷新列表</button>
                        </form>
                    </div>
                </div>
                
                <div class="card">
                    <div class="card-header">
                        <h2>用户列表</h2>
                    </div>
                    <div class="card-body">
                        <div id="usersList" class="user-list">
                            <!-- 用户列表将在这里动态加载 -->
                        </div>
                    </div>
                </div>
            </div>
            
            <div id="system-tab" class="tab-content">
                <div class="card">
                    <div class="card-header">
                        <h2>系统配置</h2>
                    </div>
                    <div class="card-body">
                        <form id="systemForm">
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                                <div>
                                    <div class="form-group">
                                        <label>SMTP服务器</label>
                                        <input type="text" class="form-control" id="smtpServer">
                                    </div>
                                    <div class="form-group">
                                        <label>SMTP端口</label>
                                        <input type="number" class="form-control" id="smtpPort">
                                    </div>
                                    <div class="form-group">
                                        <label>发送邮箱</label>
                                        <input type="email" class="form-control" id="senderEmail">
                                    </div>
                                </div>
                                <div>
                                    <div class="form-group">
                                        <label>邮箱密码</label>
                                        <input type="password" class="form-control" id="senderPassword">
                                    </div>
                                    <div class="form-group">
                                        <label>Web端口</label>
                                        <input type="number" class="form-control" id="webPort">
                                    </div>
                                    <div class="form-group">
                                        <label>日志级别</label>
                                        <select class="form-control" id="logLevel">
                                            <option value="DEBUG">DEBUG</option>
                                            <option value="INFO">INFO</option>
                                            <option value="WARNING">WARNING</option>
                                            <option value="ERROR">ERROR</option>
                                        </select>
                                    </div>
                                </div>
                            </div>
                            <button type="submit" class="btn btn-primary">保存系统配置</button>
                            <button type="button" class="btn btn-warning" onclick="loadSystemConfig()">重新加载</button>
                        </form>
                    </div>
                </div>
            </div>
            
            <div id="stats-tab" class="tab-content">
                <div id="statsContainer">
                    <!-- 统计信息将在这里动态加载 -->
                </div>
            </div>
        </div>
        
        <script>
            // Tab切换
            function showTab(tabName) {
                // 隐藏所有tab内容
                document.querySelectorAll('.tab-content').forEach(tab => {
                    tab.classList.remove('active');
                });
                document.querySelectorAll('.tab').forEach(tab => {
                    tab.classList.remove('active');
                });
                
                // 显示选中的tab
                document.getElementById(tabName + '-tab').classList.add('active');
                event.target.classList.add('active');
                
                // 加载对应数据
                if (tabName === 'users') {
                    refreshUsers();
                } else if (tabName === 'system') {
                    loadSystemConfig();
                } else if (tabName === 'stats') {
                    loadStats();
                }
            }
            
            // API调用函数
            async function apiCall(url, options = {}) {
                try {
                    const response = await fetch(url, {
                        headers: {
                            'Content-Type': 'application/json',
                            ...options.headers
                        },
                        ...options
                    });
                    
                    if (!response.ok) {
                        const error = await response.json();
                        throw new Error(error.detail || 'API调用失败');
                    }
                    
                    return await response.json();
                } catch (error) {
                    alert('错误: ' + error.message);
                    throw error;
                }
            }
            
            // 刷新用户列表
            async function refreshUsers() {
                try {
                    const users = await apiCall('/api/users');
                    const usersList = document.getElementById('usersList');
                    
                    if (Object.keys(users).length === 0) {
                        usersList.innerHTML = '<p>暂无用户配置</p>';
                        return;
                    }
                    
                    usersList.innerHTML = Object.entries(users).map(([email, user]) => `
                        <div class="user-card">
                            <div class="user-email">${user.email}</div>
                            <div style="margin-bottom: 10px;"><strong>姓名:</strong> ${user.name || '未设置'}</div>
                            
                            <div class="config-section">
                                <div class="config-title">📈 波动监控 
                                    <span class="${user.fluctuation.enabled ? 'status-enabled' : 'status-disabled'}">
                                        ${user.fluctuation.enabled ? '✅ 已启用' : '❌ 已禁用'}
                                    </span>
                                </div>
                                <div>阈值: ${user.fluctuation.threshold_percent}%</div>
                                <div>间隔: ${user.fluctuation.notification_interval_minutes}分钟</div>
                                <div class="symbol-tags">
                                    ${user.fluctuation.symbols.map(s => `<span class="symbol-tag">${s}</span>`).join('')}
                                </div>
                            </div>
                            
                            <div class="config-section">
                                <div class="config-title">📊 趋势监控 
                                    <span class="${user.trend.enabled ? 'status-enabled' : 'status-disabled'}">
                                        ${user.trend.enabled ? '✅ 已启用' : '❌ 已禁用'}
                                    </span>
                                </div>
                                <div>盘前通知: ${user.trend.pre_market_notification ? '✅' : '❌'}</div>
                                <div>盘后通知: ${user.trend.post_market_notification ? '✅' : '❌'}</div>
                                <div class="symbol-tags">
                                    ${user.trend.symbols.map(s => `<span class="symbol-tag">${s}</span>`).join('')}
                                </div>
                            </div>
                            
                            <div style="margin-top: 15px;">
                                <button class="btn btn-warning" onclick="editUser('${email}')">编辑</button>
                                <button class="btn btn-danger" onclick="deleteUser('${email}')">删除</button>
                            </div>
                            
                            <div style="margin-top: 10px; font-size: 12px; color: #666;">
                                创建: ${new Date(user.created_at).toLocaleString()}<br>
                                更新: ${new Date(user.updated_at).toLocaleString()}
                            </div>
                        </div>
                    `).join('');
                } catch (error) {
                    console.error('加载用户列表失败:', error);
                }
            }
            
            // 添加用户
            document.getElementById('userForm').addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const userData = {
                    email: document.getElementById('userEmail').value,
                    name: document.getElementById('userName').value,
                    fluctuation: {
                        threshold_percent: parseFloat(document.getElementById('fluctuationThreshold').value),
                        symbols: document.getElementById('fluctuationSymbols').value.split(',').map(s => s.trim()),
                        notification_interval_minutes: parseInt(document.getElementById('notificationInterval').value),
                        enabled: document.getElementById('fluctuationEnabled').checked
                    },
                    trend: {
                        enabled: document.getElementById('trendEnabled').checked,
                        symbols: document.getElementById('trendSymbols').value.split(',').map(s => s.trim()),
                        pre_market_notification: true,
                        post_market_notification: true
                    }
                };
                
                try {
                    await apiCall('/api/users', {
                        method: 'POST',
                        body: JSON.stringify(userData)
                    });
                    
                    alert('用户添加成功!');
                    document.getElementById('userForm').reset();
                    refreshUsers();
                } catch (error) {
                    console.error('添加用户失败:', error);
                }
            });
            
            // 删除用户
            async function deleteUser(email) {
                if (!confirm(`确定要删除用户 ${email} 吗？`)) return;
                
                try {
                    await apiCall(`/api/users/${encodeURIComponent(email)}`, {
                        method: 'DELETE'
                    });
                    
                    alert('用户删除成功!');
                    refreshUsers();
                } catch (error) {
                    console.error('删除用户失败:', error);
                }
            }
            
            // 编辑用户 (简化版，可以扩展为弹窗编辑)
            function editUser(email) {
                alert('编辑功能开发中，请先删除后重新创建用户');
            }
            
            // 加载系统配置
            async function loadSystemConfig() {
                try {
                    const config = await apiCall('/api/system');
                    
                    document.getElementById('smtpServer').value = config.smtp_server;
                    document.getElementById('smtpPort').value = config.smtp_port;
                    document.getElementById('senderEmail').value = config.sender_email;
                    document.getElementById('senderPassword').value = config.sender_password;
                    document.getElementById('webPort').value = config.web_port;
                    document.getElementById('logLevel').value = config.log_level;
                } catch (error) {
                    console.error('加载系统配置失败:', error);
                }
            }
            
            // 保存系统配置
            document.getElementById('systemForm').addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const systemData = {
                    smtp_server: document.getElementById('smtpServer').value,
                    smtp_port: parseInt(document.getElementById('smtpPort').value),
                    sender_email: document.getElementById('senderEmail').value,
                    sender_password: document.getElementById('senderPassword').value,
                    web_port: parseInt(document.getElementById('webPort').value),
                    log_level: document.getElementById('logLevel').value
                };
                
                try {
                    await apiCall('/api/system', {
                        method: 'PUT',
                        body: JSON.stringify(systemData)
                    });
                    
                    alert('系统配置保存成功!');
                } catch (error) {
                    console.error('保存系统配置失败:', error);
                }
            });
            
            // 加载统计信息
            async function loadStats() {
                try {
                    const stats = await apiCall('/api/stats');
                    
                    document.getElementById('statsContainer').innerHTML = `
                        <div class="stats">
                            <div class="stat-card">
                                <div class="stat-number">${stats.total_users}</div>
                                <div class="stat-label">总用户数</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-number">${stats.fluctuation_enabled_users}</div>
                                <div class="stat-label">波动监控用户</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-number">${stats.trend_enabled_users}</div>
                                <div class="stat-label">趋势监控用户</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-number">${stats.total_monitored_symbols}</div>
                                <div class="stat-label">监控股票数</div>
                            </div>
                        </div>
                        
                        <div class="card">
                            <div class="card-header">
                                <h3>监控的股票列表</h3>
                            </div>
                            <div class="card-body">
                                <div class="symbol-tags">
                                    ${stats.monitored_symbols.map(s => `<span class="symbol-tag">${s}</span>`).join('')}
                                </div>
                            </div>
                        </div>
                    `;
                } catch (error) {
                    console.error('加载统计信息失败:', error);
                }
            }
            
            // 页面加载完成后初始化
            document.addEventListener('DOMContentLoaded', function() {
                refreshUsers();
            });
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    import uvicorn
    
    # 获取配置的端口
    port = config_manager.system_config.web_port
    
    logging.info(f"启动Web服务，端口: {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)