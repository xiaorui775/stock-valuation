# StockVal 股票估值研究台

本地优先的个人股票研究与估值工具。输入股票代码，查看实时行情、关键指标、年度财务数据，并用两阶段 DCF、
WACC、情景分析、反向 DCF、估值倍数、Graham 公式与 Gordon 股利折现估算每股内在价值。

> ⚠️ 本工具仅供学习研究，**不构成投资建议**。估值结果取决于假设输入，DCF 等模型对增速、折现率等假设高度敏感。
> 数据来自 Yahoo Finance，可能存在延迟或误差。

## 架构

| 层 | 技术 | 目录 |
|---|---|---|
| 前端 | React 18 + TypeScript + Vite + Tailwind + ECharts | `frontend/` |
| 后端 | FastAPI + SQLAlchemy + Alembic + SQLite | `backend/` |
| 部署 | Docker Compose（api + nginx 静态服务） | `docker-compose.yml` |

后端分层：`api/`（路由）→ `services/`（业务编排）→ `repositories/` + `providers/`（数据访问）→
`valuation/`（纯计算，不含 I/O）。数据源通过 Provider 协议接入，统一字段模型，按市场路由主备源并降级。

详细需求见 [docs/PRD.md](docs/PRD.md)，开发进度见 [docs/process.md](docs/process.md)。

## 快速开始

### Docker（推荐）

```bash
cp .env.example .env
# 修改 STOCKVAL_SECRET_KEY
docker compose up -d --build
```

打开 http://localhost:8080 ，首次访问创建管理员账号。

### 本地开发

后端需要 Python 3.13+：

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

前端需要 Node 20+：

```bash
cd frontend
npm install
npm run dev
```

Vite 会把 `/api` 代理到 `http://127.0.0.1:8000`。

### 离线演示模式

不访问网络，使用内置样本数据：

```bash
STOCKVAL_DEMO=1 uvicorn app.main:app --reload
```

## 配置

所有配置通过环境变量，前缀 `STOCKVAL_`（可写入 `backend/.env`）：

| 变量 | 默认值 | 说明 |
|---|---|---|
| `STOCKVAL_SECRET_KEY` | `dev-insecure-change-me` | **生产环境必须修改** |
| `STOCKVAL_DATABASE_URL` | `sqlite:///./data/stockval.db` | SQLite 路径 |
| `STOCKVAL_DATA_DIR` | `./data` | 导出文件与数据目录 |
| `STOCKVAL_ENABLE_SCHEDULER` | `true` | 提醒等后台任务开关（多 worker 时只开一个） |
| `STOCKVAL_DEMO` | `0` | `1` 启用离线演示数据 |
| `STOCKVAL_ALLOWED_ORIGINS` | `http://localhost:5173` | CORS 白名单 |
| `STOCKVAL_LOG_LEVEL` | `INFO` | 日志级别 |

## API

统一响应包：

```json
{ "data": {}, "meta": { "source": "yfinance", "as_of": "...", "cached": false, "stale": false, "missing_fields": [] } }
```

| 接口 | 说明 |
|---|---|
| `POST /api/v1/auth/bootstrap` | 首次创建管理员账号（仅一次） |
| `POST /api/v1/auth/login` · `POST /api/v1/auth/logout` · `GET /api/v1/auth/me` | 会话管理 |
| `GET /api/v1/search?q=` | 标的搜索 |
| `GET /api/v1/stocks/{ticker}/quote` | 行情与关键指标 |
| `GET /api/v1/stocks/{ticker}/history` | 历史行情（K 线 / 收盘价） |
| `GET /api/v1/stocks/{ticker}/financials` | 年度财务数据 |
| `GET /api/v1/stocks/{ticker}/news` | 新闻与公告 |
| `GET /api/v1/stocks/{ticker}/valuation` | 基础估值（DCF、敏感性、倍数、DDM、综合） |
| `POST /api/v1/stocks/{ticker}/valuation/scenarios` | 情景分析 |
| `POST /api/v1/stocks/{ticker}/valuation/reverse` | 反向 DCF |
| `GET /api/v1/stocks/{ticker}/valuation/wacc` | WACC 计算 |

交互式文档：http://127.0.0.1:8000/api/docs

## 开发

```bash
cd backend
pytest tests -q          # 后端测试
ruff check app tests     # 代码检查

cd ../frontend
npm run typecheck        # 类型检查
npm run build            # 构建
```

## 数据口径约定

- **缺失即 `null`**，界面显示「—」，绝不用 0 或估算值填充。
- **百分数统一使用百分点**（`10` 表示 10%），仅在展示时加 `%`。
- **金额保留原始货币**，展示按设置换算为万 / 亿或 K / M / B。
- **时间**：数据库存 UTC，接口返回 ISO 8601 带时区，界面按 `Asia/Shanghai` 显示。
- FCF 定义为 **经营现金流 − 资本开支**。

## 免责声明

本工具仅供学习研究，不构成投资建议，估值结果取决于假设输入。DCF 等模型对增速、折现率等假设高度敏感，
请勿据此直接做出投资决策。数据来自 Yahoo Finance，可能存在延迟或误差。
