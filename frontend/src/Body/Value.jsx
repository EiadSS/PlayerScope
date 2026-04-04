import React from "react";
import Templeate from "./Templeate";
import Skel from "./Skel";

const Value = ({ profile }) => {
  if (!profile) {
    return <Skel />;
  }

  const columns = [
    { key: "age", label: "Age" },
    { key: "date", label: "Date" },
    { key: "clubName", label: "Club" },
    { key: "value", label: "Value" },
  ];

  const rows = (profile.result || []).map((item, index) => ({
    key: index + 1,
    age: item.age,
    date: item.date,
    clubName: item.clubName,
    value: item.value,
  }));

  return <Templeate columns={columns} rows={rows} emptyMessage="No market value history available." />;
};

export default Value;
