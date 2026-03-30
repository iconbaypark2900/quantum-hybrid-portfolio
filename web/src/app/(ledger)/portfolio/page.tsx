"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef } from "react";

import QuantumPortfolioDashboard from "@/components/CustomizableQuantumDashboard";
import { useLedgerSession } from "@/context/LedgerSessionContext";
import { useNextPageProps, type NextClientPageProps } from "@/lib/nextPageProps";

function PortfolioHydrator() {
  const searchParams = useSearchParams();
  const { dispatch } = useLedgerSession();
  const hydrated = useRef(false);
  /** Stable string for effect deps — avoids enumerating `ReadonlyURLSearchParams` (Next.js sync-dynamic-apis). */
  const queryString = searchParams.toString();

  useEffect(() => {
    if (hydrated.current) return;
    const q = new URLSearchParams(queryString);
    const objective = q.get("objective");
    const weightMin = q.get("weight_min");
    const weightMax = q.get("weight_max");
    const kScreen = q.get("K_screen");
    const kSelect = q.get("K_select");
    const tickerParam = q.get("tickers");

    if (!objective && !weightMin && !weightMax && !tickerParam) return;
    hydrated.current = true;

    dispatch({
      type: "hydrateFromUrl",
      ...(tickerParam
        ? {
            tickers: tickerParam
              .split(",")
              .map((t) => t.trim())
              .filter(Boolean),
          }
        : {}),
      ...(objective ? { objective } : {}),
      constraints: {
        ...(weightMin ? { weightMin: parseFloat(weightMin) } : {}),
        ...(weightMax ? { weightMax: parseFloat(weightMax) } : {}),
        ...(kScreen ? { kScreen } : {}),
        ...(kSelect ? { kSelect } : {}),
      },
    });
  }, [queryString, dispatch]);

  return null;
}

export default function PortfolioPage(props: NextClientPageProps) {
  useNextPageProps(props);
  return (
    <Suspense fallback={null}>
      <PortfolioHydrator />
      <QuantumPortfolioDashboard />
    </Suspense>
  );
}
