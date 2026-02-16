import axios from 'axios';
import api, {
  fetchMarketData,
  optimizePortfolio,
  runBacktest,
  runBacktestBatch,
  getObjectives,
  getPresets,
  getConstraintsSchema,
  getEfficientFrontier,
  healthCheck,
} from './api';

// Mock axios methods on the api instance
jest.mock('axios', () => {
  const mockAxios = {
    create: jest.fn(() => mockAxios),
    post: jest.fn(),
    get: jest.fn(),
    interceptors: {
      request: { use: jest.fn() },
      response: { use: jest.fn() },
    },
  };
  return { __esModule: true, default: mockAxios };
});

// Re-import after mock
const mockApi = require('axios').default;

describe('API service functions', () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('fetchMarketData', () => {
    test('sends POST with tickers array', async () => {
      mockApi.post.mockResolvedValue({ data: { assets: [] } });
      const result = await fetchMarketData(['AAPL', 'MSFT'], '2023-01-01', '2024-01-01');
      expect(mockApi.post).toHaveBeenCalledWith('/api/market-data', {
        tickers: ['AAPL', 'MSFT'],
        start_date: '2023-01-01',
        end_date: '2024-01-01',
      });
      expect(result).toEqual({ assets: [] });
    });

    test('parses comma-separated string into array', async () => {
      mockApi.post.mockResolvedValue({ data: {} });
      await fetchMarketData('AAPL, MSFT, GOOGL');
      expect(mockApi.post).toHaveBeenCalledWith('/api/market-data', {
        tickers: ['AAPL', 'MSFT', 'GOOGL'],
        start_date: null,
        end_date: null,
      });
    });
  });

  describe('optimizePortfolio', () => {
    test('sends POST with params', async () => {
      const params = { tickers: ['AAPL'], omega: 0.3 };
      mockApi.post.mockResolvedValue({ data: { qsw_result: {} } });
      const result = await optimizePortfolio(params);
      expect(mockApi.post).toHaveBeenCalledWith('/api/portfolio/optimize', params);
      expect(result).toEqual({ qsw_result: {} });
    });
  });

  describe('runBacktest', () => {
    test('sends POST with params', async () => {
      const params = { tickers: ['AAPL'], start_date: '2023-01-01' };
      mockApi.post.mockResolvedValue({ data: { results: [] } });
      const result = await runBacktest(params);
      expect(mockApi.post).toHaveBeenCalledWith('/api/portfolio/backtest', params);
      expect(result).toEqual({ results: [] });
    });
  });

  describe('runBacktestBatch', () => {
    test('sends POST to batch endpoint with requests and stop_on_error', async () => {
      const mockResponse = {
        count: 2,
        results: [
          { index: 0, status: 'ok', result: {} },
          { index: 1, status: 'ok', result: {} },
        ],
      };
      mockApi.post.mockResolvedValue({ data: mockResponse });
      const requests = [
        { tickers: ['SPY'], start_date: '2020-01-01', end_date: '2024-01-01' },
      ];
      const result = await runBacktestBatch(requests, true);
      expect(mockApi.post).toHaveBeenCalledWith('/api/portfolio/backtest/batch', {
        requests,
        stop_on_error: true,
      });
      expect(result).toEqual(mockResponse);
    });

    test('defaults stop_on_error to false', async () => {
      mockApi.post.mockResolvedValue({ data: { count: 1, results: [] } });
      await runBacktestBatch([{ tickers: ['QQQ'], start_date: '2020-01-01', end_date: '2024-01-01' }]);
      const callBody = mockApi.post.mock.calls[0][1];
      expect(callBody.stop_on_error).toBe(false);
    });
  });

  describe('getEfficientFrontier', () => {
    test('sends POST with tickers and dates', async () => {
      mockApi.post.mockResolvedValue({ data: { frontier: [] } });
      const result = await getEfficientFrontier(['AAPL', 'MSFT'], '2023-01-01', '2024-01-01', 20);
      expect(mockApi.post).toHaveBeenCalledWith('/api/portfolio/efficient-frontier', {
        tickers: ['AAPL', 'MSFT'],
        start_date: '2023-01-01',
        end_date: '2024-01-01',
        n_points: 20,
      });
      expect(result).toEqual({ frontier: [] });
    });

    test('defaults to 15 points', async () => {
      mockApi.post.mockResolvedValue({ data: {} });
      await getEfficientFrontier('AAPL,MSFT', '2023-01-01', '2024-01-01');
      const callArgs = mockApi.post.mock.calls[0][1];
      expect(callArgs.n_points).toBe(15);
    });
  });

  describe('config endpoints', () => {
    test('getObjectives calls correct endpoint', async () => {
      mockApi.get.mockResolvedValue({ data: { objectives: [] } });
      const result = await getObjectives();
      expect(mockApi.get).toHaveBeenCalledWith('/api/config/objectives');
      expect(result).toEqual({ objectives: [] });
    });

    test('getPresets calls correct endpoint', async () => {
      mockApi.get.mockResolvedValue({ data: { presets: {} } });
      const result = await getPresets();
      expect(mockApi.get).toHaveBeenCalledWith('/api/config/presets');
      expect(result).toEqual({ presets: {} });
    });

    test('getConstraintsSchema calls correct endpoint', async () => {
      mockApi.get.mockResolvedValue({ data: { schema: {} } });
      const result = await getConstraintsSchema();
      expect(mockApi.get).toHaveBeenCalledWith('/api/config/constraints');
      expect(result).toEqual({ schema: {} });
    });
  });

  describe('healthCheck', () => {
    test('calls correct endpoint and returns data', async () => {
      mockApi.get.mockResolvedValue({ data: { status: 'healthy' } });
      const result = await healthCheck();
      expect(mockApi.get).toHaveBeenCalledWith('/api/health');
      expect(result).toEqual({ status: 'healthy' });
    });
  });
});
