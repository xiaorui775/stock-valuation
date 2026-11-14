/** 估值结论卡：DCF 每股价值、相对现价空间、综合判定（FR-OVERVIEW-04）。 */
import { Link } from "react-router-dom";
import type { ValuationConclusion } from "@/api/types";
import { fmtNum, fmtPct, valuationClass } from "@/lib/format";

const BAND_STYLE: Record<string, string> = {
  低估: "text-green",
  高估: "text-red",
  合理: "text-text",
};

export default function ConclusionCard({
  conclusion,
  ticker,
}: {
  conclusion: ValuationConclusion | null;
  ticker: string;
}) {
  if (!conclusion) {
    return (
      <div className="card">
        <h2 className="card-title">估值结论</h2>
        <p className="note">数据源未提供足够的财务数据，无法给出估值结论。</p>
      </div>
    );
  }

  const band = conclusion.band ?? "—";

  return (
    <div className="card">
      <div className="flex justify-between items-start gap-4 flex-wrap">
        <h2 className="card-title mb-0">估值结论</h2>
        <Link
          to={`/stock/${encodeURIComponent(ticker)}?tab=valuation`}
          className="btn btn-ghost text-xs"
        >
          查看完整估值 →
        </Link>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
        <div>
          <div className="stat-k text-xs mb-1">DCF 每股价值</div>
          <div className="text-2xl font-bold">{fmtNum(conclusion.dcf_per_share)}</div>
        </div>
        <div>
          <div className="stat-k text-xs mb-1">相对现价空间</div>
          <div className={`text-2xl font-bold ${valuationClass(conclusion.upside_pct)}`}>
            {fmtPct(conclusion.upside_pct, 2, true)}
          </div>
        </div>
        <div>
          <div className="stat-k text-xs mb-1">综合均值</div>
          <div className="text-2xl font-bold">{fmtNum(conclusion.average_value)}</div>
        </div>
        <div>
          <div className="stat-k text-xs mb-1">综合判定</div>
          <div className={`text-2xl font-bold ${BAND_STYLE[band] ?? "text-text"}`}>{band}</div>
        </div>
      </div>

      <p className="note mt-3">
        综合均值由 {conclusion.methods_used} 种方法平均得到。判定规则：平均值高于现价 15% 以上为
        「低估」，低于 15% 以上为「高估」，其间为「合理」。这是模型输出，不是投资建议。
      </p>
    </div>
  );
}
