/** 反向 DCF：求解现价隐含的阶段一增速（FR-VAL-10 / M2-05）。 */
import { useState, type ReactNode } from "react";
import { useReverseDcf } from "@/api/valuation";
import { fmtNum, fmtPct } from "@/lib/format";

export default function ReverseDcfCard({
  ticker,
  price,
  terminal,
  discount,
  years,
}: {
  ticker: string;
  price: number | null;
  terminal: number;
  discount: number;
  years: number;
}) {
  const [targetPrice, setTargetPrice] = useState("");
  const [terminalGrowth, setTerminalGrowth] = useState("");
  const [discountRate, setDiscountRate] = useState("");
  const [growthYears, setGrowthYears] = useState("");
  const mutation = useReverseDcf(ticker);

  async function solve() {
    try {
      await mutation.mutateAsync({
        price: targetPrice === "" ? undefined : Number(targetPrice),
        terminal: terminalGrowth === "" ? undefined : Number(terminalGrowth),
        discount: discountRate === "" ? undefined : Number(discountRate),
        years1: growthYears === "" ? undefined : Number(growthYears),
      });
    } catch {
      // 错误信息由 mutation.isError 渲染
    }
  }

  const result = mutation.data?.data;
  const implied = result?.implied_growth ?? null;
  const num = (value: number) => String(Math.round(value * 100) / 100);

  return (
    <div className="card">
      <h2 className="card-title">反向 DCF</h2>
      <p className="note mb-3">
        用二分法求解「现价隐含的阶段一增速」：给定现价、永续增速与折现率，反推需要多高的
        5 年增速才能支撑当前价格。这是从价格反推的结果，不代表对未来的判断。
      </p>

      <form
        className="grid grid-cols-[repeat(auto-fill,minmax(140px,1fr))] gap-3 items-start mb-3"
        onSubmit={(e) => e.preventDefault()}
      >
        <Field label="目标价格" hint={price != null ? `现价 ${fmtNum(price)}` : undefined}>
          <input
            className="input w-full"
            type="number"
            step="0.01"
            placeholder={price == null ? "—" : num(price)}
            value={targetPrice}
            onChange={(e) => setTargetPrice(e.target.value)}
          />
        </Field>
        <Field label="阶段一增速年数">
          <input
            className="input w-full"
            type="number"
            step="1"
            min={1}
            max={20}
            placeholder={num(years)}
            value={growthYears}
            onChange={(e) => setGrowthYears(e.target.value)}
          />
        </Field>
        <Field label="永续增速 %">
          <input
            className="input w-full"
            type="number"
            step="0.1"
            placeholder={num(terminal)}
            value={terminalGrowth}
            onChange={(e) => setTerminalGrowth(e.target.value)}
          />
        </Field>
        <Field label="折现率 %">
          <input
            className="input w-full"
            type="number"
            step="0.1"
            placeholder={num(discount)}
            value={discountRate}
            onChange={(e) => setDiscountRate(e.target.value)}
          />
        </Field>
      </form>

      <button
        type="button"
        className="btn btn-primary"
        disabled={mutation.isPending}
        onClick={() => void solve()}
      >
        {mutation.isPending ? "求解中…" : "求解隐含增速"}
      </button>

      {mutation.isError && (
        <p className="text-red text-xs mt-2">
          {(mutation.error as Error)?.message ?? "求解失败"}
        </p>
      )}

      {result && (
        <div className="mt-4">
          {implied == null ? (
            <p className="text-accent text-sm">{result.reason ?? "无法求解"}</p>
          ) : (
            <>
              <div className="flex gap-6 flex-wrap text-sm">
                <div>
                  市场隐含阶段一增速
                  <b className="block text-2xl font-extrabold">{fmtPct(implied, 2)}</b>
                </div>
                <div>
                  该增速下的每股价值
                  <b className="block text-lg">{fmtNum(result.value_at_solution)}</b>
                </div>
                <div>
                  求解区间
                  <b className="block text-lg">
                    {result.range
                      ? `${fmtNum(result.range[0], 0)}% ~ ${fmtNum(result.range[1], 0)}%`
                      : "—"}
                  </b>
                </div>
              </div>
              <p className="note mt-2">
                {describe(implied)}　求解精度 0.01 个百分点；若现价超出了可解区间，会给出原因而不是编造结果。
              </p>
            </>
          )}
        </div>
      )}
    </div>
  );
}

function describe(growth: number): string {
  if (growth < 0) return "事实陈述：当前价格隐含的阶段一增速为负值。";
  if (growth < 5) return "事实陈述：当前价格隐含的阶段一增速低于 5%。";
  if (growth < 15) return "事实陈述：当前价格隐含的阶段一增速处于 5%–15% 区间。";
  return "事实陈述：当前价格隐含的阶段一增速高于 15%，属于较高的增长预期。";
}

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1.5 text-xs text-muted">
      <span>{label}</span>
      {children}
      {hint && <span className="text-[11px]">{hint}</span>}
    </label>
  );
}
