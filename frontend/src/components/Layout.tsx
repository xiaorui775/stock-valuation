import { Link, Outlet, useNavigate } from "react-router-dom";
import { useState } from "react";
import { useSearch } from "@/api/queries";
import { useDebounced } from "@/hooks/useDebounced";

export default function Layout() {
  const navigate = useNavigate();
  const [keyword, setKeyword] = useState("");
  const debounced = useDebounced(keyword, 300);
  const { data: results } = useSearch(debounced);
  const items = results?.data ?? [];

  return (
    <div className="min-h-full">
      <header className="bg-panel border-b border-line px-5 py-3 flex items-center gap-6 flex-wrap">
        <Link to="/" className="text-xl font-bold shrink-0">
          📊 StockVal{" "}
          <span className="text-[13px] font-normal text-muted ml-1.5">股票估值研究台</span>
        </Link>

        <form
          className="flex gap-2 flex-1 max-w-xl"
          onSubmit={(e) => {
            e.preventDefault();
            const first = items[0];
            if (first) navigate(`/stock/${encodeURIComponent(first.ticker)}`);
            else if (keyword.trim()) navigate(`/stock/${encodeURIComponent(keyword.trim().toUpperCase())}`);
          }}
        >
          <input
            className="input flex-1 uppercase"
            placeholder="输入股票代码，如 AAPL / 0700.HK / 600519.SS"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            autoComplete="off"
            spellCheck={false}
          />
          <button className="btn btn-primary" type="submit">
            查询
          </button>
        </form>

        <nav className="flex gap-1 text-sm">
          <Link className="px-3 py-1.5 rounded hover:bg-panel2" to="/watchlists">
            自选
          </Link>
          <Link className="px-3 py-1.5 rounded hover:bg-panel2" to="/portfolios">
            组合
          </Link>
          <Link className="px-3 py-1.5 rounded hover:bg-panel2" to="/compare">
            对比
          </Link>
          <Link className="px-3 py-1.5 rounded hover:bg-panel2" to="/screener">
            筛选
          </Link>
          <Link className="px-3 py-1.5 rounded hover:bg-panel2" to="/settings">
            设置
          </Link>
        </nav>
      </header>

      {debounced.trim() && items.length > 0 && (
        <div className="absolute z-20 mt-1 ml-[210px] bg-panel2 border border-line rounded-md overflow-hidden w-[420px]">
          {items.map((item) => (
            <button
              key={item.ticker}
              className="w-full text-left px-3 py-2 hover:bg-line flex justify-between items-center text-sm"
              onClick={() => {
                navigate(`/stock/${encodeURIComponent(item.ticker)}`);
                setKeyword("");
              }}
            >
              <span>
                <span className="font-semibold">{item.ticker}</span>{" "}
                <span className="text-muted">{item.name}</span>
              </span>
              <span className="text-xs text-muted">{item.market}</span>
            </button>
          ))}
        </div>
      )}

      <main className="max-w-[1080px] mx-auto px-4 py-5 pb-12">
        <Outlet />
      </main>

      <footer className="max-w-[1080px] mx-auto px-4 pb-10 text-xs text-muted leading-relaxed">
        数据来源：Yahoo Finance（yfinance）。估值模型：两阶段 DCF、估值倍数、Graham 公式、Gordon
        股利增长模型。本工具仅供学习研究，不构成投资建议。
      </footer>
    </div>
  );
}
