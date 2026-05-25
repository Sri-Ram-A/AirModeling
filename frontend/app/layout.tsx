import type { Metadata } from "next";
import { ThemeProvider } from "@/components/theme-provider";
import { APP_NAME } from "@/lib/config";
import { TooltipProvider } from "@/components/ui/tooltip"

import "./globals.css";
import { Figtree, DM_Sans } from "next/font/google";
import { cn } from "@/lib/utils";

const dmSansHeading = DM_Sans({subsets:['latin'],variable:'--font-heading'});

const figtree = Figtree({subsets:['latin'],variable:'--font-sans'});

export const metadata: Metadata = {
  title: APP_NAME,
  description: "Dashboard UI for station-level air transport attribution."
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en" suppressHydrationWarning
      className={cn("h-full", "antialiased", "font-sans", figtree.variable, dmSansHeading.variable)}
    >
      <body className="min-h-full flex flex-col">
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <TooltipProvider>
            {children}
          </TooltipProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
