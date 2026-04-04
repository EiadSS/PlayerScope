import React from "react";
import Templeate from "./Templeate";
import Skel from "./Skel";

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

  return <Templeate columns={columns} rows={rows} emptyMessage="No transfer history available." />;
};

export default Transfers;
