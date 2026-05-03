import React from "react";
import { Card, CardBody } from "@nextui-org/react";

export default function MetricCard({ label, value, helper, accent }) {
  return (
    <Card className={`metric-card ${accent ? `metric-card-${accent}` : ""}`}>
      <CardBody>
        <div className="metric-label">{label}</div>
        <div className="metric-value">{value ?? "-"}</div>
        {helper && <div className="metric-helper">{helper}</div>}
      </CardBody>
    </Card>
  );
}
