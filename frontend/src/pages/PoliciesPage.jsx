import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FileText,
  Plus,
  Zap,
  Search,
  X,
  Loader2,
  AlertCircle,
  Layers,
} from 'lucide-react';
import PolicyUpload from '../components/PolicyUpload';
import PolicyList from '../components/PolicyList';
import { api } from '../api/client';

const normalizeList = (data, key) =>
  Array.isArray(data) ? data : data?.[key] || [];

export default function PoliciesPage() {
  const [policies, setPolicies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showUpload, setShowUpload] = useState(false);
  const [loadingSample, setLoadingSample] = useState(false);
  const [query, setQuery] = useState('');
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    loadPolicies();
  }, []);

  const loadPolicies = async () => {
    try {
      setLoading(true);
      const res = await api.getPolicies();
      setPolicies(normalizeList(res, 'policies'));
    } catch (err) {
      console.error('Error loading policies:', err);
      setPolicies([]);
      setError('Could not load your policy library. Please refresh and try again.');
    } finally {
      setLoading(false);
    }
  };

  const hasProcessing = useMemo(() => {
    return Array.isArray(policies) && policies.some((p) => p.status === 'processing');
  }, [policies]);

  useEffect(() => {
    if (!hasProcessing) return;
    const interval = setInterval(async () => {
      try {
        const res = await api.getPolicies();
        setPolicies(normalizeList(res, 'policies'));
      } catch (err) {
        console.error('Error polling policies:', err);
      }
    }, 2500);
    return () => clearInterval(interval);
  }, [hasProcessing]);

  const handleUploadSuccess = () => {
    loadPolicies();
    setShowUpload(false);
  };

  const handleDeleteSuccess = (deletedId) => {
    setPolicies((prev) =>
      Array.isArray(prev) ? prev.filter((p) => p.id !== deletedId) : []
    );
  };

  const handleSelectPolicy = (id) => {
    navigate(`/policies/${id}`);
  };

  const handleLoadSample = async () => {
    setLoadingSample(true);
    setError(null);
    try {
      const sample = await api.loadSamplePolicy();
      await loadPolicies();
      navigate(`/policies/${sample.id}`);
    } catch (err) {
      setError('Failed to load sample policy: ' + err.message);
    } finally {
      setLoadingSample(false);
    }
  };

  const safePolicies = Array.isArray(policies) ? policies : [];

  const totalPages = safePolicies.reduce((acc, p) => acc + (p.page_count || 0), 0);

  const filteredPolicies = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return safePolicies;
    return safePolicies.filter((p) =>
      [p.display_name, p.policy_type]
        .filter(Boolean)
        .some((v) => String(v).toLowerCase().includes(q))
    );
  }, [safePolicies, query]);

  const noPolicies = !loading && safePolicies.length === 0;
  const uploadVisible = showUpload || noPolicies;
  const searching = query.trim().length > 0;

  return (
    <div className="min-h-full bg-gradient-to-b from-slate-50 to-white">
      <div className="mx-auto max-w-7xl space-y-6 px-4 py-6 sm:px-6 sm:py-8 lg:px-8">
        {/* Header */}
        <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <div className="mb-2 inline-flex items-center gap-1.5 rounded-full bg-indigo-50 px-2.5 py-1 text-[11px] font-semibold text-indigo-700 ring-1 ring-inset ring-indigo-200">
              <Layers className="h-3.5 w-3.5" />
              Policy library
            </div>
            <h1 className="text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl">
              Policies
            </h1>
            <p className="mt-1 max-w-xl text-sm text-slate-500">
              Manage policy documents, inspect page chunks, and run grounded AI
              queries.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-2 sm:flex sm:items-center">
            <button
              onClick={handleLoadSample}
              disabled={loadingSample}
              className="inline-flex items-center justify-center gap-1.5 rounded-xl border border-indigo-200 bg-indigo-50 px-3.5 py-2.5 text-xs font-semibold text-indigo-700 transition hover:bg-indigo-100 disabled:opacity-60"
            >
              {loadingSample ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Zap className="h-3.5 w-3.5" />
              )}
              {loadingSample ? 'Loading…' : 'Load sample policy'}
            </button>

            <button
              onClick={() => setShowUpload((v) => !v)}
              aria-expanded={uploadVisible}
              className="inline-flex items-center justify-center gap-1.5 rounded-xl bg-indigo-600 px-3.5 py-2.5 text-xs font-semibold text-white shadow-sm transition hover:bg-indigo-700 focus:outline-none focus:ring-4 focus:ring-indigo-200"
            >
              {showUpload ? (
                <X className="h-3.5 w-3.5" />
              ) : (
                <Plus className="h-3.5 w-3.5" />
              )}
              {showUpload ? 'Close upload' : 'Upload policy'}
            </button>
          </div>
        </header>

        {/* Error banner */}
        {error && (
          <div
            role="alert"
            className="flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 p-3.5 text-rose-800"
          >
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-600" />
            <p className="flex-1 text-xs sm:text-sm">{error}</p>
            <button
              onClick={() => setError(null)}
              aria-label="Dismiss error"
              className="rounded p-0.5 text-rose-500 transition hover:bg-rose-100"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        )}

        {/* Upload panel */}
        {uploadVisible && !loading && (
          <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6">
            <div className="mb-4 flex items-start justify-between gap-3">
              <div>
                <h2 className="text-sm font-bold text-slate-900">
                  Upload a policy document
                </h2>
                <p className="mt-0.5 text-xs text-slate-500">
                  Add a policy PDF to ingest it for Q&amp;A and claim checks.
                </p>
              </div>
              {showUpload && (
                <button
                  onClick={() => setShowUpload(false)}
                  aria-label="Close upload"
                  className="rounded-lg p-1.5 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>
            <div className="max-w-2xl">
              <PolicyUpload onUploadSuccess={handleUploadSuccess} />
            </div>
          </section>
        )}

        {/* Toolbar: summary + search */}
        {!loading && safePolicies.length > 0 && (
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex flex-wrap items-center gap-2 text-[11px] font-semibold">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-white px-3 py-1.5 text-slate-700 shadow-sm ring-1 ring-slate-200">
                <FileText className="h-3.5 w-3.5 text-indigo-600" />
                {safePolicies.length}{' '}
                {safePolicies.length === 1 ? 'policy' : 'policies'}
              </span>
              {totalPages > 0 && (
                <span className="rounded-full bg-white px-3 py-1.5 text-slate-700 shadow-sm ring-1 ring-slate-200">
                  {totalPages.toLocaleString()} pages indexed
                </span>
              )}
            </div>

            <div className="relative w-full sm:w-72">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input
                type="search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search policies…"
                aria-label="Search policies"
                className="w-full rounded-xl border border-slate-200 bg-white py-2.5 pl-9 pr-9 text-sm text-slate-900 placeholder-slate-400 shadow-sm transition focus:border-indigo-500 focus:outline-none focus:ring-4 focus:ring-indigo-100"
              />
              {query && (
                <button
                  onClick={() => setQuery('')}
                  aria-label="Clear search"
                  className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
          </div>
        )}

        {/* Policy library */}
        {loading ? (
          <div
            className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3"
            aria-busy="true"
            aria-label="Loading policy library"
          >
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="h-32 animate-pulse rounded-2xl border border-slate-200 bg-white"
              />
            ))}
          </div>
        ) : searching && filteredPolicies.length === 0 ? (
          <div className="flex flex-col items-center rounded-2xl border border-dashed border-slate-300 bg-white/70 px-6 py-12 text-center">
            <span className="mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-100 text-slate-400">
              <Search className="h-6 w-6" />
            </span>
            <h3 className="text-sm font-bold text-slate-900">No matching policies</h3>
            <p className="mt-1 text-xs text-slate-500">
              Nothing matches “{query.trim()}”. Try a different name or type.
            </p>
            <button
              onClick={() => setQuery('')}
              className="mt-4 rounded-lg bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-200"
            >
              Clear search
            </button>
          </div>
        ) : (
          <PolicyList
            policies={filteredPolicies}
            onDeleteSuccess={handleDeleteSuccess}
            onSelectPolicy={handleSelectPolicy}
            onLoadSample={handleLoadSample}
          />
        )}
      </div>
    </div>
  );
}