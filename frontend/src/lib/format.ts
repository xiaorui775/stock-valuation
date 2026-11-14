/** 数值格式化：缺失一律显示「—」，不做填充。 */

export const DASH = "—";

export function fmtNum(
  value: number | null | undefined,
  digits = 2,
): string {
  if (value === null || value === undefined || Number.isNaN(value)) return DASH;
  return value.toLocaleString("zh-CN", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function fmtInt(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return DASH;
  return Math.round(value).toLocaleString("zh-CN");
}

/** 大额金额：万亿 / 亿 / 万 */
export function fmtBig(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return DASH;
  const a = Math.abs(value);
  if (a >= 1e12) return `${fmtNum(value / 1e12)} 万亿`;
  if (a >= 1e8) return `${fmtNum(value / 1e8)} 亿`;
  if (a >= 1e4) return `${fmtNum(value / 1e4)} 万`;
  return fmtNum(value);
}

/** 财务报表：统一换算成亿元 */
export function fmtYi(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return DASH;
  return fmtNum(value / 1e8);
}

/** 百分数：入参为百分点（10 表示 10%） */
export function fmtPct(
  value: number | null | undefined,
  digits = 2,
  withSign = false,
): string {
  if (value === null || value === undefined || Number.isNaN(value)) return DASH;
  const sign = withSign && value > 0 ? "+" : "";
  return `${sign}${fmtNum(value, digits)}%`;
}

export function fmtSigned(
  value: number | null | undefined,
  digits = 2,
): string {
  if (value === null || value === undefined || Number.isNaN(value)) return DASH;
  const sign = value > 0 ? "+" : "";
  return `${sign}${fmtNum(value, digits)}`;
}

/** 涨跌配色：默认红涨绿跌，可在设置中切换 */
export type ColorScheme = "cn" | "intl";

export function changeClass(
  value: number | null | undefined,
  scheme: ColorScheme = "cn",
): string {
  if (value === null || value === undefined || Number.isNaN(value) || value === 0) {
    return "text-muted";
  }
  const up = value > 0;
  if (scheme === "cn") return up ? "text-red" : "text-green";
  return up ? "text-green" : "text-red";
}

/** 估值空间的配色：低于现价为「高估」，用红色标示风险。
 *
 * 与涨跌配色方向相反——价格下跌是中性事实，而估值低于现价是负面信号。
 */
export function valuationClass(
  value: number | null | undefined,
  scheme: ColorScheme = "cn",
): string {
  if (value === null || value === undefined || Number.isNaN(value) || value === 0) {
    return "text-muted";
  }
  const undervalued = value > 0;
  if (scheme === "cn") return undervalued ? "text-green" : "text-red";
  return undervalued ? "text-red" : "text-green";
}

/** 市场的中文标签。 */
export function marketLabel(market: string | null | undefined): string {
  switch (market) {
    case "US":
      return "美股";
    case "HK":
      return "港股";
    case "CN":
      return "A股";
    default:
      return "未知";
  }
}
