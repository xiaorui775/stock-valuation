/** 组合汇总卡片：市值、盈亏、权重、分布与汇率（FR-PORT-03 / 04 / 07）。
 *
 * 数字全部来自后端汇总：缺汇率时后端按币种分组，这里照实展示，不做前端换算。
 */
import { usePortfolioSummary } from "@/api/portfolios";
import { changeClass, fmtBig, fmtNum, fmtPct, marketLabel, valuationClass } from "@/lib/format";

export default function PortfolioSummaryCard({
  portfolioId,
}: {
  portfolioId: number;
}) {
  const { data, isLoading, isError, error } = usePortfolioSummary(portfolioId);
  const summary = data?.data;

  return (
    <div className="card">
      <div className="flex items-baseline justify-between gap-3 flex-wrap">
        <h2 className="card-title mb-0">组合汇总</h2>
        {summary && (
          <span className="note">
            基础货币 {summary.base_currency}
            {summary.as_of && ` · 数据时间 ${fmtTime(summary.as_of)}`}
          </span>
        )}
      </div>

      {isLoading && <p className="note mt-3">计算中…</p>}
      {isError && (
        <p className="text-red text-sm mt-3">
          {(error as Error)?.message ?? "汇总加载失败"}
        </p>
      )}

      {summary && (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-3 text-sm">
            <Metric label="总市值" value={fmtBig(summary.total_market_value)} strong />
            <Metric label="总成本" value={fmtBig(summary.total_cost)} />
            <Metric
              label="未实现盈亏"
              value={`${fmtBig(summary.unrealized_pnl)}（${fmtPct(summary.unrealized_pnl_pct, 2, true)}）`}
              tone={changeClass(summary.unrealized_pnl)}
            />
            <Metric
              label="当日盈亏"
              value={`${fmtBig(summary.day_pnl)}（${fmtPct(summary.day_pnl_pct, 2, true)}）`}
              tone={changeClass(summary.day_pnl)}
            />
          </div>

          <div className="grid grid-cols-2 gap-4 mt-3 text-sm">
            <div>
              组合加权 DCF 上行
              <b className={`block text-lg ${valuationClass(summary.weighted_upside_pct)}`}>
                {fmtPct(summary.weighted_upside_pct, 1, true)}
              </b>
              <span className="note">
                覆盖率 {fmtPct(summary.upside_coverage_pct, 1)}（按市值加权，未覆盖部分不计入）
              </span>
            </div>
            <div>
              持仓数
              <b className="block text-lg">{summary.rows.length}</b>
              <span className="note">汇率缺失的持仓不计入基础货币汇总</span>
            </div>
          </div>

          {summary.rows.length > 0 && (
            <div className="overflow-x-auto mt-4">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-muted text-xs border-b border-line">
                    <th className="text-left font-medium py-1.5">代码 / 名称</th>
                    <th className="text-right font-medium py-1.5">数量</th>
                    <th className="text-right font-medium py-1.5">现价</th>
                    <th className="text-right font-medium py-1.5">市值</th>
                    <th className="text-right font-medium py-1.5">未实现盈亏</th>
                    <th className="text-right font-medium py-1.5">权重</th>
                    <th className="text-right font-medium py-1.5">DCF 上行</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.rows.map((row) => (
                    <tr key={row.ticker} className="border-b border-line">
                      <td className="py-1.5">
                        <span className="font-semibold">{row.ticker}</span>
                        <span className="note ml-2">{row.name}</span>
                        {row.error && <span className="text-red text-xs ml-2">{row.error}</span>}
                      </td>
                      <td className="text-right tabular-nums">{fmtNum(row.quantity)}</td>
                      <td className="text-right tabular-nums">
                        {fmtNum(row.price)}
                        {row.currency && (
                          <span className="text-muted text-xs ml-1">{row.currency}</span>
                        )}
                      </td>
                      <td className="text-right tabular-nums">
                        {row.market_value == null
                          ? `${fmtBig(row.market_value_local)} ${row.currency ?? ""}（未换算）`
                          : fmtBig(row.market_value)}
                      </td>
                      <td
                        className={`text-right tabular-nums ${changeClass(row.unrealized_pnl)}`}
                      >
                        {fmtBig(row.unrealized_pnl)}
                        <span className="text-xs ml-1 block">
                          {fmtPct(row.unrealized_pnl_pct, 2, true)}
                        </span>
                      </td>
                      <td className="text-right tabular-nums">{fmtPct(row.weight_pct, 1)}</td>
                      <td
                        className={`text-right tabular-nums ${valuationClass(row.dcf_upside_pct)}`}
                      >
                        {fmtPct(row.dcf_upside_pct, 1, true)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {summary.distribution.length > 0 && (
            <div className="mt-4">
              <h3 className="text-sm font-semibold mb-1">市场分布（按市值）</h3>
              <div className="space-y-1.5">
                {summary.distribution.map((item) => (
                  <div key={item.market} className="flex items-center gap-2 text-xs">
                    <span className="w-12 text-muted">{marketLabel(item.market)}</span>
                    <span className="flex-1 h-2 rounded bg-panel2 overflow-hidden">
                      <span
                        className="block h-full bg-accent"
                        style={{ width: `${Math.max(0, Math.min(100, item.weight_pct ?? 0))}%` }}
                      />
                    </span>
                    <span className="w-16 text-right tabular-nums">
                      {fmtPct(item.weight_pct, 1)}
                    </span>
                    <span className="w-24 text-right tabular-nums text-muted">
                      {fmtBig(item.market_value)}
                    </span>
                  </div>
                ))}
              </div>
              <p className="note mt-1">行业分布暂不可用：数据源未提供行业字段。</p>
            </div>
          )}

          <div className="mt-4">
            <h3 className="text-sm font-semibold mb-1">汇率</h3>
            <div className="flex gap-2 flex-wrap text-xs">
              {summary.fx_rates.map((rate) => (
                <span
                  key={rate.currency}
                  className="px-2 py-1 rounded bg-panel2 border border-line"
                >
                  {rate.currency}/{summary.base_currency}{" "}
                  <b className="tabular-nums">{rate.rate == null ? "不可用" : fmtNum(rate.rate, 4)}</b>
                  {rate.source && (
                    <span className="note ml-1">（{sourceLabel(rate.source)}）</span>
                  )}
                </span>
              ))}
            </div>
          </div>

          {summary.unconverted.length > 0 && (
            <div className="mt-3">
              <h3 className="text-sm font-semibold mb-1">未换算持仓（缺汇率）</h3>
              {summary.unconverted.map((group) => (
                <p key={group.currency} className="note">
                  {group.currency}：{group.count} 条，本币市值{" "}
                  {fmtBig(group.market_value_local)}
                  {group.priced_count < group.count &&
                    `（${group.count - group.priced_count} 条缺少行情）`}
                </p>
              ))}
            </div>
          )}

          {summary.warnings.length > 0 && (
            <ul className="mt-3 space-y-1">
              {summary.warnings.map((warning) => (
                <li key={warning} className="note">
                  · {warning}
                </li>
              ))}
            </ul>
          )}

          <p className="note mt-3">
            未实现盈亏 =（现价 − 平均成本）× 数量，多币种先按上表汇率换算再汇总；
            集中度提示为事实描述，不构成建议。
          </p>
        </>
      )}
    </div>
  );
}

function Metric({
  label,
  value,
  tone,
  strong,
}: {
  label: string;
  value: string;
  tone?: string;
  strong?: boolean;
}) {
  return (
    <div>
      <span className="text-muted text-xs">{label}</span>
      <b className={`block ${strong ? "text-2xl font-extrabold" : "text-lg"} ${tone ?? ""}`}>
        {value}
      </b>
    </div>
  );
}

/** 汇率来源的中文标注；未知来源照实显示，不猜测。 */
function sourceLabel(source: string): string {
  switch (source) {
    case "identity":
      return "基准货币";
    case "demo":
      return "演示数据";
    default:
      return source;
  }
}

function fmtTime(value: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", { hour12: false });
}
