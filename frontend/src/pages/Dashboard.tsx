import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import MetricCard from '../components/ui/MetricCard';
import DataTable from '../components/ui/DataTable';
import StatusBadge from '../components/ui/StatusBadge';
import Sparkline from '../components/ui/Sparkline';
import Button from '../components/ui/Button';
import { metricsService, deploymentService, knowledgeService } from '../services';
import type { MetricData, Deployment, KnowledgeEntry } from '../types';

export default function Dashboard() {
  const navigate = useNavigate();
  const [metrics, setMetrics] = useState<MetricData[]>([]);
  const [deployments, setDeployments] = useState<Deployment[]>([]);
  const [allIncidents, setAllIncidents] = useState<KnowledgeEntry[]>([]);

  useEffect(() => {
    metricsService.getMetrics().then(setMetrics);
    deploymentService.getAll().then((data) => setDeployments(data.slice(0, 5)));
    knowledgeService.getAll().then(setAllIncidents);
  }, []);

  const activeIncidents = allIncidents.filter((i) => !i.hasPostmortem);
  const recoveredIncidents = allIncidents.filter((i) => i.hasPostmortem);
  const latestDeployment = deployments[0];

  return (
    <div className="flex flex-col gap-6">
      {/* Page Title */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-headline text-headline-md text-on-surface">Main Dashboard</h1>
          <p className="font-body text-body-md text-on-surface-variant">Real-time system health and deployment pipeline telemetry</p>
        </div>
        <Button variant="primary" icon="rocket_launch" onClick={() => navigate('/deployments')}>
          New Deployment
        </Button>
      </div>

      {/* Key Metrics Row */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {metrics.map((m, idx) => (
          <MetricCard key={idx} {...m} />
        ))}
      </section>

      {/* Latest Deployment Banner (if available) */}
      {latestDeployment && (
        <div className="bg-surface-container-lowest border border-border-subtle rounded-md p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-md bg-primary/10 border border-primary/30 flex items-center justify-center flex-shrink-0">
              <span className="material-symbols-outlined text-primary text-[20px]">rocket_launch</span>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-label-caps text-on-surface-variant">Latest Deployment</span>
                <StatusBadge status={latestDeployment.status} />
              </div>
              <p className="font-mono text-mono-data text-on-surface font-medium">
                {latestDeployment.service} ({latestDeployment.version}) — {latestDeployment.environment}
              </p>
            </div>
          </div>
          <Button
            variant="ghost"
            size="sm"
            icon="arrow_forward"
            onClick={() => navigate(latestDeployment.traceId ? `/deployments/${latestDeployment.traceId}` : `/deployments/${latestDeployment.id}`)}
          >
            View Pipeline Status
          </Button>
        </div>
      )}

      {/* Main Data Panels */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Deployments Panel */}
        <div className="lg:col-span-8 bg-surface-container-lowest border border-border-subtle rounded-md flex flex-col">
          <div className="px-5 py-4 border-b border-border-subtle flex justify-between items-center bg-surface-container-low rounded-t-md">
            <h2 className="font-headline text-headline-sm text-on-surface">Deployments</h2>
            <button
              onClick={() => navigate('/deployments')}
              className="font-mono text-label-caps text-primary hover:text-primary-fixed-dim transition-colors uppercase flex items-center gap-1"
            >
              View All <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
            </button>
          </div>
          <DataTable
            rows={deployments}
            keyFn={(d) => d.id}
            onRowClick={(d) => navigate(d.traceId ? `/deployments/${d.traceId}` : `/deployments/${d.id}`)}
            columns={[
              {
                key: 'service',
                header: 'Service',
                render: (d) => (
                  <span className="font-mono text-mono-data text-on-surface font-medium">
                    {d.service}
                  </span>
                )
              },
              {
                key: 'environment',
                header: 'Environment',
                render: (d) => (
                  <span className="font-mono text-mono-data text-on-surface-variant">
                    {d.environment}
                  </span>
                )
              },
              {
                key: 'status',
                header: 'Status',
                render: (d) => <StatusBadge status={d.status} />
              },
              {
                key: 'health',
                header: 'Health Signal',
                align: 'right',
                render: (d) => (
                  <div className="flex justify-end">
                    <Sparkline healthy={d.status === 'healthy'} />
                  </div>
                )
              }
            ]}
          />
        </div>

        {/* Active & Recovered Incidents Panel */}
        <div className="lg:col-span-4 bg-surface-container-lowest border border-border-subtle rounded-md flex flex-col min-h-[360px]">
          <div className="px-5 py-4 border-b border-border-subtle flex justify-between items-center bg-surface-container-low rounded-t-md">
            <h2 className="font-headline text-headline-sm text-on-surface">Incidents &amp; Memory</h2>
            <button
              onClick={() => navigate('/incidents')}
              className="font-mono text-label-caps text-primary hover:text-primary-fixed-dim transition-colors uppercase flex items-center gap-1"
            >
              Feed <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
            </button>
          </div>
          <div className="flex-1 p-6 flex flex-col gap-4">
            {/* Active Incidents */}
            <div>
              <p className="font-mono text-label-caps text-on-surface-variant uppercase mb-2">
                Active ({activeIncidents.length})
              </p>
              {activeIncidents.length === 0 ? (
                <div className="p-3 bg-surface-container rounded border border-border-subtle text-center font-mono text-xs text-on-surface-variant flex items-center justify-center gap-2">
                  <span className="material-symbols-outlined text-success text-[16px]">check_circle</span>
                  No active incidents
                </div>
              ) : (
                <div className="flex flex-col gap-2">
                  {activeIncidents.map((inc) => (
                    <div
                      key={inc.id}
                      onClick={() => navigate(`/incidents/${inc.id}/rca`)}
                      className="p-3 bg-surface-container border border-border-subtle rounded-md cursor-pointer hover:border-primary/50 transition-colors"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-mono text-mono-data text-risk-red text-xs">{inc.id}</span>
                        <StatusBadge status={inc.severity} />
                      </div>
                      <p className="font-body text-body-md text-on-surface font-medium text-xs line-clamp-1">{inc.title}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Recovered Incidents */}
            <div>
              <p className="font-mono text-label-caps text-on-surface-variant uppercase mb-2">
                Recently Recovered ({recoveredIncidents.length})
              </p>
              {recoveredIncidents.length === 0 ? (
                <div className="p-3 bg-surface-container rounded border border-border-subtle text-center font-mono text-xs text-on-surface-variant">
                  No recovered incidents logged yet
                </div>
              ) : (
                <div className="flex flex-col gap-2">
                  {recoveredIncidents.slice(0, 3).map((inc) => (
                    <div
                      key={inc.id}
                      onClick={() => navigate(`/postmortem/${inc.id}`)}
                      className="p-3 bg-surface-container border border-border-subtle rounded-md cursor-pointer hover:border-primary/50 transition-colors"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-mono text-mono-data text-success text-xs flex items-center gap-1">
                          <span className="material-symbols-outlined text-[12px]">check_circle</span>
                          RESOLVED
                        </span>
                        <span className="font-mono text-[10px] text-on-surface-variant">{inc.date}</span>
                      </div>
                      <p className="font-body text-body-md text-on-surface font-medium text-xs line-clamp-1">{inc.title}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
