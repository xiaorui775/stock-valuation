/** 与后端 Pydantic 模型对应的类型定义。 */

export type Market = "US" | "HK" | "CN" | "UNKNOWN";

export type InstrumentKind = "equity" | "etf" | "index" | "fund" | "unknown";

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
  kind: InstrumentKind;
  provider: string | null;
  note: string | null;
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

/** 技术指标序列：每条与 bars 按下标对齐，窗口不满为 null。 */
export interface Indicators {
  ma5: (number | null)[];
  ma10: (number | null)[];
  ma20: (number | null)[];
  ma60: (number | null)[];
  ma120: (number | null)[];
  boll_mid: (number | null)[];
  boll_upper: (number | null)[];
  boll_lower: (number | null)[];
  dif: (number | null)[];
  dea: (number | null)[];
  macd: (number | null)[];
  rsi14: (number | null)[];
}

export interface History {
  ticker: string;
  period: string;
  interval: string;
  adjustment: string;
  start_date: string | null;
  end_date: string | null;
  count: number;
  bars: Bar[];
  indicators: Indicators;
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
  yoy: Record<string, number | null>;
}

export interface CrossCheck {
  field: string;
  values: Record<string, number>;
  ratio: number | null;
  diff_pct: number;
  conflict: boolean;
  note: string;
}

export interface CalendarInfo {
  ticker: string;
  earnings_date: string | null;
  dividend_date: string | null;
  ex_dividend_date: string | null;
  days_until_earnings: number | null;
  note: string | null;
}

export interface Financials {
  ticker: string;
  currency: string | null;
  period: string;
  years: FinancialYear[];
  cagr: Record<string, number | null>;
  cagr_years: number;
  missing_fields: string[];
  cross_check?: CrossCheck | null;
}

export interface Insights {
  ticker: string;
  currency: string | null;
  fiscal_year: number | null;
  items: {
    rule: string;
    name: string;
    level: "alert" | "watch" | "info";
    title: string;
    detail: string;
    formula: string;
    value: number | null;
    period: string | null;
  }[];
  uncovered: { rule: string; name: string; reason: string }[];
  summary: string;
}

export interface DataQualitySection {
  key: string;
  label: string;
  source: string | null;
  as_of: string | null;
  cached: boolean;
  stale: boolean;
  missing_fields: string[];
  note: string | null;
}

export interface DataQuality {
  ticker: string;
  checked_at: string;
  sections: DataQualitySection[];
  warnings: string[];
  cross_check: CrossCheck | null;
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

export type SessionStatus = "pre" | "regular" | "post" | "closed";

export interface Session {
  status: SessionStatus;
  label: string;
  timezone: string;
  local_time: string;
  note: string | null;
}

export interface Week52Position {
  position: number | null;
  from_high_pct: number | null;
  from_low_pct: number | null;
}

export interface ValuationConclusion {
  dcf_per_share: number | null;
  upside_pct: number | null;
  average_value: number | null;
  vs_price_pct: number | null;
  band: string | null;
  methods_used: number;
  note: string | null;
}

export interface Overview {
  ticker: string;
  name: string;
  market: Market;
  market_label: string;
  currency: string | null;
  price: number | null;
  change: number | null;
  change_pct: number | null;
  session: Session | null;
  week52: Week52Position | null;
  conclusion: ValuationConclusion | null;
  quote: Quote | null;
  as_of: string | null;
}
