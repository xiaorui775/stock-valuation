/** 新闻与公告列表（FR-NEWS-02/03/04/06）：类型筛选、去重、外链提示。
 *
 * 数据来自后端 `/stocks/{ticker}/news`（yfinance / akshare 已按时间倒序返回）；
 * 前端仅做防御性去重（URL 或 标题+时间），分页 20 条。
 */
import { useMemo, useState } from "react";
import { useNews } from "@/api/queries";
import type { NewsItem } from "@/api/types";

const PAGE_SIZE = 20;

const KIND_LABELS: Record<string, string> = {
  news: "新闻",
  announcement: "公告",
};

const KINDS: { key: string; label: string }[] = [
  { key: "all", label: "全部" },
  { key: "news", label: "新闻" },
  { key: "announcement", label: "公告" },
];

/** 按 URL 或 标题+时间去重；URL 相同优先保留较新的一条。 */
function dedupe(items: NewsItem[]): NewsItem[] {
  const seenUrl = new Set<string>();
  const seenKey = new Set<string>();
  const out: NewsItem[] = [];
  for (const item of items) {
    const urlKey = item.url ?? "";
    if (urlKey) {
      if (seenUrl.has(urlKey)) continue;
      seenUrl.add(urlKey);
    }
    const fallbackKey = `${item.title}|${item.published_at ?? ""}`;
    if (seenKey.has(fallbackKey)) continue;
    seenKey.add(fallbackKey);
    out.push(item);
  }
  return out;
}

function fmtTime(value: string | null): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

export default function NewsPanel({ ticker }: { ticker: string }) {
  const [kind, setKind] = useState("all");
  const [page, setPage] = useState(0);
  const query = useNews(ticker, kind);

  const items = query.data?.data.items ?? [];
  const visible = useMemo(() => dedupe(items), [items]);
  const totalPages = Math.max(1, Math.ceil(visible.length / PAGE_SIZE));
  const pageItems = visible.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);
  const safePage = Math.min(page, totalPages - 1);
  const shown = safePage === page ? pageItems : visible.slice(safePage * PAGE_SIZE, (safePage + 1) * PAGE_SIZE);

  return (
    <div className="card">
      <div className="flex justify-between items-center flex-wrap gap-2 mb-3">
        <h2 className="card-title mb-0">新闻与公告</h2>
        <div className="flex gap-1" role="group" aria-label="类型筛选">
          {KINDS.map((k) => (
            <button
              key={k.key}
              type="button"
              className={`tab-chip ${kind === k.key ? "tab-chip-on" : ""}`}
              aria-pressed={kind === k.key}
              onClick={() => {
                setKind(k.key);
                setPage(0);
              }}
            >
              {k.label}
            </button>
          ))}
        </div>
      </div>

      {query.isError ? (
        <p className="text-red text-sm">{(query.error as Error)?.message ?? "新闻加载失败"}</p>
      ) : query.isLoading ? (
        <p className="note py-8 text-center">正在加载新闻 …</p>
      ) : shown.length === 0 ? (
        <p className="note py-8 text-center">暂无新闻或公告。</p>
      ) : (
        <ul className="divide-y divide-[#2a3552]">
          {shown.map((item, index) => (
            <li key={`${item.url ?? item.title}-${index}`} className="py-2.5">
              <div className="flex items-baseline gap-2">
                {item.url ? (
                  <a
                    href={item.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm hover:underline"
                    title="外部链接，内容由来源网站提供"
                  >
                    {item.title} ↗
                  </a>
                ) : (
                  <span className="text-sm">{item.title}</span>
                )}
                <span className="badge bg-panel2 text-muted shrink-0">
                  {KIND_LABELS[item.kind] ?? item.kind}
                </span>
              </div>
              <p className="note mt-0.5">
                {item.source ?? "来源未知"} · {fmtTime(item.published_at)}
              </p>
            </li>
          ))}
        </ul>
      )}

      {totalPages > 1 && (
        <div className="flex justify-between items-center mt-3">
          <button
            type="button"
            className="btn btn-ghost text-xs"
            disabled={safePage === 0}
            onClick={() => setPage(safePage - 1)}
          >
            上一页
          </button>
          <span className="note">
            第 {safePage + 1} / {totalPages} 页 · 共 {visible.length} 条
          </span>
          <button
            type="button"
            className="btn btn-ghost text-xs"
            disabled={safePage >= totalPages - 1}
            onClick={() => setPage(safePage + 1)}
          >
            下一页
          </button>
        </div>
      )}

      {shown.length > 0 && (
        <p className="note mt-2">
          外部链接在新窗口打开，内容由来源网站提供；列表按时间倒序，同一事件已去重。
        </p>
      )}
    </div>
  );
}
