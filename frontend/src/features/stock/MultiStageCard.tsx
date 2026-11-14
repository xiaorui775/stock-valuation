/** 三阶段 DCF / DDM：显式期 + 线性衰减期 + 永续期（FR-VAL-12）。 */
import { useState, type ReactNode } from "react";
import { useMultistage, type MultiStageParams } from "@/api/valuation";
import { DASH, fmtBig, fmtNum, fmtPct, valuationClass } from "@/lib/format";

export default function MultiStageCard({
  ticker,
  growth,
  terminal,
  discount,
  years,
}: {
  ticker: string;
  growth: number;
  terminal: number;
  discount: number;
  years: number;
}) {
  const [values, setValues] = useState({
    growth: "",
    terminal: "",
    discount: "",
    years1: "",
    fade_years: "",
  });
  const params: MultiStageParams = {
    growth: values.growth === "" ? undefined : Number(values.growth),
    terminal: values.terminal === "" ? undefined : Number(values.terminal),
    discount: values.discount === "" ? undefined : Number(values.discount),
    years1: values.years1 === "" ? undefined : Number(values.years1),
    fade_years: values.fade_years === "" ? undefined : Number(values.fade_years),
  };
  const { data, isLoading, isError, error } = useMultistage(ticker, params);
  const view = data?.data;
  const set = (key: keyof typeof values) => (event: { target: { value: string } }) =>
    setValues((prev) => ({ ...prev, [key]: event.target.value }));
  // 默认值来自 CAPM 计算，可能是 9.899999999999999，展示前收敛到两位小数
  const num = (value: number) => String(Math.round(value * 100) / 100);

  return (
    <div className="card">
      <h2 className="card-title">三阶段 DCF / 股利折现</h2>
      <p className="note mb-3">
        显式期按固定增速增长，随后增速线性衰减到永续增速，最后按永续模型计算终值。
        与两阶段模型相比，衰减期让高增长不会突然中断；期限对齐后，结果低于「同期限恒定高增速」。
      </p>

      <form
        className="grid grid-cols-[repeat(auto-fill,minmax(130px,1fr))] gap-3 items-start mb-3"
        onSubmit={(e) => e.preventDefault()}
      >
        <Field label="阶段一增速 %">
          <input
            className="input w-full"
            type="number"
            step="0.1"
            placeholder={num(growth)}
            value={values.growth}
            onChange={set("growth")}
          />
        </Field>
        <Field label="显式期年数">
          <input
            className="input w-full"
            type="number"
            step="1"
            min={1}
            max={20}
            placeholder={String(years)}
            value={values.years1}
            onChange={set("years1")}
          />
        </Field>
        <Field label="衰减期年数">
          <input
            className="input w-full"
            type="number"
            step="1"
            min={0}
            max={20}
            placeholder="5"
            value={values.fade_years}
            onChange={set("fade_years")}
          />
        </Field>
        <Field label="永续增速 %">
          <input
            className="input w-full"
            type="number"
            step="0.1"
            placeholder={num(terminal)}
            value={values.terminal}
            onChange={set("terminal")}
          />
        </Field>
        <Field label="折现率 %">
          <input
            className="input w-full"
            type="number"
            step="0.1"
            placeholder={num(discount)}
            value={values.discount}
            onChange={set("discount")}
          />
        </Field>
      </form>

      {isLoading && <p className="note">计算中…</p>}
      {isError && (
        <p className="text-red text-xs">{(error as Error)?.message ?? "计算失败"}</p>
      )}

      {view && (
        <div className="space-y-4">
          {view.missing.length > 0 && (
            <ul className="note space-y-0.5">
              {view.missing.map((item) => (
                <li key={item} className="text-accent">
                  {item}
                </li>
              ))}
            </ul>
          )}

          {view.dcf ? (
            <div>
              <div className="flex gap-6 flex-wrap text-sm">
                <div>
                  三阶段 DCF 每股价值
                  <b className="block text-2xl font-extrabold">
                    {fmtNum(view.dcf.per_share)}
                  </b>
                </div>
                <div>
                  相对现价
                  <b
                    className={`block text-lg ${valuationClass(view.dcf.upside_pct)}`}
                  >
                    {fmtPct(view.dcf.upside_pct, 2, true)}
                  </b>
                </div>
                <div>
                  覆盖年数
                  <b className="block text-lg">{view.dcf.years} 年</b>
                </div>
                <div>
                  终值占比
                  <b className="block text-lg">
                    {fmtPct(
                      view.dcf.pv_terminal_ratio == null
                        ? null
                        : view.dcf.pv_terminal_ratio * 100,
                      1,
                    )}
                  </b>
                </div>
              </div>
              <p className="note mt-2">
                基准自由现金流 {fmtBig(view.assumptions.base_fcf)}（
                {view.assumptions.base_fcf_source}）；假设 {fmtNum(view.assumptions.growth, 1)}% ×{" "}
                {view.assumptions.years1} 年 → 线性衰减到 {fmtNum(view.assumptions.terminal, 1)}% ×{" "}
                {view.assumptions.fade_years} 年 → 永续。
              </p>
            </div>
          ) : (
            <p className="note">缺少自由现金流或总股本，无法计算三阶段 DCF。</p>
          )}

          <div className="border-t border-line pt-3">
            <div className="text-sm mb-1">三阶段股利折现（DDM）</div>
            {view.ddm ? (
              <>
                <div className="flex gap-6 flex-wrap text-sm">
                  <div>
                    每股价值
                    <b className="block text-lg">{fmtNum(view.ddm.per_share)}</b>
                  </div>
                  <div>
                    相对现价
                    <b className={`block text-lg ${valuationClass(view.ddm.upside_pct)}`}>
                      {fmtPct(view.ddm.upside_pct, 2, true)}
                    </b>
                  </div>
                  <div>
                    当前股息率
                    <b className="block text-lg">{fmtPct(view.ddm.dividend_yield)}</b>
                  </div>
                  <div>
                    每股股利 DPS
                    <b className="block text-lg">{fmtNum(view.ddm.dps)}</b>
                  </div>
                  <div>
                    终值占比
                    <b className="block text-lg">
                      {fmtPct(
                        view.ddm.terminal_ratio == null
                          ? null
                          : view.ddm.terminal_ratio * 100,
                        1,
                      )}
                    </b>
                  </div>
                </div>
                <p className="note mt-2">
                  显式期现值 {fmtNum(view.ddm.pv_explicit)} + 衰减期现值{" "}
                  {fmtNum(view.ddm.pv_fade)} + 终值现值 {fmtNum(view.ddm.pv_terminal)} =
                  每股价值（{view.ddm.years} 年）。
                </p>
              </>
            ) : (
              <p className="note">{view.ddm_reason ?? DASH}</p>
            )}
          </div>

          <p className="note">{view.formula}</p>
        </div>
      )}
    </div>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="flex flex-col gap-1.5 text-xs text-muted">
      <span>{label}</span>
      {children}
    </label>
  );
}
