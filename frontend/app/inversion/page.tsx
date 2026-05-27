"use client";

/**
 * Inversion Page — Source Attribution (C = T·Q)
 *
 * Shadcn-style dashboard with a clean professional UI.
 * Focus:
 * 1. solver comparison,
 * 2. station-level contribution totals,
 * 3. per-receptor source contribution breakdown,
 * 4. compact matrix-style inspection.
 */

import { useEffect, useMemo, useState } from "react";
import { useTheme } from "next-themes";
import { format } from "date-fns";
import {
  AlertCircle,
  CalendarDays,
  Gauge,
  Info,
  Moon,
  RefreshCw,
  SunMedium,
  BarChart3,
  Sigma,
  Waves,
  ChevronRight,
  Calculator,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { REQUEST } from "@/lib/request";

// =============================================================================
// 1. Types
// =============================================================================

type SolverResult = {
  method: string;
  residual_norm: number;
  Q: number[];
  reconstructed_C: number[];
  residuals: number[];
  contribution_matrix: number[][];
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
  | "pm25"
  | "pm10"
  | "no"
  | "no2"
  | "nox"
  | "nh3"
  | "so2"
  | "co"
  | "o3"
  | "benzene"
  | "toluene";

const POLLUTANT_LABELS: Record<PollutantKey, string> = {
  pm25: "PM2.5",
  pm10: "PM10",
  no: "NO",
  no2: "NO₂",
  nox: "NOₓ",
  nh3: "NH₃",
  so2: "SO₂",
  co: "CO",
  o3: "O₃",
  benzene: "Benzene",
  toluene: "Toluene",
};

const SOLVER_LABELS: Record<string, string> = {
  lstsq: "Least Squares",
  nnls: "Non-negative LS",
  tikhonov: "Tikhonov",
  truncated_svd: "Truncated SVD",
};

// =============================================================================
// 2. Helpers
// =============================================================================

function fmt(val: number | null | undefined, decimals = 4): string {
  if (val === null || val === undefined) return "—";
  if (Number.isNaN(val)) return "NaN";
  return Number(val).toFixed(decimals);
}

function relativeWidth(val: number, max: number): string {
  if (!Number.isFinite(max) || max === 0) return "0%";
  return `${Math.min(100, (Math.abs(val) / max) * 100).toFixed(1)}%`;
}

function valueIntensity(val: number, maxAbs: number): string {
  if (!Number.isFinite(val) || maxAbs <= 0) return "rgba(15,23,42,0.04)";
  const r = Math.min(1, Math.abs(val) / maxAbs);
  const alpha = 0.08 + r * 0.28;
  return val >= 0 ? `rgba(34,197,94,${alpha})` : `rgba(239,68,68,${alpha})`;
}

function topContributors(contribRow: number[], stationNames: string[], limit = 5) {
  return contribRow
    .map((value, idx) => ({ value, idx, name: stationNames[idx] }))
    .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))
    .slice(0, limit);
}

function sumRow(row: number[]): number {
  return row.reduce((acc, v) => acc + v, 0);
}

function columnSums(matrix: number[][]): number[] {
  if (!matrix.length) return [];
  const cols = matrix[0].length;
  const sums = new Array(cols).fill(0);
  for (const row of matrix) {
    for (let j = 0; j < cols; j++) sums[j] += row[j] ?? 0;
  }
  return sums;
}

function formatSigned(val: number, decimals = 3): string {
  const abs = Math.abs(val).toFixed(decimals);
  return val >= 0 ? `+${abs}` : `-${abs}`;
}

// =============================================================================
// 3. Small reusable UI blocks
// =============================================================================

function MetricCard({
  title,
  value,
  subtitle,
  icon,
}: {
  title: string;
  value: string;
  subtitle?: string;
  icon: React.ReactNode;
}) {
  return (
    <Card className="rounded-2xl shadow-sm">
      <CardContent className="p-5">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.16em] text-muted-foreground">{title}</p>
            <p className="mt-2 text-2xl font-semibold tracking-tight">{value}</p>
            {subtitle ? <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p> : null}
          </div>
          <div className="grid h-11 w-11 place-items-center rounded-xl border bg-background text-foreground shadow-sm">
            {icon}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function SectionTitle({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div>
        <h2 className="text-lg font-semibold tracking-tight">{title}</h2>
        {subtitle ? <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p> : null}
      </div>
      {action}
    </div>
  );
}

function LoadingMatrix({ rows = 6, cols = 6 }: { rows?: number; cols?: number }) {
  return (
    <div className="space-y-2 overflow-hidden rounded-xl border bg-card p-3">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="grid gap-2" style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }}>
          {Array.from({ length: cols }).map((__, j) => (
            <Skeleton key={j} className="h-8 w-full rounded-md" />
          ))}
        </div>
      ))}
    </div>
  );
}

// =============================================================================
// 4. Component
// =============================================================================

export default function InversionPage() {
  const [result, setResult] = useState<InversionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [selectedPollutant, setSelectedPollutant] = useState<PollutantKey>("pm25");
  const [selectedDate, setSelectedDate] = useState<Date | undefined>(undefined);
  const [activeSolver, setActiveSolver] = useState<string>("nnls");
  const [selectedStationIndex, setSelectedStationIndex] = useState<number>(0);

  const { theme, setTheme } = useTheme();

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
      if (data.solutions.length) setActiveSolver(data.solutions[0].method);
      setSelectedStationIndex(0);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Inversion failed.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchInversion(selectedPollutant);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handlePollutantChange(value: string) {
    const p = value as PollutantKey;
    setSelectedPollutant(p);
    fetchInversion(p, selectedDate);
  }

  function handleDateSelect(date: Date | undefined) {
    setSelectedDate(date);
    fetchInversion(selectedPollutant, date);
  }

  const solverData = useMemo(
    () => result?.solutions.find((s) => s.method === activeSolver) ?? null,
    [result, activeSolver]
  );

  const maxContribution = useMemo(() => {
    if (!solverData) return 1;
    const flat = solverData.contribution_matrix.flat();
    return Math.max(...flat.map((v) => Math.abs(v)), 1e-12);
  }, [solverData]);

  const maxResidual = useMemo(() => {
    if (!result) return 1;
    return Math.max(...result.solutions.map((s) => Math.abs(s.residual_norm)), 1e-12);
  }, [result]);

  const selectedStationName = result?.station_names[selectedStationIndex] ?? "—";
  const selectedContributionRow = solverData?.contribution_matrix[selectedStationIndex] ?? [];
  const selectedTopContributors = useMemo(
    () =>
      solverData && result
        ? topContributors(selectedContributionRow, result.station_names, 6)
        : [],
    [solverData, result, selectedContributionRow]
  );

  const contributionTotals = useMemo(
    () => (solverData ? columnSums(solverData.contribution_matrix) : []),
    [solverData]
  );

  // =============================================================================
  // 5. Render
  // =============================================================================

  return (
    <TooltipProvider>
      <div className="flex min-h-screen w-full bg-background text-foreground">
        {/* Sidebar */}
        <aside className="flex w-72 shrink-0 flex-col border-r bg-card px-4 py-5">
          <div className="rounded-2xl border bg-background p-4 shadow-sm">
            <div className="flex items-center gap-3">

              <div className="flex items-center gap-2 px-1 mb-2">
                <Gauge className="h-5 w-5 text-primary" />
                <span className="font-semibold tracking-tight text-sm">AirWatch</span>
              </div>

            </div>
            <div className="mt-4 rounded-xl border bg-card px-3 py-2">
              <p className="text-[11px] uppercase tracking-[0.16em] text-muted-foreground">Workspace</p>
              <p className="mt-1 text-sm font-medium">Gaussian plume inversion</p>
            </div>
          </div>

          <div className="mt-5 space-y-3">
            <div className="rounded-2xl border bg-background p-4 shadow-sm">
              <p className="text-xs font-medium uppercase tracking-[0.16em] text-muted-foreground">Pollutant</p>
              <Select value={selectedPollutant} onValueChange={handlePollutantChange}>
                <SelectTrigger className="mt-2 h-10 rounded-xl bg-background text-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {(Object.keys(POLLUTANT_LABELS) as PollutantKey[]).map((k) => (
                    <SelectItem key={k} value={k} className="text-sm">
                      {POLLUTANT_LABELS[k]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="rounded-2xl border bg-background p-4 shadow-sm">
              <p className="text-xs font-medium uppercase tracking-[0.16em] text-muted-foreground">Snapshot date</p>
              <Popover>
                <PopoverTrigger asChild>
                  <Button variant="outline" className="mt-2 h-10 w-full justify-start rounded-xl text-sm font-normal">
                    <CalendarDays className="mr-2 h-4 w-4" />
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
                    <div className="border-t p-2">
                      <Button variant="ghost" size="sm" className="w-full" onClick={() => handleDateSelect(undefined)}>
                        Clear — use latest
                      </Button>
                    </div>
                  )}
                </PopoverContent>
              </Popover>
            </div>
          </div>

          <div className="mt-5 rounded-2xl border bg-background p-4 shadow-sm">
            <p className="text-xs font-medium uppercase tracking-[0.16em] text-muted-foreground">Solver</p>
            <div className="mt-3 space-y-2">
              {result ? (
                result.solutions.map((s) => (
                  <button
                    key={s.method}
                    onClick={() => setActiveSolver(s.method)}
                    className={[
                      "flex w-full items-center justify-between rounded-xl border px-3 py-2.5 text-left transition",
                      activeSolver === s.method
                        ? "border-primary bg-primary text-primary-foreground"
                        : "bg-background hover:bg-accent",
                    ].join(" ")}
                  >
                    <span className="text-sm font-medium">{SOLVER_LABELS[s.method] ?? s.method}</span>
                    <span className={activeSolver === s.method ? "text-xs opacity-80" : "text-xs text-muted-foreground"}>
                      {s.residual_norm.toFixed(2)}
                    </span>
                  </button>
                ))
              ) : (
                <p className="text-sm text-muted-foreground">Run inversion to load solvers</p>
              )}
            </div>
          </div>

          <div className="mt-5 grid gap-3 rounded-2xl border bg-background p-4 shadow-sm">
            <Button variant="outline" className="h-10 rounded-xl" onClick={() => fetchInversion(selectedPollutant, selectedDate)} disabled={loading}>
              <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
              Run inversion
            </Button>
            <Button variant="ghost" className="h-10 rounded-xl" onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>
              {theme === "dark" ? (
                <>
                  <SunMedium className="mr-2 h-4 w-4" /> Light mode
                </>
              ) : (
                <>
                  <Moon className="mr-2 h-4 w-4" /> Dark mode
                </>
              )}
            </Button>
          </div>

          <div className="mt-auto pt-5">
            <div className="rounded-2xl border bg-background p-4 shadow-sm">
              <p className="text-sm font-medium">Contribution-first view</p>
              <p className="mt-1 text-sm text-muted-foreground">
                Inspect source contribution rows, top contributors, and cumulative source impact.
              </p>
            </div>
          </div>
        </aside>

        {/* Main */}
        <main className="flex min-w-0 flex-1 flex-col overflow-hidden">
          <header className="flex items-center justify-between border-b bg-card px-5 py-4">
            <div>
              <h1 className="text-sm font-semibold tracking-tight sm:text-base">
                Source Inversion — {result ? POLLUTANT_LABELS[result.pollutant as PollutantKey] : POLLUTANT_LABELS[selectedPollutant]}
              </h1>
              <p className="mt-1 text-xs text-muted-foreground">
                {result ? `${result.station_names.length} stations · ${result.timestamp}` : "No result yet"}
              </p>
            </div>
            {error ? (
              <div className="flex items-center gap-2 rounded-full border border-destructive/20 bg-destructive/10 px-3 py-2 text-xs text-destructive">
                <AlertCircle className="h-4 w-4" />
                {error}
              </div>
            ) : (
              <div className="flex items-center gap-2 rounded-full border bg-background px-3 py-2 text-xs text-muted-foreground">
                <Gauge className="h-4 w-4" />
                {loading ? "Processing" : "Ready"}
              </div>
            )}
          </header>

          <div className="min-w-0 flex-1 overflow-y-auto p-5">
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <MetricCard
                title="Stations"
                value={result ? String(result.station_names.length) : "—"}
                subtitle="Canonical source / receptor set"
                icon={<Gauge className="h-5 w-5" />}
              />
              <MetricCard
                title="Active solver"
                value={solverData ? (SOLVER_LABELS[solverData.method] ?? solverData.method) : "—"}
                subtitle={solverData ? `Residual ${solverData.residual_norm.toFixed(4)}` : "No solver selected"}
                icon={<BarChart3 className="h-5 w-5" />}
              />
              <MetricCard
                title="Condition number"
                value={result?.diagnostics.condition_number ? result.diagnostics.condition_number.toExponential(2) : "—"}
                subtitle={result ? `Rank ${result.diagnostics.rank} · Shape ${result.diagnostics.shape.join(" × ")}` : "No diagnostics"}
                icon={<Sigma className="h-5 w-5" />}
              />
              <MetricCard
                title="Negative Q"
                value={solverData ? String(solverData.negative_q_count) : "—"}
                subtitle="Emission estimates below zero"
                icon={<Calculator className="h-5 w-5" />}
              />
            </div>

            <div className="mt-5 grid gap-5 xl:grid-cols-[1.3fr_0.7fr]">
              <div className="space-y-5">
                <Card className="rounded-2xl shadow-sm">
                  <CardContent className="p-5">
                    <SectionTitle
                      title="Contribution matrix"
                      subtitle="Cell value = T[i][j] × Q[j]. Row i is the modeled contribution to receptor station i from every source station."
                      action={
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Button variant="ghost" size="icon" className="h-9 w-9 rounded-full">
                              <Info className="h-4 w-4" />
                            </Button>
                          </TooltipTrigger>
                          <TooltipContent className="max-w-xs text-xs">
                            Darker cells mean larger contributions. Negative values can appear when Q is negative.
                          </TooltipContent>
                        </Tooltip>
                      }
                    />

                    <div className="mt-4 overflow-auto rounded-xl border">
                      {loading ? (
                        <LoadingMatrix rows={6} cols={6} />
                      ) : result && solverData ? (
                        <Table>
                          <TableHeader>
                            <TableRow className="bg-muted/40 hover:bg-muted/40">
                              <TableHead className="sticky left-0 z-10 w-[180px] bg-muted/40 text-xs">Receptor \ Source</TableHead>
                              {result.station_names.map((name, j) => (
                                <TableHead key={name + j} className="min-w-[110px] text-right text-xs">
                                  <div className="flex flex-col items-end">
                                    <span className="truncate max-w-[100px]">{name}</span>
                                    <span className="text-[10px] text-muted-foreground">src #{j + 1}</span>
                                  </div>
                                </TableHead>
                              ))}
                              <TableHead className="min-w-[120px] text-right text-xs">Row sum</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {result.station_names.map((receptor, i) => {
                              const row = solverData.contribution_matrix[i] ?? [];
                              const rowSum = sumRow(row);
                              const selected = i === selectedStationIndex;

                              return (
                                <TableRow
                                  key={receptor + i}
                                  onClick={() => setSelectedStationIndex(i)}
                                  className={selected ? "bg-accent/50 hover:bg-accent/50" : "cursor-pointer hover:bg-muted/40"}
                                >
                                  <TableCell className="sticky left-0 z-10 bg-inherit font-medium">
                                    <div className="flex items-center gap-2">
                                      <span className="inline-flex h-2 w-2 rounded-full bg-primary" />
                                      <div>
                                        <div className="text-sm font-medium">{receptor}</div>
                                        <div className="text-[10px] text-muted-foreground">{result.stability_classes[i]}</div>
                                      </div>
                                    </div>
                                  </TableCell>

                                  {row.map((value, j) => (
                                    <TableCell key={receptor + j} className="p-1.5">
                                      <div
                                        className="flex h-12 min-w-[104px] items-end rounded-lg border border-border/60 px-2 py-2"
                                        style={{ backgroundColor: valueIntensity(value, maxContribution) }}
                                        title={`${receptor} ← ${result.station_names[j]} = ${value.toExponential(3)}`}
                                      >
                                        <div className="w-full text-right">
                                          <div className="text-[10px] text-muted-foreground">{j + 1}</div>
                                          <div className="mt-1 font-mono text-xs">{fmt(value, 2)}</div>
                                        </div>
                                      </div>
                                    </TableCell>
                                  ))}

                                  <TableCell className="text-right font-mono text-sm font-medium">{fmt(rowSum, 2)}</TableCell>
                                </TableRow>
                              );
                            })}
                          </TableBody>
                        </Table>
                      ) : (
                        <div className="p-8 text-center text-sm text-muted-foreground">Run inversion to see source contributions.</div>
                      )}
                    </div>
                  </CardContent>
                </Card>

                <div className="grid gap-5 xl:grid-cols-2">
                  <Card className="rounded-2xl shadow-sm">
                    <CardContent className="p-5">
                      <SectionTitle
                        title={`Top contributors for ${selectedStationName}`}
                        subtitle="Largest absolute contribution terms in the selected receptor row."
                      />

                      {loading ? (
                        <div className="mt-4 space-y-3">
                          {Array.from({ length: 5 }).map((_, i) => (
                            <Skeleton key={i} className="h-12 w-full rounded-xl" />
                          ))}
                        </div>
                      ) : result && solverData ? (
                        <div className="mt-4 space-y-3">
                          {selectedTopContributors.map((item) => (
                            <div key={item.idx} className="rounded-xl border bg-card p-3">
                              <div className="flex items-start justify-between gap-4">
                                <div>
                                  <p className="text-sm font-medium">{item.name}</p>
                                  <p className="text-xs text-muted-foreground">Source station #{item.idx + 1}</p>
                                </div>
                                <Badge variant={item.value < 0 ? "destructive" : "outline"} className="rounded-full px-2 py-0 text-[10px]">
                                  {formatSigned(item.value, 2)}
                                </Badge>
                              </div>
                              <div className="mt-2 h-2 rounded-full bg-muted">
                                <div
                                  className={item.value < 0 ? "h-2 rounded-full bg-destructive" : "h-2 rounded-full bg-primary"}
                                  style={{ width: relativeWidth(item.value, maxContribution) }}
                                />
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="mt-4 text-sm text-muted-foreground">No contributions available.</div>
                      )}
                    </CardContent>
                  </Card>

                  <Card className="rounded-2xl shadow-sm">
                    <CardContent className="p-5">
                      <SectionTitle
                        title="Selected receptor breakdown"
                        subtitle="Observed concentration vs reconstructed concentration and source-level split."
                      />

                      {loading ? (
                        <div className="mt-4 space-y-3">
                          <Skeleton className="h-24 w-full rounded-xl" />
                          <Skeleton className="h-24 w-full rounded-xl" />
                        </div>
                      ) : result && solverData ? (
                        <div className="mt-4 space-y-4">
                          <div className="grid gap-3 sm:grid-cols-3">
                            <div className="rounded-xl border bg-card p-4">
                              <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Observed</p>
                              <p className="mt-2 text-2xl font-semibold">{fmt(result.observed_concentrations[selectedStationIndex], 2)}</p>
                            </div>
                            <div className="rounded-xl border bg-card p-4">
                              <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Reconstructed</p>
                              <p className="mt-2 text-2xl font-semibold">{fmt(solverData.reconstructed_C[selectedStationIndex], 2)}</p>
                            </div>
                            <div className="rounded-xl border bg-card p-4">
                              <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Residual</p>
                              <p className="mt-2 text-2xl font-semibold">{fmt(solverData.residuals[selectedStationIndex], 3)}</p>
                            </div>
                          </div>

                          <div className="rounded-xl border bg-card p-4">
                            <div className="mb-3 flex items-center justify-between">
                              <p className="text-sm font-medium">Row contribution bars</p>
                              <p className="text-xs text-muted-foreground">Higher bars = stronger source impact</p>
                            </div>

                            <div className="space-y-3">
                              {selectedContributionRow.map((value, j) => (
                                <div key={j} className="grid grid-cols-[120px_1fr_72px] items-center gap-3">
                                  <div className="truncate text-sm text-muted-foreground">{result.station_names[j]}</div>
                                  <div className="h-2 overflow-hidden rounded-full bg-muted">
                                    <div
                                      className={value < 0 ? "h-2 rounded-full bg-destructive" : "h-2 rounded-full bg-primary"}
                                      style={{ width: relativeWidth(value, maxContribution) }}
                                    />
                                  </div>
                                  <div className="text-right font-mono text-sm">{fmt(value, 2)}</div>
                                </div>
                              ))}
                            </div>
                          </div>
                        </div>
                      ) : (
                        <div className="mt-4 text-sm text-muted-foreground">No receptor selected.</div>
                      )}
                    </CardContent>
                  </Card>
                </div>
              </div>

              <div className="mt-5 grid gap-5 xl:grid-cols-[0.95fr_1.05fr]">
                <Card className="rounded-2xl shadow-sm">
                  <CardContent className="p-5">
                    <SectionTitle title="Solver diagnostics" subtitle="Residual norms and matrix conditioning." />

                    {loading ? (
                      <div className="mt-4 space-y-3">
                        <Skeleton className="h-8 w-full rounded-xl" />
                        <Skeleton className="h-24 w-full rounded-xl" />
                        <Skeleton className="h-8 w-full rounded-xl" />
                      </div>
                    ) : result ? (
                      <div className="mt-4 space-y-4">
                        <div className="grid gap-3 sm:grid-cols-3">
                          <div className="rounded-xl border bg-card p-3">
                            <p className="text-xs text-muted-foreground">Shape</p>
                            <p className="mt-1 font-mono text-sm">{result.diagnostics.shape.join(" × ")}</p>
                          </div>
                          <div className="rounded-xl border bg-card p-3">
                            <p className="text-xs text-muted-foreground">Rank</p>
                            <p className="mt-1 font-mono text-sm">{result.diagnostics.rank}</p>
                          </div>
                          <div className="rounded-xl border bg-card p-3">
                            <p className="text-xs text-muted-foreground">κ(T)</p>
                            <p className="mt-1 font-mono text-sm">{result.diagnostics.condition_number?.toExponential(2) ?? "—"}</p>
                          </div>
                        </div>

                        <div>
                          <div className="mb-2 flex items-center gap-2 text-sm font-medium">
                            <Waves className="h-4 w-4 text-muted-foreground" /> Singular values
                          </div>
                          <div className="flex h-14 items-end gap-1 rounded-xl border bg-card p-3">
                            {result.diagnostics.singular_values.map((v, i) => {
                              const max = Math.max(...result.diagnostics.singular_values, 1e-12);
                              return (
                                <Tooltip key={i}>
                                  <TooltipTrigger asChild>
                                    <div
                                      className="flex-1 rounded-md bg-primary/70"
                                      style={{ height: relativeWidth(v, max) }}
                                    />
                                  </TooltipTrigger>
                                  <TooltipContent className="text-xs">σ{i + 1} = {v.toExponential(2)}</TooltipContent>
                                </Tooltip>
                              );
                            })}
                          </div>
                        </div>

                        <div className="space-y-2">
                          {result.solutions.map((s) => (
                            <button
                              key={s.method}
                              onClick={() => setActiveSolver(s.method)}
                              className={[
                                "flex w-full items-center justify-between rounded-xl border px-3 py-2.5 text-left transition",
                                activeSolver === s.method
                                  ? "border-primary bg-accent"
                                  : "bg-background hover:bg-accent/60",
                              ].join(" ")}
                            >
                              <span className="text-sm font-medium">{SOLVER_LABELS[s.method] ?? s.method}</span>
                              <span className="font-mono text-xs text-muted-foreground">{s.residual_norm.toFixed(4)}</span>
                            </button>
                          ))}
                        </div>
                      </div>
                    ) : (
                      <div className="mt-4 text-sm text-muted-foreground">No diagnostics yet.</div>
                    )}
                  </CardContent>
                </Card>

                <Card className="rounded-2xl shadow-sm">
                  <CardContent className="p-5">
                    <SectionTitle
                      title="Station contribution totals"
                      subtitle="Column-wise totals aggregate each source station’s overall influence across all receptors."
                    />

                    {loading ? (
                      <div className="mt-4 space-y-3">
                        {Array.from({ length: 8 }).map((_, i) => (
                          <Skeleton key={i} className="h-10 w-full rounded-xl" />
                        ))}
                      </div>
                    ) : result && solverData ? (
                      <div className="mt-4 space-y-3">
                        {contributionTotals.map((total, j) => {
                          const maxTotal = Math.max(...contributionTotals.map((v) => Math.abs(v)), 1e-12);
                          const name = result.station_names[j];
                          return (
                            <div key={name + j} className="rounded-xl border bg-card p-3">
                              <div className="mb-2 flex items-center justify-between gap-4">
                                <div className="min-w-0">
                                  <p className="truncate text-sm font-medium">{name}</p>
                                  <p className="text-xs text-muted-foreground">Source total contribution</p>
                                </div>
                                <Badge variant={total < 0 ? "destructive" : "outline"} className="rounded-full px-2 py-0 text-[10px]">
                                  {fmt(total, 2)}
                                </Badge>
                              </div>
                              <div className="h-2 overflow-hidden rounded-full bg-muted">
                                <div
                                  className={total < 0 ? "h-2 rounded-full bg-destructive" : "h-2 rounded-full bg-primary"}
                                  style={{ width: relativeWidth(total, maxTotal) }}
                                />
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    ) : (
                      <div className="mt-4 text-sm text-muted-foreground">No contribution totals yet.</div>
                    )}
                  </CardContent>
                </Card>
              </div>

              <div className="mt-5 rounded-2xl border bg-card p-4 shadow-sm">
                <div className="flex flex-wrap items-center justify-between gap-4">
                  <div>
                    <p className="text-sm font-medium">Selected view</p>
                    <p className="text-sm text-muted-foreground">
                      {selectedStationName} · {solverData ? (SOLVER_LABELS[solverData.method] ?? solverData.method) : "—"}
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                    <span className="rounded-full border bg-background px-3 py-1">Observed → reconstructed</span>
                    <span className="rounded-full border bg-background px-3 py-1">Source contribution matrix</span>
                    <span className="rounded-full border bg-background px-3 py-1">Residual analysis</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </main>
      </div>
    </TooltipProvider>
  );
}
