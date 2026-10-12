import React, { useState, useEffect, useRef } from 'react';
import {
  Send,
  Bot,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  HelpCircle,
  XCircle,
  Trash2,
  Quote,
  ShieldCheck,
  FileText,
  Loader2,
  X,
  AlertCircle,
  CornerDownRight,
  Clock,
} from 'lucide-react';
import { api } from '../api/client';

/* ------------------------------ Constants ------------------------------ */

const STARTER_QUESTIONS = [
  'What is covered under this policy?',
  'What are the key exclusions and non-covered scenarios?',
  'What is the notification time limit to report an incident?',
  'What documents are required to file a claim?',
  'What is the deductible or excess amount?',
];

const VERDICTS = {
  covered: {
    label: 'Covered',
    Icon: CheckCircle2,
    cls: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  },
  excluded: {
    label: 'Excluded',
    Icon: XCircle,
    cls: 'bg-rose-50 text-rose-700 ring-rose-200',
  },
  conditional: {
    label: 'Conditional',
    Icon: AlertTriangle,
    cls: 'bg-amber-50 text-amber-700 ring-amber-200',
  },
  not_stated: {
    label: 'Not stated',
    Icon: HelpCircle,
    cls: 'bg-slate-100 text-slate-700 ring-slate-200',
  },
};

/* --------------------------- Sub-components --------------------------- */

function VerdictBadge({ verdict }) {
  const meta = VERDICTS[verdict];
  if (!meta) return null;
  const { Icon } = meta;
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold ring-1 ring-inset ${meta.cls}`}
    >
      <Icon className="h-3 w-3" aria-hidden="true" />
      {meta.label}
    </span>
  );
}

function TypingIndicator() {
  return (
    <div className="flex items-start gap-2.5" role="status" aria-label="Assistant is thinking">
      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 ring-1 ring-indigo-100">
        <Bot className="h-4 w-4" aria-hidden="true" />
      </span>
      <div className="flex items-center gap-2 rounded-2xl rounded-tl-md border border-slate-200 bg-white px-4 py-3 text-xs text-slate-500 shadow-sm">
        <span className="flex gap-1" aria-hidden="true">
          <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-indigo-400 [animation-delay:-0.3s]" />
          <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-indigo-400 [animation-delay:-0.15s]" />
          <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-indigo-400" />
        </span>
        Searching policy clauses…
      </div>
    </div>
  );
}

function MessageBubble({ msg, isLast, onCite, onFollowUp, disabled }) {
  const isUser = msg.role === 'user';
  const isError = msg.verdict === 'error';
  const citations = msg.citations?.length ? msg.citations : (msg.sources?.length ? msg.sources : []);

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[88%] rounded-2xl rounded-tr-md bg-indigo-600 px-4 py-3 text-white shadow-sm sm:max-w-[80%]">
          <p className="whitespace-pre-wrap text-sm leading-relaxed">{msg.content}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-2.5">
      <span
        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-xl ring-1 ${
          isError
            ? 'bg-rose-50 text-rose-600 ring-rose-100'
            : 'bg-indigo-50 text-indigo-600 ring-indigo-100'
        }`}
      >
        {isError ? (
          <AlertCircle className="h-4 w-4" aria-hidden="true" />
        ) : (
          <Bot className="h-4 w-4" aria-hidden="true" />
        )}
      </span>

      <div className="min-w-0 max-w-[88%] space-y-2.5 sm:max-w-[80%]">
        <div
          className={`rounded-2xl rounded-tl-md border px-4 py-3 shadow-sm ${
            isError
              ? 'border-rose-200 bg-rose-50 text-rose-900'
              : 'border-slate-200 bg-white text-slate-900'
          }`}
        >
          {msg.verdict && !isError && (
            <div className="mb-2">
              <VerdictBadge verdict={msg.verdict} />
            </div>
          )}

          <p className="whitespace-pre-wrap break-words text-sm leading-relaxed">
            {msg.content}
          </p>

          {msg.supported === false && !isError && (
            <p className="mt-2 flex items-start gap-1.5 rounded-lg bg-amber-50 px-2.5 py-1.5 text-[11px] text-amber-800">
              <AlertTriangle className="mt-px h-3 w-3 shrink-0" aria-hidden="true" />
              This answer may not be fully supported by the policy text. Please verify with the cited pages.
            </p>
          )}

          {citations.length > 0 && (
            <div className="mt-3 border-t border-slate-100 pt-2.5">
              <div className="mb-1.5 flex items-center gap-1.5 text-[11px] font-semibold text-indigo-700">
                <ShieldCheck className="h-3.5 w-3.5 text-indigo-600" aria-hidden="true" />
                Verified citations
              </div>
              <div className="flex flex-wrap gap-1.5">
                {citations.map((cit, i) => (
                  <button
                    key={i}
                    onClick={() => onCite(cit)}
                    className="inline-flex items-center gap-1 rounded-full border border-indigo-200 bg-indigo-50 px-2.5 py-1 text-[11px] font-semibold text-indigo-700 transition hover:bg-indigo-100 focus:outline-none focus-visible:ring-4 focus-visible:ring-indigo-100"
                  >
                    <Quote className="h-3 w-3" aria-hidden="true" />
                    Page {cit.page}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Follow-up suggestions only under the latest answer */}
        {isLast && msg.follow_up_suggestions?.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {msg.follow_up_suggestions.map((s, i) => (
              <button
                key={i}
                onClick={() => onFollowUp(s)}
                disabled={disabled}
                className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-left text-[11px] font-medium text-slate-600 shadow-sm transition hover:border-indigo-300 hover:text-indigo-700 disabled:opacity-50"
              >
                <CornerDownRight className="h-3 w-3 shrink-0 text-slate-400" aria-hidden="true" />
                {s}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/* ------------------------------ Component ------------------------------ */

export default function PolicyChat({ policyId, policyType, policyStatus = 'ready' }) {
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [selectedCitation, setSelectedCitation] = useState(null);
  const [confirmingClear, setConfirmingClear] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [error, setError] = useState(null);

  const scrollRef = useRef(null);
  const inputRef = useRef(null);
  const activeAbortRef = useRef(null);
  const currentPolicyIdRef = useRef(policyId);
  const sendingRef = useRef(false);

  const isReady = policyStatus === 'ready';

  // Reset and reload whenever the policy changes; cancel in-flight queries.
  useEffect(() => {
    currentPolicyIdRef.current = policyId;
    if (activeAbortRef.current) {
      activeAbortRef.current.abort();
      activeAbortRef.current = null;
    }
    setMessages([]);
    setSelectedCitation(null);
    setConfirmingClear(false);
    setError(null);
    setLoading(false);

    if (policyId) {
      loadChatHistory(policyId);
    }

    return () => {
      if (activeAbortRef.current) {
        activeAbortRef.current.abort();
        activeAbortRef.current = null;
      }
    };
  }, [policyId]);

  // Scroll only the message pane.
  useEffect(() => {
    const el = scrollRef.current;
    if (el && (messages.length > 0 || loading)) {
      el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
    }
  }, [messages, loading]);

  // Auto-grow textarea.
  useEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 128)}px`;
  }, [question]);

  const loadChatHistory = async (targetPolicyId) => {
    const controller = new AbortController();
    activeAbortRef.current = controller;
    try {
      const res = await api.getChatHistory(targetPolicyId, { signal: controller.signal });
      if (currentPolicyIdRef.current !== targetPolicyId) return;

      const rawMessages = Array.isArray(res) ? res : res?.messages || [];
      const normalized = rawMessages.map((m) => ({
        ...m,
        citations: m.citations || m.sources || [],
      }));
      setMessages(normalized);
    } catch (err) {
      if (err.isAbort) return;
      console.error('Failed to load chat history:', err);
    } finally {
      if (activeAbortRef.current === controller) {
        activeAbortRef.current = null;
      }
    }
  };

  const handleSend = async (questionText = question) => {
    const q = (questionText || '').trim();
    if (!q || loading || sendingRef.current || !isReady) return;

    sendingRef.current = true;
    const targetPolicyId = policyId;

    setMessages((prev) => [
      ...prev,
      { role: 'user', content: q, created_at: new Date().toISOString() },
    ]);
    setQuestion('');
    setLoading(true);
    setError(null);

    const controller = new AbortController();
    activeAbortRef.current = controller;

    try {
      const response = await api.sendMessage(targetPolicyId, q, [], { signal: controller.signal });
      if (currentPolicyIdRef.current !== targetPolicyId) return;

      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: response.answer,
          verdict: response.verdict,
          supported: response.supported,
          citations: response.citations || response.sources || [],
          follow_up_suggestions: response.follow_up_suggestions || [],
          created_at: new Date().toISOString(),
        },
      ]);
    } catch (err) {
      if (err.isAbort) return;
      if (currentPolicyIdRef.current !== targetPolicyId) return;

      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Sorry, an error occurred while processing your question: ' + err.message,
          verdict: 'error',
          citations: [],
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      sendingRef.current = false;
      setLoading(false);
      if (activeAbortRef.current === controller) {
        activeAbortRef.current = null;
      }
      inputRef.current?.focus();
    }
  };

  const handleClearHistory = async () => {
    setClearing(true);
    setError(null);
    try {
      await api.clearChatHistory(policyId);
      setMessages([]);
      setSelectedCitation(null);
      setConfirmingClear(false);
    } catch (err) {
      setError('Failed to clear history: ' + err.message);
    } finally {
      setClearing(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      handleSend();
    }
  };

  const lastIndex = messages.length - 1;

  return (
    <section
      aria-label="Policy AI assistant"
      className="flex h-[75vh] min-h-[520px] max-h-[760px] flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm"
    >
      {/* Header */}
      <header className="flex items-center justify-between gap-3 border-b border-slate-200 bg-white px-4 py-3 sm:px-5">
        <div className="flex min-w-0 items-center gap-3">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-indigo-700 text-white shadow-sm">
            <Bot className="h-4.5 w-4.5" aria-hidden="true" />
          </span>
          <div className="min-w-0">
            <h3 className="truncate text-sm font-bold text-slate-900">
              Policy AI assistant
            </h3>
            <p className="truncate text-[11px] text-slate-500">
              {policyType ? (
                <span className="capitalize">{policyType} policy • </span>
              ) : null}
              Answers cite verified policy pages
            </p>
          </div>
        </div>

        {messages.length > 0 &&
          (confirmingClear ? (
            <div className="flex shrink-0 items-center gap-1.5">
              <span className="hidden text-[11px] text-slate-500 sm:inline">
                Clear conversation?
              </span>
              <button
                onClick={handleClearHistory}
                disabled={clearing}
                className="inline-flex items-center gap-1 rounded-lg bg-rose-600 px-2.5 py-1.5 text-[11px] font-semibold text-white transition hover:bg-rose-700 disabled:opacity-60"
              >
                {clearing && <Loader2 className="h-3 w-3 animate-spin" />}
                Clear
              </button>
              <button
                onClick={() => setConfirmingClear(false)}
                disabled={clearing}
                className="rounded-lg border border-slate-200 px-2.5 py-1.5 text-[11px] font-semibold text-slate-600 transition hover:bg-slate-50"
              >
                Cancel
              </button>
            </div>
          ) : (
            <button
              onClick={() => setConfirmingClear(true)}
              className="inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-slate-200 px-2.5 py-1.5 text-[11px] font-semibold text-slate-500 transition hover:bg-slate-50 hover:text-slate-800"
            >
              <Trash2 className="h-3 w-3" aria-hidden="true" />
              <span className="hidden sm:inline">Clear chat</span>
            </button>
          ))}
      </header>

      {/* Non-ready policy banner */}
      {!isReady && (
        <div
          role="status"
          className="flex items-center gap-2 border-b border-amber-200 bg-amber-50 px-4 py-2.5 text-xs text-amber-900"
        >
          <Clock className="h-4 w-4 shrink-0 text-amber-600 animate-spin" />
          <span>
            This policy is currently in <strong className="capitalize">{policyStatus}</strong> status. AI chat will unlock automatically once indexing finishes.
          </span>
        </div>
      )}

      {error && (
        <div
          role="alert"
          className="flex items-start gap-2 border-b border-rose-200 bg-rose-50 px-4 py-2 text-xs text-rose-800"
        >
          <AlertCircle className="mt-px h-3.5 w-3.5 shrink-0 text-rose-600" />
          <span className="flex-1">{error}</span>
          <button
            onClick={() => setError(null)}
            aria-label="Dismiss error"
            className="rounded p-0.5 text-rose-500 hover:bg-rose-100"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {/* Messages */}
      <div
        ref={scrollRef}
        role="log"
        aria-live="polite"
        className="flex-1 space-y-4 overflow-y-auto bg-slate-50/60 px-4 py-5 sm:px-5"
      >
        {messages.length === 0 && !loading && (
          <div className="mx-auto flex max-w-lg flex-col items-center py-6 text-center">
            <span className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600 ring-1 ring-indigo-100">
              <Sparkles className="h-6 w-6" aria-hidden="true" />
            </span>
            <h4 className="text-base font-bold text-slate-900">
              Ask anything about this policy
            </h4>
            <p className="mt-1 max-w-xs text-xs text-slate-500">
              Answers cite exact policy pages and clearly separate covered from excluded terms.
            </p>

            <div className="mt-5 grid w-full grid-cols-1 gap-2 sm:grid-cols-2">
              {STARTER_QUESTIONS.map((sq) => (
                <button
                  key={sq}
                  onClick={() => handleSend(sq)}
                  disabled={!isReady}
                  className="rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-left text-xs font-medium text-slate-700 shadow-sm transition hover:-translate-y-0.5 hover:border-indigo-300 hover:text-indigo-700 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {sq}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, idx) => (
          <MessageBubble
            key={idx}
            msg={msg}
            isLast={idx === lastIndex && !loading}
            onCite={setSelectedCitation}
            onFollowUp={handleSend}
            disabled={loading || !isReady}
          />
        ))}

        {loading && <TypingIndicator />}
      </div>

      {/* Citation inspector */}
      {selectedCitation && (
        <div className="relative border-t border-indigo-200 bg-indigo-50/90 px-4 py-3 text-xs sm:px-5">
          <button
            onClick={() => setSelectedCitation(null)}
            aria-label="Close excerpt"
            className="absolute right-3 top-3 rounded p-1 text-slate-400 transition hover:bg-white hover:text-slate-700"
          >
            <X className="h-3.5 w-3.5" />
          </button>
          <div className="mb-1.5 flex items-center gap-1.5 pr-6 font-bold text-indigo-900">
            <FileText className="h-3.5 w-3.5 text-indigo-600" aria-hidden="true" />
            Policy excerpt — page {selectedCitation.page}
          </div>
          {selectedCitation.quote ? (
            <blockquote className="max-h-28 overflow-y-auto rounded-lg border border-indigo-100 bg-white p-2.5 font-mono text-[11px] italic leading-relaxed text-slate-700">
              “{selectedCitation.quote}”
            </blockquote>
          ) : (
            <p className="text-slate-500">No excerpt available for this citation.</p>
          )}
        </div>
      )}

      {/* Input */}
      <div className="border-t border-slate-200 bg-white p-3 sm:p-4">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex items-end gap-2"
        >
          <label htmlFor="policy-question" className="sr-only">
            Ask a question about this policy
          </label>
          <textarea
            id="policy-question"
            ref={inputRef}
            rows={1}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={isReady ? "Ask about coverage, exclusions, deductible…" : `Policy is currently ${policyStatus}. Chat disabled.`}
            disabled={loading || !isReady}
            className="max-h-32 min-h-[44px] flex-1 resize-none rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-2.5 text-sm text-slate-900 placeholder-slate-400 transition focus:border-indigo-500 focus:bg-white focus:outline-none focus:ring-4 focus:ring-indigo-100 disabled:opacity-60"
          />
          <button
            type="submit"
            disabled={loading || !question.trim() || !isReady}
            aria-label="Send question"
            className="inline-flex h-11 shrink-0 items-center justify-center gap-1.5 rounded-xl bg-indigo-600 px-4 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-700 focus:outline-none focus:ring-4 focus:ring-indigo-200 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
            <span className="hidden sm:inline">Ask</span>
          </button>
        </form>
        <p className="mt-1.5 hidden px-1 text-[10px] text-slate-400 sm:block">
          Press Enter to send • Shift+Enter for a new line
        </p>
      </div>
    </section>
  );
}