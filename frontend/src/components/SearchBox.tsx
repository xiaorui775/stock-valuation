/** 全局搜索框：代码与公司名称搜索，最近搜索，键盘导航。
 *
 * 对应 PRD §5.2：
 * - FR-SEARCH-01 顶栏常驻、300ms 防抖、下拉展示代码/名称/市场/交易所/货币/数据源
 * - FR-SEARCH-04 最近搜索本地保存 10 条，可清除
 */
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useSearch } from "@/api/queries";
import type { Instrument } from "@/api/types";
import { useDebounced } from "@/hooks/useDebounced";
import { useRecentSearches } from "@/hooks/useRecentSearches";
import { marketLabel } from "@/lib/format";

interface Props {
  onNavigate?: () => void;
}

/** 输入是否像代码（ASCII 字母数字 + . - ^ =）；中文名称不是代码。 */
function isCodeLike(value: string): boolean {
  return /^[A-Za-z0-9][A-Za-z0-9.\-^=]*$/.test(value.trim());
}

export default function SearchBox({ onNavigate }: Props) {
  const navigate = useNavigate();
  const [keyword, setKeyword] = useState("");
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const debounced = useDebounced(keyword, 300);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const recent = useRecentSearches();

  const trimmed = debounced.trim();
  const { data, isFetching } = useSearch(trimmed);
  const results: Instrument[] = data?.data ?? [];

  // 最近搜索在下拉打开且输入为空时展示
  const showRecent = open && keyword.trim() === "" && recent.items.length > 0;
  const rows: Instrument[] = showRecent
    ? recent.items.map((r) => ({
        ticker: r.ticker,
        name: r.name,
        market: r.market as Instrument["market"],
        exchange: null,
        currency: null,
        kind: "equity",
        provider: "local",
        note: null,
      }))
    : results;

  const searching = open && trimmed.length > 0 && isFetching;

  // 点击外部关闭下拉
  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (!containerRef.current?.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  // "/" 聚焦搜索框
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const target = e.target as HTMLElement | null;
      const typing =
        target &&
        (target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.isContentEditable);
      if (e.key === "/" && !typing) {
        e.preventDefault();
        inputRef.current?.focus();
      }
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    setActiveIndex(-1);
  }, [debounced]);

  function go(ticker: string, name?: string, market?: string) {
    const t = ticker.trim().toUpperCase();
    if (!t) return;
    recent.add({ ticker: t, name: name ?? t, market: market ?? "UNKNOWN" });
    setKeyword("");
    setOpen(false);
    onNavigate?.();
    navigate(`/stock/${encodeURIComponent(t)}`);
  }

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const active = rows[activeIndex];
    if (active) {
      go(active.ticker, active.name, active.market);
      return;
    }
    const typed = keyword.trim();
    if (!typed) return;
    // 有搜索结果时回车默认选第一条（名称查询也能落到真实代码上）
    if (rows.length > 0) {
      go(rows[0].ticker, rows[0].name, rows[0].market);
      return;
    }
    // 没有结果：只有看起来是代码才进详情页，否则停在搜索框
    if (!isCodeLike(typed)) return;
    // 输入是 6 位纯数字时提示需要交易所后缀，但仍可进入（由个股页给出提示）
    go(typed.toUpperCase());
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (!open && (e.key === "ArrowDown" || e.key === "ArrowUp")) {
      setOpen(true);
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((i) => (rows.length ? (i + 1) % rows.length : -1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((i) => (rows.length ? (i - 1 + rows.length) % rows.length : -1));
    } else if (e.key === "Escape") {
      setOpen(false);
    } else if (e.key === "Enter") {
      onSubmit(e as unknown as React.FormEvent);
    }
  }

  return (
    <div ref={containerRef} className="relative flex-1 max-w-xl">
      <form onSubmit={onSubmit}>
        <div className="flex gap-2">
          <input
            ref={inputRef}
            className="input flex-1"
            placeholder="搜索代码或名称：AAPL / 0700.HK / 600519.SS / 贵州茅台"
            value={keyword}
            onChange={(e) => {
              setKeyword(e.target.value);
              setOpen(true);
            }}
            onFocus={() => setOpen(true)}
            onClick={() => setOpen(true)}
            onMouseDown={() => setOpen(true)}
            onKeyDown={onKeyDown}
            autoComplete="off"
            spellCheck={false}
            aria-label="搜索股票"
            aria-expanded={open}
            role="combobox"
            aria-controls="search-dropdown"
          />
          <button className="btn btn-primary" type="submit">
            查询
          </button>
        </div>
      </form>

      {open && (
        <div
          id="search-dropdown"
          role="listbox"
          className="absolute z-30 mt-1 left-0 right-0 bg-panel2 border border-line rounded-md overflow-hidden shadow-xl"
        >
          {showRecent && (
            <div className="flex items-center justify-between px-3 py-1.5 border-b border-line">
              <span className="text-[11px] text-muted uppercase tracking-wide">最近搜索</span>
              <button
                type="button"
                className="text-[11px] text-muted hover:text-text"
                onClick={recent.clear}
              >
                清空
              </button>
            </div>
          )}

          {searching && <div className="px-3 py-2 text-sm text-muted">搜索中…</div>}

          {!searching && trimmed.length > 0 && rows.length === 0 && (
            <div className="px-3 py-4 text-sm text-muted">
              没有找到「{trimmed}」。
              <span className="block mt-1 text-xs">
                代码无效或暂无数据。港股请加 .HK 后缀，A 股请加 .SS / .SZ / .BJ 后缀。
              </span>
            </div>
          )}

          {!searching &&
            trimmed.length === 0 &&
            !showRecent && (
              <div className="px-3 py-4 text-sm text-muted">
                输入代码或公司名称开始搜索。
              </div>
            )}

          {rows.map((item, idx) => (
            <button
              key={`${item.ticker}-${idx}`}
              type="button"
              role="option"
              aria-selected={idx === activeIndex}
              className={`w-full text-left px-3 py-2 flex items-center justify-between gap-3 text-sm ${
                idx === activeIndex ? "bg-line" : "hover:bg-line"
              }`}
              onMouseEnter={() => setActiveIndex(idx)}
              onClick={() => go(item.ticker, item.name, item.market)}
            >
              <span className="min-w-0">
                <span className="font-semibold">{item.ticker}</span>
                <span className="text-muted ml-2 truncate">{item.name}</span>
                {item.note && (
                  <span className="block text-[11px] text-accent mt-0.5">{item.note}</span>
                )}
              </span>
              <span className="shrink-0 flex items-center gap-1.5 text-[11px] text-muted">
                {item.exchange && <span>{item.exchange}</span>}
                <span className="badge bg-line">{marketLabel(item.market)}</span>
                {item.currency && <span>{item.currency}</span>}
                {item.provider && <span>{item.provider}</span>}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
