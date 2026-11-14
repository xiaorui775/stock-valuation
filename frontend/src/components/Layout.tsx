import { Link, Outlet } from "react-router-dom";
import SearchBox from "./SearchBox";

export default function Layout() {
  return (
    <div className="min-h-full">
      <header className="bg-panel border-b border-line px-5 py-3 flex items-center gap-6 flex-wrap relative z-30">
        <Link to="/" className="text-xl font-bold shrink-0">
          📊 StockVal{" "}
          <span className="text-[13px] font-normal text-muted ml-1.5">股票估值研究台</span>
        </Link>

        <SearchBox />

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

      <main className="max-w-[1080px] mx-auto px-4 py-5 pb-12">
        <Outlet />
      </main>

      <footer className="max-w-[1080px] mx-auto px-4 pb-10 text-xs text-muted leading-relaxed text-center">
        数据来源：akshare（新浪 / 东方财富等公开接口），Yahoo Finance 作为备用。估值模型：两阶段
        DCF、估值倍数、Graham 公式、Gordon 股利增长模型。本工具仅供学习研究，不构成投资建议。
      </footer>
    </div>
  );
}
