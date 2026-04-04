import React from "react";
import Templeate from "./Templeate";
import Skel from "./Skel";

const Stats = ({ profile }) => {
  if (!profile) {
    return <Skel />;
  }

  const columns = [
    { key: "Season", label: "Season" },
    { key: "Competition", label: "Competition" },
    { key: "Appearances", label: "Appearances" },
    { key: "Goals", label: "Goals" },
    { key: "Assists", label: "Assists" },
    { key: "Yellow Cards", label: "Yellow Cards" },
    { key: "Red Cards", label: "Red Cards" },
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

  return <Templeate columns={columns} rows={rows} emptyMessage="No stats available." />;
};

export default Stats;
