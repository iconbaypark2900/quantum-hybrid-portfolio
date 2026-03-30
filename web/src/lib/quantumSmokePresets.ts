/**
 * IBM Runtime smoke-test ticker presets (Quantum Engine).
 * Keep Mag 7 + JPM in sync with `_SMOKE_DEFAULT_TICKERS` in `services/ibm_quantum.py`.
 */
export type SmokeTestPreset = {
  id: string;
  label: string;
  description: string;
  tickers: readonly string[];
};

export const SMOKE_PRESET_MAG7_FIN_TILT: SmokeTestPreset = {
  id: "mag7-jpm",
  label: "Mag 7 + JPM",
  description: "Eight names — matches server default when the field is empty",
  tickers: [
    "AAPL",
    "MSFT",
    "GOOGL",
    "AMZN",
    "META",
    "NVDA",
    "TSLA",
    "JPM",
  ],
};

/** Lighter two-asset smoke (broad equity / growth). */
export const SMOKE_PRESET_CORE_ETFS: SmokeTestPreset = {
  id: "core-etfs",
  label: "Core ETFs",
  description: "SPY + QQQ — smaller universe, faster fetch",
  tickers: ["SPY", "QQQ"],
};

export const IBM_SMOKE_TEST_PRESETS: SmokeTestPreset[] = [
  SMOKE_PRESET_MAG7_FIN_TILT,
  SMOKE_PRESET_CORE_ETFS,
];

export function formatSmokePresetTickers(tickers: readonly string[]): string {
  return tickers.join(", ");
}

/** Compare two comma-separated ticker strings (order-insensitive, case-insensitive). */
export function smokeTickerListsEqual(a: string, b: string): boolean {
  const norm = (s: string) =>
    s
      .split(",")
      .map((t) => t.trim().toUpperCase())
      .filter(Boolean)
      .sort()
      .join(",");
  return norm(a) === norm(b);
}

/** Empty field uses the same universe as Mag 7 + JPM on the server. */
export function isMag7FinTiltInput(input: string): boolean {
  const t = input.trim();
  if (!t) return true;
  return smokeTickerListsEqual(
    t,
    formatSmokePresetTickers(SMOKE_PRESET_MAG7_FIN_TILT.tickers)
  );
}

export function isCoreEtfInput(input: string): boolean {
  const t = input.trim();
  if (!t) return false;
  return smokeTickerListsEqual(
    t,
    formatSmokePresetTickers(SMOKE_PRESET_CORE_ETFS.tickers)
  );
}
