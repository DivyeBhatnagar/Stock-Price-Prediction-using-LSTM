/**
 * NavDrawer.jsx — Mobile-first side navigation drawer
 * =====================================================
 * Slides in from the left on small screens.
 * Uses @headlessui/react Dialog for accessible focus-trapping.
 * All interactive elements satisfy 44×44 px minimum touch target.
 */

import { Fragment } from "react";
import { Dialog, Transition } from "@headlessui/react";
import {
  X, TrendingUp, BarChart2, CandlestickChart,
  Settings, Github, Activity, BookOpen,
} from "lucide-react";

const NAV_ITEMS = [
  { href: "/",          Icon: TrendingUp,        label: "Dashboard"    },
  { href: "#overview",  Icon: BarChart2,          label: "Overview"     },
  { href: "#candles",   Icon: CandlestickChart,   label: "Candlestick"  },
  { href: "#live",      Icon: Activity,           label: "Live Stream"  },
  { href: "#training",  Icon: Settings,           label: "Train Model"  },
  { href: "#docs",      Icon: BookOpen,            label: "Docs"         },
];

export default function NavDrawer({ open, onClose }) {
  return (
    <Transition show={open} as={Fragment}>
      <Dialog
        as="div"
        onClose={onClose}
        className="relative z-[60] lg:hidden"
        aria-label="Navigation drawer"
      >
        {/* Backdrop */}
        <Transition.Child
          as={Fragment}
          enter="transition-opacity ease-out duration-200"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="transition-opacity ease-in duration-150"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div
            className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm"
            aria-hidden="true"
          />
        </Transition.Child>

        {/* Drawer panel */}
        <Transition.Child
          as={Fragment}
          enter="transform transition ease-out duration-250"
          enterFrom="-translate-x-full"
          enterTo="translate-x-0"
          leave="transform transition ease-in duration-200"
          leaveFrom="translate-x-0"
          leaveTo="-translate-x-full"
        >
          <Dialog.Panel className="fixed inset-y-0 left-0 w-72 overflow-y-auto bg-white shadow-xl ring-1 ring-black/5">
            {/* Drawer header */}
            <div className="flex h-14 items-center justify-between border-b border-slate-100 px-4">
              <div className="flex items-center gap-2.5">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600">
                  <TrendingUp className="h-4 w-4 text-white" aria-hidden="true" />
                </div>
                <span className="text-sm font-bold tracking-tight text-slate-900">
                  StockOracle
                </span>
              </div>
              <button
                type="button"
                onClick={onClose}
                className="flex h-11 w-11 items-center justify-center rounded-lg text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600"
                aria-label="Close navigation"
              >
                <X className="h-5 w-5" aria-hidden="true" />
              </button>
            </div>

            {/* Nav links */}
            <nav aria-label="Main navigation" className="px-3 py-4">
              <ul role="list" className="space-y-1">
                {NAV_ITEMS.map(({ href, Icon, label }) => (
                  <li key={label}>
                    <a
                      href={href}
                      onClick={onClose}
                      className="flex min-h-[44px] items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-slate-700 transition-colors hover:bg-brand-50 hover:text-brand-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600"
                    >
                      <Icon className="h-4.5 w-4.5 shrink-0" aria-hidden="true" />
                      {label}
                    </a>
                  </li>
                ))}
              </ul>
            </nav>

            {/* Footer */}
            <div className="absolute bottom-0 left-0 right-0 border-t border-slate-100 px-4 py-4">
              <a
                href="https://github.com/DivyeBhatnagar/Stock-Price-Prediction-using-LSTM"
                target="_blank"
                rel="noreferrer"
                className="flex min-h-[44px] items-center gap-2.5 rounded-lg px-3 py-2.5 text-sm font-medium text-slate-600 transition-colors hover:bg-slate-100 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600"
                aria-label="View source code on GitHub (opens in new tab)"
              >
                <Github className="h-4 w-4 shrink-0" aria-hidden="true" />
                View on GitHub
              </a>
            </div>
          </Dialog.Panel>
        </Transition.Child>
      </Dialog>
    </Transition>
  );
}
