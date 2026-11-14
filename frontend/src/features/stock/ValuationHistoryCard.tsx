/** 历史估值区间：P/E、P/B、P/S、FCF Yield 的 3 年 / 5 年分位（FR-VAL-11）。 */
import { useState } from "react";
import {
  useValuationHistory,
  type MetricHistory,
  type PercentileStats,
} from "@/api/valuation";
import { DASH, fmtNum } from "@/lib/format";

type Span = "3y" | "5y";

export default function ValuationHistoryCard({ ticker }: { ticker: string }) {
  const [span, setSpan] = useState<Span>("5y");
  const { data, isLoading, isError, error, refetch } = useValuationHistory(ticker);
  const view = data?.data;

  return (
    <div className="card">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <h2 className="card-title mb-0">历史估值区间</h2>
        <div className="flex gap-1.5">
          {(["3y", "5y"] as Span[]).map((value) => (
            <button
              key={value}
              type="button"
              className={`tab-chip ${span === value ? "tab-chip-on" : ""}`}
              onClick={() => setSpan(value)}
            >
              {value === "3y" ? "近 3 年" : "近 5 年"}
            </button>
          ))}
        </div>
      </div>

      <p className="note mt-2">
        {view?.sample_hint ??
          "每个交易日使用该日之前最近一个已完成财年的财报计算倍数，不使用未来数据。"}
      </p>

      {isLoading && <p className="note mt-3">加载中…</p>}
      {isError && (
        <p className="text-red text-xs mt-3">
          {(error as Error)?.message ?? "加载失败"}{" "}
          <button type="button" className="underline" onClick={() => void refetch()}>
            重试
          </button>
        </p>
      )}

      {view && (
        <>
          {view.warnings.length > 0 && (
            <ul className="note mt-2 space-y-0.5">
              {view.warnings.map((item) => (
                <li key={item} className="text-accent">
                  数据不足：{item}
                </li>
              ))}
            </ul>
          )}

          <table className="w-full text-sm mt-3">
            <thead>
              <tr className="text-muted text-xs text-left">
                <th className="py-1.5 font-normal">指标</th>
                <th className="py-1.5 font-normal text-right">当前</th>
                <th className="py-1.5 font-normal text-right">当前分位</th>
                <th className="py-1.5 font-normal pl-4">
                  分位分布（{span === "3y" ? "3 年" : "5 年"}）
                </th>
              </tr>
            </thead>
            <tbody>
              {view.metrics.map((metric) => (
                <Row key={metric.key} metric={metric} span={span} />
              ))}
            </tbody>
          </table>

          <p className="note mt-2">
            分位＝历史样本中小于等于当前值的占比。样本自 {view.windows[span]} 起算，最多{" "}
            {Math.max(0, ...view.metrics.map((m) => statsOf(m, span)?.count ?? 0))} 个交易日；
            数据截至 {view.as_of}。倍数由历史价格与已公布财报推导，不含预测。
          </p>
        </>
      )}
    </div>
  );
}

function statsOf(metric: MetricHistory | undefined, span: Span): PercentileStats | null {
  if (!metric) return null;
  return span === "3y" ? metric.stats_3y : metric.stats_5y;
}

function percentileOf(metric: MetricHistory, span: Span): number | null {
  return span === "3y" ? metric.percentile_3y : metric.percentile_5y;
}

function Row({ metric, span }: { metric: MetricHistory; span: Span }) {
  const stats = statsOf(metric, span);
  const percentile = percentileOf(metric, span);
  const unusable = metric.current == null || stats == null;

  return (
    <tr className="border-t border-line align-top">
      <td className="py-2">
        <div>{metric.label}</div>
        {metric.note && (
          <div className="text-[11px] text-accent mt-0.5">{metric.note}</div>
        )}
      </td>
      <td className="py-2 text-right tabular-nums">
        {format(metric.current, metric.unit)}
      </td>
      <td className="py-2 text-right tabular-nums">
        {percentile == null ? (
          DASH
        ) : (
          <div>
            <span className={tone(percentile)}>{fmtNum(percentile, 0)}%</span>
            <div className="text-[11px] text-muted">{toneLabel(percentile)}</div>
          </div>
        )}
      </td>
      <td className="py-2 pl-4">
        {unusable ? (
          <span className="text-muted text-xs">数据不足，不计算分位</span>
        ) : (
          <Band current={metric.current as number} stats={stats} unit={metric.unit} />
        )}
      </td>
    </tr>
  );
}

/** 10–90 分位区间条，当前值以竖线标出；数值始终以文字给出，不依赖颜色。 */
function Band({
  current,
  stats,
  unit,
}: {
  current: number;
  stats: PercentileStats;
  unit: string;
}) {
  const low = stats.p10;
  const high = stats.p90;
  if (low == null || high == null) {
    return <span className="text-muted text-xs">{DASH}</span>;
  }
  const width = high - low;
  const position = (value: number | null) =>
    value == null || width <= 0 ? null : clamp(((value - low) / width) * 100);
  const ticks = [
    { key: "p10", label: "p10", value: stats.p10 },
    { key: "p25", label: "p25", value: stats.p25 },
    { key: "p50", label: "p50", value: stats.p50 },
    { key: "p75", label: "p75", value: stats.p75 },
    { key: "p90", label: "p90", value: stats.p90 },
  ];

  return (
    <div className="min-w-[220px]">
      <div className="relative h-4">
        <div className="absolute inset-x-0 top-1/2 h-1 -translate-y-1/2 rounded-full bg-line" />
        {ticks.map((tick) => {
          const left = position(tick.value);
          if (left == null) return null;
          return (
            <span
              key={tick.key}
              className="absolute top-1/2 h-2.5 w-px -translate-y-1/2 bg-muted/70"
              style={{ left: `${left}%` }}
            />
          );
        })}
        <span
          className="absolute top-1/2 h-3 w-[2px] -translate-x-1/2 -translate-y-1/2 rounded bg-accent"
          style={{ left: `${position(current) ?? 0}%` }}
        />
      </div>
      <div className="relative h-3 mt-1 text-[10px] text-muted tabular-nums">
        {ticks.map((tick) => {
          const left = position(tick.value);
          if (left == null) return null;
          const shift = left <= 8 ? "0" : left >= 92 ? "-100%" : "-50%";
          return (
            <span
              key={tick.key}
              className="absolute whitespace-nowrap"
              style={{ left: `${left}%`, transform: `translateX(${shift})` }}
            >
              {tick.label} {format(tick.value, unit, 1)}
            </span>
          );
        })}
      </div>
    </div>
  );
}

function format(value: number | null, unit: string, digits = 2): string {
  if (value == null) return DASH;
  return unit === "%" ? `${fmtNum(value, digits)}%` : `${fmtNum(value, digits)}×`;
}

function clamp(value: number): number {
  return Math.min(100, Math.max(0, value));
}

/** 分位高＝相对历史偏贵。用文字同时标注，避免只靠颜色传达。 */
function tone(percentile: number): string {
  if (percentile >= 70) return "text-red font-semibold";
  if (percentile <= 30) return "text-green font-semibold";
  return "text-muted";
}

function toneLabel(percentile: number): string {
  if (percentile >= 70) return "偏高";
  if (percentile <= 30) return "偏低";
  return "居中";
}
