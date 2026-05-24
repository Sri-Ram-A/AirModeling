"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { TransportMatrixResponse } from "@/lib/types";

export function MatrixTable(props: { data: TransportMatrixResponse | null }) {
  if (!props.data) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Transport matrix</CardTitle>
        <CardDescription>
          T[i, j] maps source station j to receptor station i.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="overflow-auto rounded-xl border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="sticky left-0 bg-background">Receptor / Source</TableHead>
                {props.data.station_names.map(function (name) {
                  return <TableHead key={name} className="min-w-28">{name}</TableHead>;
                })}
              </TableRow>
            </TableHeader>
            <TableBody>
              {props.data.transport_matrix.map(function (row, rowIndex) {
                return (
                  <TableRow key={props.data.station_names[rowIndex]}>
                    <TableCell className="sticky left-0 bg-background font-medium">
                      {props.data.station_names[rowIndex]}
                    </TableCell>
                    {row.map(function (value, colIndex) {
                      const opacity = Math.min(Math.max(Math.log10(value + 1e-12) + 10, 0), 10) / 10;
                      return (
                        <TableCell
                          key={`${rowIndex}-${colIndex}`}
                          className="text-right text-xs"
                          title={value.toExponential(2)}
                        >
                          <span
                            className="inline-flex min-w-16 justify-end rounded-lg border border-border px-2 py-1"
                            style={{ backgroundColor: `hsl(var(--primary) / ${0.08 + opacity * 0.22})` }}
                          >
                            {value > 0 ? value.toExponential(2) : "0"}
                          </span>
                        </TableCell>
                      );
                    })}
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
