import React, { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  Shield,
  LayoutDashboard,
  FileText,
  ClipboardCheck,
  Menu,
  X,
  Activity,
  User,
  LogOut,
  Info,
  Sparkles,
  Home,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

/* ---------------------------- Health status ---------------------------- */

function HealthStatus({ health, className = '' }) {
  if (!health) {
    return (
      <div
        role="status"
        className={`inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[11px] text-slate-400 ${className}`}
      >
        <Activity className="h-3 w-3 animate-spin text-indigo-500" aria-hidden="true" />
        <span>Connecting…</span>
      </div>
    );
  }

  if (health.status === 'offline') {
    return (
      <div
        role="status"
        title={health.error || 'Backend service is offline'}
        className={`inline-flex items-center gap-1.5 rounded-full border border-rose-200 bg-rose-50 px-2.5 py-1 text-[11px] font-semibold text-rose-700 ${className}`}
      >
        <span className="relative flex h-2 w-2" aria-hidden="true">
          <span className="relative inline-flex h-2 w-2 rounded-full bg-rose-500" />
        </span>
        <span>OFFLINE</span>
      </div>
    );
  }

  return (
    <div
      role="status"
      className={`inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[11px] ${className}`}
    >
      <span className="relative flex h-2 w-2" aria-hidden="true">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
        <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
      </span>
      <span className="font-semibold text-slate-700">
        {health.llm_provider ? health.llm_provider.toUpperCase() : 'AI ONLINE'}
      </span>

      {health.tesseract_available && (
        <span
          className="border-l border-slate-200 pl-1.5 font-mono text-[9px] text-slate-400"
          title="OCR active"
        >
          OCR
        </span>
      )}
    </div>
  );
}

/* -------------------------------- Navbar -------------------------------- */

export default function Navbar({ health }) {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const { user, isAuthenticated, logout } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const isActive = (path) =>
    path === '/' ? pathname === '/' : pathname.startsWith(path);

  // Close the mobile menu whenever the route changes.
  useEffect(() => {
    setMobileMenuOpen(false);
  }, [pathname]);

  // Close the mobile menu with Escape key.
  useEffect(() => {
    if (!mobileMenuOpen) return undefined;
    const onKeyDown = (e) => {
      if (e.key === 'Escape') setMobileMenuOpen(false);
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [mobileMenuOpen]);

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const navLinks = isAuthenticated
    ? [
        { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
        { name: 'Policies', path: '/policies', icon: FileText },
        { name: 'Claims Assistant', path: '/claims', icon: ClipboardCheck },
        { name: 'About', path: '/about', icon: Info },
      ]
    : [
        { name: 'Home', path: '/', icon: Home },
        { name: 'About', path: '/about', icon: Info },
      ];

  return (
    <header className="sticky top-0 z-50 border-b border-slate-200 bg-white/90 backdrop-blur supports-[backdrop-filter]:bg-white/75">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-14 items-center justify-between sm:h-16">
          {/* Left: brand + desktop links */}
          <div className="flex items-center gap-6 lg:gap-8">
            <Link
              to={isAuthenticated ? '/dashboard' : '/'}
              className="group flex items-center gap-2.5 rounded-lg focus:outline-none focus-visible:ring-4 focus-visible:ring-indigo-100"
              aria-label="InsureWise AI home"
            >
              <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-indigo-700 text-white shadow-sm transition group-hover:shadow-md">
                <Shield className="h-4.5 w-4.5" aria-hidden="true" />
              </span>
              <span className="flex items-center gap-1.5">
                <span className="text-base font-extrabold tracking-tight text-slate-900">
                  InsureWise
                </span>
                <span className="rounded-md border border-indigo-200 bg-indigo-50 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-indigo-700">
                  AI
                </span>
              </span>
            </Link>

            <nav aria-label="Main" className="hidden items-center gap-1 md:flex">
              {navLinks.map(({ name, path, icon: Icon }) => {
                const active = isActive(path);
                return (
                  <Link
                    key={path}
                    to={path}
                    aria-current={active ? 'page' : undefined}
                    className={`flex items-center gap-1.5 rounded-lg px-3 py-2 text-xs font-semibold transition focus:outline-none focus-visible:ring-4 focus-visible:ring-indigo-100 ${
                      active
                        ? 'bg-indigo-50 text-indigo-700'
                        : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                    }`}
                  >
                    <Icon
                      className={`h-4 w-4 ${active ? 'text-indigo-600' : 'text-slate-400'}`}
                      aria-hidden="true"
                    />
                    {name}
                  </Link>
                );
              })}
            </nav>
          </div>

          {/* Right: status + user profile / auth action buttons */}
          <div className="flex items-center gap-3">
            <HealthStatus health={health} className="hidden sm:inline-flex" />

            {isAuthenticated ? (
              <div className="hidden sm:flex items-center gap-2">
                <div className="flex items-center gap-2 rounded-xl bg-slate-100 px-3 py-1.5 border border-slate-200/80">
                  <div className="flex h-6 w-6 items-center justify-center rounded-full bg-indigo-600 text-white text-[10px] font-bold">
                    {user?.name ? user.name.slice(0, 1).toUpperCase() : 'U'}
                  </div>
                  <div className="flex flex-col text-left">
                    <span className="text-xs font-bold text-slate-900 leading-none">
                      {user?.name || 'Customer'}
                    </span>
                    <span className="text-[10px] text-slate-500 leading-none mt-0.5">
                      {user?.email || ''}
                    </span>
                  </div>
                </div>

                <button
                  onClick={handleLogout}
                  title="Sign out"
                  className="flex items-center gap-1 rounded-xl border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-50 hover:text-rose-600 transition"
                >
                  <LogOut className="h-3.5 w-3.5" />
                  <span className="hidden lg:inline">Sign Out</span>
                </button>
              </div>
            ) : (
              <div className="hidden sm:flex items-center gap-2">
                <Link
                  to="/login"
                  className="rounded-xl px-3.5 py-1.5 text-xs font-bold text-slate-700 hover:bg-slate-100 transition"
                >
                  Sign In
                </Link>
                <Link
                  to="/signup"
                  className="inline-flex items-center gap-1.5 rounded-xl bg-indigo-600 px-4 py-1.5 text-xs font-bold text-white shadow-sm hover:bg-indigo-500 transition"
                >
                  <Sparkles className="h-3.5 w-3.5" />
                  <span>Get Started</span>
                </Link>
              </div>
            )}

            {/* Mobile toggle */}
            <button
              onClick={() => setMobileMenuOpen((open) => !open)}
              aria-label={mobileMenuOpen ? 'Close menu' : 'Open menu'}
              aria-expanded={mobileMenuOpen}
              aria-controls="mobile-menu"
              className="rounded-lg p-2 text-slate-500 transition hover:bg-slate-100 hover:text-slate-900 focus:outline-none focus-visible:ring-4 focus-visible:ring-indigo-100 md:hidden"
            >
              {mobileMenuOpen ? (
                <X className="h-5 w-5" aria-hidden="true" />
              ) : (
                <Menu className="h-5 w-5" aria-hidden="true" />
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile menu */}
      {mobileMenuOpen && (
        <div
          id="mobile-menu"
          className="space-y-2 border-t border-slate-200 bg-white px-4 pb-4 pt-3 shadow-lg md:hidden"
        >
          <nav aria-label="Mobile" className="space-y-1">
            {navLinks.map(({ name, path, icon: Icon }) => {
              const active = isActive(path);
              return (
                <Link
                  key={path}
                  to={path}
                  aria-current={active ? 'page' : undefined}
                  className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold transition ${
                    active
                      ? 'bg-indigo-50 text-indigo-700'
                      : 'text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  <Icon
                    className={`h-4 w-4 ${active ? 'text-indigo-600' : 'text-slate-400'}`}
                    aria-hidden="true"
                  />
                  {name}
                </Link>
              );
            })}
          </nav>

          {isAuthenticated ? (
            <div className="border-t border-slate-100 pt-3 space-y-2">
              <div className="flex items-center gap-2 px-2 py-1">
                <div className="flex h-7 w-7 items-center justify-center rounded-full bg-indigo-600 text-white text-xs font-bold">
                  {user?.name ? user.name.slice(0, 1).toUpperCase() : 'U'}
                </div>
                <div>
                  <div className="text-xs font-bold text-slate-900">{user?.name}</div>
                  <div className="text-[10px] text-slate-500">{user?.email}</div>
                </div>
              </div>
              <button
                onClick={handleLogout}
                className="w-full flex items-center justify-center gap-2 rounded-xl border border-slate-200 py-2 text-xs font-bold text-rose-600 hover:bg-rose-50 transition"
              >
                <LogOut className="h-3.5 w-3.5" />
                <span>Sign Out</span>
              </button>
            </div>
          ) : (
            <div className="border-t border-slate-100 pt-3 flex flex-col gap-2">
              <Link
                to="/login"
                className="w-full text-center rounded-xl border border-slate-200 py-2 text-xs font-bold text-slate-700 hover:bg-slate-50"
              >
                Sign In
              </Link>
              <Link
                to="/signup"
                className="w-full text-center rounded-xl bg-indigo-600 py-2 text-xs font-bold text-white shadow-sm hover:bg-indigo-500"
              >
                Create Free Account
              </Link>
            </div>
          )}

          <div className="border-t border-slate-100 pt-2 sm:hidden">
            <HealthStatus health={health} />
          </div>
        </div>
      )}
    </header>
  );
}