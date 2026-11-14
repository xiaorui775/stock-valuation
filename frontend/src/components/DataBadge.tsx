import type { Meta } from "@/api/api";

/** 数据来源徽标：来源、时间、缓存与缺失字段。 */
export default function DataBadge({ meta }: { meta: Meta }) {
  const asOf = meta.as_of ? new Date(meta.as_of).toLocaleString("zh-CN") : null;
  const missing = meta.missing_fields ?? [];

  return (
    <div className="text-xs text-muted text-right leading-relaxed">
      <div>
        来源：<span className="text-text">{meta.source ?? "—"}</span>
        {asOf && <> · 数据时间：{asOf}</>}
      </div>
      <div>
        {meta.cached && "命中缓存 "}
        {meta.stale && <span className="text-accent">数据已过期（降级返回）</span>}
        {!meta.cached && !meta.stale && "实时获取"}
      </div>
      {missing.length > 0 && (
        <div className="text-accent">缺失字段：{missing.join("、")}</div>
      )}
    </div>
  );
}
