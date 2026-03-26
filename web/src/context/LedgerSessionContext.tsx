"use client";

import {
  createContext,
  useCallback,
  useContext,
  useReducer,
  type Dispatch,
  type ReactNode,
} from "react";

import {
  DEFAULT_TICKERS,
  DEFAULT_OBJECTIVE,
  DEFAULT_WEIGHT_MIN,
  DEFAULT_WEIGHT_MAX,
} from "@/lib/defaultUniverse";
import {
  appendOptimizationRun,
  type OptimizationRunSource,
} from "@/lib/optimizationRunHistory";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

export interface LedgerConstraints {
  weightMin: number;
  weightMax: number;
  kScreen?: string;
  kSelect?: string;
}

export interface LastOptimize {
  at: string;
  tickers: string[];
  objective: string;
  constraints: LedgerConstraints;
  payload: Record<string, unknown>;
}

export interface LedgerSession {
  tickers: string[];
  objective: string;
  constraints: LedgerConstraints;
  lastOptimize: LastOptimize | null;
}

/* ------------------------------------------------------------------ */
/*  Actions                                                            */
/* ------------------------------------------------------------------ */

type Action =
  | { type: "setUniverse"; tickers: string[]; objective?: string }
  | { type: "setConstraints"; constraints: Partial<LedgerConstraints> }
  | { type: "setLastOptimize"; optimize: LastOptimize }
  | {
      type: "hydrateFromUrl";
      tickers?: string[];
      objective?: string;
      constraints?: Partial<LedgerConstraints>;
    };

/* ------------------------------------------------------------------ */
/*  Reducer                                                            */
/* ------------------------------------------------------------------ */

const initialState: LedgerSession = {
  tickers: [...DEFAULT_TICKERS],
  objective: DEFAULT_OBJECTIVE,
  constraints: { weightMin: DEFAULT_WEIGHT_MIN, weightMax: DEFAULT_WEIGHT_MAX },
  lastOptimize: null,
};

function reducer(state: LedgerSession, action: Action): LedgerSession {
  switch (action.type) {
    case "setUniverse":
      return {
        ...state,
        tickers: action.tickers,
        ...(action.objective != null ? { objective: action.objective } : {}),
      };

    case "setConstraints":
      return {
        ...state,
        constraints: { ...state.constraints, ...action.constraints },
      };

    case "setLastOptimize":
      return { ...state, lastOptimize: action.optimize };

    case "hydrateFromUrl": {
      const next = { ...state };
      if (action.tickers?.length) next.tickers = action.tickers;
      if (action.objective) next.objective = action.objective;
      if (action.constraints)
        next.constraints = { ...next.constraints, ...action.constraints };
      return next;
    }

    default:
      return state;
  }
}

/* ------------------------------------------------------------------ */
/*  Context                                                            */
/* ------------------------------------------------------------------ */

interface LedgerSessionContextValue {
  session: LedgerSession;
  dispatch: Dispatch<Action>;
  setUniverse: (tickers: string[], objective?: string) => void;
  setConstraints: (c: Partial<LedgerConstraints>) => void;
  setLastOptimize: (
    opt: LastOptimize,
    meta?: { source?: OptimizationRunSource }
  ) => void;
}

const LedgerSessionContext = createContext<LedgerSessionContextValue | null>(
  null
);

export function LedgerSessionProvider({ children }: { children: ReactNode }) {
  const [session, dispatch] = useReducer(reducer, initialState);

  const setUniverse = useCallback(
    (tickers: string[], objective?: string) =>
      dispatch({ type: "setUniverse", tickers, objective }),
    []
  );

  const setConstraints = useCallback(
    (constraints: Partial<LedgerConstraints>) =>
      dispatch({ type: "setConstraints", constraints }),
    []
  );

  const setLastOptimize = useCallback(
    (optimize: LastOptimize, meta?: { source?: OptimizationRunSource }) => {
      dispatch({ type: "setLastOptimize", optimize });
      try {
        appendOptimizationRun(
          {
            at: optimize.at,
            tickers: optimize.tickers,
            objective: optimize.objective,
            constraints: {
              weightMin: optimize.constraints.weightMin,
              weightMax: optimize.constraints.weightMax,
              ...(optimize.constraints.kScreen != null
                ? { kScreen: optimize.constraints.kScreen }
                : {}),
              ...(optimize.constraints.kSelect != null
                ? { kSelect: optimize.constraints.kSelect }
                : {}),
            },
            payload: optimize.payload,
          },
          meta?.source ?? "portfolio_lab"
        );
      } catch {
        /* localStorage full or disabled */
      }
    },
    []
  );

  return (
    <LedgerSessionContext.Provider
      value={{ session, dispatch, setUniverse, setConstraints, setLastOptimize }}
    >
      {children}
    </LedgerSessionContext.Provider>
  );
}

export function useLedgerSession(): LedgerSessionContextValue {
  const ctx = useContext(LedgerSessionContext);
  if (!ctx) {
    throw new Error("useLedgerSession must be used within LedgerSessionProvider");
  }
  return ctx;
}
