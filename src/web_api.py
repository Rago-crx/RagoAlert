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
from src.config.config_manager import config_manager, UserConfig, UserFluctuationConfig, UserTrendConfig
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
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <style>
            :root {
                --primary: #2563eb;
                --primary-light: #3b82f6;
                --primary-dark: #1e40af;
                --secondary: #6b7280;
                --success: #059669;
                --danger: #dc2626;
                --warning: #d97706;
                --info: #0891b2;
                --dark: #111827;
                --text-primary: #1f2937;
                --text-secondary: #6b7280;
                --text-muted: #9ca3af;
                --surface: #ffffff;
                --surface-secondary: #f9fafb;
                --surface-tertiary: #f3f4f6;
                --border: #e5e7eb;
                --border-light: #f3f4f6;
                --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
                --shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1);
                --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
                --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
                --shadow-xl: 0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1);
                --radius-xs: 0.125rem;
                --radius-sm: 0.25rem;
                --radius: 0.5rem;
                --radius-lg: 0.75rem;
                --radius-xl: 1rem;
                --radius-2xl: 1.5rem;
                --transition: all 0.15s cubic-bezier(0.4, 0, 0.2, 1);
                --transition-slow: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }

            * { margin: 0; padding: 0; box-sizing: border-box; }
            
            body { 
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                background: var(--surface-secondary);
                min-height: 100vh;
                line-height: 1.5;
                color: var(--text-primary);
                font-size: 14px;
                -webkit-font-smoothing: antialiased;
                -moz-osx-font-smoothing: grayscale;
            }
            
            .container { 
                max-width: 1200px; 
                margin: 0 auto; 
                padding: 2rem 1rem; 
            }
            
            .header { 
                background: var(--surface);
                border: 1px solid var(--border);
                color: var(--text-primary); 
                padding: 2rem; 
                border-radius: var(--radius-xl); 
                margin-bottom: 2rem; 
                box-shadow: var(--shadow-sm);
                text-align: center;
            }
            
            .header h1 {
                font-size: 2rem;
                font-weight: 600;
                margin-bottom: 0.5rem;
                color: var(--text-primary);
                letter-spacing: -0.025em;
            }
            
            .header p {
                font-size: 1rem;
                color: var(--text-secondary);
                font-weight: 400;
            }
            
            .nav-container {
                background: var(--surface);
                border: 1px solid var(--border);
                border-radius: var(--radius-xl);
                padding: 0.5rem;
                margin-bottom: 2rem;
                box-shadow: var(--shadow-sm);
            }
            
            .tabs { 
                display: flex; 
                gap: 0.25rem;
                background: transparent;
                padding: 0;
                border-radius: 0;
            }
            
            .tab { 
                flex: 1;
                padding: 0.75rem 1rem; 
                cursor: pointer; 
                border: none; 
                background: transparent;
                border-radius: var(--radius-lg);
                font-weight: 500;
                font-size: 0.875rem;
                transition: var(--transition);
                color: var(--text-secondary);
                text-align: center;
                position: relative;
            }
            
            .tab:hover {
                background: var(--surface-tertiary);
                color: var(--text-primary);
            }
            
            .tab.active { 
                background: var(--primary); 
                color: white; 
                box-shadow: var(--shadow-sm);
            }
            
            .tab-content { 
                display: none; 
            }
            
            .tab-content.active { 
                display: block; 
                animation: fadeIn 0.3s;
            }
            
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }
            
            .card { 
                background: var(--surface);
                border: 1px solid var(--border);
                border-radius: var(--radius-xl); 
                box-shadow: var(--shadow-sm); 
                margin-bottom: 1.5rem; 
                overflow: hidden;
                transition: var(--transition);
            }
            
            .card:hover {
                box-shadow: var(--shadow-md);
                border-color: var(--border);
            }
            
            .card-header { 
                background: var(--surface); 
                color: var(--text-primary); 
                padding: 1.5rem; 
                border-bottom: 1px solid var(--border);
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            
            .card-header h2, .card-header h3 {
                font-weight: 600;
                font-size: 1.125rem;
                margin: 0;
                color: var(--text-primary);
            }
            
            .btn-sm {
                padding: 0.5rem 1rem;
                font-size: 0.8rem;
            }
            
            .card-body { 
                padding: 2rem; 
            }
            
            .form-row {
                display: grid; 
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); 
                gap: 1.5rem;
                margin-bottom: 1rem;
            }
            
            .section {
                background: var(--surface-secondary);
                border-radius: var(--radius-lg);
                padding: 1.5rem;
                margin-bottom: 1.5rem;
                border: 1px solid var(--border-light);
            }
            
            .section h3 {
                margin: 0 0 1rem 0;
                font-size: 1rem;
                font-weight: 600;
                color: var(--text-primary);
            }
            
            .form-actions {
                display: flex;
                gap: 1rem;
                justify-content: flex-start;
                padding-top: 1rem;
                border-top: 1px solid var(--border);
            }
            
            .loading-container {
                text-align: center;
                padding: 2rem;
                color: var(--gray);
            }
            
            .form-group { 
                margin-bottom: 1.5rem; 
            }
            
            .form-group label { 
                display: block; 
                margin-bottom: 0.5rem; 
                font-weight: 500;
                color: var(--text-primary);
                font-size: 0.875rem;
            }
            
            .form-control { 
                width: 100%; 
                padding: 0.75rem 1rem; 
                border: 1px solid var(--border); 
                border-radius: var(--radius-lg); 
                font-size: 0.875rem;
                transition: var(--transition);
                background: var(--surface);
                color: var(--text-primary);
            }
            
            .form-control:focus {
                outline: none;
                border-color: var(--primary);
                box-shadow: 0 0 0 3px rgb(37 99 235 / 0.1);
                background: var(--surface);
            }
            
            .form-control::placeholder {
                color: var(--text-muted);
            }
            
            .btn { 
                padding: 0.75rem 1rem; 
                border: none; 
                border-radius: var(--radius-lg); 
                cursor: pointer; 
                font-size: 0.875rem;
                font-weight: 500;
                transition: var(--transition);
                display: inline-flex;
                align-items: center;
                gap: 0.5rem;
                text-decoration: none;
                position: relative;
                overflow: hidden;
            }
            
            .btn:hover {
                transform: translateY(-1px);
                box-shadow: var(--shadow-md);
            }
            
            .btn:active {
                transform: translateY(0);
            }
            
            .btn-primary { 
                background: var(--primary); 
                color: white; 
            }
            
            .btn-primary:hover {
                background: var(--primary-dark);
            }
            
            .btn-success { 
                background: var(--success); 
                color: white; 
            }
            
            .btn-danger { 
                background: var(--danger); 
                color: white; 
            }
            
            .btn-warning { 
                background: var(--warning); 
                color: white; 
            }
            
            .btn-secondary {
                background: var(--surface);
                color: var(--text-primary);
                border: 1px solid var(--border);
            }
            
            .btn-secondary:hover {
                background: var(--surface-tertiary);
            }
            
            .user-list { 
                display: flex;
                flex-direction: column;
                gap: 1rem; 
            }
            
            .user-item { 
                border: 1px solid var(--border); 
                border-radius: var(--radius-xl); 
                background: var(--surface);
                transition: var(--transition);
                overflow: hidden;
            }
            
            .user-item:hover {
                border-color: var(--primary);
                box-shadow: var(--shadow-md);
            }
            
            .user-header {
                background: var(--surface);
                padding: 1rem 1.5rem;
                border-bottom: 1px solid var(--border);
                display: flex;
                justify-content: space-between;
                align-items: center;
                cursor: pointer;
            }
            
            .user-info {
                display: flex;
                flex-direction: column;
                gap: 0.25rem;
            }
            
            .user-email { 
                font-weight: 600; 
                color: var(--text-primary); 
                font-size: 1rem;
            }
            
            .user-name {
                color: var(--text-secondary);
                font-size: 0.875rem;
            }
            
            .user-actions {
                display: flex;
                gap: 0.5rem;
            }
            
            .btn-xs {
                padding: 0.25rem 0.75rem;
                font-size: 0.75rem;
            }
            
            .user-details { 
                padding: 1.5rem;
                display: none;
            }
            
            .user-details.show {
                display: block;
            }
            
            .config-section { 
                margin-bottom: 1rem; 
                padding: 1rem; 
                background: var(--surface-secondary); 
                border-radius: var(--radius-lg);
                border: 1px solid var(--border-light);
            }
            
            .config-title { 
                font-weight: 600; 
                margin-bottom: 0.75rem;
                display: flex;
                align-items: center;
                gap: 0.5rem;
                font-size: 0.875rem;
                color: var(--text-primary);
            }
            
            .config-row {
                display: flex;
                gap: 2rem;
                flex-wrap: wrap;
                margin-bottom: 0.5rem;
                font-size: 0.9rem;
            }
            
            .config-item {
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }
            
            .symbol-tags { 
                display: flex; 
                flex-wrap: wrap; 
                gap: 0.5rem; 
                margin-top: 0.5rem;
            }
            
            .symbol-tag { 
                background: var(--primary); 
                color: white;
                padding: 0.25rem 0.75rem; 
                border-radius: var(--radius-xl); 
                font-size: 0.75rem;
                font-weight: 500;
            }
            
            .status-enabled { 
                color: var(--success); 
                font-weight: 600;
            }
            
            .status-disabled { 
                color: var(--danger); 
                font-weight: 600;
            }
            
            .stats { 
                display: grid; 
                grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); 
                gap: 1.5rem; 
                margin-bottom: 2rem; 
            }
            
            .stat-card { 
                background: var(--surface); 
                color: var(--text-primary); 
                padding: 1.5rem; 
                border-radius: var(--radius-xl); 
                text-align: center;
                box-shadow: var(--shadow-sm);
                transition: var(--transition);
                border: 1px solid var(--border);
            }
            
            .stat-card:hover {
                transform: translateY(-2px);
                box-shadow: var(--shadow-md);
                border-color: var(--primary);
            }
            
            .stat-number { 
                font-size: 2.5rem; 
                font-weight: 700;
                margin-bottom: 0.5rem;
                color: var(--primary);
            }
            
            .stat-label { 
                font-size: 0.875rem; 
                color: var(--text-secondary);
                font-weight: 500;
            }
            
            .checkbox-wrapper {
                display: flex;
                align-items: center;
                gap: 0.5rem;
                margin-top: 0.5rem;
            }
            
            .checkbox-wrapper input[type="checkbox"] {
                width: 1.25rem;
                height: 1.25rem;
                accent-color: var(--primary);
            }
            
            .action-buttons {
                display: flex;
                gap: 0.75rem;
                margin-top: 1.5rem;
                flex-wrap: wrap;
            }
            
            .user-meta {
                margin-top: 1rem;
                padding-top: 1rem;
                border-top: 1px solid var(--border);
                font-size: 0.75rem;
                color: var(--gray);
            }
            
            .loading {
                display: inline-block;
                width: 1rem;
                height: 1rem;
                border: 2px solid transparent;
                border-top: 2px solid currentColor;
                border-radius: 50%;
                animation: spin 1s linear infinite;
            }
            
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            /* 模态弹窗样式 */
            .modal {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.4);
                backdrop-filter: blur(8px);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 1000;
                animation: modalFadeIn 0.2s ease-out;
            }
            
            @keyframes modalFadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }
            
            .modal-content {
                background: var(--surface);
                border-radius: var(--radius-2xl);
                box-shadow: var(--shadow-xl);
                max-width: 600px;
                width: 90%;
                max-height: 90vh;
                overflow-y: auto;
                transform: scale(0.95);
                opacity: 0;
                transition: var(--transition-slow);
                border: 1px solid var(--border);
            }
            
            .modal-header {
                background: var(--surface);
                color: var(--text-primary);
                padding: 1.5rem 2rem;
                border-bottom: 1px solid var(--border);
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            
            .modal-header h2 {
                margin: 0;
                font-size: 1.125rem;
                font-weight: 600;
                color: var(--text-primary);
            }
            
            .modal-close {
                background: var(--surface-tertiary);
                border: none;
                color: var(--text-secondary);
                font-size: 1.25rem;
                cursor: pointer;
                padding: 0.5rem;
                border-radius: var(--radius-lg);
                width: 2rem;
                height: 2rem;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: var(--transition);
            }
            
            .modal-close:hover {
                background: var(--border);
                color: var(--text-primary);
            }
            
            .modal-body {
                padding: 1.5rem 2rem 2rem;
            }
            
            /* 点击背景关闭模态窗口 */
            .modal-content:focus {
                outline: none;
            }
            
            @media (max-width: 768px) {
                .container {
                    padding: 1rem;
                }
                
                .header h1 {
                    font-size: 2rem;
                }
                
                .form-grid {
                    grid-template-columns: 1fr;
                }
                
                .user-list {
                    grid-template-columns: 1fr;
                }
                
                .stats {
                    grid-template-columns: repeat(2, 1fr);
                }
                
                .modal-content {
                    width: 95%;
                    max-height: 95vh;
                    border-radius: var(--radius-xl);
                }
                
                .modal-header {
                    padding: 1rem 1.5rem;
                }
                
                .modal-body {
                    padding: 1rem 1.5rem 1.5rem;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>RagoAlert</h1>
                <p>智能股票监控配置管理</p>
            </div>
            
            <div class="nav-container">
                <div class="tabs">
                    <button class="tab active" onclick="showTab('users')">用户管理</button>
                    <button class="tab" onclick="showTab('system')">系统配置</button>
                    <button class="tab" onclick="showTab('stats')">统计信息</button>
                </div>
            </div>
            
            <div id="users-tab" class="tab-content active">
                <!-- 用户列表 -->
                <div class="card">
                    <div class="card-header">
                        <h2>用户列表</h2>
                        <button class="btn btn-primary btn-sm" onclick="showUserModal()">
                            添加用户
                        </button>
                    </div>
                    <div class="card-body">
                        <div id="usersList" class="user-list">
                            <div class="loading-container">
                                <div class="loading"></div>
                                <p>正在加载用户数据...</p>
                            </div>
                        </div>
                    </div>
                </div>
                
            </div>
            
            <div id="system-tab" class="tab-content">
                <div class="card">
                    <div class="card-header">
                        <h2>系统配置</h2>
                        <button class="btn btn-primary btn-sm" onclick="showSystemModal()">
                            编辑配置
                        </button>
                    </div>
                    <div class="card-body">
                        <div id="systemConfigDisplay">
                            <div class="loading-container">
                                <div class="loading"></div>
                                <p>正在加载系统配置...</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div id="stats-tab" class="tab-content">
                <div id="statsContainer">
                    <!-- 统计信息将在这里动态加载 -->
                </div>
            </div>
        </div>
        
        <!-- 模态弹窗 -->
        <div id="userModal" class="modal" style="display: none;" onclick="modalBackgroundClick(event)">
            <div class="modal-content" onclick="event.stopPropagation()">
                <div class="modal-header">
                    <h2 id="modalTitle">添加用户</h2>
                    <button class="modal-close" onclick="hideUserModal()">✕</button>
                </div>
                <div class="modal-body">
                    <form id="userForm">
                        <div class="form-row">
                            <div class="form-group">
                                <label>📧 邮箱地址</label>
                                <input type="email" class="form-control" id="userEmail" required placeholder="user@example.com">
                            </div>
                            <div class="form-group">
                                <label>👤 用户名称</label>
                                <input type="text" class="form-control" id="userName" placeholder="请输入用户名">
                            </div>
                        </div>
                        
                        <div class="section">
                            <h3>📉 波动监控设置</h3>
                            <div class="form-row">
                                <div class="form-group">
                                    <label>波动阈值 (%)</label>
                                    <input type="number" class="form-control" id="fluctuationThreshold" value="3" step="0.1" min="0.1" max="50">
                                </div>
                                <div class="form-group">
                                    <label>通知间隔 (分钟)</label>
                                    <input type="number" class="form-control" id="notificationInterval" value="5" min="1" max="60">
                                </div>
                                <div class="form-group">
                                    <div class="checkbox-wrapper">
                                        <input type="checkbox" id="fluctuationEnabled" checked>
                                        <label for="fluctuationEnabled">启用波动监控</label>
                                    </div>
                                </div>
                            </div>
                            <div class="form-group">
                                <label>监控股票 (逗号分隔)</label>
                                <textarea class="form-control" id="fluctuationSymbols" rows="3" placeholder="AAPL,TSLA,NVDA,MSFT,GOOGL">AAPL,TSLA,NVDA,MSFT,GOOGL</textarea>
                            </div>
                        </div>
                        
                        <div class="section">
                            <h3>📊 趋势监控设置</h3>
                            <div class="form-row">
                                <div class="form-group">
                                    <div class="checkbox-wrapper">
                                        <input type="checkbox" id="trendEnabled" checked>
                                        <label for="trendEnabled">启用趋势监控</label>
                                    </div>
                                </div>
                                <div class="form-group">
                                    <div class="checkbox-wrapper">
                                        <input type="checkbox" id="preMarketNotification" checked>
                                        <label for="preMarketNotification">盘前通知</label>
                                    </div>
                                </div>
                                <div class="form-group">
                                    <div class="checkbox-wrapper">
                                        <input type="checkbox" id="postMarketNotification" checked>
                                        <label for="postMarketNotification">盘后通知</label>
                                    </div>
                                </div>
                            </div>
                            <div class="form-group">
                                <label>监控股票 (逗号分隔)</label>
                                <textarea class="form-control" id="trendSymbols" rows="3" placeholder="AAPL,TSLA,NVDA,MSFT,GOOGL">AAPL,TSLA,NVDA,MSFT,GOOGL</textarea>
                            </div>
                        </div>
                        
                        <div class="form-actions">
                            <button type="submit" class="btn btn-primary">
                                💾 保存
                            </button>
                            <button type="button" class="btn btn-secondary" onclick="hideUserModal()">
                                取消
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
        
        <!-- 系统配置模态弹窗 -->
        <div id="systemModal" class="modal" style="display: none;" onclick="systemModalBackgroundClick(event)">
            <div class="modal-content" onclick="event.stopPropagation()">
                <div class="modal-header">
                    <h2>系统配置</h2>
                    <button class="modal-close" onclick="hideSystemModal()">✕</button>
                </div>
                <div class="modal-body">
                    <form id="systemForm">
                        <div class="form-row">
                            <div class="form-group">
                                <label>📧 SMTP服务器</label>
                                <input type="text" class="form-control" id="smtpServer" placeholder="smtp.gmail.com">
                            </div>
                            <div class="form-group">
                                <label>🔌 SMTP端口</label>
                                <input type="number" class="form-control" id="smtpPort" placeholder="465" min="1" max="65535">
                            </div>
                        </div>
                        
                        <div class="form-row">
                            <div class="form-group">
                                <label>📨 发送邮箱</label>
                                <input type="email" class="form-control" id="senderEmail" placeholder="your-email@gmail.com">
                            </div>
                            <div class="form-group">
                                <label>🔑 邮箱密码</label>
                                <input type="password" class="form-control" id="senderPassword" placeholder="请输入应用专用密码">
                            </div>
                        </div>
                        
                        <div class="form-row">
                            <div class="form-group">
                                <label>🌐 Web端口</label>
                                <input type="number" class="form-control" id="webPort" placeholder="8080" min="1" max="65535">
                            </div>
                            <div class="form-group">
                                <label>📋 日志级别</label>
                                <select class="form-control" id="logLevel">
                                    <option value="DEBUG">🔍 DEBUG (详细调试)</option>
                                    <option value="INFO">ℹ️ INFO (一般信息)</option>
                                    <option value="WARNING">⚠️ WARNING (警告)</option>
                                    <option value="ERROR">❌ ERROR (错误)</option>
                                </select>
                            </div>
                        </div>
                        
                        <div class="form-actions">
                            <button type="submit" class="btn btn-primary">
                                💾 保存配置
                            </button>
                            <button type="button" class="btn btn-secondary" onclick="hideSystemModal()">
                                取消
                            </button>
                            <button type="button" class="btn btn-warning" onclick="loadSystemConfig()">
                                🔄 重新加载
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
        
        <script>
            // 全局变量
            let currentEditingUser = null;
            
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
                
                // 重置表单显示状态
                if (tabName === 'users') {
                    hideUserModal();
                    refreshUsers();
                } else if (tabName === 'system') {
                    hideSystemModal();
                    displaySystemConfig();
                } else if (tabName === 'stats') {
                    loadStats();
                }
            }
            
            // 显示用户模态窗口
            function showUserModal() {
                document.getElementById('userModal').style.display = 'flex';
                document.getElementById('modalTitle').textContent = '添加用户';
                
                // 重置表单
                document.getElementById('userForm').reset();
                document.getElementById('fluctuationThreshold').value = '3';
                document.getElementById('notificationInterval').value = '5';
                document.getElementById('fluctuationSymbols').value = 'AAPL,TSLA,NVDA,MSFT,GOOGL';
                document.getElementById('trendSymbols').value = 'AAPL,TSLA,NVDA,MSFT,GOOGL';
                document.getElementById('fluctuationEnabled').checked = true;
                document.getElementById('trendEnabled').checked = true;
                document.getElementById('preMarketNotification').checked = true;
                document.getElementById('postMarketNotification').checked = true;
                document.getElementById('userEmail').readOnly = false;
                
                currentEditingUser = null;
                
                // 添加显示动画
                setTimeout(() => {
                    document.querySelector('.modal-content').style.transform = 'scale(1)';
                    document.querySelector('.modal-content').style.opacity = '1';
                }, 10);
            }
            
            // 隐藏用户模态窗口
            function hideUserModal() {
                document.querySelector('.modal-content').style.transform = 'scale(0.8)';
                document.querySelector('.modal-content').style.opacity = '0';
                
                setTimeout(() => {
                    document.getElementById('userModal').style.display = 'none';
                }, 200);
                
                currentEditingUser = null;
            }
            
            // 点击背景关闭模态窗口
            function modalBackgroundClick(event) {
                if (event.target === event.currentTarget) {
                    hideUserModal();
                }
            }
            
            // ESC键关闭模态窗口
            document.addEventListener('keydown', function(event) {
                if (event.key === 'Escape') {
                    if (document.getElementById('userModal').style.display === 'flex') {
                        hideUserModal();
                    } else if (document.getElementById('systemModal').style.display === 'flex') {
                        hideSystemModal();
                    }
                }
            });
            
            // 显示系统配置模态窗口
            function showSystemModal() {
                document.getElementById('systemModal').style.display = 'flex';
                
                // 加载系统配置数据
                loadSystemConfig();
                
                // 添加显示动画
                setTimeout(() => {
                    document.querySelectorAll('#systemModal .modal-content')[0].style.transform = 'scale(1)';
                    document.querySelectorAll('#systemModal .modal-content')[0].style.opacity = '1';
                }, 10);
            }
            
            // 隐藏系统配置模态窗口
            function hideSystemModal() {
                const modalContent = document.querySelectorAll('#systemModal .modal-content')[0];
                modalContent.style.transform = 'scale(0.8)';
                modalContent.style.opacity = '0';
                
                setTimeout(() => {
                    document.getElementById('systemModal').style.display = 'none';
                }, 200);
            }
            
            // 系统配置模态弹窗背景点击
            function systemModalBackgroundClick(event) {
                if (event.target === event.currentTarget) {
                    hideSystemModal();
                }
            }
            
            // 切换用户详情显示
            function toggleUserDetails(email) {
                const details = document.getElementById('user-details-' + btoa(email));
                if (details) {
                    details.classList.toggle('show');
                }
            }
            
            // 显示系统配置信息
            async function displaySystemConfig() {
                try {
                    const config = await apiCall('/api/system');
                    const display = document.getElementById('systemConfigDisplay');
                    
                    display.innerHTML = `
                        <div class="config-section">
                            <div class="config-title">📧 邮件服务配置</div>
                            <div class="config-row">
                                <div class="config-item">
                                    <span>SMTP服务器:</span> <strong>${config.smtp_server}</strong>
                                </div>
                                <div class="config-item">
                                    <span>端口:</span> <strong>${config.smtp_port}</strong>
                                </div>
                            </div>
                            <div class="config-row">
                                <div class="config-item">
                                    <span>发送邮箱:</span> <strong>${config.sender_email || '未配置'}</strong>
                                </div>
                                <div class="config-item">
                                    <span>密码:</span> <strong>${config.sender_password ? '已设置' : '未设置'}</strong>
                                </div>
                            </div>
                        </div>
                        
                        <div class="config-section">
                            <div class="config-title">🌐 Web服务配置</div>
                            <div class="config-row">
                                <div class="config-item">
                                    <span>Web端口:</span> <strong>${config.web_port}</strong>
                                </div>
                                <div class="config-item">
                                    <span>日志级别:</span> <strong>${config.log_level}</strong>
                                </div>
                            </div>
                        </div>
                    `;
                } catch (error) {
                    console.error('加载系统配置显示失败:', error);
                    document.getElementById('systemConfigDisplay').innerHTML = 
                        '<p style="color: var(--danger);">❌ 加载系统配置失败</p>';
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
                    
                    usersList.innerHTML = Object.entries(users).map(([email, user]) => {
                        const emailId = btoa(email); // Base64编码用于ID
                        return `
                        <div class="user-item">
                            <div class="user-header" onclick="toggleUserDetails('${email}')">
                                <div class="user-info">
                                    <div class="user-email">${email}</div>
                                    <div class="user-name">👤 ${user.name || '未设置姓名'}</div>
                                </div>
                                <div class="user-actions" onclick="event.stopPropagation()">
                                    <button class="btn btn-warning btn-xs" onclick="editUser('${email}')">
                                        ✏️ 编辑
                                    </button>
                                    <button class="btn btn-danger btn-xs" onclick="deleteUser('${email}')">
                                        🗑️ 删除
                                    </button>
                                </div>
                            </div>
                            
                            <div id="user-details-${emailId}" class="user-details">
                                <div class="config-section">
                                    <div class="config-title">
                                        📉 波动监控 
                                        <span class="${user.fluctuation.enabled ? 'status-enabled' : 'status-disabled'}">
                                            ${user.fluctuation.enabled ? '✅ 已启用' : '❌ 已禁用'}
                                        </span>
                                    </div>
                                    <div class="config-row">
                                        <div class="config-item">
                                            <span>阈值:</span> <strong>${user.fluctuation.threshold_percent}%</strong>
                                        </div>
                                        <div class="config-item">
                                            <span>间隔:</span> <strong>${user.fluctuation.notification_interval_minutes}分钟</strong>
                                        </div>
                                    </div>
                                    <div class="symbol-tags">
                                        ${user.fluctuation.symbols.map(s => `<span class="symbol-tag">${s}</span>`).join('')}
                                    </div>
                                </div>
                                
                                <div class="config-section">
                                    <div class="config-title">
                                        📊 趋势监控 
                                        <span class="${user.trend.enabled ? 'status-enabled' : 'status-disabled'}">
                                            ${user.trend.enabled ? '✅ 已启用' : '❌ 已禁用'}
                                        </span>
                                    </div>
                                    <div class="config-row">
                                        <div class="config-item">
                                            <span>盘前通知:</span> ${user.trend.pre_market_notification ? '✅' : '❌'}
                                        </div>
                                        <div class="config-item">
                                            <span>盘后通知:</span> ${user.trend.post_market_notification ? '✅' : '❌'}
                                        </div>
                                    </div>
                                    <div class="symbol-tags">
                                        ${user.trend.symbols.map(s => `<span class="symbol-tag">${s}</span>`).join('')}
                                    </div>
                                </div>
                                
                                <div style="font-size: 0.8rem; color: var(--gray); margin-top: 1rem; padding-top: 1rem; border-top: 1px solid var(--border);">
                                    创建: ${new Date(user.created_at).toLocaleString()} | 
                                    更新: ${new Date(user.updated_at).toLocaleString()}
                                </div>
                            </div>
                        </div>
                    `;
                    }).join('');
                } catch (error) {
                    console.error('加载用户列表失败:', error);
                }
            }
            
            // 添加/更新用户
            document.getElementById('userForm').addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const userData = {
                    email: document.getElementById('userEmail').value,
                    name: document.getElementById('userName').value,
                    fluctuation: {
                        threshold_percent: parseFloat(document.getElementById('fluctuationThreshold').value),
                        symbols: document.getElementById('fluctuationSymbols').value.split(',').map(s => s.trim()).filter(s => s),
                        notification_interval_minutes: parseInt(document.getElementById('notificationInterval').value),
                        enabled: document.getElementById('fluctuationEnabled').checked
                    },
                    trend: {
                        enabled: document.getElementById('trendEnabled').checked,
                        symbols: document.getElementById('trendSymbols').value.split(',').map(s => s.trim()).filter(s => s),
                        pre_market_notification: document.getElementById('preMarketNotification').checked,
                        post_market_notification: document.getElementById('postMarketNotification').checked
                    }
                };
                
                try {
                    if (currentEditingUser) {
                        // 更新用户
                        await apiCall(`/api/users/${encodeURIComponent(currentEditingUser)}`, {
                            method: 'PUT',
                            body: JSON.stringify({
                                name: userData.name,
                                fluctuation: userData.fluctuation,
                                trend: userData.trend
                            })
                        });
                        
                        showNotification('用户配置更新成功!', 'success');
                    } else {
                        // 添加新用户
                        await apiCall('/api/users', {
                            method: 'POST',
                            body: JSON.stringify(userData)
                        });
                        
                        showNotification('用户添加成功!', 'success');
                    }
                    
                    document.getElementById('userForm').reset();
                    hideUserModal();
                    refreshUsers();
                } catch (error) {
                    console.error('操作失败:', error);
                    showNotification(error.message, 'error');
                }
            });
            
            // 删除用户
            async function deleteUser(email) {
                if (!confirm(`⚠️ 确定要删除用户 ${email} 吗？\n\n此操作不可撤销！`)) return;
                
                try {
                    await apiCall(`/api/users/${encodeURIComponent(email)}`, {
                        method: 'DELETE'
                    });
                    
                    showNotification('用户删除成功!', 'success');
                    refreshUsers();
                } catch (error) {
                    console.error('删除用户失败:', error);
                    showNotification('删除用户失败: ' + error.message, 'error');
                }
            }
            
            // 编辑用户
            async function editUser(email) {
                try {
                    const user = await apiCall(`/api/users/${encodeURIComponent(email)}`);
                    
                    // 填充表单
                    document.getElementById('userEmail').value = user.email;
                    document.getElementById('userEmail').readOnly = true; // 邮箱不允许修改
                    document.getElementById('userName').value = user.name || '';
                    document.getElementById('fluctuationThreshold').value = user.fluctuation.threshold_percent;
                    document.getElementById('notificationInterval').value = user.fluctuation.notification_interval_minutes;
                    document.getElementById('fluctuationSymbols').value = user.fluctuation.symbols.join(',');
                    document.getElementById('trendSymbols').value = user.trend.symbols.join(',');
                    document.getElementById('fluctuationEnabled').checked = user.fluctuation.enabled;
                    document.getElementById('trendEnabled').checked = user.trend.enabled;
                    document.getElementById('preMarketNotification').checked = user.trend.pre_market_notification;
                    document.getElementById('postMarketNotification').checked = user.trend.post_market_notification;
                    
                    // 设置编辑模式
                    currentEditingUser = email;
                    
                    // 显示模态窗口
                    document.getElementById('userModal').style.display = 'flex';
                    
                    // 更新标题
                    document.getElementById('modalTitle').textContent = '编辑用户: ' + email;
                    
                    // 添加显示动画
                    setTimeout(() => {
                        document.querySelector('.modal-content').style.transform = 'scale(1)';
                        document.querySelector('.modal-content').style.opacity = '1';
                    }, 10);
                    
                } catch (error) {
                    console.error('加载用户数据失败:', error);
                    showNotification('加载用户数据失败: ' + error.message, 'error');
                }
            }
            
            // 通知函数
            function showNotification(message, type = 'info') {
                // 创建通知元素
                const notification = document.createElement('div');
                notification.style.cssText = `
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    padding: 1rem 1.5rem;
                    border-radius: var(--radius);
                    color: white;
                    font-weight: 500;
                    z-index: 1000;
                    box-shadow: var(--shadow-lg);
                    transform: translateX(100%);
                    transition: var(--transition);
                `;
                
                // 根据类型设置颜色
                switch (type) {
                    case 'success':
                        notification.style.background = 'var(--success)';
                        notification.innerHTML = `✅ ${message}`;
                        break;
                    case 'error':
                        notification.style.background = 'var(--danger)';
                        notification.innerHTML = `❌ ${message}`;
                        break;
                    default:
                        notification.style.background = 'var(--info)';
                        notification.innerHTML = `ℹ️ ${message}`;
                }
                
                document.body.appendChild(notification);
                
                // 显示动画
                setTimeout(() => {
                    notification.style.transform = 'translateX(0)';
                }, 100);
                
                // 自动隐藏
                setTimeout(() => {
                    notification.style.transform = 'translateX(100%)';
                    setTimeout(() => {
                        document.body.removeChild(notification);
                    }, 300);
                }, 3000);
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
                    
                    showNotification('系统配置保存成功!', 'success');
                    hideSystemModal();
                    displaySystemConfig();
                } catch (error) {
                    console.error('保存系统配置失败:', error);
                    showNotification('保存系统配置失败: ' + error.message, 'error');
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
                displaySystemConfig();
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