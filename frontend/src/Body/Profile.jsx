import React from "react";
import Skel from "./Skel";
import Templeate from "./Templeate";

const PROFILE_IGNORED_KEYS = new Set(["picture", "id"]);

const Profile = ({ profile }) => {
  if (!profile) {
    return <Skel />;
  }

  const visibleKeys = Object.keys(profile).filter(
    (key) => !PROFILE_IGNORED_KEYS.has(key) && profile[key] !== undefined && profile[key] !== ""
  );

  const columns = visibleKeys.map((key) => ({ key, label: key }));
  const rows = [
    visibleKeys.reduce(
      (accumulator, key) => ({ ...accumulator, key: "profile-row", [key]: profile[key] }),
      {}
    ),
  ];

  return <Templeate columns={columns} rows={rows} emptyMessage="No profile details available." />;
};

export default Profile;
