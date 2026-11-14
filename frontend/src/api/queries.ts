/** TanStack Query hooks：统一缓存键与失效策略。 */
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { api } from "./api";
import type { CalendarInfo, DataQuality, Financials, History, Insights, Instrument, NewsList, Overview, Quote, User } from "./types";

export const queryKeys = {
  authStatus: ["auth", "status"] as const,
  me: ["auth", "me"] as const,
  search: (q: string, market?: string) => ["search", q, market ?? ""] as const,
  quote: (ticker: string) => ["stocks", ticker, "quote"] as const,
  overview: (ticker: string) => ["stocks", ticker, "overview"] as const,
  history: (ticker: string, period: string, interval: string) =>
    ["stocks", ticker, "history", period, interval] as const,
  financials: (ticker: string, period: string) =>
    ["stocks", ticker, "financials", period] as const,
  insights: (ticker: string) => ["stocks", ticker, "insights"] as const,
  calendar: (ticker: string) => ["stocks", ticker, "calendar"] as const,
  dataQuality: (ticker: string) => ["stocks", ticker, "data-quality"] as const,
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
    retry: false,
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

export function useOverview(ticker: string) {
  return useQuery({
    queryKey: queryKeys.overview(ticker),
    queryFn: () => api.get<Overview>(`/stocks/${encodeURIComponent(ticker)}/overview`),
    enabled: Boolean(ticker),
    staleTime: 30_000,
  });
}

export function useCalendar(ticker: string) {
  return useQuery({
    queryKey: queryKeys.calendar(ticker),
    queryFn: () => api.get<CalendarInfo>(`/stocks/${encodeURIComponent(ticker)}/calendar`),
    enabled: Boolean(ticker),
    staleTime: 6 * 60 * 60 * 1000,
    retry: false,
  });
}

export function useDataQuality(ticker: string) {
  return useQuery({
    queryKey: queryKeys.dataQuality(ticker),
    queryFn: () =>
      api.get<DataQuality>(`/stocks/${encodeURIComponent(ticker)}/data-quality`),
    enabled: Boolean(ticker),
    staleTime: 60_000,
    retry: false,
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
    // 切换周期/线型时保留上一份数据，避免图表闪空；同一周期的重复切换直接命中缓存
    placeholderData: keepPreviousData,
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

export function useInsights(ticker: string) {
  return useQuery({
    queryKey: queryKeys.insights(ticker),
    queryFn: () => api.get<Insights>(`/stocks/${encodeURIComponent(ticker)}/insights`),
    enabled: Boolean(ticker),
    staleTime: 300_000,
  });
}

export function useNews(ticker: string, kind: string) {  return useQuery({
    queryKey: queryKeys.news(ticker, kind),
    queryFn: () =>
      api.get<NewsList>(`/stocks/${encodeURIComponent(ticker)}/news?kind=${kind}`),
    enabled: Boolean(ticker),
    staleTime: 300_000,
  });
}
