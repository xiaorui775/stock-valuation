import { useState, type CSSProperties, type ReactNode } from "react";
import {
  usePresetComparison,
  usePresetMutations,
  usePresets,
  type Preset,
  type PresetAssumptions,
} from "@/api/presets";
import { useValuation } from "@/api/valuation";
import { DASH, fmtBig, fmtNum, fmtPct, fmtYi, valuationClass } from "@/lib/format";
import WaccCard from "./WaccCard";
import ScenariosCard from "./ScenariosCard";
import ReverseDcfCard from "./ReverseDcfCard";
import ValuationHistoryCard from "./ValuationHistoryCard";
import MultiStageCard from "./MultiStageCard";
import SummaryWeightsCard from "./SummaryWeightsCard";

/** 估值工作台：假设输入 + DCF 结果 + 假设来源 + 敏感性 + 倍数 + 综合结论。 */
export default function ValuationPanel({ ticker }: { ticker: string }) {
  const [fcfYi, setFcfYi] = useState("");
  const [growth, setGrowth] = useState("");
  const [years, setYears] = useState("");
  const [terminal, setTerminal] = useState("");
  const [discount, setDiscount] = useState("");
  const [ddmGrowth, setDdmGrowth] = useState("");
  const [sensView, setSensView] = useState<"table" | "heatmap">("table");

  const params = {
    base_fcf: fcfYi === "" ? undefined : Number(fcfYi) * 1e8,
    growth: growth === "" ? undefined : Number(growth),
    years1: years === "" ? undefined : Number(years),
    terminal: terminal === "" ? undefined : Number(terminal),
    discount: discount === "" ? undefined : Number(discount),
    ddm_growth: ddmGrowth === "" ? undefined : Number(ddmGrowth),
  };

  function resetDefaults() {
    setFcfYi("");
    setGrowth("");
    setYears("");
    setTerminal("");
    setDiscount("");
    setDdmGrowth("");
  }

  const { data, isLoading, isError, error } = useValuation(ticker, params);
  const presets = usePresets(ticker);
  const { createPreset, updatePreset, deletePreset } = usePresetMutations(ticker);
  const [presetName, setPresetName] = useState("");
  const [presetError, setPresetError] = useState<string | null>(null);
  const [compareIds, setCompareIds] = useState<number[]>([]);

  const presetItems = presets.data?.data.items ?? [];
  // 预设被删除后自动从对比选择中剔除，避免请求不存在的 ID
  const selectedCompareIds = compareIds.filter((id) =>
    presetItems.some((preset) => preset.id === id),
  );
  const comparison = usePresetComparison(ticker, selectedCompareIds);

  function toggleCompare(id: number) {
    setCompareIds((previous) => {
      if (previous.includes(id)) return previous.filter((item) => item !== id);
      if (previous.length >= 6) return previous;
      return [...previous, id];
    });
  }

  function currentAssumptions(): PresetAssumptions {
    return {
      base_fcf: params.base_fcf ?? null,
      growth: params.growth ?? null,
      years1: params.years1 ?? null,
      terminal: params.terminal ?? null,
      discount: params.discount ?? null,
      ddm_growth: params.ddm_growth ?? null,
    };
  }

  async function savePreset() {
    const name = presetName.trim();
    if (!name) {
      setPresetError("请填写预设名称");
      return;
    }
    try {
      await createPreset.mutateAsync({ name, assumptions: currentAssumptions() });
      setPresetName("");
      setPresetError(null);
    } catch (e) {
      setPresetError((e as Error).message);
    }
  }

  function loadPreset(preset: Preset) {
    const a = preset.assumptions;
    setFcfYi(a.base_fcf == null ? "" : String(a.base_fcf / 1e8));
    setGrowth(a.growth == null ? "" : String(a.growth));
    setYears(a.years1 == null ? "" : String(a.years1));
    setTerminal(a.terminal == null ? "" : String(a.terminal));
    setDiscount(a.discount == null ? "" : String(a.discount));
    setDdmGrowth(a.ddm_growth == null ? "" : String(a.ddm_growth));
    setPresetError(null);
  }

  async function overwritePreset(preset: Preset) {
    try {
      await updatePreset.mutateAsync({
        id: preset.id,
        assumptions: currentAssumptions(),
      });
      setPresetError(null);
    } catch (e) {
      setPresetError((e as Error).message);
    }
  }

  async function removePreset(preset: Preset) {
    if (!window.confirm(`删除预设「${preset.name}」？`)) return;
    try {
      await deletePreset.mutateAsync(preset.id);
      setPresetError(null);
    } catch (e) {
      setPresetError((e as Error).message);
    }
  }

  if (isLoading) return <div className="note">正在计算估值 …</div>;
  if (isError)
    return <p className="text-red text-sm">{(error as Error)?.message ?? "估值计算失败"}</p>;
  if (!data) return null;

  const v = data.data;
  const inp = v.inputs;
  const compare = comparison.data?.data;
  const compareRows = compare?.items ?? [];
  const compareBase = compareRows[0];

  return (
    <div>
      <div className="card">
        <h2 className="card-title">DCF 现金流折现（两阶段）</h2>

        <form
          className="grid grid-cols-[repeat(auto-fill,minmax(150px,1fr))] gap-3 items-start mb-3"
          onSubmit={(e) => e.preventDefault()}
        >
          <Field
            label={`基准 FCF（亿 ${v.currency ?? "原币"}）`}
            hint={`默认取 ${inp.base_fcf_year ?? "—"} 财年`}
          >
            <input
              className="input w-full"
              type="number"
              step="1"
              placeholder={inp.base_fcf == null ? "—" : fmtNum(inp.base_fcf / 1e8, 0)}
              value={fcfYi}
              onChange={(e) => setFcfYi(e.target.value)}
            />
          </Field>
          <Field label="阶段一增速 %" hint={`未来 ${inp.years1} 年`}>
            <input
              className="input w-full"
              type="number"
              step="0.1"
              placeholder={String(inp.growth)}
              value={growth}
              onChange={(e) => setGrowth(e.target.value)}
            />
          </Field>
          <Field label="阶段一年数">
            <input
              className="input w-full"
              type="number"
              step="1"
              min={1}
              max={20}
              placeholder={String(inp.years1)}
              value={years}
              onChange={(e) => setYears(e.target.value)}
            />
          </Field>
          <Field label="永续增速 %">
            <input
              className="input w-full"
              type="number"
              step="0.1"
              placeholder={String(inp.terminal)}
              value={terminal}
              onChange={(e) => setTerminal(e.target.value)}
            />
          </Field>
          <Field label="折现率 %" hint="默认 CAPM 预填">
            <input
              className="input w-full"
              type="number"
              step="0.1"
              placeholder={fmtNum(inp.discount)}
              value={discount}
              onChange={(e) => setDiscount(e.target.value)}
            />
          </Field>
          <Field label="股利增速 %" hint="仅用于 DDM">
            <input
              className="input w-full"
              type="number"
              step="0.1"
              placeholder={String(inp.ddm_growth)}
              value={ddmGrowth}
              onChange={(e) => setDdmGrowth(e.target.value)}
            />
          </Field>
        </form>

        <div className="flex gap-3 items-center flex-wrap mb-4">
          <button className="btn btn-ghost" type="button" onClick={resetDefaults}>
            恢复 CAPM 默认值
          </button>
          <span className="note">
            留空即使用服务端默认：10% 阶段一增速、5 年、2.5% 永续增速、CAPM
            折现率、3% 股利增速。
          </span>
        </div>

        {inp.base_fcf !== null && inp.base_fcf < 0 && (
          <p className="text-accent text-xs mb-2">
            ⚠️ 基准 FCF 为负值，估值结果的计算仍成立，但解释力有限。
          </p>
        )}

        {v.dcf ? (
          <div className="flex gap-6 flex-wrap text-sm mb-2">
            <div>
              DCF 每股内在价值
              <b className="block text-2xl font-extrabold">{fmtNum(v.dcf.per_share)}</b>
            </div>
            <div>
              相对现价
              <b className={`block text-lg ${valuationClass(v.dcf.upside_pct)}`}>
                {v.dcf.upside_pct == null ? "—" : `${v.dcf.upside_pct > 0 ? "+" : ""}${fmtNum(v.dcf.upside_pct)}%`}
              </b>
            </div>
            <div>
              企业价值 EV
              <b className="block text-lg">{fmtBig(v.dcf.enterprise_value)}</b>
            </div>
            <div>
              股权价值
              <b className="block text-lg">{fmtBig(v.dcf.equity_value)}</b>
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
        <h2 className="card-title">假设与来源</h2>
        <div className="grid grid-cols-[repeat(auto-fill,minmax(280px,1fr))] gap-x-6">
          <SourceRow
            label="基准 FCF"
            value={`${fmtBig(v.sources.fcf.value)}（${v.sources.fcf.year ?? "—"} 财年）`}
            origin={v.sources.fcf.origin}
          />
          <SourceRow
            label="总债务"
            value={fmtBig(v.sources.balance.values.debt)}
            origin={v.sources.balance.origins.debt}
          />
          <SourceRow
            label="现金及等价物"
            value={fmtBig(v.sources.balance.values.cash)}
            origin={v.sources.balance.origins.cash}
          />
          <SourceRow
            label="股东权益"
            value={fmtBig(v.sources.balance.values.equity)}
            origin={v.sources.balance.origins.equity}
          />
          <SourceRow
            label="总股本"
            value={fmtBig(v.sources.shares.value)}
            origin={v.sources.shares.origin}
          />
          <SourceRow
            label="Beta"
            value={fmtNum(v.sources.beta.value, 3)}
            origin={v.sources.beta.origin}
          />
          <SourceRow
            label="CAPM 折现率"
            value={`${fmtNum(v.sources.capm.value)}%`}
            origin={v.sources.capm.formula}
          />
        </div>
        {v.sources.balance.note && (
          <p className="text-accent text-xs mt-2">⚠️ {v.sources.balance.note}</p>
        )}
        <p className="note mt-2">
          金额单位：{v.currency ?? "原币"}。来源随数据源变化；修改左侧输入后按新假设重新计算。
        </p>
      </div>

      <div className="card">
        <h2 className="card-title">估值预设</h2>
        <p className="note mb-3">
          把当前假设保存为命名预设，下次可一键加载。预设按标的保存，仅自己可见。
        </p>

        <div className="flex gap-2 items-end flex-wrap mb-3">
          <label className="flex flex-col gap-1.5 text-xs text-muted">
            预设名称
            <input
              className="input w-56"
              value={presetName}
              maxLength={80}
              placeholder="例如：保守假设"
              onChange={(e) => setPresetName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  void savePreset();
                }
              }}
            />
          </label>
          <button
            className="btn btn-primary"
            type="button"
            disabled={createPreset.isPending}
            onClick={() => void savePreset()}
          >
            保存当前假设
          </button>
        </div>

        {presetError && <p className="text-red text-xs mb-2">{presetError}</p>}

        {presets.isLoading ? (
          <p className="note">正在加载预设 …</p>
        ) : presets.isError ? (
          <p className="text-red text-xs">
            {(presets.error as Error)?.message ?? "预设加载失败"}
          </p>
        ) : (presets.data?.data.items.length ?? 0) === 0 ? (
          <p className="note">还没有预设。</p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>名称</th>
                <th>对比</th>
                <th>阶段一增速</th>
                <th>永续增速</th>
                <th>折现率</th>
                <th>年数</th>
                <th>更新时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {presets.data?.data.items.map((preset) => (
                <tr key={preset.id}>
                  <td>{preset.name}</td>
                  <td className="!text-center">
                    <input
                      type="checkbox"
                      className="accent-accent"
                      aria-label={`对比预设 ${preset.name}`}
                      checked={compareIds.includes(preset.id)}
                      disabled={
                        !compareIds.includes(preset.id) && compareIds.length >= 6
                      }
                      title={
                        !compareIds.includes(preset.id) && compareIds.length >= 6
                          ? "最多选择 6 个预设"
                          : "加入对比"
                      }
                      onChange={() => toggleCompare(preset.id)}
                    />
                  </td>
                  <td>{fmtPct(preset.assumptions.growth, 1)}</td>
                  <td>{fmtPct(preset.assumptions.terminal, 1)}</td>
                  <td>{fmtPct(preset.assumptions.discount, 1)}</td>
                  <td>{preset.assumptions.years1 ?? "—"}</td>
                  <td>{formatTime(preset.updated_at)}</td>
                  <td className="!text-right">
                    <div className="flex gap-1 justify-end">
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
                        onClick={() => void overwritePreset(preset)}
                      >
                        覆盖
                      </button>
                      <button
                        type="button"
                        className="tab-chip"
                        onClick={() => void removePreset(preset)}
                      >
                        删除
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <p className="note mt-2">
          「覆盖」把当前输入写入该预设；留空的输入表示使用服务端默认值。
        </p>
      </div>

      <div className="card">
        <div className="flex justify-between items-start gap-3 flex-wrap mb-2">
          <h2 className="card-title !mb-0">预设对比</h2>
          <span className="note">已选 {selectedCompareIds.length} / 最多 6</span>
        </div>
        <p className="note mb-3">
          在「估值预设」中勾选 2–6 个预设。对比使用同一份行情与财务报表，结果差异只来自假设。
        </p>

        {selectedCompareIds.length < 2 ? (
          <p className="note">至少勾选 2 个预设。</p>
        ) : comparison.isLoading ? (
          <p className="note">正在计算对比 …</p>
        ) : comparison.isError ? (
          <p className="text-red text-xs">
            {(comparison.error as Error)?.message ?? "对比计算失败"}
          </p>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>预设</th>
                    <th>基准 FCF（亿）</th>
                    <th>阶段一增速</th>
                    <th>年数</th>
                    <th>永续增速</th>
                    <th>折现率</th>
                    <th>每股价值</th>
                    <th>较首个</th>
                    <th>上行空间</th>
                    <th>终值占比</th>
                  </tr>
                </thead>
                <tbody>
                  {compareRows.map((row, index) => {
                    const delta =
                      compareBase &&
                      index > 0 &&
                      compareBase.per_share !== null &&
                      row.per_share !== null &&
                      compareBase.per_share !== 0
                        ? ((row.per_share - compareBase.per_share) /
                            compareBase.per_share) *
                          100
                        : null;
                    return (
                      <tr key={row.preset_id}>
                        <td>
                          {row.name}
                          {index === 0 && <span className="note ml-1.5">基准</span>}
                        </td>
                        <td>{fmtYi(row.base_fcf)}</td>
                        <td>{fmtPct(row.growth, 1)}</td>
                        <td>{row.years1}</td>
                        <td>{fmtPct(row.terminal, 1)}</td>
                        <td>{fmtPct(row.discount, 1)}</td>
                        <td>{fmtNum(row.per_share, 2)}</td>
                        <td>{fmtPct(delta, 2, true)}</td>
                        <td className={valuationClass(row.upside_pct)}>
                          {fmtPct(row.upside_pct, 2, true)}
                        </td>
                        <td>
                          {row.pv_terminal_ratio === null
                            ? DASH
                            : fmtPct(row.pv_terminal_ratio * 100, 1)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <div className="mt-2 space-y-1">
              {compareRows
                .filter((row) => row.note)
                .map((row) => (
                  <p key={row.preset_id} className="note text-accent">
                    {row.name}：{row.note}
                  </p>
                ))}
              {compare?.notes.map((note) => (
                <p key={note} className="note">
                  {note}
                </p>
              ))}
              {compare?.currency && (
                <p className="note">
                  金额与每股价值币种：{compare.currency}；「较首个」= (本预设每股价值 −
                  基准) / 基准。
                </p>
              )}
              {comparison.data?.meta.source && (
                <p className="note">数据来源：{comparison.data.meta.source}。</p>
              )}
            </div>
          </>
        )}
      </div>

      <div className="card">
        <div className="flex justify-between items-start gap-3 flex-wrap mb-1">
          <h3 className="font-semibold">敏感性分析（每股价值）</h3>
          <div className="flex gap-1" role="group" aria-label="敏感性展示方式">
            <button
              type="button"
              className={`tab-chip ${sensView === "table" ? "tab-chip-on" : ""}`}
              aria-pressed={sensView === "table"}
              onClick={() => setSensView("table")}
            >
              表格
            </button>
            <button
              type="button"
              className={`tab-chip ${sensView === "heatmap" ? "tab-chip-on" : ""}`}
              aria-pressed={sensView === "heatmap"}
              onClick={() => setSensView("heatmap")}
            >
              热力图
            </button>
          </div>
        </div>
        <p className="note mb-2">行：折现率（基准 ±1%、±2%）；列：永续增速。</p>
        {v.sensitivity ? (
          <SensitivityMatrix
            sensitivity={v.sensitivity}
            baseDiscount={inp.discount}
            price={v.price}
            heatmap={sensView === "heatmap"}
          />
        ) : (
          <p className="note">数据不足。</p>
        )}
        {sensView === "heatmap" && v.price !== null && (
          <p className="note mt-2">
            热力图以现价 {fmtNum(v.price)} 为基准：绿色表示每股价值高于现价，红色表示低于现价，
            颜色越深表示空间越大。
          </p>
        )}
      </div>

      <MultiStageCard
        ticker={ticker}
        growth={inp.growth}
        terminal={inp.terminal}
        discount={inp.discount}
        years={inp.years1}
      />

      <ScenariosCard
        ticker={ticker}
        growth={inp.growth}
        terminal={inp.terminal}
        discount={inp.discount}
        price={v.price}
      />

      <ReverseDcfCard
        ticker={ticker}
        price={v.price}
        terminal={inp.terminal}
        discount={inp.discount}
        years={inp.years1}
      />

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

      <ValuationHistoryCard ticker={ticker} />

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

      <WaccCard ticker={ticker} />

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
                <b className={`block text-lg ${valuationClass(v.summary.vs_price_pct)}`}>
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
            {v.summary.methods.length > 0 && (
              <div className="mt-3">
                <div className="note mb-1">参与方法（默认等权）</div>
                {v.summary.methods.map((m) => (
                  <div
                    key={m.name}
                    className="flex justify-between gap-3 py-1.5 border-b border-line text-sm"
                  >
                    <span className="text-muted">
                      {m.name} · 权重 {fmtNum(m.weight, 1)}%
                    </span>
                    <span className="font-semibold">{fmtNum(m.value)}</span>
                  </div>
                ))}
              </div>
            )}
          </>
        ) : (
          <p className="note">可用估值方法不足，暂无法给出综合结论。</p>
        )}
        <p className="text-accent text-sm mt-4">⚠️ {v.disclaimer}</p>
      </div>

      <SummaryWeightsCard
        key={ticker}
        ticker={ticker}
        methods={v.summary?.methods ?? []}
      />
    </div>
  );
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

function SourceRow({
  label,
  value,
  origin,
}: {
  label: string;
  value: string;
  origin: string;
}) {
  return (
    <div className="flex justify-between gap-3 py-2 border-b border-line text-sm">
      <div>
        {label}
        <div className="text-muted text-xs">{origin}</div>
      </div>
      <div className="font-semibold whitespace-nowrap">{value}</div>
    </div>
  );
}

interface SensitivityData {
  terminal_growths: number[];
  rows: { discount: number; values: (number | null)[] }[];
}

/** 敏感性矩阵：表格与热力图共用同一份数据（FR-VAL-03）。 */
function SensitivityMatrix({
  sensitivity,
  baseDiscount,
  price,
  heatmap,
}: {
  sensitivity: SensitivityData;
  baseDiscount: number;
  price: number | null;
  heatmap: boolean;
}) {
  return (
    <table className="data-table">
      <thead>
        <tr>
          <th>折现率 \ 永续增速</th>
          {sensitivity.terminal_growths.map((g) => (
            <th key={g}>{fmtNum(g, 1)}%</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {sensitivity.rows.map((row) => {
          const isBase = Math.abs(row.discount - baseDiscount) < 1e-9;
          return (
            <tr key={row.discount}>
              <td className={isBase ? "text-accent font-semibold" : undefined}>
                {fmtNum(row.discount)}%{isBase && <span className="note ml-1">基准</span>}
              </td>
              {row.values.map((value, i) => {
                const upside = value !== null && price ? value / price - 1 : null;
                return (
                  <td
                    key={i}
                    style={heatmap ? heatStyle(upside) : undefined}
                    title={
                      upside === null
                        ? "数据不足"
                        : `折现率 ${fmtNum(row.discount)}% / 永续增速 ${fmtNum(
                            sensitivity.terminal_growths[i],
                            1,
                          )}% → ${fmtNum(value)}（${fmtPct(upside * 100, 1, true)}）`
                    }
                  >
                    <div>{fmtNum(value)}</div>
                    {heatmap && (
                      <div className="text-[11px]">
                        {fmtPct(upside === null ? null : upside * 100, 1, true)}
                      </div>
                    )}
                  </td>
                );
              })}
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

/** 以现价为中点的红绿热力底色：高于现价绿、低于现价红；50% 空间达到最深。 */
function heatStyle(upside: number | null): CSSProperties {
  if (upside === null) return {};
  const intensity = Math.min(Math.abs(upside) / 0.5, 1);
  const alpha = 0.1 + intensity * 0.55;
  return {
    backgroundColor:
      upside >= 0 ? `rgba(29,185,84,${alpha})` : `rgba(242,54,69,${alpha})`,
  };
}

function formatTime(value: string): string {
  // 后端返回的是不带时区标记的 UTC 时间（SQLite），补 Z 后再按本地时区展示
  const iso = /[zZ]|[+-]\d\d:?\d\d$/.test(value) ? value : `${value}Z`;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}
