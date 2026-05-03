import React from "react";
import { Card, CardBody, Image, Skeleton } from "@nextui-org/react";

export default function PlayerPic({ picture, isLoading, playerName }) {
  return (
    <Card className="player-card">
      <CardBody className="player-card-body">
        <div className="player-card-label">Selected player</div>
        {isLoading ? (
          <Skeleton className="player-pic-skeleton rounded-3xl">
            <div className="player-pic" />
          </Skeleton>
        ) : picture ? (
          <Image
            alt={playerName ? `${playerName} portrait` : "Player portrait"}
            src={picture}
            className="player-pic"
            radius="lg"
            isZoomed
          />
        ) : (
          <div className="player-placeholder">
            {playerName?.slice(0, 2)?.toUpperCase() || "PF"}
          </div>
        )}
        <div className="player-nameplate">
          <span>{playerName || "Player"}</span>
          <small>Profile image</small>
        </div>
      </CardBody>
    </Card>
  );
}
