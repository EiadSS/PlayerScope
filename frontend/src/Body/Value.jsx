import React from "react";
import Templeate from "./Templeate";
import Skel from "./Skel";
import LineChart from "../components/LineChart";
import MetricCard from "../components/MetricCard";

const Value = ({ profile }) => {
  if (!profile) {
    return <Skel />;
  }

  const columns = [
    { key: "date", label: "Date" },
    { key: "clubName", label: "Club" },
    { key: "value", label: "Value" },
  ];

  const rows = (profile.result || []).map((item, index) => ({
    key: index + 1,
    date: item.date,
    clubName: item.clubName,
    value: item.value,
  }));

  const summary = profile.summary || {};

  return (
    <div className="analytics-stack">
      <div className="metric-grid metric-grid-four">
        <MetricCard label="Current value" value={summary.currentValue || "-"} />
        <MetricCard label="Peak value" value={summary.peakValue || "-"} helper={summary.peakDate} />
        <MetricCard label="First recorded" value={summary.firstValue || "-"} />
        <MetricCard
          label="Change"
          value={summary.valueChange || "-"}
          helper={summary.valueChangePercent !== null && summary.valueChangePercent !== undefined ? `${summary.valueChangePercent}%` : ""}
        />
      </div>
      <LineChart data={profile.result || []} title="Market value curve" />
      <Templeate columns={columns} rows={rows} emptyMessage="No market value history available." />
    </div>
  );
};

export default Value;
