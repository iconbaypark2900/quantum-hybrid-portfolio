/**
 * Shared stress scenario labels for Simulations page and copy in strategy presets.
 * Heuristic shocks — not realized portfolio returns.
 */
export type StressScenario = { name: string; shock: number; desc: string };

export const STRESS_BEAR_SCENARIOS: StressScenario[] = [
  { name: "Black Monday 1987", shock: -0.55, desc: "Single-day crash, Oct 1987" },
  { name: "2008 GFC", shock: -0.5, desc: "Lehman collapse, credit freeze" },
  { name: "Dot-com unwind", shock: -0.35, desc: "2000–2002 growth reset" },
  { name: "COVID Crash", shock: -0.34, desc: "March 2020 multi-week selloff" },
  { name: "2022 Rate Shock", shock: -0.25, desc: "Fed tightening, growth selloff" },
  { name: "2018 Q4", shock: -0.26, desc: "Rates / growth scare" },
  { name: "2011 US downgrade", shock: -0.22, desc: "Rating cut, Europe fears" },
  { name: "2015 China deval.", shock: -0.18, desc: "August yuan move, EM risk-off" },
  { name: "Flash Crash", shock: -0.09, desc: "Intraday chaos, May 2010" },
];

export const STRESS_BULL_SCENARIOS: StressScenario[] = [
  { name: "March 2009 bounce", shock: 0.1, desc: "Post-crisis QE / risk-on leg" },
  { name: "2016 election relief", shock: 0.12, desc: "Overnight / next-session relief rally" },
  { name: "Stimulus / reopening", shock: 0.14, desc: "2020 policy + reopening momentum" },
  { name: "Vaccine Monday", shock: 0.18, desc: "Nov 2020 vaccine efficacy rally" },
  { name: "Oct 2022 CPI day", shock: 0.1, desc: "Bear-market bear rally (illustrative)" },
  { name: "AI / growth melt-up", shock: 0.08, desc: "Narrative risk-on (illustrative)" },
];
