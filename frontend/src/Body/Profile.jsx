import React, { useMemo } from "react";
import Skel from "./Skel";

const PROFILE_IGNORED_KEYS = new Set(["picture", "id", "Name"]);

const LABEL_ALIASES = {
  "date of birth/age": "Date of birth / age",
  "date of birth / age": "Date of birth / age",
  "date of birth": "Date of birth / age",
  age: "Date of birth / age",
  "place of birth": "Place of birth",
  height: "Height",
  citizenship: "Citizenship",
  nationality: "Citizenship",
  position: "Position",
  foot: "Preferred foot",
  "preferred foot": "Preferred foot",
  "player agent": "Player agent",
  "current club": "Current club",
  joined: "Joined",
  "contract expires": "Contract expires",
  "contract option": "Contract option",
  "on loan from": "On loan from",
  "contract there expires": "Contract there expires",
  outfitter: "Outfitter",
  "social-media": "Social media",
  "social media": "Social media",
};

const KNOWN_LABELS = new Set(Object.values(LABEL_ALIASES));

const normalizeKey = (value = "") =>
  String(value)
    .replace(/:/g, "")
    .replace(/\s+/g, " ")
    .trim()
    .toLowerCase();

const canonicalLabel = (value) => LABEL_ALIASES[normalizeKey(value)] || null;

const formatLooseLabel = (key) =>
  String(key)
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/[-_]/g, " ")
    .replace(/^./, (char) => char.toUpperCase());

const formatValue = (value) => {
  if (value === null || value === undefined) return "";
  return String(value)
    .replace(/\s+/g, " ")
    .replace(/,/g, ".")
    .trim();
};

function mergeValue(current, next) {
  const cleanNext = formatValue(next);
  if (!cleanNext) return current || "";
  if (!current) return cleanNext;
  if (current.toLowerCase().includes(cleanNext.toLowerCase())) return current;
  return `${current}, ${cleanNext}`;
}

function normalizeProfile(profile) {
  const normalized = {};
  let pendingLabel = null;

  Object.entries(profile || {}).forEach(([rawKey, rawValue]) => {
    if (PROFILE_IGNORED_KEYS.has(rawKey)) return;

    const key = formatValue(rawKey);
    const value = formatValue(rawValue);
    if (!key || !value) return;

    const keyLabel = canonicalLabel(key);
    const valueLabel = canonicalLabel(value);

    if (keyLabel) {
      normalized[keyLabel] = mergeValue(normalized[keyLabel], value);
      pendingLabel = keyLabel;
      return;
    }

    if (valueLabel) {
      if (pendingLabel) {
        normalized[pendingLabel] = mergeValue(normalized[pendingLabel], key);
      }
      pendingLabel = valueLabel;
      return;
    }

    if (!KNOWN_LABELS.has(key)) {
      normalized[formatLooseLabel(key)] = mergeValue(normalized[formatLooseLabel(key)], value);
    }
  });

  return normalized;
}

function getField(data, labels) {
  for (const label of labels) {
    if (data[label]) return data[label];
  }
  return "—";
}

function Field({ label, value }) {
  return (
    <div className="profile-detail-field">
      <span>{label}</span>
      <strong>{value || "—"}</strong>
    </div>
  );
}

function ProfileSection({ icon, title, children }) {
  return (
    <section className="profile-section-card">
      <div className="profile-section-heading">
        <span aria-hidden="true">{icon}</span>
        <h3>{title}</h3>
      </div>
      <div className="profile-section-divider" />
      <div className="profile-detail-grid">{children}</div>
    </section>
  );
}

const Profile = ({ profile }) => {
  const data = useMemo(() => normalizeProfile(profile), [profile]);

  if (!profile) {
    return <Skel />;
  }

  const hasDetails = Object.values(data).some(Boolean);

  if (!hasDetails) {
    return <div className="chart-empty">No profile details available.</div>;
  }

  const usedLabels = new Set([
    "Date of birth / age",
    "Place of birth",
    "Height",
    "Citizenship",
    "Position",
    "Preferred foot",
    "Player agent",
    "Current club",
    "On loan from",
    "Joined",
    "Contract expires",
    "Contract there expires",
    "Contract option",
    "Outfitter",
  ]);

  const extraFields = Object.entries(data).filter(
    ([label, value]) => value && !usedLabels.has(label) && !PROFILE_IGNORED_KEYS.has(label)
  );

  return (
    <div className="profile-page">
      <div className="profile-page-header">
        <div>
          <p className="profile-eyebrow">Player profile</p>
          <h2>{profile.Name || "Selected player"}</h2>
          <span>Personal, playing, club, and contract information.</span>
        </div>
      </div>

      <ProfileSection icon="◆" title="Personal Details">
        <Field label="Date of birth / age" value={getField(data, ["Date of birth / age"])} />
        <Field label="Place of birth" value={getField(data, ["Place of birth"])} />
        <Field label="Height" value={getField(data, ["Height"])} />
        <Field label="Citizenship" value={getField(data, ["Citizenship"])} />
      </ProfileSection>

      <ProfileSection icon="◉" title="Playing Profile">
        <Field label="Position" value={getField(data, ["Position"])} />
        <Field label="Preferred foot" value={getField(data, ["Preferred foot"])} />
        <Field label="Player agent" value={getField(data, ["Player agent"])} />
      </ProfileSection>

      <ProfileSection icon="▣" title="Contract & Club">
        <Field label="Current club" value={getField(data, ["Current club"])} />
        <Field label="On loan from" value={getField(data, ["On loan from"])} />
        <Field label="Joined" value={getField(data, ["Joined"])} />
        <Field label="Contract expires" value={getField(data, ["Contract expires"])} />
        <Field label="Contract there expires" value={getField(data, ["Contract there expires"])} />
        <Field label="Contract option" value={getField(data, ["Contract option"])} />
        <Field label="Outfitter" value={getField(data, ["Outfitter"])} />
      </ProfileSection>

      {extraFields.length > 0 && (
        <ProfileSection icon="⋯" title="Additional Details">
          {extraFields.map(([label, value]) => (
            <Field key={label} label={label} value={value} />
          ))}
        </ProfileSection>
      )}
    </div>
  );
};

export default Profile;
