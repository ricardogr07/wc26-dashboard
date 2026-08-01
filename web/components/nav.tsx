"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu } from "lucide-react";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { useLocale, useT } from "@/lib/locale-context";
import type { Locale } from "@/lib/translations";

const NAV_LINKS = [
  { href: "/", tKey: "nav.standings" },
  { href: "/schedule/", tKey: "nav.schedule" },
  { href: "/bracket/", tKey: "nav.bracket" },
  { href: "/teams/", tKey: "nav.teams" },
  { href: "/simulate/", tKey: "nav.simulation" },
  { href: "/faq/", tKey: "nav.faq" },
] as const;

function NavLink({ href, label }: { href: string; label: string }) {
  const pathname = usePathname();
  const isActive = pathname === href || (href !== "/" && pathname.startsWith(href));
  return (
    <Link
      href={href}
      className="text-sm font-medium transition-colors"
      style={{ color: isActive ? "#ffffff" : "rgba(255,255,255,0.7)" }}
    >
      {label}
    </Link>
  );
}

function LocaleToggle() {
  const { locale, setLocale } = useLocale();
  const locales: Locale[] = ["en", "es"];
  return (
    <div className="flex items-center gap-1">
      {locales.map((l, i) => (
        <span key={l} className="flex items-center gap-1">
          {i > 0 && <span className="text-white/30 text-xs select-none">|</span>}
          <button
            onClick={() => setLocale(l)}
            className="text-xs font-medium px-0.5 transition-colors"
            style={{ color: locale === l ? "#ffffff" : "rgba(255,255,255,0.4)" }}
          >
            {l.toUpperCase()}
          </button>
        </span>
      ))}
    </div>
  );
}

export function Nav() {
  const t = useT();
  return (
    <nav
      className="sticky top-0 z-50 flex items-center px-4 md:px-8"
      style={{ backgroundColor: "#111827", height: "64px" }}
    >
      <Link href="/" className="mr-8 flex items-center gap-2 text-white font-bold text-lg shrink-0">
        <span>⚽</span>
        <span className="hidden sm:inline">WC26</span>
      </Link>

      {/* Desktop links */}
      <div className="hidden md:flex items-center gap-6 shrink-0">
        {NAV_LINKS.map((link) => (
          <NavLink key={link.href} href={link.href} label={t(link.tKey)} />
        ))}
      </div>

      {/* Desktop locale toggle */}
      <div className="hidden md:flex ml-auto">
        <LocaleToggle />
      </div>

      {/* Mobile hamburger */}
      <div className="md:hidden ml-auto flex items-center gap-3">
        <LocaleToggle />
        <Sheet modal>
          <SheetTrigger
            className="text-white p-1 rounded"
            aria-label="Open menu"
          >
            <Menu size={22} />
          </SheetTrigger>
          <SheetContent
            side="left"
            className="w-64 p-0"
            style={{ backgroundColor: "#111827" }}
          >
            <nav className="flex flex-col gap-4 pt-16 px-6">
              {NAV_LINKS.map((link) => (
                <NavLink key={link.href} href={link.href} label={t(link.tKey)} />
              ))}
            </nav>
          </SheetContent>
        </Sheet>
      </div>
    </nav>
  );
}
