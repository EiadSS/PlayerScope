import React from "react";
import { Card, CardBody, Chip } from "@nextui-org/react";
import Skel from "./Skel";

const TYPE_LABELS = {
  performance: "Performance",
  market: "Market",
  transfer: "Transfer",
  injury: "Injury",
};

export default function Timeline({ profile }) {
  if (!profile) {
    return <Skel />;
  }

  const events = profile.timeline || [];
  const competitions = profile.competitionProfile?.topCompetitions || [];

  return (
    <div className="analytics-stack">
      <div className="analytics-hero-panel">
        <div>
          <div className="eyebrow">Career timeline</div>
          <h2>Timeline & competition map</h2>
          <p>Combines transfers, market-value peaks, strongest seasons, major injury spells, and production by competition.</p>
        </div>
      </div>

      <div className="analytics-grid-two timeline-layout">
        <Card className="insight-card">
          <CardBody>
            <div className="section-title">Key career events</div>
            <div className="career-timeline">
              {events.length ? events.map((event, index) => (
                <div className={`career-event career-event-${event.type}`} key={`${event.type}-${event.title}-${index}`}>
                  <div className="career-event-marker" />
                  <div>
                    <div className="career-event-top">
                      <Chip size="sm" variant="flat" color={event.type === "injury" ? "warning" : "primary"}>
                        {TYPE_LABELS[event.type] || event.type}
                      </Chip>
                      <span>{event.label}</span>
                    </div>
                    <strong>{event.title}</strong>
                    <p>{event.description}</p>
                  </div>
                </div>
              )) : <div className="chart-empty">No timeline events available yet.</div>}
            </div>
          </CardBody>
        </Card>

        <Card className="insight-card">
          <CardBody>
            <div className="section-title">Competition production share</div>
            <div className="competition-map">
              {competitions.length ? competitions.map((item) => (
                <div className="competition-map-row" key={item.name}>
                  <div>
                    <strong>{item.name}</strong>
                    <span>{item.appearances} apps • {item.goals}G {item.assists}A</span>
                  </div>
                  <div className="competition-share">
                    <i style={{ width: `${Math.max(4, item.share)}%` }} />
                  </div>
                  <b>{item.share}%</b>
                </div>
              )) : <div className="chart-empty">No competition breakdown available.</div>}
            </div>
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
