import React, { useState, useRef, useEffect } from 'react';
import {
  UploadCloud,
  Sparkles,
  AlertCircle,
  Loader2,
  FileText,
  Zap,
  X,
  CheckCircle2,
  RefreshCw,
} from 'lucide-react';
import { api } from '../api/client';

/* ------------------------------ Constants ------------------------------ */

const MAX_FILE_SIZE_MB = 15;
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;
const MAX_POLL_TIMEOUT_MS = 180_000; // 3 minutes max

const STAGES = [
  { key: 'uploading', label: 'Validating & uploading policy PDF' },
  { key: 'extracting_text', label: 'Extracting document text & OCR inspection' },
  { key: 'chunking', label: 'Segmenting clauses and policy sections' },
  { key: 'building_index', label: 'Generating vector embeddings & FAISS index' },
  { key: 'analyzing', label: 'Analyzing policy terms & generating summary' },
];

const STAGE_ORDER = {
  uploading: 0,
  extracting_text: 1,
  chunking: 2,
  building_index: 3,
  analyzing: 4,
  completed: 5,
};

const formatSize = (bytes) =>
  bytes >= 1024 * 1024
    ? `${(bytes / (1024 * 1024)).toFixed(2)} MB`
    : `${Math.max(1, Math.round(bytes / 1024))} KB`;

/* ------------------------------ Component ------------------------------ */

export default function PolicyUpload({ onUploadSuccess }) {
  const [isDragging, setIsDragging] = useState(false);
  const [file, setFile] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [currentStage, setCurrentStage] = useState('uploading');
  const [loadingSample, setLoadingSample] = useState(false);
  const [error, setError] = useState(null);

  const inputRef = useRef(null);
  const pollTimerRef = useRef(null);
  const isMountedRef = useRef(true);

  const busy = processing || loadingSample;

  const clearPollTimer = () => {
    if (pollTimerRef.current) {
      clearTimeout(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  };

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      clearPollTimer();
    };
  }, []);

  /* ----------------------------- Polling logic ----------------------------- */

  const pollPolicyStatus = (policyId, startTime = Date.now(), delay = 1500) => {
    clearPollTimer();
    pollTimerRef.current = setTimeout(async () => {
      if (!isMountedRef.current) return;

      if (Date.now() - startTime > MAX_POLL_TIMEOUT_MS) {
        setProcessing(false);
        setError('Processing is taking longer than expected. Please check the Policies tab or retry.');
        return;
      }

      try {
        const policy = await api.getPolicy(policyId);
        if (!isMountedRef.current) return;

        if (policy.progress_stage) {
          setCurrentStage(policy.progress_stage);
        }

        if (policy.status === 'ready') {
          setProcessing(false);
          setFile(null);
          if (onUploadSuccess) onUploadSuccess(policy);
        } else if (policy.status === 'failed') {
          setProcessing(false);
          setError(policy.error_message || 'Policy processing failed. Please check the PDF and retry.');
        } else {
          // Continue polling with gentle backoff
          const nextDelay = Math.min(delay + 500, 3000);
          pollPolicyStatus(policyId, startTime, nextDelay);
        }
      } catch (err) {
        if (!isMountedRef.current) return;
        // In case of a transient network error, retry polling up to timeout
        const nextDelay = Math.min(delay + 1000, 4000);
        pollPolicyStatus(policyId, startTime, nextDelay);
      }
    }, delay);
  };

  /* ----------------------------- File handling ----------------------------- */

  const handleFileSelection = (selectedFile) => {
    setError(null);
    if (!selectedFile) return;

    const isPdf =
      selectedFile.type === 'application/pdf' ||
      selectedFile.name.toLowerCase().endsWith('.pdf');

    if (!isPdf) {
      setError('Only PDF documents are allowed.');
      return;
    }
    if (selectedFile.size === 0) {
      setError('This file is empty (0 bytes). Please choose a valid PDF.');
      return;
    }
    if (selectedFile.size > MAX_FILE_SIZE_BYTES) {
      setError(`File size exceeds the ${MAX_FILE_SIZE_MB} MB limit.`);
      return;
    }
    setFile(selectedFile);
  };

  const handleFileChange = (e) => {
    handleFileSelection(e.target.files?.[0]);
    e.target.value = '';
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    if (!busy) setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    if (!e.currentTarget.contains(e.relatedTarget)) setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (busy) return;
    handleFileSelection(e.dataTransfer.files?.[0]);
  };

  const removeFile = () => {
    setFile(null);
    setError(null);
  };

  /* ------------------------------- Actions ------------------------------- */

  const handleUpload = async () => {
    if (!file || busy) return;
    setProcessing(true);
    setError(null);
    setCurrentStage('uploading');

    try {
      const initialPolicy = await api.uploadPolicy(file);
      if (initialPolicy.status === 'ready') {
        setProcessing(false);
        setFile(null);
        if (onUploadSuccess) onUploadSuccess(initialPolicy);
      } else if (initialPolicy.status === 'failed') {
        setProcessing(false);
        setError(initialPolicy.error_message || 'Policy processing failed.');
      } else {
        // Start polling real status
        setCurrentStage(initialPolicy.progress_stage || 'extracting_text');
        pollPolicyStatus(initialPolicy.id);
      }
    } catch (err) {
      setProcessing(false);
      setError(err.message || 'Failed to upload policy PDF.');
    }
  };

  const handleLoadSample = async () => {
    if (busy) return;
    setLoadingSample(true);
    setError(null);
    setCurrentStage('uploading');

    try {
      const samplePolicy = await api.loadSamplePolicy();
      if (samplePolicy.status === 'ready') {
        setLoadingSample(false);
        if (onUploadSuccess) onUploadSuccess(samplePolicy);
      } else if (samplePolicy.status === 'failed') {
        setLoadingSample(false);
        setError(samplePolicy.error_message || 'Failed to load sample policy.');
      } else {
        setLoadingSample(false);
        setProcessing(true);
        setCurrentStage(samplePolicy.progress_stage || 'extracting_text');
        pollPolicyStatus(samplePolicy.id);
      }
    } catch (err) {
      setLoadingSample(false);
      setError(err.message || 'Failed to load sample policy.');
    }
  };

  const currentStageIndex = STAGE_ORDER[currentStage] ?? 0;

  /* -------------------------------- Render -------------------------------- */

  return (
    <div className="space-y-4">
      {/* Dropzone / selected file */}
      {!file ? (
        <label
          htmlFor="policy-file-input"
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`relative flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-4 py-8 text-center transition focus-within:ring-4 focus-within:ring-indigo-100 sm:py-10 ${
            isDragging
              ? 'border-indigo-500 bg-indigo-50'
              : 'border-slate-200 bg-slate-50/60 hover:border-indigo-400 hover:bg-indigo-50/40'
          } ${busy ? 'pointer-events-none opacity-60' : ''}`}
        >
          <span
            className={`mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-white shadow-sm ring-1 transition ${
              isDragging ? 'scale-110 ring-indigo-300' : 'ring-slate-200'
            }`}
          >
            <UploadCloud className="h-6 w-6 text-indigo-600" aria-hidden="true" />
          </span>
          <p className="text-sm font-semibold text-slate-800">
            {isDragging ? (
              'Drop your PDF to upload'
            ) : (
              <>
                Drag &amp; drop your policy PDF, or{' '}
                <span className="text-indigo-600 underline-offset-2 hover:underline">
                  browse
                </span>
              </>
            )}
          </p>
          <p className="mt-1 text-xs text-slate-400">
            PDF up to {MAX_FILE_SIZE_MB} MB • Automatic OCR • Vehicle, health, home or travel
          </p>

          <input
            ref={inputRef}
            id="policy-file-input"
            type="file"
            accept=".pdf,application/pdf"
            onChange={handleFileChange}
            className="sr-only"
            disabled={busy}
          />
        </label>
      ) : (
        <div className="flex items-center gap-3 rounded-2xl border border-indigo-200 bg-indigo-50/40 p-3.5">
          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-indigo-100 bg-white text-indigo-600">
            <FileText className="h-5 w-5" aria-hidden="true" />
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold text-slate-900" title={file.name}>
              {file.name}
            </p>
            <p className="text-xs text-slate-500">{formatSize(file.size)}</p>
          </div>
          {!busy && (
            <button
              onClick={removeFile}
              aria-label="Remove selected file"
              className="rounded-lg border border-slate-200 bg-white p-2 text-slate-400 transition hover:border-rose-200 hover:text-rose-600"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
      )}

      {/* Error Banner with Retry */}
      {error && (
        <div
          role="alert"
          className="flex flex-col gap-2 rounded-xl border border-rose-200 bg-rose-50 p-3.5 text-xs text-rose-800"
        >
          <div className="flex items-start gap-2.5">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-600" />
            <span className="flex-1 font-medium">{error}</span>
            <button
              onClick={() => setError(null)}
              aria-label="Dismiss error"
              className="rounded p-0.5 text-rose-500 transition hover:bg-rose-100"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
          {file && (
            <div className="mt-1 flex justify-end">
              <button
                onClick={handleUpload}
                disabled={busy}
                className="inline-flex items-center gap-1.5 rounded-lg bg-rose-600 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-rose-700 disabled:opacity-50"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                Retry Ingestion
              </button>
            </div>
          )}
        </div>
      )}

      {/* Real Ingestion Stages */}
      {processing && (
        <div
          role="status"
          aria-live="polite"
          className="space-y-3 rounded-2xl border border-indigo-100 bg-indigo-50/60 p-4"
        >
          <div className="flex items-center gap-2 text-sm font-semibold text-indigo-900">
            <Loader2 className="h-4 w-4 animate-spin text-indigo-600" />
            Ingesting &amp; indexing policy document…
          </div>
          <ol className="space-y-1.5">
            {STAGES.map((stage, i) => {
              const done = i < currentStageIndex;
              const active = i === currentStageIndex;
              return (
                <li
                  key={stage.key}
                  className={`flex items-center gap-2 text-xs transition ${
                    done
                      ? 'text-emerald-700'
                      : active
                      ? 'font-semibold text-indigo-800'
                      : 'text-slate-400'
                  }`}
                >
                  {done ? (
                    <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-emerald-600" aria-hidden="true" />
                  ) : active ? (
                    <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin text-indigo-600" aria-hidden="true" />
                  ) : (
                    <span className="h-3.5 w-3.5 shrink-0 rounded-full border border-slate-300" />
                  )}
                  {stage.label}
                </li>
              );
            })}
          </ol>
        </div>
      )}

      {loadingSample && (
        <div
          role="status"
          className="flex items-center gap-2 rounded-2xl border border-indigo-100 bg-indigo-50/60 p-4 text-sm font-semibold text-indigo-900"
        >
          <Loader2 className="h-4 w-4 animate-spin text-indigo-600" />
          Ingesting sample vehicle policy…
        </div>
      )}

      {/* Actions */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
        {file && !busy && (
          <button
            onClick={handleUpload}
            className="inline-flex flex-1 items-center justify-center gap-1.5 rounded-xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-700 focus:outline-none focus:ring-4 focus:ring-indigo-200 sm:flex-none"
          >
            <Sparkles className="h-4 w-4" aria-hidden="true" />
            Ingest &amp; index policy
          </button>
        )}

        <button
          onClick={handleLoadSample}
          disabled={busy}
          className="inline-flex items-center justify-center gap-1.5 rounded-xl border border-slate-200 bg-white px-4 py-3 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 disabled:opacity-50 sm:py-2.5"
        >
          <Zap className="h-3.5 w-3.5 text-indigo-600" aria-hidden="true" />
          Load sample policy
        </button>
      </div>
    </div>
  );
}