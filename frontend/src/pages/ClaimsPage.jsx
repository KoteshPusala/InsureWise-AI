import React, { useState, useEffect, useRef, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  ClipboardCheck,
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
  Download,
  FileUp,
  ArrowRight,
  AlertCircle,
  ShieldCheck,
  Loader2,
  X,
  RefreshCw,
  Calendar,
  FileText,
  Layers,
  Eye,
  Trash2,
  UserCheck,
  Clock,
  MapPin,
  Building,
  Info,
  FileSpreadsheet,
} from 'lucide-react';
import { api } from '../api/client';

/* ----------------------------- Constants & Helpers ----------------------------- */

const INCIDENT_CATEGORIES = [
  { value: 'medical_health', label: 'Medical / Health (Hospitalization)' },
  { value: 'vehicle_accident', label: 'Vehicle Accident / Damage' },
  { value: 'theft', label: 'Theft / Burglary' },
  { value: 'fire_property_damage', label: 'Property / Fire Damage' },
];

const formatCategory = (t = '') => t.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

const formatBytes = (bytes = 0) => {
  if (!bytes || bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
};

const normalizeList = (data, key) => (Array.isArray(data) ? data : data?.[key] || []);

const STATUS_META = {
  reviewed: {
    label: 'Human Verified & Accepted',
    Icon: CheckCircle2,
    badge: 'bg-emerald-100 text-emerald-800 ring-emerald-300',
    bar: 'bg-emerald-600',
  },
  correction_required: {
    label: 'Correction Required',
    Icon: AlertTriangle,
    badge: 'bg-amber-100 text-amber-800 ring-amber-300',
    bar: 'bg-amber-500',
  },
  human_rejected: {
    label: 'Human Rejected',
    Icon: AlertCircle,
    badge: 'bg-rose-100 text-rose-800 ring-rose-300',
    bar: 'bg-rose-600',
  },
  ready_for_review: {
    label: 'AI Verified (Pending Review)',
    Icon: UserCheck,
    badge: 'bg-indigo-50 text-indigo-700 ring-indigo-200',
    bar: 'bg-indigo-500',
  },
  present: {
    label: 'Fact Verified',
    Icon: CheckCircle2,
    badge: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
    bar: 'bg-emerald-500',
  },
  needs_attention: {
    label: 'Needs Attention (Issue Found)',
    Icon: AlertTriangle,
    badge: 'bg-amber-50 text-amber-800 ring-amber-300',
    bar: 'bg-amber-500',
  },
  unclear: {
    label: 'Needs Clarification',
    Icon: AlertTriangle,
    badge: 'bg-amber-50 text-amber-700 ring-amber-200',
    bar: 'bg-amber-400',
  },
  processing: {
    label: 'AI Verifying…',
    Icon: Loader2,
    badge: 'bg-sky-50 text-sky-700 ring-sky-200',
    bar: 'bg-sky-500',
  },
  awaiting_upload: {
    label: 'Awaiting Upload',
    Icon: HelpCircle,
    badge: 'bg-rose-50 text-rose-700 ring-rose-200',
    bar: 'bg-rose-500',
  },
  missing: {
    label: 'Awaiting Upload',
    Icon: HelpCircle,
    badge: 'bg-rose-50 text-rose-700 ring-rose-200',
    bar: 'bg-rose-500',
  },
  not_stated: {
    label: 'Not Stated in Policy',
    Icon: Info,
    badge: 'bg-slate-100 text-slate-600 ring-slate-200',
    bar: 'bg-slate-400',
  },
  processing_failed: {
    label: 'Processing Failed',
    Icon: AlertCircle,
    badge: 'bg-red-100 text-red-800 ring-red-300',
    bar: 'bg-red-500',
  },
};

const normalizeStatus = (s) => {
  if (s === 'reviewed' || s === 'human_verified' || s === 'accepted') return 'reviewed';
  if (s === 'correction_required' || s === 'info_required') return 'correction_required';
  if (s === 'human_rejected' || s === 'mismatch_confirmed') return 'human_rejected';
  if (s === 'ready_for_review') return 'ready_for_review';
  if (s === 'present' || s === 'matched') return 'present';
  if (s === 'needs_attention') return 'needs_attention';
  if (s === 'unclear') return 'unclear';
  if (s === 'processing' || s === 'uploading' || s === 'ai_processing') return 'processing';
  if (s === 'processing_failed' || s === 'ai_failed') return 'processing_failed';
  if (s === 'not_stated' || s === 'not_applicable') return 'not_stated';
  return 'awaiting_upload';
};

/* --------------------------- Visual UI Primitives --------------------------- */

function StatusBadge({ status }) {
  const norm = normalizeStatus(status);
  const meta = STATUS_META[norm] || STATUS_META.awaiting_upload;
  const { Icon } = meta;
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-semibold ring-1 ring-inset ${meta.badge}`}
    >
      <Icon className={`h-3 w-3 ${norm === 'processing' ? 'animate-spin' : ''}`} aria-hidden="true" />
      {meta.label}
    </span>
  );
}

function ReadinessRing({ value = 0, size = 100 }) {
  const stroke = 9;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(100, Number(value) || 0));
  const color = pct >= 80 ? '#10b981' : pct >= 50 ? '#f59e0b' : '#ef4444';

  return (
    <div className="relative inline-flex items-center justify-center group" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} stroke="#e2e8f0" strokeWidth={stroke} fill="transparent" />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          stroke={color}
          strokeWidth={stroke}
          strokeDasharray={c}
          strokeDashoffset={c - (pct / 100) * c}
          strokeLinecap="round"
          fill="transparent"
          className="transition-all duration-700 ease-out"
        />
      </svg>
      <div className="absolute flex flex-col items-center justify-center text-center">
        <span className="text-xl font-black text-slate-900">{pct}%</span>
        <span className="text-[9px] font-bold uppercase tracking-wider text-slate-500">Readiness</span>
      </div>
    </div>
  );
}

function Stepper({ steps, current }) {
  return (
    <nav aria-label="Progress" className="w-full">
      <ol className="flex items-center justify-between gap-2 border-b border-slate-200/80 bg-white/70 px-4 py-3 rounded-2xl shadow-sm backdrop-blur">
        {steps.map((s, idx) => {
          const isDone = s.num < current;
          const isCurr = s.num === current;
          return (
            <li key={s.num} className="flex flex-1 items-center gap-2">
              <span
                className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold transition-all ${
                  isDone
                    ? 'bg-emerald-600 text-white'
                    : isCurr
                    ? 'bg-indigo-600 text-white ring-4 ring-indigo-100'
                    : 'bg-slate-100 text-slate-500'
                }`}
              >
                {isDone ? <CheckCircle2 className="h-4 w-4" /> : s.num}
              </span>
              <span
                className={`hidden text-xs font-semibold sm:inline ${
                  isCurr ? 'text-indigo-900 font-bold' : isDone ? 'text-slate-800' : 'text-slate-400'
                }`}
              >
                {s.label}
              </span>
              {idx < steps.length - 1 && <span className="h-0.5 flex-1 bg-slate-200 mx-1 hidden md:block" />}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

function Card({ title, subtitle, icon: Icon, action, children, className = '' }) {
  return (
    <section className={`rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm sm:p-6 ${className}`}>
      {(title || action) && (
        <div className="mb-4 flex items-start justify-between gap-4">
          <div className="flex items-center gap-2.5">
            {Icon && (
              <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 ring-1 ring-indigo-100">
                <Icon className="h-4 w-4" />
              </span>
            )}
            <div>
              <h3 className="text-sm font-bold text-slate-900">{title}</h3>
              {subtitle && <p className="text-xs text-slate-500">{subtitle}</p>}
            </div>
          </div>
          {action}
        </div>
      )}
      {children}
    </section>
  );
}

/* ------------------------------- Main Component ------------------------------- */

export default function ClaimsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const urlClaimId = searchParams.get('claimId');
  const urlPolicyId = searchParams.get('policyId');

  // Application Data States
  const [policies, setPolicies] = useState([]);
  const [claimsList, setClaimsList] = useState([]);
  const [selectedPolicyId, setSelectedPolicyId] = useState('');
  const [activeClaim, setActiveClaim] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [claimDocuments, setClaimDocuments] = useState([]);
  const [reviewQueue, setReviewQueue] = useState([]);
  const [pvEligibility, setPvEligibility] = useState(null);
  const [physicalVerification, setPhysicalVerification] = useState(null);
  const [auditLogs, setAuditLogs] = useState([]);

  // Role simulation state ('reviewer' or 'claimant')
  const [userRole, setUserRole] = useState('reviewer');

  // UI Interactive States
  const [showForm, setShowForm] = useState(true);
  const [filter, setFilter] = useState('all');
  const [activeTab, setActiveTab] = useState('checklist'); // 'checklist' | 'review_queue' | 'physical_verification' | 'audit_trail'
  const [expandedDocItem, setExpandedDocItem] = useState(null);
  const [reviewModalDoc, setReviewModalDoc] = useState(null);
  const [reassignModalDoc, setReassignModalDoc] = useState(null);
  const [scheduleModalOpen, setScheduleModalOpen] = useState(false);
  const [outcomeModalOpen, setOutcomeModalOpen] = useState(false);

  // Review Form States
  const [reviewerName, setReviewerName] = useState('Senior Claims Analyst');
  const [reviewOutcome, setReviewOutcome] = useState('accepted');
  const [reviewerNotes, setReviewerNotes] = useState('');
  const [submittingReview, setSubmittingReview] = useState(false);

  // Physical Verification Schedule Form States
  const [schedDate, setSchedDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() + 3);
    return d.toISOString().split('T')[0];
  });
  const [schedLocation, setSchedLocation] = useState('Authorized Regional Inspection Center / Claimant Premises');
  const [schedInspector, setSchedInspector] = useState('Field Officer R. Sharma');
  const [schedInstructions, setSchedInstructions] = useState('Please bring original vehicle documents and valid photo ID for on-site physical stamp verification.');
  const [submittingSchedule, setSubmittingSchedule] = useState(false);

  // Physical Verification Outcome Form States
  const [outcomeStatus, setOutcomeStatus] = useState('completed');
  const [outcomeNotes, setOutcomeNotes] = useState('');
  const [submittingOutcome, setSubmittingOutcome] = useState(false);

  // Form Fields
  const [claimTitle, setClaimTitle] = useState('');
  const [incidentCategory, setIncidentCategory] = useState('medical_health');
  const [incidentDate, setIncidentDate] = useState(() => new Date().toISOString().split('T')[0]);
  const [incidentDescription, setIncidentDescription] = useState('');
  const [expenses, setExpenses] = useState('');
  // Adaptive Health Fields
  const [hospitalName, setHospitalName] = useState('');
  const [admissionDate, setAdmissionDate] = useState('');
  const [dischargeDate, setDischargeDate] = useState('');
  const [diagnosis, setDiagnosis] = useState('');
  // Adaptive Motor Fields
  const [vehicleReg, setVehicleReg] = useState('');
  const [driverName, setDriverName] = useState('');
  const [licenceNo, setLicenceNo] = useState('');
  const [accidentLocation, setAccidentLocation] = useState('');
  const [thirdPartyInvolved, setThirdPartyInvolved] = useState(false);

  // Action Loading States
  const [creating, setCreating] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [uploadingItemId, setUploadingItemId] = useState(null);
  const [generatingReport, setGeneratingReport] = useState(false);
  const [requestingPv, setRequestingPv] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  const activeClaimIdRef = useRef(null);

  /* ---------------------------- Data Loading ---------------------------- */

  const loadInitialData = async () => {
    try {
      const polData = await api.getPolicies();
      const polList = normalizeList(polData, 'policies');
      setPolicies(polList);

      if (urlPolicyId) {
        setSelectedPolicyId(urlPolicyId);
      } else if (polList.length > 0) {
        setSelectedPolicyId((prev) => prev || polList[0].id);
      }

      const claimData = await api.getClaims();
      const cList = normalizeList(claimData, 'claims');
      setClaimsList(cList);

      if (urlClaimId) {
        const match = cList.find((c) => c.id === urlClaimId);
        if (match) {
          selectClaim(match);
        } else {
          try {
            const single = await api.getClaim(urlClaimId);
            selectClaim(single);
          } catch {
            startNewClaim();
          }
        }
      }
    } catch (err) {
      console.error('Error loading initial claims data:', err);
      setError('Could not load policies and claims. Please check backend.');
    }
  };

  useEffect(() => {
    loadInitialData();
  }, []);

  const selectClaim = async (claim) => {
    setActiveClaim(claim);
    activeClaimIdRef.current = claim.id;
    setShowForm(false);
    setError(null);
    setFilter('all');

    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.set('claimId', claim.id);
      return next;
    });

    await refreshClaimData(claim.id);
  };

  const refreshClaimData = async (claimId) => {
    const targetId = claimId || activeClaim?.id;
    if (!targetId) return;

    setAnalyzing(true);
    try {
      const updatedClaim = await api.getClaim(targetId);
      setActiveClaim(updatedClaim);

      const docsRes = await api.getClaimDocuments(targetId);
      setClaimDocuments(docsRes.documents || []);

      const queueRes = await api.getReviewQueue(targetId);
      setReviewQueue(queueRes.queue || []);

      const analysisRes = await api.analyzeClaim(targetId);
      setAnalysis(analysisRes);

      try {
        const eligRes = await api.getPhysicalVerificationEligibility(targetId);
        setPvEligibility(eligRes);
      } catch {
        setPvEligibility(null);
      }

      try {
        const pvRes = await api.getPhysicalVerification(targetId);
        setPhysicalVerification(pvRes);
      } catch {
        setPhysicalVerification(null);
      }

      try {
        const auditRes = await api.getAuditHistory(targetId);
        setAuditLogs(auditRes.audit_logs || []);
      } catch {
        setAuditLogs([]);
      }
    } catch (err) {
      setError('Failed to refresh claim data: ' + err.message);
    } finally {
      setAnalyzing(false);
    }
  };

  const startNewClaim = () => {
    setActiveClaim(null);
    activeClaimIdRef.current = null;
    setAnalysis(null);
    setClaimDocuments([]);
    setReviewQueue([]);
    setPvEligibility(null);
    setPhysicalVerification(null);
    setAuditLogs([]);
    setShowForm(true);
    setError(null);
    setIncidentDescription('');
    setClaimTitle('');

    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.delete('claimId');
      return next;
    });
  };

  /* ---------------------------- Creation Flow ---------------------------- */

  const handleCreateClaim = async (e) => {
    e.preventDefault();
    if (!selectedPolicyId) {
      setError('Please select an active policy.');
      return;
    }
    if (incidentDescription.trim().length < 20) {
      setError('Incident description must be at least 20 characters.');
      return;
    }

    setCreating(true);
    setError(null);

    const incidentDetails = {
      approx_expenses: expenses ? Number(expenses) : null,
    };
    if (incidentCategory === 'medical_health') {
      incidentDetails.hospital_name = hospitalName.trim();
      incidentDetails.admission_date = admissionDate;
      incidentDetails.discharge_date = dischargeDate;
      incidentDetails.diagnosis = diagnosis.trim();
    } else if (incidentCategory === 'vehicle_accident') {
      incidentDetails.vehicle_registration = vehicleReg.trim();
      incidentDetails.driver_name = driverName.trim();
      incidentDetails.licence_no = licenceNo.trim();
      incidentDetails.accident_location = accidentLocation.trim();
      incidentDetails.third_party_involved = thirdPartyInvolved;
    }

    try {
      const newClaim = await api.createClaim({
        policy_id: selectedPolicyId,
        incident_description: incidentDescription.trim(),
        incident_type: incidentCategory,
        incident_date: incidentDate,
        claim_title: claimTitle.trim() || `${formatCategory(incidentCategory)} Claim`,
        claim_category: incidentCategory,
        incident_details: incidentDetails,
      });

      setClaimsList((prev) => [newClaim, ...prev]);
      await selectClaim(newClaim);
      setSuccessMsg('Personalized claim checklist generated based on your policy terms!');
      setTimeout(() => setSuccessMsg(null), 5000);
    } catch (err) {
      setError(err.message || 'Failed to create claim');
    } finally {
      setCreating(false);
    }
  };

  const handleRetryChecklist = async () => {
    if (!activeClaim) return;
    setAnalyzing(true);
    try {
      await api.forceGenerateChecklist(activeClaim.id);
      await refreshClaimData(activeClaim.id);
      setSuccessMsg('Checklist regenerated successfully.');
      setTimeout(() => setSuccessMsg(null), 4000);
    } catch (err) {
      setError('Failed to regenerate checklist: ' + err.message);
    } finally {
      setAnalyzing(false);
    }
  };

  /* ---------------------------- Dedicated Per-Item Upload ---------------------------- */

  const handleItemFileUpload = async (itemId, file, inputElement) => {
    if (inputElement) inputElement.value = '';
    if (!file || !activeClaim) return;

    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setError('Only PDF documents are supported for insurance verification.');
      return;
    }
    if (file.size === 0) {
      setError('Selected file is empty (0 bytes). Please select a valid document.');
      return;
    }
    if (file.size > 15 * 1024 * 1024) {
      setError('File exceeds maximum size limit of 15MB.');
      return;
    }

    setUploadingItemId(itemId);
    setError(null);

    try {
      await api.uploadChecklistDocument(activeClaim.id, itemId, file);
      setSuccessMsg(`Uploaded ${file.name}! AI verified document and placed in human review queue.`);
      await refreshClaimData(activeClaim.id);
      setTimeout(() => setSuccessMsg(null), 4000);
    } catch (err) {
      setError(`Upload failed for ${file.name}: ${err.message}`);
    } finally {
      setUploadingItemId(null);
    }
  };

  const handleDocumentReplace = async (docId, file, inputElement) => {
    if (inputElement) inputElement.value = '';
    if (!file || !activeClaim) return;

    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setError('Only PDF documents are supported.');
      return;
    }
    if (file.size === 0) {
      setError('Selected file is empty (0 bytes).');
      return;
    }
    if (file.size > 15 * 1024 * 1024) {
      setError('File exceeds maximum size limit of 15MB.');
      return;
    }

    setUploadingItemId(docId);
    setError(null);
    try {
      await api.replaceClaimDocument(activeClaim.id, docId, file);
      setSuccessMsg(`Document replaced with ${file.name}. Prior version archived in audit history.`);
      await refreshClaimData(activeClaim.id);
      setTimeout(() => setSuccessMsg(null), 4000);
    } catch (err) {
      setError(`Replacement failed: ${err.message}`);
    } finally {
      setUploadingItemId(null);
    }
  };

  const handleDocumentDelete = async (docId, fileName) => {
    if (!window.confirm(`Are you sure you want to remove '${fileName}'?`)) return;
    try {
      await api.deleteClaimDocument(activeClaim.id, docId);
      await refreshClaimData(activeClaim.id);
      setSuccessMsg(`Document '${fileName}' removed.`);
      setTimeout(() => setSuccessMsg(null), 3000);
    } catch (err) {
      setError(`Delete failed: ${err.message}`);
    }
  };

  const handleReassignSubmit = async (docId, newChecklistItemId) => {
    try {
      await api.reassignClaimDocument(activeClaim.id, docId, newChecklistItemId);
      setReassignModalDoc(null);
      await refreshClaimData(activeClaim.id);
      setSuccessMsg('Document successfully reassigned and re-verified!');
      setTimeout(() => setSuccessMsg(null), 4000);
    } catch (err) {
      setError(`Reassignment failed: ${err.message}`);
    }
  };

  /* ---------------------------- Human Review Actions ---------------------------- */

  const openReviewModal = (doc) => {
    if (userRole === 'claimant') {
      setError('Claimant role is not authorized to sign off or review documents. Switch to Reviewer Portal mode above to perform review.');
      return;
    }
    setReviewModalDoc(doc);
    setReviewerNotes(doc.reviewer_notes || '');
    setReviewOutcome(doc.review_status && doc.review_status !== 'pending' ? doc.review_status : 'accepted');
  };

  const handleSubmitReview = async (e) => {
    e.preventDefault();
    if (!reviewModalDoc || !activeClaim) return;

    if (reviewOutcome !== 'accepted' && reviewOutcome !== 'human_verified' && !reviewerNotes.trim()) {
      setError('Mandatory reviewer notes and justification are required when requesting correction or rejecting a document.');
      return;
    }

    setSubmittingReview(true);
    try {
      await api.submitDocumentReview(activeClaim.id, reviewModalDoc.id, {
        reviewer_name: reviewerName.trim() || 'Senior Claims Analyst',
        review_status: reviewOutcome,
        reviewer_notes: reviewerNotes.trim(),
        reviewer_role: userRole,
      });
      setReviewModalDoc(null);
      await refreshClaimData(activeClaim.id);
      setSuccessMsg(`Review recorded: Document marked as ${reviewOutcome.replace('_', ' ').toUpperCase()}.`);
      setTimeout(() => setSuccessMsg(null), 4000);
    } catch (err) {
      setError(`Failed to submit review: ${err.message}`);
    } finally {
      setSubmittingReview(false);
    }
  };

  /* ---------------------------- Physical Verification Actions ---------------------------- */

  const handleRequestPhysicalVerification = async () => {
    if (!activeClaim) return;
    setRequestingPv(true);
    setError(null);
    try {
      await api.requestPhysicalVerification(activeClaim.id, {
        requested_by: reviewerName.trim() || 'Senior Claims Analyst',
        instructions: 'Please inspect original policy document, driver licence, and vehicle damage in person.',
      });
      setSuccessMsg('Physical verification requested successfully. Claim status advanced to PHYSICAL_VERIFICATION_PENDING.');
      await refreshClaimData(activeClaim.id);
      setActiveTab('physical_verification');
      setTimeout(() => setSuccessMsg(null), 5000);
    } catch (err) {
      setError(`Physical verification request blocked: ${err.message}`);
    } finally {
      setRequestingPv(false);
    }
  };

  const handleScheduleSubmit = async (e) => {
    e.preventDefault();
    if (!activeClaim) return;
    if (!schedDate || !schedLocation.trim()) {
      setError('Appointment date and inspection location are required.');
      return;
    }
    setSubmittingSchedule(true);
    try {
      await api.schedulePhysicalVerification(activeClaim.id, {
        scheduled_date: schedDate,
        scheduled_location: schedLocation.trim(),
        assigned_inspector: schedInspector.trim(),
        instructions: schedInstructions.trim(),
        reviewer_name: reviewerName,
      });
      setScheduleModalOpen(false);
      setSuccessMsg('Physical verification appointment scheduled! Claim status updated to PHYSICAL_VERIFICATION_SCHEDULED.');
      await refreshClaimData(activeClaim.id);
      setTimeout(() => setSuccessMsg(null), 5000);
    } catch (err) {
      setError(`Failed to schedule physical verification: ${err.message}`);
    } finally {
      setSubmittingSchedule(false);
    }
  };

  const handleOutcomeSubmit = async (e) => {
    e.preventDefault();
    if (!activeClaim) return;
    if (!outcomeNotes.trim()) {
      setError('Mandatory inspection outcome notes and findings must be recorded.');
      return;
    }
    setSubmittingOutcome(true);
    try {
      await api.recordPhysicalVerificationOutcome(activeClaim.id, {
        outcome_status: outcomeStatus,
        outcome_notes: outcomeNotes.trim(),
        inspector_name: schedInspector || reviewerName,
      });
      setOutcomeModalOpen(false);
      setSuccessMsg(`Physical verification outcome recorded: ${outcomeStatus.toUpperCase()}!`);
      await refreshClaimData(activeClaim.id);
      setTimeout(() => setSuccessMsg(null), 5000);
    } catch (err) {
      setError(`Failed to record outcome: ${err.message}`);
    } finally {
      setSubmittingOutcome(false);
    }
  };

  /* ---------------------------- Report Actions ---------------------------- */

  const handleGenerateReport = async () => {
    if (!activeClaim) return;
    setGeneratingReport(true);
    setError(null);
    try {
      await api.generateReport(activeClaim.id, 'pdf');
      const pdfUrl = `${api.downloadReport(activeClaim.id, 'pdf')}&_t=${Date.now()}`;
      window.open(pdfUrl, '_blank');
      await refreshClaimData(activeClaim.id);
    } catch (err) {
      setError('Failed to generate report: ' + err.message);
    } finally {
      setGeneratingReport(false);
    }
  };

  /* ---------------------------- Derived State ---------------------------- */

  const items = analysis?.checklist_items || [];

  const counts = useMemo(() => {
    const c = { all: items.length, reviewed: 0, ready_for_review: 0, needs_attention: 0, awaiting_upload: 0, not_stated: 0 };
    items.forEach((i) => {
      const s = normalizeStatus(i.status);
      if (s === 'reviewed') c.reviewed += 1;
      else if (s === 'ready_for_review' || s === 'present') c.ready_for_review += 1;
      else if (s === 'needs_attention' || s === 'unclear' || s === 'correction_required' || s === 'human_rejected') c.needs_attention += 1;
      else if (s === 'not_stated') c.not_stated += 1;
      else c.awaiting_upload += 1;
    });
    return c;
  }, [items]);

  const filteredItems = useMemo(() => {
    if (filter === 'all') return items;
    return items.filter((i) => {
      const s = normalizeStatus(i.status);
      if (filter === 'reviewed') return s === 'reviewed';
      if (filter === 'ready_for_review') return s === 'ready_for_review' || s === 'present';
      if (filter === 'needs_attention') return s === 'needs_attention' || s === 'unclear' || s === 'correction_required' || s === 'human_rejected';
      if (filter === 'awaiting_upload') return s === 'awaiting_upload' || s === 'missing' || s === 'processing_failed';
      return true;
    });
  }, [items, filter]);

  // Determine 5-Stage Stepper current index
  let currentStep = 1;
  if (activeClaim) currentStep = 2;
  if (items.length > 0) currentStep = 3;
  if (claimDocuments.length > 0 && claimDocuments.some((d) => d.review_status && d.review_status !== 'pending')) currentStep = 4;
  if (physicalVerification && physicalVerification.status !== 'none') currentStep = 5;

  const steps = [
    { num: 1, label: 'Policy & Incident' },
    { num: 2, label: 'Document Checklist' },
    { num: 3, label: 'Uploads & AI Check' },
    { num: 4, label: 'Human Review' },
    { num: 5, label: 'Physical Verification' },
  ];

  const selectedPolicy = policies.find((p) => p.id === selectedPolicyId);

  return (
    <div className="min-h-full bg-slate-50/70 py-6 pb-28">
      <div className="mx-auto max-w-7xl space-y-6 px-4 sm:px-6 lg:px-8">
        {/* Header with Role Simulator Switch */}
        <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="mb-1.5 inline-flex items-center gap-1.5 rounded-full bg-indigo-50 px-2.5 py-1 text-[11px] font-bold text-indigo-700 ring-1 ring-inset ring-indigo-200">
              <ShieldCheck className="h-3.5 w-3.5" />
              End-to-End Insurance Claim Verification Engine
            </div>
            <h1 className="text-2xl font-black tracking-tight text-slate-900 sm:text-3xl">
              Insurance Claims Assistant
            </h1>
            <p className="mt-1 text-xs text-slate-500 sm:text-sm">
              Online document intake, independent requirement uploads, AI OCR verification, human online review queue, and physical verification.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* Role Simulation Badge / Toggle */}
            <div className="flex items-center rounded-xl border border-slate-200 bg-white p-1 text-xs font-semibold shadow-sm">
              <span className="px-2 text-slate-500 text-[11px]">Role:</span>
              <button
                type="button"
                onClick={() => setUserRole('claimant')}
                className={`rounded-lg px-2.5 py-1 transition ${
                  userRole === 'claimant' ? 'bg-slate-900 text-white' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Claimant
              </button>
              <button
                type="button"
                onClick={() => setUserRole('reviewer')}
                className={`rounded-lg px-2.5 py-1 transition ${
                  userRole === 'reviewer' ? 'bg-indigo-600 text-white' : 'text-slate-600 hover:text-indigo-600'
                }`}
              >
                Reviewer Portal
              </button>
            </div>

            {activeClaim && (
              <button
                onClick={startNewClaim}
                className="inline-flex items-center gap-1.5 rounded-xl bg-slate-900 px-3.5 py-2 text-xs font-semibold text-white shadow-sm transition hover:bg-slate-800"
              >
                <ClipboardCheck className="h-3.5 w-3.5" />
                New Claim
              </button>
            )}
          </div>
        </header>

        {/* 5-Stage Stepper */}
        <Stepper steps={steps} current={currentStep} />

        {/* Toast / Notification Banners */}
        {error && (
          <div role="alert" className="flex items-start gap-3 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-xs text-rose-800 shadow-sm sm:text-sm">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-600" />
            <p className="flex-1 font-medium">{error}</p>
            <button onClick={() => setError(null)} className="rounded p-0.5 text-rose-500 hover:bg-rose-100">
              <X className="h-4 w-4" />
            </button>
          </div>
        )}

        {successMsg && (
          <div role="status" className="flex items-start gap-3 rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-xs text-emerald-800 shadow-sm sm:text-sm">
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
            <p className="flex-1 font-semibold">{successMsg}</p>
            <button onClick={() => setSuccessMsg(null)} className="rounded p-0.5 text-emerald-500 hover:bg-emerald-100">
              <X className="h-4 w-4" />
            </button>
          </div>
        )}

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12 lg:gap-8">
          {/* LEFT COLUMN: Policy & Incident Form OR Active Claim Summary */}
          <div className="space-y-6 lg:col-span-5">
            {showForm || !activeClaim ? (
              <Card
                title="Stage 1: Claim Creation & Incident Details"
                subtitle="Select your policy and tell us what happened to build a grounded checklist."
                icon={FileText}
                action={
                  activeClaim && (
                    <button onClick={() => setShowForm(false)} className="text-xs font-semibold text-slate-500 hover:text-slate-800">
                      Cancel
                    </button>
                  )
                }
              >
                <form onSubmit={handleCreateClaim} className="space-y-4">
                  {/* Step 1: Policy Selection */}
                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1">
                      1. Select Insurance Policy ({policies.length} available)
                    </label>
                    <select
                      value={selectedPolicyId}
                      onChange={(e) => setSelectedPolicyId(e.target.value)}
                      className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-800 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-100"
                      required
                    >
                      <option value="">Select an active policy…</option>
                      {policies.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.display_name} ({p.policy_type || 'Standard'} &bull; {p.page_count} pages)
                        </option>
                      ))}
                    </select>

                    {selectedPolicy && (
                      <div className="mt-2 rounded-xl border border-indigo-100 bg-indigo-50/50 p-3 text-xs space-y-1">
                        <div className="flex justify-between font-medium text-indigo-950">
                          <span>Coverage Category:</span>
                          <span className="font-bold">{selectedPolicy.policy_type || 'Standard'}</span>
                        </div>
                        <div className="flex justify-between text-indigo-800">
                          <span>Document Length:</span>
                          <span>{selectedPolicy.page_count} pages indexed</span>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Step 2: Incident Form */}
                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1">Claim Title / Reference</label>
                    <input
                      type="text"
                      placeholder="e.g. Appendicitis Surgery Claim or Highway Collision"
                      value={claimTitle}
                      onChange={(e) => setClaimTitle(e.target.value)}
                      className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs text-slate-800 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-100"
                    />
                  </div>

                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                    <div>
                      <label className="block text-xs font-bold text-slate-700 mb-1">Claim Category</label>
                      <select
                        value={incidentCategory}
                        onChange={(e) => setIncidentCategory(e.target.value)}
                        className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs text-slate-800 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-100"
                      >
                        {INCIDENT_CATEGORIES.map((c) => (
                          <option key={c.value} value={c.value}>{c.label}</option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-slate-700 mb-1">Incident Date</label>
                      <input
                        type="date"
                        value={incidentDate}
                        max={new Date().toISOString().split('T')[0]}
                        onChange={(e) => setIncidentDate(e.target.value)}
                        className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs text-slate-800 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-100"
                        required
                      />
                    </div>
                  </div>

                  {/* Adaptive Category Fields */}
                  {incidentCategory === 'medical_health' && (
                    <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-3.5 space-y-3">
                      <p className="text-[11px] font-bold uppercase tracking-wider text-indigo-700">Hospitalization Details</p>
                      <div>
                        <label className="block text-[11px] font-semibold text-slate-600 mb-0.5">Hospital Name</label>
                        <input
                          type="text"
                          placeholder="e.g. City Care Hospital"
                          value={hospitalName}
                          onChange={(e) => setHospitalName(e.target.value)}
                          className="w-full rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs"
                        />
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <label className="block text-[11px] font-semibold text-slate-600 mb-0.5">Admission Date</label>
                          <input
                            type="date"
                            value={admissionDate}
                            onChange={(e) => setAdmissionDate(e.target.value)}
                            className="w-full rounded-lg border border-slate-300 bg-white px-2 py-1.5 text-xs"
                          />
                        </div>
                        <div>
                          <label className="block text-[11px] font-semibold text-slate-600 mb-0.5">Discharge Date</label>
                          <input
                            type="date"
                            value={dischargeDate}
                            onChange={(e) => setDischargeDate(e.target.value)}
                            className="w-full rounded-lg border border-slate-300 bg-white px-2 py-1.5 text-xs"
                          />
                        </div>
                      </div>
                      <div>
                        <label className="block text-[11px] font-semibold text-slate-600 mb-0.5">Primary Diagnosis</label>
                        <input
                          type="text"
                          placeholder="e.g. Acute Appendicitis with Laparoscopic Surgery"
                          value={diagnosis}
                          onChange={(e) => setDiagnosis(e.target.value)}
                          className="w-full rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs"
                        />
                      </div>
                    </div>
                  )}

                  {incidentCategory === 'vehicle_accident' && (
                    <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-3.5 space-y-3">
                      <p className="text-[11px] font-bold uppercase tracking-wider text-indigo-700">Vehicle & Incident Details</p>
                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <label className="block text-[11px] font-semibold text-slate-600 mb-0.5">Vehicle Registration</label>
                          <input
                            type="text"
                            placeholder="e.g. MH-01-AB-1234"
                            value={vehicleReg}
                            onChange={(e) => setVehicleReg(e.target.value)}
                            className="w-full rounded-lg border border-slate-300 bg-white px-2 py-1.5 text-xs"
                          />
                        </div>
                        <div>
                          <label className="block text-[11px] font-semibold text-slate-600 mb-0.5">Driver Name</label>
                          <input
                            type="text"
                            placeholder="e.g. Rajesh Kumar"
                            value={driverName}
                            onChange={(e) => setDriverName(e.target.value)}
                            className="w-full rounded-lg border border-slate-300 bg-white px-2 py-1.5 text-xs"
                          />
                        </div>
                      </div>
                      <div>
                        <label className="block text-[11px] font-semibold text-slate-600 mb-0.5">Accident Location</label>
                        <input
                          type="text"
                          placeholder="e.g. Western Express Highway, Mumbai"
                          value={accidentLocation}
                          onChange={(e) => setAccidentLocation(e.target.value)}
                          className="w-full rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs"
                        />
                      </div>
                    </div>
                  )}

                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1">
                      Approximate Expenses Incurred (₹)
                    </label>
                    <input
                      type="number"
                      placeholder="e.g. 45000"
                      value={expenses}
                      onChange={(e) => setExpenses(e.target.value)}
                      className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs text-slate-800 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-100"
                    />
                  </div>

                  <div>
                    <div className="flex justify-between items-center mb-1">
                      <label className="text-xs font-bold text-slate-700">Incident Description (Mandatory)</label>
                      <span className="text-[10px] text-slate-400">{incidentDescription.trim().length}/20 min chars</span>
                    </div>
                    <textarea
                      rows={4}
                      placeholder="Describe the incident in detail: what happened, symptoms or damage, hospital timeline, FIR details, etc…"
                      value={incidentDescription}
                      onChange={(e) => setIncidentDescription(e.target.value)}
                      className="w-full rounded-xl border border-slate-300 bg-white p-3 text-xs text-slate-800 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-100 resize-y"
                      required
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={creating || !selectedPolicyId}
                    className="flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-3 text-xs font-bold text-white shadow-sm transition hover:bg-indigo-700 disabled:opacity-50"
                  >
                    {creating ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Analyzing policy and generating checklist…
                      </>
                    ) : (
                      <>
                        Create Claim & Generate Checklist
                        <ArrowRight className="h-4 w-4" />
                      </>
                    )}
                  </button>
                </form>
              </Card>
            ) : (
              /* Active Claim Details Card */
              <Card
                title={activeClaim.claim_title || `${formatCategory(activeClaim.incident_type)} Claim`}
                icon={ClipboardCheck}
                action={
                  <button onClick={() => setShowForm(true)} className="text-xs font-bold text-indigo-600 hover:text-indigo-800">
                    Edit Details
                  </button>
                }
              >
                <div className="space-y-3 text-xs">
                  <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                    <span className="text-slate-500">Lifecycle Status</span>
                    <span className="rounded-full bg-indigo-50 px-2.5 py-0.5 font-bold uppercase tracking-wide text-indigo-700 text-[10px] ring-1 ring-inset ring-indigo-200">
                      {(activeClaim.status || 'draft').replace(/_/g, ' ')}
                    </span>
                  </div>
                  <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                    <span className="text-slate-500">Claim Category</span>
                    <span className="font-bold text-slate-900">{formatCategory(activeClaim.incident_type)}</span>
                  </div>
                  <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                    <span className="text-slate-500">Incident Date</span>
                    <span className="font-semibold text-slate-900">{String(activeClaim.incident_date).slice(0, 10)}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block mb-1">Incident Statement:</span>
                    <p className="rounded-xl bg-slate-50 p-3 text-slate-700 leading-relaxed border border-slate-100">
                      {activeClaim.incident_description}
                    </p>
                  </div>
                </div>
              </Card>
            )}

            {/* Past Claims History List scoped to currently selected policy */}
            {(() => {
              const scopedClaims = selectedPolicyId
                ? claimsList.filter((c) => c.policy_id === selectedPolicyId)
                : claimsList;
              if (scopedClaims.length === 0) return null;
              return (
                <Card title="Saved Claims for Policy" icon={Layers}>
                  <ul className="space-y-2 max-h-60 overflow-y-auto pr-1">
                    {scopedClaims.map((c) => {
                      const isSelected = activeClaim?.id === c.id;
                      return (
                        <li key={c.id}>
                          <button
                            onClick={() => selectClaim(c)}
                            className={`w-full rounded-xl p-3 text-left transition border ${
                              isSelected
                                ? 'border-indigo-300 bg-indigo-50/70 shadow-sm'
                                : 'border-slate-200/80 hover:bg-slate-50 bg-white'
                            }`}
                          >
                            <div className="flex items-center justify-between">
                              <span className="text-xs font-bold text-slate-900">
                                {c.claim_title || formatCategory(c.incident_type)}
                              </span>
                              <span className="text-[10px] font-bold text-indigo-600">
                                {c.readiness_score || 0}% Ready
                              </span>
                            </div>
                            <p className="line-clamp-1 text-[11px] text-slate-500 mt-1">
                              {c.incident_description}
                            </p>
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                </Card>
              );
            })()}
          </div>

          {/* RIGHT COLUMN: Checklist Dashboard, Per-Item Upload Cards, Review Queue & Physical Verification */}
          <div className="space-y-6 lg:col-span-7">
            {!activeClaim ? (
              <div className="flex min-h-[380px] flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-white/70 p-10 text-center">
                <span className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600">
                  <ClipboardCheck className="h-7 w-7" />
                </span>
                <h3 className="text-base font-bold text-slate-900">No Claim Selected</h3>
                <p className="mt-1 max-w-sm text-xs text-slate-500">
                  Select a policy and submit incident details to generate a customized, policy-grounded document checklist.
                </p>
              </div>
            ) : (
              <>
                {/* Readiness Score & Audit Overview Banner */}
                <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm p-5 sm:p-6">
                  <div className="flex flex-col sm:flex-row items-center gap-6">
                    <ReadinessRing value={analysis?.readiness_score || activeClaim?.readiness_score || 0} />
                    <div className="min-w-0 flex-1 space-y-1.5 text-center sm:text-left">
                      <div className="flex items-center justify-center sm:justify-start gap-2">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-600">
                          Claim Preparation Readiness
                        </span>
                        <div className="relative group cursor-pointer inline-flex items-center">
                          <Info className="h-3.5 w-3.5 text-slate-400 hover:text-slate-700" />
                          <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 hidden group-hover:block w-64 rounded-xl bg-slate-900 p-2.5 text-[11px] text-white shadow-lg z-20 font-normal">
                            Deterministic completeness score based on validated document requirements, human review sign-offs, and policy grounding.
                          </div>
                        </div>
                      </div>
                      <h3 className="text-lg font-black text-slate-900">
                        {activeClaim.claim_title || formatCategory(activeClaim.incident_type)}
                      </h3>
                      <p className="text-xs text-slate-500 line-clamp-1">
                        Policy: {selectedPolicy?.display_name || 'Associated Policy'}
                      </p>

                      {/* Status Badges Row */}
                      <div className="flex flex-wrap items-center justify-center sm:justify-start gap-1.5 pt-2 text-[11px] font-semibold">
                        <span className="rounded-full bg-emerald-100 px-2.5 py-0.5 text-emerald-800">
                          {counts.reviewed} Human Verified
                        </span>
                        <span className="rounded-full bg-indigo-50 px-2.5 py-0.5 text-indigo-700">
                          {counts.ready_for_review} Awaiting Human Review
                        </span>
                        {counts.needs_attention > 0 && (
                          <span className="rounded-full bg-amber-100 px-2.5 py-0.5 text-amber-800">
                            {counts.needs_attention} Needs Attention
                          </span>
                        )}
                        <span className="rounded-full bg-rose-50 px-2.5 py-0.5 text-rose-700">
                          {counts.awaiting_upload} Awaiting Upload
                        </span>
                      </div>
                    </div>

                    <button
                      onClick={() => refreshClaimData(activeClaim.id)}
                      disabled={analyzing}
                      title="Refresh Analysis"
                      className="rounded-xl border border-slate-200 p-2.5 text-slate-500 hover:bg-slate-50 transition"
                    >
                      <RefreshCw className={`h-4 w-4 ${analyzing ? 'animate-spin' : ''}`} />
                    </button>
                  </div>
                </section>

                {/* Navigation Tabs: Document Checklist, Review Queue, Physical Verification, Audit Trail */}
                <div className="flex items-center justify-between border-b border-slate-200 pb-2">
                  <div className="flex flex-wrap gap-2">
                    <button
                      onClick={() => setActiveTab('checklist')}
                      className={`rounded-xl px-3.5 py-2 text-xs font-bold transition ${
                        activeTab === 'checklist'
                          ? 'bg-indigo-600 text-white shadow-sm'
                          : 'bg-white text-slate-600 hover:bg-slate-100'
                      }`}
                    >
                      Document Checklist ({items.length})
                    </button>
                    <button
                      onClick={() => setActiveTab('review_queue')}
                      className={`relative rounded-xl px-3.5 py-2 text-xs font-bold transition ${
                        activeTab === 'review_queue'
                          ? 'bg-indigo-600 text-white shadow-sm'
                          : 'bg-white text-slate-600 hover:bg-slate-100'
                      }`}
                    >
                      Human Review Queue
                      {reviewQueue.length > 0 && (
                        <span className="ml-1.5 rounded-full bg-amber-500 px-1.5 py-0.2 text-[10px] text-white">
                          {reviewQueue.length}
                        </span>
                      )}
                    </button>
                    <button
                      onClick={() => setActiveTab('physical_verification')}
                      className={`rounded-xl px-3.5 py-2 text-xs font-bold transition ${
                        activeTab === 'physical_verification'
                          ? 'bg-indigo-600 text-white shadow-sm'
                          : 'bg-white text-slate-600 hover:bg-slate-100'
                      }`}
                    >
                      Physical Verification
                      {physicalVerification && physicalVerification.status !== 'none' && (
                        <span className="ml-1.5 rounded-full bg-emerald-500 px-1.5 py-0.2 text-[10px] text-white">
                          Active
                        </span>
                      )}
                    </button>
                    <button
                      onClick={() => setActiveTab('audit_trail')}
                      className={`rounded-xl px-3.5 py-2 text-xs font-bold transition ${
                        activeTab === 'audit_trail'
                          ? 'bg-indigo-600 text-white shadow-sm'
                          : 'bg-white text-slate-600 hover:bg-slate-100'
                      }`}
                    >
                      Audit Trail ({auditLogs.length})
                    </button>
                  </div>
                </div>

                {/* TAB 1: Document Checklist Cards */}
                {activeTab === 'checklist' && (
                  <div className="space-y-4">
                    {/* Filters bar */}
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="text-xs font-bold text-slate-700">Filter Checklist:</span>
                      <div className="flex flex-wrap gap-1">
                        {[
                          { key: 'all', label: 'All', count: counts.all },
                          { key: 'awaiting_upload', label: 'Awaiting Upload', count: counts.awaiting_upload },
                          { key: 'ready_for_review', label: 'Ready for Review', count: counts.ready_for_review },
                          { key: 'needs_attention', label: 'Needs Attention', count: counts.needs_attention },
                          { key: 'reviewed', label: 'Human Verified', count: counts.reviewed },
                        ].map((t) => (
                          <button
                            key={t.key}
                            onClick={() => setFilter(t.key)}
                            className={`rounded-lg px-2.5 py-1 text-[11px] font-semibold transition ${
                              filter === t.key
                                ? 'bg-slate-900 text-white shadow-sm'
                                : 'bg-white text-slate-600 hover:bg-slate-100'
                            }`}
                          >
                            {t.label} <span className="text-slate-400">({t.count})</span>
                          </button>
                        ))}
                      </div>
                    </div>

                    {filteredItems.length === 0 ? (
                      <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center space-y-3">
                        <p className="text-xs text-slate-500">
                          {items.length === 0
                            ? 'Checklist is currently empty. Click below to generate from policy terms.'
                            : 'No items match the selected filter.'}
                        </p>
                        {items.length === 0 && (
                          <button
                            onClick={handleRetryChecklist}
                            className="rounded-xl bg-indigo-600 px-4 py-2 text-xs font-bold text-white shadow hover:bg-indigo-700"
                          >
                            Generate Policy Checklist
                          </button>
                        )}
                      </div>
                    ) : (
                      <div className="space-y-3.5">
                        {filteredItems.map((item) => {
                          const norm = normalizeStatus(item.status);
                          const meta = STATUS_META[norm];
                          const associatedDoc = claimDocuments.find(
                            (d) => d.checklist_item_id === item.item_id || d.id === item.document_id
                          );
                          const isUploadingThis = uploadingItemId === item.item_id;

                          return (
                            <div
                              key={item.item_id}
                              className="relative overflow-hidden rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm transition hover:border-slate-300 space-y-3"
                            >
                              <span className={`absolute inset-y-0 left-0 w-1.5 ${meta.bar}`} />

                              {/* Card Header */}
                              <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2 pl-1">
                                <div className="space-y-1">
                                  <div className="flex flex-wrap items-center gap-2">
                                    <h4 className="text-sm font-bold text-slate-900">{item.title}</h4>
                                    <StatusBadge status={item.status} />
                                    {item.source === 'policy_requirement' && (
                                      <span className="rounded bg-indigo-50 px-2 py-0.5 text-[10px] font-bold text-indigo-700 ring-1 ring-inset ring-indigo-200">
                                        Mandatory Policy Requirement
                                      </span>
                                    )}
                                    {item.source === 'general_guidance' && (
                                      <span className="rounded bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-600 ring-1 ring-inset ring-slate-200">
                                        General Guidance
                                      </span>
                                    )}
                                  </div>
                                  <p className="text-xs text-slate-600">{item.why_needed}</p>
                                </div>

                                {/* Policy Citation Tag */}
                                {item.policy_citations?.[0] && (
                                  <span className="shrink-0 self-start rounded-lg bg-indigo-50 px-2.5 py-1 text-[10px] font-bold text-indigo-800 ring-1 ring-indigo-100">
                                    Policy Clause (Page {item.policy_citations[0].page})
                                  </span>
                                )}
                              </div>

                              {/* Policy Citation Quote */}
                              {item.policy_citations?.[0]?.quote && (
                                <div className="ml-1 rounded-xl border border-indigo-100 bg-indigo-50/40 p-2.5 text-[11px] text-indigo-900">
                                  <span className="font-bold text-indigo-800">Clause Excerpt:</span> “{item.policy_citations[0].quote}”
                                </div>
                              )}

                              {/* STATE 1: If file has NOT been uploaded yet -> Dedicated Upload Control */}
                              {!associatedDoc && (
                                <div className="ml-1 pt-1">
                                  <label
                                    htmlFor={`upload-item-${item.item_id}`}
                                    className={`flex items-center justify-center gap-2 rounded-xl border-2 border-dashed border-indigo-200 bg-indigo-50/40 p-3.5 text-center cursor-pointer transition hover:bg-indigo-50 hover:border-indigo-400 ${
                                      isUploadingThis ? 'opacity-50 pointer-events-none' : ''
                                    }`}
                                  >
                                    {isUploadingThis ? (
                                      <Loader2 className="h-4 w-4 animate-spin text-indigo-600" />
                                    ) : (
                                      <FileUp className="h-4 w-4 text-indigo-600" />
                                    )}
                                    <span className="text-xs font-bold text-indigo-700">
                                      {isUploadingThis ? 'Uploading & Verifying…' : `Upload ${item.title} (PDF)`}
                                    </span>
                                    <input
                                      id={`upload-item-${item.item_id}`}
                                      type="file"
                                      accept=".pdf,application/pdf"
                                      onChange={(e) => handleItemFileUpload(item.item_id, e.target.files?.[0], e.target)}
                                      className="sr-only"
                                      disabled={isUploadingThis}
                                    />
                                  </label>
                                </div>
                              )}

                              {/* STATE 2: If document IS uploaded -> File metadata & AI Verification results */}
                              {associatedDoc && (
                                <div className="ml-1 rounded-xl border border-slate-200 bg-slate-50/70 p-3.5 space-y-3">
                                  {/* Document info bar */}
                                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200/80 pb-2.5">
                                    <div className="flex items-center gap-2">
                                      <FileSpreadsheet className="h-4 w-4 text-indigo-600" />
                                      <span className="text-xs font-bold text-slate-900">{associatedDoc.filename}</span>
                                      <span className="text-[10px] text-slate-500">
                                        ({formatBytes(associatedDoc.file_size)} &bull; {associatedDoc.page_count} pgs &bull; v{associatedDoc.version || 1})
                                      </span>
                                    </div>
                                    <div className="flex items-center gap-1.5">
                                      {/* Secure Preview Button */}
                                      <a
                                        href={api.getDocumentFileUrl(activeClaim.id, associatedDoc.id)}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="inline-flex items-center gap-1 text-[11px] font-semibold text-indigo-700 hover:text-indigo-900 px-2 py-0.5 rounded border border-indigo-200 bg-white"
                                        title="Preview PDF"
                                      >
                                        <Eye className="h-3.5 w-3.5 text-indigo-600" />
                                        View PDF
                                      </a>

                                      {/* Reassign Button */}
                                      <button
                                        onClick={() => setReassignModalDoc(associatedDoc)}
                                        className="text-[11px] font-semibold text-slate-600 hover:text-indigo-600 px-2 py-0.5 rounded border border-slate-200 bg-white"
                                      >
                                        Reassign
                                      </button>

                                      {/* Replace Document Button */}
                                      <label
                                        htmlFor={`replace-${associatedDoc.id}`}
                                        className="cursor-pointer text-[11px] font-semibold text-indigo-600 hover:text-indigo-800 px-2 py-0.5 rounded border border-indigo-200 bg-indigo-50/50"
                                      >
                                        Replace
                                        <input
                                          id={`replace-${associatedDoc.id}`}
                                          type="file"
                                          accept=".pdf,application/pdf"
                                          onChange={(e) => handleDocumentReplace(associatedDoc.id, e.target.files?.[0], e.target)}
                                          className="sr-only"
                                        />
                                      </label>

                                      {/* Delete Button */}
                                      <button
                                        onClick={() => handleDocumentDelete(associatedDoc.id, associatedDoc.filename)}
                                        className="p-1 text-slate-400 hover:text-rose-600 transition"
                                        title="Delete Document"
                                      >
                                        <Trash2 className="h-3.5 w-3.5" />
                                      </button>
                                    </div>
                                  </div>

                                  {/* Mismatch Alert with Quick Reassign Option */}
                                  {associatedDoc.classification?.is_mismatch && (
                                    <div className="rounded-xl border border-amber-300 bg-amber-50 p-3 text-xs text-amber-900 flex items-start gap-2.5">
                                      <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
                                      <div className="flex-1">
                                        <p className="font-bold">Document Category Mismatch Detected by AI</p>
                                        <p className="mt-0.5 text-[11px]">
                                          {associatedDoc.classification.mismatch_message}
                                        </p>
                                        {associatedDoc.classification.suggested_item_id && (
                                          <button
                                            onClick={() => handleReassignSubmit(associatedDoc.id, associatedDoc.classification.suggested_item_id)}
                                            className="mt-2 inline-flex items-center gap-1 rounded-lg bg-amber-600 px-2.5 py-1 text-[11px] font-bold text-white hover:bg-amber-700"
                                          >
                                            Reassign to {associatedDoc.classification.detected_label}
                                          </button>
                                        )}
                                      </div>
                                    </div>
                                  )}

                                  {/* Issues / Discrepancy Warnings */}
                                  {associatedDoc.issues?.length > 0 && (
                                    <div className="space-y-1">
                                      {associatedDoc.issues.map((iss, i) => (
                                        <div key={i} className="flex items-start gap-2 text-[11px] text-amber-900 bg-amber-50/80 p-2 rounded-lg border border-amber-200">
                                          <AlertCircle className="h-3.5 w-3.5 text-amber-600 shrink-0 mt-0.5" />
                                          <span>{iss.message}</span>
                                        </div>
                                      ))}
                                    </div>
                                  )}

                                  {/* Verification Summary Chips */}
                                  <div className="flex flex-wrap items-center gap-2 text-[11px]">
                                    {associatedDoc.extracted_data?.patient_name && (
                                      <span className="rounded-md bg-white border border-slate-200 px-2 py-1 text-slate-700">
                                        <b>Patient:</b> {associatedDoc.extracted_data.patient_name}
                                      </span>
                                    )}
                                    {associatedDoc.extracted_data?.total_amount !== undefined && (
                                      <span className="rounded-md bg-white border border-slate-200 px-2 py-1 text-slate-700">
                                        <b>Amount:</b> ₹{associatedDoc.extracted_data.total_amount?.toLocaleString()}
                                      </span>
                                    )}
                                    {associatedDoc.verification_findings?.arithmetic_check && (
                                      <span className="rounded-md bg-emerald-50 text-emerald-800 border border-emerald-200 px-2 py-1 font-semibold">
                                        Arithmetic Check: {associatedDoc.verification_findings.arithmetic_check}
                                      </span>
                                    )}

                                    <button
                                      onClick={() => setExpandedDocItem(expandedDocItem === item.item_id ? null : item.item_id)}
                                      className="text-indigo-600 hover:text-indigo-800 font-bold ml-auto"
                                    >
                                      {expandedDocItem === item.item_id ? 'Hide Details' : 'View Extracted Facts'}
                                    </button>
                                  </div>

                                  {/* Expandable Structured Facts Drawer */}
                                  {expandedDocItem === item.item_id && (
                                    <div className="rounded-xl border border-slate-200 bg-white p-3 text-xs space-y-2 mt-2">
                                      <p className="font-bold text-slate-900">Extracted Structured Facts</p>
                                      <pre className="text-[10px] bg-slate-50 p-2 rounded border border-slate-100 overflow-x-auto text-slate-800">
                                        {JSON.stringify(associatedDoc.extracted_data || {}, null, 2)}
                                      </pre>
                                    </div>
                                  )}

                                  {/* Human Review Status Banner / Trigger */}
                                  <div className="flex items-center justify-between pt-1 border-t border-slate-200/60 text-xs">
                                    {associatedDoc.review_status && associatedDoc.review_status !== 'pending' ? (
                                      <span className="text-[11px] font-semibold text-emerald-700 flex items-center gap-1">
                                        <CheckCircle2 className="h-3.5 w-3.5" />
                                        Reviewed by {associatedDoc.reviewer_name || 'Assessor'} ({associatedDoc.review_status.replace(/_/g, ' ').toUpperCase()})
                                      </span>
                                    ) : (
                                      <span className="text-[11px] text-slate-500 flex items-center gap-1">
                                        <Clock className="h-3.5 w-3.5 text-slate-400" />
                                        In human review queue (Pending Assessor Sign-Off)
                                      </span>
                                    )}

                                    <button
                                      onClick={() => openReviewModal(associatedDoc)}
                                      className="inline-flex items-center gap-1 rounded-lg bg-slate-900 px-2.5 py-1 text-[11px] font-bold text-white hover:bg-slate-800"
                                    >
                                      <UserCheck className="h-3 w-3" />
                                      {associatedDoc.review_status && associatedDoc.review_status !== 'pending' ? 'Update Review' : 'Perform Review'}
                                    </button>
                                  </div>
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                )}

                {/* TAB 2: Human Review Queue */}
                {activeTab === 'review_queue' && (
                  <Card
                    title="Online Human Review Queue"
                    subtitle="Assess uploaded documents, inspect AI findings, and record verified decisions with complete audit trail."
                    icon={UserCheck}
                  >
                    {reviewQueue.length === 0 ? (
                      <p className="p-8 text-center text-xs text-slate-500">
                        No documents currently in the review queue. Upload documents against checklist items to start reviewing.
                      </p>
                    ) : (
                      <div className="space-y-4">
                        {reviewQueue.map((doc) => (
                          <div key={doc.id} className="rounded-xl border border-slate-200 p-4 space-y-3 bg-slate-50/50">
                            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                              <div>
                                <h4 className="text-xs font-bold text-slate-900">{doc.filename}</h4>
                                <p className="text-[11px] text-slate-500">
                                  Checklist Requirement: <b>{doc.checklist_item_id || 'General'}</b> &bull; Status: <StatusBadge status={doc.status} />
                                </p>
                              </div>
                              <div className="flex items-center gap-2">
                                <a
                                  href={api.getDocumentFileUrl(activeClaim.id, doc.id)}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                                >
                                  Preview File
                                </a>
                                <button
                                  onClick={() => openReviewModal(doc)}
                                  className="rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-bold text-white hover:bg-indigo-700"
                                >
                                  Perform Review
                                </button>
                              </div>
                            </div>

                            {doc.review_status && doc.review_status !== 'pending' && (
                              <div className="rounded-lg bg-white p-2.5 border border-slate-200 text-xs text-slate-700">
                                <p className="font-semibold text-emerald-700">
                                  Outcome: {doc.review_status.replace(/_/g, ' ').toUpperCase()} by {doc.reviewer_name}
                                </p>
                                {doc.reviewer_notes && <p className="mt-1 text-slate-600 italic">“{doc.reviewer_notes}”</p>}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </Card>
                )}

                {/* TAB 3: Physical Verification Workflow */}
                {activeTab === 'physical_verification' && (
                  <Card
                    title="Physical Document Verification Workflow"
                    subtitle="Initiated only after all required online human verification has been completed successfully."
                    icon={Building}
                  >
                    <div className="space-y-5 text-xs">
                      {/* Eligibility Banner */}
                      {pvEligibility && !pvEligibility.eligible && (
                        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-amber-900 space-y-2">
                          <div className="flex items-center gap-2 font-bold text-sm text-amber-800">
                            <AlertTriangle className="h-4 w-4" />
                            Physical Verification Blocked
                          </div>
                          <p className="text-xs">{pvEligibility.reason}</p>
                          {pvEligibility.summary?.missing?.length > 0 && (
                            <p className="text-[11px] text-amber-800">
                              <b>Missing mandatory files:</b> {pvEligibility.summary.missing.join(', ')}
                            </p>
                          )}
                          {pvEligibility.summary?.unverified?.length > 0 && (
                            <p className="text-[11px] text-amber-800">
                              <b>Awaiting assessor online sign-off:</b> {pvEligibility.summary.unverified.join(', ')}
                            </p>
                          )}
                          {pvEligibility.summary?.corrections?.length > 0 && (
                            <p className="text-[11px] text-amber-800">
                              <b>Correction/Replacement required:</b> {pvEligibility.summary.corrections.join(', ')}
                            </p>
                          )}
                        </div>
                      )}

                      {pvEligibility && pvEligibility.eligible && (!physicalVerification || physicalVerification.status === 'none') && (
                        <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-emerald-900 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                          <div>
                            <div className="flex items-center gap-2 font-bold text-sm text-emerald-800">
                              <CheckCircle2 className="h-4 w-4" />
                              Online Human Verification Complete!
                            </div>
                            <p className="text-xs mt-1">
                              All mandatory documents have been reviewed and accepted online. The claim is now eligible for physical inspection.
                            </p>
                          </div>
                          <button
                            onClick={handleRequestPhysicalVerification}
                            disabled={requestingPv}
                            className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 font-bold text-white shadow-sm hover:bg-indigo-700 disabled:opacity-50 shrink-0"
                          >
                            {requestingPv ? <Loader2 className="h-4 w-4 animate-spin" /> : <Building className="h-4 w-4" />}
                            Request Physical Verification
                          </button>
                        </div>
                      )}

                      {/* Physical Verification Active Status Details */}
                      {physicalVerification && physicalVerification.status !== 'none' && (
                        <div className="rounded-2xl border border-slate-200 bg-slate-50/70 p-5 space-y-4">
                          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-slate-200 pb-3">
                            <div>
                              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Current Verification State</span>
                              <h4 className="text-sm font-black text-slate-900">
                                {physicalVerification.status === 'pending' && 'Physical Verification Requested (Pending Scheduling)'}
                                {physicalVerification.status === 'scheduled' && 'Physical Verification Appointment Scheduled'}
                                {physicalVerification.status === 'completed' && 'Physical Verification Conducted & Signed Off'}
                                {physicalVerification.status === 'failed' && 'Physical Verification Failed Inspection'}
                              </h4>
                            </div>
                            <span
                              className={`rounded-full px-3 py-1 font-bold uppercase text-[10px] ring-1 ring-inset ${
                                physicalVerification.status === 'completed'
                                  ? 'bg-emerald-100 text-emerald-800 ring-emerald-300'
                                  : physicalVerification.status === 'scheduled'
                                  ? 'bg-indigo-100 text-indigo-800 ring-indigo-300'
                                  : physicalVerification.status === 'failed'
                                  ? 'bg-rose-100 text-rose-800 ring-rose-300'
                                  : 'bg-amber-100 text-amber-800 ring-amber-300'
                              }`}
                            >
                              {physicalVerification.status}
                            </span>
                          </div>

                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                            <div>
                              <span className="text-slate-500 block">Requested By:</span>
                              <span className="font-semibold text-slate-900">{physicalVerification.requested_by}</span>
                            </div>
                            <div>
                              <span className="text-slate-500 block">Requested At:</span>
                              <span className="font-semibold text-slate-900">{physicalVerification.requested_at?.slice(0, 16)}</span>
                            </div>
                            {physicalVerification.scheduled_date && (
                              <div>
                                <span className="text-slate-500 block">Scheduled Date:</span>
                                <span className="font-semibold text-slate-900 flex items-center gap-1">
                                  <Calendar className="h-3.5 w-3.5 text-indigo-600" />
                                  {physicalVerification.scheduled_date}
                                </span>
                              </div>
                            )}
                            {physicalVerification.scheduled_location && (
                              <div>
                                <span className="text-slate-500 block">Inspection Location:</span>
                                <span className="font-semibold text-slate-900 flex items-center gap-1">
                                  <MapPin className="h-3.5 w-3.5 text-indigo-600" />
                                  {physicalVerification.scheduled_location}
                                </span>
                              </div>
                            )}
                            {physicalVerification.assigned_inspector && (
                              <div>
                                <span className="text-slate-500 block">Assigned Inspector:</span>
                                <span className="font-semibold text-slate-900">{physicalVerification.assigned_inspector}</span>
                              </div>
                            )}
                            {physicalVerification.completed_at && (
                              <div>
                                <span className="text-slate-500 block">Completed Timestamp:</span>
                                <span className="font-semibold text-slate-900">{physicalVerification.completed_at?.slice(0, 16)}</span>
                              </div>
                            )}
                          </div>

                          {physicalVerification.instructions && (
                            <div className="rounded-xl bg-white p-3 border border-slate-200">
                              <span className="font-bold text-slate-700 block mb-0.5">Claimant Instructions:</span>
                              <p className="text-slate-600 leading-relaxed">{physicalVerification.instructions}</p>
                            </div>
                          )}

                          {physicalVerification.outcome_notes && (
                            <div className="rounded-xl bg-white p-3 border border-slate-200">
                              <span className="font-bold text-slate-700 block mb-0.5">Inspector Findings & Outcome Notes:</span>
                              <p className="text-slate-600 leading-relaxed">{physicalVerification.outcome_notes}</p>
                            </div>
                          )}

                          {/* Reviewer Action Buttons */}
                          <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-200">
                            {physicalVerification.status === 'pending' && (
                              <button
                                onClick={() => setScheduleModalOpen(true)}
                                className="rounded-xl bg-indigo-600 px-4 py-2 font-bold text-white shadow hover:bg-indigo-700"
                              >
                                Schedule Inspection Appointment
                              </button>
                            )}

                            {physicalVerification.status === 'scheduled' && (
                              <>
                                <button
                                  onClick={() => setScheduleModalOpen(true)}
                                  className="rounded-xl border border-slate-300 bg-white px-3 py-2 font-semibold text-slate-700 hover:bg-slate-50"
                                >
                                  Reschedule
                                </button>
                                <button
                                  onClick={() => setOutcomeModalOpen(true)}
                                  className="rounded-xl bg-emerald-600 px-4 py-2 font-bold text-white shadow hover:bg-emerald-700"
                                >
                                  Record Inspection Outcome
                                </button>
                              </>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  </Card>
                )}

                {/* TAB 4: Audit Trail & History */}
                {activeTab === 'audit_trail' && (
                  <Card
                    title="Immutable Audit Trail"
                    subtitle="Chronological log of all claim creation, document uploads, AI checks, reviewer determinations, and physical verifications."
                    icon={ClipboardCheck}
                  >
                    {auditLogs.length === 0 ? (
                      <p className="p-8 text-center text-xs text-slate-500">
                        No audit events recorded yet.
                      </p>
                    ) : (
                      <div className="space-y-3">
                        {auditLogs.map((log) => (
                          <div key={log.id} className="rounded-xl border border-slate-200 p-3.5 bg-white text-xs space-y-1.5">
                            <div className="flex items-center justify-between">
                              <span className="font-bold text-slate-900">
                                {log.event_type.replace(/_/g, ' ').toUpperCase()}
                              </span>
                              <span className="text-[10px] text-slate-400">
                                {log.created_at?.slice(0, 19).replace('T', ' ')}
                              </span>
                            </div>
                            <div className="flex items-center gap-2 text-[11px] text-slate-600">
                              <span>Actor: <b>{log.actor_name}</b> ({log.actor_role})</span>
                              {log.new_status && (
                                <span className="rounded bg-slate-100 px-1.5 py-0.5 text-slate-700 font-semibold">
                                  Status &rarr; {log.new_status}
                                </span>
                              )}
                            </div>
                            {log.details && Object.keys(log.details).length > 0 && (
                              <p className="text-[10px] bg-slate-50 p-2 rounded text-slate-600 font-mono">
                                {JSON.stringify(log.details)}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </Card>
                )}

                {/* Report Generation Section */}
                <Card
                  title="Claim Preparation Audit Report"
                  subtitle="Download comprehensive PDF report grounded in your policy terms with verified document audit trail."
                  icon={Download}
                >
                  <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
                    <div>
                      <p className="text-xs text-slate-600 font-medium">
                        Report includes incident breakdown, clause citations, document checklist status, and disclaimer.
                      </p>
                      {activeClaim.report_stale && (
                        <p className="text-[11px] font-bold text-amber-700 mt-1 flex items-center gap-1">
                          <AlertTriangle className="h-3.5 w-3.5 text-amber-600" />
                          New documents uploaded since last report. Please regenerate for updated audit trail.
                        </p>
                      )}
                    </div>

                    <button
                      onClick={handleGenerateReport}
                      disabled={generatingReport || analyzing}
                      className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-xs font-bold text-white shadow-sm hover:bg-indigo-700 disabled:opacity-50 transition shrink-0"
                    >
                      {generatingReport ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Download className="h-4 w-4" />
                      )}
                      {generatingReport ? 'Building PDF…' : 'Download Claim Report (PDF)'}
                    </button>
                  </div>
                </Card>
              </>
            )}
          </div>
        </div>
      </div>

      {/* MODAL 1: Human Review Decision Form */}
      {reviewModalDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b pb-3">
              <h3 className="text-sm font-bold text-slate-900">Record Human Review Assessment</h3>
              <button onClick={() => setReviewModalDoc(null)} className="rounded p-1 text-slate-400 hover:bg-slate-100">
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="rounded-xl bg-slate-50 p-3 text-xs space-y-1 border border-slate-200">
              <p><b>Document:</b> {reviewModalDoc.filename}</p>
              <p><b>Requirement:</b> {reviewModalDoc.checklist_item_id}</p>
              <p><b>AI Status:</b> {reviewModalDoc.status}</p>
            </div>

            <form onSubmit={handleSubmitReview} className="space-y-3 text-xs">
              <div>
                <label className="block font-bold text-slate-700 mb-1">Reviewer Name / Title</label>
                <input
                  type="text"
                  value={reviewerName}
                  onChange={(e) => setReviewerName(e.target.value)}
                  className="w-full rounded-xl border border-slate-300 p-2.5"
                  required
                />
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Review Outcome</label>
                <select
                  value={reviewOutcome}
                  onChange={(e) => setReviewOutcome(e.target.value)}
                  className="w-full rounded-xl border border-slate-300 p-2.5 font-semibold"
                >
                  <option value="accepted">Accepted & Verified (Human Verified)</option>
                  <option value="info_required">Correction Required / Replacement Requested</option>
                  <option value="mismatch_confirmed">Document Rejected (Mismatch Confirmed)</option>
                  <option value="unable_to_verify">Unable to Verify</option>
                </select>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">
                  Reviewer Notes & Justification {reviewOutcome !== 'accepted' && <span className="text-rose-600">* (Mandatory)</span>}
                </label>
                <textarea
                  rows={3}
                  placeholder="Record assessment notes, date verification, or requested clarification…"
                  value={reviewerNotes}
                  onChange={(e) => setReviewerNotes(e.target.value)}
                  className="w-full rounded-xl border border-slate-300 p-2.5"
                  required={reviewOutcome !== 'accepted'}
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setReviewModalDoc(null)}
                  className="rounded-xl border border-slate-300 px-4 py-2 font-semibold text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingReview}
                  className="rounded-xl bg-indigo-600 px-4 py-2 font-bold text-white hover:bg-indigo-700 disabled:opacity-50"
                >
                  {submittingReview ? 'Saving…' : 'Record Decision'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 2: Document Reassign Picker */}
      {reassignModalDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b pb-3">
              <h3 className="text-sm font-bold text-slate-900">Reassign Document Category</h3>
              <button onClick={() => setReassignModalDoc(null)} className="rounded p-1 text-slate-400 hover:bg-slate-100">
                <X className="h-4 w-4" />
              </button>
            </div>

            <p className="text-xs text-slate-600">
              Select the correct checklist requirement to associate with <b>{reassignModalDoc.filename}</b>:
            </p>

            <div className="space-y-1.5 max-h-60 overflow-y-auto">
              {items.map((i) => (
                <button
                  key={i.item_id}
                  onClick={() => handleReassignSubmit(reassignModalDoc.id, i.item_id)}
                  className={`w-full rounded-xl p-3 text-left text-xs font-semibold border transition ${
                    reassignModalDoc.checklist_item_id === i.item_id
                      ? 'border-indigo-300 bg-indigo-50 text-indigo-900'
                      : 'border-slate-200 hover:bg-slate-50 text-slate-800'
                  }`}
                >
                  {i.title}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* MODAL 3: Schedule Physical Verification Modal */}
      {scheduleModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b pb-3">
              <h3 className="text-sm font-bold text-slate-900">Schedule Physical Inspection</h3>
              <button onClick={() => setScheduleModalOpen(false)} className="rounded p-1 text-slate-400 hover:bg-slate-100">
                <X className="h-4 w-4" />
              </button>
            </div>

            <form onSubmit={handleScheduleSubmit} className="space-y-3 text-xs">
              <div>
                <label className="block font-bold text-slate-700 mb-1">Appointment Date</label>
                <input
                  type="date"
                  value={schedDate}
                  min={new Date().toISOString().split('T')[0]}
                  onChange={(e) => setSchedDate(e.target.value)}
                  className="w-full rounded-xl border border-slate-300 p-2.5"
                  required
                />
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Inspection Location</label>
                <input
                  type="text"
                  value={schedLocation}
                  onChange={(e) => setSchedLocation(e.target.value)}
                  className="w-full rounded-xl border border-slate-300 p-2.5"
                  required
                />
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Assigned Inspector Name</label>
                <input
                  type="text"
                  value={schedInspector}
                  onChange={(e) => setSchedInspector(e.target.value)}
                  className="w-full rounded-xl border border-slate-300 p-2.5"
                  required
                />
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Instructions for Claimant</label>
                <textarea
                  rows={2}
                  value={schedInstructions}
                  onChange={(e) => setSchedInstructions(e.target.value)}
                  className="w-full rounded-xl border border-slate-300 p-2.5"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setScheduleModalOpen(false)}
                  className="rounded-xl border border-slate-300 px-4 py-2 font-semibold text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingSchedule}
                  className="rounded-xl bg-indigo-600 px-4 py-2 font-bold text-white hover:bg-indigo-700 disabled:opacity-50"
                >
                  {submittingSchedule ? 'Scheduling…' : 'Confirm Appointment'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 4: Record Physical Verification Outcome Modal */}
      {outcomeModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b pb-3">
              <h3 className="text-sm font-bold text-slate-900">Record Inspection Findings & Outcome</h3>
              <button onClick={() => setOutcomeModalOpen(false)} className="rounded p-1 text-slate-400 hover:bg-slate-100">
                <X className="h-4 w-4" />
              </button>
            </div>

            <form onSubmit={handleOutcomeSubmit} className="space-y-3 text-xs">
              <div>
                <label className="block font-bold text-slate-700 mb-1">Inspection Result</label>
                <select
                  value={outcomeStatus}
                  onChange={(e) => setOutcomeStatus(e.target.value)}
                  className="w-full rounded-xl border border-slate-300 p-2.5 font-semibold"
                >
                  <option value="completed">Completed & Verified In-Person</option>
                  <option value="failed">Failed Physical Inspection</option>
                </select>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Inspector Notes & Assessment Findings *</label>
                <textarea
                  rows={4}
                  placeholder="Record findings from physical inspection, chassis number verification, original invoice stamp check…"
                  value={outcomeNotes}
                  onChange={(e) => setOutcomeNotes(e.target.value)}
                  className="w-full rounded-xl border border-slate-300 p-2.5"
                  required
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setOutcomeModalOpen(false)}
                  className="rounded-xl border border-slate-300 px-4 py-2 font-semibold text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingOutcome}
                  className="rounded-xl bg-emerald-600 px-4 py-2 font-bold text-white hover:bg-emerald-700 disabled:opacity-50"
                >
                  {submittingOutcome ? 'Saving…' : 'Record Final Outcome'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}