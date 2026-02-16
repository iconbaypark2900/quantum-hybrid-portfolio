/**
 * Predefined scenario presets for the Index & ETF Tester.
 * Each scenario has: id, name, description, tickers, startDate, endDate.
 */

let _nextId = 1;
const id = () => String(_nextId++);

const SCENARIO_PRESETS = [
  {
    id: id(),
    name: "S&P 500",
    description: "Large-cap US equity index tracker",
    tickers: ["SPY"],
    startDate: "2020-01-01",
    endDate: "2024-12-31",
  },
  {
    id: id(),
    name: "Nasdaq 100",
    description: "Tech-heavy US equity index tracker",
    tickers: ["QQQ"],
    startDate: "2020-01-01",
    endDate: "2024-12-31",
  },
  {
    id: id(),
    name: "US Total Market",
    description: "Broad US equity exposure",
    tickers: ["VTI"],
    startDate: "2020-01-01",
    endDate: "2024-12-31",
  },
  {
    id: id(),
    name: "Small Cap",
    description: "US small-cap equities (Russell 2000)",
    tickers: ["IWM"],
    startDate: "2020-01-01",
    endDate: "2024-12-31",
  },
  {
    id: id(),
    name: "Dow Jones",
    description: "30 large-cap US blue chips",
    tickers: ["DIA"],
    startDate: "2020-01-01",
    endDate: "2024-12-31",
  },
  {
    id: id(),
    name: "International Developed",
    description: "Developed markets ex-US (FTSE)",
    tickers: ["VEA"],
    startDate: "2020-01-01",
    endDate: "2024-12-31",
  },
  {
    id: id(),
    name: "Emerging Markets",
    description: "Emerging market equities",
    tickers: ["VWO"],
    startDate: "2020-01-01",
    endDate: "2024-12-31",
  },
  {
    id: id(),
    name: "US Aggregate Bond",
    description: "US investment-grade bond market",
    tickers: ["BND"],
    startDate: "2020-01-01",
    endDate: "2024-12-31",
  },
  {
    id: id(),
    name: "60/40 Portfolio",
    description: "Classic 60% equity / 40% bond allocation",
    tickers: ["SPY", "BND"],
    startDate: "2020-01-01",
    endDate: "2024-12-31",
  },
  {
    id: id(),
    name: "Tech Giants",
    description: "Top-5 large-cap US tech stocks",
    tickers: ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"],
    startDate: "2020-01-01",
    endDate: "2024-12-31",
  },
  {
    id: id(),
    name: "Sector Rotation",
    description: "Major US sector ETFs",
    tickers: ["XLK", "XLF", "XLE", "XLV", "XLI"],
    startDate: "2020-01-01",
    endDate: "2024-12-31",
  },
  {
    id: id(),
    name: "Global Diversified",
    description: "US + international equity + bonds",
    tickers: ["VTI", "VEA", "VWO", "BND", "BNDX"],
    startDate: "2020-01-01",
    endDate: "2024-12-31",
  },
];

export default SCENARIO_PRESETS;
