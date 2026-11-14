/** 多股对比的类型与查询（§5.10）。 */
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./api";

export interface CompareTicker {
  ticker: string;
  name: string;
  market: string;
  currency: string | null;
  error: string | null;
}

export interface ComparePoint {
  date: string;
  value: number;
}

export interface CompareMetric {
  key: string;
  label: string;
  /** pct = 百分点，x = 倍数，currency = 金额（原币） */
  unit: string;
  direction: "higher" | "lower" | null;
  values: Record<string, number | null>;
  best: string | null;
  worst: string | null;
  missing: string[];
}

export interface CompareResult {
  as_of: string;
  period: string;
  tickers: CompareTicker[];
  series: Record<string, ComparePoint[]>;
  metrics: CompareMetric[];
  valuation: {
    assumptions: { growth: number; years1: number; terminal: number; note: string };
    rows: {
      ticker: string;
      price: number | null;
      per_share: number | null;
      upside_pct: number | null;
    }[];
  };
  warnings: string[];
}

export function useCompare(tickers: string[], period: string) {
  const key = tickers.join(",");
  return useQuery({
    queryKey: ["compare", key, period] as const,
    queryFn: () =>
      api.get<CompareResult>(
        `/compare?tickers=${encodeURIComponent(key)}&period=${encodeURIComponent(period)}`,
      ),
    enabled: tickers.length >= 2,
    placeholderData: keepPreviousData,
    staleTime: 60_000,
  });
}

export interface ComparePreset {
  id: number;
  name: string;
  tickers: string[];
  created_at: string;
  updated_at: string;
}

export const comparePresetKey = ["compare", "presets"] as const;

export function useComparePresets() {
  return useQuery({
    queryKey: comparePresetKey,
    queryFn: () => api.get<{ items: ComparePreset[] }>("/compare/presets"),
    staleTime: 60_000,
  });
}

export function useComparePresetMutations() {
  const qc = useQueryClient();
  const invalidate = () => qc.invalidateQueries({ queryKey: comparePresetKey });

  const createPreset = useMutation({
    mutationFn: (body: { name: string; tickers: string[] }) =>
      api.post<ComparePreset>("/compare/presets", body),
    onSuccess: invalidate,
  });

  const updatePreset = useMutation({
    mutationFn: (body: { id: number; name?: string; tickers?: string[] }) => {
      const { id, ...patch } = body;
      return api.patch<ComparePreset>(`/compare/presets/${id}`, patch);
    },
    onSuccess: invalidate,
  });

  const deletePreset = useMutation({
    mutationFn: (id: number) =>
      api.del<{ id: number; deleted: boolean }>(`/compare/presets/${id}`),
    onSuccess: invalidate,
  });

  return { createPreset, updatePreset, deletePreset };
}
