import React from "react";
import Templeate from "./Templeate";
import Skel from "./Skel";
import MetricCard from "../components/MetricCard";

const Transfers = ({ profile }) => {
  if (!profile) {
    return <Skel />;
  }

  const columns = [
    { key: "Season", label: "Season" },
    { key: "Date", label: "Date" },
    { key: "From", label: "From" },
    { key: "To", label: "To" },
    { key: "Market Value", label: "Market Value" },
    { key: "Fee", label: "Fee" },
  ];

  const rows = (profile.body || []).map((item, index) => ({
    key: index + 1,
    Season: item[0],
    Date: item[1],
    From: item[2],
    To: item[3],
    "Market Value": item[4],
    Fee: item[5],
  }));

  const summary = profile.summary || {};

  return (
    <div className="analytics-stack">
      <div className="metric-grid metric-grid-four">
        <MetricCard label="Transfers" value={summary.totalTransfers ?? 0} />
        <MetricCard label="Known fees" value={summary.totalKnownFees || "-"} />
        <MetricCard label="Biggest fee" value={summary.biggestFee || "-"} />
        <MetricCard label="Clubs" value={summary.clubsRepresented ?? 0} />
      </div>

      {summary.latestMove && (
        <div className="insight-row">
          <span>Latest move: <strong>{summary.latestMove.from} → {summary.latestMove.to}</strong></span>
          <span>{summary.latestMove.season}</span>
          <span>{summary.latestMove.fee}</span>
        </div>
      )}

      <Templeate columns={columns} rows={rows} emptyMessage="No transfer history available." />
    </div>
  );
};

export default Transfers;
