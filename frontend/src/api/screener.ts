/** 筛选器类型与请求（§5.11）。 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./api";

export type MetricKey =
  | "market_cap"
  | "pe_ttm"
  | "forward_pe"
  | "peg"
  | "price_to_book"
  | "price_to_sales"
  | "ev_ebitda"
  | "dividend_yield"
  | "revenue_growth"
  | "fcf_yield"
  | "dcf_upside_pct"
  | "beta";

export type MarketKey = "US" | "HK" | "CN";

export interface ScreenerFilter {
  metric: MetricKey;
  min?: number | null;
  max?: number | null;
}

export interface ScreenerRequest {
  pool: {
    kind: "custom" | "watchlist" | "index";
    tickers?: string[];
    watchlist_id?: number | null;
    index_key?: string | null;
  };
  market?: MarketKey[] | null;
  filters?: ScreenerFilter[];
  sort_key?: MetricKey | null;
  sort_desc?: boolean;
  page?: number;
  page_size?: number;
}

export interface ScreenerRow {
  ticker: string;
  name: string;
  market: string;
  currency: string | null;
  price: number | null;
  market_cap: number | null;
  pe_ttm: number | null;
  forward_pe: number | null;
  peg: number | null;
  price_to_book: number | null;
  price_to_sales: number | null;
  ev_ebitda: number | null;
  dividend_yield: number | null;
  revenue_growth: number | null;
  fcf_yield: number | null;
  dcf_upside_pct: number | null;
  beta: number | null;
  as_of: string | null;
}

export interface ScreenerResult {
  as_of: string;
  page: number;
  page_size: number;
  total: number;
  requested: number;
  succeeded: number;
  failed: number;
  failures: { ticker: string; reason: string }[];
  rows: ScreenerRow[];
  elapsed_ms: number;
  estimate_seconds: number;
  note: string;
}

export function useScreen() {
  return useMutation({
    mutationFn: (body: ScreenerRequest) =>
      api.post<ScreenerResult>("/screener", body),
  });
}


export interface IndexSummary {
  key: string;
  label: string;
  count: number;
  source: string;
  updated_at: string | null;
}

export interface ScreenerPreset {
  id: number;
  name: string;
  payload: ScreenerRequest;
  created_at: string;
  updated_at: string;
}

export function useIndexes() {
  return useQuery({
    queryKey: ["screener", "indexes"] as const,
    queryFn: () => api.get<IndexSummary[]>("/screener/indexes"),
    staleTime: 60_000,
  });
}

export function useScreenerPresets() {
  return useQuery({
    queryKey: ["screener", "presets"] as const,
    queryFn: () => api.get<ScreenerPreset[]>("/screener/presets"),
    staleTime: 10_000,
  });
}

export function useScreenerPresetMutations() {
  const qc = useQueryClient();
  const invalidate = () => qc.invalidateQueries({ queryKey: ["screener", "presets"] });
  const createPreset = useMutation({
    mutationFn: (body: { name: string; payload: ScreenerRequest }) =>
      api.post<ScreenerPreset>("/screener/presets", body),
    onSuccess: invalidate,
  });
  const deletePreset = useMutation({
    mutationFn: (id: number) =>
      api.del<{ id: number; deleted: boolean }>(`/screener/presets/${id}`),
    onSuccess: invalidate,
  });
  return { createPreset, deletePreset };
}
