import React from "react";
import { Card, CardBody, Chip } from "@nextui-org/react";
import Skel from "./Skel";
import LineChart from "../components/LineChart";
import MetricCard from "../components/MetricCard";

export default function MarketLab({ profile }) {
  if (!profile) {
    return <Skel />;
  }

  const value = profile.value || {};
  const analysis = profile.valueAnalysis || {};
  const summary = value.summary || {};

  return (
    <div className="analytics-stack">
      <div className="analytics-hero-panel">
        <div>
          <div className="eyebrow">Market value lab</div>
          <h2>{analysis.trendLabel || "Market analysis"}</h2>
          <p>{analysis.volatilityLabel || "Value trend"} • Current value is {analysis.currentPercentOfPeak || 0}% of peak valuation.</p>
        </div>
        <div className="badge-row">
          <Chip color="primary" variant="flat">Latest move {analysis.latestMove || "-"}</Chip>
          <Chip color="primary" variant="flat">Volatility {analysis.volatilityPercent ?? 0}%</Chip>
        </div>
      </div>

      <div className="metric-grid metric-grid-four">
        <MetricCard label="Current" value={summary.currentValue || "-"} />
        <MetricCard label="Peak" value={summary.peakValue || "-"} helper={summary.peakDate} />
        <MetricCard label="Change since first" value={summary.valueChange || "-"} helper={summary.valueChangePercent !== null && summary.valueChangePercent !== undefined ? `${summary.valueChangePercent}%` : ""} />
        <MetricCard label="Latest movement" value={analysis.latestMove || "-"} helper={analysis.latestMovePercent !== null && analysis.latestMovePercent !== undefined ? `${analysis.latestMovePercent}%` : ""} />
      </div>

      <LineChart data={value.result || []} title="Valuation curve" />

      <div className="analytics-grid-two">
        <Card className="insight-card">
          <CardBody>
            <div className="section-title">Valuation range</div>
            <div className="value-range-list">
              {(analysis.range || []).map((item) => (
                <div key={item.label}>
                  <span>{item.label}</span>
                  <strong>{item.value}</strong>
                </div>
              ))}
            </div>
          </CardBody>
        </Card>

        <Card className="insight-card">
          <CardBody>
            <div className="section-title">Scenario cards</div>
            <div className="scenario-grid">
              {(analysis.scenarioCards || []).map((card) => (
                <div className="scenario-card" key={card.label}>
                  <span>{card.label}</span>
                  <strong>{card.value}</strong>
                  <small>{card.note}</small>
                </div>
              ))}
            </div>
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
