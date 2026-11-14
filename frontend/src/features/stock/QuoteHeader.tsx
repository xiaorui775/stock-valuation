/** 报价头：名称、代码、市场标签、现价、涨跌、交易状态（FR-OVERVIEW-01）。 */
import type { Overview } from "@/api/types";
import { changeClass, fmtNum } from "@/lib/format";

const SESSION_STYLE: Record<string, string> = {
  pre: "bg-line text-muted",
  regular: "bg-green/15 text-green",
  post: "bg-line text-muted",
  closed: "bg-line text-muted",
};

export default function QuoteHeader({ overview }: { overview: Overview }) {
  const s = overview.session;
  return (
    <div className="flex justify-between items-start gap-4 flex-wrap">
      <div>
        <h1 className="text-2xl font-bold mb-1.5 flex items-center gap-2 flex-wrap">
          {overview.name}
          <span className="text-muted text-base font-normal">{overview.ticker}</span>
          <span className="badge bg-line text-muted">{overview.market_label}</span>
          {s && (
            <span
              className={`badge ${SESSION_STYLE[s.status] ?? "bg-line text-muted"}`}
              title={`当地时间 ${s.local_time}（${s.timezone}）${s.note ? ` · ${s.note}` : ""}`}
            >
              {s.label}
            </span>
          )}
        </h1>
        <div className="flex items-baseline gap-3 flex-wrap">
          <span className="text-4xl font-extrabold">{fmtNum(overview.price)}</span>
          <span className={`text-lg font-bold ${changeClass(overview.change)}`}>
            {overview.change == null
              ? "—"
              : `${overview.change > 0 ? "+" : ""}${fmtNum(overview.change)} (${
                  overview.change_pct == null
                    ? "—"
                    : `${overview.change_pct > 0 ? "+" : ""}${fmtNum(overview.change_pct)}%`
                })`}
          </span>
          <span className="text-muted text-sm">{overview.currency ?? ""}</span>
          {s && <span className="text-muted text-xs">{s.local_time}</span>}
        </div>
      </div>
    </div>
  );
}
