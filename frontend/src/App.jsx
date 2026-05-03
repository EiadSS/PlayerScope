import React, { useState } from "react";
import { Chip } from "@nextui-org/react";
import Bar from "./components/Bar";
import PlayerPic from "./components/PlayerPic";
import Nav from "./components/Nav";

export default function App() {
  const [selectedPlayer, setSelectedPlayer] = useState(null);
  const [playerPicture, setPlayerPicture] = useState("");
  const [isSearching, setIsSearching] = useState(false);

  return (
    <div className="page-shell">
      <div className="ambient-grid" />
      <div className="ambient-glow ambient-glow-left" />
      <div className="ambient-glow ambient-glow-right" />
      <div className="ambient-glow ambient-glow-bottom" />

      <div className="page">
        <section className="hero-card hero-card-clean">
          <div className="hero-main hero-main-clean">
            <Chip color="primary" variant="flat" className="hero-chip">
              Player intelligence platform
            </Chip>

            <div className="brand-row" aria-label="PlayerScope brand">
              <div className="brand-mark">PS</div>
              <span>PlayerScope</span>
            </div>

            <h1>Explore football intelligence faster</h1>
            <p className="hero-copy">
              Search players, compare profiles, and review scouting, value, transfer, injury,
              and performance data in one clean dashboard.
            </p>

            <Bar onSearch={setSelectedPlayer} isSearching={isSearching} />

            <div className="home-actions" aria-label="Main features">
              <div className="home-action-card">
                <span>⌕</span>
                <div>
                  <strong>Search Player</strong>
                  <small>Find any player profile</small>
                </div>
              </div>
              <div className="home-action-card">
                <span>⇄</span>
                <div>
                  <strong>Compare Players</strong>
                  <small>Side-by-side analysis</small>
                </div>
              </div>
              <div className="home-action-card">
                <span>▣</span>
                <div>
                  <strong>Scout Report</strong>
                  <small>Signal scores and radar view</small>
                </div>
              </div>
            </div>
          </div>
        </section>

        {selectedPlayer && (
          <section className="content-shell">
            <PlayerPic
              picture={playerPicture}
              isLoading={isSearching}
              playerName={selectedPlayer.name || selectedPlayer.query}
            />
            <Nav
              selectedPlayer={selectedPlayer}
              setPicture={setPlayerPicture}
              setIsSearching={setIsSearching}
            />
          </section>
        )}
      </div>
    </div>
  );
}
