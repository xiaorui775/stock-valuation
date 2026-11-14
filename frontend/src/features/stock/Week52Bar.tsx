/** 52 周位置条：现价在 52 周区间中的位置（FR-OVERVIEW-03）。 */
import { fmtNum } from "@/lib/format";

interface Props {
  price: number | null;
  high: number | null;
  low: number | null;
  position: number | null;
}

export default function Week52Bar({ price, high, low, position }: Props) {
  if (position === null || high === null || low === null) {
    return (
      <div>
        <div className="flex justify-between text-xs text-muted mb-1.5">
          <span>52 周低点 {fmtNum(low)}</span>
          <span>52 周高点 {fmtNum(high)}</span>
        </div>
        <div className="h-2 rounded bg-line relative">
          <div className="absolute inset-0 flex items-center justify-center text-[10px] text-muted">
            数据源未提供 52 周区间
          </div>
        </div>
      </div>
    );
  }

  const pct = Math.min(100, Math.max(0, position * 100));
  const fromHigh = price !== null ? (price - high) / high * 100 : null;

  return (
    <div>
      <div className="flex justify-between text-xs text-muted mb-1.5">
        <span>52 周低点 {fmtNum(low)}</span>
        <span className="text-text font-semibold">现价 {fmtNum(price)}</span>
        <span>52 周高点 {fmtNum(high)}</span>
      </div>
      <div className="h-2 rounded bg-line relative">
        <div
          className="absolute h-3 w-1 bg-accent rounded -top-0.5"
          style={{ left: `calc(${pct}% - 2px)` }}
          title={`现价位于 52 周区间的 ${pct.toFixed(1)}% 处`}
        />
      </div>
      <p className="note mt-1.5">
        现价处于 52 周区间的 {pct.toFixed(1)}% 位置（距高点 {fmtNum(fromHigh)}%）
      </p>
    </div>
  );
}
