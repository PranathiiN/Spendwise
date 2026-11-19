import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router";
import { useAuth } from "../../contexts/AuthContext";
import { Icon, type IconName } from "../common/Icon";

const NAV: { to: string; label: string; icon: IconName }[] = [
  { to: "/dashboard", label: "Dashboard", icon: "dashboard" },
  { to: "/transactions", label: "Transactions", icon: "list" },
  { to: "/budgets", label: "Budgets", icon: "wallet" },
  { to: "/goals", label: "Savings Goals", icon: "target" },
  { to: "/reports", label: "Reports", icon: "chart" },
  { to: "/settings", label: "Settings", icon: "settings" },
];

function Logo() {
  return (
    <div className="flex items-center gap-2">
      <img src="/favicon.svg" alt="" className="h-8 w-8" />
      <span className="text-lg font-bold tracking-tight text-slate-900">SpendWise</span>
    </div>
  );
}

function NavItems({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <nav className="flex flex-col gap-1">
      {NAV.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          onClick={onNavigate}
          className={({ isActive }) =>
            `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
              isActive ? "bg-brand-50 text-brand-800" : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
            }`
          }
        >
          <Icon name={item.icon} className="h-5 w-5" />
          {item.label}
        </NavLink>
      ))}
    </nav>
  );
}

export function AppLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  const userBlock = (
    <div className="border-t border-slate-200 pt-4">
      <div className="mb-3 px-3">
        <p className="truncate text-sm font-medium text-slate-900">{user?.name}</p>
        <p className="truncate text-xs text-slate-500">{user?.email}</p>
      </div>
      <button type="button" onClick={handleLogout} className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100">
        <Icon name="logout" /> Log out
      </button>
    </div>
  );

  return (
    <div className="min-h-screen">
      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 hidden w-60 flex-col justify-between border-r border-slate-200 bg-white px-3 py-5 lg:flex">
        <div>
          <div className="mb-8 px-3">
            <Logo />
          </div>
          <NavItems />
        </div>
        {userBlock}
      </aside>

      {/* Mobile top bar */}
      <header className="sticky top-0 z-30 flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3 lg:hidden">
        <Logo />
        <button type="button" className="btn-ghost" onClick={() => setMobileOpen(true)} aria-label="Open menu">
          <Icon name="menu" />
        </button>
      </header>

      {mobileOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-slate-900/40" onClick={() => setMobileOpen(false)} />
          <aside className="absolute inset-y-0 left-0 flex w-64 flex-col justify-between bg-white px-3 py-5 shadow-xl">
            <div>
              <div className="mb-6 flex items-center justify-between px-3">
                <Logo />
                <button type="button" className="btn-ghost" onClick={() => setMobileOpen(false)} aria-label="Close menu">
                  <Icon name="x" />
                </button>
              </div>
              <NavItems onNavigate={() => setMobileOpen(false)} />
            </div>
            {userBlock}
          </aside>
        </div>
      )}

      <main className="lg:pl-60">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
