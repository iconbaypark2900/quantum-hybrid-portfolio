/**
 * Simulation engine for the Quantum Portfolio Lab.
 * Contains seeded random, market data generation, QSW optimization,
 * benchmark runners, equity curve simulation, VaR computation, and helpers.
 */

// ─── SEEDED RANDOM ───
let seed = 42;

export function seededRandom() {
  seed = (seed * 16807 + 0) % 2147483647;
  return (seed - 1) / 2147483646;
}

export function resetSeed(s = 42) {
  seed = s;
}

// ─── DEFAULT TICKERS / SECTORS ───
export const DEFAULT_TICKERS = [
  "AAPL","MSFT","GOOGL","AMZN","META","NVDA","TSLA","JPM","V","JNJ",
  "PG","UNH","HD","MA","BAC","DIS","NFLX","KO","PFE","CVX",
  "WMT","MRK","ABT","ADBE","NKE","PEP","T","VZ","PYPL","BRK",
];

export const DEFAULT_SECTORS = [
  "Tech","Tech","Tech","Tech","Tech","Tech","Tech","Finance","Finance","Health",
  "Consumer","Health","Consumer","Finance","Finance","Consumer","Tech","Consumer",
  "Health","Energy","Consumer","Health","Health","Tech","Consumer","Consumer",
  "Telecom","Telecom","Tech","Finance",
];

// ─── MARKET DATA GENERATION ───
export function generateMarketData(nAssets, nDays, regime, seedVal, customTickerList) {
  resetSeed(seedVal);
  const regimeParams = {
    bull:     { drift:  0.0008, vol: 0.012, corrBase: 0.3 },
    bear:     { drift: -0.0003, vol: 0.022, corrBase: 0.6 },
    volatile: { drift:  0.0002, vol: 0.028, corrBase: 0.45 },
    normal:   { drift:  0.0004, vol: 0.015, corrBase: 0.35 },
  };
  const { drift, vol, corrBase } = regimeParams[regime];
  const rawNames = (Array.isArray(customTickerList) && customTickerList.length > 0) ? customTickerList : DEFAULT_TICKERS;
  const names = [];
  for (let i = 0; i < nAssets; i++) names.push(rawNames[i] || `A${i}`);
  const sectors = DEFAULT_SECTORS;
  const assets = [];
  for (let i = 0; i < nAssets; i++) {
    const assetDrift = drift + (seededRandom() - 0.4) * 0.001;
    const assetVol = vol * (0.7 + seededRandom() * 0.6);
    const returns = [];
    for (let d = 0; d < nDays; d++) {
      const r = assetDrift + assetVol * (seededRandom() + seededRandom() + seededRandom() - 1.5) * 0.816;
      returns.push(r);
    }
    const annReturn = returns.reduce((a, b) => a + b, 0) / nDays * 252;
    const annVol = Math.sqrt(returns.map(r => r * r).reduce((a, b) => a + b, 0) / nDays) * Math.sqrt(252);
    assets.push({ name: names[i] || `A${i}`, sector: sectors[i] || "Other", returns, annReturn, annVol, sharpe: annReturn / (annVol || 1) });
  }
  const corr = [];
  for (let i = 0; i < nAssets; i++) {
    corr[i] = [];
    for (let j = 0; j < nAssets; j++) {
      if (i === j) corr[i][j] = 1;
      else if (j < i) corr[i][j] = corr[j][i];
      else {
        const sameSector = sectors[i] === sectors[j] ? 0.2 : 0;
        corr[i][j] = Math.max(-0.3, Math.min(0.95, corrBase + sameSector + (seededRandom() - 0.5) * 0.4));
      }
    }
  }
  return { assets, corr, regime };
}

// ─── HELPER METRICS ───
export function calculatePortfolioScore(weights, data, objective) {
  const n = data.assets.length;
  let portReturn = 0, portVar = 0;
  for (let i = 0; i < n; i++) {
    portReturn += weights[i] * data.assets[i].annReturn;
    for (let j = 0; j < n; j++) {
      portVar += weights[i] * weights[j] * data.corr[i][j] * data.assets[i].annVol * data.assets[j].annVol;
    }
  }
  const portVol = Math.sqrt(Math.max(0, portVar));
  const sharpe = portReturn / (portVol || 1);
  const diversification = 1 / (weights.reduce((a, b) => a + b * b, 0) || 1);
  switch (objective) {
    case 'diversification':
      return sharpe * 0.7 + diversification * 0.3;
    case 'momentum': {
      const momentumScore = weights.reduce((sum, w, i) => sum + w * data.assets[i].sharpe, 0);
      return sharpe * 0.6 + momentumScore * 0.4;
    }
    case 'conservative':
      return (sharpe > 0 ? sharpe : 0) * 0.8 + (1 / (portVol || 1)) * 0.2;
    default:
      return sharpe * 0.5 + diversification * 0.3 + (portReturn > 0 ? portReturn : 0) * 0.2;
  }
}

export function calculateDiversificationRatio(weights, data) {
  const portfolioVol = Math.sqrt(weights.reduce((variance, wi, i) => {
    return variance + wi * wi * data.assets[i].annVol * data.assets[i].annVol +
      weights.reduce((innerSum, wj, j) => {
        if (i !== j) return innerSum + wi * wj * data.corr[i][j] * data.assets[i].annVol * data.assets[j].annVol;
        return innerSum;
      }, 0);
  }, 0));
  const weightedAvgVol = weights.reduce((sum, w, i) => sum + w * data.assets[i].annVol, 0);
  return portfolioVol > 0 ? weightedAvgVol / portfolioVol : 1.0;
}

export function calculateInformationRatio(weights, data) {
  const n = data.assets.length;
  const equalWeights = new Array(n).fill(1 / n);
  const portfolioReturn = weights.reduce((sum, w, i) => sum + w * data.assets[i].annReturn, 0);
  const benchmarkReturn = equalWeights.reduce((sum, w, i) => sum + w * data.assets[i].annReturn, 0);
  let trackingError = 0;
  for (let i = 0; i < n; i++) {
    for (let j = 0; j < n; j++) {
      trackingError += (weights[i] - equalWeights[i]) * (weights[j] - equalWeights[j]) *
        data.corr[i][j] * data.assets[i].annVol * data.assets[j].annVol;
    }
  }
  trackingError = Math.sqrt(Math.max(0, trackingError));
  const excessReturn = portfolioReturn - benchmarkReturn;
  return trackingError > 0 ? excessReturn / trackingError : 0;
}

export function calculateAlpha(weights, data) {
  const n = data.assets.length;
  const portfolioReturn = weights.reduce((sum, w, i) => sum + w * data.assets[i].annReturn, 0);
  const benchmarkReturn = data.assets.reduce((sum, asset) => sum + asset.annReturn, 0) / n;
  return portfolioReturn - benchmarkReturn;
}

export function calculateBeta(weights, data) {
  const n = data.assets.length;
  const marketWeights = new Array(n).fill(1 / n);
  let marketVar = 0;
  for (let i = 0; i < n; i++) {
    for (let j = 0; j < n; j++) {
      marketVar += marketWeights[i] * marketWeights[j] * data.corr[i][j] * data.assets[i].annVol * data.assets[j].annVol;
    }
  }
  let cov = 0;
  for (let i = 0; i < n; i++) {
    for (let j = 0; j < n; j++) {
      cov += weights[i] * marketWeights[j] * data.corr[i][j] * data.assets[i].annVol * data.assets[j].annVol;
    }
  }
  return marketVar > 0 ? cov / marketVar : 1.0;
}

export function calculateRiskContributions(weights, data) {
  const n = data.assets.length;
  const portfolioVol = Math.sqrt(weights.reduce((variance, wi, i) => {
    return variance + wi * wi * data.assets[i].annVol * data.assets[i].annVol +
      weights.reduce((innerSum, wj, j) => {
        if (i !== j) return innerSum + wi * wj * data.corr[i][j] * data.assets[i].annVol * data.assets[j].annVol;
        return innerSum;
      }, 0);
  }, 0));
  const contributions = [];
  for (let i = 0; i < n; i++) {
    let marginalContribution = 0;
    for (let j = 0; j < n; j++) {
      marginalContribution += weights[j] * data.corr[i][j] * data.assets[i].annVol * data.assets[j].annVol;
    }
    contributions.push(weights[i] * marginalContribution / (portfolioVol || 1));
  }
  return contributions;
}

export function calculateSectorExposures(weights, data) {
  const sectors = {};
  for (let i = 0; i < data.assets.length; i++) {
    const sector = data.assets[i].sector || 'Unknown';
    sectors[sector] = (sectors[sector] || 0) + (weights[i] || 0);
  }
  return sectors;
}

export function calculateSharpe(weights, data) {
  const n = data.assets.length;
  let portReturn = 0, portVar = 0;
  for (let i = 0; i < n; i++) {
    portReturn += weights[i] * data.assets[i].annReturn;
    for (let j = 0; j < n; j++) {
      portVar += weights[i] * weights[j] * data.corr[i][j] * data.assets[i].annVol * data.assets[j].annVol;
    }
  }
  const portVol = Math.sqrt(Math.max(0, portVar));
  return portReturn / (portVol || 1);
}

// ─── QSW OPTIMIZATION ───
export function runEnhancedQSWOptimization(data, omega, evolutionTime, maxWeight, turnoverLimit, evolutionMethod = 'continuous', objective = 'balanced') {
  const n = data.assets.length;
  const weights = new Array(n).fill(0);
  const sharpes = data.assets.map(a => Math.max(0.01, a.sharpe + 0.5));
  const totalSharpe = sharpes.reduce((a, b) => a + b, 0);

  for (let i = 0; i < n; i++) {
    let potential = sharpes[i] / totalSharpe;
    let coupling = 0;
    for (let j = 0; j < n; j++) {
      if (i !== j) {
        const diversBenefit = (1 - Math.abs(data.corr[i][j])) * sharpes[j] / totalSharpe;
        coupling += diversBenefit;
      }
    }
    weights[i] = (1 - omega) * potential + omega * coupling / (n - 1);
  }

  switch (evolutionMethod) {
    case 'discrete': {
      const dtSteps = evolutionTime * 2;
      for (let step = 0; step < dtSteps; step++) {
        const newWeights = [...weights];
        for (let i = 0; i < n; i++) {
          let neighborSum = 0;
          let neighborCount = 0;
          for (let j = 0; j < n; j++) {
            if (i !== j && Math.abs(data.corr[i][j]) > 0.1) { neighborSum += weights[j]; neighborCount++; }
          }
          if (neighborCount > 0) newWeights[i] = (weights[i] + neighborSum / neighborCount) / 2;
        }
        for (let i = 0; i < n; i++) weights[i] = newWeights[i];
      }
      break;
    }
    case 'decoherent': {
      const decoherenceRate = 0.15;
      for (let i = 0; i < n; i++) weights[i] = (1 - decoherenceRate) * weights[i] + decoherenceRate * (1 / n);
      break;
    }
    case 'adiabatic': {
      const adiabaticSteps = evolutionTime * 3;
      for (let step = 0; step < adiabaticSteps; step++) {
        const s = step / adiabaticSteps;
        const currentOmega = omega * s;
        for (let i = 0; i < n; i++) {
          let potential = sharpes[i] / totalSharpe;
          let coupling = 0;
          for (let j = 0; j < n; j++) {
            if (i !== j) {
              const diversBenefit = (1 - Math.abs(data.corr[i][j])) * sharpes[j] / totalSharpe;
              coupling += diversBenefit;
            }
          }
          weights[i] = (1 - currentOmega) * potential + currentOmega * coupling / (n - 1);
        }
      }
      break;
    }
    case 'variational': {
      let bestWeights = [...weights];
      let bestScore = calculatePortfolioScore(weights, data, objective);
      for (let trial = 0; trial < 5; trial++) {
        const trialOmega = omega * (0.8 + seededRandom() * 0.4);
        const trialWeights = new Array(n).fill(0);
        for (let i = 0; i < n; i++) {
          let potential = sharpes[i] / totalSharpe;
          let coupling = 0;
          for (let j = 0; j < n; j++) {
            if (i !== j) {
              const diversBenefit = (1 - Math.abs(data.corr[i][j])) * sharpes[j] / totalSharpe;
              coupling += diversBenefit;
            }
          }
          trialWeights[i] = (1 - trialOmega) * potential + trialOmega * coupling / (n - 1);
        }
        for (let i = 0; i < n; i++) trialWeights[i] = Math.min(trialWeights[i], maxWeight);
        for (let i = 0; i < n; i++) if (trialWeights[i] < 0.005) trialWeights[i] = 0;
        const trialSum = trialWeights.reduce((a, b) => a + b, 0);
        if (trialSum > 0) for (let i = 0; i < n; i++) trialWeights[i] /= trialSum;
        const trialScore = calculatePortfolioScore(trialWeights, data, objective);
        if (trialScore > bestScore) { bestScore = trialScore; bestWeights = [...trialWeights]; }
      }
      for (let i = 0; i < n; i++) weights[i] = bestWeights[i];
      break;
    }
    default: {
      const smoothFactor = Math.exp(-evolutionTime / 50);
      const equalW = 1 / n;
      for (let i = 0; i < n; i++) weights[i] = weights[i] * (1 - smoothFactor) + equalW * smoothFactor;
    }
  }

  switch (objective) {
    case 'diversification':
      for (let i = 0; i < n; i++) weights[i] = Math.min(weights[i], maxWeight * 0.8);
      break;
    case 'momentum':
      for (let i = 0; i < n; i++) weights[i] = Math.min(weights[i], maxWeight * 1.2);
      break;
    case 'conservative':
      for (let i = 0; i < n; i++) weights[i] = Math.min(weights[i], maxWeight * 0.7);
      break;
    default:
      for (let i = 0; i < n; i++) weights[i] = Math.min(weights[i], maxWeight);
  }

  for (let i = 0; i < n; i++) if (weights[i] < 0.005) weights[i] = 0;
  const sum = weights.reduce((a, b) => a + b, 0);
  if (sum === 0) { for (let i = 0; i < n; i++) weights[i] = 1 / n; }
  else { for (let i = 0; i < n; i++) weights[i] /= sum; }

  let portReturn = 0, portVar = 0;
  for (let i = 0; i < n; i++) {
    portReturn += weights[i] * data.assets[i].annReturn;
    for (let j = 0; j < n; j++) {
      portVar += weights[i] * weights[j] * data.corr[i][j] * data.assets[i].annVol * data.assets[j].annVol;
    }
  }
  const portVol = Math.sqrt(Math.max(0, portVar));
  const sharpe = portReturn / (portVol || 1);

  return {
    weights, portReturn, portVol, sharpe,
    nActive: weights.filter(w => w > 0.005).length,
    diversificationRatio: calculateDiversificationRatio(weights, data),
    informationRatio: calculateInformationRatio(weights, data),
    alpha: calculateAlpha(weights, data),
    beta: calculateBeta(weights, data),
    riskContributions: calculateRiskContributions(weights, data),
    sectorExposures: calculateSectorExposures(weights, data),
  };
}

// ─── QUANTUM ANNEALING ───
export function runQuantumAnnealingOptimization(data, maxWeight) {
  const n = data.assets.length;
  const weights = new Array(n).fill(0);
  for (let i = 0; i < n; i++) weights[i] = seededRandom();
  const sum = weights.reduce((a, b) => a + b, 0);
  for (let i = 0; i < n; i++) weights[i] /= sum;

  const iterations = 100;
  let currentSharpe = calculateSharpe(weights, data);
  for (let iter = 0; iter < iterations; iter++) {
    const neighborWeights = [...weights];
    const temp = 100 * Math.exp(-iter / 20);
    for (let i = 0; i < n; i++) {
      neighborWeights[i] += (seededRandom() - 0.5) * 0.1;
      neighborWeights[i] = Math.max(0, Math.min(maxWeight, neighborWeights[i]));
    }
    const neighborSum = neighborWeights.reduce((a, b) => a + b, 0);
    for (let i = 0; i < n; i++) neighborWeights[i] /= neighborSum;
    const neighborSharpe = calculateSharpe(neighborWeights, data);
    if (neighborSharpe > currentSharpe || Math.exp(-(currentSharpe - neighborSharpe) / temp) > seededRandom()) {
      for (let i = 0; i < n; i++) weights[i] = neighborWeights[i];
      currentSharpe = neighborSharpe;
    }
  }

  for (let i = 0; i < n; i++) weights[i] = Math.min(weights[i], maxWeight);
  for (let i = 0; i < n; i++) if (weights[i] < 0.005) weights[i] = 0;
  const finalSum = weights.reduce((a, b) => a + b, 0);
  if (finalSum > 0) for (let i = 0; i < n; i++) weights[i] /= finalSum;

  let portReturn = 0, portVar = 0;
  for (let i = 0; i < n; i++) {
    portReturn += weights[i] * data.assets[i].annReturn;
    for (let j = 0; j < n; j++) {
      portVar += weights[i] * weights[j] * data.corr[i][j] * data.assets[i].annVol * data.assets[j].annVol;
    }
  }
  const portVol = Math.sqrt(Math.max(0, portVar));
  const sharpe = portReturn / (portVol || 1);

  return {
    weights, portReturn, portVol, sharpe,
    nActive: weights.filter(w => w > 0.005).length,
    diversificationRatio: calculateDiversificationRatio(weights, data),
    informationRatio: calculateInformationRatio(weights, data),
    alpha: calculateAlpha(weights, data),
    beta: calculateBeta(weights, data),
    riskContributions: calculateRiskContributions(weights, data),
    sectorExposures: calculateSectorExposures(weights, data),
  };
}

// ─── HRP (Hierarchical Risk Parity - López de Prado) ───
function computeHRPWeights(data) {
  const n = data.assets.length;
  if (n <= 1) return new Array(n).fill(1);

  const dist = [];
  for (let i = 0; i < n; i++) {
    dist[i] = [];
    for (let j = 0; j < n; j++) {
      dist[i][j] = Math.sqrt(0.5 * (1 - (data.corr[i]?.[j] ?? (i === j ? 1 : 0))));
    }
  }

  const clusters = Array.from({ length: n }, (_, i) => [i]);
  const active = new Array(n).fill(true);

  while (active.filter(Boolean).length > 1) {
    let minDist = Infinity, mergeA = -1, mergeB = -1;
    for (let i = 0; i < clusters.length; i++) {
      if (!active[i]) continue;
      for (let j = i + 1; j < clusters.length; j++) {
        if (!active[j]) continue;
        let d = Infinity;
        for (const a of clusters[i]) {
          for (const b of clusters[j]) {
            d = Math.min(d, dist[a][b]);
          }
        }
        if (d < minDist) { minDist = d; mergeA = i; mergeB = j; }
      }
    }
    if (mergeA < 0) break;
    clusters.push([...clusters[mergeA], ...clusters[mergeB]]);
    active.push(true);
    active[mergeA] = false;
    active[mergeB] = false;
  }

  const sortedIndices = clusters[clusters.length - 1] || Array.from({ length: n }, (_, i) => i);

  function clusterVariance(indices) {
    if (indices.length === 0) return 1;
    const invV = indices.map(i => 1 / (data.assets[i].annVol * data.assets[i].annVol || 1));
    const ivSum = invV.reduce((a, b) => a + b, 0) || 1;
    const w = invV.map(v => v / ivSum);
    let variance = 0;
    for (let ii = 0; ii < indices.length; ii++) {
      for (let jj = 0; jj < indices.length; jj++) {
        const i = indices[ii], j = indices[jj];
        variance += w[ii] * w[jj] * (data.corr[i]?.[j] ?? (i === j ? 1 : 0)) * data.assets[i].annVol * data.assets[j].annVol;
      }
    }
    return Math.max(1e-10, variance);
  }

  const weights = new Array(n).fill(1);

  function recursiveBisect(items) {
    if (items.length <= 1) return;
    const mid = Math.floor(items.length / 2);
    const left = items.slice(0, mid);
    const right = items.slice(mid);
    const vL = clusterVariance(left);
    const vR = clusterVariance(right);
    const alpha = 1 - vL / (vL + vR);
    for (const i of left) weights[i] *= alpha;
    for (const i of right) weights[i] *= (1 - alpha);
    recursiveBisect(left);
    recursiveBisect(right);
  }

  recursiveBisect(sortedIndices);

  const sum = weights.reduce((a, b) => a + b, 0) || 1;
  return weights.map(w => w / sum);
}

// ─── BENCHMARKS ───
export function runBenchmarks(data) {
  const n = data.assets.length;
  const calc = (w) => {
    let r = 0, v = 0;
    for (let i = 0; i < n; i++) { r += w[i] * data.assets[i].annReturn; for (let j = 0; j < n; j++) v += w[i] * w[j] * data.corr[i][j] * data.assets[i].annVol * data.assets[j].annVol; }
    const vol = Math.sqrt(Math.max(0, v));
    return { weights: w, portReturn: r, portVol: vol, sharpe: r / (vol || 1) };
  };
  const ew = new Array(n).fill(1 / n);
  const invVol = data.assets.map(a => 1 / (a.annVol || 1));
  const ivSum = invVol.reduce((a, b) => a + b, 0);
  const mv = invVol.map(v => v / ivSum);
  const riskBudget = data.assets.map(a => 1 / (a.annVol * a.annVol || 1));
  const rbSum = riskBudget.reduce((a, b) => a + b, 0);
  const rp = riskBudget.map(v => v / rbSum);
  const sharpeW = data.assets.map(a => Math.max(0, a.sharpe));
  const swSum = sharpeW.reduce((a, b) => a + b, 0) || 1;
  const ms = sharpeW.map(v => v / swSum);
  const hrpW = computeHRPWeights(data);

  return {
    equalWeight: { name: "Equal Weight", ...calc(ew) },
    minVariance: { name: "Min Variance", ...calc(mv) },
    riskParity: { name: "Risk Parity", ...calc(rp) },
    maxSharpe: { name: "Max Sharpe", ...calc(ms) },
    hrp: { name: "HRP", ...calc(hrpW) },
  };
}

// ─── UNIFIED OPTIMISATION DISPATCHER ───
export function runOptimisation(data, opts = {}) {
  const { objective = "hybrid", K, KScreen, KSelect, wMax = 0.20 } = opts;
  const n = data.assets.length;
  const maxWeight = wMax;

  switch (objective) {
    case "equal_weight": {
      const w = new Array(n).fill(1 / n);
      return _metrics(w, data, null);
    }
    case "markowitz":
    case "min_variance":
    case "target_return": {
      const r = runEnhancedQSWOptimization(data, 0.3, 10, maxWeight, 0.2, "continuous", objective === "markowitz" ? "balanced" : "conservative");
      return _metrics(r.weights, data, null);
    }
    case "hrp": {
      const w = computeHRPWeights(data);
      return _metrics(w, data, null);
    }
    case "qubo_sa": {
      const k = K || Math.min(Math.ceil(n * 0.4), 8);
      const selected = data.assets.map((a, i) => ({ i, score: a.sharpe })).sort((a, b) => b.score - a.score).slice(0, k).map(x => x.i);
      const w = new Array(n).fill(0);
      selected.forEach(i => { w[i] = 1 / k; });
      return _metrics(w, data, { stage2_selected_idx: selected, stage2_qubo_obj: 0, stage1_screened_count: n, stage3_sharpe: 0 });
    }
    case "vqe": {
      const r = runEnhancedQSWOptimization(data, 0.25, 8, maxWeight, 0.2, "continuous", "balanced");
      return _metrics(r.weights, data, null);
    }
    case "hybrid":
    default: {
      const kScr = KScreen || Math.min(Math.ceil(n * 0.6), 15);
      const kSel = KSelect || Math.min(Math.ceil(kScr * 0.5), 5);
      const screened = data.assets.map((a, i) => ({ i, score: a.sharpe + (1 - a.annVol) * 0.5 })).sort((a, b) => b.score - a.score).slice(0, kScr);
      const selected = screened.slice(0, kSel);
      const w = new Array(n).fill(0);
      selected.forEach(s => { w[s.i] = 1 / kSel; });
      const selectedNames = selected.map(s => data.assets[s.i].name);
      const r = _metrics(w, data, {
        stage1_screened_count: kScr,
        stage2_selected_idx: selected.map(s => s.i),
        stage2_selected_names: selectedNames,
        stage2_qubo_obj: 0,
        stage3_sharpe: 0,
      });
      if (r.stage_info) r.stage_info.stage3_sharpe = r.sharpe;
      return r;
    }
  }
}

function _metrics(weights, data, stageInfo) {
  const n = data.assets.length;
  let portReturn = 0, portVar = 0;
  for (let i = 0; i < n; i++) {
    portReturn += weights[i] * data.assets[i].annReturn;
    for (let j = 0; j < n; j++) {
      portVar += weights[i] * weights[j] * data.corr[i][j] * data.assets[i].annVol * data.assets[j].annVol;
    }
  }
  const portVol = Math.sqrt(Math.max(0, portVar));
  return { weights, portReturn, portVol, sharpe: portReturn / (portVol || 1), nActive: weights.filter(w => w > 0.005).length, stage_info: stageInfo };
}

/**
 * Portfolio metrics from a weight vector (same Σ, μ as runOptimisation) — no optimizer call.
 * @param {number[]} weights
 * @param {object} data lab data with assets + corr
 */
export function portfolioMetricsFromWeights(weights, data) {
  const w = weights.map((x) => Number(x) || 0);
  return _metrics(w, data, null);
}

/**
 * Clip each weight to [wMin, wMax], then renormalize so sum ≈ 1 (two passes for stability).
 * @param {number[]} weights
 * @param {number} wMin
 * @param {number} wMax
 * @returns {number[]}
 */
export function clipNormalizeWeights(weights, wMin, wMax) {
  const n = weights.length;
  if (n === 0) return [];
  let w = weights.map((x) => Math.max(wMin, Math.min(wMax, Number(x) || 0)));
  let s = w.reduce((a, b) => a + b, 0);
  if (s <= 1e-15) {
    w = new Array(n).fill(1 / n);
    w = w.map((x) => Math.max(wMin, Math.min(wMax, x)));
    s = w.reduce((a, b) => a + b, 0);
  }
  if (s > 0) w = w.map((x) => x / s);
  w = w.map((x) => Math.max(wMin, Math.min(wMax, x)));
  s = w.reduce((a, b) => a + b, 0);
  if (s > 0) w = w.map((x) => x / s);
  return w;
}

export function computeHRPWeightsArr(data) {
  return computeHRPWeights(data);
}

// ─── EQUITY CURVE ───
export function simulateEquityCurve(data, weights, nDays) {
  const curve = [{ day: 0, value: 100 }];
  let val = 100;
  for (let d = 0; d < Math.min(nDays, data.assets[0]?.returns.length || 0); d++) {
    let dayReturn = 0;
    for (let i = 0; i < weights.length; i++) dayReturn += weights[i] * (data.assets[i]?.returns[d] || 0);
    val *= (1 + dayReturn);
    if (d % 5 === 0) curve.push({ day: d + 1, value: val });
  }
  return curve;
}

/**
 * Per-asset equity simulation: tracks each position's dollar value through time.
 * Returns { total: [{day,value}], perAsset: [{name,day0,...dayN}], finalPositions }.
 */
export function simulatePerAssetEquity(data, weights, nDays, notional = 100000) {
  const n = weights.length;
  const maxD = Math.min(nDays, data.assets[0]?.returns.length || 0);
  const positions = weights.map((w) => w * notional);
  const snapDays = [0];
  const totalCurve = [{ day: 0, value: notional }];

  for (let d = 0; d < maxD; d++) {
    for (let i = 0; i < n; i++) {
      positions[i] *= 1 + (data.assets[i]?.returns[d] || 0);
    }
    if (d % 5 === 0) {
      const day = d + 1;
      snapDays.push(day);
      totalCurve.push({ day, value: positions.reduce((a, b) => a + b, 0) });
    }
  }

  const finalTotal = positions.reduce((a, b) => a + b, 0);
  const finalPositions = data.assets.map((a, i) => ({
    name: a.name,
    sector: a.sector,
    initAlloc: weights[i] * notional,
    currentValue: positions[i],
    pnl: positions[i] - weights[i] * notional,
    pnlPct: weights[i] > 0 ? (positions[i] / (weights[i] * notional) - 1) * 100 : 0,
    weight: weights[i],
  }));

  return {
    total: totalCurve,
    finalPositions,
    summary: {
      notional,
      currentValue: finalTotal,
      totalPnl: finalTotal - notional,
      totalReturnPct: (finalTotal / notional - 1) * 100,
    },
  };
}

// ─── VaR ───
export function computeVaR(data, weights, confidence) {
  const n = weights.length;
  const nSim = 2000;
  const losses = [];
  resetSeed(123);
  for (let s = 0; s < nSim; s++) {
    let portReturn = 0;
    for (let i = 0; i < n; i++) {
      const dayIdx = Math.floor(seededRandom() * (data.assets[i]?.returns.length || 1));
      portReturn += weights[i] * (data.assets[i]?.returns[dayIdx] || 0);
    }
    losses.push(-portReturn);
  }
  losses.sort((a, b) => a - b);
  const varIdx = Math.floor(nSim * confidence);
  const var95 = losses[varIdx] || 0;
  const cvar = losses.slice(varIdx).reduce((a, b) => a + b, 0) / (nSim - varIdx || 1);
  return { var95: var95 * 100, cvar: cvar * 100 };
}
