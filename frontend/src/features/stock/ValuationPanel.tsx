import { useState } from "react";
import { useValuation, useWacc } from "@/api/valuation";
import { changeClass, fmtBig, fmtNum, fmtPct } from "@/lib/format";

/** 估值工作台：假设输入 + DCF 结果 + 敏感性 + 倍数 + 综合结论。 */
export default function ValuationPanel({ ticker }: { ticker: string }) {
  const [growth, setGrowth] = useState("");
  const [terminal, setTerminal] = useState("");
  const [discount, setDiscount] = useState("");
  const [ddmGrowth, setDdmGrowth] = useState("");

  const params = {
    growth: growth === "" ? undefined : Number(growth),
    terminal: terminal === "" ? undefined : Number(terminal),
    discount: discount === "" ? undefined : Number(discount),
    ddm_growth: ddmGrowth === "" ? undefined : Number(ddmGrowth),
  };

  const { data, isLoading, isError, error } = useValuation(ticker, params);
  const wacc = useWacc(ticker);

  if (isLoading) return <div className="note">正在计算估值 …</div>;
  if (isError)
    return <p className="text-red text-sm">{(error as Error)?.message ?? "估值计算失败"}</p>;
  if (!data) return null;

  const v = data.data;
  const inp = v.inputs;

  return (
    <div>
      <div className="card">
        <h2 className="card-title">DCF 现金流折现（两阶段）</h2>

        <div className="text-muted text-xs leading-relaxed mb-3">
          基准 FCF（{inp.base_fcf_year ?? "—"} 财年）：<b className="text-text">{fmtBig(inp.base_fcf)}</b> ·
          总债务：<b className="text-text">{fmtBig(inp.total_debt)}</b> · 现金：
          <b className="text-text">{fmtBig(inp.total_cash)}</b> · 总股本：
          <b className="text-text">{fmtBig(inp.shares_outstanding)}</b>
          <br />
          CAPM 折现率 = 4% + Beta({fmtNum(inp.beta)}) × 5% ={" "}
          <b className="text-text">{fmtNum(inp.discount_default_capm)}%</b>
          {inp.balance_note && <span className="text-accent"> ⚠️ {inp.balance_note}</span>}
        </div>

        <form
          className="flex gap-3 flex-wrap items-end mb-4"
          onSubmit={(e) => e.preventDefault()}
        >
          <label className="flex flex-col gap-1.5 text-xs text-muted">
            阶段一增速 %（未来 {inp.years1} 年）
            <input
              className="input w-36"
              type="number"
              step="0.1"
              placeholder={String(inp.growth)}
              value={growth}
              onChange={(e) => setGrowth(e.target.value)}
            />
          </label>
          <label className="flex flex-col gap-1.5 text-xs text-muted">
            永续增速 %
            <input
              className="input w-28"
              type="number"
              step="0.1"
              placeholder={String(inp.terminal)}
              value={terminal}
              onChange={(e) => setTerminal(e.target.value)}
            />
          </label>
          <label className="flex flex-col gap-1.5 text-xs text-muted">
            折现率 %（CAPM 预填，可改）
            <input
              className="input w-32"
              type="number"
              step="0.1"
              placeholder={fmtNum(inp.discount)}
              value={discount}
              onChange={(e) => setDiscount(e.target.value)}
            />
          </label>
          <label className="flex flex-col gap-1.5 text-xs text-muted">
            股利增速 %
            <input
              className="input w-28"
              type="number"
              step="0.1"
              placeholder={String(inp.ddm_growth)}
              value={ddmGrowth}
              onChange={(e) => setDdmGrowth(e.target.value)}
            />
          </label>
          <button
            className="btn btn-ghost"
            type="button"
            onClick={() => {
              setGrowth("");
              setTerminal("");
              setDiscount("");
              setDdmGrowth("");
            }}
          >
            恢复默认
          </button>
        </form>

        {v.dcf ? (
          <div className="flex gap-6 flex-wrap text-sm mb-2">
            <div>
              DCF 每股内在价值
              <b className="block text-2xl font-extrabold">{fmtNum(v.dcf.per_share)}</b>
            </div>
            <div>
              相对现价
              <b className={`block text-lg ${changeClass(v.dcf.upside_pct)}`}>
                {v.dcf.upside_pct == null ? "—" : `${v.dcf.upside_pct > 0 ? "+" : ""}${fmtNum(v.dcf.upside_pct)}%`}
              </b>
            </div>
            <div>
              企业价值 EV
              <b className="block text-lg">{fmtBig(v.dcf.enterprise_value)}</b>
            </div>
            <div>
              终值占 EV
              <b className="block text-lg">
                {v.dcf.pv_terminal_ratio == null ? "—" : fmtNum(v.dcf.pv_terminal_ratio * 100, 1) + "%"}
              </b>
            </div>
          </div>
        ) : (
          <p className="note">自由现金流或股本数据缺失，无法计算 DCF。</p>
        )}
        <p className="note">{v.dcf?.formula}</p>
      </div>

      <div className="card">
        <h3 className="font-semibold mb-1">敏感性分析（每股价值）</h3>
        <p className="note mb-2">行：折现率（基准 ±1%、±2%）；列：永续增速。</p>
        {v.sensitivity ? (
          <table className="data-table">
            <thead>
              <tr>
                <th>折现率 \ 永续增速</th>
                {v.sensitivity.terminal_growths.map((g) => (
                  <th key={g}>{fmtNum(g, 1)}%</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {v.sensitivity.rows.map((row) => (
                <tr key={row.discount}>
                  <td>{fmtNum(row.discount)}%</td>
                  {row.values.map((val, i) => (
                    <td key={i}>{fmtNum(val)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="note">数据不足。</p>
        )}
      </div>

      <div className="card">
        <h2 className="card-title">估值倍数与经典公式</h2>
        {v.multiples.map((m) => (
          <div className="flex justify-between gap-3 py-2 border-b border-line text-sm" key={m.name}>
            <div>
              {m.name}
              <div className="text-muted text-xs">{m.formula}</div>
            </div>
            <div className="font-bold">{fmtNum(m.value)}</div>
          </div>
        ))}
      </div>

      {v.ddm && (
        <div className="card">
          <h2 className="card-title">股利折现（Gordon 增长模型）</h2>
          <div className="flex gap-6 flex-wrap text-sm">
            <div>
              每股价值
              <b className="block text-lg">{fmtNum(v.ddm.per_share)}</b>
            </div>
            <div>
              当前股息率
              <b className="block text-lg">{fmtPct(v.ddm.dividend_yield)}</b>
            </div>
            <div>
              假设增速
              <b className="block text-lg">{fmtPct(v.ddm.growth)}</b>
            </div>
            <div>
              折现率
              <b className="block text-lg">{fmtPct(v.ddm.discount)}</b>
            </div>
          </div>
          <p className="note mt-2">{v.ddm.formula}</p>
        </div>
      )}

      {wacc.data?.data.result && (
        <div className="card">
          <h2 className="card-title">WACC</h2>
          <div className="flex gap-6 flex-wrap text-sm">
            <div>
              WACC
              <b className="block text-lg">{fmtNum(wacc.data.data.result.wacc)}%</b>
            </div>
            <div>
              股权成本
              <b className="block text-lg">{fmtNum(wacc.data.data.result.cost_of_equity)}%</b>
            </div>
            <div>
              税后债务成本
              <b className="block text-lg">{fmtNum(wacc.data.data.result.after_tax_cost_of_debt)}%</b>
            </div>
          </div>
          <p className="note mt-2">{wacc.data.data.formula}</p>
        </div>
      )}

      <div className="card">
        <h2 className="card-title">综合结论（模型输出）</h2>
        {v.summary ? (
          <>
            <div className="flex gap-6 flex-wrap text-sm">
              <div>
                平均每股价值
                <b className="block text-lg">{fmtNum(v.summary.average_value)}</b>
              </div>
              <div>
                参与方法数
                <b className="block text-lg">{v.summary.methods_used}</b>
              </div>
              <div>
                相对现价
                <b className={`block text-lg ${changeClass(v.summary.vs_price_pct)}`}>
                  {v.summary.vs_price_pct > 0 ? "+" : ""}
                  {fmtNum(v.summary.vs_price_pct)}%
                </b>
              </div>
              <div>
                模型判定
                <b
                  className={`block text-lg ${
                    v.summary.band === "低估"
                      ? "text-green"
                      : v.summary.band === "高估"
                        ? "text-red"
                        : "text-accent"
                  }`}
                >
                  {v.summary.band}
                </b>
              </div>
            </div>
            <p className="note mt-2">{v.summary.note}</p>
          </>
        ) : (
          <p className="note">可用估值方法不足，暂无法给出综合结论。</p>
        )}
        <p className="text-accent text-sm mt-4">⚠️ {v.disclaimer}</p>
      </div>
    </div>
  );
}
