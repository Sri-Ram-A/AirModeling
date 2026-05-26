"use client";
// frontend/pages/inversion.tsx

/**
 * Inversion Page — Source Attribution (C = T·Q)
 *
 * Runs Gaussian-plume inversion for a selected pollutant + timestamp.
 * Shows per-station emission estimates (Q) for 4 classical solvers,
 * a matrix diagnostics panel, and singular value spectrum.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { useTheme } from "next-themes";
import { format } from "date-fns";
import {
  Activity, AlertCircle, CalendarDays, ChevronRight,
  Gauge, Info, Moon, RefreshCw, SunMedium,
} from "lucide-react";

import { Badge }        from "@/components/ui/badge";
import { Button }       from "@/components/ui/button";
import { Calendar }     from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Separator }    from "@/components/ui/separator";
import { Skeleton }     from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { REQUEST }      from "@/lib/request";

// ─── Types (self-contained) ───────────────────────────────────────────────────

type SolverResult = {
  method: string;
  residual_norm: number;
  Q: number[];
  reconstructed_C: number[];
  residuals: number[];
  negative_q_count: number;
  metadata: Record<string, unknown> | null;
};

type MatrixDiagnostics = {
  shape: number[];
  rank: number;
  condition_number: number | null;
  singular_values: number[];
};

type InversionResponse = {
  timestamp: string;
  pollutant: string;
  station_names: string[];
  stability_classes: string[];
  observed_concentrations: number[];
  solutions: SolverResult[];
  diagnostics: MatrixDiagnostics;
};

type PollutantKey =
  "pm25" | "pm10" | "no" | "no2" | "nox" |
  "nh3" | "so2" | "co" | "o3" | "benzene" | "toluene";

const POLLUTANT_LABELS: Record<PollutantKey, string> = {
  pm25: "PM2.5", pm10: "PM10", no: "NO", no2: "NO₂",
  nox: "NOₓ", nh3: "NH₃", so2: "SO₂", co: "CO",
  o3: "O₃", benzene: "Benzene", toluene: "Toluene",
};

const SOLVER_LABELS: Record<string, string> = {
  lstsq:        "Least Squares",
  nnls:         "Non-negative LS",
  tikhonov:     "Tikhonov",
  truncated_svd: "Truncated SVD",
};

// ─── Helpers ──────────────────────────────────────────────────────────────────
function fmt(val: number | null | undefined, decimals = 4): string {
  if (val === null || val === undefined) return "—";
  if (isNaN(val as number)) return "NaN";
  return Number(val).toFixed(decimals);
}

/** Scale a value 0–1 relative to the max in an array (for bar widths). */
function relativeWidth(val: number, max: number): string {
  if (max === 0) return "0%";
  return `${Math.min(100, (Math.abs(val) / max) * 100).toFixed(1)}%`;
}

// ─── Singular value mini-chart ────────────────────────────────────────────────
function SVSpectrum({ values }: { values: number[] }) {
  const max = Math.max(...values);
  return (
    <div className="flex items-end gap-0.5 h-12 w-full">
      {values.map((v, i) => (
        <div
          key={i}
          title={`σ${i + 1} = ${v.toExponential(2)}`}
          style={{ height: relativeWidth(v, max) }}
          className="flex-1 bg-primary/60 hover:bg-primary transition-colors rounded-sm min-h-[2px]"
        />
      ))}
    </div>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────
export default function InversionPage() {
  // 1. State: API result + loading/error
  const [result, setResult]   = useState<InversionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState<string | null>(null);

  // 2. State: filters
  const [selectedPollutant, setSelectedPollutant] = useState<PollutantKey>("pm25");
  const [selectedDate, setSelectedDate]           = useState<Date | undefined>(undefined);
  const [activeSolver, setActiveSolver]           = useState<string>("nnls");

  // 3. Theme toggle
  const { theme, setTheme } = useTheme();

  // ── Fetch inversion result ─────────────────────────────────────────────────
  async function fetchInversion(pollutant: PollutantKey, date?: Date) {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ pollutant });
      if (date) params.set("timestamp", format(date, "yyyy-MM-dd"));

      const data = await REQUEST<InversionResponse>(
        "GET",
        `inversion/invert_snapshot?${params.toString()}`
      );
      setResult(data);
      // Default to first available solver
      if (data.solutions.length) setActiveSolver(data.solutions[0].method);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Inversion failed.");
    } finally {
      setLoading(false);
    }
  }

  // ── Initial load ──────────────────────────────────────────────────────────
  useEffect(function onMount() {
    fetchInversion(selectedPollutant);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Handler: pollutant change ─────────────────────────────────────────────
  function handlePollutantChange(value: string) {
    const p = value as PollutantKey;
    setSelectedPollutant(p);
    fetchInversion(p, selectedDate);
  }

  // ── Handler: date select ──────────────────────────────────────────────────
  function handleDateSelect(date: Date | undefined) {
    setSelectedDate(date);
    fetchInversion(selectedPollutant, date);
  }

  // ── Derived: active solver data ───────────────────────────────────────────
  const solverData = useMemo(
    () => result?.solutions.find((s) => s.method === activeSolver) ?? null,
    [result, activeSolver]
  );

  const maxQ = useMemo(
    () => (solverData ? Math.max(...solverData.Q.map(Math.abs)) : 1),
    [solverData]
  );

  // ─── Render ────────────────────────────────────────────────────────────────
  return (
    <TooltipProvider>
      <div className="flex h-screen w-full overflow-hidden bg-background text-foreground">

        {/* ── Sidebar ──────────────────────────────────────────────────── */}
        <aside className="flex w-56 flex-col border-r border-border bg-card px-3 py-5 gap-4">
          {/* Logo */}
          <div className="flex items-center gap-2 px-1 mb-2">
            <Activity className="h-5 w-5 text-primary" />
            <span className="font-semibold tracking-tight text-sm">Inversion</span>
          </div>

          <Separator />

          {/* Pollutant */}
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

          {/* Date picker */}
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

          {/* Solver selector */}
          {result && (
            <div className="flex flex-col gap-1 flex-1">
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider px-1 mb-1">
                Solver
              </span>
              {result.solutions.map((s) => (
                <button
                  key={s.method}
                  onClick={() => setActiveSolver(s.method)}
                  className={[
                    "text-left px-2 py-1.5 text-xs rounded-sm transition-colors flex justify-between items-center",
                    activeSolver === s.method
                      ? "bg-primary text-primary-foreground"
                      : "hover:bg-accent text-foreground",
                  ].join(" ")}
                >
                  <span>{SOLVER_LABELS[s.method] ?? s.method}</span>
                  <span className={`font-mono text-[10px] ${activeSolver === s.method ? "opacity-80" : "text-muted-foreground"}`}>
                    {s.residual_norm.toFixed(2)}
                  </span>
                </button>
              ))}
            </div>
          )}

          <Separator />

          {/* Actions */}
          <div className="flex flex-col gap-2">
            <Button
              variant="outline"
              size="sm"
              className="h-8 text-xs rounded-sm"
              onClick={() => fetchInversion(selectedPollutant, selectedDate)}
              disabled={loading}
            >
              <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${loading ? "animate-spin" : ""}`} />
              Run Inversion
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

        {/* ── Main ─────────────────────────────────────────────────────── */}
        <main className="flex flex-col flex-1 overflow-hidden">

          {/* Header */}
          <header className="flex items-center justify-between px-5 py-3 border-b border-border bg-card">
            <div>
              <h1 className="text-sm font-semibold tracking-tight">
                Source Inversion — {result ? POLLUTANT_LABELS[result.pollutant as PollutantKey] : POLLUTANT_LABELS[selectedPollutant]}
              </h1>
              <p className="text-xs text-muted-foreground mt-0.5">
                {result ? `${result.station_names.length} stations · ${result.timestamp}` : "No result yet"}
              </p>
            </div>
            {error && (
              <div className="flex items-center gap-1.5 text-xs text-destructive">
                <AlertCircle className="h-4 w-4" /> {error}
              </div>
            )}
          </header>

          <div className="flex flex-1 overflow-hidden">

            {/* ── Emission estimates table ─────────────────────────────── */}
            <div className="flex flex-col flex-1 overflow-hidden border-r border-border">
              <div className="px-4 py-2.5 border-b border-border bg-card flex items-center justify-between">
                <span className="text-xs font-medium">
                  Emission Estimates Q [g/s] — {SOLVER_LABELS[activeSolver] ?? activeSolver}
                </span>
                {solverData && (
                  <div className="flex items-center gap-3 text-xs text-muted-foreground">
                    <span>||residual|| = <span className="text-foreground font-mono">{solverData.residual_norm.toFixed(4)}</span></span>
                    {solverData.negative_q_count > 0 && (
                      <Badge variant="destructive" className="text-xs rounded-sm px-1.5">
                        {solverData.negative_q_count} negative
                      </Badge>
                    )}
                  </div>
                )}
              </div>

              <div className="flex-1 overflow-y-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="hover:bg-transparent">
                      <TableHead className="text-xs h-8 w-[180px]">Station</TableHead>
                      <TableHead className="text-xs h-8">Stability</TableHead>
                      <TableHead className="text-xs h-8 text-right">C_obs</TableHead>
                      <TableHead className="text-xs h-8 text-right">C_reconstructed</TableHead>
                      <TableHead className="text-xs h-8 text-right">Q [g/s]</TableHead>
                      <TableHead className="text-xs h-8 text-right">Residual</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {loading
                      ? Array.from({ length: 8 }).map((_, i) => (
                          <TableRow key={i}>
                            {[0,1,2,3,4,5].map((j) => (
                              <TableCell key={j}><Skeleton className="h-4 w-full" /></TableCell>
                            ))}
                          </TableRow>
                        ))
                      : result && solverData
                        ? result.station_names.map((name, i) => {
                            const q    = solverData.Q[i];
                            const cObs = result.observed_concentrations[i];
                            const cRec = solverData.reconstructed_C[i];
                            const res  = solverData.residuals[i];
                            return (
                              <TableRow key={name} className="text-xs hover:bg-accent/50">
                                <TableCell className="font-medium py-1.5 max-w-[180px] truncate">
                                  {name}
                                </TableCell>
                                <TableCell className="py-1.5">
                                  <Badge variant="outline" className="text-[10px] rounded-sm px-1 py-0">
                                    {result.stability_classes[i]}
                                  </Badge>
                                </TableCell>
                                <TableCell className="text-right py-1.5 font-mono text-muted-foreground">
                                  {fmt(cObs, 2)}
                                </TableCell>
                                <TableCell className="text-right py-1.5 font-mono">
                                  {fmt(cRec, 2)}
                                </TableCell>
                                <TableCell className="text-right py-1.5">
                                  <div className="flex items-center justify-end gap-2">
                                    {/* Inline bar */}
                                    <div className="h-1.5 bg-muted rounded-sm w-16 overflow-hidden">
                                      <div
                                        className={`h-full rounded-sm ${q < 0 ? "bg-destructive/70" : "bg-primary/70"}`}
                                        style={{ width: relativeWidth(q, maxQ) }}
                                      />
                                    </div>
                                    <span className={`font-mono ${q < 0 ? "text-destructive" : ""}`}>
                                      {fmt(q, 4)}
                                    </span>
                                  </div>
                                </TableCell>
                                <TableCell className={`text-right py-1.5 font-mono ${Math.abs(res) > 10 ? "text-orange-500" : "text-muted-foreground"}`}>
                                  {fmt(res, 3)}
                                </TableCell>
                              </TableRow>
                            );
                          })
                        : (
                          <TableRow>
                            <TableCell colSpan={6} className="text-center text-xs text-muted-foreground py-8">
                              Run inversion to see results
                            </TableCell>
                          </TableRow>
                        )}
                  </TableBody>
                </Table>
              </div>
            </div>

            {/* ── Right panel: diagnostics ─────────────────────────────── */}
            <div className="w-64 flex flex-col border-l border-border overflow-y-auto shrink-0">

              {/* Matrix diagnostics */}
              <div className="px-4 py-2.5 border-b border-border bg-card">
                <span className="text-xs font-medium">Matrix Diagnostics</span>
              </div>

              {loading
                ? <div className="p-4 space-y-3">{Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-8 w-full" />)}</div>
                : result
                  ? (
                    <div className="p-4 space-y-4">
                      {/* Key metrics */}
                      {[
                        { label: "Shape",     val: `${result.diagnostics.shape[0]} × ${result.diagnostics.shape[1]}` },
                        { label: "Rank",      val: String(result.diagnostics.rank) },
                        { label: "κ (cond.)", val: result.diagnostics.condition_number?.toExponential(3) ?? "—" },
                      ].map(({ label, val }) => (
                        <div key={label} className="flex justify-between items-center text-xs">
                          <span className="text-muted-foreground">{label}</span>
                          <span className="font-mono font-medium">{val}</span>
                        </div>
                      ))}

                      <Separator />

                      {/* Singular value spectrum */}
                      <div>
                        <div className="flex items-center gap-1 mb-2">
                          <span className="text-xs text-muted-foreground">Singular values σ</span>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Info className="h-3 w-3 text-muted-foreground cursor-help" />
                            </TooltipTrigger>
                            <TooltipContent className="text-xs max-w-[180px]">
                              Rapid drop-off indicates ill-conditioning. Truncated SVD zeros values below threshold.
                            </TooltipContent>
                          </Tooltip>
                        </div>
                        <SVSpectrum values={result.diagnostics.singular_values} />
                        <div className="flex justify-between text-[10px] text-muted-foreground mt-1">
                          <span>σ₁ = {result.diagnostics.singular_values[0]?.toExponential(2)}</span>
                          <span>σₙ = {result.diagnostics.singular_values.at(-1)?.toExponential(2)}</span>
                        </div>
                      </div>

                      <Separator />

                      {/* Solver comparison */}
                      <div>
                        <span className="text-xs text-muted-foreground block mb-2">Solver residuals</span>
                        {result.solutions.map((s) => {
                          const maxResidual = Math.max(...result.solutions.map((x) => x.residual_norm));
                          return (
                            <div
                              key={s.method}
                              className={`flex flex-col gap-0.5 mb-2 p-1.5 rounded-sm cursor-pointer transition-colors ${activeSolver === s.method ? "bg-accent" : "hover:bg-accent/50"}`}
                              onClick={() => setActiveSolver(s.method)}
                            >
                              <div className="flex justify-between text-xs">
                                <span className={activeSolver === s.method ? "font-medium" : "text-muted-foreground"}>
                                  {SOLVER_LABELS[s.method] ?? s.method}
                                </span>
                                <span className="font-mono text-[10px]">{s.residual_norm.toFixed(3)}</span>
                              </div>
                              <div className="h-1 bg-muted rounded-sm overflow-hidden">
                                <div
                                  className="h-full bg-primary/60 rounded-sm"
                                  style={{ width: relativeWidth(s.residual_norm, maxResidual) }}
                                />
                              </div>
                            </div>
                          );
                        })}
                      </div>

                      {/* Active solver metadata */}
                      {solverData?.metadata && Object.keys(solverData.metadata).length > 0 && (
                        <>
                          <Separator />
                          <div>
                            <span className="text-xs text-muted-foreground block mb-1.5">Solver params</span>
                            {Object.entries(solverData.metadata).map(([k, v]) => (
                              <div key={k} className="flex justify-between text-xs">
                                <span className="text-muted-foreground">{k}</span>
                                <span className="font-mono">{String(v)}</span>
                              </div>
                            ))}
                          </div>
                        </>
                      )}
                    </div>
                  )
                  : (
                    <div className="p-4 text-xs text-muted-foreground text-center mt-8">
                      No diagnostics yet
                    </div>
                  )}
            </div>
          </div>
        </main>
      </div>
    </TooltipProvider>
  );
}