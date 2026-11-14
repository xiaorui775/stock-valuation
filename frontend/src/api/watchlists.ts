/** 自选股的类型与查询/变更 hooks（FR-WATCH-01 / 02）。 */
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./api";

export interface WatchlistItem {
  id: number;
  ticker: string;
  name: string;
  market: string;
  currency: string | null;
  sort_order: number;
}

export interface WatchlistGroup {
  id: number;
  name: string;
  sort_order: number;
  items: WatchlistItem[];
}

export interface BatchResult {
  added: WatchlistItem[];
  failed: { ticker: string; reason: string }[];
}

/** 自选股行情行（FR-WATCH-03）。 */
export interface WatchlistQuote {
  ticker: string;
  name: string | null;
  market: string;
  currency: string | null;
  price: number | null;
  change_pct: number | null;
  market_cap: number | null;
  pe_ttm: number | null;
  forward_pe: number | null;
  dividend_yield: number | null;
  fcf_yield: number | null;
  dcf_upside_pct: number | null;
  earnings_date: string | null;
  days_until_earnings: number | null;
  earnings_source: string | null;
  as_of: string | null;
  stale: boolean;
  error: string | null;
}

export interface WatchlistQuotes {
  group_id: number;
  items: WatchlistQuote[];
  refreshed_at: string;
}

export const watchlistKey = ["watchlists"] as const;

export function useWatchlists() {
  return useQuery({
    queryKey: watchlistKey,
    queryFn: () => api.get<{ groups: WatchlistGroup[] }>("/watchlists"),
    staleTime: 10_000,
  });
}

export function useWatchlistQuotes(groupId: number | null) {
  return useQuery({
    queryKey: ["watchlists", groupId, "quotes"] as const,
    queryFn: () => api.get<WatchlistQuotes>(`/watchlists/${groupId}/quotes`),
    enabled: Boolean(groupId),
    staleTime: 15_000,
    // 刷新时保留上一份数据，失败不清空（FR-WATCH-05）
    placeholderData: keepPreviousData,
  });
}

export function useWatchlistMutations() {
  const qc = useQueryClient();
  const invalidate = () => qc.invalidateQueries({ queryKey: watchlistKey });

  const createGroup = useMutation({
    mutationFn: (name: string) =>
      api.post<WatchlistGroup>("/watchlists", { name }),
    onSuccess: invalidate,
  });
  const renameGroup = useMutation({
    mutationFn: (body: { id: number; name: string }) =>
      api.patch<WatchlistGroup>(`/watchlists/${body.id}`, { name: body.name }),
    onSuccess: invalidate,
  });
  const deleteGroup = useMutation({
    mutationFn: (id: number) =>
      api.del<{ id: number; deleted: boolean }>(`/watchlists/${id}`),
    onSuccess: invalidate,
  });
  const reorderGroups = useMutation({
    mutationFn: (groupIds: number[]) =>
      api.patch<{ groups: WatchlistGroup[] }>("/watchlists/order", {
        group_ids: groupIds,
      }),
    onSuccess: invalidate,
  });

  const addItem = useMutation({
    mutationFn: (body: { groupId: number; ticker: string }) =>
      api.post<WatchlistItem>(`/watchlists/${body.groupId}/items`, {
        ticker: body.ticker,
      }),
    onSuccess: invalidate,
  });
  const addItems = useMutation({
    mutationFn: (body: { groupId: number; tickers: string[] }) =>
      api.post<BatchResult>(`/watchlists/${body.groupId}/items/batch`, {
        tickers: body.tickers,
      }),
    onSuccess: invalidate,
  });
  const removeItem = useMutation({
    mutationFn: (body: { groupId: number; itemId: number }) =>
      api.del<{ id: number; deleted: boolean }>(
        `/watchlists/${body.groupId}/items/${body.itemId}`,
      ),
    onSuccess: invalidate,
  });
  const reorderItems = useMutation({
    mutationFn: (body: { groupId: number; itemIds: number[] }) =>
      api.patch<WatchlistItem[]>(`/watchlists/${body.groupId}/items/order`, {
        item_ids: body.itemIds,
      }),
    onSuccess: invalidate,
  });

  return {
    createGroup,
    renameGroup,
    deleteGroup,
    reorderGroups,
    addItem,
    addItems,
    removeItem,
    reorderItems,
  };
}
