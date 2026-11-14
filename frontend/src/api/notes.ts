/** 研究笔记的类型与查询/变更 hooks（FR-RESEARCH-03）。 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./api";

export type NoteKind = "conclusion" | "assumption" | "question" | "note";

export const NOTE_KIND_LABELS: Record<NoteKind, string> = {
  conclusion: "结论",
  assumption: "假设",
  question: "待验证",
  note: "其他",
};

export const NOTE_KIND_ORDER: NoteKind[] = [
  "conclusion",
  "assumption",
  "question",
  "note",
];

export interface ResearchNote {
  id: number;
  ticker: string;
  kind: NoteKind;
  title: string;
  content: string | null;
  preset_id: number | null;
  preset_name: string | null;
  is_resolved: boolean;
  created_at: string;
  updated_at: string;
}

export interface NoteInput {
  ticker: string;
  kind: NoteKind;
  title: string;
  content: string | null;
  preset_id: number | null;
  is_resolved: boolean;
}

export type NotePatch = Partial<Omit<NoteInput, "ticker">>;

export const noteKey = (ticker: string, query: string, kind: NoteKind | "all") =>
  ["notes", ticker, query, kind] as const;

export function useNotes(ticker: string, query = "", kind: NoteKind | "all" = "all") {
  const params = new URLSearchParams({ ticker });
  if (query) params.set("q", query);
  if (kind !== "all") params.set("kind", kind);
  return useQuery({
    queryKey: noteKey(ticker, query, kind),
    queryFn: () =>
      api.get<{ items: ResearchNote[]; total: number }>(`/notes?${params.toString()}`),
    enabled: Boolean(ticker),
  });
}

export function useNoteMutations(ticker: string) {
  const qc = useQueryClient();
  const invalidate = () => qc.invalidateQueries({ queryKey: ["notes", ticker] });

  const createNote = useMutation({
    mutationFn: (body: NoteInput) => api.post<ResearchNote>("/notes", body),
    onSuccess: invalidate,
  });

  const updateNote = useMutation({
    mutationFn: (body: { id: number } & NotePatch) => {
      const { id, ...patch } = body;
      return api.patch<ResearchNote>(`/notes/${id}`, patch);
    },
    onSuccess: invalidate,
  });

  const deleteNote = useMutation({
    mutationFn: (id: number) => api.del<{ id: number; deleted: boolean }>(`/notes/${id}`),
    onSuccess: invalidate,
  });

  return { createNote, updateNote, deleteNote };
}
