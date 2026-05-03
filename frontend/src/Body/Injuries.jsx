import React from "react";
import Templeate from "./Templeate";
import Skel from "./Skel";
import MetricCard from "../components/MetricCard";

const Injuries = ({ profile }) => {
  if (!profile) {
    return <Skel />;
  }

  const columns = [
    { key: "Season", label: "Season" },
    { key: "Injury", label: "Injury" },
    { key: "From", label: "From" },
    { key: "Until", label: "Until" },
    { key: "Days", label: "Days" },
    { key: "Games missed", label: "Games missed" },
  ];

  const rows = (profile.body || []).map((item, index) => ({
    key: index + 1,
    Season: item[0],
    Injury: item[1],
    From: item[2],
    Until: item[3],
    Days: item[4],
    "Games missed": item[5],
  }));

  const summary = profile.summary || {};

  return (
    <div className="analytics-stack">
      <div className="metric-grid metric-grid-four">
        <MetricCard label="Listed injuries" value={summary.totalInjuries ?? 0} />
        <MetricCard label="Days out" value={summary.totalDaysOut ?? 0} />
        <MetricCard label="Games missed" value={summary.totalGamesMissed ?? 0} />
        <MetricCard label="Avg. days out" value={summary.averageDaysOut ?? 0} />
      </div>

      {summary.longestInjury && (
        <div className="insight-row">
          <span>Longest absence: <strong>{summary.longestInjury.injury}</strong></span>
          <span>{summary.longestInjury.days} days</span>
          <span>{summary.longestInjury.season}</span>
        </div>
      )}

      <Templeate columns={columns} rows={rows} emptyMessage="No injury history available." />
    </div>
  );
};

export default Injuries;
