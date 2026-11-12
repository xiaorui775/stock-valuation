import { useState } from "react";
import { useParams } from "react-router-dom";
import { useQuote, useHistory, useFinancials } from "@/api/queries";
import { changeClass, fmtBig, fmtInt, fmtNum } from "@/lib/format";
import PriceChart from "./PriceChart";
import DataBadge from "@/components/DataBadge";
import ValuationPanel from "./ValuationPanel";
import type { FinancialYear } from "@/api/types";

type Tab = "overview" | "financials" | "valuation";

const TABS: { key: Tab; label: string }[] = [
  { key: "overview", label: "概览" },
  { key: "financials", label: "财务报表" },
  { key: "valuation", label: "估值" },
];

export default function StockPage() {
  const { ticker = "" } = useParams();
  const [tab, setTab] = useState<Tab>("overview");
  const quote = useQuote(ticker);
  const history = useHistory(ticker, "1y", "1d");
  const financials = useFinancials(ticker, "annual");

  if (quote.isLoading) return <div className="note">正在加载 {ticker.toUpperCase()} …</div>;

  if (quote.isError) {
    return (
      <div className="card">
        <p className="text-red">{(quote.error as Error)?.message ?? "加载失败"}</p>
        <p className="note mt-2">请确认股票代码是否正确，例如 AAPL、0700.HK、600519.SS。</p>
      </div>
    );
  }

  const q = quote.data?.data;
  const meta = quote.data?.meta;
  if (!q) return null;

  const stats: [string, string][] = [
    ["市值", fmtBig(q.market_cap)],
    ["市盈率 P/E (TTM)", fmtNum(q.pe_ttm)],
    ["预期市盈率 Forward P/E", fmtNum(q.forward_pe)],
    ["每股收益 EPS (TTM)", fmtNum(q.eps_ttm)],
    ["股息率", q.dividend_yield == null ? "—" : `${fmtNum(q.dividend_yield)}%`],
    ["Beta", fmtNum(q.beta, 3)],
    ["52 周最高", fmtNum(q.week52_high)],
    ["52 周最低", fmtNum(q.week52_low)],
    ["成交量", fmtInt(q.volume)],
    ["昨收", fmtNum(q.previous_close)],
    [
      "日内区间",
      `${q.day_low == null ? "—" : fmtNum(q.day_low)} – ${q.day_high == null ? "—" : fmtNum(q.day_high)}`,
    ],
    ["总股本", fmtBig(q.shares_outstanding)],
  ];

  return (
    <div>
      <div className="flex justify-between items-start gap-4 flex-wrap mb-4">
        <div>
          <h1 className="text-2xl font-bold mb-1.5">
            {q.name} <span className="text-muted text-base font-normal">{q.ticker}</span>
          </h1>
          <div className="flex items-baseline gap-3">
            <span className="text-4xl font-extrabold">{fmtNum(q.price)}</span>
            <span className={`text-lg font-bold ${changeClass(q.change)}`}>
              {q.change == null
                ? "—"
                : `${q.change > 0 ? "+" : ""}${fmtNum(q.change)} (${
                    q.change_pct == null ? "—" : `${q.change_pct > 0 ? "+" : ""}${fmtNum(q.change_pct)}%`
                  })`}
            </span>
            <span className="text-muted text-sm">{q.currency ?? ""}</span>
          </div>
        </div>
        {meta && <DataBadge meta={meta} />}
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
            onClick={() => setTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {tab === "overview" && (
        <>
          <div className="card">
            <h2 className="card-title">近一年股价走势</h2>
            <PriceChart bars={history.data?.data.bars ?? []} loading={history.isLoading} />
          </div>
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
          </div>
        </>
      )}

      {tab === "financials" && (
        <div className="card">
          <h2 className="card-title">年度财务数据（最近 4 个财年，单位：亿元）</h2>
          {financials.isLoading ? (
            <p className="note">正在加载财务数据 …</p>
          ) : financials.isError ? (
            <p className="text-red text-sm">{(financials.error as Error)?.message}</p>
          ) : (
            <FinancialTable years={financials.data?.data.years ?? []} />
          )}
          <p className="note mt-3">个别公司报表科目缺失时以「—」表示，不做估算填充。</p>
        </div>
      )}

      {tab === "valuation" && <ValuationPanel ticker={ticker} />}
    </div>
  );
}

function FinancialTable({ years }: { years: FinancialYear[] }) {
  const rows: [string, keyof FinancialYear][] = [
    ["营业收入", "revenue"],
    ["毛利润", "gross_profit"],
    ["营业利润", "operating_income"],
    ["净利润", "net_income"],
    ["自由现金流 FCF", "free_cash_flow"],
  ];
  if (years.length === 0) return <p className="note">暂无财务数据。</p>;

  return (
    <table className="data-table">
      <thead>
        <tr>
          <th>科目（亿元）</th>
          {years.map((y) => (
            <th key={y.year}>{y.year}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map(([label, key]) => (
          <tr key={key}>
            <td>{label}</td>
            {years.map((y) => (
              <td key={y.year}>{fmtBig(y[key] as number | null)}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
