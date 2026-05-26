"use client";

import * as React from "react";
import { ThemeProvider as NextThemesProvider } from "next-themes";

export function ThemeProvider({ children, ...props }: React.ComponentProps<typeof NextThemesProvider>) {
  // React 19 / Next 16 Fix: 
  // Tell next-themes to use application/json on the client to suppress the warning
  const scriptProps = typeof window === "undefined" ? {} : { type: "application/json" };
  return (
    <NextThemesProvider {...props} scriptProps={scriptProps as any}>
      {children}
    </NextThemesProvider>
  );
}