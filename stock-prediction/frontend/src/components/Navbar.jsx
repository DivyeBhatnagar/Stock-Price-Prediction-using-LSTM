// Navbar.jsx  —  Top navigation bar (light theme)

import { TrendingUp, Github } from "lucide-react";

export default function Navbar() {
  return (
    <nav className="sticky top-0 z-50 border-b border-surface-border bg-white/95 backdrop-blur-sm shadow-card">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-14 items-center justify-between">

          {/* Logo */}
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600">
              <TrendingUp className="h-4 w-4 text-white" />
            </div>
            <div className="flex items-center gap-2">
              <span className="text-base font-bold tracking-tight text-slate-900">
                StockOracle
              </span>
              <span className="rounded border border-brand-200 bg-brand-50 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-widest text-brand-600">
                LSTM AI
              </span>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-1">
            <a
              href="https://github.com/DivyeBhatnagar/Stock-Price-Prediction-using-LSTM"
              target="_blank"
              rel="noreferrer"
              className="flex cursor-pointer items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium text-slate-600 transition-colors duration-200 hover:bg-slate-100 hover:text-slate-900"
            >
              <Github className="h-4 w-4" />
              <span className="hidden sm:inline">Source</span>
            </a>
          </div>
        </div>
      </div>
    </nav>
  );
}
