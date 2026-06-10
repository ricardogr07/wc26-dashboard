"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu } from "lucide-react";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";

const NAV_LINKS = [
  { href: "/", label: "Standings" },
  { href: "/schedule/", label: "Schedule" },
  { href: "/teams/", label: "Teams" },
  { href: "/simulate/", label: "Simulation" },
];

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

export function Nav() {
  return (
    <nav
      className="sticky top-0 z-50 flex items-center px-4 md:px-8"
      style={{ backgroundColor: "#111827", height: "64px" }}
    >
      <Link href="/" className="mr-8 flex items-center gap-2 text-white font-bold text-lg flex-shrink-0">
        <span>⚽</span>
        <span className="hidden sm:inline">WC26</span>
      </Link>

      {/* Desktop links */}
      <div className="hidden md:flex items-center gap-6">
        {NAV_LINKS.map((link) => (
          <NavLink key={link.href} href={link.href} label={link.label} />
        ))}
      </div>

      {/* Mobile hamburger */}
      <div className="md:hidden ml-auto">
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
                <NavLink key={link.href} href={link.href} label={link.label} />
              ))}
            </nav>
          </SheetContent>
        </Sheet>
      </div>
    </nav>
  );
}
