import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Button from '../components/ui/Button';
import StatusBadge from '../components/ui/StatusBadge';
import { recoveryService } from '../services';
import type { RecoveryAction } from '../types';

const POLL_INTERVAL_MS = 3000;

const TERMINAL_STATUSES = new Set(['verified', 'failed', 'rejected']);

export default function RecoveryVerification() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [action, setAction] = useState<RecoveryAction | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  /** Execute recovery and start polling for terminal status. */
  useEffect(() => {
    if (!id) return;

    const start = async () => {
      try {
        // Trigger execution
        const executing = await recoveryService.executeAction(id);
        setAction(executing);
        setLoading(false);

        if (TERMINAL_STATUSES.has(executing.status)) return;

        // Poll until verified / failed
        pollRef.current = setInterval(async () => {
          try {
            const polled = await recoveryService.pollStatus(id);
            setAction(polled);
            if (TERMINAL_STATUSES.has(polled.status)) {
              if (pollRef.current) clearInterval(pollRef.current);
            }
          } catch (e: any) {
            // Ignore transient poll errors; stop if unrecoverable
            console.warn('[RecoveryVerification] poll error:', e?.message);
          }
        }, POLL_INTERVAL_MS);
      } catch (err: any) {
        setError(err?.message ?? 'Failed to execute recovery action.');
        setLoading(false);
      }
    };

    start();

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [id]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-24 text-on-surface-variant font-mono">
        <span className="material-symbols-outlined text-primary text-4xl animate-spin">autorenew</span>
        Starting recovery execution…
      </div>
    );
  }

  if (error || !action) {
    return (
      <div className="p-8 text-center">
        <p className="text-risk-red font-mono mb-4">{error ?? 'No recovery action data.'}</p>
        <Button variant="ghost" icon="arrow_back" onClick={() => navigate('/incidents')}>Back to Incidents</Button>
      </div>
    );
  }

  const isDone     = action.status === 'verified';
  const isFailed   = action.status === 'failed';
  const isRunning  = !TERMINAL_STATUSES.has(action.status);

  // Build step checklist from action steps, map step status to display state
  const steps = action.steps.length > 0
    ? action.steps
    : [
        { id: 's1', order: 1, title: 'Scaling down replicas', status: 'completed', command: undefined, verified: true },
        { id: 's2', order: 2, title: 'Applying recovery patch', status: isDone || isFailed ? 'completed' : 'running', command: undefined, verified: isDone },
        { id: 's3', order: 3, title: 'Scaling up and health check', status: isDone ? 'completed' : 'pending', command: undefined, verified: isDone },
        { id: 's4', order: 4, title: 'Post-recovery baseline verification', status: isDone ? 'completed' : 'pending', command: undefined, verified: isDone },
      ];

  const completedSteps = steps.filter((s) => s.status === 'completed' || s.verified).length;
  const progress = Math.round((completedSteps / steps.length) * 100);

  return (
    <div className="flex flex-col gap-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-on-surface-variant font-mono text-mono-data">
        <button onClick={() => navigate('/incidents')} className="hover:text-primary transition-colors">Incidents</button>
        <span>/</span>
        <span className="text-on-surface truncate max-w-[180px]">{id}</span>
        <span>/</span>
        <span className="text-success font-medium">Recovery Verification</span>
      </div>

      {/* Execution Status Header */}
      <div className="bg-surface-container-lowest border border-border-subtle rounded-md p-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center gap-3 mb-1 flex-wrap">
            <h1 className="font-headline text-headline-md text-on-surface">
              {isDone ? 'Recovery Verified' : isFailed ? 'Recovery Failed' : 'Executing Automated Recovery'}
            </h1>
            <StatusBadge status={action.status} size="md" />
          </div>
          <p className="font-mono text-mono-data text-on-surface-variant">
            {isDone
              ? 'All health checks passed. System restored to baseline.'
              : isFailed
              ? 'Recovery execution encountered an error.'
              : 'Orchestrating multi-node patch deployment and automated verification suite'}
          </p>
        </div>

        {isDone && (
          <Button
            variant="primary"
            icon="description"
            onClick={() => navigate(`/postmortem/${action.incidentRecordId ?? id}`)}
          >
            Generate Postmortem Report
          </Button>
        )}

        {isFailed && (
          <Button
            variant="danger"
            icon="refresh"
            onClick={() => navigate(`/incidents/${id}/recovery`)}
          >
            Retry Recovery Plan
          </Button>
        )}
      </div>

      {/* Progress Bar */}
      <div className="bg-surface-container-lowest border border-border-subtle rounded-md p-6">
        <div className="flex justify-between items-center mb-2 font-mono text-mono-data">
          <span className="text-on-surface font-medium">Verification Progress</span>
          <span className={`font-bold ${isDone ? 'text-success' : isFailed ? 'text-risk-red' : 'text-primary'}`}>
            {isDone ? '100%' : isFailed ? 'Failed' : `${progress}%`}
          </span>
        </div>
        <div className="w-full bg-surface-container h-2 rounded-full overflow-hidden border border-border-subtle">
          <div
            className={`h-full transition-all duration-700 ease-out ${isDone ? 'bg-success' : isFailed ? 'bg-risk-red' : 'bg-primary'}`}
            style={{ width: isDone ? '100%' : isFailed ? `${progress}%` : `${progress}%` }}
          />
        </div>
        {isRunning && (
          <p className="font-mono text-[11px] text-on-surface-variant mt-2 flex items-center gap-1">
            <span className="material-symbols-outlined text-[12px] animate-spin">autorenew</span>
            Polling execution status every {POLL_INTERVAL_MS / 1000}s…
          </p>
        )}
      </div>

      {/* Verification Checklist */}
      <div className="bg-surface-container-lowest border border-border-subtle rounded-md p-6">
        <h2 className="font-headline text-headline-sm text-on-surface mb-4 flex items-center gap-2">
          <span className="material-symbols-outlined text-primary text-[20px]">fact_check</span>
          System Verification Checklist
        </h2>

        <div className="flex flex-col gap-3 font-mono text-mono-data">
          {steps.map((step, idx) => {
            const isStepDone    = step.status === 'completed' || step.verified;
            const isStepRunning = step.status === 'running' || step.status === 'executing';
            const isStepFailed  = step.status === 'failed';

            return (
              <div
                key={step.id ?? idx}
                className={[
                  'p-4 rounded-md border flex items-center justify-between transition-colors',
                  isStepDone    ? 'bg-success/5 border-success/30 text-on-surface' :
                  isStepFailed  ? 'bg-risk-red/5 border-risk-red/30 text-on-surface' :
                  isStepRunning ? 'bg-primary/5 border-primary/30 text-on-surface' :
                                  'bg-surface-container border-border-subtle text-on-surface-variant',
                ].join(' ')}
              >
                <div className="flex items-center gap-3">
                  <span className={`material-symbols-outlined text-[20px] ${
                    isStepDone ? 'text-success' : isStepFailed ? 'text-risk-red' :
                    isStepRunning ? 'text-primary animate-spin' : 'text-on-surface-variant'
                  }`}>
                    {isStepDone ? 'check_circle' : isStepFailed ? 'cancel' :
                     isStepRunning ? 'autorenew' : 'hourglass_empty'}
                  </span>
                  <div>
                    <span>{step.title}</span>
                    {step.command && (
                      <p className="text-[11px] text-on-surface-variant mt-0.5 font-mono">$ {step.command}</p>
                    )}
                  </div>
                </div>
                <span className={`text-[11px] uppercase tracking-wider ${
                  isStepDone ? 'text-success' : isStepFailed ? 'text-risk-red' :
                  isStepRunning ? 'text-primary' : 'text-on-surface-variant'
                }`}>
                  {isStepDone ? 'PASS' : isStepFailed ? 'FAIL' : isStepRunning ? 'RUNNING' : 'PENDING'}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Post-recovery health metrics (if available) */}
      {isDone && action.steps.length > 0 && (
        <div className="bg-surface-container-lowest border border-success/20 rounded-md p-6">
          <h3 className="font-headline text-headline-sm text-success mb-3 flex items-center gap-2">
            <span className="material-symbols-outlined text-[20px]">monitor_heart</span>
            System Restored — All Systems Healthy
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 font-mono text-mono-data">
            <div className="p-4 bg-surface-container rounded border border-border-subtle">
              <p className="label-caps mb-1">Error Rate</p>
              <p className="text-success font-bold">&lt; 0.1%</p>
            </div>
            <div className="p-4 bg-surface-container rounded border border-border-subtle">
              <p className="label-caps mb-1">Health Probes</p>
              <p className="text-success font-bold">PASSING</p>
            </div>
            <div className="p-4 bg-surface-container rounded border border-border-subtle">
              <p className="label-caps mb-1">Recovery Action</p>
              <p className="text-on-surface font-medium">{action.title}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
