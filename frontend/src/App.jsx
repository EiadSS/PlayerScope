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
      <div className="ambient-glow ambient-glow-left" />
      <div className="ambient-glow ambient-glow-right" />

      <div className="page">
        <div className="hero-card">
          <Chip color="primary" variant="flat" className="hero-chip">
            Football player search + stats explorer
          </Chip>

          <h1>FootyFinder</h1>
          <p className="hero-copy">
            Search a player and browse their profile, stats, injuries, market value,
            and transfer history in one place.
          </p>

          <Bar onSearch={setSelectedPlayer} isSearching={isSearching} />
        </div>

        {selectedPlayer && (
          <div className="content-shell">
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
          </div>
        )}
      </div>
    </div>
  );
}