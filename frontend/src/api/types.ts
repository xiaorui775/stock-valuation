/** 与后端 Pydantic 模型对应的类型定义。 */

export type Market = "US" | "HK" | "CN" | "UNKNOWN";

export interface User {
  id: number;
  email: string;
  display_name: string;
  base_currency: string;
  role: string;
  created_at: string;
}

export interface Instrument {
  ticker: string;
  name: string;
  market: Market;
  exchange: string | null;
  currency: string | null;
  provider: string | null;
}

export interface Quote {
  ticker: string;
  name: string;
  currency: string | null;
  market: Market;
  price: number | null;
  previous_close: number | null;
  change: number | null;
  change_pct: number | null;
  day_high: number | null;
  day_low: number | null;
  open_price: number | null;
  market_cap: number | null;
  pe_ttm: number | null;
  forward_pe: number | null;
  eps_ttm: number | null;
  dividend_yield: number | null;
  beta: number | null;
  week52_high: number | null;
  week52_low: number | null;
  volume: number | null;
  shares_outstanding: number | null;
  price_to_book: number | null;
  price_to_sales: number | null;
  ev_ebitda: number | null;
  peg: number | null;
  total_debt: number | null;
  total_cash: number | null;
  total_revenue: number | null;
  ebitda: number | null;
  book_value_per_share: number | null;
  as_of: string | null;
}

export interface Bar {
  date: string;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number;
  volume: number | null;
}

export interface History {
  ticker: string;
  period: string;
  interval: string;
  bars: Bar[];
}

export interface FinancialYear {
  year: number;
  period_end: string | null;
  revenue: number | null;
  gross_profit: number | null;
  operating_income: number | null;
  net_income: number | null;
  eps: number | null;
  operating_cash_flow: number | null;
  capex: number | null;
  free_cash_flow: number | null;
  total_debt: number | null;
  total_cash: number | null;
  total_equity: number | null;
  shares_outstanding: number | null;
}

export interface Financials {
  ticker: string;
  currency: string | null;
  period: string;
  years: FinancialYear[];
}

export interface NewsItem {
  title: string;
  url: string | null;
  source: string | null;
  kind: string;
  published_at: string | null;
  summary: string | null;
}

export interface NewsList {
  ticker: string;
  items: NewsItem[];
}
