import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Shield,
  FileCheck2,
  Sparkles,
  ArrowRight,
  CheckCircle2,
  Lock,
  Search,
  FileText,
  Users,
  Layers,
  ChevronDown,
  Quote,
  Zap,
  Eye,
  SlidersHorizontal,
  ChevronRight,
  Star,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function LandingPage() {
  const { isAuthenticated, user } = useAuth();
  const [activeFaq, setActiveFaq] = useState(null);
  const [previewTab, setPreviewTab] = useState('citations');

  const faqs = [
    {
      q: 'How does InsureWise AI eliminate hallucinations?',
      a: 'InsureWise uses deterministic FAISS vector retrieval combined with citation grounding. Every answer links strictly to the verbatim policy clause and exact page number, and will explicitly declare "Not Stated" if the clause is absent.',
    },
    {
      q: 'Is my uploaded policy document kept private?',
      a: 'Yes. With your personal account, your uploaded policies, claim records, and verification audit trails are scoped exclusively to your profile.',
    },
    {
      q: 'Do I need an email verification to get started?',
      a: 'No! You can register instantly with your name and email and start exploring and filing claims in seconds with zero verification barriers.',
    },
    {
      q: 'What types of insurance policies are supported?',
      a: 'We support health, motor/vehicle, life, home, and commercial policies. The system automatically inspects document structures, OCR-indexes scanned PDFs, and extracts personalized claim checklists.',
    },
  ];

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 selection:bg-indigo-500 selection:text-white">
      {/* Glow Ambient Lights */}
      <div className="relative overflow-hidden">
        <div className="pointer-events-none absolute -top-40 left-1/2 h-[500px] w-[800px] -translate-x-1/2 rounded-full bg-gradient-to-tr from-indigo-600/30 via-violet-500/20 to-sky-400/20 blur-[130px]" />
        <div className="pointer-events-none absolute top-96 -left-32 h-96 w-96 rounded-full bg-violet-600/20 blur-[110px]" />
        <div className="pointer-events-none absolute top-[800px] -right-32 h-96 w-96 rounded-full bg-emerald-600/15 blur-[120px]" />

        {/* Hero Section */}
        <div className="relative mx-auto max-w-7xl px-4 pt-20 pb-16 sm:px-6 sm:pt-28 sm:pb-24 lg:px-8">
          <div className="text-center">
            {/* Top Badge */}
            <div className="inline-flex items-center gap-2 rounded-full border border-indigo-500/30 bg-indigo-500/10 px-3.5 py-1.5 text-xs font-semibold text-indigo-300 backdrop-blur-md shadow-inner transition hover:border-indigo-400/50">
              <Sparkles className="h-3.5 w-3.5 text-indigo-400 animate-pulse" />
              <span>Next-Gen Insurance Intelligence &amp; Claim Automation</span>
              <span className="rounded-full bg-indigo-400/20 px-1.5 py-0.5 text-[10px] text-indigo-200">v2.4 Grounded</span>
            </div>

            {/* Main Headline */}
            <h1 className="mt-8 text-4xl font-extrabold tracking-tight sm:text-6xl lg:text-7xl">
              <span className="block text-white">Understand Every Clause.</span>
              <span className="mt-2 block bg-gradient-to-r from-indigo-400 via-violet-300 to-sky-300 bg-clip-text text-transparent">
                Settle Claims in Minutes.
              </span>
            </h1>

            {/* Subtitle */}
            <p className="mx-auto mt-6 max-w-2xl text-base text-slate-300 sm:text-lg lg:text-xl font-normal leading-relaxed">
              No more confusing 40-page policy manuals. InsureWise AI performs vector-grounded
              clause retrieval, automated OCR document verification, and generates ready-to-sign claim checklists with verified page citations.
            </p>

            {/* CTAs */}
            <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
              {isAuthenticated ? (
                <Link
                  to="/dashboard"
                  className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 px-7 py-3.5 text-sm font-bold text-white shadow-lg shadow-indigo-600/30 transition hover:from-indigo-500 hover:to-violet-500 hover:shadow-indigo-600/50 hover:-translate-y-0.5"
                >
                  <span>Go to My Dashboard</span>
                  <ArrowRight className="h-4 w-4" />
                </Link>
              ) : (
                <>
                  <Link
                    to="/signup"
                    className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 px-7 py-3.5 text-sm font-bold text-white shadow-lg shadow-indigo-600/30 transition hover:from-indigo-500 hover:to-violet-500 hover:shadow-indigo-600/50 hover:-translate-y-0.5"
                  >
                    <span>Get Started Free</span>
                    <ArrowRight className="h-4 w-4" />
                  </Link>
                  <Link
                    to="/login"
                    className="inline-flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-800/80 px-6 py-3.5 text-sm font-semibold text-slate-200 backdrop-blur transition hover:border-slate-600 hover:bg-slate-800 hover:text-white"
                  >
                    <span>Log In to Account</span>
                  </Link>
                </>
              )}
              <Link
                to="/about"
                className="inline-flex items-center gap-2 rounded-xl px-5 py-3.5 text-sm font-medium text-slate-400 transition hover:text-indigo-300"
              >
                <span>Read How It Works &rarr;</span>
              </Link>
            </div>

            {/* Trust Bar */}
            <div className="mt-12 flex flex-wrap items-center justify-center gap-x-8 gap-y-3 text-xs text-slate-400">
              <span className="flex items-center gap-1.5">
                <CheckCircle2 className="h-4 w-4 text-emerald-400" /> 100% Policy Clause Grounded
              </span>
              <span className="flex items-center gap-1.5">
                <CheckCircle2 className="h-4 w-4 text-emerald-400" /> Instant OCR &amp; Math Audits
              </span>
              <span className="flex items-center gap-1.5">
                <CheckCircle2 className="h-4 w-4 text-emerald-400" /> Zero Email Verification Required
              </span>
              <span className="flex items-center gap-1.5">
                <Lock className="h-4 w-4 text-indigo-400" /> Isolated User Privacy
              </span>
            </div>
          </div>

          {/* Interactive Feature Live Preview Card */}
          <div className="mt-16 rounded-3xl border border-slate-700/60 bg-slate-800/50 p-4 shadow-2xl backdrop-blur-xl sm:p-6 lg:p-8">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-slate-700/60 pb-4 gap-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-600/20 text-indigo-400 border border-indigo-500/30">
                  <Shield className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white">InsureWise Intelligent Engine Preview</h3>
                  <p className="text-xs text-slate-400">Live demonstration of grounded policy analysis</p>
                </div>
              </div>

              {/* Tabs */}
              <div className="flex items-center gap-1 rounded-xl bg-slate-900/80 p-1 border border-slate-700/60">
                <button
                  onClick={() => setPreviewTab('citations')}
                  className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                    previewTab === 'citations' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
                  }`}
                >
                  Grounded Citations
                </button>
                <button
                  onClick={() => setPreviewTab('checklist')}
                  className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                    previewTab === 'checklist' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
                  }`}
                >
                  Automated Checklist
                </button>
                <button
                  onClick={() => setPreviewTab('human_review')}
                  className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                    previewTab === 'human_review' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
                  }`}
                >
                  Reviewer Queue
                </button>
              </div>
            </div>

            {/* Tab Contents */}
            <div className="pt-6">
              {previewTab === 'citations' && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="rounded-2xl border border-slate-700/60 bg-slate-900/60 p-5 space-y-3">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-400">User Query</span>
                    <p className="text-sm font-medium text-slate-200">
                      "Are flood and water ingress damages covered for my vehicle?"
                    </p>
                    <div className="rounded-xl border border-slate-700/80 bg-slate-800/80 p-4 text-xs space-y-2">
                      <div className="flex items-center gap-2 text-emerald-400 font-semibold">
                        <CheckCircle2 className="h-4 w-4" />
                        <span>Verifiable Coverage Status: Covered (Subject to Deductible)</span>
                      </div>
                      <p className="text-slate-300 leading-relaxed">
                        Under Section 3 (Inundation & Natural Calamities), water ingress to mechanical components is protected when engine protection add-on is active. Deductible is $250.
                      </p>
                    </div>
                  </div>

                  <div className="rounded-2xl border border-indigo-500/30 bg-indigo-950/20 p-5 space-y-3">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-400">Exact Document Citation</span>
                    <div className="rounded-xl border border-indigo-500/20 bg-slate-900/80 p-4 text-xs space-y-2">
                      <div className="flex items-center justify-between text-indigo-300 font-bold">
                        <span>Page 4 • Clause 7.2.1</span>
                        <span className="rounded-full bg-indigo-500/20 px-2 py-0.5 text-[10px]">Verified Quote</span>
                      </div>
                      <p className="italic text-slate-300 font-serif">
                        “Loss or damage directly caused by storm, cyclone, typhoon, tempest, flood, and inundation is covered under Own Damage Schedule B.”
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {previewTab === 'checklist' && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="rounded-2xl border border-slate-700/60 bg-slate-900/60 p-4 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-white">Driving Licence</span>
                      <span className="rounded-full bg-emerald-500/20 px-2 py-0.5 text-[10px] font-bold text-emerald-300">
                        Verified
                      </span>
                    </div>
                    <p className="text-xs text-slate-400">Class & validity matched against accident date.</p>
                  </div>
                  <div className="rounded-2xl border border-slate-700/60 bg-slate-900/60 p-4 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-white">Photos of Damage</span>
                      <span className="rounded-full bg-rose-500/20 px-2 py-0.5 text-[10px] font-bold text-rose-300">
                        Awaiting Upload
                      </span>
                    </div>
                    <p className="text-xs text-slate-400">Strictly requires physical vehicle photo upload.</p>
                  </div>
                  <div className="rounded-2xl border border-slate-700/60 bg-slate-900/60 p-4 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-white">Repair Estimate</span>
                      <span className="rounded-full bg-indigo-500/20 px-2 py-0.5 text-[10px] font-bold text-indigo-300">
                        AI Verified
                      </span>
                    </div>
                    <p className="text-xs text-slate-400">Line items arithmetic cross-checked with 0% discrepancy.</p>
                  </div>
                </div>
              )}

              {previewTab === 'human_review' && (
                <div className="rounded-2xl border border-slate-700/60 bg-slate-900/60 p-5 space-y-4">
                  <div className="flex items-center justify-between border-b border-slate-700 pb-3">
                    <div>
                      <h4 className="text-sm font-bold text-white">Online Reviewer Queue & Settlement Desk</h4>
                      <p className="text-xs text-slate-400">Human adjusters review discrepancies with one-click audit actions.</p>
                    </div>
                    <span className="rounded-full bg-indigo-500/20 px-3 py-1 text-xs font-bold text-indigo-300">
                      Audit Trail Sealed
                    </span>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                    <div className="rounded-xl bg-slate-800/80 p-3 border border-slate-700">
                      <span className="text-slate-400 block">AI Finding</span>
                      <span className="font-semibold text-emerald-400">Names & Policy Numbers Match</span>
                    </div>
                    <div className="rounded-xl bg-slate-800/80 p-3 border border-slate-700">
                      <span className="text-slate-400 block">Arithmetic Check</span>
                      <span className="font-semibold text-emerald-400">Subtotals match Grand Total ($1,420.00)</span>
                    </div>
                    <div className="rounded-xl bg-slate-800/80 p-3 border border-slate-700">
                      <span className="text-slate-400 block">Decision</span>
                      <span className="font-semibold text-indigo-300">Fast-Track Payout Approved</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Feature Pillars */}
      <div className="relative border-t border-slate-800 bg-slate-950 py-20">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto">
            <h2 className="text-xs font-bold uppercase tracking-wider text-indigo-400">Architectural Excellence</h2>
            <p className="mt-3 text-3xl font-extrabold text-white sm:text-4xl">
              Engineered for absolute accuracy and verifiable truth.
            </p>
            <p className="mt-4 text-base text-slate-400">
              Traditional AI models hallucinate coverage terms. InsureWise couples dense FAISS vector embeddings with deterministic rule checking.
            </p>
          </div>

          <div className="mt-16 grid grid-cols-1 gap-8 md:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 transition hover:border-indigo-500/40 hover:-translate-y-1">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-600/20 text-indigo-400 border border-indigo-500/30">
                <Search className="h-6 w-6" />
              </div>
              <h3 className="mt-4 text-lg font-bold text-white">Clause Vector Search</h3>
              <p className="mt-2 text-xs text-slate-400 leading-relaxed">
                FAISS indexing splits multi-page insurance policy documents into semantic clauses for sub-second retrieval.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 transition hover:border-indigo-500/40 hover:-translate-y-1">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-violet-600/20 text-violet-400 border border-violet-500/30">
                <FileCheck2 className="h-6 w-6" />
              </div>
              <h3 className="mt-4 text-lg font-bold text-white">Checklist Intelligence</h3>
              <p className="mt-2 text-xs text-slate-400 leading-relaxed">
                Dynamic generation of required claim documents tailored specifically to health, motor, or property accident scenarios.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 transition hover:border-indigo-500/40 hover:-translate-y-1">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-sky-600/20 text-sky-400 border border-sky-500/30">
                <Zap className="h-6 w-6" />
              </div>
              <h3 className="mt-4 text-lg font-bold text-white">Arithmetic &amp; OCR Check</h3>
              <p className="mt-2 text-xs text-slate-400 leading-relaxed">
                Extracts bill totals, medical codes, vehicle numbers, and audits line items for discrepancies automatically.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 transition hover:border-indigo-500/40 hover:-translate-y-1">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-600/20 text-emerald-400 border border-emerald-500/30">
                <Lock className="h-6 w-6" />
              </div>
              <h3 className="mt-4 text-lg font-bold text-white">User Privacy &amp; Audit Trail</h3>
              <p className="mt-2 text-xs text-slate-400 leading-relaxed">
                Customer files are isolated per account with full audit event histories recording every review and replacement.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* FAQ Accordion */}
      <div className="relative border-t border-slate-800 bg-slate-900 py-20">
        <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <h2 className="text-xs font-bold uppercase tracking-wider text-indigo-400">Frequently Asked Questions</h2>
            <p className="mt-3 text-3xl font-extrabold text-white">Clear answers to common questions.</p>
          </div>

          <div className="mt-12 space-y-4">
            {faqs.map((faq, idx) => {
              const isOpen = activeFaq === idx;
              return (
                <div
                  key={idx}
                  className="rounded-2xl border border-slate-800 bg-slate-800/50 backdrop-blur transition hover:border-slate-700"
                >
                  <button
                    onClick={() => setActiveFaq(isOpen ? null : idx)}
                    className="flex w-full items-center justify-between p-5 text-left text-sm font-bold text-white"
                  >
                    <span>{faq.q}</span>
                    <ChevronDown
                      className={`h-4 w-4 text-slate-400 transition-transform duration-200 ${
                        isOpen ? 'rotate-180 text-indigo-400' : ''
                      }`}
                    />
                  </button>
                  {isOpen && (
                    <div className="border-t border-slate-800/80 px-5 pt-3 pb-5 text-xs text-slate-300 leading-relaxed">
                      {faq.a}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Bottom CTA Banner */}
      <div className="relative overflow-hidden border-t border-slate-800 bg-gradient-to-b from-slate-900 to-indigo-950 py-20">
        <div className="mx-auto max-w-5xl px-4 text-center sm:px-6 lg:px-8">
          <h2 className="text-3xl font-extrabold text-white sm:text-4xl">
            Start Processing Your Claims with Total Confidence
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-sm text-indigo-200">
            Create an account in 10 seconds without verification. Upload your policy PDF and let AI verify your claim preparation instantly.
          </p>
          <div className="mt-8 flex justify-center gap-4">
            <Link
              to={isAuthenticated ? "/dashboard" : "/signup"}
              className="inline-flex items-center gap-2 rounded-xl bg-white px-7 py-3 text-sm font-bold text-indigo-950 shadow-xl transition hover:bg-slate-100 hover:scale-105"
            >
              <span>{isAuthenticated ? "Go to Dashboard" : "Create Free Account"}</span>
              <ArrowRight className="h-4 w-4 text-indigo-600" />
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
