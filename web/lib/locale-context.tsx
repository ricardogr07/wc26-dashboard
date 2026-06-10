"use client";

import { createContext, useContext, useState, useEffect } from "react";
import { translations, type Locale } from "@/lib/translations";

interface LocaleContextValue {
  locale: Locale;
  setLocale: (l: Locale) => void;
}

const LocaleContext = createContext<LocaleContextValue>({
  locale: "en",
  setLocale: () => {},
});

export function LocaleProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("en");

  useEffect(() => {
    const stored = localStorage.getItem("locale") as Locale | null;
    if (stored === "en" || stored === "es") setLocaleState(stored);
  }, []);

  function setLocale(l: Locale) {
    setLocaleState(l);
    localStorage.setItem("locale", l);
    document.documentElement.lang = l;
  }

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
