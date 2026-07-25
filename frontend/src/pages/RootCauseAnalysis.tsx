import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import StatusBadge from '../components/ui/StatusBadge';
import Button from '../components/ui/Button';
import CausalChain from '../components/ui/CausalChain';
import { incidentService } from '../services';
import type { Incident, RootCauseAnalysis as RCAType } from '../types';

export default function RootCauseAnalysis() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [incident, setIncident] = useState<Incident | null>(null);
  const [rca, setRca] = useState<RCAType | null>(null);

  useEffect(() => {
    const incId = id || 'INC-2024-003';
    incidentService.getById(incId).then((inc) => {
      if (inc) setIncident(inc);
      else incidentService.getAll().then((all) => setIncident(all[2] || all[0]));
    });
    incidentService.getRCA(incId).then(setRca);
  }, [id]);

  if (!incident || !rca) {
    return <div className="p-8 text-center text-on-surface-variant font-mono">Loading Root Cause Analysis...</div>;
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center gap-2 text-on-surface-variant font-mono text-mono-data">
        <button onClick={() => navigate('/incidents')} className="hover:text-primary transition-colors">
          Incidents
        </button>
        <span>/</span>
        <span className="text-on-surface">{incident.id}</span>
        <span>/</span>
        <span className="text-primary font-medium">Root Cause Analysis</span>
      </div>

      {/* Incident Banner */}
      <div className="bg-surface-container-lowest border border-border-subtle rounded-md p-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <span className="font-mono text-mono-data text-risk-red">{incident.id}</span>
            <StatusBadge status={incident.severity} />
            <StatusBadge status={incident.status} />
          </div>
          <h1 className="font-headline text-headline-md text-on-surface">{incident.title}</h1>
          <p className="font-body text-body-md text-on-surface-variant mt-1">{incident.description}</p>
        </div>

        <div className="flex items-center gap-3 flex-shrink-0">
          <div className="bg-primary/10 border border-primary/30 px-4 py-2 rounded-md text-center">
            <p className="label-caps text-[10px]">AI Confidence</p>
            <p className="font-mono text-headline-sm text-primary font-bold">{rca.confidence}%</p>
          </div>
          <Button
            variant="primary"
            icon="task_alt"
            onClick={() => navigate(`/incidents/${incident.id}/recovery`)}
          >
            Review Recovery Options
          </Button>
        </div>
      </div>

      {/* Causal Chain Topology Section */}
      <div className="bg-surface-container-lowest border border-border-subtle rounded-md p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-headline text-headline-sm text-on-surface flex items-center gap-2">
            <span className="material-symbols-outlined text-primary text-[20px]">account_tree</span>
            Causal Chain Topology
          </h2>
          <span className="label-caps">Deterministic Graph Model</span>
        </div>
        <div className="bg-background rounded-md border border-border-subtle p-4">
          <CausalChain nodes={rca.nodes} edges={rca.edges} />
        </div>
      </div>

      {/* Narrative Section */}
      <div className="bg-surface-container-lowest border border-border-subtle rounded-md p-6">
        <h2 className="font-headline text-headline-sm text-on-surface mb-3 flex items-center gap-2">
          <span className="material-symbols-outlined text-primary text-[20px]">psychology</span>
          Autonomous Diagnostic Narrative
        </h2>
        <div className="bg-surface-container p-5 rounded-md border border-border-subtle font-body text-body-md text-on-surface leading-relaxed">
          <p className="mb-4">{rca.narrative}</p>
          <div className="p-3 bg-primary/10 border border-primary/30 rounded font-mono text-mono-data text-primary text-xs flex items-center gap-2">
            <span className="material-symbols-outlined text-[16px]">info</span>
            Recommendation: Execute automated patch rollout to resolve Postgres connection leak.
          </div>
        </div>
      </div>
    </div>
  );
}
