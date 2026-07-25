// ──────────────────────────────────────────────────────────
// OpsForge — Shared TypeScript Types
// Aligned with FastAPI backend Pydantic schemas (camelCase via alias_generator)
// ──────────────────────────────────────────────────────────

// ── Primitive enums ───────────────────────────────────────

export type DeploymentStatus =
  | 'healthy'
  | 'deploying'
  | 'degraded'
  | 'failed'
  | 'pending'
  | 'rolled-back'
  | 'active'
  | 'success'
  | 'building';

export type IncidentSeverity   = 'critical' | 'high' | 'medium' | 'low' | 'info';
export type IncidentStatus     = 'open' | 'investigating' | 'resolved' | 'closed';
export type RecoveryStatus     = 'pending' | 'approval_pending' | 'approved' | 'executing' | 'verifying' | 'verified' | 'failed' | 'rejected';
export type StageStatus        = 'pending' | 'running' | 'completed' | 'skipped' | 'failed';
export type WorkflowStatus     = 'running' | 'awaiting_approval' | 'completed' | 'failed';

// ── Deployment (frontend-local model, used for list/history display) ─────────

export interface Deployment {
  id:          string;
  service:     string;
  version:     string;
  environment: 'production' | 'staging' | 'development';
  status:      DeploymentStatus;
  startedAt:   string;
  duration?:   string;
  commit:      string;
  branch:      string;
  deployedBy:  string;
  healthScore: number;
  logs?:       LogEntry[];
  traceId?:    string; // pipeline trace_id for linking to WorkflowResult
}

export interface Incident {
  id:          string;
  title:       string;
  description: string;
  severity:    string;
  status:      string;
  service:     string;
  environment: string;
  openedAt:    string;
  resolvedAt?: string;
  mttr?:       string;
  tags:        string[];
}

export interface LogEntry {
  id:        string;
  timestamp: string;
  level:     'info' | 'warn' | 'error' | 'debug';
  message:   string;
}

// ── Pipeline (matches backend orchestration.py) ───────────────────────────────

export interface PipelineRequest {
  description:     string;
  dockerfile:      string;
  simulateFailure: boolean;
}

export interface StageResult {
  stage:       string;
  status:      StageStatus;
  startedAt:   string;
  finishedAt?: string;
  durationMs?: number;
  data?:       Record<string, any>;
  error?:      string;
}

export interface WorkflowResult {
  traceId:              string;
  workflowStatus:       WorkflowStatus;
  stages:               StageResult[];
  appName?:             string;
  deploymentId?:        string;
  appId?:               string;
  liveUrl?:             string;
  incidentDetected?:    boolean;
  severity?:            string;
  rootCause?:           string;
  confidence?:          number;
  recoveryActionId?:    string;
  similarIncidentsFound?: number;
  startedAt:            string;
  finishedAt?:          string;
  totalDurationMs?:     number;
  error?:               string;
}

// ── Incident (backend: IncidentReport from incident.py) ──────────────────────

export interface RecoveryRecommendation {
  rank:                 number;
  category:             string;
  action:               string;
  rationale:            string;
  risk:                 string;
  estimatedTtmMinutes?: number;
  targetDeploymentId?:  string;
}

export interface IncidentReport {
  traceId?:            string;
  appId?:              string;
  deploymentId:        string;
  appName:             string;
  incidentStatus:      IncidentStatus;
  severity:            IncidentSeverity;
  rootCause:           string;
  causalChain:         string[];
  affectedSignals:     string[];
  contributingFactors: string[];
  recommendations:     RecoveryRecommendation[];
  confidence:          number;
  summary:             string;
  warnings:            string[];
  similarIncidents:    Record<string, any>[];
}

// ── RCA (frontend causal-chain visualiser) ────────────────────────────────────

export interface CausalNode {
  id:    string;
  label: string;
  type:  'trigger' | 'logic' | 'impact' | 'action';
  icon:  string;
}

export interface CausalEdge {
  from:   string;
  to:     string;
  dashed: boolean;
}

export interface RootCauseAnalysis {
  incidentId:  string;
  summary:     string;
  confidence:  number; // 0-100
  nodes:       CausalNode[];
  edges:       CausalEdge[];
  narrative:   string;
  generatedAt: string;
}

// ── Recovery (matches backend recovery.py) ────────────────────────────────────

export interface RecoveryStep {
  id:        string;
  order:     number;
  title:     string;
  command?:  string;
  verified?: boolean;
  status:    string; // pending | running | completed | failed
}

export interface RecoveryAction {
  id:                string;
  traceId?:          string;
  appId?:            string;
  deploymentId?:     string;
  incidentId:        string;
  title:             string;
  description:       string;
  steps:             RecoveryStep[];
  riskLevel:         'low' | 'medium' | 'high';
  status:            RecoveryStatus;
  estimatedDuration: string;
  approvedBy?:       string;
  executedAt?:       string;
  narrative?:        string;
  audioUrl?:         string;
  incidentRecordId?: string;
}

export interface RecoveryApprovalRequest {
  approved:      boolean;
  approver?:     string;
  approvalMode?: string;
}

// ── Knowledge / Memory (matches backend knowledge.py) ────────────────────────

export interface IncidentOutcome {
  success:                boolean;
  resolutionTimeSeconds?: number;
  verificationDetails:    Record<string, any>;
  operatorNotes?:         string;
  resolvedAt?:            string;
}

export interface IncidentRecord {
  id:                    string;
  deploymentId:          string;
  appName:               string;
  severity:              IncidentSeverity;
  status:                IncidentStatus;
  rootCause:             string;
  causalChain:           string[];
  affectedSignals:       string[];
  selectedRecoveryAction?: string;
  recoveryCategory?:     string;
  recoveryStatus?:       RecoveryStatus;
  approvedBy?:           string;
  approvalMode?:         string;
  outcome?:              IncidentOutcome;
  summary:               string;
  tags:                  string[];
  createdAt:             string;
  updatedAt:             string;
}

export interface SimilarityMatch {
  incidentId:          string;
  appName:             string;
  rootCause:           string;
  recoveryAction?:     string;
  recoveryCategory?:   string;
  outcomeSuccess:      boolean;
  similarityScore:     number;
  similarityPercentage: number;
  explanation:         string;
  createdAt:           string;
}

export interface SimilaritySearchResult {
  query:        string;
  totalMatches: number;
  topMatch?:    SimilarityMatch;
  matches:      SimilarityMatch[];
}

// ── Knowledge Base (frontend display) ────────────────────────────────────────

export interface KnowledgeEntry {
  id:            string;
  title:         string;
  service:       string;
  severity:      IncidentSeverity;
  date:          string;
  summary:       string;
  tags:          string[];
  hasPostmortem: boolean;
}

// ── Postmortem ────────────────────────────────────────────

export interface TimelineEvent {
  timestamp: string;
  event:     string;
  type:      'detection' | 'escalation' | 'action' | 'resolution';
}

export interface ActionItem {
  id:       string;
  title:    string;
  owner:    string;
  dueDate:  string;
  priority: 'high' | 'medium' | 'low';
  status:   'open' | 'in-progress' | 'done';
}

export interface Postmortem {
  id:          string;
  incidentId:  string;
  title:       string;
  date:        string;
  severity:    IncidentSeverity;
  service:     string;
  timeline:    TimelineEvent[];
  rootCause:   string;
  impact:      string;
  actionItems: ActionItem[];
  generatedAt: string;
}

// ── Settings / Integrations ───────────────────────────────

export interface Integration {
  id:        string;
  name:      string;
  icon:      string;
  connected: boolean;
  status?:   string;
  account?:  string;
}

export interface MetricData {
  label:   string;
  value:   string | number;
  unit?:   string;
  icon:    string;
  trend?:  'up' | 'down' | 'flat';
  badge?:  { text: string; variant: 'success' | 'warning' | 'error' };
}
