"use client";
// app/page.tsx
// AirWatch home page — overview cards, quick navigation, recent activity

import Link from "next/link";
import {
  Wind, Thermometer, Droplets, Activity,
  LayoutDashboard, ArrowRight, TrendingUp,
  TrendingDown, Minus, AlertTriangle, CheckCircle2,
  MapPin, Clock,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";


export default function HomePage() {
  return (
    <div className="flex flex-col flex-1 overflow-y-auto px-8 py-7 gap-8">

      {/* Header */}
      <header className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Welcome back</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Real-time air quality monitoring across all stations.
          </p>
        </div>
        <Badge variant="secondary" className="gap-1.5 text-xs h-7 px-3">
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
          Live data
        </Badge>
      </header>

      {/* Recent alerts */}
      <section className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold">View Dashboard</h2>
          <Button variant="ghost" size="sm" className="text-xs h-7 gap-1" asChild>
            <Link href="/dashboard">View all <ArrowRight className="h-3 w-3" /></Link>
          </Button>
        </div>
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold">View Inversion</h2>
          <Button variant="ghost" size="sm" className="text-xs h-7 gap-1" asChild>
            <Link href="/inversion">View all <ArrowRight className="h-3 w-3" /></Link>
          </Button>
        </div>

      </section>

    </div>
  );
}