/** 自选股：多分组、增删、排序与批量行情（FR-WATCH-01 ~ 05）。 */
import { useMemo, useRef, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import {
  useWatchlistMutations,
  useWatchlistQuotes,
  useWatchlists,
  type WatchlistGroup,
  type WatchlistQuote,
} from "@/api/watchlists";
import {
  DASH,
  changeClass,
  fmtBig,
  fmtNum,
  fmtPct,
  valuationClass,
} from "@/lib/format";

type ColumnKey =
  | "price"
  | "change"
  | "marketCap"
  | "pe"
  | "forwardPe"
  | "dividend"
  | "fcfYield"
  | "dcfUpside"
  | "earnings"
  | "asOf";

type SortKey = "change" | "upside";

const COLUMNS: {
  key: ColumnKey;
  label: string;
  sort?: SortKey;
  render: (quote: WatchlistQuote | undefined) => ReactNode;
}[] = [
  { key: "price", label: "现价", render: (q) => fmtNum(q?.price ?? null) },
  {
    key: "change",
    label: "涨跌幅",
    sort: "change",
    render: (q) => (
      <span className={changeClass(q?.change_pct ?? null)}>
        {fmtPct(q?.change_pct ?? null, 2, true)}
      </span>
    ),
  },
  { key: "marketCap", label: "市值", render: (q) => fmtBig(q?.market_cap ?? null) },
  { key: "pe", label: "P/E", render: (q) => fmtNum(q?.pe_ttm ?? null) },
  {
    key: "forwardPe",
    label: "Forward P/E",
    render: (q) => fmtNum(q?.forward_pe ?? null),
  },
  {
    key: "dividend",
    label: "股息率",
    render: (q) => fmtPct(q?.dividend_yield ?? null, 2),
  },
  {
    key: "fcfYield",
    label: "FCF Yield",
    render: (q) => (q?.fcf_yield == null ? DASH : fmtPct(q.fcf_yield, 2)),
  },
  {
    key: "dcfUpside",
    label: "DCF 上行",
    sort: "upside",
    render: (q) => (
      <span className={valuationClass(q?.dcf_upside_pct ?? null)}>
        {fmtPct(q?.dcf_upside_pct ?? null, 1, true)}
      </span>
    ),
  },
  {
    key: "earnings",
    label: "下次财报",
    render: (q) =>
      q?.earnings_date ? (
        <span title={q.earnings_source ? `来源：${q.earnings_source}` : undefined}>
          {q.earnings_date}
          {q.days_until_earnings != null && (
            <span className="note ml-1">{q.days_until_earnings} 天</span>
          )}
        </span>
      ) : (
        DASH
      ),
  },
  { key: "asOf", label: "数据时间", render: (q) => fmtTime(q?.as_of ?? null) },
];

const ALL_COLUMNS = COLUMNS.map((c) => c.key);

/** 默认只展示核心四列，宽表按需通过「列」开关展开，避免页面横向滚动。 */
const DEFAULT_COLUMNS: ColumnKey[] = ["price", "change", "pe", "dcfUpside"];

const MARKETS: { key: "ALL" | "US" | "HK" | "CN"; label: string }[] = [
  { key: "ALL", label: "全部" },
  { key: "US", label: "美股" },
  { key: "HK", label: "港股" },
  { key: "CN", label: "A股" },
];

export default function WatchlistPage() {
  const { data, isLoading, isError, error } = useWatchlists();
  const m = useWatchlistMutations();

  const [activeId, setActiveId] = useState<number | null>(null);
  const [newGroupName, setNewGroupName] = useState("");
  const [tickerInput, setTickerInput] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");
  const [dragId, setDragId] = useState<number | null>(null);

  const [visible, setVisible] = useState<ColumnKey[]>(DEFAULT_COLUMNS);
  const [marketFilter, setMarketFilter] = useState<"ALL" | "US" | "HK" | "CN">("ALL");
  const [sort, setSort] = useState<{ key: SortKey; desc: boolean } | null>(null);

  const groups = data?.data.groups ?? [];
  const active = groups.find((g) => g.id === activeId) ?? groups[0];
  const quotes = useWatchlistQuotes(active?.id ?? null);

  // 刷新失败的行沿用上一次成功的数据，并标记 stale（FR-WATCH-05）
  const lastGood = useRef<Record<string, WatchlistQuote>>({});
  const quoteMap = useMemo(() => {
    const map: Record<string, WatchlistQuote> = {};
    for (const quote of quotes.data?.data.items ?? []) {
      if (!quote.error) {
        lastGood.current[quote.ticker] = quote;
        map[quote.ticker] = quote;
      } else {
        const previous = lastGood.current[quote.ticker];
        map[quote.ticker] = previous
          ? { ...previous, stale: true, error: quote.error }
          : quote;
      }
    }
    return map;
  }, [quotes.data]);

  const rows = useMemo(() => {
    if (!active) return [];
    const list = active.items
      .filter(
        (item) =>
          marketFilter === "ALL" ||
          (quoteMap[item.ticker]?.market ?? item.market) === marketFilter,
      )
      .map((item) => ({ item, quote: quoteMap[item.ticker] }));
    if (!sort) return list;
    const pick = (row: (typeof list)[number]) =>
      sort.key === "change" ? row.quote?.change_pct : row.quote?.dcf_upside_pct;
    return [...list].sort((a, b) => {
      const va = pick(a) ?? null;
      const vb = pick(b) ?? null;
      if (va === null && vb === null) return 0;
      if (va === null) return 1;
      if (vb === null) return -1;
      return sort.desc ? vb - va : va - vb;
    });
  }, [active, marketFilter, sort, quoteMap]);

  const canReorder = !sort && marketFilter === "ALL";

  if (isLoading) return <p className="note">正在加载自选股 …</p>;
  if (isError)
    return <p className="text-red text-sm">{(error as Error)?.message ?? "加载失败"}</p>;

  async function createGroup() {
    const name = newGroupName.trim();
    if (!name) return;
    try {
      const created = await m.createGroup.mutateAsync(name);
      setNewGroupName("");
      setActiveId(created.data.id);
      setMessage(null);
    } catch (e) {
      setMessage((e as Error).message);
    }
  }

  function startRename(group: WatchlistGroup) {
    setEditingId(group.id);
    setEditName(group.name);
  }

  async function saveRename() {
    if (editingId === null) return;
    const name = editName.trim();
    setEditingId(null);
    if (!name) return;
    try {
      await m.renameGroup.mutateAsync({ id: editingId, name });
      setMessage(null);
    } catch (e) {
      setMessage((e as Error).message);
    }
  }

  async function removeGroup(group: WatchlistGroup) {
    if (
      !window.confirm(`删除分组「${group.name}」及其 ${group.items.length} 只标的？`)
    )
      return;
    try {
      await m.deleteGroup.mutateAsync(group.id);
      if (activeId === group.id) setActiveId(null);
      setMessage(null);
    } catch (e) {
      setMessage((e as Error).message);
    }
  }

  function moveGroup(index: number, delta: number) {
    const ids = groups.map((g) => g.id);
    const target = index + delta;
    if (target < 0 || target >= ids.length) return;
    [ids[index], ids[target]] = [ids[target], ids[index]];
    m.reorderGroups.mutate(ids);
  }

  async function addTickers() {
    if (!active) return;
    const tickers = tickerInput
      .split(/[\s,，;；]+/)
      .map((t) => t.trim())
      .filter(Boolean);
    if (tickers.length === 0) return;
    try {
      if (tickers.length === 1) {
        await m.addItem.mutateAsync({ groupId: active.id, ticker: tickers[0] });
        setMessage(null);
      } else {
        const result = await m.addItems.mutateAsync({
          groupId: active.id,
          tickers,
        });
        const failed = result.data.failed;
        setMessage(
          failed.length
            ? `已添加 ${result.data.added.length} 只；未添加：${failed
                .map((f) => `${f.ticker}（${f.reason}）`)
                .join("；")}`
            : `已添加 ${result.data.added.length} 只。`,
        );
      }
      setTickerInput("");
    } catch (e) {
      setMessage((e as Error).message);
    }
  }

  function reorderItems(itemIds: number[]) {
    if (!active) return;
    m.reorderItems.mutate({ groupId: active.id, itemIds });
  }

  function moveItem(index: number, delta: number) {
    if (!active) return;
    const ids = active.items.map((i) => i.id);
    const target = index + delta;
    if (target < 0 || target >= ids.length) return;
    [ids[index], ids[target]] = [ids[target], ids[index]];
    reorderItems(ids);
  }

  function dropOn(targetId: number) {
    if (!active || dragId === null || dragId === targetId) return;
    const ids = active.items.map((i) => i.id).filter((id) => id !== dragId);
    const at = ids.indexOf(targetId);
    ids.splice(at < 0 ? ids.length : at, 0, dragId);
    setDragId(null);
    reorderItems(ids);
  }

  function toggleSort(key: SortKey) {
    setSort((current) =>
      current?.key === key ? { key, desc: !current.desc } : { key, desc: true },
    );
  }

  function toggleColumn(key: ColumnKey) {
    setVisible((current) =>
      current.includes(key)
        ? current.filter((k) => k !== key)
        : ALL_COLUMNS.filter((k) => current.includes(k) || k === key),
    );
  }

  return (
    <div>
      <div className="flex justify-between items-center gap-3 flex-wrap mb-4">
        <h1 className="text-xl font-bold">自选股</h1>
        <div className="flex gap-2 items-center">
          <input
            className="input w-40"
            placeholder="新分组名称"
            maxLength={80}
            value={newGroupName}
            onChange={(e) => setNewGroupName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void createGroup();
            }}
          />
          <button
            className="btn btn-ghost"
            type="button"
            onClick={() => void createGroup()}
          >
            新建分组
          </button>
        </div>
      </div>

      {message && <p className="text-accent text-xs mb-3">{message}</p>}

      <div className="grid gap-3 md:grid-cols-[188px_1fr] items-start">
        <aside className="card !p-1.5">
          <div className="note px-2 py-1.5">分组</div>
          {groups.length === 0 && <p className="note px-2 py-1">还没有分组。</p>}
          {groups.map((group, index) => (
            <div
              key={group.id}
              className={`flex items-center rounded-md border-l-2 ${
                active?.id === group.id
                  ? "border-accent bg-panel2"
                  : "border-transparent"
              }`}
            >
              {editingId === group.id ? (
                <input
                  autoFocus
                  className="input flex-1 !py-1 mx-1 my-0.5"
                  value={editName}
                  maxLength={80}
                  onChange={(e) => setEditName(e.target.value)}
                  onBlur={() => void saveRename()}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") void saveRename();
                    if (e.key === "Escape") setEditingId(null);
                  }}
                />
              ) : (
                <button
                  type="button"
                  className="flex-1 min-w-0 text-left text-sm truncate bg-transparent border-0 text-text cursor-pointer p-0"
                  onClick={() => setActiveId(group.id)}
                >
                  <span className="truncate">{group.name}</span>
                  <span className="note ml-1.5">{group.items.length}</span>
                </button>
              )}
              <div className="flex shrink-0 opacity-40 hover:opacity-100 transition-opacity">
                <IconButton
                  label="上移分组"
                  disabled={index === 0}
                  onClick={() => moveGroup(index, -1)}
                >
                  ↑
                </IconButton>
                <IconButton
                  label="下移分组"
                  disabled={index === groups.length - 1}
                  onClick={() => moveGroup(index, 1)}
                >
                  ↓
                </IconButton>
                <IconButton label="重命名分组" onClick={() => startRename(group)}>
                  ✎
                </IconButton>
                <IconButton label="删除分组" onClick={() => void removeGroup(group)}>
                  ✕
                </IconButton>
              </div>
            </div>
          ))}
        </aside>

        <section className="card">
          {!active ? (
            <p className="note">还没有分组，先在左上角新建一个。</p>
          ) : (
            <>
              <div className="flex justify-between items-start gap-2 flex-wrap mb-3">
                <div>
                  <h2 className="card-title mb-0.5">
                    {active.name}
                    <span className="note ml-2 font-normal">{active.items.length} 只</span>
                  </h2>
                  <p className="note">
                    {quotes.data
                      ? `行情刷新于 ${fmtTime(quotes.data.data.refreshed_at)}`
                      : quotes.isFetching
                        ? "正在获取行情 …"
                        : ""}
                  </p>
                </div>
                <div className="flex gap-1.5 items-center flex-wrap">
                  <div className="flex gap-1" role="group" aria-label="市场筛选">
                    {MARKETS.map((item) => (
                      <button
                        key={item.key}
                        type="button"
                        className={`tab-chip ${
                          marketFilter === item.key ? "tab-chip-on" : ""
                        }`}
                        aria-pressed={marketFilter === item.key}
                        onClick={() => setMarketFilter(item.key)}
                      >
                        {item.label}
                      </button>
                    ))}
                  </div>
                  <button
                    type="button"
                    className="btn btn-ghost !px-2.5 !py-1"
                    disabled={quotes.isFetching}
                    onClick={() => void quotes.refetch()}
                  >
                    {quotes.isFetching ? "刷新中…" : "刷新"}
                  </button>
                  <details className="relative">
                    <summary className="tab-chip cursor-pointer list-none" title="显示/隐藏列">
                      列
                    </summary>
                    <div className="absolute right-0 z-20 mt-1 bg-panel2 border border-line rounded p-2 flex flex-col gap-1 text-xs">
                      {COLUMNS.map((column) => (
                        <label
                          key={column.key}
                          className="flex items-center gap-2 cursor-pointer whitespace-nowrap"
                        >
                          <input
                            type="checkbox"
                            checked={visible.includes(column.key)}
                            onChange={() => toggleColumn(column.key)}
                          />
                          {column.label}
                        </label>
                      ))}
                    </div>
                  </details>
                </div>
              </div>

              <div className="flex gap-2 items-center mb-3">
                <input
                  className="input flex-1 min-w-0"
                  placeholder="添加代码，批量用逗号分隔：AAPL, 0700.HK"
                  value={tickerInput}
                  onChange={(e) => setTickerInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") void addTickers();
                  }}
                />
                <button
                  className="btn btn-primary !px-3.5 !py-1.5"
                  type="button"
                  onClick={() => void addTickers()}
                >
                  添加
                </button>
              </div>

              {quotes.isError && (
                <p className="text-accent text-xs mb-2">
                  刷新失败，正在显示上次数据。
                </p>
              )}

              {active.items.length === 0 ? (
                <p className="note py-8 text-center">
                  该分组还没有标的。输入股票代码后按回车添加。
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="data-table">
                    <thead>
                      <tr>
                        {canReorder && <th className="!w-7"></th>}
                        <th className="!text-left">代码 / 名称</th>
                        {COLUMNS.filter((c) => visible.includes(c.key)).map((c) => (
                          <th key={c.key}>
                            {c.sort ? (
                              <button
                                type="button"
                                className="bg-transparent border-0 text-muted cursor-pointer font-semibold"
                                onClick={() => toggleSort(c.sort!)}
                              >
                                {c.label}
                                {sort?.key === c.sort ? (sort.desc ? " ↓" : " ↑") : ""}
                              </button>
                            ) : (
                              c.label
                            )}
                          </th>
                        ))}
                        <th>操作</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map(({ item, quote }, index) => (
                        <tr
                          key={item.id}
                          draggable={canReorder}
                          onDragStart={() => canReorder && setDragId(item.id)}
                          onDragOver={(e) => e.preventDefault()}
                          onDrop={() => canReorder && dropOn(item.id)}
                          onDragEnd={() => setDragId(null)}
                          className={dragId === item.id ? "opacity-50" : undefined}
                        >
                          {canReorder && (
                            <td
                              className="!text-center text-muted cursor-grab"
                              title="拖拽排序"
                            >
                              ⋮⋮
                            </td>
                          )}
                          <td className="!text-left">
                            <Link
                              to={`/stock/${encodeURIComponent(item.ticker)}`}
                              className="font-semibold"
                            >
                              {item.ticker}
                            </Link>
                            {quote?.stale && (
                              <span
                                className="badge bg-panel2 text-accent ml-1.5"
                                title={quote.error ?? "上次刷新失败，显示缓存数据"}
                              >
                                stale
                              </span>
                            )}
                            <div className="text-xs text-muted mt-0.5 flex items-center gap-1.5">
                              <span className="truncate">
                                {quote?.name ?? item.name ?? DASH}
                              </span>
                              {quote?.error && !quote.stale && (
                                <span className="text-red shrink-0" title={quote.error}>
                                  数据获取失败
                                </span>
                              )}
                            </div>
                          </td>
                          {COLUMNS.filter((c) => visible.includes(c.key)).map((c) => (
                            <td key={c.key}>{c.render(quote)}</td>
                          ))}
                          <td className="!text-right">
                            <div className="flex gap-1 justify-end items-center">
                              {canReorder && (
                                <div className="flex flex-col leading-none">
                                  <IconButton
                                    label="上移"
                                    disabled={index === 0}
                                    onClick={() => moveItem(index, -1)}
                                  >
                                    ▲
                                  </IconButton>
                                  <IconButton
                                    label="下移"
                                    disabled={index === rows.length - 1}
                                    onClick={() => moveItem(index, 1)}
                                  >
                                    ▼
                                  </IconButton>
                                </div>
                              )}
                              <button
                                type="button"
                                className="tab-chip !px-2"
                                onClick={() =>
                                  m.removeItem.mutate({
                                    groupId: active.id,
                                    itemId: item.id,
                                  })
                                }
                              >
                                移除
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              <p className="note mt-3 text-center">
                拖拽行或使用 ▲/▼ 调整顺序（排序或筛选时隐藏）。数据 15 秒后失效，刷新失败的行保留上次结果并标记
                stale。「下次财报」来自各标的数据源日历，仅展示不推送，可在「列」中开启。
              </p>
            </>
          )}
        </section>
      </div>
    </div>
  );
}

function fmtTime(value: string | null): string {
  if (!value) return DASH;
  const iso = /[zZ]|[+-]\d\d:?\d\d$/.test(value) ? value : `${value}Z`;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return DASH;
  return date.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function IconButton({
  label,
  disabled,
  onClick,
  children,
}: {
  label: string;
  disabled?: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      title={label}
      aria-label={label}
      disabled={disabled}
      onClick={onClick}
      className="px-1.5 py-0.5 rounded border border-line bg-panel2 text-muted text-[11px] leading-4 cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed hover:border-accent"
    >
      {children}
    </button>
  );
}
