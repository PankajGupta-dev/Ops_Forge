// ──────────────────────────────────────────────────────────
// OpsForge — Shared TypeScript Types
// ──────────────────────────────────────────────────────────

export type DeploymentStatus =
  | 'healthy'
  | 'deploying'
  | 'degraded'
  | 'failed'
  | 'pending'
  | 'rolled-back';

export type IncidentSeverity = 'critical' | 'high' | 'medium' | 'low';
export type IncidentStatus   = 'open' | 'investigating' | 'resolved' | 'closed';
export type RecoveryStatus   = 'pending' | 'approved' | 'executing' | 'verified' | 'rejected';

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
}

export interface LogEntry {
  id:        string;
  timestamp: string;
  level:     'info' | 'warn' | 'error' | 'debug';
  message:   string;
}

export interface Incident {
  id:          string;
  title:       string;
  description: string;
  severity:    IncidentSeverity;
  status:      IncidentStatus;
  service:     string;
  environment: string;
  openedAt:    string;
  resolvedAt?: string;
  mttr?:       string;
  tags:        string[];
}

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

export interface RecoveryAction {
  id:          string;
  incidentId:  string;
  title:       string;
  description: string;
  steps:       RecoveryStep[];
  riskLevel:   'low' | 'medium' | 'high';
  status:      RecoveryStatus;
  estimatedDuration: string;
  approvedBy?: string;
  executedAt?: string;
}

export interface RecoveryStep {
  id:          string;
  order:       number;
  title:       string;
  command?:    string;
  verified?:   boolean;
}

export interface KnowledgeEntry {
  id:          string;
  title:       string;
  service:     string;
  severity:    IncidentSeverity;
  date:        string;
  summary:     string;
  tags:        string[];
  hasPostmortem: boolean;
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

export interface TimelineEvent {
  timestamp: string;
  event:     string;
  type:      'detection' | 'escalation' | 'action' | 'resolution';
}

export interface ActionItem {
  id:        string;
  title:     string;
  owner:     string;
  dueDate:   string;
  priority:  'high' | 'medium' | 'low';
  status:    'open' | 'in-progress' | 'done';
}

export interface Integration {
  id:        string;
  name:      string;
  icon:      string;
  connected: boolean;
  status?:   string;
  account?:  string;
}

export interface MetricData {
  label:       string;
  value:       string | number;
  unit?:       string;
  icon:        string;
  trend?:      'up' | 'down' | 'flat';
  badge?:      { text: string; variant: 'success' | 'warning' | 'error' };
}
