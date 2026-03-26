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

export type LabMarketData = {
  assets: LabAsset[];
  corr: number[][];
  regime: string;
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

/** Simple IID daily path for visualization (API gives annual stats only). */
function synthesizeDailyReturns(
  annualReturns: number[],
  cov: number[][],
  nDays: number
): number[][] {
  const n = annualReturns.length;
  const dailyMeans = annualReturns.map((r) => r / 252);
  const dailyVols = cov.map((row, i) =>
    Math.sqrt(Math.max(row[i] ?? 0, 1e-12)) / Math.sqrt(252)
  );
  const perDay: number[][] = [];
  for (let d = 0; d < nDays; d++) {
    const row: number[] = [];
    for (let i = 0; i < n; i++) {
      const z = randn();
      row.push(dailyMeans[i] + z * dailyVols[i]);
    }
    perDay.push(row);
  }
  return perDay;
}

function randn(): number {
  let u = 0;
  let v = 0;
  while (u === 0) u = Math.random();
  while (v === 0) v = Math.random();
  return Math.sqrt(-2.0 * Math.log(u)) * Math.cos(2.0 * Math.PI * v);
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
  const perDay = synthesizeDailyReturns(returnsArr, covM, nDays);
  const byAsset = transpose(perDay);

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
  };
}
