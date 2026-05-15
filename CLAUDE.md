# LOF 基金实时数据查询系统

## 项目定位

前后端分离的 LOF 基金监控面板，展示实时交易价、溢价率（静态/估算）、申购限额，以及单只基金的历史溢价走势和场内份额变化。

## 技术栈

- 后端：Python 3.10+ / FastAPI / uvicorn / pandas / akshare（降级备用）
- 前端：Vue 3 / Vite / Element Plus / Axios / IndexedDB

## 目录结构

```
back/
├── run.py                    # uvicorn 启动入口
├── requirements.txt          # fastapi, uvicorn, akshare, pandas
└── app/
    ├── main.py               # FastAPI 应用实例、CORS、路由挂载
    ├── cache.py              # 内存缓存（实时数据 + 净值/限额 5min TTL）
    ├── routers/lof.py        # /api/lof 和 /api/lof/history 两个路由
    ├── services/fetcher.py   # 东方财富、同花顺原始数据拉取
    └── utils/formatters.py   # 限额、金额格式化
front/vite-project/
└── src/
    ├── main.js               # Vue 入口（Element Plus + Router）
    ├── router.js             # / → RealTimePremium, /history → HistoryDetail
    ├── App.vue               # keep-alive 包裹，缓存 RealTimePremium 实例
    ├── components/
    │   ├── RealTimePremium.vue  # 全量 LOF 实时表格 + 搜索/筛选/收藏
    │   └── HistoryDetail.vue    # 单只基金历史数据明细
    └── style.css             # 全局样式（亮/暗主题 CSS 变量）
```

## 后端架构

### GET /api/lof 数据流

```
并行请求 (ThreadPoolExecutor, 3 workers)
  ├─ fetch_spot_data()     → 东方财富 push2delay 接口（实时价、量、额）
  ├─ fetch_purchase_data() → 东方财富 Fund_JJJZ_Data 接口（净值、限额）[5min缓存]
  └─ fetch_estimate_data() → 东方财富 FundGuZhi 接口（估算净值）
      ↓
  pandas merge on 基金代码
      ↓
  静态溢价率 = (最新价 - 收盘净值) / 收盘净值 * 100
  估算溢价率 = (最新价 - 估算净值) / 估算净值 * 100
      ↓
  格式化限额/金额 → 存入内存缓存 → 返回 JSON
```

超时或异常时降级到缓存数据返回。

### GET /api/lof/history 数据流

```
1. 主数据源：同花顺 K-line（换手率基于场内份额，可直接算份额）
   备用数据源：东方财富 K-line
2. 东方财富实时数据校准最新一天（同花顺 year.js 缓存延迟问题）
3. f84（实时总份额）校准/填充最新一天的 share_volume
4. 净值：东方财富 lsjz 接口（分页拉全量）
5. QDII 基金 → T-1 净值匹配（净值公布延迟），非 QDII → 当日净值
6. 份额 shift(1) 延后一天（T日结算，T+1公布）
```

### 关键设计决策

- **绕过 akshare**：东方财富接口直接 requests 调用，akshare 仅 fallback。部分 akshare 域名已失效。
- **净值/限额缓存**：5 分钟 TTL，变化频率低，避免每次请求拉全量。
- **份额校准**：同花顺换手率仅 3 位小数，低换手率基金份额误差可达 ~40 万份。用东方财富 f84 校准最新一天，误差 <1%。
- **基金类型**：`_fund_type_cache` 模块级 dict，无 TTL，程序生命周期内只爬一次类型页。

## 前端架构

| 路径 | 组件 | 说明 |
|------|------|------|
| `/` | RealTimePremium | 全量 LOF 实时表格，keep-alive 缓存 |
| `/history?fundCode=` | HistoryDetail | 单只基金历史走势 + 份额变化 |

### 收藏功能

IndexedDB（`lof-monitor` / `favorites`），结构 `{ fundCode, time }`。组件 mount 时加载到 `favorites` Set。

### 筛选

`displayList` computed：收藏过滤 → 代码搜索 → 名称搜索 → 申购状态过滤。

## 启动

```bash
./start.sh                    # 一键启动前后端
# 后端: http://localhost:8000
# 前端: http://localhost:5173
# API 文档: http://localhost:8000/docs
```
