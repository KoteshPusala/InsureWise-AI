import React from 'react';
import { Link } from 'react-router-dom';
import {
  Shield,
  FileCheck2,
  Cpu,
  Lock,
  ArrowRight,
  CheckCircle2,
  Users,
  Target,
  Sparkles,
  BookOpen,
  Mail,
  Send,
} from 'lucide-react';

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-slate-900 text-slate-100">
      {/* Top Ambient Glow */}
      <div className="relative overflow-hidden py-20 sm:py-28">
        <div className="pointer-events-none absolute -top-40 left-1/2 h-[450px] w-[700px] -translate-x-1/2 rounded-full bg-gradient-to-tr from-indigo-600/25 via-violet-500/20 to-sky-400/15 blur-[120px]" />

        <div className="relative mx-auto max-w-5xl px-4 sm:px-6 lg:px-8 text-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-indigo-500/30 bg-indigo-500/10 px-3 py-1 text-xs font-semibold text-indigo-300">
            <Sparkles className="h-3.5 w-3.5 text-indigo-400" />
            <span>Our Mission &amp; Core Architecture</span>
          </div>
          <h1 className="mt-6 text-4xl font-extrabold tracking-tight text-white sm:text-5xl lg:text-6xl">
            Making Insurance Claims <span className="bg-gradient-to-r from-indigo-400 via-violet-300 to-sky-300 bg-clip-text text-transparent">Verifiable, Transparent &amp; Instant</span>
          </h1>
          <p className="mx-auto mt-6 max-w-3xl text-base text-slate-300 sm:text-lg leading-relaxed">
            Insurance policies are written in dense legal vernacular designed for underwriter compliance, not customer clarity. InsureWise AI was built to bridge this divide through grounded vector intelligence.
          </p>
        </div>
      </div>

      {/* Philosophy & Pillars */}
      <div className="border-t border-slate-800 bg-slate-950 py-16">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 space-y-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-600/20 text-indigo-400 border border-indigo-500/30">
                <Target className="h-6 w-6" />
              </div>
              <h3 className="text-lg font-bold text-white">Zero Guesswork Guarantee</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                We never guess coverage limits or make speculative claims. Every AI answer links to an exact page number and verbatim excerpt from your uploaded policy PDF.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 space-y-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-violet-600/20 text-violet-400 border border-violet-500/30">
                <Lock className="h-6 w-6" />
              </div>
              <h3 className="text-lg font-bold text-white">Sovereign Data Privacy</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Your medical receipts, vehicle repair estimates, and policy files belong strictly to you. Each account is isolated with zero cross-tenant contamination.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 space-y-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-sky-600/20 text-sky-400 border border-sky-500/30">
                <Users className="h-6 w-6" />
              </div>
              <h3 className="text-lg font-bold text-white">Human-in-the-Loop Review</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                AI accelerates document intake, arithmetic audits, and OCR extraction, while human claim officers retain full supervisory control through an interactive review queue.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Technical Architecture */}
      <div className="border-t border-slate-800 bg-slate-900 py-20">
        <div className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-2xl mx-auto">
            <h2 className="text-xs font-bold uppercase tracking-wider text-indigo-400">The Technology Stack</h2>
            <p className="mt-3 text-3xl font-extrabold text-white">Modern Engineering Built for Speed</p>
          </div>

          <div className="mt-12 rounded-3xl border border-slate-800 bg-slate-800/40 p-6 sm:p-8 backdrop-blur space-y-6">
            <div className="flex items-start gap-4">
              <div className="rounded-xl bg-indigo-600/20 p-2 text-indigo-400 border border-indigo-500/30">
                <BookOpen className="h-5 w-5" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-white">PyMuPDF &amp; Tesseract OCR Pipeline</h4>
                <p className="text-xs text-slate-300 mt-1 leading-relaxed">
                  Scanned hospital bills and mobile photos of vehicle damage are automatically processed with multi-page OCR and rotated orientations to extract legible text and dates.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-4">
              <div className="rounded-xl bg-violet-600/20 p-2 text-violet-400 border border-violet-500/30">
                <Cpu className="h-5 w-5" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-white">FAISS Dense Vector Indexing</h4>
                <p className="text-xs text-slate-300 mt-1 leading-relaxed">
                  Fast sub-millisecond semantic retrieval indexed locally. Policies are broken down into clause-aligned chunks preserving header hierarchies and table relationships.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-4">
              <div className="rounded-xl bg-emerald-600/20 p-2 text-emerald-400 border border-emerald-500/30">
                <FileCheck2 className="h-5 w-5" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-white">Deterministic Arithmetic Discrepancy Auditing</h4>
                <p className="text-xs text-slate-300 mt-1 leading-relaxed">
                  Line items, taxes, deductibles, and repair invoices are cross-checked mathematically using strict rules rather than probabilistic LLM approximations.
                </p>
              </div>
            </div>
          </div>

          {/* Call to action */}
          <div className="mt-14 text-center">
            <Link
              to="/signup"
              className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 px-7 py-3.5 text-sm font-bold text-white shadow-lg shadow-indigo-600/30 transition hover:from-indigo-500 hover:to-violet-500"
            >
              <span>Create an Account in Seconds</span>
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
