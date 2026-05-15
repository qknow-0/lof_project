# LOF 实时数据查询系统

前后端分离项目，展示 LOF 基金的实时交易价格、溢价率和申购限额。

## 技术栈

| 端 | 技术 |
|---|---|
| 前端 | Vue 3 + Vite + Element Plus + Axios |
| 后端 | FastAPI + Uvicorn + akshare + pandas |

---

## 目录结构

```
lof_project/
├── start.sh                    # 一键启动脚本
├── back/                       # 后端服务
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py             # FastAPI 应用入口
│   │   ├── cache.py            # 缓存管理
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   └── lof.py          # LOF 接口控制器
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   └── fetcher.py      # 数据获取服务
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── formatters.py   # 格式化工具
│   ├── run.py                  # uvicorn 启动入口
│   └── requirements.txt
├── front/                      # 前端项目
│   └── vite-project/
│       ├── package.json
│       └── src/
└── README.md
```

---

## 快速启动（推荐）

> 一键同时启动前后端，自动切换 Node 版本。

```bash
./start.sh
```

脚本会自动完成：

1. 激活后端 Python 虚拟环境，启动 FastAPI（`http://localhost:8000`）
2. 通过 `nvm use` 切换到 `.nvmrc` 指定的 Node 版本，启动 Vite 开发服务器（`http://localhost:5173`）
3. 按 `Ctrl+C` 同时停止所有服务

---

## 一、后端服务（手动启动）

### 前置要求

- Python 3.10+（[下载地址](https://www.python.org/downloads/)）

### 1. 安装依赖

```bash
cd back

# 创建虚拟环境（推荐）
python -m venv venv

# 激活虚拟环境
# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 启动服务

```bash
# 确保在 back 目录且虚拟环境已激活
source venv/bin/activate

uvicorn app.main:app --reload --port 8000
```

- `app.main:app` — `app/main.py` 中的 `app` 实例
- `--reload` — 开发模式，代码修改自动重启
- `--port 8000` — 服务端口

> 也可使用 `python run.py` 启动（已内置 reload + 0.0.0.0 配置）。

### 3. 验证

- API 文档：[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- LOF 数据接口：[http://127.0.0.1:8000/api/lof](http://127.0.0.1:8000/api/lof)

---

## 二、前端服务（手动启动）

> **前置要求**：电脑上需安装 [nvm](https://github.com/nvm-sh/nvm)（Node 版本管理工具）。

### 1. 切换 Node 版本

前端项目通过 `.nvmrc` 文件锁定 Node 版本（当前为 `v22.21.1`）。

**macOS / Linux：**

```bash
cd front/vite-project

# 自动读取 .nvmrc 中的版本并切换
nvm use

# 如果该版本未安装，先安装再切换
nvm install
nvm use
```

**Windows：**

Windows 版 nvm 不支持自动读取 `.nvmrc`，需显式指定版本号：

```bash
cd front/vite-project

nvm install v22.21.1
nvm use v22.21.1
```

### 2. 安装依赖

```bash
npm install
```

### 3. 启动服务

```bash
npm run dev
```

默认运行在 [http://localhost:5173](http://localhost:5173)

### 3. 构建生产包

```bash
npm run build
```

---

## 三、接口说明

完整的 API 文档可在启动后端后访问：[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### GET `/api/lof`

获取全量 LOF 实时数据（交易价、净值、溢价率、限额等）。

**返回字段：**

| 字段 | 类型 | 说明 |
|---|---|---|
| `fundCode` | string | 基金代码 |
| `fundName` | string | 基金名称 |
| `tradePrice` | number | 最新交易价 |
| `increaseRate` | number | 涨跌幅（%）|
| `netValue` | number | 最新净值/万份收益 |
| `estimateValue` | number | 实时估算净值 |
| `premiumRate` | number | 静态溢价率（%），基于最新收盘净值 |
| `estimatePremiumRate` | number | 估算溢价率（%），基于实时估算净值 |
| `purchaseLimit` | string | 日申购限额（格式化后） |
| `purchaseStatus` | string | 申购状态 |
| `fundSize` | string | 总市值（格式化后） |
| `volume` | number | 成交量（手） |
| `turnover` | string | 成交额（格式化后） |

**限额显示规则：**
- `不限` — 日限额 ≥ 1 亿
- `-` — 日限额为 0 或空值
- `xx元/日` — 日限额 < 1 万
- `xx万/日` — 日限额 ≥ 1 万

### GET `/api/lof/history`

获取单只 LOF 基金的历史数据（价格、净值、溢价率、成交额、场内份额）。

**请求参数：**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `fund_code` | string | 是 | 基金代码，如 `161725` |
| `fund_name` | string | 否 | 基金名称 |

**返回字段：**

| 字段 | 类型 | 说明 |
|---|---|---|
| `date` | string | 交易日期（YYYY-MM-DD） |
| `price` | number | 当日收盘价 |
| `navDate` | string | 净值对应日期（上一交易日） |
| `nav` | number | 基金净值 |
| `premiumRate` | number | 溢价率（%） |
| `turnover` | number | 成交额（万元） |
| `shareVolume` | number | 场内份额（万份） |
| `changeAmount` | number | 场内份额变化量（万份） |
| `changePct` | number | 场内份额变化率（%） |

---

## 四、常见问题

### 1. 后端端口被占用

```bash
# 查找占用 8000 端口的进程并结束
lsof -ti:8000 | xargs kill -9
```

### 2. 前端请求后端接口失败

确保后端服务已启动，且 CORS 配置正确（默认允许所有来源）。
