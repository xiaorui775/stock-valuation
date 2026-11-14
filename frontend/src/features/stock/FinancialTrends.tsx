/** 财务趋势视图（PRD §5.17 FR-RESEARCH-01）。
 *
 * 与年度财务报表同源同口径：金额统一换算为「亿」，利润率由同一组科目相除得到。
 * 缺失财年或科目在图中留空（connectNulls=false），不做插值或估算。
 */
import { useMemo, useState } from "react";
import ReactECharts from "echarts-for-react";
import type { Financials, FinancialYear } from "@/api/types";
import { CHART_COLORS, TREND_COLORS, TREND_GRID } from "@/lib/chartTheme";
import { fmtNum, fmtPct } from "@/lib/format";

type View = "scale" | "margin";

const VIEWS: { key: View; label: string; hint: string }[] = [
  { key: "scale", label: "规模", hint: "营业收入、净利润与现金流" },
  { key: "margin", label: "利润率", hint: "毛利率、净利率与 FCF 利润率" },
];

/** 缺失值用 ECharts 的空值占位，不插值。 */
function scaleOf(value: number | null | undefined): number | "-" {
  if (value === null || value === undefined || Number.isNaN(value)) return "-";
  return Number((value / 1e8).toFixed(2));
}

function marginOf(
  numerator: number | null | undefined,
  denominator: number | null | undefined,
): number | "-" {
  if (
    numerator === null ||
    numerator === undefined ||
    denominator === null ||
    denominator === undefined ||
    denominator === 0 ||
    Number.isNaN(numerator) ||
    Number.isNaN(denominator)
  ) {
    return "-";
  }
  return Number(((numerator / denominator) * 100).toFixed(2));
}

interface TooltipItem {
  axisValue?: string;
  seriesName?: string;
  value?: number | string;
  marker?: string;
}

function tooltipHtml(params: unknown, view: View, currency: string | null): string {
  const list = (Array.isArray(params) ? params : [params]) as TooltipItem[];
  if (list.length === 0) return "";
  const rows = list
    .map((item) => {
      const raw = item.value;
      if (raw === "-" || raw === undefined || raw === null) {
        return `<div>${item.marker ?? ""}${item.seriesName ?? ""} —（数据缺失）</div>`;
      }
      const num = typeof raw === "number" ? raw : Number(raw);
      const text =
        view === "scale"
          ? `${fmtNum(num)} 亿${currency ? ` ${currency}` : ""}`
          : fmtPct(num, 2);
      return `<div>${item.marker ?? ""}${item.seriesName ?? ""} ${text}</div>`;
    })
    .join("");
  const title = list[0]?.axisValue ?? "";
  return `<div style="font-weight:600;margin-bottom:4px">${title} 财年</div>${rows}`;
}

function buildOption(years: FinancialYear[], view: View, currency: string | null) {
  const labels = years.map((y) => String(y.year));

  const series =
    view === "scale"
      ? [
          {
            name: "营业收入",
            type: "bar",
            barMaxWidth: 28,
            itemStyle: { color: TREND_COLORS.revenue },
            data: years.map((y) => scaleOf(y.revenue)),
          },
          {
            name: "净利润",
            type: "bar",
            barMaxWidth: 28,
            itemStyle: { color: TREND_COLORS.netIncome },
            data: years.map((y) => scaleOf(y.net_income)),
          },
          {
            name: "经营现金流",
            type: "line",
            connectNulls: false,
            symbolSize: 6,
            lineStyle: { width: 2, color: TREND_COLORS.operatingCash },
            itemStyle: { color: TREND_COLORS.operatingCash },
            data: years.map((y) => scaleOf(y.operating_cash_flow)),
          },
          {
            name: "自由现金流",
            type: "line",
            connectNulls: false,
            symbolSize: 6,
            lineStyle: { width: 2, color: TREND_COLORS.freeCash },
            itemStyle: { color: TREND_COLORS.freeCash },
            data: years.map((y) => scaleOf(y.free_cash_flow)),
          },
        ]
      : [
          {
            name: "毛利率",
            type: "line",
            connectNulls: false,
            symbolSize: 6,
            lineStyle: { width: 2, color: TREND_COLORS.grossMargin },
            itemStyle: { color: TREND_COLORS.grossMargin },
            data: years.map((y) => marginOf(y.gross_profit, y.revenue)),
          },
          {
            name: "净利率",
            type: "line",
            connectNulls: false,
            symbolSize: 6,
            lineStyle: { width: 2, color: TREND_COLORS.netMargin },
            itemStyle: { color: TREND_COLORS.netMargin },
            data: years.map((y) => marginOf(y.net_income, y.revenue)),
          },
          {
            name: "FCF 利润率",
            type: "line",
            connectNulls: false,
            symbolSize: 6,
            lineStyle: { width: 2, color: TREND_COLORS.fcfMargin },
            itemStyle: { color: TREND_COLORS.fcfMargin },
            data: years.map((y) => marginOf(y.free_cash_flow, y.revenue)),
          },
        ];

  return {
    backgroundColor: "transparent",
    grid: TREND_GRID,
    tooltip: {
      trigger: "axis",
      backgroundColor: CHART_COLORS.panel2,
      borderColor: CHART_COLORS.line,
      textStyle: { color: CHART_COLORS.text, fontSize: 12 },
      axisPointer: { type: "shadow", shadowStyle: { color: "rgba(42,53,82,0.35)" } },
      formatter: (params: unknown) => tooltipHtml(params, view, currency),
    },
    legend: {
      top: 0,
      right: 8,
      itemWidth: 10,
      itemHeight: 8,
      textStyle: { color: CHART_COLORS.muted, fontSize: 11 },
    },
    xAxis: {
      type: "category",
      data: labels,
      axisTick: { show: false },
      axisLine: { lineStyle: { color: CHART_COLORS.line } },
      axisLabel: { color: CHART_COLORS.muted, fontSize: 11 },
    },
    yAxis: {
      type: "value",
      name: view === "scale" ? `亿元${currency ? `（${currency}）` : ""}` : "百分比",
      nameTextStyle: { color: CHART_COLORS.muted, fontSize: 10, align: "left" },
      axisLabel: {
        color: CHART_COLORS.muted,
        fontSize: 10,
        formatter: view === "margin" ? "{value}%" : "{value}",
      },
      splitLine: { lineStyle: { color: CHART_COLORS.split } },
    },
    series,
  };
}

export default function FinancialTrends({
  data,
  source,
}: {
  data: Financials;
  source?: string | null;
}) {
  const [view, setView] = useState<View>("scale");
  const years = useMemo(
    () => [...data.years].sort((a, b) => a.year - b.year),
    [data.years],
  );
  const option = useMemo(
    () => buildOption(years, view, data.currency),
    [years, view, data.currency],
  );

  if (years.length < 2) {
    return (
      <p className="note">
        至少需要 2 个财年才能绘制趋势；当前只有 {years.length} 个财年。
      </p>
    );
  }

  return (
    <div>
      <div className="flex justify-between items-start gap-3 flex-wrap mb-3">
        <div className="flex gap-1 items-center" role="group" aria-label="趋势口径">
          {VIEWS.map((item) => (
            <button
              key={item.key}
              type="button"
              className={`tab-chip ${view === item.key ? "tab-chip-on" : ""}`}
              aria-pressed={view === item.key}
              title={item.hint}
              onClick={() => setView(item.key)}
            >
              {item.label}
            </button>
          ))}
        </div>
        <span className="note">{VIEWS.find((v) => v.key === view)?.hint}</span>
      </div>

      <div role="img" aria-label={`财务趋势图（${view === "scale" ? "规模" : "利润率"}）`}>
        <ReactECharts option={option} style={{ height: 320 }} notMerge lazyUpdate />
      </div>

      <div className="mt-2 space-y-1">
        <p className="note">
          口径与下方年度财务报表一致；
          {view === "scale"
            ? `金额按亿元展示${data.currency ? `（${data.currency}）` : ""}`
            : "利润率由同一组科目相除得到"}
          。缺失财年或科目在图中留空，不做插值。
        </p>
        {source && (
          <p className="note">
            数据来源：{source}（{data.period === "annual" ? "年度" : data.period}报表）。
          </p>
        )}
      </div>
    </div>
  );
}
