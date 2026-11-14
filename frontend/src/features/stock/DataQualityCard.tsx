/** 个股数据质量面板（PRD §5.17 FR-RESEARCH-05）。
 *
 * 展示各数据区块的来源、时间、缓存/stale 状态、缺失字段与交叉校验差异；
 * 只描述已有取数结果，不推算缺失数据。
 */
import { useDataQuality } from "@/api/queries";
import { DASH, fmtBig, fmtNum } from "@/lib/format";

function fmtTime(value: string | null): string {
  if (!value) return DASH;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return DASH;
  return date.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

export default function DataQualityCard({ ticker }: { ticker: string }) {
  const { data, isLoading, isError, error } = useDataQuality(ticker);

  if (isLoading) return <p className="note">正在汇总数据质量 …</p>;
  if (isError) {
    return (
      <p className="text-red text-sm">
        {(error as Error)?.message ?? "数据质量信息加载失败"}
      </p>
    );
  }

  const quality = data?.data;
  if (!quality) return null;

  return (
    <div>
      {quality.warnings.length > 0 ? (
        <ul className="mb-3 space-y-1">
          {quality.warnings.map((warning) => (
            <li key={warning} className="text-accent text-xs">
              ⚠️ {warning}
            </li>
          ))}
        </ul>
      ) : (
        <p className="note mb-3">
          未发现明显的数据质量问题；缺失字段仍会以「—」展示且不参与计算。
        </p>
      )}

      <div className="overflow-x-auto">
        <table className="data-table">
          <thead>
            <tr>
              <th>区块</th>
              <th>来源</th>
              <th>数据时间</th>
              <th>状态</th>
              <th>缺失字段</th>
              <th>备注</th>
            </tr>
          </thead>
          <tbody>
            {quality.sections.map((section) => (
              <tr key={section.key}>
                <td>{section.label}</td>
                <td>{section.source ?? DASH}</td>
                <td>{fmtTime(section.as_of)}</td>
                <td className={section.stale ? "text-accent" : undefined}>
                  {section.stale ? "过期缓存" : section.cached ? "命中缓存" : "实时"}
                </td>
                <td>
                  {section.missing_fields.length > 0
                    ? section.missing_fields.join("、")
                    : DASH}
                </td>
                <td>{section.note ?? DASH}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {quality.cross_check && (
        <p className={`note mt-3 ${quality.cross_check.conflict ? "text-red" : ""}`}>
          交叉校验：年报营业收入 {fmtBig(quality.cross_check.values.annual ?? null)}，TTM{" "}
          {fmtBig(quality.cross_check.values.ttm ?? null)}，比例{" "}
          {fmtNum(quality.cross_check.ratio, 3)}。{quality.cross_check.note}
        </p>
      )}

      <p className="note mt-3">
        stale 表示数据源失败时返回了过期缓存；缺失字段不做估算填充。最近检查：
        {fmtTime(quality.checked_at)}。
      </p>
    </div>
  );
}
