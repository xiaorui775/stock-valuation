/** 估值相关类型与查询。 */
import { useQuery } from "@tanstack/react-query";
import { api } from "./api";

export interface ValuationInputs {
  base_fcf: number | null;
  base_fcf_year: number | null;
  growth: number;
  years1: number;
  terminal: number;
  discount: number;
  discount_default_capm: number;
  beta: number | null;
  total_debt: number | null;
  total_cash: number | null;
  shares_outstanding: number | null;
  balance_note: string | null;
  ddm_growth: number;
}

export interface DcfResult {
  per_share: number;
  upside_pct: number | null;
  enterprise_value: number;
  equity_value: number;
  base_fcf: number | null;
  pv_terminal_ratio: number | null;
  formula: string;
}

export interface Multiple {
  name: string;
  value: number | null;
  formula: string;
}

export interface Valuation {
  ticker: string;
  currency: string | null;
  price: number | null;
  inputs: ValuationInputs;
  dcf: DcfResult | null;
  sensitivity: {
    terminal_growths: number[];
    rows: { discount: number; values: (number | null)[] }[];
  } | null;
  multiples: Multiple[];
  ddm: {
    per_share: number;
    dividend_yield: number;
    growth: number;
    discount: number;
    formula: string;
  } | null;
  graham: number | null;
  summary: {
    average_value: number;
    methods_used: number;
    vs_price_pct: number;
    band: string;
    note: string;
  } | null;
  disclaimer: string;
}

export interface WaccResult {
  inputs: Record<string, number | null>;
  result: {
    wacc: number;
    cost_of_equity: number;
    after_tax_cost_of_debt: number;
    weight_equity: number;
    weight_debt: number;
  } | null;
  formula: string;
}

export interface ScenarioItem {
  name: string;
  growth: number | null;
  terminal: number | null;
  discount: number | null;
  probability: number;
  per_share: number | null;
  upside_pct: number | null;
  error: string | null;
}

export interface Scenarios {
  scenarios: ScenarioItem[];
  weighted: number | null;
  weighted_upside_pct: number | null;
  error: string | null;
}

export interface ReverseResult {
  implied_growth: number | null;
  value_at_solution: number | null;
  range: number[] | null;
  reason: string | null;
}

export interface ValuationParams {
  growth?: number;
  terminal?: number;
  discount?: number;
  ddm_growth?: number;
  years1?: number;
}

export function valuationKey(ticker: string, params: ValuationParams) {
  return ["stocks", ticker, "valuation", JSON.stringify(params)] as const;
}

export function useValuation(ticker: string, params: ValuationParams) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") query.set(k, String(v));
  });
  const qs = query.toString();
  return useQuery({
    queryKey: valuationKey(ticker, params),
    queryFn: () => api.get<Valuation>(`/stocks/${encodeURIComponent(ticker)}/valuation${qs ? `?${qs}` : ""}`),
    enabled: Boolean(ticker),
  });
}

export function useWacc(ticker: string) {
  return useQuery({
    queryKey: ["stocks", ticker, "valuation", "wacc"],
    queryFn: () => api.get<WaccResult>(`/stocks/${encodeURIComponent(ticker)}/valuation/wacc`),
    enabled: Boolean(ticker),
  });
}
