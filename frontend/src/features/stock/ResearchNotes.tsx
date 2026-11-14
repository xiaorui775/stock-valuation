/** 研究笔记（PRD §5.17 FR-RESEARCH-03）。
 *
 * 按标的记录研究结论、关键假设与待验证问题，可关联同标的的估值预设；
 * 支持按类型筛选与标题/正文关键词检索。笔记按用户隔离，前端只做展示与编辑。
 */
import { useState } from "react";
import {
  NOTE_KIND_LABELS,
  NOTE_KIND_ORDER,
  useNoteMutations,
  useNotes,
  type NoteKind,
  type ResearchNote,
} from "@/api/notes";
import { usePresets } from "@/api/presets";
import { useDebounced } from "@/hooks/useDebounced";

const KIND_HINTS: Record<NoteKind, string> = {
  conclusion: "研究结论或判断",
  assumption: "估值/经营假设",
  question: "尚待验证的问题",
  note: "其他备忘",
};

interface FormState {
  kind: NoteKind;
  title: string;
  content: string;
  presetId: string;
  isResolved: boolean;
}

const EMPTY_FORM: FormState = {
  kind: "conclusion",
  title: "",
  content: "",
  presetId: "",
  isResolved: false,
};

function fmtTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

export default function ResearchNotes({ ticker }: { ticker: string }) {
  const [kindFilter, setKindFilter] = useState<NoteKind | "all">("all");
  const [query, setQuery] = useState("");
  const debouncedQuery = useDebounced(query.trim(), 300);

  const notes = useNotes(ticker, debouncedQuery, kindFilter);
  const presets = usePresets(ticker);
  const { createNote, updateNote, deleteNote } = useNoteMutations(ticker);

  const [editorOpen, setEditorOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [formError, setFormError] = useState<string | null>(null);

  const items = notes.data?.data.items ?? [];
  const presetItems = presets.data?.data.items ?? [];
  const saving = createNote.isPending || updateNote.isPending;

  function openCreate() {
    setEditorOpen(true);
    setEditingId(null);
    setForm(EMPTY_FORM);
    setFormError(null);
  }

  function openEdit(note: ResearchNote) {
    setEditorOpen(true);
    setEditingId(note.id);
    setForm({
      kind: note.kind,
      title: note.title,
      content: note.content ?? "",
      presetId: note.preset_id === null ? "" : String(note.preset_id),
      isResolved: note.is_resolved,
    });
    setFormError(null);
  }

  function closeEditor() {
    setEditorOpen(false);
    setEditingId(null);
    setForm(EMPTY_FORM);
    setFormError(null);
  }

  async function submit() {
    const title = form.title.trim();
    if (!title) {
      setFormError("请填写笔记标题");
      return;
    }
    const payload = {
      kind: form.kind,
      title,
      content: form.content.trim() || null,
      preset_id: form.presetId === "" ? null : Number(form.presetId),
      is_resolved: form.kind === "question" ? form.isResolved : false,
    };
    try {
      if (editingId === null) {
        await createNote.mutateAsync({ ticker, ...payload });
      } else {
        await updateNote.mutateAsync({ id: editingId, ...payload });
      }
      closeEditor();
    } catch (e) {
      setFormError((e as Error).message);
    }
  }

  async function toggleResolved(note: ResearchNote) {
    try {
      await updateNote.mutateAsync({
        id: note.id,
        is_resolved: !note.is_resolved,
      });
    } catch (e) {
      setFormError((e as Error).message);
    }
  }

  async function remove(note: ResearchNote) {
    if (!window.confirm(`删除笔记「${note.title}」？`)) return;
    try {
      await deleteNote.mutateAsync(note.id);
      if (editingId === note.id) closeEditor();
    } catch (e) {
      setFormError((e as Error).message);
    }
  }

  const filtered = debouncedQuery !== "" || kindFilter !== "all";

  return (
    <div className="card">
      <div className="flex justify-between items-start gap-3 flex-wrap mb-3">
        <div>
          <h2 className="card-title !mb-0">研究笔记</h2>
          <p className="note mt-1">
            记录结论、假设与待验证问题；可关联同标的的估值预设。仅自己可见。
          </p>
        </div>
        <button type="button" className="btn btn-primary text-xs" onClick={openCreate}>
          新建笔记
        </button>
      </div>

      {editorOpen && (
        <div className="border border-line rounded-md p-3 mb-4 bg-panel2">
          <h3 className="font-semibold text-sm mb-2">
            {editingId === null ? "新建笔记" : "编辑笔记"}
          </h3>
          <div className="grid gap-2">
            <div className="flex gap-2 flex-wrap items-end">
              <label className="flex flex-col gap-1.5 text-xs text-muted">
                类型
                <select
                  className="input"
                  value={form.kind}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      kind: e.target.value as NoteKind,
                      isResolved:
                        e.target.value === "question" ? prev.isResolved : false,
                    }))
                  }
                >
                  {NOTE_KIND_ORDER.map((kind) => (
                    <option key={kind} value={kind}>
                      {NOTE_KIND_LABELS[kind]}（{KIND_HINTS[kind]}）
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex flex-col gap-1.5 text-xs text-muted flex-1 min-w-56">
                标题
                <input
                  className="input"
                  maxLength={200}
                  placeholder="例如：毛利率能否维持"
                  value={form.title}
                  onChange={(e) => setForm((prev) => ({ ...prev, title: e.target.value }))}
                />
              </label>
              <label className="flex flex-col gap-1.5 text-xs text-muted min-w-44">
                关联估值预设（可选）
                <select
                  className="input"
                  value={form.presetId}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, presetId: e.target.value }))
                  }
                >
                  <option value="">不关联</option>
                  {presetItems.map((preset) => (
                    <option key={preset.id} value={preset.id}>
                      {preset.name}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <label className="flex flex-col gap-1.5 text-xs text-muted">
              正文
              <textarea
                className="input min-h-24"
                maxLength={5000}
                placeholder="结论、依据、待验证事项…（缺失数据请注明）"
                value={form.content}
                onChange={(e) =>
                  setForm((prev) => ({ ...prev, content: e.target.value }))
                }
              />
            </label>

            {form.kind === "question" && (
              <label className="flex items-center gap-2 text-xs text-muted cursor-pointer select-none">
                <input
                  type="checkbox"
                  className="accent-accent"
                  checked={form.isResolved}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, isResolved: e.target.checked }))
                  }
                />
                标记为已解决
              </label>
            )}

            {formError && <p className="text-red text-xs">{formError}</p>}

            <div className="flex gap-2 justify-end">
              <button type="button" className="btn btn-ghost text-xs" onClick={closeEditor}>
                取消
              </button>
              <button
                type="button"
                className="btn btn-primary text-xs"
                disabled={saving}
                onClick={() => void submit()}
              >
                {saving ? "保存中…" : "保存"}
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="flex justify-between items-start gap-3 flex-wrap mb-3">
        <div className="flex gap-1 flex-wrap" role="group" aria-label="笔记类型筛选">
          <button
            type="button"
            className={`tab-chip ${kindFilter === "all" ? "tab-chip-on" : ""}`}
            aria-pressed={kindFilter === "all"}
            onClick={() => setKindFilter("all")}
          >
            全部
          </button>
          {NOTE_KIND_ORDER.map((kind) => (
            <button
              key={kind}
              type="button"
              className={`tab-chip ${kindFilter === kind ? "tab-chip-on" : ""}`}
              aria-pressed={kindFilter === kind}
              onClick={() => setKindFilter(kind)}
            >
              {NOTE_KIND_LABELS[kind]}
            </button>
          ))}
        </div>
        <input
          className="input w-64"
          placeholder="搜索标题或正文"
          aria-label="搜索研究笔记"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>

      {!editorOpen && formError && <p className="text-red text-xs mb-2">{formError}</p>}

      {notes.isLoading ? (
        <p className="note">正在加载笔记 …</p>
      ) : notes.isError ? (
        <p className="text-red text-sm">
          {(notes.error as Error)?.message ?? "研究笔记加载失败"}
        </p>
      ) : items.length === 0 ? (
        <p className="note py-6 text-center">
          {filtered ? "没有符合条件的笔记。" : "还没有研究笔记，点击右上角「新建笔记」记录第一条。"}
        </p>
      ) : (
        <div className="space-y-2">
          {items.map((note) => (
            <article key={note.id} className="border border-line rounded-md p-3">
              <div className="flex justify-between items-start gap-3 flex-wrap">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="badge bg-line">{NOTE_KIND_LABELS[note.kind]}</span>
                    <h3 className="font-semibold text-sm break-words">{note.title}</h3>
                    {note.kind === "question" && note.is_resolved && (
                      <span className="badge bg-line text-green">已解决</span>
                    )}
                  </div>
                  {note.content && (
                    <p className="text-sm text-muted mt-2 whitespace-pre-wrap break-words">
                      {note.content}
                    </p>
                  )}
                  <p className="note mt-2">
                    {note.preset_name ? `关联预设：${note.preset_name} · ` : ""}
                    更新于 {fmtTime(note.updated_at)}
                  </p>
                </div>
                <div className="flex gap-1 shrink-0">
                  <button
                    type="button"
                    className="tab-chip"
                    onClick={() => openEdit(note)}
                  >
                    编辑
                  </button>
                  {note.kind === "question" && (
                    <button
                      type="button"
                      className="tab-chip"
                      onClick={() => void toggleResolved(note)}
                    >
                      {note.is_resolved ? "重新打开" : "标记已解决"}
                    </button>
                  )}
                  <button
                    type="button"
                    className="tab-chip"
                    onClick={() => void remove(note)}
                  >
                    删除
                  </button>
                </div>
              </div>
            </article>
          ))}
        </div>
      )}

      <p className="note mt-3">
        笔记内容为用户输入，不参与估值计算；关联预设只建立引用，不改动预设假设。
      </p>
    </div>
  );
}
