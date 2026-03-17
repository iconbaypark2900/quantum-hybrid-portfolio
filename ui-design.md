# UI Design Guide — Professional Dashboard

Read this before making any visual or component changes. This guide defines
the aesthetic direction, design system, and component patterns for the
Quantum Portfolio dashboard.

---

## Aesthetic direction

**Refined dark-first fintech.** Think Bloomberg Terminal meets modern SaaS:
high information density, restrained color, every pixel intentional.

- Dark background (`#0f1117`) with subtle elevation layers
- Monospaced font for numbers, sans-serif for labels
- Accent: electric teal (`#00d4aa`) for primary actions, amber for warnings
- No gradients on containers. No glows. No drop shadows on cards.
- Motion: entrance only — no persistent animations. Transitions ≤ 200ms.

---

## Design tokens (use these; do not hardcode hex values)

These are already defined in `theme.js` as a `DashboardThemeContext`. Import
and use them in every component.

```js
// Access via:
import { DashboardThemeContext } from '../../theme';
const colors = useContext(DashboardThemeContext);

// Key tokens:
colors.bg           // '#0f1117' — page background
colors.surface      // '#1a1d27' — card / panel background
colors.surfaceLight // '#252836' — elevated surface (hover, selected)
colors.border       // '#2d3142' — 1px borders
colors.text         // '#e8eaf0' — primary text
colors.textMuted    // '#8b8fa8' — secondary / label text
colors.accent       // '#00d4aa' — primary action, active state
colors.accentWarm   // '#f59e0b' — warning, slow-method badge
colors.danger       // '#ef4444' — error, negative return
colors.green        // '#22c55e' — positive return, success
```

---

## Typography rules

```css
/* Numbers — always monospaced */
font-family: 'JetBrains Mono', 'Fira Code', monospace;

/* Labels, body — sans-serif */
font-family: 'IBM Plex Sans', 'DM Sans', system-ui, sans-serif;

/* Sizes */
--text-xs:   11px;  /* badge, caption */
--text-sm:   12px;  /* secondary labels */
--text-base: 13px;  /* body, table rows */
--text-md:   14px;  /* primary labels, tab names */
--text-lg:   18px;  /* section headings */
--text-xl:   24px;  /* metric values */
--text-2xl:  32px;  /* hero numbers */
```

Always use `font-variant-numeric: tabular-nums` on number columns so digits
align in tables.

---

## Spacing system (8px grid)

```
4px   — gap between badge and label
8px   — inner padding on tight components (badges, chips)
12px  — control row item spacing
16px  — card inner padding
24px  — section gap
32px  — tab content padding
48px  — major section separation
```

Never use odd numbers (3px, 7px, 11px). Always multiples of 4.

---

## Component patterns

### MetricCard

```jsx
// Correct pattern — three-line hierarchy
<div style={{ background: colors.surface, borderRadius: 8, padding: '16px 20px',
              border: `1px solid ${colors.border}` }}>
  <div style={{ fontSize: 11, color: colors.textMuted, letterSpacing: '0.06em',
                textTransform: 'uppercase', fontFamily: 'JetBrains Mono, monospace',
                marginBottom: 4 }}>
    Sharpe Ratio
  </div>
  <div style={{ fontSize: 28, fontFamily: 'JetBrains Mono, monospace',
                color: colors.text, lineHeight: 1, fontWeight: 500 }}>
    1.47
  </div>
  <div style={{ fontSize: 11, color: colors.accentWarm, marginTop: 4 }}>
    ↑ 12% vs equal weight
  </div>
</div>
```

### Table rows

```jsx
// Alternating row color on hover only — no static zebra striping
<tr style={{ borderBottom: `1px solid ${colors.border}` }}
    onMouseEnter={e => e.currentTarget.style.background = colors.surfaceLight}
    onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
```

### Tabs

Active tab: solid left border (3px, `colors.accent`) + text at full opacity.
Inactive tab: no border, text at 60% opacity. No background fill on active tab.

```jsx
<button style={{
  borderLeft: isActive ? `3px solid ${colors.accent}` : '3px solid transparent',
  color: isActive ? colors.text : colors.textMuted,
  background: 'none',
  padding: '10px 16px 10px 13px',
  transition: 'all 150ms',
}}>
```

### Badges / pills

```jsx
// Method badge (e.g. "NB05", "slow")
<span style={{
  fontSize: 10, padding: '2px 6px', borderRadius: 4,
  background: `${colors.accentWarm}20`,
  color: colors.accentWarm,
  fontFamily: 'JetBrains Mono, monospace',
  letterSpacing: '0.04em',
}}>
  SLOW
</span>
```

### Sliders

Use the custom `Slider` component from `components/dashboard/Slider.js`.
Do not use raw `<input type="range">` — the custom component applies
the teal track color and correct thumb styling.

### Select / dropdown

```jsx
<select style={{
  background: colors.surface,
  border: `1px solid ${colors.border}`,
  borderRadius: 6,
  color: colors.text,
  padding: '7px 10px',
  fontSize: 13,
  width: '100%',
  cursor: 'pointer',
  outline: 'none',
  appearance: 'none',           // custom caret arrow below
  backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' fill='none'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%238b8fa8' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E")`,
  backgroundRepeat: 'no-repeat',
  backgroundPosition: 'right 10px center',
  paddingRight: 30,
}}>
```

### Section headers

```jsx
<div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
  <div style={{ width: 3, height: 16, background: colors.accent, borderRadius: 2 }} />
  <span style={{ fontSize: 13, fontWeight: 600, color: colors.textMuted,
                  letterSpacing: '0.06em', textTransform: 'uppercase' }}>
    Holdings
  </span>
</div>
```

---

## Chart rules (Recharts)

```jsx
// Standard chart colors — use in order
const CHART_COLORS = ['#00d4aa', '#7c6bff', '#f59e0b', '#ef4444', '#22c55e', '#64748b'];

// Grid
<CartesianGrid strokeDasharray="3 3" stroke={colors.border} vertical={false} />

// Axes
<XAxis tick={{ fill: colors.textMuted, fontSize: 11, fontFamily: 'JetBrains Mono, monospace' }}
       axisLine={{ stroke: colors.border }} tickLine={false} />

// Tooltip
<Tooltip
  contentStyle={{ background: colors.surface, border: `1px solid ${colors.border}`,
                  borderRadius: 6, fontSize: 12 }}
  labelStyle={{ color: colors.textMuted }}
/>

// Legend (bottom, no background box)
<Legend wrapperStyle={{ fontSize: 12, color: colors.textMuted, paddingTop: 8 }} />
```

Always set `margin={{ top: 8, right: 16, left: 0, bottom: 0 }}` on
`<ResponsiveContainer>` charts.

---

## Responsive grid

```jsx
// Card grid — adapts from 1 col on mobile to 3 on wide screens
<div style={{
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
  gap: 16,
}}>
```

Never use hardcoded pixel widths wider than 480px on inner components.
The left sidebar should be `280px` fixed; the content area takes the rest.

---

## Loading states

Use the `LoadingOverlay` component from `components/dashboard/LoadingOverlay.js`.
Never show a spinner without a text label. Use:

```jsx
<LoadingOverlay visible={loading} message="Running optimisation…" />
```

For skeleton loading on cards, use a pulsing background:

```jsx
const skeleton = {
  background: `linear-gradient(90deg, ${colors.surface} 25%, ${colors.surfaceLight} 50%, ${colors.surface} 75%)`,
  backgroundSize: '200% 100%',
  animation: 'skeleton-pulse 1.5s ease infinite',
  borderRadius: 4,
};
```

---

## Objective selector UI

The objective selector should be a styled radio group or segmented control,
not a plain `<select>`. Group methods by type:

```
Classical        │ Equal Weight  │ Markowitz  │ Min Variance  │ HRP
Quantum-inspired │ QUBO-SA       │ VQE
Hybrid           │ Hybrid Pipeline
```

Show a "SLOW" amber badge next to QUBO-SA, VQE, and Hybrid. Show a
tooltip explaining each method on hover. The active method should have
a teal left border accent.

---

## Avoid

- `box-shadow` — use border instead
- `filter: blur()` — never
- `text-shadow`
- Inline styles wider than 2 lines — extract to a `styles` const at top of component
- Hardcoded `#ffffff`, `#000000`, or `#333` — always use design tokens
- `!important`
- Static `height` on containers that hold variable content
- More than 3 font sizes in a single component