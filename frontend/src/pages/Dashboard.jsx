import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  FileText,
  ClipboardCheck,
  Zap,
  ArrowRight,
  ShieldCheck,
  Layers,
  Plus,
  AlertCircle,
  FileUp,
  Loader2,
  X,
  Sparkles,
  ChevronRight,
} from 'lucide-react';
import { api } from '../api/client';

/* ----------------------------- Helpers ----------------------------- */

const normalizeList = (data, key) =>
  Array.isArray(data) ? data : data?.[key] || [];

const formatType = (t = '') => t.replace(/_/g, ' ');

const TONES = {
  indigo: 'bg-indigo-50 text-indigo-600',
  violet: 'bg-violet-50 text-violet-600',
  sky: 'bg-sky-50 text-sky-600',
  emerald: 'bg-emerald-50 text-emerald-600',
};

function StatCard({ label, value, icon: Icon, tone = 'indigo', loading, valueClass = '' }) {
  return (
    <div className="group flex items-center justify-between rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md sm:p-5">
      <div className="min-w-0">
        <p className="text-xs font-medium text-slate-500">{label}</p>
        {loading ? (
          <div className="mt-2 h-7 w-14 animate-pulse rounded bg-slate-100" />
        ) : (
          <p
            className={`mt-1 truncate text-2xl font-extrabold tracking-tight text-slate-900 ${valueClass}`}
          >
            {value}
          </p>
        )}
      </div>
      <span
        className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl transition group-hover:scale-105 ${TONES[tone]}`}
      >
        <Icon className="h-5 w-5" />
      </span>
    </div>
  );
}

function ListCard({ title, icon: Icon, linkTo, linkLabel, children }) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
      <header className="mb-3 flex items-center justify-between gap-3">
        <h2 className="flex items-center gap-2 text-sm font-bold text-slate-900">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
            <Icon className="h-4 w-4" />
          </span>
          {title}
        </h2>
        <Link
          to={linkTo}
          className="inline-flex items-center gap-0.5 text-xs font-semibold text-indigo-600 hover:text-indigo-800"
        >
          {linkLabel}
          <ChevronRight className="h-3.5 w-3.5" />
        </Link>
      </header>
      {children}
    </section>
  );
}

function RowSkeleton() {
  return (
    <div className="space-y-2" aria-busy="true">
      {[0, 1, 2].map((i) => (
        <div key={i} className="h-14 animate-pulse rounded-xl bg-slate-100" />
      ))}
    </div>
  );
}

function EmptyState({ children }) {
  return (
    <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50/60 py-8 text-center text-xs text-slate-400">
      {children}
    </div>
  );
}

/* ------------------------------ Page ------------------------------ */

export default function Dashboard({ health }) {
  const [policies, setPolicies] = useState([]);
  const [claims, setClaims] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadingSample, setLoadingSample] = useState(false);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const polData = await api.getPolicies();
      setPolicies(normalizeList(polData, 'policies'));

      const claimData = await api.getClaims();
      setClaims(normalizeList(claimData, 'claims'));
    } catch (err) {
      console.error('Error loading overview data:', err);
      setError('Could not load overview data. Please refresh and try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleLoadSample = async () => {
    setLoadingSample(true);
    setError(null);
    try {
      const sample = await api.loadSamplePolicy();
      await loadData();
      navigate(`/policies/${sample.id}`);
    } catch (err) {
      setError('Failed to load sample: ' + err.message);
    } finally {
      setLoadingSample(false);
    }
  };

  const safePolicies = Array.isArray(policies) ? policies : [];
  const safeClaims = Array.isArray(claims) ? claims : [];
  const totalChunks = safePolicies.reduce((acc, p) => acc + (p.chunk_count || 0), 0);
  const showOnboarding = !loading && safePolicies.length === 0;

  const SampleButton = ({ variant = 'soft', label }) => (
    <button
      onClick={handleLoadSample}
      disabled={loadingSample}
      className={
        variant === 'solid'
          ? 'inline-flex items-center justify-center gap-1.5 rounded-xl bg-indigo-600 px-4 py-2.5 text-xs font-semibold text-white shadow-sm transition hover:bg-indigo-700 focus:outline-none focus:ring-4 focus:ring-indigo-200 disabled:opacity-60'
          : 'inline-flex items-center justify-center gap-1.5 rounded-xl border border-indigo-200 bg-indigo-50 px-3.5 py-2.5 text-xs font-semibold text-indigo-700 transition hover:bg-indigo-100 disabled:opacity-60'
      }
    >
      {loadingSample ? (
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
      ) : (
        <Zap className="h-3.5 w-3.5" />
      )}
      {loadingSample ? 'Loading sample…' : label}
    </button>
  );

  return (
    <div className="min-h-full bg-gradient-to-b from-slate-50 to-white">
      <div className="mx-auto max-w-7xl space-y-6 px-4 py-6 sm:space-y-8 sm:px-6 sm:py-8 lg:px-8">
        {/* Header */}
        <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <div className="mb-2 inline-flex items-center gap-1.5 rounded-full bg-indigo-50 px-2.5 py-1 text-[11px] font-semibold text-indigo-700 ring-1 ring-inset ring-indigo-200">
              <Sparkles className="h-3.5 w-3.5" />
              InsureWise AI
            </div>
            <h1 className="text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl">
              Overview
            </h1>
            <p className="mt-1 max-w-xl text-sm text-slate-500">
              Monitor insurance policies, AI ingestion status, and active claim
              readiness audits.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-2 sm:flex sm:items-center">
            <SampleButton label="Load sample policy" />
            <Link
              to="/policies"
              className="inline-flex items-center justify-center gap-1.5 rounded-xl bg-slate-900 px-3.5 py-2.5 text-xs font-semibold text-white shadow-sm transition hover:bg-slate-800"
            >
              <Plus className="h-3.5 w-3.5" />
              Upload policy
            </Link>
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

        {/* Metrics */}
        <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
          <StatCard
            label="Ingested policies"
            value={safePolicies.length}
            icon={FileText}
            tone="indigo"
            loading={loading}
          />
          <StatCard
            label="Active claims"
            value={safeClaims.length}
            icon={ClipboardCheck}
            tone="violet"
            loading={loading}
          />
          <StatCard
            label="Vector chunks"
            value={totalChunks.toLocaleString()}
            icon={Layers}
            tone="sky"
            loading={loading}
          />
          <StatCard
            label="AI engine"
            value={health?.llm_provider || 'Online'}
            icon={ShieldCheck}
            tone="emerald"
            valueClass="!text-base uppercase !text-emerald-600 sm:!text-lg"
          />
        </div>

        {/* Onboarding */}
        {showOnboarding && (
          <section className="relative overflow-hidden rounded-2xl border border-indigo-100 bg-gradient-to-br from-indigo-50 via-white to-violet-50 p-6 text-center shadow-sm sm:p-10">
            <span className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-white text-indigo-600 shadow-sm ring-1 ring-indigo-100">
              <FileUp className="h-7 w-7" />
            </span>
            <h3 className="text-lg font-extrabold text-slate-900">
              Welcome to InsureWise AI
            </h3>
            <p className="mx-auto mt-1 max-w-md text-sm text-slate-500">
              Upload your insurance policy PDF, or ingest a sample vehicle policy
              to try instant policy Q&amp;A and claim readiness checks.
            </p>
            <div className="mt-5 flex flex-col items-stretch justify-center gap-2 sm:flex-row sm:items-center">
              <SampleButton variant="solid" label="Load sample vehicle policy" />
              <Link
                to="/policies"
                className="inline-flex items-center justify-center rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-50"
              >
                Upload PDF file
              </Link>
            </div>
          </section>
        )}

        {/* Lists */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2 lg:gap-8">
          <ListCard
            title="Recent policies"
            icon={FileText}
            linkTo="/policies"
            linkLabel={`View all (${safePolicies.length})`}
          >
            {loading ? (
              <RowSkeleton />
            ) : safePolicies.length === 0 ? (
              <EmptyState>No policies ingested yet.</EmptyState>
            ) : (
              <ul className="space-y-1.5">
                {safePolicies.slice(0, 4).map((p) => (
                  <li key={p.id}>
                    <Link
                      to={`/policies/${p.id}`}
                      className="group flex items-center gap-3 rounded-xl border border-transparent px-2.5 py-2.5 transition hover:border-slate-200 hover:bg-slate-50"
                    >
                      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-slate-500 transition group-hover:bg-indigo-50 group-hover:text-indigo-600">
                        <FileText className="h-4 w-4" />
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-semibold text-slate-900">
                          {p.display_name}
                        </p>
                        <p className="truncate text-[11px] capitalize text-slate-500">
                          {p.policy_type || 'General policy'}
                          {p.page_count != null && ` • ${p.page_count} pages`}
                        </p>
                      </div>
                      <span className="flex shrink-0 items-center gap-1 text-xs font-semibold text-indigo-600">
                        <span className="hidden sm:inline">Open</span>
                        <ArrowRight className="h-3.5 w-3.5 transition group-hover:translate-x-0.5" />
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </ListCard>

          <ListCard
            title="Recent claims"
            icon={ClipboardCheck}
            linkTo="/claims"
            linkLabel={`View claims (${safeClaims.length})`}
          >
            {loading ? (
              <RowSkeleton />
            ) : safeClaims.length === 0 ? (
              <EmptyState>
                No claims created yet.{' '}
                <Link
                  to="/claims"
                  className="font-semibold text-indigo-600 hover:underline"
                >
                  Start a claim audit
                </Link>
              </EmptyState>
            ) : (
              <ul className="space-y-1.5">
                {safeClaims.slice(0, 4).map((c) => (
                  <li key={c.id}>
                    <Link
                      to="/claims"
                      className="group flex items-center gap-3 rounded-xl border border-transparent px-2.5 py-2.5 transition hover:border-slate-200 hover:bg-slate-50"
                    >
                      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-slate-500 transition group-hover:bg-violet-50 group-hover:text-violet-600">
                        <ClipboardCheck className="h-4 w-4" />
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-semibold capitalize text-slate-900">
                          {formatType(c.incident_type)}
                        </p>
                        <p className="truncate text-[11px] text-slate-500">
                          {c.incident_description}
                        </p>
                      </div>
                      <span className="flex shrink-0 items-center gap-1 text-xs font-semibold text-indigo-600">
                        <span className="hidden sm:inline">View</span>
                        <ArrowRight className="h-3.5 w-3.5 transition group-hover:translate-x-0.5" />
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </ListCard>
        </div>
      </div>
    </div>
  );
}