import React, { useState, useMemo, useContext } from "react";
import { DashboardThemeContext } from "../../theme";
import SectionTitle from "./SectionTitle";

function TradeBlotter({ holdings, portfolioValue }) {
  const colors = useContext(DashboardThemeContext);
  const [localPortfolioValue, setLocalPortfolioValue] = useState(portfolioValue || 100000);

  const tradeActions = useMemo(() => {
    if (!holdings || !holdings.length) return [];
    return holdings.map(holding => ({
      ...holding,
      dollarAmount: holding.weight * localPortfolioValue,
      shares: (holding.weight * localPortfolioValue) / 100,
    }));
  }, [holdings, localPortfolioValue]);

  return (
    <div style={{ background: colors.surface, border: `1px solid ${colors.border}`, borderRadius: 10, padding: 20 }}>
      <SectionTitle subtitle="Enter portfolio value to see buy/sell actions with dollar amounts" info="Translates optimized weights into dollar amounts and share counts for execution.">Trade Blotter</SectionTitle>
      <div style={{ marginBottom: 16 }}>
        <label style={{ display: "block", fontSize: 12, color: colors.textMuted, marginBottom: 6 }}>Portfolio Value ($)</label>
        <input type="number" value={localPortfolioValue} onChange={(e) => setLocalPortfolioValue(Number(e.target.value))}
          style={{ width: "100%", padding: "8px 12px", background: colors.surfaceLight, border: `1px solid ${colors.border}`, borderRadius: 6, color: colors.text, fontFamily: "'JetBrains Mono', monospace" }} />
      </div>
      <div style={{ maxHeight: 300, overflowY: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11 }}>
          <thead>
            <tr style={{ borderBottom: `1px solid ${colors.border}` }}>
              <th style={{ textAlign: "left", padding: "8px", color: colors.textMuted }}>Asset</th>
              <th style={{ textAlign: "right", padding: "8px", color: colors.textMuted }}>Sector</th>
              <th style={{ textAlign: "right", padding: "8px", color: colors.textMuted }}>Weight</th>
              <th style={{ textAlign: "right", padding: "8px", color: colors.textMuted }}>Dollar Amount</th>
              <th style={{ textAlign: "right", padding: "8px", color: colors.textMuted }}>Action</th>
            </tr>
          </thead>
          <tbody>
            {tradeActions.map((action, i) => (
              <tr key={action.name || i} style={{ borderBottom: `1px solid ${colors.borderLight}` }}>
                <td style={{ padding: "8px", color: colors.text }}>{action.name}</td>
                <td style={{ padding: "8px", color: colors.text, textAlign: "right" }}>{action.sector}</td>
                <td style={{ padding: "8px", color: colors.text, textAlign: "right" }}>{(action.weight * 100).toFixed(2)}%</td>
                <td style={{ padding: "8px", color: colors.text, textAlign: "right" }}>${action.dollarAmount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                <td style={{ padding: "8px", color: colors.green, textAlign: "right" }}>BUY</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default React.memo(TradeBlotter);
