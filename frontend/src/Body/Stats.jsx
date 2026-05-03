import React, { useMemo, useState } from "react";
import { Input } from "@nextui-org/react";
import Templeate from "./Templeate";
import Skel from "./Skel";
import MetricCard from "../components/MetricCard";

const Stats = ({ profile }) => {
  const [seasonFilter, setSeasonFilter] = useState("All");
  const [competitionFilter, setCompetitionFilter] = useState("");

  if (!profile) {
    return <Skel />;
  }

  const columns = [
    { key: "Season", label: "Season" },
    { key: "Competition", label: "Competition" },
    { key: "Appearances", label: "Apps" },
    { key: "Goals", label: "Goals" },
    { key: "Assists", label: "Assists" },
    { key: "Yellow Cards", label: "YC" },
    { key: "Red Cards", label: "RC" },
    { key: "Minutes", label: "Minutes" },
  ];

  const rows = (profile.body || []).map((item, index) => ({
    key: index + 1,
    Season: item[0],
    Competition: item[1],
    Appearances: item[2],
    Goals: item[3],
    Assists: item[4],
    "Yellow Cards": item[5],
    "Red Cards": item[6],
    Minutes: item[7],
  }));

  const seasons = useMemo(
    () => ["All", ...Array.from(new Set(rows.map((row) => row.Season).filter(Boolean)))],
    [rows]
  );

  const filteredRows = rows.filter((row) => {
    const matchesSeason = seasonFilter === "All" || row.Season === seasonFilter;
    const matchesCompetition = row.Competition.toLowerCase().includes(competitionFilter.toLowerCase());
    return matchesSeason && matchesCompetition;
  });

  const summary = profile.summary || {};

  return (
    <div className="analytics-stack">
      <div className="metric-grid metric-grid-four">
        <MetricCard label="Appearances" value={summary.appearances ?? 0} />
        <MetricCard label="Goals" value={summary.goals ?? 0} />
        <MetricCard label="Assists" value={summary.assists ?? 0} />
        <MetricCard label="G+A per 90" value={summary.contributionsPer90 ?? "0.00"} />
      </div>

      <div className="filters-row">
        <label>
          Season
          <select value={seasonFilter} onChange={(event) => setSeasonFilter(event.target.value)}>
            {seasons.map((season) => (
              <option key={season} value={season}>{season}</option>
            ))}
          </select>
        </label>
        <Input
          label="Competition filter"
          labelPlacement="outside"
          placeholder="Premier League, Champions League..."
          value={competitionFilter}
          onValueChange={setCompetitionFilter}
        />
      </div>

      <div className="insight-row">
        <span>Best season: <strong>{profile.bestSeason?.name || "-"}</strong></span>
        <span>Top competition: <strong>{profile.topCompetition?.name || "-"}</strong></span>
        <span>Minutes: <strong>{summary.minutesDisplay || "0"}</strong></span>
      </div>

      <Templeate columns={columns} rows={filteredRows} emptyMessage="No stats available for this filter." />
    </div>
  );
};

export default Stats;
