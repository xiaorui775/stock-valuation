/** 自定义权重的综合估值（FR-VAL-13）。 */
import { useState } from "react";
import { useSummaryWeights } from "@/api/valuation";
import { fmtNum, fmtPct, valuationClass } from "@/lib/format";

export interface MethodValue {
  name: string;
  value: number;
}

/** 等权且合计恰好 100：3 个方法给 34/33/33，而不是四舍五入成 33/33/33 的 99。 */
function equalWeights(names: string[]): Record<string, number> {
  if (names.length === 0) return {};
  const base = Math.floor(100 / names.length);
  const remainder = 100 - base * names.length;
  return Object.fromEntries(
    names.map((name, index) => [name, base + (index < remainder ? 1 : 0)]),
  );
}

export default function SummaryWeightsCard({
  ticker,
  methods,
}: {
  ticker: string;
  methods: MethodValue[];
}) {
  const [weights, setWeights] = useState<Record<string, number>>(() =>
    equalWeights(methods.map((m) => m.name)),
  );
  const [enabled, setEnabled] = useState<Set<string>>(
    () => new Set(methods.map((m) => m.name)),
  );
  const mutation = useSummaryWeights(ticker);

  const total = [...enabled].reduce((sum, name) => sum + (weights[name] ?? 0), 0);

  function toggle(name: string) {
    setEnabled((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  }

  async function apply() {
    try {
      await mutation.mutateAsync(
        [...enabled].map((name) => ({ name, weight: weights[name] ?? 0 })),
      );
    } catch {
      // 错误信息由 mutation.isError 渲染
    }
  }

  const result = mutation.data?.data;

  if (methods.length < 2) {
    return (
      <div className="card">
        <h2 className="card-title">自定义权重</h2>
        <p className="note">
          可用估值方法不足两个（当前 {methods.length} 个），无法做加权综合。
        </p>
      </div>
    );
  }

  return (
    <div className="card">
      <h2 className="card-title">自定义权重综合</h2>
      <p className="note mb-3">
        勾选参与综合的方法并设置权重，权重合计必须为 100%（不做自动归一化，避免显示与实际不一致）。
        各方法的每股价值取自上方 DCF / DDM / Graham 的当前假设。
      </p>

      <div className="space-y-2">
        {methods.map((method) => (
          <div key={method.name} className="flex items-center gap-3 text-sm">
            <label className="flex items-center gap-2 w-40">
              <input
                type="checkbox"
                checked={enabled.has(method.name)}
                onChange={() => toggle(method.name)}
              />
              <span>{method.name}</span>
            </label>
            <span className="text-muted w-28">
              {fmtNum(method.value)} / 股
            </span>
            <input
              className="input w-24"
              type="number"
              min={0}
              max={100}
              step="1"
              disabled={!enabled.has(method.name)}
              value={weights[method.name] ?? 0}
              onChange={(e) =>
                setWeights((prev) => ({ ...prev, [method.name]: Number(e.target.value) }))
              }
            />
            <span className="text-muted text-xs">%</span>
          </div>
        ))}
      </div>

      <div className="flex items-center gap-3 mt-3">
        <button
          type="button"
          className="btn btn-primary"
          disabled={mutation.isPending}
          onClick={() => void apply()}
        >
          {mutation.isPending ? "计算中…" : "按权重计算"}
        </button>
        <span className={`text-xs ${Math.abs(total - 100) < 0.05 ? "text-muted" : "text-accent"}`}>
          权重合计 {fmtNum(total, 1)}%
          {Math.abs(total - 100) >= 0.05 && "（需为 100%）"}
        </span>
      </div>

      {mutation.isError && (
        <p className="text-red text-xs mt-2">
          {(mutation.error as Error)?.message ?? "计算失败"}
        </p>
      )}

      {result && (
        <div className="mt-4">
          <div className="flex gap-6 flex-wrap text-sm">
            <div>
              加权每股价值
              <b className="block text-2xl font-extrabold">{fmtNum(result.weighted_value)}</b>
            </div>
            <div>
              相对现价
              <b className={`block text-lg ${valuationClass(result.vs_price_pct)}`}>
                {fmtPct(result.vs_price_pct, 2, true)}
              </b>
            </div>
            <div>
              模型判定
              <b
                className={`block text-lg ${
                  result.band === "低估"
                    ? "text-green"
                    : result.band === "高估"
                      ? "text-red"
                      : "text-accent"
                }`}
              >
                {result.band ?? "—"}
              </b>
            </div>
          </div>
          <div className="mt-3">
            {result.methods.map((m) => (
              <div
                key={m.name}
                className="flex justify-between gap-3 py-1.5 border-b border-line text-sm"
              >
                <span className="text-muted">
                  {m.name} · 权重 {fmtNum(m.weight, 1)}%
                </span>
                <span className="tabular-nums">
                  {fmtNum(m.value)} → 贡献 {fmtNum(m.contribution)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
