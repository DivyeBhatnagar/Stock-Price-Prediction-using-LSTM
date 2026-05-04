import { NavLink } from "react-router-dom";

const navItems = [
  { label: "Dashboard", to: "/" },
  { label: "Prediction", to: "/prediction" },
  { label: "News", to: "/news" }
];

export default function Navbar() {
  return (
    <header className="sticky top-0 z-20 border-b border-border/60 bg-white/70 backdrop-blur">
      <div className="container-width flex h-16 items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-border bg-white shadow-soft">
            <span className="text-sm font-semibold text-accent">SM</span>
          </div>
          <div>
            <p className="text-sm font-semibold text-ink">Stock Market</p>
            <p className="text-xs text-muted">Prediction & Analysis</p>
          </div>
        </div>
        <nav className="flex items-center gap-4 text-sm text-muted">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `rounded-full px-3 py-1.5 transition ${
                  isActive
                    ? "bg-accent/10 text-accent"
                    : "hover:text-ink"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </div>
    </header>
  );
}
