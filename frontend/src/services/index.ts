// ──────────────────────────────────────────────────────────
// OpsForge — API Services
// Replaces mock data with live FastAPI backend calls.
// Controlled by VITE_USE_MOCKS=true for offline development.
// ──────────────────────────────────────────────────────────

import { apiFetch, USE_MOCKS } from './api';
import {
  mockDeployments,
  mockIncidents,
  mockRCA,
  mockRecovery,
  mockKnowledgeEntries,
  mockPostmortem,
  mockIntegrations,
  mockMetrics,
} from '../data/mock';
import type {
  Deployment,
  Incident,
  RootCauseAnalysis,
  RecoveryAction,
  RecoveryApprovalRequest,
  KnowledgeEntry,
  Postmortem,
  Integration,
  MetricData,
  WorkflowResult,
  PipelineRequest,
  IncidentRecord,
  SimilaritySearchResult,
} from '../types';

// ---------------------------------------------------------------------------
// In-session pipeline cache: trace_id → WorkflowResult
// Allows pages to retrieve results without re-fetching.
// ---------------------------------------------------------------------------
const pipelineCache = new Map<string, WorkflowResult>();

// ---------------------------------------------------------------------------
// Pipeline / Orchestration
// ---------------------------------------------------------------------------

export const pipelineService = {
  /**
   * Run the full E2E pipeline: Plan → Deploy → RCA → Recovery Plan.
   * POST /pipeline/run → WorkflowResult (synchronous, includes all 4 stages).
   */
  async run(request: PipelineRequest): Promise<WorkflowResult> {
    if (USE_MOCKS) {
      const mock: WorkflowResult = {
        traceId: 'mock-trace-001',
        workflowStatus: 'awaiting_approval',
        stages: [
          { stage: 'PLAN',          status: 'completed', startedAt: new Date().toISOString(), durationMs: 1200 },
          { stage: 'DEPLOY',        status: 'completed', startedAt: new Date().toISOString(), durationMs: 4500 },
          { stage: 'RCA',           status: 'completed', startedAt: new Date().toISOString(), durationMs: 2200 },
          { stage: 'RECOVERY_PLAN', status: 'completed', startedAt: new Date().toISOString(), durationMs: 800 },
        ],
        appName: 'opsforge-app',
        deploymentId: 'dep-mock-001',
        incidentDetected: true,
        severity: 'high',
        rootCause: 'Database connection pool exhausted due to unclosed connections.',
        confidence: 0.94,
        recoveryActionId: 'rec-001',
        similarIncidentsFound: 2,
        startedAt: new Date().toISOString(),
        finishedAt: new Date().toISOString(),
        totalDurationMs: 8700,
      };
      pipelineCache.set(mock.traceId, mock);
      return mock;
    }

    const raw = await apiFetch<any>('/pipeline/run', {
      method: 'POST',
      body: JSON.stringify({
        description: request.description,
        dockerfile: request.dockerfile,
        repository: request.repository,
        branch: request.branch,
        simulate_failure: request.simulateFailure,
      }),
    });
    const result = normalizeWorkflowResult(raw);
    if (result.traceId) {
      pipelineCache.set(result.traceId, result);
    }
    return result;
  },

  /**
   * Get a cached or re-fetched WorkflowResult by trace_id.
   * GET /pipeline/status/{trace_id}
   */
  async getStatus(traceId: string): Promise<WorkflowResult> {
    if (pipelineCache.has(traceId)) {
      return pipelineCache.get(traceId)!;
    }
    if (USE_MOCKS) {
      throw new Error('Mock pipeline status: no cached result for ' + traceId);
    }
    const raw = await apiFetch<any>(`/pipeline/status/${encodeURIComponent(traceId)}`);
    const result = normalizeWorkflowResult(raw);
    if (result.traceId) {
      pipelineCache.set(result.traceId, result);
    }
    return result;
  },

  /** Store a result in the session cache (called externally when needed). */
  cache(result: WorkflowResult): void {
    const normalized = normalizeWorkflowResult(result);
    if (normalized.traceId) {
      pipelineCache.set(normalized.traceId, normalized);
    }
  },
};

function normalizeWorkflowResult(raw: any): WorkflowResult {
  if (!raw) return raw;
  const traceId = raw.traceId || raw.trace_id || '';
  const workflowStatus = raw.workflowStatus || raw.workflow_status || 'running';
  const stages = (raw.stages || []).map((s: any) => ({
    ...s,
    startedAt: s.startedAt || s.started_at,
    finishedAt: s.finishedAt || s.finished_at,
    durationMs: s.durationMs ?? s.duration_ms,
  }));

  return {
    ...raw,
    traceId,
    trace_id: traceId,
    workflowStatus,
    workflow_status: workflowStatus,
    stages,
    appName: raw.appName || raw.app_name,
    app_name: raw.appName || raw.app_name,
    deploymentId: raw.deploymentId || raw.deployment_id,
    deployment_id: raw.deploymentId || raw.deployment_id,
    appId: raw.appId || raw.app_id,
    app_id: raw.appId || raw.app_id,
    liveUrl: raw.liveUrl || raw.live_url,
    live_url: raw.liveUrl || raw.live_url,
    incidentDetected: raw.incidentDetected ?? raw.incident_detected,
    incident_detected: raw.incidentDetected ?? raw.incident_detected,
    severity: raw.severity,
    rootCause: raw.rootCause || raw.root_cause,
    root_cause: raw.rootCause || raw.root_cause,
    confidence: raw.confidence,
    recoveryActionId: raw.recoveryActionId || raw.recovery_action_id,
    recovery_action_id: raw.recoveryActionId || raw.recovery_action_id,
    similarIncidentsFound: raw.similarIncidentsFound ?? raw.similar_incidents_found,
    similar_incidents_found: raw.similarIncidentsFound ?? raw.similar_incidents_found,
    startedAt: raw.startedAt || raw.started_at,
    started_at: raw.startedAt || raw.started_at,
    finishedAt: raw.finishedAt || raw.finished_at,
    finished_at: raw.finishedAt || raw.finished_at,
    totalDurationMs: raw.totalDurationMs ?? raw.total_duration_ms,
    total_duration_ms: raw.totalDurationMs ?? raw.total_duration_ms,
    error: raw.error,
  };
}

// ---------------------------------------------------------------------------
// Deployment (local state management + backend for new deployments)
// ---------------------------------------------------------------------------

export const deploymentService = {
  /** Local deployment history (from session + mock seed) */
  _history: [...mockDeployments] as Deployment[],

  async getAll(): Promise<Deployment[]> {
    return Promise.resolve([...this._history]);
  },

  async getById(id: string): Promise<Deployment | undefined> {
    return Promise.resolve(this._history.find((d) => d.id === id));
  },

  /**
   * Create a new deployment record locally.
   * The real deployment is triggered via pipelineService.run().
   * This keeps a history entry for the DeploymentPlanner list.
   */
  async create(newDeployment: Omit<Deployment, 'id' | 'startedAt' | 'healthScore'>): Promise<Deployment> {
    const created: Deployment = {
      ...newDeployment,
      id: `dep-${Date.now().toString().slice(-6)}`,
      startedAt: new Date().toISOString(),
      healthScore: 100,
      logs: [
        {
          id: `l-${Date.now()}`,
          timestamp: new Date().toLocaleTimeString(),
          level: 'info',
          message: `Pipeline triggered for ${newDeployment.service}`,
        },
      ],
    };
    this._history.unshift(created);
    return Promise.resolve(created);
  },

  /** Update a deployment record (e.g. after pipeline run completes). */
  update(id: string, patch: Partial<Deployment>): void {
    const idx = this._history.findIndex((d) => d.id === id);
    if (idx !== -1) {
      this._history[idx] = { ...this._history[idx], ...patch };
    }
  },
};

// ---------------------------------------------------------------------------
// Incidents
// ---------------------------------------------------------------------------

export const incidentService = {
  async getAll(): Promise<Incident[]> {
    if (USE_MOCKS) return Promise.resolve([...mockIncidents]);
    return Promise.resolve([...mockIncidents]); // fallback: loaded from Knowledge Base
  },

  async getById(id: string): Promise<Incident | undefined> {
    if (USE_MOCKS) return Promise.resolve(mockIncidents.find((i) => i.id === id));
    return Promise.resolve(mockIncidents.find((i) => i.id === id));
  },

  async getRCA(incidentId: string): Promise<RootCauseAnalysis> {
    return Promise.resolve({ ...mockRCA, incidentId });
  },
};



// ---------------------------------------------------------------------------
// Recovery
// ---------------------------------------------------------------------------

export const recoveryService = {
  /**
   * Fetch a recovery action by ID.
   * GET /recovery/{id}
   */
  async getAction(actionId: string): Promise<RecoveryAction> {
    if (USE_MOCKS) return Promise.resolve({ ...mockRecovery, id: actionId });
    return apiFetch<RecoveryAction>(`/recovery/${encodeURIComponent(actionId)}`);
  },

  /**
   * Submit operator approval or rejection.
   * POST /recovery/{id}/approve
   */
  async approveAction(
    actionId: string,
    payload: RecoveryApprovalRequest = { approved: true, approver: 'Operator', approvalMode: 'ui' }
  ): Promise<RecoveryAction> {
    if (USE_MOCKS) return Promise.resolve({ ...mockRecovery, id: actionId, status: 'approved' });
    return apiFetch<RecoveryAction>(`/recovery/${encodeURIComponent(actionId)}/approve`, {
      method: 'POST',
      body: JSON.stringify({
        approved: payload.approved,
        approver: payload.approver ?? 'Operator',
        approval_mode: payload.approvalMode ?? 'ui',
      }),
    });
  },

  /**
   * Trigger infrastructure recovery execution.
   * POST /recovery/{id}/execute
   */
  async executeAction(actionId: string): Promise<RecoveryAction> {
    if (USE_MOCKS) return Promise.resolve({ ...mockRecovery, id: actionId, status: 'executing' });
    return apiFetch<RecoveryAction>(`/recovery/${encodeURIComponent(actionId)}/execute`, {
      method: 'POST',
    });
  },

  /**
   * Poll recovery status until terminal state.
   * GET /recovery/{id}
   */
  async pollStatus(actionId: string): Promise<RecoveryAction> {
    if (USE_MOCKS) return Promise.resolve({ ...mockRecovery, id: actionId, status: 'verified' });
    return apiFetch<RecoveryAction>(`/recovery/${encodeURIComponent(actionId)}`);
  },
};

// ---------------------------------------------------------------------------
// Knowledge / Memory (Agent 5)
// ---------------------------------------------------------------------------

export const knowledgeService = {
  /**
   * List all stored incident records.
   * GET /memory/incidents
   */
  async getAll(): Promise<KnowledgeEntry[]> {
    if (USE_MOCKS) return Promise.resolve([...mockKnowledgeEntries]);
    const records = await apiFetch<IncidentRecord[]>('/memory/incidents');
    return records.map((r) => ({
      id:            r.id,
      title:         r.rootCause,
      service:       r.appName,
      severity:      r.severity as any,
      date:          r.createdAt.split('T')[0],
      summary:       r.summary,
      tags:          r.tags,
      hasPostmortem: r.status === 'resolved',
    }));
  },

  /**
   * Semantic similarity search against stored incident embeddings.
   * POST /memory/similar
   */
  async searchSimilar(queryText: string, limit = 10): Promise<SimilaritySearchResult> {
    if (USE_MOCKS) {
      return Promise.resolve({
        query: queryText,
        totalMatches: 0,
        matches: [],
      });
    }
    return apiFetch<SimilaritySearchResult>('/memory/similar', {
      method: 'POST',
      body: JSON.stringify({ query_text: queryText, limit }),
    });
  },

  /**
   * Fetch a single incident record by ID (for Postmortem page).
   * GET /memory/incidents/{id}
   */
  async getIncidentRecord(id: string): Promise<IncidentRecord> {
    if (USE_MOCKS) throw new Error('Mock: no incident records');
    return apiFetch<IncidentRecord>(`/memory/incidents/${encodeURIComponent(id)}`);
  },

  async getPostmortem(id: string): Promise<Postmortem> {
    // Try live record first, fall back to mock postmortem
    if (USE_MOCKS) return Promise.resolve({ ...mockPostmortem, id });
    try {
      const record = await this.getIncidentRecord(id);
      return incidentRecordToPostmortem(record);
    } catch {
      return Promise.resolve({ ...mockPostmortem, id });
    }
  },

  async storeApprovedSolution(payload: {
    app_name: string;
    deployment_id: string;
    severity: string;
    root_cause: string;
    causal_chain: string[];
    summary: string;
    selected_recommendation: string;
  }) {
    if (USE_MOCKS) return Promise.resolve({ success: true, incident_id: 'INC-APPROVED' });
    return apiFetch<any>('/memory/store', {
      method: 'POST',
      body: JSON.stringify({
        deployment_id: payload.deployment_id,
        app_name: payload.app_name,
        severity: payload.severity,
        root_cause: payload.root_cause,
        causal_chain: payload.causal_chain,
        affected_signals: [],
        summary: `${payload.summary} | Selected Solution: ${payload.selected_recommendation}`,
        outcome_success: true,
      }),
    });
  },
};

export const monitoringService = {
  async start(serviceName: string, baseUrl: string) {
    if (USE_MOCKS) {
      return Promise.resolve({
        service_name: serviceName,
        base_url: baseUrl,
        health_status: 'healthy',
        incident_detected: false,
        detection_reasons: [],
        logs: [],
        metrics: [],
        events: [],
        rca_report: null,
      });
    }
    return apiFetch<any>('/monitor/start', {
      method: 'POST',
      body: JSON.stringify({
        service_name: serviceName,
        base_url: baseUrl,
      }),
    });
  },
};

/** Convert a live IncidentRecord into the Postmortem display format. */
function incidentRecordToPostmortem(record: IncidentRecord): Postmortem {
  const timeline: import('../types').TimelineEvent[] = record.causalChain.map((step, idx) => ({
    timestamp: record.createdAt,
    event: step,
    type: idx === 0 ? 'detection' : idx === record.causalChain.length - 1 ? 'resolution' : 'action',
  }));

  return {
    id:          record.id,
    incidentId:  record.id,
    title:       `${record.appName} — Incident Postmortem`,
    date:        record.createdAt.split('T')[0],
    severity:    record.severity as any,
    service:     record.appName,
    rootCause:   record.rootCause,
    impact:      record.summary,
    timeline,
    actionItems: record.selectedRecoveryAction
      ? [{
          id:       'ai-1',
          title:    record.selectedRecoveryAction,
          owner:    record.approvedBy || 'Operator',
          dueDate:  record.createdAt.split('T')[0],
          priority: 'high' as const,
          status:   record.outcome?.success ? 'done' : 'in-progress' as const,
        }]
      : [],
    generatedAt: record.updatedAt,
  };
}

// ---------------------------------------------------------------------------
// Settings / Integrations
// ---------------------------------------------------------------------------

export const authService = {
  async getRepos(): Promise<import('../types').RepositoryItem[]> {
    if (USE_MOCKS) {
      return [
        { id: 1, name: 'demo-app', fullName: 'opsforge/demo-app', defaultBranch: 'main', visibility: 'public', cloneUrl: '' },
        { id: 2, name: 'api-service', fullName: 'opsforge/api-service', defaultBranch: 'main', visibility: 'private', cloneUrl: '' },
      ];
    }
    const rawRepos = await apiFetch<any[]>('/auth/repos');
    return rawRepos.map((r) => ({
      ...r,
      fullName: r.fullName || r.full_name || r.name,
      defaultBranch: r.defaultBranch || r.default_branch || 'main',
      cloneUrl: r.cloneUrl || r.clone_url || '',
      htmlUrl: r.htmlUrl || r.html_url,
    }));
  },
  async getBranches(owner: string, repo: string): Promise<import('../types').BranchItem[]> {
    if (USE_MOCKS) {
      return [
        { name: 'main', protected: true },
        { name: 'staging', protected: false },
        { name: 'dev', protected: false },
      ];
    }
    return apiFetch<import('../types').BranchItem[]>(`/auth/repos/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}/branches`);
  },
};

export const integrationService = {
  async getAll(): Promise<Integration[]> {
    if (USE_MOCKS) return Promise.resolve([...mockIntegrations]);
    // Check backend health and overlay connection status
    try {
      const health = await apiFetch<Record<string, any>>('/health');
      return mockIntegrations.map((item) => {
        if (item.id === 'railway' && health.agents?.agent_2 === 'active') {
          return { ...item, connected: true, status: 'Connected' };
        }
        if (item.id === 'mongo' && health.agents?.agent_5 === 'active') {
          return { ...item, connected: true, status: 'Connected' };
        }
        return item;
      });
    } catch {
      return Promise.resolve([...mockIntegrations]);
    }
  },
};

// ---------------------------------------------------------------------------
// Metrics / Dashboard
// ---------------------------------------------------------------------------

export const metricsService = {
  async getMetrics(): Promise<MetricData[]> {
    if (USE_MOCKS) return Promise.resolve([...mockMetrics]);
    try {
      const [health, incidents] = await Promise.all([
        apiFetch<Record<string, any>>('/health'),
        apiFetch<IncidentRecord[]>('/memory/incidents').catch(() => [] as IncidentRecord[]),
      ]);
      const openCount = incidents.filter(
        (i) => i.status === 'open' || i.status === 'investigating'
      ).length;
      const resolvedCount = incidents.filter((i) => i.status === 'resolved').length;

      const allHealthy = Object.values(health.agents || {}).every((v) => v === 'active');

      return [
        {
          label: 'Pipeline Status',
          value: health.pipeline === 'active' ? 'Active' : 'Offline',
          icon: 'rocket',
          trend: 'flat',
          badge: health.pipeline === 'active'
            ? { text: 'LIVE', variant: 'success' }
            : { text: 'OFFLINE', variant: 'error' },
        },
        {
          label: 'Open Incidents',
          value: openCount,
          icon: 'warning',
          badge: openCount === 0
            ? { text: 'HEALTHY', variant: 'success' }
            : { text: 'ACTIVE', variant: 'warning' },
        },
        {
          label: 'Resolved Incidents',
          value: resolvedCount,
          icon: 'check_circle',
          trend: 'up',
        },
        {
          label: 'System Health',
          value: allHealthy ? '99.9' : '—',
          unit: allHealthy ? '%' : '',
          icon: 'monitor_heart',
          trend: allHealthy ? 'flat' : 'down',
        },
      ];
    } catch {
      return Promise.resolve([...mockMetrics]);
    }
  },
};

// Re-export types used by pages
export type { Incident };
export type { IncidentRecord };
