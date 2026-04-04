import React from "react";
import { Card, CardBody, Skeleton } from "@nextui-org/react";

const Skel = () => {
  return (
    <Card className="profile-skel" radius="lg">
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
};

export default Skel;
