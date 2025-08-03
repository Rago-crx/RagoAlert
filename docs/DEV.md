# RagoAlert 开发指南

这是RagoAlert的快速开发和测试指南，帮助你在本地Mac或Windows系统上快速验证修改效果。

## 🚀 快速开始

### 必要步骤

```bash
# 1. 安装依赖（必需）
pip install -r requirements.txt

# 2. 验证环境（推荐）
python tests/run_tests.py --deps --syntax
```

### 可选步骤

```bash
# 生成测试数据（可选）
# 仅在需要离线测试或网络受限时运行
python tests/test_data_generator.py

# 检查开发环境状态
python tests/dev_start.py --status
```

> **💡 说明**: 测试数据生成器创建模拟的股价数据用于离线测试。在有网络连接时，系统会自动使用真实的Yahoo Finance数据，因此这不是必需步骤。

## 🧪 测试系统

### 快速测试（推荐用于日常开发）

```bash
# 运行核心功能验证
python tests/run_tests.py --quick
```

### 完整测试（代码提交前运行）

```bash
# 运行所有测试
python tests/run_tests.py --all
```

### 特定测试

```bash
# 只检查代码质量
python tests/run_tests.py --deps --syntax

# 只运行单元测试
python tests/run_tests.py --unit

# 只检查配置系统
python tests/run_tests.py --config

# 只运行性能测试
python tests/run_tests.py --perf
```

## 🏃‍♂️ 启动开发环境

```bash
# 启动完整开发环境（Web界面 + 监控服务）
python tests/dev_start.py --dev

# 只启动Web管理界面
python tests/dev_start.py --web

# 只启动监控服务
python tests/dev_start.py --monitor
```

访问地址: http://localhost:8080

## 📋 典型开发工作流

### 日常迭代开发
1. **修改代码** - 编辑任何Python文件
2. **快速验证** - `python tests/run_tests.py --quick`
3. **本地运行** - `python tests/dev_start.py --dev`
4. **手动测试** - 访问 http://localhost:8080

### 代码提交前
1. **完整测试** - `python tests/run_tests.py --all`
2. **确保通过** - 所有测试项应该显示 ✅
3. **提交代码** - git commit & push

---

## 📖 详细说明

### 🔍 测试命令详解

#### `--quick` 快速验证测试
**目的**: 快速验证核心功能是否正常，适合日常开发使用  
**耗时**: 约5秒  
**测试项目**:
- ✅ **配置系统** - 验证YAML配置加载、股票池展开、用户管理
- ✅ **数据获取** - 测试Yahoo Finance API连接、实时价格、历史数据
- ✅ **趋势分析** - 验证技术指标计算（EMA、RSI、MACD、ADX）
- ✅ **波动分析** - 测试价格变化检测和阈值触发
- ✅ **用户监控器** - 验证单用户监控器创建和配置
- ✅ **Web API** - 测试REST接口响应和数据交换
- ✅ **集成测试** - 验证多用户监控管理器协调
- ✅ **用户管理** - 测试用户创建、更新、删除功能

#### `--all` 完整测试套件
**目的**: 全面验证系统质量，代码提交前必须运行  
**耗时**: 约15-30秒  
**包含内容**:
- 🔍 **依赖检查** - 验证所有Python包是否正确安装
- 📝 **语法检查** - 检查所有Python文件语法正确性
- ⚙️ **配置测试** - 验证配置文件存在性和加载正确性
- 🧪 **单元测试** - 运行15个单元测试用例
- ⚡ **快速验证** - 运行8项集成测试
- 🚀 **性能测试** - 验证响应时间和系统性能

#### `--unit` 单元测试
**目的**: 测试单个组件的功能正确性  
**耗时**: 约3秒  
**测试模块**:
- **配置管理器** (5个测试)
  - 默认配置创建
  - 用户配置CRUD操作
  - 股票池展开功能
  - 趋势分析配置
  - 配置持久化
- **波动监控器** (5个测试)
  - 数据不足处理
  - 波动触发检测
  - 通知间隔限制
  - 邮件通知发送
  - 配置动态更新
- **趋势分析** (5个测试)
  - 上涨趋势识别
  - 下跌趋势识别
  - 数据不足处理
  - 自定义配置参数
  - 直接配置传递

#### `--deps` 依赖检查
**目的**: 确保开发环境依赖完整  
**检查内容**:
- ✅ yaml - YAML配置文件解析
- ✅ fastapi - Web API框架
- ✅ uvicorn - ASGI服务器
- ✅ pandas - 数据处理
- ✅ numpy - 数值计算
- ✅ yfinance - 股票数据获取
- ✅ pandas_ta - 技术指标计算
- ✅ requests - HTTP请求

#### `--syntax` 语法检查
**目的**: 确保代码语法正确性  
**检查范围**: 项目中所有.py文件（约23个文件）  
**检查内容**:
- Python语法错误
- 导入语句错误
- 缩进和格式问题

#### `--config` 配置测试
**目的**: 验证配置系统完整性  
**测试内容**:
- 配置模板文件存在性
- 配置管理器导入
- 系统配置加载
- 股票池配置验证

#### `--perf` 性能测试
**目的**: 验证系统响应性能  
**性能基准**:
- 配置加载 < 0.5秒
- 价格获取 < 3秒
- 趋势分析 < 2秒
- 总体验证 < 10秒

### 🛠️ 开发环境命令详解

#### `--dev` 完整开发环境
**启动内容**:
- Web管理界面 (端口8080)
- 多用户监控服务
- 实时配置监听
- 日志输出

**适用场景**: 完整功能测试、用户界面开发

#### `--web` 仅Web界面
**启动内容**:
- FastAPI Web服务
- 用户管理界面
- 配置管理API

**适用场景**: 前端开发、API测试

#### `--monitor` 仅监控服务
**启动内容**:
- 多用户监控管理器
- 股票价格监控
- 趋势分析服务
- 邮件通知

**适用场景**: 后端逻辑测试、监控功能验证

### 📁 重要文件说明

| 文件/目录 | 用途 | 是否必需 |
|-----------|------|----------|
| `config/config_dev.yaml` | 开发环境配置（宽松参数） | 否* |
| `config/config_template.yaml` | 生产配置模板 | 是 |
| `tests/run_tests.py` | 测试运行器 | 是 |
| `tests/quick_test.py` | 快速验证脚本 | 是 |
| `tests/test_data_generator.py` | 测试数据生成器 | 否 |
| `tests/dev_start.py` | 开发环境管理 | 否 |
| `test_data_cache/` | 模拟测试数据缓存 | 否 |

*自动生成，首次运行时会创建

### 🔧 高级用法

#### 组合命令
```bash
# 检查环境 + 快速测试
python tests/run_tests.py --deps --syntax --quick

# 只检查代码质量
python tests/run_tests.py --deps --syntax --config

# 性能基准测试
python tests/run_tests.py --perf --config
```

#### 环境变量
```bash
# 手动指定配置启动
RAGOALERT_CONFIG=~/.ragoalert-dev/users_config.yaml python main.py

# 开启调试日志
RAGOALERT_LOG_LEVEL=DEBUG python tests/dev_start.py --dev
```

### 📊 性能基准

开发环境性能预期:
- **配置加载**: < 0.5秒
- **价格获取**: < 3秒 (依赖网络)
- **趋势分析**: < 2秒
- **Web API响应**: < 1秒
- **完整验证**: < 10秒

### ⚡ 快速问题排查

#### 测试失败？
1. **检查依赖**: `python tests/run_tests.py --deps`
2. **检查语法**: `python tests/run_tests.py --syntax`
3. **检查配置**: `python tests/run_tests.py --config`
4. **重新安装**: `pip install -r requirements.txt`

#### 无法获取数据？
1. **检查网络连接**
2. **生成离线数据**: `python tests/test_data_generator.py`
3. **使用模拟数据**: 设置 `RAGOALERT_USE_MOCK_DATA=true`

#### 配置问题？
1. **检查文件存在**: `ls config/`
2. **验证YAML语法**: `python -c "import yaml; yaml.safe_load(open('config/config_template.yaml'))"`
3. **重新生成**: `python tests/test_data_generator.py`

### 📈 开发最佳实践

1. **每次修改后**: 运行 `python tests/run_tests.py --quick`
2. **提交代码前**: 运行 `python tests/run_tests.py --all`
3. **性能监控**: 定期运行 `python tests/run_tests.py --perf`
4. **代码质量**: 确保语法检查100%通过

---

💡 **提示**: 快速验证命令 `--quick` 可以在几秒钟内发现大部分问题，建议作为日常开发的标准流程。