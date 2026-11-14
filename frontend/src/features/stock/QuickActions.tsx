/** 概览页快捷操作（FR-OVERVIEW-05 / FR-WATCH-06）。
 *
 * 「加入自选」「加入组合」已接线；导出入口按里程碑禁用并说明。
 */
import { useState } from "react";
import {
  usePortfolioMutations,
  usePortfolios,
} from "@/api/portfolios";
import { useWatchlistMutations, useWatchlists } from "@/api/watchlists";
import { fmtNum } from "@/lib/format";

interface Props {
  ticker: string;
  ready: boolean;
  signedIn: boolean;
  /** 现价，仅用于提示；不会自动当作持仓成本。 */
  price?: number | null;
}

export default function QuickActions({ ticker, ready, signedIn, price }: Props) {
  const blocked = !ready || !signedIn;
  const { data } = useWatchlists();
  const { addItem } = useWatchlistMutations();
  const portfolios = usePortfolios();
  const { addHolding } = usePortfolioMutations();

  const [open, setOpen] = useState(false);
  const [portfolioOpen, setPortfolioOpen] = useState(false);
  const [targetId, setTargetId] = useState<number | "">("");
  const [quantity, setQuantity] = useState("");
  const [avgCost, setAvgCost] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  const groups = data?.data.groups ?? [];
  const portfolioList = portfolios.data?.data.items ?? [];

  async function addTo(groupId: number, name: string) {
    setOpen(false);
    try {
      await addItem.mutateAsync({ groupId, ticker });
      setMessage(`已加入「${name}」`);
    } catch (e) {
      setMessage((e as Error).message);
    }
  }

  async function addToPortfolio() {
    if (targetId === "") return;
    const target = portfolioList.find((p) => p.id === targetId);
    try {
      await addHolding.mutateAsync({
        portfolioId: targetId,
        holding: {
          ticker,
          quantity: Number(quantity),
          avg_cost: Number(avgCost),
        },
      });
      setMessage(`已加入组合「${target?.name ?? targetId}」`);
      setPortfolioOpen(false);
      setTargetId("");
      setQuantity("");
      setAvgCost("");
    } catch (e) {
      setMessage((e as Error).message);
    }
  }

  const disabledReason = blocked
    ? signedIn
      ? "数据加载完成后可用"
      : "请先登录"
    : null;

  return (
    <div className="flex gap-2 flex-wrap items-center">
      <div className="relative">
        <button
          type="button"
          className="btn btn-ghost text-xs"
          disabled={blocked}
          title={disabledReason ?? "选择分组加入自选"}
          aria-haspopup="menu"
          aria-expanded={open}
          onClick={() => setOpen((current) => !current)}
        >
          加入自选
        </button>
        {open && !blocked && (
          <div
            className="absolute left-0 z-30 mt-1 min-w-48 bg-panel2 border border-line rounded-md p-1 shadow-lg"
            role="menu"
          >
            {groups.length === 0 ? (
              <p className="note px-2 py-1.5">暂无分组，请先去自选股页新建。</p>
            ) : (
              groups.map((group) => (
                <button
                  key={group.id}
                  type="button"
                  role="menuitem"
                  className="block w-full text-left px-2 py-1.5 text-sm rounded hover:bg-panel cursor-pointer bg-transparent border-0 text-text"
                  onClick={() => void addTo(group.id, group.name)}
                >
                  {group.name}
                  <span className="note ml-2">{group.items.length}</span>
                </button>
              ))
            )}
          </div>
        )}
      </div>

      <div className="relative">
        <button
          type="button"
          className="btn btn-ghost text-xs"
          disabled={blocked}
          title={disabledReason ?? "录入持仓到组合"}
          aria-haspopup="dialog"
          aria-expanded={portfolioOpen}
          onClick={() => setPortfolioOpen((current) => !current)}
        >
          加入组合
        </button>
        {portfolioOpen && !blocked && (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
            role="dialog"
            aria-modal="true"
            aria-label="加入组合"
            onClick={() => setPortfolioOpen(false)}
          >
            <div
              className="w-full max-w-sm bg-panel2 border border-line rounded-lg p-4 shadow-xl"
              onClick={(e) => e.stopPropagation()}
            >
              {portfolioList.length === 0 ? (
                <p className="note px-1 py-1">暂无组合，请先去「组合」页新建。</p>
              ) : (
                <>
                  <h3 className="text-base font-semibold mb-3">加入组合</h3>
                  <select
                    className="input w-full mb-2"
                    value={targetId}
                    aria-label="选择组合"
                    onChange={(e) =>
                      setTargetId(e.target.value === "" ? "" : Number(e.target.value))
                    }
                  >
                    <option value="">选择组合…</option>
                    {portfolioList.map((portfolio) => (
                      <option key={portfolio.id} value={portfolio.id}>
                        {portfolio.name}（{portfolio.base_currency}）
                      </option>
                    ))}
                  </select>
                  <div className="flex gap-2 mb-2">
                    <input
                      className="input flex-1"
                      type="number"
                      min={0}
                      step="any"
                      placeholder="数量"
                      aria-label="数量"
                      value={quantity}
                      onChange={(e) => setQuantity(e.target.value)}
                    />
                    <input
                      className="input flex-1"
                      type="number"
                      min={0}
                      step="any"
                      placeholder="平均成本"
                      aria-label="平均成本"
                      value={avgCost}
                      onChange={(e) => setAvgCost(e.target.value)}
                    />
                  </div>
                  <p className="note mb-3">
                    {price == null
                      ? "成本请按实际成交价填写。"
                      : `现价 ${fmtNum(price)}；成本请按实际成交价填写，不会自动带入现价。`}
                  </p>
                  <div className="flex gap-2 justify-end">
                    <button
                      type="button"
                      className="btn btn-ghost text-xs"
                      onClick={() => setPortfolioOpen(false)}
                    >
                      取消
                    </button>
                    <button
                      type="button"
                      className="btn btn-primary text-xs"
                      disabled={
                        addHolding.isPending ||
                        targetId === "" ||
                        quantity === "" ||
                        avgCost === ""
                      }
                      onClick={() => void addToPortfolio()}
                    >
                      {addHolding.isPending ? "添加中…" : "确认加入"}
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        )}
      </div>

      <button
        type="button"
        className="btn btn-ghost text-xs"
        disabled
        title="报告导出将在 M4-01 提供"
      >
        导出报告
      </button>

      {message && <span className="note">{message}</span>}
    </div>
  );
}
