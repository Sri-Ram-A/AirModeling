"use client";

import * as React from "react";
import { RefreshCcw, MapPinned, Waves, SplitSquareHorizontal, Activity } from "lucide-react";
import { motion } from "framer-motion";
import { STATIONS } from "@/lib/stations";
import { REQUEST, RequestError } from "@/lib/request";
import type {
  CurrentReadingResponse,
  ContributionResponse,
  SolverMethod,
  StationReading,
  TransportMatrixResponse
} from "@/lib/types";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ThemeToggle } from "@/components/theme-toggle";
import { LoadingShell } from "@/components/loading-shell";
import { ErrorState } from "@/components/error-state";
import { StationMap } from "@/components/station-map";
import { CurrentReadingTable } from "@/components/current-reading-table";
import { MatrixTable } from "@/components/matrix-table";
import { ContributionPanel } from "@/components/contribution-panel";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";
import { ChartContainer } from "@/components/ui/chart";
import { ResponsiveContainer, BarChart, CartesianGrid, XAxis, YAxis, Tooltip, Bar } from "recharts";

type LoadingState = {
  current: boolean;
  matrix: boolean;
  contribution: boolean;
};

type ErrorStateMap = {
  current?: string;
  matrix?: string;
  contribution?: string;
};

function initialLoading(): LoadingState {
  return {
    current: true,
    matrix: true,
    contribution: true
  };
}

export function Dashboard() {
  const [current, setCurrent] = React.useState<CurrentReadingResponse | null>(null);
  const [matrix, setMatrix] = React.useState<TransportMatrixResponse | null>(null);
  const [contribution, setContribution] = React.useState<ContributionResponse | null>(null);
  const [method, setMethod] = React.useState<SolverMethod>("nnls");
  const [loading, setLoading] = React.useState<LoadingState>(initialLoading());
  const [errors, setErrors] = React.useState<ErrorStateMap>({});
  const [selectedStation, setSelectedStation] = React.useState<StationReading | null>(null);
  const [dialogOpen, setDialogOpen] = React.useState(false);

  React.useEffect(function () {
    loadDashboard();
  }, []);

  function loadDashboard() {
    void loadCurrentReading();
    void loadTransportMatrix();
    void loadContribution(method);
  }

  async function loadCurrentReading() {
    setLoading(function (prev) {
      return { ...prev, current: true };
    });

    try {
      const data = await REQUEST<CurrentReadingResponse>("GET", "current_reading");
      setCurrent(data);
      setErrors(function (prev) {
        return { ...prev, current: undefined };
      });
    } catch (error) {
      setErrors(function (prev) {
        return { ...prev, current: resolveMessage(error, "Current reading failed.") };
      });
    } finally {
      setLoading(function (prev) {
        return { ...prev, current: false };
      });
    }
  }

  async function loadTransportMatrix() {
    setLoading(function (prev) {
      return { ...prev, matrix: true };
    });

    try {
      const data = await REQUEST<TransportMatrixResponse>("GET", "get_transport_matrix");
      setMatrix(data);
      setErrors(function (prev) {
        return { ...prev, matrix: undefined };
      });
    } catch (error) {
      setErrors(function (prev) {
        return { ...prev, matrix: resolveMessage(error, "Transport matrix failed.") };
      });
    } finally {
      setLoading(function (prev) {
        return { ...prev, matrix: false };
      });
    }
  }

  async function loadContribution(nextMethod: SolverMethod) {
    setLoading(function (prev) {
      return { ...prev, contribution: true };
    });

    try {
      const data = await REQUEST<ContributionResponse>("GET", `get_contributions/${nextMethod}`);
      setContribution(data);
      setErrors(function (prev) {
        return { ...prev, contribution: undefined };
      });
    } catch (error) {
      setErrors(function (prev) {
        return { ...prev, contribution: resolveMessage(error, "Contribution solver failed.") };
      });
    } finally {
      setLoading(function (prev) {
        return { ...prev, contribution: false };
      });
    }
  }

  function handleMethodChange(nextMethod: SolverMethod) {
    setMethod(nextMethod);
    void loadContribution(nextMethod);
  }

  function handleRowSelect(reading: StationReading) {
    setSelectedStation(reading);
    setDialogOpen(true);
  }

  function handleRefresh() {
    loadDashboard();
  }

  function resolveMessage(error: unknown, fallback: string): string {
    if (error instanceof RequestError) {
      return error.message;
    }

    if (error instanceof Error) {
      return error.message;
    }

    return fallback;
  }

  function getStats() {
    const values = current?.readings.map(function (item) {
      return item.pollutant;
    }) ?? [];
    const max = values.length > 0 ? Math.max.apply(null, values) : 0;
    const avg = values.length > 0 ? values.reduce(function (acc, value) {
      return acc + value;
    }, 0) / values.length : 0;
    const calm = current?.readings.filter(function (item) {
      return item.wind_speed < 0.5;
    }).length ?? 0;

    return { max: max, avg: avg, calm: calm };
  }

  function getReadingSeries() {
    return current?.readings.map(function (item) {
      return {
        station: item.station_name.length > 9 ? `${item.station_name.slice(0, 9)}…` : item.station_name,
        value: item.pollutant
      };
    }) ?? [];
  }

  if (loading.current && loading.matrix && loading.contribution && !current && !matrix && !contribution) {
    return <LoadingShell />;
  }

  const stats = getStats();

  return (
    <div className="grid gap-6">
      <section className="relative overflow-hidden rounded-3xl border border-border bg-card p-6 shadow-soft">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/10 via-transparent to-transparent" />
        <div className="relative grid gap-4 lg:grid-cols-[1.6fr_0.8fr] lg:items-end">
          <div className="grid gap-3">
            <Badge className="w-fit">Live backend connected</Badge>
            <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
              Air Attribution Dashboard
            </h1>
            <p className="max-w-3xl text-sm leading-6 text-muted-foreground sm:text-base">
              Monitor the latest station snapshot, inspect the transport matrix, and compare source
              attribution methods in one responsive workspace.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3 lg:justify-end">
            <Button type="button" variant="outline" onClick={handleRefresh} title="Refresh all API data">
              <RefreshCcw className="h-4 w-4" />
              Refresh
            </Button>
            <ThemeToggle />
          </div>
        </div>
      </section>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard title="Stations" value={`${current?.station_count ?? STATIONS.length}`} icon={<MapPinned className="h-4 w-4" />} />
        <MetricCard title="Average level" value={stats.avg.toFixed(2)} subtitle={current?.pollutant?.toUpperCase() ?? "PM2.5"} icon={<Waves className="h-4 w-4" />} />
        <MetricCard title="Peak reading" value={stats.max.toFixed(2)} icon={<Activity className="h-4 w-4" />} />
        <MetricCard title="Calm wind" value={`${stats.calm}`} subtitle="Stations below 0.5 m/s" icon={<SplitSquareHorizontal className="h-4 w-4" />} />
      </div>

      <Tabs defaultValue="overview" className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="map">Map</TabsTrigger>
          <TabsTrigger value="matrix">Matrix</TabsTrigger>
          <TabsTrigger value="solver">Solver</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <div className="grid gap-4 xl:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Station concentration profile</CardTitle>
                <CardDescription>Quick scan of the current pollutant field.</CardDescription>
              </CardHeader>
              <CardContent>
                <ChartContainer
                  config={{
                    value: { label: "Concentration", color: "hsl(var(--chart-1))" }
                  }}
                >
                  <div className="h-[300px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={getReadingSeries()}>
                        <CartesianGrid vertical={false} strokeOpacity={0.2} />
                        <XAxis dataKey="station" tickLine={false} axisLine={false} />
                        <YAxis tickLine={false} axisLine={false} />
                        <Tooltip />
                        <Bar dataKey="value" fill="var(--color-value)" radius={4} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </ChartContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Snapshot metadata</CardTitle>
                <CardDescription>Useful state for the dashboard header and downstream actions.</CardDescription>
              </CardHeader>
              <CardContent className="grid gap-3 text-sm">
                <InfoRow label="Timestamp" value={current?.timestamp ?? "N/A"} />
                <InfoRow label="Pollutant" value={current?.pollutant?.toUpperCase() ?? "N/A"} />
                <InfoRow label="Complete stations" value={`${current?.complete_station_count ?? 0}`} />
                <InfoRow label="Matrix rows" value={`${matrix?.transport_matrix.length ?? 0}`} />
                <InfoRow label="Solver method" value={contribution?.method ?? method} />
              </CardContent>
            </Card>
          </div>

          <div className="mt-4">
            {errors.current ? (
              <ErrorState title="Current reading error" message={errors.current} onRetry={loadCurrentReading} />
            ) : null}
            {current ? (
              <div className="mt-4">
                <CurrentReadingTable readings={current.readings} pollutant={current.pollutant} onSelect={handleRowSelect} />
              </div>
            ) : null}
          </div>
        </TabsContent>

        <TabsContent value="map">
          {errors.current ? (
            <ErrorState title="Current reading error" message={errors.current} onRetry={loadCurrentReading} />
          ) : null}
          {current ? <StationMap stations={STATIONS} readings={current.readings} /> : null}
        </TabsContent>

        <TabsContent value="matrix">
          {errors.matrix ? (
            <ErrorState title="Transport matrix error" message={errors.matrix} onRetry={loadTransportMatrix} />
          ) : null}
          <div className="mt-4">
            <MatrixTable data={matrix} />
          </div>
        </TabsContent>

        <TabsContent value="solver">
          {errors.contribution ? (
            <ErrorState title="Solver error" message={errors.contribution} onRetry={function () { void loadContribution(method); }} />
          ) : null}
          <div className="mt-4">
            <ContributionPanel
              data={contribution}
              method={method}
              onMethodChange={handleMethodChange}
              onRun={function () { void loadContribution(method); }}
              loading={loading.contribution}
            />
          </div>
        </TabsContent>
      </Tabs>

      <Separator />

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          {selectedStation ? (
            <div className="grid gap-2">
              <h3 className="text-lg font-semibold">{selectedStation.station_name}</h3>
              <p className="text-sm text-muted-foreground">
                Snapshot detail view for station-level inspection.
              </p>
              <div className="grid gap-2 rounded-2xl border border-border bg-muted p-4 text-sm">
                <InfoRow label="Pollutant" value={selectedStation.pollutant.toFixed(2)} />
                <InfoRow label="Wind speed" value={`${selectedStation.wind_speed.toFixed(2)} m/s`} />
                <InfoRow label="Wind direction" value={`${selectedStation.wind_direction.toFixed(1)}°`} />
                <InfoRow label="Solar radiation" value={`${selectedStation.solar_radiation.toFixed(2)} W/m²`} />
                <InfoRow label="Timestamp" value={selectedStation.timestamp} />
              </div>
            </div>
          ) : null}
        </DialogContent>
      </Dialog>
    </div>
  );
}

function MetricCard(props: { title: string; value: string; subtitle?: string; icon: React.ReactNode }) {
  return (
    <motion.div whileHover={{ y: -3 }} transition={{ type: "spring", stiffness: 250, damping: 20 }}>
      <Card className="h-full">
        <CardContent className="flex h-full items-center gap-4 p-5">
          <div className="rounded-2xl bg-primary/10 p-3 text-primary">{props.icon}</div>
          <div className="min-w-0">
            <p className="text-sm text-muted-foreground">{props.title}</p>
            <p className="text-2xl font-bold tracking-tight">{props.value}</p>
            {props.subtitle ? <p className="text-xs text-muted-foreground">{props.subtitle}</p> : null}
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}

function InfoRow(props: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <span className="text-muted-foreground">{props.label}</span>
      <span className="font-medium">{props.value}</span>
    </div>
  );
}
