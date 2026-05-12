"use client";

import { createContext, ReactNode, useContext, useEffect, useMemo, useState } from "react";

export type UiLocale = "en" | "zh";

export type LocalizedText =
  | string
  | {
      en: string;
      zh: string;
    };

type UiLanguageContextValue = {
  locale: UiLocale;
  setLocale: (locale: UiLocale) => void;
  text: (value: LocalizedText) => string;
};

const STORAGE_KEY = "tradingagents.ui_locale";

const UiLanguageContext = createContext<UiLanguageContextValue | null>(null);

export function UiLanguageProvider({
  children,
}: {
  children: ReactNode;
}) {
  const [locale, setLocaleState] = useState<UiLocale>("en");

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored === "en" || stored === "zh") {
      setLocaleState(stored);
    }
  }, []);

  function setLocale(next: UiLocale) {
    setLocaleState(next);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, next);
    }
  }

  const value = useMemo<UiLanguageContextValue>(
    () => ({
      locale,
      setLocale,
      text: (input: LocalizedText) =>
        typeof input === "string" ? input : input[locale],
    }),
    [locale],
  );

  return <UiLanguageContext.Provider value={value}>{children}</UiLanguageContext.Provider>;
}

export function useUiLanguage() {
  const context = useContext(UiLanguageContext);
  if (!context) {
    throw new Error("useUiLanguage must be used inside UiLanguageProvider.");
  }
  return context;
}

export function resolveLocalizedText(locale: UiLocale, input: LocalizedText): string {
  return typeof input === "string" ? input : input[locale];
}
