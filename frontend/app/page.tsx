"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { format } from "date-fns";
import {
  Activity,
  CalendarDays,
  ChevronDown,
  Droplets,
  Gauge,
  MapPin,
  RefreshCw,
  Thermometer,
  Wind,
} from "lucide-react";
import {
  Map,
  MapMarker,
  MapPopup,
  MapTileLayer,
} from "@/components/ui/map"
import { Badge } from "@/components/ui/badge";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { REQUEST } from "@/lib/request";
import * as types from "@/types"

// Pollutant display metadata
export interface PollutantMeta {
  label: string;
  unit: string;
  key: keyof types.PollutantReadings;
  safeLimit: number; // µg/m³ or ppb threshold for "good"
}

// CONSTANTS
const POLLUTANT_META: PollutantMeta[] = [
  { key: "pm25", label: "PM2.5", unit: "µg/m³", safeLimit: 60 },
  { key: "pm10", label: "PM10", unit: "µg/m³", safeLimit: 100 },
  { key: "no2", label: "NO₂", unit: "µg/m³", safeLimit: 40 },
  { key: "so2", label: "SO₂", unit: "µg/m³", safeLimit: 50 },
  { key: "co", label: "CO", unit: "µg/m³", safeLimit: 1000 },
  { key: "o3", label: "O₃", unit: "µg/m³", safeLimit: 70 },
  { key: "nh3", label: "NH₃", unit: "µg/m³", safeLimit: 40 },
  { key: "benzene", label: "Benzene", unit: "µg/m³", safeLimit: 1 },
];

const BENGALURU_CENTER: [number, number] = [12.97, 77.59];

/* Returns a semantic Tailwind text colour based on AQI value vs safe limit */
function pollutantColour(value: number | null, limit: number): string {
  if (value === null) return "text-muted-foreground";
  if (value === 0) return "text-muted-foreground";
  if (value <= limit * 0.6) return "text-emerald-600 dark:text-emerald-400";
  if (value <= limit) return "text-amber-600 dark:text-amber-400";
  return "text-red-600 dark:text-red-400";
}

/* AQI category label for PM2.5 */
function aqiCategory(pm25: number | null): { label: string; colour: string } {
  if (pm25 === null || pm25 === 0) return { label: "No data", colour: "bg-muted text-muted-foreground" };
  if (pm25 <= 30) return { label: "Good", colour: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300" };
  if (pm25 <= 60) return { label: "Satisfactory", colour: "bg-lime-100 text-lime-800 dark:bg-lime-900/40 dark:text-lime-300" };
  if (pm25 <= 90) return { label: "Moderate", colour: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300" };
  if (pm25 <= 120) return { label: "Poor", colour: "bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-300" };
  return { label: "Severe", colour: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300" };
}

function fmt(val: number | null, decimals = 1): string {
  if (val === null) return "—";
  return val.toFixed(decimals);
}



function PollutantBar({ meta, value }: { meta: PollutantMeta; value: number | null }) {
  const pct = value !== null && value > 0 ? Math.min((value / (meta.safeLimit * 2)) * 100, 100) : 0;
  const colour = pollutantColour(value, meta.safeLimit);

  return (
    <div className="space-y-0.5">
      <div className="flex justify-between items-center border-b p-0.5">
        <span className="text-xs text-muted-foreground">{meta.label}</span>
        <span className={`text-xs font font-semibold ${colour}`}>
          {value !== null ? `${fmt(value)} ${meta.unit}` : "—"}
        </span>
      </div>
    </div>
  );
}

// MAIN PAGE COMPONENT
export default function AQIDashboard() {
  //  1. State 
  const [data, setData] = useState<types.CurrentReadingResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedStation, setSelectedStation] = useState<types.StationSnapshot | null>(null);
  const [selectedDate, setSelectedDate] = useState<Date | undefined>(undefined);
  const [calOpen, setCalOpen] = useState(false);
  const [selectedPollutant, setSelectedPollutant] = useState<keyof types.PollutantReadings>("pm25");
  const [refreshing, setRefreshing] = useState(false);

  //  2. Fetch data 
  async function fetchData(timestamp?: string) {
    try {
      setRefreshing(true);
      const params = timestamp ? `current_reading?timestamp=${encodeURIComponent(timestamp)}` : "current_reading";
      const result = await REQUEST<types.CurrentReadingResponse>("GET", params);
      setData(result);
      // Auto-select first station with data
      const firstValid = result.readings.find((r) => r.pollutants.pm25 !== null);
      setSelectedStation(firstValid ?? result.readings[0] ?? null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load data");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(function initialLoad() {
    fetchData();
  }, []);

  //  3. Click handlers 
  function handleStationSelect(station: types.StationSnapshot) {
    setSelectedStation(station);
  }

  function handleDateSelect(date: Date | undefined) {
    setSelectedDate(date);
    setCalOpen(false);
    if (date) {
      // format to ISO-like string the backend accepts
      const ts = format(date, "yyyy-MM-dd") + " 00:00:00";
      fetchData(ts);
    } else {
      fetchData();
    }
  }

  function handleRefresh() {
    fetchData(selectedDate ? format(selectedDate, "yyyy-MM-dd") + " 00:00:00" : undefined);
  }

  //  4. Derived / memoised values 
  /* Average PM2.5 across stations that have data */
  const avgPm25 = useMemo(() => {
    if (!data) return null;
    const vals = data.readings.map((r) => r.pollutants.pm25).filter((v): v is number => v !== null && v > 0);
    if (!vals.length) return null;
    return vals.reduce((a, b) => a + b, 0) / vals.length;
  }, [data]);

  /* Highest PM2.5 station */
  const worstStation = useMemo(() => {
    if (!data) return null;
    return [...data.readings].sort((a, b) => (b.pollutants.pm25 ?? 0) - (a.pollutants.pm25 ?? 0))[0];
  }, [data]);

  const { label: aqiLabel, colour: aqiColour } = aqiCategory(avgPm25);

  //  5. Render 
  if (loading) {
    return (
      <div className="p-6 space-y-4">
        <Skeleton className="h-10 w-64" />
        <div className="grid grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-24" />)}
        </div>
        <Skeleton className="h-100" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64 text-destructive text-sm">
        Error: {error}
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-background text-foreground overflow-hidden">

      {/*  1. Header  */}
      <header className="flex items-center justify-between px-6 py-3 border-b border-border shrink-0">
        <div className="flex items-center gap-3">
          <Activity className="w-5 h-5 text-primary" />
          <div>
            <h1 className="text-sm font-semibold tracking-tight">Bengaluru AQI Monitor</h1>
            <p className="text-[11px] text-muted-foreground ">
              {data?.timestamp ?? "—"}
            </p>
          </div>
        </div>

        {/* Date picker */}
        <div className="ml-auto">
          <span className={`text-xs font-medium px-2.5 py-1 rounded-sm ${aqiColour}`}>{aqiLabel}</span>
        </div>
        <Popover open={calOpen} onOpenChange={setCalOpen}>
          <PopoverTrigger asChild>
            <button className="flex items-center gap-2 text-xs px-3 py-1.5 border border-border rounded-sm bg-background hover:bg-muted transition-colors">
              <CalendarDays className="w-3.5 h-3.5" />
              {selectedDate ? format(selectedDate, "dd MMM yyyy") : "Live"}
              <ChevronDown className="w-3 h-3 text-muted-foreground" />
            </button>
          </PopoverTrigger>
          <PopoverContent className="w-auto p-0" align="end">
            <Calendar
              mode="single"
              selected={selectedDate}
              onSelect={handleDateSelect}
              disabled={{ after: new Date() }}
              captionLayout="dropdown"
            />
            {selectedDate && (
              <div className="p-2 border-t border-border">
                <button
                  className="w-full text-xs text-muted-foreground hover:text-foreground py-1"
                  onClick={() => handleDateSelect(undefined)}
                >
                  Reset to live
                </button>
              </div>
            )}
          </PopoverContent>
        </Popover>

        {/* Pollutant filter */}
        <Select
          value={selectedPollutant}
          onValueChange={(v) => setSelectedPollutant(v as keyof types.PollutantReadings)}
        >
          <SelectTrigger className="w-28 h-8 text-xs rounded-sm">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {POLLUTANT_META.map((m) => (
              <SelectItem key={m.key} value={m.key} className="text-xs">{m.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        {/* Refresh */}
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              onClick={handleRefresh}
              className="p-1.5 rounded-sm border border-border hover:bg-muted transition-colors"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`} />
            </button>
          </TooltipTrigger>
          <TooltipContent>Refresh data</TooltipContent>
        </Tooltip>
      </header>


      {/*  Main layout  */}
      <div className="flex flex-1 overflow-hidden">

        {/* Left — Station list */}
        <aside className="w-56 border-r border-border overflow-y-auto shrink-0">
          <div className="px-4 py-2 border-b border-border">
            <p className="text-[10px] uppercase tracking-widest text-muted-foreground font-medium">Stations</p>
          </div>
          {data?.readings.map(function renderStation(station) {
            const val = station.pollutants[selectedPollutant] as number | null;
            const meta = POLLUTANT_META.find((m) => m.key === selectedPollutant)!;
            const colour = pollutantColour(val, meta?.safeLimit ?? 60);
            const isActive = selectedStation?.station_name === station.station_name;

            return (
              <button
                key={station.station_name}
                onClick={() => handleStationSelect(station)}
                className={`w-full text-left px-4 py-2.5 border-b border-border/50 transition-colors ${isActive ? "bg-muted" : "hover:bg-muted/50"
                  }`}
              >
                <p className="text-xs font-medium truncate text-foreground">{station.station_name}</p>
                <p className={`text-[11px]  ${colour}`}>
                  {val !== null ? `${fmt(val)} ${meta?.unit ?? ""}` : "No data"}
                </p>
              </button>
            );
          })}
        </aside>

        {/* Centre — Map */}
        <main className="flex-1 relative overflow-hidden">
          <Map
            center={BENGALURU_CENTER}
            zoom={11}
            className="w-full h-full"
          >
            <MapTileLayer />
            {data?.readings.map(function renderMarker(station) {
              const val = station.pollutants[selectedPollutant] as number | null;
              const meta = POLLUTANT_META.find((m) => m.key === selectedPollutant)!;
              const { label } = aqiCategory(station.pollutants.pm25);

              return (
                <MapMarker
                  key={station.station_name}
                  position={[station.latitude, station.longitude]}
                  eventHandlers={{ click: () => handleStationSelect(station) }}
                >
                  <MapPopup>
                    <div className="text-xs space-y-1 min-w-35">
                      <p className="font-semibold">{station.station_name}</p>
                      <p className="text-muted-foreground">{label}</p>
                      <Separator />
                      <p>{meta?.label}: {val !== null ? `${fmt(val)} ${meta?.unit}` : "—"}</p>
                      <p>Temp: {fmt(station.meteorology.average_temperature)}°C</p>
                      <p>Humidity: {fmt(station.meteorology.relative_humidity)}%</p>
                    </div>
                  </MapPopup>
                </MapMarker>
              );
            })}
          </Map>
        </main>

        {/* Right — Station detail */}
        <aside className="w-64 border-l border-border overflow-y-auto shrink-0 flex flex-col">
          {selectedStation ? (
            <>
              {/* Station header */}
              <div className="px-4 py-3 border-b border-border">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="text-xs font-semibold">{selectedStation.station_name}</p>
                    <p className="text-[10px] text-muted-foreground  mt-0.5">
                      {selectedStation.latitude.toFixed(4)}, {selectedStation.longitude.toFixed(4)}
                    </p>
                  </div>
                  <Badge className={`text-[10px] shrink-0 ${aqiCategory(selectedStation.pollutants.pm25).colour} border-0`}>
                    {aqiCategory(selectedStation.pollutants.pm25).label}
                  </Badge>
                </div>
              </div>

              {/* Pollutants */}
              <div className="px-4 py-3 border-b border-border space-y-2.5">
                <p className="text-[10px] uppercase tracking-widest text-muted-foreground font-medium">Pollutants</p>
                {POLLUTANT_META.map(function renderBar(meta) {
                  return (
                    <PollutantBar
                      key={meta.key}
                      meta={meta}
                      value={selectedStation.pollutants[meta.key] as number | null}
                    />
                  );
                })}
                {/* Extra pollutants without bars */}
                <div className="flex justify-between pt-1">
                  <span className="text-xs text-muted-foreground">Toluene</span>
                  <span className="text-xs ">{fmt(selectedStation.pollutants.toluene)} µg/m³</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-xs text-muted-foreground">NOx</span>
                  <span className="text-xs ">{fmt(selectedStation.pollutants.nox)} µg/m³</span>
                </div>
              </div>

              {/* Meteorology */}
              <div className="px-4 py-3">
                <p className="text-[10px] uppercase tracking-widest text-muted-foreground font-medium mb-2">Meteorology</p>
                <MeteoRow label="Temperature" value={`${fmt(selectedStation.meteorology.average_temperature)}°C`} icon={<Thermometer className="w-3 h-3" />} />
                <MeteoRow label="Humidity" value={`${fmt(selectedStation.meteorology.relative_humidity)}%`} icon={<Droplets className="w-3 h-3" />} />
                <MeteoRow label="Wind Speed" value={`${fmt(selectedStation.meteorology.wind_speed)} m/s`} icon={<Wind className="w-3 h-3" />} />
                <MeteoRow label="Wind Dir." value={selectedStation.meteorology.wind_direction !== null ? `${fmt(selectedStation.meteorology.wind_direction, 0)}°` : "—"} icon={<Wind className="w-3 h-3" />} />
                <MeteoRow label="Pressure" value={`${fmt(selectedStation.meteorology.pressure)} hPa`} icon={<Gauge className="w-3 h-3" />} />
                <MeteoRow label="Solar Rad." value={`${fmt(selectedStation.meteorology.solar_radiation)} W/m²`} icon={<Activity className="w-3 h-3" />} />
                <MeteoRow label="Rainfall" value={`${fmt(selectedStation.meteorology.rainfall)} mm`} icon={<Droplets className="w-3 h-3" />} />
              </div>

              <div className="flex flex-col gap-4 px-6 py-4 border-b border-border">
                <div className=" w-full">
                  <StatBadge label="Avg PM2.5" value={avgPm25 !== null ? `${fmt(avgPm25)} µg/m³` : "—"} icon={<Gauge className="w-3.5 h-3.5" />} />
                  <StatBadge label="AQI Level" value={aqiLabel} icon={<Activity className="w-3.5 h-3.5" />} />
                  <StatBadge label="Stations" value={`${data?.stations_in_snapshot ?? 0} / ${data?.total_stations ?? 0}`} icon={<MapPin className="w-3.5 h-3.5" />} />
                  <StatBadge label="Worst Station" value={worstStation?.station_name ?? "—"} icon={<Wind className="w-3.5 h-3.5" />} />
                </div>
              </div>
            </>
          ) : (
            <div className="flex items-center justify-center h-full text-xs text-muted-foreground">
              Select a station
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
// SUBCOMPONENTS
function StatBadge({ label, value, icon }: { label: string; value: string; icon: React.ReactNode }) {
  return (
    <div className="flex items-center gap-2 px-3 py-2 bg-muted/50 border border-border rounded-sm">
      <span className="text-muted-foreground">{icon}</span>
      <div>
        <p className="text-[10px] uppercase tracking-widest text-muted-foreground font-medium">{label}</p>
        <p className="text-sm font-semibold text-foreground leading-tight">{value}</p>
      </div>
    </div>
  );
}

function MeteoRow({ label, value, icon }: { label: string; value: string; icon: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between py-1.5">
      <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
        {icon} {label}
      </span>
      <span className="text-xs  font-medium text-foreground">{value}</span>
    </div>
  );
}