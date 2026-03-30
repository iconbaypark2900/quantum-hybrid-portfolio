/**
 * Maps Flask /api/market-data JSON (unwrapped) to the shape expected by
 * `simulationEngine` + `CustomizableQuantumDashboard` (assets + corr + daily returns for charts).
 */

export type LabAsset = {
  name: string;
  sector: string;
  annReturn: number;
  annVol: number;
  sharpe: number;
  returns: number[];
};

export type ReturnsSource = "historical" | "mvn_synthetic";

/**
 * Indicates which observations underlie the primary μ and Σ in the payload.
 *   panel_aligned – Σ computed from the tail slice matching daily_returns.
 *   full_window   – Σ computed from the full available window (may differ from plotted dailies).
 */
export type CovarianceSource = "panel_aligned" | "full_window";

export type LabMarketData = {
  assets: LabAsset[];
  corr: number[][];
  regime: string;
  returnsSource: ReturnsSource;
  covarianceSource: CovarianceSource;
};

function buildCorrFromCov(cov: number[][]): number[][] {
  const n = cov.length;
  const corr: number[][] = Array.from({ length: n }, () => Array(n).fill(0));
  const vols = cov.map((row, i) => Math.sqrt(Math.max(row[i] ?? 0, 1e-12)));
  for (let i = 0; i < n; i++) {
    for (let j = 0; j < n; j++) {
      corr[i][j] = cov[i][j] / (vols[i] * vols[j]);
    }
  }
  return corr;
}

/**
 * Lower-triangular Cholesky factor of a symmetric positive-semi-definite matrix.
 * A small jitter (1e-8) is added to the diagonal to guard against exact
 * semi-definiteness from floating-point round-trip errors.
 */
function cholesky(A: number[][]): number[][] {
  const n = A.length;
  const L: number[][] = Array.from({ length: n }, () => Array(n).fill(0));
  const jitter = 1e-8;
  for (let i = 0; i < n; i++) {
    for (let j = 0; j <= i; j++) {
      let s = A[i]![j]!;
      for (let k = 0; k < j; k++) s -= L[i]![k]! * L[j]![k]!;
      if (i === j) {
        // Floor to zero before sqrt; add jitter only on diagonal
        L[i]![j] = Math.sqrt(Math.max(s + jitter, 0));
      } else {
        L[i]![j] = L[j]![j]! > 1e-14 ? s / L[j]![j]! : 0;
      }
    }
  }
  return L;
}

function randn(rng: () => number): number {
  let u = 0;
  let v = 0;
  while (u === 0) u = rng();
  while (v === 0) v = rng();
  return Math.sqrt(-2.0 * Math.log(u)) * Math.cos(2.0 * Math.PI * v);
}

/**
 * Draw nDays daily returns from a multivariate normal with:
 *   mean  = annualReturns / 252
 *   cov   = annualCov / 252   (Σ_daily)
 *
 * Uses a Cholesky decomposition so portfolio statistics align with Σ.
 * Optionally accepts a seeded RNG for deterministic tests.
 */
export function synthesizeMVNDailyReturns(
  annualReturns: number[],
  annualCov: number[][],
  nDays: number,
  rng: () => number = Math.random
): number[][] {
  const n = annualReturns.length;
  const dailyMeans = annualReturns.map((r) => r / 252);
  // Σ_daily = Σ_annual / 252
  const dailyCov: number[][] = annualCov.map((row) => row.map((v) => v / 252));
  const L = cholesky(dailyCov);

  const perDay: number[][] = [];
  for (let d = 0; d < nDays; d++) {
    // z ~ N(0, I)
    const z = Array.from({ length: n }, () => randn(rng));
    // r = μ_daily + L @ z
    const row: number[] = dailyMeans.map((mu, i) => {
      let val = mu;
      for (let k = 0; k <= i; k++) val += L[i]![k]! * z[k]!;
      return val;
    });
    perDay.push(row);
  }
  return perDay;
}

function transpose(perDay: number[][]): number[][] {
  if (!perDay.length) return [];
  const n = perDay[0].length;
  const out: number[][] = Array.from({ length: n }, () => []);
  for (let d = 0; d < perDay.length; d++) {
    for (let i = 0; i < n; i++) {
      out[i].push(perDay[d][i]!);
    }
  }
  return out;
}

export function apiMarketPayloadToLabShape(
  payload: unknown,
  nDays = 252
): LabMarketData {
  if (!payload || typeof payload !== "object") {
    throw new Error("Invalid market data payload");
  }
  const p = payload as Record<string, unknown>;
  const assets = p.assets;
  const ret = p.returns;
  const cov = p.covariance;
  const sectors = p.sectors;
  const names = p.names;

  if (!Array.isArray(assets) || !Array.isArray(ret) || !Array.isArray(cov)) {
    throw new Error("Market data missing assets, returns, or covariance");
  }

  const returnsArr = ret as number[];
  const covM = cov as number[][];
  const sectorList = Array.isArray(sectors)
    ? (sectors as string[])
    : (assets as string[]).map(() => "Unknown");
  const nameList = Array.isArray(names)
    ? (names as string[])
    : (assets as string[]);

  const n = returnsArr.length;
  if (covM.length !== n || !covM[0] || covM[0].length !== n) {
    throw new Error("Covariance dimensions do not match returns");
  }

  const corr = buildCorrFromCov(covM);

  // Prefer real daily returns when the backend includes them
  const rawDailyDates = (p as Record<string, unknown>).daily_dates;
  const rawDailyReturns = (p as Record<string, unknown>).daily_returns;
  const hasRealDailies =
    Array.isArray(rawDailyDates) &&
    Array.isArray(rawDailyReturns) &&
    (rawDailyReturns as number[][]).length > 1 &&
    Array.isArray((rawDailyReturns as number[][])[0]) &&
    (rawDailyReturns as number[][])[0]!.length === n;

  let byAsset: number[][];
  let returnsSource: ReturnsSource;

  if (hasRealDailies) {
    // Transpose T×n rows into n×T per-asset arrays
    const rows = rawDailyReturns as number[][];
    byAsset = Array.from({ length: n }, (_, i) => rows.map((row) => row[i] ?? 0));
    returnsSource = "historical";
  } else {
    const perDay = synthesizeMVNDailyReturns(returnsArr, covM, nDays);
    byAsset = transpose(perDay);
    returnsSource = "mvn_synthetic";
  }

  // Parse covariance_source from the API payload; fall back to full_window for
  // legacy responses that pre-date this field.
  const rawCovSource = (p as Record<string, unknown>).covariance_source;
  const covarianceSource: CovarianceSource =
    rawCovSource === "panel_aligned" ? "panel_aligned" : "full_window";

  const labAssets: LabAsset[] = (assets as string[]).map((sym, i) => {
    const annR = returnsArr[i] ?? 0;
    const annVol = Math.sqrt(Math.max(covM[i]![i]!, 1e-12));
    const sharpe = annVol > 1e-9 ? annR / annVol : 0;
    return {
      name: nameList[i] || sym,
      sector: sectorList[i] || "Unknown",
      annReturn: annR,
      annVol,
      sharpe,
      returns: byAsset[i] ?? [],
    };
  });

  return {
    assets: labAssets,
    corr,
    regime: "live",
    returnsSource,
    covarianceSource,
  };
}
