import type { Config } from "tailwindcss";

/**
 * Quantum Ledger tokens — CSS custom properties defined in globals.css.
 * `ql-*` names are canonical in app code.
 */
export default {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        "ql-surface": "var(--ql-surface)",
        "ql-surface-low": "var(--ql-surface-low)",
        "ql-surface-container": "var(--ql-surface-container)",
        "ql-surface-high": "var(--ql-surface-high)",
        "ql-surface-highest": "var(--ql-surface-highest)",
        "ql-surface-lowest": "var(--ql-surface-lowest)",
        "ql-primary": "var(--ql-primary)",
        "ql-primary-container": "var(--ql-primary-container)",
        "ql-tertiary": "var(--ql-tertiary)",
        "ql-tertiary-container": "var(--ql-tertiary-container)",
        "ql-on-surface": "var(--ql-on-surface)",
        "ql-on-surface-variant": "var(--ql-on-surface-variant)",
        "ql-outline": "var(--ql-outline)",
        "ql-outline-variant": "var(--ql-outline-variant)",
        "ql-error": "var(--ql-error)",
        "ql-error-container": "var(--ql-error-container)",
        "ql-secondary": "var(--ql-secondary)",
        "ql-on-primary": "var(--ql-on-primary)",
        "ql-on-primary-fixed": "var(--ql-on-primary-fixed)",
        // Stitch semantic aliases (same CSS vars)
        surface: "var(--ql-surface)",
        background: "var(--ql-surface)",
        "on-surface": "var(--ql-on-surface)",
        "on-background": "var(--ql-on-surface)",
        primary: "var(--ql-primary)",
        "primary-container": "var(--ql-primary-container)",
        "primary-fixed-dim": "var(--ql-primary)",
        tertiary: "var(--ql-tertiary)",
        "tertiary-container": "var(--ql-tertiary-container)",
        "outline-variant": "var(--ql-outline-variant)",
        "surface-container": "var(--ql-surface-container)",
        "surface-container-low": "var(--ql-surface-low)",
        "surface-container-high": "var(--ql-surface-high)",
        "surface-container-highest": "var(--ql-surface-highest)",
        "surface-container-lowest": "var(--ql-surface-lowest)",
      },
      fontFamily: {
        headline: ["Space Grotesk", "var(--font-space-grotesk)", "sans-serif"],
        body: ["Inter", "var(--font-inter)", "sans-serif"],
        label: ["Inter", "var(--font-inter)", "sans-serif"],
        mono: ["JetBrains Mono", "var(--font-jetbrains-mono)", "monospace"],
      },
      borderRadius: {
        DEFAULT: "0.125rem",
        lg: "0.25rem",
        xl: "0.5rem",
        full: "0.75rem",
      },
    },
  },
  plugins: [],
} satisfies Config;
