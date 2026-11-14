/** 最近搜索：本地持久化，最多保留 10 条（PRD FR-SEARCH-04）。 */
import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "stockval.recent-searches";
const MAX_ITEMS = 10;

export interface RecentSearch {
  ticker: string;
  name: string;
  market: string;
  at: number;
}

function read(): RecentSearch[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    // 过滤掉历史遗留的「名称当代码」条目（如 ticker=英伟达），它们不是合法代码
    return parsed
      .filter(
        (x): x is RecentSearch =>
          Boolean(x && typeof x.ticker === "string" && /^[\x20-\x7E]+$/.test(x.ticker)),
      )
      .slice(0, MAX_ITEMS);
  } catch {
    return [];
  }
}

function write(items: RecentSearch[]): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
  } catch {
    /* 隐私模式下 localStorage 可能不可写，忽略即可 */
  }
}

export function useRecentSearches() {
  const [items, setItems] = useState<RecentSearch[]>(read);

  useEffect(() => {
    write(items);
  }, [items]);

  const add = useCallback((entry: { ticker: string; name: string; market: string }) => {
    setItems((prev) => {
      const rest = prev.filter((x) => x.ticker !== entry.ticker);
      return [{ ...entry, at: Date.now() }, ...rest].slice(0, MAX_ITEMS);
    });
  }, []);

  const remove = useCallback((ticker: string) => {
    setItems((prev) => prev.filter((x) => x.ticker !== ticker));
  }, []);

  const clear = useCallback(() => setItems([]), []);

  return { items, add, remove, clear };
}
