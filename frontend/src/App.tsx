import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import LoginPage from "./features/auth/LoginPage";
import ComparePage from "./features/compare/ComparePage";
import ScreenerPage from "./features/screener/ScreenerPage";
import StockPage from "./features/stock/StockPage";
import PortfolioPage from "./features/portfolio/PortfolioPage";
import WatchlistPage from "./features/watchlist/WatchlistPage";
import Placeholder from "./features/Placeholder";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<Layout />}>
        <Route index element={<Placeholder title="StockVal 股票估值研究台" hint="在顶部搜索框输入股票代码开始研究。" />} />
        <Route path="/stock/:ticker" element={<StockPage />} />
        <Route path="/watchlists" element={<WatchlistPage />} />
        <Route path="/portfolios" element={<PortfolioPage />} />
        <Route path="/compare" element={<ComparePage />} />
        <Route path="/screener" element={<ScreenerPage />} />
        <Route path="/settings" element={<Placeholder title="设置" hint="M4 阶段交付" />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
