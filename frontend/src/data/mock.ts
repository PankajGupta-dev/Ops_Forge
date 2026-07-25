// ──────────────────────────────────────────────────────────
// OpsForge — Mock Data
// ──────────────────────────────────────────────────────────
import type {
  Deployment, Incident, RootCauseAnalysis, RecoveryAction,
  KnowledgeEntry, Postmortem, Integration, MetricData,
} from '../types';

export const mockDeployments: Deployment[] = [
  {
    id: 'dep-001', service: 'api-gateway', version: 'v2.4.1',
    environment: 'production', status: 'healthy',
    startedAt: '2024-01-15T08:30:00Z', duration: '4m 12s',
    commit: 'a3f8e2c', branch: 'main', deployedBy: 'ops-bot',
    healthScore: 99,
    logs: [
      { id: 'l1', timestamp: '08:30:01', level: 'info', message: 'Deployment initiated for api-gateway v2.4.1' },
      { id: 'l2', timestamp: '08:30:15', level: 'info', message: 'Docker image pulled successfully' },
      { id: 'l3', timestamp: '08:31:02', level: 'info', message: 'Rolling update started — 0/3 replicas updated' },
      { id: 'l4', timestamp: '08:32:44', level: 'info', message: 'Rolling update complete — 3/3 replicas healthy' },
      { id: 'l5', timestamp: '08:34:13', level: 'info', message: 'Health checks passing. Deployment finalized.' },
    ],
  },
  {
    id: 'dep-002', service: 'auth-service', version: 'v1.9.0',
    environment: 'production', status: 'healthy',
    startedAt: '2024-01-15T09:15:00Z', duration: '3m 40s',
    commit: 'b72d1a9', branch: 'main', deployedBy: 'ops-bot',
    healthScore: 98,
    logs: [
      { id: 'l1', timestamp: '09:15:00', level: 'info', message: 'Deployment initiated for auth-service v1.9.0' },
      { id: 'l2', timestamp: '09:17:10', level: 'info', message: 'Canary rollout: 10% traffic routed' },
      { id: 'l3', timestamp: '09:18:40', level: 'info', message: 'Canary healthy. Full rollout started.' },
    ],
  },
  {
    id: 'dep-003', service: 'payment-processor', version: 'v3.1.0-beta',
    environment: 'staging', status: 'deploying',
    startedAt: '2024-01-15T10:00:00Z',
    commit: 'c91b4f2', branch: 'feat/payment-v3', deployedBy: 'ci-pipeline',
    healthScore: 72,
    logs: [
      { id: 'l1', timestamp: '10:00:01', level: 'info', message: 'Deployment initiated for payment-processor v3.1.0-beta' },
      { id: 'l2', timestamp: '10:00:30', level: 'warn', message: 'Image scan: 2 low-severity vulnerabilities detected' },
      { id: 'l3', timestamp: '10:01:15', level: 'info', message: 'Deploying to staging cluster...' },
    ],
  },
  {
    id: 'dep-004', service: 'notification-svc', version: 'v0.8.3',
    environment: 'production', status: 'failed',
    startedAt: '2024-01-14T22:00:00Z', duration: '1m 03s',
    commit: 'd04c77e', branch: 'hotfix/notif-crash', deployedBy: 'ops-bot',
    healthScore: 0,
    logs: [
      { id: 'l1', timestamp: '22:00:01', level: 'info', message: 'Deployment initiated for notification-svc v0.8.3' },
      { id: 'l2', timestamp: '22:00:45', level: 'error', message: 'Container failed to start: OOMKilled (exit code 137)' },
      { id: 'l3', timestamp: '22:01:03', level: 'error', message: 'Deployment failed. Rolling back to v0.8.2.' },
    ],
  },
  {
    id: 'dep-005', service: 'data-pipeline', version: 'v5.2.0',
    environment: 'production', status: 'healthy',
    startedAt: '2024-01-15T07:00:00Z', duration: '6m 18s',
    commit: 'e55a3d1', branch: 'main', deployedBy: 'ops-bot',
    healthScore: 100,
    logs: [],
  },
];

export const mockIncidents: Incident[] = [
  {
    id: 'INC-2024-001', title: 'API Gateway 503 Errors — EU Region',
    description: 'Elevated 503 response rates detected on api-gateway nodes in eu-west-1. Error rate peaked at 34%.',
    severity: 'critical', status: 'resolved',
    service: 'api-gateway', environment: 'production',
    openedAt: '2024-01-14T03:12:00Z', resolvedAt: '2024-01-14T03:47:00Z', mttr: '35m',
    tags: ['api-gateway', 'eu-west-1', 'latency'],
  },
  {
    id: 'INC-2024-002', title: 'Auth Service Token Expiry Loop',
    description: 'JWT tokens being invalidated prematurely due to clock drift between auth-service pods.',
    severity: 'high', status: 'resolved',
    service: 'auth-service', environment: 'production',
    openedAt: '2024-01-12T14:22:00Z', resolvedAt: '2024-01-12T15:08:00Z', mttr: '46m',
    tags: ['auth', 'jwt', 'clock-drift'],
  },
  {
    id: 'INC-2024-003', title: 'Payment Processor Memory Spike',
    description: 'OOM events on payment-processor nodes causing cascading restarts.',
    severity: 'critical', status: 'investigating',
    service: 'payment-processor', environment: 'production',
    openedAt: '2024-01-15T10:45:00Z',
    tags: ['payment', 'memory', 'oom'],
  },
  {
    id: 'INC-2024-004', title: 'Data Pipeline Ingestion Lag',
    description: 'Kafka consumer group falling behind — 15-minute lag on main topic.',
    severity: 'medium', status: 'open',
    service: 'data-pipeline', environment: 'production',
    openedAt: '2024-01-15T09:30:00Z',
    tags: ['kafka', 'pipeline', 'lag'],
  },
  {
    id: 'INC-2024-005', title: 'Notification Service Crash Loop',
    description: 'Container crash loop detected post-deploy. OOMKilled on startup.',
    severity: 'high', status: 'resolved',
    service: 'notification-svc', environment: 'production',
    openedAt: '2024-01-14T22:00:00Z', resolvedAt: '2024-01-14T22:40:00Z', mttr: '40m',
    tags: ['notification', 'oom', 'deploy'],
  },
];

export const mockRCA: RootCauseAnalysis = {
  incidentId: 'INC-2024-003',
  summary: 'Memory leak in payment-processor v3.0.9 due to unclosed database connections in the transaction reconciliation worker.',
  confidence: 94,
  generatedAt: '2024-01-15T11:02:00Z',
  narrative: `OpsForge AI detected a consistent memory growth pattern starting at 10:42 UTC, correlating with a spike in transaction reconciliation jobs. Analysis of heap dumps confirms that the reconciliation worker in payment-processor v3.0.9 fails to release PostgreSQL connection pool objects after timeout events, resulting in a progressive memory leak. Under sustained load, this triggers OOMKill at approximately 45-minute intervals. The fix requires patching the connection pool teardown logic in the reconciliation worker and setting explicit connection lifetime limits.`,
  nodes: [
    { id: 'n1', label: 'High Txn Load', type: 'trigger', icon: 'trending_up' },
    { id: 'n2', label: 'Reconciliation Worker', type: 'logic', icon: 'settings' },
    { id: 'n3', label: 'DB Pool Leak', type: 'logic', icon: 'leak_add' },
    { id: 'n4', label: 'Memory Exhaustion', type: 'impact', icon: 'memory' },
    { id: 'n5', label: 'OOMKill + Restart', type: 'impact', icon: 'dangerous' },
  ],
  edges: [
    { from: 'n1', to: 'n2', dashed: false },
    { from: 'n2', to: 'n3', dashed: false },
    { from: 'n3', to: 'n4', dashed: false },
    { from: 'n4', to: 'n5', dashed: false },
  ],
};

export const mockRecovery: RecoveryAction = {
  id: 'rec-001', incidentId: 'INC-2024-003',
  title: 'Rollback payment-processor to v3.0.8 + connection pool patch',
  description: 'Immediate rollback to the last stable version, followed by applying the connection pool configuration patch.',
  riskLevel: 'medium', status: 'pending',
  estimatedDuration: '8–12 minutes',
  steps: [
    { id: 's1', order: 1, title: 'Scale down payment-processor to 0 replicas', command: 'kubectl scale deploy/payment-processor --replicas=0 -n production', status: 'pending' },
    { id: 's2', order: 2, title: 'Roll back image to v3.0.8', command: 'kubectl set image deploy/payment-processor app=registry/payment-processor:v3.0.8 -n production', status: 'pending' },
    { id: 's3', order: 3, title: 'Apply connection pool config patch', command: 'kubectl apply -f patches/payment-processor-pool-config.yaml', status: 'pending' },
    { id: 's4', order: 4, title: 'Scale back up to 3 replicas', command: 'kubectl scale deploy/payment-processor --replicas=3 -n production', status: 'pending' },
    { id: 's5', order: 5, title: 'Verify health checks pass (wait 120s)', command: 'kubectl rollout status deploy/payment-processor -n production --timeout=120s', status: 'pending' },
  ],
};

export const mockKnowledgeEntries: KnowledgeEntry[] = [
  { id: 'k1', title: 'API Gateway 503 Errors — EU Region', service: 'api-gateway', severity: 'critical', date: '2024-01-14', summary: 'Load balancer health check misconfiguration after deploy.', tags: ['api-gateway', 'eu-west-1'], hasPostmortem: true },
  { id: 'k2', title: 'Auth Service Token Expiry Loop', service: 'auth-service', severity: 'high', date: '2024-01-12', summary: 'Clock drift between auth pods causing JWT invalidation.', tags: ['auth', 'jwt'], hasPostmortem: true },
  { id: 'k3', title: 'Notification Crash Loop', service: 'notification-svc', severity: 'high', date: '2024-01-14', summary: 'OOM on startup due to excessive pre-load caching.', tags: ['notification', 'oom'], hasPostmortem: false },
  { id: 'k4', title: 'Data Pipeline Kafka Lag', service: 'data-pipeline', severity: 'medium', date: '2024-01-15', summary: 'Consumer group lag under high ingestion load.', tags: ['kafka', 'pipeline'], hasPostmortem: false },
  { id: 'k5', title: 'DB Connection Pool Exhaustion', service: 'user-service', severity: 'high', date: '2024-01-10', summary: 'pgBouncer pool size too small for peak traffic.', tags: ['database', 'postgres'], hasPostmortem: true },
];

export const mockPostmortem: Postmortem = {
  id: 'pm-001', incidentId: 'INC-2024-001',
  title: 'API Gateway 503 Errors — EU Region — Postmortem',
  date: '2024-01-14', severity: 'critical', service: 'api-gateway',
  rootCause: 'A misconfigured load balancer health check endpoint (/health → /healthz) caused all newly deployed pods to be marked unhealthy, draining the pool during a rolling deployment.',
  impact: '34% of EU-region API requests returned 503 for 35 minutes. Estimated ~12,000 failed requests. No data loss. Payment flows unaffected (routed via redundant region).',
  timeline: [
    { timestamp: '03:12 UTC', event: 'Alert triggered: 503 error rate > 5% on api-gateway eu-west-1', type: 'detection' },
    { timestamp: '03:15 UTC', event: 'On-call engineer paged. OpsForge begins RCA analysis.', type: 'escalation' },
    { timestamp: '03:22 UTC', event: 'OpsForge identifies health check misconfiguration with 91% confidence.', type: 'action' },
    { timestamp: '03:28 UTC', event: 'Recovery approved: revert health check path. Executing rollback.', type: 'action' },
    { timestamp: '03:47 UTC', event: 'All pods healthy. Error rate returns to baseline. Incident resolved.', type: 'resolution' },
  ],
  actionItems: [
    { id: 'ai1', title: 'Add health check path validation to CI/CD pipeline', owner: 'Platform Team', dueDate: '2024-01-21', priority: 'high', status: 'in-progress' },
    { id: 'ai2', title: 'Configure cross-region failover for EU API Gateway', owner: 'Infra Team', dueDate: '2024-01-28', priority: 'high', status: 'open' },
    { id: 'ai3', title: 'Write runbook for load balancer health check failures', owner: 'SRE Team', dueDate: '2024-01-25', priority: 'medium', status: 'open' },
  ],
  generatedAt: '2024-01-14T08:00:00Z',
};

export const mockIntegrations: Integration[] = [
  { id: 'github',   name: 'GitHub',       icon: 'code',            connected: true,  status: 'Connected', account: 'opsforge-org' },
  { id: 'railway',  name: 'Railway',      icon: 'cloud',           connected: true,  status: 'Connected', account: 'opsforge-railway-prod' },
  { id: 'mongo',    name: 'MongoDB Atlas',icon: 'storage',         connected: false },
  { id: 'eleven',   name: 'ElevenLabs',   icon: 'record_voice_over', connected: false },
  { id: 'slack',    name: 'Slack',        icon: 'chat',            connected: false },
  { id: 'pagerduty',name: 'PagerDuty',   icon: 'notifications_active', connected: false },
];

export const mockMetrics: MetricData[] = [
  { label: 'Active Deployments', value: 12, icon: 'rocket', trend: 'up' },
  { label: 'Open Incidents', value: 0, icon: 'warning', badge: { text: 'HEALTHY', variant: 'success' } },
  { label: 'MTTR (30d)', value: '14', unit: 'm', icon: 'timer', trend: 'down' },
  { label: 'System Health', value: '99.9', unit: '%', icon: 'monitor_heart', trend: 'flat' },
];
