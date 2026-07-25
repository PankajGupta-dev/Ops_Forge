import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import StatusBadge from '../components/ui/StatusBadge';
import Button from '../components/ui/Button';
import { deploymentService } from '../services';
import type { Deployment } from '../types';

export default function DeploymentDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [deployment, setDeployment] = useState<Deployment | null>(null);
  const [activeTab, setActiveTab] = useState<'logs' | 'config'>('logs');

  useEffect(() => {
    if (id) {
      deploymentService.getById(id).then((d) => {
        if (d) setDeployment(d);
        else deploymentService.getAll().then((all) => setDeployment(all[0] || null));
      });
    }
  }, [id]);

  if (!deployment) {
    return <div className="p-8 text-center text-on-surface-variant font-mono">Loading deployment details...</div>;
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Header / Breadcrumb */}
      <div className="flex items-center gap-2 text-on-surface-variant font-mono text-mono-data">
        <button onClick={() => navigate('/deployments')} className="hover:text-primary transition-colors">
          Deployments
        </button>
        <span>/</span>
        <span className="text-on-surface">{deployment.id}</span>
      </div>

      {/* Main Banner */}
      <div className="bg-surface-container-lowest border border-border-subtle rounded-md p-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h1 className="font-headline text-headline-md text-on-surface">{deployment.service}</h1>
            <StatusBadge status={deployment.status} size="md" />
          </div>
          <p className="font-mono text-mono-data text-on-surface-variant">
            {deployment.version} • {deployment.environment} • Commit <span className="text-primary">{deployment.commit}</span> ({deployment.branch})
          </p>
        </div>

        <div className="flex items-center gap-3">
          {deployment.status === 'failed' && (
            <Button variant="danger" icon="warning" onClick={() => navigate('/incidents')}>
              View Incident
            </Button>
          )}
          <Button variant="ghost" icon="settings_backup_restore" onClick={() => alert('Rollback triggered')}>
            Rollback
          </Button>
          <Button variant="primary" icon="refresh" onClick={() => alert('Re-deploying...')}>
            Re-deploy
          </Button>
        </div>
      </div>

      {/* Metadata Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-surface-container-lowest border border-border-subtle rounded-md p-4">
          <p className="label-caps mb-1">Deployed By</p>
          <p className="font-mono text-mono-data text-on-surface font-medium">{deployment.deployedBy}</p>
        </div>
        <div className="bg-surface-container-lowest border border-border-subtle rounded-md p-4">
          <p className="label-caps mb-1">Started At</p>
          <p className="font-mono text-mono-data text-on-surface font-medium">
            {new Date(deployment.startedAt).toLocaleTimeString()}
          </p>
        </div>
        <div className="bg-surface-container-lowest border border-border-subtle rounded-md p-4">
          <p className="label-caps mb-1">Duration</p>
          <p className="font-mono text-mono-data text-on-surface font-medium">{deployment.duration || 'In progress...'}</p>
        </div>
        <div className="bg-surface-container-lowest border border-border-subtle rounded-md p-4">
          <p className="label-caps mb-1">Health Score</p>
          <p className="font-mono text-mono-data text-primary font-medium">{deployment.healthScore}%</p>
        </div>
      </div>

      {/* Tabs & Content */}
      <div className="bg-surface-container-lowest border border-border-subtle rounded-md">
        <div className="flex border-b border-border-subtle bg-surface-container-low px-4 pt-2 gap-4">
          <button
            onClick={() => setActiveTab('logs')}
            className={[
              'pb-3 font-mono text-mono-data border-b-2 font-medium transition-colors',
              activeTab === 'logs'
                ? 'border-primary text-primary'
                : 'border-transparent text-on-surface-variant hover:text-on-surface'
            ].join(' ')}
          >
            Execution Logs ({deployment.logs?.length || 0})
          </button>
          <button
            onClick={() => setActiveTab('config')}
            className={[
              'pb-3 font-mono text-mono-data border-b-2 font-medium transition-colors',
              activeTab === 'config'
                ? 'border-primary text-primary'
                : 'border-transparent text-on-surface-variant hover:text-on-surface'
            ].join(' ')}
          >
            Configuration Spec
          </button>
        </div>

        <div className="p-4">
          {activeTab === 'logs' ? (
            <div className="bg-background rounded-md border border-border-subtle p-4 font-mono text-mono-data text-on-surface flex flex-col gap-2 max-h-[400px] overflow-y-auto">
              {deployment.logs && deployment.logs.length > 0 ? (
                deployment.logs.map((log) => (
                  <div key={log.id} className="flex gap-4 hover:bg-surface-container/50 p-1 rounded">
                    <span className="text-on-surface-variant text-[11px] select-none">{log.timestamp}</span>
                    <span className={[
                      'uppercase text-[11px] font-bold w-12 text-center rounded px-1',
                      log.level === 'error' ? 'bg-risk-red/20 text-risk-red' :
                      log.level === 'warn' ? 'bg-risk-amber/20 text-risk-amber' : 'bg-primary/20 text-primary'
                    ].join(' ')}>
                      {log.level}
                    </span>
                    <span className="flex-1">{log.message}</span>
                  </div>
                ))
              ) : (
                <div className="text-on-surface-variant italic">No logs available for this deployment.</div>
              )}
            </div>
          ) : (
            <div className="bg-background rounded-md border border-border-subtle p-4 font-mono text-mono-data text-primary">
              <pre>{JSON.stringify({
                service: deployment.service,
                version: deployment.version,
                environment: deployment.environment,
                replicas: 3,
                resources: { cpu: '500m', memory: '1Gi' },
                healthCheck: '/healthz'
              }, null, 2)}</pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
