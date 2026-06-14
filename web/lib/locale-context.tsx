"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useSyncExternalStore,
} from "react";
import { translations, type Locale } from "@/lib/translations";

interface LocaleContextValue {
  locale: Locale;
  setLocale: (l: Locale) => void;
}

const LocaleContext = createContext<LocaleContextValue>({
  locale: "en",
  setLocale: () => {},
});

// Module-level store so any number of LocaleProvider instances share state.
const localeListeners = new Set<() => void>();

function localeSubscribe(listener: () => void): () => void {
  localeListeners.add(listener);
  return () => {
    localeListeners.delete(listener);
  };
}

function getLocaleSnapshot(): Locale {
  const stored = localStorage.getItem("locale") as Locale | null;
  return stored === "en" || stored === "es" ? stored : "en";
}

function getLocaleServerSnapshot(): Locale {
  return "en";
}

export function LocaleProvider({ children }: { children: React.ReactNode }) {
  const locale = useSyncExternalStore(
    localeSubscribe,
    getLocaleSnapshot,
    getLocaleServerSnapshot,
  );

  // Keep document.lang in sync (safe DOM side-effect, not a setState call).
  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  const setLocale = useCallback((l: Locale) => {
    localStorage.setItem("locale", l);
    for (const listener of localeListeners) listener();
  }, []);

  return (
    <LocaleContext.Provider value={{ locale, setLocale }}>
      {children}
    </LocaleContext.Provider>
  );
}

export function useLocale(): LocaleContextValue {
  return useContext(LocaleContext);
}

export function useT(): (path: string) => string {
  const { locale } = useLocale();
  const dict = translations[locale];
  return function t(path: string): string {
    const parts = path.split(".");
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let current: any = dict;
    for (const part of parts) {
      if (typeof current !== "object" || current === null) return path;
      current = current[part];
    }
    return typeof current === "string" ? current : path;
  };
}
