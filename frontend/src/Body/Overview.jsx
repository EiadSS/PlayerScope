import React from "react";
import { Card, CardBody, Chip } from "@nextui-org/react";
import Skel from "./Skel";
import LineChart from "../components/LineChart";
import MetricCard from "../components/MetricCard";

function ScoreBar({ label, value }) {
  const safeValue = Math.max(0, Math.min(100, Number(value) || 0));
  return (
    <div className="score-row">
      <div className="score-row-top">
        <span>{label}</span>
        <strong>{safeValue}/100</strong>
      </div>
      <div className="score-track">
        <div className="score-fill" style={{ width: `${safeValue}%` }} />
      </div>
    </div>
  );
}

function SeasonBars({ seasons = [] }) {
  const visible = seasons.slice(0, 8);
  const max = Math.max(...visible.map((item) => item.goalContributions || 0), 1);

  if (!visible.length) {
    return <div className="chart-empty">No season breakdown available.</div>;
  }

  return (
    <div className="bar-chart-card">
      <div className="chart-header">
        <span>Season contribution trend</span>
        <span>Goals + assists</span>
      </div>
      <div className="bar-chart-list">
        {visible.map((item) => (
          <div className="bar-chart-row" key={item.name}>
            <span>{item.name}</span>
            <div className="bar-track">
              <div className="bar-fill" style={{ width: `${((item.goalContributions || 0) / max) * 100}%` }} />
            </div>
            <strong>{item.goalContributions || 0}</strong>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function Overview({ profile }) {
  if (!profile) {
    return <Skel />;
  }

  const summary = profile.summary || {};
  const stats = profile.stats || {};
  const value = profile.value || {};
  const injuries = profile.injuries || {};
  const transfers = profile.transfers || {};
  const dataQuality = profile.dataQuality || {};
  const scouting = profile.scouting || {};

  return (
    <div className="analytics-stack">
      <div className="analytics-hero-panel">
        <div>
          <div className="eyebrow">Player intelligence report</div>
          <h2>{summary.name}</h2>
          <p>
            {[summary.club, summary.position, summary.age ? `${summary.age} years old` : null]
              .filter(Boolean)
              .join(" • ")}
          </p>
        </div>
        <div className="badge-row">
          {(summary.badges || []).map((badge) => (
            <Chip key={badge} color="primary" variant="flat">
              {badge}
            </Chip>
          ))}
        </div>
      </div>

      <div className="metric-grid">
        {(summary.headlineMetrics || []).map((item) => (
          <MetricCard key={item.label} label={item.label} value={item.value} />
        ))}
      </div>

      <div className="analytics-grid-two">
        <Card className="insight-card">
          <CardBody>
            <div className="section-title">Recruiter-demo scores</div>
            <ScoreBar label="Overall" value={summary.scores?.overall} />
            <ScoreBar label="Productivity" value={summary.scores?.productivity} />
            <ScoreBar label="Availability" value={summary.scores?.availability} />
            <ScoreBar label="Market momentum" value={summary.scores?.marketMomentum} />
            <ScoreBar label="Career stability" value={summary.scores?.careerStability} />
            <ScoreBar label="Discipline" value={summary.scores?.discipline} />
          </CardBody>
        </Card>

        <Card className="insight-card">
          <CardBody>
            <div className="section-title">Best signals</div>
            <div className="insight-list">
              <div>
                <strong>{stats.bestSeason?.name || "-"}</strong>
                <span>Best season by goals + assists</span>
              </div>
              <div>
                <strong>{stats.topCompetition?.name || "-"}</strong>
                <span>Top competition by production</span>
              </div>
              <div>
                <strong>{value.summary?.peakValue || "-"}</strong>
                <span>Peak market value {value.summary?.peakDate ? `on ${value.summary.peakDate}` : ""}</span>
              </div>
              <div>
                <strong>{injuries.summary?.longestInjury?.injury || "-"}</strong>
                <span>Longest listed injury spell</span>
              </div>
              <div>
                <strong>{scouting.archetype || "-"}</strong>
                <span>Automated scouting archetype</span>
              </div>
              <div>
                <strong>{dataQuality.label || "-"}</strong>
                <span>Data coverage: {dataQuality.score ?? 0}/100</span>
              </div>
            </div>
          </CardBody>
        </Card>
      </div>

      <div className="analytics-grid-two">
        <LineChart data={value.result || []} title="Market value development" />
        <SeasonBars seasons={stats.seasonBreakdown || []} />
      </div>

      <Card className="insight-card">
        <CardBody>
          <div className="section-title">Career movement snapshot</div>
          <div className="timeline-list">
            {(transfers.body || []).slice(0, 5).map((row, index) => (
              <div className="timeline-item" key={`${row[0]}-${row[1]}-${index}`}>
                <div className="timeline-dot" />
                <div>
                  <strong>{row[2]} → {row[3]}</strong>
                  <span>{[row[0], row[1], row[5]].filter(Boolean).join(" • ")}</span>
                </div>
              </div>
            ))}
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
