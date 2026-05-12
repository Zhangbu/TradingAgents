"use client";

export type VendorPreset = "safe" | "balanced" | "alpha_vantage_heavy";

export type OperatorPreferences = {
  defaultMode: "paper_manual" | "paper_auto" | "analysis_only";
  defaultSymbol: string;
  defaultBroker: "alpaca" | "interactive_brokers";
  defaultReferencePrice: string;
  defaultLimitPrice: string;
  llmProviderPreference: string;
  vendorPreset: VendorPreset;
  notes: string;
};

const STORAGE_KEY = "tradingagents.operator_preferences";
export const OPERATOR_PREFERENCES_EVENT = "tradingagents-preferences-changed";

export const defaultOperatorPreferences: OperatorPreferences = {
  defaultMode: "paper_manual",
  defaultSymbol: "AAPL",
  defaultBroker: "alpaca",
  defaultReferencePrice: "100",
  defaultLimitPrice: "1",
  llmProviderPreference: "",
  vendorPreset: "balanced",
  notes: "",
};

export function loadOperatorPreferences(): OperatorPreferences {
  if (typeof window === "undefined") {
    return defaultOperatorPreferences;
  }

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return defaultOperatorPreferences;
    }

    const parsed = JSON.parse(raw) as Partial<OperatorPreferences>;
    return {
      ...defaultOperatorPreferences,
      ...parsed,
    };
  } catch {
    return defaultOperatorPreferences;
  }
}

export function saveOperatorPreferences(next: OperatorPreferences): void {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  window.dispatchEvent(
    new CustomEvent(OPERATOR_PREFERENCES_EVENT, { detail: next }),
  );
}

export function vendorPresetToMap(preset: VendorPreset): Record<string, "yfinance" | "alpha_vantage"> {
  switch (preset) {
    case "safe":
      return {
        core_stock_apis: "yfinance",
        technical_indicators: "yfinance",
        fundamental_data: "yfinance",
        news_data: "yfinance",
      };
    case "alpha_vantage_heavy":
      return {
        core_stock_apis: "alpha_vantage",
        technical_indicators: "alpha_vantage",
        fundamental_data: "yfinance",
        news_data: "yfinance",
      };
    case "balanced":
    default:
      return {
        core_stock_apis: "alpha_vantage",
        technical_indicators: "alpha_vantage",
        fundamental_data: "yfinance",
        news_data: "yfinance",
      };
  }
}
