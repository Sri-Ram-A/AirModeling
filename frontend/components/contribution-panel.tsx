"use client";

import { Bar, BarChart, CartesianGrid, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ChartContainer } from "@/components/ui/chart";
import type { ContributionResponse, SolverMethod } from "@/lib/types";
import { Select } from "@/components/ui/select";
import { Button } from "@/components/ui/button";

export function ContributionPanel(props: {
  data: ContributionResponse | null;
  method: SolverMethod;
  onMethodChange: (method: SolverMethod) => void;
  onRun: () => void;
  loading: boolean;
}) {
  function buildSeries(data: ContributionResponse | null) {
    if (!data) {
      return [];
    }

    return data.estimated_emissions.map(function (value, index) {
      return {
        station: `${index + 1}`,
        emission: value,
        residual: Math.abs(data.residuals[index] ?? 0)
      };
    });
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Emission attribution</CardTitle>
        <CardDescription>
          Select a solver, then recompute source contributions for the active snapshot.
        </CardDescription>
        <div className="flex flex-col gap-3 sm:flex-row">
          <Select
            value={props.method}
            onChange={function (event) {
              props.onMethodChange(event.target.value as SolverMethod);
            }}
          >
            <option value="lstsq">Least squares</option>
            <option value="nnls">NNLS</option>
            <option value="tikhonov">Tikhonov</option>
            <option value="truncated_svd">Truncated SVD</option>
          </Select>
          <Button type="button" onClick={props.onRun} disabled={props.loading}>
            {props.loading ? "Running..." : "Run solver"}
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {props.data ? (
          <div className="grid gap-4 xl:grid-cols-2">
            <div className="rounded-2xl border border-border p-4">
              <div className="mb-3 text-sm font-medium">Estimated emissions</div>
              <ChartContainer
                config={{
                  emission: { label: "Emission", color: "hsl(var(--chart-1))" },
                  residual: { label: "Residual", color: "hsl(var(--chart-4))" }
                }}
              >
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={buildSeries(props.data)}>
                    <CartesianGrid vertical={false} strokeOpacity={0.2} />
                    <XAxis dataKey="station" tickLine={false} axisLine={false} />
                    <YAxis tickLine={false} axisLine={false} />
                    <Tooltip />
                    <Bar dataKey="emission" fill="var(--color-emission)" radius={4} />
                    <Bar dataKey="residual" fill="var(--color-residual)" radius={4} />
                  </BarChart>
                </ResponsiveContainer>
              </ChartContainer>
            </div>
            <div className="grid gap-3 rounded-2xl border border-border p-4 text-sm">
              <div className="flex items-center justify-between gap-4">
                <span className="text-muted-foreground">Residual norm</span>
                <span className="font-medium">{props.data.residual_norm.toFixed(4)}</span>
              </div>
              <div className="flex items-center justify-between gap-4">
                <span className="text-muted-foreground">Rank</span>
                <span className="font-medium">{props.data.rank ?? "N/A"}</span>
              </div>
              <div className="flex items-center justify-between gap-4">
                <span className="text-muted-foreground">Condition number</span>
                <span className="font-medium">{props.data.condition_number?.toFixed(2) ?? "N/A"}</span>
              </div>
              <div className="rounded-xl bg-muted p-3">
                <div className="mb-1 text-xs uppercase tracking-wide text-muted-foreground">Snapshot</div>
                <div className="font-medium">{props.data.timestamp}</div>
              </div>
              <div className="rounded-xl bg-muted p-3">
                <div className="mb-1 text-xs uppercase tracking-wide text-muted-foreground">Method</div>
                <div className="font-medium">{props.data.method}</div>
              </div>
            </div>
          </div>
        ) : (
          <div className="rounded-2xl border border-dashed border-border p-6 text-sm text-muted-foreground">
            No contribution data loaded yet.
          </div>
        )}
      </CardContent>
    </Card>
  );
}
