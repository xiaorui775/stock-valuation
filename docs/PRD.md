# StockVal 产品需求文档（PRD）

| 项目 | 内容 |
|---|---|
| 产品名称 | StockVal 股票估值研究台 |
| 文档版本 | v1.0 |
| 文档状态 | 待评审 |
| 创建日期 | 2026-11-12 |
| 产品形态 | 本地优先的个人投资研究工具（Web 应用，Docker 部署） |
| 技术方向 | FastAPI + React SPA + SQLite |
| 目标读者 | 产品、设计、前后端开发、测试 |

---

## 1. 背景与现状

### 1.1 当前版本能力

现有项目是一个可运行的 Demo：

- Flask 单应用，`app.py` 提供 4 个只读 API。
- `data_service.py` 通过 yfinance 获取行情、近一年日线、最近 4 个财年财务数据，带约 300 秒进程内缓存；支持 `STOCKVAL_DEMO=1` 离线样本数据。
- `valuation.py` 提供两阶段 DCF、估值倍数、Graham 数字、Gordon 股利折现和简单的综合结论。
- 原生 JavaScript + Chart.js 的单页界面，深色金融风格，包含概览、财务报表、估值三个标签页。
- 无数据库、无用户体系、无测试、无后台任务、无日志与监控。

### 1.2 核心问题

| 问题 | 具体表现 | 影响 |
|---|---|---|
| 架构不可扩展 | 路由、数据获取、页面渲染全部围绕单次请求；新功能会持续堆积到 `app.py` 和 `app.js` | 功能越多越难维护，无法支撑组合、提醒、筛选等有状态功能 |
| 无持久化 | 自选股、持仓、估值假设、提醒规则、报告无处保存 | 每次打开都是“查一次就走”，无法形成研究工作流 |
| 前端强耦合 | 模板 DOM ID 与脚本一一对应，状态散落在全局变量 | 新增页面、复用组件、做响应式布局成本高 |
| 数据源单一且无降级 | 仅 yfinance；A 股财务口径不稳定；上游失败直接报错 | 数据可用性和可信度不足 |
| 估值深度不足 | 只有一组假设的 DCF + 固定敏感性表；没有情景、反向 DCF、WACC、历史估值区间 | 无法表达不确定性与市场隐含预期 |
| 财务只展示不解读 | 仅 5 行年度数字 | 用户仍需手工计算增长率、利润率、现金流质量 |
| 缺少研究闭环 | 无自选、组合、对比、筛选、新闻、提醒、导出 | 产品停留在“单股计算器” |
| 工程保障缺失 | 无测试、无结构化日志、无健康检查 | 重构和扩展风险高 |

### 1.3 本次升级的机会

在不引入付费数据源与外部大模型依赖的前提下，把 Demo 升级为**个人可长期使用的股票研究与估值工作台**：以“数据真实、假设透明、结论可解释”为核心，补齐从发现标的、研究基本面、估值、跟踪持仓到提醒与导出的完整链路。

---

## 2. 产品定位与目标

### 2.1 一句话定位

面向具备基础财务知识的个人投资者，本地部署、数据可追溯、假设可调整的股票研究与估值工作台。

### 2.2 目标用户

- **主要用户**：个人投资者 / 金融学习者，关注美股、港股、A 股，能理解 P/E、FCF、折现率等基本概念。
- **使用环境**：个人电脑或家庭服务器，Docker 常驻；通过浏览器访问，可能从局域网内其他设备访问。
- **不使用场景**：专业机构的多用户协作、合规投研、交易执行。

### 2.3 典型使用场景

1. **单股深度研究**：搜索代码 → 查看行情与关键指标 → 阅读财务趋势与规则化解读 → 调整 DCF 假设与情景 → 保存估值预设 → 导出 PDF 报告。
2. **每日复盘**：打开自选股列表 → 查看涨跌与估值偏离 → 处理站内/桌面提醒 → 查看组合盈亏。
3. **横向比较**：选择 3–6 家同业公司 → 对比增长、利润率、估值倍数 → 用筛选器在预设股票池中找候选。
4. **持仓跟踪**：录入持仓成本与数量 → 查看组合市值、权重、未实现盈亏 → 为关键持仓设置估值/价格提醒。

### 2.4 产品目标

| 目标 | 衡量方式 |
|---|---|
| 研究闭环完整 | 单只股票从搜索到导出报告可在同一产品内完成 |
| 数据可信可追溯 | 所有展示数字带数据源与时间戳；缺失值明确标注，不填充 |
| 估值可解释 | 每个估值结果展示公式、输入、假设与敏感性；支持情景与反向推演 |
| 使用效率 | 常用操作（查股、加自选、改假设重算、设提醒）不超过 3 次交互 |
| 工程可持续 | 分层架构、自动化测试、结构化日志、容器化一键启动 |

### 2.5 非目标（本期明确不做）

- 不接入券商、不做交易下单、不做资金流。
- 不提供实时逐笔、Level-2、Tick 级行情。
- 不输出投资建议、不自动荐股、不做收益承诺。
- 不做回测引擎、组合优化、VaR 等专业风险模型。
- 不做移动原生 App；Web 端做基础响应式适配即可。
- 不做公开注册与多租户 SaaS；多用户仅做数据模型与权限预留。
- 不支持期权、期货、外汇、加密货币。
- 不接入大模型生成解读；财务解读采用确定性规则。

### 2.6 成功指标

| 类别 | 指标 | 目标 |
|---|---|---|
| 数据 | 支持市场的行情可用率 | ≥ 95% |
| 数据 | 所有缺失字段标记率 | 100%（null + 缺失原因） |
| 正确性 | 估值核心公式单元测试分支覆盖 | 100% |
| 正确性 | 估值结果与手算 golden case 一致 | 100% |
| 性能 | 首屏可交互（本地） | P95 < 2s |
| 性能 | 行情接口（命中缓存） | P95 < 300ms |
| 性能 | 估值计算接口（纯计算） | P95 < 500ms |
| 提醒 | 规则触发到站内通知 | < 5 分钟 |
| 质量 | 后端测试覆盖率 | ≥ 70% |
| 稳定 | 正常使用下未处理异常 | 0 |

---

## 3. 设计原则

1. **不编造数据**：缺失即 `null`，UI 显示「—」，并说明缺失原因；绝不用 0、均值或推测值填充。唯一的回退是**公式推导**（如 FCF = 经营现金流 + 资本开支），且必须标注来源。
2. **假设透明**：任何估值数字都能展开查看输入、公式、数据时间与来源。
3. **时间戳优先**：行情标注 `as_of` 与延迟提示；财务标注财年；缓存数据标注 `cached` / `stale`。
4. **渐进降级**：主数据源失败时尝试备用源；备用源也失败时返回明确错误或过期缓存（标记 stale），而不是伪造。
5. **本地优先**：默认仅本机访问；配置后可局域网访问；不依赖云服务即可完整使用。
6. **信息密度**：深色金融终端风格，强调数据层级与可扫描性，避免大面积留白和装饰性动画。
7. **涨跌配色可配置**：默认按中国用户习惯「红涨绿跌」，设置中可切换为「绿涨红跌」。
8. **中文优先**：界面、错误信息、报告均为中文；数字单位默认「万 / 亿」，可在设置中切换 K/M/B。

---

## 4. 信息架构与核心流程

### 4.1 页面地图

```
登录 / 首次初始化
└── 主应用（全局顶栏：搜索、自选、组合、对比、筛选、提醒、报告、设置、通知）
    ├── 个股详情 /stock/:ticker
    │   ├── 概览（报价头、关键指标、估值结论、快捷操作）
    │   ├── 图表（K 线/面积、技术指标、周期切换）
    │   ├── 财务（年度/季度报表、趋势、规则化解读）
    │   ├── 估值（DCF、情景、反向 DCF、WACC、敏感性、倍数、DDM、历史区间、综合）
    │   └── 新闻与公告
    ├── 自选股 /watchlists
    ├── 投资组合 /portfolios、/portfolios/:id
    ├── 多股对比 /compare
    ├── 筛选器 /screener
    ├── 提醒 /alerts（含通知中心）
    ├── 报告 /reports
    └── 设置 /settings
```

### 4.2 核心流程

**流程 A：单股研究**
搜索标的 → 个股概览 → 财务报表与解读 → 估值工作台调整假设 → 查看情景与敏感性 → 保存估值预设 → 导出 PDF/Excel。

**流程 B：日常复盘**
登录 → 自选股列表（按市场分组）→ 查看异动标记 → 打开提醒/通知中心 → 进入个股 → 调整组合或提醒规则。

**流程 C：横向筛选**
筛选器选择股票池与条件 → 运行筛选（显示数据覆盖率与时间）→ 排序 → 勾选 2–6 只加入对比 → 查看倍数与估值对比 → 加入自选。

**流程 D：组合跟踪**
新建组合 → 录入持仓（代码、数量、成本）→ 自动换算基础货币 → 查看市值、权重、盈亏 → 为持仓设置提醒 → 导出组合报告。

---

## 5. 功能需求

### 5.0 优先级与阶段总览

| 模块 | 优先级 | 交付阶段 |
|---|---|---|
| 用户与认证（预留多用户） | P0 | M0 |
| 全局搜索与标的识别 | P0 | M1 |
| 个股概览 | P0 | M1 |
| 行情图表与技术指标 | P0（基础）/ P1（指标） | M1 / M2 |
| 财务报表 | P0 | M1 |
| 规则化财务解读 | P1 | M2 |
| 估值工作台（基础） | P0 | M1 |
| 估值增强（情景、反向 DCF、WACC、历史区间、多阶段 DDM） | P1 | M2 |
| 自选股 | P0 | M1 |
| 投资组合 | P0 | M2 |
| 多股对比 | P1 | M2 |
| 筛选器 | P1 | M2 |
| 新闻与公告 | P1 | M3 |
| 提醒与通知 | P1 | M3 |
| 报告导出（PDF / Excel） | P1 | M4 |
| 设置 | P1 | M4 |
| 数据源与质量体系 | P0 | 贯穿 |

优先级定义：**P0** 为本期必须完成，缺失则不能发布；**P1** 为本期应完成，可在资源紧张时顺延一个阶段；**P2** 为可选增强，不在本期承诺。

---

### 5.1 用户与认证（P0）

#### 目标
支持单用户长期使用，数据按用户隔离，并为未来多用户预留结构。

#### 需求
- **FR-AUTH-01 首次初始化**：数据库为空时，前端进入初始化页，创建第一个 owner 账号（邮箱/用户名 + 密码）。创建成功后关闭初始化入口。
- **FR-AUTH-02 登录与会话**：登录后签发 httpOnly、SameSite=Lax 的会话 Cookie；支持「记住我 30 天」；支持登出与主动失效会话。
- **FR-AUTH-03 数据隔离**：自选股、组合、提醒、估值预设、报告均带 `user_id`；所有查询强制按当前用户过滤。角色字段预留 `owner` / `member`，本期只使用 `owner`。
- **FR-AUTH-04 账号设置**：修改显示名、密码、基础货币（默认 CNY）。
- **FR-AUTH-05 默认关闭注册**：不提供公开注册入口；新增用户仅能通过环境变量开关或命令行工具创建（本期不实现 UI）。

#### 边界
- 不做邮箱验证、找回密码邮件（个人工具可通过命令行重置密码）。
- 不做 OAuth / SSO。

#### 验收标准
- 未登录访问业务页面重定向到登录页；未登录调用业务 API 返回 401。
- 首次初始化只能用一次；重复调用返回 409。
- 用户 A 无法读取或修改用户 B 的任何资源（API 测试覆盖）。
- 密码使用 Argon2id 或 bcrypt 哈希存储，日志与响应中不出现密码或哈希。

---

### 5.2 全局搜索与标的识别（P0）

#### 目标
让用户用代码或名称快速定位标的，并正确路由到数据源。

#### 需求
- **FR-SEARCH-01 搜索框**：顶栏常驻，支持股票代码与公司名称；输入 300ms 防抖；结果下拉展示代码、名称、市场、交易所、货币、数据源。
- **FR-SEARCH-02 代码格式**：
  - `AAPL`、`MSFT` → 美股（US）
  - `0700.HK` → 港股（HK）
  - `600519.SS` / `000001.SZ` / `830799.BJ` → A 股（CN）
  - 支持大小写与前后空格容错。
- **FR-SEARCH-03 名称搜索**：A 股通过 akshare 名称检索；美股/港股优先使用数据源搜索接口，失败时仅支持代码精确匹配并提示。
- **FR-SEARCH-04 最近搜索**：本地保存最近 10 条，可清除。
- **FR-SEARCH-05 无效代码**：返回 404，错误信息说明「代码无效或暂无数据」，不展示任何模拟数据。

#### 验收标准
- 输入 `aapl` 能命中 AAPL；输入 `600519` 能提示 `600519.SS`（若无法自动补全，则明确提示需要后缀）。
- 搜索接口 P95 < 800ms（命中缓存 < 200ms）。
- 无结果时下拉显示空状态，不报错。

---

### 5.3 个股概览（P0）

#### 需求
- **FR-OVERVIEW-01 报价头**：名称、代码、市场标签、现价、涨跌额、涨跌幅、货币、交易状态（盘前/盘中/盘后/休市）、数据时间。
- **FR-OVERVIEW-02 关键指标**：市值、P/E (TTM)、Forward P/E、EPS (TTM)、股息率、Beta、52 周高/低、成交量、昨收、日内区间、总股本、P/B、P/S、EV/EBITDA、PEG。
- **FR-OVERVIEW-03 52 周位置**：用水平条展示现价在 52 周区间中的位置。
- **FR-OVERVIEW-04 估值结论卡**：展示 DCF 每股价值、相对现价空间、综合判定（低估/合理/高估），点击跳转估值页。
- **FR-OVERVIEW-05 快捷操作**：加入自选、加入组合、创建提醒、导出报告。
- **FR-OVERVIEW-06 数据徽标**：每个数据区块标注数据源（yfinance / akshare）与 `as_of`；缺失字段显示「—」并可通过悬浮说明原因（如「数据源未提供」）。

#### 验收标准
- 所有指标缺失时页面仍可正常渲染，不出现 `NaN`、`Infinity`、`undefined`。
- 行情延迟提示清楚可见；不把延迟数据描述为实时。
- 快捷操作在未登录或数据未加载时禁用。

---

### 5.4 行情图表与技术指标（P0 / P1）

#### 需求
- **FR-CHART-01 周期**：1M / 3M / 6M / 1Y / 3Y / 5Y / MAX；日线 / 周线 / 月线。
- **FR-CHART-02 图表类型**：面积图（默认）与 K 线图切换。
- **FR-CHART-03 技术指标（P1）**：MA5/10/20/60/120、BOLL(20,2)；副图支持成交量、MACD(12,26,9)、RSI(14)。指标计算口径在前后端保持一致，优先后端计算并随历史数据返回。
- **FR-CHART-04 交互**：十字光标、数值提示、缩放与平移、区间选择；移动端支持触摸。
- **FR-CHART-05 数据完整性**：停牌/缺失交易日不插值；图表下方提示数据起止日期与复权方式。
- **FR-CHART-06 事件标记（P1）**：财报日、分红除权日标记（数据源提供时）。

#### 验收标准
- 指标数值与独立计算（或已知库）结果误差 < 0.01%。
- 切换周期不产生重复请求；请求失败显示可重试的错误态。
- 大数据量（5 年日线）渲染流畅，交互无明显卡顿。

---

### 5.5 财务报表（P0）

#### 需求
- **FR-FIN-01 年度报表**：最近 4–5 个财年，包含营业收入、毛利润、营业利润、净利润、EPS、经营现金流、资本开支、自由现金流、总债务、现金、股东权益、总股本。
- **FR-FIN-02 季度报表（P1）**：最近 8 个季度，字段同上（数据源支持时）。
- **FR-FIN-03 展示**：默认原始货币，支持切换「亿 / 百万 / 原始值」；支持显示同比（YoY）列与 3 年 CAGR。
- **FR-FIN-04 缺失处理**：缺失科目显示「—」，不计算同比；表格底部说明缺失项。
- **FR-FIN-05 导出**：当前报表可导出 Excel（复用报告导出能力）。
- **FR-FIN-06 口径说明**：明确 FCF 定义（经营现金流 − 资本开支）与数据来源；A 股与美股字段映射在文档与 UI 中可查。

#### 验收标准
- 字段缺失、财年数量不足、币种不同均不导致页面崩溃。
- 同比公式为 `(本期 − 上期) / |上期|`，上期为 0 或缺失时返回「—」。
- 单位切换不改变底层数据，仅改变展示。

---

### 5.6 规则化财务解读（P1）

#### 目标
在不接入大模型的前提下，自动指出财务数据中的关键事实与异常，帮助用户快速形成判断。

#### 规则集

| 规则 | 计算 | 触发 | 级别 |
|---|---|---|---|
| 营收增长 | 最近财年 YoY、3 年 CAGR | 增长 > 20% 或 < 0 | info / watch |
| 毛利率趋势 | 毛利率 = 毛利 / 营收 | 连续 2 年下降且累计 > 3pp | watch |
| 营业利润率趋势 | 营业利润 / 营收 | 连续 2 年下降且累计 > 3pp | watch |
| 净利率趋势 | 净利润 / 营收 | 连续 2 年下降且累计 > 3pp | watch |
| 现金流质量 | FCF / 净利润 | 连续 2 年 < 50% | alert |
| 应计异常 | 净利润增速 − 经营现金流增速 | > 20pp | alert |
| 杠杆 | 总债务 / 股东权益；净债务 / EBITDA | > 2.0 或 > 4.0（数据可得时） | watch |
| 股本稀释 | 总股本 YoY | > 2% | watch |
| 毛利率扩张 | 毛利率同比 | > 3pp | info |
| 营收与应收/存货 | 应收或存货增速 − 营收增速 | > 20pp（字段可得时） | watch |

#### 输出规范
- 每条解读包含：结论一句话、涉及财年与数值、计算公式、级别（info / watch / alert）。
- 按级别排序；无触发规则时显示「未发现显著异常」。
- 所有文字为事实陈述，不使用「建议买入/卖出」等投资建议措辞。
- 规则结果完全确定性，可单元测试；相同输入必须产生相同输出。

#### 验收标准
- 每条规则有正例、反例、边界值测试（分母为 0、负利润、缺失字段）。
- 解读结果不包含任何数据源之外的数值。
- 缺失字段导致规则无法计算时，该规则静默跳过并在「未覆盖项」中列出。

---

### 5.7 估值工作台（P0 基础 / P1 增强）

#### 目标
提供可解释、可调节、可保存的多模型估值环境。

#### 基础能力（P0）
- **FR-VAL-01 输入面板**：基准 FCF、阶段一增速、阶段一年数（默认 5）、永续增速、折现率、股利增速；提供「恢复 CAPM 默认值」。
- **FR-VAL-02 两阶段 DCF**：沿用现有公式，输出每股价值、企业价值、股权价值、终值占 EV 比例、相对现价空间。
- **FR-VAL-03 敏感性表**：折现率 ±2/±1/0 与永续增速 1.5/2.5/3.5% 的矩阵，支持热力图展示。
- **FR-VAL-04 估值倍数**：P/E、Forward P/E、P/S、P/B、EV/EBITDA、PEG（源提供时）、FCF Yield、Graham 数字，均展示公式。
- **FR-VAL-05 综合结论**：对 DCF、DDM（股息率 > 0）、Graham 取平均，标注参与方法数与权重；阈值 ±15% 判定低估/高估/合理。
- **FR-VAL-06 假设与来源**：展示基准 FCF 来源财年、资产负债表债务/现金取值、总股本来源、Beta 与 CAPM 计算过程。
- **FR-VAL-07 保存预设**：保存当前假设为命名预设，支持加载、更新、删除。

#### 增强能力（P1）
- **FR-VAL-08 WACC 计算器**：输入无风险利率、股权风险溢价、Beta、税前债务成本、实际税率、D/E；输出 `WACC = E/(D+E)×r_e + D/(D+E)×r_d×(1−t)`，其中 `r_e = r_f + β×ERP`。默认无风险利率按币种预填（USD 4.0%、CNY 2.5%、HKD 3.5%），可修改。
- **FR-VAL-09 情景分析**：Bear / Base / Bull 三套参数（增速、永续增速、折现率），支持设置概率权重；输出各情景每股价值、加权期望价值、相对现价空间；图表对比。
- **FR-VAL-10 反向 DCF**：给定现价、折现率、永续增速、年数，用二分法求解市场隐含的阶段一增速（区间 −50% 至 100%，容差 0.01%）；输出隐含增速与「市场预期是否激进」的事实描述（不做建议）。
- **FR-VAL-11 历史估值区间**：P/E、P/B、P/S、FCF Yield 的 3 年 / 5 年分位数（10/25/50/75/90）与当前分位；需要历史价格与对应历史财务数据。数据不足时显示「数据不足」并说明缺什么。
- **FR-VAL-12 多阶段 DCF/DDM**：显式增长期 + 线性衰减期 + 永续期；DDM 仅对股息率 > 0 的标的展示。
- **FR-VAL-13 加权综合**：允许用户勾选参与综合的方法并设置权重，默认等权。

#### 计算与边界规则
- 所有百分数参数以「百分点」传入（10 表示 10%），服务端内部转小数。
- `折现率 ≤ 永续增速`、`折现率 ≤ −100%`、股本为 0、基准 FCF 缺失 → 返回 `null` 并给出原因，不抛 500。
- 负 FCF、负 EPS 等合法负值不拒绝计算，但 UI 标注「基于负值，结果解释力有限」。
- 结果不得出现 `NaN` / `Infinity`；序列化前统一清洗。
- 每个估值结果包含 `formula`、`inputs`、`source`、`as_of`。

#### 验收标准
- 两阶段 DCF、DDM、Graham、WACC、反向 DCF 均有 golden case 单元测试。
- 修改任一输入后 500ms 内完成重算（纯计算 + 已缓存数据）。
- 情景权重之和不为 100% 时给出校验错误。
- 历史估值区间数据不足时不影响其他估值模块渲染。

---

### 5.8 自选股（P0）

#### 需求
- **FR-WATCH-01 多分组**：支持创建多个自选列表（如「核心持仓」「观察池」），重命名、删除、排序。
- **FR-WATCH-02 增删与排序**：按代码添加（校验有效性）、移除、拖拽排序；支持批量添加。
- **FR-WATCH-03 列表字段**：代码、名称、现价、涨跌幅、市值、P/E、Forward P/E、股息率、FCF Yield、DCF 上行空间、数据时间。列可配置显示/隐藏与排序。
- **FR-WATCH-04 分组与筛选**：按市场（US/HK/CN）分组；按涨跌幅、估值空间排序。
- **FR-WATCH-05 刷新策略**：进入页面自动刷新；手动刷新按钮；单次刷新失败保留上次数据并标记 stale。
- **FR-WATCH-06 快速操作**：行内跳转个股、移除、创建提醒。

#### 验收标准
- 同一列表内重复添加同一代码返回 409 或幂等成功（二选一，需固定）。
- 100 只标的的列表首屏 P95 < 2s（并发受限 + 缓存）。
- 上游失败时列表不清空，显示 stale 标记与失败原因。

---

### 5.9 投资组合（P0）

#### 需求
- **FR-PORT-01 多组合**：创建、重命名、删除组合；设置基础货币（默认 CNY）。
- **FR-PORT-02 持仓管理**：录入代码、数量、平均成本、币种、建仓日期、备注；支持编辑、删除。
- **FR-PORT-03 组合指标**：总市值、总成本、未实现盈亏与收益率、当日盈亏、持仓权重、按市场/行业分布、组合加权估值上行空间。
- **FR-PORT-04 汇率换算**：非基础货币持仓按最新汇率换算；展示汇率来源与时间；汇率缺失时按币种分组展示并提示，不做静默估算。
- **FR-PORT-05 交易流水（P1）**：记录买入/卖出/分红，计算已实现盈亏与股息收入；本期可先只做持仓，流水作为 P1。
- **FR-PORT-06 组合报告**：导出 PDF/Excel，包含持仓明细、权重、盈亏、估值汇总。
- **FR-PORT-07 风险提示**：单一持仓权重 > 30% 时标黄提示（事实提示，不构成建议）。

#### 验收标准
- 未实现盈亏 = `(现价 − 平均成本) × 数量`，多币种先换算再汇总；单元测试覆盖正负盈亏、零持仓、汇率缺失。
- 组合总权重之和为 100%（浮点误差 < 0.01%）。
- 删除组合需二次确认；删除后关联持仓不可恢复（或采用软删除，需固定）。

---

### 5.10 多股对比（P1）

#### 需求
- **FR-CMP-01 选择标的**：2–6 只，支持从自选、组合、搜索结果或手动输入添加。
- **FR-CMP-02 走势对比**：近 1 年归一化收益率曲线（起点 = 100），统一货币或分别展示。
- **FR-CMP-03 指标对比表**：市值、营收增速、毛利率、净利率、P/E、Forward P/E、PEG、P/B、P/S、EV/EBITDA、股息率、FCF Yield、DCF 上行空间、Beta。每行高亮最优/最差值（最优定义需在 UI 说明，如估值越低越好、增速越高越好）。
- **FR-CMP-04 估值对比**：在相同假设下计算的每股价值与上行空间，注明假设统一。
- **FR-CMP-05 导出**：对比表导出 Excel。

#### 验收标准
- 指标缺失的标的在对应单元格显示「—」，不参与最优/最差评选。
- 超过 6 只时拒绝并提示上限。
- 对比结果标注数据时间，混合市场时明确币种。

---

### 5.11 筛选器（P1）

#### 需求
- **FR-SCR-01 股票池**：自选列表、预设指数（S&P 500、沪深 300、恒生指数）、自定义代码列表（上限 500）。
- **FR-SCR-02 筛选条件**：市场、市值区间、P/E、Forward P/E、PEG、P/B、P/S、EV/EBITDA、股息率、营收增速、FCF Yield、DCF 上行空间、Beta。
- **FR-SCR-03 结果**：排序、分页（50/页）、显示数据覆盖率（成功获取数 / 总数）、`as_of`。
- **FR-SCR-04 保存预设**：保存筛选条件与股票池。
- **FR-SCR-05 降级**：部分标的获取失败时仍返回成功结果，并列出失败数量与原因；不因单只失败中断整体。
- **FR-SCR-06 频率控制**：服务端限制并发（默认 4）与每轮股票池上限；命中缓存优先；显示预计耗时。

#### 边界
- 不做全市场实时扫描；预设指数成分股列表每日更新一次并缓存。
- DCF 上行空间筛选使用统一默认假设，结果标注「统一假设」。

#### 验收标准
- 500 只股票池在缓存冷启动下可完成筛选且不触发上游封禁（限流 + 重试 + 降级）。
- 筛选条件为空时返回股票池全部可用标的（仍受分页限制）。
- 结果中的每个数值都可通过个股详情复现（相同时间与来源）。

---

### 5.12 新闻与公告（P1）

#### 需求
- **FR-NEWS-01 来源**：美股/港股通过 yfinance 新闻；A 股通过 akshare 获取东方财富新闻与公告。
- **FR-NEWS-02 列表**：标题、来源、发布时间、类型（新闻/公告）、外链；按时间倒序；分页 20 条。
- **FR-NEWS-03 去重**：按 URL 或标题+时间去重；同一事件不重复展示。
- **FR-NEWS-04 过滤**：按类型筛选；默认全部。
- **FR-NEWS-05 缓存**：新闻缓存 15 分钟；公告缓存 60 分钟；展示 `fetched_at`。
- **FR-NEWS-06 外部链接**：新窗口打开，标注「外部链接，内容由来源网站提供」。

#### 边界
- 不做正文抓取、不做情绪评分、不做摘要生成。
- 来源失败时显示空状态与原因，不影响其他模块。

#### 验收标准
- 新闻/公告为空或上游失败时页面正常。
- 同一 URL 不重复出现。
- 不缓存或展示付费墙后的全文。

---

### 5.13 提醒与通知（P1）

#### 需求
- **FR-ALERT-01 规则类型**：
  - 价格高于 / 低于阈值
  - 当日涨跌幅超过阈值
  - P/E 低于阈值
  - DCF 上行空间高于阈值
  - FCF Yield 高于阈值
  - 距财报日少于 N 天
  - 成交量高于 N 日均量的倍数
- **FR-ALERT-02 规则配置**：标的、类型、阈值、冷却时间（默认 60 分钟）、启用开关、通知渠道（站内 / 浏览器桌面）。
- **FR-ALERT-03 评估调度**：交易时段内每 5 分钟评估一次（按交易所日历）；收盘后评估每日类规则一次；非交易日不评估。
- **FR-ALERT-04 去重与冷却**：同一规则在冷却期内不重复通知；数据缺失或获取失败时不触发，并记录跳过原因。
- **FR-ALERT-05 通知中心**：列表、未读角标、标记已读/全部已读、按标的筛选、删除。
- **FR-ALERT-06 浏览器桌面通知**：用户授权后，在页面打开时通过 SSE 实时推送；页面关闭时无法送达（需在 UI 明确说明）。
- **FR-ALERT-07 触发历史**：保留最近 90 天通知；支持查看规则命中记录。

#### 边界
- 本期不做邮件、短信、Telegram、Bark、Server酱等外部渠道；数据模型预留 `channels` 字段。
- 提醒基于延迟行情，不承诺盘中实时性。
- 不做复杂组合条件（AND/OR 表达式）；本期单条件规则。

#### 验收标准
- 规则评估单元测试覆盖：触发、未触发、冷却中、数据缺失、停牌。
- 同一规则同一冷却期内只产生一条通知。
- 浏览器通知权限被拒绝时，站内通知仍正常工作。
- 提醒服务崩溃或重启后，不重复发送已通知事件（持久化 `last_triggered_at` 与去重键）。

---

### 5.14 报告导出（P1）

#### 需求
- **FR-RPT-01 PDF 研究报告**：服务端渲染报告页面并用 Playwright 转 PDF。内容：
  1. 封面/标题：公司名称、代码、生成时间、数据源
  2. 行情快照与关键指标
  3. 近一年价格走势图（静态图）
  4. 年度财务表与规则化解读
  5. 估值摘要：DCF、情景、敏感性、倍数、DDM、综合结论
  6. 假设与数据来源、免责声明
- **FR-RPT-02 Excel 数据**：多 sheet：`Quote`、`Financials`、`Valuation`、`Sensitivity`、`Scenarios`、`Assumptions`。表头包含 `as_of` 与 `source`。
- **FR-RPT-03 异步任务**：创建导出任务 → 返回 job id → 轮询状态（`pending/running/succeeded/failed`）→ 下载；单份报告生成超时 120 秒。
- **FR-RPT-04 存储与保留**：文件存放于挂载卷 `data/exports/`；默认保留 30 天，启动时清理过期文件。
- **FR-RPT-05 命名**：`StockVal_{ticker}_{YYYYMMDD_HHMM}.pdf|xlsx`。
- **FR-RPT-06 缺失数据**：报告中缺失值统一「—」，并附缺失说明；不隐藏缺失项。

#### 验收标准
- PDF 中文字体正常渲染，无乱码、无截断。
- Excel 数值为数值类型而非文本，百分比字段带单位说明。
- 报告生成失败时返回可读错误并保留任务记录。
- 同一任务重复下载不重复生成。

---

### 5.15 设置（P1）

#### 需求
- **FR-SET-01 个人资料**：显示名、邮箱/用户名、基础货币、修改密码。
- **FR-SET-02 显示偏好**：涨跌配色（红涨绿跌 / 绿涨红跌）、数字单位（万/亿 或 K/M/B）、主题（深色默认，浅色 P2）、图表默认周期。
- **FR-SET-03 估值默认值**：阶段一增速、阶段一 5 年、永续增速、折现率来源（CAPM 或手动）、DDM 增速、情景默认参数。
- **FR-SET-04 数据源**：展示各市场当前数据源与优先级；只读（配置通过环境变量/配置文件，避免运行期复杂切换）。
- **FR-SET-05 缓存与刷新**：展示缓存 TTL；提供「清除缓存」按钮（仅当前用户或全局，需确认）。
- **FR-SET-06 关于与免责声明**：版本、数据来源、免责声明、开源许可。
- **FR-SET-07 演示模式**：`STOCKVAL_DEMO=1` 时顶栏显示明显横幅；设置页说明演示数据不联网。

#### 验收标准
- 设置修改即时生效并持久化；刷新页面后保留。
- 基础货币变更后，组合与报告按新货币换算并标注汇率时间。
- 清除缓存需二次确认，且不删除用户数据（自选、组合、提醒、预设）。

---

### 5.16 数据源与质量体系（P0，贯穿）

#### 需求
- **FR-DATA-01 数据源路由**：
  | 市场/代码特征 | 主数据源 | 备用/补充 |
  |---|---|---|
  | `.SS` / `.SZ` / `.BJ` | akshare | yfinance（仅行情兜底） |
  | `.HK` | yfinance | akshare（财务/行情兜底，视可用性） |
  | 其他 | yfinance | 无 |
- **FR-DATA-02 统一字段模型**：所有数据源先转换为统一 schema（snake_case，币种、单位、时间明确），再进入服务层。
- **FR-DATA-03 字段缺失标记**：响应包含 `missing_fields` 列表与原因分类（源未提供 / 解析失败 / 不适用）。
- **FR-DATA-04 交叉校验**：A 股财务同时可得时，对营业收入做一致性检查；差异 > 2% 时在 UI 标记「数据源存在差异」并展示两个值。
- **FR-DATA-05 缓存与降级**：
  | 数据类型 | TTL | 过期策略 |
  |---|---|---|
  | 行情 quote | 30–60 秒 | 过期后同步刷新；失败返回 stale 缓存 |
  | 历史价格 | 5–15 分钟 | 同上 |
  | 财务报表 | 12 小时 | 持久化到 SQLite，过期后台刷新 |
  | 新闻 | 15 分钟 | 过期刷新 |
  | 公告 | 60 分钟 | 过期刷新 |
  | 搜索/标的元数据 | 24 小时 | 持久化 |
  | 汇率 | 60 分钟 | 过期刷新，失败用 stale 并标记 |
  | 估值计算 | 不缓存（纯计算） | — |
- **FR-DATA-06 数据血缘**：每个 API 响应带 `meta.source`、`meta.as_of`、`meta.cached`、`meta.stale`、`meta.missing_fields`。
- **FR-DATA-07 契约测试**：为 yfinance / akshare 的字段映射准备固定样本（fixture），上游字段改名时测试失败并提示。
- **FR-DATA-08 复权与拆分**：历史价格默认前复权（auto_adjust=True），并在 UI 标注；财务每股数据与拆股口径需与数据源一致。

#### 验收标准
- 上游超时/限流时，接口在 10 秒内返回错误或 stale 数据，不挂起。
- 所有响应通过 Pydantic 校验，不出现 `NaN`、日期格式错误、货币缺失。
- 交叉校验差异可复现、可解释。

---

## 6. 数据与内容规范

### 6.1 字段与单位

| 类别 | 规范 |
|---|---|
| 百分数 | API 与计算统一使用「百分点」（10 = 10%）；仅在展示时加 `%` |
| 金额 | 存储原始货币最小单位（元/美元），展示按设置换算为万/亿或 K/M/B |
| 币种 | 每个金额字段必须带币种上下文；组合汇总使用基础货币并记录汇率与时间 |
| 时间 | 数据库存 UTC；API 返回 ISO 8601 带时区；UI 按 `Asia/Shanghai` 展示 |
| 日期 | 行情 `as_of` 精确到分钟；财务数据精确到财年/季度 |
| 缺失 | `null`，不使用 0、空字符串或 `N/A` 混用 |
| 负数 | 合法负值（负 FCF、负利润）保留并标注，不取绝对值 |
| 精度 | 金额展示 2 位小数（大额可用 1–2 位）；比率 2 位；Beta 3 位 |

### 6.2 数据来源标注

- 每个数据卡片右上角显示来源徽标与时间。
- 混合来源时逐字段标注（tooltip 或明细表）。
- 演示模式下所有数据统一标注「演示数据」。

### 6.3 涨跌配色

- 默认：红涨绿跌（中国用户习惯）。
- 设置项可切换为绿涨红跌。
- 注意：当前 Demo 实现为绿涨红跌，升级时需统一为可配置并默认红涨绿跌（见开放问题 Q1）。

### 6.4 文案规范

- 事实与观点分离：不出现「建议买入」「必涨」「稳赚」等措辞。
- 所有页面底部保留免责声明：「本工具仅供学习研究，不构成投资建议。」
- 错误信息说明原因与下一步动作，不暴露堆栈或内部路径。

---

## 7. 技术方案

### 7.1 总体架构

```
┌──────────────────────────────────────────────────────────────┐
│ React SPA (Vite + TS + Tailwind + ECharts)                   │
│ TanStack Query（服务端状态） / Zustand（UI 状态）             │
└───────────────┬──────────────────────────────┬───────────────┘
                │ REST /api/v1 (JSON)          │ SSE /api/v1/notifications/stream
┌───────────────▼──────────────────────────────▼───────────────┐
│ FastAPI                                                      │
│  API Routers（认证、行情、财务、估值、自选、组合、对比、筛选、 │
│  提醒、新闻、报告、设置）                                     │
│  Services（业务编排、估值、组合计算、规则解读、提醒评估）      │
│  Repositories（SQLAlchemy）                                   │
│  Providers（yfinance / akshare 适配器 + 注册表 + 缓存）       │
│  Scheduler（APScheduler：提醒评估、报表生成、缓存预热）        │
└───────────────┬──────────────────────────────┬───────────────┘
                │                              │
        ┌───────▼────────┐             ┌───────▼────────┐
        │ SQLite         │             │ data/exports/  │
        │ (SQLAlchemy +  │             │ PDF / XLSX     │
        │  Alembic)      │             └────────────────┘
        └────────────────┘
```

### 7.2 后端目录结构

```
backend/
├── pyproject.toml
├── alembic.ini
├── alembic/versions/
├── app/
│   ├── main.py                 # FastAPI 实例、中间件、路由挂载、静态文件
│   ├── core/
│   │   ├── config.py           # pydantic-settings，读取 .env
│   │   ├── db.py               # engine / session
│   │   ├── security.py         # 密码哈希、会话、CSRF
│   │   ├── logging.py          # structlog 配置、request_id
│   │   └── errors.py           # 统一错误模型与异常处理器
│   ├── api/
│   │   ├── deps.py             # current_user、分页、限流依赖
│   │   └── v1/
│   │       ├── auth.py
│   │       ├── search.py
│   │       ├── stocks.py       # quote / history / financials / news
│   │       ├── valuation.py
│   │       ├── watchlists.py
│   │       ├── portfolios.py
│   │       ├── compare.py
│   │       ├── screener.py
│   │       ├── alerts.py
│   │       ├── notifications.py
│   │       ├── reports.py
│   │       └── settings.py
│   ├── models/                 # SQLAlchemy ORM
│   ├── schemas/                # Pydantic 请求/响应
│   ├── repositories/
│   ├── services/
│   │   ├── market_service.py
│   │   ├── financial_service.py
│   │   ├── interpretation_service.py
│   │   ├── valuation_service.py
│   │   ├── portfolio_service.py
│   │   ├── screener_service.py
│   │   ├── alert_service.py
│   │   ├── news_service.py
│   │   └── report_service.py
│   ├── valuation/              # 纯计算包
│   │   ├── dcf.py
│   │   ├── ddm.py
│   │   ├── multiples.py
│   │   ├── graham.py
│   │   ├── wacc.py
│   │   ├── reverse_dcf.py
│   │   ├── scenarios.py
│   │   └── bands.py
│   ├── providers/
│   │   ├── base.py             # Provider 协议与统一模型
│   │   ├── yfinance_provider.py
│   │   ├── akshare_provider.py
│   │   ├── registry.py         # 按市场/代码路由、降级
│   │   ├── cache.py            # L1 TTL + L2 SQLite
│   │   └── fx.py               # 汇率
│   └── tasks/
│       ├── scheduler.py
│       ├── alert_evaluator.py
│       └── maintenance.py      # 清理过期导出、刷新预设指数成分
└── tests/
    ├── unit/                   # 估值、规则、组合、提供器映射
    ├── api/                    # httpx AsyncClient 契约测试
    └── fixtures/               # 上游样本数据
```

### 7.3 前端目录结构

```
frontend/
├── index.html
├── vite.config.ts
├── tailwind.config.ts
├── src/
│   ├── main.tsx
│   ├── App.tsx                 # 路由与布局
│   ├── api/
│   │   ├── client.ts           # fetch 封装、错误解包、401 处理
│   │   ├── queries.ts          # TanStack Query hooks
│   │   └── types.ts            # 由 OpenAPI 生成的类型（可选）
│   ├── components/             # Button、Card、DataTable、Stat、Badge、Chart、EmptyState、ErrorState
│   ├── features/
│   │   ├── auth/
│   │   ├── search/
│   │   ├── stock/
│   │   ├── chart/
│   │   ├── financials/
│   │   ├── valuation/
│   │   ├── watchlists/
│   │   ├── portfolios/
│   │   ├── compare/
│   │   ├── screener/
│   │   ├── alerts/
│   │   ├── notifications/
│   │   ├── reports/
│   │   └── settings/
│   ├── hooks/
│   ├── stores/                 # Zustand：UI 偏好、通知未读数
│   ├── lib/                    # 格式化（货币、百分比、单位）、日期、配色
│   └── styles/
└── e2e/                        # Playwright
```

### 7.4 数据源适配层契约

```python
class MarketDataProvider(Protocol):
    name: str
    markets: set[str]          # {"US", "HK", "CN"}

    def search(self, query: str) -> list[Instrument]: ...
    def get_quote(self, ticker: str) -> Quote: ...
    def get_history(self, ticker: str, range: str, interval: str) -> list[Bar]: ...
    def get_financials(self, ticker: str, period: str) -> Financials: ...
    def get_news(self, ticker: str) -> list[NewsItem]: ...
    def get_calendar(self, ticker: str) -> CalendarInfo | None: ...
```

- 统一模型使用 Pydantic（`Quote`、`Bar`、`Financials`、`NewsItem`、`Instrument`）。
- Registry 根据代码后缀选择主/备提供器；提供器抛 `ProviderUnavailable`、`TickerNotFound`、`RateLimited`。
- 服务层负责降级、缓存与 `meta` 组装；提供器不直接面向 API。
- 所有网络调用设置超时（连接 5s、读取 10s）与有限重试（最多 2 次，指数退避）。

### 7.5 缓存策略

- **L1**：进程内 TTL 缓存（线程安全），用于 quote/history/news/search。
- **L2**：SQLite 表 `data_cache`，用于财务报表、标的元数据、汇率、预设指数成分；过期后返回 stale 并后台刷新。
- **stale-while-revalidate**：过期数据先返回（标记 `stale=true`），同时触发刷新；刷新失败保留 stale。
- 缓存键包含 ticker、数据类型、关键参数与提供器版本。
- 禁止缓存用户私有数据到共享键。

### 7.6 后台任务

使用 APScheduler（AsyncIOScheduler）：

| 任务 | 频率 | 说明 |
|---|---|---|
| 提醒评估 | 交易时段每 5 分钟 | 按交易所日历；非交易时段跳过 |
| 收盘后每日规则 | 每个市场收盘后 15 分钟 | 财报日、日涨跌幅类规则 |
| 预设指数成分刷新 | 每日 1 次 | S&P 500 / 沪深 300 / 恒生指数 |
| 导出任务清理 | 每日 1 次 | 删除 30 天前文件 |
| 新闻预热（可选） | 自选股每 15 分钟 | 降低首次打开延迟 |

**部署约束**：仅允许一个进程运行调度器（环境变量 `ENABLE_SCHEDULER=true`），API 多 worker 时其他进程设为 false，避免重复通知。

### 7.7 数据库设计（SQLite）

> 所有表包含 `created_at`、`updated_at`（除纯日志表）；外键开启 `PRAGMA foreign_keys=ON`。

| 表 | 关键字段 | 说明 |
|---|---|---|
| `users` | id, email, password_hash, display_name, base_currency, role, is_active | 预留多用户；本期单 owner |
| `sessions` | id, user_id, token_hash, expires_at, revoked_at, user_agent, ip | httpOnly Cookie 会话 |
| `instruments` | ticker(PK), name, market, exchange, currency, provider, is_active, meta_json | 标的元数据缓存 |
| `watchlists` | id, user_id, name, sort_order | 自选分组 |
| `watchlist_items` | id, watchlist_id, ticker, note, sort_order | 唯一约束 (watchlist_id, ticker) |
| `portfolios` | id, user_id, name, base_currency, sort_order | 组合 |
| `positions` | id, portfolio_id, ticker, quantity, avg_cost, currency, opened_at, note | 持仓；数量允许小数 |
| `transactions` | id, portfolio_id, ticker, type(buy/sell/dividend), quantity, price, fee, traded_at, note | P1 |
| `valuation_presets` | id, user_id, ticker(nullable), name, params_json | 估值假设预设 |
| `alert_rules` | id, user_id, ticker, type, params_json, channels_json, cooldown_minutes, is_active, last_triggered_at | 提醒规则 |
| `notifications` | id, user_id, rule_id(nullable), ticker, title, body, level, dedupe_key, is_read, created_at | 站内通知；dedupe_key 唯一 |
| `report_jobs` | id, user_id, ticker, formats_json, status, file_paths_json, error, started_at, finished_at | 导出任务 |
| `screener_presets` | id, user_id, name, universe_json, filters_json | 筛选预设 |
| `user_settings` | user_id, key, value_json | 设置键值 |
| `data_cache` | key(PK), payload_json, source, fetched_at, expires_at | L2 缓存 |
| `news_items` | id, ticker, title, url, source, kind, published_at, fetched_at, hash | 新闻去重缓存 |
| `fx_rates` | base, quote, rate, as_of | 汇率缓存 |

索引建议：
- `watchlist_items(watchlist_id, sort_order)`
- `positions(portfolio_id)`
- `alert_rules(user_id, is_active)`
- `notifications(user_id, is_read, created_at)`
- `news_items(ticker, published_at)`
- `report_jobs(user_id, created_at)`

### 7.8 API 契约（`/api/v1`）

统一响应包：

```json
{
  "data": {},
  "meta": {
    "source": "yfinance",
    "as_of": "2026-11-12T15:30:00+08:00",
    "cached": true,
    "stale": false,
    "missing_fields": [],
    "currency": "USD"
  }
}
```

列表响应：`{"data": {"items": [], "page": 1, "page_size": 50, "total": 0}, "meta": {...}}`

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| POST | `/auth/bootstrap` | 否 | 首次创建 owner；已初始化返回 409 |
| POST | `/auth/login` | 否 | 登录，设置会话 Cookie |
| POST | `/auth/logout` | 是 | 注销当前会话 |
| GET | `/auth/me` | 是 | 当前用户信息 |
| PATCH | `/auth/me` | 是 | 修改显示名/基础货币/密码 |
| GET | `/search?q=` | 是 | 标的搜索 |
| GET | `/stocks/{ticker}/quote` | 是 | 行情与关键指标 |
| GET | `/stocks/{ticker}/history?range=1y&interval=1d&indicators=ma,macd,rsi,boll` | 是 | K 线/收盘价与指标 |
| GET | `/stocks/{ticker}/financials?period=annual&limit=5` | 是 | 财务报表 |
| GET | `/stocks/{ticker}/financials/analysis` | 是 | 规则化解读 |
| GET | `/stocks/{ticker}/news?kind=all` | 是 | 新闻与公告 |
| GET | `/stocks/{ticker}/valuation?growth=&terminal=&discount=&ddm_growth=` | 是 | 基础估值结果 |
| POST | `/stocks/{ticker}/valuation/scenarios` | 是 | 情景估值（Bear/Base/Bull） |
| POST | `/stocks/{ticker}/valuation/reverse` | 是 | 反向 DCF |
| GET | `/stocks/{ticker}/valuation/wacc` | 是 | WACC 计算与默认参数 |
| GET | `/stocks/{ticker}/valuation/bands?metric=pe&years=5` | 是 | 历史估值区间 |
| GET/POST | `/watchlists` | 是 | 列表查询/创建 |
| PATCH/DELETE | `/watchlists/{id}` | 是 | 重命名/删除 |
| POST | `/watchlists/{id}/items` | 是 | 添加标的（重复返回 409） |
| PATCH/DELETE | `/watchlists/{id}/items/{ticker}` | 是 | 备注/排序/移除 |
| GET | `/watchlists/{id}/quotes` | 是 | 批量行情（含失败项） |
| GET/POST | `/portfolios` | 是 | 组合查询/创建 |
| PATCH/DELETE | `/portfolios/{id}` | 是 | 修改/删除 |
| GET/POST | `/portfolios/{id}/positions` | 是 | 持仓查询/新增 |
| PATCH/DELETE | `/portfolios/{id}/positions/{position_id}` | 是 | 修改/删除 |
| GET | `/portfolios/{id}/summary` | 是 | 组合汇总（市值、盈亏、权重、汇率） |
| GET | `/compare?tickers=AAPL,MSFT&range=1y` | 是 | 多股对比 |
| POST | `/screener/run` | 是 | 运行筛选 |
| GET/POST | `/screener/presets` | 是 | 筛选预设 |
| GET/POST | `/alerts` | 是 | 提醒规则查询/创建 |
| PATCH/DELETE | `/alerts/{id}` | 是 | 修改/删除/启停 |
| GET | `/notifications?unread_only=` | 是 | 通知列表 |
| POST | `/notifications/read` | 是 | 批量标记已读 |
| GET | `/notifications/stream` | 是 | SSE 实时通知 |
| POST | `/reports` | 是 | 创建导出任务 |
| GET | `/reports` | 是 | 任务列表 |
| GET | `/reports/{id}` | 是 | 任务状态 |
| GET | `/reports/{id}/download` | 是 | 下载文件 |
| GET/PATCH | `/settings` | 是 | 用户设置 |
| POST | `/settings/cache/clear` | 是 | 清除数据缓存 |
| GET | `/healthz` | 否 | 存活检查 |
| GET | `/readyz` | 否 | 数据库/依赖就绪检查 |

**现有接口迁移映射**

| 现有 | 新接口 |
|---|---|
| `GET /api/quote` | `GET /api/v1/stocks/{ticker}/quote` |
| `GET /api/history` | `GET /api/v1/stocks/{ticker}/history` |
| `GET /api/financials` | `GET /api/v1/stocks/{ticker}/financials` |
| `GET /api/valuation` | `GET /api/v1/stocks/{ticker}/valuation` |

旧接口不保留兼容层；前端同步重写。

### 7.9 错误模型

```json
{
  "error": {
    "code": "DATA_UNAVAILABLE",
    "message": "数据源暂时不可用，请稍后重试",
    "details": {"ticker": "AAPL", "provider": "yfinance"},
    "request_id": "01J..."
  }
}
```

| HTTP | code | 场景 |
|---|---|---|
| 400 | `VALIDATION_ERROR` | 参数格式/范围错误 |
| 401 | `UNAUTHORIZED` | 未登录或会话过期 |
| 403 | `FORBIDDEN` | 访问他人资源 |
| 404 | `NOT_FOUND` / `TICKER_NOT_FOUND` | 资源或代码不存在 |
| 409 | `CONFLICT` | 重复添加、重复初始化、重复运行 |
| 422 | `UNPROCESSABLE` | 计算条件不成立（如 r ≤ g） |
| 429 | `RATE_LIMITED` | 上游或本地限流 |
| 502 | `UPSTREAM_ERROR` | 数据源解析/网络失败 |
| 503 | `DATA_UNAVAILABLE` | 主备源均不可用且无可用缓存 |
| 500 | `INTERNAL` | 未预期异常，日志记录 request_id |

### 7.10 安全设计

- 密码哈希：Argon2id（首选）或 bcrypt；禁止明文与可逆加密。
- 会话：httpOnly + Secure（HTTPS 时）+ SameSite=Lax Cookie；会话令牌仅存哈希。
- CSRF：状态变更请求校验双提交 Token 或 `Origin` 白名单。
- CORS：默认同源；开发环境允许 `http://localhost:5173`。
- 限流：登录接口按 IP 限流；上游数据源按提供器限并发。
- 密钥：`.env` 管理，`.gitignore` 排除；仓库不提交任何 token。
- 输入校验：ticker 格式白名单（字母、数字、`.`、`-`、`^`），长度上限；所有查询参数用 Pydantic 校验。
- 依赖安全：锁定版本；周期性 `pip-audit` / `npm audit`（可选）。
- 日志脱敏：不记录密码、Cookie、完整 token。

### 7.11 可观测性

- 结构化 JSON 日志（structlog），字段：`request_id`、`user_id`、`path`、`status`、`duration_ms`、`provider`、`cache_hit`。
- 请求中间件生成/透传 `X-Request-ID`，错误响应携带 `request_id`。
- `/healthz`：进程存活；`/readyz`：数据库可写、数据目录可写。
- 提供器调用计数与耗时指标（日志聚合即可，本期不引入 Prometheus）。
- 启动时打印版本、数据源、调度器状态、演示模式。

### 7.12 部署

- **Docker Compose**：
  - `api`：FastAPI + uvicorn（单 worker 运行调度器；如需多 worker，拆分 `scheduler` 服务）。
  - `web`：Nginx 托管前端构建产物，反向代理 `/api` 到 `api`（或由 FastAPI 直接托管静态文件，二选一，推荐 Nginx）。
  - 卷：`./data:/data`（SQLite、导出文件）。
  - 健康检查：`/readyz`；依赖 `api` 就绪后再启动 `web`。
- **环境变量**（示例）：

```env
STOCKVAL_ENV=production
STOCKVAL_SECRET_KEY=...            # 会话签名
STOCKVAL_DATABASE_URL=sqlite:////data/stockval.db
STOCKVAL_DATA_DIR=/data
STOCKVAL_ENABLE_SCHEDULER=true
STOCKVAL_DEMO=0
STOCKVAL_ALLOWED_ORIGINS=http://localhost:8080
STOCKVAL_LOG_LEVEL=INFO
STOCKVAL_REPORT_RETENTION_DAYS=30
```

- **本地开发**：后端 `uvicorn app.main:app --reload`，前端 `npm run dev`（Vite 代理 `/api`）。
- **PDF 依赖**：Playwright + Chromium 体积较大；构建镜像时安装浏览器依赖。若体积不可接受，降级为 WeasyPrint（需验证中文字体）。
- **备份**：文档中提供 `data/stockval.db` 与 `data/exports/` 的备份说明；不实现自动云备份。

---

## 8. 非功能需求

| 类别 | 要求 |
|---|---|
| 性能 | 首屏 P95 < 2s（本地）；行情缓存命中 < 300ms；估值纯计算 < 500ms；筛选 500 只标的在缓存冷启动下 < 60s（可显示进度） |
| 可靠性 | 上游失败不导致 500；优先返回 stale 数据并标记；调度器重启不重复通知 |
| 数据质量 | 所有数值经 Pydantic 校验；禁止 NaN/Infinity；缺失字段 100% 标记；A 股交叉校验 |
| 安全 | 密码哈希、httpOnly 会话、CSRF 防护、输入白名单、限流、日志脱敏 |
| 可用性 | 桌面优先，宽度 ≥ 1280px 最佳；≥ 768px 可用；键盘可完成主要操作 |
| 可维护性 | 分层清晰；估值/规则/组合计算为纯函数；类型注解；Alembic 迁移 |
| 测试 | 后端单元 + API 契约 + 前端组件 + 关键 E2E；后端覆盖率 ≥ 70% |
| 本地化 | 中文界面；数字与日期本地化；时区 Asia/Shanghai |
| 可访问性 | 对比度达标；图表提供文字摘要；表单有 label；错误可被屏幕阅读器读取 |
| 兼容性 | 最新两个版本的 Chrome / Edge / Safari / Firefox |

---

## 9. 里程碑与交付计划

> 工期为单人开发估算，按阶段交付，不绑定具体日期。

### M0 架构与基础设施（约 2 周）
- FastAPI 分层骨架、配置、日志、错误模型、健康检查。
- SQLAlchemy + Alembic + SQLite；用户/会话/设置表。
- Provider 抽象与 yfinance 适配器；缓存层。
- React SPA 骨架、路由、布局、设计令牌、API 客户端。
- Docker Compose、CI（lint + pytest + 前端构建）。
- **退出标准**：登录 → 搜索 → 行情页跑通；测试与镜像构建通过。

### M1 功能对齐与基础研究（约 2–3 周）
- 全局搜索、个股概览、历史图表（面积/K 线）、财务表。
- 两阶段 DCF、敏感性、倍数、综合结论（对齐现有能力并提升）。
- 自选股（多分组、批量行情）。
- **退出标准**：现有 Demo 功能全部可在新架构中复现；核心估值 golden tests 通过。

### M2 研究深度与组合（约 3 周）
- 财务规则化解读。
- 估值增强：WACC、情景、反向 DCF、历史估值区间、多阶段 DDM、加权综合、预设保存。
- 投资组合（持仓、汇总、汇率、盈亏）。
- 多股对比、筛选器。
- 技术指标（MA/BOLL/MACD/RSI）。
- **退出标准**：研究闭环完整；组合与筛选的边界测试通过。

### M3 跟踪与信息流（约 2 周）
- 新闻与公告聚合、去重、缓存。
- 提醒规则、调度评估、SSE 通知、浏览器桌面通知、通知中心。
- **退出标准**：提醒冷却与去重有效；非交易时段不误触发。

### M4 交付与打磨（约 2 周）
- PDF / Excel 报告导出、任务状态与文件保留。
- 设置页、演示模式横幅、免责声明、空状态与错误态统一。
- 数据质量看板（缺失字段、stale、交叉校验差异）。
- 性能优化、E2E 测试、部署文档。
- **退出标准**：全部 P0/P1 验收标准通过；Docker 一键启动；文档齐备。

### M5 持续加固（长期）
- 数据源稳定性、字段映射回归、备份与恢复演练。
- 可选：浅色主题、更多指标、回测（另立 PRD）。

---

## 10. 风险与应对

| 风险 | 影响 | 应对 |
|---|---|---|
| yfinance 非官方接口变动/限流 | 行情与财务不可用 | Provider 隔离 + 契约 fixture 测试 + 重试 + stale 缓存 + 明确错误；后续可接商业 API |
| akshare 数据口径/字段命名不稳定 | A 股财务映射失败或数值错误 | 字段候选列表 + 交叉校验 + 缺失标记 + 回归测试 |
| 历史财务数据不足 | 历史估值区间、3 年 CAGR 无法计算 | 明确「数据不足」并列出缺失项，不强行计算 |
| PDF 生成依赖 Chromium | 镜像体积大、构建慢 | 独立构建阶段；备选 WeasyPrint；报告中文字体自测 |
| 后台调度与多 worker 冲突 | 重复通知 | 单调度进程 + 数据库去重键 + 分布式锁（SQLite 可用事务） |
| 免费数据源无 SLA | 提醒延迟或失败 | UI 标注数据延迟；失败记录与重试；不承诺实时 |
| 多用户预留但实际单用户 | 权限设计过度或不足 | owner-scoped 查询强制注入 user_id；API 测试覆盖越权 |
| 功能范围过大 | 交付延期 | 严格按 P0/P1 阶段交付；P1 可顺延；P2 不承诺 |
| 红涨绿跌与现有实现不一致 | 用户认知冲突 | 默认红涨绿跌并在设置中可切换；迁移说明中标注 |

---

## 11. 开放问题（需确认）

| # | 问题 | 建议默认 |
|---|---|---|
| Q1 | 涨跌配色默认红涨绿跌还是绿涨红跌？当前 Demo 为绿涨红跌 | 红涨绿跌，设置可切换 |
| Q2 | 预设指数范围是否只做 S&P 500 / 沪深 300 / 恒生指数？ | 是，后续可扩展 |
| Q3 | 是否需要季度财务报表？ | 需要，P1 |
| Q4 | PDF 报告是否包含新闻列表？ | 不包含，避免正文版权与时效问题 |
| Q5 | 提醒是否仅在交易时段评估？非交易时段的阈值提醒如何处理？ | 仅交易时段；收盘后评估一次每日类规则 |
| Q6 | 组合是否需要交易流水与已实现盈亏？ | P1，先做持仓与未实现盈亏 |
| Q7 | 数据保留与备份策略？ | SQLite + 导出文件保留 30 天；手动备份说明 |
| Q8 | 是否允许局域网访问与首次初始化？ | 默认仅本机监听；通过环境变量开启局域网，初始化后关闭注册 |
| Q9 | 是否接受 Playwright/Chromium 的镜像体积？ | 接受；若不可接受则改用 WeasyPrint |
| Q10 | 是否需要移动端完整适配？ | 基础响应式，不承诺复杂图表在手机上的完整体验 |
| Q11 | 筛选器预设指数成分股来源与更新频率？ | 每日一次，缓存；来源失败沿用旧数据并标记 |
| Q12 | 估值默认假设是否按市场区分（A 股/美股不同折现率）？ | 按币种预填无风险利率，其余统一默认 |

---

## 12. 附录

### 12.1 估值公式

| 模型 | 公式 |
|---|---|
| CAPM | `r_e = r_f + β × ERP` |
| WACC | `WACC = E/(D+E) × r_e + D/(D+E) × r_d × (1 − t)` |
| 两阶段 DCF | `FCF_t = FCF_0 × (1+g)^t`；`TV = FCF_n × (1+g_T)/(r − g_T)`；`EV = Σ FCF_t/(1+r)^t + TV/(1+r)^n`；`Equity = EV − Debt + Cash`；`每股 = Equity / Shares` |
| 三阶段 DCF | 前 5 年 `g1`；第 6–10 年线性衰减至 `g_T`；第 10 年后永续 `g_T` |
| Gordon DDM | `V = DPS × (1+g) / (r − g)` |
| Graham | `V = √(22.5 × EPS × BVPS)` |
| 反向 DCF | 求解 `g` 使 `DCF(g) = Price`；二分法，区间 `[−50%, 100%]`，容差 `0.01%` |
| 敏感性 | 折现率 `r ± {0,1,2}pp` × 永续增速 `{1.5,2.5,3.5}%` |
| FCF Yield | `FCF / Market Cap` |
| 历史分位 | 当前指标在 3/5 年历史序列中的百分位（10/25/50/75/90） |

### 12.2 财务字段映射（示例）

| 统一字段 | yfinance | akshare（示例，需实现时校验） |
|---|---|---|
| revenue | `Total Revenue` | 营业收入 |
| gross_profit | `Gross Profit` | 营业总收入/毛利（按可得字段） |
| operating_income | `Operating Income` | 营业利润 |
| net_income | `Net Income` / `Net Income Common Stockholders` | 净利润 |
| operating_cash_flow | `Operating Cash Flow` / `Total Cash From Operating Activities` | 经营活动产生的现金流量净额 |
| capex | `Capital Expenditure` | 购建固定资产、无形资产和其他长期资产支付的现金 |
| free_cash_flow | `Free Cash Flow`，否则 OCF + capex | 同上推导 |
| total_debt | `Total Debt` | 负债合计/有息负债（口径需确认） |
| cash | `Cash And Cash Equivalents` / `Cash Cash Equivalents And Short Term Investments` | 货币资金 |
| equity | `Stockholders Equity` / `Total Equity Gross Minority Interest` / `Common Stock Equity` | 所有者权益合计 |
| shares_outstanding | `sharesOutstanding` | 总股本 |

> A 股字段命名与口径以实现时 akshare 实际返回为准，必须通过 fixture 回归测试固化。

### 12.3 术语表

| 术语 | 说明 |
|---|---|
| FCF | 自由现金流，本产品定义为经营现金流 − 资本开支 |
| TTM | 滚动十二个月 |
| EV | 企业价值 = 市值 + 总债务 − 现金 |
| stale | 缓存已过期但被降级返回的数据，必须标记 |
| 百分点（pp） | 两个百分数之差，如 20% 与 18% 相差 2pp |
| owner | 本期唯一用户角色 |

---

## 13. 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.0 | 2026-11-12 | 初始 PRD：确定产品定位、FastAPI + React 架构、全量功能规格与分期计划 |
