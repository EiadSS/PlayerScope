import React, { useEffect, useMemo, useState } from "react";
import { Card, CardBody, Skeleton, Snippet } from "@nextui-org/react";
import Profile from "../Body/Profile";
import Overview from "../Body/Overview";
import Stats from "../Body/Stats";
import Transfers from "../Body/Transfers";
import Injuries from "../Body/Injuries";
import Value from "../Body/Value";
import Compare from "../Body/Compare";
import ScoutReport from "../Body/ScoutReport";
import Timeline from "../Body/Timeline";
import MarketLab from "../Body/MarketLab";
import { fetchJson } from "../lib/api";

const TAB_COMPONENTS = {
  Profile,
  Overview,
  Stats,
  Injuries,
  Value,
  Transfers,
  Compare,
  ScoutReport,
  Timeline,
  MarketLab,
};

const TAB_REQUESTS = {
  Profile: null,
  Overview: "analytics",
  Stats: "stats",
  Injuries: "injuries",
  Value: "value",
  Transfers: "transfers",
  Compare: null,
  ScoutReport: "analytics",
  Timeline: "analytics",
  MarketLab: "analytics",
};

const TABS = [
  { id: "Overview", label: "Overview", icon: "⌂" },
  { id: "Profile", label: "Profile", icon: "👤" },
  { id: "Stats", label: "Stats", icon: "▥" },
  { id: "ScoutReport", label: "Scout Report", icon: "▤" },
  { id: "Compare", label: "Compare", icon: "⇄" },
  { id: "Transfers", label: "Transfers", icon: "↔" },
  { id: "Value", label: "Value", icon: "€" },
  { id: "Injuries", label: "Injuries", icon: "+" },
  { id: "Timeline", label: "Timeline", icon: "◷" },
  { id: "MarketLab", label: "Market Lab", icon: "◇" },
];

export default function Nav({ selectedPlayer, setIsSearching, setPicture }) {
  const [activeTab, setActiveTab] = useState("Profile");
  const [profile, setProfile] = useState(null);
  const [dataMap, setDataMap] = useState({});
  const [loadingMap, setLoadingMap] = useState({ Profile: false });
  const [tabErrors, setTabErrors] = useState({});
  const [fatalError, setFatalError] = useState("");

  const playerId = selectedPlayer?.id || profile?.id;

  useEffect(() => {
    const controller = new AbortController();

    async function loadProfile() {
      setActiveTab("Profile");
      setProfile(null);
      setDataMap({});
      setLoadingMap({ Profile: true });
      setTabErrors({});
      setFatalError("");
      setPicture("");
      setIsSearching(true);

      try {
        const path = selectedPlayer?.id
          ? `profile-by-id/${encodeURIComponent(selectedPlayer.id)}`
          : `profile/${encodeURIComponent(selectedPlayer.query || selectedPlayer.name)}`;

        const payload = await fetchJson(path, {
          signal: controller.signal,
        });

        setProfile(payload);
        setDataMap({ Profile: payload });
        setPicture(payload.picture || "");
      } catch (err) {
        if (err.name !== "AbortError") {
          setFatalError(err.message || "Player not found.");
        }
      } finally {
        setLoadingMap({ Profile: false });
        setIsSearching(false);
      }
    }

    if (selectedPlayer) {
      loadProfile();
    }

    return () => controller.abort();
  }, [selectedPlayer, setIsSearching, setPicture]);

  const loadTabData = async (tabId) => {
    if (!playerId || tabId === "Profile" || dataMap[tabId] || loadingMap[tabId]) {
      return;
    }

    const requestName = TAB_REQUESTS[tabId];
    if (!requestName) {
      return;
    }

    const sharedEntry = Object.entries(TAB_REQUESTS).find(
      ([key, value]) => value === requestName && dataMap[key]
    );

    if (sharedEntry) {
      setDataMap((current) => ({ ...current, [tabId]: dataMap[sharedEntry[0]] }));
      return;
    }

    setLoadingMap((current) => ({ ...current, [tabId]: true }));
    setTabErrors((current) => ({ ...current, [tabId]: "" }));

    try {
      const payload = await fetchJson(`${requestName}/${encodeURIComponent(playerId)}`);
      setDataMap((current) => {
        const updated = { ...current, [tabId]: payload };
        Object.entries(TAB_REQUESTS).forEach(([key, value]) => {
          if (value === requestName) {
            updated[key] = payload;
          }
        });
        return updated;
      });
    } catch (err) {
      setTabErrors((current) => ({
        ...current,
        [tabId]: err.message || `Could not load ${tabId.toLowerCase()}.`,
      }));
    } finally {
      setLoadingMap((current) => ({ ...current, [tabId]: false }));
    }
  };

  const handleSelectionChange = (tabId) => {
    setActiveTab(tabId);
    loadTabData(tabId);
  };

  const currentContent = useMemo(() => {
    const Component = TAB_COMPONENTS[activeTab];
    if (!Component) {
      return null;
    }

    const isLoading = loadingMap[activeTab];
    const tabData = activeTab === "Profile" ? profile : dataMap[activeTab];
    const tabError = tabErrors[activeTab];

    if (isLoading) {
      return (
        <Card className="tab-loading-card">
          <CardBody>
            <Skeleton className="rounded-lg">
              <div className="h-10 rounded-lg bg-default-300" />
            </Skeleton>
            <div className="space-y-3 mt-4">
              <Skeleton className="w-full rounded-lg">
                <div className="h-5 w-full rounded-lg bg-default-200" />
              </Skeleton>
              <Skeleton className="w-full rounded-lg">
                <div className="h-5 w-full rounded-lg bg-default-200" />
              </Skeleton>
              <Skeleton className="w-full rounded-lg">
                <div className="h-5 w-full rounded-lg bg-default-200" />
              </Skeleton>
            </div>
          </CardBody>
        </Card>
      );
    }

    if (tabError) {
      return (
        <Snippet hideSymbol hideCopyButton variant="flat" color="danger">
          {tabError}
        </Snippet>
      );
    }

    return (
      <Component
        profile={tabData}
        playerId={playerId}
        selectedPlayer={selectedPlayer}
      />
    );
  }, [activeTab, dataMap, loadingMap, playerId, profile, selectedPlayer, tabErrors]);

  if (fatalError) {
    return (
      <div className="info-shell">
        <Snippet hideSymbol hideCopyButton variant="flat" color="danger">
          {fatalError}
        </Snippet>
      </div>
    );
  }

  if (!profile && loadingMap.Profile) {
    return <div className="info-shell">{currentContent}</div>;
  }

  if (!profile) {
    return null;
  }

  return (
    <div className="info-shell">
      <nav className="player-tabs" aria-label="Player sections">
        {TABS.map((item) => {
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              type="button"
              className={`player-tab ${isActive ? "player-tab-active" : ""}`}
              onClick={() => handleSelectionChange(item.id)}
              aria-current={isActive ? "page" : undefined}
            >
              <span className="player-tab-icon" aria-hidden="true">{item.icon}</span>
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      <div className="player-tab-panel">
        {currentContent}
      </div>
    </div>
  );
}
