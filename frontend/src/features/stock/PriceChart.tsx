/** 历史行情图表：1M–MAX 周期、日/周/月线、面积图与 K 线切换。
 *
 * 覆盖 FR-CHART-01/02/03/04/05：十字光标、缩放平移、数据区间与复权方式提示，
 * 主图叠加 MA5/10/20/60/120 与 BOLL(20,2)，副图可切 成交量 / MACD(12,26,9) / RSI(14)。
 * 指标由后端随历史数据返回（口径一致），前端只做渲染，窗口不满的位置不画。
 */
import { useMemo, useState } from "react";
import ReactECharts from "echarts-for-react";
import { useHistory } from "@/api/queries";
import type { Bar, Indicators } from "@/api/types";
import { DASH, fmtInt, fmtNum, fmtPct } from "@/lib/format";
import { CHART_COLORS as COLORS } from "@/lib/chartTheme";

type ChartType = "area" | "candle";
type PeriodKey = "1mo" | "3mo" | "6mo" | "1y" | "3y" | "5y" | "max";
type IntervalKey = "1d" | "1wk" | "1mo";
/** 副图类型：none 时仍显示主图叠加层开关。 */
type SubKey = "volume" | "macd" | "rsi" | "none";
type OverlayKey = "ma" | "boll" | "none";

const PERIODS: { key: PeriodKey; label: string }[] = [
  { key: "1mo", label: "1M" },
  { key: "3mo", label: "3M" },
  { key: "6mo", label: "6M" },
  { key: "1y", label: "1Y" },
  { key: "3y", label: "3Y" },
  { key: "5y", label: "5Y" },
  { key: "max", label: "MAX" },
];

const INTERVALS: { key: IntervalKey; label: string }[] = [
  { key: "1d", label: "日线" },
  { key: "1wk", label: "周线" },
  { key: "1mo", label: "月线" },
];

const SUBS: { key: SubKey; label: string }[] = [
  { key: "volume", label: "成交量" },
  { key: "macd", label: "MACD" },
  { key: "rsi", label: "RSI" },
  { key: "none", label: "无" },
];

const OVERLAYS: { key: OverlayKey; label: string }[] = [
  { key: "ma", label: "MA" },
  { key: "boll", label: "BOLL" },
  { key: "none", label: "无" },
];

/** MA 周期 → 颜色，参照国内行情软件惯例。 */
const MA_COLORS: Record<string, string> = {
  ma5: "#f5b942",
  ma10: "#5b8ff9",
  ma20: "#5ad8a6",
  ma60: "#e8684a",
  ma120: "#b68cd9",
};

const BOLL_COLORS = { mid: "#93a0bb", upper: "#5ad8a6", lower: "#5ad8a6" };

/** K 线/成交量/指标缺失值：用 ECharts 的空值占位，不插值。 */
function value(v: number | null | undefined): number | "-" {
  return v === null || v === undefined || Number.isNaN(v) ? "-" : v;
}

export default function PriceChart({
  ticker,
  height = 420,
}: {
  ticker: string;
  height?: number;
}) {
  const [period, setPeriod] = useState<PeriodKey>("1y");
  const [interval, setInterval] = useState<IntervalKey>("1d");
  const [chartType, setChartType] = useState<ChartType>("area");
  const [sub, setSub] = useState<SubKey>("volume");
  const [overlay, setOverlay] = useState<OverlayKey>("ma");

  const history = useHistory(ticker, period, interval);
  const data = history.data?.data;
  const bars = data?.bars ?? [];
  const indicators = data?.indicators;

  const option = useMemo(
    () => buildOption(bars, indicators, chartType, sub, overlay),
    [bars, indicators, chartType, sub, overlay],
  );

  return (
    <div>
      <div className="flex justify-between items-start gap-3 flex-wrap mb-3">
        <div className="flex gap-1 flex-wrap" role="group" aria-label="时间区间">
          {PERIODS.map((p) => (
            <button
              key={p.key}
              type="button"
              className={`tab-chip ${period === p.key ? "tab-chip-on" : ""}`}
              aria-pressed={period === p.key}
              onClick={() => setPeriod(p.key)}
            >
              {p.label}
            </button>
          ))}
        </div>

        <div className="flex gap-3 items-center flex-wrap">
          <div className="flex gap-1" role="group" aria-label="K 线周期">
            {INTERVALS.map((i) => (
              <button
                key={i.key}
                type="button"
                className={`tab-chip ${interval === i.key ? "tab-chip-on" : ""}`}
                aria-pressed={interval === i.key}
                onClick={() => setInterval(i.key)}
              >
                {i.label}
              </button>
            ))}
          </div>
          <div className="flex gap-1" role="group" aria-label="图表类型">
            <button
              type="button"
              className={`tab-chip ${chartType === "area" ? "tab-chip-on" : ""}`}
              aria-pressed={chartType === "area"}
              onClick={() => setChartType("area")}
            >
              面积
            </button>
            <button
              type="button"
              className={`tab-chip ${chartType === "candle" ? "tab-chip-on" : ""}`}
              aria-pressed={chartType === "candle"}
              onClick={() => setChartType("candle")}
            >
              K 线
            </button>
          </div>
        </div>
      </div>

      <div className="flex gap-4 items-center flex-wrap mb-2" role="group" aria-label="指标设置">
        <div className="flex gap-1 items-center">
          <span className="note text-xs mr-1">主图</span>
          {OVERLAYS.map((o) => (
            <button
              key={o.key}
              type="button"
              className={`tab-chip ${overlay === o.key ? "tab-chip-on" : ""}`}
              aria-pressed={overlay === o.key}
              onClick={() => setOverlay(o.key)}
            >
              {o.label}
            </button>
          ))}
        </div>
        <div className="flex gap-1 items-center">
          <span className="note text-xs mr-1">副图</span>
          {SUBS.map((s) => (
            <button
              key={s.key}
              type="button"
              className={`tab-chip ${sub === s.key ? "tab-chip-on" : ""}`}
              aria-pressed={sub === s.key}
              onClick={() => setSub(s.key)}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {history.isError ? (
        <div className="py-12 text-center">
          <p className="text-red text-sm">
            {(history.error as Error)?.message ?? "历史行情加载失败"}
          </p>
          <button
            type="button"
            className="btn btn-ghost mt-3"
            onClick={() => history.refetch()}
          >
            重试
          </button>
        </div>
      ) : history.isLoading ? (
        <div className="note py-16 text-center">正在加载图表 …</div>
      ) : bars.length === 0 ? (
        <div className="note py-16 text-center">暂无历史数据。</div>
      ) : (
        <div className={history.isFetching ? "opacity-60 transition-opacity" : undefined}>
          <ReactECharts option={option} style={{ height }} notMerge lazyUpdate />
        </div>
      )}

      {data && bars.length > 0 && (
        <p className="note mt-2">
          数据区间 {data.start_date ?? DASH} ~ {data.end_date ?? DASH} ·{" "}
          {INTERVALS.find((i) => i.key === data.interval)?.label ?? data.interval} ·{" "}
          {data.adjustment} · 共 {fmtInt(data.count)} 条。停牌或缺失的交易日不插值，指标窗口不满处不绘制。
        </p>
      )}
    </div>
  );
}

// ----------------------------------------------------------------------
function buildOption(
  bars: Bar[],
  indicators: Indicators | undefined,
  chartType: ChartType,
  sub: SubKey,
  overlay: OverlayKey,
) {
  const dates = bars.map((b) => b.date);

  // 三段栅格：主图 / 副图 / 时间轴 + 缩放滑条。副图有无决定布局。
  const sliderBottom = 6;
  const sliderHeight = 14;
  const xAxisSpace = 22;
  const subHeight = sub === "none" ? 0 : sub === "macd" ? 76 : 60;
  const subBottom = sliderBottom + sliderHeight + xAxisSpace;
  // 主图底部必须为副图（含其 x 轴标签）留出空间，否则两块栅格重叠
  const mainBottom = sub === "none" ? subBottom : subBottom + subHeight + 30;

  const grids: Record<string, unknown>[] = [
    { left: 64, right: 18, top: 18, bottom: mainBottom },
  ];
  if (sub !== "none") {
    grids.push({ left: 64, right: 18, height: subHeight, bottom: subBottom });
  }

  const priceSeries =
    chartType === "candle"
      ? {
          name: "K 线",
          type: "candlestick" as const,
          // ECharts 口径：[open, close, low, high]
          data: bars.map((b) => [
            value(b.open),
            value(b.close),
            value(b.low),
            value(b.high),
          ]),
          itemStyle: {
            color: COLORS.up, // 阳线（收 > 开）红
            color0: COLORS.down, // 阴线绿
            borderColor: COLORS.up,
            borderColor0: COLORS.down,
          },
        }
      : {
          name: "收盘价",
          type: "line" as const,
          data: bars.map((b) => b.close),
          showSymbol: false,
          smooth: false,
          sampling: "lttb",
          lineStyle: { width: 1.6, color: COLORS.accent },
          areaStyle: { color: "rgba(245,185,66,0.12)" },
        };

  const series: Record<string, unknown>[] = [priceSeries];

  // 主图叠加层：MA 或 BOLL。指标序列缺失（旧数据）时静默不画。
  if (indicators && overlay === "ma") {
    for (const key of ["ma5", "ma10", "ma20", "ma60", "ma120"]) {
      const values = indicators[key as keyof Indicators];
      if (!values) continue;
      series.push({
        name: key.toUpperCase(),
        type: "line",
        data: values.map((v) => value(v)),
        showSymbol: false,
        sampling: "lttb",
        lineStyle: { width: 1, color: MA_COLORS[key] },
        // 面积图时叠加线画在收盘价之上
        z: 3,
        emphasis: { focus: "none" },
      });
    }
  }
  if (indicators && overlay === "boll") {
    series.push(
      {
        name: "BOLL 中轨",
        type: "line",
        data: indicators.boll_mid.map((v) => value(v)),
        showSymbol: false,
        sampling: "lttb",
        lineStyle: { width: 1, color: BOLL_COLORS.mid, type: "dashed" },
        z: 3,
      },
      {
        name: "BOLL 上轨",
        type: "line",
        data: indicators.boll_upper.map((v) => value(v)),
        showSymbol: false,
        sampling: "lttb",
        lineStyle: { width: 1, color: BOLL_COLORS.upper },
        z: 3,
      },
      {
        name: "BOLL 下轨",
        type: "line",
        data: indicators.boll_lower.map((v) => value(v)),
        showSymbol: false,
        sampling: "lttb",
        lineStyle: { width: 1, color: BOLL_COLORS.lower },
        areaStyle: { color: "rgba(90,216,166,0.06)" },
        z: 2,
      },
    );
  }

  // 副图系列
  if (sub === "volume") {
    series.push({
      name: "成交量",
      type: "bar",
      xAxisIndex: 1,
      yAxisIndex: 1,
      // 不开 large 模式：large 会忽略逐根涨跌配色（MAX 周期超过 400 根时尤其明显）
      data: bars.map((b) => ({
        value: value(b.volume),
        itemStyle: {
          color:
            b.open !== null && b.close < b.open
              ? "rgba(29,185,84,0.55)"
              : "rgba(242,54,69,0.55)",
        },
      })),
    });
  } else if (sub === "macd" && indicators) {
    series.push(
      {
        name: "DIF",
        type: "line",
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: indicators.dif.map((v) => value(v)),
        showSymbol: false,
        sampling: "lttb",
        lineStyle: { width: 1, color: "#f5b942" },
      },
      {
        name: "DEA",
        type: "line",
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: indicators.dea.map((v) => value(v)),
        showSymbol: false,
        sampling: "lttb",
        lineStyle: { width: 1, color: "#5b8ff9" },
      },
      {
        name: "MACD",
        type: "bar",
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: indicators.macd.map((v) => {
          if (v === null || v === undefined) return "-";
          return {
            value: v,
            itemStyle: { color: v >= 0 ? "rgba(242,54,69,0.75)" : "rgba(29,185,84,0.75)" },
          };
        }),
      },
    );
  } else if (sub === "rsi" && indicators) {
    series.push({
      name: "RSI14",
      type: "line",
      xAxisIndex: 1,
      yAxisIndex: 1,
      data: indicators.rsi14.map((v) => value(v)),
      showSymbol: false,
      sampling: "lttb",
      lineStyle: { width: 1.2, color: "#b68cd9" },
      markLine: {
        symbol: "none",
        silent: true,
        label: { show: false },
        lineStyle: { color: COLORS.line, type: "dashed", width: 1 },
        data: [{ yAxis: 70 }, { yAxis: 30 }],
      },
    });
  }

  const yAxes: Record<string, unknown>[] = [
    {
      type: "value",
      scale: true,
      splitNumber: 5,
      axisLine: { show: false },
      axisLabel: { color: COLORS.muted },
      splitLine: { lineStyle: { color: COLORS.split } },
    },
  ];
  if (sub !== "none") {
    yAxes.push({
      type: "value",
      gridIndex: 1,
      scale: sub !== "rsi",
      min: sub === "rsi" ? 0 : undefined,
      max: sub === "rsi" ? 100 : undefined,
      splitNumber: sub === "volume" ? 2 : 3,
      axisLine: { show: false },
      // 成交量刻度省略（数值见悬浮提示）；MACD/RSI 显示数值刻度
      axisLabel: {
        show: sub !== "volume",
        color: COLORS.muted,
        fontSize: 10,
        formatter: sub === "macd" ? (v: number) => fmtNum(v, 1) : undefined,
      },
      splitLine: { lineStyle: { color: COLORS.split } },
    });
  }

  const xAxes: Record<string, unknown>[] = [
    {
      type: "category",
      data: dates,
      boundaryGap: chartType === "candle",
      axisLine: { lineStyle: { color: COLORS.line } },
      axisLabel: { color: COLORS.muted, hideOverlap: true, show: sub === "none" },
      axisTick: { show: false },
    },
  ];
  if (sub !== "none") {
    xAxes.push({
      type: "category",
      gridIndex: 1,
      data: dates,
      boundaryGap: chartType === "candle",
      axisLine: { lineStyle: { color: COLORS.line } },
      axisLabel: { color: COLORS.muted, hideOverlap: true },
      axisTick: { show: false },
    });
  }

  const zoomIndex = sub === "none" ? [0] : [0, 1];

  return {
    backgroundColor: "transparent",
    animationDuration: 250,
    grid: grids,
    axisPointer: { link: [{ xAxisIndex: "all" }] },
    tooltip: {
      trigger: "axis",
      backgroundColor: COLORS.panel2,
      borderColor: COLORS.line,
      textStyle: { color: COLORS.text, fontSize: 12 },
      axisPointer: { type: "cross", label: { backgroundColor: COLORS.line } },
      formatter: (params: unknown) => formatTooltip(params, bars, indicators),
    },
    legend:
      overlay === "none" && sub === "none"
        ? undefined
        : {
            // 只列出当前可见的指标，避免图例把空间撑爆
            data: legendNames(overlay, sub),
            top: 0,
            right: 8,
            itemWidth: 10,
            itemHeight: 8,
            textStyle: { color: COLORS.muted, fontSize: 10 },
            icon: "roundRect",
          },
    xAxis: xAxes,
    yAxis: yAxes,
    dataZoom: [
      { type: "inside", xAxisIndex: zoomIndex, throttle: 50 },
      {
        type: "slider",
        xAxisIndex: zoomIndex,
        height: sliderHeight,
        bottom: sliderBottom,
        borderColor: COLORS.line,
        backgroundColor: "transparent",
        fillerColor: "rgba(42,53,82,0.55)",
        handleStyle: { color: COLORS.accent, borderColor: COLORS.accent },
        textStyle: { color: COLORS.muted, fontSize: 10 },
        dataBackground: {
          lineStyle: { color: COLORS.line },
          areaStyle: { color: COLORS.line },
        },
      },
    ],
    series,
  };
}

function legendNames(overlay: OverlayKey, sub: SubKey): string[] {
  const names: string[] = [];
  if (overlay === "ma") names.push("MA5", "MA10", "MA20", "MA60", "MA120");
  if (overlay === "boll") names.push("BOLL 中轨", "BOLL 上轨", "BOLL 下轨");
  if (sub === "volume") names.push("成交量");
  if (sub === "macd") names.push("DIF", "DEA", "MACD");
  if (sub === "rsi") names.push("RSI14");
  return names;
}

function formatTooltip(
  params: unknown,
  bars: Bar[],
  indicators: Indicators | undefined,
): string {
  const list = Array.isArray(params) ? params : [params];
  const first = list[0] as { dataIndex?: number } | undefined;
  const index = first?.dataIndex;
  if (index === undefined || !bars[index]) return "";
  const bar = bars[index];
  const prev = index > 0 ? bars[index - 1].close : null;
  const changePct =
    prev === null || prev === 0 ? null : ((bar.close - prev) / prev) * 100;

  const rows = [
    `<div style="font-weight:600;margin-bottom:4px">${bar.date}</div>`,
    `开 ${fmtNum(bar.open)}　高 ${fmtNum(bar.high)}`,
    `低 ${fmtNum(bar.low)}　收 ${fmtNum(bar.close)}`,
    `涨跌 ${fmtPct(changePct, 2, true)}`,
    bar.volume === null || bar.volume === undefined
      ? "成交量 —"
      : `成交量 ${fmtInt(bar.volume)}`,
  ];

  if (indicators) {
    const mas = (["ma5", "ma10", "ma20", "ma60", "ma120"] as const)
      .filter((key) => indicators[key][index] !== null)
      .map(
        (key) =>
          `<span style="color:${MA_COLORS[key]}">${key.toUpperCase()} ${fmtNum(indicators[key][index])}</span>`,
      );
    if (mas.length) rows.push(mas.join("　"));
    if (indicators.rsi14[index] !== null && indicators.rsi14[index] !== undefined) {
      rows.push(`RSI14 ${fmtNum(indicators.rsi14[index], 1)}`);
    }
  }
  return rows.join("<br/>");
}
