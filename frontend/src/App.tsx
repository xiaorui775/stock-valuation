import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import LoginPage from "./features/auth/LoginPage";
import StockPage from "./features/stock/StockPage";
import Placeholder from "./features/Placeholder";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<Layout />}>
        <Route index element={<Placeholder title="StockVal 股票估值研究台" hint="在顶部搜索框输入股票代码开始研究。" />} />
        <Route path="/stock/:ticker" element={<StockPage />} />
        <Route path="/watchlists" element={<Placeholder title="自选股" hint="M1 阶段交付" />} />
        <Route path="/portfolios" element={<Placeholder title="投资组合" hint="M2 阶段交付" />} />
        <Route path="/compare" element={<Placeholder title="多股对比" hint="M2 阶段交付" />} />
        <Route path="/screener" element={<Placeholder title="筛选器" hint="M2 阶段交付" />} />
        <Route path="/settings" element={<Placeholder title="设置" hint="M4 阶段交付" />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
