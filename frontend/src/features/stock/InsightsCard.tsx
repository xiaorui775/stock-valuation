/** 规则化财务解读：事实列表、未覆盖项、无投资建议措辞（§5.6 / M2-02）。 */
import { useInsights } from "@/api/queries";

const LEVELS: Record<string, { label: string; text: string; border: string }> = {
  alert: { label: "alert", text: "text-red", border: "border-red" },
  watch: { label: "watch", text: "text-accent", border: "border-accent" },
  info: { label: "info", text: "text-muted", border: "border-line" },
};

export default function InsightsCard({ ticker }: { ticker: string }) {
  const { data, isLoading, isError, error } = useInsights(ticker);
  const insights = data?.data;

  return (
    <div className="card">
      <div className="flex justify-between items-start gap-3 flex-wrap">
        <h2 className="card-title mb-0">财务解读</h2>
        {insights && <span className="note">{insights.summary}</span>}
      </div>

      {isLoading ? (
        <p className="note mt-3">正在生成解读 …</p>
      ) : isError ? (
        <p className="text-red text-sm mt-3">{(error as Error)?.message ?? "解读加载失败"}</p>
      ) : !insights ? null : (
        <>
          {insights.items.length === 0 ? (
            <p className="note mt-3">未发现显著异常。</p>
          ) : (
            <ul className="mt-3 space-y-3">
              {insights.items.map((item) => {
                const level = LEVELS[item.level] ?? LEVELS.info;
                return (
                  <li
                    key={item.rule}
                    className={`border-l-2 pl-3 py-0.5 ${level.border}`}
                  >
                    <div className="flex gap-2 items-baseline flex-wrap">
                      <span className={`badge bg-panel2 ${level.text}`}>
                        {level.label}
                      </span>
                      <span className="font-semibold text-sm">{item.name}</span>
                      <span className="text-sm">{item.title}</span>
                    </div>
                    <div className="note mt-1">
                      {item.detail}
                      {item.period ? ` · ${item.period}` : ""}
                    </div>
                    <div className="note">公式：{item.formula}</div>
                  </li>
                );
              })}
            </ul>
          )}

          {insights.uncovered.length > 0 && (
            <div className="mt-4">
              <div className="note font-semibold mb-1">
                未覆盖项（数据不足，规则已跳过）
              </div>
              <ul className="note space-y-0.5">
                {insights.uncovered.map((item) => (
                  <li key={item.rule}>
                    · {item.name}：{item.reason}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <p className="note mt-3">
            以上为基于财务报表的事实陈述，不含买卖建议；口径以最近财年
            {insights.fiscal_year != null ? `（${insights.fiscal_year}）` : ""}为准。
          </p>
        </>
      )}
    </div>
  );
}
