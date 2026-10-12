import React, { useState, useEffect, useCallback } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';

import Navbar from './components/Navbar';
import ErrorBoundary from './components/ErrorBoundary';

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
    <footer className="mt-auto border-t border-slate-200 bg-white">
      <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-2 px-4 py-4 text-center text-xs text-slate-500 sm:flex-row sm:px-6 sm:text-left lg:px-8">
        <p>
          © {new Date().getFullYear()} InsureWise AI. All policy answers are
          grounded strictly in document clauses.
        </p>
        <p className="font-medium text-slate-400">Healthtech AI SaaS Engine</p>
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
      <BrowserRouter>
        <div className="flex min-h-screen flex-col bg-slate-50 font-sans text-slate-900 antialiased">
          <Navbar health={health} />

          <main className="flex-1">
            <Routes>
              <Route path="/" element={<DashboardPage health={health} />} />
              <Route path="/policies" element={<PoliciesPage />} />
              <Route path="/policies/:id" element={<PolicyDetailPage />} />
              <Route path="/claims" element={<ClaimsPage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>

          <AppFooter />
        </div>
      </BrowserRouter>
    </ErrorBoundary>
  );
}