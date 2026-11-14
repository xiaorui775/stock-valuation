/** 筛选器：股票池 + 条件 + 排序分页（§5.11）。
 *
 * 取数与计算都在后端；这里只负责组条件、展示结果与失败原因。
 * 指数股票池（S&P 500 / 沪深 300 / 恒生）依赖成分股刷新，属于 M2-13。
 */
import { useState } from "react";
import { useWatchlists } from "@/api/watchlists";
import {
  useIndexes,
  useScreen,
  useScreenerPresetMutations,
  useScreenerPresets,
  type MarketKey,
  type MetricKey,
  type ScreenerFilter,
  type ScreenerPreset,
  type ScreenerRequest,
  type ScreenerResult,
} from "@/api/screener";
import { DASH, fmtBig, fmtNum, fmtPct, marketLabel, valuationClass } from "@/lib/format";

type Unit = "pct" | "x" | "money" | "number";

const METRICS: { key: MetricKey; label: string; unit: Unit }[] = [
  { key: "market_cap", label: "市值", unit: "money" },
  { key: "pe_ttm", label: "P/E", unit: "x" },
  { key: "forward_pe", label: "Forward P/E", unit: "x" },
  { key: "peg", label: "PEG", unit: "x" },
  { key: "price_to_book", label: "P/B", unit: "x" },
  { key: "price_to_sales", label: "P/S", unit: "x" },
  { key: "ev_ebitda", label: "EV/EBITDA", unit: "x" },
  { key: "dividend_yield", label: "股息率", unit: "pct" },
  { key: "revenue_growth", label: "营收增速", unit: "pct" },
  { key: "fcf_yield", label: "FCF Yield", unit: "pct" },
  { key: "dcf_upside_pct", label: "DCF 上行空间", unit: "pct" },
  { key: "beta", label: "Beta", unit: "number" },
];

const METRIC_BY_KEY = Object.fromEntries(METRICS.map((m) => [m.key, m])) as Record<
  MetricKey,
  (typeof METRICS)[number]
>;

const MARKETS: { key: MarketKey; label: string }[] = [
  { key: "US", label: "美股" },
  { key: "HK", label: "港股" },
  { key: "CN", label: "A股" },
];

const PAGE_SIZE = 50;

interface FilterDraft {
  id: number;
  metric: MetricKey;
  min: string;
  max: string;
}

export default function ScreenerPage() {
  const screen = useScreen();
  const watchlists = useWatchlists();
  const indexes = useIndexes();
  const presets = useScreenerPresets();
  const presetMutations = useScreenerPresetMutations();

  const [poolKind, setPoolKind] = useState<"custom" | "watchlist" | "index">("custom");
  const [tickerText, setTickerText] = useState("");
  const [watchlistId, setWatchlistId] = useState<number | "">("");
  const [indexKey, setIndexKey] = useState("");
  const [markets, setMarkets] = useState<MarketKey[]>([]);
  const [filters, setFilters] = useState<FilterDraft[]>([]);
  const [sortKey, setSortKey] = useState<MetricKey | "">("");
  const [sortDesc, setSortDesc] = useState(false);
  const [lastBody, setLastBody] = useState<ScreenerRequest | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [presetName, setPresetName] = useState("");
  const [presetMessage, setPresetMessage] = useState<string | null>(null);

  const tickers = tickerText
    .split(/[\s,，]+/)
    .map((item) => item.trim().toUpperCase())
    .filter(Boolean);

  const result = screen.data?.data;

  function addFilter() {
    setFilters((prev) => [
      ...prev,
      { id: Date.now() + prev.length, metric: "pe_ttm", min: "", max: "" },
    ]);
  }

  function updateFilter(id: number, patch: Partial<FilterDraft>) {
    setFilters((prev) => prev.map((item) => (item.id === id ? { ...item, ...patch } : item)));
  }

  function buildBody(page: number): ScreenerRequest | null {
    setFormError(null);
    const pool =
      poolKind === "custom"
        ? { kind: "custom" as const, tickers }
        : poolKind === "watchlist"
          ? { kind: "watchlist" as const, watchlist_id: watchlistId === "" ? null : watchlistId }
          : { kind: "index" as const, index_key: indexKey || null };
    if (poolKind === "custom" && tickers.length === 0) {
      setFormError("请先在自定义股票池里填写代码");
      return null;
    }
    if (poolKind === "watchlist" && watchlistId === "") {
      setFormError("请选择一个自选分组");
      return null;
    }
    if (poolKind === "index" && !indexKey) {
      setFormError("请选择一个预设指数");
      return null;
    }
    const parsed: ScreenerFilter[] = [];
    for (const item of filters) {
      const min = item.min.trim() === "" ? null : Number(item.min);
      const max = item.max.trim() === "" ? null : Number(item.max);
      if (min === null && max === null) continue;
      if (min !== null && max !== null && min > max) {
        setFormError(`${METRIC_BY_KEY[item.metric].label} 的下限大于上限`);
        return null;
      }
      parsed.push({ metric: item.metric, min, max });
    }
    return {
      pool,
      market: markets.length ? markets : null,
      filters: parsed,
      sort_key: sortKey === "" ? null : sortKey,
      sort_desc: sortDesc,
      page,
      page_size: PAGE_SIZE,
    };
  }

  function run() {
    const body = buildBody(1);
    if (!body) return;
    setLastBody(body);
    screen.mutate(body);
  }

  function goPage(page: number) {
    if (!lastBody) return;
    const body = { ...lastBody, page };
    setLastBody(body);
    screen.mutate(body);
  }

  const totalPages = result ? Math.max(1, Math.ceil(result.total / result.page_size)) : 1;

  function loadPreset(preset: ScreenerPreset) {
    const payload = preset.payload;
    setPresetMessage(`已加载「${preset.name}」`);
    setPoolKind(payload.pool.kind);
    setTickerText((payload.pool.tickers ?? []).join(", "));
    setWatchlistId(payload.pool.watchlist_id ?? "");
    setIndexKey(payload.pool.index_key ?? "");
    setMarkets(payload.market ?? []);
    setSortKey(payload.sort_key ?? "");
    setSortDesc(Boolean(payload.sort_desc));
    setFilters(
      (payload.filters ?? []).map((item, index) => ({
        id: Date.now() + index,
        metric: item.metric,
        min: item.min == null ? "" : String(item.min),
        max: item.max == null ? "" : String(item.max),
      })),
    );
    setLastBody({ ...payload, page: 1 });
    screen.mutate({ ...payload, page: 1 });
  }

  return (
    <div className="space-y-4">
      <div className="flex items-baseline justify-between gap-3 flex-wrap">
        <h1 className="text-xl font-bold">筛选器</h1>
        <span className="note">
          股票池上限 500 只 · 并发 4 · 命中缓存优先
        </span>
      </div>

      <div className="card space-y-4">
        <div>
          <h2 className="card-title">股票池</h2>
          <div className="flex gap-2 mb-2">
            <button
              type="button"
              className={`btn text-xs ${poolKind === "custom" ? "btn-primary" : "btn-ghost"}`}
              onClick={() => setPoolKind("custom")}
            >
              自定义代码
            </button>
            <button
              type="button"
              className={`btn text-xs ${poolKind === "watchlist" ? "btn-primary" : "btn-ghost"}`}
              onClick={() => setPoolKind("watchlist")}
            >
              自选分组
            </button>
            <button
              type="button"
              className={`btn text-xs ${poolKind === "index" ? "btn-primary" : "btn-ghost"}`}
              onClick={() => setPoolKind("index")}
            >
              预设指数
            </button>
          </div>

          {poolKind === "index" ? (
            <div>
              <select
                className="input w-64"
                aria-label="预设指数"
                value={indexKey}
                onChange={(e) => setIndexKey(e.target.value)}
              >
                <option value="">选择预设指数…</option>
                {(indexes.data?.data ?? []).map((item) => (
                  <option key={item.key} value={item.key}>
                    {item.label}（{item.count} 只）
                  </option>
                ))}
              </select>
              {(() => {
                const current = (indexes.data?.data ?? []).find((item) => item.key === indexKey);
                if (!current) return null;
                return (
                  <p className="note mt-1">
                    来源：{current.source} · 更新于 {formatDate(current.updated_at)}。
                    成分股会随指数调整变化，结果以该名单为准。
                  </p>
                );
              })()}
            </div>
          ) : poolKind === "custom" ? (
            <>
              <textarea
                className="input w-full h-20"
                placeholder="输入代码，用逗号、空格或换行分隔，例如：AAPL, MSFT, 0700.HK, 600519.SS"
                value={tickerText}
                onChange={(e) => setTickerText(e.target.value)}
              />
              <p className="note mt-1">已识别 {tickers.length} 个代码（去重后）</p>
            </>
          ) : (
            <select
              className="input w-56"
              aria-label="自选分组"
              value={watchlistId}
              onChange={(e) =>
                setWatchlistId(e.target.value === "" ? "" : Number(e.target.value))
              }
            >
              <option value="">选择自选分组…</option>
              {(watchlists.data?.data.groups ?? []).map((group) => (
                <option key={group.id} value={group.id}>
                  {group.name}（{group.items.length}）
                </option>
              ))}
            </select>
          )}
        </div>

        <div>
          <h2 className="card-title">市场</h2>
          <div className="flex gap-3 text-sm">
            {MARKETS.map((market) => (
              <label key={market.key} className="flex items-center gap-1.5">
                <input
                  type="checkbox"
                  checked={markets.includes(market.key)}
                  onChange={() =>
                    setMarkets((prev) =>
                      prev.includes(market.key)
                        ? prev.filter((item) => item !== market.key)
                        : [...prev, market.key],
                    )
                  }
                />
                {market.label}
              </label>
            ))}
            <span className="note self-center">不勾选表示不限市场</span>
          </div>
        </div>

        <div>
          <div className="flex items-center gap-2 mb-2">
            <h2 className="card-title mb-0">筛选条件</h2>
            <button type="button" className="btn btn-ghost text-xs" onClick={addFilter}>
              添加条件
            </button>
          </div>
          {filters.length === 0 ? (
            <p className="note">没有条件时返回股票池中全部可用标的（仍受分页限制）。</p>
          ) : (
            <div className="space-y-2">
              {filters.map((item) => (
                <div key={item.id} className="flex items-center gap-2 flex-wrap text-sm">
                  <select
                    className="input w-40"
                    aria-label="筛选指标"
                    value={item.metric}
                    onChange={(e) =>
                      updateFilter(item.id, { metric: e.target.value as MetricKey })
                    }
                  >
                    {METRICS.map((metric) => (
                      <option key={metric.key} value={metric.key}>
                        {metric.label}
                      </option>
                    ))}
                  </select>
                  <input
                    className="input w-28"
                    type="number"
                    placeholder="下限"
                    aria-label="下限"
                    value={item.min}
                    onChange={(e) => updateFilter(item.id, { min: e.target.value })}
                  />
                  <span className="text-muted">–</span>
                  <input
                    className="input w-28"
                    type="number"
                    placeholder="上限"
                    aria-label="上限"
                    value={item.max}
                    onChange={(e) => updateFilter(item.id, { max: e.target.value })}
                  />
                  <span className="note">
                    {METRIC_BY_KEY[item.metric].unit === "pct" ? "百分点（10 = 10%）" : ""}
                  </span>
                  <button
                    type="button"
                    className="btn btn-ghost text-xs"
                    onClick={() => setFilters((prev) => prev.filter((f) => f.id !== item.id))}
                  >
                    移除
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="flex items-end gap-3 flex-wrap">
          <label className="flex flex-col gap-1 text-xs">
            <span className="text-muted">排序</span>
            <select
              className="input w-40"
              value={sortKey}
              onChange={(e) => setSortKey(e.target.value as MetricKey | "")}
            >
              <option value="">不排序</option>
              {METRICS.map((metric) => (
                <option key={metric.key} value={metric.key}>
                  {metric.label}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            className="btn btn-ghost text-xs"
            disabled={sortKey === ""}
            onClick={() => setSortDesc((prev) => !prev)}
          >
            {sortDesc ? "降序 ↓" : "升序 ↑"}
          </button>
          <button
            type="button"
            className="btn btn-primary"
            disabled={screen.isPending}
            onClick={run}
          >
            {screen.isPending ? "筛选中…" : "开始筛选"}
          </button>
          {formError && <span className="text-red text-xs">{formError}</span>}
          {screen.isError && (
            <span className="text-red text-xs">
              {(screen.error as Error)?.message ?? "筛选失败"}
            </span>
          )}
        </div>
      </div>

      <PresetBar
        presets={presets.data?.data ?? []}
        name={presetName}
        onName={setPresetName}
        message={presetMessage}
        busy={presetMutations.createPreset.isPending || presetMutations.deletePreset.isPending}
        onSave={() => {
          const body = buildBody(1);
          if (!body) return;
          const name = presetName.trim();
          if (!name) {
            setPresetMessage("请先填写预设名称");
            return;
          }
          presetMutations.createPreset.mutate(
            { name, payload: body },
            {
              onSuccess: () => {
                setPresetName("");
                setPresetMessage(`已保存「${name}」`);
              },
              onError: (error) => setPresetMessage((error as Error).message),
            },
          );
        }}
        onLoad={(preset) => loadPreset(preset)}
        onDelete={(preset) => {
          if (!window.confirm(`删除筛选预设「${preset.name}」？`)) return;
          presetMutations.deletePreset.mutate(preset.id, {
            onError: (error) => setPresetMessage((error as Error).message),
          });
        }}
      />

      {result && <ResultBlock result={result} page={result.page} totalPages={totalPages} onPage={goPage} />}
    </div>
  );
}

function ResultBlock({
  result,
  page,
  totalPages,
  onPage,
}: {
  result: ScreenerResult;
  page: number;
  totalPages: number;
  onPage: (page: number) => void;
}) {
  return (
    <div className="card">
        <div className="flex items-baseline justify-between gap-3 flex-wrap">
          <h2 className="card-title mb-0">结果</h2>
          <span className="note">
            匹配 {result.total} 只 · 已获取 {result.succeeded}/{result.requested}
            {result.failed > 0 && ` · 失败 ${result.failed}`} · 用时{" "}
            {(result.elapsed_ms / 1000).toFixed(1)} 秒（预计 {result.estimate_seconds} 秒）
          </span>
        </div>
        <p className="note mt-1">{result.note} DCF 上行空间使用统一默认假设。</p>

        {result.failures.length > 0 && (
          <details className="mt-2">
            <summary className="text-xs text-muted cursor-pointer">
              查看 {result.failures.length} 条失败原因
            </summary>
            <ul className="mt-1 space-y-1">
              {result.failures.map((item) => (
                <li key={item.ticker} className="note">
                  {item.ticker}：{item.reason}
                </li>
              ))}
            </ul>
          </details>
        )}

        {result.rows.length === 0 ? (
          <p className="note mt-3">没有符合条件的标的，试着放宽条件或缩小股票池。</p>
        ) : (
          <div className="overflow-x-auto mt-3">
            <table className="w-full text-sm whitespace-nowrap">
              <thead>
                <tr className="text-muted text-xs border-b border-line">
                  <th className="text-left font-medium py-1.5">代码 / 名称</th>
                  <th className="text-left font-medium py-1.5 pl-2">市场</th>
                  <th className="text-right font-medium py-1.5 px-2">现价</th>
                  {METRICS.map((metric) => (
                    <th key={metric.key} className="text-right font-medium py-1.5 px-2">
                      {metric.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.rows.map((row) => (
                  <tr key={row.ticker} className="border-b border-line">
                    <td className="py-1.5">
                      <span className="font-semibold">{row.ticker}</span>
                      <span className="note ml-2">{row.name}</span>
                    </td>
                    <td className="pl-2">
                      {marketLabel(row.market)}
                      {row.currency && <span className="note ml-1">{row.currency}</span>}
                    </td>
                    <td className="text-right tabular-nums px-2">{fmtNum(row.price)}</td>
                    {METRICS.map((metric) => {
                      const value = row[metric.key];
                      return (
                        <td
                          key={metric.key}
                          className={`text-right tabular-nums px-2 ${
                            metric.key === "dcf_upside_pct" ? valuationClass(value) : ""
                          }`}
                        >
                          {formatValue(metric.unit, value)}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {totalPages > 1 && (
          <div className="flex items-center gap-2 mt-3 text-xs">
            <button
              type="button"
              className="btn btn-ghost text-xs"
              disabled={page <= 1}
              onClick={() => onPage(page - 1)}
            >
              上一页
            </button>
            <span className="note">
              第 {page} / {totalPages} 页
            </span>
            <button
              type="button"
              className="btn btn-ghost text-xs"
              disabled={page >= totalPages}
              onClick={() => onPage(page + 1)}
            >
              下一页
            </button>
          </div>
        )}
    </div>
  );
}

function formatValue(unit: Unit, value: number | null): string {
  if (value === null || value === undefined) return DASH;
  if (unit === "pct") return fmtPct(value, 2);
  if (unit === "money") return fmtBig(value);
  return fmtNum(value, 2);
}

function PresetBar({
  presets,
  name,
  onName,
  message,
  busy,
  onSave,
  onLoad,
  onDelete,
}: {
  presets: ScreenerPreset[];
  name: string;
  onName: (value: string) => void;
  message: string | null;
  busy: boolean;
  onSave: () => void;
  onLoad: (preset: ScreenerPreset) => void;
  onDelete: (preset: ScreenerPreset) => void;
}) {
  return (
    <div className="card">
      <h2 className="card-title">筛选预设</h2>
      <p className="note mb-2">
        保存当前股票池、条件与排序；加载后会立即按保存时的设置重跑一次。
      </p>
      <div className="flex gap-2 flex-wrap items-center">
        <input
          className="input w-48"
          placeholder="预设名称"
          aria-label="预设名称"
          value={name}
          onChange={(e) => onName(e.target.value)}
        />
        <button type="button" className="btn btn-primary text-xs" disabled={busy} onClick={onSave}>
          保存当前条件
        </button>
        {message && <span className="note">{message}</span>}
      </div>
      {presets.length > 0 && (
        <div className="mt-3 space-y-1">
          {presets.map((preset) => (
            <div
              key={preset.id}
              className="flex items-center justify-between gap-2 py-1 border-b border-line text-sm"
            >
              <span>
                {preset.name}
                <span className="note ml-2">
                  {poolLabel(preset.payload.pool)} · 更新于 {formatDate(preset.updated_at)}
                </span>
              </span>
              <span className="flex gap-1">
                <button
                  type="button"
                  className="btn btn-ghost text-xs"
                  onClick={() => onLoad(preset)}
                >
                  加载
                </button>
                <button
                  type="button"
                  className="btn btn-ghost text-xs"
                  onClick={() => onDelete(preset)}
                >
                  删除
                </button>
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function poolLabel(pool: ScreenerRequest["pool"]): string {
  if (pool.kind === "index") return `预设指数 ${pool.index_key ?? ""}`;
  if (pool.kind === "watchlist") return "自选分组";
  return `${(pool.tickers ?? []).length} 个代码`;
}

function formatDate(value: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("zh-CN");
}
