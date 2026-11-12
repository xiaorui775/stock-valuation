import { useMemo } from "react";
import ReactECharts from "echarts-for-react";
import type { Bar } from "@/api/types";

/** 近一年收盘价面积图。ECharts 深色主题配色与站点设计令牌一致。 */
export default function PriceChart({
  bars,
  loading,
  height = 320,
}: {
  bars: Bar[];
  loading?: boolean;
  height?: number;
}) {
  const option = useMemo(() => {
    const dates = bars.map((b) => b.date);
    const closes = bars.map((b) => b.close);
    return {
      backgroundColor: "transparent",
      grid: { left: 56, right: 20, top: 20, bottom: 32 },
      tooltip: {
        trigger: "axis",
        backgroundColor: "#1e2740",
        borderColor: "#2a3552",
        textStyle: { color: "#e8ecf5" },
        axisPointer: { type: "cross", label: { backgroundColor: "#2a3552" } },
      },
      xAxis: {
        type: "category",
        data: dates,
        boundaryGap: false,
        axisLine: { lineStyle: { color: "#2a3552" } },
        axisLabel: { color: "#93a0bb", maxTicksLimit: 8 },
      },
      yAxis: {
        type: "value",
        scale: true,
        axisLine: { lineStyle: { color: "#2a3552" } },
        axisLabel: { color: "#93a0bb" },
        splitLine: { lineStyle: { color: "#232c47" } },
      },
      series: [
        {
          name: "收盘价",
          type: "line",
          data: closes,
          showSymbol: false,
          smooth: false,
          lineStyle: { width: 1.6, color: "#f5b942" },
          areaStyle: { color: "rgba(245,185,66,0.12)" },
        },
      ],
    };
  }, [bars]);

  if (loading) return <div className="note py-16 text-center">正在加载图表 …</div>;
  if (bars.length === 0) return <div className="note py-16 text-center">暂无历史数据。</div>;

  return <ReactECharts option={option} style={{ height }} notMerge lazyUpdate />;
}
