/**
 * Navbar.jsx — Accessible top navigation bar with mobile hamburger drawer
 * =========================================================================
 * • Sticky, blurred, light-themed header
 * • Hamburger menu (≤lg) → NavDrawer slide-in
 * • Full ARIA roles: role="banner", aria-label on all buttons
 * • focus-visible rings for keyboard navigation
 * • Minimum 44×44 px touch targets on all interactive elements
 */

import { useState } from "react";
import { TrendingUp, Github, Menu, Activity } from "lucide-react";
import NavDrawer from "./NavDrawer";

export default function Navbar() {
  const [drawerOpen, setDrawerOpen] = useState(false);

  return (
    <>
      <header
        role="banner"
        className="sticky top-0 z-50 border-b border-surface-border bg-white/95 shadow-card backdrop-blur-sm"
      >
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-14 items-center justify-between">

            {/* ── Logo ── */}
            <a
              href="/"
              className="flex items-center gap-2.5 rounded-lg p-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600"
              aria-label="StockOracle — go to home"
            >
              <div
                className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600"
                aria-hidden="true"
              >
                <TrendingUp className="h-4 w-4 text-white" />
              </div>
              <div className="flex items-center gap-2">
                <span className="text-base font-bold tracking-tight text-slate-900">
                  StockOracle
                </span>
                <span
                  className="rounded border border-brand-200 bg-brand-50 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-widest text-brand-600"
                  aria-label="LSTM AI powered"
                >
                  LSTM AI
                </span>
              </div>
            </a>

            {/* ── Desktop actions ── */}
            <nav
              aria-label="Primary navigation"
              className="hidden items-center gap-1 lg:flex"
            >
              <a
                href="#live"
                className="flex min-h-[44px] items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium text-slate-600 transition-colors duration-200 hover:bg-slate-100 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600"
              >
                <Activity className="h-4 w-4" aria-hidden="true" />
                Live
              </a>
              <a
                href="https://github.com/DivyeBhatnagar/Stock-Price-Prediction-using-LSTM"
                target="_blank"
                rel="noreferrer"
                className="flex min-h-[44px] items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium text-slate-600 transition-colors duration-200 hover:bg-slate-100 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600"
                aria-label="View source code on GitHub (opens in new tab)"
              >
                <Github className="h-4 w-4" aria-hidden="true" />
                <span>Source</span>
              </a>
            </nav>

            {/* ── Hamburger (mobile) ── */}
            <button
              type="button"
              onClick={() => setDrawerOpen(true)}
              className="flex h-11 w-11 items-center justify-center rounded-lg text-slate-600 transition-colors hover:bg-slate-100 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 lg:hidden"
              aria-label="Open navigation menu"
              aria-expanded={drawerOpen}
              aria-controls="nav-drawer"
            >
              <Menu className="h-5 w-5" aria-hidden="true" />
            </button>
          </div>
        </div>
      </header>

      {/* Mobile nav drawer */}
      <NavDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
      />
    </>
  );
}
