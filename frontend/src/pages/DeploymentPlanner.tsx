import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Button from '../components/ui/Button';
import DataTable from '../components/ui/DataTable';
import StatusBadge from '../components/ui/StatusBadge';
import { deploymentService, pipelineService, authService, monitoringService } from '../services';
import type { Deployment, RepositoryItem, BranchItem } from '../types';

const DEFAULT_DOCKERFILE = `FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]`;

export default function DeploymentPlanner() {
  const navigate = useNavigate();
  const [deployments, setDeployments] = useState<Deployment[]>([]);
  const [mode, setMode] = useState<'monitor' | 'pipeline'>('monitor');

  // Monitor URL Mode State
  const [monitorServiceName, setMonitorServiceName] = useState('checkout-system');
  const [monitorBaseUrl, setMonitorBaseUrl] = useState('https://checkout-system-production-ecd6.up.railway.app');
  const [monitorResult, setMonitorResult] = useState<any>(null);
  const [isMonitoring, setIsMonitoring] = useState(false);

  const [description, setDescription] = useState('');
  const [dockerfile, setDockerfile] = useState(DEFAULT_DOCKERFILE);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [service, setService] = useState('api-gateway');
  const [environment, setEnvironment] = useState<'production' | 'staging' | 'development'>('production');
  const [version, setVersion] = useState('v2.5.0');
  const [simulateFailure, setSimulateFailure] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // GitHub Repositories & Branches state
  const [repos, setRepos] = useState<RepositoryItem[]>([]);
  const [selectedRepo, setSelectedRepo] = useState<string>('');
  const [branches, setBranches] = useState<BranchItem[]>([]);
  const [selectedBranch, setSelectedBranch] = useState<string>('main');
  const [isLoadingRepos, setIsLoadingRepos] = useState(false);
  const [isLoadingBranches, setIsLoadingBranches] = useState(false);

  useEffect(() => {
    deploymentService.getAll().then(setDeployments);

    setIsLoadingRepos(true);
    authService.getRepos()
      .then((data) => {
        setRepos(data);
        if (data.length > 0) {
          const firstRepoName = data[0].fullName || data[0].full_name || data[0].name;
          const firstRepoBranch = data[0].defaultBranch || data[0].default_branch || 'main';
          setSelectedRepo(firstRepoName);
          setSelectedBranch(firstRepoBranch);
        }
      })
      .catch((err) => {
        console.error('Failed to fetch user repositories:', err);
      })
      .finally(() => setIsLoadingRepos(false));
  }, []);

  useEffect(() => {
    if (!selectedRepo || !selectedRepo.includes('/')) return;
    const [owner, repoName] = selectedRepo.split('/');
    setIsLoadingBranches(true);
    authService.getBranches(owner, repoName)
      .then((data) => {
        setBranches(data);
        if (data.length > 0) {
          setSelectedBranch(data[0].name);
        }
      })
      .catch((err) => {
        console.error('Failed to fetch repository branches:', err);
        setBranches([{ name: 'main', protected: false }]);
        setSelectedBranch('main');
      })
      .finally(() => setIsLoadingBranches(false));
  }, [selectedRepo]);

  const handleStartMonitor = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!monitorServiceName.trim() || !monitorBaseUrl.trim()) {
      setError('Please provide service name and application URL.');
      return;
    }
    setError(null);
    setIsMonitoring(true);
    try {
      const res = await monitoringService.start(monitorServiceName, monitorBaseUrl);
      setMonitorResult(res);

      // Create a local deployment history entry
      await deploymentService.create({
        service: monitorServiceName,
        environment: 'production',
        branch: 'main',
        version: 'v1.0.0',
        status: res.incident_detected ? 'failed' : 'healthy',
        commit: 'live-url',
        deployedBy: 'AI Incident Commander',
      });

    } catch (err: any) {
      setError(err?.message ?? 'Failed to analyze application URL.');
    } finally {
      setIsMonitoring(false);
    }
  };

  const handleDeploy = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!description.trim()) {
      setError('Please enter a deployment description.');
      return;
    }
    if (!dockerfile.trim()) {
      setError('Please provide a Dockerfile.');
      return;
    }
    setError(null);
    setIsSubmitting(true);

    try {
      const localDep = await deploymentService.create({
        service: selectedRepo ? selectedRepo.split('/')[1] : service,
        environment,
        branch: selectedBranch,
        version,
        status: 'deploying',
        commit: Math.random().toString(36).substring(2, 9),
        deployedBy: 'ops-engineer',
      });

      const result = await pipelineService.run({
        description,
        dockerfile,
        repository: selectedRepo,
        branch: selectedBranch,
        simulateFailure,
      });

      const traceId = result.traceId || result.trace_id;
      const status = (result.workflowStatus || result.workflow_status) === 'failed' ? 'failed' : 'healthy';

      deploymentService.update(localDep.id, {
        traceId,
        status,
      });

      if (status === 'failed' || result.error) {
        setError(result.error || 'Pipeline execution failed during stage run.');
        setIsSubmitting(false);
        return;
      }

      if (!traceId || traceId === 'undefined') {
        setError('Pipeline execution returned invalid trace_id.');
        setIsSubmitting(false);
        return;
      }

      navigate(`/deployments/${traceId}`);
    } catch (err: any) {
      setError(err?.message ?? 'Pipeline failed to start. Is the backend running?');
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Page Header */}
      <div>
        <h1 className="font-headline text-headline-md text-on-surface">AI Incident Commander</h1>
        <p className="font-body text-body-md text-on-surface-variant">
          Autonomous Telemetry Collection, Rule Detection, Gemini RCA &amp; Knowledge Memory Integration
        </p>
      </div>

      {/* Mode Selector Tabs */}
      <div className="flex gap-3">
        <button
          onClick={() => setMode('monitor')}
          className={`px-4 py-2 rounded-md font-mono text-mono-data text-sm font-medium border transition-colors flex items-center gap-2 ${
            mode === 'monitor'
              ? 'bg-primary/20 border-primary text-primary'
              : 'bg-surface-container border-border-subtle text-on-surface-variant hover:text-on-surface'
          }`}
        >
          <span className="material-symbols-outlined text-[18px]">monitor_heart</span>
          Monitor App URL (AI Incident Commander)
        </button>
        <button
          onClick={() => setMode('pipeline')}
          className={`px-4 py-2 rounded-md font-mono text-mono-data text-sm font-medium border transition-colors flex items-center gap-2 ${
            mode === 'pipeline'
              ? 'bg-primary/20 border-primary text-primary'
              : 'bg-surface-container border-border-subtle text-on-surface-variant hover:text-on-surface'
          }`}
        >
          <span className="material-symbols-outlined text-[18px]">rocket_launch</span>
          Deployment Pipeline
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* ── Form Panel ─────────────────────────────────── */}
        <div className="lg:col-span-5 bg-surface-container-lowest border border-border-subtle rounded-md p-6 flex flex-col gap-5">
          {mode === 'monitor' ? (
            <>
              <h2 className="font-headline text-headline-sm text-on-surface flex items-center gap-2">
                <span className="material-symbols-outlined text-primary text-[20px]">monitor_heart</span>
                Monitor Pre-Deployed Service
              </h2>
              <form onSubmit={handleStartMonitor} className="flex flex-col gap-4">
                <div>
                  <label className="label-caps block mb-1">Service Name *</label>
                  <input
                    type="text"
                    value={monitorServiceName}
                    onChange={(e) => setMonitorServiceName(e.target.value)}
                    className="input-base w-full"
                    placeholder="e.g. checkout-system"
                    required
                  />
                </div>

                <div>
                  <label className="label-caps block mb-1">Application URL (base_url) *</label>
                  <input
                    type="url"
                    value={monitorBaseUrl}
                    onChange={(e) => setMonitorBaseUrl(e.target.value)}
                    className="input-base w-full font-mono text-sm"
                    placeholder="https://checkout-system-production-ecd6.up.railway.app"
                    required
                  />
                </div>

                {error && (
                  <div className="p-3 bg-risk-red/10 border border-risk-red/30 rounded-md font-mono text-xs text-risk-red">
                    {error}
                  </div>
                )}

                <Button variant="primary" icon="search" loading={isMonitoring} className="w-full mt-2">
                  Analyze &amp; Detect Incidents
                </Button>
              </form>
            </>
          ) : (
            <>
              <h2 className="font-headline text-headline-sm text-on-surface flex items-center gap-2">
                <span className="material-symbols-outlined text-primary text-[20px]">rocket_launch</span>
                New Pipeline Run
              </h2>

          <form onSubmit={handleDeploy} className="flex flex-col gap-4">
            {/* Repository Dropdown */}
            <div>
              <label className="label-caps block mb-1">Repository *</label>
              <select
                value={selectedRepo}
                onChange={(e) => setSelectedRepo(e.target.value)}
                className="input-base w-full"
                disabled={isLoadingRepos}
              >
                {isLoadingRepos ? (
                  <option value="">Loading repositories…</option>
                ) : repos.length === 0 ? (
                  <option value="opsforge/demo-app">opsforge/demo-app (Default)</option>
                ) : (
                  repos.map((r) => {
                    const repoFullName = r.fullName || r.full_name || r.name;
                    return (
                      <option key={r.id} value={repoFullName}>
                        {repoFullName} ({r.visibility})
                      </option>
                    );
                  })
                )}
              </select>
            </div>

            {/* Branch Dropdown */}
            <div>
              <label className="label-caps block mb-1">Branch *</label>
              <select
                value={selectedBranch}
                onChange={(e) => setSelectedBranch(e.target.value)}
                className="input-base w-full"
                disabled={isLoadingBranches}
              >
                {isLoadingBranches ? (
                  <option value="">Loading branches…</option>
                ) : branches.length === 0 ? (
                  <option value="main">main</option>
                ) : (
                  branches.map((b) => (
                    <option key={b.name} value={b.name}>
                      {b.name} {b.protected ? '🔒' : ''}
                    </option>
                  ))
                )}
              </select>
            </div>

            {/* Description */}
            <div>
              <label className="label-caps block mb-1">Deployment Description *</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="input-base w-full h-24 resize-none font-mono text-sm"
                placeholder="e.g. Deploy Node.js auth service with Redis session store and autoscaling enabled"
                required
              />
            </div>

            {/* Dockerfile */}
            <div>
              <label className="label-caps block mb-1">Dockerfile *</label>
              <textarea
                value={dockerfile}
                onChange={(e) => setDockerfile(e.target.value)}
                className="input-base w-full h-44 resize-y font-mono text-xs leading-relaxed"
                placeholder="FROM node:20-alpine&#10;WORKDIR /app&#10;..."
                required
              />
            </div>

            {/* Simulate Failure Toggle */}
            <div className="flex items-center justify-between p-3 bg-surface-container rounded-md border border-border-subtle">
              <div>
                <p className="font-mono text-mono-data text-on-surface font-medium text-sm">Simulate Failure & RCA</p>
                <p className="font-mono text-[11px] text-on-surface-variant">
                  Inject controlled failure telemetry to trigger the full incident pipeline
                </p>
              </div>
              <input
                type="checkbox"
                checked={simulateFailure}
                onChange={(e) => setSimulateFailure(e.target.checked)}
                className="w-4 h-4 accent-primary rounded cursor-pointer"
              />
            </div>

            {/* Advanced Options */}
            <div>
              <button
                type="button"
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="flex items-center gap-2 font-mono text-mono-data text-on-surface-variant hover:text-primary transition-colors text-sm"
              >
                <span className={`material-symbols-outlined text-[16px] transition-transform ${showAdvanced ? 'rotate-90' : ''}`}>
                  chevron_right
                </span>
                Advanced Options
              </button>

              {showAdvanced && (
                <div className="mt-4 flex flex-col gap-4 p-4 bg-surface-container rounded-md border border-border-subtle">
                  {/* Service Name */}
                  <div>
                    <label className="label-caps block mb-1">Target Service</label>
                    <select
                      value={service}
                      onChange={(e) => setService(e.target.value)}
                      className="input-base"
                    >
                      <option value="api-gateway">api-gateway</option>
                      <option value="auth-service">auth-service</option>
                      <option value="payment-processor">payment-processor</option>
                      <option value="notification-svc">notification-svc</option>
                      <option value="data-pipeline">data-pipeline</option>
                    </select>
                  </div>

                  {/* Environment */}
                  <div>
                    <label className="label-caps block mb-1 font-mono">Environment</label>
                    <div className="grid grid-cols-3 gap-2">
                      {(['production', 'staging', 'development'] as const).map((env) => (
                        <button
                          key={env}
                          type="button"
                          onClick={() => setEnvironment(env)}
                          className={[
                            'py-2 px-3 rounded-md font-mono text-mono-data uppercase tracking-wider text-[11px] border transition-colors',
                            environment === env
                              ? 'bg-primary/20 border-primary text-primary'
                              : 'bg-surface-container border-border-subtle text-on-surface-variant hover:text-on-surface',
                          ].join(' ')}
                        >
                          {env}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Version */}
                  <div>
                    <label className="label-caps block mb-1 font-mono">Release Tag / Version</label>
                    <input
                      type="text"
                      value={version}
                      onChange={(e) => setVersion(e.target.value)}
                      className="input-base"
                      placeholder="v1.0.0"
                    />
                  </div>
                </div>
              )}
            </div>

            {/* Error */}
            {error && (
              <div className="p-3 bg-risk-red/10 border border-risk-red/30 rounded-md font-mono text-mono-data text-risk-red text-sm flex items-center gap-2">
                <span className="material-symbols-outlined text-[16px]">error</span>
                {error}
              </div>
            )}

            <div className="pt-1">
              <Button
                type="submit"
                variant="primary"
                loading={isSubmitting}
                icon="rocket_launch"
                className="w-full"
              >
                {isSubmitting ? 'Running Pipeline…' : 'Run Pipeline'}
              </Button>
            </div>
          </form>
        </div>

        {/* ── Right Panel: AI Incident Commander Results or Recent History ────────────────────────── */}
        <div className="lg:col-span-7 flex flex-col gap-6">
          {mode === 'monitor' && monitorResult ? (
            <div className="bg-surface-container-lowest border border-border-subtle rounded-md p-6 flex flex-col gap-5">
              <div className="flex justify-between items-center border-b border-border-subtle pb-4">
                <div>
                  <h2 className="font-headline text-headline-sm text-on-surface flex items-center gap-2">
                    <span className="material-symbols-outlined text-primary">monitor_heart</span>
                    {monitorResult.service_name} Monitoring Status
                  </h2>
                  <p className="font-mono text-xs text-on-surface-variant mt-1">{monitorResult.base_url}</p>
                </div>
                <span className={`font-mono text-xs px-3 py-1 rounded-full uppercase border font-bold ${
                  monitorResult.health_status === 'healthy' && !monitorResult.incident_detected
                    ? 'text-success border-success/40 bg-success/10'
                    : 'text-risk-amber border-risk-amber/40 bg-risk-amber/10'
                }`}>
                  {monitorResult.incident_detected ? 'ANOMALY DETECTED' : monitorResult.health_status}
                </span>
              </div>

              {/* Health Metrics & Probes */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 font-mono text-xs">
                <div className="p-3 bg-surface-container rounded border border-border-subtle">
                  <span className="text-on-surface-variant block mb-1">HEALTH PROBE</span>
                  <span className={monitorResult.health_status === 'healthy' ? 'text-success font-bold' : 'text-risk-red font-bold'}>
                    {monitorResult.health_status.toUpperCase()}
                  </span>
                </div>
                <div className="p-3 bg-surface-container rounded border border-border-subtle">
                  <span className="text-on-surface-variant block mb-1">REAL P99 LATENCY</span>
                  <span className="text-primary font-bold">
                    {monitorResult.metrics?.find((m: any) => m.name === 'p99_latency_ms')?.value ?? '—'} ms
                  </span>
                </div>
                <div className="p-3 bg-surface-container rounded border border-border-subtle">
                  <span className="text-on-surface-variant block mb-1">REAL LOGS COLLECTED</span>
                  <span className="text-on-surface font-bold">{monitorResult.logs?.length ?? 0} lines</span>
                </div>
              </div>

              {/* Real Logs Display */}
              {monitorResult.logs && monitorResult.logs.length > 0 && (
                <div className="bg-background rounded border border-border-subtle p-3 font-mono text-xs flex flex-col gap-1 max-h-48 overflow-y-auto">
                  <span className="text-on-surface-variant label-caps mb-1">Real Collected Logs</span>
                  {monitorResult.logs.map((l: any, idx: number) => (
                    <div key={idx} className={l.level === 'ERROR' || l.level === 'FATAL' ? 'text-risk-red' : 'text-on-surface-variant'}>
                      <span className="opacity-60">[{l.level}]</span> {l.message}
                    </div>
                  ))}
                </div>
              )}

              {/* RCA & Agent 5 Search Section */}
              {monitorResult.rca_report ? (
                <div className="p-4 bg-surface-container border border-primary/30 rounded flex flex-col gap-4">
                  <div className="flex justify-between items-center">
                    <h3 className="font-headline text-sm text-primary flex items-center gap-2">
                      <span className="material-symbols-outlined text-[18px]">psychology</span>
                      Agent 3 Gemini Root Cause Analysis
                    </h3>
                    <span className="font-mono text-xs text-primary font-bold">
                      Confidence: {Math.round((monitorResult.rca_report.confidence ?? 0.8) * 100)}%
                    </span>
                  </div>

                  <div>
                    <span className="label-caps block mb-1">Root Cause</span>
                    <p className="font-body text-sm text-on-surface">{monitorResult.rca_report.root_cause}</p>
                  </div>

                  {monitorResult.rca_report.summary && (
                    <div>
                      <span className="label-caps block mb-1">Executive Summary</span>
                      <p className="font-body text-xs text-on-surface-variant">{monitorResult.rca_report.summary}</p>
                    </div>
                  )}

                  {/* Recommendations */}
                  {monitorResult.rca_report.recommendations?.length > 0 && (
                    <div>
                      <span className="label-caps block mb-1">Suggested Recovery Actions</span>
                      <div className="flex flex-col gap-2 mt-1">
                        {monitorResult.rca_report.recommendations.map((rec: any, idx: number) => (
                          <div key={idx} className="p-2 bg-surface-container-lowest rounded border border-border-subtle font-mono text-xs">
                            <span className="text-primary font-bold">#{rec.rank} [{rec.category}]:</span> {rec.action}
                            <p className="text-on-surface-variant mt-0.5 text-[11px]">{rec.rationale}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Agent 5 Historical Incident Search Matches */}
                  {monitorResult.rca_report.similar_incidents?.length > 0 && (
                    <div>
                      <span className="label-caps block mb-1">Agent 5 Vector Search (Similar Historical Incidents)</span>
                      <div className="flex flex-col gap-2 mt-1">
                        {monitorResult.rca_report.similar_incidents.map((match: any, idx: number) => (
                          <div key={idx} className="p-2 bg-surface-container-lowest rounded border border-success/30 font-mono text-xs">
                            <span className="text-success font-bold">[{match.similarity_percentage ?? 85}% Match] {match.incident_id ?? 'INC-PAST'}</span>: {match.root_cause}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Single Approve Solution Action Button */}
                  <div className="pt-2 flex justify-end">
                    <Button
                      variant="primary"
                      icon="check_circle"
                      onClick={async () => {
                        try {
                          const { knowledgeService } = await import('../services');
                          await knowledgeService.storeApprovedSolution({
                            app_name: monitorResult.service_name,
                            deployment_id: monitorResult.rca_report.deployment_id || 'dep-monitored',
                            severity: monitorResult.rca_report.severity || 'high',
                            root_cause: monitorResult.rca_report.root_cause,
                            causal_chain: monitorResult.rca_report.causal_chain || [monitorResult.rca_report.root_cause],
                            summary: monitorResult.rca_report.summary || monitorResult.rca_report.root_cause,
                            selected_recommendation: monitorResult.rca_report.recommendations?.[0]?.action || 'Manual resolution',
                          });
                          navigate('/knowledge');
                        } catch (err: any) {
                          alert('Failed storing incident: ' + err.message);
                        }
                      }}
                    >
                      Approve Solution
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="p-4 bg-surface-container rounded border border-border-subtle font-mono text-xs text-success flex items-center gap-2">
                  <span className="material-symbols-outlined text-[18px]">check_circle</span>
                  Service is responding normally. No anomalies detected.
                </div>
              )}
            </div>
          ) : (
            <div className="bg-surface-container-lowest border border-border-subtle rounded-md">
              <div className="px-5 py-4 border-b border-border-subtle flex justify-between items-center bg-surface-container-low rounded-t-md">
                <h2 className="font-headline text-headline-sm text-on-surface">Recent Deployments &amp; Monitored Apps</h2>
                <span className="font-mono text-label-caps text-on-surface-variant">{deployments.length} total</span>
              </div>
              <DataTable
                rows={deployments}
                keyFn={(d) => d.id}
                onRowClick={(d) =>
                  navigate(d.traceId ? `/deployments/${d.traceId}` : `/deployments/${d.id}`)
                }
                columns={[
                  {
                    key: 'service',
                    header: 'Service',
                    render: (d) => (
                      <div>
                        <p className="font-mono text-mono-data text-on-surface font-medium">{d.service}</p>
                        <p className="font-mono text-[11px] text-on-surface-variant">{d.version}</p>
                      </div>
                    ),
                  },
                  {
                    key: 'environment',
                    header: 'Env',
                    render: (d) => (
                      <span className="font-mono text-mono-data text-on-surface-variant">{d.environment}</span>
                    ),
                  },
                  {
                    key: 'status',
                    header: 'Status',
                    render: (d) => <StatusBadge status={d.status} />,
                  },
                  {
                    key: 'startedAt',
                    header: 'Timestamp',
                    align: 'right',
                    render: (d) => (
                      <span className="font-mono text-mono-data text-on-surface-variant">
                        {new Date(d.startedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    ),
                  },
                ]}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
