/** 投资组合：多组合与持仓录入（FR-PORT-01 / 02）。
 *
 * 只做录入与展示，不在这里计算市值/盈亏——那属于 M2-10 的组合汇总，
 * 需要行情与汇率，避免前端各算一套口径。
 */
import { useMemo, useState } from "react";
import {
  usePortfolioMutations,
  usePortfolios,
  type Holding,
  type Portfolio,
  type PortfolioCurrency,
} from "@/api/portfolios";
import { fmtNum } from "@/lib/format";
import PortfolioSummaryCard from "./PortfolioSummaryCard";

const CURRENCIES: PortfolioCurrency[] = ["CNY", "USD", "HKD"];

interface HoldingForm {
  ticker: string;
  quantity: string;
  avg_cost: string;
  currency: "" | PortfolioCurrency;
  opened_on: string;
  note: string;
}

const EMPTY_FORM: HoldingForm = {
  ticker: "",
  quantity: "",
  avg_cost: "",
  currency: "",
  opened_on: "",
  note: "",
};

export default function PortfolioPage() {
  const { data, isLoading, isError, error } = usePortfolios();
  const m = usePortfolioMutations();

  const portfolios = data?.data.items ?? [];
  const [activeId, setActiveId] = useState<number | null>(null);
  const active = portfolios.find((p) => p.id === activeId) ?? portfolios[0];

  const [newName, setNewName] = useState("");
  const [newCurrency, setNewCurrency] = useState<PortfolioCurrency>("CNY");
  const [renamingId, setRenamingId] = useState<number | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [noteDraft, setNoteDraft] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const [form, setForm] = useState<HoldingForm>(EMPTY_FORM);
  const [editing, setEditing] = useState<{ id: number; form: HoldingForm } | null>(null);

  const busy =
    m.createPortfolio.isPending ||
    m.updatePortfolio.isPending ||
    m.addHolding.isPending ||
    m.updateHolding.isPending ||
    m.deleteHolding.isPending;

  async function run(action: () => Promise<unknown>, ok?: string) {
    setMessage(null);
    try {
      await action();
      if (ok) setMessage(ok);
    } catch (e) {
      setMessage((e as Error).message);
    }
  }

  const holdingCount = useMemo(
    () => portfolios.reduce((sum, p) => sum + p.holding_count, 0),
    [portfolios],
  );

  if (isLoading) return <p className="note">加载中…</p>;
  if (isError)
    return <p className="text-red text-sm">{(error as Error)?.message ?? "加载失败"}</p>;

  return (
    <div className="space-y-4">
      <div className="flex items-baseline gap-3 flex-wrap">
        <h1 className="text-xl font-bold">投资组合</h1>
        <span className="note">
          {portfolios.length} 个组合 · {holdingCount} 条持仓
        </span>
      </div>

      <div className="grid gap-4 lg:grid-cols-[260px_1fr]">
        <aside className="card">
          <h2 className="card-title">组合列表</h2>
          <div className="space-y-1">
            {portfolios.map((p) => (
              <div key={p.id}>
                {renamingId === p.id ? (
                  <div className="flex gap-1 py-1">
                    <input
                      className="input flex-1"
                      value={renameValue}
                      autoFocus
                      onChange={(e) => setRenameValue(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") void rename(p);
                        if (e.key === "Escape") setRenamingId(null);
                      }}
                    />
                    <button
                      type="button"
                      className="btn btn-ghost text-xs"
                      onClick={() => void rename(p)}
                    >
                      保存
                    </button>
                  </div>
                ) : (
                  <button
                    type="button"
                    className={`w-full text-left px-2 py-1.5 rounded text-sm border-0 cursor-pointer bg-transparent ${
                      active?.id === p.id ? "bg-panel2 text-text" : "text-muted hover:bg-panel2"
                    }`}
                    onClick={() => {
                      setActiveId(p.id);
                      setNoteDraft(null);
                      setEditing(null);
                    }}
                  >
                    <span className="flex justify-between gap-2">
                      <span className="truncate">{p.name}</span>
                      <span className="text-xs text-muted shrink-0">
                        {p.holding_count} · {p.base_currency}
                      </span>
                    </span>
                  </button>
                )}
              </div>
            ))}
          </div>

          <div className="mt-3 pt-3 border-t border-line space-y-2">
            <input
              className="input"
              placeholder="新组合名称"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") void create();
              }}
            />
            <div className="flex gap-2">
              <select
                className="input flex-1"
                value={newCurrency}
                onChange={(e) => setNewCurrency(e.target.value as PortfolioCurrency)}
              >
                {CURRENCIES.map((c) => (
                  <option key={c} value={c}>
                    基础货币 {c}
                  </option>
                ))}
              </select>
              <button
                type="button"
                className="btn btn-primary text-xs"
                disabled={busy || !newName.trim()}
                onClick={() => void create()}
              >
                新建
              </button>
            </div>
          </div>
        </aside>

        <section className="space-y-4">
          {!active ? (
            <div className="card">
              <p className="note">还没有组合，先在左侧新建一个。</p>
            </div>
          ) : (
            <>
              <div className="card">
                <div className="flex items-start justify-between gap-3 flex-wrap">
                  <div>
                    <h2 className="card-title mb-1">{active.name}</h2>
                    <p className="note">
                      基础货币 {active.base_currency} · {active.holding_count} 条持仓
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      className="btn btn-ghost text-xs"
                      onClick={() => {
                        setRenamingId(active.id);
                        setRenameValue(active.name);
                      }}
                    >
                      重命名
                    </button>
                    <select
                      className="input text-xs w-28"
                      aria-label="基础货币"
                      value={active.base_currency}
                      disabled={busy}
                      onChange={(e) =>
                        void run(
                          () =>
                            m.updatePortfolio.mutateAsync({
                              id: active.id,
                              base_currency: e.target.value as PortfolioCurrency,
                            }),
                          `基础货币已改为 ${e.target.value}`,
                        )
                      }
                    >
                      {CURRENCIES.map((c) => (
                        <option key={c} value={c}>
                          {c}
                        </option>
                      ))}
                    </select>
                    <button
                      type="button"
                      className="btn btn-ghost text-xs"
                      onClick={() => {
                        if (
                          !window.confirm(
                            `删除组合「${active.name}」及其 ${active.holding_count} 条持仓？删除后不可恢复。`,
                          )
                        )
                          return;
                        void run(
                          () => m.deletePortfolio.mutateAsync(active.id),
                          `已删除「${active.name}」`,
                        ).then(() => {
                          setActiveId(null);
                          setEditing(null);
                        });
                      }}
                    >
                      删除组合
                    </button>
                  </div>
                </div>

                <div className="mt-3">
                  <label className="note block mb-1">备注</label>
                  <div className="flex gap-2">
                    <input
                      className="input flex-1"
                      placeholder="例如：长期持有、行业分散"
                      value={noteDraft ?? active.note}
                      onChange={(e) => setNoteDraft(e.target.value)}
                    />
                    <button
                      type="button"
                      className="btn btn-ghost text-xs"
                      disabled={busy || noteDraft === null}
                      onClick={() =>
                        void run(
                          () =>
                            m.updatePortfolio.mutateAsync({
                              id: active.id,
                              note: noteDraft ?? undefined,
                            }),
                          "备注已保存",
                        ).then(() => setNoteDraft(null))
                      }
                    >
                      保存备注
                    </button>
                  </div>
                </div>
              </div>

              <PortfolioSummaryCard portfolioId={active.id} />

              <div className="card">
                <h2 className="card-title">持仓明细</h2>
                <HoldingsTable
                  holdings={active.holdings}
                  editing={editing}
                  setEditing={setEditing}
                  busy={busy}
                  onSave={(holding, form) =>
                    void run(
                      () =>
                        m.updateHolding.mutateAsync({
                          portfolioId: active.id,
                          holdingId: holding.id,
                          patch: toPatch(form),
                        }),
                      "持仓已更新",
                    ).then(() => setEditing(null))
                  }
                  onDelete={(holding) => {
                    if (
                      !window.confirm(
                        `删除持仓 ${holding.ticker}？删除后不可恢复。`,
                      )
                    )
                      return;
                    void run(
                      () =>
                        m.deleteHolding.mutateAsync({
                          portfolioId: active.id,
                          holdingId: holding.id,
                        }),
                      `已移除 ${holding.ticker}`,
                    );
                  }}
                />

                <div className="mt-4 pt-3 border-t border-line">
                  <h3 className="text-sm font-semibold mb-2">新增持仓</h3>
                  <HoldingFields
                    form={form}
                    onChange={setForm}
                    idPrefix="new"
                  />
                  <div className="flex items-center gap-3 mt-2 flex-wrap">
                    <button
                      type="button"
                      className="btn btn-primary text-xs"
                      disabled={busy || !form.ticker.trim() || form.quantity === "" || form.avg_cost === ""}
                      onClick={() =>
                        void run(async () => {
                          await m.addHolding.mutateAsync({
                            portfolioId: active.id,
                            holding: {
                              ticker: form.ticker,
                              quantity: Number(form.quantity),
                              avg_cost: Number(form.avg_cost),
                              currency: form.currency || null,
                              opened_on: form.opened_on || null,
                              note: form.note,
                            },
                          });
                          setForm(EMPTY_FORM);
                        }, "持仓已添加")
                      }
                    >
                      添加
                    </button>
                    <span className="note">
                      代码无效会返回 404，不会写入占位数据；币种留空则取行情计价货币。
                    </span>
                  </div>
                </div>
              </div>
            </>
          )}

          {message && <p className="note">{message}</p>}
        </section>
      </div>
    </div>
  );

  async function create() {
    const name = newName.trim();
    if (!name) return;
    await run(async () => {
      const created = await m.createPortfolio.mutateAsync({
        name,
        base_currency: newCurrency,
      });
      setActiveId(created.data.id);
      setNewName("");
    }, `已创建「${name}」`);
  }

  async function rename(portfolio: Portfolio) {
    const name = renameValue.trim();
    if (!name || name === portfolio.name) {
      setRenamingId(null);
      return;
    }
    await run(
      () => m.updatePortfolio.mutateAsync({ id: portfolio.id, name }),
      "组合已重命名",
    );
    setRenamingId(null);
  }
}

function toPatch(form: HoldingForm) {
  return {
    quantity: Number(form.quantity),
    avg_cost: Number(form.avg_cost),
    currency: form.currency || undefined,
    opened_on: form.opened_on || null,
    note: form.note,
  };
}

function HoldingsTable({
  holdings,
  editing,
  setEditing,
  busy,
  onSave,
  onDelete,
}: {
  holdings: Holding[];
  editing: { id: number; form: HoldingForm } | null;
  setEditing: (value: { id: number; form: HoldingForm } | null) => void;
  busy: boolean;
  onSave: (holding: Holding, form: HoldingForm) => void;
  onDelete: (holding: Holding) => void;
}) {
  if (holdings.length === 0) {
    return <p className="note">还没有持仓，用下面的表单添加第一条。</p>;
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-muted text-xs border-b border-line">
            <th className="text-left font-medium py-1.5">代码 / 名称</th>
            <th className="text-right font-medium py-1.5">数量</th>
            <th className="text-right font-medium py-1.5">平均成本</th>
            <th className="text-left font-medium py-1.5 pl-2">币种</th>
            <th className="text-left font-medium py-1.5 pl-2">建仓日期</th>
            <th className="text-left font-medium py-1.5 pl-2">备注</th>
            <th className="text-right font-medium py-1.5">操作</th>
          </tr>
        </thead>
        <tbody>
          {holdings.map((holding) =>
            editing?.id === holding.id ? (
              <tr key={holding.id} className="border-b border-line align-top">
                <td className="py-2" colSpan={7}>
                  <div className="text-sm font-semibold mb-2">
                    {holding.ticker} · {holding.name}
                  </div>
                  <HoldingFields
                    form={editing.form}
                    onChange={(form) => setEditing({ id: holding.id, form })}
                    idPrefix={`edit-${holding.id}`}
                  />
                  <div className="flex gap-2 mt-2">
                    <button
                      type="button"
                      className="btn btn-primary text-xs"
                      disabled={busy}
                      onClick={() => onSave(holding, editing.form)}
                    >
                      保存
                    </button>
                    <button
                      type="button"
                      className="btn btn-ghost text-xs"
                      onClick={() => setEditing(null)}
                    >
                      取消
                    </button>
                  </div>
                </td>
              </tr>
            ) : (
              <tr key={holding.id} className="border-b border-line">
                <td className="py-1.5">
                  <span className="font-semibold">{holding.ticker}</span>
                  <span className="note ml-2">{holding.name}</span>
                </td>
                <td className="text-right tabular-nums">{fmtNum(holding.quantity)}</td>
                <td className="text-right tabular-nums">{fmtNum(holding.avg_cost, 2)}</td>
                <td className="pl-2">{holding.currency ?? "—"}</td>
                <td className="pl-2">{holding.opened_on ?? "—"}</td>
                <td className="pl-2 text-muted">{holding.note || "—"}</td>
                <td className="text-right whitespace-nowrap">
                  <button
                    type="button"
                    className="btn btn-ghost text-xs"
                    onClick={() =>
                      setEditing({
                        id: holding.id,
                        form: {
                          ticker: holding.ticker,
                          quantity: String(holding.quantity),
                          avg_cost: String(holding.avg_cost),
                          currency: (holding.currency as PortfolioCurrency) || "",
                          opened_on: holding.opened_on ?? "",
                          note: holding.note,
                        },
                      })
                    }
                  >
                    编辑
                  </button>
                  <button
                    type="button"
                    className="btn btn-ghost text-xs"
                    onClick={() => onDelete(holding)}
                  >
                    删除
                  </button>
                </td>
              </tr>
            ),
          )}
        </tbody>
      </table>
    </div>
  );
}

function HoldingFields({
  form,
  onChange,
  idPrefix,
}: {
  form: HoldingForm;
  onChange: (form: HoldingForm) => void;
  idPrefix: string;
}) {
  const set = (patch: Partial<HoldingForm>) => onChange({ ...form, ...patch });
  return (
    <div className="flex gap-2 flex-wrap items-end text-xs">
      <label className="flex flex-col gap-1">
        <span className="text-muted">代码</span>
        <input
          id={`${idPrefix}-ticker`}
          className="input w-28"
          value={form.ticker}
          placeholder="AAPL"
          onChange={(e) => set({ ticker: e.target.value.toUpperCase() })}
        />
      </label>
      <label className="flex flex-col gap-1">
        <span className="text-muted">数量</span>
        <input
          id={`${idPrefix}-quantity`}
          className="input w-24"
          type="number"
          min={0}
          step="any"
          value={form.quantity}
          onChange={(e) => set({ quantity: e.target.value })}
        />
      </label>
      <label className="flex flex-col gap-1">
        <span className="text-muted">平均成本</span>
        <input
          id={`${idPrefix}-cost`}
          className="input w-28"
          type="number"
          min={0}
          step="any"
          value={form.avg_cost}
          onChange={(e) => set({ avg_cost: e.target.value })}
        />
      </label>
      <label className="flex flex-col gap-1">
        <span className="text-muted">成本币种</span>
        <select
          id={`${idPrefix}-currency`}
          className="input w-24"
          value={form.currency}
          onChange={(e) => set({ currency: e.target.value as "" | PortfolioCurrency })}
        >
          <option value="">跟随行情</option>
          {CURRENCIES.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </label>
      <label className="flex flex-col gap-1">
        <span className="text-muted">建仓日期</span>
        <input
          id={`${idPrefix}-date`}
          className="input w-36"
          type="date"
          value={form.opened_on}
          onChange={(e) => set({ opened_on: e.target.value })}
        />
      </label>
      <label className="flex flex-col gap-1 flex-1 min-w-40">
        <span className="text-muted">备注</span>
        <input
          id={`${idPrefix}-note`}
          className="input"
          value={form.note}
          onChange={(e) => set({ note: e.target.value })}
        />
      </label>
    </div>
  );
}
