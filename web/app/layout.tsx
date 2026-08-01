import type { Metadata } from "next";
import { Geist } from "next/font/google";
import "./globals.css";
import { Nav } from "@/components/nav";
import { TooltipProvider } from "@/components/ui/tooltip";
import { LocaleProvider } from "@/lib/locale-context";

const geist = Geist({ subsets: ["latin"], variable: "--font-geist-sans" });

export const metadata: Metadata = {
  title: "WC26 Quiniela",
  description: "World Cup 2026 pool dashboard: standings, schedule, teams, and simulations",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning className={`${geist.variable} antialiased`}>
      <body className="min-h-screen bg-[#F9FAFB] font-sans">
        <LocaleProvider>
          <TooltipProvider>
            <Nav />
            <main>{children}</main>
          </TooltipProvider>
        </LocaleProvider>
      </body>
    </html>
  );
}
