import React, { useEffect, useMemo, useState } from "react";
import { Card, CardBody, Skeleton, Snippet, Tab, Tabs } from "@nextui-org/react";
import Profile from "../Body/Profile";
import Stats from "../Body/Stats";
import Transfers from "../Body/Transfers";
import Injuries from "../Body/Injuries";
import Value from "../Body/Value";
import { fetchJson } from "../lib/api";

const TAB_COMPONENTS = {
  Profile,
  Stats,
  Injuries,
  Value,
  Transfers,
};

const TAB_REQUESTS = {
  Profile: null,
  Stats: "stats",
  Injuries: "injuries",
  Value: "value",
  Transfers: "transfers",
};

const TABS = [
  { id: "Profile", label: "Profile" },
  { id: "Stats", label: "Stats" },
  { id: "Injuries", label: "Injuries" },
  { id: "Value", label: "Value" },
  { id: "Transfers", label: "Transfers" },
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

    setLoadingMap((current) => ({ ...current, [tabId]: true }));
    setTabErrors((current) => ({ ...current, [tabId]: "" }));

    try {
      const payload = await fetchJson(`${requestName}/${encodeURIComponent(playerId)}`);
      setDataMap((current) => ({ ...current, [tabId]: payload }));
    } catch (err) {
      setTabErrors((current) => ({
        ...current,
        [tabId]: err.message || `Could not load ${tabId.toLowerCase()}.`,
      }));
    } finally {
      setLoadingMap((current) => ({ ...current, [tabId]: false }));
    }
  };

  const handleSelectionChange = (key) => {
    setActiveTab(key);
    loadTabData(key);
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

    return <Component profile={tabData} />;
  }, [activeTab, dataMap, loadingMap, profile, tabErrors]);

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
      <Tabs
        aria-label="Player sections"
        className="tabs"
        color="primary"
        selectedKey={activeTab}
        onSelectionChange={handleSelectionChange}
      >
        {TABS.map((item) => (
          <Tab key={item.id} title={item.label}>
            {currentContent}
          </Tab>
        ))}
      </Tabs>
    </div>
  );
}