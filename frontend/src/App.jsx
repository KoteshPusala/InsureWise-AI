import React, { useState, useEffect, useCallback } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';

import { AuthProvider } from './context/AuthContext';
import Navbar from './components/Navbar';
import ErrorBoundary from './components/ErrorBoundary';

import LandingPage from './pages/LandingPage';
import AboutPage from './pages/AboutPage';
import LoginPage from './pages/LoginPage';
import SignupPage from './pages/SignupPage';

import DashboardPage from './pages/Dashboard';
import PoliciesPage from './pages/PoliciesPage';
import PolicyDetailPage from './pages/PolicyDetail';
import ClaimsPage from './pages/ClaimsPage';

import { api } from './api/client';

/* ------------------------------ Constants ------------------------------ */

const HEALTH_POLL_INTERVAL_MS = 30_000;

/* ------------------------------ Footer ------------------------------ */

function AppFooter() {
  return (
    <footer className="mt-auto border-t border-slate-800 bg-slate-950 text-slate-400">
      <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-3 px-4 py-6 text-center text-xs sm:flex-row sm:px-6 sm:text-left lg:px-8">
        <p>
          © {new Date().getFullYear()} InsureWise AI. All policy answers and claim audits are
          grounded strictly in document clauses.
        </p>
        <div className="flex items-center gap-4 text-slate-400">
          <a href="/about" className="hover:text-indigo-400 transition">About Architecture</a>
          <span>•</span>
          <a href="/login" className="hover:text-indigo-400 transition">Customer Sign In</a>
          <span>•</span>
          <span className="font-semibold text-slate-300">Isolated Sovereign Privacy</span>
        </div>
      </div>
    </footer>
  );
}

/* -------------------------------- App -------------------------------- */

export default function App() {
  const [health, setHealth] = useState(null);

  const loadHealthStatus = useCallback(async () => {
    try {
      const status = await api.getHealth({ timeoutMs: 5000 });
      setHealth(status);
    } catch (err) {
      setHealth({ status: 'offline', error: err.message });
    }
  }, []);

  useEffect(() => {
    loadHealthStatus();
    const intervalId = setInterval(loadHealthStatus, HEALTH_POLL_INTERVAL_MS);
    return () => clearInterval(intervalId);
  }, [loadHealthStatus]);

  return (
    <ErrorBoundary>
      <AuthProvider>
        <BrowserRouter>
          <div className="flex min-h-screen flex-col bg-slate-50 font-sans text-slate-900 antialiased">
            <Navbar health={health} />

            <main className="flex-1">
              <Routes>
                {/* Public Marketing & Informational Pages */}
                <Route path="/" element={<LandingPage />} />
                <Route path="/about" element={<AboutPage />} />
                <Route path="/login" element={<LoginPage />} />
                <Route path="/signup" element={<SignupPage />} />

                {/* Application Core Pages */}
                <Route path="/dashboard" element={<DashboardPage health={health} />} />
                <Route path="/policies" element={<PoliciesPage />} />
                <Route path="/policies/:id" element={<PolicyDetailPage />} />
                <Route path="/claims" element={<ClaimsPage />} />

                {/* Fallback */}
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </main>

            <AppFooter />
          </div>
        </BrowserRouter>
      </AuthProvider>
    </ErrorBoundary>
  );
}