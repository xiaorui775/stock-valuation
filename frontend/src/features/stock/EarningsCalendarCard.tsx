/** 财报日历（PRD §5.17 FR-RESEARCH-04）。
 *
 * 只展示下一次财报日与分红/除息日，不做提醒或推送；数据源没有日历时如实说明。
 */
import { useCalendar } from "@/api/queries";
import DataBadge from "@/components/DataBadge";

function relativeDays(days: number | null): string | null {
  if (days === null) return null;
  if (days === 0) return "今天";
  if (days === 1) return "明天";
  return `${days} 天后`;
}

export default function EarningsCalendarCard({ ticker }: { ticker: string }) {
  const { data, isLoading, isError, error } = useCalendar(ticker);

  if (isLoading) return <p className="note">正在加载财报日历 …</p>;
  if (isError) {
    return (
      <p className="text-red text-sm">
        {(error as Error)?.message ?? "财报日历加载失败"}
      </p>
    );
  }

  const info = data?.data;
  if (!info) return null;

  const meta = data.meta;
  const relative = relativeDays(info.days_until_earnings);

  return (
    <div>
      <div className="flex justify-between items-start gap-4 flex-wrap">
        <div>
          <span className="stat-k">下一次财报</span>
          {info.earnings_date ? (
            <>
              <div className="text-2xl font-bold mt-1">{info.earnings_date}</div>
              {relative && <div className="text-accent text-sm mt-1">{relative}</div>}
            </>
          ) : (
            <p className="note mt-1">{info.note ?? "数据源未提供下一次财报日"}</p>
          )}
          {info.earnings_date && info.note && (
            <p className="note mt-1">{info.note}</p>
          )}
        </div>
        {meta && <DataBadge meta={meta} />}
      </div>

      {(info.dividend_date || info.ex_dividend_date) && (
        <div className="grid grid-cols-[repeat(auto-fill,minmax(180px,1fr))] mt-3">
          {info.dividend_date && (
            <div className="stat">
              <span className="stat-k">分红日</span>
              <span className="stat-v">{info.dividend_date}</span>
            </div>
          )}
          {info.ex_dividend_date && (
            <div className="stat">
              <span className="stat-k">除息日</span>
              <span className="stat-v">{info.ex_dividend_date}</span>
            </div>
          )}
        </div>
      )}

      <p className="note mt-3">
        仅信息展示，不做提醒或推送；财报日期可能由公司调整，请以官方公告为准。
      </p>
    </div>
  );
}
