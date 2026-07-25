import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Button from '../components/ui/Button';
import Badge from '../components/ui/Badge';
import { recoveryService } from '../services';
import type { RecoveryAction } from '../types';

export default function RecoveryApproval() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [action, setAction] = useState<RecoveryAction | null>(null);
  const [isExecuting, setIsExecuting] = useState(false);

  useEffect(() => {
    const incId = id || 'INC-2024-003';
    recoveryService.getAction(incId).then(setAction);
  }, [id]);

  const handleApprove = async () => {
    if (!action) return;
    setIsExecuting(true);
    await recoveryService.approveAction(action.id);
    setIsExecuting(false);
    navigate(`/incidents/${id || 'INC-2024-003'}/verify`);
  };

  if (!action) {
    return <div className="p-8 text-center text-on-surface-variant font-mono">Loading recovery action details...</div>;
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-on-surface-variant font-mono text-mono-data">
        <button onClick={() => navigate('/incidents')} className="hover:text-primary transition-colors">
          Incidents
        </button>
        <span>/</span>
        <button onClick={() => navigate(`/incidents/${id}/rca`)} className="hover:text-primary transition-colors">
          RCA
        </button>
        <span>/</span>
        <span className="text-primary font-medium">Recovery Approval</span>
      </div>

      {/* Recovery Plan Summary Banner */}
      <div className="bg-surface-container-lowest border border-border-subtle rounded-md p-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <span className="font-mono text-mono-data text-primary">STRATEGY #{action.id}</span>
            <Badge variant={action.riskLevel === 'high' ? 'red' : action.riskLevel === 'medium' ? 'amber' : 'primary'}>
              {action.riskLevel} Risk
            </Badge>
          </div>
          <h1 className="font-headline text-headline-md text-on-surface">{action.title}</h1>
          <p className="font-body text-body-md text-on-surface-variant mt-1">{action.description}</p>
        </div>

        <div className="flex items-center gap-3">
          <Button variant="danger" icon="close" onClick={() => navigate('/incidents')}>
            Reject Strategy
          </Button>
          <Button
            variant="primary"
            icon="play_arrow"
            loading={isExecuting}
            onClick={handleApprove}
          >
            Approve & Execute
          </Button>
        </div>
      </div>

      {/* Steps Execution Plan */}
      <div className="bg-surface-container-lowest border border-border-subtle rounded-md p-6">
        <h2 className="font-headline text-headline-sm text-on-surface mb-4 flex items-center gap-2">
          <span className="material-symbols-outlined text-primary text-[20px]">format_list_numbered</span>
          Orchestrated Recovery Steps ({action.steps.length})
        </h2>

        <div className="flex flex-col gap-3">
          {action.steps.map((step) => (
            <div
              key={step.id}
              className="p-4 bg-surface-container border border-border-subtle rounded-md flex flex-col gap-2"
            >
              <div className="flex items-center gap-3">
                <span className="w-6 h-6 rounded-full bg-primary/20 text-primary border border-primary/40 font-mono text-xs flex items-center justify-center font-bold">
                  {step.order}
                </span>
                <span className="font-body text-body-md text-on-surface font-medium">{step.title}</span>
              </div>
              {step.command && (
                <div className="bg-background rounded p-3 font-mono text-mono-data text-on-surface-variant border border-border-subtle overflow-x-auto">
                  <code>$ {step.command}</code>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Impact Assessment Card */}
      <div className="bg-surface-container-lowest border border-border-subtle rounded-md p-6">
        <h3 className="font-headline text-headline-sm text-on-surface mb-3 flex items-center gap-2">
          <span className="material-symbols-outlined text-risk-amber text-[20px]">shield</span>
          Safety & Impact Assessment
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 font-mono text-mono-data">
          <div className="p-4 bg-surface-container rounded border border-border-subtle">
            <p className="label-caps mb-1">Estimated Downtime</p>
            <p className="text-on-surface font-medium">Zero Downtime (Rolling)</p>
          </div>
          <div className="p-4 bg-surface-container rounded border border-border-subtle">
            <p className="label-caps mb-1">Estimated Duration</p>
            <p className="text-on-surface font-medium">{action.estimatedDuration}</p>
          </div>
          <div className="p-4 bg-surface-container rounded border border-border-subtle">
            <p className="label-caps mb-1">Auto-Rollback Trigger</p>
            <p className="text-on-surface font-medium">Active (If 5xx &gt; 1%)</p>
          </div>
        </div>
      </div>
    </div>
  );
}
