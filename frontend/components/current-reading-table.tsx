"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { StationReading } from "@/lib/types";

export function CurrentReadingTable(props: {
  readings: StationReading[];
  pollutant: string;
  onSelect: (reading: StationReading) => void;
}) {
  function getTag(value: number): string {
    if (value >= 80) return "High";
    if (value >= 40) return "Moderate";
    return "Low";
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Current station readings</CardTitle>
        <CardDescription>
          Hover a row for quick inspection, or open a station record in the modal.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="overflow-hidden rounded-xl border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Station</TableHead>
                <TableHead className="text-right">{props.pollutant.toUpperCase()}</TableHead>
                <TableHead className="text-right">Wind</TableHead>
                <TableHead className="text-right">Dir</TableHead>
                <TableHead className="text-right">Class</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {props.readings.map(function (reading) {
                return (
                  <TableRow
                    key={reading.station_name}
                    className="cursor-pointer"
                    title="Click to inspect station details"
                    onClick={function () {
                      props.onSelect(reading);
                    }}
                  >
                    <TableCell className="font-medium">{reading.station_name}</TableCell>
                    <TableCell className="text-right">{reading.pollutant.toFixed(2)}</TableCell>
                    <TableCell className="text-right">{reading.wind_speed.toFixed(2)}</TableCell>
                    <TableCell className="text-right">{reading.wind_direction.toFixed(1)}°</TableCell>
                    <TableCell className="text-right">
                      <Badge>{getTag(reading.pollutant)}</Badge>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}
