import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  FileText,
  MessageSquare,
  ShieldAlert,
  Trash2,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Zap,
  AlertCircle,
  Loader2,
  X,
} from 'lucide-react';
import { api } from '../api/client';

/* ----------------------------- Helpers ----------------------------- */

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

/* --------------------------- Sub-components --------------------------- */

function StatusBadge({ status, errorMessage }) {
  const isReady = status === 'ready';
  const isFailed = status === 'failed';

  const cls = isReady
    ? 'bg-emerald-50 text-emerald-700 ring-emerald-200'
    : isFailed
    ? 'bg-rose-50 text-rose-700 ring-rose-200'
    : 'bg-amber-50 text-amber-700 ring-amber-200';

  return (
    <span
      title={isFailed && errorMessage ? errorMessage : undefined}
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-semibold capitalize ring-1 ring-inset ${cls}`}
    >
      {isReady && <CheckCircle2 className="h-3 w-3" aria-hidden="true" />}
      {isFailed && <AlertTriangle className="h-3 w-3" aria-hidden="true" />}
      {!isReady && !isFailed && (
        <Clock className="h-3 w-3 animate-spin" aria-hidden="true" />
      )}
      {status || 'processing'}
    </span>
  );
}

function PolicyActions({ policy, confirming, deleting, onAskDelete, onCancel, onConfirm }) {
  const ready = policy.status === 'ready';

  if (confirming) {
    return (
      <div className="flex items-center justify-end gap-1.5">
        <span className="text-[11px] font-medium text-slate-500">Delete?</span>
        <button
          onClick={onConfirm}
          disabled={deleting}
          className="inline-flex items-center gap-1 rounded-lg bg-rose-600 px-2.5 py-1.5 text-[11px] font-semibold text-white transition hover:bg-rose-700 disabled:opacity-60"
        >
          {deleting && <Loader2 className="h-3 w-3 animate-spin" />}
          Yes, delete
        </button>
        <button
          onClick={onCancel}
          disabled={deleting}
          className="rounded-lg border border-slate-200 px-2.5 py-1.5 text-[11px] font-semibold text-slate-600 transition hover:bg-slate-50"
        >
          Cancel
        </button>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-end gap-1.5">
      {ready ? (
        <>
          <Link
            to={`/policies/${policy.id}`}
            className="inline-flex items-center gap-1 rounded-lg bg-slate-100 px-2.5 py-1.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-200"
          >
            <MessageSquare className="h-3.5 w-3.5 text-indigo-600" aria-hidden="true" />
            Ask AI
          </Link>
          <Link
            to={`/claims?policyId=${policy.id}`}
            className="inline-flex items-center gap-1 rounded-lg border border-indigo-200 bg-indigo-50 px-2.5 py-1.5 text-xs font-semibold text-indigo-700 transition hover:bg-indigo-100"
          >
            <ShieldAlert className="h-3.5 w-3.5 text-indigo-600" aria-hidden="true" />
            Claim
          </Link>
        </>
      ) : null}

      <button
        onClick={onAskDelete}
        aria-label={`Delete ${policy.display_name}`}
        title="Delete policy"
        className="rounded-lg p-1.5 text-slate-400 transition hover:bg-rose-50 hover:text-rose-600"
      >
        <Trash2 className="h-4 w-4" />
      </button>
    </div>
  );
}

function PolicyIcon() {
  return (
    <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-indigo-100 bg-indigo-50 text-indigo-600">
      <FileText className="h-5 w-5" aria-hidden="true" />
    </span>
  );
}

/* ------------------------------ Component ------------------------------ */

/**
 * Presentational list of policies.
 * Searching/filtering is owned by the parent page, which passes the
 * already-filtered `policies` array.
 */
export default function PolicyList({
  policies,
  onDeleteSuccess,
  onSelectPolicy,
  onLoadSample,
}) {
  const [confirmingId, setConfirmingId] = useState(null);
  const [deletingId, setDeletingId] = useState(null);
  const [error, setError] = useState(null);

  const safePolicies = Array.isArray(policies) ? policies : [];

  const handleDelete = async (id) => {
    setDeletingId(id);
    setError(null);
    try {
      await api.deletePolicy(id);
      setConfirmingId(null);
      if (onDeleteSuccess) onDeleteSuccess(id);
    } catch (err) {
      setError('Failed to delete policy: ' + err.message);
    } finally {
      setDeletingId(null);
    }
  };

  const openPolicy = (policy) => {
    if (policy.status === 'ready' && onSelectPolicy) onSelectPolicy(policy.id);
  };

  /* ----------------------------- Empty state ----------------------------- */
  if (safePolicies.length === 0) {
    return (
      <div className="flex flex-col items-center rounded-2xl border border-dashed border-slate-300 bg-white/70 px-6 py-12 text-center">
        <span className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-100 text-slate-400">
          <FileText className="h-7 w-7" aria-hidden="true" />
        </span>
        <h3 className="text-base font-bold text-slate-900">No policies yet</h3>
        <p className="mt-1 max-w-sm text-sm text-slate-500">
          Upload your insurance policy PDF, or load a sample vehicle policy to
          try the assistant.
        </p>
        {onLoadSample && (
          <button
            onClick={onLoadSample}
            className="mt-5 inline-flex items-center gap-1.5 rounded-xl border border-indigo-200 bg-indigo-50 px-4 py-2.5 text-xs font-semibold text-indigo-700 transition hover:bg-indigo-100"
          >
            <Zap className="h-3.5 w-3.5" aria-hidden="true" />
            Load sample vehicle policy
          </button>
        )}
      </div>
    );
  }

  const actionProps = (policy) => ({
    policy,
    confirming: confirmingId === policy.id,
    deleting: deletingId === policy.id,
    onAskDelete: () => {
      setError(null);
      setConfirmingId(policy.id);
    },
    onCancel: () => setConfirmingId(null),
    onConfirm: () => handleDelete(policy.id),
  });

  return (
    <div className="space-y-3">
      {error && (
        <div
          role="alert"
          className="flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 p-3 text-rose-800"
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

      {/* Mobile / small tablet: cards */}
      <ul className="space-y-3 md:hidden">
        {safePolicies.map((policy) => {
          const ready = policy.status === 'ready';
          return (
            <li
              key={policy.id}
              className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"
            >
              <div className="flex items-start gap-3">
                <PolicyIcon />
                <div className="min-w-0 flex-1">
                  <button
                    onClick={() => openPolicy(policy)}
                    disabled={!ready}
                    className="block max-w-full truncate text-left text-sm font-bold text-slate-900 enabled:hover:text-indigo-700"
                  >
                    {policy.display_name}
                  </button>
                  <p className="mt-0.5 text-[11px] capitalize text-slate-500">
                    {policy.policy_type || 'General'} • Uploaded{' '}
                    {formatDate(policy.uploaded_at)}
                  </p>
                </div>
                <StatusBadge status={policy.status} errorMessage={policy.error_message} />
              </div>

              <p className="mt-3 text-xs text-slate-500">
                {policy.page_count ?? '—'} pages • {policy.chunk_count ?? '—'}{' '}
                chunks
              </p>

              <div className="mt-3 border-t border-slate-100 pt-3">
                <PolicyActions {...actionProps(policy)} />
              </div>
            </li>
          );
        })}
      </ul>

      {/* Desktop: table */}
      <div className="hidden overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm md:block">
        <table className="w-full border-collapse text-left">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50/80 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              <th scope="col" className="px-5 py-3">Document</th>
              <th scope="col" className="px-4 py-3">Type</th>
              <th scope="col" className="px-4 py-3">Pages / chunks</th>
              <th scope="col" className="px-4 py-3">Status</th>
              <th scope="col" className="px-5 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 text-xs">
            {safePolicies.map((policy) => {
              const ready = policy.status === 'ready';
              return (
                <tr
                  key={policy.id}
                  onClick={() => openPolicy(policy)}
                  className={`transition-colors hover:bg-slate-50/80 ${
                    ready ? 'cursor-pointer' : ''
                  }`}
                >
                  <td className="px-5 py-3.5">
                    <div className="flex max-w-xs items-center gap-3 lg:max-w-sm">
                      <PolicyIcon />
                      <div className="min-w-0">
                        <p
                          className="truncate text-sm font-semibold text-slate-900"
                          title={policy.display_name}
                        >
                          {policy.display_name}
                        </p>
                        <p className="text-[11px] text-slate-400">
                          Uploaded {formatDate(policy.uploaded_at)}
                        </p>
                      </div>
                    </div>
                  </td>

                  <td className="px-4 py-3.5">
                    <span className="font-medium capitalize text-slate-600">
                      {policy.policy_type || 'General'}
                    </span>
                  </td>

                  <td className="whitespace-nowrap px-4 py-3.5 font-medium text-slate-600">
                    {policy.page_count ?? '—'} pgs / {policy.chunk_count ?? '—'}{' '}
                    chunks
                  </td>

                  <td className="px-4 py-3.5">
                    <StatusBadge status={policy.status} errorMessage={policy.error_message} />
                  </td>

                  <td
                    className="px-5 py-3.5"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <PolicyActions {...actionProps(policy)} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}