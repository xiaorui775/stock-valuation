/** 估值相关类型与查询。 */
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "./api";

export interface ValuationInputs {
  base_fcf: number | null;
  base_fcf_year: number | null;
  base_fcf_source: string | null;
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

/** 假设来源（FR-VAL-06）。 */
export interface ValuationSources {
  fcf: { value: number | null; year: number | null; origin: string; field: string };
  balance: {
    values: { debt: number | null; cash: number | null; equity: number | null };
    origins: Record<string, string>;
    note: string | null;
  };
  shares: { value: number | null; origin: string };
  beta: { value: number | null; origin: string };
  capm: {
    risk_free: number;
    erp: number;
    beta_used: number;
    value: number;
    formula: string;
  };
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
  sources: ValuationSources;
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
    methods: { name: string; value: number; weight: number }[];
    vs_price_pct: number;
    band: string;
    note: string;
  } | null;
  disclaimer: string;
}

/** 历史分位（FR-VAL-11）。 */
export interface PercentileStats {
  p10: number | null;
  p25: number | null;
  p50: number | null;
  p75: number | null;
  p90: number | null;
  count: number;
}

export interface MetricHistory {
  key: "pe" | "pb" | "ps" | "fcf_yield";
  label: string;
  unit: string;
  current: number | null;
  percentile_3y: number | null;
  percentile_5y: number | null;
  stats_3y: PercentileStats | null;
  stats_5y: PercentileStats | null;
  note: string | null;
}

export interface ValuationHistory {
  ticker: string;
  currency: string | null;
  as_of: string;
  windows: Record<string, string>;
  sample_hint: string;
  metrics: MetricHistory[];
  warnings: string[];
}

export interface WaccResult {  inputs: Record<string, number | null>;
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
  base_fcf?: number;
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

export interface WaccParams {
  risk_free?: number;
  beta?: number;
  erp?: number;
  cost_of_debt?: number;
  tax_rate?: number;
}

export interface ScenarioInput {
  name: string;
  growth: number;
  terminal: number;
  discount: number;
  probability: number;
}

/** 情景分析：概率和必须为 100（后端校验，不在前端静默归一化）。 */
export function useScenarios(ticker: string) {
  return useMutation({
    mutationFn: (scenarios: ScenarioInput[]) =>
      api.post<Scenarios>(
        `/stocks/${encodeURIComponent(ticker)}/valuation/scenarios`,
        { scenarios },
      ),
  });
}

/** 反向 DCF：从现价反推隐含的阶段一增速。 */
export function useReverseDcf(ticker: string) {
  return useMutation({
    mutationFn: (body: {
      price?: number;
      terminal?: number;
      discount?: number;
      years1?: number;
    }) =>
      api.post<ReverseResult>(
        `/stocks/${encodeURIComponent(ticker)}/valuation/reverse`,
        body,
      ),
  });
}

/** 历史估值区间：3 年 / 5 年分位。 */
export function useValuationHistory(ticker: string) {
  return useQuery({
    queryKey: ["stocks", ticker, "valuation", "history"],
    queryFn: () =>
      api.get<ValuationHistory>(
        `/stocks/${encodeURIComponent(ticker)}/valuation/history`,
      ),
    enabled: Boolean(ticker),
  });
}

export interface MultiStageAssumptions {
  growth: number;
  years1: number;
  fade_years: number;
  terminal: number;
  discount: number;
  discount_default_capm: number;
  base_fcf: number | null;
  base_fcf_source: string;
  ddm_growth: number;
}

export interface MultiStageDcf {
  per_share: number;
  upside_pct: number | null;
  enterprise_value: number;
  equity_value: number;
  base_fcf: number | null;
  pv_terminal_ratio: number | null;
  years: number;
}

export interface MultiStageDdm {
  per_share: number;
  upside_pct: number | null;
  dividend_yield: number;
  dps: number;
  pv_explicit: number;
  pv_fade: number;
  pv_terminal: number;
  terminal_ratio: number | null;
  years: number;
}

export interface MultiStage {
  ticker: string;
  currency: string | null;
  price: number | null;
  assumptions: MultiStageAssumptions;
  dcf: MultiStageDcf | null;
  ddm: MultiStageDdm | null;
  ddm_reason: string | null;
  missing: string[];
  formula: string;
  disclaimer: string;
}

export interface MultiStageParams {
  growth?: number;
  terminal?: number;
  discount?: number;
  years1?: number;
  fade_years?: number;
}

/** 三阶段 DCF / DDM（FR-VAL-12）。 */
export function useMultistage(ticker: string, params: MultiStageParams) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) query.set(key, String(value));
  });
  const qs = query.toString();
  return useQuery({
    queryKey: ["stocks", ticker, "valuation", "multistage", qs],
    queryFn: () =>
      api.get<MultiStage>(
        `/stocks/${encodeURIComponent(ticker)}/valuation/multistage${qs ? `?${qs}` : ""}`,
      ),
    enabled: Boolean(ticker),
  });
}

export interface WeightedMethod {
  name: string;
  value: number;
  weight: number;
  contribution: number;
}

export interface WeightedSummary {
  available: { name: string; value: number }[];
  weighted_value: number | null;
  vs_price_pct: number | null;
  band: string | null;
  methods: WeightedMethod[];
  total_weight: number;
  error: string | null;
}

/** 自定义权重的综合估值（FR-VAL-13）。 */
export function useSummaryWeights(ticker: string) {
  return useMutation({
    mutationFn: (methods: { name: string; weight: number }[]) =>
      api.post<WeightedSummary>(
        `/stocks/${encodeURIComponent(ticker)}/valuation/summary`,
        { methods },
      ),
  });
}

export function useWacc(ticker: string, params: WaccParams = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) query.set(key, String(value));
  });
  const qs = query.toString();
  return useQuery({
    queryKey: ["stocks", ticker, "valuation", "wacc", qs],
    queryFn: () =>
      api.get<WaccResult>(
        `/stocks/${encodeURIComponent(ticker)}/valuation/wacc${qs ? `?${qs}` : ""}`,
      ),
    enabled: Boolean(ticker),
  });
}
