import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ArrowLeft,
  FileText,
  ExternalLink,
  ShieldAlert,
  Layers,
  CheckCircle2,
  Sparkles,
  AlertCircle,
  Calendar,
  Loader2,
} from 'lucide-react';
import PolicyChat from '../components/PolicyChat';
import { api } from '../api/client';

const formatDate = (value) => {
  if (!value) return '—';
  const d = new Date(value);
  return Number.isNaN(d.getTime())
    ? '—'
    : d.toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
};

function Stat({ label, value, icon: Icon }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-3">
      <div className="flex items-center gap-1.5 text-[11px] font-medium text-slate-500">
        <Icon className="h-3.5 w-3.5 text-indigo-600" />
        {label}
      </div>
      <p className="mt-1 text-lg font-extrabold tracking-tight text-slate-900">
        {value}
      </p>
    </div>
  );
}

function PageShell({ children }) {
  return (
    <div className="min-h-full bg-gradient-to-b from-slate-50 to-white">
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8 lg:px-8">
        {children}
      </div>
    </div>
  );
}

export default function PolicyDetail() {
  const { id } = useParams();
  const [policy, setPolicy] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadPolicy();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const loadPolicy = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getPolicy(id);
      setPolicy(data);
    } catch (err) {
      setError(err.message || 'Failed to load policy');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (policy?.status !== 'processing') return;
    const interval = setInterval(async () => {
      try {
        const data = await api.getPolicy(id);
        setPolicy(data);
      } catch (err) {
        console.error('Failed to poll policy details:', err);
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [policy?.status, id]);

  /* ---------------------------- Loading state ---------------------------- */
  if (loading) {
    return (
      <PageShell>
        <div className="space-y-6" aria-busy="true" aria-label="Loading policy details">
          <div className="space-y-3">
            <div className="h-4 w-32 animate-pulse rounded bg-slate-200" />
            <div className="h-8 w-2/3 max-w-md animate-pulse rounded bg-slate-200" />
            <div className="h-3 w-48 animate-pulse rounded bg-slate-100" />
          </div>
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3 lg:gap-8">
            <div className="h-80 animate-pulse rounded-2xl border border-slate-200 bg-white" />
            <div className="h-80 animate-pulse rounded-2xl border border-slate-200 bg-white lg:col-span-2" />
          </div>
        </div>
      </PageShell>
    );
  }

  /* ----------------------------- Error state ----------------------------- */
  if (error || !policy) {
    return (
      <PageShell>
        <div
          role="alert"
          className="mx-auto max-w-md rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm"
        >
          <span className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-rose-50 text-rose-600">
            <AlertCircle className="h-6 w-6" />
          </span>
          <h2 className="text-base font-bold text-slate-900">
            {error ? 'Something went wrong' : 'Policy not found'}
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            {error || "We couldn't find the policy you're looking for."}
          </p>
          <div className="mt-5 flex flex-col justify-center gap-2 sm:flex-row">
            {error && (
              <button
                onClick={loadPolicy}
                className="inline-flex items-center justify-center gap-1.5 rounded-xl bg-indigo-600 px-4 py-2.5 text-xs font-semibold text-white shadow-sm transition hover:bg-indigo-700"
              >
                <Loader2 className="h-3.5 w-3.5" />
                Try again
              </button>
            )}
            <Link
              to="/policies"
              className="inline-flex items-center justify-center gap-1.5 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-50"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              Back to policies
            </Link>
          </div>
        </div>
      </PageShell>
    );
  }

  /* ------------------------------- Main view ------------------------------- */
  return (
    <PageShell>
      <div className="space-y-6">
        {/* Header */}
        <header className="space-y-4">
          <Link
            to="/policies"
            className="inline-flex items-center gap-1 text-xs font-medium text-slate-500 transition hover:text-slate-900"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to policies
          </Link>

          <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div className="flex min-w-0 items-start gap-3 sm:gap-4">
              <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-indigo-600 text-white shadow-sm">
                <FileText className="h-6 w-6" />
              </span>
              <div className="min-w-0">
                <h1
                  className="truncate text-xl font-extrabold tracking-tight text-slate-900 sm:text-2xl"
                  title={policy.display_name}
                >
                  {policy.display_name}
                </h1>
                <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500">
                  <span className="rounded-full bg-indigo-50 px-2 py-0.5 font-semibold capitalize text-indigo-700 ring-1 ring-inset ring-indigo-200">
                    {policy.policy_type || 'Insurance policy'}
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <Calendar className="h-3 w-3" />
                    Uploaded {formatDate(policy.uploaded_at)}
                  </span>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 sm:flex sm:shrink-0 sm:items-center">
              <a
                href={api.getPolicyPdf(policy.id)}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center justify-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-xs font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50"
              >
                <ExternalLink className="h-3.5 w-3.5 text-indigo-600" />
                View PDF
              </a>

              <Link
                to={`/claims?policyId=${policy.id}`}
                className="inline-flex items-center justify-center gap-1.5 rounded-xl bg-indigo-600 px-3.5 py-2.5 text-xs font-semibold text-white shadow-sm transition hover:bg-indigo-700 focus:outline-none focus:ring-4 focus:ring-indigo-200"
              >
                <ShieldAlert className="h-3.5 w-3.5" />
                Start claim
              </Link>
            </div>
          </div>
        </header>

        {/* Grid */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3 lg:gap-8">
          {/* Left: overview */}
          <aside className="space-y-6 lg:sticky lg:top-6 lg:self-start">
            <section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <h2 className="text-sm font-bold text-slate-900">
                    Document overview
                  </h2>
                  <p className="text-[11px] text-slate-500">FAISS vector indexed</p>
                </div>
                <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-1 text-[11px] font-semibold capitalize text-emerald-700 ring-1 ring-inset ring-emerald-200">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  {policy.status || 'ready'}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <Stat
                  label="Pages"
                  value={policy.page_count ?? '—'}
                  icon={FileText}
                />
                <Stat
                  label="Chunks"
                  value={policy.chunk_count ?? '—'}
                  icon={Layers}
                />
              </div>

              <div className="rounded-xl border border-indigo-100 bg-gradient-to-br from-indigo-50/80 to-violet-50/60 p-4">
                <div className="mb-1.5 flex items-center gap-1.5 text-xs font-bold text-indigo-700">
                  <Sparkles className="h-3.5 w-3.5 text-indigo-600" />
                  AI policy summary
                </div>
                <p className="text-xs leading-relaxed text-slate-700">
                  {policy.summary ||
                    'Policy uploaded and indexed for vector search.'}
                </p>
              </div>
            </section>
          </aside>

          {/* Right: chat */}
          <div className="min-w-0 lg:col-span-2">
            <PolicyChat policyId={policy.id} policyType={policy.policy_type} policyStatus={policy.status} />
          </div>
        </div>
      </div>
    </PageShell>
  );
}