/** 情景分析：Bear / Base / Bull 三套假设、概率权重与期望值（FR-VAL-09）。 */
import { useState } from "react";
import { useScenarios } from "@/api/valuation";
import { fmtNum, fmtPct, valuationClass } from "@/lib/format";

interface Row {
  name: "bear" | "base" | "bull";
  label: string;
  growth: string;
  terminal: string;
  discount: string;
  probability: string;
}

const LABELS: Record<string, string> = {
  bear: "悲观",
  base: "基准",
  bull: "乐观",
};

function round1(value: number): number {
  return Math.round(value * 10) / 10;
}

function buildRows(growth: number, terminal: number, discount: number): Row[] {
  return [
    {
      name: "bear",
      label: "悲观",
      growth: String(round1(Math.max(growth - 5, -20))),
      terminal: String(round1(Math.max(terminal - 1, 0))),
      discount: String(round1(discount + 2)),
      probability: "25",
    },
    {
      name: "base",
      label: "基准",
      growth: String(round1(growth)),
      terminal: String(round1(terminal)),
      discount: String(round1(discount)),
      probability: "50",
    },
    {
      name: "bull",
      label: "乐观",
      growth: String(round1(growth + 5)),
      terminal: String(round1(terminal + 1)),
      discount: String(round1(discount - 1)),
      probability: "25",
    },
  ];
}

export default function ScenariosCard({
  ticker,
  growth,
  terminal,
  discount,
  price,
}: {
  ticker: string;
  growth: number;
  terminal: number;
  discount: number;
  price: number | null;
}) {
  const [rows, setRows] = useState<Row[]>(() => buildRows(growth, terminal, discount));
  const [error, setError] = useState<string | null>(null);
  const mutation = useScenarios(ticker);

  const probabilitySum = rows.reduce((sum, row) => {
    const value = Number(row.probability);
    return sum + (Number.isFinite(value) ? value : 0);
  }, 0);

  function update(index: number, field: keyof Row, value: string) {
    setRows((current) =>
      current.map((row, i) => (i === index ? { ...row, [field]: value } : row)),
    );
  }

  async function run() {
    setError(null);
    const invalid = rows.some(
      (row) =>
        !Number.isFinite(Number(row.growth)) ||
        !Number.isFinite(Number(row.terminal)) ||
        !Number.isFinite(Number(row.discount)) ||
        !Number.isFinite(Number(row.probability)),
    );
    if (invalid) {
      setError("请填写有效的数值");
      return;
    }
    if (Math.abs(probabilitySum - 100) > 1e-6) {
      setError(`概率之和为 ${fmtNum(probabilitySum, 1)}%，必须等于 100%`);
      return;
    }
    try {
      await mutation.mutateAsync(
        rows.map((row) => ({
          name: row.name,
          growth: Number(row.growth),
          terminal: Number(row.terminal),
          discount: Number(row.discount),
          probability: Number(row.probability),
        })),
      );
    } catch (e) {
      setError((e as Error).message);
    }
  }

  const result = mutation.data?.data;
  const scenarios = result?.scenarios ?? [];
  const maxValue = Math.max(
    ...scenarios.map((s) => s.per_share ?? 0),
    price ?? 0,
    1,
  );

  return (
    <div className="card">
      <div className="flex justify-between items-start gap-3 flex-wrap mb-1">
        <h2 className="card-title mb-0">情景分析</h2>
        <button
          type="button"
          className="btn btn-ghost text-xs"
          onClick={() => {
            setRows(buildRows(growth, terminal, discount));
            setError(null);
          }}
        >
          按当前假设重置
        </button>
      </div>
      <p className="note mb-3">
        三套假设分别做 DCF；概率之和必须为 100%。加权期望值 = Σ 每股价值 × 概率。
      </p>

      <div className="overflow-x-auto">
        <table className="data-table">
          <thead>
            <tr>
              <th>情景</th>
              <th>阶段一增速 %</th>
              <th>永续增速 %</th>
              <th>折现率 %</th>
              <th>概率 %</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => (
              <tr key={row.name}>
                <td>
                  <span className="font-semibold">{LABELS[row.name]}</span>
                </td>
                <td>
                  <input
                    className="input w-20 !py-1"
                    type="number"
                    step="0.5"
                    value={row.growth}
                    onChange={(e) => update(index, "growth", e.target.value)}
                  />
                </td>
                <td>
                  <input
                    className="input w-20 !py-1"
                    type="number"
                    step="0.5"
                    value={row.terminal}
                    onChange={(e) => update(index, "terminal", e.target.value)}
                  />
                </td>
                <td>
                  <input
                    className="input w-20 !py-1"
                    type="number"
                    step="0.5"
                    value={row.discount}
                    onChange={(e) => update(index, "discount", e.target.value)}
                  />
                </td>
                <td>
                  <input
                    className="input w-20 !py-1"
                    type="number"
                    step="5"
                    value={row.probability}
                    onChange={(e) => update(index, "probability", e.target.value)}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex gap-3 items-center flex-wrap mt-3">
        <button
          type="button"
          className="btn btn-primary"
          disabled={mutation.isPending}
          onClick={() => void run()}
        >
          {mutation.isPending ? "计算中…" : "计算情景"}
        </button>
        <span className={Math.abs(probabilitySum - 100) > 1e-6 ? "text-accent text-xs" : "note"}>
          概率合计 {fmtNum(probabilitySum, 1)}%
        </span>
        {error && <span className="text-red text-xs">{error}</span>}
      </div>

      {result?.error && <p className="text-red text-xs mt-2">{result.error}</p>}

      {scenarios.length > 0 && (
        <>
          <div className="flex gap-6 flex-wrap text-sm mt-4">
            <div>
              加权期望价值
              <b className="block text-2xl font-extrabold">{fmtNum(result?.weighted)}</b>
            </div>
            <div>
              相对现价
              <b
                className={`block text-lg ${valuationClass(result?.weighted_upside_pct ?? null)}`}
              >
                {fmtPct(result?.weighted_upside_pct ?? null, 2, true)}
              </b>
            </div>
          </div>

          <div className="mt-4 space-y-2" aria-label="情景对比">
            {scenarios.map((scenario) => {
              const value = scenario.per_share;
              const width = value == null ? 0 : Math.max((value / maxValue) * 100, 2);
              const undervalued = (value ?? 0) >= (price ?? 0);
              return (
                <div key={scenario.name} className="flex items-center gap-2 text-sm">
                  <span className="w-12 text-muted shrink-0">
                    {LABELS[scenario.name] ?? scenario.name}
                  </span>
                  <div className="flex-1 bg-panel2 rounded h-4 relative overflow-hidden">
                    <div
                      className="h-4 rounded"
                      style={{
                        width: `${width}%`,
                        backgroundColor: undervalued
                          ? "rgba(29,185,84,0.55)"
                          : "rgba(242,54,69,0.55)",
                      }}
                    />
                    {price !== null && (
                      <div
                        className="absolute top-0 bottom-0 border-l border-accent"
                        style={{ left: `${(price / maxValue) * 100}%` }}
                        title={`现价 ${fmtNum(price)}`}
                      />
                    )}
                  </div>
                  <span className="w-24 text-right font-semibold">
                    {fmtNum(value)}
                  </span>
                  <span
                    className={`w-20 text-right text-xs ${valuationClass(scenario.upside_pct)}`}
                  >
                    {fmtPct(scenario.upside_pct, 1, true)}
                  </span>
                </div>
              );
            })}
            <p className="note">竖线为现价 {fmtNum(price)}；绿色表示该情景高于现价。</p>
          </div>
        </>
      )}
    </div>
  );
}
