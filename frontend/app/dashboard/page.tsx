"use client";
// frontend/pages/dashboard.tsx
/**
 * Dashboard Page — Station Readings
 *
 * Shows latest air quality readings per station on a map + table.
 * Uses a calendar to pick a date and a pollutant selector.
 * Each section is independently data-driven via the REQUEST helper.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import { useTheme } from "next-themes";
import { format } from "date-fns";
import {
  Wind, Thermometer, Droplets, Sun,
  RefreshCw, CalendarDays, ChevronDown,
  AlertCircle, Moon, SunMedium, Gauge,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Badge } from "@/components/ui/badge";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Separator } from "@/components/ui/separator";
import { REQUEST } from "@/lib/request";

// ─── Types (self-contained, no external import needed) ───────────────────────
type StationRow = {
  time: string; station_name: string;
  latitude: number | null; longitude: number | null;
  pm25: number | null; pm10: number | null; no: number | null;
  no2: number | null; nox: number | null; nh3: number | null;
  so2: number | null; co: number | null; o3: number | null;
  benzene: number | null; toluene: number | null;
  average_temperature: number | null; relative_humidity: number | null;
  wind_speed: number | null; wind_direction: number | null;
  solar_radiation: number | null; pressure: number | null;
  rainfall: number | null; total_rainfall: number | null;
  site: string | number | null; org: string | null;
};

type PollutantKey =
  "pm25" | "pm10" | "no" | "no2" | "nox" |
  "nh3" | "so2" | "co" | "o3" | "benzene" | "toluene";

const POLLUTANT_LABELS: Record<PollutantKey, string> = {
  pm25: "PM2.5", pm10: "PM10", no: "NO", no2: "NO₂",
  nox: "NOₓ", nh3: "NH₃", so2: "SO₂", co: "CO",
  o3: "O₃", benzene: "Benzene", toluene: "Toluene",
};

const POLLUTANT_UNIT: Record<PollutantKey, string> = {
  pm25: "µg/m³", pm10: "µg/m³", no: "µg/m³", no2: "µg/m³",
  nox: "µg/m³", nh3: "µg/m³", so2: "µg/m³", co: "mg/m³",
  o3: "µg/m³", benzene: "µg/m³", toluene: "µg/m³",
};

// ─── Map (dynamic import — Leaflet requires browser) ─────────────────────────

const Map = dynamic(
  () => import("@/components/ui/map").then((m) => m.Map),
  { ssr: false, loading: () => <Skeleton className="h-full w-full" /> }
);
const MapTileLayer = dynamic(
  () => import("@/components/ui/map").then((m) => m.MapTileLayer),
  { ssr: false }
);
const MapMarker = dynamic(
  () => import("@/components/ui/map").then((m) => m.MapMarker),
  { ssr: false }
);
const MapPopup = dynamic(
  () => import("@/components/ui/map").then((m) => m.MapPopup),
  { ssr: false }
);
const MapZoomControl = dynamic(
  () => import("@/components/ui/map").then((m) => m.MapZoomControl),
  { ssr: false }
);

// ─── Helpers ─────────────────────────────────────────────────────────────────

function fmt(val: number | null | undefined): string {
  if (val === null || val === undefined) return "—";
  if (isNaN(val as number)) return "NaN";
  return Number(val).toFixed(2);
}

function getPollutantColor(val: number | null, key: PollutantKey): string {
  // Very rough AQI-like colouring for PM2.5; others get neutral
  if (val === null || isNaN(val)) return "text-muted-foreground";
  if (key === "pm25") {
    if (val < 12)  return "text-emerald-600 dark:text-emerald-400";
    if (val < 35)  return "text-yellow-600 dark:text-yellow-400";
    if (val < 55)  return "text-orange-600 dark:text-orange-400";
    return "text-red-600 dark:text-red-400";
  }
  return "text-foreground";
}

// ─── Component ───────────────────────────────────────────────────────────────

export default function DashboardPage() {
  // 1. State: data + loading/error
  const [rows, setRows]           = useState<StationRow[]>([]);
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState<string | null>(null);

  // 2. State: filters
  const [selectedDate, setSelectedDate]       = useState<Date | undefined>(undefined);
  const [selectedPollutant, setSelectedPollutant] = useState<PollutantKey>("pm25");
  const [selectedStation, setSelectedStation] = useState<string | null>(null);

  // 3. Theme toggle
  const { theme, setTheme } = useTheme();

  // ── Fetch current reading ────────────────────────────────────────────────

  async function fetchData(date?: Date, pollutant?: PollutantKey) {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (date)      params.set("timestamp", format(date, "yyyy-MM-dd"));
      if (pollutant) params.set("pollutant", pollutant);

      const data = await REQUEST<StationRow[]>(
        "GET",
        `dashboard/current_reading?${params.toString()}`
      );
      setRows(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load data.");
    } finally {
      setLoading(false);
    }
  }

  // ── Initial load ─────────────────────────────────────────────────────────

  useEffect(function onMount() {
    fetchData(undefined, selectedPollutant);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Handler: date pick from calendar ─────────────────────────────────────

  function handleDateSelect(date: Date | undefined) {
    setSelectedDate(date);
    fetchData(date, selectedPollutant);
  }

  // ── Handler: pollutant change ─────────────────────────────────────────────

  function handlePollutantChange(value: string) {
    const p = value as PollutantKey;
    setSelectedPollutant(p);
    fetchData(selectedDate, p);
  }

  // ── Handler: refresh ─────────────────────────────────────────────────────

  function handleRefresh() {
    fetchData(selectedDate, selectedPollutant);
  }

  // ── Derived: selected station detail row ──────────────────────────────────

  const detailRow = useMemo(
    () => rows.find((r) => r.station_name === selectedStation) ?? null,
    [rows, selectedStation]
  );

  // ── Derived: map center from data ─────────────────────────────────────────

  const mapCenter = useMemo((): [number, number] => {
    const valid = rows.filter((r) => r.latitude && r.longitude);
    if (!valid.length) return [20.5937, 78.9629]; // India default
    const lat = valid.reduce((s, r) => s + r.latitude!, 0) / valid.length;
    const lon = valid.reduce((s, r) => s + r.longitude!, 0) / valid.length;
    return [lat, lon];
  }, [rows]);

  // ─── Render ───────────────────────────────────────────────────────────────

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background text-foreground">

      {/* ── Sidebar ────────────────────────────────────────────────────── */}
      <aside className="flex w-56 flex-col border-r border-border bg-card px-3 py-5 gap-4">
        {/* Logo */}
        <div className="flex items-center gap-2 px-1 mb-2">
          <Gauge className="h-5 w-5 text-primary" />
          <span className="font-semibold tracking-tight text-sm">AirWatch</span>
        </div>

        <Separator />

        {/* Pollutant selector */}
        <div className="flex flex-col gap-1.5">
          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider px-1">
            Pollutant
          </span>
          <Select value={selectedPollutant} onValueChange={handlePollutantChange}>
            <SelectTrigger className="h-8 text-xs rounded-sm">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {(Object.keys(POLLUTANT_LABELS) as PollutantKey[]).map((k) => (
                <SelectItem key={k} value={k} className="text-xs">
                  {POLLUTANT_LABELS[k]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Calendar date picker */}
        <div className="flex flex-col gap-1.5">
          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider px-1">
            Date
          </span>
          <Popover>
            <PopoverTrigger asChild>
              <Button variant="outline" size="sm" className="justify-start text-xs h-8 rounded-sm font-normal">
                <CalendarDays className="h-3.5 w-3.5 mr-1.5" />
                {selectedDate ? format(selectedDate, "dd MMM yyyy") : "Latest"}
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-0" align="start">
              <Calendar
                mode="single"
                selected={selectedDate}
                onSelect={handleDateSelect}
                disabled={{ after: new Date() }}
              />
              {selectedDate && (
                <div className="p-2 border-t">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="w-full text-xs h-7"
                    onClick={() => handleDateSelect(undefined)}
                  >
                    Clear — use latest
                  </Button>
                </div>
              )}
            </PopoverContent>
          </Popover>
        </div>

        <Separator />

        {/* Station list */}
        <div className="flex flex-col gap-1 flex-1 overflow-y-auto min-h-0">
          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider px-1 mb-1">
            Stations
          </span>
          {loading
            ? Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-6 w-full rounded-sm" />
              ))
            : rows.map((r) => (
                <button
                  key={r.station_name}
                  onClick={() => setSelectedStation(
                    selectedStation === r.station_name ? null : r.station_name
                  )}
                  className={[
                    "text-left px-2 py-1 text-xs rounded-sm transition-colors",
                    selectedStation === r.station_name
                      ? "bg-primary text-primary-foreground"
                      : "hover:bg-accent text-foreground",
                  ].join(" ")}
                >
                  {r.station_name}
                </button>
              ))}
        </div>

        <Separator />

        {/* Bottom actions */}
        <div className="flex flex-col gap-2">
          <Button
            variant="outline"
            size="sm"
            className="h-8 text-xs rounded-sm"
            onClick={handleRefresh}
            disabled={loading}
          >
            <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="h-8 text-xs rounded-sm"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          >
            {theme === "dark"
              ? <><SunMedium className="h-3.5 w-3.5 mr-1.5" />Light mode</>
              : <><Moon className="h-3.5 w-3.5 mr-1.5" />Dark mode</>
            }
          </Button>
        </div>
      </aside>

      {/* ── Main content ───────────────────────────────────────────────── */}
      <main className="flex flex-col flex-1 overflow-hidden">

        {/* Header bar */}
        <header className="flex items-center justify-between px-5 py-3 border-b border-border bg-card">
          <div>
            <h1 className="text-sm font-semibold tracking-tight">
              Air Quality — {POLLUTANT_LABELS[selectedPollutant]}
            </h1>
            <p className="text-xs text-muted-foreground mt-0.5">
              {rows.length > 0
                ? `${rows.length} stations · ${rows[0].time}`
                : "No data loaded"}
            </p>
          </div>
          {error && (
            <div className="flex items-center gap-1.5 text-xs text-destructive">
              <AlertCircle className="h-4 w-4" />
              {error}
            </div>
          )}
        </header>

        {/* Body: map + detail + table */}
        <div className="flex flex-1 overflow-hidden">

          {/* Left: Map */}
          <div className="flex flex-col flex-1 overflow-hidden">

            {/* Map panel */}
            <div className="relative flex-1 min-h-0 border-b border-border">
              {loading
                ? <Skeleton className="h-full w-full" />
                : (
                  <Map
                    center={mapCenter}
                    zoom={10}
                    className="h-full w-full"
                    style={{ zIndex: 0 }}
                  >
                    <MapTileLayer />
                    <MapZoomControl position="bottomright" />
                    {rows
                      .filter((r) => r.latitude && r.longitude)
                      .map((r) => (
                        <MapMarker
                          key={r.station_name}
                          position={[r.latitude!, r.longitude!]}
                        >
                          <MapPopup>
                            <div className="text-xs space-y-1 min-w-[140px]">
                              <p className="font-semibold">{r.station_name}</p>
                              <p>
                                {POLLUTANT_LABELS[selectedPollutant]}:{" "}
                                <span className="font-medium">
                                  {fmt(r[selectedPollutant])} {POLLUTANT_UNIT[selectedPollutant]}
                                </span>
                              </p>
                              <p className="text-muted-foreground">{r.time}</p>
                            </div>
                          </MapPopup>
                        </MapMarker>
                      ))}
                  </Map>
                )}
            </div>

            {/* Station detail strip (shown when station selected) */}
            {detailRow && (
              <div className="flex items-center gap-6 px-5 py-3 bg-card border-b border-border text-xs overflow-x-auto shrink-0">
                <span className="font-semibold text-sm shrink-0">{detailRow.station_name}</span>
                <Separator orientation="vertical" className="h-4" />
                {[
                  { icon: <Thermometer className="h-3.5 w-3.5" />, label: "Temp", val: `${fmt(detailRow.average_temperature)} °C` },
                  { icon: <Droplets className="h-3.5 w-3.5" />, label: "Humidity", val: `${fmt(detailRow.relative_humidity)} %` },
                  { icon: <Wind className="h-3.5 w-3.5" />, label: "Wind", val: `${fmt(detailRow.wind_speed)} m/s · ${fmt(detailRow.wind_direction)}°` },
                  { icon: <Sun className="h-3.5 w-3.5" />, label: "Solar", val: `${fmt(detailRow.solar_radiation)} W/m²` },
                ].map(({ icon, label, val }) => (
                  <div key={label} className="flex items-center gap-1.5 shrink-0 text-muted-foreground">
                    {icon}
                    <span>{label}:</span>
                    <span className="text-foreground font-medium">{val}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Right: Data table */}
          <div className="w-[440px] flex flex-col border-l border-border overflow-hidden shrink-0">
            <div className="px-4 py-2.5 border-b border-border bg-card flex items-center justify-between">
              <span className="text-xs font-medium">Station Readings</span>
              <Badge variant="outline" className="text-xs rounded-sm">
                {selectedPollutant.toUpperCase()}
              </Badge>
            </div>
            <div className="flex-1 overflow-y-auto">
              <Table>
                <TableHeader>
                  <TableRow className="hover:bg-transparent">
                    <TableHead className="text-xs h-8 w-[180px]">Station</TableHead>
                    <TableHead className="text-xs h-8 text-right">
                      {POLLUTANT_LABELS[selectedPollutant]}
                    </TableHead>
                    <TableHead className="text-xs h-8 text-right">PM2.5</TableHead>
                    <TableHead className="text-xs h-8 text-right">NO₂</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {loading
                    ? Array.from({ length: 8 }).map((_, i) => (
                        <TableRow key={i}>
                          {[0,1,2,3].map((j) => (
                            <TableCell key={j}><Skeleton className="h-4 w-full" /></TableCell>
                          ))}
                        </TableRow>
                      ))
                    : rows.map((r) => (
                        <TableRow
                          key={r.station_name}
                          className={[
                            "cursor-pointer text-xs",
                            selectedStation === r.station_name
                              ? "bg-accent"
                              : "hover:bg-accent/50",
                          ].join(" ")}
                          onClick={() => setSelectedStation(
                            selectedStation === r.station_name ? null : r.station_name
                          )}
                        >
                          <TableCell className="font-medium py-1.5 max-w-[180px] truncate">
                            {r.station_name}
                          </TableCell>
                          <TableCell className={`text-right py-1.5 font-mono ${getPollutantColor(r[selectedPollutant], selectedPollutant)}`}>
                            {fmt(r[selectedPollutant])}
                          </TableCell>
                          <TableCell className={`text-right py-1.5 font-mono ${getPollutantColor(r.pm25, "pm25")}`}>
                            {fmt(r.pm25)}
                          </TableCell>
                          <TableCell className={`text-right py-1.5 font-mono ${getPollutantColor(r.no2, "no2")}`}>
                            {fmt(r.no2)}
                          </TableCell>
                        </TableRow>
                      ))}
                </TableBody>
              </Table>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}