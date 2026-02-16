import React, { useMemo, useContext } from "react";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { DashboardThemeContext } from "../../theme";
import SectionTitle from "./SectionTitle";
import CustomTooltip from "./CustomTooltip";

function DrawdownChart({ backtestResult }) {
  const colors = useContext(DashboardThemeContext);

  const drawdownData = useMemo(() => {
    if (!backtestResult?.equity_curve?.length) return [];
    let runningMax = backtestResult.equity_curve[0].portfolio_value;
    return backtestResult.equity_curve.map(point => {
      if (point.portfolio_value > runningMax) runningMax = point.portfolio_value;
      const drawdown = runningMax > 0 ? (runningMax - point.portfolio_value) / runningMax : 0;
      return { ...point, drawdown: drawdown * 100 };
    });
  }, [backtestResult]);

  if (!backtestResult?.equity_curve) return null;

  return (
    <div style={{ background: colors.surface, border: `1px solid ${colors.border}`, borderRadius: 10, padding: 20 }}>
      <SectionTitle subtitle="Portfolio drawdown from peak value over time" info="Shows % decline from the highest portfolio value. Useful to gauge downside risk.">Drawdown Chart</SectionTitle>
      <div style={{ height: 250 }} role="img" aria-label="Drawdown chart showing portfolio decline from peak">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={drawdownData}>
            <defs>
              <linearGradient id="drawdownGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={colors.red} stopOpacity={0.3} />
                <stop offset="100%" stopColor={colors.red} stopOpacity={0.05} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke={colors.border} />
            <XAxis dataKey="date" stroke={colors.textDim} tick={{ fontSize: 10 }} label={{ value: "Date", position: "bottom", fill: colors.textDim, fontSize: 11 }} />
            <YAxis stroke={colors.textDim} tick={{ fontSize: 10 }} tickFormatter={v => `${v.toFixed(1)}%`} label={{ value: "Drawdown (%)", angle: -90, position: "insideLeft", fill: colors.textDim, fontSize: 11 }} />
            <Tooltip content={<CustomTooltip />} />
            <Area type="monotone" dataKey="drawdown" stroke={colors.red} fill="url(#drawdownGradient)" strokeWidth={2} name="Drawdown (%)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export default React.memo(DrawdownChart);
