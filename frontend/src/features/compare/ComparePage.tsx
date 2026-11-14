/** 多股对比：2–6 只、归一化走势、指标表与统一假设估值（§5.10）。
 *
 * 最优/最差由后端按指标方向给出（估值越低越好、增速越高越好），前端只负责展示，
 * 并且用「优/差」文字标注，不依赖颜色单独传达信息。
 */
import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import ReactECharts from "echarts-for-react";
import {
  useCompare,
  useComparePresetMutations,
  useComparePresets,
  type CompareMetric,
  type ComparePreset,
} from "@/api/compare";
import { DASH, fmtBig, fmtNum, fmtPct, marketLabel, valuationClass } from "@/lib/format";

const MAX_TICKERS = 6;
const MIN_TICKERS = 2;
const PERIODS = [
  { key: "3mo", label: "3M" },
  { key: "6mo", label: "6M" },
  { key: "1y", label: "1Y" },
] as const;
const SERIES_COLORS = ["#f5b942", "#5aa9ff", "#1db954", "#f23645", "#b07cff", "#33d6c0"];

type PeriodKey = (typeof PERIODS)[number]["key"];

export default function ComparePage() {
  const [params, setParams] = useSearchParams();
  const [tickers, setTickers] = useState<string[]>(() => {
    const raw = params.get("tickers") ?? "";
    return raw
      .split(",")
      .map((t) => t.trim().toUpperCase())
      .filter(Boolean)
      .slice(0, MAX_TICKERS);
  });
  const [input, setInput] = useState("");
  const [period, setPeriod] = useState<PeriodKey>("1y");
  const [message, setMessage] = useState<string | null>(null);
  const [presetName, setPresetName] = useState("");
  const [presetError, setPresetError] = useState<string | null>(null);

  const { data, isLoading, isError, error } = useCompare(tickers, period);
  const result = data?.data;

  const presets = useComparePresets();
  const { createPreset, updatePreset, deletePreset } = useComparePresetMutations();
  const presetItems = presets.data?.data.items ?? [];

  function sync(next: string[]) {
    setTickers(next);
    const nextParams = new URLSearchParams(params);
    if (next.length) nextParams.set("tickers", next.join(","));
    else nextParams.delete("tickers");
    setParams(nextParams, { replace: true });
  }

  function add() {
    const symbol = input.trim().toUpperCase();
    setMessage(null);
    if (!symbol) return;
    if (tickers.includes(symbol)) {
      setMessage(`${symbol} 已在对比列表中`);
      setInput("");
      return;
    }
    if (tickers.length >= MAX_TICKERS) {
      setMessage(`最多对比 ${MAX_TICKERS} 只标的`);
      return;
    }
    sync([...tickers, symbol]);
    setInput("");
  }

  function remove(symbol: string) {
    setMessage(null);
    sync(tickers.filter((t) => t !== symbol));
  }

  async function savePreset() {
    const name = presetName.trim();
    if (!name || tickers.length < MIN_TICKERS) return;
    try {
      await createPreset.mutateAsync({ name, tickers });
      setPresetName("");
      setPresetError(null);
      setMessage(`已保存对比组合「${name}」`);
    } catch (e) {
      setPresetError((e as Error).message);
    }
  }

  function loadPreset(preset: ComparePreset) {
    sync(preset.tickers);
    setPresetError(null);
    setMessage(`已加载「${preset.name}」`);
  }

  async function overwritePreset(preset: ComparePreset) {
    if (tickers.length < MIN_TICKERS) return;
    try {
      await updatePreset.mutateAsync({ id: preset.id, tickers });
      setPresetError(null);
      setMessage(`已用当前标的覆盖「${preset.name}」`);
    } catch (e) {
      setPresetError((e as Error).message);
    }
  }

  async function removePreset(preset: ComparePreset) {
    if (!window.confirm(`删除对比组合「${preset.name}」？`)) return;
    try {
      await deletePreset.mutateAsync(preset.id);
      setPresetError(null);
    } catch (e) {
      setPresetError((e as Error).message);
    }
  }

  const option = useMemo(() => {
    if (!result) return null;
    return {
      backgroundColor: "transparent",
      color: SERIES_COLORS,
      grid: { left: 52, right: 20, top: 36, bottom: 44 },
      tooltip: {
        trigger: "axis",
        backgroundColor: "#1e2740",
        borderColor: "#2a3552",
        textStyle: { color: "#e8ecf5", fontSize: 12 },
        valueFormatter: (value: number) => `${fmtNum(value)}`,
      },
      legend: {
        top: 0,
        textStyle: { color: "#93a0bb", fontSize: 11 },
        icon: "roundRect",
        itemWidth: 12,
        itemHeight: 3,
      },
      xAxis: {
        type: "time",
        axisLine: { lineStyle: { color: "#2a3552" } },
        axisLabel: { color: "#93a0bb", fontSize: 11 },
        splitLine: { show: false },
      },
      yAxis: {
        type: "value",
        name: "起点 = 100",
        nameTextStyle: { color: "#93a0bb", fontSize: 11 },
        axisLabel: { color: "#93a0bb", fontSize: 11 },
        splitLine: { lineStyle: { color: "#232c47" } },
        scale: true,
      },
      series: tickers.map((ticker) => ({
        name: ticker,
        type: "line",
        showSymbol: false,
        smooth: false,
        connectNulls: false,
        lineStyle: { width: 1.6 },
        data: (result.series[ticker] ?? []).map((point) => [point.date, point.value]),
      })),
    };
  }, [result, tickers]);

  return (
    <div className="space-y-4">
      <div className="flex items-baseline justify-between gap-3 flex-wrap">
        <h1 className="text-xl font-bold">多股对比</h1>
        <span className="note">
          选择 {MIN_TICKERS}–{MAX_TICKERS} 只标的；估值使用统一假设
        </span>
      </div>

      <div className="card">
        <div className="flex justify-between items-start gap-3 flex-wrap mb-3">
          <div>
            <h2 className="card-title !mb-0">常用对比组合</h2>
            <p className="note mt-1">保存 2–6 只标的，下次一键加载；按用户隔离。</p>
          </div>
        </div>

        <div className="flex gap-2 flex-wrap items-end mb-3">
          <input
            className="input w-56"
            placeholder="组合名称，例如：云计算"
            aria-label="对比组合名称"
            maxLength={80}
            value={presetName}
            onChange={(e) => setPresetName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void savePreset();
            }}
          />
          <button
            type="button"
            className="btn btn-primary text-xs"
            disabled={
              tickers.length < MIN_TICKERS ||
              !presetName.trim() ||
              createPreset.isPending
            }
            title={
              tickers.length < MIN_TICKERS
                ? `至少需要 ${MIN_TICKERS} 只标的`
                : "保存当前对比列表"
            }
            onClick={() => void savePreset()}
          >
            保存当前组合
          </button>
        </div>

        {presetError && <p className="text-red text-xs mb-2">{presetError}</p>}

        {presets.isLoading ? (
          <p className="note">正在加载对比组合 …</p>
        ) : presets.isError ? (
          <p className="text-red text-xs">
            {(presets.error as Error)?.message ?? "对比组合加载失败"}
          </p>
        ) : presetItems.length === 0 ? (
          <p className="note">还没有保存的对比组合。</p>
        ) : (
          <div className="flex flex-col gap-1.5">
            {presetItems.map((preset) => (
              <div
                key={preset.id}
                className="flex justify-between items-center gap-2 border border-line rounded px-2 py-1.5 text-sm"
              >
                <div className="min-w-0">
                  <span className="font-semibold">{preset.name}</span>
                  <span className="note ml-2">{preset.tickers.join(" / ")}</span>
                </div>
                <div className="flex gap-1 shrink-0">
                  <button
                    type="button"
                    className="tab-chip"
                    onClick={() => loadPreset(preset)}
                  >
                    加载
                  </button>
                  <button
                    type="button"
                    className="tab-chip"
                    disabled={tickers.length < MIN_TICKERS || updatePreset.isPending}
                    title="用当前对比列表覆盖该组合"
                    onClick={() => void overwritePreset(preset)}
                  >
                    设为当前
                  </button>
                  <button
                    type="button"
                    className="tab-chip"
                    onClick={() => void removePreset(preset)}
                  >
                    删除
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="card">
        <div className="flex gap-2 flex-wrap items-center">
          <input
            className="input w-36"
            placeholder="输入代码，如 AAPL"
            aria-label="添加对比标的"
            value={input}
            onChange={(e) => setInput(e.target.value.toUpperCase())}
            onKeyDown={(e) => {
              if (e.key === "Enter") add();
            }}
          />
          <button
            type="button"
            className="btn btn-primary text-xs"
            disabled={!input.trim() || tickers.length >= MAX_TICKERS}
            onClick={add}
          >
            添加
          </button>
          {tickers.length > 0 && (
            <button
              type="button"
              className="btn btn-ghost text-xs"
              onClick={() => sync([])}
            >
              清空
            </button>
          )}
          <span className="note ml-2">{tickers.length}/{MAX_TICKERS}</span>
        </div>

        <div className="flex gap-2 flex-wrap mt-3">
          {tickers.map((ticker, index) => (
            <span
              key={ticker}
              className="flex items-center gap-1.5 px-2 py-1 rounded bg-panel2 border border-line text-sm"
            >
              <span
                className="inline-block w-2 h-2 rounded-full"
                style={{ background: SERIES_COLORS[index % SERIES_COLORS.length] }}
                aria-hidden
              />
              {ticker}
              <button
                type="button"
                className="text-muted hover:text-text bg-transparent border-0 cursor-pointer text-xs"
                aria-label={`移除 ${ticker}`}
                onClick={() => remove(ticker)}
              >
                ✕
              </button>
            </span>
          ))}
          {tickers.length === 0 && <span className="note">先添加至少两只标的。</span>}
        </div>
        {message && <p className="note mt-2">{message}</p>}
      </div>

      {tickers.length < MIN_TICKERS ? (
        <div className="card">
          <p className="note">添加 {MIN_TICKERS} 只及以上标的开始对比。</p>
        </div>
      ) : isError ? (
        <div className="card">
          <p className="text-red text-sm">{(error as Error)?.message ?? "对比失败"}</p>
        </div>
      ) : (
        <>
          <div className="card">
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <h2 className="card-title mb-0">归一化走势</h2>
              <div className="flex gap-1">
                {PERIODS.map((item) => (
                  <button
                    key={item.key}
                    type="button"
                    className={`tab-chip ${period === item.key ? "tab-chip-on" : ""}`}
                    onClick={() => setPeriod(item.key)}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>
            <p className="note mt-1">
              各自以区间内第一个有数据的交易日为 100；不同市场的节假日不同，曲线起点可能差一两天。
            </p>
            {isLoading ? (
              <p className="note mt-3">计算中…</p>
            ) : option ? (
              <ReactECharts option={option} style={{ height: 320 }} notMerge lazyUpdate />
            ) : null}
          </div>

          {result && (
            <>
              <div className="card">
                <h2 className="card-title">指标对比</h2>
                <p className="note mb-2">
                  「优 / 差」由指标方向决定：估值类越低越好，增速与股息类越高越好；
                  缺失值显示「—」且不参与评选。金额类指标为各自原币，不换算。
                </p>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-muted text-xs border-b border-line">
                        <th className="text-left font-medium py-1.5">指标</th>
                        {result.tickers.map((item) => (
                          <th key={item.ticker} className="text-right font-medium py-1.5 px-2">
                            {item.ticker}
                            <span className="note ml-1">
                              {marketLabel(item.market)}
                              {item.currency ? ` · ${item.currency}` : ""}
                            </span>
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {result.metrics.map((metric) => (
                        <MetricRow
                          key={metric.key}
                          metric={metric}
                          tickers={result.tickers.map((item) => item.ticker)}
                        />
                      ))}
                    </tbody>
                  </table>
                </div>
                <p className="note mt-2">
                  「—」表示该标的缺少此项数据，不参与「优/差」评选；金额类指标若币种不同，
                  只比较数量级，不做汇率换算。
                </p>
              </div>

              <div className="card">
                <h2 className="card-title">估值对比（统一假设）</h2>
                <p className="note mb-2">{result.valuation.assumptions.note}</p>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-muted text-xs border-b border-line">
                        <th className="text-left font-medium py-1.5">标的</th>
                        <th className="text-right font-medium py-1.5">现价</th>
                        <th className="text-right font-medium py-1.5">DCF 每股价值</th>
                        <th className="text-right font-medium py-1.5">上行空间</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.valuation.rows.map((row) => (
                        <tr key={row.ticker} className="border-b border-line">
                          <td className="py-1.5 font-semibold">{row.ticker}</td>
                          <td className="text-right tabular-nums">{fmtNum(row.price)}</td>
                          <td className="text-right tabular-nums">{fmtNum(row.per_share)}</td>
                          <td
                            className={`text-right tabular-nums ${valuationClass(row.upside_pct)}`}
                          >
                            {fmtPct(row.upside_pct, 1, true)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {result.warnings.length > 0 && (
                <ul className="space-y-1">
                  {result.warnings.map((warning) => (
                    <li key={warning} className="note">
                      · {warning}
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}

function MetricRow({
  metric,
  tickers,
}: {
  metric: CompareMetric;
  tickers: string[];
}) {
  return (
    <tr className="border-b border-line">
      <td className="py-1.5 text-muted">
        {metric.label}
        {metric.direction && (
          <span className="text-xs ml-1">{metric.direction === "higher" ? "↑越高越好" : "↓越低越好"}</span>
        )}
      </td>
      {tickers.map((ticker) => {
        const value = metric.values[ticker];
        const isMissing = value === null || value === undefined;
        const isBest = metric.best === ticker;
        const isWorst = metric.worst === ticker;
        return (
          <td key={ticker} className="text-right tabular-nums px-2 py-1.5">
            <span
              className={
                isMissing
                  ? "text-muted"
                  : isBest
                    ? "text-green font-semibold"
                    : isWorst
                      ? "text-red"
                      : ""
              }
              title={isMissing ? "数据缺失，不参与优/差评选" : undefined}
            >
              {formatMetric(metric.unit, value ?? null)}
            </span>
            {!isMissing && isBest && <span className="text-green text-xs ml-1">优</span>}
            {!isMissing && isWorst && <span className="text-red text-xs ml-1">差</span>}
          </td>
        );
      })}
    </tr>
  );
}

function formatMetric(unit: string, value: number | null): string {
  if (value === null || value === undefined) return DASH;
  if (unit === "pct") return fmtPct(value, 2);
  if (unit === "x") return fmtNum(value, 2);
  return fmtBig(value);
}
