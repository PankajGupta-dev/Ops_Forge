import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Button from '../components/ui/Button';
import DataTable from '../components/ui/DataTable';
import StatusBadge from '../components/ui/StatusBadge';
import { deploymentService } from '../services';
import type { Deployment } from '../types';

export default function DeploymentPlanner() {
  const navigate = useNavigate();
  const [deployments, setDeployments] = useState<Deployment[]>([]);
  const [service, setService] = useState('api-gateway');
  const [environment, setEnvironment] = useState<'production' | 'staging' | 'development'>('production');
  const [branch, setBranch] = useState('main');
  const [version, setVersion] = useState('v2.5.0');
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    deploymentService.getAll().then(setDeployments);
  }, []);

  const handleDeploy = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    const newDep = await deploymentService.create({
      service,
      environment,
      branch,
      version,
      status: 'deploying',
      commit: Math.random().toString(36).substring(2, 9),
      deployedBy: 'ops-engineer'
    });
    setIsSubmitting(false);
    navigate(`/deployments/${newDep.id}`);
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Page Header */}
      <div>
        <h1 className="font-headline text-headline-md text-on-surface">Deployment Planner</h1>
        <p className="font-body text-body-md text-on-surface-variant">Configure and launch zero-downtime deployments across environments</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Planner Form */}
        <div className="lg:col-span-5 bg-surface-container-lowest border border-border-subtle rounded-md p-6">
          <h2 className="font-headline text-headline-sm text-on-surface mb-4 flex items-center gap-2">
            <span className="material-symbols-outlined text-primary text-[20px]">tune</span>
            New Deployment Pipeline
          </h2>

          <form onSubmit={handleDeploy} className="flex flex-col gap-4">
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
                        : 'bg-surface-container border-border-subtle text-on-surface-variant hover:text-on-surface'
                    ].join(' ')}
                  >
                    {env}
                  </button>
                ))}
              </div>
            </div>

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

            <div className="pt-2">
              <Button
                type="submit"
                variant="primary"
                loading={isSubmitting}
                icon="rocket_launch"
                className="w-full"
              >
                Trigger Deployment
              </Button>
            </div>
          </form>
        </div>

        {/* Deployments List */}
        <div className="lg:col-span-7 bg-surface-container-lowest border border-border-subtle rounded-md">
          <div className="px-5 py-4 border-b border-border-subtle flex justify-between items-center bg-surface-container-low rounded-t-md">
            <h2 className="font-headline text-headline-sm text-on-surface">Recent Deployments</h2>
            <span className="font-mono text-label-caps text-on-surface-variant">{deployments.length} total</span>
          </div>
          <DataTable
            rows={deployments}
            keyFn={(d) => d.id}
            onRowClick={(d) => navigate(`/deployments/${d.id}`)}
            columns={[
              {
                key: 'service',
                header: 'Service',
                render: (d) => (
                  <div>
                    <p className="font-mono text-mono-data text-on-surface font-medium">{d.service}</p>
                    <p className="font-mono text-[11px] text-on-surface-variant">{d.version}</p>
                  </div>
                )
              },
              {
                key: 'environment',
                header: 'Env',
                render: (d) => <span className="font-mono text-mono-data text-on-surface-variant">{d.environment}</span>
              },
              {
                key: 'status',
                header: 'Status',
                render: (d) => <StatusBadge status={d.status} />
              },
              {
                key: 'startedAt',
                header: 'Deployed',
                align: 'right',
                render: (d) => (
                  <span className="font-mono text-mono-data text-on-surface-variant">
                    {new Date(d.startedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                )
              }
            ]}
          />
        </div>
      </div>
    </div>
  );
}
