import React, { useMemo } from "react";

function formatShortMoney(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "-";
  }

  const amount = Number(value);
  if (Math.abs(amount) >= 1_000_000_000) {
    return `€${(amount / 1_000_000_000).toFixed(1).replace(".0", "")}b`;
  }
  if (Math.abs(amount) >= 1_000_000) {
    return `€${(amount / 1_000_000).toFixed(1).replace(".0", "")}m`;
  }
  if (Math.abs(amount) >= 1_000) {
    return `€${Math.round(amount / 1_000)}k`;
  }
  return `€${amount}`;
}

export default function LineChart({ data = [], title = "Trend", valueKey = "valueNumber", labelKey = "date" }) {
  const chart = useMemo(() => {
    const points = data
      .map((item, index) => ({
        index,
        label: item[labelKey] || "",
        value: Number(item[valueKey]),
      }))
      .filter((item) => Number.isFinite(item.value));

    if (points.length < 2) {
      return null;
    }

    const width = 640;
    const height = 220;
    const padding = 24;
    const min = Math.min(...points.map((item) => item.value));
    const max = Math.max(...points.map((item) => item.value));
    const spread = max - min || 1;

    const polyline = points
      .map((item, pointIndex) => {
        const x = padding + (pointIndex / (points.length - 1)) * (width - padding * 2);
        const y = height - padding - ((item.value - min) / spread) * (height - padding * 2);
        return `${x},${y}`;
      })
      .join(" ");

    return { points, width, height, polyline, min, max };
  }, [data, labelKey, valueKey]);

  if (!chart) {
    return <div className="chart-empty">Not enough trend data yet.</div>;
  }

  return (
    <div className="chart-card">
      <div className="chart-header">
        <span>{title}</span>
        <span>{formatShortMoney(chart.max)} peak</span>
      </div>
      <svg viewBox={`0 0 ${chart.width} ${chart.height}`} className="line-chart" role="img" aria-label={title}>
        <defs>
          <linearGradient id="chartFill" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopOpacity="0.35" />
            <stop offset="100%" stopOpacity="0.02" />
          </linearGradient>
        </defs>
        <polyline className="line-chart-path" points={chart.polyline} fill="none" />
        {chart.points.map((item, index) => {
          const [x, y] = chart.polyline.split(" ")[index].split(",").map(Number);
          return <circle key={`${item.label}-${index}`} className="line-chart-dot" cx={x} cy={y} r="4" />;
        })}
      </svg>
      <div className="chart-footer">
        <span>{chart.points[0]?.label}</span>
        <span>{chart.points[chart.points.length - 1]?.label}</span>
      </div>
    </div>
  );
}
