import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { useOverview, useFinancials, useCurrentUser } from "@/api/queries";
import { fmtBig, fmtInt, fmtNum } from "@/lib/format";
import PriceChart from "./PriceChart";
import DataBadge from "@/components/DataBadge";
import DataQualityCard from "./DataQualityCard";
import ValuationPanel from "./ValuationPanel";
import QuoteHeader from "./QuoteHeader";
import Week52Bar from "./Week52Bar";
import ConclusionCard from "./ConclusionCard";
import EarningsCalendarCard from "./EarningsCalendarCard";
import QuickActions from "./QuickActions";
import FinancialsTable from "./FinancialsTable";
import FinancialTrends from "./FinancialTrends";
import InsightsCard from "./InsightsCard";
import NewsPanel from "./NewsPanel";
import ResearchNotes from "./ResearchNotes";

type Tab = "overview" | "financials" | "valuation" | "notes";

const TABS: { key: Tab; label: string }[] = [
  { key: "overview", label: "概览" },
  { key: "financials", label: "财务报表" },
  { key: "valuation", label: "估值" },
  { key: "notes", label: "研究笔记" },
];

export default function StockPage() {
  const { ticker = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const tabParam = params.get("tab") as Tab | null;
  const [tab, setTab] = useState<Tab>(
    tabParam && TABS.some((t) => t.key === tabParam) ? tabParam : "overview",
  );

  // 同一路由下仅改变 ?tab= 时组件不会重挂载（概览卡「查看完整估值」就是这种跳转），
  // 因此需要跟随查询参数同步当前标签页。
  useEffect(() => {
    const next = tabParam && TABS.some((t) => t.key === tabParam) ? tabParam : "overview";
    setTab(next);
  }, [tabParam, ticker]);
  const overview = useOverview(ticker);
  const financials = useFinancials(ticker, "annual");
  const me = useCurrentUser();

  function switchTab(next: Tab) {
    setTab(next);
    const nextParams = new URLSearchParams(params);
    if (next === "overview") nextParams.delete("tab");
    else nextParams.set("tab", next);
    setParams(nextParams, { replace: true });
  }

  if (overview.isLoading) {
    return <div className="note">正在加载 {ticker.toUpperCase()} …</div>;
  }

  if (overview.isError) {
    // 名称不是代码：常见于旧版搜索把「英伟达」当成 ticker 保存到最近搜索
    const nonAscii = /[^\x00-\x7F]/.test(ticker);
    return (
      <div className="card">
        <p className="text-red">{(overview.error as Error)?.message ?? "加载失败"}</p>
        {nonAscii ? (
          <p className="note mt-2">
            「{ticker}」是名称而不是代码。请用顶部搜索框重新搜索并选择结果，例如「英伟达」对应
            NVDA。
          </p>
        ) : (
          <p className="note mt-2">
            请确认股票代码是否正确，例如 AAPL、0700.HK、600519.SS。
          </p>
        )}
      </div>
    );
  }

  const data = overview.data?.data;
  const meta = overview.data?.meta;
  if (!data) return null;

  const q = data.quote;

  const stats: [string, string][] = [
    ["市值", fmtBig(q?.market_cap ?? null)],
    ["市盈率 P/E (TTM)", fmtNum(q?.pe_ttm ?? null)],
    ["预期市盈率 Forward P/E", fmtNum(q?.forward_pe ?? null)],
    ["每股收益 EPS (TTM)", fmtNum(q?.eps_ttm ?? null)],
    ["股息率", q?.dividend_yield == null ? "—" : `${fmtNum(q.dividend_yield)}%`],
    ["Beta", fmtNum(q?.beta ?? null, 3)],
    ["52 周最高", fmtNum(q?.week52_high ?? null)],
    ["52 周最低", fmtNum(q?.week52_low ?? null)],
    ["成交量", fmtInt(q?.volume ?? null)],
    ["昨收", fmtNum(q?.previous_close ?? null)],
    [
      "日内区间",
      `${q?.day_low == null ? "—" : fmtNum(q.day_low)} – ${
        q?.day_high == null ? "—" : fmtNum(q.day_high)
      }`,
    ],
    ["总股本", fmtBig(q?.shares_outstanding ?? null)],
    ["市净率 P/B", fmtNum(q?.price_to_book ?? null)],
    ["市销率 P/S", fmtNum(q?.price_to_sales ?? null)],
    ["EV/EBITDA", fmtNum(q?.ev_ebitda ?? null)],
    ["PEG", fmtNum(q?.peg ?? null)],
  ];

  return (
    <div>
      <div className="flex justify-between items-start gap-4 flex-wrap mb-4">
        <QuoteHeader overview={data} />
        {meta && <DataBadge meta={meta} />}
      </div>

      <div className="mb-4">
        <QuickActions
          ticker={ticker}
          ready={!overview.isLoading}
          signedIn={Boolean(me.data?.data)}
          price={q?.price ?? null}
        />
      </div>

      <nav className="flex gap-1 mb-4 border-b border-line">
        {TABS.map((t) => (
          <button
            key={t.key}
            className={`px-4 py-2.5 bg-none border-0 border-b-2 cursor-pointer text-[15px] ${
              tab === t.key
                ? "border-accent text-text font-bold"
                : "border-transparent text-muted"
            }`}
            onClick={() => switchTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {tab === "overview" && (
        <>
          <div className="card">
            <h2 className="card-title">股价走势</h2>
            <PriceChart ticker={ticker} />
          </div>

          <div className="card">
            <h2 className="card-title">52 周位置</h2>
            <Week52Bar
              price={q?.price ?? null}
              high={q?.week52_high ?? null}
              low={q?.week52_low ?? null}
              position={data.week52?.position ?? null}
            />
          </div>

          <div className="card">
            <h2 className="card-title">财报日历</h2>
            <EarningsCalendarCard ticker={ticker} />
          </div>

          <ConclusionCard conclusion={data.conclusion} ticker={ticker} />

          <div className="card">
            <h2 className="card-title">关键指标</h2>
            <div className="grid grid-cols-[repeat(auto-fill,minmax(220px,1fr))]">
              {stats.map(([k, v]) => (
                <div className="stat" key={k}>
                  <span className="stat-k">{k}</span>
                  <span className="stat-v">{v}</span>
                </div>
              ))}
            </div>
            <p className="note mt-3">数据源未提供的字段以「—」显示，不做估算填充。</p>
          </div>

          <div className="card">
            <h2 className="card-title">数据质量</h2>
            <DataQualityCard ticker={ticker} />
          </div>

          <NewsPanel ticker={ticker} />
        </>
      )}

      {tab === "financials" && (
        <>
          <InsightsCard ticker={ticker} />
          {financials.isLoading ? (
            <div className="card">
              <p className="note">正在加载财务数据 …</p>
            </div>
          ) : financials.isError ? (
            <div className="card">
              <p className="text-red text-sm">{(financials.error as Error)?.message}</p>
            </div>
          ) : financials.data ? (
            <>
              <div className="card">
                <h2 className="card-title">财务趋势</h2>
                <FinancialTrends
                  data={financials.data.data}
                  source={financials.data.meta.source}
                />
              </div>
              <div className="card">
                <h2 className="card-title">年度财务报表</h2>
                <FinancialsTable
                  data={financials.data.data}
                  source={financials.data.meta.source}
                />
              </div>
            </>
          ) : null}
        </>
      )}

      {tab === "valuation" && <ValuationPanel ticker={ticker} />}

      {tab === "notes" && <ResearchNotes ticker={ticker} />}
    </div>
  );
}
