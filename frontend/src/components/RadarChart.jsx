import React, { useMemo } from "react";

export default function RadarChart({ data = [], title = "Player radar" }) {
  const chart = useMemo(() => {
    const points = data
      .filter((item) => item && item.label)
      .map((item) => ({ label: item.label, value: Math.max(0, Math.min(100, Number(item.value) || 0)) }));

    if (points.length < 3) {
      return null;
    }

    const width = 460;
    const height = 380;
    const centerX = width / 2;
    const centerY = height / 2 + 10;
    const radius = 112;
    const labelDistance = 76;
    const angleStep = (Math.PI * 2) / points.length;

    const rings = [0.25, 0.5, 0.75, 1].map((scale) =>
      points
        .map((_, index) => {
          const angle = -Math.PI / 2 + index * angleStep;
          return `${centerX + Math.cos(angle) * radius * scale},${centerY + Math.sin(angle) * radius * scale}`;
        })
        .join(" ")
    );

    const polygon = points
      .map((item, index) => {
        const angle = -Math.PI / 2 + index * angleStep;
        const scaledRadius = radius * (item.value / 100);
        return `${centerX + Math.cos(angle) * scaledRadius},${centerY + Math.sin(angle) * scaledRadius}`;
      })
      .join(" ");

    const axes = points.map((item, index) => {
      const angle = -Math.PI / 2 + index * angleStep;
      const labelX = centerX + Math.cos(angle) * (radius + labelDistance);
      const labelY = centerY + Math.sin(angle) * (radius + labelDistance);
      return {
        ...item,
        x: centerX + Math.cos(angle) * radius,
        y: centerY + Math.sin(angle) * radius,
        labelX,
        labelY,
        textAnchor: labelX < centerX - 14 ? "end" : labelX > centerX + 14 ? "start" : "middle",
      };
    });

    return { width, height, centerX, centerY, radius, rings, polygon, axes };
  }, [data]);

  if (!chart) {
    return <div className="chart-empty">Not enough radar data yet.</div>;
  }

  return (
    <div className="radar-card radar-card-roomy">
      <div className="chart-header">
        <span>{title}</span>
        <span>0-100 signal score</span>
      </div>
      <svg
        viewBox={`0 0 ${chart.width} ${chart.height}`}
        className="radar-chart"
        role="img"
        aria-label={title}
        preserveAspectRatio="xMidYMid meet"
      >
        {chart.rings.map((ring, index) => (
          <polygon key={index} points={ring} className="radar-ring" />
        ))}
        {chart.axes.map((axis) => (
          <line
            key={axis.label}
            x1={chart.centerX}
            y1={chart.centerY}
            x2={axis.x}
            y2={axis.y}
            className="radar-axis"
          />
        ))}
        <polygon points={chart.polygon} className="radar-shape" />
        {chart.axes.map((axis) => (
          <g key={axis.label}>
            <circle cx={axis.x} cy={axis.y} r="4" className="radar-dot" />
            <text
              x={axis.labelX}
              y={axis.labelY}
              textAnchor={axis.textAnchor}
              dominantBaseline="middle"
              className="radar-label"
            >
              {axis.label}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}
