/** 图表通用配色与坐标轴样式，保证价格图、财务趋势图视觉一致。 */
export const CHART_COLORS = {
  line: "#2a3552",
  split: "#232c47",
  text: "#e8ecf5",
  muted: "#93a0bb",
  panel2: "#1e2740",
  accent: "#f5b942",
  up: "#f23645",
  down: "#1db954",
} as const;

/** 财务趋势的系列配色：与图例顺序对应。 */
export const TREND_COLORS = {
  revenue: "#f5b942",
  netIncome: "#5b8ff9",
  operatingCash: "#5ad8a6",
  freeCash: "#e8684a",
  grossMargin: "#f5b942",
  netMargin: "#5b8ff9",
  fcfMargin: "#5ad8a6",
} as const;

/** ECharts 网格：左侧留出坐标轴标签空间。 */
export const TREND_GRID = { left: 64, right: 16, top: 36, bottom: 32 } as const;
