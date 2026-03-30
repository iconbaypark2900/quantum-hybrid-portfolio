"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { fetchMarketData } from "@/lib/api";
import {
  apiMarketPayloadToLabShape,
  type CovarianceSource,
  type LabMarketData,
  type ReturnsSource,
} from "@/lib/marketDataAdapter";
import { generateMarketData } from "@/lib/simulationEngine";

export type MarketMode = "synthetic" | "live";

/**
 * `customTickerList` drives both synthetic name labels and live fetch.
 * Synthetic generation uses the first `nAssets` names from the list (falling
 * back to DEFAULT_TICKERS when the list is empty). Live mode clears cached
 * data whenever the list, startDate, or endDate changes so the user must
 * reload before the next optimize, preventing stale-panel use.
 */
export function usePortfolioLabMarketData(
  nAssets: number,
  setNAssets: (n: number) => void,
  regime: string,
  dataSeed: number,
  customTickerList: readonly string[]
) {
  const [marketMode, setMarketMode] = useState<MarketMode>("synthetic");
  const [startDate, setStartDate] = useState("2020-01-01");
  const [endDate, setEndDate] = useState("2024-01-01");
  const [liveLoading, setLiveLoading] = useState(false);
  const [liveError, setLiveError] = useState<string | null>(null);
  const [liveLabData, setLiveLabData] = useState<LabMarketData | null>(null);

  // Stable string key for memo deps — prevents referential churn from the array prop.
  const tickerKey = customTickerList.join(",");

  const syntheticData = useMemo(
    () =>
      generateMarketData(
        nAssets,
        504,
        regime,
        dataSeed,
        customTickerList.length > 0 ? (customTickerList as string[]) : null
      ),
    // tickerKey is the stable proxy for customTickerList contents.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [nAssets, regime, dataSeed, tickerKey]
  );

  const data =
    marketMode === "live" && liveLabData ? liveLabData : syntheticData;

  const loadLiveMarketData = useCallback(async () => {
    setLiveLoading(true);
    setLiveError(null);
    try {
      const tickers = tickerKey
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
      if (tickers.length === 0) {
        throw new Error("Enter at least one ticker");
      }
      const raw = await fetchMarketData(tickers, startDate, endDate, true);
      const lab = apiMarketPayloadToLabShape(raw);
      setLiveLabData(lab);
      setNAssets(lab.assets.length);
    } catch (e) {
      setLiveError(e instanceof Error ? e.message : String(e));
      setLiveLabData(null);
    } finally {
      setLiveLoading(false);
    }
  }, [tickerKey, startDate, endDate, setNAssets]);

  // Clear live data when switching back to synthetic.
  useEffect(() => {
    if (marketMode === "synthetic") {
      setLiveLabData(null);
      setLiveError(null);
    }
  }, [marketMode]);

  // Invalidate stale live data when ticker or date inputs change.
  // Setting state to its current value (null → null) is a React no-op, so
  // this is safe to run unconditionally on input changes regardless of whether
  // data is currently loaded.
  useEffect(() => {
    if (marketMode !== "live") return;
    setLiveLabData(null);
    setLiveError(null);
  }, [tickerKey, startDate, endDate, marketMode]);

  const returnsSource: ReturnsSource =
    marketMode === "live" && liveLabData
      ? liveLabData.returnsSource
      : "mvn_synthetic";

  const covarianceSource: CovarianceSource =
    marketMode === "live" && liveLabData
      ? liveLabData.covarianceSource
      : "full_window";

  return {
    marketMode,
    setMarketMode,
    startDate,
    setStartDate,
    endDate,
    setEndDate,
    liveLoading,
    liveError,
    loadLiveMarketData,
    data,
    isLiveLoaded: marketMode === "live" && liveLabData !== null,
    returnsSource,
    covarianceSource,
  };
}
