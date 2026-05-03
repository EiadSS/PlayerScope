import React, { useState } from "react";
import { Button, Card, CardBody, Input, Snippet, Spinner } from "@nextui-org/react";
import { fetchJson } from "../lib/api";

function initials(name = "") {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("") || "PL";
}

function PlayerPanel({ label, player, fallbackName, tone = "green" }) {
  const summary = player?.summary || {};
  const profile = player?.profile || {};
  const name = summary.name || profile.Name || fallbackName || "Select player";
  const meta = [summary.club || profile["Current club"], summary.position || profile.Position, summary.age ? `${summary.age} yrs` : null]
    .filter(Boolean)
    .join(" • ");

  return (
    <div className={`compare-select-card compare-select-card-${tone}`}>
      <div className="compare-select-topline">
        <span>{label}</span>
        {player && <b>Selected</b>}
      </div>
      <div className="compare-selected-player">
        <div className="compare-avatar">{initials(name)}</div>
        <div>
          <strong>{name}</strong>
          <small>{meta || "Current search profile"}</small>
        </div>
      </div>
    </div>
  );
}

function MetricComparison({ metric }) {
  return (
    <div className="compare-metric-row clean">
      <div className={metric.winner === "left" ? "metric-winner" : ""}>{metric.left || "—"}</div>
      <div>
        <span>{metric.label}</span>
        {metric.winner === "tie" ? <small>Even</small> : <small>{metric.winner === "left" ? "Left leads" : "Right leads"}</small>}
      </div>
      <div className={metric.winner === "right" ? "metric-winner" : ""}>{metric.right || "—"}</div>
    </div>
  );
}

export default function Compare({ playerId, selectedPlayer }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [comparison, setComparison] = useState(null);
  const [selectedComparisonPlayer, setSelectedComparisonPlayer] = useState(null);
  const [isSearching, setIsSearching] = useState(false);
  const [isComparing, setIsComparing] = useState(false);
  const [error, setError] = useState("");

  const searchPlayers = async () => {
    const trimmed = query.trim();
    if (!trimmed) {
      setError("Enter another player to compare.");
      return;
    }

    setError("");
    setIsSearching(true);
    setResults([]);

    try {
      const payload = await fetchJson(`search/${encodeURIComponent(trimmed)}`);
      setResults((payload.results || []).filter((player) => String(player.id) !== String(playerId)));
    } catch (err) {
      setError(err.message || "Could not search players.");
    } finally {
      setIsSearching(false);
    }
  };

  const compareTo = async (player) => {
    if (!playerId || !player?.id) {
      setError("Missing player id for comparison.");
      return;
    }

    setError("");
    setIsComparing(true);
    setComparison(null);
    setSelectedComparisonPlayer(player);

    try {
      const payload = await fetchJson(`compare/${encodeURIComponent(playerId)}/${encodeURIComponent(player.id)}`);
      setComparison(payload);
      setResults([]);
      setQuery(player.name);
    } catch (err) {
      setError(err.message || "Could not compare these players.");
    } finally {
      setIsComparing(false);
    }
  };

  return (
    <div className="compare-page">
      <div className="compare-page-header">
        <p className="profile-eyebrow">Player comparison</p>
        <h2>Compare Players</h2>
        <span>Search for another player and compare the key signals side by side.</span>
      </div>

      <Card className="compare-setup-card">
        <CardBody>
          <div className="compare-setup-grid">
            <PlayerPanel
              label="Player 1"
              fallbackName={selectedPlayer?.name || selectedPlayer?.query}
              player={comparison?.left || { summary: { name: selectedPlayer?.name || selectedPlayer?.query } }}
              tone="green"
            />

            <div className="compare-swap" aria-hidden="true">⇄</div>

            <div className="compare-right-stack">
              <PlayerPanel
                label="Player 2"
                fallbackName={selectedComparisonPlayer?.name || "Search for a player"}
                player={comparison?.right || (selectedComparisonPlayer ? { summary: selectedComparisonPlayer } : null)}
                tone="blue"
              />

              <div className="compare-search-row clean">
                <Input
                  aria-label="Compare with"
                  placeholder="Search a player... e.g. Bukayo Saka"
                  value={query}
                  onValueChange={setQuery}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") {
                      searchPlayers();
                    }
                  }}
                />
                <Button color="primary" onClick={searchPlayers} isLoading={isSearching}>
                  Find player
                </Button>
              </div>
            </div>
          </div>

          {error && (
            <Snippet hideSymbol hideCopyButton variant="flat" color="danger" className="mt-4">
              {error}
            </Snippet>
          )}

          {results.length > 0 && (
            <div className="compare-results clean">
              {results.slice(0, 5).map((player) => (
                <button key={player.id} type="button" onClick={() => compareTo(player)}>
                  <span>{player.name}</span>
                  <small>{[player.club, player.position, player.marketValue].filter(Boolean).join(" • ")}</small>
                </button>
              ))}
            </div>
          )}
        </CardBody>
      </Card>

      {isComparing && (
        <div className="center-loading">
          <Spinner />
          <span>Building comparison...</span>
        </div>
      )}

      {comparison && (
        <Card className="compare-summary-card">
          <CardBody>
            <div className="section-title">Comparison Summary</div>
            <div className="compare-metric-list clean">
              {(comparison.metrics || []).map((metric) => (
                <MetricComparison key={metric.label} metric={metric} />
              ))}
            </div>
          </CardBody>
        </Card>
      )}
    </div>
  );
}
