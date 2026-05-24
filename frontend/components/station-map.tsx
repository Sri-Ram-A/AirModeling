"use client";

import * as React from "react";
import { CircleMarker, MapContainer, Popup, TileLayer, Tooltip } from "react-leaflet";
import { useTheme } from "next-themes";
import type { StationMeta, StationReading } from "@/lib/types";

export function StationMap(props: { stations: StationMeta[]; readings: StationReading[] }) {
  const { theme } = useTheme();

  function findReading(stationName: string): StationReading | undefined {
    return props.readings.find(function (reading) {
      return reading.station_name === stationName;
    });
  }

  function getColor(value: number, min: number, max: number): string {
    const ratio = (value - min) / Math.max(max - min, 1e-6);
    if (ratio > 0.75) return "#dc2626";
    if (ratio > 0.5) return "#f97316";
    if (ratio > 0.25) return "#ca8a04";
    return "#2563eb";
  }

  const values = props.readings.map(function (reading) {
    return reading.pollutant;
  });

  const min = values.length > 0 ? Math.min.apply(null, values) : 0;
  const max = values.length > 0 ? Math.max.apply(null, values) : 1;
  const center: [number, number] = [12.9716, 77.5946];
  const tileUrl = theme === "dark"
    ? "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
    : "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png";

  return (
    <div className="h-[420px] overflow-hidden rounded-2xl border border-border">
      <MapContainer
        center={center}
        zoom={11}
        scrollWheelZoom={false}
        className="h-full w-full"
      >
        <TileLayer
          url={tileUrl}
          attribution='&copy; OpenStreetMap contributors &copy; CARTO'
        />
        {props.stations.map(function (station) {
          const reading = findReading(station.station_name);
          const value = reading?.pollutant ?? 0;
          const color = getColor(value, min, max);

          return (
            <CircleMarker
              key={station.station_name}
              center={[station.latitude, station.longitude]}
              radius={reading ? 10 : 7}
              pathOptions={{ color: color, fillColor: color, fillOpacity: 0.75 }}
            >
              <Tooltip direction="top" offset={[0, -8]} opacity={1} permanent={false}>
                <span>{station.station_name}</span>
              </Tooltip>
              <Popup>
                <div className="grid gap-1">
                  <strong>{station.station_name}</strong>
                  <span>Pollutant: {reading?.pollutant?.toFixed(2) ?? "N/A"}</span>
                  <span>Wind: {reading?.wind_speed?.toFixed(2) ?? "N/A"} m/s</span>
                  <span>Direction: {reading?.wind_direction?.toFixed(1) ?? "N/A"}°</span>
                </div>
              </Popup>
            </CircleMarker>
          );
        })}
      </MapContainer>
    </div>
  );
}
