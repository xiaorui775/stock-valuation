/** 投资组合的类型与查询/变更 hooks（FR-PORT-01 / 02）。 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./api";

export type PortfolioCurrency = "CNY" | "USD" | "HKD";

export interface Holding {
  id: number;
  ticker: string;
  name: string;
  market: string;
  currency: string | null;
  quantity: number;
  avg_cost: number;
  opened_on: string | null;
  note: string;
  created_at: string;
  updated_at: string;
}

export interface Portfolio {
  id: number;
  name: string;
  base_currency: string;
  note: string;
  sort_order: number;
  holding_count: number;
  holdings: Holding[];
  created_at: string;
  updated_at: string;
}

export interface HoldingInput {
  ticker: string;
  quantity: number;
  avg_cost: number;
  currency?: PortfolioCurrency | null;
  opened_on?: string | null;
  note?: string;
}

export const portfolioKey = ["portfolios"] as const;

export function usePortfolios() {
  return useQuery({
    queryKey: portfolioKey,
    queryFn: () => api.get<{ items: Portfolio[] }>("/portfolios"),
    staleTime: 10_000,
  });
}

/** 组合汇总（FR-PORT-03 / 04 / 07）。 */
export interface FxRate {
  currency: string;
  rate: number | null;
  source: string | null;
  as_of: string | null;
  symbol: string | null;
}

export interface HoldingSummary {
  ticker: string;
  name: string;
  market: string;
  currency: string | null;
  quantity: number;
  avg_cost: number;
  price: number | null;
  previous_close: number | null;
  fx_rate: number | null;
  dcf_upside_pct: number | null;
  as_of: string | null;
  error: string | null;
  market_value_local: number | null;
  market_value: number | null;
  cost: number | null;
  unrealized_pnl: number | null;
  unrealized_pnl_pct: number | null;
  day_pnl: number | null;
  weight_pct: number | null;
  converted: boolean;
}

export interface PortfolioSummary {
  portfolio_id: number;
  name: string;
  base_currency: string;
  as_of: string | null;
  total_market_value: number | null;
  total_cost: number | null;
  unrealized_pnl: number | null;
  unrealized_pnl_pct: number | null;
  day_pnl: number | null;
  day_pnl_pct: number | null;
  weighted_upside_pct: number | null;
  upside_coverage_pct: number | null;
  rows: HoldingSummary[];
  fx_rates: FxRate[];
  unconverted: {
    currency: string;
    count: number;
    priced_count: number;
    market_value_local: number | null;
  }[];
  distribution: { market: string; market_value: number | null; weight_pct: number | null }[];
  concentration: { ticker: string; name: string; weight_pct: number | null }[];
  warnings: string[];
}

export function usePortfolioSummary(portfolioId: number | null) {
  return useQuery({
    queryKey: ["portfolios", portfolioId, "summary"] as const,
    queryFn: () =>
      api.get<PortfolioSummary>(`/portfolios/${portfolioId}/summary`),
    enabled: Boolean(portfolioId),
    staleTime: 15_000,
  });
}

export function usePortfolioMutations() {
  const qc = useQueryClient();
  const invalidate = () => qc.invalidateQueries({ queryKey: portfolioKey });

  const createPortfolio = useMutation({
    mutationFn: (body: {
      name: string;
      base_currency: PortfolioCurrency;
      note?: string;
    }) => api.post<Portfolio>("/portfolios", body),
    onSuccess: invalidate,
  });
  const updatePortfolio = useMutation({
    mutationFn: (body: {
      id: number;
      name?: string;
      base_currency?: PortfolioCurrency;
      note?: string;
    }) => {
      const { id, ...rest } = body;
      return api.patch<Portfolio>(`/portfolios/${id}`, rest);
    },
    onSuccess: invalidate,
  });
  const deletePortfolio = useMutation({
    mutationFn: (id: number) =>
      api.del<{ id: number; deleted: boolean }>(`/portfolios/${id}`),
    onSuccess: invalidate,
  });

  const addHolding = useMutation({
    mutationFn: (body: { portfolioId: number; holding: HoldingInput }) => {
      const { portfolioId, holding } = body;
      return api.post<Holding>(`/portfolios/${portfolioId}/holdings`, holding);
    },
    onSuccess: invalidate,
  });
  const updateHolding = useMutation({
    mutationFn: (body: {
      portfolioId: number;
      holdingId: number;
      patch: Partial<Omit<HoldingInput, "ticker">>;
    }) =>
      api.patch<Holding>(
        `/portfolios/${body.portfolioId}/holdings/${body.holdingId}`,
        body.patch,
      ),
    onSuccess: invalidate,
  });
  const deleteHolding = useMutation({
    mutationFn: (body: { portfolioId: number; holdingId: number }) =>
      api.del<{ id: number; deleted: boolean }>(
        `/portfolios/${body.portfolioId}/holdings/${body.holdingId}`,
      ),
    onSuccess: invalidate,
  });

  return {
    createPortfolio,
    updatePortfolio,
    deletePortfolio,
    addHolding,
    updateHolding,
    deleteHolding,
  };
}
