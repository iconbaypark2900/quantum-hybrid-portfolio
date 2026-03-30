# Design System Specification: High-Tech Financial Intelligence

## 1. Overview & Creative North Star: "The Quantum Ledger"
The Creative North Star for this design system is **The Quantum Ledger**. In the world of high-stakes financial optimization, users require more than just "data visualization"—they require an environment that feels like a precision instrument.

This system moves away from the "generic SaaS" look by embracing **Kinetic Precision**. We reject the standard 12-column grid in favor of intentional asymmetry that guides the eye toward critical financial insights. By layering charcoal surfaces and using high-contrast "Quantum Blue" accents, we create a sense of depth that feels like a digital cockpit. The interface doesn't just display information; it manifests authority through editorial spacing and a complete absence of distracting structural lines.

---

## 2. Colors: Tonal Depth over Borders
Color in this system is used to define architecture, not just decoration. We prioritize "Tonal Layering" to create hierarchy.

### The Palette
*   **Primary (Quantum Blue):** `#98cbff` (Fixed) | `#00a3ff` (Container). Use for primary actions and active states.
*   **Tertiary (Success Green):** `#00e475` (Fixed). Reserved strictly for positive growth, "In the Green" states, and completed optimizations.
*   **Surface Foundation:** Base background is `#111316`.

### The "No-Line" Rule
**Standard 1px solid borders are prohibited for sectioning.** To separate a sidebar from a main content area, or a header from a body, use background shifts. 
*   *Example:* Place a `surface-container-low` (`#1a1c1f`) content area directly against a `surface` (`#111316`) background. The 2% shift in value is enough for the human eye to perceive a boundary without the "boxed-in" feel of a stroke.

### Surface Hierarchy & Nesting
Treat the UI as a series of nested physical plates:
1.  **Level 0 (Base):** `surface` (`#111316`) - The void.
2.  **Level 1 (Sections):** `surface-container-low` (`#1a1c1f`) - Large layout blocks.
3.  **Level 2 (Cards/Modules):** `surface-container` (`#1e2023`) - Data modules.
4.  **Level 3 (Interactive/Popovers):** `surface-container-high` (`#282a2d`) - Elevated focus points.

### The "Glass & Gradient" Rule
For high-level insights or floating "Optimization Alerts," use **Glassmorphism**. Apply `surface-container-highest` at 60% opacity with a `24px` backdrop-blur. 
*   **Signature Texture:** Main CTAs should use a subtle linear gradient from `primary` (`#98cbff`) to `primary-container` (`#00a3ff`) at a 135-degree angle to provide a "machined metal" luster.

---

## 3. Typography: Editorial Authority
We pair the technical precision of **Inter** with the architectural strength of **Space Grotesk**.

*   **Display & Headlines (Space Grotesk):** Used for "Hero" numbers (Portfolio Totals) and Section Titles. The slight geometric quirks of Space Grotesk convey a high-tech, futuristic tone.
*   **Data & Body (Inter):** Used for all tabular data and descriptive text. For specific monospaced data points (Transaction Hashes, Percentages), use a high-legibility tabular lining feature within Inter or fallback to a dedicated mono.

**Scale Highlight:**
*   **Display-LG (3.5rem):** For the "Big Number"—the portfolio's net worth.
*   **Label-SM (0.6875rem):** All-caps with 0.05em letter spacing for data headers (e.g., "ASSET CLASS").

---

## 4. Elevation & Depth: Atmospheric Layering
Traditional shadows are too heavy for a sophisticated financial tool. We use **Ambient Softness**.

*   **The Layering Principle:** Instead of a shadow, a `surface-container-highest` card sitting on a `surface-container-low` background creates "natural" elevation.
*   **Ambient Shadows:** For floating modals, use a shadow with a `40px` blur, 0px offset, and 6% opacity of `on-surface` (`#e2e2e6`). This creates a "glow" of light rather than a dark drop-shadow.
*   **The Ghost Border Fallback:** If a data table requires a border for legibility, use `outline-variant` (`#3f4852`) at **15% opacity**. It should be felt, not seen.

---

## 5. Components: Precision Instruments

### Buttons
*   **Primary:** Gradient fill (Primary to Primary-Container), white text (`on-primary-fixed`), `md` (0.375rem) corner radius.
*   **Secondary:** Ghost style. No background, `Ghost Border` (15% opacity outline), text in `primary-fixed-dim`.

### Data Sparklines (Custom Component)
Financial trends should be rendered as 2px paths using `primary` (Quantum Blue). Area fills below the sparkline should use a gradient from `primary` (10% opacity) to `transparent`. No axes or grids—the shape is the signal.

### Cards & Lists
**Strict Rule:** No dividers. Use `spacing-6` (1.3rem) of vertical white space to separate list items. If separation is visually required, use a subtle background hover state (`surface-container-high`).

### Input Fields
Darker than the surface they sit on. Use `surface-container-lowest` for the input track. Upon focus, the `Ghost Border` transitions to 100% opacity `primary` with a 2px outer "glow" (Quantum Blue at 20% opacity).

### High-Context Components
*   **Optimization Toggle:** A custom switch that, when active, triggers a subtle "pulse" animation using `tertiary` (`Success Green`) to indicate the system is actively calculating.
*   **Risk Heatmap:** A grid using varying opacities of `error_container` and `tertiary_container` to show portfolio exposure without using "traffic light" clichés.

---

## 6. Do's and Don'ts

### Do
*   **Do** use asymmetrical layouts. A 40/60 split for a dashboard feels more "curated" than a 50/50 split.
*   **Do** use `spaceGrotesk` for large numbers. It makes financial figures look like architectural measurements.
*   **Do** rely on the Spacing Scale (specifically `1.5`, `3`, and `6`) to create "rhythmic breathing room" between data clusters.

### Don't
*   **Don't** use pure black (#000000). Use the `surface` token (`#111316`) to maintain tonal depth.
*   **Don't** use 100% opaque borders. They clutter the UI and distract from the data.
*   **Don't** use standard "Success/Warning/Error" colors at high saturation. Use the designated `tertiary` and `error_container` tokens to maintain the sophisticated dark aesthetic.