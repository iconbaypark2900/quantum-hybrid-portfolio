/**
 * API service for Quantum Portfolio backend.
 * Default base URL assumes API runs on port 5000 (same host or via proxy).
 */
import axios from 'axios';
import { toast } from 'react-toastify';

const API_BASE = process.env.REACT_APP_API_URL || '';
const API_KEY = process.env.REACT_APP_API_KEY || '';

const defaultHeaders = { 'Content-Type': 'application/json' };
if (API_KEY) {
  defaultHeaders['X-API-Key'] = API_KEY;
}

const api = axios.create({
  baseURL: API_BASE,
  headers: defaultHeaders,
  timeout: 60000,
});

// ─── Response Interceptor ───
api.interceptors.response.use(
  (response) => {
    // Unwrap standardized envelope: { data: <payload>, meta: {...} }
    if (response.data && typeof response.data === 'object' && 'data' in response.data && 'meta' in response.data) {
      response.data = response.data.data;
    }
    return response;
  },
  async (error) => {
    const status = error.response?.status;
    const config = error.config;

    if (status === 401) {
      toast.error('Unauthorized (401). Check your API key configuration.');
    }

    if (status === 429) {
      toast.warn('Rate limited (429). Please slow down requests.');
    }

    // 5xx Server Error — retry once
    if (status >= 500 && !config._retried) {
      config._retried = true;
      toast.info('Server error — retrying once...');
      return api(config);
    }

    // Normalize error message from envelope or legacy format
    const respData = error.response?.data;
    const message =
      respData?.error?.message ||
      respData?.error ||
      respData?.message ||
      error.message ||
      'An unexpected error occurred';

    return Promise.reject(new Error(message));
  }
);

/** Fetch market data for given tickers */
export async function fetchMarketData(tickers, startDate = null, endDate = null) {
  const res = await api.post('/api/market-data', {
    tickers: Array.isArray(tickers) ? tickers : tickers.split(',').map(t => t.trim()).filter(Boolean),
    start_date: startDate,
    end_date: endDate,
  });
  return res.data;
}

/** Run portfolio optimization */
export async function optimizePortfolio(params) {
  const res = await api.post('/api/portfolio/optimize', params);
  return res.data;
}

/** Run backtest */
export async function runBacktest(params) {
  const res = await api.post('/api/portfolio/backtest', params);
  return res.data;
}

/** Run batch backtest for multiple scenarios */
export async function runBacktestBatch(requests, stopOnError = false) {
  const res = await api.post('/api/portfolio/backtest/batch', {
    requests,
    stop_on_error: stopOnError,
  });
  return res.data;
}

/** Run batch optimization for multiple parameter sets */
export async function optimizeBatch(requests, stopOnError = false) {
  const res = await api.post('/api/portfolio/optimize/batch', {
    requests,
    stop_on_error: stopOnError,
  });
  return res.data;
}

/** Get available objectives */
export async function getObjectives() {
  const res = await api.get('/api/config/objectives');
  return res.data;
}

/** Get available presets */
export async function getPresets() {
  const res = await api.get('/api/config/presets');
  return res.data;
}

/** Get constraints schema */
export async function getConstraintsSchema() {
  const res = await api.get('/api/config/constraints');
  return res.data;
}

/** Get efficient frontier */
export async function getEfficientFrontier(tickers, startDate, endDate, nPoints = 15) {
  const res = await api.post('/api/portfolio/efficient-frontier', {
    tickers: Array.isArray(tickers) ? tickers : tickers.split(',').map(t => t.trim()).filter(Boolean),
    start_date: startDate,
    end_date: endDate,
    n_points: nPoints,
  });
  return res.data;
}

/** Health check */
export async function healthCheck() {
  const res = await api.get('/api/health');
  return res.data;
}

/** Set IBM Quantum token */
export async function setIbmQuantumToken(token) {
  const res = await api.post('/api/quantum/ibm/token', { token });
  return res.data;
}

/** Clear IBM Quantum token */
export async function clearIbmQuantumToken() {
  const res = await api.delete('/api/quantum/ibm/token');
  return res.data;
}

/** Get IBM Quantum connection status */
export async function getIbmQuantumStatus() {
  const res = await api.get('/api/quantum/ibm/status');
  return res.data;
}

/** Get IBM Quantum workloads/jobs */
export async function getIbmQuantumWorkloads() {
  const res = await api.get('/api/quantum/ibm/workloads');
  return res.data;
}

export default api;
