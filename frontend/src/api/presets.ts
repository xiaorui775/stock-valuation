/** 估值预设的类型与查询/变更 hooks（FR-VAL-07）。 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./api";

export interface PresetAssumptions {
  base_fcf: number | null;
  growth: number | null;
  years1: number | null;
  terminal: number | null;
  discount: number | null;
  ddm_growth: number | null;
}

export interface Preset {
  id: number;
  ticker: string;
  name: string;
  assumptions: PresetAssumptions;
  created_at: string;
  updated_at: string;
}

export const presetKey = (ticker: string) =>
  ["stocks", ticker, "valuation", "presets"] as const;

/** 预设对比（FR-RESEARCH-02）：同一份行情/财报下的生效假设与 DCF 结果。 */
export interface PresetComparisonRow {
  preset_id: number;
  name: string;
  growth: number;
  years1: number;
  terminal: number;
  discount: number;
  ddm_growth: number;
  base_fcf: number | null;
  per_share: number | null;
  upside_pct: number | null;
  pv_terminal_ratio: number | null;
  note: string | null;
}

export interface PresetComparison {
  ticker: string;
  price: number | null;
  currency: string | null;
  items: PresetComparisonRow[];
  notes: string[];
}

export function usePresetComparison(ticker: string, ids: number[]) {
  const params = new URLSearchParams();
  for (const id of ids) params.append("ids", String(id));
  return useQuery({
    queryKey: [...presetKey(ticker), "compare", ids.join(",")],
    queryFn: () =>
      api.get<PresetComparison>(
        `/stocks/${encodeURIComponent(ticker)}/valuation/presets/compare?${params.toString()}`,
      ),
    enabled: Boolean(ticker) && ids.length >= 2,
  });
}

export function usePresets(ticker: string) {
  return useQuery({
    queryKey: presetKey(ticker),
    queryFn: () =>
      api.get<{ items: Preset[] }>(
        `/stocks/${encodeURIComponent(ticker)}/valuation/presets`,
      ),
    enabled: Boolean(ticker),
  });
}

export function usePresetMutations(ticker: string) {
  const qc = useQueryClient();
  const invalidate = () => qc.invalidateQueries({ queryKey: presetKey(ticker) });
  const base = `/stocks/${encodeURIComponent(ticker)}/valuation/presets`;

  const createPreset = useMutation({
    mutationFn: (body: { name: string; assumptions: PresetAssumptions }) =>
      api.post<Preset>(base, body),
    onSuccess: invalidate,
  });

  const updatePreset = useMutation({
    mutationFn: (body: {
      id: number;
      name?: string;
      assumptions?: PresetAssumptions;
    }) => api.patch<Preset>(`${base}/${body.id}`, { name: body.name, assumptions: body.assumptions }),
    onSuccess: invalidate,
  });

  const deletePreset = useMutation({
    mutationFn: (id: number) => api.del<{ id: number; deleted: boolean }>(`${base}/${id}`),
    onSuccess: invalidate,
  });

  return { createPreset, updatePreset, deletePreset };
}
