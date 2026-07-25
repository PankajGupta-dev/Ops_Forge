import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Button from '../components/ui/Button';
import DataTable from '../components/ui/DataTable';
import StatusBadge from '../components/ui/StatusBadge';
import { deploymentService, pipelineService } from '../services';
import type { Deployment } from '../types';

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
  const [description, setDescription] = useState('');
  const [dockerfile, setDockerfile] = useState(DEFAULT_DOCKERFILE);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [service, setService] = useState('api-gateway');
  const [environment, setEnvironment] = useState<'production' | 'staging' | 'development'>('production');
  const [branch, setBranch] = useState('main');
  const [version, setVersion] = useState('v2.5.0');
  const [simulateFailure, setSimulateFailure] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    deploymentService.getAll().then(setDeployments);
  }, []);

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
      // Create a local deployment entry first (for history list)
      const localDep = await deploymentService.create({
        service,
        environment,
        branch,
        version,
        status: 'deploying',
        commit: Math.random().toString(36).substring(2, 9),
        deployedBy: 'ops-engineer',
      });

      // Run the full E2E pipeline via orchestrator
      const result = await pipelineService.run({
        description,
        dockerfile,
        simulateFailure,
      });

      // Patch local record with trace_id and pipeline status
      deploymentService.update(localDep.id, {
        traceId: result.traceId,
        status: result.workflowStatus === 'failed' ? 'failed' : 'healthy',
      });

      // Navigate to pipeline visualization page using trace_id
      navigate(`/deployments/${result.traceId}`);
    } catch (err: any) {
      setError(err?.message ?? 'Pipeline failed to start. Is the backend running?');
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Page Header */}
      <div>
        <h1 className="font-headline text-headline-md text-on-surface">Deployment Planner</h1>
        <p className="font-body text-body-md text-on-surface-variant">
          Trigger the full autonomous pipeline — from deployment plan to recovery approval
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* ── Pipeline Form ─────────────────────────────────── */}
        <div className="lg:col-span-5 bg-surface-container-lowest border border-border-subtle rounded-md p-6 flex flex-col gap-5">
          <h2 className="font-headline text-headline-sm text-on-surface flex items-center gap-2">
            <span className="material-symbols-outlined text-primary text-[20px]">rocket_launch</span>
            New Pipeline Run
          </h2>

          <form onSubmit={handleDeploy} className="flex flex-col gap-4">
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
                className="input-base w-full h-48 resize-y font-mono text-xs leading-relaxed"
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

                  {/* Branch */}
                  <div>
                    <label className="label-caps block mb-1 font-mono">Git Branch</label>
                    <input
                      type="text"
                      value={branch}
                      onChange={(e) => setBranch(e.target.value)}
                      className="input-base"
                      placeholder="main or feature/..."
                    />
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

        {/* ── Recent Deployments List ────────────────────────── */}
        <div className="lg:col-span-7 bg-surface-container-lowest border border-border-subtle rounded-md">
          <div className="px-5 py-4 border-b border-border-subtle flex justify-between items-center bg-surface-container-low rounded-t-md">
            <h2 className="font-headline text-headline-sm text-on-surface">Recent Deployments</h2>
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
                header: 'Deployed',
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
      </div>
    </div>
  );
}
