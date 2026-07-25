import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Button from '../components/ui/Button';
import StatusBadge from '../components/ui/StatusBadge';

export default function RecoveryVerification() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [progress, setProgress] = useState(0);
  const [isDone, setIsDone] = useState(false);

  useEffect(() => {
    const timer = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) {
          clearInterval(timer);
          setIsDone(true);
          return 100;
        }
        return prev + 25;
      });
    }, 600);
    return () => clearInterval(timer);
  }, []);

  const verificationSteps = [
    { label: 'Replicas scaled down & image reverted', done: progress >= 25 },
    { label: 'Database connection pool patch applied', done: progress >= 50 },
    { label: 'Pods scaled up & readines probes passing', done: progress >= 75 },
    { label: 'Post-recovery latency & error rate baseline verified', done: progress >= 100 }
  ];

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center gap-2 text-on-surface-variant font-mono text-mono-data">
        <button onClick={() => navigate('/incidents')} className="hover:text-primary transition-colors">
          Incidents
        </button>
        <span>/</span>
        <span className="text-on-surface">{id || 'INC-2024-003'}</span>
        <span>/</span>
        <span className="text-success font-medium">Recovery Verification</span>
      </div>

      {/* Execution Status Header */}
      <div className="bg-surface-container-lowest border border-border-subtle rounded-md p-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h1 className="font-headline text-headline-md text-on-surface">Executing Automated Recovery</h1>
            <StatusBadge status={isDone ? 'verified' : 'executing'} size="md" />
          </div>
          <p className="font-mono text-mono-data text-on-surface-variant">
            Orchestrating multi-node patch deployment and automated verification suite
          </p>
        </div>

        {isDone && (
          <Button
            variant="primary"
            icon="description"
            onClick={() => navigate(`/postmortem/${id || 'pm-001'}`)}
          >
            Generate Postmortem Report
          </Button>
        )}
      </div>

      {/* Progress Bar */}
      <div className="bg-surface-container-lowest border border-border-subtle rounded-md p-6">
        <div className="flex justify-between items-center mb-2 font-mono text-mono-data">
          <span className="text-on-surface font-medium">Verification Progress</span>
          <span className="text-primary font-bold">{progress}%</span>
        </div>
        <div className="w-full bg-surface-container h-2 rounded-full overflow-hidden border border-border-subtle">
          <div
            className="bg-primary h-full transition-all duration-500 ease-out"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Verification Checklist */}
      <div className="bg-surface-container-lowest border border-border-subtle rounded-md p-6">
        <h2 className="font-headline text-headline-sm text-on-surface mb-4 flex items-center gap-2">
          <span className="material-symbols-outlined text-primary text-[20px]">fact_check</span>
          System Verification Checklist
        </h2>

        <div className="flex flex-col gap-3 font-mono text-mono-data">
          {verificationSteps.map((step, idx) => (
            <div
              key={idx}
              className={[
                'p-4 rounded-md border flex items-center justify-between transition-colors',
                step.done
                  ? 'bg-success/5 border-success/30 text-on-surface'
                  : 'bg-surface-container border-border-subtle text-on-surface-variant'
              ].join(' ')}
            >
              <div className="flex items-center gap-3">
                <span className={`material-symbols-outlined text-[20px] ${step.done ? 'text-success' : 'text-on-surface-variant'}`}>
                  {step.done ? 'check_circle' : 'hourglass_empty'}
                </span>
                <span>{step.label}</span>
              </div>
              <span className="text-[11px] uppercase tracking-wider">
                {step.done ? 'PASS' : 'PENDING'}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
