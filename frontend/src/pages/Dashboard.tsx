import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import MetricCard from '../components/ui/MetricCard';
import DataTable from '../components/ui/DataTable';
import StatusBadge from '../components/ui/StatusBadge';
import Sparkline from '../components/ui/Sparkline';
import Button from '../components/ui/Button';
import { metricsService, deploymentService, incidentService } from '../services';
import type { MetricData, Deployment, Incident } from '../types';

export default function Dashboard() {
  const navigate = useNavigate();
  const [metrics, setMetrics] = useState<MetricData[]>([]);
  const [deployments, setDeployments] = useState<Deployment[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);

  useEffect(() => {
    metricsService.getMetrics().then(setMetrics);
    deploymentService.getAll().then((data) => setDeployments(data.slice(0, 5)));
    incidentService.getAll().then((data) => setIncidents(data.filter((i) => i.status === 'open' || i.status === 'investigating')));
  }, []);

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
            onRowClick={(d) => navigate(`/deployments/${d.id}`)}
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

        {/* Incidents Panel */}
        <div className="lg:col-span-4 bg-surface-container-lowest border border-border-subtle rounded-md flex flex-col min-h-[360px]">
          <div className="px-5 py-4 border-b border-border-subtle flex justify-between items-center bg-surface-container-low rounded-t-md">
            <h2 className="font-headline text-headline-sm text-on-surface">Active Incidents</h2>
            <button
              onClick={() => navigate('/incidents')}
              className="font-mono text-label-caps text-primary hover:text-primary-fixed-dim transition-colors uppercase flex items-center gap-1"
            >
              Feed <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
            </button>
          </div>
          <div className="flex-1 p-6 flex flex-col items-center justify-center text-center relative overflow-hidden">
            {incidents.length === 0 ? (
              <>
                {/* Causal Chain Motif Background */}
                <div className="absolute inset-0 flex items-center justify-center opacity-20 pointer-events-none">
                  <svg className="stroke-outline-variant fill-surface-container-lowest" width="200" height="200" viewBox="0 0 200 200">
                    <rect x="20" y="80" width="40" height="40" rx="4" strokeWidth="1" />
                    <line x1="60" y1="100" x2="100" y2="100" strokeWidth="1" strokeDasharray="2 2" />
                    <circle cx="120" cy="100" r="20" strokeWidth="1" />
                    <line x1="140" y1="100" x2="170" y2="70" strokeWidth="1" strokeDasharray="2 2" />
                    <rect x="160" y="30" width="30" height="30" rx="4" strokeWidth="1" />
                    <line x1="140" y1="100" x2="170" y2="130" strokeWidth="1" strokeDasharray="2 2" />
                    <rect x="160" y="140" width="30" height="30" rx="4" strokeWidth="1" />
                  </svg>
                </div>
                <div className="relative z-10 flex flex-col items-center gap-3">
                  <div className="w-12 h-12 rounded-full bg-surface-container flex items-center justify-center border border-border-subtle">
                    <span className="material-symbols-outlined text-success text-2xl">check_circle</span>
                  </div>
                  <p className="font-body text-body-md text-on-surface-variant max-w-[220px]">
                    No active incidents. All systems operating normally.
                  </p>
                </div>
              </>
            ) : (
              <div className="w-full flex flex-col gap-3">
                {incidents.map((inc) => (
                  <div
                    key={inc.id}
                    onClick={() => navigate(`/incidents/${inc.id}/rca`)}
                    className="p-4 bg-surface-container border border-border-subtle rounded-md text-left cursor-pointer hover:border-primary/50 transition-colors"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-mono text-mono-data text-risk-red">{inc.id}</span>
                      <StatusBadge status={inc.severity} />
                    </div>
                    <p className="font-body text-body-md text-on-surface font-medium line-clamp-1">{inc.title}</p>
                    <p className="font-mono text-mono-data text-on-surface-variant text-[11px] mt-1">{inc.service}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
