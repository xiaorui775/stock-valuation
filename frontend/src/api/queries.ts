/** TanStack Query hooks：统一缓存键与失效策略。 */
import { useQuery } from "@tanstack/react-query";
import { api } from "./api";
import type { Financials, History, Instrument, NewsList, Quote, User } from "./types";

export const queryKeys = {
  authStatus: ["auth", "status"] as const,
  me: ["auth", "me"] as const,
  search: (q: string, market?: string) => ["search", q, market ?? ""] as const,
  quote: (ticker: string) => ["stocks", ticker, "quote"] as const,
  history: (ticker: string, period: string, interval: string) =>
    ["stocks", ticker, "history", period, interval] as const,
  financials: (ticker: string, period: string) =>
    ["stocks", ticker, "financials", period] as const,
  news: (ticker: string, kind: string) => ["stocks", ticker, "news", kind] as const,
};

export function useAuthStatus() {
  return useQuery({
    queryKey: queryKeys.authStatus,
    queryFn: () => api.get<{ initialized: boolean }>("/auth/status"),
    staleTime: 60_000,
    retry: false,
  });
}

export function useCurrentUser() {
  return useQuery({
    queryKey: queryKeys.me,
    queryFn: () => api.get<User>("/auth/me"),
    staleTime: 60_000,
    retry: false,
  });
}

export function useSearch(q: string, market?: string) {
  return useQuery({
    queryKey: queryKeys.search(q, market),
    queryFn: () => api.get<Instrument[]>(`/search?q=${encodeURIComponent(q)}${market ? `&market=${market}` : ""}`),
    enabled: q.trim().length > 0,
    staleTime: 60_000,
  });
}

export function useQuote(ticker: string) {
  return useQuery({
    queryKey: queryKeys.quote(ticker),
    queryFn: () => api.get<Quote>(`/stocks/${encodeURIComponent(ticker)}/quote`),
    enabled: Boolean(ticker),
    staleTime: 30_000,
  });
}

export function useHistory(ticker: string, period: string, interval: string) {
  return useQuery({
    queryKey: queryKeys.history(ticker, period, interval),
    queryFn: () =>
      api.get<History>(
        `/stocks/${encodeURIComponent(ticker)}/history?period=${period}&interval=${interval}`,
      ),
    enabled: Boolean(ticker),
    staleTime: 60_000,
  });
}

export function useFinancials(ticker: string, period: string) {
  return useQuery({
    queryKey: queryKeys.financials(ticker, period),
    queryFn: () =>
      api.get<Financials>(
        `/stocks/${encodeURIComponent(ticker)}/financials?period=${period}&limit=5`,
      ),
    enabled: Boolean(ticker),
    staleTime: 300_000,
  });
}

export function useNews(ticker: string, kind: string) {
  return useQuery({
    queryKey: queryKeys.news(ticker, kind),
    queryFn: () =>
      api.get<NewsList>(`/stocks/${encodeURIComponent(ticker)}/news?kind=${kind}`),
    enabled: Boolean(ticker),
    staleTime: 300_000,
  });
}
