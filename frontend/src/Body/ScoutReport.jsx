import React from "react";
import { Card, CardBody, Chip } from "@nextui-org/react";
import Skel from "./Skel";
import MetricCard from "../components/MetricCard";
import RadarChart from "../components/RadarChart";

function TextList({ title, items = [], tone = "default" }) {
  return (
    <Card className={`report-card report-card-${tone}`}>
      <CardBody>
        <div className="section-title">{title}</div>
        <div className="report-list">
          {items.map((item, index) => (
            <div key={`${item}-${index}`} className="report-list-item">
              <span>{index + 1}</span>
              <p>{item}</p>
            </div>
          ))}
        </div>
      </CardBody>
    </Card>
  );
}

function ScorePill({ label, value, helper }) {
  const safeValue = Math.max(0, Math.min(100, Number(value) || 0));
  return (
    <div className="score-pill">
      <div>
        <strong>{label}</strong>
        {helper && <span>{helper}</span>}
      </div>
      <div className="score-pill-meter">
        <span style={{ width: `${safeValue}%` }} />
      </div>
      <b>{safeValue}/100</b>
    </div>
  );
}

export default function ScoutReport({ profile }) {
  if (!profile) {
    return <Skel />;
  }

  const scouting = profile.scouting || {};
  const summary = profile.summary || {};
  const dataQuality = profile.dataQuality || {};
  const scores = summary.scores || {};
  const scoreLabels = summary.scoreLabels || {};

  return (
    <div className="analytics-stack">
      <div className="analytics-hero-panel report-hero-panel">
        <div>
          <div className="eyebrow">Scouting report</div>
          <h2>{scouting.archetype || "Player report"}</h2>
          <p>{scouting.oneLineVerdict}</p>
        </div>
        <div className="badge-row">
          {(summary.badges || []).map((badge) => (
            <Chip key={badge} color="primary" variant="flat">
              {badge}
            </Chip>
          ))}
        </div>
      </div>

      <div className="metric-grid metric-grid-four">
        <MetricCard label="Overall" value={scores.overall ?? "-"} helper={scoreLabels.overall} />
        <MetricCard label="Productivity" value={scores.productivity ?? "-"} helper={scoreLabels.productivity} />
        <MetricCard label="Availability" value={scores.availability ?? "-"} helper={scoreLabels.availability} />
        <MetricCard label="Data quality" value={dataQuality.score ?? "-"} helper={dataQuality.label} />
      </div>

      <div className="analytics-grid-two">
        <RadarChart data={scouting.radar || []} title="Scouting radar" />
        <Card className="insight-card">
          <CardBody>
            <div className="section-title">Signal breakdown</div>
            <ScorePill label="Output" value={scores.productivity} helper={scoreLabels.productivity} />
            <ScorePill label="Availability" value={scores.availability} helper={scoreLabels.availability} />
            <ScorePill label="Market" value={scores.marketMomentum} helper={scoreLabels.marketMomentum} />
            <ScorePill label="Stability" value={scores.careerStability} helper={scoreLabels.careerStability} />
            <ScorePill label="Discipline" value={scores.discipline} helper={scoreLabels.discipline} />
          </CardBody>
        </Card>
      </div>

      <div className="analytics-grid-three">
        <TextList title="Strengths" items={scouting.strengths || []} tone="good" />
        <TextList title="Risks / questions" items={scouting.risks || []} tone="risk" />
        <TextList title="Next analysis" items={scouting.opportunities || []} tone="idea" />
      </div>

      <Card className="insight-card">
        <CardBody>
          <div className="section-title">Data coverage</div>
          <div className="quality-grid">
            {(dataQuality.checks || []).map((check) => (
              <div className="quality-item" key={check.label}>
                <strong>{check.label}</strong>
                <span>{check.count} records</span>
                <div className="quality-track"><i style={{ width: `${check.score}%` }} /></div>
              </div>
            ))}
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
