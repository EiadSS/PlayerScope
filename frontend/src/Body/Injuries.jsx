import React from "react";
import Templeate from "./Templeate";
import Skel from "./Skel";

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

  return <Templeate columns={columns} rows={rows} emptyMessage="No injury history available." />;
};

export default Injuries;
