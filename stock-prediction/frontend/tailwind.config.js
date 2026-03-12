/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: "class",   // toggle dark mode via <html class="dark">
  theme: {
    extend: {
      // ── Brand & Surface Colors ─────────────────────────────────────────
      colors: {
        brand: {
          50:  "#eff6ff",
          100: "#dbeafe",
          200: "#bfdbfe",
          300: "#93c5fd",
          400: "#60a5fa",
          500: "#3b82f6",
          600: "#2563eb",
          700: "#1d4ed8",
          800: "#1e40af",
          900: "#1e3a8a",
        },
        surface: {
          DEFAULT: "#F8FAFC",   // page background
          card:    "#FFFFFF",   // card / panel background
          border:  "#E2E8F0",   // default border
          hover:   "#F1F5F9",   // hover / active background
          muted:   "#F8FAFC",   // subtle fills
        },
        // Semantic chart colours
        chart: {
          price:      "#2563EB",   // historical price line (blue)
          forecast:   "#F59E0B",   // LSTM forecast (amber)
          live:       "#0891b2",   // live streaming line (cyan)
          prediction: "#7c3aed",   // LSTM target line (violet)
          up:         "#16a34a",   // positive change (green)
          down:       "#dc2626",   // negative change (red)
          volume:     "#94a3b8",   // volume bars (slate)
        },
        // Status colours for WS badge
        ws: {
          open:       "#16a34a",
          connecting: "#d97706",
          closed:     "#94a3b8",
          error:      "#dc2626",
        },
      },

      // ── Typography ─────────────────────────────────────────────────────
      fontFamily: {
        sans: ["Inter", "IBM Plex Sans", "system-ui", "sans-serif"],
        mono: ["IBM Plex Mono", "JetBrains Mono", "monospace"],
      },
      fontSize: {
        "2xs": ["0.625rem", { lineHeight: "0.875rem" }],
      },

      // ── Shadows ─────────────────────────────────────────────────────────
      boxShadow: {
        card:        "0 1px 3px 0 rgb(0 0 0/0.06), 0 1px 2px -1px rgb(0 0 0/0.04)",
        "card-md":   "0 4px 6px -1px rgb(0 0 0/0.06), 0 2px 4px -2px rgb(0 0 0/0.04)",
        "card-lg":   "0 10px 15px -3px rgb(0 0 0/0.06), 0 4px 6px -4px rgb(0 0 0/0.04)",
        "inner-sm":  "inset 0 1px 2px 0 rgb(0 0 0/0.04)",
      },

      // ── Aspect Ratios ───────────────────────────────────────────────────
      aspectRatio: {
        "chart":        "16 / 9",
        "chart-wide":   "21 / 9",
        "chart-square": "1 / 1",
      },

      // ── Border Radius ───────────────────────────────────────────────────
      borderRadius: {
        "2xl": "1rem",
        "3xl": "1.5rem",
      },

      // ── Animation ───────────────────────────────────────────────────────
      keyframes: {
        "slide-in-left": {
          "0%":   { transform: "translateX(-100%)" },
          "100%": { transform: "translateX(0)" },
        },
        "slide-out-left": {
          "0%":   { transform: "translateX(0)" },
          "100%": { transform: "translateX(-100%)" },
        },
        "fade-in": {
          "0%":   { opacity: "0" },
          "100%": { opacity: "1" },
        },
        "pulse-dot": {
          "0%, 100%": { transform: "scale(1)", opacity: "1" },
          "50%":       { transform: "scale(1.4)", opacity: "0.5" },
        },
      },
      animation: {
        "slide-in-left":  "slide-in-left 250ms ease-out",
        "slide-out-left": "slide-out-left 200ms ease-in",
        "fade-in":        "fade-in 200ms ease-out",
        "pulse-dot":      "pulse-dot 1.5s ease-in-out infinite",
      },

      // ── Transitions ─────────────────────────────────────────────────────
      transitionDuration: {
        "250": "250ms",
      },
    },
  },
  plugins: [
    // Lightweight form-switch pattern without @tailwindcss/forms
    function ({ addComponents, theme }) {
      addComponents({
        ".focus-ring": {
          "@apply focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2": {},
        },
        ".card": {
          "@apply rounded-2xl border border-surface-border bg-surface-card shadow-card": {},
        },
        ".card-header": {
          "@apply mb-4 flex items-center justify-between": {},
        },
        ".stat-card": {
          "@apply flex flex-col gap-1 rounded-xl border border-surface-border bg-surface-card p-4 shadow-card": {},
        },
        ".btn-primary": {
          "@apply inline-flex min-h-[44px] items-center justify-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors duration-200 hover:bg-brand-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50": {},
        },
        ".btn-ghost": {
          "@apply inline-flex min-h-[44px] items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold text-slate-700 transition-colors duration-200 hover:bg-slate-100 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50": {},
        },
        ".toggle-switch": {
          "@apply relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2": {},
        },
      });
    },
  ],
}

