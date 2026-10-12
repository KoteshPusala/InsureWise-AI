const BASE_URL = '/api';

class ApiError extends Error {
  constructor(status, code, message, isAbort = false) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.isAbort = isAbort;
  }
}

function extractErrorMessage(errorData, rawText, status) {
  if (errorData) {
    if (typeof errorData.detail === 'string' && errorData.detail.trim()) {
      return errorData.detail;
    }
    if (Array.isArray(errorData.detail)) {
      const msgs = errorData.detail.map((d) => d.msg || JSON.stringify(d)).filter(Boolean);
      if (msgs.length > 0) return msgs.join('; ');
    }
    if (errorData.error && typeof errorData.error.message === 'string' && errorData.error.message.trim()) {
      return errorData.error.message;
    }
    if (typeof errorData.message === 'string' && errorData.message.trim()) {
      return errorData.message;
    }
  }
  if (rawText && rawText.length < 200 && !rawText.trim().startsWith('<')) {
    return rawText.trim();
  }
  return `Request failed with status ${status}`;
}

async function request(path, options = {}) {
  const url = `${BASE_URL}${path}`;
  const { timeoutMs, ...fetchOptions } = options;
  const config = {
    headers: {},
    ...fetchOptions,
  };
  
  if (config.body && !(config.body instanceof FormData)) {
    config.headers['Content-Type'] = 'application/json';
    config.body = JSON.stringify(config.body);
  }

  let timeoutId = null;
  if (timeoutMs && !config.signal) {
    const internalController = new AbortController();
    config.signal = internalController.signal;
    timeoutId = setTimeout(() => internalController.abort(), timeoutMs);
  }
  
  try {
    const response = await fetch(url, config);
    if (timeoutId) clearTimeout(timeoutId);
    
    if (!response.ok) {
      let errorData = null;
      let rawText = '';
      try {
        rawText = await response.text();
        errorData = JSON.parse(rawText);
      } catch {
        errorData = null;
      }
      
      const message = extractErrorMessage(errorData, rawText, response.status);
      const code = errorData?.error?.code || errorData?.code || `HTTP_${response.status}`;
      throw new ApiError(response.status, code, message);
    }
    
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      return response.json();
    }
    return response;
  } catch (error) {
    if (timeoutId) clearTimeout(timeoutId);
    if (error instanceof ApiError) throw error;
    if (error.name === 'AbortError' || error.message?.includes('aborted')) {
      throw new ApiError(0, 'ABORTED', 'Request was cancelled', true);
    }
    throw new ApiError(0, 'NETWORK_ERROR', 'Unable to connect to the server. Please check if the backend is running.');
  }
}

export const api = {
  // Health
  getHealth: (options = {}) => request('/health', options),
  
  // Policies
  getPolicies: (options = {}) => request('/policies', options),
  getPolicy: (id, options = {}) => request(`/policies/${id}`, options),
  loadSamplePolicy: (options = {}) => request('/policies/sample', { method: 'POST', ...options }),
  uploadPolicy: (file, options = {}) => {
    const formData = new FormData();
    formData.append('file', file);
    return request('/policies', { method: 'POST', body: formData, ...options });
  },
  deletePolicy: (id, options = {}) => request(`/policies/${id}`, { method: 'DELETE', ...options }),
  getPolicyPdf: (id) => `${BASE_URL}/policies/${id}/pdf`,
  
  // Chat
  sendMessage: (policyId, question, history = [], options = {}) =>
    request(`/policies/${policyId}/chat`, {
      method: 'POST',
      body: { question, history },
      ...options,
    }),
  getChatHistory: (policyId, options = {}) => request(`/policies/${policyId}/chat`, options),
  clearChatHistory: (policyId, options = {}) => request(`/policies/${policyId}/chat`, { method: 'DELETE', ...options }),
  
  // Claims
  createClaim: (data, options = {}) => request('/claims', { method: 'POST', body: data, ...options }),
  updateClaim: (id, data, options = {}) => request(`/claims/${id}`, { method: 'PATCH', body: data, ...options }),
  getClaim: (id, options = {}) => request(`/claims/${id}`, options),
  getClaims: (params = {}, options = {}) => {
    const policyId = typeof params === 'string' ? params : params?.policy_id;
    const query = policyId ? `?policy_id=${encodeURIComponent(policyId)}` : '';
    const opts = typeof params === 'object' && !params.policy_id ? { ...params, ...options } : options;
    return request(`/claims${query}`, opts);
  },
  
  // Per-item checklist upload
  uploadChecklistDocument: (claimId, itemId, file, options = {}) => {
    const formData = new FormData();
    formData.append('file', file);
    return request(`/claims/${claimId}/checklist/${itemId}/documents`, { method: 'POST', body: formData, ...options });
  },
  uploadClaimDocument: (claimId, file, options = {}) => {
    const formData = new FormData();
    formData.append('file', file);
    return request(`/claims/${claimId}/documents`, { method: 'POST', body: formData, ...options });
  },
  getClaimDocuments: (claimId, options = {}) => request(`/claims/${claimId}/documents`, options),
  getClaimDocumentDetail: (claimId, docId, options = {}) => request(`/claims/${claimId}/documents/${docId}`, options),
  replaceClaimDocument: (claimId, docId, file, options = {}) => {
    const formData = new FormData();
    formData.append('file', file);
    return request(`/claims/${claimId}/documents/${docId}/replace`, { method: 'POST', body: formData, ...options });
  },
  reassignClaimDocument: (claimId, docId, checklistItemId, options = {}) =>
    request(`/claims/${claimId}/documents/${docId}/reassign`, {
      method: 'POST',
      body: { checklist_item_id: checklistItemId },
      ...options,
    }),
  deleteClaimDocument: (claimId, docId, options = {}) =>
    request(`/claims/${claimId}/documents/${docId}`, { method: 'DELETE', ...options }),
    
  // Human Review Workflow
  getReviewQueue: (claimId, options = {}) => request(`/claims/${claimId}/review-queue`, options),
  submitDocumentReview: (claimId, docId, reviewData, options = {}) =>
    request(`/claims/${claimId}/documents/${docId}/review`, {
      method: 'POST',
      body: reviewData,
      ...options,
    }),
    
  // Analysis & Audit
  analyzeClaim: (claimId, options = {}) => request(`/claims/${claimId}/analyze`, { method: 'POST', ...options }),
  auditClaim: (claimId, options = {}) => request(`/claims/${claimId}/audit`, { method: 'POST', ...options }),
  
  // Reports
  generateReport: (claimId, format = 'pdf', options = {}) =>
    request(`/claims/${claimId}/report?format_type=${format}`, { method: 'POST', ...options }),
  getReportInfo: (claimId, options = {}) => request(`/claims/${claimId}/report`, options),
  downloadReport: (claimId, format = 'pdf') =>
    `${BASE_URL}/claims/${claimId}/report/download?format=${format}`,

  // Document file preview/download
  getDocumentFileUrl: (claimId, docId) =>
    `${BASE_URL}/claims/${claimId}/documents/${docId}/file`,

  // Physical Verification Workflow
  getPhysicalVerificationEligibility: (claimId, options = {}) =>
    request(`/claims/${claimId}/physical-verification/eligibility`, options),
  getPhysicalVerification: (claimId, options = {}) =>
    request(`/claims/${claimId}/physical-verification`, options),
  requestPhysicalVerification: (claimId, data = {}, options = {}) =>
    request(`/claims/${claimId}/physical-verification/request`, { method: 'POST', body: data, ...options }),
  schedulePhysicalVerification: (claimId, data, options = {}) =>
    request(`/claims/${claimId}/physical-verification/schedule`, { method: 'POST', body: data, ...options }),
  recordPhysicalVerificationOutcome: (claimId, data, options = {}) =>
    request(`/claims/${claimId}/physical-verification/outcome`, { method: 'POST', body: data, ...options }),

  // Audit History
  getAuditHistory: (claimId, options = {}) =>
    request(`/claims/${claimId}/audit-history`, options),

  // Checklist Generation Retry
  forceGenerateChecklist: (claimId, options = {}) =>
    request(`/claims/${claimId}/checklist/generate`, { method: 'POST', ...options }),
};

export { ApiError };
export default api;
