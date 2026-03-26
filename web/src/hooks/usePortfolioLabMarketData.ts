"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { fetchMarketData } from "@/lib/api";
import { apiMarketPayloadToLabShape, type LabMarketData } from "@/lib/marketDataAdapter";
import { generateMarketData } from "@/lib/simulationEngine";

export type MarketMode = "synthetic" | "live";

export function usePortfolioLabMarketData(
  nAssets: number,
  setNAssets: (n: number) => void,
  regime: string,
  dataSeed: number
) {
  const [marketMode, setMarketMode] = useState<MarketMode>("synthetic");
  const [tickerInput, setTickerInput] = useState(
    "AAPL,MSFT,GOOGL,AMZN,META"
  );
  const [startDate, setStartDate] = useState("2020-01-01");
  const [endDate, setEndDate] = useState("2024-01-01");
  const [liveLoading, setLiveLoading] = useState(false);
  const [liveError, setLiveError] = useState<string | null>(null);
  const [liveLabData, setLiveLabData] = useState<LabMarketData | null>(null);

  const syntheticData = useMemo(
    () => generateMarketData(nAssets, 504, regime, dataSeed, null),
    [nAssets, regime, dataSeed]
  );

  const data =
    marketMode === "live" && liveLabData ? liveLabData : syntheticData;

  const loadLiveMarketData = useCallback(async () => {
    setLiveLoading(true);
    setLiveError(null);
    try {
      const tickers = tickerInput
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
      if (tickers.length === 0) {
        throw new Error("Enter at least one ticker");
      }
      const raw = await fetchMarketData(tickers, startDate, endDate);
      const lab = apiMarketPayloadToLabShape(raw);
      setLiveLabData(lab);
      setNAssets(lab.assets.length);
    } catch (e) {
      setLiveError(e instanceof Error ? e.message : String(e));
      setLiveLabData(null);
    } finally {
      setLiveLoading(false);
    }
  }, [tickerInput, startDate, endDate, setNAssets]);

  useEffect(() => {
    if (marketMode === "synthetic") {
      setLiveLabData(null);
      setLiveError(null);
    }
  }, [marketMode]);

  return {
    marketMode,
    setMarketMode,
    tickerInput,
    setTickerInput,
    startDate,
    setStartDate,
    endDate,
    setEndDate,
    liveLoading,
    liveError,
    loadLiveMarketData,
    data,
    isLiveLoaded: marketMode === "live" && liveLabData !== null,
  };
}
