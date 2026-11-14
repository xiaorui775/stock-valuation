/** WACC 计算器：按币种预填无风险利率，参数可改（FR-VAL-08 / M2-03）。 */
import { useState, type ReactNode } from "react";
import { useWacc } from "@/api/valuation";
import { DASH, fmtNum } from "@/lib/format";

export default function WaccCard({ ticker }: { ticker: string }) {
  const [riskFree, setRiskFree] = useState("");
  const [erp, setErp] = useState("");
  const [beta, setBeta] = useState("");
  const [costOfDebt, setCostOfDebt] = useState("");
  const [taxRate, setTaxRate] = useState("");

  const params = {
    risk_free: riskFree === "" ? undefined : Number(riskFree),
    erp: erp === "" ? undefined : Number(erp),
    beta: beta === "" ? undefined : Number(beta),
    cost_of_debt: costOfDebt === "" ? undefined : Number(costOfDebt),
    tax_rate: taxRate === "" ? undefined : Number(taxRate),
  };

  const { data, isLoading, isError, error } = useWacc(ticker, params);
  const wacc = data?.data;
  const inputs = wacc?.inputs;
  const result = wacc?.result;

  function reset() {
    setRiskFree("");
    setErp("");
    setBeta("");
    setCostOfDebt("");
    setTaxRate("");
  }

  return (
    <div className="card">
      <div className="flex justify-between items-start gap-3 flex-wrap mb-1">
        <h2 className="card-title mb-0">WACC 计算器</h2>
        <button type="button" className="btn btn-ghost text-xs" onClick={reset}>
          恢复按币种默认
        </button>
      </div>
      <p className="note mb-3">
        无风险利率按币种预填（USD 4.0% / CNY 2.5% / HKD 3.5%），留空即使用默认值。
      </p>

      <form
        className="grid grid-cols-[repeat(auto-fill,minmax(130px,1fr))] gap-3 items-start mb-4"
        onSubmit={(e) => e.preventDefault()}
      >
        <Field label="无风险利率 r_f %" hint={inputs ? `默认 ${fmtNum(Number(inputs.risk_free), 1)}%` : undefined}>
          <input
            className="input w-full"
            type="number"
            step="0.1"
            value={riskFree}
            placeholder={inputs ? String(inputs.risk_free ?? "") : "—"}
            onChange={(e) => setRiskFree(e.target.value)}
          />
        </Field>
        <Field label="股权风险溢价 ERP %" hint="默认 5.0%">
          <input
            className="input w-full"
            type="number"
            step="0.1"
            value={erp}
            placeholder={inputs ? String(inputs.erp ?? "") : "5"}
            onChange={(e) => setErp(e.target.value)}
          />
        </Field>
        <Field label="Beta β" hint="默认取行情快照">
          <input
            className="input w-full"
            type="number"
            step="0.01"
            value={beta}
            placeholder={inputs?.beta == null ? "1" : String(inputs.beta)}
            onChange={(e) => setBeta(e.target.value)}
          />
        </Field>
        <Field label="税前债务成本 r_d %" hint="默认 4.0%">
          <input
            className="input w-full"
            type="number"
            step="0.1"
            value={costOfDebt}
            placeholder={inputs ? String(inputs.cost_of_debt ?? "") : "4"}
            onChange={(e) => setCostOfDebt(e.target.value)}
          />
        </Field>
        <Field label="实际税率 t %" hint="默认 21%">
          <input
            className="input w-full"
            type="number"
            step="0.1"
            value={taxRate}
            placeholder={inputs ? String(inputs.tax_rate ?? "") : "21"}
            onChange={(e) => setTaxRate(e.target.value)}
          />
        </Field>
      </form>

      {isLoading ? (
        <p className="note">正在计算 WACC …</p>
      ) : isError ? (
        <p className="text-red text-sm">{(error as Error)?.message ?? "WACC 计算失败"}</p>
      ) : result ? (
        <>
          <div className="flex gap-6 flex-wrap text-sm">
            <div>
              WACC
              <b className="block text-2xl font-extrabold">{fmtNum(result.wacc)}%</b>
            </div>
            <div>
              股权成本 r_e
              <b className="block text-lg">{fmtNum(result.cost_of_equity)}%</b>
              <span className="note">
                = {fmtNum(Number(inputs?.risk_free), 1)}% + β × {fmtNum(Number(inputs?.erp), 1)}%
              </span>
            </div>
            <div>
              税后债务成本
              <b className="block text-lg">{fmtNum(result.after_tax_cost_of_debt)}%</b>
            </div>
            <div>
              权重 E / D
              <b className="block text-lg">
                {fmtNum(result.weight_equity * 100, 1)}% /{" "}
                {fmtNum(result.weight_debt * 100, 1)}%
              </b>
            </div>
          </div>
          <p className="note mt-2">{wacc?.formula}</p>
        </>
      ) : (
        <p className="note">缺少债务或股权市值，无法计算 WACC。</p>
      )}
      {inputs && (
        <p className="note mt-2">
          资本结构：股东权益市值 {formatBig(inputs.equity)}，总债务 {formatBig(inputs.debt)}。
        </p>
      )}
    </div>
  );
}

function formatBig(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return DASH;
  const magnitude = Math.abs(value);
  if (magnitude >= 1e12) return `${fmtNum(value / 1e12)} 万亿`;
  if (magnitude >= 1e8) return `${fmtNum(value / 1e8)} 亿`;
  return fmtNum(value);
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
