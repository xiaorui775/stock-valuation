/** 年度财务报表：科目表 + 单位切换 + 同比 + 3 年 CAGR（FR-FIN-01/03/04）。
 *
 * 单位切换只改变展示口径，底层数据不变；缺失科目一律显示「—」，不做估算。
 */
import { useState } from "react";
import type { Financials, FinancialYear } from "@/api/types";
import { DASH, fmtBig, fmtNum, fmtPct, changeClass } from "@/lib/format";

type Unit = "yi" | "million" | "raw";
type MetricKind = "money" | "pershare" | "shares";

interface Metric {
  key: keyof FinancialYear;
  label: string;
  kind: MetricKind;
  hint?: string;
}

const UNITS: { key: Unit; label: string; divisor: number; digits: number }[] = [
  { key: "yi", label: "亿", divisor: 1e8, digits: 2 },
  { key: "million", label: "百万", divisor: 1e6, digits: 2 },
  { key: "raw", label: "原始值", divisor: 1, digits: 0 },
];

const GROUPS: { title: string; metrics: Metric[] }[] = [
  {
    title: "利润表",
    metrics: [
      { key: "revenue", label: "营业收入", kind: "money" },
      { key: "gross_profit", label: "毛利润", kind: "money" },
      { key: "operating_income", label: "营业利润", kind: "money" },
      { key: "net_income", label: "净利润", kind: "money" },
      { key: "eps", label: "每股收益 EPS", kind: "pershare", hint: "原币/股，不随单位切换缩放" },
    ],
  },
  {
    title: "现金流",
    metrics: [
      { key: "operating_cash_flow", label: "经营现金流", kind: "money" },
      { key: "capex", label: "资本开支", kind: "money", hint: "以负数表示现金流出" },
      { key: "free_cash_flow", label: "自由现金流", kind: "money" },
    ],
  },
  {
    title: "资产负债",
    metrics: [
      { key: "total_debt", label: "总债务", kind: "money" },
      { key: "total_cash", label: "现金及等价物", kind: "money" },
      { key: "total_equity", label: "股东权益", kind: "money" },
      { key: "shares_outstanding", label: "总股本", kind: "shares", hint: "按股数展示" },
    ],
  },
];

const FIELD_LABELS: Record<string, string> = Object.fromEntries(
  GROUPS.flatMap((g) => g.metrics.map((m) => [m.key, m.label])),
);

function moneyLabel(unit: Unit, currency: string | null): string {
  const cur = currency ?? "原币";
  if (currency === "CNY") {
    if (unit === "yi") return "亿元";
    if (unit === "million") return "百万元";
    return "元";
  }
  if (unit === "yi") return `亿 ${cur}`;
  if (unit === "million") return `百万 ${cur}`;
  return `原始值 ${cur}`;
}

export default function FinancialsTable({
  data,
  source,
}: {
  data: Financials;
  source?: string | null;
}) {
  const [unit, setUnit] = useState<Unit>("yi");
  const [showYoY, setShowYoY] = useState(false);

  const years = data.years;
  if (years.length === 0) return <p className="note">暂无财务数据。</p>;

  const unitDef = UNITS.find((u) => u.key === unit) ?? UNITS[0];

  const formatValue = (metric: Metric, year: FinancialYear): string => {
    const raw = year[metric.key] as number | null;
    if (raw === null || raw === undefined) return DASH;
    if (metric.kind === "shares") return `${fmtBig(raw)}股`;
    if (metric.kind === "pershare") return fmtNum(raw, 2);
    return fmtNum(raw / unitDef.divisor, unitDef.digits);
  };

  const formatYoy = (metric: Metric, year: FinancialYear): string => {
    const value = year.yoy?.[metric.key as string];
    return fmtPct(value ?? null, 2, true);
  };

  return (
    <div>
      <div className="flex justify-between items-start gap-3 flex-wrap mb-3">
        <div className="flex gap-1 items-center" role="group" aria-label="金额单位">
          <span className="note mr-1">单位</span>
          {UNITS.map((u) => (
            <button
              key={u.key}
              type="button"
              className={`tab-chip ${unit === u.key ? "tab-chip-on" : ""}`}
              aria-pressed={unit === u.key}
              onClick={() => setUnit(u.key)}
            >
              {u.label}
            </button>
          ))}
        </div>
        <label className="flex items-center gap-2 text-xs text-muted cursor-pointer select-none">
          <input
            type="checkbox"
            checked={showYoY}
            onChange={(e) => setShowYoY(e.target.checked)}
            className="accent-accent"
          />
          显示同比（YoY）
        </label>
      </div>

      <div className="overflow-x-auto">
        <table className="data-table">
          <thead>
            <tr>
              <th>科目（单位：{moneyLabel(unit, data.currency)}）</th>
              {years.map((y) => (
                <th key={y.year}>{y.year}</th>
              ))}
              <th>{data.cagr_years} 年 CAGR</th>
            </tr>
          </thead>
          <tbody>
            {GROUPS.map((group) => (
              <GroupRows
                key={group.title}
                group={group}
                years={years}
                showYoY={showYoY}
                formatValue={formatValue}
                formatYoy={formatYoy}
                cagr={data.cagr}
              />
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-3 space-y-1">
        <p className="note">
          自由现金流 = 经营现金流 + 资本开支（资本开支以负数表示现金流出）。同比公式为
          (本期 − 上期) / |上期|，上期为 0 或缺失时不计算。
        </p>
        <p className="note">单位切换只改变展示口径，不改动底层数据。</p>
        {data.missing_fields.length > 0 && (
          <p className="note">
            数据源未提供以下科目，显示为「—」且不参与同比：
            {data.missing_fields.map((f) => FIELD_LABELS[f] ?? f).join("、")}。
          </p>
        )}
        {source && <p className="note">数据来源：{source}（{data.period === "annual" ? "年度" : data.period}报表）。</p>}
        {data.cross_check && (
          <p className={`note ${data.cross_check.conflict ? "text-red" : ""}`}>
            交叉校验：营业收入年报 {fmtBig(data.cross_check.values.annual ?? null)}
            {data.currency === "CNY" ? " 元" : ` ${data.currency ?? ""}`}，TTM{" "}
            {fmtBig(data.cross_check.values.ttm ?? null)}，比例{" "}
            {fmtNum(data.cross_check.ratio, 3)}。{data.cross_check.note}
          </p>
        )}
      </div>
    </div>
  );
}

function GroupRows({
  group,
  years,
  showYoY,
  formatValue,
  formatYoy,
  cagr,
}: {
  group: { title: string; metrics: Metric[] };
  years: FinancialYear[];
  showYoY: boolean;
  formatValue: (metric: Metric, year: FinancialYear) => string;
  formatYoy: (metric: Metric, year: FinancialYear) => string;
  cagr: Record<string, number | null>;
}) {
  return (
    <>
      <tr>
        <td
          colSpan={years.length + 2}
          className="!text-left text-muted font-semibold pt-4"
        >
          {group.title}
        </td>
      </tr>
      {group.metrics.map((metric) => (
        <tr key={metric.key as string}>
          <td>
            {metric.label}
            {metric.hint && <span className="note ml-1.5">{metric.hint}</span>}
          </td>
          {years.map((year) => {
            const yoy = year.yoy?.[metric.key as string] ?? null;
            return (
              <td key={year.year}>
                <div>{formatValue(metric, year)}</div>
                {showYoY && (
                  <div className={`text-[11px] ${changeClass(yoy)}`}>
                    {formatYoy(metric, year)}
                  </div>
                )}
              </td>
            );
          })}
          <td className={changeClass(cagr[metric.key as string] ?? null)}>
            {fmtPct(cagr[metric.key as string] ?? null, 2, true)}
          </td>
        </tr>
      ))}
    </>
  );
}
