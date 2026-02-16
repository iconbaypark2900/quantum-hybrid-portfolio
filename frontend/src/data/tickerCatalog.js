/**
 * Local ticker catalog for instant search/autocomplete.
 * Each entry: { symbol, name, sector, type }.
 * type: "stock" | "etf" | "index"
 *
 * Covers S&P 500 top ~100 by market cap, major sector/thematic ETFs, and broad indices.
 * Users can still type any ticker not in this catalog.
 */

const TICKER_CATALOG = [
  // ─── Major Indices / Broad ETFs ───
  { symbol: "SPY",  name: "SPDR S&P 500 ETF",               sector: "Broad Market",  type: "etf" },
  { symbol: "QQQ",  name: "Invesco Nasdaq 100 ETF",          sector: "Broad Market",  type: "etf" },
  { symbol: "DIA",  name: "SPDR Dow Jones Industrial ETF",   sector: "Broad Market",  type: "etf" },
  { symbol: "IWM",  name: "iShares Russell 2000 ETF",        sector: "Broad Market",  type: "etf" },
  { symbol: "VTI",  name: "Vanguard Total Stock Market ETF", sector: "Broad Market",  type: "etf" },
  { symbol: "VOO",  name: "Vanguard S&P 500 ETF",            sector: "Broad Market",  type: "etf" },
  { symbol: "IVV",  name: "iShares Core S&P 500 ETF",        sector: "Broad Market",  type: "etf" },
  { symbol: "MDY",  name: "SPDR S&P MidCap 400 ETF",         sector: "Broad Market",  type: "etf" },
  { symbol: "VXF",  name: "Vanguard Extended Market ETF",     sector: "Broad Market",  type: "etf" },

  // ─── International ETFs ───
  { symbol: "VEA",  name: "Vanguard FTSE Developed Markets",  sector: "International", type: "etf" },
  { symbol: "VWO",  name: "Vanguard FTSE Emerging Markets",   sector: "International", type: "etf" },
  { symbol: "EFA",  name: "iShares MSCI EAFE ETF",            sector: "International", type: "etf" },
  { symbol: "EEM",  name: "iShares MSCI Emerging Markets",    sector: "International", type: "etf" },
  { symbol: "VXUS", name: "Vanguard Total International ETF", sector: "International", type: "etf" },
  { symbol: "ACWI", name: "iShares MSCI ACWI ETF",            sector: "International", type: "etf" },

  // ─── Fixed Income ETFs ───
  { symbol: "BND",  name: "Vanguard Total Bond Market ETF",   sector: "Fixed Income",  type: "etf" },
  { symbol: "AGG",  name: "iShares Core US Aggregate Bond",   sector: "Fixed Income",  type: "etf" },
  { symbol: "TLT",  name: "iShares 20+ Year Treasury Bond",   sector: "Fixed Income",  type: "etf" },
  { symbol: "IEF",  name: "iShares 7-10 Year Treasury Bond",  sector: "Fixed Income",  type: "etf" },
  { symbol: "SHY",  name: "iShares 1-3 Year Treasury Bond",   sector: "Fixed Income",  type: "etf" },
  { symbol: "LQD",  name: "iShares Investment Grade Corp",    sector: "Fixed Income",  type: "etf" },
  { symbol: "HYG",  name: "iShares High Yield Corporate",     sector: "Fixed Income",  type: "etf" },
  { symbol: "BNDX", name: "Vanguard Total Intl Bond ETF",     sector: "Fixed Income",  type: "etf" },
  { symbol: "TIP",  name: "iShares TIPS Bond ETF",            sector: "Fixed Income",  type: "etf" },

  // ─── Sector ETFs ───
  { symbol: "XLK",  name: "Technology Select Sector SPDR",    sector: "Technology",    type: "etf" },
  { symbol: "XLF",  name: "Financial Select Sector SPDR",     sector: "Financials",    type: "etf" },
  { symbol: "XLE",  name: "Energy Select Sector SPDR",        sector: "Energy",        type: "etf" },
  { symbol: "XLV",  name: "Health Care Select Sector SPDR",   sector: "Healthcare",    type: "etf" },
  { symbol: "XLI",  name: "Industrial Select Sector SPDR",    sector: "Industrials",   type: "etf" },
  { symbol: "XLY",  name: "Consumer Discretionary SPDR",      sector: "Consumer Disc", type: "etf" },
  { symbol: "XLP",  name: "Consumer Staples Select SPDR",     sector: "Consumer Stpl", type: "etf" },
  { symbol: "XLU",  name: "Utilities Select Sector SPDR",     sector: "Utilities",     type: "etf" },
  { symbol: "XLB",  name: "Materials Select Sector SPDR",     sector: "Materials",     type: "etf" },
  { symbol: "XLRE", name: "Real Estate Select Sector SPDR",   sector: "Real Estate",   type: "etf" },
  { symbol: "XLC",  name: "Communication Services SPDR",      sector: "Communication", type: "etf" },

  // ─── Thematic / Factor ETFs ───
  { symbol: "ARKK", name: "ARK Innovation ETF",               sector: "Thematic",      type: "etf" },
  { symbol: "SOXX", name: "iShares Semiconductor ETF",        sector: "Technology",    type: "etf" },
  { symbol: "GLD",  name: "SPDR Gold Shares",                 sector: "Commodities",   type: "etf" },
  { symbol: "SLV",  name: "iShares Silver Trust",             sector: "Commodities",   type: "etf" },
  { symbol: "USO",  name: "United States Oil Fund",           sector: "Commodities",   type: "etf" },
  { symbol: "VNQ",  name: "Vanguard Real Estate ETF",         sector: "Real Estate",   type: "etf" },
  { symbol: "SCHD", name: "Schwab US Dividend Equity ETF",    sector: "Broad Market",  type: "etf" },

  // ─── Mega-Cap Technology ───
  { symbol: "AAPL", name: "Apple Inc.",                        sector: "Technology",    type: "stock" },
  { symbol: "MSFT", name: "Microsoft Corporation",             sector: "Technology",    type: "stock" },
  { symbol: "GOOGL",name: "Alphabet Inc. (Class A)",           sector: "Technology",    type: "stock" },
  { symbol: "GOOG", name: "Alphabet Inc. (Class C)",           sector: "Technology",    type: "stock" },
  { symbol: "AMZN", name: "Amazon.com Inc.",                   sector: "Consumer Disc", type: "stock" },
  { symbol: "NVDA", name: "NVIDIA Corporation",                sector: "Technology",    type: "stock" },
  { symbol: "META", name: "Meta Platforms Inc.",                sector: "Communication", type: "stock" },
  { symbol: "TSLA", name: "Tesla Inc.",                        sector: "Consumer Disc", type: "stock" },
  { symbol: "AVGO", name: "Broadcom Inc.",                     sector: "Technology",    type: "stock" },
  { symbol: "ADBE", name: "Adobe Inc.",                        sector: "Technology",    type: "stock" },
  { symbol: "CRM",  name: "Salesforce Inc.",                   sector: "Technology",    type: "stock" },
  { symbol: "ORCL", name: "Oracle Corporation",                sector: "Technology",    type: "stock" },
  { symbol: "CSCO", name: "Cisco Systems Inc.",                sector: "Technology",    type: "stock" },
  { symbol: "ACN",  name: "Accenture plc",                     sector: "Technology",    type: "stock" },
  { symbol: "INTC", name: "Intel Corporation",                 sector: "Technology",    type: "stock" },
  { symbol: "AMD",  name: "Advanced Micro Devices Inc.",       sector: "Technology",    type: "stock" },
  { symbol: "TXN",  name: "Texas Instruments Inc.",            sector: "Technology",    type: "stock" },
  { symbol: "QCOM", name: "Qualcomm Inc.",                     sector: "Technology",    type: "stock" },
  { symbol: "IBM",  name: "International Business Machines",   sector: "Technology",    type: "stock" },
  { symbol: "AMAT", name: "Applied Materials Inc.",            sector: "Technology",    type: "stock" },
  { symbol: "NOW",  name: "ServiceNow Inc.",                   sector: "Technology",    type: "stock" },
  { symbol: "INTU", name: "Intuit Inc.",                       sector: "Technology",    type: "stock" },
  { symbol: "MU",   name: "Micron Technology Inc.",            sector: "Technology",    type: "stock" },
  { symbol: "LRCX", name: "Lam Research Corporation",         sector: "Technology",    type: "stock" },
  { symbol: "KLAC", name: "KLA Corporation",                   sector: "Technology",    type: "stock" },
  { symbol: "SNPS", name: "Synopsys Inc.",                     sector: "Technology",    type: "stock" },
  { symbol: "CDNS", name: "Cadence Design Systems",           sector: "Technology",    type: "stock" },
  { symbol: "PANW", name: "Palo Alto Networks Inc.",           sector: "Technology",    type: "stock" },
  { symbol: "NFLX", name: "Netflix Inc.",                      sector: "Communication", type: "stock" },

  // ─── Financials ───
  { symbol: "JPM",  name: "JPMorgan Chase & Co.",              sector: "Financials",    type: "stock" },
  { symbol: "V",    name: "Visa Inc.",                          sector: "Financials",    type: "stock" },
  { symbol: "MA",   name: "Mastercard Inc.",                    sector: "Financials",    type: "stock" },
  { symbol: "BAC",  name: "Bank of America Corp.",              sector: "Financials",    type: "stock" },
  { symbol: "WFC",  name: "Wells Fargo & Company",              sector: "Financials",    type: "stock" },
  { symbol: "GS",   name: "Goldman Sachs Group Inc.",           sector: "Financials",    type: "stock" },
  { symbol: "MS",   name: "Morgan Stanley",                     sector: "Financials",    type: "stock" },
  { symbol: "BLK",  name: "BlackRock Inc.",                     sector: "Financials",    type: "stock" },
  { symbol: "SCHW", name: "Charles Schwab Corp.",               sector: "Financials",    type: "stock" },
  { symbol: "AXP",  name: "American Express Company",           sector: "Financials",    type: "stock" },
  { symbol: "C",    name: "Citigroup Inc.",                      sector: "Financials",    type: "stock" },
  { symbol: "PYPL", name: "PayPal Holdings Inc.",               sector: "Financials",    type: "stock" },
  { symbol: "BRK-B",name: "Berkshire Hathaway Inc. (Class B)",  sector: "Financials",    type: "stock" },

  // ─── Healthcare ───
  { symbol: "UNH",  name: "UnitedHealth Group Inc.",            sector: "Healthcare",    type: "stock" },
  { symbol: "JNJ",  name: "Johnson & Johnson",                  sector: "Healthcare",    type: "stock" },
  { symbol: "LLY",  name: "Eli Lilly and Company",              sector: "Healthcare",    type: "stock" },
  { symbol: "PFE",  name: "Pfizer Inc.",                         sector: "Healthcare",    type: "stock" },
  { symbol: "ABBV", name: "AbbVie Inc.",                         sector: "Healthcare",    type: "stock" },
  { symbol: "MRK",  name: "Merck & Co. Inc.",                    sector: "Healthcare",    type: "stock" },
  { symbol: "TMO",  name: "Thermo Fisher Scientific",           sector: "Healthcare",    type: "stock" },
  { symbol: "ABT",  name: "Abbott Laboratories",                 sector: "Healthcare",    type: "stock" },
  { symbol: "DHR",  name: "Danaher Corporation",                 sector: "Healthcare",    type: "stock" },
  { symbol: "BMY",  name: "Bristol-Myers Squibb Co.",            sector: "Healthcare",    type: "stock" },
  { symbol: "AMGN", name: "Amgen Inc.",                          sector: "Healthcare",    type: "stock" },
  { symbol: "GILD", name: "Gilead Sciences Inc.",                sector: "Healthcare",    type: "stock" },
  { symbol: "ISRG", name: "Intuitive Surgical Inc.",             sector: "Healthcare",    type: "stock" },
  { symbol: "MDT",  name: "Medtronic plc",                       sector: "Healthcare",    type: "stock" },

  // ─── Consumer / Retail ───
  { symbol: "WMT",  name: "Walmart Inc.",                        sector: "Consumer Stpl", type: "stock" },
  { symbol: "PG",   name: "Procter & Gamble Co.",                sector: "Consumer Stpl", type: "stock" },
  { symbol: "KO",   name: "Coca-Cola Company",                   sector: "Consumer Stpl", type: "stock" },
  { symbol: "PEP",  name: "PepsiCo Inc.",                        sector: "Consumer Stpl", type: "stock" },
  { symbol: "COST", name: "Costco Wholesale Corp.",              sector: "Consumer Stpl", type: "stock" },
  { symbol: "HD",   name: "Home Depot Inc.",                      sector: "Consumer Disc", type: "stock" },
  { symbol: "MCD",  name: "McDonald's Corporation",              sector: "Consumer Disc", type: "stock" },
  { symbol: "NKE",  name: "Nike Inc.",                            sector: "Consumer Disc", type: "stock" },
  { symbol: "SBUX", name: "Starbucks Corporation",               sector: "Consumer Disc", type: "stock" },
  { symbol: "LOW",  name: "Lowe's Companies Inc.",               sector: "Consumer Disc", type: "stock" },
  { symbol: "TGT",  name: "Target Corporation",                  sector: "Consumer Disc", type: "stock" },
  { symbol: "DIS",  name: "Walt Disney Company",                 sector: "Communication", type: "stock" },
  { symbol: "PM",   name: "Philip Morris International",         sector: "Consumer Stpl", type: "stock" },
  { symbol: "CL",   name: "Colgate-Palmolive Co.",               sector: "Consumer Stpl", type: "stock" },

  // ─── Industrials ───
  { symbol: "CAT",  name: "Caterpillar Inc.",                    sector: "Industrials",   type: "stock" },
  { symbol: "HON",  name: "Honeywell International",            sector: "Industrials",   type: "stock" },
  { symbol: "UPS",  name: "United Parcel Service Inc.",          sector: "Industrials",   type: "stock" },
  { symbol: "GE",   name: "General Electric Company",            sector: "Industrials",   type: "stock" },
  { symbol: "BA",   name: "Boeing Company",                      sector: "Industrials",   type: "stock" },
  { symbol: "RTX",  name: "RTX Corporation",                     sector: "Industrials",   type: "stock" },
  { symbol: "LMT",  name: "Lockheed Martin Corp.",               sector: "Industrials",   type: "stock" },
  { symbol: "DE",   name: "Deere & Company",                     sector: "Industrials",   type: "stock" },
  { symbol: "MMM",  name: "3M Company",                          sector: "Industrials",   type: "stock" },

  // ─── Energy ───
  { symbol: "XOM",  name: "Exxon Mobil Corporation",             sector: "Energy",        type: "stock" },
  { symbol: "CVX",  name: "Chevron Corporation",                  sector: "Energy",        type: "stock" },
  { symbol: "COP",  name: "ConocoPhillips",                       sector: "Energy",        type: "stock" },
  { symbol: "SLB",  name: "Schlumberger Limited",                  sector: "Energy",        type: "stock" },
  { symbol: "EOG",  name: "EOG Resources Inc.",                    sector: "Energy",        type: "stock" },
  { symbol: "MPC",  name: "Marathon Petroleum Corp.",              sector: "Energy",        type: "stock" },

  // ─── Telecom / Communication ───
  { symbol: "T",    name: "AT&T Inc.",                             sector: "Communication", type: "stock" },
  { symbol: "VZ",   name: "Verizon Communications Inc.",           sector: "Communication", type: "stock" },
  { symbol: "TMUS", name: "T-Mobile US Inc.",                      sector: "Communication", type: "stock" },
  { symbol: "CMCSA",name: "Comcast Corporation",                   sector: "Communication", type: "stock" },

  // ─── Utilities ───
  { symbol: "NEE",  name: "NextEra Energy Inc.",                   sector: "Utilities",     type: "stock" },
  { symbol: "DUK",  name: "Duke Energy Corporation",              sector: "Utilities",     type: "stock" },
  { symbol: "SO",   name: "Southern Company",                      sector: "Utilities",     type: "stock" },

  // ─── Real Estate ───
  { symbol: "AMT",  name: "American Tower Corporation",            sector: "Real Estate",   type: "stock" },
  { symbol: "PLD",  name: "Prologis Inc.",                          sector: "Real Estate",   type: "stock" },
  { symbol: "CCI",  name: "Crown Castle Inc.",                      sector: "Real Estate",   type: "stock" },
  { symbol: "O",    name: "Realty Income Corporation",               sector: "Real Estate",   type: "stock" },

  // ─── Materials ───
  { symbol: "LIN",  name: "Linde plc",                             sector: "Materials",     type: "stock" },
  { symbol: "APD",  name: "Air Products & Chemicals",              sector: "Materials",     type: "stock" },
  { symbol: "SHW",  name: "Sherwin-Williams Company",              sector: "Materials",     type: "stock" },
  { symbol: "FCX",  name: "Freeport-McMoRan Inc.",                  sector: "Materials",     type: "stock" },
  { symbol: "NEM",  name: "Newmont Corporation",                    sector: "Materials",     type: "stock" },
];

export default TICKER_CATALOG;

/**
 * Search the catalog by query string. Matches symbol prefix and name substring.
 * Returns up to `limit` results sorted: exact symbol match first, then symbol prefix, then name match.
 */
export function searchTickers(query, limit = 15) {
  if (!query || !query.trim()) return [];
  const q = query.trim().toUpperCase();
  const qLower = query.trim().toLowerCase();

  const exact = [];
  const symbolPrefix = [];
  const nameMatch = [];

  for (const entry of TICKER_CATALOG) {
    if (entry.symbol === q) {
      exact.push(entry);
    } else if (entry.symbol.startsWith(q)) {
      symbolPrefix.push(entry);
    } else if (entry.name.toLowerCase().includes(qLower) || entry.sector.toLowerCase().includes(qLower)) {
      nameMatch.push(entry);
    }
  }

  return [...exact, ...symbolPrefix, ...nameMatch].slice(0, limit);
}
